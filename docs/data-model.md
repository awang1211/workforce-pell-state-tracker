# Data Model

The tracker separates tables by **grain** so current status, historical events, program records, and review candidates do not overwrite one another.

## State_Status

**Grain:** one row per state.

Authoritative current snapshot used by the Tableau map and state-level KPIs.

Key concepts:
- `Overall_Stage`
- `Stage_Order`
- framework/application status
- state-approved program count
- federally approved program count
- lead agency
- data readiness
- source and evidence strength
- approved-program summary
- student-funds usability
- occupation-list method
- UI wage-data access

## Event_History

**Grain:** one row per material implementation event.

Typical events:
- framework issued
- application portal opened
- deadline/review milestone
- state program approval
- federal program approval
- capacity-building grant
- implementation evidence

An event can be material without changing the state's stage.

## Approved_Programs

**Grain:** one row per program.

Tracks:
- state
- institution
- program
- industry / occupation
- program length
- state/federal approval dates
- approval level
- federal approval source
- verification flag
- student-funds usability
- actual enrollment start
- provenance

## Review_Queue

**Grain:** one row per candidate update awaiting analyst review.

Purpose: human-in-the-loop control layer for AI/manual ingestion.

## Capacity_Building

**Grain:** one row per grant, technical-assistance initiative, or capacity-building intervention.

Capacity funding must never be interpreted as program approval.

## National_Summary

**Grain:** one row per national snapshot date.

Purpose: maintain reproducible national headline counts and their methodology.

## Federal_Guidance

**Grain:** one row per federal implementation rule/guidance topic.

Purpose: preserve federal operational guidance separately from state implementation status.
