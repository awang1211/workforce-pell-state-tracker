# Data

The live operational backend is maintained in Google Sheets rather than committed directly to this repository.

Recommended practice:
- periodically export dated CSV snapshots
- keep only non-sensitive research data in Git
- preserve source URLs and evidence fields
- never commit credentials

Suggested snapshots:

```text
state_status_YYYY-MM-DD.csv
event_history_YYYY-MM-DD.csv
approved_programs_YYYY-MM-DD.csv
capacity_building_YYYY-MM-DD.csv
```
