#!/usr/bin/env python3
"""Build CAR symmetric event-window outcome layer for H1-H3 regression.

Tobin's Q is deferred as primary Brand Equity DV. This script builds the
current executable DV: CAR symmetric event-window outcomes from 10-K filing
events.

CAR interpretation constraints:
  - CAR is a short-window capital market response proxy.
  - CAR is a market-based brand/value response proxy (secondary DV).
  - CAR is NOT Tobin's Q and does NOT substitute for it.
  - CAR is NOT direct Brand Equity.
  - CAR is NOT consumer-based brand equity.
  - CAR results are NOT causal brand equity effects.

CAR windows implemented:
  CAR_m1_p1 = CAR[-1,+1]   3-day window   primary short-window proxy
  CAR_m3_p3 = CAR[-3,+3]   7-day window   robustness proxy
  CAR_m5_p5 = CAR[-5,+5]  11-day window   wider-window robustness

Computation rules:
  CAR_m1_p1: direct from korea_uni event study dataset if available
  CAR_m3_p3: requires daily abnormal return file; marked missing if absent
  CAR_m5_p5: requires daily abnormal return file; marked missing if absent
  Formula: CAR[a,b] = sum(abnormal_return for event_day in [a..b])

CONSTRAINTS:
  - No external API calls, no SEC collection, no market data collection.
  - No X/social media collection.
  - No arbitrary CAR value generation.
  - No imputation of missing windows.
  - CAR_0_p3 and CAR_0_p5 are NOT renamed to CAR_m3_p3/CAR_m5_p5.
  - H1-H3 regression is not executed here.

Inputs (required):
  data/external/korea_uni/ai_10k_event_study_analysis_dataset.csv
  data/derived/humor/hypothesis_variables/humor_firm_period_hypothesis_variables.csv
  data/audit/humor/hypothesis_variables/humor_hypothesis_variables_manifest.json

Inputs (optional — CAR_m3_p3, CAR_m5_p5 will be missing without this):
  data/external/korea_uni/event_window_daily_abnormal_returns.csv
  data/external/korea_uni/post_filing_market_reaction_estimates.csv

Outputs:
  data/derived/car_event_windows/car_symmetric_event_window_panel.csv
  data/derived/car_event_windows/humor_car_linkage_panel.csv
  data/derived/car_event_windows/car_window_variable_dictionary.csv
  data/audit/car_event_windows/car_symmetric_event_window_manifest.json
"""

import argparse
import calendar
import csv
import json
import re
import sys
from collections import defaultdict
from datetime import date, datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------
DEFAULT_KOREA_EVENT   = Path("data/external/korea_uni/ai_10k_event_study_analysis_dataset.csv")
DEFAULT_DAILY_AR      = Path("data/external/korea_uni/event_window_daily_abnormal_returns.csv")
DEFAULT_HUMOR_VARS    = Path("data/derived/humor/hypothesis_variables/humor_firm_period_hypothesis_variables.csv")
DEFAULT_HUMOR_MAN     = Path("data/audit/humor/hypothesis_variables/humor_hypothesis_variables_manifest.json")
DEFAULT_POST_FILING   = Path("data/external/korea_uni/post_filing_market_reaction_estimates.csv")

DEFAULT_OUT_CAR       = Path("data/derived/car_event_windows/car_symmetric_event_window_panel.csv")
DEFAULT_OUT_LINKAGE   = Path("data/derived/car_event_windows/humor_car_linkage_panel.csv")
DEFAULT_OUT_DICT      = Path("data/derived/car_event_windows/car_window_variable_dictionary.csv")
DEFAULT_OUT_MANIFEST  = Path("data/audit/car_event_windows/car_symmetric_event_window_manifest.json")

REFERENCE_DATE = date(2026, 6, 14)

# CAR windows: {name: (low, high)}
CAR_WINDOWS = {
    "CAR_m1_p1": (-1,  1),
    "CAR_m3_p3": (-3,  3),
    "CAR_m5_p5": (-5,  5),
}

# Humor columns to carry through to linkage panel
HUMOR_CARRY_COLS = [
    "humor_share",
    "humor_count",
    "total_posts",
    "humor_share_ambiguity_as_zero",
    "humor_share_ambiguity_excluded",
    "humor_share_ambiguity_as_missing",
    "humor_presence_any",
    "aggressive_share",
    "aggressive_count",
    "aggressive_humor_usage_intensity",
    "aggressive_humor_usage_intensity_sq",
    "rare_negative_humor_share",
    "ambiguity_rate",
    "high_ambiguity_flag",
    "source_x_handle_count",
    "source_x_handle_list",
]

