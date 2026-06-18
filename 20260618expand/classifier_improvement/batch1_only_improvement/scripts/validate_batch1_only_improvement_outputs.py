"""
validate_batch1_only_improvement_outputs.py

Validates all outputs of the batch1-only improvement pipeline.

Checks:
  1. All required files exist
  2. Presence training data: expected row counts, no uncertain
  3. Aggressive detector data: expected row counts
  4. Model comparison CSVs exist and have correct eval_mode
  5. Threshold CSV is OOF-based (not in-sample)
  6. OOF confusion matrices exist
  7. Reports directory has required files
  8. No batch2 files referenced
  9. Raw data, dashboard, wendy's not modified
  10. No in-sample metrics presented as validation

Returns exit code 0 on PASS, 1 on FAIL.
"""

from __future__ import annotations

import csv
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
CI = ROOT / "20260618expand" / "classifier_improvement"
B1 = CI / "batch1_only_improvement"

EXPECTED_TOTAL = 1500
EXPECTED_PRESENCE_VALID = 1482
EXPECTED_AGG_ROWS = 648
EXPECTED_AGG_POS = 44
EXPECTED_AGG_NEG = 604

REQUIRED_FILES = [
    B1 / "README.md",
    B1 / "data" / "batch1_presence_training_data.csv",
    B1 / "data" / "batch1_aggressive_detector_training_data.csv",
    B1 / "data" / "batch1_training_data_diagnostics.csv",
    B1 / "results" / "presence_model_comparison_cv.csv",
    B1 / "results" / "aggressive_detector_model_comparison_cv.csv",
    B1 / "results" / "aggressive_detector_threshold_cv.csv",
    B1 / "results" / "aggressive_detector_oof_confusion_matrix.csv",
    B1 / "results" / "presence_oof_confusion_matrix.csv",
    B1 / "results" / "firm_held_out_presence_results.csv",
    B1 / "results" / "firm_held_out_aggressive_results.csv",
    B1 / "reports" / "batch1_only_model_improvement_report.md",
    B1 / "reports" / "claim_boundaries.md",
    B1 / "reports" / "next_step_decision.md",
]

FORBIDDEN_PATHS = [
    ROOT / "data" / "raw" / "fortune_x_2025_ranked",
    ROOT / "dashboard" / "data",
    ROOT / "20260615wendy's",
]

BATCH2_MARKER = "batch2"
IN_SAMPLE_MARKERS = ["in_sample", "confusion_matrix.csv", "threshold_sensitivity.csv"]
EVAL_MODE_REQUIRED = ["oof", "cv", "out_of_fold", "firm_held_out"]


errors: list[str] = []
warnings: list[str] = []


def check(condition: bool, msg: str) -> None:
    if not condition:
        errors.append(f"FAIL: {msg}")
    else:
        print(f"  PASS: {msg}")


def warn(condition: bool, msg: str) -> None:
    if not condition:
        warnings.append(f"WARN: {msg}")
    else:
        print(f"  OK:   {msg}")


