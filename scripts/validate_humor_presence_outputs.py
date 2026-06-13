#!/usr/bin/env python3
"""Validate humor presence classification outputs."""

import argparse
import csv
import sys
from pathlib import Path
from collections import Counter

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    if not args.input.exists():
        print(f"Error: Input file {args.input} not found.")
        sys.exit(1)
    if not args.output.exists():
        print(f"Error: Output file {args.output} not found.")
        sys.exit(1)

    with args.input.open(encoding="utf-8-sig", newline="") as f:
        input_ids = {row["global_post_id"] for row in csv.DictReader(f)}

    output_rows = []
    with args.output.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            output_rows.append(row)

    output_ids = {row["global_post_id"] for row in output_rows}

    print(f"Validation Report:")
    print(f"- Input rows: {len(input_ids)}")
    print(f"- Output rows: {len(output_rows)}")
    
    if len(input_ids) != len(output_rows):
        print(f"WARNING: Row count mismatch! {len(input_ids)} vs {len(output_rows)}")
    
    missing_ids = input_ids - output_ids
    if missing_ids:
        print(f"FAIL: {len(missing_ids)} IDs from input are missing in output.")
    
    extra_ids = output_ids - input_ids
    if extra_ids:
        print(f"FAIL: {len(extra_ids)} IDs in output are not in input.")

    # Column check
    required_cols = [
        "global_post_id", "humor_presence", "confidence_score", 
        "classification_status", "needs_manual_review"
    ]
    actual_cols = output_rows[0].keys() if output_rows else []
    missing_cols = [c for c in required_cols if c not in actual_cols]
    if missing_cols:
        print(f"FAIL: Missing required columns: {', '.join(missing_cols)}")

    # Value checks
    presence_counts = Counter(r["humor_presence"] for r in output_rows)
    status_counts = Counter(r["classification_status"] for r in output_rows)
    review_counts = Counter(r["needs_manual_review"] for r in output_rows)
    
    print(f"- Humor Presence distribution: {dict(presence_counts)}")
    print(f"- Classification Status distribution: {dict(status_counts)}")
    print(f"- Needs Manual Review distribution: {dict(review_counts)}")

    # Specific checks
    failed_rows = [r for r in output_rows if r["classification_status"] == "failed"]
    if failed_rows:
        print(f"- Failed rows: {len(failed_rows)}")

    ambiguous_rows = [r for r in output_rows if r["humor_presence"] == "ambiguous"]
    print(f"- Ambiguous rows: {len(ambiguous_rows)}")

    humor_no_evidence = [r for r in output_rows if r["humor_presence"] == "humor" and not r.get("evidence_phrase")]
    print(f"- Humor rows with empty evidence: {len(humor_no_evidence)}")

    # Sample group distribution
    group_presence = Counter((r["sample_group"], r["humor_presence"]) for r in output_rows)
    print("\nSample Group x Humor Presence:")
    for group in sorted({r["sample_group"] for r in output_rows}):
        h = group_presence.get((group, "humor"), 0)
        nh = group_presence.get((group, "non_humor"), 0)
        amb = group_presence.get((group, "ambiguous"), 0)
        total = h + nh + amb
        rate = (h / total * 100) if total > 0 else 0
        print(f"  {group}: humor={h}, non_humor={nh}, ambiguous={amb} (Humor Rate: {rate:.1f}%)")

    # API Key leak check
    for row in output_rows:
        for val in row.values():
            if val and len(val) > 20 and val.isalnum() and any(c.isdigit() for c in val) and any(c.isupper() for c in val):
                # Simple heuristic for potential API key (not perfect but helpful)
                if "AIza" in val: # Gemini key prefix
                    print(f"CRITICAL: Possible API Key detected in output field!")
                    sys.exit(1)

    print("\nValidation completed.")

if __name__ == "__main__":
    main()
