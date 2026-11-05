"""Deterministic candidate validation independent of AI output."""

from __future__ import annotations

from .models import CandidateUpdate
from .state_detection import US_STATES
from .taxonomy import STAGE_LABELS

ALLOWED_STATES = frozenset(US_STATES)
ALLOWED_DATE_BASES = frozenset({
    "Exact event date", "Effective date", "Source publication date only",
    "Detected date only", "Unknown",
})


class CandidateValidationError(ValueError):
    """Raised when a candidate violates a deterministic business rule."""


def validate_candidate(candidate: CandidateUpdate) -> None:
    """Validate stage, date, provenance, and review-status invariants."""
    errors: list[str] = []
    if candidate.state not in ALLOWED_STATES:
        errors.append("state is not a recognized U.S. state")
    if candidate.review_status != "Pending":
        errors.append('Review_Status must be "Pending"')
    if candidate.date_basis not in ALLOWED_DATE_BASES:
        errors.append("Date_Basis is not allowed")
    if candidate.date_basis in {"Exact event date", "Effective date"} and candidate.proposed_event_date is None:
        errors.append("an event/effective date basis requires Proposed_Event_Date")
    if candidate.date_basis in {"Source publication date only", "Detected date only", "Unknown"} and candidate.proposed_event_date is not None:
        errors.append("publication/detected/unknown date cannot populate Proposed_Event_Date")
    if candidate.date_basis == "Source publication date only" and candidate.source_publication_date is None:
        errors.append("source publication date basis requires Source_Publication_Date")
    order, label = candidate.proposed_stage_order, candidate.proposed_stage_label
    if (order is None) != (label is None):
        errors.append("stage order and label must both be set or both be null")
    elif order is not None and STAGE_LABELS.get(order) != label:
        errors.append("stage order and label do not match the taxonomy")
    if candidate.stage_change and order is None:
        errors.append("a stage change requires a proposed stage")
    if not candidate.stage_change and candidate.current_known_stage_order != order and order is not None:
        errors.append("a non-stage-change event cannot propose a different known stage")
    if order == 0 and candidate.metadata.get("stage_uncertain"):
        errors.append("Stage 0 cannot represent uncertainty")
    for name, value in {
        "Candidate_ID": candidate.candidate_id, "Proposed_Event_Type": candidate.proposed_event_type,
        "Proposed_Change": candidate.proposed_change, "Source_Name": candidate.source_name,
        "Source_URL": candidate.source_url, "Source_Type": candidate.source_type,
        "Evidence_Excerpt": candidate.evidence_excerpt,
    }.items():
        if not value.strip():
            errors.append(f"{name} is required")
    if errors:
        raise CandidateValidationError("; ".join(errors))
