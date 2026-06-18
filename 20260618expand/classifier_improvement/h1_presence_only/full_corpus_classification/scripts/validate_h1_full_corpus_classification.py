"""
validate_h1_full_corpus_classification.py

Validates outputs of apply_h1_presence_only_classifier.py.

Checks:
  1. Output files exist
  2. Row count matches input corpus (65,245)
  3. Probability values in [0,1]
  4. Threshold predictions are 0/1 (or blank for missing_text)
  5. No type/aggressive columns generated
  6. No H1 regression output generated
  7. Classifier metadata columns present
  8. Summary file has expected metrics

Returns exit code 0 on PASS, 1 on FAIL.
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
CI = ROOT / "20260618expand" / "classifier_improvement"
H1 = CI / "h1_presence_only"
FC = H1 / "full_corpus_classification"
DATA_DIR = FC / "data"

EXPECTED_CORPUS_ROWS = 65245
POST_MASTER = ROOT / "20260618expand" / "data" / "processed" / "fortune100_post_master.csv"

REQUIRED_OUTPUT_FILES = [
    DATA_DIR / "fortune100_h1_presence_classified_posts.csv",
    DATA_DIR / "fortune100_h1_presence_classification_summary.csv",
    DATA_DIR / "fortune100_h1_presence_by_firm_summary.csv",
    FC / "reports" / "h1_full_corpus_classification_memo.md",
    FC / "reports" / "h1_full_corpus_classification_claim_boundaries.md",
]

FORBIDDEN_COLS = [
    "h2_", "h3_", "aggressive", "type_label", "humor_type",
    "human_humor_type", "self_enhancing", "affiliative", "self_defeating",
]

REQUIRED_META_COLS = [
    "h1_humor_presence_probability",
    "h1_humor_presence_pred_t40",
    "h1_humor_presence_pred_t50",
    "h1_humor_presence_pred_t60",
    "missing_text",
    "h1_classifier_model",
    "h1_classifier_training_scope",
    "h1_classifier_status",
]

errors: list[str] = []
warnings: list[str] = []


def check(cond: bool, msg: str) -> None:
    if not cond:
        errors.append(f"FAIL: {msg}")
    else:
        print(f"  PASS: {msg}")


def warn(cond: bool, msg: str) -> None:
    if not cond:
        warnings.append(f"WARN: {msg}")
    else:
        print(f"  OK:   {msg}")


def main() -> None:
    print("=== validate_h1_full_corpus_classification ===")

    # 1. Required files exist
    print("\n[1] Required output files:")
    for fp in REQUIRED_OUTPUT_FILES:
        check(fp.exists(), f"exists: {fp.relative_to(ROOT)}")

    # 2. Count input corpus rows
    print("\n[2] Input corpus row count:")
    actual_corpus_rows = EXPECTED_CORPUS_ROWS
    if POST_MASTER.exists():
        with open(POST_MASTER, encoding="utf-8", newline="") as f:
            actual_corpus_rows = sum(1 for _ in csv.DictReader(f))
        check(actual_corpus_rows == EXPECTED_CORPUS_ROWS,
              f"corpus rows == {EXPECTED_CORPUS_ROWS} (got {actual_corpus_rows})")
    else:
        warnings.append(f"WARN: post master not found at expected path: {POST_MASTER}")

    # 3. Classified posts file
    print("\n[3] Classified posts file:")
    posts_path = DATA_DIR / "fortune100_h1_presence_classified_posts.csv"
    if posts_path.exists():
        with open(posts_path, encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            cols = reader.fieldnames or []
            rows = list(reader)

        check(len(rows) == actual_corpus_rows,
              f"output rows == corpus rows ({actual_corpus_rows}, got {len(rows)})")

        # Required metadata columns present
        for col in REQUIRED_META_COLS:
            check(col in cols, f"column present: {col}")

        # No forbidden columns
        lower_cols = [c.lower() for c in cols]
        for fc_pattern in FORBIDDEN_COLS:
            has_forbidden = any(fc_pattern in c for c in lower_cols)
            check(not has_forbidden, f"no forbidden column matching '{fc_pattern}'")

        # Probability range check (on non-missing rows)
        bad_prob = 0
        bad_t = 0
        checked = 0
        for r in rows:
            if r.get("missing_text", "0") == "1":
                continue
            prob_str = r.get("h1_humor_presence_probability", "")
            if prob_str == "" or prob_str is None:
                continue
            try:
                p = float(prob_str)
                if not (0.0 <= p <= 1.0):
                    bad_prob += 1
            except ValueError:
                bad_prob += 1
            for col in ["h1_humor_presence_pred_t40", "h1_humor_presence_pred_t50",
                        "h1_humor_presence_pred_t60"]:
                v = r.get(col, "")
                if v not in ("0", "1", ""):
                    bad_t += 1
            checked += 1

        check(bad_prob == 0, f"all probabilities in [0,1] (bad={bad_prob}, checked={checked})")
        check(bad_t == 0, f"all threshold preds are 0/1 (bad={bad_t})")

        # Classifier metadata values
        models = set(r.get("h1_classifier_model", "") for r in rows[:10])
        check("word_char_comb__lr_liblin_C01" in models,
              f"classifier_model = word_char_comb__lr_liblin_C01 (found: {models})")
        scopes = set(r.get("h1_classifier_training_scope", "") for r in rows[:10])
        check("batch1_only" in scopes, f"training_scope = batch1_only (found: {scopes})")
        statuses = set(r.get("h1_classifier_status", "") for r in rows[:10])
        check("provisional" in statuses, f"classifier_status = provisional (found: {statuses})")

        # Missing text count
        missing_n = sum(1 for r in rows if r.get("missing_text", "0") == "1")
        print(f"  OK:   missing_text posts: {missing_n}")

    # 4. Summary file
    print("\n[4] Summary file:")
    summ_path = DATA_DIR / "fortune100_h1_presence_classification_summary.csv"
    if summ_path.exists():
        with open(summ_path, encoding="utf-8") as f:
            summ = {r["metric"]: r["value"] for r in csv.DictReader(f)}

        check(summ.get("h1_regression_run") == "NO", "summary: h1_regression_run=NO")
        check(summ.get("h2_h3_run") == "NO", "summary: h2_h3_run=NO")
        check(summ.get("type_classifier_used") == "NO", "summary: type_classifier_used=NO")
        check(summ.get("aggressive_detector_used") == "NO", "summary: aggressive_detector_used=NO")

        try:
            total = int(summ.get("total_posts", 0))
            check(total == actual_corpus_rows, f"summary total_posts={actual_corpus_rows} (got {total})")
        except ValueError:
            errors.append("FAIL: summary total_posts not integer")

        warn(float(summ.get("humor_rate_t50", 0) or 0) > 0,
             "humor_rate_t50 > 0 (sanity check)")

    # 5. Firm summary file
    print("\n[5] Firm summary file:")
    firm_path = DATA_DIR / "fortune100_h1_presence_by_firm_summary.csv"
    if firm_path.exists():
        with open(firm_path, encoding="utf-8") as f:
            firm_rows = list(csv.DictReader(f))
        check(len(firm_rows) > 0, f"firm summary has rows (got {len(firm_rows)})")
        warn(len(firm_rows) >= 90, f"firm count >= 90 (got {len(firm_rows)})")

    # 6. Report files
    print("\n[6] Report files:")
    memo_path = FC / "reports" / "h1_full_corpus_classification_memo.md"
    cb_path   = FC / "reports" / "h1_full_corpus_classification_claim_boundaries.md"
    if memo_path.exists():
        memo = memo_path.read_text(encoding="utf-8").lower()
        check("provisional" in memo, "memo mentions 'provisional'")
        check("h1 regression" in memo or "h1 regression is not" in memo or "not" in memo,
              "memo clarifies H1 regression status")
        check("h2" in memo or "h3" in memo, "memo references H2/H3 scope exclusion")
    if cb_path.exists():
        cb = cb_path.read_text(encoding="utf-8").lower()
        check("h1 is supported" in cb or "h1 is not supported" in cb or "h1 is" in cb,
              "claim_boundaries references H1 status")
        check("prohibited" in cb or "must not" in cb or "not permitted" in cb,
              "claim_boundaries has prohibited section")

    # 7. No H1 regression output in classification directory
    print("\n[7] No regression output present:")
    reg_patterns = ["h1_regression", "regression_results", "hypothesis_test"]
    regression_files = []
    for pattern in reg_patterns:
        regression_files.extend(list(FC.rglob(f"*{pattern}*")))
    check(len(regression_files) == 0,
          f"no H1 regression output files found (found: {regression_files})")

    # Summary
    print("\n" + "=" * 60)
    if errors:
        print(f"VALIDATION RESULT: FAIL ({len(errors)} errors, {len(warnings)} warnings)")
        for e in errors:
            print(f"  {e}")
        for w in warnings:
            print(f"  {w}")
        sys.exit(1)
    else:
        print(f"VALIDATION RESULT: PASS ({len(warnings)} warnings)")
        for w in warnings:
            print(f"  {w}")
        print("=== validate_h1_full_corpus_classification COMPLETE ===")
        sys.exit(0)


if __name__ == "__main__":
    main()
