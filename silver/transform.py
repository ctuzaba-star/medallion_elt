"""
silver/transform.py
Silver layer: Clean, validate, and cast types from the Bronze file.
"""

from pathlib import Path
from typing import Optional
from datetime import datetime, timezone

import pandas as pd

from config.settings import (
    BRONZE_DIR, SILVER_DIR,
    REQUIRED_COLUMNS, NUMERIC_COLUMNS, DATETIME_COLUMNS,
    MIN_TRIP_DISTANCE, MAX_TRIP_DISTANCE,
    MIN_FARE, MAX_FARE, MAX_PASSENGERS,
)
from utils.logger import get_logger
from utils.storage import write as storage_write, read as storage_read, glob_latest

logger = get_logger("silver.transform")


def cast_types(df: pd.DataFrame) -> pd.DataFrame:
    for col in NUMERIC_COLUMNS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    for col in DATETIME_COLUMNS:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce", utc=True)
    if "vendor_id" in df.columns:
        df["vendor_id"] = df["vendor_id"].astype(str).str.strip()
    return df


def drop_missing_required(df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    present = [c for c in REQUIRED_COLUMNS if c in df.columns]
    before = len(df)
    df = df.dropna(subset=present)
    dropped = before - len(df)
    if dropped:
        logger.warning(f"Dropped {dropped:,} rows with nulls in required columns")
    return df, dropped


def apply_quality_filters(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    stats: dict[str, int] = {}

    mask = df["trip_distance"].between(MIN_TRIP_DISTANCE, MAX_TRIP_DISTANCE)
    stats["invalid_distance"] = int((~mask).sum())
    df = df[mask]

    mask = df["fare_amount"].between(MIN_FARE, MAX_FARE)
    stats["invalid_fare"] = int((~mask).sum())
    df = df[mask]

    mask = df["passenger_count"].between(1, MAX_PASSENGERS)
    stats["invalid_passengers"] = int((~mask).sum())
    df = df[mask]

    if "pickup_datetime" in df.columns and "dropoff_datetime" in df.columns:
        df = df.copy()
        df["trip_duration_minutes"] = (
            (df["dropoff_datetime"] - df["pickup_datetime"]).dt.total_seconds() / 60
        )
        mask = df["trip_duration_minutes"] > 0
        stats["negative_duration"] = int((~mask).sum())
        df = df[mask]

    for rule, count in stats.items():
        if count:
            logger.warning(f"Quality filter '{rule}' removed {count:,} rows")

    return df, stats


def enrich(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["pickup_hour"]    = df["pickup_datetime"].dt.hour
    df["pickup_weekday"] = df["pickup_datetime"].dt.day_name()
    df["tip_pct"]        = (df["tip_amount"] / df["fare_amount"].replace(0, pd.NA) * 100).round(2)
    df["_processed_at"]  = datetime.now(timezone.utc).isoformat()
    return df


def run(bronze_path: Optional[Path] = None) -> Path:
    logger.info("=" * 60)
    logger.info("SILVER LAYER — starting transformation")
    logger.info("=" * 60)

    bronze_path = bronze_path or glob_latest(BRONZE_DIR, "nyc_taxi_raw_")
    logger.info(f"Reading Bronze file: {bronze_path}")

    df = storage_read(bronze_path)
    logger.info(f"Loaded {len(df):,} raw rows")

    df = df.drop(columns=["_raw_json", "_ingested_at"], errors="ignore")
    df = cast_types(df)
    df, _ = drop_missing_required(df)
    df, _ = apply_quality_filters(df)
    df = enrich(df)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    base_path = SILVER_DIR / f"nyc_taxi_clean_{timestamp}"
    output_path = storage_write(df, base_path)

    logger.info(f"Silver file written → {output_path}  ({len(df):,} rows)")
    logger.info("SILVER LAYER — complete ✓")
    return output_path


if __name__ == "__main__":
    run()
