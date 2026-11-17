-- 07_business_queries.sql
-- Answers the business questions from the star schema. Run after 01-05.
-- STATUS: executed in Azure on 14 Nov 2026 (Q1a, Q1b, Q1d, Q1e, Q2 yearly, Q3, Q4, Q5), results cross-checked locally.
--
-- Reading rules used by every ride-duration query:
--   * f.is_valid_duration = 1 drops negative, zero and over-24h rides (1,474 of 4.58M rows).
--   * Member / casual comes from dim_rider.is_member, the CURRENT flag. A rider who is a member
--     today may have been casual on the ride date; the source cannot tell.
--   * Trip duration (minutes on a bike) and payment amount (money) are separate measures.
--     No payment is ever matched to a single ride.

-- ===== Q1a. Ride duration by day of week and time of day =================================
-- Measures: average ride length and ride count per weekday x time band (time = ride START).
-- Caveat: an average can be pulled up by a few very long rides (capped here at 24 h).
SELECT d.day_of_week, d.day_name, f.time_band,
       COUNT(*) AS rides, AVG(f.ride_duration_minutes) AS avg_minutes
FROM dbo.fact_trip f
JOIN dbo.dim_date d ON d.date_key = f.start_date_key
WHERE f.is_valid_duration = 1
GROUP BY d.day_of_week, d.day_name, f.time_band
ORDER BY d.day_of_week, f.time_band;

-- ===== Q1b. Ride duration by START station (top 25 longest, stations with >= 100 rides) =====
-- Measures: where long rides begin. The ride-count floor stops tiny stations from topping the list.
SELECT TOP 25
    s.station_id, s.station_name, COUNT(*) AS rides, AVG(f.ride_duration_minutes) AS avg_minutes
FROM dbo.fact_trip f
JOIN dbo.dim_station s ON s.station_id = f.start_station_id
WHERE f.is_valid_duration = 1
GROUP BY s.station_id, s.station_name
HAVING COUNT(*) >= 100
ORDER BY avg_minutes DESC;

-- ===== Q1c. Ride duration by END station (same shape; same dim_station, second role) =========
SELECT TOP 25
    s.station_id, s.station_name, COUNT(*) AS rides, AVG(f.ride_duration_minutes) AS avg_minutes
FROM dbo.fact_trip f
JOIN dbo.dim_station s ON s.station_id = f.end_station_id
WHERE f.is_valid_duration = 1
GROUP BY s.station_id, s.station_name
HAVING COUNT(*) >= 100
ORDER BY avg_minutes DESC;

-- ===== Q1d. Ride duration by rider age at the time of the ride ===============================
-- Age bands use rider_age_at_trip (age on the ride date, not today).
SELECT
    CASE WHEN rider_age_at_trip < 18 THEN '1: under 18'
         WHEN rider_age_at_trip < 25 THEN '2: 18-24'
         WHEN rider_age_at_trip < 35 THEN '3: 25-34'
         WHEN rider_age_at_trip < 45 THEN '4: 35-44'
         WHEN rider_age_at_trip < 55 THEN '5: 45-54'
         WHEN rider_age_at_trip < 65 THEN '6: 55-64'
         WHEN rider_age_at_trip IS NULL THEN '9: unknown'
         ELSE '7: 65+' END AS age_band,
    COUNT(*) AS rides, AVG(ride_duration_minutes) AS avg_minutes
FROM dbo.fact_trip
WHERE is_valid_duration = 1
GROUP BY CASE WHEN rider_age_at_trip < 18 THEN '1: under 18'
              WHEN rider_age_at_trip < 25 THEN '2: 18-24'
              WHEN rider_age_at_trip < 35 THEN '3: 25-34'
              WHEN rider_age_at_trip < 45 THEN '4: 35-44'
              WHEN rider_age_at_trip < 55 THEN '5: 45-54'
              WHEN rider_age_at_trip < 65 THEN '6: 55-64'
              WHEN rider_age_at_trip IS NULL THEN '9: unknown'
              ELSE '7: 65+' END
ORDER BY age_band;

-- ===== Q1e. Ride duration: member vs casual (current flag, see caveat above) =================
SELECT CASE r.is_member WHEN 1 THEN 'member' WHEN 0 THEN 'casual' ELSE 'unknown' END AS rider_type,
       COUNT(*) AS rides, AVG(f.ride_duration_minutes) AS avg_minutes
FROM dbo.fact_trip f
LEFT JOIN dbo.dim_rider r ON r.rider_id = f.rider_id
WHERE f.is_valid_duration = 1
GROUP BY r.is_member
ORDER BY rider_type;

