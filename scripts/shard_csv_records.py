#!/usr/bin/env python3
"""Shard CSV files by records rather than physical lines."""

import argparse
import csv
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--shard-index", type=int, required=True, help="1-based shard index")
    parser.add_argument("--shard-size", type=int, required=True)
    parser.add_argument("--expected-total", type=int, default=None)
    parser.add_argument("--fail-empty", action="store_true")
    args = parser.parse_args()

    if args.shard_index < 1:
        raise ValueError("--shard-index must be 1 or greater")
    if args.shard_size < 1:
        raise ValueError("--shard-size must be 1 or greater")

    with args.input.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            raise ValueError(f"Input CSV has no header: {args.input}")
        fieldnames = list(reader.fieldnames)
        rows = list(reader)

    total_rows = len(rows)
    if args.expected_total is not None and total_rows != args.expected_total:
        raise ValueError(f"Expected {args.expected_total} rows before sharding, got {total_rows}")

    start = (args.shard_index - 1) * args.shard_size
    end = start + args.shard_size
    shard_rows = rows[start:end]

    if args.fail_empty and not shard_rows:
        raise ValueError(
            f"Shard {args.shard_index} is empty. total_rows={total_rows}, shard_size={args.shard_size}"
        )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(shard_rows)

    print(json.dumps({
        "input_rows": total_rows,
        "output_rows": len(shard_rows),
        "shard_index": args.shard_index,
        "shard_size": args.shard_size,
        "start_record_0_based": start,
        "end_record_exclusive": min(end, total_rows),
    }, indent=2))


if __name__ == "__main__":
    main()
