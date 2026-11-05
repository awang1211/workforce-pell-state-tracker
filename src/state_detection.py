"""Conservative state detection for manually supplied sources."""

from __future__ import annotations

from dataclasses import dataclass
import re
from urllib.parse import urlsplit

from .models import SourceDocument

US_STATES: tuple[str, ...] = (
    "Alabama", "Alaska", "Arizona", "Arkansas", "California", "Colorado", "Connecticut",
    "Delaware", "District of Columbia", "Florida", "Georgia", "Hawaii", "Idaho", "Illinois",
    "Indiana", "Iowa", "Kansas", "Kentucky", "Louisiana", "Maine", "Maryland", "Massachusetts",
    "Michigan", "Minnesota", "Mississippi", "Missouri", "Montana", "Nebraska", "Nevada",
    "New Hampshire", "New Jersey", "New Mexico", "New York", "North Carolina", "North Dakota",
    "Ohio", "Oklahoma", "Oregon", "Pennsylvania", "Rhode Island", "South Carolina",
    "South Dakota", "Tennessee", "Texas", "Utah", "Vermont", "Virginia", "Washington",
    "West Virginia", "Wisconsin", "Wyoming",
)


@dataclass(frozen=True, slots=True)
class StateDetection:
    """State inference result with a warning when evidence is ambiguous."""

    state: str | None
    warning: str | None = None


def detect_state(document: SourceDocument) -> StateDetection:
    """Infer a state only from explicit full-name content or an official state domain."""
    searchable = f"{document.title}\n{document.source_name}\n{document.text}"
    matches = [state for state in US_STATES if re.search(rf"\b{re.escape(state)}\b", searchable, re.IGNORECASE)]
    if len(matches) == 1:
        return StateDetection(matches[0])
    if len(matches) > 1:
        return StateDetection(None, "Multiple states are explicitly referenced: " + ", ".join(matches))

    domain = urlsplit(document.url).netloc.lower()
    domain_matches = [state for state, marker in _OFFICIAL_DOMAIN_MARKERS.items() if domain == marker or domain.endswith(f".{marker}")]
    if len(domain_matches) == 1:
        return StateDetection(domain_matches[0])
    return StateDetection(None, "State is ambiguous; supply --state with an explicit state name")


def validate_state_name(state: str) -> str:
    """Return the canonical state name or raise for an unsupported override."""
    canonical = next((item for item in US_STATES if item.casefold() == state.strip().casefold()), None)
    if canonical is None:
        raise ValueError(f"Unknown U.S. state: {state!r}")
    return canonical


_OFFICIAL_DOMAIN_MARKERS: dict[str, str] = {
    "California": "ca.gov", "Delaware": "delaware.gov", "Illinois": "illinois.gov",
    "Iowa": "iowa.gov", "North Carolina": "nc.gov", "Pennsylvania": "pa.gov",
}
