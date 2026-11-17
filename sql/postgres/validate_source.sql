-- Validate the four PostgreSQL source tables (run in pgAdmin / psql against
-- the "udacityproject" database AFTER ProjectDataToPostgres.py finishes).
--
-- STATUS: executed in Azure on 14 Nov 2026; results matched the expected values (see evidence/).
-- "Expected" numbers come from profiling the local CSV files (Datasets) with Python.

-- 1. Row counts.
-- Expected: rider 75000, payment 1946607, station 838, trip 4584921
SELECT 'rider'   AS tbl, COUNT(*) AS row_count FROM rider
UNION ALL SELECT 'payment', COUNT(*) FROM payment
UNION ALL SELECT 'station', COUNT(*) FROM station
UNION ALL SELECT 'trip',    COUNT(*) FROM trip;

-- 2. Column types as created (confirms station_id is text and amount is money).
SELECT table_name, column_name, data_type
FROM information_schema.columns
WHERE table_schema = 'public'
ORDER BY table_name, ordinal_position;

-- 3. Sample values.
SELECT * FROM rider   LIMIT 5;
SELECT * FROM payment LIMIT 5;
SELECT * FROM station LIMIT 5;
SELECT * FROM trip    LIMIT 5;

-- 4. Duplicate / null checks. Expected: every count is 0 except
-- rider.account_end_date nulls (expected 60046 = riders with an open account).
SELECT
  (SELECT COUNT(*) - COUNT(DISTINCT rider_id)   FROM rider)   AS dup_rider_id,
  (SELECT COUNT(*) - COUNT(DISTINCT payment_id) FROM payment) AS dup_payment_id,
  (SELECT COUNT(*) - COUNT(DISTINCT station_id) FROM station) AS dup_station_id,
  (SELECT COUNT(*) - COUNT(DISTINCT trip_id)    FROM trip)    AS dup_trip_id,
  (SELECT COUNT(*) FROM rider WHERE account_end_date IS NULL) AS open_accounts;

-- 5. Foreign-key match rates (expected: all four are 0 orphans).
SELECT
  (SELECT COUNT(*) FROM trip t LEFT JOIN station s ON s.station_id = t.start_station_id WHERE s.station_id IS NULL) AS orphan_start_station,
  (SELECT COUNT(*) FROM trip t LEFT JOIN station s ON s.station_id = t.end_station_id   WHERE s.station_id IS NULL) AS orphan_end_station,
  (SELECT COUNT(*) FROM trip t    LEFT JOIN rider r ON r.rider_id = t.rider_id WHERE r.rider_id IS NULL) AS orphan_trip_rider,
  (SELECT COUNT(*) FROM payment p LEFT JOIN rider r ON r.rider_id = p.rider_id WHERE r.rider_id IS NULL) AS orphan_payment_rider;

-- 6. Timestamp anomalies.
-- Expected from local profile: negative 116, zero 81, over 24h 1277
SELECT
  COUNT(*) FILTER (WHERE ended_at <  start_at) AS negative_duration,
  COUNT(*) FILTER (WHERE ended_at =  start_at) AS zero_duration,
  COUNT(*) FILTER (WHERE ended_at - start_at > INTERVAL '24 hours') AS over_24h,
  MIN(start_at) AS first_trip, MAX(start_at) AS last_trip
FROM trip;
-- Expected first_trip 2021-02-01 01:07:04, last_trip 2022-01-31 23:58:37

-- 7. Account-date anomalies. Expected: 1033 riders end before they start.
SELECT COUNT(*) AS account_end_before_start
FROM rider WHERE account_end_date < account_start_date;

-- 8. Payment amount range (MONEY). Expected min $3.00, max $25.00.
SELECT MIN(amount) AS min_amount, MAX(amount) AS max_amount, SUM(amount) AS total_amount
FROM payment;
-- Expected total: $19,457,105.25 (local CSV sum 19457105.24999999)
