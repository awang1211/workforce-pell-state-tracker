"""Read authoritative tabs and append only to Review_Queue."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, Sequence

from .models import CandidateUpdate, REVIEW_QUEUE_COLUMNS
from .validation import validate_candidate

STATE_STATUS_TAB = "State_Status"
EVENT_HISTORY_TAB = "Event_History"
REVIEW_QUEUE_TAB = "Review_Queue"
READABLE_TABS = frozenset({STATE_STATUS_TAB, EVENT_HISTORY_TAB, REVIEW_QUEUE_TAB})


class SheetBackend(Protocol):
    """Minimal backend used by the safe spreadsheet gateway."""

    def get_values(self, spreadsheet_id: str, range_name: str) -> list[list[Any]]: ...
    def append_values(self, spreadsheet_id: str, range_name: str, values: list[list[Any]]) -> str: ...


@dataclass(slots=True)
class GoogleApiBackend:
    """Lazy Google Sheets API backend using service-account credentials."""

    credentials_path: str
    _service: Any = None

    def _get_service(self) -> Any:
        if self._service is None:
            from google.oauth2.service_account import Credentials
            from googleapiclient.discovery import build
            scopes = ["https://www.googleapis.com/auth/spreadsheets"]
            credentials = Credentials.from_service_account_file(self.credentials_path, scopes=scopes)
            self._service = build("sheets", "v4", credentials=credentials, cache_discovery=False)
        return self._service

    def get_values(self, spreadsheet_id: str, range_name: str) -> list[list[Any]]:
        response = self._get_service().spreadsheets().values().get(
            spreadsheetId=spreadsheet_id, range=range_name
        ).execute()
        return response.get("values", [])

    def append_values(self, spreadsheet_id: str, range_name: str, values: list[list[Any]]) -> str:
        response = self._get_service().spreadsheets().values().append(
            spreadsheetId=spreadsheet_id,
            range=range_name,
            valueInputOption="RAW",
            insertDataOption="INSERT_ROWS",
            body={"values": values},
        ).execute()
        return response.get("updates", {}).get("updatedRange", "")


class SafeSheetsGateway:
    """Spreadsheet boundary with read-only authoritative tabs and one write target."""

    def __init__(self, spreadsheet_id: str, backend: SheetBackend) -> None:
        self._spreadsheet_id = spreadsheet_id
        self._backend = backend

    def read_tab(self, tab_name: str) -> list[dict[str, str]]:
        """Read one allowlisted tab into header-keyed dictionaries."""
        if tab_name not in READABLE_TABS:
            raise ValueError(f"Reading tab {tab_name!r} is not allowed")
        values = self._backend.get_values(self._spreadsheet_id, f"'{tab_name}'!A:ZZ")
        if not values:
            return []
        headers = [str(value) for value in values[0]]
        return [dict(zip(headers, [str(value) for value in row], strict=False)) for row in values[1:]]

    def append_review_candidates(self, candidates: Sequence[CandidateUpdate]) -> str:
        """Validate and append candidates to Review_Queue only."""
        rows: list[list[str | int]] = []
        for candidate in candidates:
            validate_candidate(candidate)
            row = candidate.to_review_queue_dict()
            rows.append([row[column] for column in REVIEW_QUEUE_COLUMNS])
        if not rows:
            return ""
        return self._append_to_tab(REVIEW_QUEUE_TAB, rows)

    def _append_to_tab(self, tab_name: str, rows: list[list[Any]]) -> str:
        if tab_name != REVIEW_QUEUE_TAB:
            raise PermissionError("Writes are permitted only to Review_Queue")
        return self._backend.append_values(
            self._spreadsheet_id, f"'{REVIEW_QUEUE_TAB}'!A:{_column_letter(len(REVIEW_QUEUE_COLUMNS))}", rows
        )


def _column_letter(number: int) -> str:
    result = ""
    while number:
        number, remainder = divmod(number - 1, 26)
        result = chr(65 + remainder) + result
    return result
