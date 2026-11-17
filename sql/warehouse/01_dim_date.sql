-- 01_dim_date.sql   (TRANSFORM step, dimension)
-- Grain: one row per calendar day.
-- Range: built from the data itself, from the earliest to the latest date found in
-- trips, payments and rider account dates (inclusive, no gaps). Nothing is hardcoded.
-- Used by: fact_trip.start_date_key / end_date_key and fact_payment.payment_date_key.
--
-- RE-RUN: DROP EXTERNAL TABLE does NOT delete the files CETAS wrote. Before a re-run,
-- change run01 in LOCATION to run02, run03... (use the same number in every script).
-- Never reuse a folder: old and new files would be read together.

IF OBJECT_ID('dbo.dim_date') IS NOT NULL
    DROP EXTERNAL TABLE dbo.dim_date;
GO

CREATE EXTERNAL TABLE dbo.dim_date
WITH (
    LOCATION    = 'warehouse/dim_date/run01/',
    DATA_SOURCE = [divvy_storage],
    FILE_FORMAT = [divvy_parquet_format]
)
AS
WITH all_dates AS (
    SELECT TRY_CONVERT(date, LEFT(started_at, 10))        AS d FROM dbo.staging_trip
    UNION ALL
    SELECT TRY_CONVERT(date, LEFT(ended_at, 10))          FROM dbo.staging_trip
    UNION ALL
    SELECT TRY_CONVERT(date, LEFT(payment_date, 10))      FROM dbo.staging_payment
    UNION ALL
    SELECT TRY_CONVERT(date, LEFT(account_start_date, 10)) FROM dbo.staging_rider
    UNION ALL
    SELECT TRY_CONVERT(date, LEFT(account_end_date, 10))   FROM dbo.staging_rider
),
bounds AS (
    SELECT MIN(d) AS min_d, MAX(d) AS max_d FROM all_dates
),
digits AS (
    SELECT n FROM (VALUES (0),(1),(2),(3),(4),(5),(6),(7),(8),(9)) v(n)
),
day_numbers AS (   -- 0 .. 99,999 (about 273 years of days)
    SELECT a.n + 10*b.n + 100*c.n + 1000*d.n + 10000*e.n AS i
    FROM digits a CROSS JOIN digits b CROSS JOIN digits c
         CROSS JOIN digits d CROSS JOIN digits e
),
calendar AS (
    SELECT DATEADD(day, dn.i, b.min_d) AS full_date
    FROM day_numbers dn CROSS JOIN bounds b
    WHERE DATEADD(day, dn.i, b.min_d) <= b.max_d
)
SELECT
    CAST(YEAR(full_date) * 10000 + MONTH(full_date) * 100 + DAY(full_date) AS INT) AS date_key,
    full_date,
    -- ISO weekday, independent of DATEFIRST: 1900-01-01 was a Monday.
    CAST((DATEDIFF(day, '19000101', full_date) % 7) + 1 AS TINYINT)                  AS day_of_week,
    CAST(CHOOSE((DATEDIFF(day, '19000101', full_date) % 7) + 1,
        'Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday')
        AS VARCHAR(10))                                                              AS day_name,
    CAST(CASE WHEN (DATEDIFF(day, '19000101', full_date) % 7) + 1 >= 6 THEN 1 ELSE 0 END AS BIT) AS is_weekend,
    CAST(DAY(full_date) AS TINYINT)                                                  AS day_of_month,
    CAST(MONTH(full_date) AS TINYINT)                                                AS month_number,
    CAST(CHOOSE(MONTH(full_date),
        'January','February','March','April','May','June',
        'July','August','September','October','November','December')
        AS VARCHAR(10))                                                              AS month_name,
    CAST(CONVERT(CHAR(7), full_date, 126) AS CHAR(7))                                AS year_month,
    CAST(DATEPART(quarter, full_date) AS TINYINT)                                    AS quarter,
    CAST(YEAR(full_date) AS SMALLINT)                                                AS year
FROM calendar;
GO

SELECT COUNT_BIG(*) AS row_count, MIN(full_date) AS first_day, MAX(full_date) AS last_day
FROM dbo.dim_date;
SELECT TOP 100 * FROM dbo.dim_date ORDER BY date_key;
