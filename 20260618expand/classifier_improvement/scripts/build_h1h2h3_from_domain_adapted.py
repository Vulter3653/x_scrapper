"""
build_h1h2h3_from_domain_adapted.py

Builds H1/H2 post-level and H3 firm-month panel datasets from the
domain-adapted classifier output (batch1+batch2 trained).

Input:
  data/classified/fortune100_domain_adapted_humor_classification.csv

Outputs (parallel to model_transfer layout, domain-adapted branch):
  data/regression_ready/h1_post_level_regression_ready.csv
  data/regression_ready/h2_post_level_regression_ready.csv
  data/processed/h3_firm_month_panel.csv
  data/regression_ready/h3_firm_period_regression_ready.csv
  data/diagnostics/domain_adapted_regression_sample_inclusion.csv

Inclusion rules:
  H1: classification_status == "ok" AND humor_presence in ("0","1")
  H2: classification_status == "ok" AND humor_type not in ("uncertain","")
  H3: H1 sample aggregated to firm-month panel
"""

from __future__ import annotations

import csv
import math
from collections import defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CI   = ROOT / "20260618expand" / "classifier_improvement"

CLASSIFIED     = CI / "data" / "classified" / "fortune100_domain_adapted_humor_classification.csv"
FORTUNE_MASTER = ROOT / "20260618expand" / "data" / "processed" / "fortune100_post_master.csv"

OUT_H1      = CI / "data" / "regression_ready" / "h1_post_level_regression_ready.csv"
OUT_H2      = CI / "data" / "regression_ready" / "h2_post_level_regression_ready.csv"
OUT_H3_PANEL = CI / "data" / "processed" / "h3_firm_month_panel.csv"
OUT_H3_RR   = CI / "data" / "regression_ready" / "h3_firm_period_regression_ready.csv"
OUT_INCL    = CI / "data" / "diagnostics" / "domain_adapted_regression_sample_inclusion.csv"

VALID_TYPES = {"aggressive", "affiliative", "self_enhancing", "self_defeating", "non_humorous"}

TWITTER_FMT = "%a %b %d %H:%M:%S +0000 %Y"


def parse_yearmonth(created_at: str) -> str:
    try:
        dt = datetime.strptime(created_at.strip(), TWITTER_FMT)
        return dt.strftime("%Y-%m")
    except ValueError:
        return "missing_period"


def safe_float(v: str, default: float = 0.0) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def load_master() -> dict[str, dict]:
    with open(FORTUNE_MASTER, newline="", encoding="utf-8-sig") as f:
        return {r["tweet_id"]: r for r in csv.DictReader(f)}


