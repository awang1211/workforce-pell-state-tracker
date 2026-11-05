"""Offline tests for the manual URL ingestion orchestration path."""

from __future__ import annotations

from datetime import date
import unittest

from tests.helpers import make_candidate
from src.config import StateConfig
from src.extract import CandidateExtractor
from src.fetch import FetchedSource, RetrievalBlocked, detect_block_page
from src.models import CandidateUpdate, SourceDocument
from src.pipeline import WorkforcePellPipeline
from src.search import FallbackEvidence, SearchProvider
from src.state_detection import detect_state


class FailingSearchProvider(SearchProvider):
    """Prove that manual ingestion never invokes web search."""

    def search(self, state: StateConfig, lookback_days: int) -> list[object]:
        raise AssertionError("Search provider must not be called in manual URL mode")

    def search_blocked_url(
        self, url: str, page_title: str | None = None, state: str | None = None
    ) -> FallbackEvidence:
        raise AssertionError("Fallback search must not be called for a successful direct fetch")


class FakeFallbackSearchProvider(SearchProvider):
    def __init__(self, sufficient: bool) -> None:
        self.sufficient = sufficient
        self.calls = 0

    def search(self, state: StateConfig, lookback_days: int) -> list[object]:
        raise AssertionError("Automated search must not run in manual ingestion")

    def search_blocked_url(
        self, url: str, page_title: str | None = None, state: str | None = None
    ) -> FallbackEvidence:
        del page_title, state
        self.calls += 1
        text = (
            "Delaware Workforce Pell applications open under the implementation framework with verified dates. "
            "This source-grounded fallback context is long enough for conservative downstream review."
            if self.sufficient else "Possible Pell mention without supporting evidence."
        )
        return FallbackEvidence(
            "Blocked article", url, "ccdaily.com", text, self.sufficient,
            "Matched evidence found" if self.sufficient else "Needs more matched source evidence",
        )


class FakeFetcher:
    def __init__(self, content_type: str = "text/html", final_url: str = "https://labor.delaware.gov/update") -> None:
        self.content_type = content_type
        self.final_url = final_url

    def fetch(self, url: str) -> FetchedSource:
        return FetchedSource(url, self.final_url, self.content_type, b"fixture bytes")


class BlockedFetcher:
    def fetch(self, url: str) -> FetchedSource:
        raise RetrievalBlocked(url, 403, "Cloudflare challenge page")


class FakeTextExtractor:
    def __init__(self, text: str, title: str = "Workforce Pell update") -> None:
        self.text = text
        self.title = title
        self.seen_content_type = ""

    def extract(self, fetched: FetchedSource, title: str, source_type: str) -> SourceDocument:
        del title
        self.seen_content_type = fetched.content_type
        return SourceDocument(
            url=fetched.final_url, title=self.title, text=self.text, source_name=self.title,
            source_type=source_type, publication_date=date(2026, 8, 18), original_url=fetched.requested_url,
        )


class FakeCandidateExtractor(CandidateExtractor):
    def __init__(self, count: int = 1) -> None:
        self.count = count
        self.calls = 0

    def extract(
        self, state: str, document: SourceDocument, detected_date: date, current_known_stage_order: int | None
    ) -> list[CandidateUpdate]:
        self.calls += 1
        candidates = [make_candidate(
            candidate_id=f"manual-{index}", state=state, detected_date=detected_date,
            source_publication_date=document.publication_date, source_name=document.source_name,
            source_url=document.url, source_type=document.source_type,
            current_known_stage_order=current_known_stage_order,
        ) for index in range(self.count)]
        if self.count > 1:
            candidates[1].proposed_event_type = "Application deadline announced"
            candidates[1].proposed_change = "A separate application deadline was announced."
            candidates[1].evidence_excerpt = "Applications must be submitted by September 30."
        return candidates


