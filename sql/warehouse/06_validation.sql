-- 06_validation.sql
-- Run in the serverless SQL pool, database divvy_dw, AFTER scripts 01-05.
-- STATUS: executed in Azure on 14 Nov 2026; results matched the expected values (see evidence/).
-- "Expected" values come from profiling the local CSV files with Python, not from Azure.
-- A check passes when the result equals the Expected value.

-- 1. Source vs staging vs warehouse counts ---------------------------------------------
-- Nothing is filtered out, so every row must match.
-- Expected: rider 75000 | payment 1946607 | station 838 | trip 4584921
SELECT 'rider'   AS entity, (SELECT COUNT_BIG(*) FROM dbo.staging_rider)   AS staging_rows, (SELECT COUNT_BIG(*) FROM dbo.dim_rider)    AS warehouse_rows
UNION ALL SELECT 'station', (SELECT COUNT_BIG(*) FROM dbo.staging_station), (SELECT COUNT_BIG(*) FROM dbo.dim_station)
UNION ALL SELECT 'payment', (SELECT COUNT_BIG(*) FROM dbo.staging_payment), (SELECT COUNT_BIG(*) FROM dbo.fact_payment)
UNION ALL SELECT 'trip',    (SELECT COUNT_BIG(*) FROM dbo.staging_trip),    (SELECT COUNT_BIG(*) FROM dbo.fact_trip);

-- 2 & 3. Unique keys (external tables do not enforce PKs, so check them) ----------------
-- Expected: every column = 0 (rows minus distinct keys)
SELECT
    (SELECT COUNT_BIG(*) - COUNT_BIG(DISTINCT trip_id)    FROM dbo.fact_trip)    AS dup_trip_id,
    (SELECT COUNT_BIG(*) - COUNT_BIG(DISTINCT payment_id) FROM dbo.fact_payment) AS dup_payment_id,
    (SELECT COUNT_BIG(*) - COUNT_BIG(DISTINCT rider_id)   FROM dbo.dim_rider)    AS dup_rider_id,
    (SELECT COUNT_BIG(*) - COUNT_BIG(DISTINCT station_id) FROM dbo.dim_station)  AS dup_station_id,
    (SELECT COUNT_BIG(*) - COUNT_BIG(DISTINCT date_key)   FROM dbo.dim_date)     AS dup_date_key;

-- 4. Unmatched foreign keys (anti-joins). Expected: every column = 0 ---------------------
SELECT
    (SELECT COUNT_BIG(*) FROM dbo.fact_trip f LEFT JOIN dbo.dim_rider   d ON d.rider_id   = f.rider_id         WHERE d.rider_id   IS NULL) AS trip_orphan_rider,
    (SELECT COUNT_BIG(*) FROM dbo.fact_trip f LEFT JOIN dbo.dim_station d ON d.station_id = f.start_station_id WHERE d.station_id IS NULL) AS trip_orphan_start_station,
    (SELECT COUNT_BIG(*) FROM dbo.fact_trip f LEFT JOIN dbo.dim_station d ON d.station_id = f.end_station_id   WHERE d.station_id IS NULL) AS trip_orphan_end_station,
    (SELECT COUNT_BIG(*) FROM dbo.fact_trip f LEFT JOIN dbo.dim_date    d ON d.date_key   = f.start_date_key   WHERE d.date_key   IS NULL) AS trip_orphan_start_date,
    (SELECT COUNT_BIG(*) FROM dbo.fact_trip f LEFT JOIN dbo.dim_date    d ON d.date_key   = f.end_date_key     WHERE d.date_key   IS NULL) AS trip_orphan_end_date,
    (SELECT COUNT_BIG(*) FROM dbo.fact_payment f LEFT JOIN dbo.dim_rider d ON d.rider_id  = f.rider_id         WHERE d.rider_id   IS NULL) AS pay_orphan_rider,
    (SELECT COUNT_BIG(*) FROM dbo.fact_payment f LEFT JOIN dbo.dim_date  d ON d.date_key  = f.payment_date_key  WHERE d.date_key   IS NULL) AS pay_orphan_date;

-- 5. Trip duration quality (all rows kept, bad ones flagged) -----------------------------
-- Expected: ok 4583447 | negative 116 | zero 81 | over_24h 1277 | missing 0
SELECT duration_issue, COUNT_BIG(*) AS trips, MIN(ride_duration_minutes) AS min_min, MAX(ride_duration_minutes) AS max_min
FROM dbo.fact_trip GROUP BY duration_issue ORDER BY trips DESC;
-- Expected is_valid_duration = 1 -> 4583447 rows (= the 'ok' row above).
-- Trips with duration <1 minute are still 'ok' (about 59.5k incl. the bad ones); decide in reporting.

