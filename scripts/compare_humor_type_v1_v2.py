#!/usr/bin/env python3
"""Compare v1 (full-chain pipeline) vs v2 (direct 5-class) humor type classifications.

Takes the A/B test sample (which has v1 labels from the full-chain master) and the
v2 direct classification output, joins them on global_post_id, and produces:
  - A row-level comparison CSV with both labels, agreement flag, and transition type
  - A summary JSON with aggregate statistics

Inputs:
  --sample    Stratified sample CSV from build_humor_type_ab_test_sample.py
              (contains v1 labels from the full-chain master)
  --v2        v2 classification CSV from classify_humor_type_v2_direct.py

Outputs:
  data/audit/humor/evaluation/humor_type_v1_v2_comparison.csv
  data/audit/humor/evaluation/humor_type_v1_v2_summary.json
"""

import argparse
import csv
import json
import sys
from collections import Counter
from pathlib import Path

DEFAULT_SAMPLE = Path("data/derived/humor/evaluation/humor_type_ab_test_sample.csv")
DEFAULT_V2 = Path("data/derived/humor/evaluation/humor_type_v2_classified_sample.csv")
DEFAULT_COMPARISON = Path("data/audit/humor/evaluation/humor_type_v1_v2_comparison.csv")
DEFAULT_SUMMARY = Path("data/audit/humor/evaluation/humor_type_v1_v2_summary.json")

COMPARISON_FIELDS = [
    "global_post_id",
    "company_name",
    "source_x_handle",
    "stratum",
    "text",
    "v1_label",
    "v2_label",
    "agreement",
    "transition_type",
    "v1_confidence",
    "v2_confidence",
    "v2_review_flag",
    "v2_reason_code",
    "v2_target_of_humor",
    "v2_humor_function",
]

# Transition category definitions
HUMOR_LABELS = frozenset(["affiliative", "self_enhancing", "aggressive", "self_defeating"])
AMBIGUOUS_LABELS = frozenset(["ambiguous_or_review", "ambiguous_review"])
NOT_HUMOR_LABELS = frozenset(["not_applicable", "not_humor", "non_humor"])


def categorize_transition(v1: str, v2: str) -> str:
    """Assign a human-readable transition type to a v1→v2 label pair."""
    if v1 == v2:
        return "same"
    v1_is_humor = v1 in HUMOR_LABELS
    v1_is_ambig = v1 in AMBIGUOUS_LABELS
    v1_is_not_humor = v1 in NOT_HUMOR_LABELS
    v2_is_humor = v2 in HUMOR_LABELS
    v2_is_ambig = v2 in AMBIGUOUS_LABELS
    v2_is_not_humor = v2 in NOT_HUMOR_LABELS

    if v1_is_ambig and v2_is_humor:
        return "resolved_to_humor"
    if v1_is_ambig and v2_is_not_humor:
        return "resolved_to_not_humor"
    if v1_is_ambig and v2_is_ambig:
        return "still_ambiguous"
    if v1_is_humor and v2_is_not_humor:
        return "humor_to_not_humor"
    if v1_is_not_humor and v2_is_humor:
        return "not_humor_to_humor"
    if v1_is_humor and v2_is_ambig:
        return "humor_to_ambiguous"
    if v1_is_not_humor and v2_is_ambig:
        return "not_humor_to_ambiguous"
    if v1_is_humor and v2_is_humor:
        return f"type_change_{v1}_to_{v2}"
    return f"other_{v1}_to_{v2}"


def normalize_label(label: str) -> str:
    label = (label or "").strip().lower()
    # Normalize v1 not_applicable to not_humor for comparison
    if label in ("not_applicable",):
        return "not_humor"
    return label


def load_csv(path: Path, label: str) -> dict[str, dict]:
    if not path.exists():
        raise FileNotFoundError(f"{label} CSV not found: {path}")
    with path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            raise ValueError(f"{label} CSV has no header: {path}")
        return {r["global_post_id"]: r for r in reader if r.get("global_post_id")}