def main() -> None:
    print("=== build_h1h2h3_from_domain_adapted ===\n")

    master = load_master()
    print(f"Master posts loaded: {len(master)}")

    with open(CLASSIFIED, newline="", encoding="utf-8") as f:
        classified = list(csv.DictReader(f))
    print(f"Classified rows: {len(classified)}")

    from collections import Counter
    pres_dist = Counter(r["humor_presence"] for r in classified)
    stat_dist = Counter(r["classification_status"] for r in classified)
    type_dist = Counter(r["humor_type"] for r in classified)
    print(f"  Presence: {dict(pres_dist)}")
    print(f"  Status:   {dict(stat_dist)}")
    print(f"  Type:     {dict(type_dist)}")

    # Merge with master
    merged, n_miss = [], 0
    for cr in classified:
        tid = cr.get("tweet_id", "")
        mr  = master.get(tid)
        if mr is None:
            n_miss += 1
            continue

        period = parse_yearmonth(cr.get("created_at", ""))
        year   = period[:4] if period != "missing_period" else "missing"
        month  = period[5:7] if period != "missing_period" else "missing"

        merged.append({
            "tweet_id":             tid,
            "company_name":         cr.get("company_name", ""),
            "source_x_handle":      cr.get("source_x_handle", ""),
            "period":               period,
            "year":                 year,
            "month":                month,
            "created_at":           cr.get("created_at", ""),
            "log_total_engagement": f"{safe_float(mr.get('log_total_engagement','')):.6f}",
            "total_engagement":     mr.get("total_engagement", ""),
            "text_length":          mr.get("text_length", ""),
            "hashtag_count":        mr.get("hashtag_count", ""),
            "mention_count":        mr.get("mention_count", ""),
            "humor_presence":       cr.get("humor_presence", ""),
            "humor_type":           cr.get("humor_type", ""),
            "aggressive_humor":     cr.get("aggressive_humor", ""),
            "affiliative_humor":    cr.get("affiliative_humor", ""),
            "self_enhancing_humor": cr.get("self_enhancing_humor", ""),
            "self_defeating_humor": cr.get("self_defeating_humor", ""),
            "non_humorous":         cr.get("non_humorous", ""),
            "classification_status": cr.get("classification_status", ""),
        })

    print(f"\nMerged: {len(merged)}  (master-missing: {n_miss})")

    # H1: classified posts only
    h1_rows = [
        r for r in merged
        if r["classification_status"] == "ok"
        and r["humor_presence"] in ("0", "1")
    ]
    print(f"\nH1 sample: {len(h1_rows)}")
    print(f"  humor: {sum(1 for r in h1_rows if r['humor_presence']=='1')}  "
          f"non-humor: {sum(1 for r in h1_rows if r['humor_presence']=='0')}")

    # H2: classified posts with valid humor type (incl. non_humorous)
    h2_rows = [
        r for r in merged
        if r["classification_status"] == "ok"
        and r["humor_type"] in VALID_TYPES
    ]
    print(f"\nH2 sample: {len(h2_rows)}")
    print(f"  Type dist: {dict(Counter(r['humor_type'] for r in h2_rows))}")

    # Write H1
    h1_cols = [
        "tweet_id", "company_name", "source_x_handle", "period", "year", "month",
        "log_total_engagement", "humor_presence",
        "text_length", "hashtag_count", "mention_count",
        "h1_sample_inclusion_flag",
    ]
    for r in h1_rows:
        r["h1_sample_inclusion_flag"] = "1"
    OUT_H1.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_H1, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=h1_cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(h1_rows)
    print(f"\nH1 → {OUT_H1.name}")

    # Write H2
    h2_cols = [
        "tweet_id", "company_name", "source_x_handle", "period", "year", "month",
        "log_total_engagement", "humor_type",
        "aggressive_humor", "affiliative_humor", "self_enhancing_humor",
        "self_defeating_humor", "non_humorous",
        "text_length", "hashtag_count", "mention_count",
        "h2_sample_inclusion_flag",
    ]
    for r in h2_rows:
        r["h2_sample_inclusion_flag"] = "1"
    with open(OUT_H2, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=h2_cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(h2_rows)
    print(f"H2 → {OUT_H2.name}")

    # H3 firm-month panel (from H1 sample)
    panel: dict[tuple, dict] = {}
    for r in h1_rows:
        key = (r["company_name"], r["period"])
        if key not in panel:
            panel[key] = {
                "company_name": r["company_name"],
                "period": r["period"],
                "_log_sum": 0.0, "_eng_sum": 0.0,
                "_n": 0, "_h_cnt": 0, "_agg_cnt": 0,
                "_tl_sum": 0.0, "_hc_sum": 0.0, "_mc_sum": 0.0,
                "_eng_list": [],
            }
        p = panel[key]
        p["_log_sum"]  += safe_float(r["log_total_engagement"])
        p["_eng_sum"]  += safe_float(r["total_engagement"])
        p["_n"]        += 1
        p["_h_cnt"]    += int(r["humor_presence"])
        p["_agg_cnt"]  += int(r["aggressive_humor"])
        p["_tl_sum"]   += safe_float(r["text_length"])
        p["_hc_sum"]   += safe_float(r["hashtag_count"])
        p["_mc_sum"]   += safe_float(r["mention_count"])
        p["_eng_list"].append(safe_float(r["total_engagement"]))

    panel_rows = []
    for (company, period), p in panel.items():
        n = p["_n"]
        if n == 0:
            continue
        rate = p["_agg_cnt"] / n
        sl = sorted(p["_eng_list"])
        mid = len(sl) // 2
        median = sl[mid] if len(sl) % 2 == 1 else (sl[mid-1] + sl[mid]) / 2
        panel_rows.append({
            "company_name":                        company,
            "period":                              period,
            "post_count":                          n,
            "humor_post_count":                    p["_h_cnt"],
            "aggressive_humor_post_count":         p["_agg_cnt"],
            "aggressive_humor_usage_intensity":    round(rate, 12),
            "aggressive_humor_usage_intensity_sq": round(rate * rate, 12),
            "mean_log_total_engagement":           round(p["_log_sum"] / n, 6),
            "mean_total_engagement":               round(p["_eng_sum"] / n, 6),
            "median_total_engagement":             round(median, 6),
            "mean_text_length":                    round(p["_tl_sum"] / n, 4),
            "mean_hashtag_count":                  round(p["_hc_sum"] / n, 4),
            "mean_mention_count":                  round(p["_mc_sum"] / n, 4),
        })

    h3_cols = [
        "company_name", "period", "post_count", "humor_post_count",
        "aggressive_humor_post_count", "aggressive_humor_usage_intensity",
        "aggressive_humor_usage_intensity_sq",
        "mean_log_total_engagement", "mean_total_engagement", "median_total_engagement",
        "mean_text_length", "mean_hashtag_count", "mean_mention_count",
    ]
    OUT_H3_PANEL.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_H3_PANEL, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=h3_cols)
        w.writeheader()
        w.writerows(panel_rows)
    print(f"H3 panel → {OUT_H3_PANEL.name}  ({len(panel_rows)} firm-month rows)")

    h3_rr = [{**r, "h3_sample_inclusion_flag": "1"} for r in panel_rows]
    OUT_H3_RR.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_H3_RR, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=h3_cols + ["h3_sample_inclusion_flag"])
        w.writeheader()
        w.writerows(h3_rr)
    print(f"H3 regression-ready → {OUT_H3_RR.name}")

    n_nonzero = sum(1 for r in panel_rows if r["aggressive_humor_post_count"] > 0)
    print(f"H3 non-zero aggressive firm-months: {n_nonzero} / {len(panel_rows)}")

    # Diagnostics
    OUT_INCL.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_INCL, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["metric", "value"])
        w.writeheader()
        for m, v in [
            ("total_classified_rows",         len(classified)),
            ("master_matched_rows",            len(merged)),
            ("master_missing_rows",            n_miss),
            ("presence_ok",                    stat_dist.get("ok", 0)),
            ("presence_abstained_uncertain",   stat_dist.get("abstained", 0)),
            ("h1_sample_rows",                 len(h1_rows)),
            ("h1_humor_rows",                  sum(1 for r in h1_rows if r["humor_presence"]=="1")),
            ("h1_non_humor_rows",              sum(1 for r in h1_rows if r["humor_presence"]=="0")),
            ("h2_sample_rows",                 len(h2_rows)),
            ("h2_aggressive_rows",             sum(1 for r in h2_rows if r["aggressive_humor"]=="1")),
            ("h3_firm_month_rows",             len(panel_rows)),
            ("h3_nonzero_aggressive_rows",     n_nonzero),
            ("training_data_source",           "batch1+batch2_combined"),
            ("n_training_labels",              1980),
            ("classifier",                     "tfidf_logreg_domain_adapted"),
        ]:
            w.writerow({"metric": m, "value": v})

    print(f"\nDiagnostics → {OUT_INCL.name}")
    print("\n=== build_h1h2h3_from_domain_adapted COMPLETE ===")


if __name__ == "__main__":
    main()
