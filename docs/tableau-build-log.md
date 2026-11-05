# Tableau Build Log

## Dashboard components
- U.S. implementation-stage choropleth
- KPI cards
- All States Summary
- Implementation Timeline
- Timeline Updates / event feed
- State Stage Guide

## Core calculations

### Map Stage

```tableau
IF [Stage Order] = 0 THEN "Not yet reviewed"
ELSEIF [Stage Order] = 1 THEN "Planning / systems build"
ELSEIF [Stage Order] = 2 THEN "Framework issued / rulemaking"
ELSEIF [Stage Order] = 3 THEN "Applications open"
ELSEIF [Stage Order] = 4 THEN "Programs approved"
ELSEIF [Stage Order] = 5 THEN "Operational / student access"
END
```

### Reviewed Flag
```tableau
IF [Stage Order] > 0 THEN 1 ELSE 0 END
```

### Applications Open Plus Flag
```tableau
IF [Stage Order] >= 3 THEN 1 ELSE 0 END
```

### States with Approved Programs
```tableau
IF [Stage Order] >= 4 THEN 1 ELSE 0 END
```

## Tooltip design
Map tooltip should include state, stage number + label, framework, applications, lead agency, evidence strength, last verified, and approved-program summary.

## Timeline design
The timeline emphasizes **when** material events happened. Long headlines belong in tooltips rather than point labels.

## Extract troubleshooting
A recurring Tableau error occurred when `.hyper` extracts were stored in macOS temporary paths such as `/var/folders/.../T/tableau-temp/...hyper`.

Fix:
- regenerate the extract
- save permanent extracts under `~/Documents/My Tableau Repository/Datasources/`
- do not rely on temp paths
