# Workforce Pell State Tracker

A state policy intelligence system for tracking Workforce Pell implementation across the United States.

This project combines policy research, a structured Google Sheets backend, Tableau visualization, and an AI-assisted human-in-the-loop monitoring workflow. The goal is not only to show **where each state stands**, but also **what changed, what evidence supports the status, which programs are approved, and how implementation capacity differs across states**.

## What the tracker answers

- How far has each state progressed in implementing Workforce Pell?
- Which states have opened applications, approved programs, or reached student access?
- Which approvals are state-level versus final federal approvals?
- Which institutions and occupations are represented in approved programs?
- What material implementation events changed a state's status over time?
- Where are data infrastructure, governance, and institutional readiness creating bottlenecks?

## Current architecture

**Visualization:** Tableau Public / Tableau Desktop  
**Operational backend:** Google Sheets  
**Monitoring:** Python + OpenAI-assisted source discovery/extraction  
**Quality control:** Human review before authoritative state-status changes

## Core tables

- `State_Status` — one row per state; authoritative current snapshot
- `Event_History` — one row per material implementation event
- `Approved_Programs` — one row per approved program
- `Review_Queue` — one row per AI/manual candidate awaiting review
- `Capacity_Building` — one row per capacity-building grant or technical-assistance intervention
- `National_Summary` — national headline counts with methodology notes
- `Federal_Guidance` — structured federal implementation guidance

See [`docs/data-model.md`](docs/data-model.md) for details.

## Implementation stages

| Stage | Label | Meaning |
|---|---|---|
| 0 | Not yet reviewed | State has not yet been systematically verified; does **not** mean no activity |
| 1 | Planning / systems build | Governance, data, and implementation systems are being prepared |
| 2 | Framework issued / rulemaking | Formal policy, guidance, or certification framework is public |
| 3 | Applications open | Institutions/programs can submit for state review |
| 4 | Programs approved | At least one program has formal approval; approval level is tracked separately |
| 5 | Operational / student access | Students can actually access Workforce Pell through approved programs |

Important: Stage 4 intentionally includes both state-approved and federally approved programs. Approval level is tracked separately in `Approved_Programs` and related fields.

## Data-quality principles

1. **Unreviewed is not inactive.** Stage 0 is a research-status flag, not a policy-status claim.
2. **State approval ≠ federal approval.** These are recorded separately.
3. **Material event ≠ stage change.** An event can matter without changing the state's stage.
4. **Event date ≠ publication date ≠ detection date.** Date basis is explicitly recorded.
5. **AI never directly overwrites authoritative state status.** Candidate updates go through human review.
6. **Provenance is part of the data model.** State, event, source URL, evidence excerpt, and analyst decision should remain traceable.

## Repository structure

```text
workforce-pell-state-tracker/
├── README.md
├── docs/
│   ├── methodology.md
│   ├── stage-taxonomy.md
│   ├── data-model.md
│   ├── workflow.md
│   ├── decisions.md
│   ├── tableau-build-log.md
│   └── security.md
├── tableau/
│   └── README.md
├── data/
│   └── README.md
├── src/
│   └── README.md
├── screenshots/
│   └── README.md
└── .gitignore
```

## Portfolio framing

> Built a state policy intelligence system for Workforce Pell that combines a structured state-level data model, implementation taxonomy, Tableau visualization, provenance-aware event history, and an AI-assisted human-in-the-loop monitoring pipeline.

## Status

Active project. The live Google Sheets backend and Tableau dashboard continue to be updated as states move through implementation.
