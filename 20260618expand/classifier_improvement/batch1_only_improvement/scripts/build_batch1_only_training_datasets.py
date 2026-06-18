"""
build_batch1_only_training_datasets.py

Reads batch1 coder split files (coder1/2/3) and builds two training datasets:
  1. Presence training data  — binary: humor(1) vs non_humor(0); uncertain excluded
  2. Aggressive detector data — binary: aggressive(1) vs non_aggressive_humor(0);
                                only humor rows (presence=1) are included

Output files (batch1_only_improvement/data/):
  batch1_presence_training_data.csv
  batch1_aggressive_detector_training_data.csv
  batch1_training_data_diagnostics.csv

NOTE: batch2 files are not used. raw data is not modified.
"""

from __future__ import annotations

import csv
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
CI = ROOT / "20260618expand" / "classifier_improvement"
B1 = CI / "batch1_only_improvement"
SPLITS_DIR = CI / "data" / "human_labeling_template" / "coder_splits"

OUT_PRESENCE = B1 / "data" / "batch1_presence_training_data.csv"
OUT_AGG = B1 / "data" / "batch1_aggressive_detector_training_data.csv"
OUT_DIAG = B1 / "data" / "batch1_training_data_diagnostics.csv"

CODERS = ["coder1", "coder2", "coder3"]
EXPECTED_TOTAL = 1500
EXPECTED_PRESENCE_VALID = 1482
EXPECTED_AGG_ROWS = 648
EXPECTED_AGG_POS = 44
EXPECTED_AGG_NEG = 604

KOR_TO_ENG = {
    "후보_ID":      "candidate_id",
    "표본_층화":    "sampling_stratum",
    "Fortune_순위": "fortune_rank",
    "회사명":       "company_name",
    "X_계정":       "x_account",
    "트윗_ID":      "tweet_id",
    "트윗_URL":     "tweet_url",
    "작성일시":     "created_at",
    "본문":         "text",
    "유머_존재여부": "presence_code",
    "유머_유형":    "type_code",
    "배정_코더":    "assigned_coder",
}

TYPE_LABEL = {"1": "aggressive", "2": "affiliative", "3": "self_enhancing", "4": "self_defeating"}

PRESENCE_FIELDS = [
    "candidate_id", "sampling_stratum", "fortune_rank", "company_name",
    "assigned_coder", "text", "presence_code", "humor_label",
]
AGG_FIELDS = [
    "candidate_id", "sampling_stratum", "fortune_rank", "company_name",
    "assigned_coder", "text", "presence_code", "type_code", "type_label", "aggressive_label",
]


