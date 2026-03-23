"""
governance/rules.py
Data governance: schema validation, quality rules, and lineage tracking.
"""

from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
import pandas as pd


@dataclass
class ValidationRule:
    """A single data quality rule."""
    name: str
    description: str
    column: str
    check: callable
    severity: str = "warning"  # "warning" or "error"

    def evaluate(self, df: pd.DataFrame) -> tuple[bool, int]:
        """Apply rule; return (passed, num_violations)."""
        if self.column not in df.columns:
            return False, len(df)
        try:
            mask = self.check(df[self.column])
            violations = (~mask).sum() if isinstance(mask, pd.Series) else (not mask)
            return mask.all() if isinstance(mask, pd.Series) else mask, violations
        except Exception:
            return False, len(df)


class DataQualityReport:
    """Accumulate and track validation results."""

    def __init__(self, layer: str, input_rows: int):
        self.layer = layer
        self.input_rows = input_rows
        self.output_rows = 0
        self.rules_passed: List[str] = []
        self.rules_failed: List[Dict[str, Any]] = []
        self.timestamp = datetime.now(timezone.utc).isoformat()

    def record_pass(self, rule_name: str):
        self.rules_passed.append(rule_name)

    def record_fail(self, rule_name: str, violations: int, severity: str):
        self.rules_failed.append({
            "rule": rule_name,
            "violations": violations,
            "severity": severity,
        })

    def summary(self) -> Dict[str, Any]:
        """Return a summary dict for logging/serialization."""
        return {
            "layer": self.layer,
            "timestamp": self.timestamp,
            "input_rows": self.input_rows,
            "output_rows": self.output_rows,
            "rules_passed": len(self.rules_passed),
            "rules_failed": len(self.rules_failed),
            "failures": self.rules_failed,
        }


class GovernanceEngine:
    """Apply data governance rules to dataframes."""

    def __init__(self, rules: Optional[List[ValidationRule]] = None):
        self.rules = rules or []

    def add_rule(self, rule: ValidationRule):
        """Register a validation rule."""
        self.rules.append(rule)

    def validate(self, df: pd.DataFrame, layer: str = "unknown") -> DataQualityReport:
        """Run all rules against dataframe; return report."""
        report = DataQualityReport(layer, len(df))

        for rule in self.rules:
            passed, violations = rule.evaluate(df)
            if passed:
                report.record_pass(rule.name)
            else:
                report.record_fail(rule.name, violations, rule.severity)

        report.output_rows = len(df)
        return report


# ────────────────────────────────────────────────────────────────────────────
# Predefined rule sets for each layer

def bronze_rules() -> List[ValidationRule]:
    """Schema and format rules for Bronze (raw) layer."""
    return [
        ValidationRule(
            name="required_columns_present",
            description="All core columns are present in raw data",
            column="vendor_id",
            check=lambda col: col.notna(),
            severity="error",
        ),
        ValidationRule(
            name="pickup_datetime_valid",
            description="Pickup datetime is not null",
            column="pickup_datetime",
            check=lambda col: col.notna(),
            severity="error",
        ),
        ValidationRule(
            name="fare_amount_numeric",
            description="Fare amount is numeric type",
            column="fare_amount",
            check=lambda col: pd.to_numeric(col, errors="coerce").notna(),
            severity="warning",
        ),
    ]


def silver_rules() -> List[ValidationRule]:
    """Quality and validity rules for Silver (cleaned) layer."""
    return [
        ValidationRule(
            name="no_null_trip_distance",
            description="Trip distance has no nulls",
            column="trip_distance",
            check=lambda col: col.notna(),
            severity="error",
        ),
        ValidationRule(
            name="fare_in_valid_range",
            description="Fare amount is between $0 and $500",
            column="fare_amount",
            check=lambda col: col.between(0, 500),
            severity="warning",
        ),
        ValidationRule(
            name="passenger_count_positive",
            description="Passenger count > 0",
            column="passenger_count",
            check=lambda col: col > 0,
            severity="error",
        ),
        ValidationRule(
            name="trip_distance_positive",
            description="Trip distance > 0",
            column="trip_distance",
            check=lambda col: col > 0,
            severity="warning",
        ),
    ]


def gold_rules() -> List[ValidationRule]:
    """Logical consistency rules for Gold (aggregated) layer."""
    return [
        ValidationRule(
            name="aggregation_completeness",
            description="No null values in aggregated metrics",
            column="trip_count",
            check=lambda col: col.notna(),
            severity="error",
        ),
    ]
