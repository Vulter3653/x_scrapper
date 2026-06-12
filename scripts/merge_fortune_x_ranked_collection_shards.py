#!/usr/bin/env python3
"""Merge ranked Fortune X matrix shard summary CSV files."""

from __future__ import annotations

import argparse
import csv
import sys
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT_PATTERN = "data/audit/fortune_x_2025_ranked_collection_summary_shard_*.csv"
DEFAULT_OUTPUT = REPO_ROOT / "data" / "audit" / "fortune_x_2025_ranked_collection_summary.csv"
SUMMARY_COLUMNS = [
    "fortune_rank", "company_name", "official_x_handle", "folder", "attempted", "status",
    "posts_collected", "error_type", "error_message", "started_at", "completed_at",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Merge ranked Fortune X collection shard summaries.")
    parser.add_argument("--input-pattern", default=DEFAULT_INPUT_PATTERN)
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    return parser.parse_args()


def parse_int(value: str) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def parse_completed_at(value: str) -> datetime:
    if not value:
        return datetime.min
    normalized = value.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(normalized)
    except ValueError:
        return datetime.min


def row_score(row: dict[str, str]) -> tuple[int, int, datetime]:
    return (
        1 if row.get("status") == "success" else 0,
        parse_int(row.get("posts_collected", "")),
        parse_completed_at(row.get("completed_at", "")),
    )


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        missing = [column for column in SUMMARY_COLUMNS if column not in (reader.fieldnames or [])]
        if missing:
            raise ValueError(f"{path} missing summary columns: {', '.join(missing)}")
        return list(reader)


def main() -> int:
    args = parse_args()
    pattern_path = Path(args.input_pattern)
    if pattern_path.is_absolute():
        shard_files = sorted(pattern_path.parent.glob(pattern_path.name))
    else:
        shard_files = sorted(REPO_ROOT.glob(args.input_pattern))
    if not shard_files:
        print(f"error: no shard summary files matched {args.input_pattern}", file=sys.stderr)
        return 1

    selected: dict[int, dict[str, str]] = {}
    for shard_file in shard_files:
        for row in read_rows(shard_file):
            rank = parse_int(row.get("fortune_rank", ""))
            if rank <= 0:
                continue
            current = selected.get(rank)
            if current is None or row_score(row) > row_score(current):
                selected[rank] = row

    output = Path(args.output)
    if not output.is_absolute():
        output = REPO_ROOT / output
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=SUMMARY_COLUMNS)
        writer.writeheader()
        for rank in sorted(selected):
            row = selected[rank]
            writer.writerow({column: row.get(column, "") for column in SUMMARY_COLUMNS})
    print(f"merged_shard_summaries={len(shard_files)} rows={len(selected)} output={output.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
