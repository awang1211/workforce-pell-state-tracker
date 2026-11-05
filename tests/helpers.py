"""Shared test helpers."""

from __future__ import annotations

from datetime import date
from typing import Any

from src.models import CandidateUpdate


def make_candidate(**overrides: Any) -> CandidateUpdate:
    """Build a valid candidate and allow individual fields to be overridden."""
    values: dict[str, Any] = {
        "candidate_id": "WP-PA-20260814-abc123",
        "state": "Pennsylvania",
        "detected_date": date(2026, 8, 14),
        "proposed_event_date": date(2026, 8, 10),
        "source_publication_date": date(2026, 8, 11),
        "date_basis": "Exact event date",
        "proposed_event_type": "Applications opened",
        "proposed_change": "Applications opened for eligible workforce programs.",
        "source_name": "Pennsylvania Department of Education",
        "source_url": "https://pa.gov/workforce-pell",
        "source_type": "Official state source",
        "evidence_excerpt": "Applications opened on August 10, 2026.",
        "ai_confidence": "High",
        "stage_change": True,
        "current_known_stage_order": 2,
        "proposed_stage_order": 3,
        "proposed_stage_label": "Applications open",
    }
    values.update(overrides)
    return CandidateUpdate(**values)