def main():
    parser = argparse.ArgumentParser(
        description="Compare v1 vs v2 humor type labels on the A/B test sample."
    )
    parser.add_argument("--sample", type=Path, default=DEFAULT_SAMPLE,
                        help="A/B test sample CSV (contains v1 labels from full-chain master)")
    parser.add_argument("--v2", type=Path, default=DEFAULT_V2,
                        help="v2 direct classification output CSV")
    parser.add_argument("--comparison-output", type=Path, default=DEFAULT_COMPARISON)
    parser.add_argument("--summary-output", type=Path, default=DEFAULT_SUMMARY)
    args = parser.parse_args()

    print(f"Loading sample (v1): {args.sample}")
    sample_by_id = load_csv(args.sample, "sample")

    print(f"Loading v2 classifications: {args.v2}")
    v2_by_id = load_csv(args.v2, "v2")

    matched = 0
    unmatched_v2 = 0
    comparison_rows: list[dict] = []

    for gid, v1_row in sample_by_id.items():
        v2_row = v2_by_id.get(gid)
        if v2_row is None:
            unmatched_v2 += 1
            # Still include in comparison with missing v2 marker
            comparison_rows.append({
                "global_post_id": gid,
                "company_name": v1_row.get("company_name", ""),
                "source_x_handle": v1_row.get("source_x_handle", ""),
                "stratum": v1_row.get("stratum", ""),
                "text": v1_row.get("text", ""),
                "v1_label": normalize_label(v1_row.get("humor_type", "")),
                "v2_label": "missing_v2",
                "agreement": "false",
                "transition_type": "missing_v2_output",
                "v1_confidence": v1_row.get("humor_type_confidence", ""),
                "v2_confidence": "",
                "v2_review_flag": "",
                "v2_reason_code": "",
                "v2_target_of_humor": "",
                "v2_humor_function": "",
            })
            continue

        matched += 1
        v1_label = normalize_label(v1_row.get("humor_type", ""))
        v2_label = normalize_label(v2_row.get("v2_humor_label", ""))
        agree = (v1_label == v2_label) or (
            v1_label in NOT_HUMOR_LABELS and v2_label in NOT_HUMOR_LABELS
        )
        transition = categorize_transition(v1_label, v2_label)

        comparison_rows.append({
            "global_post_id": gid,
            "company_name": v1_row.get("company_name", ""),
            "source_x_handle": v1_row.get("source_x_handle", ""),
            "stratum": v1_row.get("stratum", ""),
            "text": v1_row.get("text", ""),
            "v1_label": v1_label,
            "v2_label": v2_label,
            "agreement": str(agree).lower(),
            "transition_type": transition,
            "v1_confidence": v1_row.get("humor_type_confidence", ""),
            "v2_confidence": v2_row.get("v2_confidence", ""),
            "v2_review_flag": v2_row.get("v2_review_flag", ""),
            "v2_reason_code": v2_row.get("v2_reason_code", ""),
            "v2_target_of_humor": v2_row.get("v2_target_of_humor", ""),
            "v2_humor_function": v2_row.get("v2_humor_function", ""),
        })

    args.comparison_output.parent.mkdir(parents=True, exist_ok=True)
    with args.comparison_output.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=COMPARISON_FIELDS)
        writer.writeheader()
        writer.writerows(comparison_rows)

    n = len(comparison_rows)
    agree_count = sum(1 for r in comparison_rows if r["agreement"] == "true")
    transition_counts = dict(Counter(r["transition_type"] for r in comparison_rows))

    v1_dist = dict(Counter(r["v1_label"] for r in comparison_rows))
    v2_dist = dict(Counter(r["v2_label"] for r in comparison_rows if r["v2_label"] != "missing_v2"))

    resolved_to_humor = sum(1 for r in comparison_rows if r["transition_type"] == "resolved_to_humor")
    resolved_to_not_humor = sum(1 for r in comparison_rows if r["transition_type"] == "resolved_to_not_humor")
    still_ambiguous = sum(1 for r in comparison_rows if r["transition_type"] == "still_ambiguous")

    v2_aggressive = v2_dist.get("aggressive", 0)
    v1_aggressive = v1_dist.get("aggressive", 0)
    v2_self_defeating = v2_dist.get("self_defeating", 0)
    v1_self_defeating = v1_dist.get("self_defeating", 0)

    # Per-company breakdown
    company_transitions: dict[str, dict] = {}
    for r in comparison_rows:
        company = r.get("company_name", "unknown")
        if company not in company_transitions:
            company_transitions[company] = Counter()
        company_transitions[company][r["transition_type"]] += 1
    company_summary = {
        c: dict(counter) for c, counter in sorted(company_transitions.items())
    }

    summary = {
        "total_sample_rows": n,
        "matched_v2_rows": matched,
        "unmatched_v2_rows": unmatched_v2,
        "overall_agreement_count": agree_count,
        "overall_agreement_rate": round(agree_count / n, 4) if n else 0.0,
        "v1_label_distribution": v1_dist,
        "v2_label_distribution": v2_dist,
        "transition_counts": transition_counts,
        "ambiguous_resolution": {
            "resolved_to_humor": resolved_to_humor,
            "resolved_to_not_humor": resolved_to_not_humor,
            "still_ambiguous": still_ambiguous,
            "resolution_rate": round(
                (resolved_to_humor + resolved_to_not_humor) /
                max(1, resolved_to_humor + resolved_to_not_humor + still_ambiguous),
                4
            ),
        },
        "rare_class_change": {
            "v1_aggressive": v1_aggressive,
            "v2_aggressive": v2_aggressive,
            "aggressive_delta": v2_aggressive - v1_aggressive,
            "v1_self_defeating": v1_self_defeating,
            "v2_self_defeating": v2_self_defeating,
            "self_defeating_delta": v2_self_defeating - v1_self_defeating,
        },
        "not_humor_reclassification": {
            "humor_to_not_humor": transition_counts.get("humor_to_not_humor", 0),
            "not_humor_to_humor": transition_counts.get("not_humor_to_humor", 0),
        },
        "company_transition_counts": company_summary,
    }

    args.summary_output.parent.mkdir(parents=True, exist_ok=True)
    args.summary_output.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(f"\nComparison written to: {args.comparison_output}")
    print(f"Summary written to:    {args.summary_output}")
    print(f"\n--- Key Metrics ---")
    print(f"  Total rows:        {n}")
    print(f"  Matched v2:        {matched}")
    print(f"  Agreement rate:    {summary['overall_agreement_rate']:.2%}")
    print(f"  Ambiguous resolved: {resolved_to_humor + resolved_to_not_humor} / {resolved_to_humor + resolved_to_not_humor + still_ambiguous}")
    print(f"  Aggressive  v1={v1_aggressive}  v2={v2_aggressive}  delta={v2_aggressive - v1_aggressive:+d}")
    print(f"  Self-defeating  v1={v1_self_defeating}  v2={v2_self_defeating}  delta={v2_self_defeating - v1_self_defeating:+d}")

    if unmatched_v2 > 0:
        print(f"\n  WARNING: {unmatched_v2} sample rows had no matching v2 output. "
              "Re-run classify_humor_type_v2_direct.py on the sample before comparing.", file=sys.stderr)


if __name__ == "__main__":
    main()
