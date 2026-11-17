-- staging_rider.sql  (LOAD step, source: public.rider)
-- External table = a schema laid over the file in the lake. No rows are copied
-- into the serverless pool (it has no storage); every query reads the file.
--
-- File column order (no header), from riders.csv / the PostgreSQL table:
--   rider_id, first, last, address, birthday, account_start_date, account_end_date, is_member
-- Dates and the boolean are kept as VARCHAR here and converted in 02_dim_rider.sql.
-- account_end_date is empty for riders whose account is still open.

IF OBJECT_ID('dbo.staging_rider') IS NOT NULL
    DROP EXTERNAL TABLE dbo.staging_rider;
GO

CREATE EXTERNAL TABLE dbo.staging_rider (
    rider_id            INT,
    first_name          VARCHAR(50),
    last_name           VARCHAR(50),
    address             VARCHAR(100),
    birthday            VARCHAR(30),
    account_start_date  VARCHAR(30),
    account_end_date    VARCHAR(30),
    is_member           VARCHAR(10)
)
WITH (
    LOCATION    = 'public.rider.txt',   -- file name written by the Ingest wizard
    DATA_SOURCE = [divvy_storage],
    FILE_FORMAT = [divvy_csv_format]
);
GO

-- Inspection. Expected row count: 75000
SELECT COUNT_BIG(*) AS row_count FROM dbo.staging_rider;
SELECT TOP 10 * FROM dbo.staging_rider;
