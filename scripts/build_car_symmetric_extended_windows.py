#!/usr/bin/env python3
"""
build_car_symmetric_extended_windows.py

Gemini Pre-Audit Integration: compute CAR_m3_p3 and CAR_m5_p5 from daily return panel
using per-event market model parameters (alpha, beta). Updates five existing output files.

Abnormal return formula (market model):
    AR_it = firm_return_it - (alpha_i + beta_i * market_return_it)

FORBIDDEN (enforced via manifest flags):
  - ticker / company / overall-average alpha or beta
  - renaming CAR_0_p3 to CAR_m3_p3 or CAR_0_p5 to CAR_m5_p5
  - using firm_return sum as CAR without market-model adjustment
  - overwriting existing CAR_m1_p1 (cross-check only)
  - causal claims in manifest
  - automatic regression execution
"""

import argparse
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

SCRIPT_VERSION = "1.0.0"
DESCRIPTION = "Gemini Pre-Audit: CAR_m3_p3 / CAR_m5_p5 from daily return panel"

# Cross-check: CONDITIONAL FAIL if >5% of rows have abs_diff > this threshold
CAR_M1P1_CROSSCHECK_THRESHOLD = 1e-6
CAR_M1P1_CROSSCHECK_FAIL_RATE = 0.05


def parse_args():
    p = argparse.ArgumentParser(description=DESCRIPTION)
    p.add_argument("--daily-returns", required=True,
                   help="daily_market_data_10k_events.csv (firm_return, market_return per event-day)")
    p.add_argument("--estimation-diagnostics", required=True,
                   help="event_study_estimation_diagnostics.csv (market_model_alpha, market_model_beta per event_id)")
    p.add_argument("--event-study-dataset", required=True,
                   help="ai_10k_event_study_analysis_dataset.csv (for (ticker,filing_date)→event_id mapping)")
    p.add_argument("--existing-car-panel", required=True)
    p.add_argument("--existing-linkage", required=True)
    p.add_argument("--existing-regression-master", required=True)
    p.add_argument("--existing-car-manifest", required=True)
    p.add_argument("--existing-regression-manifest", required=True)
    p.add_argument("--out-car-panel", required=True)
    p.add_argument("--out-linkage", required=True)
    p.add_argument("--out-regression-master", required=True)
    p.add_argument("--out-car-manifest", required=True)
    p.add_argument("--out-regression-manifest", required=True)
    return p.parse_args()


def check_required_inputs(args):
    """Exit code 2 = missing required input files (not a script error)."""
    missing = []
    for attr, label in [
        ("daily_returns", "daily_market_data_10k_events.csv"),
        ("estimation_diagnostics", "event_study_estimation_diagnostics.csv"),
    ]:
        path = getattr(args, attr.replace("-", "_"))
        if not Path(path).exists():
            missing.append(f"  {label}  →  {path}")
    if missing:
        print("ERROR [exit 2 — missing inputs]", file=sys.stderr)
        print("The following files must be copied from the korea_uni source repo to", file=sys.stderr)
        print("data/external/korea_uni/ before this script can run:", file=sys.stderr)
        for m in missing:
            print(m, file=sys.stderr)
        sys.exit(2)


def load_csv_rows(path, encoding="utf-8-sig"):
    with open(path, encoding=encoding, newline="") as f:
        reader = csv.DictReader(f)
        return list(reader), reader.fieldnames


def safe_float(val, default=None):
    if val is None or str(val).strip() in ("", "NA", "nan", "NaN", "None", "null"):
        return default
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


def safe_int(val, default=None):
    if val is None or str(val).strip() in ("", "NA", "nan", "NaN", "None", "null"):
        return default
    try:
        return int(float(str(val).strip()))
    except (ValueError, TypeError):
        return default


# ── Join-key helpers ────────────────────────────────────────────────────────

def build_ticker_date_to_event_id(event_study_rows):
    """
    Build {(ticker_upper, filing_date): event_id_estimate} from event study dataset.
    event_id_estimate uses padded-CIK format matching market-data pipeline.
    """
    idx = {}
    for row in event_study_rows:
        ticker = (row.get("ticker") or "").strip().upper()
        filing_date = (row.get("filing_date") or "").strip()
        eid = (row.get("event_id_estimate") or "").strip()
        if ticker and filing_date and eid:
            idx[(ticker, filing_date)] = eid
    return idx


