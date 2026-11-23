"""Workforce Pell readiness rules.

Each rule returns one result: rule name, rule type, status, reason, and source.

Rule types
    Program  -> can be decided from the program's own information
    State    -> depends on the state's Workforce Pell process
    Outcomes -> depends on data or approvals that come later

Statuses
    Met          -> the information given satisfies the rule
    Not met      -> the information given fails the rule
    Needs check  -> cannot be decided from the information given

Source: U.S. Department of Education, Federal Student Aid,
"Workforce Pell Frequently Asked Questions" (October 2026), and the
regulations it cites (34 CFR 690.91–690.95).
"""

FAQ_URL = "https://fsapartners.ed.gov/sites/default/files/2026-10/WorkforcePellFAQs.pdf"

MET, NOT_MET, CHECK = "Met", "Not met", "Needs check"

# Allowed program size by unit type (34 CFR 690.92)
HOUR_RANGES = {
    "Clock hours": (150, 599),
    "Semester or trimester credit hours": (4, 15),
    "Quarter credit hours": (6, 23),
}


def _result(rule, rule_type, status, reason, source):
    return {"rule": rule, "type": rule_type, "status": status, "reason": reason, "source": source}


def _yes_no_unsure(answer, rule, rule_type, met_reason, not_met_reason, source):
    """Turn a Yes / No / Not sure answer into a result."""
    if answer == "Yes":
        return _result(rule, rule_type, MET, met_reason, source)
    if answer == "No":
        return _result(rule, rule_type, NOT_MET, not_met_reason, source)
    return _result(rule, rule_type, CHECK, "Not confirmed yet. " + met_reason, source)


def check_length(weeks):
    """At least 8 but fewer than 15 weeks of instruction."""
    source = "FSA Workforce Pell FAQs, intro and FAQ 14"
    if 8 <= weeks < 15:
        return _result("Program length", "Program", MET,
                       f"{weeks} weeks is within 8 to fewer than 15 weeks.", source)
    return _result("Program length", "Program", NOT_MET,
                   f"{weeks} weeks is outside 8 to fewer than 15 weeks.", source)


def check_hours(amount, unit):
    """150–599 clock hours, 4–15 semester/trimester hours, or 6–23 quarter hours."""
    source = "34 CFR 690.92(a)–(c); FSA Workforce Pell FAQs, FAQ 3"
    low, high = HOUR_RANGES[unit]
    if low <= amount <= high:
        return _result("Program size", "Program", MET,
                       f"{amount} {unit.lower()} is within {low}–{high}.", source)
    return _result("Program size", "Program", NOT_MET,
                   f"{amount} {unit.lower()} is outside {low}–{high}.", source)


