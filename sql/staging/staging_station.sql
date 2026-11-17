-- staging_station.sql  (LOAD step, source: public.station)
-- File column order (no header): station_id, name, latitude, longitude
--
-- station_id is TEXT. Values like 'KA1503000012' and 'TA1305000029' exist next
-- to numeric-looking ones such as '525', so it must never be cast to INT.
-- Latitude/longitude are staged as text (values like -87.66605799999999)
-- and converted in 03_dim_station.sql.

IF OBJECT_ID('dbo.staging_station') IS NOT NULL
    DROP EXTERNAL TABLE dbo.staging_station;
GO

CREATE EXTERNAL TABLE dbo.staging_station (
    station_id    VARCHAR(50),
    station_name  VARCHAR(75),
    latitude      VARCHAR(40),
    longitude     VARCHAR(40)
)
WITH (
    LOCATION    = 'public.station.txt',
    DATA_SOURCE = [divvy_storage],
    FILE_FORMAT = [divvy_csv_format]
);
GO

-- Inspection. Expected row count: 838
SELECT COUNT_BIG(*) AS row_count FROM dbo.staging_station;
SELECT TOP 10 * FROM dbo.staging_station;
