-- 04_fact_trip.sql   (TRANSFORM step, fact)
-- Grain: ONE ROW PER TRIP (trip_id). All 4,584,921 source trips are kept.
--
-- Measures : ride_duration_minutes (fractional), rider_age_at_trip.
-- Keys     : rider_id -> dim_rider, start/end_station_id -> dim_station (two roles),
--            start_date_key / end_date_key -> dim_date.
--
-- Choices:
--  * Duration = seconds / 60.0, so 6m47s = 6.7833 minutes (not rounded to whole minutes).
--  * Bad durations are KEPT but flagged, never silently dropped:
--      duration_issue = 'negative' (end before start), 'zero', 'over_24h', 'missing' or 'ok'.
--      is_valid_duration = 1 only for 0 < duration <= 24h. Reports filter on it.
--  * The only join is to dim_rider on its unique key (rider_id), so it cannot multiply rows.
--    It is a LEFT JOIN: a trip with an unknown rider stays, with NULL age.
--  * Station ids are copied as-is (no join), so an unknown station is not lost; the
--    06_validation.sql checks look for ids missing from dim_station.
--  * Time zone: the source does not state one. Times are used exactly as stored
--    (assumed Chicago local time) and are NOT converted.
--  * Membership is NOT stored here: dim_rider.is_member is current-only (see 02_dim_rider.sql).
--
-- RE-RUN: change run01 to run02... in LOCATION first (see 01_dim_date.sql).
-- Needs dim_rider (02) to exist. dim_date (01) and dim_station (03) are joined at query time.

IF OBJECT_ID('dbo.fact_trip') IS NOT NULL
    DROP EXTERNAL TABLE dbo.fact_trip;
GO

CREATE EXTERNAL TABLE dbo.fact_trip
WITH (
    LOCATION    = 'warehouse/fact_trip/run01/',
    DATA_SOURCE = [divvy_storage],
    FILE_FORMAT = [divvy_parquet_format]
)
AS
WITH trip AS (
    SELECT
        trip_id,
        rideable_type,
        TRY_CONVERT(datetime2(0), LEFT(REPLACE(started_at, 'T', ' '), 19)) AS started_at,
        TRY_CONVERT(datetime2(0), LEFT(REPLACE(ended_at,   'T', ' '), 19)) AS ended_at,
        NULLIF(start_station_id, '') AS start_station_id,
        NULLIF(end_station_id,   '') AS end_station_id,
        rider_id
    FROM dbo.staging_trip
),
calc AS (
    SELECT
        t.*,
        DATEDIFF(second, t.started_at, t.ended_at) AS duration_seconds,
        r.birthday
    FROM trip t
    LEFT JOIN dbo.dim_rider r ON r.rider_id = t.rider_id
)
SELECT
    trip_id,
    rider_id,
    start_station_id,
    end_station_id,
    CAST(YEAR(started_at) * 10000 + MONTH(started_at) * 100 + DAY(started_at) AS INT) AS start_date_key,
    CAST(YEAR(ended_at)   * 10000 + MONTH(ended_at)   * 100 + DAY(ended_at)   AS INT) AS end_date_key,
    rideable_type,
    started_at,
    ended_at,
    CAST(DATEPART(hour, started_at) AS TINYINT) AS start_hour,
    CAST(CASE
        WHEN started_at IS NULL            THEN NULL
        WHEN DATEPART(hour, started_at) < 6  THEN 'Night 00-05'
        WHEN DATEPART(hour, started_at) < 10 THEN 'Morning 06-09'
        WHEN DATEPART(hour, started_at) < 16 THEN 'Midday 10-15'
        WHEN DATEPART(hour, started_at) < 20 THEN 'PM rush 16-19'
        ELSE 'Evening 20-23' END AS VARCHAR(20)) AS time_band,
    CAST(duration_seconds / 60.0 AS DECIMAL(12, 4)) AS ride_duration_minutes,
    -- age on the day the ride started; same birthday rule as dim_rider
    CAST(CASE
        WHEN birthday IS NULL OR started_at IS NULL OR CAST(started_at AS date) < birthday THEN NULL
        ELSE DATEDIFF(year, birthday, CAST(started_at AS date))
             - CASE WHEN DATEADD(year, DATEDIFF(year, birthday, CAST(started_at AS date)), birthday) > CAST(started_at AS date)
                    THEN 1 ELSE 0 END
    END AS INT) AS rider_age_at_trip,
    CAST(CASE WHEN duration_seconds > 0 AND duration_seconds <= 86400 THEN 1 ELSE 0 END AS BIT) AS is_valid_duration,
    CAST(CASE
        WHEN duration_seconds IS NULL   THEN 'missing'
        WHEN duration_seconds < 0       THEN 'negative'
        WHEN duration_seconds = 0       THEN 'zero'
        WHEN duration_seconds > 86400   THEN 'over_24h'
        ELSE 'ok' END AS VARCHAR(20)) AS duration_issue
FROM calc;
GO

SELECT COUNT_BIG(*) AS row_count FROM dbo.fact_trip;
SELECT TOP 100 * FROM dbo.fact_trip;
