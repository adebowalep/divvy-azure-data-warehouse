-- 03_dim_station.sql   (TRANSFORM step, dimension)
-- Grain: one row per station (source: staging_station). Key: station_id (VARCHAR, may be alphanumeric).
-- ONE dimension, TWO roles: fact_trip.start_station_id and fact_trip.end_station_id both point here.
--
-- RE-RUN: change run01 to run02... in LOCATION first (see 01_dim_date.sql).

IF OBJECT_ID('dbo.dim_station') IS NOT NULL
    DROP EXTERNAL TABLE dbo.dim_station;
GO

CREATE EXTERNAL TABLE dbo.dim_station
WITH (
    LOCATION    = 'warehouse/dim_station/run01/',
    DATA_SOURCE = [divvy_storage],
    FILE_FORMAT = [divvy_parquet_format]
)
AS
SELECT
    station_id,
    station_name,
    TRY_CAST(latitude  AS FLOAT) AS latitude,
    TRY_CAST(longitude AS FLOAT) AS longitude
FROM dbo.staging_station;
GO

SELECT COUNT_BIG(*) AS row_count FROM dbo.dim_station;
SELECT TOP 100 * FROM dbo.dim_station ORDER BY station_id;
