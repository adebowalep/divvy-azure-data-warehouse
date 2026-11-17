-- staging_payment.sql  (LOAD step, source: public.payment)
-- File column order (no header): payment_id, date, amount, rider_id
--
-- amount was PostgreSQL MONEY. The Copy activity may write it as 9.0, $9.00 or
-- "$1,234.00" depending on settings, so it is staged as text and parsed in
-- 05_fact_payment.sql. Do not stage it as DECIMAL: a "$" would silently become NULL.

IF OBJECT_ID('dbo.staging_payment') IS NOT NULL
    DROP EXTERNAL TABLE dbo.staging_payment;
GO

CREATE EXTERNAL TABLE dbo.staging_payment (
    payment_id    INT,
    payment_date  VARCHAR(30),
    amount        VARCHAR(30),
    rider_id      INT
)
WITH (
    LOCATION    = 'public.payment.txt',
    DATA_SOURCE = [divvy_storage],
    FILE_FORMAT = [divvy_csv_format]
);
GO

-- Inspection. Expected row count: 1946607
SELECT COUNT_BIG(*) AS row_count FROM dbo.staging_payment;
SELECT TOP 10 * FROM dbo.staging_payment;