class FakeSheets:
    def __init__(self, event_history: list[dict[str, str]] | None = None) -> None:
        self.event_history = event_history or []
        self.appended: list[CandidateUpdate] = []
        self.read_count = 0

    def read_tab(self, tab_name: str) -> list[dict[str, str]]:
        self.read_count += 1
        if tab_name == "State_Status":
            return [{"State": "Delaware", "Stage_Order": "2"}, {"State": "California", "Stage_Order": "2"}]
        if tab_name == "Event_History":
            return self.event_history
        return []

    def append_review_candidates(self, candidates: list[CandidateUpdate]) -> str:
        self.appended.extend(candidates)
        return "'Review_Queue'!A2:T2"


def make_pipeline(
    text: str, *, content_type: str = "text/html", final_url: str = "https://labor.delaware.gov/update",
    count: int = 1, sheets: FakeSheets | None = None,
) -> tuple[WorkforcePellPipeline, FakeTextExtractor, FakeSheets]:
    text_extractor = FakeTextExtractor(text)
    fake_sheets = sheets or FakeSheets()
    pipeline = WorkforcePellPipeline(
        FailingSearchProvider(), FakeFetcher(content_type, final_url), text_extractor,
        FakeCandidateExtractor(count), fake_sheets, 90,
    )
    return pipeline, text_extractor, fake_sheets


