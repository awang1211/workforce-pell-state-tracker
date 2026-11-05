"""End-to-end orchestration for discovery, extraction, deduplication, and review staging."""

from __future__ import annotations

from datetime import date
import logging
from dataclasses import dataclass, field
from typing import Any, Sequence
from urllib.parse import urlsplit
from uuid import uuid4

from .classify import assess_materiality
from .config import StateConfig
from .dedupe import check_duplicate
from .extract import CandidateExtractor, TextExtractor
from .fetch import FetchedSource, RetrievalBlocked, SourceFetcher
from .models import CandidateUpdate, SourceDocument
from .search import SearchProvider, canonicalize_source_url
from .sheets import SafeSheetsGateway
from .state_detection import detect_state, validate_state_name
from .validation import validate_candidate

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class RetrievalWarning:
    """Structured warning describing why normal source retrieval was unavailable."""

    code: str
    message: str
    source_url: str
    http_status: int | None = None


@dataclass(slots=True)
class ManualIngestionResult:
    """Outcome of ingesting one user-supplied URL."""

    original_url: str
    canonical_final_url: str | None = None
    detected_state: str | None = None
    retrieval_method: str | None = None
    status: str = "No material event"
    material_event_found: bool = False
    candidates: list[CandidateUpdate] = field(default_factory=list)
    duplicates: list[CandidateUpdate] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    retrieval_warnings: list[RetrievalWarning] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Return a CLI-friendly representation including provenance and skips."""
        return {
            "original_input_url": self.original_url,
            "canonical_final_url": self.canonical_final_url,
            "detected_state": self.detected_state,
            "retrieval_method": self.retrieval_method,
            "status": self.status,
            "material_event_found": self.material_event_found,
            "warnings": self.warnings,
            "retrieval_warnings": [
                {
                    "code": warning.code,
                    "message": warning.message,
                    "source_url": warning.source_url,
                    "http_status": warning.http_status,
                }
                for warning in self.retrieval_warnings
            ],
            "candidates": [
                {"review_queue_row": item.to_review_queue_dict(), "internal_metadata": item.metadata}
                for item in self.candidates
            ],
            "duplicates_not_appended": [
                {"review_queue_row": item.to_review_queue_dict(), "internal_metadata": item.metadata}
                for item in self.duplicates
            ],
        }


class WorkforcePellPipeline:
    """Coordinate the MVP while preserving the analyst review boundary."""

    def __init__(
        self,
        search_provider: SearchProvider,
        fetcher: SourceFetcher,
        text_extractor: TextExtractor,
        candidate_extractor: CandidateExtractor,
        sheets: SafeSheetsGateway,
        lookback_days: int = 90,
    ) -> None:
        self._search = search_provider
        self._fetcher = fetcher
        self._text = text_extractor
        self._candidates = candidate_extractor
        self._sheets = sheets
        self._lookback_days = lookback_days

    def run(self, states: Sequence[StateConfig], dry_run: bool = True) -> list[CandidateUpdate]:
        """Process all states; append only new/possible candidates unless dry-running."""
        run_id = uuid4().hex
        state_status = self._sheets.read_tab("State_Status")
        event_history = self._sheets.read_tab("Event_History")
        review_queue = self._sheets.read_tab("Review_Queue")
        output: list[CandidateUpdate] = []
        for state in states:
            try:
                output.extend(self._process_state(
                    state, _current_stage(state.name, state_status), event_history, review_queue, run_id
                ))
            except Exception:
                LOGGER.exception("state_failed", extra={"run_id": run_id, "state": state.name, "step": "state"})
        if not dry_run and output:
            updated_range = self._sheets.append_review_candidates(output)
            LOGGER.info("review_queue_append_succeeded", extra={"run_id": run_id, "step": "write", "source_url": updated_range})
        return output

    def ingest_url(
        self, url: str, state_override: str | None = None, dry_run: bool = True
    ) -> ManualIngestionResult:
        """Ingest one URL, invoking search only as fallback for blocked retrieval."""
        result = ManualIngestionResult(original_url=url)
        try:
            fetched = self._fetcher.fetch(url)
            canonical_url = canonicalize_source_url(fetched.final_url)
            result.canonical_final_url = canonical_url
            result.retrieval_method = (
                "direct_pdf"
                if "pdf" in fetched.content_type or canonical_url.lower().endswith(".pdf")
                else "direct_html"
            )
            normalized_fetch = FetchedSource(url, canonical_url, fetched.content_type, fetched.content)
            document = self._text.extract(normalized_fetch, "", _manual_source_type(canonical_url))
        except RetrievalBlocked as blocked:
            canonical_url = canonicalize_source_url(blocked.url or url)
            result.canonical_final_url = canonical_url
            result.retrieval_method = "web_search_fallback"
            result.retrieval_warnings.append(RetrievalWarning(
                code="source_access_blocked",
                message=f"Direct source fetch was blocked: {blocked.reason}",
                source_url=canonical_url,
                http_status=blocked.status_code,
            ))
            evidence = self._search.search_blocked_url(canonical_url, blocked.page_title, state_override)
            if not evidence.evidence_sufficient:
                result.status = "Needs more evidence"
                result.warnings.append(evidence.reason)
                return result
            document = SourceDocument(
                url=evidence.source_url,
                title=evidence.title,
                text=evidence.text,
                source_name=evidence.title,
                source_type="Web search fallback source",
                original_url=url,
            )
        return self._process_manual_document(result, document, state_override, dry_run)

    def ingest_text(
        self,
        text: str,
        source_url: str,
        state_override: str | None = None,
        dry_run: bool = True,
        source_name: str | None = None,
    ) -> ManualIngestionResult:
        """Ingest user-supplied article text while preserving its source URL."""
        canonical_url = canonicalize_source_url(source_url)
        result = ManualIngestionResult(
            original_url=source_url,
            canonical_final_url=canonical_url,
            retrieval_method="manual_text",
        )
        document = SourceDocument(
            url=canonical_url,
            title=source_name or canonical_url,
            text=text,
            source_name=source_name or canonical_url,
            source_type="Manually supplied text",
            original_url=source_url,
        )
        return self._process_manual_document(result, document, state_override, dry_run)

    def _process_manual_document(
        self,
        result: ManualIngestionResult,
        document: SourceDocument,
        state_override: str | None,
        dry_run: bool,
    ) -> ManualIngestionResult:
        """Run the shared classifier, extractor, validator, deduplicator, and writer."""
        assessment = assess_materiality(document)
        if not assessment.potentially_material:
            result.warnings.append("No material Workforce Pell implementation update was found")
            return result
        result.material_event_found = True

        if state_override:
            state = validate_state_name(state_override)
        else:
            detection = detect_state(document)
            state = detection.state
            if detection.warning:
                result.warnings.append(detection.warning)
        result.detected_state = state
        if state is None:
            result.warnings.append("No candidate was extracted or written because state validation is unresolved")
            return result

        state_status = self._sheets.read_tab("State_Status")
        event_history = self._sheets.read_tab("Event_History")
        review_queue = self._sheets.read_tab("Review_Queue")
        current_stage = _current_stage(state, state_status)
        for candidate in self._candidates.extract(state, document, date.today(), current_stage):
            candidate.metadata.update({
                "ingestion_mode": "manual_text" if result.retrieval_method == "manual_text" else "manual_url",
                "retrieval_method": result.retrieval_method,
                "original_input_url": result.original_url,
                "canonical_final_url": result.canonical_final_url,
            })
            validate_candidate(candidate)
            decision = check_duplicate(
                candidate,
                event_history,
                [*review_queue, *(item.to_review_queue_dict() for item in result.candidates)],
            )
            candidate.duplicate_check = _decision_text(decision)
            if decision.classification in {"exact_duplicate", "likely_duplicate"}:
                result.duplicates.append(candidate)
            else:
                result.candidates.append(candidate)

        if not result.candidates and not result.duplicates:
            result.material_event_found = False
            result.warnings.append("No material Workforce Pell implementation update was found after structured extraction")
        elif result.candidates:
            result.status = "Ready for review"
        else:
            result.status = "Duplicate found"
        if not dry_run and result.candidates:
            self._sheets.append_review_candidates(result.candidates)
        return result

    def _process_state(
        self,
        state: StateConfig,
        current_known_stage_order: int | None,
        event_history: list[dict[str, str]],
        review_queue: list[dict[str, str]],
        run_id: str,
    ) -> list[CandidateUpdate]:
        accepted: list[CandidateUpdate] = []
        for result in self._search.search(state, self._lookback_days):
            try:
                fetched = self._fetcher.fetch(result.url)
                document = self._text.extract(fetched, result.title, result.source_type)
                assessment = assess_materiality(document)
                if not assessment.potentially_material:
                    LOGGER.info("finding_rejected_non_material", extra={"run_id": run_id, "state": state.name, "step": "classify", "source_url": result.url})
                    continue
                for candidate in self._candidates.extract(
                    state.name, document, date.today(), current_known_stage_order
                ):
                    decision = check_duplicate(candidate, event_history, [*review_queue, *(item.to_review_queue_dict() for item in accepted)])
                    candidate.duplicate_check = _decision_text(decision)
                    if decision.classification in {"exact_duplicate", "likely_duplicate"}:
                        LOGGER.info("duplicate_detected", extra={"run_id": run_id, "state": state.name, "step": "dedupe", "candidate_id": candidate.candidate_id})
                        continue
                    accepted.append(candidate)
            except Exception:
                LOGGER.exception("source_failed", extra={"run_id": run_id, "state": state.name, "step": "source", "source_url": result.url})
        return accepted


def _decision_text(decision: object) -> str:
    classification = getattr(decision, "classification")
    reason = getattr(decision, "reason")
    matched_table = getattr(decision, "matched_table")
    matched_id = getattr(decision, "matched_id")
    suffix = f" ({matched_table} {matched_id})" if matched_table and matched_id else ""
    return f"{classification}: {reason}{suffix}"


def _current_stage(state: str, rows: list[dict[str, str]]) -> int | None:
    """Read the analyst-approved stage order without treating blank as Stage 0."""
    for row in rows:
        if row.get("State", "").strip().lower() != state.lower():
            continue
        raw = next((row.get(key, "") for key in ("Stage_Order", "Current_Stage", "Implementation_Stage", "Stage") if row.get(key)), "")
        prefix = raw.strip().split(" ", 1)[0]
        return int(prefix) if prefix.isdigit() and 0 <= int(prefix) <= 5 else None
    return None


def _manual_source_type(url: str) -> str:
    """Classify the supplied source conservatively from its final domain."""
    domain = urlsplit(url).netloc.lower()
    return "Official government source" if domain.endswith(".gov") or ".gov." in domain else "Supplied source"
