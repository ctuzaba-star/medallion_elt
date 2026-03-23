"""tests/test_silver.py — Silver layer unit tests (stdlib unittest)."""
import unittest
import pandas as pd

from silver.transform import cast_types, drop_missing_required, apply_quality_filters, enrich


def make_df(**overrides):
    base = {
        "vendor_id":          ["CMT", "VTS", "CMT"],
        "pickup_datetime":    ["2013-12-01 08:00:00+00:00", "2013-12-01 09:00:00+00:00", "2013-12-01 10:00:00+00:00"],
        "dropoff_datetime":   ["2013-12-01 08:10:00+00:00", "2013-12-01 09:20:00+00:00", "2013-12-01 10:15:00+00:00"],
        "passenger_count":    ["1", "2", "1"],
        "trip_distance":      ["1.5", "3.0", "2.2"],
        "fare_amount":        ["7.0", "12.0", "9.5"],
        "tip_amount":         ["1.0", "2.0", "1.5"],
        "total_amount":       ["9.5", "15.0", "12.0"],
        "rate_code":          ["1", "1", "1"],
    }
    base.update(overrides)
    return pd.DataFrame(base)


class TestCastTypes(unittest.TestCase):
    def test_numeric_columns_are_float(self):
        df = cast_types(make_df())
        self.assertTrue(pd.api.types.is_float_dtype(df["fare_amount"]))

    def test_datetime_columns_are_datetime(self):
        df = cast_types(make_df())
        self.assertTrue(pd.api.types.is_datetime64_any_dtype(df["pickup_datetime"]))

    def test_invalid_numeric_becomes_nan(self):
        df = cast_types(make_df(fare_amount=["bad", "12.0", "9.5"]))
        self.assertTrue(pd.isna(df["fare_amount"].iloc[0]))


class TestDropMissingRequired(unittest.TestCase):
    def test_drops_null_required_rows(self):
        df = cast_types(make_df(fare_amount=["bad", "12.0", "9.5"]))
        df, dropped = drop_missing_required(df)
        self.assertEqual(dropped, 1)
        self.assertEqual(len(df), 2)

    def test_keeps_all_when_no_nulls(self):
        df = cast_types(make_df())
        df, dropped = drop_missing_required(df)
        self.assertEqual(dropped, 0)
        self.assertEqual(len(df), 3)


class TestApplyQualityFilters(unittest.TestCase):
    def _prep(self, **overrides):
        df = cast_types(make_df(**overrides))
        df, _ = drop_missing_required(df)
        df = df.copy()
        df["trip_duration_minutes"] = 10.0
        return df

    def test_removes_negative_fare(self):
        df = self._prep(fare_amount=["7.0", "-5.0", "9.5"])
        df, stats = apply_quality_filters(df)
        self.assertEqual(stats.get("invalid_fare", 0), 1)

    def test_removes_zero_passengers(self):
        df = self._prep(passenger_count=["0", "2", "1"])
        df, stats = apply_quality_filters(df)
        self.assertEqual(stats.get("invalid_passengers", 0), 1)

    def test_valid_rows_pass_through(self):
        df = self._prep()
        df, _ = apply_quality_filters(df)
        self.assertEqual(len(df), 3)


class TestEnrich(unittest.TestCase):
    def _clean(self):
        df = cast_types(make_df())
        df, _ = drop_missing_required(df)
        df, _ = apply_quality_filters(df)
        return enrich(df)

    def test_adds_pickup_hour(self):
        df = self._clean()
        self.assertIn("pickup_hour", df.columns)
        self.assertTrue(df["pickup_hour"].between(0, 23).all())

    def test_adds_tip_pct(self):
        df = self._clean()
        self.assertIn("tip_pct", df.columns)


if __name__ == "__main__":
    unittest.main()
