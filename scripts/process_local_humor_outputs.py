#!/usr/bin/env python3
"""Process local humor-presence outputs into audit and review files."""

import argparse
import csv
import os
import sys
from collections import Counter
from pathlib import Path


def boolish(value):
    return str(value).strip().lower() in {"1", "true", "yes"}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--audit", type=Path, required=True)
    parser.add_argument("--review", type=Path, required=True)
    parser.add_argument("--model", default="local_tfidf_logreg_humor_presence_v1")
    parser.add_argument("--training-seed", default="data/derived/humor/humor_presence_training_seed.csv")
    parser.add_argument("--cues", default="config/humor_presence_rule_cues.json")
    args = parser.parse_args()

    if not args.input.exists():
        print(f"Error: input file not found: {args.input}", file=sys.stderr)
        sys.exit(1)
    if not args.results.exists():
        print(f"Error: results file not found: {args.results}", file=sys.stderr)
        sys.exit(1)

    with args.input.open(encoding="utf-8-sig", newline="") as f:
        input_rows = list(csv.DictReader(f))
    with args.results.open(encoding="utf-8-sig", newline="") as f:
        results_rows = list(csv.DictReader(f))

    status_counts = Counter(row.get("classification_status", "") for row in results_rows)
    presence_counts = Counter(row.get("humor_presence", "") for row in results_rows)
    review_counts = Counter(boolish(row.get("needs_manual_review", "")) for row in results_rows)
    group_counts = Counter(row.get("sample_group", "") for row in results_rows)
    group_presence = Counter((row.get("sample_group", ""), row.get("humor_presence", "")) for row in results_rows)
    rule_counts = Counter(row.get("rule_label", "") or "ml_only" for row in results_rows)

    def rate(group, label):
        total = group_counts.get(group, 0)
        return 0.0 if not total else group_presence.get((group, label), 0) / total

    audit_rows = [
        ("local_input_rows", len(input_rows)),
        ("local_output_rows", len(results_rows)),
        ("classification_status_classified", status_counts.get("classified", 0)),
        ("classification_status_failed", status_counts.get("failed", 0)),
        ("humor_presence_humor", presence_counts.get("humor", 0)),
        ("humor_presence_non_humor", presence_counts.get("non_humor", 0)),
        ("humor_presence_ambiguous", presence_counts.get("ambiguous", 0)),
        ("needs_manual_review_true", review_counts.get(True, 0)),
        ("needs_manual_review_false", review_counts.get(False, 0)),
        ("rule_humor", rule_counts.get("humor", 0)),
        ("rule_non_humor", rule_counts.get("non_humor", 0)),
        ("rule_ambiguous", rule_counts.get("ambiguous", 0)),
        ("ml_only", rule_counts.get("ml_only", 0)),
        ("sample_group_fortune_top100_ranked", group_counts.get("fortune_top100_ranked", 0)),
        ("sample_group_benchmark_aggressive_wendys", group_counts.get("benchmark_aggressive_wendys", 0)),
        ("sample_group_benchmark_self_defeating_moonpie", group_counts.get("benchmark_self_defeating_moonpie", 0)),
        ("fortune_top100_humor_rate", f"{rate('fortune_top100_ranked', 'humor'):.4f}"),
        ("wendys_humor_rate", f"{rate('benchmark_aggressive_wendys', 'humor'):.4f}"),
        ("moonpie_humor_rate", f"{rate('benchmark_self_defeating_moonpie', 'humor'):.4f}"),
        ("fortune_top100_ambiguous_rate", f"{rate('fortune_top100_ranked', 'ambiguous'):.4f}"),
        ("wendys_ambiguous_rate", f"{rate('benchmark_aggressive_wendys', 'ambiguous'):.4f}"),
        ("moonpie_ambiguous_rate", f"{rate('benchmark_self_defeating_moonpie', 'ambiguous'):.4f}"),
        ("model_name", args.model),
        ("training_seed", args.training_seed),
        ("rule_cues", args.cues),
        ("github_run_id", os.environ.get("GITHUB_RUN_ID", "local")),
        ("github_sha", os.environ.get("GITHUB_SHA", "local")),
    ]

    args.audit.parent.mkdir(parents=True, exist_ok=True)
    with args.audit.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["audit_key", "audit_value"])
        writer.writerows(audit_rows)

    review_rows = []
    for row in results_rows:
        try:
            confidence = float(row.get("confidence_score", 0.0))
        except ValueError:
            confidence = 0.0
        if (
            boolish(row.get("needs_manual_review", ""))
            or row.get("humor_presence") == "ambiguous"
            or confidence < 0.70
            or row.get("classification_status") == "failed"
        ):
            review_rows.append(row)
            if len(review_rows) >= 200:
                break

    if results_rows:
        with args.review.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(results_rows[0].keys()))
            writer.writeheader()
            writer.writerows(review_rows)

    print(f"Generated local audit: {args.audit}")
    print(f"Generated local review sample: {args.review} ({len(review_rows)} rows)")


if __name__ == "__main__":
    main()
