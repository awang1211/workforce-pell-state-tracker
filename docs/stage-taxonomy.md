# Implementation Stage Taxonomy

The tracker uses a custom 0–5 implementation maturity scale. This is an analytical framework developed for the tracker, **not an official U.S. Department of Education classification**.

## Stage 0 — Not yet reviewed
The state has not yet been systematically verified.

**Do not interpret this as:** no public activity, no planning, or no implementation.

## Stage 1 — Planning / systems build
The state has begun implementation preparation but has not yet opened a formal application/certification pathway.

Typical evidence:
- lead agency designated
- interagency working group formed
- data systems under development
- draft implementation process under discussion
- institutional readiness work underway

## Stage 2 — Framework issued / rulemaking
The state has published a formal implementation framework, policy, eligibility methodology, guidance, or certification rules, but applications are not yet open.

## Stage 3 — Applications open
Institutions or programs can submit for state approval/certification.

**Applications open does not imply that any program has been approved.**

## Stage 4 — Programs approved
At least one concrete program has received formal approval.

This stage may contain two different approval levels:
- **State-approved only**
- **Final federal approval**

Approval level is tracked separately using program-level fields such as `Approval_Level`, `Federal_Approval_Source`, and `Verification_Flag`.

## Stage 5 — Operational / student access
The program is not only approved but operational for students to receive Workforce Pell.

Possible evidence:
- enrollment period open for an approved Workforce Pell program
- institution confirms Pell can be awarded/disbursed
- actual Workforce Pell students enrolled
- disbursement begins

## Why Stage 4 is not split into 4A/4B
The tracker deliberately keeps a simple 0–5 visual taxonomy for Tableau readability. Approval nuance belongs in program-level fields and tooltips.
