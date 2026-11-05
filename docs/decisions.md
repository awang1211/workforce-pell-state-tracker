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
