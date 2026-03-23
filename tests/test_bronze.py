"""tests/test_bronze.py — Bronze layer unit tests (stdlib unittest)."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

import pandas as pd
from utils.storage import read as storage_read

from bronze.ingest import fetch_raw_data, save_bronze

SAMPLE_RECORDS = [
    {"vendor_id": "CMT", "pickup_datetime": "2013-12-01T00:11:00.000",
     "dropoff_datetime": "2013-12-01T00:18:00.000", "passenger_count": "1",
     "trip_distance": "1.9", "fare_amount": "8.0", "tip_amount": "1.5",
     "total_amount": "10.5", "rate_code": "1"},
    {"vendor_id": "VTS", "pickup_datetime": "2013-12-01T01:00:00.000",
     "dropoff_datetime": "2013-12-01T01:15:00.000", "passenger_count": "2",
     "trip_distance": "3.2", "fare_amount": "12.0", "tip_amount": "2.0",
     "total_amount": "15.0", "rate_code": "1"},
]


def _mock_urlopen(records):
    mock = MagicMock()
    mock.read.return_value = json.dumps(records).encode()
    mock.__enter__ = lambda s: s
    mock.__exit__ = MagicMock(return_value=False)
    return mock


class TestFetchRawData(unittest.TestCase):
    def test_returns_list(self):
        with patch("urllib.request.urlopen", return_value=_mock_urlopen(SAMPLE_RECORDS)):
            result = fetch_raw_data(limit=2)
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 2)

    def test_records_have_expected_keys(self):
        with patch("urllib.request.urlopen", return_value=_mock_urlopen(SAMPLE_RECORDS)):
            result = fetch_raw_data(limit=2)
        self.assertIn("vendor_id", result[0])
        self.assertIn("fare_amount", result[0])

    def test_raises_on_network_error(self):
        with patch("urllib.request.urlopen", side_effect=OSError("network error")):
            with self.assertRaises(OSError):
                fetch_raw_data()


class TestSaveBronze(unittest.TestCase):
    def test_creates_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = save_bronze(SAMPLE_RECORDS, output_dir=Path(tmp))
            self.assertTrue(path.exists())

    def test_has_audit_columns(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = save_bronze(SAMPLE_RECORDS, output_dir=Path(tmp))
            df = storage_read(path)
            self.assertIn("_raw_json", df.columns)
            self.assertIn("_ingested_at", df.columns)

    def test_row_count_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = save_bronze(SAMPLE_RECORDS, output_dir=Path(tmp))
            df = storage_read(path)
            self.assertEqual(len(df), len(SAMPLE_RECORDS))

    def test_raises_on_empty_records(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                save_bronze([], output_dir=Path(tmp))


if __name__ == "__main__":
    unittest.main()
