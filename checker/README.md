# Workforce Pell Readiness Checker

**Live app:** https://workforce-pell-checker.streamlit.app/

A self-check tool for institutions: enter a short-term program's details and see which federal Workforce Pell
requirements it appears to meet, which it fails, and which still need confirmation, along with where the
state's approval process stands.

**Not official guidance.** Only the governor's certification and U.S. Department of Education approval
determine eligibility.

## What it checks

| Type | Rule | Source |
|---|---|---|
| Program | 8 to fewer than 15 weeks of instruction | FSA Workforce Pell FAQs, FAQ 14 |
| Program | 150–599 clock hours (or 4–15 semester / 6–23 quarter hours) | 34 CFR 690.92 |
| Program | Met length rules for the 12 months before applying | FAQ 3, 16 |
| Program | Within the institution's accreditation | FAQ 3, 10 |
| Program | Leads to a recognized postsecondary credential | 34 CFR 690.91; FAQ 15 |
| Program | Completion earns academic credit (stackable) | 34 CFR 690.93(a)(4); FAQ 22 |
| Program | No correspondence, remedial/ESL, study abroad, or direct assessment coursework | FAQ 11 |
| State | Governor certification (shows the state's tracker stage) | 34 CFR 690.93; FAQ 17–19 |
| State | Online delivery to other states needs a bilateral agreement | 34 CFR 668.93(h); FAQ 20 |
| Outcomes | Completion rate ≥ 70% within 150% of normal time | 34 CFR 690.94; FAQ 23 |
| Outcomes | Job placement rate ≥ 70% (second quarter after exit) | FAQ 24 |
| Outcomes | Value-added earnings test (from 2030–31) | 34 CFR 690.95; FAQ 27–30 |
| Outcomes | U.S. Department of Education approval | FAQ 3 |

Rules source: [U.S. Department of Education, Federal Student Aid — Workforce Pell FAQs (Oct 2026)](https://fsapartners.ed.gov/sites/default/files/2026-10/WorkforcePellFAQs.pdf).
State stages come from this repository's tracker (data frozen 2026-11-17).

## Run locally

```bash
pip install -r checker/requirements.txt
streamlit run checker/app.py
```

## Tests

```bash
pip install pytest
pytest checker
```

See [`TEST_LOG.md`](TEST_LOG.md) for test cases, defects found, and manual test results.