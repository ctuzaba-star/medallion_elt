# 🥇 Medallion ELT Pipeline

A simple, production-style **Bronze → Silver → Gold** medallion architecture ELT pipeline using **public NYC taxi trip data** from the NYC Open Data API.

## Architecture Overview

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   BRONZE    │───▶│   SILVER    │───▶│    GOLD     │
│  Raw Data   │    │  Cleaned    │    │  Aggregated │
│  (as-is)    │    │  Validated  │    │  Analytics  │
└─────────────┘    └─────────────┘    └─────────────┘
     extract            transform          transform
      + load
```

| Layer  | Purpose | Format |
|--------|---------|--------|
| Bronze | Raw ingestion, no transformations | Parquet (raw JSON preserved) |
| Silver | Cleaned, validated, typed | Parquet |
| Gold   | Aggregated business metrics | Parquet / CSV |

## Data Source

**NYC TLC Trip Record Data** via NYC Open Data Socrata API — free, no API key required.

- Endpoint: `https://data.cityofnewyork.us/resource/gkne-dk5s.json`
- ~1,000 rows per run (configurable)

## Project Structure

```
medallion_elt/
├── config/
│   └── settings.py          # Central config (paths, API URL, limits)
├── bronze/
│   └── ingest.py            # Extract from API → save raw Parquet
├── silver/
│   └── transform.py         # Clean, validate, cast types
├── gold/
│   └── aggregate.py         # Business-level aggregations
├── utils/
│   └── logger.py            # Shared logger
├── tests/
│   ├── test_bronze.py
│   ├── test_silver.py
│   └── test_gold.py
├── pipeline.py              # Orchestrator — runs all three layers
├── requirements.txt
└── README.md
```

## Quickstart

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Run the full pipeline

```bash
python pipeline.py
```

### 3. Run individual layers

```bash
python -m bronze.ingest
python -m silver.transform
python -m gold.aggregate
```

### 4. Run tests

```bash
pytest tests/ -v
```

## Output

After a successful run you'll find:

```
data/
├── bronze/
│   └── nyc_taxi_raw_<timestamp>.parquet
├── silver/
│   └── nyc_taxi_clean_<timestamp>.parquet
└── gold/
    ├── trips_by_hour.parquet
    ├── trips_by_vendor.parquet
    └── summary_stats.csv
```

## Key Metrics Produced (Gold Layer)

- 🕐 **Trips by hour of day** — demand patterns
- 🚖 **Trips by vendor** — vendor share
- 💵 **Average fare & tip by passenger count**
- 📊 **Overall summary statistics**

## Configuration

Edit `config/settings.py` to adjust:

```python
API_LIMIT = 1000        # rows to fetch per run
DATA_ROOT = "data/"     # output directory
```

## Extending This Pipeline

- **Swap the data source**: Update `config/settings.py` with any Socrata endpoint
- **Add scheduling**: Wrap `pipeline.py` with `cron`, Airflow, or Prefect
- **Add a lakehouse**: Replace local Parquet with Delta Lake or Iceberg
- **Add dbt**: Point dbt at the Silver layer for SQL-based Gold transforms
