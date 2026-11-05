"""Text extraction and structured AI candidate extraction."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date
from hashlib import sha256
from io import BytesIO
import json
import re
from typing import Any

from .fetch import FetchedSource
from .models import CandidateUpdate, SourceDocument
from .taxonomy import STAGE_LABELS
from .validation import validate_candidate


class TextExtractor:
    """Extract normalized text from HTML, plain text, or PDF sources."""

    def extract(self, fetched: FetchedSource, title: str, source_type: str) -> SourceDocument:
        publication_date: date | None = None
        if "pdf" in fetched.content_type or fetched.final_url.lower().endswith(".pdf"):
            from pypdf import PdfReader
            reader = PdfReader(BytesIO(fetched.content))
            text = "\n".join(page.extract_text() or "" for page in reader.pages)
            if not title and reader.metadata and reader.metadata.title:
                title = str(reader.metadata.title)
        elif "html" in fetched.content_type:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(fetched.content, "html.parser")
            publication_date = _html_publication_date(soup)
            for element in soup(["script", "style", "nav", "footer"]):
                element.decompose()
            text = soup.get_text(" ", strip=True)
            if not title and soup.title:
                title = soup.title.get_text(" ", strip=True)
        else:
            text = fetched.content.decode("utf-8", errors="replace")
        return SourceDocument(
            url=fetched.final_url,
            title=title,
            text=" ".join(text.split()),
            source_name=title or fetched.final_url,
            source_type=source_type,
            publication_date=publication_date,
            original_url=fetched.requested_url,
        )


class CandidateExtractor(ABC):
    """Interface for converting a source document to review candidates."""

    @abstractmethod
    def extract(
        self, state: str, document: SourceDocument, detected_date: date, current_known_stage_order: int | None
    ) -> list[CandidateUpdate]:
        """Return only material, evidence-grounded candidates."""


class OpenAICandidateExtractor(CandidateExtractor):
    """Schema-constrained OpenAI extractor followed by deterministic validation."""

    def __init__(self, api_key: str, model: str) -> None:
        from openai import OpenAI
        self._client = OpenAI(api_key=api_key)
        self._model = model

    def extract(
        self, state: str, document: SourceDocument, detected_date: date, current_known_stage_order: int | None
    ) -> list[CandidateUpdate]:
        response = self._client.responses.create(
            model=self._model,
            instructions=_EXTRACTION_INSTRUCTIONS,
            input=json.dumps({
                "state": state,
                "detected_date": detected_date.isoformat(),
                "source_url": document.url,
                "source_name": document.source_name,
                "source_type": document.source_type,
                "source_publication_date": document.publication_date.isoformat() if document.publication_date else None,
                "current_known_stage_order": current_known_stage_order,
                "text": document.text[:80_000],
            }),
            text={"format": {"type": "json_schema", "name": "workforce_pell_candidates", "strict": True, "schema": _AI_SCHEMA}},
        )
        payload = json.loads(response.output_text)
        candidates = [_candidate_from_ai(item, state, document, detected_date, current_known_stage_order) for item in payload["candidates"]]
        for candidate in candidates:
            validate_candidate(candidate)
        return candidates


def _candidate_from_ai(
    item: dict[str, Any], state: str, document: SourceDocument, detected: date, current_known_stage_order: int | None
) -> CandidateUpdate:
    order = item["proposed_stage_order"]
    event_date = date.fromisoformat(item["proposed_event_date"]) if item["proposed_event_date"] else None
    publication_date = date.fromisoformat(item["source_publication_date"]) if item["source_publication_date"] else None
    identity = "|".join([state, item["proposed_event_type"], item["proposed_event_date"] or "", document.url, item["evidence_excerpt"]])
    return CandidateUpdate(
        candidate_id=f"WP-{state[:2].upper()}-{detected:%Y%m%d}-{sha256(identity.encode()).hexdigest()[:10]}",
        state=state,
        detected_date=detected,
        proposed_event_date=event_date,
        source_publication_date=publication_date,
        date_basis=item["date_basis"],
        proposed_event_type=item["proposed_event_type"],
        proposed_change=item["proposed_change"],
        source_name=document.source_name,
        source_url=document.url,
        source_type=document.source_type,
        evidence_excerpt=item["evidence_excerpt"],
        ai_confidence=item["ai_confidence"],
        stage_change=item["stage_change"],
        current_known_stage_order=current_known_stage_order,
        proposed_stage_order=order,
        proposed_stage_label=STAGE_LABELS[order] if order is not None else None,
        metadata={
            "stage_uncertain": item["stage_uncertain"],
            "original_input_url": document.original_url or document.url,
            "canonical_final_url": document.url,
        },
    )


def _html_publication_date(soup: Any) -> date | None:
    """Read an explicit ISO-like publication date from common HTML metadata."""
    selectors = (
        ('meta[property="article:published_time"]', "content"),
        ('meta[name="date"]', "content"),
        ('meta[name="publish-date"]', "content"),
        ('time[datetime]', "datetime"),
    )
    for selector, attribute in selectors:
        element = soup.select_one(selector)
        raw = str(element.get(attribute, "")) if element else ""
        match = re.match(r"(\d{4}-\d{2}-\d{2})", raw.strip())
        if match:
            try:
                return date.fromisoformat(match.group(1))
            except ValueError:
                continue
    return None


_EXTRACTION_INSTRUCTIONS = """Extract only material Workforce Pell implementation events. Never invent dates.
An application/submission is not an approval. A future window is not open. State and federal approval are distinct.
A material event need not change stage. Stage 0 means Not yet reviewed only and never uncertainty. If evidence cannot
determine stage, return null stage values. Publication/detected dates must never substitute for event date. Evidence
excerpt must directly support the event. Return no candidate for general commentary or insufficient evidence."""

_NULLABLE_INT = {"anyOf": [{"type": "integer", "minimum": 0, "maximum": 5}, {"type": "null"}]}
_NULLABLE_DATE = {"anyOf": [{"type": "string", "format": "date"}, {"type": "null"}]}
_AI_ITEM_PROPERTIES: dict[str, Any] = {
    "proposed_event_date": _NULLABLE_DATE,
    "source_publication_date": _NULLABLE_DATE,
    "date_basis": {"type": "string", "enum": ["Exact event date", "Effective date", "Source publication date only", "Detected date only", "Unknown"]},
    "proposed_event_type": {"type": "string"},
    "proposed_change": {"type": "string"},
    "evidence_excerpt": {"type": "string"},
    "ai_confidence": {"type": "string", "enum": ["High", "Medium", "Low"]},
    "stage_change": {"type": "boolean"},
    "proposed_stage_order": _NULLABLE_INT,
    "stage_uncertain": {"type": "boolean"},
}
_AI_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {"candidates": {"type": "array", "items": {
        "type": "object", "properties": _AI_ITEM_PROPERTIES,
        "required": list(_AI_ITEM_PROPERTIES), "additionalProperties": False,
    }}},
    "required": ["candidates"],
    "additionalProperties": False,
}
