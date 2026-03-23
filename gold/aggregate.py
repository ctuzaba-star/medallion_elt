"""
gold/aggregate.py
Gold layer: Business-level aggregations from the Silver file.
"""

from pathlib import Path
from typing import Optional
from datetime import datetime

import pandas as pd

from config.settings import SILVER_DIR, GOLD_DIR
from utils.logger import get_logger
from utils.storage import write as storage_write, read as storage_read, glob_latest

logger = get_logger("gold.aggregate")


def _save(df: pd.DataFrame, name: str) -> Path:
    base = GOLD_DIR / name
    path = storage_write(df, base)
    # Always also write a plain CSV for easy inspection
    csv_path = GOLD_DIR / f"{name}.csv"
    df.to_csv(csv_path, index=False)
    logger.info(f"  ↳ {name}: {len(df):,} rows → {path.name} + {csv_path.name}")
    return path


def trips_by_hour(df: pd.DataFrame) -> pd.DataFrame:
    return (
        df.groupby("pickup_hour", as_index=False)
        .agg(
            trip_count=("fare_amount", "count"),
            avg_fare=("fare_amount", "mean"),
            avg_tip_pct=("tip_pct", "mean"),
            avg_duration_min=("trip_duration_minutes", "mean"),
        )
        .round(2)
        .sort_values("pickup_hour")
    )


def trips_by_vendor(df: pd.DataFrame) -> pd.DataFrame:
    total_trips = len(df)
    agg = (
        df.groupby("vendor_id", as_index=False)
        .agg(
            trip_count=("fare_amount", "count"),
            total_fare=("fare_amount", "sum"),
            total_tips=("tip_amount", "sum"),
            avg_fare=("fare_amount", "mean"),
            avg_distance=("trip_distance", "mean"),
        )
        .round(2)
    )
    agg["market_share_pct"] = (agg["trip_count"] / total_trips * 100).round(2)
    return agg.sort_values("trip_count", ascending=False)


def fare_by_passenger_count(df: pd.DataFrame) -> pd.DataFrame:
    return (
        df.groupby("passenger_count", as_index=False)
        .agg(
            trip_count=("fare_amount", "count"),
            avg_fare=("fare_amount", "mean"),
            avg_tip=("tip_amount", "mean"),
            avg_distance=("trip_distance", "mean"),
        )
        .round(2)
        .sort_values("passenger_count")
    )


def summary_stats(df: pd.DataFrame) -> pd.DataFrame:
    stats = {
        "total_trips":           len(df),
        "total_fare_usd":        round(df["fare_amount"].sum(), 2),
        "total_tips_usd":        round(df["tip_amount"].sum(), 2),
        "avg_fare_usd":          round(df["fare_amount"].mean(), 2),
        "avg_trip_distance_mi":  round(df["trip_distance"].mean(), 2),
        "avg_trip_duration_min": round(df["trip_duration_minutes"].mean(), 2),
        "avg_tip_pct":           round(df["tip_pct"].mean(), 2),
        "unique_vendors":        df["vendor_id"].nunique(),
        "date_range_start":      str(df["pickup_datetime"].min()),
        "date_range_end":        str(df["pickup_datetime"].max()),
    }
    return pd.DataFrame([stats])


def run(silver_path: Optional[Path] = None) -> list[Path]:
    logger.info("=" * 60)
    logger.info("GOLD LAYER — starting aggregation")
    logger.info("=" * 60)

    silver_path = silver_path or glob_latest(SILVER_DIR, "nyc_taxi_clean_")
    logger.info(f"Reading Silver file: {silver_path}")

    df = storage_read(silver_path)
    logger.info(f"Loaded {len(df):,} clean rows — building Gold tables …")

    outputs = [
        _save(trips_by_hour(df),            "trips_by_hour"),
        _save(trips_by_vendor(df),          "trips_by_vendor"),
        _save(fare_by_passenger_count(df),  "fare_by_passenger_count"),
        _save(summary_stats(df),            "summary_stats"),
    ]

    logger.info("GOLD LAYER — complete ✓")
    return outputs


if __name__ == "__main__":
    run()
