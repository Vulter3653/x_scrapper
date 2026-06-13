#!/usr/bin/env python3
"""Aggregate CSV shards using record-aware CSV parsing."""

import argparse
import csv
import glob
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-glob", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--expected-rows", type=int, default=None)
    args = parser.parse_args()

    paths = sorted(Path(p) for p in glob.glob(args.input_glob))
    if not paths:
        raise FileNotFoundError(f"No CSV files matched: {args.input_glob}")

    fieldnames = None
    rows = []
    for path in paths:
        with path.open(encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            if reader.fieldnames is None:
                raise ValueError(f"CSV has no header: {path}")
            if fieldnames is None:
                fieldnames = list(reader.fieldnames)
            elif list(reader.fieldnames) != fieldnames:
                raise ValueError(f"Header mismatch in {path}")
            rows.extend(list(reader))

    if args.expected_rows is not None and len(rows) != args.expected_rows:
        raise ValueError(f"Aggregated row-count mismatch: expected {args.expected_rows}, got {len(rows)}")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames or [])
        writer.writeheader()
        writer.writerows(rows)

    print(f"Aggregated {len(paths)} files and {len(rows)} rows into {args.output}")


if __name__ == "__main__":
    main()
