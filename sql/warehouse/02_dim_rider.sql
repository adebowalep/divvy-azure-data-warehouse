-- 02_dim_rider.sql   (TRANSFORM step, dimension)
-- Grain: one row per rider (source: staging_rider). Key: rider_id (the stable source id).
-- Used by: fact_trip.rider_id and fact_payment.rider_id.
--
-- Source limitation: is_member is the rider's CURRENT flag. The source has no
-- membership history, so it cannot say whether a rider was a member on a past trip.
-- address is left out on purpose: no business question needs it.
--
-- Age rule: whole years between birthday and the reference date, minus 1 if the
-- birthday has not happened yet that year. (DATEDIFF(year) alone is wrong: it only
-- counts calendar-year boundaries.) NULL when either date is missing/invalid.
--
-- RE-RUN: change run01 to run02... in LOCATION first (see 01_dim_date.sql).

IF OBJECT_ID('dbo.dim_rider') IS NOT NULL
    DROP EXTERNAL TABLE dbo.dim_rider;
GO

CREATE EXTERNAL TABLE dbo.dim_rider
WITH (
    LOCATION    = 'warehouse/dim_rider/run01/',
    DATA_SOURCE = [divvy_storage],
    FILE_FORMAT = [divvy_parquet_format]
)
AS
WITH parsed AS (
    SELECT
        rider_id,
        first_name,
        last_name,
        TRY_CONVERT(date, LEFT(birthday, 10))                       AS birthday,
        TRY_CONVERT(date, LEFT(account_start_date, 10))             AS account_start_date,
        TRY_CONVERT(date, LEFT(NULLIF(account_end_date, ''), 10))   AS account_end_date,
        CASE WHEN LOWER(is_member) IN ('true', 't', '1') THEN CAST(1 AS BIT)
             WHEN LOWER(is_member) IN ('false', 'f', '0') THEN CAST(0 AS BIT)
             ELSE NULL END                                          AS is_member
    FROM dbo.staging_rider
)
SELECT
    rider_id,
    first_name,
    last_name,
    birthday,
    account_start_date,
    account_end_date,
    is_member,
    CAST(CASE
        WHEN birthday IS NULL OR account_start_date IS NULL OR account_start_date < birthday THEN NULL
        ELSE DATEDIFF(year, birthday, account_start_date)
             - CASE WHEN DATEADD(year, DATEDIFF(year, birthday, account_start_date), birthday) > account_start_date
                    THEN 1 ELSE 0 END
    END AS INT)                                                     AS age_at_account_start,
    -- Data-quality flag: 1,033 riders in the source have an end date before their start date.
    CAST(CASE WHEN account_end_date IS NOT NULL AND account_end_date < account_start_date
              THEN 0 ELSE 1 END AS BIT)                             AS is_account_period_valid
FROM parsed;
GO

SELECT COUNT_BIG(*) AS row_count FROM dbo.dim_rider;
SELECT TOP 100 * FROM dbo.dim_rider ORDER BY rider_id;
