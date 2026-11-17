-- 05_fact_payment.sql   (TRANSFORM step, fact)
-- Grain: ONE ROW PER PAYMENT (payment_id). All 1,946,607 source payments are kept.
--
-- Measure : amount (DECIMAL(18,2)).
-- Keys    : rider_id -> dim_rider, payment_date_key -> dim_date.
-- Age at account start is NOT repeated here. Get it from dim_rider.age_at_account_start
-- (rider_id is unique there, so the join adds no rows).
--
-- Payments are NOT linked to trips. The source has no trip_id on a payment, so this
-- table must never be joined to fact_trip row-by-row (that would repeat each amount
-- once per ride). Combine them only after both are summed to the same grain.
--
-- Amount parsing: strips $ and thousands commas, and treats (12.00) as -12.00 in case the
-- MONEY export used accounting style. If a value still cannot be parsed, amount is NULL
-- and 06_validation.sql counts it, so nothing fails silently.
--
-- RE-RUN: change run01 to run02... in LOCATION first (see 01_dim_date.sql).

IF OBJECT_ID('dbo.fact_payment') IS NOT NULL
    DROP EXTERNAL TABLE dbo.fact_payment;
GO

CREATE EXTERNAL TABLE dbo.fact_payment
WITH (
    LOCATION    = 'warehouse/fact_payment/run01/',
    DATA_SOURCE = [divvy_storage],
    FILE_FORMAT = [divvy_parquet_format]
)
AS
WITH pay AS (
    SELECT
        payment_id,
        rider_id,
        TRY_CONVERT(date, LEFT(payment_date, 10)) AS payment_date,
        TRY_CAST(
            REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(LTRIM(RTRIM(amount)), '$', ''), ',', ''), '"', ''), '(', '-'), ')', '')
            AS DECIMAL(18, 2)) AS amount
    FROM dbo.staging_payment
)
SELECT
    payment_id,
    rider_id,
    CAST(YEAR(payment_date) * 10000 + MONTH(payment_date) * 100 + DAY(payment_date) AS INT) AS payment_date_key,
    payment_date,
    amount
FROM pay;
GO

SELECT COUNT_BIG(*) AS row_count, SUM(amount) AS total_amount FROM dbo.fact_payment;
SELECT TOP 100 * FROM dbo.fact_payment;
