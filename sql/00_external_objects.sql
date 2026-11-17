-- 00_external_objects.sql
-- Run FIRST, once per lab session, in Synapse Studio -> Develop -> New SQL script,
-- connected to the BUILT-IN serverless SQL pool.
--
-- ONLY EDIT THE TWO PLACEHOLDERS in the data source below:
--     <container>        e.g. the file system the Ingest wizard wrote to
--     <storage_account>  your lab's linked storage account
-- Both are shown in Synapse Studio -> Data -> Linked. Do not copy them from
-- screenshots or examples; they change every lab session.
--
-- Auth: no credential is created. Serverless reads/writes the lake with the
-- signed-in user's Azure AD identity. That user needs "Storage Blob Data
-- Contributor" on the storage account (CETAS writes files). If CETAS later
-- fails with a permission error, that role is the first thing to check.

-- 1. A user database. External tables cannot live in master.
--    (Run this one statement while connected to "master", then switch the
--     "Use database" box to divvy_dw for everything else.)
-- CREATE DATABASE divvy_dw COLLATE Latin1_General_100_BIN2_UTF8;
-- GO

-- 2. Where the files live. One data source is used for reading the raw files
--    AND for writing CETAS output.
IF NOT EXISTS (SELECT * FROM sys.external_data_sources WHERE name = 'divvy_storage')
    CREATE EXTERNAL DATA SOURCE [divvy_storage]
    WITH (LOCATION = 'abfss://divvy@divvystorage.dfs.core.windows.net');
GO

-- 3. How to read the extracted text files.
--    The Ingest wizard writes comma-separated files. The Divvy data has no
--    commas inside values and no quotes, but STRING_DELIMITER is set anyway
--    so quoted values would still parse.
--    FIRST_ROW = 1 assumes NO header row (the wizard's default).
--    If you ticked "add header to file" in the wizard, change it to 2.
IF NOT EXISTS (SELECT * FROM sys.external_file_formats WHERE name = 'divvy_csv_format')
    CREATE EXTERNAL FILE FORMAT [divvy_csv_format]
    WITH (
        FORMAT_TYPE = DELIMITEDTEXT,
        FORMAT_OPTIONS (
            FIELD_TERMINATOR = ',',
            STRING_DELIMITER = '"',
            FIRST_ROW = 1,
            USE_TYPE_DEFAULT = FALSE,
            PARSER_VERSION = '2.0'
        )
    );
GO

-- 4. How CETAS writes the star-schema tables. Parquet keeps real column types
--    (dates stay dates, decimals stay decimals) and is much smaller than CSV.
--    FALLBACK: if CETAS-to-Parquet is blocked in your lab, replace this with a
--    second DELIMITEDTEXT format and change the name in the 01-05 scripts.
IF NOT EXISTS (SELECT * FROM sys.external_file_formats WHERE name = 'divvy_parquet_format')
    CREATE EXTERNAL FILE FORMAT [divvy_parquet_format]
    WITH (FORMAT_TYPE = PARQUET);
GO

-- 5. Check what exists.
SELECT name, location FROM sys.external_data_sources;
SELECT name, format_type FROM sys.external_file_formats;
