#!/usr/bin/env python3
"""Process humor presence pilot outputs to generate merged results, audit, and review samples."""

from __future__ import annotations

import argparse
import csv
import os
from collections import Counter
from pathlib import Path
from typing import Iterable


DEFAULT_RESULTS_GLOBS = [
    "**/humor_presence_pilot_results_shard_*.csv",
    "**/humor_presence_speed_test_results_shard_*.csv",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Process humor presence pilot output CSV files.")
    parser.add_argument("--input", type=Path, required=True, help="Path to pilot sample CSV")
    parser.add_argument("--results", type=Path, help="Path to a single pilot results CSV")
    parser.add_argument(
        "--shard-results-root",
        type=Path,
        help="Directory containing shard result artifacts to merge recursively",
    )
    parser.add_argument("--output", type=Path, help="Merged output CSV path when using shard results")
    parser.add_argument("--audit", "--audit-output", dest="audit", type=Path, required=True, help="Path to output audit CSV")
    parser.add_argument(
        "--review",
        "--review-output",
        dest="review",
        type=Path,
        required=True,
        help="Path to output low-confidence review sample CSV",
    )
    parser.add_argument("--model", default="gemini-3.5-flash")
    parser.add_argument("--prompt", "--prompt-path", dest="prompt_path", default="config/prompts/humor_presence_zero_shot_prompt.md")
    parser.add_argument(
        "--schema",
        "--schema-path",
        dest="schema_path",
        default="config/schemas/humor_presence_classification_output.schema.json",
    )
    return parser.parse_args()


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    if not path.exists():
        raise SystemExit(f"CSV file not found: {path}")
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = list(reader.fieldnames or [])
        rows = list(reader)
    if not fieldnames:
        raise SystemExit(f"CSV file has no header: {path}")
    return fieldnames, rows


def write_csv(path: Path, fieldnames: Iterable[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(fieldnames))
        writer.writeheader()
        writer.writerows(rows)


def find_shard_result_paths(root: Path) -> list[Path]:
    paths: list[Path] = []
    for pattern in DEFAULT_RESULTS_GLOBS:
        paths.extend(root.glob(pattern))
    unique_paths = sorted({path.resolve(): path for path in paths}.values())
    return unique_paths


def load_result_rows(args: argparse.Namespace) -> tuple[list[str], list[dict[str, str]], list[Path]]:
    if bool(args.results) == bool(args.shard_results_root):
        raise SystemExit("Provide exactly one of --results or --shard-results-root")

    if args.results:
        fieldnames, rows = read_csv(args.results)
        return fieldnames, rows, [args.results]

    if not args.shard_results_root.exists():
        raise SystemExit(f"Shard results root not found: {args.shard_results_root}")

    result_paths = find_shard_result_paths(args.shard_results_root)
    if not result_paths:
        patterns = ", ".join(DEFAULT_RESULTS_GLOBS)
        raise SystemExit(f"No shard result files found under {args.shard_results_root} with patterns: {patterns}")

    merged_rows: list[dict[str, str]] = []
    fieldnames: list[str] | None = None
    for result_path in result_paths:
        current_fieldnames, current_rows = read_csv(result_path)
        if fieldnames is None:
            fieldnames = current_fieldnames
        elif current_fieldnames != fieldnames:
            raise SystemExit(f"Shard fieldnames mismatch: {result_path}")
        merged_rows.extend(current_rows)

    return fieldnames or [], merged_rows, result_paths


def validate_result_ids(input_rows: list[dict[str, str]], results_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    input_ids = [row.get("global_post_id", "") for row in input_rows]
    if any(not value for value in input_ids):
        raise SystemExit("Input contains rows with empty global_post_id")

    input_id_set = set(input_ids)
    result_by_id: dict[str, dict[str, str]] = {}
    duplicate_ids: list[str] = []
    for row in results_rows:
        global_post_id = row.get("global_post_id", "")
        if not global_post_id:
            raise SystemExit("Result contains row with empty global_post_id")
        if global_post_id in result_by_id:
            duplicate_ids.append(global_post_id)
            continue
        result_by_id[global_post_id] = row

    if duplicate_ids:
        sample = ", ".join(duplicate_ids[:10])
        raise SystemExit(f"Duplicate global_post_id values in results: {len(duplicate_ids)} sample={sample}")

    result_id_set = set(result_by_id)
    missing_ids = sorted(input_id_set - result_id_set)
    extra_ids = sorted(result_id_set - input_id_set)
    if missing_ids or extra_ids:
        raise SystemExit(
            "Input/result global_post_id mismatch: "
            f"missing={len(missing_ids)} extra={len(extra_ids)} "
            f"missing_sample={missing_ids[:5]} extra_sample={extra_ids[:5]}"
        )

    return [result_by_id[global_post_id] for global_post_id in input_ids]


def build_review_sample(results_rows: list[dict[str, str]], limit: int = 200) -> list[dict[str, str]]:
    review_sample: list[dict[str, str]] = []
    for row in results_rows:
        needs_review = str(row.get("needs_manual_review", "")).lower() == "true"
        is_ambiguous = row.get("humor_presence") == "ambiguous"
        failed = row.get("classification_status") == "failed"
        try:
            confidence = float(row.get("confidence_score") or 0.0)
        except ValueError:
            confidence = 0.0
        if needs_review or is_ambiguous or confidence < 0.70 or failed:
            review_sample.append(row)
            if len(review_sample) >= limit:
                break
    return review_sample


def main() -> int:
    args = parse_args()
    _, input_rows = read_csv(args.input)
    result_fieldnames, loaded_results, result_paths = load_result_rows(args)
    ordered_results = validate_result_ids(input_rows, loaded_results)

    if args.output:
        write_csv(args.output, result_fieldnames, ordered_results)
        print(f"Generated merged output: {args.output} ({len(ordered_results)} rows)")

    status_counts = Counter(row.get("classification_status", "") for row in ordered_results)
    presence_counts = Counter(row.get("humor_presence", "") for row in ordered_results)
    review_counts = Counter(str(row.get("needs_manual_review", "")).lower() == "true" for row in ordered_results)
    group_counts = Counter(row.get("sample_group", "") for row in ordered_results)
    group_presence = Counter((row.get("sample_group", ""), row.get("humor_presence", "")) for row in ordered_results)

    def get_rate(group: str, presence_type: str) -> float:
        total = group_counts.get(group, 0)
        if total == 0:
            return 0.0
        return group_presence.get((group, presence_type), 0) / total

    audit_data = [
        ("pilot_input_rows", len(input_rows)),
        ("pilot_output_rows", len(ordered_results)),
        ("shard_result_files", len(result_paths)),
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

    args.audit.parent.mkdir(parents=True, exist_ok=True)
    with args.audit.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["audit_key", "audit_value"])
        writer.writerows(audit_data)

    review_sample = build_review_sample(ordered_results)
    if ordered_results:
        write_csv(args.review, result_fieldnames, review_sample)

    print(f"Processed result files: {len(result_paths)}")
    print(f"Generated audit: {args.audit}")
    print(f"Generated review sample: {args.review} ({len(review_sample)} rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