class ManualIngestionTests(unittest.TestCase):
    material_text = "Delaware Workforce Pell applications open under the new implementation framework."

    def test_manual_html_url_ingestion_returns_multiple_events(self) -> None:
        pipeline, extractor, sheets = make_pipeline(self.material_text, count=2)
        result = pipeline.ingest_url("https://labor.delaware.gov/start?utm_source=test")
        self.assertEqual(extractor.seen_content_type, "text/html")
        self.assertEqual(len(result.candidates), 2)
        self.assertEqual(sheets.appended, [])
        self.assertEqual(result.original_url, "https://labor.delaware.gov/start?utm_source=test")
        self.assertEqual(result.canonical_final_url, "https://labor.delaware.gov/update")
        self.assertEqual(result.retrieval_method, "direct_html")

    def test_manual_pdf_url_ingestion(self) -> None:
        pipeline, extractor, _ = make_pipeline(self.material_text, content_type="application/pdf",
                                               final_url="https://labor.delaware.gov/update.pdf")
        result = pipeline.ingest_url("https://labor.delaware.gov/document")
        self.assertEqual(extractor.seen_content_type, "application/pdf")
        self.assertEqual(len(result.candidates), 1)
        self.assertTrue(result.candidates[0].source_url.endswith("update.pdf"))
        self.assertEqual(result.retrieval_method, "direct_pdf")

    def test_403_cloudflare_page_detection(self) -> None:
        body = b"<html><title>Attention Required</title>Cloudflare Ray ID: abc</html>"
        reason = detect_block_page(403, "text/html", body)
        self.assertIsNotNone(reason)
        self.assertIn("403", reason or "")

    def test_block_page_is_not_classified_as_source_content(self) -> None:
        search = FakeFallbackSearchProvider(sufficient=False)
        text_extractor = FakeTextExtractor("This must never be classified")
        candidate_extractor = FakeCandidateExtractor()
        sheets = FakeSheets()
        pipeline = WorkforcePellPipeline(
            search, BlockedFetcher(), text_extractor, candidate_extractor, sheets,
        )
        result = pipeline.ingest_url("https://ccdaily.com/blocked", state_override="Indiana")
        self.assertEqual(text_extractor.seen_content_type, "")
        self.assertEqual(candidate_extractor.calls, 0)
        self.assertEqual(sheets.read_count, 0)
        self.assertEqual(result.status, "Needs more evidence")
        self.assertEqual(result.retrieval_warnings[0].code, "source_access_blocked")

    def test_fallback_search_path_extracts_with_provenance(self) -> None:
        search = FakeFallbackSearchProvider(sufficient=True)
        sheets = FakeSheets()
        pipeline = WorkforcePellPipeline(
            search, BlockedFetcher(), FakeTextExtractor("unused"), FakeCandidateExtractor(), sheets,
        )
        result = pipeline.ingest_url("https://ccdaily.com/workforce-pell", state_override="Delaware")
        self.assertEqual(search.calls, 1)
        self.assertEqual(result.retrieval_method, "web_search_fallback")
        self.assertEqual(len(result.candidates), 1)
        self.assertEqual(result.candidates[0].metadata["retrieval_method"], "web_search_fallback")
        self.assertEqual(sheets.appended, [])

    def test_insufficient_fallback_evidence_does_not_write(self) -> None:
        search = FakeFallbackSearchProvider(sufficient=False)
        sheets = FakeSheets()
        pipeline = WorkforcePellPipeline(
            search, BlockedFetcher(), FakeTextExtractor("unused"), FakeCandidateExtractor(), sheets,
        )
        result = pipeline.ingest_url(
            "https://ccdaily.com/workforce-pell", state_override="Indiana", dry_run=False
        )
        self.assertEqual(result.status, "Needs more evidence")
        self.assertEqual(result.candidates, [])
        self.assertEqual(sheets.appended, [])
        self.assertEqual(sheets.read_count, 0)

    def test_state_detection_from_explicit_content(self) -> None:
        document = SourceDocument("https://example.gov/x", "Update", "California Workforce Pell applications open.",
                                  "Agency", "Official government source")
        self.assertEqual(detect_state(document).state, "California")

    def test_state_override_resolves_ambiguous_content(self) -> None:
        text = "Workforce Pell applications open under the implementation framework."
        pipeline, _, _ = make_pipeline(text, final_url="https://example.gov/update")
        result = pipeline.ingest_url("https://example.gov/update", state_override="delaware")
        self.assertEqual(result.detected_state, "Delaware")
        self.assertEqual(result.candidates[0].state, "Delaware")

    def test_ambiguous_state_does_not_extract_or_write(self) -> None:
        text = "Workforce Pell applications open under the implementation framework."
        pipeline, _, sheets = make_pipeline(text, final_url="https://example.gov/update")
        result = pipeline.ingest_url("https://example.gov/update", dry_run=False)
        self.assertEqual(result.candidates, [])
        self.assertEqual(sheets.appended, [])
        self.assertTrue(any("ambiguous" in warning.lower() for warning in result.warnings))

    def test_no_material_event_source(self) -> None:
        pipeline, _, sheets = make_pipeline("Delaware published general education commentary.")
        result = pipeline.ingest_url("https://labor.delaware.gov/commentary", dry_run=False)
        self.assertFalse(result.material_event_found)
        self.assertEqual(sheets.read_count, 0)
        self.assertEqual(sheets.appended, [])

    def test_duplicate_source_reports_match_without_append(self) -> None:
        existing = [{
            "Event_ID": "EH-42", "State": "Delaware", "Event_Type": "Applications opened",
            "Event_Date": "2026-08-10", "Source_URL": "https://labor.delaware.gov/update",
            "Description": "Applications opened for eligible workforce programs.",
        }]
        sheets = FakeSheets(existing)
        pipeline, _, _ = make_pipeline(self.material_text, sheets=sheets)
        result = pipeline.ingest_url("https://labor.delaware.gov/update", dry_run=False)
        self.assertEqual(result.candidates, [])
        self.assertEqual(len(result.duplicates), 1)
        self.assertIn("EH-42", result.duplicates[0].duplicate_check)
        self.assertEqual(sheets.appended, [])

    def test_write_appends_pending_candidates_only(self) -> None:
        pipeline, _, sheets = make_pipeline(self.material_text)
        result = pipeline.ingest_url("https://labor.delaware.gov/update", dry_run=False)
        self.assertEqual(sheets.appended, result.candidates)
        self.assertTrue(all(candidate.review_status == "Pending" for candidate in sheets.appended))

    def test_manual_text_ingestion_reuses_validation_and_safe_write(self) -> None:
        pipeline, _, sheets = make_pipeline(self.material_text)
        result = pipeline.ingest_text(
            self.material_text,
            "https://example.org/article?utm_source=email",
            state_override="Delaware",
            dry_run=False,
            source_name="Saved article",
        )
        self.assertEqual(result.retrieval_method, "manual_text")
        self.assertEqual(result.canonical_final_url, "https://example.org/article")
        self.assertEqual(sheets.appended, result.candidates)
        self.assertTrue(all(candidate.review_status == "Pending" for candidate in sheets.appended))


if __name__ == "__main__":
    unittest.main()
