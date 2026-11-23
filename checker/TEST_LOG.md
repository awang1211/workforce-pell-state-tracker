# Test log — Workforce Pell Readiness Checker

## Automated tests (`pytest checker`)

25 tests, all passing (2026-11-23).

| Area | What is tested | Cases |
|---|---|---|
| Program length | Boundary values around 8 and 15 weeks | 7 ❌, 8 ✅, 14 ✅, 15 ❌ |
| Program size | Boundary values for all three unit types | 149/150/599/600 clock hours; 3/4/15/16 semester hours; 5/6/23/24 quarter hours |
| Completion rate | Boundary at 70% and missing value | 69.9% ❌, 70% ✅, blank ⚠️ |
| Excluded coursework | Correspondence / remedial / study abroad / direct assessment | Checked → ❌ |
| Yes / No / Not sure answers | "Not sure" never counts as met | Not sure → ⚠️ |
| Online delivery to other states | Requires bilateral agreement | Yes → ⚠️ |
| Federal approval | Always requires ED review | ⚠️ |
| Overall verdict | Any failed rule → overall "Not met" | 20 weeks → ❌ |
| Sources | Every result cites a source | All rules |

## Defects found

| # | Found | Steps to reproduce | Expected | Actual | Cause | Fix | Retest |
|---|---|---|---|---|---|---|---|
| 1 | 2026-11-23, UI test (Streamlit AppTest) | Change unit to "Quarter credit hours", enter 20, click "Check my program" | "20 quarter credit hours is within 6–23" | Result showed 300 (the default) | The size input's label included the selected unit, so changing the unit created a new input and reset its value | Use a fixed label for the size input | ✅ Pass |

## Manual tests (browser)

| # | Steps | Expected | Result |
|---|---|---|---|
| M1 | Select Oklahoma, keep defaults, submit | Governor certification ⚠️: "No public application process found… (stage 0)" | |
| M2 | Select California, 10 weeks, 300 clock hours, all "Yes", rates 80/75 | No ❌; only ⚠️ for governor, value-added test, ED approval | |
| M3 | Set 15 weeks | Program length ❌; overall red message | |
| M4 | Unit = Quarter credit hours, size 24 | Program size ❌ "outside 6–23" | |
| M5 | Check "excluded coursework" | ❌ No excluded coursework | |
| M6 | Online to other states = Yes | ⚠️ bilateral agreement message | |
| M7 | Leave "I have completion and job placement rates" unchecked | Both rate rules ⚠️ "Rate not provided" | |
| M8 | Select each of 5 states at different stages (e.g., OK, VT, AK, CA, NC) | "Where [state] stands" shows the matching tracker stage and source | |