def build_cik_date_to_event_id(event_study_rows):
    """
    Fallback: {(cik_padded_10, filing_date): event_id_estimate}.
    event_id_estimate CIK portion is zero-padded to 10 digits.
    """
    idx = {}
    for row in event_study_rows:
        cik_raw = (row.get("cik") or "").strip()
        cik10 = cik_raw.lstrip("0").zfill(10) if cik_raw else ""
        filing_date = (row.get("filing_date") or "").strip()
        eid = (row.get("event_id_estimate") or "").strip()
        if cik10 and filing_date and eid:
            idx[(cik10, filing_date)] = eid
    return idx


def lookup_event_id(row, ticker_date_idx, cik_date_idx):
    """
    Look up event_id_estimate for a panel row (car_panel / linkage / regression_master).
    Primary key: (ticker, filing_date). Fallback: (cik padded, filing_date).
    """
    ticker = (row.get("ticker") or "").strip().upper()
    filing_date = (row.get("filing_date") or "").strip()
    eid = ticker_date_idx.get((ticker, filing_date))
    if eid:
        return eid
    # Fallback via cik
    cik_raw = (row.get("cik") or "").strip()
    if cik_raw:
        cik10 = cik_raw.lstrip("0").zfill(10)
        eid = cik_date_idx.get((cik10, filing_date))
    return eid


# ── Estimation diagnostics ───────────────────────────────────────────────────

def load_estimation_diagnostics(path):
    """
    Returns {event_id: {"alpha": float, "beta": float}}.
    event_id must be joined at the event level — never averaged across events.
    """
    rows, _ = load_csv_rows(path)
    if not rows:
        print("ERROR: estimation diagnostics file is empty.", file=sys.stderr)
        sys.exit(1)

    # Detect alpha/beta column names (allow minor variations)
    sample = rows[0]
    cols = list(sample.keys())
    alpha_col = next((c for c in cols if c.lower() in ("market_model_alpha", "alpha", "mm_alpha", "est_alpha")), None)
    beta_col = next((c for c in cols if c.lower() in ("market_model_beta", "beta", "mm_beta", "est_beta")), None)

    if alpha_col is None or beta_col is None:
        print(f"ERROR: Cannot find alpha/beta columns in estimation diagnostics.", file=sys.stderr)
        print(f"  Columns found: {cols}", file=sys.stderr)
        print(f"  Expected: market_model_alpha, market_model_beta (or alpha, beta)", file=sys.stderr)
        sys.exit(1)

    diag = {}
    missing_count = 0
    for row in rows:
        eid = (row.get("event_id") or "").strip()
        if not eid:
            continue
        alpha = safe_float(row.get(alpha_col))
        beta = safe_float(row.get(beta_col))
        if alpha is None or beta is None:
            missing_count += 1
            continue
        diag[eid] = {"alpha": alpha, "beta": beta}

    return diag, missing_count, len(rows), alpha_col, beta_col


# ── Daily return panel ────────────────────────────────────────────────────────

