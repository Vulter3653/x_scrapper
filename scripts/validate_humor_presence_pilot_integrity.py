#!/usr/bin/env python3
"""Validate pilot sample/result integrity before evaluation."""

import argparse
import csv
import json
import sys
from collections import Counter
from pathlib import Path

ALLOWED_SAMPLE_GROUPS = {
    "benchmark_aggressive_wendys",
    "benchmark_self_defeating_moonpie",
    "fortune_top100_ranked",
}


def read_csv(path):
    if not path.exists():
        raise FileNotFoundError(f"CSV not found: {path}")
    with path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            raise ValueError(f"CSV has no header: {path}")
        return list(reader)


def duplicate_nonblank_ids(rows):
    ids = [r.get("global_post_id", "").strip() for r in rows if r.get("global_post_id", "").strip()]
    counts = Counter(ids)
    return {k: v for k, v in counts.items() if v > 1}


def invalid_groups(rows):
    counts = Counter((r.get("sample_group") or "missing_sample_group").strip() for r in rows)
    return {k: v for k, v in counts.items() if k not in ALLOWED_SAMPLE_GROUPS}


def write_audit(path, summary):
    if not path:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["metric", "value"])
        for key, value in summary.items():
            writer.writerow([key, json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list)) else value])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample", type=Path, required=True)
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--expected-rows", type=int, required=True)
    parser.add_argument("--output-audit", type=Path)
    args = parser.parse_args()

    sample_rows = read_csv(args.sample)
    result_rows = read_csv(args.results)
    errors = []

    if len(sample_rows) != args.expected_rows:
        errors.append(f"sample_rows != expected_rows ({len(sample_rows)} != {args.expected_rows})")
    if len(result_rows) != args.expected_rows:
        errors.append(f"result_rows != expected_rows ({len(result_rows)} != {args.expected_rows})")

    sample_invalid_groups = invalid_groups(sample_rows)
    result_invalid_groups = invalid_groups(result_rows)
    if sample_invalid_groups:
        errors.append(f"invalid sample groups in sample: {sample_invalid_groups}")
    if result_invalid_groups:
        errors.append(f"invalid sample groups in results: {result_invalid_groups}")

    sample_duplicate_ids = duplicate_nonblank_ids(sample_rows)
    result_duplicate_ids = duplicate_nonblank_ids(result_rows)
    if sample_duplicate_ids:
        errors.append(f"duplicate global_post_id values in sample: {len(sample_duplicate_ids)}")
    if result_duplicate_ids:
        errors.append(f"duplicate global_post_id values in results: {len(result_duplicate_ids)}")

    sample_ids = [r.get("global_post_id", "").strip() for r in sample_rows]
    result_ids = [r.get("global_post_id", "").strip() for r in result_rows]
    if all(sample_ids) and all(result_ids):
        missing_result_ids = sorted(set(sample_ids) - set(result_ids))
        extra_result_ids = sorted(set(result_ids) - set(sample_ids))
        if missing_result_ids:
            errors.append(f"missing result ids: {len(missing_result_ids)}")
        if extra_result_ids:
            errors.append(f"extra result ids: {len(extra_result_ids)}")
    else:
        missing_sample_ids = sum(1 for x in sample_ids if not x)
        missing_result_ids = sum(1 for x in result_ids if not x)
        if missing_sample_ids or missing_result_ids:
            errors.append(f"blank global_post_id values found: sample={missing_sample_ids}, results={missing_result_ids}")

    failed_rows = sum(1 for r in result_rows if r.get("classification_status") == "failed")
    if failed_rows:
        errors.append(f"classification_status=failed rows: {failed_rows}")

    summary = {
        "integrity_pass": not errors,
        "expected_rows": args.expected_rows,
        "sample_rows": len(sample_rows),
        "result_rows": len(result_rows),
        "failed_rows": failed_rows,
        "sample_group_distribution": dict(Counter(r.get("sample_group", "") for r in result_rows)),
        "sample_invalid_groups": sample_invalid_groups,
        "result_invalid_groups": result_invalid_groups,
        "sample_duplicate_nonblank_global_post_ids": len(sample_duplicate_ids),
        "result_duplicate_nonblank_global_post_ids": len(result_duplicate_ids),
        "errors": errors,
    }

    write_audit(args.output_audit, summary)
    print(json.dumps(summary, indent=2, ensure_ascii=False))

    if errors:
        for error in errors:
            print(f"INTEGRITY ERROR: {error}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
