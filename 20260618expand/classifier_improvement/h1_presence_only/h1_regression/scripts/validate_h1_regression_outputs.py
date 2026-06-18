"""validate_h1_regression_outputs.py — validates H1 simple OLS outputs."""

from __future__ import annotations
import csv, sys
from pathlib import Path

ROOT  = Path(__file__).resolve().parents[5]
H1REG = ROOT / "20260618expand" / "classifier_improvement" / "h1_presence_only" / "h1_regression"
RES   = H1REG / "results"
REP   = H1REG / "reports"

REQUIRED = [
    RES / "h1_regression_main_results.csv",
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

    print("\n[2] Main results — simple OLS only:")
    mp = RES / "h1_regression_main_results.csv"
    if mp.exists():
        with open(mp, encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        check(len(rows) == 1, f"main results has exactly 1 row (got {len(rows)})")
        r = rows[0]
        check(r.get("regression_status") == "exploratory", "regression_status=exploratory")
        check("simple" in r.get("method", "").lower(), "method field mentions 'simple'")
        check("no fe" in r.get("method", "").lower() or "no fixed" in r.get("method", "").lower(),
              "method field explicitly states no FE")
        check(r.get("predictor") == "h1_humor_presence_pred_t50", "predictor=t50")
        check(r.get("dv") == "log_total_engagement", "dv=log_total_engagement")
        check("intercept" in r, "intercept column present")
        check("coef" in r, "coef column present")
        check("r_squared" in r, "r_squared column present (not r_sq_within)")

        # FE-related columns must NOT be present
        fe_cols = {"fe", "r_sq_within", "se_hc1", "t_hc1", "p_hc1",
                   "sig_hc1_5pct", "main_predictor"}
        found_fe_cols = [c for c in r.keys() if c in fe_cols]
        check(len(found_fe_cols) == 0,
              f"no FE/HC1 columns in output (found: {found_fe_cols})")

        try:
            coef = float(r.get("coef", "nan"))
            check(not (coef != coef), f"coef is valid float: {coef}")
        except ValueError:
            errors.append("FAIL: coef is not a valid float")
        try:
            p = float(r.get("p_value", "1"))
            warn(p < 0.05, f"p_value < 0.05 (got {p:.6f})")
        except ValueError:
            pass
        try:
            n = int(r.get("n_obs", 0))
            check(n > 60000, f"n_obs > 60000 (got {n})")
        except ValueError:
            pass

    print("\n[3] Robustness file — must NOT contain active spec results:")
    rp = RES / "h1_regression_robustness_results.csv"
    if rp.exists():
        with open(rp, encoding="utf-8") as f:
            rrows = list(csv.DictReader(f))
        active_specs = [r for r in rrows if r.get("status") != "not_run_simple_ols_only"
                        and "spec_label" in r]
        check(len(active_specs) == 0,
              f"robustness file has no active specs (found {len(active_specs)} active rows)")

    print("\n[4] Model summary:")
    sp = RES / "h1_regression_model_summary.csv"
    if sp.exists():
        with open(sp, encoding="utf-8") as f:
            srows = list(csv.DictReader(f))
        check(len(srows) == 1, f"model_summary has exactly 1 row (simple OLS only; got {len(srows)})")
        check("r_squared" in srows[0], "model_summary has r_squared column")
        check("r_sq_within" not in srows[0], "model_summary does NOT have r_sq_within")

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

    print("\n[6] Reports — must NOT contain FE/HC1/robustness language:")
    memo = REP / "h1_regression_memo.md"
    cb   = REP / "h1_regression_claim_boundaries.md"
    forbidden_phrases = [
        "firm fixed effects", "month fixed effects", "two-way fe", "demeaning",
        "hc1", "robust se", "clustered se",
        "robustness specifications are significant",
    ]
    for fp, label in [(memo, "memo"), (cb, "claim_boundaries")]:
        if fp.exists():
            text = fp.read_text(encoding="utf-8").lower()
            check("exploratory" in text, f"{label} mentions 'exploratory'")
            check("simple ols" in text, f"{label} mentions 'simple ols'")
            check("no fixed effects" in text or "no fe" in text,
                  f"{label} states 'no fixed effects'")
            check("no control" in text,
                  f"{label} states 'no control'")
            check("not a causal" in text or "not causal" in text or "causal" in text,
                  f"{label} mentions causal limitation")
            check("provisional" in text, f"{label} mentions 'provisional'")
            for phrase in forbidden_phrases:
                bad = phrase in text and "prohibited" not in text[max(0, text.find(phrase)-100):text.find(phrase)+100]
                if bad:
                    warnings.append(f"WARN: {label} may contain forbidden phrase: '{phrase}'")
                    print(f"  WARN: {label} may contain forbidden phrase: '{phrase}'")

    print("\n[7] No H2/H3 output present:")
    h23 = (list(H1REG.rglob("*h2*")) + list(H1REG.rglob("*h3*")) +
           list(H1REG.rglob("*aggressive*")))
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