def main() -> None:
    print("=== build_batch1_only_training_datasets ===")

    all_rows: list[dict] = []
    for coder in CODERS:
        path = SPLITS_DIR / f"{coder}_labeling_template.csv"
        if not path.exists():
            raise FileNotFoundError(f"Missing coder file: {path}")
        with open(path, encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                mapped = {KOR_TO_ENG.get(k, k): v for k, v in row.items()}
                all_rows.append(mapped)
        print(f"  Loaded {coder}: {sum(1 for r in all_rows if r.get('assigned_coder','') == coder or True)} rows total so far")

    print(f"  Total rows loaded: {len(all_rows)}")
    assert len(all_rows) == EXPECTED_TOTAL, f"Expected {EXPECTED_TOTAL} rows, got {len(all_rows)}"

    presence_dist = Counter(r.get("presence_code", "").strip() for r in all_rows)
    print(f"  Presence distribution: {dict(sorted(presence_dist.items()))}")

    # --- Presence dataset ---
    presence_rows: list[dict] = []
    for r in all_rows:
        pc = r.get("presence_code", "").strip()
        if pc in ("0", "1"):
            presence_rows.append({
                "candidate_id":    r.get("candidate_id", ""),
                "sampling_stratum": r.get("sampling_stratum", ""),
                "fortune_rank":    r.get("fortune_rank", ""),
                "company_name":    r.get("company_name", ""),
                "assigned_coder":  r.get("assigned_coder", ""),
                "text":            r.get("text", ""),
                "presence_code":   pc,
                "humor_label":     1 if pc == "1" else 0,
            })
    print(f"  Presence valid rows (0/1 only): {len(presence_rows)}")
    assert len(presence_rows) == EXPECTED_PRESENCE_VALID, (
        f"Expected {EXPECTED_PRESENCE_VALID}, got {len(presence_rows)}"
    )
    humor_n = sum(r["humor_label"] for r in presence_rows)
    non_humor_n = len(presence_rows) - humor_n
    uncertain_n = presence_dist.get("2", 0)
    print(f"    humor={humor_n}  non_humor={non_humor_n}  uncertain_excluded={uncertain_n}")

    # --- Aggressive detector dataset ---
    agg_rows: list[dict] = []
    for r in all_rows:
        pc = r.get("presence_code", "").strip()
        tc = r.get("type_code", "").strip()
        if pc == "1" and tc in ("1", "2", "3", "4"):
            agg_rows.append({
                "candidate_id":    r.get("candidate_id", ""),
                "sampling_stratum": r.get("sampling_stratum", ""),
                "fortune_rank":    r.get("fortune_rank", ""),
                "company_name":    r.get("company_name", ""),
                "assigned_coder":  r.get("assigned_coder", ""),
                "text":            r.get("text", ""),
                "presence_code":   pc,
                "type_code":       tc,
                "type_label":      TYPE_LABEL[tc],
                "aggressive_label": 1 if tc == "1" else 0,
            })
    print(f"  Aggressive detector rows (presence=1 with valid type): {len(agg_rows)}")
    assert len(agg_rows) == EXPECTED_AGG_ROWS, (
        f"Expected {EXPECTED_AGG_ROWS}, got {len(agg_rows)}"
    )
    agg_pos = sum(r["aggressive_label"] for r in agg_rows)
    agg_neg = len(agg_rows) - agg_pos
    print(f"    aggressive={agg_pos}  non_aggressive_humor={agg_neg}")
    assert agg_pos == EXPECTED_AGG_POS, f"Expected {EXPECTED_AGG_POS} aggressive, got {agg_pos}"
    assert agg_neg == EXPECTED_AGG_NEG, f"Expected {EXPECTED_AGG_NEG} non-aggressive, got {agg_neg}"

    type_dist = Counter(r["type_label"] for r in agg_rows)
    print(f"  Type distribution: {dict(type_dist)}")

    # Check humor rows with missing type
    humor_no_type = sum(
        1 for r in all_rows
        if r.get("presence_code", "").strip() == "1"
        and r.get("type_code", "").strip() not in ("1", "2", "3", "4")
    )
    if humor_no_type:
        print(f"  WARNING: {humor_no_type} humor rows have no valid type code (excluded from agg detector)")

    # --- Write outputs ---
    B1.mkdir(parents=True, exist_ok=True)
    (B1 / "data").mkdir(exist_ok=True)

    with open(OUT_PRESENCE, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=PRESENCE_FIELDS)
        w.writeheader()
        w.writerows(presence_rows)
    print(f"\n  Written: {OUT_PRESENCE}")

    with open(OUT_AGG, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=AGG_FIELDS)
        w.writeheader()
        w.writerows(agg_rows)
    print(f"  Written: {OUT_AGG}")

    # --- Diagnostics ---
    company_presence = Counter(r["company_name"] for r in presence_rows)
    company_agg = Counter(r["company_name"] for r in agg_rows if r["aggressive_label"] == 1)
    n_firms_presence = len(company_presence)
    n_firms_agg_positive = len(company_agg)

    diag_rows = [
        {"metric": "total_batch1_rows",           "value": len(all_rows)},
        {"metric": "presence_valid_rows",          "value": len(presence_rows)},
        {"metric": "uncertain_excluded",           "value": uncertain_n},
        {"metric": "humor_count",                  "value": humor_n},
        {"metric": "non_humor_count",              "value": non_humor_n},
        {"metric": "humor_base_rate",              "value": round(humor_n / len(presence_rows), 4)},
        {"metric": "aggressive_detector_rows",     "value": len(agg_rows)},
        {"metric": "aggressive_positives",         "value": agg_pos},
        {"metric": "non_aggressive_humor",         "value": agg_neg},
        {"metric": "aggressive_base_rate",         "value": round(agg_pos / len(agg_rows), 4)},
        {"metric": "type_aggressive",              "value": type_dist.get("aggressive", 0)},
        {"metric": "type_affiliative",             "value": type_dist.get("affiliative", 0)},
        {"metric": "type_self_enhancing",          "value": type_dist.get("self_enhancing", 0)},
        {"metric": "type_self_defeating",          "value": type_dist.get("self_defeating", 0)},
        {"metric": "n_unique_firms_presence",      "value": n_firms_presence},
        {"metric": "n_firms_with_aggressive",      "value": n_firms_agg_positive},
        {"metric": "batch2_used",                  "value": "NO"},
        {"metric": "raw_data_modified",            "value": "NO"},
        {"metric": "labels_modified",              "value": "NO"},
    ]
    with open(OUT_DIAG, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["metric", "value"])
        w.writeheader()
        w.writerows(diag_rows)
    print(f"  Written: {OUT_DIAG}")
    print("=== build_batch1_only_training_datasets COMPLETE ===")


if __name__ == "__main__":
    main()
