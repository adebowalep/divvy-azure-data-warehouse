# Loading the source data into PostgreSQL

The load script is Udacity's starter script (`ProjectDataToPostgres.py`). It is licensed CC BY-NC-ND, so a modified copy is **not** published in this repo. Get the original from Udacity's project repository (Azure-Data-Warehouse-Project, folder `starter`) and the data files from the course resources.

The table definitions are in `../sql/postgres/create_tables.sql`.

Three changes were made to the script for the run documented in `evidence/00_*`:
1. Connection settings (`PGHOST`, `PGUSER`, `PGPASSWORD`) are read from environment variables instead of being typed into the file.
2. It no longer drops the `udacityproject` database without asking: it stops if the database exists, unless `DIVVY_ALLOW_RESET=yes`.
3. If a `COPY` fails, it stops with an error and rolls back, instead of printing "Finished populating" anyway. It also prints the row count of each loaded table.

Then run the source checks in `../sql/postgres/validate_source.sql`.
