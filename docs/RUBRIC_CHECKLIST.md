# Rubric checklist (status as of 15 Nov 2026)

All items were executed in the Udacity cloud lab on 14 Nov 2026. Screenshots are real; file names below are in `evidence/`.

| Criterion | Artifact | Status |
|---|---|---|
| Two facts sharing dimensions; trip fact has duration + age; payment fact has amount | `diagram/star_schema.pdf` (fact_trip: ride_duration_minutes, rider_age_at_trip; fact_payment: amount) | DONE |
| Trip dimensions: riders, stations, dates. Payment dimensions: riders, dates | same PDF | DONE |
| Extract: storage screenshot with the 4 files | `01_extraction_four_files.png` (also `01_extraction_pipeline_run.png`, `01_extraction_activity_runs.png`, `01_extraction_preview_*.png`) | DONE |
| Load: 4 scripts with CREATE EXTERNAL TABLE pointing at the 4 files | `sql/staging/staging_*.sql` (zip copies: `Load1-4.txt`); proof `02_staging_*.png`, `02_staging_counts.png` | DONE, executed; counts match |
| Transform: fact CETAS with dimension keys and measures | `sql/warehouse/04_fact_trip.sql`, `05_fact_payment.sql`; proof `03_fact_trip.png`, `03_fact_payment.png` | DONE, executed |
| Transform: dimension CETAS matching the diagram, no facts | `sql/warehouse/01-03`; proof `03_dim_date.png`, `03_dim_rider.png`, `03_dim_station.png`, `03_warehouse_folders.png`, `03_warehouse_parquet_files.png` | DONE, executed |
| Beyond the rubric: interactive dashboard | `dashboard/index.html` (open in a browser) | DONE, opened and tested in a browser |
| Beyond the rubric: validation and business questions | `06_validation_summary.sql` (26/26 PASS, `04_validation_summary.png`), `07_business_queries.sql` (`05_q*.png`) | DONE, cross-checked against an independent Python calculation |
