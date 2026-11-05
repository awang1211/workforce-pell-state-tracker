"""Conservative pre-classification of potentially material sources."""

from __future__ import annotations

from dataclasses import dataclass

from .models import SourceDocument

MATERIAL_TERMS = (
    "application window", "applications open", "approved program", "program approval",
    "effective date", "rulemaking", "final rule", "implementation", "eligible program",
    "student access", "workforce pell", "short-term pell",
)
ACTION_TERMS = ("open", "approved", "issued", "effective", "deadline", "submitted", "launched", "published")


@dataclass(frozen=True, slots=True)
class MaterialityAssessment:
    """Deterministic gate before more expensive structured extraction."""

    potentially_material: bool
    reason: str


def assess_materiality(document: SourceDocument) -> MaterialityAssessment:
    """Conservatively identify documents that may contain implementation events."""
    text = document.text.lower()
    topic = any(term in text for term in MATERIAL_TERMS)
    action = any(term in text for term in ACTION_TERMS)
    if topic and action:
        return MaterialityAssessment(True, "Contains Workforce Pell implementation and action language")
    return MaterialityAssessment(False, "No concrete implementation action found")
