#!/usr/bin/env python3
"""Static validation for the isolated 20260618expand package."""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "20260618expand"

REQUIRED = {
    "data/processed/fortune100_post_master.csv": ["tweet_id", "company_name", "total_engagement", "text_length", "hashtag_count", "mention_count"],
    "data/processed/fortune100_post_master.json": None,
    "data/processed/fortune100_humor_variables.csv": ["tweet_id", "humor_presence", "humor_type", "classification_source"],
    "data/processed/fortune100_firm_period_panel.csv": ["company_name", "period", "aggressive_humor_usage_intensity", "aggressive_humor_usage_intensity_sq"],
    "data/regression_ready/fortune100_post_level_regression_ready.csv": ["h1_sample_inclusion_flag", "h2_sample_inclusion_flag"],
    "data/regression_ready/fortune100_firm_period_regression_ready.csv": ["h3_sample_inclusion_flag"],
    "data/diagnostics/fortune100_collection_coverage.csv": ["fortune_rank", "posts_csv_exists", "posts_csv_non_empty"],
    "data/diagnostics/fortune100_missingness_summary.csv": ["dataset", "column", "missing_count"],
    "data/diagnostics/fortune100_duplicate_tweet_audit.csv": ["tweet_id", "source_folder"],
    "data/diagnostics/fortune100_humor_classification_coverage.csv": ["classified_count", "classification_missing_count"],
    "reports/coverage_diagnostics.md": None,
    "reports/variable_construction.md": None,
    "reports/model_free_evidence.md": None,
    "reports/h1_h2_h3_analysis_plan.md": None,
    "reports/limitations_and_claim_boundaries.md": None,
    "schemas/fortune100_post_master.schema.json": None,
    "schemas/fortune100_firm_period_panel.schema.json": None,
    "schemas/fortune100_regression_ready.schema.json": None,
}

FORBIDDEN_OUTPUT_PREFIXES = [
    ROOT / "dashboard/data",
    ROOT / "20260615wendy's",
    ROOT / "data/raw/fortune_x_2025_ranked",
    ROOT / "data/analysis",
]


def csv_header(path: Path) -> list[str]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return next(csv.reader(handle), [])


def count_rows(path: Path) -> int:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle)
        next(reader, None)
        return sum(1 for _ in reader)


def main() -> int:
    failures: list[str] = []
    for rel, columns in REQUIRED.items():
        path = PACKAGE / rel
        if not path.exists():
            failures.append(f"missing required output: {rel}")
            continue
        if path.suffix == ".csv":
            header = csv_header(path)
            missing = [column for column in (columns or []) if column not in header]
            if missing:
                failures.append(f"{rel} missing columns: {missing}")
            if count_rows(path) == 0 and "duplicate_tweet_audit" not in rel:
                failures.append(f"{rel} has zero data rows")
        elif path.suffix == ".json":
            try:
                json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                failures.append(f"{rel} invalid JSON: {exc}")

    for generated in PACKAGE.rglob("*"):
        if not generated.is_file():
            continue
        resolved = generated.resolve()
        for forbidden in FORBIDDEN_OUTPUT_PREFIXES:
            try:
                resolved.relative_to(forbidden)
            except ValueError:
                continue
            failures.append(f"forbidden output path touched by package traversal: {resolved}")

    # Content checks for required audit documentation
    content_checks = [
        (
            "reports/model_free_evidence.md",
            "aggressive: 95",
            "model_free_evidence.md must contain aggressive humor frequency count (aggressive: 95)",
        ),
        (
            "reports/model_free_evidence.md",
            "ambiguous",
            "model_free_evidence.md must contain ambiguous post count documentation",
        ),
        (
            "reports/h1_h2_h3_analysis_plan.md",
            "exploratory",
            "h1_h2_h3_analysis_plan.md must contain H3 exploratory/readiness downgrade statement",
        ),
        (
            "reports/variable_construction.md",
            "bookmark_count",
            "variable_construction.md must document bookmark_count exclusion and DV difference from Wendy's",
        ),
    ]
    for rel, keyword, message in content_checks:
        path = PACKAGE / rel
        if path.exists():
            text = path.read_text(encoding="utf-8")
            if keyword not in text:
                failures.append(message)

    # Period format check: all period values in post-level regression-ready must be YYYY-MM or missing_period
    period_path = PACKAGE / "data/regression_ready/fortune100_post_level_regression_ready.csv"
    if period_path.exists():
        import re as _re
        period_pattern = _re.compile(r"^\d{4}-\d{2}$")
        bad_periods: list[str] = []
        with period_path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                val = row.get("period", "")
                if val and val != "missing_period" and not period_pattern.match(val):
                    bad_periods.append(val)
                    if len(bad_periods) >= 5:
                        break
        if bad_periods:
            failures.append(f"period column contains non-YYYY-MM values: {bad_periods[:5]}")

    if failures:
        print("VALIDATION FAIL")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("VALIDATION PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
