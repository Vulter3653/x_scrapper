"""
build_fortune_labeling_candidates.py

Stratified + active-learning candidate sampling for Fortune Top 100 human labeling.
Generates a 1,500-post candidate set (adjustable via --sample-size) that covers:

  random_fortune_sample         - baseline random coverage
  wendys_transfer_aggressive    - oversample potential aggressive humor
  full_chain_aggressive         - known aggressive humor from full_chain_master
  classifier_disagreement       - where transfer and full_chain disagree
  humor_presence_uncertain      - near-threshold binary predictions
  type_uncertain                - low-confidence type predictions
  high_engagement_posts         - high-signal posts for H1/H2 relevance
  low_engagement_posts          - contrast coverage
  firm_balanced_sample          - at least one post per firm

Usage:
  python build_fortune_labeling_candidates.py [--sample-size 1500]
"""

from __future__ import annotations

import argparse
import csv
import math
import random
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CI = ROOT / "20260618expand" / "classifier_improvement"

MASTER = ROOT / "20260618expand" / "data" / "processed" / "fortune100_post_master.csv"
TRANSFER = ROOT / "20260618expand" / "model_transfer" / "data" / "classified" / "fortune100_wendys_model_humor_classification.csv"
FULL_CHAIN = ROOT / "data" / "derived" / "humor" / "full_chain" / "humor_full_chain_master.csv"

OUT_CANDIDATES = CI / "data" / "labeling_candidates" / "fortune100_labeling_candidates.csv"
OUT_DIAG = CI / "data" / "diagnostics" / "labeling_candidate_diagnostics.csv"

RANDOM_SEED = 42


def safe_float(v: str, default: float = 0.0) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def load_master() -> dict[str, dict]:
    with open(MASTER, newline="", encoding="utf-8-sig") as f:
        return {r["tweet_id"]: r for r in csv.DictReader(f)}


def load_transfer() -> dict[str, dict]:
    with open(TRANSFER, newline="", encoding="utf-8") as f:
        return {r["tweet_id"]: r for r in csv.DictReader(f)}


def load_full_chain() -> dict[str, dict]:
    if not FULL_CHAIN.exists():
        return {}
    with open(FULL_CHAIN, newline="", encoding="utf-8-sig") as f:
        return {r.get("tweet_id", ""): r for r in csv.DictReader(f) if r.get("tweet_id")}


def build_merged(master: dict, transfer: dict, full_chain: dict) -> list[dict]:
    merged = []
    for tid, mr in master.items():
        tr = transfer.get(tid, {})
        fc = full_chain.get(tid, {})

        presence_score = safe_float(tr.get("humor_presence_score", "0.5"))
        type_score = safe_float(tr.get("humor_type_score", "0.0"))

        # disagreement: transfer says humor=1, full_chain says non_humor; or vice versa
        tr_presence = tr.get("humor_presence", "")
        fc_presence = fc.get("humor_presence", "")
        disagree = (
            (tr_presence == "1" and fc_presence == "non_humor") or
            (tr_presence == "0" and fc_presence == "humor")
        ) if fc_presence else False

        uncertainty_score = 1.0 - abs(2.0 * presence_score - 1.0) if tr_presence in ("0", "1") else 0.5

        merged.append({
            "tweet_id": tid,
            "fortune_rank": mr.get("fortune_rank", ""),
            "company_name": mr.get("company_name", ""),
            "source_x_handle": mr.get("source_x_handle", ""),
            "tweet_url": mr.get("tweet_url", ""),
            "created_at": mr.get("created_at", ""),
            "text": mr.get("text", ""),
            "total_engagement": mr.get("total_engagement", ""),
            "log_total_engagement": mr.get("log_total_engagement", ""),
            "wendys_transfer_humor_presence": tr_presence,
            "wendys_transfer_humor_score": f"{presence_score:.6f}",
            "wendys_transfer_humor_type": tr.get("humor_type", ""),
            "wendys_transfer_type_score": f"{type_score:.6f}",
            "full_chain_humor_presence": fc_presence,
            "full_chain_humor_type": fc.get("humor_type", ""),
            "classifier_disagreement_flag": "1" if disagree else "0",
            "uncertainty_score": f"{uncertainty_score:.6f}",
        })
    return merged


