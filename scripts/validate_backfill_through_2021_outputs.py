#!/usr/bin/env python3
"""Validate historical backfill-through-2021 staging outputs or workflow readiness."""

from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT_ROOT = ROOT / "data" / "backfill" / "humor_through_2021"
RAW_DIR = OUT_ROOT / "raw"
SUMMARY = OUT_ROOT / "audit" / "backfill_through_2021_summary.csv"
FAILED = OUT_ROOT / "audit" / "backfill_through_2021_failed_targets.csv"
README = OUT_ROOT / "README.md"
WORKFLOW = ROOT / ".github" / "workflows" / "backfill-humor-collection-through-2021.yml"
WRAPPER = ROOT / "scripts" / "run_humor_backfill_through_2021.py"


def parse_date(value: Any) -> datetime | None:
    text = str(value or "").strip().replace("Z", "+00:00")
    if not text:
        return None
    for parser in (
        lambda x: datetime.fromisoformat(x),
        lambda x: datetime.strptime(x, "%a %b %d %H:%M:%S %z %Y"),
        lambda x: datetime.strptime(x[:19], "%Y-%m-%d %H:%M:%S"),
        lambda x: datetime.strptime(x[:10], "%Y-%m-%d"),
    ):
        try:
            dt = parser(text)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        except ValueError:
            continue
    return None


def load_posts(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, list) else []


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cutoff-date", default="2021-12-31")
    parser.add_argument("--allow-empty", action="store_true", help="Allow no backfill outputs yet; validates workflow/script readiness.")
    args = parser.parse_args()
    cutoff = datetime.fromisoformat(args.cutoff_date + "T23:59:59+00:00")
    failures: list[str] = []
    warnings: list[str] = []

    for path in [WORKFLOW, WRAPPER]:
        if not path.exists():
            failures.append(f"missing required file: {path}")

    if not OUT_ROOT.exists():
        if args.allow_empty:
            warnings.append("output directory not present yet; workflow has not been run")
        else:
            failures.append(f"output directory missing: {OUT_ROOT}")
    else:
        if not README.exists():
            failures.append("README missing in backfill output")
        if not SUMMARY.exists():
            if args.allow_empty:
                warnings.append("audit summary not present yet; workflow has not produced outputs")
            else:
                failures.append("audit summary missing")
        else:
            with SUMMARY.open(encoding="utf-8-sig", newline="") as f:
                summary_rows = list(csv.DictReader(f))
            failed_rows = [row for row in summary_rows if str(row.get("status", "")).startswith("failed")]
            if failed_rows and not FAILED.exists():
                failures.append("failed targets exist in summary but failed-targets CSV is missing")
            for row in summary_rows:
                if int(row.get("new_unique_posts_on_or_before_2021") or 0) > int(row.get("posts_on_or_before_2021") or 0):
                    failures.append("new_unique_posts_on_or_before_2021 exceeds posts_on_or_before_2021")
                    break
        if RAW_DIR.exists():
            for path in RAW_DIR.glob("**/posts_on_or_before_2021.json"):
                for post in load_posts(path):
                    dt = parse_date(post.get("created_at"))
                    if dt and dt > cutoff:
                        failures.append(f"post after cutoff in {path}: {post.get('created_at')}")
                        break
        elif not args.allow_empty:
            failures.append("raw staging directory missing")

    forbidden_changes = []
    for path in [ROOT / "dashboard" / "data", ROOT / "20260615wendy's"]:
        if path.exists():
            # This validator does not mutate; git status is checked by workflow separately.
            pass
    if forbidden_changes:
        failures.extend(forbidden_changes)

    if warnings:
        print("WARNINGS:")
        for warning in warnings:
            print(f"- {warning}")
    if failures:
        print("VALIDATION FAIL")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("VALIDATION PASS")
    print(f"output_dir={OUT_ROOT}")
    print(f"cutoff_date={args.cutoff_date}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
