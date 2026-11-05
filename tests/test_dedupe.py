"""Tests for exact, likely, and distinct-event duplicate behavior."""

from __future__ import annotations

import unittest

from tests.helpers import make_candidate
from src.dedupe import check_duplicate


class DedupeTests(unittest.TestCase):
    def test_exact_duplicate_ignores_tracking_parameters(self) -> None:
        candidate = make_candidate(source_url="https://pa.gov/workforce-pell?utm_source=email")
        rows = [{"Event_ID": "EH-1", "State": "Pennsylvania", "Event_Type": "Applications opened",
                 "Event_Date": "2026-08-10", "Source_URL": "https://pa.gov/workforce-pell",
                 "Description": candidate.proposed_change}]
        self.assertEqual(check_duplicate(candidate, rows, []).classification, "exact_duplicate")

    def test_application_submission_is_not_program_approval_duplicate(self) -> None:
        candidate = make_candidate(proposed_event_type="Program submitted for federal approval")
        rows = [{"Event_ID": "EH-2", "State": "Pennsylvania", "Event_Type": "Program approved",
                 "Event_Date": "2026-08-10", "Source_URL": "https://pa.gov/workforce-pell"}]
        self.assertNotIn(check_duplicate(candidate, rows, []).classification,
                         {"exact_duplicate", "likely_duplicate"})

    def test_existing_candidate_id_is_exact_duplicate(self) -> None:
        candidate = make_candidate()
        self.assertEqual(check_duplicate(candidate, [], [{"Candidate_ID": candidate.candidate_id}]).classification,
                         "exact_duplicate")


if __name__ == "__main__":
    unittest.main()