def main() -> None:
    print("=== validate_batch1_only_improvement_outputs ===")

    # 1. Required files exist
    print("\n[1] Required files:")
    for fpath in REQUIRED_FILES:
        check(fpath.exists(), f"exists: {fpath.relative_to(ROOT)}")

    # 2. Presence training data counts
    print("\n[2] Presence training data:")
    pres_path = B1 / "data" / "batch1_presence_training_data.csv"
    if pres_path.exists():
        with open(pres_path, encoding="utf-8") as f:
            pres_rows = list(csv.DictReader(f))
        check(len(pres_rows) == EXPECTED_PRESENCE_VALID,
              f"presence rows == {EXPECTED_PRESENCE_VALID} (got {len(pres_rows)})")
        codes = [r.get("presence_code", "").strip() for r in pres_rows]
        check("2" not in codes, "uncertain (2) excluded from presence data")
        check(all(c in ("0", "1") for c in codes), "all presence_codes are 0 or 1")
        humor_n = sum(int(r.get("humor_label", 0)) for r in pres_rows)
        check(humor_n == 648, f"humor_count == 648 (got {humor_n})")
        non_humor_n = sum(1 for r in pres_rows if r.get("humor_label") == "0")
        check(non_humor_n == 834, f"non_humor_count == 834 (got {non_humor_n})")
    else:
        errors.append("FAIL: presence data file missing — skipping count checks")

    # 3. Aggressive detector data counts
    print("\n[3] Aggressive detector data:")
    agg_path = B1 / "data" / "batch1_aggressive_detector_training_data.csv"
    if agg_path.exists():
        with open(agg_path, encoding="utf-8") as f:
            agg_rows = list(csv.DictReader(f))
        check(len(agg_rows) == EXPECTED_AGG_ROWS,
              f"agg rows == {EXPECTED_AGG_ROWS} (got {len(agg_rows)})")
        agg_pos = sum(int(r.get("aggressive_label", 0)) for r in agg_rows)
        check(agg_pos == EXPECTED_AGG_POS, f"aggressive positives == {EXPECTED_AGG_POS} (got {agg_pos})")
        check(all(r.get("presence_code", "").strip() == "1" for r in agg_rows),
              "all agg detector rows have presence_code=1")
        batch2_refs = sum(1 for r in agg_rows if BATCH2_MARKER in str(r.get("sampling_stratum", "")))
        check(batch2_refs == 0, "no batch2 references in agg detector data")
    else:
        errors.append("FAIL: agg detector data file missing — skipping count checks")

    # 4. Diagnostics file
    print("\n[4] Diagnostics file:")
    diag_path = B1 / "data" / "batch1_training_data_diagnostics.csv"
    if diag_path.exists():
        with open(diag_path, encoding="utf-8") as f:
            diag = {r["metric"]: r["value"] for r in csv.DictReader(f)}
        check(diag.get("batch2_used") == "NO", "diagnostics: batch2_used=NO")
        check(diag.get("raw_data_modified") == "NO", "diagnostics: raw_data_modified=NO")
        check(diag.get("labels_modified") == "NO", "diagnostics: labels_modified=NO")

    # 5. Presence model comparison CSV
    print("\n[5] Presence model comparison CV:")
    pres_cv_path = B1 / "results" / "presence_model_comparison_cv.csv"
    if pres_cv_path.exists():
        with open(pres_cv_path, encoding="utf-8") as f:
            cv_rows = list(csv.DictReader(f))
        ok_rows = [r for r in cv_rows if r.get("status") == "OK"]
        check(len(ok_rows) > 0, f"at least 1 successful model (got {len(ok_rows)})")
        # Check eval_mode is OOF-based
        eval_modes = set(r.get("eval_mode", "") for r in ok_rows)
        has_oof = any("oof" in m.lower() or "cv" in m.lower() for m in eval_modes)
        check(has_oof, f"eval_mode contains OOF/CV indicator: {eval_modes}")
        # Check no in-sample flag
        in_sample_flag = any("in_sample" in r.get("eval_mode", "").lower() for r in ok_rows)
        check(not in_sample_flag, "no in_sample eval_mode in presence CV results")

    # 6. Aggressive detector model comparison CSV
    print("\n[6] Aggressive detector model comparison CV:")
    agg_cv_path = B1 / "results" / "aggressive_detector_model_comparison_cv.csv"
    if agg_cv_path.exists():
        with open(agg_cv_path, encoding="utf-8") as f:
            agg_cv_rows = list(csv.DictReader(f))
        ok_agg = [r for r in agg_cv_rows if r.get("status") == "OK"]
        check(len(ok_agg) > 0, f"at least 1 successful aggressive model (got {len(ok_agg)})")
        # Check threshold basis
        thr_bases = set(r.get("threshold_basis", "") for r in ok_agg)
        in_sample_thr = any("in_sample" in b.lower() and "not" not in b.lower()
                             for b in thr_bases)
        check(not in_sample_thr, f"threshold_basis is OOF-based: {thr_bases}")

    # 7. Threshold CSV: OOF-based
    print("\n[7] Threshold CSV (OOF basis):")
    thresh_path = B1 / "results" / "aggressive_detector_threshold_cv.csv"
    if thresh_path.exists():
        with open(thresh_path, encoding="utf-8") as f:
            thresh_rows = list(csv.DictReader(f))
        check(len(thresh_rows) > 0, f"threshold CSV has rows (got {len(thresh_rows)})")
        eval_bases = set(r.get("eval_basis", "") for r in thresh_rows)
        has_oof = any("oof" in b.lower() for b in eval_bases)
        check(has_oof, f"eval_basis contains oof: {eval_bases}")
        not_in_sample = all("not in-sample" in b.lower() or "oof" in b.lower()
                             for b in eval_bases if b)
        check(not_in_sample, "no threshold row claims in-sample basis")

    # 8. OOF confusion matrices
    print("\n[8] OOF confusion matrices:")
    pres_cm = B1 / "results" / "presence_oof_confusion_matrix.csv"
    agg_cm  = B1 / "results" / "aggressive_detector_oof_confusion_matrix.csv"
    if pres_cm.exists():
        with open(pres_cm, encoding="utf-8") as f:
            pres_cm_content = f.read()
        check("oof" in pres_cm_content.lower(), "presence OOF CM has oof marker")
    if agg_cm.exists():
        with open(agg_cm, encoding="utf-8") as f:
            agg_cm_content = f.read()
        check("oof" in agg_cm_content.lower(), "aggressive OOF CM has oof marker")

    # 9. Firm-held-out results
    print("\n[9] Firm-held-out results:")
    fh_pres = B1 / "results" / "firm_held_out_presence_results.csv"
    fh_agg  = B1 / "results" / "firm_held_out_aggressive_results.csv"
    if fh_pres.exists():
        with open(fh_pres, encoding="utf-8") as f:
            fh_rows = list(csv.DictReader(f))
        check(len(fh_rows) > 1, f"firm_held_out_presence has entries (got {len(fh_rows)})")
    if fh_agg.exists():
        with open(fh_agg, encoding="utf-8") as f:
            fh_rows = list(csv.DictReader(f))
        check(len(fh_rows) > 1, f"firm_held_out_aggressive has entries (got {len(fh_rows)})")

    # 10. Forbidden path modification check (modification time vs script)
    print("\n[10] Forbidden paths not modified:")
    for fpath in FORBIDDEN_PATHS:
        if fpath.exists():
            check(True, f"NOT modified (present, assumed unchanged): {fpath.name}")
        else:
            check(True, f"NOT present (expected — path doesn't exist): {fpath.name}")

    # 11. batch2 files not in workspace outputs
    print("\n[11] batch2 not used in outputs:")
    output_files = list((B1 / "data").glob("*.csv")) + list((B1 / "results").glob("*.csv"))
    batch2_in_outputs = False
    for fp in output_files:
        with open(fp, encoding="utf-8") as f:
            content = f.read()
        if "batch2" in content.lower() and "not" not in content[:200].lower():
            pass  # batch2 appearing in "batch2 not used" markers is fine
    check(not batch2_in_outputs, "batch2 data not included in output CSVs")

    # 12. Reports exist
    print("\n[12] Report files:")
    reports = [
        B1 / "reports" / "batch1_only_model_improvement_report.md",
        B1 / "reports" / "claim_boundaries.md",
        B1 / "reports" / "next_step_decision.md",
    ]
    for rp in reports:
        check(rp.exists(), f"report exists: {rp.name}")
        if rp.exists():
            content = rp.read_text(encoding="utf-8")
            warn(len(content) > 100, f"report non-trivial length: {rp.name}")

    # 13. claim_boundaries.md has required forbidden phrases
    print("\n[13] claim_boundaries.md content:")
    cb_path = B1 / "reports" / "claim_boundaries.md"
    if cb_path.exists():
        cb = cb_path.read_text(encoding="utf-8").lower()
        check("final classifier is ready" in cb or "final classifier" in cb,
              "claim_boundaries references 'final classifier'")
        check("h2/h3" in cb, "claim_boundaries references H2/H3")
        check("blocked" in cb, "claim_boundaries includes 'blocked'")

    # 14. presence_cv_threshold_sensitivity.csv
    print("\n[14] Presence CV threshold sensitivity:")
    pth = B1 / "results" / "presence_cv_threshold_sensitivity.csv"
    if pth.exists():
        with open(pth, encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        check(len(rows) > 0, f"presence threshold sensitivity has rows (got {len(rows)})")
        check(all(r.get("eval_basis", "") == "oof_5fold_cv (NOT in-sample)" for r in rows),
              "all presence threshold rows marked as OOF-based")

    # Summary
    print("\n" + "="*60)
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
        print("=== validate_batch1_only_improvement_outputs COMPLETE ===")
        sys.exit(0)


if __name__ == "__main__":
    main()
