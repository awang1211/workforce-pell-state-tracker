"""Deterministic duplicate detection for candidate material events."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import re
from typing import Mapping, Sequence
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from .models import CandidateUpdate


@dataclass(frozen=True, slots=True)
class DuplicateDecision:
    """Duplicate classification and its strongest matching row."""

    classification: str
    score: float
    reason: str
    matched_id: str | None = None
    matched_table: str | None = None


def check_duplicate(
    candidate: CandidateUpdate,
    event_history: Sequence[Mapping[str, str]],
    review_queue: Sequence[Mapping[str, str]],
) -> DuplicateDecision:
    """Compare a candidate with authoritative history and existing review rows."""
    best = DuplicateDecision("new", 0.0, "No likely duplicate found")
    for table, rows in (("Event_History", event_history), ("Review_Queue", review_queue)):
        for row in rows:
            decision = _compare(candidate, row, table)
            if decision.score > best.score:
                best = decision
            if decision.classification == "exact_duplicate":
                return decision
    return best


def _compare(candidate: CandidateUpdate, row: Mapping[str, str], table: str) -> DuplicateDecision:
    row_id = row.get("Candidate_ID") or row.get("Event_ID") or None
    if row.get("Candidate_ID") == candidate.candidate_id:
        return DuplicateDecision("exact_duplicate", 1.0, "Candidate_ID already exists", row_id, table)

    row_state = _field(row, "State")
    row_type = _field(row, "Proposed_Event_Type", "Event_Type")
    row_date = _field(row, "Proposed_Event_Date", "Event_Date")
    row_url = _field(row, "Source_URL")
    row_change = _field(row, "Proposed_Change", "Change", "Event_Description", "Description")
    state_same = _norm(row_state) == _norm(candidate.state)
    type_same = _event_type(row_type) == _event_type(candidate.proposed_event_type)
    date_same = bool(row_date and candidate.proposed_event_date and row_date == candidate.proposed_event_date.isoformat())
    url_same = bool(row_url and canonicalize_url(row_url) == canonicalize_url(candidate.source_url))
    text_score = _token_similarity(row_change, candidate.proposed_change)

    if state_same and type_same and date_same and url_same:
        return DuplicateDecision("exact_duplicate", 1.0, "Same state, event type, date, and canonical URL", row_id, table)
    score = (0.30 if state_same else 0) + (0.25 if type_same else 0) + (0.20 if date_same else 0) + (0.15 if url_same else 0) + (0.10 * text_score)
    if state_same and type_same and (date_same or url_same) and score >= 0.70:
        return DuplicateDecision("likely_duplicate", score, "Same state/type and matching date or source", row_id, table)
    if state_same and (type_same or date_same) and score >= 0.50:
        return DuplicateDecision("possible_duplicate", score, "Related event should be reviewed for duplication", row_id, table)
    return DuplicateDecision("new", score, "No likely duplicate found", row_id, table)


def canonicalize_url(url: str) -> str:
    """Normalize URL identity while retaining meaningful query parameters."""
    parts = urlsplit(url.strip())
    query = [(key, value) for key, value in parse_qsl(parts.query) if not key.lower().startswith("utm_") and key.lower() not in {"fbclid", "gclid"}]
    path = parts.path.rstrip("/") or "/"
    return urlunsplit((parts.scheme.lower() or "https", parts.netloc.lower(), path, urlencode(query), ""))


def _field(row: Mapping[str, str], *names: str) -> str:
    return next((str(row[name]).strip() for name in names if row.get(name)), "")


def _norm(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def _event_type(value: str) -> str:
    normalized = _norm(value)
    replacements = {"application opened": "applications open", "program approval": "program approved"}
    return replacements.get(normalized, normalized)


def _token_similarity(left: str, right: str) -> float:
    a, b = set(_norm(left).split()), set(_norm(right).split())
    return len(a & b) / len(a | b) if a and b else 0.0
