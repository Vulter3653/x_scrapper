#!/usr/bin/env python3
"""Historical browser-based backfill runner through 2021-12-31.

This runner is intended for GitHub Actions workflow_dispatch only. It uses the
existing scrape_x.py browser/Playwright collector, writes staging outputs under
`data/backfill/humor_through_2021/`, and never overwrites existing raw/master
or dashboard files.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRAPER = REPO_ROOT / "scrape_x.py"
DEFAULT_TARGETS = REPO_ROOT / "config" / "humor_collection_append_targets.csv"
FAILED_TARGETS = REPO_ROOT / "data" / "audit" / "humor_collection_append_failed_targets.csv"
OUT_ROOT = REPO_ROOT / "data" / "backfill" / "humor_through_2021"
RAW_DIR = OUT_ROOT / "raw"
AUDIT_DIR = OUT_ROOT / "audit"
SUMMARY = AUDIT_DIR / "backfill_through_2021_summary.csv"
FAILED = AUDIT_DIR / "backfill_through_2021_failed_targets.csv"
README = OUT_ROOT / "README.md"

SUMMARY_FIELDS = [
    "company_name", "handle", "source_group", "status", "attempts",
    "previous_posts", "collected_posts_raw", "posts_on_or_before_2021",
    "new_unique_posts_on_or_before_2021", "duplicate_posts", "min_date", "max_date",
    "reached_cutoff_date", "stopped_reason", "scrolls_completed", "last_error",
]


def slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_") or "target"


def tweet_id(post: dict[str, Any]) -> str:
    for key in ("id", "tweet_id", "rest_id"):
        value = post.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    return ""


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


def load_json(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, list) else []


def save_json(path: Path, posts: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(posts, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_targets(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def existing_count(target: dict[str, str]) -> int:
    rank = target.get("fortune_rank", "")
    name = target.get("company_name", "")
    handle = target.get("handle", "")
    if rank == "benchmark":
        path = REPO_ROOT / "data" / slugify(name.replace("'", "")) / "posts.json"
        return len(load_json(path))
    rank_prefix = f"{int(rank):03d}" if str(rank).isdigit() else ""
    raw_root = REPO_ROOT / "data" / "raw" / "fortune_x_2025_ranked"
    candidates = list(raw_root.glob(f"{rank_prefix}_*/posts.csv")) if rank_prefix else []
    if not candidates:
        candidates = list(raw_root.glob(f"*/accounts/*{slugify(handle.lstrip('@'))}*/posts.csv"))
    if not candidates:
        return 0
    with candidates[0].open(encoding="utf-8-sig", newline="") as f:
        return sum(1 for _ in csv.DictReader(f))


def write_readme(cutoff_date: str) -> None:
    README.parent.mkdir(parents=True, exist_ok=True)
    README.write_text(f"""# Humor Historical Backfill Through 2021

Purpose: stage browser/Playwright-collected historical posts dated on or before `{cutoff_date}`.

This workflow does not use the official X API. It uses the existing browser collector through `scrape_x.py`.
Outputs here are staging outputs only and are not merged into the current integrated collected corpus.

Existing raw/master files and dashboard data are not overwritten by this workflow.
""", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--targets", default=str(DEFAULT_TARGETS))
    parser.add_argument("--target-scope", choices=["all", "failed_only"], default="all")
    parser.add_argument("--max-posts-per-account", type=int, default=0)
    parser.add_argument("--max-scrolls", type=int, default=3500)
    parser.add_argument("--cutoff-date", default="2021-12-31")
    parser.add_argument("--retry-attempts", type=int, default=1)
    parser.add_argument("--between-company-delay-seconds", type=int, default=30)
    args = parser.parse_args()

    cutoff = datetime.fromisoformat(args.cutoff_date + "T23:59:59+00:00")
    source_path = FAILED_TARGETS if args.target_scope == "failed_only" else Path(args.targets)
    targets = read_targets(source_path)
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    write_readme(args.cutoff_date)

    rows: list[dict[str, Any]] = []
    for target in targets:
        company = target.get("company_name", "")
        handle = target.get("handle", "")
        group = target.get("sample_group", target.get("source_group", ""))
        if not handle:
            continue
        slug = f"{slugify(group)}__{slugify(company)}__{slugify(handle.lstrip('@'))}"
        target_dir = RAW_DIR / slug
        raw_path = target_dir / "collected_posts_raw.json"
        filtered_path = target_dir / "posts_on_or_before_2021.json"
        state_path = target_dir / "scrape_state.json"
        metrics_path = target_dir / "scrape_metrics.json"
        previous_posts = existing_count(target)
        status = "failed_skipped"
        last_error = ""
        attempts_used = 0
        target_dir.mkdir(parents=True, exist_ok=True)

        for attempt in range(1, max(1, args.retry_attempts) + 1):
            attempts_used = attempt
            env = os.environ.copy()
            env.update({
                "TARGET_USER": handle,
                "BRAND_DIR": str(target_dir),
                "OUTPUT_FILE": str(raw_path),
                "STATE_FILE": str(state_path),
                "MAX_POSTS": str(args.max_posts_per_account),
                "MAX_SCROLLS": str(args.max_scrolls),
                "HEADLESS": "true",
                "STOP_ON_EXISTING": "0",
                "SCRAPE_METRICS_FILE": str(metrics_path),
            })
            try:
                subprocess.run([sys.executable, str(SCRAPER)], env=env, check=True)
                status = "success"
                last_error = ""
                break
            except Exception as exc:
                last_error = str(exc)
                status = "failed_skipped"

        posts = load_json(raw_path)
        ids_seen: set[str] = set()
        filtered: list[dict[str, Any]] = []
        duplicate_posts = 0
        dates: list[datetime] = []
        for post in posts:
            tid = tweet_id(post)
            if tid and tid in ids_seen:
                duplicate_posts += 1
                continue
            if tid:
                ids_seen.add(tid)
            dt = parse_date(post.get("created_at"))
            if dt:
                dates.append(dt)
            if dt and dt <= cutoff:
                filtered.append(post)
        save_json(filtered_path, filtered)
        metrics = json.loads(metrics_path.read_text(encoding="utf-8")) if metrics_path.exists() else {}
        reached_cutoff = any((parse_date(post.get("created_at")) or datetime.max.replace(tzinfo=timezone.utc)) <= cutoff for post in posts)
        rows.append({
            "company_name": company,
            "handle": handle,
            "source_group": group,
            "status": status,
            "attempts": attempts_used,
            "previous_posts": previous_posts,
            "collected_posts_raw": len(posts),
            "posts_on_or_before_2021": len(filtered),
            "new_unique_posts_on_or_before_2021": len(filtered),
            "duplicate_posts": duplicate_posts,
            "min_date": min(dates).date().isoformat() if dates else "",
            "max_date": max(dates).date().isoformat() if dates else "",
            "reached_cutoff_date": str(reached_cutoff),
            "stopped_reason": metrics.get("stop_reason", ""),
            "scrolls_completed": metrics.get("scrolls_completed", ""),
            "last_error": last_error,
        })
        if args.between_company_delay_seconds:
            time.sleep(args.between_company_delay_seconds)

    with SUMMARY.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=SUMMARY_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    failed = [row for row in rows if str(row.get("status", "")).startswith("failed")]
    if failed:
        with FAILED.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=SUMMARY_FIELDS)
            writer.writeheader()
            writer.writerows(failed)
    print(f"targets={len(rows)}")
    print(f"posts_on_or_before_2021={sum(int(row['posts_on_or_before_2021']) for row in rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
