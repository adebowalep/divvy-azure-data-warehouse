# Divvy Bike Share - Azure Data Warehouse (Udacity project)

**Project state: the pipeline has been run end to end in Azure** (PostgreSQL, Synapse Ingest, 4 external staging tables, 5 CETAS tables, validation, business queries). Real screenshots are in `evidence/`. Outstanding: the cleanup of Azure resources (see the end).
Run date: 14 Nov 2026, Udacity cloud lab, built-in serverless SQL pool, region West Europe (PostgreSQL in Canada Central).
`RUBRIC_CHECKLIST.md` lists the evidence for each rubric criterion.

## Architecture

```
Datasets/*.csv --(starter/ProjectDataToPostgres.py)--> Azure PostgreSQL (OLTP, 4 tables)
   --(Synapse Ingest wizard, one-time copy)--> Azure storage: 4 text files        [EXTRACT]
   --(4x CREATE EXTERNAL TABLE)--> staging_* external tables, serverless pool    [LOAD]
   --(5x CETAS)--> dim_* and fact_* external tables (Parquet files in storage)  [TRANSFORM]
```
Only the built-in **serverless** SQL pool is used. It has no local storage, so no table is ever
"created" in the normal sense: external tables are a schema laid over files, and CETAS
(`CREATE EXTERNAL TABLE ... AS SELECT`) writes the query result to new files.

## Source data (checked against the real files, not the overview picture)
The overview ERD shows five entities, but the starter script creates **four** tables:

| Table | Rows | Columns |
|---|---|---|
| rider | 75,000 | rider_id, first, last, address, birthday, account_start_date, account_end_date, is_member |
| payment | 1,946,607 | payment_id, date, amount (MONEY), rider_id |
| station | 838 | station_id (text, e.g. `KA1503000012`), name, latitude, longitude |
| trip | 4,584,921 | trip_id, rideable_type, start_at, ended_at, start_station_id, end_station_id, rider_id |

There is no Account table, `member_id`, or `account_number`. The CSV files have no header row, no quotes, and no commas inside values.
Row counts, ranges and anomalies below were measured locally on the CSVs (Python), not in Azure.

Findings that shaped the design:
* All trips are from 2021-02-01 to 2022-01-31; payments run 2013-02-01 to 2022-02-01 (all on the 1st of a month, one per rider per month).
* Station and rider ids in trips and payments all match their tables (0 orphans).
* Trip durations: 116 negative, 81 zero, 1,277 over 24 h (max 932 h). They are kept and flagged, not deleted.
* 1,033 riders have an account end date before their start date (flagged `is_account_period_valid = 0`).
* Many trips fall before the rider's account start (838,258) or after its end (561,467). The data is synthetic; I report it but do not filter on it.
* `is_member` is a current flag only. Membership history does not exist, so member/casual by ride is "current status".
* Timestamps carry no time zone. They are used as stored (assumed Chicago local time).

## Star schema (`diagram/star_schema.pdf`)
| Table | Grain | Key | Main columns |
|---|---|---|---|
| `fact_trip` | one row per trip | trip_id | rider_id, start_station_id, end_station_id, start_date_key, end_date_key, started_at, ended_at, start_hour, time_band, **ride_duration_minutes**, **rider_age_at_trip**, is_valid_duration, duration_issue |
| `fact_payment` | one row per payment | payment_id | rider_id, payment_date_key, payment_date, **amount** |
| `dim_rider` | one row per rider | rider_id | name, birthday, account start/end, is_member (current), age_at_account_start, is_account_period_valid |
| `dim_station` | one row per station | station_id | station_name, latitude, longitude (used for both start and end roles) |
| `dim_date` | one row per day | date_key (YYYYMMDD) | full_date, day_of_week (1=Mon), day_name, is_weekend, month, quarter, year, year_month |

