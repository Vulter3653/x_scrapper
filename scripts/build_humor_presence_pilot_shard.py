#!/usr/bin/env python3
"""Build a row-range shard from the humor presence pilot sample CSV."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Slice a pilot sample CSV into a deterministic row-range shard.")
    parser.add_argument("--input", type=Path, required=True, help="Input pilot sample CSV")
    parser.add_argument("--output", type=Path, required=True, help="Output shard CSV")
    parser.add_argument("--start-row", type=int, required=True, help="0-based inclusive data-row index")
    parser.add_argument("--end-row", type=int, required=True, help="0-based exclusive data-row index")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.start_row < 0:
        raise SystemExit("--start-row must be >= 0")
    if args.end_row <= args.start_row:
        raise SystemExit("--end-row must be greater than --start-row")
    if not args.input.exists():
        raise SystemExit(f"Input file not found: {args.input}")

    with args.input.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = reader.fieldnames
        if not fieldnames:
            raise SystemExit(f"Input CSV has no header: {args.input}")
        rows = list(reader)

    shard_rows = rows[args.start_row : args.end_row]
    if not shard_rows:
        raise SystemExit(
            f"Shard range is empty: start_row={args.start_row} end_row={args.end_row} input_rows={len(rows)}"
        )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(shard_rows)

    print(
        "built_shard "
        f"input={args.input} output={args.output} start_row={args.start_row} "
        f"end_row={args.end_row} rows={len(shard_rows)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