-- ===== Q2. Money spent by year, quarter and month ==============================================
-- Measures: total payments and payment count by period. Uses fact_payment + dim_date only.
SELECT d.year, d.quarter, d.month_number, d.month_name,
       COUNT(*) AS payments, SUM(p.amount) AS total_spent
FROM dbo.fact_payment p
JOIN dbo.dim_date d ON d.date_key = p.payment_date_key
GROUP BY d.year, d.quarter, d.month_number, d.month_name
ORDER BY d.year, d.month_number;
-- Roll-ups (same table, coarser grain)
SELECT d.year, d.quarter, SUM(p.amount) AS total_spent FROM dbo.fact_payment p
JOIN dbo.dim_date d ON d.date_key = p.payment_date_key GROUP BY d.year, d.quarter ORDER BY d.year, d.quarter;
SELECT d.year, SUM(p.amount) AS total_spent FROM dbo.fact_payment p
JOIN dbo.dim_date d ON d.date_key = p.payment_date_key GROUP BY d.year ORDER BY d.year;
-- Caveat: the source holds one payment per rider on the 1st of each month, so "month" is
-- the billing month. 2022 only contains January (data ends 2022-02-01).

-- ===== Q3. Money spent per rider, by age at account start =======================================
-- Step 1 sums each rider's payments (one row per rider), step 2 averages those by age band, so a
-- long-lived rider is not counted once per payment.
WITH rider_spend AS (
    SELECT rider_id, SUM(amount) AS total_spent
    FROM dbo.fact_payment GROUP BY rider_id
)
SELECT
    CASE WHEN r.age_at_account_start < 18 THEN '1: under 18'
         WHEN r.age_at_account_start < 25 THEN '2: 18-24'
         WHEN r.age_at_account_start < 35 THEN '3: 25-34'
         WHEN r.age_at_account_start < 45 THEN '4: 35-44'
         WHEN r.age_at_account_start < 55 THEN '5: 45-54'
         WHEN r.age_at_account_start < 65 THEN '6: 55-64'
         WHEN r.age_at_account_start IS NULL THEN '9: unknown'
         ELSE '7: 65+' END AS age_at_account_start_band,
    CASE r.is_member WHEN 1 THEN 'member' WHEN 0 THEN 'casual' ELSE 'unknown' END AS rider_type,
    COUNT(*)                AS riders,
    SUM(s.total_spent)      AS total_spent,
    AVG(s.total_spent)      AS avg_spent_per_rider
FROM rider_spend s
JOIN dbo.dim_rider r ON r.rider_id = s.rider_id
GROUP BY CASE WHEN r.age_at_account_start < 18 THEN '1: under 18'
              WHEN r.age_at_account_start < 25 THEN '2: 18-24'
              WHEN r.age_at_account_start < 35 THEN '3: 25-34'
              WHEN r.age_at_account_start < 45 THEN '4: 35-44'
              WHEN r.age_at_account_start < 55 THEN '5: 45-54'
              WHEN r.age_at_account_start < 65 THEN '6: 55-64'
              WHEN r.age_at_account_start IS NULL THEN '9: unknown'
              ELSE '7: 65+' END,
         r.is_member
ORDER BY age_at_account_start_band, rider_type;
-- Caveat: spend is lifetime-to-date and riders joined in different years, so riders with
-- older accounts have had more months to pay. Compare avg_spent_per_rider with that in mind.

-- ===== EXTRA CREDIT: rider-month grain ==============================================================
-- Rides and payments are each summed to ONE row per (rider_id, year_month) first, then joined on
-- that key. Rows never multiply, and no payment is tied to a ride.
-- Window: only months that have trips (the data gives 2021-02 .. 2022-01); payments exist for other years too.
-- FULL JOIN keeps a month where a rider paid but did not ride (0 rides) or rode without a payment.
-- Timing caveat: a payment is dated the 1st of its month; rides happen any day in the same month.

-- Shared building block (repeat in Q4 and Q5 below; serverless has no temp tables)
--   rides_m : rider_id, year_month, rides, ride_minutes   from fact_trip (valid durations only)
--   spend_m : rider_id, year_month, spend                  from fact_payment

