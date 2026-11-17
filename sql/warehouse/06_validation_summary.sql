-- 06_validation_summary.sql
-- One result table that checks the whole warehouse at once: PASS / FAIL per check.
-- "expected" values come from profiling the source CSVs locally (not from Azure).
-- Run in the serverless SQL pool, database divvy_dw, after scripts 01-05.
-- Takes about a minute: it scans the 4.6M-row trip data several times.

WITH checks AS (
    SELECT '01 rows: fact_trip'    AS check_name, CAST((SELECT COUNT_BIG(*) FROM dbo.fact_trip)    AS DECIMAL(18,2)) AS actual, CAST(4584921 AS DECIMAL(18,2)) AS expected
    UNION ALL SELECT '02 rows: fact_payment', (SELECT COUNT_BIG(*) FROM dbo.fact_payment), 1946607
    UNION ALL SELECT '03 rows: dim_rider',    (SELECT COUNT_BIG(*) FROM dbo.dim_rider),    75000
    UNION ALL SELECT '04 rows: dim_station',  (SELECT COUNT_BIG(*) FROM dbo.dim_station),  838
    UNION ALL SELECT '05 rows: dim_date (2013-01-31..2022-02-12)', (SELECT COUNT_BIG(*) FROM dbo.dim_date), 3300
    UNION ALL SELECT '06 duplicate trip_id',    (SELECT COUNT_BIG(*) - COUNT_BIG(DISTINCT trip_id)    FROM dbo.fact_trip),    0
    UNION ALL SELECT '07 duplicate payment_id', (SELECT COUNT_BIG(*) - COUNT_BIG(DISTINCT payment_id) FROM dbo.fact_payment), 0
    UNION ALL SELECT '08 duplicate rider_id',   (SELECT COUNT_BIG(*) - COUNT_BIG(DISTINCT rider_id)   FROM dbo.dim_rider),    0
    UNION ALL SELECT '09 duplicate station_id', (SELECT COUNT_BIG(*) - COUNT_BIG(DISTINCT station_id) FROM dbo.dim_station),  0
    UNION ALL SELECT '10 duplicate date_key',   (SELECT COUNT_BIG(*) - COUNT_BIG(DISTINCT date_key)   FROM dbo.dim_date),     0
    UNION ALL SELECT '11 trips with unknown rider',
        (SELECT COUNT_BIG(*) FROM dbo.fact_trip f LEFT JOIN dbo.dim_rider d ON d.rider_id = f.rider_id WHERE d.rider_id IS NULL), 0
    UNION ALL SELECT '12 trips with unknown start station',
        (SELECT COUNT_BIG(*) FROM dbo.fact_trip f LEFT JOIN dbo.dim_station d ON d.station_id = f.start_station_id WHERE d.station_id IS NULL), 0
    UNION ALL SELECT '13 trips with unknown end station',
        (SELECT COUNT_BIG(*) FROM dbo.fact_trip f LEFT JOIN dbo.dim_station d ON d.station_id = f.end_station_id WHERE d.station_id IS NULL), 0
    UNION ALL SELECT '14 trips with start date not in dim_date',
        (SELECT COUNT_BIG(*) FROM dbo.fact_trip f LEFT JOIN dbo.dim_date d ON d.date_key = f.start_date_key WHERE d.date_key IS NULL), 0
    UNION ALL SELECT '15 payments with unknown rider',
        (SELECT COUNT_BIG(*) FROM dbo.fact_payment f LEFT JOIN dbo.dim_rider d ON d.rider_id = f.rider_id WHERE d.rider_id IS NULL), 0
    UNION ALL SELECT '16 payments with date not in dim_date',
        (SELECT COUNT_BIG(*) FROM dbo.fact_payment f LEFT JOIN dbo.dim_date d ON d.date_key = f.payment_date_key WHERE d.date_key IS NULL), 0
    UNION ALL SELECT '17 payments with NULL amount (parse failures)', (SELECT COUNT_BIG(*) FROM dbo.fact_payment WHERE amount IS NULL), 0
    UNION ALL SELECT '18 total payment amount',  (SELECT SUM(amount) FROM dbo.fact_payment), 19457105.25
    UNION ALL SELECT '19 trips duration ok',       (SELECT COUNT_BIG(*) FROM dbo.fact_trip WHERE duration_issue = 'ok'),       4583447
    UNION ALL SELECT '20 trips duration negative', (SELECT COUNT_BIG(*) FROM dbo.fact_trip WHERE duration_issue = 'negative'), 116
    UNION ALL SELECT '21 trips duration zero',     (SELECT COUNT_BIG(*) FROM dbo.fact_trip WHERE duration_issue = 'zero'),     81
    UNION ALL SELECT '22 trips duration over 24h', (SELECT COUNT_BIG(*) FROM dbo.fact_trip WHERE duration_issue = 'over_24h'), 1277
    UNION ALL SELECT '23 trips with NULL age',     (SELECT COUNT_BIG(*) FROM dbo.fact_trip WHERE rider_age_at_trip IS NULL),   0
    UNION ALL SELECT '24 riders with account end before start', (SELECT COUNT_BIG(*) FROM dbo.dim_rider WHERE is_account_period_valid = 0), 1033
    UNION ALL SELECT '25 hand check: trip 89E7AA6C29227EFF age (37)',
        (SELECT MAX(rider_age_at_trip) FROM dbo.fact_trip WHERE trip_id = '89E7AA6C29227EFF'), 37
    UNION ALL SELECT '26 hand check: rider 1002 age at account start (23)',
        (SELECT MAX(age_at_account_start) FROM dbo.dim_rider WHERE rider_id = 1002), 23
)
SELECT check_name, actual, expected,
       CASE WHEN actual = expected THEN 'PASS' ELSE 'FAIL' END AS status
FROM checks
ORDER BY check_name;
