"""
build_hypothesis_datasets_from_new_classification.py

Builds H1/H2 post-level and H3 firm-month panel regression-ready datasets
from the Wendy's-model-transferred Fortune 100 classification.
"""

from __future__ import annotations

import csv
import math
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
MT = ROOT / "20260618expand" / "model_transfer"

CLASSIFIED = MT / "data" / "classified" / "fortune100_wendys_model_humor_classification.csv"
FORTUNE_MASTER = ROOT / "20260618expand" / "data" / "processed" / "fortune100_post_master.csv"

OUT_H1 = MT / "data" / "regression_ready" / "h1_post_level_regression_ready.csv"
OUT_H2 = MT / "data" / "regression_ready" / "h2_post_level_regression_ready.csv"
OUT_H3_PANEL = MT / "data" / "processed" / "h3_firm_month_panel.csv"
OUT_H3_RR = MT / "data" / "regression_ready" / "h3_firm_period_regression_ready.csv"
OUT_INCLUSION = MT / "data" / "diagnostics" / "regression_sample_inclusion.csv"

TWITTER_DATE_FORMATS = [
    "%a %b %d %H:%M:%S +0000 %Y",
]


def parse_yearmonth(created_at: str) -> str:
    for fmt in TWITTER_DATE_FORMATS:
        try:
            from datetime import datetime
            dt = datetime.strptime(created_at.strip(), fmt)
            return dt.strftime("%Y-%m")
        except ValueError:
            continue
    return "missing_period"


