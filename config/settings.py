"""
config/settings.py
Central configuration for the medallion ELT pipeline.
"""

import os
from pathlib import Path

# ── Project root ──────────────────────────────────────────────────────────────
ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_ROOT = ROOT_DIR / "data"

# ── Layer paths ───────────────────────────────────────────────────────────────
BRONZE_DIR = DATA_ROOT / "bronze"
SILVER_DIR = DATA_ROOT / "silver"
GOLD_DIR   = DATA_ROOT / "gold"

# Create directories if they don't exist
for _dir in (BRONZE_DIR, SILVER_DIR, GOLD_DIR):
    _dir.mkdir(parents=True, exist_ok=True)

# ── Data source ───────────────────────────────────────────────────────────────
# NYC TLC Yellow Taxi Trip Data via NYC Open Data (Socrata) — no API key needed
NYC_TAXI_API_URL = "https://data.cityofnewyork.us/resource/gkne-dk5s.json"

# Number of rows to fetch per pipeline run (max 50,000 without pagination)
API_LIMIT = 1_000

# ── Schema expectations (Silver layer) ───────────────────────────────────────
REQUIRED_COLUMNS = [
    "vendor_id",
    "pickup_datetime",
    "dropoff_datetime",
    "passenger_count",
    "trip_distance",
    "fare_amount",
    "tip_amount",
    "total_amount",
]

NUMERIC_COLUMNS = [
    "passenger_count",
    "trip_distance",
    "fare_amount",
    "tip_amount",
    "total_amount",
    "rate_code",
]

DATETIME_COLUMNS = ["pickup_datetime", "dropoff_datetime"]

# Silver quality thresholds
MIN_TRIP_DISTANCE = 0.01     # miles
MAX_TRIP_DISTANCE = 200.0    # miles
MIN_FARE          = 0.50     # USD (NYC minimum)
MAX_FARE          = 500.0    # USD
MAX_PASSENGERS    = 6
