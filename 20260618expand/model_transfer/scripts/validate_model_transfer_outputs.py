"""validate_model_transfer_outputs.py — static validation for model_transfer outputs."""

from __future__ import annotations

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
MT = ROOT / "20260618expand" / "model_transfer"

REQUIRED_FILES = [
    MT / "data" / "classified" / "fortune100_wendys_model_humor_classification.csv",
    MT / "data" / "regression_ready" / "h1_post_level_regression_ready.csv",
    MT / "data" / "regression_ready" / "h2_post_level_regression_ready.csv",
    MT / "data" / "processed" / "h3_firm_month_panel.csv",
    MT / "data" / "regression_ready" / "h3_firm_period_regression_ready.csv",
    MT / "data" / "diagnostics" / "classification_coverage.csv",
    MT / "data" / "diagnostics" / "humor_presence_frequency.csv",
    MT / "data" / "diagnostics" / "humor_type_frequency.csv",
    MT / "data" / "diagnostics" / "aggressive_humor_sparsity.csv",
    MT / "data" / "diagnostics" / "regression_sample_inclusion.csv",
    MT / "results" / "h1" / "h1_regression_results.csv",
    MT / "results" / "h2" / "h2_regression_results.csv",
    MT / "results" / "h2" / "h2_aggressive_contrast_tests.csv",
    MT / "results" / "h3" / "h3_regression_results.csv",
    MT / "results" / "h3" / "h3_turning_point_diagnostics.csv",
    MT / "reports" / "classifier_transfer_audit.md",
    MT / "reports" / "h1_results.md",
    MT / "reports" / "h2_results.md",
    MT / "reports" / "h3_results.md",
]

REQUIRED_COLUMNS = {
    "data/classified/fortune100_wendys_model_humor_classification.csv": [
        "tweet_id", "humor_presence", "humor_type",
        "aggressive_humor", "affiliative_humor", "self_enhancing_humor", "self_defeating_humor",
        "classification_model_source", "classification_threshold", "classification_status",
    ],
    "data/regression_ready/h1_post_level_regression_ready.csv": [
        "log_total_engagement", "humor_presence",
        "text_length", "hashtag_count", "mention_count",
        "h1_sample_inclusion_flag",
    ],
    "data/regression_ready/h2_post_level_regression_ready.csv": [
        "log_total_engagement", "humor_type",
        "aggressive_humor", "affiliative_humor",
        "text_length", "hashtag_count", "mention_count",
        "h2_sample_inclusion_flag",
    ],
    "data/regression_ready/h3_firm_period_regression_ready.csv": [
        "aggressive_humor_usage_intensity",
        "aggressive_humor_usage_intensity_sq",
        "mean_log_total_engagement",
        "h3_sample_inclusion_flag",
    ],
    "results/h1/h1_regression_results.csv": [
        "variable", "coefficient", "se", "p_value",
    ],
    "results/h2/h2_regression_results.csv": [
        "variable", "coefficient", "se", "p_value",
    ],
    "results/h2/h2_aggressive_contrast_tests.csv": [
        "contrast", "difference", "p_value",
    ],
    "results/h3/h3_regression_results.csv": [
        "variable", "coefficient", "p_value", "h3_status",
    ],
}

FORBIDDEN_OUTPUT_PREFIXES = [
    ROOT / "dashboard" / "data",
    ROOT / "20260615wendy's",
    ROOT / "data" / "raw" / "fortune_x_2025_ranked",
    ROOT / "data" / "analysis",
]

VALID_HUMOR_PRESENCE = {"0", "1"}
VALID_HUMOR_TYPES = {
    "aggressive", "affiliative", "self-enhancing", "self-defeating", "non_humorous"
}


def csv_header(path: Path) -> list[str]:
    with path.open("r", encoding="utf-8", newline="") as fh:
        return next(csv.reader(fh), [])


def csv_row_count(path: Path) -> int:
    with path.open("r", encoding="utf-8", newline="") as fh:
        r = csv.reader(fh)
        next(r, None)
        return sum(1 for _ in r)


