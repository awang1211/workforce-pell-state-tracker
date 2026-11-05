"""Tests for the Google Sheets write-target safety boundary."""

from __future__ import annotations

import unittest
from typing import Any

from tests.helpers import make_candidate
from src.sheets import REVIEW_QUEUE_TAB, SafeSheetsGateway


class FakeBackend:
    def __init__(self) -> None:
        self.appended_range = ""

    def get_values(self, spreadsheet_id: str, range_name: str) -> list[list[Any]]:
        del spreadsheet_id, range_name
        return []

    def append_values(self, spreadsheet_id: str, range_name: str, values: list[list[Any]]) -> str:
        del spreadsheet_id, values
        self.appended_range = range_name
        return range_name


class SheetSafetyTests(unittest.TestCase):
    def test_candidate_append_targets_review_queue_only(self) -> None:
        backend = FakeBackend()
        SafeSheetsGateway("sheet-id", backend).append_review_candidates([make_candidate()])
        self.assertTrue(backend.appended_range.startswith(f"'{REVIEW_QUEUE_TAB}'!"))

    def test_internal_append_rejects_every_other_tab(self) -> None:
        gateway = SafeSheetsGateway("sheet-id", FakeBackend())
        for forbidden in ("State_Status", "Event_History", "Other"):
            with self.subTest(forbidden=forbidden), self.assertRaisesRegex(PermissionError, "Review_Queue"):
                gateway._append_to_tab(forbidden, [["unsafe"]])


if __name__ == "__main__":
    unittest.main()