def stratified_sample(
    merged: list[dict],
    sample_size: int,
    seed: int = RANDOM_SEED,
) -> list[dict]:
    rng = random.Random(seed)

    # Pre-index pools
    all_ids = {r["tweet_id"] for r in merged}
    by_id = {r["tweet_id"]: r for r in merged}

    selected: dict[str, str] = {}  # tweet_id -> stratum

    def add(pool: list[str], stratum: str, n: int) -> None:
        available = [tid for tid in pool if tid not in selected]
        take = rng.sample(available, min(n, len(available)))
        for tid in take:
            selected[tid] = stratum

    # Strata pools
    transfer_aggressive = [r["tweet_id"] for r in merged
                           if r["wendys_transfer_humor_type"] == "aggressive"]
    full_chain_aggressive = [r["tweet_id"] for r in merged
                              if r["full_chain_humor_type"] == "aggressive"]
    disagreement = [r["tweet_id"] for r in merged
                    if r["classifier_disagreement_flag"] == "1"]
    uncertain_presence = [r["tweet_id"] for r in merged
                          if 0.35 <= safe_float(r["wendys_transfer_humor_score"]) <= 0.65]
    uncertain_type = [r["tweet_id"] for r in merged
                      if r["wendys_transfer_humor_presence"] == "1"
                      and safe_float(r["wendys_transfer_type_score"]) < 0.50]

    engs = [(r["tweet_id"], safe_float(r["total_engagement"])) for r in merged]
    engs_sorted = sorted(engs, key=lambda x: -x[1])
    high_eng = [tid for tid, _ in engs_sorted[:int(len(engs_sorted) * 0.05)]]
    low_eng = [tid for tid, _ in engs_sorted[-int(len(engs_sorted) * 0.05):]]

    # Firm-balanced: ensure at least one post per firm not yet selected
    firms: dict[str, list[str]] = defaultdict(list)
    for r in merged:
        firms[r["company_name"]].append(r["tweet_id"])

    # Allocation (sum should be ≤ sample_size; remainder filled with random)
    total = sample_size
    alloc = {
        "full_chain_aggressive":    (full_chain_aggressive, min(len(full_chain_aggressive), 120)),
        "wendys_transfer_aggressive": (transfer_aggressive, 200),
        "classifier_disagreement":  (disagreement, 200),
        "humor_presence_uncertain": (uncertain_presence, 200),
        "type_uncertain":           (uncertain_type, 100),
        "high_engagement_posts":    (high_eng, 150),
        "low_engagement_posts":     (low_eng, 100),
    }
    for stratum, (pool, n) in alloc.items():
        add(pool, stratum, n)

    # Firm-balanced: one random post per firm (if not yet selected)
    firm_pool = []
    for firm, tids in firms.items():
        candidates = [tid for tid in tids if tid not in selected]
        if candidates:
            firm_pool.append(rng.choice(candidates))
    add(firm_pool, "firm_balanced_sample", len(firm_pool))

    # Fill remainder with random
    remaining = total - len(selected)
    if remaining > 0:
        random_pool = [tid for tid in all_ids if tid not in selected]
        add(random_pool, "random_fortune_sample", remaining)

    # Build output rows
    output = []
    for cid, (tid, stratum) in enumerate(selected.items(), start=1):
        r = by_id[tid]
        row = {"candidate_id": f"C{cid:05d}", "sampling_stratum": stratum}
        row.update(r)
        output.append(row)

    # Shuffle to avoid stratum ordering in template
    rng.shuffle(output)
    for cid, row in enumerate(output, start=1):
        row["candidate_id"] = f"C{cid:05d}"

    return output


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample-size", type=int, default=1500)
    args = parser.parse_args()

    print(f"=== build_fortune_labeling_candidates (target={args.sample_size}) ===")
    print("Loading data...")
    master = load_master()
    transfer = load_transfer()
    full_chain = load_full_chain()
    print(f"  master: {len(master)}  transfer: {len(transfer)}  full_chain: {len(full_chain)}")

    merged = build_merged(master, transfer, full_chain)
    print(f"  merged: {len(merged)}")

    candidates = stratified_sample(merged, args.sample_size)
    print(f"  candidates selected: {len(candidates)}")

    from collections import Counter
    strata_dist = Counter(r["sampling_stratum"] for r in candidates)
    for s, n in sorted(strata_dist.items(), key=lambda x: -x[1]):
        print(f"    {s}: {n}")

    FIELDNAMES = [
        "candidate_id", "sampling_stratum",
        "fortune_rank", "company_name", "source_x_handle",
        "tweet_id", "tweet_url", "created_at", "text",
        "total_engagement", "log_total_engagement",
        "wendys_transfer_humor_presence", "wendys_transfer_humor_score",
        "wendys_transfer_humor_type", "wendys_transfer_type_score",
        "full_chain_humor_presence", "full_chain_humor_type",
        "classifier_disagreement_flag", "uncertainty_score",
    ]

    OUT_CANDIDATES.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_CANDIDATES, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDNAMES, extrasaction="ignore")
        w.writeheader()
        w.writerows(candidates)
    print(f"\nCandidates → {OUT_CANDIDATES}")

    # Diagnostics
    OUT_DIAG.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_DIAG, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["metric", "value"])
        w.writeheader()
        w.writerow({"metric": "total_candidates", "value": len(candidates)})
        w.writerow({"metric": "target_sample_size", "value": args.sample_size})
        w.writerow({"metric": "input_post_master_rows", "value": len(master)})
        w.writerow({"metric": "full_chain_matched_rows", "value": len(full_chain)})
        for s, n in sorted(strata_dist.items()):
            w.writerow({"metric": f"stratum_{s}", "value": n})
        agg_n = strata_dist.get("wendys_transfer_aggressive", 0) + strata_dist.get("full_chain_aggressive", 0)
        w.writerow({"metric": "aggressive_oversample_total", "value": agg_n})
    print(f"Diagnostics → {OUT_DIAG}")
    print("=== build_fortune_labeling_candidates COMPLETE ===")


if __name__ == "__main__":
    main()