Design choices (good to be able to explain):
* **Natural keys as dimension keys.** rider_id, station_id and trip/payment ids are stable and unique, and serverless has no IDENTITY. This keeps the SQL simple. Station ids stay text.
* **Two facts, not one.** Trips and payments have different grain and no link. Joining them per row would repeat each payment once per ride. The extra-credit queries sum each side to rider-month first and join on that.
* **Age** = completed years: `DATEDIFF(year)` minus 1 if the birthday has not yet occurred. `rider_age_at_trip` uses the ride start date; `age_at_account_start` uses the account start date.
* **Leap-day birthdays** count as 28 Feb in non-leap years (how SQL Server's `DATEADD` behaves). It affects exactly one trip in this data (trip `90994BC0562F8150`, rider born 1976-02-29, ridden 2021-02-28), which is why an independent Python check differed by one ride between the 35-44 and 45-54 bands.
* **Duration** = seconds / 60.0 stored as `DECIMAL(12,4)`. Flagged bad rows are excluded only in reports (`is_valid_duration = 1`).
* **Time of day** is a `start_hour` plus a five-band `time_band` inside the fact. A separate time dimension was not worth it.
* **Parquet** output for the warehouse tables (types stay intact). The staging reads use the CSV format.

## Folder layout
```
starter/ProjectDataToPostgres.py   Udacity script, 3 small marked fixes (env-var credentials, no silent DB drop, fail on COPY error)
sql/postgres/validate_source.sql   source table checks (run in pgAdmin/psql)
sql/00_external_objects.sql        data source + file formats (edit 2 placeholders)
sql/staging/staging_*.sql          LOAD: 4 CREATE EXTERNAL TABLE scripts
sql/warehouse/01..05_*.sql         TRANSFORM: one CETAS per dimension/fact, in dependency order
sql/warehouse/06_validation.sql    reconciliation and quality checks
sql/warehouse/07_business_queries.sql  the business questions
diagram/                           schema_spec.py (single source of truth), make_star_schema_pdf.py, star_schema.pdf
tests/check_project.py             local consistency check (no Azure needed)
evidence/                          real screenshots only (empty until the lab is run)
```

## How to run (in order)
1. **Local data:** unzip the Udacity dataset into `./data` next to the starter script. `pip install psycopg2-binary`.
   Set `PGHOST`, `PGUSER`, `PGPASSWORD` (from the lab page; never in code), then `python starter/ProjectDataToPostgres.py`.
   It refuses to drop an existing `udacityproject` database unless `DIVVY_ALLOW_RESET=yes`.
   Then run `sql/postgres/validate_source.sql`.
2. **Extract:** Synapse Studio -> Integrate/Ingest -> Built-in copy task -> one-time. Source: the PostgreSQL connection, tables `public.payment`, `public.rider`, `public.trip`, `public.station`. Destination: the linked storage, **no header row**, folder = container root, file names `public.<table>.txt`. Screenshot the four files.
3. **Setup:** in `sql/00_external_objects.sql` replace `<container>` and `<storage_account>`; run it connected to the built-in pool (create database `divvy_dw` first, as the comment says).
4. **Load:** run the four `sql/staging/staging_*.sql`. If your file names or folder differ, change `LOCATION` only.
5. **Transform:** run `sql/warehouse/01` to `05` in order (dims before facts).
6. **Check:** run `06_validation.sql`, then `07_business_queries.sql`. Screenshot results.

### Re-running CETAS
`DROP EXTERNAL TABLE` removes only the table definition, **not the files** CETAS wrote. Reusing a folder would mix old and new files.
For a re-run, change `run01` to `run02` in the `LOCATION` of all five scripts (the local check enforces one run number), or delete only your own `warehouse/<table>/run01/` folders in Synapse Studio first.

## What actually happened in Azure (verified)
* PostgreSQL load: 75,000 / 1,946,607 / 838 / 4,584,921 rows; source checks matched the local CSV profile (`evidence/00_*`).
* Extract: the Ingest wizard wrote `public.payment.txt`, `public.rider.txt`, `public.station.txt`, `public.trip.txt` at the container root, **no header**. Text values are **quoted** (`"Diana"`), timestamps look like `2021-02-12 16:14:56.0000000`, and money like `9.00` (no `$`). The scripts handle all of these.
* The default storage connection failed with `AuthorizationPermissionMismatch` (the workspace identity had no role and the lab account cannot assign roles). The fix was a second linked service that uses the storage **account key**. CETAS and the external tables use the signed-in user's identity (Storage Blob Data Owner), which worked.
* `divvy_dw` database, 4 staging tables, 5 CETAS tables (Parquet, `run01`) all ran without script changes.
* `sql/warehouse/06_validation_summary.sql`: all 26 checks PASS (`evidence/04_validation_summary.png`).
* Business queries 1-3 and the extra credit were cross-checked against an independent Python calculation from the raw CSVs. Everything matched except: one ride moves between age bands because of a leap-day birthday (see above), and a few rider-months at band edges in the minutes query, because ride minutes are stored rounded to 4 decimals.

## Findings (from the executed queries; syntheticdata, so treat as a demo)
* Weekend rides are longer (about 25-26 min at midday on Sat/Sun vs about 18 on weekdays); weekday mornings are shortest (about 12.7-13.9 min).
* Age and member/casual make almost no difference to average ride length (about 19.3-20.4 min; member 19.87 vs casual 19.76).
* Longest average rides start at low-volume far-south-side stations.
* Total payments grow every year, from $53.7k (2013) to $6.08M (2021).
* Extra credit: spend does not rise with riding. Riders who ride more pay about the same ($6.8-7.0 per active month). Months with no riding average $9.98 because 63% of paid rider-months have no rides, and 31% of ride-months have no payment that month. In this synthetic data, 93,845 ride-months fall outside the rider's account dates. So the data shows no usage-based pricing signal, and the result should not be read as customer behaviour.

## Interactive dashboard (extra, not required by the rubric)
`dashboard/index.html` is a single self-contained page (open it in any browser; no server needed). It has a rider-type filter and seven tabs: ride time, stations, flow and routes, money, riders, usage vs spend, and pipeline and checks. Headline numbers, age bands, spend and usage-vs-spend are the Azure query results; the heatmap, monthly, map, flow, route, bike-mix and rider views are computed from the same source files with the same rules. It does not read from Azure.

## Limitations
* Membership is current-only, payments cannot be tied to rides, and the time zone is unstated.
* Per-ride minutes are stored with 4 decimals; sums near a band edge can differ from exact arithmetic by a few rows.
* Trips fall outside account dates for many riders (synthetic data); they are kept and not filtered.
* Parquet CETAS output worked in this lab; the CSV fallback is described in `00_external_objects.sql` but was not needed.

## Testing done locally
`python3 -I tests/check_project.py` checks file presence, that diagram columns exist in the CETAS SQL, that load scripts use `CREATE EXTERNAL TABLE`, and that no script uses a regular `CREATE TABLE`. It is not a substitute for running the SQL in Synapse.

## Cleanup (ask before deleting anything)
The resources created for this project are in resource group `ODL-DataEng-306019`: PostgreSQL server `divvy-pg`, Synapse workspace `divvy-syn`, storage account `divvystorage`. The lab deletes them when the session ends. If you want to remove them earlier, delete only these three (not the resource group, which belongs to the lab), and only after all screenshots and SQL files are saved. **Done on 15 Nov 2026:** all three were deleted and the resource group was empty afterwards (`evidence/08_cleanup_empty_resource_group.png`).