-- 6. Payment amounts that failed to parse. Expected: 0 NULL amounts; min 3.00, max 25.00,
--    total about 19457105.25 (local CSV sum 19457105.24999999).
SELECT COUNT_BIG(*) AS null_amounts FROM dbo.fact_payment WHERE amount IS NULL;
SELECT MIN(amount) AS min_amount, MAX(amount) AS max_amount, SUM(amount) AS total_amount FROM dbo.fact_payment;
-- If null_amounts > 0, look at the raw text:
-- SELECT TOP 20 amount FROM dbo.staging_payment WHERE TRY_CAST(REPLACE(REPLACE(amount,'$',''),',','') AS DECIMAL(18,2)) IS NULL;

-- 7. Join amplification: joining the facts to the dimensions must not add rows -----------
-- Expected: each joined_rows equals its fact_rows (4584921 / 1946607).
SELECT 'fact_trip x dim_rider x dim_date' AS test,
       (SELECT COUNT_BIG(*) FROM dbo.fact_trip) AS fact_rows,
       (SELECT COUNT_BIG(*) FROM dbo.fact_trip f
          LEFT JOIN dbo.dim_rider r ON r.rider_id = f.rider_id
          LEFT JOIN dbo.dim_date  d ON d.date_key = f.start_date_key) AS joined_rows
UNION ALL
SELECT 'fact_payment x dim_rider x dim_date',
       (SELECT COUNT_BIG(*) FROM dbo.fact_payment),
       (SELECT COUNT_BIG(*) FROM dbo.fact_payment f
          LEFT JOIN dbo.dim_rider r ON r.rider_id = f.rider_id
          LEFT JOIN dbo.dim_date  d ON d.date_key = f.payment_date_key);

-- 8. Date coverage ------------------------------------------------------------------------
-- Expected: dim_date 3300 rows, 2013-01-31 .. 2022-02-12, no gaps (days_in_range = row count);
-- trips 2021-02-01 .. 2022-01-31 (start); payments 2013-02-01 .. 2022-02-01.
SELECT COUNT_BIG(*) AS dim_date_rows, MIN(full_date) AS first_day, MAX(full_date) AS last_day,
       DATEDIFF(day, MIN(full_date), MAX(full_date)) + 1 AS days_in_range
FROM dbo.dim_date;
SELECT MIN(started_at) AS first_trip_start, MAX(started_at) AS last_trip_start, MAX(ended_at) AS last_trip_end FROM dbo.fact_trip;
SELECT MIN(payment_date) AS first_payment, MAX(payment_date) AS last_payment FROM dbo.fact_payment;
-- Date key must equal the date. Expected: 0
SELECT COUNT_BIG(*) AS bad_date_keys FROM dbo.dim_date
WHERE date_key <> YEAR(full_date) * 10000 + MONTH(full_date) * 100 + DAY(full_date);

-- 9. Hand-checked samples (expected values worked out by hand / in Python from the raw CSV) ---
-- Age = completed years. Cases cover: birthday not reached yet, birthday exactly on the ride day.
--   trip 89E7AA6C29227EFF  born 1983-08-26, ride 2021-02-12 16:14:56 -> age 37, duration 6.7833 min
--   trip 0FEFDE2603568365  born 1982-12-10, ride 2021-02-14 17:52:38 -> age 38, duration 19.5167 min
--   trip FF8A16B71C279F5F  born 1977-02-10, ride 2021-02-10 (birthday!) -> age 44
--   trip 8DA4AE7FD9F99C77  born 1996-02-18, ride 2021-02-18 (birthday!) -> age 25
SELECT trip_id, started_at, ride_duration_minutes, rider_age_at_trip
FROM dbo.fact_trip
WHERE trip_id IN ('89E7AA6C29227EFF','0FEFDE2603568365','FF8A16B71C279F5F','8DA4AE7FD9F99C77');
--   rider 1000 born 1989-02-13, account start 2019-04-23 -> 30
--   rider 1001 born 1976-08-10, account start 2019-11-01 -> 43
--   rider 1002 born 1998-08-10, account start 2022-02-04 -> 23 (birthday not reached yet)
SELECT rider_id, birthday, account_start_date, age_at_account_start
FROM dbo.dim_rider WHERE rider_id IN (1000, 1001, 1002) ORDER BY rider_id;
-- Age sanity. Expected from local profile: rider_age_at_trip about 14.96-75.4 -> 14..75, no NULLs.
SELECT MIN(rider_age_at_trip) AS min_age, MAX(rider_age_at_trip) AS max_age,
       SUM(CASE WHEN rider_age_at_trip IS NULL THEN 1 ELSE 0 END) AS null_age
FROM dbo.fact_trip;
-- Expected: 1033 riders with an account end date before the start date.
SELECT COUNT_BIG(*) AS riders_end_before_start FROM dbo.dim_rider WHERE is_account_period_valid = 0;

-- 10. Re-runnability / CETAS locations ----------------------------------------------------------
-- Lists each external table and the folder it reads. Every warehouse table must point at a folder
-- ending in the SAME run number (e.g. run01). DROP EXTERNAL TABLE leaves the old files in storage,
-- so a re-run needs a new run number. Check the folders themselves in Synapse Studio -> Data -> Linked.
SELECT t.name AS table_name, t.location
FROM sys.external_tables t
ORDER BY t.name;
