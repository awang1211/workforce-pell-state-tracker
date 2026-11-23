"""Boundary-value and rule tests for the Workforce Pell checker. Run: pytest checker"""
import pytest

from eligibility import CHECK, MET, NOT_MET, check_hours, check_length, check_program, summarize


@pytest.mark.parametrize("weeks, expected", [
    (7, NOT_MET),    # one week too short
    (8, MET),        # lowest valid
    (14, MET),       # highest valid
    (15, NOT_MET),   # 15 weeks is not allowed (must be fewer than 15)
])
def test_length_boundaries(weeks, expected):
    assert check_length(weeks)["status"] == expected


@pytest.mark.parametrize("amount, unit, expected", [
    (149, "Clock hours", NOT_MET), (150, "Clock hours", MET),
    (599, "Clock hours", MET), (600, "Clock hours", NOT_MET),
    (3, "Semester or trimester credit hours", NOT_MET), (4, "Semester or trimester credit hours", MET),
    (15, "Semester or trimester credit hours", MET), (16, "Semester or trimester credit hours", NOT_MET),
    (5, "Quarter credit hours", NOT_MET), (6, "Quarter credit hours", MET),
    (23, "Quarter credit hours", MET), (24, "Quarter credit hours", NOT_MET),
])
def test_size_boundaries(amount, unit, expected):
    assert check_hours(amount, unit)["status"] == expected


def base(**overrides):
    args = dict(weeks=10, amount=300, unit="Clock hours", offered_12_months="Yes",
                within_accreditation="Yes", recognized_credential="Yes", earns_credit="Yes",
                excluded_coursework=False, online_out_of_state="No",
                completion_rate=80, placement_rate=75, state_stage=3, state_name="Test State")
    args.update(overrides)
    return {r["rule"]: r for r in check_program(**args)}


def test_every_result_has_a_source():
    assert all(r["source"] for r in base().values())


@pytest.mark.parametrize("rate, expected", [(69.9, NOT_MET), (70, MET), (None, CHECK)])
def test_completion_threshold(rate, expected):
    assert base(completion_rate=rate)["Completion rate ≥ 70%"]["status"] == expected


def test_excluded_coursework_fails():
    assert base(excluded_coursework=True)["No excluded coursework"]["status"] == NOT_MET


def test_not_sure_becomes_needs_check():
    assert base(earns_credit="Not sure")["Stackable: earns academic credit"]["status"] == CHECK


def test_online_out_of_state_needs_check():
    assert base(online_out_of_state="Yes")["Online delivery to other states"]["status"] == CHECK


def test_federal_approval_always_needs_check():
    assert base()["U.S. Department of Education approval"]["status"] == CHECK


def test_summary_fails_if_any_rule_fails():
    results = list(base(weeks=20).values())
    assert summarize(results)[0] == NOT_MET
