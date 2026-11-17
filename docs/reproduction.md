# Reproducing the project

There are three separate things you might want to reproduce, from easiest to hardest:

1. **View or rebuild the dashboard.** Works from a fresh clone, no Azure needed.
2. **Rebuild the dashboard data.** Needs the four source CSV files, which are not in this repository.
3. **Rebuild the Azure warehouse.** Needs an Azure subscription and the same CSV files. There is no one-click deployment.

## 1. The dashboard (no data files needed)

Open [dashboard/index.html](../dashboard/index.html) in any browser, or use the published copy: https://adebowalep.github.io/divvy-azure-data-warehouse/dashboard/. It is one static file with the data embedded. It does not connect to Azure. It loads three web fonts from Google Fonts and falls back to system fonts if they cannot load.

To rebuild `index.html` from the template and the committed `data.json`:

```bash
python3 dashboard/make_dashboard.py
```

The scripts find their own files, so they work from the repository root or from any other folder.

## 2. Rebuilding `data.json` from the source files

The four files are `riders.csv`, `payments.csv`, `stations.csv` and `trips.csv` (no header row). They come from the Udacity course resources and are not stored here: they are about 480 MB, and they belong to the course. Without them the committed dashboard stays viewable, but `data.json` cannot be regenerated.

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python dashboard/build_data.py /path/to/folder-with-the-four-csvs
python dashboard/make_dashboard.py
python tests/check_project.py
```

`build_data.py` stops with a clear message if a file is missing and writes `dashboard/data.json` next to the script. With the original files the output is byte-identical to the committed `data.json`.

Optional tools (`pip install -r requirements-dev.txt`, which needs a Chromium-based browser; set `DIVVY_BROWSER` to its path if Playwright cannot find one):

```bash
python tests/smoke_dashboard.py              # browser tests of the dashboard
python dashboard/capture_screenshots.py      # regenerates docs/images/dashboard-*.png
python diagram/make_architecture.py          # regenerates docs/architecture.drawio and the SVG/PNG
python diagram/make_star_schema_pdf.py       # regenerates diagram/star_schema.pdf and .png
```

## 3. The Azure warehouse

### Services

| Service | Setting used in the recorded run |
|---|---|
| Azure Database for PostgreSQL (flexible server) | Burstable B2s, 32 GiB, public access with a firewall rule for the client and "allow Azure services", TLS required |
| Azure Synapse Analytics workspace | new Data Lake Storage Gen2 account and file system, Microsoft Entra authentication only, managed virtual network off |
| Synapse built-in serverless SQL pool | a user database `divvy_dw` created with `COLLATE Latin1_General_100_BIN2_UTF8` |

The person running the SQL needs a write role on the storage account (`Storage Blob Data Contributor` or `Owner`), because CETAS writes files. No passwords or keys are stored in any script. The loader reads the database login from environment variables.

### Cost

The recorded run used a Udacity cloud lab, which paid for the resources. Outside a lab you pay for the PostgreSQL server for as long as it exists and for storage. At the time, the Azure portal estimated about $58 a month for the server I configured, and serverless SQL is billed per terabyte of data scanned (about $5 per TB in the portal estimate). Prices change, so check them, and delete the resources when you finish.

### Steps

1. **Source tables.** Create the four tables with [sql/postgres/create_tables.sql](../sql/postgres/create_tables.sql) and load the CSV files. I used Udacity's starter script ([starter/README.md](../starter/README.md) says where to find it and what I changed). Run [validate_source.sql](../sql/postgres/validate_source.sql); expect 75,000 / 1,946,607 / 838 / 4,584,921 rows and no duplicates or orphans.
2. **Extract.** In Synapse Studio use Ingest, built-in copy task, run once. Source: the PostgreSQL tables `public.rider`, `public.trip`, `public.payment`, `public.station` (SSL mode Require). Destination: the workspace storage, folder path equal to the container name, so the files sit at the container root. Format: delimited text, comma, **header row off**, suffix `.txt`. Result: `public.rider.txt` and the three others.
3. **Connect storage to SQL.** In a script connected to the built-in pool and database `divvy_dw`, edit the two placeholders in [sql/00_external_objects.sql](../sql/00_external_objects.sql) (container and storage account) and run it. It creates the data source `divvy_storage`, a CSV file format and a Parquet file format.
4. **Load.** Run the four scripts in [sql/staging/](../sql/staging/). Each ends with a row count; they should equal the source counts.
5. **Transform.** Run [sql/warehouse/01 to 05](../sql/warehouse/) in order (dimensions before facts). Each CETAS writes to `warehouse/<table>/run01/`. **To run a script again, change `run01` to `run02` in all five.** Dropping an external table does not delete its files, and reusing a folder mixes old and new output.
6. **Check.** Run [06_validation_summary.sql](../sql/warehouse/06_validation_summary.sql). All 26 rows should say PASS. Then run [07_business_queries.sql](../sql/warehouse/07_business_queries.sql).
7. **Clean up.** Delete the PostgreSQL server, the Synapse workspace and its storage account when you no longer need them. The recorded run did this; the proof is in [evidence/08_cleanup_empty_resource_group.png](../evidence/08_cleanup_empty_resource_group.png).

If the copy tool cannot write to storage because the workspace identity has no role, create a second linked service to the storage account that uses the account key and select it as the destination. That is what the recorded run needed.

### Lab limitations

The Udacity lab environment is temporary, has a limited number of sessions and removes its resources when the session ends. That is why the pipeline cannot be re-run from this repository today, and why the evidence is screenshots and exported results. The lab only allowed the built-in serverless pool, which is the reason for external tables and CETAS instead of dedicated-pool tables.

### Publishing the dashboard

GitHub Pages serves the repository from the `main` branch, root folder. [.nojekyll](../.nojekyll) turns off Jekyll processing, and the root [index.html](../index.html) redirects visitors of the base address to `dashboard/`. No build step or workflow is needed.
