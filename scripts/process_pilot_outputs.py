#!/usr/bin/env python3
"""Process pilot classification outputs to generate audit and review samples."""

import argparse
import csv
import os
import sys
from pathlib import Path
from collections import Counter

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True, help="Path to pilot sample CSV")
    parser.add_argument("--results", type=Path, required=True, help="Path to pilot results CSV")
    parser.add_argument("--audit", type=Path, required=True, help="Path to output audit CSV")
    parser.add_argument("--review", type=Path, required=True, help="Path to output review sample CSV")
    parser.add_argument("--model", default="gemini-3.5-flash")
    parser.add_argument("--prompt-path", default="config/prompts/humor_presence_zero_shot_prompt.md")
    parser.add_argument("--schema-path", default="config/schemas/humor_presence_classification_output.schema.json")
    args = parser.parse_args()

    if not args.input.exists():
        print(f"Error: Input file {args.input} not found.")
        sys.exit(1)
    if not args.results.exists():
        print(f"Error: Results file {args.results} not found.")
        sys.exit(1)

    # Load input to count rows
    with args.input.open(encoding="utf-8-sig", newline="") as f:
        input_rows = list(csv.DictReader(f))
        input_ids = {row["global_post_id"] for row in input_rows}

    # Load results
    with args.results.open(encoding="utf-8-sig", newline="") as f:
        results_rows = list(csv.DictReader(f))

    # Counters
    status_counts = Counter(r["classification_status"] for r in results_rows)
    presence_counts = Counter(r["humor_presence"] for r in results_rows)
    review_counts = Counter(r["needs_manual_review"].lower() == "true" for r in results_rows)
    group_counts = Counter(r["sample_group"] for r in results_rows)
    
    # Nested counters for rates
    group_presence = Counter((r["sample_group"], r["humor_presence"]) for r in results_rows)

    def get_rate(group, presence_type):
        total = group_counts.get(group, 0)
        if total == 0: return 0.0
        return group_presence.get((group, presence_type), 0) / total

    # Audit Data
    audit_data = [
        ("pilot_input_rows", len(input_rows)),
        ("pilot_output_rows", len(results_rows)),
        ("classification_status_classified", status_counts.get("classified", 0)),
        ("classification_status_failed", status_counts.get("failed", 0)),
        ("humor_presence_humor", presence_counts.get("humor", 0)),
        ("humor_presence_non_humor", presence_counts.get("non_humor", 0)),
        ("humor_presence_ambiguous", presence_counts.get("ambiguous", 0)),
        ("needs_manual_review_true", review_counts.get(True, 0)),
        ("needs_manual_review_false", review_counts.get(False, 0)),
        ("sample_group_fortune_top100_ranked", group_counts.get("fortune_top100_ranked", 0)),
        ("sample_group_benchmark_aggressive_wendys", group_counts.get("benchmark_aggressive_wendys", 0)),
        ("sample_group_benchmark_self_defeating_moonpie", group_counts.get("benchmark_self_defeating_moonpie", 0)),
        ("fortune_top100_humor_rate", f"{get_rate('fortune_top100_ranked', 'humor'):.4f}"),
        ("wendys_humor_rate", f"{get_rate('benchmark_aggressive_wendys', 'humor'):.4f}"),
        ("moonpie_humor_rate", f"{get_rate('benchmark_self_defeating_moonpie', 'humor'):.4f}"),
        ("fortune_top100_ambiguous_rate", f"{get_rate('fortune_top100_ranked', 'ambiguous'):.4f}"),
        ("wendys_ambiguous_rate", f"{get_rate('benchmark_aggressive_wendys', 'ambiguous'):.4f}"),
        ("moonpie_ambiguous_rate", f"{get_rate('benchmark_self_defeating_moonpie', 'ambiguous'):.4f}"),
        ("model_name", args.model),
        ("prompt_path", str(args.prompt_path)),
        ("schema_path", str(args.schema_path)),
        ("prompt_version", "1.0.0"),
        ("github_run_id", os.environ.get("GITHUB_RUN_ID", "local")),
        ("github_sha", os.environ.get("GITHUB_SHA", "local")),
    ]

    with args.audit.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["audit_key", "audit_value"])
        writer.writerows(audit_data)

    # Low-confidence review sample
    # Conditions: needs_manual_review=true OR humor_presence=ambiguous OR confidence_score < 0.70 OR classification_status=failed
    review_sample = []
    for r in results_rows:
        needs_review = r["needs_manual_review"].lower() == "true"
        is_ambiguous = r["humor_presence"] == "ambiguous"
        failed = r["classification_status"] == "failed"
        try:
            conf = float(r["confidence_score"])
        except (ValueError, KeyError):
            conf = 0.0
        
        if needs_review or is_ambiguous or conf < 0.70 or failed:
            review_sample.append(r)
            if len(review_sample) >= 200:
                break

    if results_rows:
        with args.review.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictReader(results_rows[0].keys()) # dummy for fieldnames
            writer = csv.DictWriter(f, fieldnames=results_rows[0].keys())
            writer.writeheader()
            writer.writerows(review_sample)

    print(f"Generated audit: {args.audit}")
    print(f"Generated review sample: {args.review} ({len(review_sample)} rows)")

if __name__ == "__main__":
    main()
