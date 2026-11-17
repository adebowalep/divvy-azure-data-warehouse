# Portfolio summary: Divvy Bike Share, Azure Data Warehouse & Analytics

A short version of the project for a case-study page. Every number below is checked against the repository.

## Title

Divvy Bike Share | Azure Data Warehouse & Analytics

PostgreSQL · Azure Synapse (serverless SQL) · Data Lake Storage · CETAS · Parquet · T-SQL · Python · JavaScript

## Description

I designed and built a dimensional data warehouse on Azure for Chicago's Divvy bike share, validated it with 26 automated checks, and published an interactive dashboard that explores ride duration, stations, routes, payments and rider accounts. The warehouse turns 4.6 million trips and 1.9 million payments into a star schema with two fact tables and three dimensions.

## Scale

| | |
|---|---|
| Trips | 4,584,921 (4,583,447 with a valid duration) |
| Payments | 1,946,607, totalling $19,457,105.25 |
| Riders | 75,000 |
| Stations | 838 |
| Warehouse | 2 fact tables, 3 dimensions, 5 CETAS transformations, Parquet output |
| Checks | 26 of 26 passing in Azure Synapse |

The ride data is the City of Chicago's public Divvy data. The rider, account and payment data is synthetic.

## What I did

- Designed a star schema from a relational source: two separate fact tables (trips and payments) because payments carry no trip id, sharing rider and date dimensions, with one station dimension used for both the start and end of a ride.
- Built the pipeline in Azure: PostgreSQL as the source system, a Synapse copy pipeline to Data Lake Storage, four external staging tables, and five CETAS statements writing Parquet.
- Wrote the transformation rules carefully: ages in completed years, ride durations kept to four decimals, bad durations flagged and kept (not deleted), money parsed defensively, and a separate output folder for every re-run.
- Wrote a 26-check validation scorecard in SQL and checked the dashboard figures a second way, with independent Python code.
- Built a static, interactive dashboard with a rider-type filter, seven views, a station map and keyboard-accessible tabs, and tested it in a real browser at desktop, tablet and phone widths.
- Documented the architecture, the model, the validation and the limits.

## Architecture in one paragraph

Four CSV files are loaded into Azure Database for PostgreSQL. A one-time Synapse pipeline copies the four tables to Data Lake Storage as text files. The built-in serverless SQL pool exposes them as four external staging tables, and five CETAS statements turn those into three dimensions and two facts stored as Parquet. T-SQL queries and a validation scorecard run on top. The dashboard is a separate branch: Python aggregates the same CSV files using the same rules, and a single static HTML page is hosted on GitHub Pages with no live Azure connection. The diagram is [images/architecture.svg](images/architecture.svg) (editable source: [architecture.drawio](architecture.drawio)).

## Main technical challenge

Payments cannot be matched to rides, so a direct join would repeat each payment once per ride. The warehouse keeps the two facts apart and combines them only after summing both to rider-month. A smaller lesson came from the validation: my own independent check found a one-ride difference in an age band, and I traced it to how a 29 February birthday is counted. I aligned the Python to the warehouse rule and recorded it.

## Dashboard features

- Rider-type filter (all, members, casual) that updates every chart, number and insight sentence.
- Ride time: weekday-by-hour heatmap, monthly trend, age, commute pattern, ride-length distribution, bike-type mix.
- Stations: map of the network, ranked by average ride length or by volume, for the start or the end of a ride.
- Flow and routes: stations that gain or lose bikes, and the most common routes.
- Money, riders, usage vs spend, and a pipeline and checks view.
- Direct links to each tab, working Back and Forward buttons, keyboard navigation, light and dark themes, and text contrast of at least 4.5:1.

## Important limitations

- The Azure resources were temporary and were deleted. The warehouse is shown through its SQL and recorded screenshots, not a live service.
- The dashboard is a static snapshot computed locally from the CSV files. Several of its views were not run in Synapse; [validation.md](validation.md) lists which were.
- Membership is the current flag, not history, and payments are synthetic and not linked to rides. Patterns involving payments are descriptive and say nothing about real customers.

## Suggested screenshots for the page

1. [dashboard-overview.png](images/dashboard-overview.png) as the main image.
2. [architecture.svg](images/architecture.svg) for the pipeline.
3. [dashboard-stations.png](images/dashboard-stations.png) or [dashboard-routes.png](images/dashboard-routes.png).
4. [../evidence/04_validation_summary.png](../evidence/04_validation_summary.png) for the checks.

## Links

- Live dashboard: https://adebowalep.github.io/divvy-azure-data-warehouse/dashboard/ (loaded and tested in a browser on 17 November 2026; later improvements appear there once pushed)
- Repository: https://github.com/adebowalep/divvy-azure-data-warehouse
