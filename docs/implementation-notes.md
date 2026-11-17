# Implementation notes

How the warehouse was built, what the data looked like, and why the transformations are written the way they are.
For the picture of the whole pipeline see [architecture.svg](images/architecture.svg); for the checks see [validation.md](validation.md).

## Origin of the project

The warehouse was built as the capstone of the Udacity "Data Engineering with Azure" program. Udacity supplied the business questions, the four source files and a data-loading script; the design, SQL, validation, dashboard and documentation in this repository are my own work. The ride data comes from the City of Chicago's public Divvy trip data. The rider, account and payment records are synthetic and were created by the course. Everything ran in a temporary Udacity cloud lab on 14 and 15 November 2026, and those Azure resources have since been deleted.

## What the source data looked like

The project brief drew five entities (Rider, Account, Payment, Trip, Station). The loader script actually creates **four** tables (`rider`, `payment`, `station`, `trip`; see [create_tables.sql](../sql/postgres/create_tables.sql)), and the rider table carries the account fields. The design follows the real tables, not the picture.

Profiled locally on the CSV files before anything was built:

| Fact | Value |
|---|---|
| Rows | 75,000 riders, 1,946,607 payments, 838 stations, 4,584,921 trips |
| Files | no header row, no quotes, no commas inside values |
| Trip dates | 1 Feb 2021 to 31 Jan 2022; payments run 2013-02-01 to 2022-02-01, always on the 1st of a month |
| Keys | no duplicate ids; every trip and payment matches a rider; every trip station exists |
| Station ids | text, some alphanumeric (`KA1503000012`), so they are never cast to numbers |
| Bad durations | 116 trips end before they start, 81 have zero length, 1,277 exceed 24 hours (longest 932 h) |
| Accounts | 1,033 riders have an account end date before the start date |
| Membership | `is_member` is a current flag; there is no history |
| Payments | no trip id on a payment, so a payment cannot be tied to a ride |

## What the Azure run produced

| Step | Result |
|---|---|
| PostgreSQL | four tables loaded with the expected row counts; source checks in [validate_source.sql](../sql/postgres/validate_source.sql) matched |
| Extract | one Synapse copy pipeline, four copy activities, four text files at the container root |
| Load | four external staging tables over those files |
| Transform | five CETAS statements, Parquet output in `warehouse/<table>/run01/` |
| Validation | 26 of 26 checks passed ([validation.md](validation.md)) |

What the copy activity wrote, which shaped the staging scripts: no header row, text values in double quotes, timestamps such as `2021-02-12 16:14:56.0000000`, and money as plain `9.00`. The staging tables therefore keep dates and money as text and the transformations parse them.

Two environment details worth knowing:
- The default storage connection of the Synapse copy tool failed with an authorisation error (the lab account could not give the workspace identity a role). A second linked service using the storage account key solved it. External tables and CETAS used the signed-in user's own identity, which worked.
- The serverless pool has no storage of its own. Every table is an external table over files, and CETAS writes each result as new Parquet files.

## Data model

| Table | Grain | Key | Notes |
|---|---|---|---|
| `fact_trip` | one row per trip | `trip_id` | `ride_duration_minutes` (fractional), `rider_age_at_trip`, start and end station keys, start and end date keys, time band, duration flag |
| `fact_payment` | one row per payment | `payment_id` | `amount DECIMAL(18,2)`, rider key, payment date key |
| `dim_rider` | one row per rider | `rider_id` | `age_at_account_start`, current `is_member`, `is_account_period_valid` |
| `dim_station` | one row per station | `station_id` | used for both the start and the end role |
| `dim_date` | one row per day | `date_key` (YYYYMMDD) | range built from the data itself, no gaps |

The star-schema diagram is [diagram/star_schema.png](../diagram/star_schema.png); its source of truth is [schema_spec.py](../diagram/schema_spec.py), which the checks compare against the SQL.

## Decisions and the reasons for them

**Two fact tables.** A payment has no trip id. Joining payments to trips would repeat each payment once per ride and inflate spend. The two facts share `dim_rider` and `dim_date` and are combined only after both are summed to the same grain (rider and month), as in the "usage vs spend" analysis.

**Natural keys.** The source ids are unique and stable, and the serverless pool has no identity columns, so the source ids serve as dimension keys. Foreign keys are not enforced in external tables; the validation scorecard checks uniqueness and orphans with queries instead.

**Age.** Completed years: the year difference, minus one if the birthday has not yet happened that year. `DATEDIFF(year, ...)` alone counts calendar-year boundaries and is wrong before the birthday. A 29 February birthday counts as 28 February in non-leap years, which is how T-SQL's `DATEADD` behaves. Only one trip in this data is affected. `rider_age_at_trip` uses the ride's start date; `age_at_account_start` uses the account start date.

**Duration.** Seconds divided by 60 and stored as `DECIMAL(12,4)`, so a 6 minute 47 second ride is 6.7833 minutes, not 7. Bad durations are kept in the fact table with a `duration_issue` value (`ok`, `negative`, `zero`, `over_24h`, `missing`) and `is_valid_duration`. Reports filter on the flag. Deleting them would make the warehouse disagree with the source row count.

**Time of day.** `start_hour` plus a five-band `time_band` inside the fact table. A separate time dimension would add little here.

**Missing references.** Fact keys are copied from the source and checked afterwards (every check passed), so an unknown station or rider would show up as a failed check and not disappear through an inner join.

**Dates and money as text in staging.** The copy tool's output format was not known until the run. Staging as text avoids silent NULLs from a failed conversion, and the transformation parses amounts defensively (removes `$` and commas, treats parentheses as negative) and counts failures.

**Parquet output, one folder per run.** Parquet keeps dates as dates and decimals as decimals. `DROP EXTERNAL TABLE` removes only the table definition, not the files CETAS wrote, so reusing a folder would mix old and new files. Every re-run therefore writes to a new `run02`, `run03`, and so on, in all five scripts.

**Time zone.** The source does not state one. Times are used as stored (assumed Chicago local time) and are not converted.

## Limitations

- Membership is the current flag, not what it was at each ride. Member versus casual comparisons are comparisons by current status.
- Payments cannot be linked to individual rides. Any relationship between riding and paying seen in aggregates is descriptive only. In this synthetic data it is weak, and it should not be read as customer behaviour.
- Many trips fall before an account's start date or after its end date (838,258 and 561,467). That is a property of the synthetic data. Those trips are kept.
- The 4-decimal storage of minutes means a sum that lands exactly on a bucket edge can differ from exact arithmetic by a few rows.
- Only the SQL that was run in Synapse was run in Synapse. See [validation.md](validation.md) for which dashboard views were and were not run there.
