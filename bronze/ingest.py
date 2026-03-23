"""
bronze/ingest.py
Bronze layer: Extract raw data from the NYC Open Data API and land it
as-is. No transformations — fidelity is the only goal here.
"""

import json
import urllib.request
import urllib.parse
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pandas as pd

from config.settings import NYC_TAXI_API_URL, API_LIMIT, BRONZE_DIR
from config.settings import INCREMENTAL_LOOKBACK_HOURS, BRONZE_PARTITION_BY_DATE
from utils.logger import get_logger
from utils.storage import write as storage_write

logger = get_logger("bronze.ingest")


def fetch_raw_data(limit: int = API_LIMIT) -> list[dict]:
    # Incremental support via last ingestion marker
    last_marker_path = BRONZE_DIR / ".last_ingested"
    if last_marker_path.exists():
        with open(last_marker_path, "r", encoding="utf-8") as f:
            start_datetime = f.read().strip() or None
    else:
        start_datetime = None

    # optional parameter support for manual date provide
    def _resolve_start(dt):
        return dt

    start_datetime = _resolve_start(start_datetime)

    params = {"$limit": limit, "$order": "pickup_datetime DESC"}
    if start_datetime:
        params["$where"] = f"pickup_datetime > '{start_datetime}'"
    else:
        window = datetime.now(timezone.utc) - timedelta(hours=INCREMENTAL_LOOKBACK_HOURS)
        params["$where"] = f"pickup_datetime > '{window.isoformat()}'"
    params = {"$limit": limit, "$order": "pickup_datetime DESC"}
    if start_datetime:
        params["$where"] = f"pickup_datetime > '{start_datetime}'"
    else:
        # if incremental is enabled, fallback to lookback window
        window = datetime.now(timezone.utc) - timedelta(hours=INCREMENTAL_LOOKBACK_HOURS)
        params["$where"] = f"pickup_datetime > '{window.isoformat()}'"

    params = urllib.parse.urlencode(params)
    url = f"{NYC_TAXI_API_URL}?{params}"

    logger.info(f"Fetching up to {limit:,} rows from NYC Open Data API …")
    logger.info(f"URL: {url}")

    try:
        with urllib.request.urlopen(url, timeout=30) as response:
            raw_bytes = response.read()
            records = json.loads(raw_bytes)
            logger.info(f"Received {len(records):,} raw records")
            return records
    except Exception as exc:
        logger.error(f"Failed to fetch data: {exc}")
        raise


def save_bronze(records: list[dict], output_dir: Path = BRONZE_DIR) -> Path:
    if not records:
        raise ValueError("No records to save — aborting Bronze write.")

    df = pd.DataFrame(records)
    df["pickup_datetime"] = pd.to_datetime(df["pickup_datetime"], errors="coerce", utc=True)
    df["dropoff_datetime"] = pd.to_datetime(df["dropoff_datetime"], errors="coerce", utc=True)
    df["_raw_json"] = df.apply(lambda row: row.to_json(), axis=1)
    df["_ingested_at"] = datetime.now(timezone.utc).isoformat()

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    base_path = output_dir
    if BRONZE_PARTITION_BY_DATE:
        # partition by pickup date (UTC) for performance/scalability
        partition_date = df["pickup_datetime"].dt.floor("D").iloc[0]
        year = partition_date.year
        month = f"{partition_date.month:02d}"
        day = f"{partition_date.day:02d}"
        base_path = output_dir / f"year={year}" / f"month={month}" / f"day={day}"
    base_path = base_path / f"nyc_taxi_raw_{timestamp}"
    output_path = storage_write(df, base_path)

    logger.info(f"Bronze file written → {output_path}  ({df.shape[0]:,} rows × {df.shape[1]} cols)")

    # update marker for incremental runs
    marker_path = BRONZE_DIR / ".last_ingested"
    with open(marker_path, "w", encoding="utf-8") as f:
        f.write(datetime.now(timezone.utc).isoformat())
    return output_path


def run(limit: int = API_LIMIT) -> Path:
    logger.info("=" * 60)
    logger.info("BRONZE LAYER — starting ingestion")
    logger.info("=" * 60)
    records = fetch_raw_data(limit=limit)
    path = save_bronze(records)
    logger.info("BRONZE LAYER — complete ✓")
    return path


if __name__ == "__main__":
    run()
