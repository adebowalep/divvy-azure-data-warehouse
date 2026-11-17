-- staging_trip.sql  (LOAD step, source: public.trip)
-- File column order (no header):
--   trip_id, rideable_type, start_at, ended_at, start_station_id, end_station_id, rider_id
-- NOTE: the PostgreSQL column is start_at (the ERD in the overview says started_at).
-- Timestamps are staged as text ('2021-02-12 16:14:56' locally; the Copy activity
-- may add fractional seconds or a 'T'). 04_fact_trip.sql handles both.
-- Station ids stay VARCHAR because some are alphanumeric.

IF OBJECT_ID('dbo.staging_trip') IS NOT NULL
    DROP EXTERNAL TABLE dbo.staging_trip;
GO

CREATE EXTERNAL TABLE dbo.staging_trip (
    trip_id           VARCHAR(50),
    rideable_type     VARCHAR(75),
    started_at        VARCHAR(40),
    ended_at          VARCHAR(40),
    start_station_id  VARCHAR(50),
    end_station_id    VARCHAR(50),
    rider_id          INT
)
WITH (
    LOCATION    = 'public.trip.txt',
    DATA_SOURCE = [divvy_storage],
    FILE_FORMAT = [divvy_csv_format]
);
GO

-- Inspection. Expected row count: 4584921
SELECT COUNT_BIG(*) AS row_count FROM dbo.staging_trip;
SELECT TOP 10 * FROM dbo.staging_trip;
