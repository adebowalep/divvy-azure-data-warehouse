# Validation

Two kinds of results are reported here and they are kept apart on purpose:

- **Observed in Azure Synapse.** Query output from the real warehouse, saved as screenshots in [evidence/](../evidence/).
- **Computed locally.** Python run on the original source CSV files with the same business rules as the SQL, used to cross-check the warehouse and to build the dashboard.

The dashboard never queried Azure. The Azure resources were deleted after the run, so the Azure results below cannot be re-run from this repository.

## The 26-check scorecard (observed in Azure)

[06_validation_summary.sql](../sql/warehouse/06_validation_summary.sql) returns one table: check name, actual value, expected value and PASS or FAIL. The expected values came from profiling the source files before the warehouse was built, so a check passes only when the warehouse matches the source. All 26 passed; the screenshot is [04_validation_summary.png](../evidence/04_validation_summary.png).

| Checks | What is tested | Expected |
|---|---|---|
| 01 to 05 | row counts: `fact_trip`, `fact_payment`, `dim_rider`, `dim_station`, `dim_date` | 4,584,921 / 1,946,607 / 75,000 / 838 / 3,300 |
| 06 to 10 | no duplicate `trip_id`, `payment_id`, `rider_id`, `station_id`, `date_key` | 0 each |
| 11 to 16 | no trip with an unknown rider, start station, end station or date; no payment with an unknown rider or date | 0 each |
| 17 and 18 | no payment amount failed to parse; total payment amount | 0; $19,457,105.25 |
| 19 to 22 | trip durations: valid, negative, zero, over 24 hours | 4,583,447 / 116 / 81 / 1,277 |
| 23 | no trip without a rider age | 0 |
| 24 | accounts with an end date before the start date | 1,033 |
| 25 and 26 | two ages worked out by hand (a trip and an account start) | 37 and 23 |

The longer script [06_validation.sql](../sql/warehouse/06_validation.sql) adds the same checks as separate queries, date coverage, join-amplification tests and the CETAS folder listing.

The source tables were checked first in PostgreSQL ([validate_source.sql](../sql/postgres/validate_source.sql); output in [evidence/00_postgres_validation.txt](../evidence/00_postgres_validation.txt)).

## What the dashboard shows, and where each view comes from

Every figure on the dashboard was computed locally from the CSV files by [build_data.py](../dashboard/build_data.py). Some were also observed in Synapse and match; others were not run there.

| Dashboard view | Also observed in Synapse? | Evidence |
|---|---|---|
| Headline totals (trips, valid rides, payments, total amount) | yes | `04_validation_summary.png` |
| Trip-duration issues (valid, negative, zero, over 24 h) | yes | `04_validation_summary.png` |
| Duration by weekday and time band | yes (the heatmap is the same data by hour) | `05_q1a_weekday_timeband.png` |
| Longest rides by start station (100+ rides) | yes | `05_q1b_start_station.png` |
| Duration by age band | yes | `05_q1d_age.png` |
| Member vs casual duration | yes | `05_q1e_member_casual.png` |
| Payments by year | yes | `05_q2_spend_year.png` |
| Spend per rider by age at account start | yes | `05_q3_spend_by_age_at_start.png` |
| Usage vs spend (two bar charts) | yes (the dashboard shows the Synapse output values) | `05_q4_*.png`, `05_q5_*.png` |
| Monthly rides, commute pattern, duration distribution, bike mix | no | computed locally |
| End-station role, rebalancing (net flow), routes | no | computed locally |
| Monthly payments, members vs casual payment size | no | computed locally |
| Accounts opened, closed and active | no | computed locally |

## Cross-checks of the locally computed views

The views that Synapse did not run were recomputed with a second, separately written pass in pure Python (reading the CSV files row by row, no pandas) and compared with `data.json`. Matching results: the valid ride count, the three most common point-to-point routes, the top round-trip station, the round-trip share (7.34%), starts, ends and net flow for one station, all 14 duration bins, bike-type counts for the first month, member ride count, accounts opened and closed per year, and the active-account count for every month under every filter (330 values). This was an ad hoc check and is not stored in the repository.

It found two problems, both fixed:

1. **Leap-day birthday.** The dashboard's Python age function counted a 29 February birthday as not yet reached on 28 February, while T-SQL `DATEADD` counts it as 28 February. One ride therefore sat in a different age band (1,063,542 and 474,408 locally against 1,063,541 and 474,409 in Synapse). The Python was changed to the warehouse rule and the age bands now equal the Azure output exactly.
2. **Active accounts.** Accounts with an end date before their start date were counted as active from their start onwards, although the page says they are excluded. They are now left out of the active count. Opened and closed counts were not affected.

One small known difference remains and is explained, not fixed: Azure stores each ride's minutes rounded to four decimals, so a rider-month whose total lands exactly on a bucket edge (30, 60 or 120 minutes) can fall in a neighbouring bucket. This moved 3 to 6 rider-months, with equal and opposite changes, in the minutes view. That view shows the Synapse output values.

## Dashboard tests

`python3 tests/check_project.py` (no extra packages) checks that the generated dashboard is current, the page is a complete HTML document and loads nothing from outside except fonts, the totals in `data.json` reconcile (members plus casual equal all riders, valid plus invalid equal all trips, and so on), the SQL agrees with the schema spec and the diagrams, Markdown links resolve, and no secrets or data files are in the repository.

`python3 tests/smoke_dashboard.py` drives the page in a real Chromium browser (Playwright). 84 checks passed on 17 November 2026: KPI values for each rider type against `data.json`, every tab under every filter, direct links and browser Back and Forward, keyboard navigation of the tabs, tooltips, the sliders and toggles, empty states, dark mode, text contrast (at least 4.5:1 in both colour schemes) and no sideways overflow at desktop (1280 px), tablet (820 px) and phone (390 px) widths. The same run was repeated against a local web server. It does not test other browsers and it does not test touch gestures beyond the phone-sized layout.
