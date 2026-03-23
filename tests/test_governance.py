"""tests/test_governance.py — Data governance validation tests."""
import unittest
from datetime import datetime, timezone

import pandas as pd

from governance.rules import (
    ValidationRule,
    DataQualityReport,
    GovernanceEngine,
    bronze_rules,
    silver_rules,
    gold_rules,
)


class TestValidationRule(unittest.TestCase):
    def test_rule_evaluation_pass(self):
        rule = ValidationRule(
            name="test_pass",
            description="Always passes",
            column="x",
            check=lambda col: col > 0,
        )
        df = pd.DataFrame({"x": [1, 2, 3]})
        passed, violations = rule.evaluate(df)
        self.assertTrue(passed)
        self.assertEqual(violations, 0)

    def test_rule_evaluation_fail(self):
        rule = ValidationRule(
            name="test_fail",
            description="Catches negatives",
            column="x",
            check=lambda col: col > 0,
        )
        df = pd.DataFrame({"x": [1, -2, 3]})
        passed, violations = rule.evaluate(df)
        self.assertFalse(passed)
        self.assertEqual(violations, 1)

    def test_rule_missing_column(self):
        rule = ValidationRule(
            name="test_missing",
            description="Column missing",
            column="missing_col",
            check=lambda col: col.notna(),
        )
        df = pd.DataFrame({"x": [1, 2, 3]})
        passed, violations = rule.evaluate(df)
        self.assertFalse(passed)


class TestDataQualityReport(unittest.TestCase):
    def test_report_creation(self):
        report = DataQualityReport("test_layer", 100)
        self.assertEqual(report.layer, "test_layer")
        self.assertEqual(report.input_rows, 100)
        self.assertIsNotNone(report.timestamp)

    def test_record_pass(self):
        report = DataQualityReport("test", 100)
        report.record_pass("rule_1")
        report.record_pass("rule_2")
        self.assertEqual(len(report.rules_passed), 2)

    def test_record_fail(self):
        report = DataQualityReport("test", 100)
        report.record_fail("rule_bad", 5, "error")
        self.assertEqual(len(report.rules_failed), 1)
        self.assertEqual(report.rules_failed[0]["violations"], 5)

    def test_summary(self):
        report = DataQualityReport("silver", 1000)
        report.record_pass("rule_1")
        report.record_fail("rule_2", 3, "warning")
        report.output_rows = 997
        
        summary = report.summary()
        self.assertEqual(summary["layer"], "silver")
        self.assertEqual(summary["input_rows"], 1000)
        self.assertEqual(summary["output_rows"], 997)
        self.assertEqual(summary["rules_passed"], 1)
        self.assertEqual(summary["rules_failed"], 1)


class TestGovernanceEngine(unittest.TestCase):
    def test_engine_initialization(self):
        engine = GovernanceEngine()
        self.assertEqual(len(engine.rules), 0)

    def test_add_rule(self):
        engine = GovernanceEngine()
        rule = ValidationRule(
            name="test",
            description="test",
            column="x",
            check=lambda col: col > 0,
        )
        engine.add_rule(rule)
        self.assertEqual(len(engine.rules), 1)

    def test_validate_all_pass(self):
        engine = GovernanceEngine(bronze_rules())
        df = pd.DataFrame({
            "vendor_id": ["CMT", "VTS", "CMT"],
            "pickup_datetime": ["2023-01-01", "2023-01-02", "2023-01-03"],
            "fare_amount": ["10.0", "15.0", "12.0"],
        })
        report = engine.validate(df, layer="bronze")
        self.assertEqual(len(report.rules_failed), 0)
        self.assertGreater(len(report.rules_passed), 0)

    def test_validate_with_failures(self):
        engine = GovernanceEngine(silver_rules())
        df = pd.DataFrame({
            "trip_distance": [1.5, -2.0, 3.0],
            "fare_amount": [10.0, 600.0, 12.0],  # 600 out of range
            "passenger_count": [1, 0, 2],  # 0 invalid
        })
        report = engine.validate(df, layer="silver")
        self.assertGreater(len(report.rules_failed), 0)


class TestPredefinedRules(unittest.TestCase):
    def test_bronze_rules_count(self):
        rules = bronze_rules()
        self.assertGreater(len(rules), 0)
        self.assertTrue(any(r.name == "required_columns_present" for r in rules))

    def test_silver_rules_count(self):
        rules = silver_rules()
        self.assertGreater(len(rules), 0)
        self.assertTrue(any(r.name == "passenger_count_positive" for r in rules))

    def test_gold_rules_count(self):
        rules = gold_rules()
        self.assertGreater(len(rules), 0)
        self.assertTrue(any(r.name == "aggregation_completeness" for r in rules))


if __name__ == "__main__":
    unittest.main()
