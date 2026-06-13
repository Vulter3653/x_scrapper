#!/usr/bin/env python3
"""Build a GitHub Actions matrix for failed Fortune X rank reruns."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build failed-rank matrix JSON from a ranked collection summary CSV.")
    parser.add_argument("--summary-file", required=True)
    parser.add_argument("--status-filter", default="failed")
    parser.add_argument("--exclude-ranks", default="", help="Comma-separated Fortune ranks to exclude from the rerun matrix.")
    parser.add_argument("--matrix-output", required=True, help="Path to $GITHUB_OUTPUT")
    return parser.parse_args()


def resolve_path(value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return REPO_ROOT / path


def parse_status_filter(value: str) -> set[str]:
    statuses = {item.strip().lower() for item in value.split(",") if item.strip()}
    return statuses or {"failed"}


def parse_rank_list(value: str) -> set[int]:
    ranks: set[int] = set()
    for item in value.split(","):
        token = item.strip()
        if not token:
            continue
        try:
            rank = int(token)
        except ValueError as exc:
            raise ValueError(f"Invalid rank in --exclude-ranks: {token!r}") from exc
        if rank <= 0:
            raise ValueError(f"Excluded rank must be positive: {rank}")
        ranks.add(rank)
    return ranks


def read_matching_ranks(summary_file: Path, statuses: set[str], excluded_ranks: set[int]) -> list[int]:
    with summary_file.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = set(reader.fieldnames or [])
        missing = {"fortune_rank", "status"} - fieldnames
        if missing:
            raise ValueError(f"{summary_file} missing required columns: {', '.join(sorted(missing))}")

        ranks: set[int] = set()
        for row in reader:
            status = (row.get("status") or "").strip().lower()
            if status not in statuses:
                continue
            rank_value = (row.get("fortune_rank") or "").strip()
            try:
                rank = int(rank_value)
            except ValueError:
                continue
            if rank > 0 and rank not in excluded_ranks:
                ranks.add(rank)
        return sorted(ranks)


def append_github_output(output_path: Path, values: dict[str, str]) -> None:
    with output_path.open("a", encoding="utf-8") as handle:
        for key, value in values.items():
            handle.write(f"{key}={value}\n")


def main() -> int:
    args = parse_args()
    summary_file = resolve_path(args.summary_file)
    statuses = parse_status_filter(args.status_filter)
    excluded_ranks = parse_rank_list(args.exclude_ranks)
    ranks = read_matching_ranks(summary_file, statuses, excluded_ranks)
    matrix = {"include": [{"rank": rank} for rank in ranks]}
    matrix_json = json.dumps(matrix, separators=(",", ":"))
    failed_ranks_csv = ",".join(str(rank) for rank in ranks)
    excluded_ranks_csv = ",".join(str(rank) for rank in sorted(excluded_ranks))

    append_github_output(
        Path(args.matrix_output),
        {
            "matrix_json": matrix_json,
            "has_failed_ranks": "true" if ranks else "false",
            "failed_count": str(len(ranks)),
            "failed_ranks_csv": failed_ranks_csv,
            "excluded_ranks_csv": excluded_ranks_csv,
        },
    )
    print(
        "failed_rank_count="
        f"{len(ranks)} failed_ranks={failed_ranks_csv or 'none'} "
        f"excluded_ranks={excluded_ranks_csv or 'none'}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
