"""
bronze/ingest.py
Bronze layer: Extract raw data from the NYC Open Data API and land it
as-is. No transformations — fidelity is the only goal here.
"""

import json
import urllib.request
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from config.settings import NYC_TAXI_API_URL, API_LIMIT, BRONZE_DIR
from utils.logger import get_logger
from utils.storage import write as storage_write

logger = get_logger("bronze.ingest")


def fetch_raw_data(limit: int = API_LIMIT) -> list[dict]:
    params = urllib.parse.urlencode({"$limit": limit, "$order": "pickup_datetime DESC"})
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
    df["_raw_json"] = df.apply(lambda row: row.to_json(), axis=1)
    df["_ingested_at"] = datetime.now(timezone.utc).isoformat()

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    base_path = output_dir / f"nyc_taxi_raw_{timestamp}"
    output_path = storage_write(df, base_path)

    logger.info(f"Bronze file written → {output_path}  ({df.shape[0]:,} rows × {df.shape[1]} cols)")
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
