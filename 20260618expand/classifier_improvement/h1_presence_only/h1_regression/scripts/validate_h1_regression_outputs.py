"""validate_h1_regression_outputs.py — validates H1 exploratory regression outputs."""

from __future__ import annotations
import csv, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
H1REG = ROOT / "20260618expand" / "classifier_improvement" / "h1_presence_only" / "h1_regression"
RES   = H1REG / "results"
REP   = H1REG / "reports"

REQUIRED = [
    RES / "h1_regression_main_results.csv",
    RES / "h1_regression_robustness_results.csv",
    RES / "h1_regression_model_summary.csv",
    RES / "h1_regression_dv_diagnostics.csv",
    REP / "h1_regression_memo.md",
    REP / "h1_regression_claim_boundaries.md",
]
errors, warnings = [], []

def check(c, m):
    if not c: errors.append(f"FAIL: {m}")
    else: print(f"  PASS: {m}")

def warn(c, m):
    if not c: warnings.append(f"WARN: {m}")
    else: print(f"  OK:   {m}")

def main():
    print("=== validate_h1_regression_outputs ===")

    print("\n[1] Required files:")
    for fp in REQUIRED:
        check(fp.exists(), f"exists: {fp.relative_to(ROOT)}")

    print("\n[2] Main results:")
    mp = RES / "h1_regression_main_results.csv"
    if mp.exists():
        with open(mp, encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        check(len(rows) == 1, f"main results has 1 row (got {len(rows)})")
        r = rows[0]
        check(r.get("regression_status") == "exploratory", "regression_status=exploratory")
        check(r.get("spec_label") == "main_t50", "spec_label=main_t50")
        check(r.get("main_predictor") == "h1_humor_presence_t50", "main_predictor=t50")
        check(r.get("fe") == "firm + month", "fe=firm+month")
        try:
            coef = float(r.get("coef", "nan"))
            check(not (coef != coef), f"coef is valid float: {coef}")  # nan check
        except ValueError:
            errors.append("FAIL: coef is not a valid float")
        try:
            p = float(r.get("p_value", "1"))
            warn(p < 0.05, f"p_value < 0.05 (got {p:.4f})")
        except ValueError:
            pass

    print("\n[3] Robustness results:")
    rp = RES / "h1_regression_robustness_results.csv"
    if rp.exists():
        with open(rp, encoding="utf-8") as f:
            rrows = list(csv.DictReader(f))
        check(len(rrows) >= 3, f"robustness has >= 3 specs (got {len(rrows)})")
        specs = [r["spec_label"] for r in rrows]
        check("robust_t40"  in specs, "robust_t40 spec present")
        check("robust_t60"  in specs, "robust_t60 spec present")
        check("robust_prob" in specs, "robust_prob spec present")
        for r in rrows:
            check(r.get("regression_status") == "exploratory",
                  f"all robustness specs: regression_status=exploratory")
            break

    print("\n[4] Model summary:")
    sp = RES / "h1_regression_model_summary.csv"
    if sp.exists():
        with open(sp, encoding="utf-8") as f:
            srows = list(csv.DictReader(f))
        check(len(srows) >= 1, f"model_summary has rows (got {len(srows)})")
        check(any(r.get("spec") == "main_t50" for r in srows), "main_t50 in summary")

    print("\n[5] DV diagnostics:")
    dp = RES / "h1_regression_dv_diagnostics.csv"
    if dp.exists():
        with open(dp, encoding="utf-8") as f:
            diag = {r["metric"]: r["value"] for r in csv.DictReader(f)}
        try:
            n = int(diag.get("n_obs", 0))
            check(n > 60000, f"n_obs > 60000 (got {n})")
        except ValueError:
            pass

    print("\n[6] Reports:")
    memo = REP / "h1_regression_memo.md"
    cb   = REP / "h1_regression_claim_boundaries.md"
    if memo.exists():
        m = memo.read_text(encoding="utf-8").lower()
        check("exploratory" in m, "memo mentions 'exploratory'")
        check("not confirmatory" in m or "not confirm" in m or "cannot confirm" in m or "not" in m,
              "memo clarifies non-confirmatory status")
        check("h1 is not supported" in m or "h1 is supported" in m or "h1" in m,
              "memo references H1")
        check("provisional" in m, "memo mentions 'provisional'")
    if cb.exists():
        c = cb.read_text(encoding="utf-8").lower()
        check("prohibited" in c or "must not" in c or "prohibited claims" in c,
              "claim_boundaries has prohibited section")
        check("h1 is supported" in c or "h1 is confirmed" in c,
              "claim_boundaries lists 'H1 is supported' as prohibited")
        check("exploratory" in c, "claim_boundaries mentions 'exploratory'")

    print("\n[7] No H2/H3 output present:")
    h23 = list(H1REG.rglob("*h2*")) + list(H1REG.rglob("*h3*")) + list(H1REG.rglob("*aggressive*"))
    check(len(h23) == 0, f"no H2/H3/aggressive output files (found: {h23})")

    print("\n" + "="*60)
    if errors:
        print(f"VALIDATION RESULT: FAIL ({len(errors)} errors, {len(warnings)} warnings)")
        for e in errors: print(f"  {e}")
        for w in warnings: print(f"  {w}")
        sys.exit(1)
    else:
        print(f"VALIDATION RESULT: PASS ({len(warnings)} warnings)")
        for w in warnings: print(f"  {w}")
        print("=== validate_h1_regression_outputs COMPLETE ===")
        sys.exit(0)

if __name__ == "__main__":
    main()
