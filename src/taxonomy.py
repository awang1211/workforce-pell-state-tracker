"""Workforce Pell implementation-stage taxonomy."""

from __future__ import annotations

STAGE_LABELS: dict[int, str] = {
    0: "Not yet reviewed",
    1: "Planning / systems build",
    2: "Framework issued / rulemaking",
    3: "Applications open",
    4: "Programs approved",
    5: "Operational / student access",
}


def format_stage(order: int | None, label: str | None) -> str:
    """Return the human-readable sheet value for a stage, or blank."""
    if order is None and label is None:
        return ""
    if order is None or label is None or STAGE_LABELS.get(order) != label:
        raise ValueError("Stage order and label must be a matching taxonomy pair")
    return f"{order} - {label}"