CAR_PANEL_FIELDS = [
    "company_name", "ticker", "cik", "cik_padded",
    "target_report_year", "filing_date", "event_trading_date",
    "naics_code", "naics_sector_code", "naics_sector_name",
    "CAR_m1_p1", "CAR_m3_p3", "CAR_m5_p5",
    "CAR_m1_p1_available", "CAR_m3_p3_available", "CAR_m5_p5_available",
    "car_source", "car_calculation_status", "missing_car_reason",
    "future_date_flag", "date_alignment_warning",
]

LINKAGE_FIELDS = [
    "company_name", "period", "period_year", "period_month",
    "ticker", "cik", "target_report_year", "filing_date",
    "humor_share", "humor_count", "total_posts",
    "humor_share_ambiguity_as_zero", "humor_share_ambiguity_excluded",
    "humor_share_ambiguity_as_missing", "humor_presence_any",
    "aggressive_share", "aggressive_count",
    "aggressive_humor_usage_intensity", "aggressive_humor_usage_intensity_sq",
    "rare_negative_humor_share", "ambiguity_rate", "high_ambiguity_flag",
    "source_x_handle_count", "source_x_handle_list",
    "CAR_m1_p1", "CAR_m3_p3", "CAR_m5_p5",
    "CAR_m1_p1_available", "CAR_m3_p3_available", "CAR_m5_p5_available",
    "same_month_alignment", "prefiling_lag_1m_alignment", "prefiling_lag_3m_alignment",
    "recommended_main_alignment",
    "naics_code", "naics_sector_code", "naics_sector_name",
    "industry_homogeneity_control",
    "join_ready_for_CAR_m1_p1", "join_ready_for_CAR_m3_p3", "join_ready_for_CAR_m5_p5",
]

DICT_FIELDS = [
    "variable_name", "event_window", "window_days",
    "role", "formula", "available_in_repo", "available_rows",
    "source_file", "data_notes", "caution",
]

_NORM_SUFFIXES = re.compile(
    r"\b(inc|corp|corporation|co|company|llc|lp|ltd|plc|group|holdings|holding|the)\b\.?$",
    re.IGNORECASE,
)

def normalize_company(name: str) -> str:
    n = name.strip().lower()
    n = re.sub(r"[,\.]", " ", n)
    n = _NORM_SUFFIXES.sub("", n).strip()
    return re.sub(r"\s+", " ", n)


def yyyymm_add(yyyymm: str, months: int) -> str:
    """Add or subtract months from YYYY-MM string. Returns YYYY-MM."""
    try:
        y, m = int(yyyymm[:4]), int(yyyymm[5:7])
    except (ValueError, IndexError):
        return yyyymm
    m += months
    while m > 12:
        m -= 12
        y += 1
    while m < 1:
        m += 12
        y -= 1
    return f"{y:04d}-{m:02d}"


def filing_yyyymm(filing_date_str: str) -> str:
    return filing_date_str[:7] if filing_date_str else ""


def safe_float(val: str) -> float | None:
    try:
        v = float(str(val).strip())
        return None if v != v else v
    except (ValueError, TypeError):
        return None


def load_csv(path: Path, label: str, required: bool = True) -> list[dict] | None:
    if not path.exists():
        if required:
            print(f"ERROR: {label} not found: {path}", file=sys.stderr)
            sys.exit(1)
        print(f"  INFO: {label} not found (optional): {path}")
        return None
    with path.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    print(f"  Loaded {label}: {len(rows)} rows")
    return rows