-- ===== Q4. Money spent per rider-month by average rides per month ====================================
WITH rides_m AS (
    SELECT f.rider_id, d.year_month, COUNT(*) AS rides, SUM(f.ride_duration_minutes) AS ride_minutes
    FROM dbo.fact_trip f JOIN dbo.dim_date d ON d.date_key = f.start_date_key
    WHERE f.is_valid_duration = 1
    GROUP BY f.rider_id, d.year_month
),
spend_m AS (
    SELECT p.rider_id, d.year_month, SUM(p.amount) AS spend
    FROM dbo.fact_payment p JOIN dbo.dim_date d ON d.date_key = p.payment_date_key
    WHERE d.year_month BETWEEN (SELECT MIN(year_month) FROM rides_m) AND (SELECT MAX(year_month) FROM rides_m)
    GROUP BY p.rider_id, d.year_month
),
rider_month AS (
    SELECT COALESCE(r.rider_id, s.rider_id) AS rider_id,
           COALESCE(r.year_month, s.year_month) AS year_month,
           COALESCE(r.rides, 0) AS rides, COALESCE(r.ride_minutes, 0) AS ride_minutes,
           COALESCE(s.spend, 0) AS spend
    FROM rides_m r FULL OUTER JOIN spend_m s ON s.rider_id = r.rider_id AND s.year_month = r.year_month
),
per_rider AS (   -- one row per rider: their average month in the window
    SELECT rider_id, COUNT(*) AS active_months,
           AVG(CAST(rides AS FLOAT)) AS avg_rides_per_month,
           AVG(spend)                AS avg_spend_per_month
    FROM rider_month GROUP BY rider_id
)
SELECT
    CASE WHEN avg_rides_per_month < 1  THEN '1: under 1'
         WHEN avg_rides_per_month < 3  THEN '2: 1-2.99'
         WHEN avg_rides_per_month < 6  THEN '3: 3-5.99'
         WHEN avg_rides_per_month < 11 THEN '4: 6-10.99'
         ELSE '5: 11+' END AS avg_rides_per_month_band,
    COUNT(*) AS riders, AVG(avg_spend_per_month) AS avg_spend_per_month
FROM per_rider
GROUP BY CASE WHEN avg_rides_per_month < 1  THEN '1: under 1'
              WHEN avg_rides_per_month < 3  THEN '2: 1-2.99'
              WHEN avg_rides_per_month < 6  THEN '3: 3-5.99'
              WHEN avg_rides_per_month < 11 THEN '4: 6-10.99'
              ELSE '5: 11+' END
ORDER BY avg_rides_per_month_band;
-- Reads as: "riders who ride about X times a month pay about $Y a month". Averages are over the
-- months a rider was active (rode or paid), so a rider with no activity in a month is not counted.

-- ===== Q5. Money spent per rider-month by minutes ridden per month =====================================
WITH rides_m AS (
    SELECT f.rider_id, d.year_month, COUNT(*) AS rides, SUM(f.ride_duration_minutes) AS ride_minutes
    FROM dbo.fact_trip f JOIN dbo.dim_date d ON d.date_key = f.start_date_key
    WHERE f.is_valid_duration = 1
    GROUP BY f.rider_id, d.year_month
),
spend_m AS (
    SELECT p.rider_id, d.year_month, SUM(p.amount) AS spend
    FROM dbo.fact_payment p JOIN dbo.dim_date d ON d.date_key = p.payment_date_key
    WHERE d.year_month BETWEEN (SELECT MIN(year_month) FROM rides_m) AND (SELECT MAX(year_month) FROM rides_m)
    GROUP BY p.rider_id, d.year_month
),
rider_month AS (
    SELECT COALESCE(r.rider_id, s.rider_id) AS rider_id,
           COALESCE(r.year_month, s.year_month) AS year_month,
           COALESCE(r.ride_minutes, 0) AS ride_minutes, COALESCE(s.spend, 0) AS spend
    FROM rides_m r FULL OUTER JOIN spend_m s ON s.rider_id = r.rider_id AND s.year_month = r.year_month
)
SELECT
    CASE WHEN ride_minutes = 0   THEN '1: no riding'
         WHEN ride_minutes < 30  THEN '2: under 30 min'
         WHEN ride_minutes < 60  THEN '3: 30-59 min'
         WHEN ride_minutes < 120 THEN '4: 60-119 min'
         ELSE '5: 120+ min' END AS minutes_ridden_in_month_band,
    COUNT(*) AS rider_months, AVG(spend) AS avg_spend_in_month
FROM rider_month
GROUP BY CASE WHEN ride_minutes = 0   THEN '1: no riding'
              WHEN ride_minutes < 30  THEN '2: under 30 min'
              WHEN ride_minutes < 60  THEN '3: 30-59 min'
              WHEN ride_minutes < 120 THEN '4: 60-119 min'
              ELSE '5: 120+ min' END
ORDER BY minutes_ridden_in_month_band;
-- Reads as: "in months where a rider spent N minutes on a bike, they paid about $Y". It shows
-- association only; it does not say a particular payment bought particular rides.