def load_daily_returns(path):
    """
    Returns {event_id: {trading_day_relative: {"firm_return": float, "market_return": float}}}.
    Also returns column name metadata for manifest.
    """
    rows, _ = load_csv_rows(path)
    if not rows:
        print("ERROR: daily returns file is empty.", file=sys.stderr)
        sys.exit(1)

    cols = list(rows[0].keys())
    col_lower = {c.lower(): c for c in cols}

    # Detect firm return column
    firm_candidates = ["firm_return", "ret_firm", "daily_firm_return", "firm_daily_return",
                       "return_firm", "stock_return", "firm_ret"]
    firm_col = next((col_lower[c] for c in firm_candidates if c in col_lower), None)

    # Detect market return column
    market_candidates = ["market_return", "ret_market", "daily_market_return", "market_daily_return",
                         "return_market", "benchmark_return", "market_ret", "index_return"]
    market_col = next((col_lower[c] for c in market_candidates if c in col_lower), None)

    # Detect trading day relative column
    day_candidates = ["relative_trading_day", "trading_day_relative", "event_day",
                      "relative_day", "day_relative", "t", "rel_day", "event_day_rel", "day"]
    day_col = next((col_lower[c] for c in day_candidates if c in col_lower), None)

    if not all([firm_col, market_col, day_col]):
        print("ERROR: Cannot identify required columns in daily returns file.", file=sys.stderr)
        print(f"  Columns: {cols}", file=sys.stderr)
        print(f"  Detected: firm={firm_col}, market={market_col}, day={day_col}", file=sys.stderr)
        print("  Expected: firm_return (or similar), market_return (or similar),", file=sys.stderr)
        print("            trading_day_relative (or event_day / t)", file=sys.stderr)
        sys.exit(1)

    # Determine return definition from column name
    fc_lower = firm_col.lower()
    if "log" in fc_lower:
        return_def = "log_return"
        return_def_uncertain = False
    elif any(k in fc_lower for k in ["pct", "simple", "percent", "gross"]):
        return_def = "simple_return"
        return_def_uncertain = False
    else:
        return_def = "assumed_consistent_with_market_model_estimation"
        return_def_uncertain = True

    daily = defaultdict(dict)
    parse_errors = 0

    for row in rows:
        eid = (row.get("event_id") or "").strip()
        if not eid:
            continue
        day = safe_int(row.get(day_col))
        fr = safe_float(row.get(firm_col))
        mr = safe_float(row.get(market_col))
        if day is None or fr is None or mr is None:
            parse_errors += 1
            continue
        daily[eid][day] = {"firm_return": fr, "market_return": mr}

    return dict(daily), firm_col, market_col, day_col, return_def, return_def_uncertain, parse_errors


# ── CAR computation ───────────────────────────────────────────────────────────

def compute_car_window(ar_by_day, low, high):
    """
    Sum AR over [low..high] trading days (inclusive).
    Returns: (car_or_None, window_n, nonmissing_ar_n, complete_window)
    """
    expected_n = high - low + 1
    car = 0.0
    n_present = 0
    for day in range(low, high + 1):
        if day in ar_by_day:
            car += ar_by_day[day]
            n_present += 1
    if n_present == 0:
        return None, expected_n, 0, False
    return car, expected_n, n_present, (n_present == expected_n)


# ── Cross-check ───────────────────────────────────────────────────────────────

