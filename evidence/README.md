# Evidence from the Azure run

Screenshots and exported results from the real run in a temporary Udacity cloud lab on 14 and 15 November 2026. The resources have since been deleted. Subscription ids, endpoints and similar identifiers were blacked out before saving. Nothing here is a mock-up.

| Files | What they show |
|---|---|
| `00_postgres_*` | the PostgreSQL server, the data load (row counts), source validation output and server monitoring |
| `01_*` | the resource group and workspace, the Synapse copy pipeline and its four activities, and the four extracted files with a preview of each |
| `02_*` | the external data source and file formats, the four staging tables and their row counts |
| `03_*` | the five CETAS results (three dimensions, two facts) and the Parquet folders written to the data lake |
| `04_validation_summary.png` | the 26-check scorecard, all PASS |
| `05_*` | business query results: weekday and time band, longest rides by start station, age, member vs casual, payments by year, spend by age at account start, spend vs rides and minutes ridden |
| `08_cleanup_empty_resource_group.png` | the resource group empty after the resources were deleted |
| `00_postgres_validation.txt` | text output of the source validation queries |

How the dashboard figures relate to this evidence is described in [../docs/validation.md](../docs/validation.md).