def write_csv(path: Path, fieldnames: list[str], rows: list[dict]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    return len(rows)


# ---------------------------------------------------------------------------
# Daily abnormal return computation
# ---------------------------------------------------------------------------

def build_daily_ar_index(daily_rows: list[dict]) -> dict[tuple, dict[int, float]]:
    """Build {(ticker_upper, filing_date): {event_day: abnormal_return}}."""
    idx: dict[tuple, dict[int, float]] = defaultdict(dict)
    for r in daily_rows:
        ticker  = r.get("ticker", "").strip().upper()
        fd      = r.get("filing_date", "").strip()
        raw_day = r.get("event_day", "").strip()
        raw_ar  = r.get("abnormal_return", "").strip()
        if not ticker or not fd or not raw_day:
            continue
        try:
            day = int(float(raw_day))
            ar  = float(raw_ar)
        except (ValueError, TypeError):
            continue
        idx[(ticker, fd)][day] = ar
    return idx


def compute_car_window(
    daily_idx: dict[tuple, dict[int, float]],
    ticker: str,
    filing_date: str,
    low: int,
    high: int,
) -> float | None:
    days = daily_idx.get((ticker.upper(), filing_date), {})
    required = set(range(low, high + 1))
    if not required.issubset(days.keys()):
        return None
    return sum(days[d] for d in required)


# ---------------------------------------------------------------------------
# Build CAR event panel
# ---------------------------------------------------------------------------

def build_car_event_panel(
    event_rows: list[dict],
    daily_idx: dict[tuple, dict[int, float]],
    daily_ar_available: bool,
) -> list[dict]:
    panel = []
    for r in event_rows:
        company_name    = r.get("company_name", "").strip()
        ticker          = r.get("ticker", "").strip().upper()
        cik             = str(r.get("cik", "")).strip().lstrip("0")
        cik_padded      = r.get("cik_padded", "").strip()
        rep_year        = r.get("target_report_year", r.get("fiscal_year", "")).strip()
        filing_date     = r.get("filing_date", "").strip()
        evt_trading_dt  = r.get("event_trading_date", "").strip()

        # NAICS: sector always available; naics_code is empty in this dataset
        naics_code        = r.get("naics_code", "").strip()
        naics_sector_code = r.get("naics_sector_code", "").strip()
        naics_sector_name = r.get("naics_sector_name", "").strip()

        # CAR_m1_p1: direct from event study
        raw_m1p1  = r.get("CAR_m1_p1", "").strip()
        car_m1p1  = safe_float(raw_m1p1)
        m1p1_avail = car_m1p1 is not None

        # CAR_m3_p3, CAR_m5_p5: from daily AR or missing
        car_m3p3 = car_m5p5 = None
        if daily_ar_available:
            car_m3p3 = compute_car_window(daily_idx, ticker, filing_date, -3, 3)
            car_m5p5 = compute_car_window(daily_idx, ticker, filing_date, -5, 5)

        m3p3_avail = car_m3p3 is not None
        m5p5_avail = car_m5p5 is not None

        # Source and status descriptors
        car_source = "korea_uni_event_study_direct"
        if daily_ar_available:
            car_calculation_status = "m1p1_direct__m3p3_m5p5_from_daily_ar"
            missing_reason = "" if (m1p1_avail and m3p3_avail and m5p5_avail) else (
                "; ".join(
                    w for w, a in [("CAR_m1_p1", m1p1_avail), ("CAR_m3_p3", m3p3_avail), ("CAR_m5_p5", m5p5_avail)]
                    if not a
                )
            )
        else:
            car_calculation_status = (
                "m1p1_direct_from_dataset__m3p3_m5p5_missing_daily_ar_required"
            )
            missing_reason = (
                "CAR_m3_p3 and CAR_m5_p5 require event_window_daily_abnormal_returns.csv "
                "(not found in data/external/korea_uni/)"
                if not m1p1_avail else
                "CAR_m3_p3 and CAR_m5_p5: daily_abnormal_returns not available"
            )

        # Future date flag
        try:
            fd_date = date.fromisoformat(filing_date)
            future_flag = fd_date > REFERENCE_DATE
        except ValueError:
            future_flag = False

        date_warn = ""
        if future_flag:
            date_warn = f"filing_date {filing_date} is after reference date {REFERENCE_DATE}"

        panel.append({
            "company_name":         company_name,
            "ticker":               ticker,
            "cik":                  cik,
            "cik_padded":           cik_padded,
            "target_report_year":   rep_year,
            "filing_date":          filing_date,
            "event_trading_date":   evt_trading_dt,
            "naics_code":           naics_code,
            "naics_sector_code":    naics_sector_code,
            "naics_sector_name":    naics_sector_name,
            "CAR_m1_p1":            "" if car_m1p1 is None else round(car_m1p1, 6),
            "CAR_m3_p3":            "" if car_m3p3 is None else round(car_m3p3, 6),
            "CAR_m5_p5":            "" if car_m5p5 is None else round(car_m5p5, 6),
            "CAR_m1_p1_available":  str(m1p1_avail).lower(),
            "CAR_m3_p3_available":  str(m3p3_avail).lower(),
            "CAR_m5_p5_available":  str(m5p5_avail).lower(),
            "car_source":           car_source,
            "car_calculation_status": car_calculation_status,
            "missing_car_reason":   missing_reason,
            "future_date_flag":     str(future_flag).lower(),
            "date_alignment_warning": date_warn,
        })
    return panel


# ---------------------------------------------------------------------------
# Build humor-CAR linkage panel
# ---------------------------------------------------------------------------

def build_humor_car_linkage(
    humor_rows: list[dict],
    car_panel: list[dict],
) -> list[dict]:
    # Index CAR panel by normalized company name → list of event dicts
    car_by_company: dict[str, list[dict]] = defaultdict(list)
    for evt in car_panel:
        key = normalize_company(evt["company_name"])
        car_by_company[key].append(evt)

    linkage_rows = []

    for h in humor_rows:
        company_name = h.get("company_name", "").strip()
        period       = h.get("period", "").strip()
        if not company_name or not period:
            continue

        norm_co = normalize_company(company_name)
        events  = car_by_company.get(norm_co, [])

        # Parse period parts
        try:
            per_y, per_m = int(period[:4]), int(period[5:7])
        except (ValueError, IndexError):
            continue

        period_year  = str(per_y)
        period_month = f"{per_m:02d}"

        # For each CAR event for this company, compute alignment flags
        matched_any = False
        for evt in events:
            fd_ym = filing_yyyymm(evt.get("filing_date", ""))
            if not fd_ym:
                continue

            same_month   = (period == fd_ym)
            lag1m_target = yyyymm_add(fd_ym, -1)
            lag1m        = (period == lag1m_target)
            lag3m_range  = {yyyymm_add(fd_ym, -k) for k in range(1, 4)}
            lag3m        = (period in lag3m_range)

            if not (same_month or lag1m or lag3m):
                continue

            matched_any = True

            if lag1m or lag3m:
                recommended = "prefiling_lag_1m" if lag1m else "prefiling_lag_3m"
            elif same_month:
                recommended = "same_month (caution: simultaneity risk)"
            else:
                recommended = "no_alignment"

            car_m1p1_val    = evt.get("CAR_m1_p1", "")
            car_m3p3_val    = evt.get("CAR_m3_p3", "")
            car_m5p5_val    = evt.get("CAR_m5_p5", "")
            m1p1_avail_str  = evt.get("CAR_m1_p1_available", "false")
            m3p3_avail_str  = evt.get("CAR_m3_p3_available", "false")
            m5p5_avail_str  = evt.get("CAR_m5_p5_available", "false")
            m1p1_avail      = m1p1_avail_str == "true"
            m3p3_avail      = m3p3_avail_str == "true"
            m5p5_avail      = m5p5_avail_str == "true"

            # join_ready: CAR is available AND any alignment flag is true
            any_aligned = same_month or lag1m or lag3m
            join_m1p1 = m1p1_avail and any_aligned
            join_m3p3 = m3p3_avail and any_aligned
            join_m5p5 = m5p5_avail and any_aligned

            row = {
                "company_name":           company_name,
                "period":                 period,
                "period_year":            period_year,
                "period_month":           period_month,
                "ticker":                 evt.get("ticker", ""),
                "cik":                    evt.get("cik", ""),
                "target_report_year":     evt.get("target_report_year", ""),
                "filing_date":            evt.get("filing_date", ""),
                "CAR_m1_p1":              car_m1p1_val,
                "CAR_m3_p3":              car_m3p3_val,
                "CAR_m5_p5":              car_m5p5_val,
                "CAR_m1_p1_available":    m1p1_avail_str,
                "CAR_m3_p3_available":    m3p3_avail_str,
                "CAR_m5_p5_available":    m5p5_avail_str,
                "same_month_alignment":   str(same_month).lower(),
                "prefiling_lag_1m_alignment": str(lag1m).lower(),
                "prefiling_lag_3m_alignment": str(lag3m).lower(),
                "recommended_main_alignment": recommended,
                "naics_code":             evt.get("naics_code", ""),
                "naics_sector_code":      evt.get("naics_sector_code", ""),
                "naics_sector_name":      evt.get("naics_sector_name", ""),
                "industry_homogeneity_control": evt.get("naics_sector_code", ""),
                "join_ready_for_CAR_m1_p1": str(join_m1p1).lower(),
                "join_ready_for_CAR_m3_p3": str(join_m3p3).lower(),
                "join_ready_for_CAR_m5_p5": str(join_m5p5).lower(),
            }
            # Carry humor columns
            for col in HUMOR_CARRY_COLS:
                row[col] = h.get(col, "")

            linkage_rows.append(row)

    return linkage_rows


# ---------------------------------------------------------------------------
# Variable dictionary
# ---------------------------------------------------------------------------

def build_variable_dictionary(car_panel: list[dict], daily_ar_available: bool) -> list[dict]:
    def count_avail(field: str) -> int:
        return sum(1 for r in car_panel if r.get(field) not in ("", None))

    m1p1_rows = sum(1 for r in car_panel if r.get("CAR_m1_p1_available") == "true")
    m3p3_rows = sum(1 for r in car_panel if r.get("CAR_m3_p3_available") == "true")
    m5p5_rows = sum(1 for r in car_panel if r.get("CAR_m5_p5_available") == "true")

    return [
        {
            "variable_name":  "CAR_m1_p1",
            "event_window":   "[-1,+1]",
            "window_days":    3,
            "role":           "primary short-window market reaction proxy",
            "formula":        "sum(abnormal_return for event_day in {-1, 0, +1})",
            "available_in_repo": "true",
            "available_rows": m1p1_rows,
            "source_file":    "data/external/korea_uni/ai_10k_event_study_analysis_dataset.csv",
            "data_notes":     "Direct column from korea_uni event study. 272/273 rows populated (1 row: market_data_status=failed).",
            "caution":        "",
        },
        {
            "variable_name":  "CAR_m3_p3",
            "event_window":   "[-3,+3]",
            "window_days":    7,
            "role":           "medium short-window robustness proxy",
            "formula":        "sum(abnormal_return for event_day in {-3,-2,-1,0,+1,+2,+3})",
            "available_in_repo": "false",
            "available_rows": m3p3_rows,
            "source_file":    "data/external/korea_uni/event_window_daily_abnormal_returns.csv (NOT FOUND)",
            "data_notes":     (
                "Requires event_window_daily_abnormal_returns.csv with event_day column. "
                "NOT equivalent to CAR_0_p3 ([0,+3]). "
                "Copy daily_abnormal_returns file from korea_uni repo to enable computation."
            ),
            "caution":        "Do NOT rename CAR_0_p3 to CAR_m3_p3. They cover different event windows.",
        },
        {
            "variable_name":  "CAR_m5_p5",
            "event_window":   "[-5,+5]",
            "window_days":    11,
            "role":           "wider event-window robustness proxy",
            "formula":        "sum(abnormal_return for event_day in {-5,-4,-3,-2,-1,0,+1,+2,+3,+4,+5})",
            "available_in_repo": "false",
            "available_rows": m5p5_rows,
            "source_file":    "data/external/korea_uni/event_window_daily_abnormal_returns.csv (NOT FOUND)",
            "data_notes":     (
                "Requires event_window_daily_abnormal_returns.csv. "
                "NOT equivalent to CAR_0_p5 ([0,+5]). "
                "Wider window increases confounding event risk."
            ),
            "caution":        (
                "Confounding event risk increases with wider window. "
                "Do NOT rename CAR_0_p5 to CAR_m5_p5."
            ),
        },
        {
            "variable_name":  "CAR_0_p3",
            "event_window":   "[0,+3]",
            "window_days":    4,
            "role":           "supplemental post-filing window (NOT a symmetric window)",
            "formula":        "sum(abnormal_return for event_day in {0,+1,+2,+3})",
            "available_in_repo": "true",
            "available_rows": 272,
            "source_file":    "data/external/korea_uni/ai_10k_event_study_analysis_dataset.csv",
            "data_notes":     (
                "Available directly from event study. Asymmetric (post-filing only). "
                "Retained as supplemental outcome only — NOT equivalent to CAR_m3_p3."
            ),
            "caution":        "Not a symmetric window. Use only as supplemental analysis, not primary window.",
        },
        {
            "variable_name":  "CAR_0_p5",
            "event_window":   "[0,+5]",
            "window_days":    6,
            "role":           "supplemental post-filing window (NOT a symmetric window)",
            "formula":        "sum(abnormal_return for event_day in {0,+1,+2,+3,+4,+5})",
            "available_in_repo": "true",
            "available_rows": 272,
            "source_file":    "data/external/korea_uni/ai_10k_event_study_analysis_dataset.csv",
            "data_notes":     (
                "Available directly from event study. Asymmetric (post-filing only). "
                "Retained as supplemental outcome only — NOT equivalent to CAR_m5_p5."
            ),
            "caution":        "Not a symmetric window. Use only as supplemental analysis, not primary window.",
        },
    ]


# ---------------------------------------------------------------------------
# Manifest
# ---------------------------------------------------------------------------

def build_manifest(
    humor_rows: list[dict],
    car_panel: list[dict],
    linkage_rows: list[dict],
    daily_ar_available: bool,
    daily_ar_rows: int,
    args: argparse.Namespace,
) -> dict:
    def count_flag(rows, field, val):
        return sum(1 for r in rows if str(r.get(field, "")).lower() == str(val).lower())

    m1p1_avail = count_flag(car_panel, "CAR_m1_p1_available", "true")
    m3p3_avail = count_flag(car_panel, "CAR_m3_p3_available", "true")
    m5p5_avail = count_flag(car_panel, "CAR_m5_p5_available", "true")

    same_month_rows   = count_flag(linkage_rows, "same_month_alignment",       "true")
    lag1m_rows        = count_flag(linkage_rows, "prefiling_lag_1m_alignment", "true")
    lag3m_rows        = count_flag(linkage_rows, "prefiling_lag_3m_alignment", "true")
    join_m1p1_rows    = count_flag(linkage_rows, "join_ready_for_CAR_m1_p1",   "true")
    join_m3p3_rows    = count_flag(linkage_rows, "join_ready_for_CAR_m3_p3",   "true")
    join_m5p5_rows    = count_flag(linkage_rows, "join_ready_for_CAR_m5_p5",   "true")

    future_count = count_flag(car_panel, "future_date_flag", "true")
    requires_audit = future_count > 0

    return {
        "created_at":                        datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "reference_date":                    str(REFERENCE_DATE),
        "car_dv_note": (
            "CAR is a short-window capital market response proxy (secondary DV). "
            "Tobin's Q is deferred as primary Brand Equity DV. "
            "CAR is NOT Tobin's Q. CAR is NOT direct Brand Equity."
        ),
        "source_files": {
            "korea_uni_event_study":     str(args.korea_event),
            "daily_abnormal_returns":    str(args.daily_ar) if daily_ar_available else "not_provided",
            "humor_variables":           str(args.humor_vars),
            "humor_manifest":            str(args.humor_manifest),
        },
        "humor_input_rows":                  len(humor_rows),
        "car_event_rows":                    len(car_panel),
        "daily_abnormal_return_input_available": daily_ar_available,
        "daily_abnormal_return_rows":        daily_ar_rows,
        "CAR_m1_p1_available_rows":          m1p1_avail,
        "CAR_m3_p3_available_rows":          m3p3_avail,
        "CAR_m5_p5_available_rows":          m5p5_avail,
        "humor_car_linked_rows":             len(linkage_rows),
        "same_month_alignment_rows":         same_month_rows,
        "prefiling_lag_1m_alignment_rows":   lag1m_rows,
        "prefiling_lag_3m_alignment_rows":   lag3m_rows,
        "join_ready_for_CAR_m1_p1_rows":     join_m1p1_rows,
        "join_ready_for_CAR_m3_p3_rows":     join_m3p3_rows,
        "join_ready_for_CAR_m5_p5_rows":     join_m5p5_rows,
        "future_event_count":                future_count,
        "requires_date_audit":               requires_audit,
        "missing_car_reason": (
            "" if (m3p3_avail > 0 and m5p5_avail > 0) else
            "CAR_m3_p3 and CAR_m5_p5: daily abnormal return input not available "
            "(event_window_daily_abnormal_returns.csv not found in data/external/korea_uni/)"
        ),
        # Constraint flags — all must remain false
        "tobins_q_deferred":               True,
        "car_used_as_tobins_q":            False,
        "car_used_as_direct_brand_equity": False,
        "regression_run":                  False,
        "causal_claim_made":               False,
        "external_data_downloaded":        False,
        "sec_collection_run":              False,
        "market_data_collection_run":      False,
        "x_collection_run":                False,
        "raw_data_modified":               False,
        "humor_outputs_modified":          False,
        # Next steps
        "next_steps_to_enable_car_m3_m5": [
            "Copy event_window_daily_abnormal_returns.csv from korea_uni repo to "
            "data/external/korea_uni/event_window_daily_abnormal_returns.csv",
            "File must have columns: ticker, filing_date, event_day (integer trading-day index), "
            "abnormal_return",
            "Re-run this workflow with --daily-ar pointing to the file",
        ],
        "next_steps_to_enable_tobins_q": [
            "Obtain total_assets, total_liabilities from SEC EDGAR XBRL or Compustat",
            "Obtain stock_price_fiscal_year_end, shares_outstanding from CRSP",
            "Run build_tobins_q_brand_equity_panel.py --financial-panel <path>",
        ],
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Build CAR symmetric event-window panel and humor-CAR linkage."
    )
    parser.add_argument("--korea-event",  type=Path, default=DEFAULT_KOREA_EVENT)
    parser.add_argument("--daily-ar",     type=Path, default=DEFAULT_DAILY_AR,
                        help="Optional daily abnormal return file (required for CAR_m3_p3, CAR_m5_p5)")
    parser.add_argument("--humor-vars",   type=Path, default=DEFAULT_HUMOR_VARS)
    parser.add_argument("--humor-manifest", type=Path, default=DEFAULT_HUMOR_MAN)
    parser.add_argument("--out-car",      type=Path, default=DEFAULT_OUT_CAR)
    parser.add_argument("--out-linkage",  type=Path, default=DEFAULT_OUT_LINKAGE)
    parser.add_argument("--out-dict",     type=Path, default=DEFAULT_OUT_DICT)
    parser.add_argument("--out-manifest", type=Path, default=DEFAULT_OUT_MANIFEST)
    args = parser.parse_args()

    # ---- Load humor manifest and validate ----
    print(f"\nValidating humor manifest: {args.humor_manifest}")
    if not args.humor_manifest.exists():
        print(f"ERROR: humor manifest not found: {args.humor_manifest}", file=sys.stderr)
        sys.exit(1)
    humor_man = json.loads(args.humor_manifest.read_text(encoding="utf-8"))
    # company_period_duplicate_count is at top level
    dup_count = humor_man.get("company_period_duplicate_count", -1)
    # hypothesis_testing_ready is nested under "constraints"
    constraints = humor_man.get("constraints", {})
    ht_ready = constraints.get("hypothesis_testing_ready", humor_man.get("hypothesis_testing_ready", False))
    if dup_count != 0:
        print(f"ERROR: humor manifest company_period_duplicate_count={dup_count} (expected 0)", file=sys.stderr)
        sys.exit(1)
    if not ht_ready:
        print("ERROR: humor manifest hypothesis_testing_ready is not True", file=sys.stderr)
        sys.exit(1)
    print(f"  OK: hypothesis_testing_ready={ht_ready}, company_period_duplicate_count={dup_count}")

    # ---- Load required inputs ----
    print(f"\nLoading event study: {args.korea_event}")
    event_rows = load_csv(args.korea_event, "korea_uni event study", required=True)

    print(f"\nLoading humor variables: {args.humor_vars}")
    humor_rows = load_csv(args.humor_vars, "humor hypothesis variables", required=True)

    # ---- Load optional daily AR ----
    print(f"\nChecking daily abnormal returns: {args.daily_ar}")
    daily_rows = load_csv(args.daily_ar, "daily abnormal returns", required=False)
    daily_ar_available = daily_rows is not None
    daily_ar_count = len(daily_rows) if daily_rows else 0
    if not daily_ar_available:
        print("  WARNING: CAR_m3_p3 and CAR_m5_p5 will be marked missing.")
        print("  To compute them: provide event_window_daily_abnormal_returns.csv")
        print("  with columns: ticker, filing_date, event_day (int), abnormal_return")

    # ---- Build daily AR index ----
    daily_idx: dict = {}
    if daily_rows:
        daily_idx = build_daily_ar_index(daily_rows)
        print(f"  Daily AR index: {len(daily_idx)} (ticker, filing_date) pairs")

    # ---- Build CAR event panel ----
    print("\nBuilding CAR event panel...")
    car_panel = build_car_event_panel(event_rows, daily_idx, daily_ar_available)
    m1p1_n = sum(1 for r in car_panel if r.get("CAR_m1_p1_available") == "true")
    m3p3_n = sum(1 for r in car_panel if r.get("CAR_m3_p3_available") == "true")
    m5p5_n = sum(1 for r in car_panel if r.get("CAR_m5_p5_available") == "true")
    print(f"  CAR event panel: {len(car_panel)} rows")
    print(f"  CAR_m1_p1 available: {m1p1_n}")
    print(f"  CAR_m3_p3 available: {m3p3_n}")
    print(f"  CAR_m5_p5 available: {m5p5_n}")

    # ---- Build humor-CAR linkage ----
    print("\nBuilding humor-CAR linkage panel...")
    linkage_rows = build_humor_car_linkage(humor_rows, car_panel)
    same_n  = sum(1 for r in linkage_rows if r.get("same_month_alignment") == "true")
    lag1_n  = sum(1 for r in linkage_rows if r.get("prefiling_lag_1m_alignment") == "true")
    lag3_n  = sum(1 for r in linkage_rows if r.get("prefiling_lag_3m_alignment") == "true")
    jr1_n   = sum(1 for r in linkage_rows if r.get("join_ready_for_CAR_m1_p1") == "true")
    print(f"  Linked rows: {len(linkage_rows)}")
    print(f"  same_month_alignment:       {same_n}")
    print(f"  prefiling_lag_1m_alignment: {lag1_n}")
    print(f"  prefiling_lag_3m_alignment: {lag3_n}")
    print(f"  join_ready_for_CAR_m1_p1:   {jr1_n}")

    # ---- Variable dictionary ----
    print("\nBuilding variable dictionary...")
    dict_rows = build_variable_dictionary(car_panel, daily_ar_available)

    # ---- Manifest ----
    print("\nBuilding manifest...")
    manifest = build_manifest(humor_rows, car_panel, linkage_rows, daily_ar_available, daily_ar_count, args)

    # ---- Write outputs ----
    n1 = write_csv(args.out_car,     CAR_PANEL_FIELDS, car_panel)
    n2 = write_csv(args.out_linkage, LINKAGE_FIELDS,   linkage_rows)
    n3 = write_csv(args.out_dict,    DICT_FIELDS,      dict_rows)
    print(f"  CAR panel   → {args.out_car} ({n1} rows)")
    print(f"  Linkage     → {args.out_linkage} ({n2} rows)")
    print(f"  Dict        → {args.out_dict} ({n3} rows)")

    args.out_manifest.parent.mkdir(parents=True, exist_ok=True)
    args.out_manifest.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"  Manifest    → {args.out_manifest}")

    print(f"\n{'='*62}")
    print("CAR Symmetric Event Window Panel Summary")
    print(f"  car_event_rows:                    {manifest['car_event_rows']}")
    print(f"  CAR_m1_p1_available_rows:          {manifest['CAR_m1_p1_available_rows']}")
    print(f"  CAR_m3_p3_available_rows:          {manifest['CAR_m3_p3_available_rows']}")
    print(f"  CAR_m5_p5_available_rows:          {manifest['CAR_m5_p5_available_rows']}")
    print(f"  humor_car_linked_rows:             {manifest['humor_car_linked_rows']}")
    print(f"  same_month_alignment_rows:         {manifest['same_month_alignment_rows']}")
    print(f"  prefiling_lag_1m_alignment_rows:   {manifest['prefiling_lag_1m_alignment_rows']}")
    print(f"  prefiling_lag_3m_alignment_rows:   {manifest['prefiling_lag_3m_alignment_rows']}")
    print(f"  join_ready_for_CAR_m1_p1_rows:     {manifest['join_ready_for_CAR_m1_p1_rows']}")
    print(f"  future_event_count:                {manifest['future_event_count']}")
    print(f"  requires_date_audit:               {manifest['requires_date_audit']}")
    print(f"  daily_abnormal_return_available:   {manifest['daily_abnormal_return_input_available']}")
    if not manifest["daily_abnormal_return_input_available"]:
        print(f"  missing_car_reason: {manifest['missing_car_reason'][:80]}...")


if __name__ == "__main__":
    main()