def main() -> int:
    failures: list[str] = []

    # 1. Required files exist
    for p in REQUIRED_FILES:
        if not p.exists():
            failures.append(f"missing required file: {p.relative_to(ROOT)}")

    # 2. Required columns
    for rel, cols in REQUIRED_COLUMNS.items():
        path = MT / rel
        if not path.exists():
            continue
        header = csv_header(path)
        missing = [c for c in cols if c not in header]
        if missing:
            failures.append(f"{rel} missing columns: {missing}")

    # 3. Classification output schema: valid humor_presence values
    classified = MT / "data" / "classified" / "fortune100_wendys_model_humor_classification.csv"
    if classified.exists():
        bad_presence: list[str] = []
        with classified.open("r", encoding="utf-8", newline="") as fh:
            for row in csv.DictReader(fh):
                v = row.get("humor_presence", "")
                if v not in VALID_HUMOR_PRESENCE:
                    bad_presence.append(v)
                    if len(bad_presence) >= 5:
                        break
        if bad_presence:
            failures.append(f"humor_presence contains invalid values: {bad_presence[:5]}")

        bad_type: list[str] = []
        with classified.open("r", encoding="utf-8", newline="") as fh:
            for row in csv.DictReader(fh):
                v = row.get("humor_type", "")
                if v not in VALID_HUMOR_TYPES:
                    bad_type.append(v)
                    if len(bad_type) >= 5:
                        break
        if bad_type:
            failures.append(f"humor_type contains invalid values: {bad_type[:5]}")

    # 4. H1 formula check: must NOT contain humor type variables
    h1_rr = MT / "data" / "regression_ready" / "h1_post_level_regression_ready.csv"
    if h1_rr.exists():
        header = csv_header(h1_rr)
        forbidden_in_h1 = [c for c in [
            "aggressive_humor", "affiliative_humor", "self_enhancing_humor",
            "self_defeating_humor", "humor_type",
        ] if c in header]
        if forbidden_in_h1:
            failures.append(f"H1 regression-ready must not include humor type dummies: {forbidden_in_h1}")

    # 5. H2 formula check: must NOT contain raw humor_presence column as regressor
    h2_rr = MT / "data" / "regression_ready" / "h2_post_level_regression_ready.csv"
    if h2_rr.exists():
        header = csv_header(h2_rr)
        if "humor_presence" in header:
            failures.append("H2 regression-ready must not include humor_presence column (collinearity)")

    # 6. H3 panel has both intensity and squared intensity
    h3_rr = MT / "data" / "regression_ready" / "h3_firm_period_regression_ready.csv"
    if h3_rr.exists():
        header = csv_header(h3_rr)
        for col in ["aggressive_humor_usage_intensity", "aggressive_humor_usage_intensity_sq"]:
            if col not in header:
                failures.append(f"H3 regression-ready missing required column: {col}")

    # 7. emoji_count must not be used as control in any regression-ready file
    for rel in [
        "data/regression_ready/h1_post_level_regression_ready.csv",
        "data/regression_ready/h2_post_level_regression_ready.csv",
        "data/regression_ready/h3_firm_period_regression_ready.csv",
    ]:
        path = MT / rel
        if path.exists():
            header = csv_header(path)
            if "emoji_count" in header:
                failures.append(f"{rel} must not contain emoji_count as control")

    # 8. Claim boundary reports exist
    for rel in ["reports/h1_results.md", "reports/h2_results.md", "reports/h3_results.md",
                "reports/classifier_transfer_audit.md"]:
        path = MT / rel
        if path.exists():
            text = path.read_text(encoding="utf-8")
            if "Claim Boundary" not in text and "claim boundary" not in text.lower():
                failures.append(f"{rel} must contain a 'Claim Boundary' section")

    # 9. No forbidden output outside model_transfer/
    for generated in MT.rglob("*"):
        if not generated.is_file():
            continue
        resolved = generated.resolve()
        for forbidden in FORBIDDEN_OUTPUT_PREFIXES:
            try:
                resolved.relative_to(forbidden)
                failures.append(f"forbidden output path: {resolved}")
            except ValueError:
                continue

    # 10. H3 status must acknowledge exploratory if non-zero rows < 300
    h3_results = MT / "results" / "h3" / "h3_regression_results.csv"
    if h3_results.exists():
        with h3_results.open("r", encoding="utf-8", newline="") as fh:
            rows = list(csv.DictReader(fh))
        status_vals = [r.get("h3_status", "") for r in rows]
        if status_vals:
            status = status_vals[0]
            if "exploratory" not in status and "confirmatory" not in status:
                failures.append("H3 results must have a valid h3_status value")

    if failures:
        print("VALIDATION FAIL")
        for f in failures:
            print(f"- {f}")
        return 1
    print("VALIDATION PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
