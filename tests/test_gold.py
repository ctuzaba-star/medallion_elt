"""tests/test_gold.py — Gold layer unit tests (stdlib unittest)."""
import unittest
import pandas as pd

from gold.aggregate import trips_by_hour, trips_by_vendor, fare_by_passenger_count, summary_stats


def make_silver_df():
    return pd.DataFrame({
        "vendor_id":             ["CMT", "VTS", "CMT", "VTS"],
        "pickup_hour":           [8, 8, 9, 10],
        "pickup_weekday":        ["Monday"] * 4,
        "pickup_datetime":       pd.to_datetime(
            ["2013-12-01 08:00", "2013-12-01 08:30", "2013-12-01 09:00", "2013-12-01 10:00"], utc=True),
        "dropoff_datetime":      pd.to_datetime(
            ["2013-12-01 08:10", "2013-12-01 08:45", "2013-12-01 09:20", "2013-12-01 10:15"], utc=True),
        "passenger_count":       [1, 2, 1, 3],
        "trip_distance":         [1.5, 3.0, 2.2, 4.0],
        "fare_amount":           [7.0, 12.0, 9.5, 14.0],
        "tip_amount":            [1.0, 2.0, 1.5, 0.0],
        "total_amount":          [9.5, 15.0, 12.0, 15.5],
        "trip_duration_minutes": [10.0, 15.0, 20.0, 15.0],
        "tip_pct":               [14.3, 16.7, 15.8, 0.0],
    })


class TestTripsByHour(unittest.TestCase):
    def test_returns_dataframe(self):
        self.assertIsInstance(trips_by_hour(make_silver_df()), pd.DataFrame)

    def test_has_expected_columns(self):
        result = trips_by_hour(make_silver_df())
        for col in ("pickup_hour", "trip_count", "avg_fare"):
            self.assertIn(col, result.columns)

    def test_counts_positive(self):
        result = trips_by_hour(make_silver_df())
        self.assertTrue((result["trip_count"] > 0).all())


class TestTripsByVendor(unittest.TestCase):
    def test_one_row_per_vendor(self):
        df = make_silver_df()
        self.assertEqual(len(trips_by_vendor(df)), df["vendor_id"].nunique())

    def test_market_share_sums_to_100(self):
        result = trips_by_vendor(make_silver_df())
        self.assertAlmostEqual(result["market_share_pct"].sum(), 100.0, places=1)

    def test_has_total_fare(self):
        self.assertIn("total_fare", trips_by_vendor(make_silver_df()).columns)


class TestFareByPassengerCount(unittest.TestCase):
    def test_one_row_per_pax(self):
        df = make_silver_df()
        self.assertEqual(len(fare_by_passenger_count(df)), df["passenger_count"].nunique())

    def test_avg_fare_positive(self):
        result = fare_by_passenger_count(make_silver_df())
        self.assertTrue((result["avg_fare"] > 0).all())


class TestSummaryStats(unittest.TestCase):
    def test_single_row(self):
        self.assertEqual(len(summary_stats(make_silver_df())), 1)

    def test_total_trips(self):
        df = make_silver_df()
        result = summary_stats(df)
        self.assertEqual(result["total_trips"].iloc[0], len(df))

    def test_has_date_range(self):
        result = summary_stats(make_silver_df())
        self.assertIn("date_range_start", result.columns)
        self.assertIn("date_range_end", result.columns)


if __name__ == "__main__":
    unittest.main()
