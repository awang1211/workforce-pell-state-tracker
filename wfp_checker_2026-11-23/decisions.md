# Decision Log

## Stage 0 means “not yet reviewed,” not “no activity”
Absence of research is not evidence of absence of implementation.

## State approval and federal approval are separate
A governor/state agency may certify a program before final U.S. Department of Education approval.

## Keep Stage 4 broad; show approval level separately
A simple 0–5 map is easier to interpret than 4A/4B. Approval nuance belongs in fields and tooltips.

## Material event and stage change are separate
Application deadlines, capacity grants, and federal approval confirmations can matter without changing `Stage_Order`.

## Current status and history use separate tables
`State_Status` has state grain; `Event_History` has event grain.

## Approved programs use their own table
One state can have many programs across industries and institutions.

## Capacity-building support is not approval
Federal grants and technical assistance may strengthen implementation capacity without making a program eligible.

## Human review remains authoritative
AI accelerates discovery; it does not silently make final policy judgments.

## Conditional or board-level approvals count as Stage 3 (2026-11-17)
Stage 4 requires a formal approval. A state board's conditional approval or recommendation without final
governor or ED action (e.g., Michigan's June 22 conditional approvals; Georgia's October 19 board vote)
is coded Stage 3 and described in the analyst note. The same rule applies to every state.

## Stage 5 requires evidence of student access (2026-11-04)
A state reaches Stage 5 only when an institution states that students can enroll using Workforce Pell,
or an official source confirms Pell has been disbursed. Federal approval alone stays Stage 4
(Iowa, Indiana, and Nebraska remain Stage 4 until disbursement timing is verified).

## Reviewed with no public activity stays Stage 0, with a note (2026-11-04)
States checked with no public Workforce Pell activity found (Oklahoma, Vermont, Wyoming) remain
Stage 0 to keep the dashboard scale unchanged. `Review_Note` records that they were reviewed,
so they are not confused with unreviewed states.

## Analysis uses frozen, dated snapshots (2026-11-17)
The state-level analysis in `analysis/` reads a dated export (`state_status_2026-11-17.csv`) rather
than the live sheet, so results can be reproduced. Updates to the live tracker do not change published findings.

## The readiness checker never gives a final determination (2026-11-23)
The checker in `checker/` marks each rule Met, Not met, or Needs check. "Not sure" answers and rules that
depend on governor or ED action are always Needs check. Rules cite the October 2026 FSA Workforce Pell FAQs.