def check_program(weeks, amount, unit, offered_12_months, within_accreditation,
                  recognized_credential, earns_credit, excluded_coursework,
                  online_out_of_state, completion_rate, placement_rate,
                  state_stage, state_name, state_note=""):
    """Run every rule and return a list of results.

    Yes/No/Not sure answers are passed as the strings "Yes", "No", "Not sure".
    completion_rate and placement_rate are percentages (0–100) or None if unknown.
    state_stage is the tracker's 0–5 stage for the selected state.
    """
    results = [
        check_length(weeks),
        check_hours(amount, unit),
        _yes_no_unsure(
            offered_12_months, "Offered for at least 12 months", "Program",
            "The program has met the length requirements, continuously offered, for the 12 months before applying.",
            "The program must have met the length requirements for the 12 months before the institution applies.",
            "FSA Workforce Pell FAQs, FAQ 3 and FAQ 16"),
        _yes_no_unsure(
            within_accreditation, "Within the institution's accreditation", "Program",
            "The program falls within the institution's grant of accreditation.",
            "The program must fall within the institution's grant of accreditation.",
            "FSA Workforce Pell FAQs, FAQ 3 and FAQ 10"),
        _yes_no_unsure(
            recognized_credential, "Leads to a recognized postsecondary credential", "Program",
            "Completers earn a recognized postsecondary credential, and the institution issues its own credential.",
            "The program must lead to a recognized postsecondary credential (e.g., industry certificate, license, apprenticeship certificate).",
            "34 CFR 690.91; FSA Workforce Pell FAQs, FAQ 15"),
        _yes_no_unsure(
            earns_credit, "Stackable: earns academic credit", "Program",
            "Completion earns academic credit toward a certificate or degree.",
            "Completion must earn academic credit toward a certificate or degree; a license endorsement alone does not count.",
            "34 CFR 690.93(a)(4); FSA Workforce Pell FAQs, FAQ 12 and FAQ 22"),
    ]

    # Excluded coursework: correspondence, remedial/ESL, study abroad, direct assessment
    source = "34 CFR 668.20(g); FSA Workforce Pell FAQs, intro and FAQ 11"
    if excluded_coursework:
        results.append(_result("No excluded coursework", "Program", NOT_MET,
                               "Correspondence, remedial (including ESL), study abroad, and direct assessment coursework are not eligible.",
                               source))
    else:
        results.append(_result("No excluded coursework", "Program", MET,
                               "No correspondence, remedial/ESL, study abroad, or direct assessment coursework reported.",
                               source))

    # State process: governor certification depends on the state's progress
    source = "34 CFR 690.93; FSA Workforce Pell FAQs, FAQ 17–19; stage from this repository's tracker"
    if state_stage >= 3:
        results.append(_result("Governor certification", "State", CHECK,
                               f"{state_name} has an application process open (tracker stage {state_stage}). "
                               "The program still needs governor certification.", source))
    elif state_stage in (1, 2):
        results.append(_result("Governor certification", "State", CHECK,
                               f"{state_name} is preparing its process (tracker stage {state_stage}); applications are not open yet.",
                               source))
    else:
        note = f" {state_note}" if state_note else ""
        results.append(_result("Governor certification", "State", CHECK,
                               f"No public application process found for {state_name} (tracker stage 0).{note}", source))

    # Online delivery to other states needs a bilateral agreement between governors
    source = "34 CFR 668.93(h); FSA Workforce Pell FAQs, FAQ 20"
    if online_out_of_state == "Yes":
        results.append(_result("Online delivery to other states", "State", CHECK,
                               "Reciprocity agreements do not cover these programs; a bilateral agreement between both governors is required.",
                               source))
    else:
        results.append(_result("Online delivery to other states", "State", MET,
                               "No online delivery to students in other states reported.", source))

    # Outcome thresholds
    for rule, rate, met_text, source in [
        ("Completion rate ≥ 70%", completion_rate,
         "of students complete within 150% of normal time",
         "34 CFR 690.94(a)(2); FSA Workforce Pell FAQs, FAQ 23"),
        ("Job placement rate ≥ 70%", placement_rate,
         "of completers employed in the second quarter after exit",
         "34 CFR 690.94; FSA Workforce Pell FAQs, FAQ 24"),
    ]:
        if rate is None:
            results.append(_result(rule, "Outcomes", CHECK, "Rate not provided; it must be at least 70%.", source))
        elif rate >= 70:
            results.append(_result(rule, "Outcomes", MET, f"{rate:g}% {met_text}.", source))
        else:
            results.append(_result(rule, "Outcomes", NOT_MET, f"{rate:g}% {met_text}; at least 70% is required.", source))

    results.append(_result("Value-added earnings test", "Outcomes", CHECK,
                           "Starting in 2030–31, tuition and fees may not exceed completers' value-added earnings.",
                           "34 CFR 690.95; FSA Workforce Pell FAQs, FAQ 27–30"))
    results.append(_result("U.S. Department of Education approval", "Outcomes", CHECK,
                           "After governor certification, ED reviews the institution's application.",
                           "FSA Workforce Pell FAQs, FAQ 3"))
    return results


def summarize(results):
    """One-line overall verdict."""
    statuses = [r["status"] for r in results]
    if NOT_MET in statuses:
        return NOT_MET, "As described, this program does not meet at least one requirement."
    return CHECK, "No requirement is failed by the information given. Items marked 'Needs check' must be confirmed."
