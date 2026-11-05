"""Tests for deterministic stage and date rules."""

from __future__ import annotations

import unittest

from tests.helpers import make_candidate
from src.validation import CandidateValidationError, validate_candidate


class ValidationTests(unittest.TestCase):
    def test_unknown_stage_is_blank_not_stage_zero(self) -> None:
        candidate = make_candidate(stage_change=False, current_known_stage_order=None,
                                   proposed_stage_order=None, proposed_stage_label=None,
                                   metadata={"stage_uncertain": True})
        validate_candidate(candidate)
        self.assertEqual(candidate.to_review_queue_dict()["Proposed_Stage"], "")

    def test_stage_zero_cannot_encode_uncertainty(self) -> None:
        candidate = make_candidate(stage_change=False, current_known_stage_order=0,
                                   proposed_stage_order=0, proposed_stage_label="Not yet reviewed",
                                   metadata={"stage_uncertain": True})
        with self.assertRaisesRegex(CandidateValidationError, "Stage 0"):
            validate_candidate(candidate)

    def test_non_stage_change_can_retain_current_stage(self) -> None:
        candidate = make_candidate(proposed_event_type="Application deadline extended", stage_change=False,
                                   current_known_stage_order=3, proposed_stage_order=3,
                                   proposed_stage_label="Applications open")
        validate_candidate(candidate)

    def test_publication_date_never_populates_event_date(self) -> None:
        with self.assertRaisesRegex(CandidateValidationError, "cannot populate Proposed_Event_Date"):
            validate_candidate(make_candidate(date_basis="Source publication date only"))

    def test_publication_only_date_with_blank_event_date_is_valid(self) -> None:
        validate_candidate(make_candidate(proposed_event_date=None, date_basis="Source publication date only"))


if __name__ == "__main__":
    unittest.main()
