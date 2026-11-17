"""Single source of truth for the star schema. The diagram and the local SQL check both read this."""

# (key_type, column, sql_type)  key_type: "PK", "FK" or ""
TABLES = {
    "fact_trip": [
        ("PK", "trip_id", "VARCHAR(50)"),
        ("FK", "rider_id", "INT"),
        ("FK", "start_station_id", "VARCHAR(50)"),
        ("FK", "end_station_id", "VARCHAR(50)"),
        ("FK", "start_date_key", "INT"),
        ("FK", "end_date_key", "INT"),
        ("", "rideable_type", "VARCHAR(75)"),
        ("", "started_at", "DATETIME2(0)"),
        ("", "ended_at", "DATETIME2(0)"),
        ("", "start_hour", "TINYINT"),
        ("", "time_band", "VARCHAR(20)"),
        ("", "ride_duration_minutes", "DECIMAL(12,4)"),
        ("", "rider_age_at_trip", "INT"),
        ("", "is_valid_duration", "BIT"),
        ("", "duration_issue", "VARCHAR(20)"),
    ],
    "fact_payment": [
        ("PK", "payment_id", "INT"),
        ("FK", "rider_id", "INT"),
        ("FK", "payment_date_key", "INT"),
        ("", "payment_date", "DATE"),
        ("", "amount", "DECIMAL(18,2)"),
    ],
    "dim_rider": [
        ("PK", "rider_id", "INT"),
        ("", "first_name", "VARCHAR(50)"),
        ("", "last_name", "VARCHAR(50)"),
        ("", "birthday", "DATE"),
        ("", "account_start_date", "DATE"),
        ("", "account_end_date", "DATE"),
        ("", "is_member", "BIT"),
        ("", "age_at_account_start", "INT"),
        ("", "is_account_period_valid", "BIT"),
    ],
    "dim_station": [
        ("PK", "station_id", "VARCHAR(50)"),
        ("", "station_name", "VARCHAR(75)"),
        ("", "latitude", "FLOAT"),
        ("", "longitude", "FLOAT"),
    ],
    "dim_date": [
        ("PK", "date_key", "INT"),
        ("", "full_date", "DATE"),
        ("", "day_of_week", "TINYINT"),
        ("", "day_name", "VARCHAR(10)"),
        ("", "is_weekend", "BIT"),
        ("", "day_of_month", "TINYINT"),
        ("", "month_number", "TINYINT"),
        ("", "month_name", "VARCHAR(10)"),
        ("", "year_month", "CHAR(7)"),
        ("", "quarter", "TINYINT"),
        ("", "year", "SMALLINT"),
    ],
}

# (fact, fact_column, dimension, dimension_column, label)
RELATIONSHIPS = [
    ("fact_trip", "rider_id", "dim_rider", "rider_id", ""),
    ("fact_trip", "start_station_id", "dim_station", "station_id", "start station (role 1)"),
    ("fact_trip", "end_station_id", "dim_station", "station_id", "end station (role 2)"),
    ("fact_trip", "start_date_key", "dim_date", "date_key", "start date"),
    ("fact_trip", "end_date_key", "dim_date", "date_key", "end date"),
    ("fact_payment", "rider_id", "dim_rider", "rider_id", ""),
    ("fact_payment", "payment_date_key", "dim_date", "date_key", "payment date"),
]

GRAIN = {
    "fact_trip": "Grain: one row per trip",
    "fact_payment": "Grain: one row per payment",
    "dim_rider": "One row per rider",
    "dim_station": "One row per station",
    "dim_date": "One row per calendar day",
}