def load_master() -> dict[str, dict]:
    with open(FORTUNE_MASTER, newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    return {r["tweet_id"]: r for r in rows}


def safe_float(v: str, default: float = 0.0) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def main() -> None:
    print("=== build_hypothesis_datasets_from_new_classification ===")

    master_by_id = load_master()

    with open(CLASSIFIED, newline="", encoding="utf-8") as f:
        classified_rows = list(csv.DictReader(f))

    print(f"Classified rows: {len(classified_rows)}")

    # Build merged post-level rows
    merged: list[dict] = []
    n_master_missing = 0
    for cr in classified_rows:
        tid = cr.get("tweet_id", "")
        mr = master_by_id.get(tid)
        if mr is None:
            n_master_missing += 1
            continue

        log_eng = safe_float(mr.get("log_total_engagement", ""))
        period = parse_yearmonth(cr.get("created_at", ""))
        created_at = cr.get("created_at", "")

        year = period[:4] if period != "missing_period" else "missing"
        month = period[5:7] if period != "missing_period" else "missing"

        merged.append({
            "tweet_id":               tid,
            "company_name":           cr.get("company_name", ""),
            "source_x_handle":        cr.get("source_x_handle", ""),
            "period":                 period,
            "year":                   year,
            "month":                  month,
            "created_at":             created_at,
            "log_total_engagement":   f"{log_eng:.6f}",
            "total_engagement":       mr.get("total_engagement", ""),
            "text_length":            mr.get("text_length", ""),
            "hashtag_count":          mr.get("hashtag_count", ""),
            "mention_count":          mr.get("mention_count", ""),
            "humor_presence":         cr.get("humor_presence", ""),
            "humor_type":             cr.get("humor_type", ""),
            "aggressive_humor":       cr.get("aggressive_humor", ""),
            "affiliative_humor":      cr.get("affiliative_humor", ""),
            "self_enhancing_humor":   cr.get("self_enhancing_humor", ""),
            "self_defeating_humor":   cr.get("self_defeating_humor", ""),
            "non_humorous":           cr.get("non_humorous", ""),
            "classification_status":  cr.get("classification_status", ""),
        })

    print(f"Merged with master: {len(merged)}  (master-missing: {n_master_missing})")

    # H1 sample: all classified OK rows with valid log_total_engagement
    h1_rows = [
        r for r in merged
        if r["classification_status"] == "ok"
        and r["humor_presence"] in ("0", "1")
    ]

    # H2 sample: same, humor_type is defined
    h2_rows = [
        r for r in merged
        if r["classification_status"] == "ok"
        and r["humor_type"] in {"aggressive", "affiliative", "self-enhancing",
                                "self-defeating", "non_humorous"}
    ]

    # H1 regression-ready
    for r in h1_rows:
        r["h1_sample_inclusion_flag"] = "1"

    h1_cols = [
        "tweet_id", "company_name", "source_x_handle", "period", "year", "month",
        "log_total_engagement", "humor_presence",
        "text_length", "hashtag_count", "mention_count",
        "h1_sample_inclusion_flag",
    ]
    OUT_H1.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_H1, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=h1_cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(h1_rows)
    print(f"H1 regression-ready: {len(h1_rows)} rows → {OUT_H1}")

    # H2 regression-ready
    for r in h2_rows:
        r["h2_sample_inclusion_flag"] = "1"

    h2_cols = [
        "tweet_id", "company_name", "source_x_handle", "period", "year", "month",
        "log_total_engagement", "humor_type",
        "aggressive_humor", "affiliative_humor", "self_enhancing_humor", "self_defeating_humor",
        "non_humorous",
        "text_length", "hashtag_count", "mention_count",
        "h2_sample_inclusion_flag",
    ]
    with open(OUT_H2, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=h2_cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(h2_rows)
    print(f"H2 regression-ready: {len(h2_rows)} rows → {OUT_H2}")

    # H3 firm-month panel
    panel: dict[tuple[str, str], dict] = {}
    for r in h1_rows:
        key = (r["company_name"], r["period"])
        if key not in panel:
            panel[key] = {
                "company_name": r["company_name"],
                "period": r["period"],
                "_log_eng_sum": 0.0,
                "_eng_sum": 0.0,
                "_post_count": 0,
                "_humor_count": 0,
                "_agg_count": 0,
                "_text_len_sum": 0.0,
                "_hash_sum": 0.0,
                "_mention_sum": 0.0,
                "_eng_list": [],
            }
        p = panel[key]
        le = safe_float(r["log_total_engagement"])
        te = safe_float(r["total_engagement"])
        p["_log_eng_sum"] += le
        p["_eng_sum"] += te
        p["_post_count"] += 1
        p["_humor_count"] += int(r["humor_presence"])
        p["_agg_count"] += int(r["aggressive_humor"])
        p["_text_len_sum"] += safe_float(r["text_length"])
        p["_hash_sum"] += safe_float(r["hashtag_count"])
        p["_mention_sum"] += safe_float(r["mention_count"])
        p["_eng_list"].append(te)

    panel_rows = []
    for (company, period), p in panel.items():
        n = p["_post_count"]
        if n == 0:
            continue
        agg_rate = p["_agg_count"] / n
        eng_list = p["_eng_list"]
        eng_list_sorted = sorted(eng_list)
        mid = len(eng_list_sorted) // 2
        median_eng = (
            eng_list_sorted[mid] if len(eng_list_sorted) % 2 == 1
            else (eng_list_sorted[mid - 1] + eng_list_sorted[mid]) / 2
        )
        panel_rows.append({
            "company_name":                         company,
            "period":                               period,
            "post_count":                           n,
            "humor_post_count":                     p["_humor_count"],
            "aggressive_humor_post_count":          p["_agg_count"],
            "aggressive_humor_usage_intensity":     round(agg_rate, 12),
            "aggressive_humor_usage_intensity_sq":  round(agg_rate * agg_rate, 12),
            "mean_log_total_engagement":            round(p["_log_eng_sum"] / n, 6),
            "mean_total_engagement":                round(p["_eng_sum"] / n, 6),
            "median_total_engagement":              round(median_eng, 6),
            "mean_text_length":                     round(p["_text_len_sum"] / n, 4),
            "mean_hashtag_count":                   round(p["_hash_sum"] / n, 4),
            "mean_mention_count":                   round(p["_mention_sum"] / n, 4),
        })

    OUT_H3_PANEL.parent.mkdir(parents=True, exist_ok=True)
    h3_panel_cols = [
        "company_name", "period", "post_count", "humor_post_count",
        "aggressive_humor_post_count", "aggressive_humor_usage_intensity",
        "aggressive_humor_usage_intensity_sq",
        "mean_log_total_engagement", "mean_total_engagement", "median_total_engagement",
        "mean_text_length", "mean_hashtag_count", "mean_mention_count",
    ]
    with open(OUT_H3_PANEL, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=h3_panel_cols)
        w.writeheader()
        w.writerows(panel_rows)
    print(f"H3 panel: {len(panel_rows)} firm-month rows → {OUT_H3_PANEL}")

    # H3 regression-ready: add inclusion flag
    n_nonzero_agg = sum(1 for r in panel_rows if r["aggressive_humor_post_count"] > 0)
    print(f"H3 non-zero aggressive rows: {n_nonzero_agg} / {len(panel_rows)}")

    h3_rr_rows = [{**r, "h3_sample_inclusion_flag": "1"} for r in panel_rows]
    h3_rr_cols = h3_panel_cols + ["h3_sample_inclusion_flag"]
    OUT_H3_RR.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_H3_RR, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=h3_rr_cols)
        w.writeheader()
        w.writerows(h3_rr_rows)
    print(f"H3 regression-ready: {len(h3_rr_rows)} rows → {OUT_H3_RR}")

    # Sample inclusion diagnostics
    OUT_INCLUSION.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_INCLUSION, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["metric", "value"])
        w.writeheader()
        rows = [
            ("total_classified_rows", len(classified_rows)),
            ("master_matched_rows", len(merged)),
            ("master_missing_rows", n_master_missing),
            ("h1_sample_rows", len(h1_rows)),
            ("h2_sample_rows", len(h2_rows)),
            ("h3_firm_month_rows", len(panel_rows)),
            ("h3_nonzero_aggressive_rows", n_nonzero_agg),
        ]
        for metric, value in rows:
            w.writerow({"metric": metric, "value": value})

    print("\n=== build_hypothesis_datasets COMPLETE ===")


if __name__ == "__main__":
    main()