def evaluate_crosscheck(crosscheck_rows):
    n = len(crosscheck_rows)
    if n == 0:
        return {
            "n": 0, "n_fail": 0, "fail_rate": 0.0,
            "mean_abs_diff": 0.0, "median_abs_diff": 0.0, "max_abs_diff": 0.0,
            "pass": True, "status": "PASS_NO_OVERLAP",
            "note": "No overlapping events for cross-check.",
        }
    diffs = sorted(r["abs_diff"] for r in crosscheck_rows)
    n_fail = sum(1 for d in diffs if d > CAR_M1P1_CROSSCHECK_THRESHOLD)
    fail_rate = n_fail / n
    mean_diff = sum(diffs) / n
    median_diff = diffs[n // 2]
    max_diff = diffs[-1]
    ok = fail_rate <= CAR_M1P1_CROSSCHECK_FAIL_RATE
    return {
        "n": n,
        "n_fail": n_fail,
        "fail_rate": round(fail_rate, 6),
        "mean_abs_diff": round(mean_diff, 10),
        "median_abs_diff": round(median_diff, 10),
        "max_abs_diff": round(max_diff, 10),
        "pass": ok,
        "status": "PASS" if ok else "CONDITIONAL_FAIL",
        "note": (
            f"{fail_rate:.1%} of rows have |recomputed - existing| > 1e-6; "
            + ("within acceptable tolerance." if ok
               else f"exceeds {CAR_M1P1_CROSSCHECK_FAIL_RATE:.0%} threshold. "
                    "Review return definition (log vs simple) and alpha/beta source.")
        ),
    }


# ── CSV writer ────────────────────────────────────────────────────────────────

def write_csv(path, rows, fieldnames):
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    args = parse_args()
    check_required_inputs(args)

    print(f"=== {DESCRIPTION} (v{SCRIPT_VERSION}) ===\n")

    # 1. Load event study dataset — build (ticker, filing_date) → event_id mapping
    print("Loading event study dataset for join-key mapping...")
    es_rows, _ = load_csv_rows(args.event_study_dataset)
    ticker_date_idx = build_ticker_date_to_event_id(es_rows)
    cik_date_idx = build_cik_date_to_event_id(es_rows)
    print(f"  {len(ticker_date_idx)} ticker-date keys, {len(cik_date_idx)} cik-date keys")

    # Build event_id → existing CAR_m1_p1 from event study (for cross-check)
    existing_car_m1p1_by_eid = {}
    for row in es_rows:
        eid = (row.get("event_id_estimate") or "").strip()
        v = safe_float(row.get("CAR_m1_p1"))
        if eid and v is not None:
            existing_car_m1p1_by_eid[eid] = v

    # 2. Load estimation diagnostics
    print("Loading estimation diagnostics...")
    diag_idx, diag_missing, diag_total, alpha_col, beta_col = load_estimation_diagnostics(
        args.estimation_diagnostics
    )
    print(f"  {len(diag_idx)} events with alpha/beta (of {diag_total} rows; {diag_missing} missing)")
    print(f"  alpha column: {alpha_col}, beta column: {beta_col}")

    # 3. Load daily return panel
    print("Loading daily return panel...")
    daily_panel, firm_col, market_col, day_col, return_def, return_def_uncertain, parse_errs = (
        load_daily_returns(args.daily_returns)
    )
    n_event_days = sum(len(v) for v in daily_panel.values())
    print(f"  {len(daily_panel)} events, {n_event_days} event-day rows ({parse_errs} skipped)")
    print(f"  Columns: firm={firm_col}, market={market_col}, day={day_col}")
    print(f"  Return definition: {return_def} (uncertain={return_def_uncertain})")

    # 4. Compute AR and CAR for all events in daily panel
    print("\nComputing abnormal returns and CAR windows...")
    computed = {}        # event_id → computed fields
    crosscheck_rows = []

    n_no_diag = 0
    n_no_daily = 0
    n_computed = 0

    all_eids = set(daily_panel) | set(diag_idx)

    for eid in all_eids:
        params = diag_idx.get(eid)
        daily_data = daily_panel.get(eid, {})

        base = {
            "CAR_m1_p1_recomputed": None,
            "CAR_m3_p3": None,
            "CAR_m5_p5": None,
            "CAR_m3_p3_window_n": 7,
            "CAR_m3_p3_nonmissing_ar_n": 0,
            "CAR_m3_p3_complete_window": False,
            "CAR_m5_p5_window_n": 11,
            "CAR_m5_p5_nonmissing_ar_n": 0,
            "CAR_m5_p5_complete_window": False,
            "ar_computation_status": "",
        }

        if params is None:
            base["ar_computation_status"] = "missing_alpha_beta"
            n_no_diag += 1
            computed[eid] = base
            continue

        if not daily_data:
            base["ar_computation_status"] = "missing_daily_data"
            n_no_daily += 1
            computed[eid] = base
            continue

        alpha = params["alpha"]
        beta = params["beta"]

        # Compute per-day AR for all days present in daily panel
        ar_by_day = {
            day: d["firm_return"] - (alpha + beta * d["market_return"])
            for day, d in daily_data.items()
        }

        # CAR_m1_p1 recomputed (cross-check only — do NOT overwrite existing)
        car_m1p1_re, _, n_m1p1, _ = compute_car_window(ar_by_day, -1, 1)

        # CAR_m3_p3
        car_m3p3, n_m3, nonmiss_m3, comp_m3 = compute_car_window(ar_by_day, -3, 3)

        # CAR_m5_p5
        car_m5p5, n_m5, nonmiss_m5, comp_m5 = compute_car_window(ar_by_day, -5, 5)

        # CAR_m1_p1 cross-check vs existing
        existing_v = existing_car_m1p1_by_eid.get(eid)
        if car_m1p1_re is not None and existing_v is not None:
            crosscheck_rows.append({
                "event_id": eid,
                "existing": existing_v,
                "recomputed": car_m1p1_re,
                "abs_diff": abs(car_m1p1_re - existing_v),
            })

        computed[eid] = {
            "CAR_m1_p1_recomputed": car_m1p1_re,
            "CAR_m3_p3": car_m3p3,
            "CAR_m5_p5": car_m5p5,
            "CAR_m3_p3_window_n": n_m3,
            "CAR_m3_p3_nonmissing_ar_n": nonmiss_m3,
            "CAR_m3_p3_complete_window": comp_m3,
            "CAR_m5_p5_window_n": n_m5,
            "CAR_m5_p5_nonmissing_ar_n": nonmiss_m5,
            "CAR_m5_p5_complete_window": comp_m5,
            "ar_computation_status": "computed",
        }
        n_computed += 1

    xcheck = evaluate_crosscheck(crosscheck_rows)
    print(f"  Computed: {n_computed}  |  no-diag: {n_no_diag}  |  no-daily: {n_no_daily}")
    print(f"\n  CAR_m1_p1 cross-check ({xcheck['n']} rows):")
    print(f"    mean|diff|={xcheck['mean_abs_diff']:.2e}  "
          f"median={xcheck['median_abs_diff']:.2e}  "
          f"max={xcheck['max_abs_diff']:.2e}")
    print(f"    rows > 1e-6: {xcheck['n_fail']} ({xcheck['fail_rate']:.1%})  "
          f"→  status: {xcheck['status']}")
    if xcheck["status"] == "CONDITIONAL_FAIL":
        print(f"    *** CONDITIONAL FAIL: {xcheck['note']} ***")

    # 5. Update CAR event panel
    print("\nUpdating CAR event panel...")
    car_rows, car_fieldnames = load_csv_rows(args.existing_car_panel)

    NEW_CAR_COLS = [
        "CAR_m3_p3_window_n", "CAR_m3_p3_nonmissing_ar_n", "CAR_m3_p3_complete_window",
        "CAR_m5_p5_window_n", "CAR_m5_p5_nonmissing_ar_n", "CAR_m5_p5_complete_window",
        "CAR_m1_p1_recomputed", "ar_computation_status", "crosscheck_pass",
    ]
    for col in NEW_CAR_COLS:
        if col not in car_fieldnames:
            car_fieldnames.append(col)

    n_m3_car = 0
    n_m5_car = 0
    updated_car_rows = []
    for row in car_rows:
        eid = lookup_event_id(row, ticker_date_idx, cik_date_idx)
        ext = computed.get(eid, {}) if eid else {}

        m3 = ext.get("CAR_m3_p3")
        m5 = ext.get("CAR_m5_p5")
        m1re = ext.get("CAR_m1_p1_recomputed")

        # Update existing placeholder columns (already present in file)
        if m3 is not None:
            row["CAR_m3_p3"] = round(m3, 8)
            row["CAR_m3_p3_available"] = True
            n_m3_car += 1
        if m5 is not None:
            row["CAR_m5_p5"] = round(m5, 8)
            row["CAR_m5_p5_available"] = True
            n_m5_car += 1

        # New columns
        row["CAR_m3_p3_window_n"] = ext.get("CAR_m3_p3_window_n", 7)
        row["CAR_m3_p3_nonmissing_ar_n"] = ext.get("CAR_m3_p3_nonmissing_ar_n", 0)
        row["CAR_m3_p3_complete_window"] = ext.get("CAR_m3_p3_complete_window", False)
        row["CAR_m5_p5_window_n"] = ext.get("CAR_m5_p5_window_n", 11)
        row["CAR_m5_p5_nonmissing_ar_n"] = ext.get("CAR_m5_p5_nonmissing_ar_n", 0)
        row["CAR_m5_p5_complete_window"] = ext.get("CAR_m5_p5_complete_window", False)
        row["CAR_m1_p1_recomputed"] = "" if m1re is None else round(m1re, 8)
        row["ar_computation_status"] = ext.get("ar_computation_status", "event_id_not_found")
        row["crosscheck_pass"] = xcheck["pass"]

        updated_car_rows.append(row)

    write_csv(args.out_car_panel, updated_car_rows, car_fieldnames)
    print(f"  CAR_m3_p3: {n_m3_car}/{len(updated_car_rows)}  CAR_m5_p5: {n_m5_car}/{len(updated_car_rows)}")
    print(f"  Written: {args.out_car_panel}")

    # 6. Update humor-CAR linkage panel
    print("\nUpdating humor-CAR linkage panel...")
    link_rows, link_fieldnames = load_csv_rows(args.existing_linkage)

    NEW_LINK_COLS = [
        "CAR_m3_p3_window_n", "CAR_m3_p3_nonmissing_ar_n", "CAR_m3_p3_complete_window",
        "CAR_m5_p5_window_n", "CAR_m5_p5_nonmissing_ar_n", "CAR_m5_p5_complete_window",
        "ar_computation_status",
    ]
    for col in NEW_LINK_COLS:
        if col not in link_fieldnames:
            link_fieldnames.append(col)

    n_m3_link = 0
    n_m5_link = 0
    updated_link_rows = []
    for row in link_rows:
        eid = lookup_event_id(row, ticker_date_idx, cik_date_idx)
        ext = computed.get(eid, {}) if eid else {}

        m3 = ext.get("CAR_m3_p3")
        m5 = ext.get("CAR_m5_p5")

        if m3 is not None:
            row["CAR_m3_p3"] = round(m3, 8)
            row["CAR_m3_p3_available"] = True
            row["join_ready_for_CAR_m3_p3"] = ext.get("CAR_m3_p3_complete_window", False)
            n_m3_link += 1
        if m5 is not None:
            row["CAR_m5_p5"] = round(m5, 8)
            row["CAR_m5_p5_available"] = True
            row["join_ready_for_CAR_m5_p5"] = ext.get("CAR_m5_p5_complete_window", False)
            n_m5_link += 1

        row["CAR_m3_p3_window_n"] = ext.get("CAR_m3_p3_window_n", 7)
        row["CAR_m3_p3_nonmissing_ar_n"] = ext.get("CAR_m3_p3_nonmissing_ar_n", 0)
        row["CAR_m3_p3_complete_window"] = ext.get("CAR_m3_p3_complete_window", False)
        row["CAR_m5_p5_window_n"] = ext.get("CAR_m5_p5_window_n", 11)
        row["CAR_m5_p5_nonmissing_ar_n"] = ext.get("CAR_m5_p5_nonmissing_ar_n", 0)
        row["CAR_m5_p5_complete_window"] = ext.get("CAR_m5_p5_complete_window", False)
        row["ar_computation_status"] = ext.get("ar_computation_status", "event_id_not_found")

        updated_link_rows.append(row)

    write_csv(args.out_linkage, updated_link_rows, link_fieldnames)
    print(f"  CAR_m3_p3: {n_m3_link}/{len(updated_link_rows)}  CAR_m5_p5: {n_m5_link}/{len(updated_link_rows)}")
    print(f"  Written: {args.out_linkage}")

    # 7. Update regression master
    print("\nUpdating regression master...")
    master_rows, master_fieldnames = load_csv_rows(args.existing_regression_master)

    NEW_MASTER_COLS = [
        "CAR_m3_p3_complete_window", "CAR_m5_p5_complete_window", "ar_computation_status",
    ]
    for col in NEW_MASTER_COLS:
        if col not in master_fieldnames:
            master_fieldnames.append(col)

    n_m3_master = 0
    n_m5_master = 0
    n_m3_complete = 0
    n_m5_complete = 0
    updated_master_rows = []
    for row in master_rows:
        eid = lookup_event_id(row, ticker_date_idx, cik_date_idx)
        ext = computed.get(eid, {}) if eid else {}

        m3 = ext.get("CAR_m3_p3")
        m5 = ext.get("CAR_m5_p5")

        if m3 is not None:
            row["CAR_m3_p3"] = round(m3, 8)
            row["join_ready_for_CAR_m3_p3"] = ext.get("CAR_m3_p3_complete_window", False)
            n_m3_master += 1
            if ext.get("CAR_m3_p3_complete_window"):
                n_m3_complete += 1
        if m5 is not None:
            row["CAR_m5_p5"] = round(m5, 8)
            row["join_ready_for_CAR_m5_p5"] = ext.get("CAR_m5_p5_complete_window", False)
            n_m5_master += 1
            if ext.get("CAR_m5_p5_complete_window"):
                n_m5_complete += 1

        row["CAR_m3_p3_complete_window"] = ext.get("CAR_m3_p3_complete_window", False)
        row["CAR_m5_p5_complete_window"] = ext.get("CAR_m5_p5_complete_window", False)
        row["ar_computation_status"] = ext.get("ar_computation_status", "event_id_not_found")

        updated_master_rows.append(row)

    write_csv(args.out_regression_master, updated_master_rows, master_fieldnames)
    print(f"  CAR_m3_p3: {n_m3_master} computed, {n_m3_complete} complete-window")
    print(f"  CAR_m5_p5: {n_m5_master} computed, {n_m5_complete} complete-window")
    print(f"  Written: {args.out_regression_master}")

    # 8. Update CAR event panel manifest
    print("\nUpdating manifests...")
    with open(args.existing_car_manifest, encoding="utf-8") as f:
        car_manifest = json.load(f)

    forbidden_ops = {
        "ticker_average_alpha_beta_used": False,
        "company_average_alpha_beta_used": False,
        "overall_average_alpha_beta_used": False,
        "CAR_0_p3_renamed_to_CAR_m3_p3": False,
        "CAR_0_p5_renamed_to_CAR_m5_p5": False,
        "firm_return_sum_used_as_CAR": False,
        "market_return_not_subtracted": False,
        "alpha_beta_not_used": False,
        "CAR_m1_p1_overwritten": False,
        "causal_claim_made": False,
        "regression_auto_run": False,
    }

    car_manifest.update({
        "gemini_preaudit_integrated": True,
        "gemini_preaudit_script_version": SCRIPT_VERSION,
        "daily_returns_file": str(args.daily_returns),
        "estimation_diagnostics_file": str(args.estimation_diagnostics),
        "ar_formula": "AR_it = firm_return_it - (alpha_i + beta_i * market_return_it)",
        "alpha_beta_join_level": "event_id",
        "alpha_beta_average_fallback_used": False,
        "firm_return_column": firm_col,
        "market_return_column": market_col,
        "trading_day_column": day_col,
        "alpha_column": alpha_col,
        "beta_column": beta_col,
        "return_definition": return_def,
        "return_definition_uncertain": return_def_uncertain,
        "events_with_alpha_beta": len(diag_idx),
        "events_with_daily_data": len(daily_panel),
        "events_computed": n_computed,
        "CAR_m3_p3_available_rows": n_m3_car,
        "CAR_m5_p5_available_rows": n_m5_car,
        "CAR_m1_p1_crosscheck": xcheck,
        "forbidden_operations": forbidden_ops,
        "regression_run": False,
        "causal_claim_made": False,
        "raw_data_modified": False,
        "humor_outputs_modified": False,
    })

    with open(args.out_car_manifest, "w", encoding="utf-8") as f:
        json.dump(car_manifest, f, indent=2, ensure_ascii=False)
    print(f"  Written: {args.out_car_manifest}")

    # 9. Update regression master manifest
    with open(args.existing_regression_manifest, encoding="utf-8") as f:
        reg_manifest = json.load(f)

    reg_manifest.update({
        "gemini_preaudit_integrated": True,
        "CAR_m3_p3_computed": True,
        "CAR_m5_p5_computed": True,
        "CAR_m3_p3_available_in_master": n_m3_master,
        "CAR_m5_p5_available_in_master": n_m5_master,
        "CAR_m3_p3_complete_window_in_master": n_m3_complete,
        "CAR_m5_p5_complete_window_in_master": n_m5_complete,
        "car_m1p1_crosscheck_pass": xcheck["pass"],
        "car_m1p1_crosscheck_status": xcheck["status"],
        "regression_run": False,
    })

    with open(args.out_regression_manifest, "w", encoding="utf-8") as f:
        json.dump(reg_manifest, f, indent=2, ensure_ascii=False)
    print(f"  Written: {args.out_regression_manifest}")

    # Final summary
    print(f"\n{'='*50}")
    print("SUMMARY")
    print(f"{'='*50}")
    print(f"Events with alpha/beta:     {len(diag_idx)}")
    print(f"Events with daily data:     {len(daily_panel)}")
    print(f"Events AR computed:         {n_computed}")
    print(f"CAR_m3_p3 (event panel):    {n_m3_car} / {len(updated_car_rows)}")
    print(f"CAR_m5_p5 (event panel):    {n_m5_car} / {len(updated_car_rows)}")
    print(f"CAR_m1_p1 cross-check:      {xcheck['status']}")
    print(f"Return definition:          {return_def} (uncertain={return_def_uncertain})")
    print(f"Regression run:             FALSE  [constraint enforced]")
    print(f"CAR_m1_p1 overwritten:      FALSE  [constraint enforced]")

    if not xcheck["pass"]:
        print(f"\nWARNING: CAR_m1_p1 CONDITIONAL FAIL — outputs written but flagged.")
        print(f"  {xcheck['note']}")
        print("  Review return definition and alpha/beta parameter source.")
        sys.exit(3)  # exit 3 = outputs written, cross-check failed


if __name__ == "__main__":
    main()
