"""Typed domain models and Review_Queue row serialization."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any, Literal

from .taxonomy import format_stage

Confidence = Literal["High", "Medium", "Low"]
DateBasis = Literal[
    "Exact event date",
    "Effective date",
    "Source publication date only",
    "Detected date only",
    "Unknown",
]

REVIEW_QUEUE_COLUMNS: tuple[str, ...] = (
    "Candidate_ID", "State", "Detected_Date", "Proposed_Event_Date",
    "Source_Publication_Date", "Date_Basis", "Proposed_Event_Type",
    "Proposed_Stage", "Proposed_Change", "Source_Name", "Source_URL",
    "Source_Type", "Evidence_Excerpt", "AI_Confidence", "Duplicate_Check",
    "Review_Status", "Analyst_Comment", "Reviewer", "Reviewed_Date",
    "Publish_Action",
)


@dataclass(slots=True)
class CandidateUpdate:
    """A reviewable material event discovered by the pipeline."""

    candidate_id: str
    state: str
    detected_date: date
    proposed_event_date: date | None
    source_publication_date: date | None
    date_basis: DateBasis
    proposed_event_type: str
    proposed_change: str
    source_name: str
    source_url: str
    source_type: str
    evidence_excerpt: str
    ai_confidence: Confidence
    stage_change: bool
    current_known_stage_order: int | None
    proposed_stage_order: int | None
    proposed_stage_label: str | None
    duplicate_check: str = "Not checked"
    review_status: str = "Pending"
    analyst_comment: str = ""
    reviewer: str = ""
    reviewed_date: str = ""
    publish_action: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_review_queue_dict(self) -> dict[str, str | int]:
        """Serialize this candidate in the exact Review_Queue schema."""
        return {
            "Candidate_ID": self.candidate_id,
            "State": self.state,
            "Detected_Date": self.detected_date.isoformat(),
            "Proposed_Event_Date": self.proposed_event_date.isoformat() if self.proposed_event_date else "",
            "Source_Publication_Date": self.source_publication_date.isoformat() if self.source_publication_date else "",
            "Date_Basis": self.date_basis,
            "Proposed_Event_Type": self.proposed_event_type,
            "Proposed_Stage": format_stage(self.proposed_stage_order, self.proposed_stage_label),
            "Proposed_Change": self.proposed_change,
            "Source_Name": self.source_name,
            "Source_URL": self.source_url,
            "Source_Type": self.source_type,
            "Evidence_Excerpt": self.evidence_excerpt,
            "AI_Confidence": self.ai_confidence,
            "Duplicate_Check": self.duplicate_check,
            "Review_Status": self.review_status,
            "Analyst_Comment": self.analyst_comment,
            "Reviewer": self.reviewer,
            "Reviewed_Date": self.reviewed_date,
            "Publish_Action": self.publish_action,
        }


@dataclass(frozen=True, slots=True)
class SearchResult:
    """A source lead returned by a search provider."""

    title: str
    url: str
    source_domain: str
    snippet: str
    source_type: str


@dataclass(frozen=True, slots=True)
class SourceDocument:
    """Normalized content fetched from a source URL."""

    url: str
    title: str
    text: str
    source_name: str
    source_type: str
    publication_date: date | None = None
    original_url: str | None = None
