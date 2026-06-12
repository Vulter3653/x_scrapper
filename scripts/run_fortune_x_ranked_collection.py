#!/usr/bin/env python3
"""Run ranked Fortune 2025 Top 100 X collection through the existing collector.

This script keeps the repository's existing Playwright/browser collector path and
runs accounts sequentially by Fortune rank within each matrix shard. It does not
use the official X API, MCP, dashboard sync, screenshots, traces, or browser
session persistence.
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
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
QUEUE_FILE = REPO_ROOT / "config" / "fortune2025_top100_verified_x_collection_queue.csv"
SCRAPER_ENTRYPOINT = REPO_ROOT / "scrape_x.py"
OUTPUT_ROOT = REPO_ROOT / "data" / "raw" / "fortune_x_2025_ranked"
SUMMARY_FILE = REPO_ROOT / "data" / "audit" / "fortune_x_2025_ranked_collection_summary.csv"
REQUIRED_SECRETS = ("X_AUTH_TOKEN", "X_CT0")
COLLECTION_METHOD = "browser-based scroll-exhaustion collection of observable public posts"

POST_COLUMNS = [
    "fortune_rank", "company_name", "official_x_handle", "tweet_id", "created_at", "text",
    "tweet_url", "reply_count", "repost_count", "like_count", "quote_count",
    "view_count_available", "media_present", "media_type", "collected_at", "collection_method",
    "max_posts_cap", "source_folder",
]

SUMMARY_COLUMNS = [
    "fortune_rank", "company_name", "official_x_handle", "folder", "attempted", "status",
    "posts_collected", "error_type", "error_message", "started_at", "completed_at",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class QueueAccount:
    fortune_rank: int
    company_name: str
    normalized_company_name: str
    official_x_handle: str
    collection_x_url: str

    @property
    def target_user(self) -> str:
        return self.official_x_handle.strip().lstrip("@")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Collect Fortune 2025 ranked X accounts by Fortune rank.")
    parser.add_argument("--queue-file", default=str(QUEUE_FILE))
    parser.add_argument("--start-rank", type=int, default=1)
    parser.add_argument("--end-rank", type=int, default=100)
    parser.add_argument(
        "--max-posts",
        type=int,
        default=0,
        help="Maximum posts per account. Use 0 for unbounded scroll-exhaustion collection.",
    )
    parser.add_argument("--previous-output-root", default="", help="Previous data/raw/fortune_x_2025_ranked snapshot for incremental merge.")
    parser.add_argument("--summary-file", default=str(SUMMARY_FILE))
    parser.add_argument("--retries", type=int, default=0)
    parser.add_argument("--retry-delay-seconds", type=float, default=30.0)
    parser.add_argument("--max-scrolls", type=int, default=2500)
    parser.add_argument("--scroll-delay-seconds", default="1.25")
    parser.add_argument("--idle-scroll-limit", type=int, default=60)
    parser.add_argument("--page-timeout-ms", type=int, default=60000)
    parser.add_argument("--headless", default="true", choices=["true", "false"])
    return parser.parse_args()


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return slug or "company"


def folder_name(account: QueueAccount, seen: set[str]) -> str:
    base = f"{account.fortune_rank:03d}_{slugify(account.company_name)}"
    folder = base
    if folder in seen:
        suffix = account.official_x_handle.strip().lstrip("@").lower() or "x"
        folder = f"{base}_{slugify(suffix)}"
    seen.add(folder)
    return folder


def read_queue(path: Path, start_rank: int, end_rank: int) -> list[QueueAccount]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    accounts: list[QueueAccount] = []
    for row in rows:
        rank = int(row["fortune_rank"])
        if rank < start_rank or rank > end_rank:
            continue
        if row.get("queue_source") != "human_final_manual_review":
            continue
        if row.get("eligibility_source_field") != "final_manual_scrape_eligible":
            continue
        handle = row.get("collection_x_handle", "").strip()
        if not handle:
            accounts.append(QueueAccount(rank, row["company_name"], row["normalized_company_name"], "", row.get("collection_x_url", "")))
            continue
        accounts.append(
            QueueAccount(
                fortune_rank=rank,
                company_name=row["company_name"],
                normalized_company_name=row["normalized_company_name"],
                official_x_handle=handle,
                collection_x_url=row.get("collection_x_url", ""),
            )
        )
    return sorted(accounts, key=lambda account: account.fortune_rank)


def limit_posts(posts: list[dict[str, Any]], max_posts: int) -> list[dict[str, Any]]:
    if max_posts > 0:
        return posts[:max_posts]
    return posts


def normalize_post_id(post: dict[str, Any]) -> str:
    return str(post.get("id") or post.get("tweet_id") or "").strip()


def post_sort_value(post: dict[str, Any]) -> int:
    try:
        return int(normalize_post_id(post))
    except ValueError:
        return 0


def merge_posts(existing_posts: list[dict[str, Any]], new_posts: list[dict[str, Any]], max_posts: int) -> tuple[list[dict[str, Any]], dict[str, int]]:
    by_id: dict[str, dict[str, Any]] = {}
    for post in existing_posts:
        post_id = normalize_post_id(post)
        if post_id:
            normalized = {**post, "id": post_id}
            by_id[post_id] = normalized

    existing_ids = set(by_id)
    captured_valid = 0
    duplicate_seen = 0
    new_unique = 0
    for post in new_posts:
        post_id = normalize_post_id(post)
        if not post_id:
            continue
        captured_valid += 1
        normalized = {**post, "id": post_id}
        if post_id in by_id:
            duplicate_seen += 1
            by_id[post_id] = {**by_id[post_id], **normalized}
        else:
            new_unique += 1
            by_id[post_id] = normalized

    merged = sorted(by_id.values(), key=post_sort_value, reverse=True)
    limited = limit_posts(merged, max_posts)
    return limited, {
        "previous_posts_count": len(existing_ids),
        "captured_posts_count": captured_valid,
        "new_unique_posts_count": new_unique,
        "duplicate_posts_seen_count": duplicate_seen,
        "merged_posts_count_before_cap": len(merged),
        "posts_collected_after_cap": len(limited),
    }


def post_boundaries(posts: list[dict[str, Any]]) -> dict[str, str]:
    valid = [post for post in posts if normalize_post_id(post)]
    if not valid:
        return {
            "newest_tweet_id": "",
            "newest_created_at": "",
            "oldest_tweet_id": "",
            "oldest_created_at": "",
        }
    ordered = sorted(valid, key=post_sort_value, reverse=True)
    newest = ordered[0]
    oldest = ordered[-1]
    return {
        "newest_tweet_id": normalize_post_id(newest),
        "newest_created_at": str(newest.get("created_at") or ""),
        "oldest_tweet_id": normalize_post_id(oldest),
        "oldest_created_at": str(oldest.get("created_at") or ""),
    }


def write_posts_csv(path: Path, account: QueueAccount, folder: str, posts: list[dict[str, Any]], max_posts: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    collected_at = utc_now()
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=POST_COLUMNS)
        writer.writeheader()
        for post in limit_posts(posts, max_posts):
            media_type = ""
            media_present = "false"
            writer.writerow({
                "fortune_rank": account.fortune_rank,
                "company_name": account.company_name,
                "official_x_handle": account.official_x_handle,
                "tweet_id": normalize_post_id(post),
                "created_at": post.get("created_at") or "",
                "text": post.get("text") or "",
                "tweet_url": post.get("tweet_url") or "",
                "reply_count": post.get("reply_count") if post.get("reply_count") is not None else "",
                "repost_count": post.get("retweet_count") if post.get("retweet_count") is not None else post.get("repost_count", ""),
                "like_count": post.get("favorite_count") if post.get("favorite_count") is not None else post.get("like_count", ""),
                "quote_count": post.get("quote_count") if post.get("quote_count") is not None else "",
                "view_count_available": "true" if post.get("view_count") not in (None, "") else str(post.get("view_count_available") or "false").lower(),
                "media_present": media_present,
                "media_type": media_type,
                "collected_at": collected_at,
                "collection_method": COLLECTION_METHOD,
                "max_posts_cap": max_posts,
                "source_folder": folder,
            })


def load_previous_posts_csv(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    try:
        with path.open(encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.DictReader(handle))
    except Exception:
        return []
    posts: list[dict[str, Any]] = []
    for row in rows:
        tweet_id = (row.get("tweet_id") or "").strip()
        if not tweet_id:
            continue
        posts.append({
            "id": tweet_id,
            "tweet_id": tweet_id,
            "created_at": row.get("created_at") or "",
            "text": row.get("text") or "",
            "tweet_url": row.get("tweet_url") or "",
            "reply_count": row.get("reply_count") or "",
            "retweet_count": row.get("repost_count") or "",
            "favorite_count": row.get("like_count") or "",
            "quote_count": row.get("quote_count") or "",
            "view_count_available": row.get("view_count_available") or "",
        })
    return posts


def write_audit_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_summary(rows: list[dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=SUMMARY_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, "") for column in SUMMARY_COLUMNS})


def sanitize_error(value: str) -> str:
    sanitized = value
    for secret_name in REQUIRED_SECRETS:
        secret_value = os.getenv(secret_name)
        if secret_value:
            sanitized = sanitized.replace(secret_value, "[REDACTED]")
    return sanitized[-1000:].replace("\r", " ").replace("\n", " ")


def credential_missing() -> bool:
    return any(not os.getenv(name) for name in REQUIRED_SECRETS)


def empty_posts(path: Path, account: QueueAccount, folder: str, max_posts: int, existing_posts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    retained = limit_posts(existing_posts, max_posts)
    write_posts_csv(path, account, folder, retained, max_posts)
    return retained


def load_posts(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    return []


def collect_account(account: QueueAccount, folder: str, args: argparse.Namespace) -> dict[str, Any]:
    started_at = utc_now()
    folder_path = OUTPUT_ROOT / folder
    posts_csv = folder_path / "posts.csv"
    audit_json = folder_path / "audit.json"
    tmp_posts_json = folder_path / "_collector_posts.json"
    tmp_state_json = folder_path / "_collector_state.json"
    previous_root = Path(args.previous_output_root) if args.previous_output_root else Path()
    previous_posts_csv = previous_root / folder / "posts.csv" if args.previous_output_root else Path()
    previous_posts = load_previous_posts_csv(previous_posts_csv)
    before_bounds = post_boundaries(previous_posts)

    base_audit = {
        "fortune_rank": account.fortune_rank,
        "company_name": account.company_name,
        "official_x_handle": account.official_x_handle,
        "folder": str(folder_path.relative_to(REPO_ROOT)),
        "attempted": False,
        "status": "skipped",
        "posts_collected": 0,
        "max_posts_cap": args.max_posts,
        "started_at": started_at,
        "completed_at": "",
        "error_type": "",
        "error_message": "",
        "collection_method": COLLECTION_METHOD,
        "browser_collection_used": False,
        "x_api_used": False,
        "previous_posts_count": len(previous_posts),
        "previous_newest_tweet_id": before_bounds["newest_tweet_id"],
        "previous_newest_created_at": before_bounds["newest_created_at"],
        "previous_oldest_tweet_id": before_bounds["oldest_tweet_id"],
        "previous_oldest_created_at": before_bounds["oldest_created_at"],
        "new_unique_posts_count": 0,
        "duplicate_posts_seen_count": 0,
        "merged_posts_count_before_cap": len(previous_posts),
        "final_newest_tweet_id": before_bounds["newest_tweet_id"],
        "final_newest_created_at": before_bounds["newest_created_at"],
        "final_oldest_tweet_id": before_bounds["oldest_tweet_id"],
        "final_oldest_created_at": before_bounds["oldest_created_at"],
    }

    if not account.official_x_handle:
        retained = empty_posts(posts_csv, account, folder, args.max_posts, previous_posts)
        after_bounds = post_boundaries(retained)
        audit = {
            **base_audit,
            "completed_at": utc_now(),
            "error_type": "missing_handle",
            "error_message": "missing official X handle",
            "posts_collected": len(retained),
            "final_newest_tweet_id": after_bounds["newest_tweet_id"],
            "final_newest_created_at": after_bounds["newest_created_at"],
            "final_oldest_tweet_id": after_bounds["oldest_tweet_id"],
            "final_oldest_created_at": after_bounds["oldest_created_at"],
        }
        write_audit_json(audit_json, audit)
        return audit

    if credential_missing():
        retained = empty_posts(posts_csv, account, folder, args.max_posts, previous_posts)
        after_bounds = post_boundaries(retained)
        audit = {
            **base_audit,
            "completed_at": utc_now(),
            "error_type": "credential_missing",
            "error_message": "required X cookie secrets are missing",
            "posts_collected": len(retained),
            "final_newest_tweet_id": after_bounds["newest_tweet_id"],
            "final_newest_created_at": after_bounds["newest_created_at"],
            "final_oldest_tweet_id": after_bounds["oldest_tweet_id"],
            "final_oldest_created_at": after_bounds["oldest_created_at"],
        }
        write_audit_json(audit_json, audit)
        return audit

    folder_path.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env.update({
        "TARGET_USER": account.target_user,
        "BRAND_DIR": str(folder_path),
        "OUTPUT_FILE": str(tmp_posts_json),
        "STATE_FILE": str(tmp_state_json),
        "MAX_POSTS": str(args.max_posts),
        "MAX_SCROLLS": str(args.max_scrolls),
        "SCROLL_DELAY_SECONDS": str(args.scroll_delay_seconds),
        "IDLE_SCROLL_LIMIT": str(args.idle_scroll_limit),
        "PAGE_TIMEOUT_MS": str(args.page_timeout_ms),
        "HEADLESS": args.headless,
    })

    attempts = args.retries + 1
    audit = base_audit
    for attempt in range(1, attempts + 1):
        for path in (tmp_posts_json, tmp_state_json):
            try:
                path.unlink()
            except FileNotFoundError:
                pass
        try:
            result = subprocess.run(
                [sys.executable, str(SCRAPER_ENTRYPOINT)],
                cwd=REPO_ROOT,
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )
            completed_at = utc_now()
            status = "success" if result.returncode == 0 else "failed"
            if status == "success":
                captured_posts = load_posts(tmp_posts_json)
                posts, merge_stats = merge_posts(previous_posts, captured_posts, args.max_posts)
                write_posts_csv(posts_csv, account, folder, posts, args.max_posts)
            else:
                posts = empty_posts(posts_csv, account, folder, args.max_posts, previous_posts)
                merge_stats = {
                    "previous_posts_count": len(previous_posts),
                    "captured_posts_count": 0,
                    "new_unique_posts_count": 0,
                    "duplicate_posts_seen_count": 0,
                    "merged_posts_count_before_cap": len(previous_posts),
                    "posts_collected_after_cap": len(posts),
                }
            after_bounds = post_boundaries(posts)
            error_type = "" if result.returncode == 0 else "collector_failed"
            error_message = "" if result.returncode == 0 else sanitize_error((result.stdout or "") + " " + (result.stderr or ""))
            audit = {
                **base_audit,
                **merge_stats,
                "attempted": True,
                "status": status,
                "posts_collected": len(posts),
                "completed_at": completed_at,
                "error_type": error_type,
                "error_message": error_message,
                "browser_collection_used": True,
                "final_newest_tweet_id": after_bounds["newest_tweet_id"],
                "final_newest_created_at": after_bounds["newest_created_at"],
                "final_oldest_tweet_id": after_bounds["oldest_tweet_id"],
                "final_oldest_created_at": after_bounds["oldest_created_at"],
            }
        except Exception as exc:
            completed_at = utc_now()
            posts = empty_posts(posts_csv, account, folder, args.max_posts, previous_posts)
            after_bounds = post_boundaries(posts)
            audit = {
                **base_audit,
                "attempted": True,
                "status": "failed",
                "posts_collected": len(posts),
                "completed_at": completed_at,
                "error_type": type(exc).__name__,
                "error_message": sanitize_error(str(exc)),
                "browser_collection_used": True,
                "final_newest_tweet_id": after_bounds["newest_tweet_id"],
                "final_newest_created_at": after_bounds["newest_created_at"],
                "final_oldest_tweet_id": after_bounds["oldest_tweet_id"],
                "final_oldest_created_at": after_bounds["oldest_created_at"],
            }

        if audit["status"] == "success":
            break
        if attempt < attempts:
            print(
                f"retry_rank={account.fortune_rank:03d} attempt={attempt + 1}/{attempts} "
                f"delay_seconds={args.retry_delay_seconds}",
                flush=True,
            )
            time.sleep(args.retry_delay_seconds)

    for path in (tmp_posts_json, tmp_state_json):
        try:
            path.unlink()
        except FileNotFoundError:
            pass

    write_audit_json(audit_json, audit)
    return audit


def main() -> int:
    args = parse_args()
    if args.start_rank < 1 or args.end_rank > 100 or args.start_rank > args.end_rank:
        raise SystemExit("rank range must be within 1-100 and start_rank <= end_rank")
    if args.max_posts < 0:
        raise SystemExit("max_posts must be >= 0; use 0 for unbounded scroll-exhaustion collection")
    if args.retries < 0:
        raise SystemExit("retries must be >= 0")
    if args.retry_delay_seconds < 0:
        raise SystemExit("retry_delay_seconds must be >= 0")
    if args.max_scrolls < 1:
        raise SystemExit("max_scrolls must be >= 1")
    if args.idle_scroll_limit < 1:
        raise SystemExit("idle_scroll_limit must be >= 1")
    if args.page_timeout_ms < 1000:
        raise SystemExit("page_timeout_ms must be >= 1000")

    accounts = read_queue(Path(args.queue_file), args.start_rank, args.end_rank)
    seen_folders: set[str] = set()
    summary_rows: list[dict[str, Any]] = []

    for account in accounts:
        folder = folder_name(account, seen_folders)
        print(f"collect_rank={account.fortune_rank:03d} company={account.company_name} handle={account.official_x_handle}", flush=True)
        audit = collect_account(account, folder, args)
        summary_rows.append({
            "fortune_rank": audit["fortune_rank"],
            "company_name": audit["company_name"],
            "official_x_handle": audit["official_x_handle"],
            "folder": audit["folder"],
            "attempted": str(audit["attempted"]).lower(),
            "status": audit["status"],
            "posts_collected": audit["posts_collected"],
            "error_type": audit["error_type"],
            "error_message": audit["error_message"],
            "started_at": audit["started_at"],
            "completed_at": audit["completed_at"],
        })
        time.sleep(1)

    write_summary(summary_rows, Path(args.summary_file))
    failed = sum(1 for row in summary_rows if row["status"] == "failed")
    skipped = sum(1 for row in summary_rows if row["status"] == "skipped")
    print(f"ranked_collection_complete attempted={len(summary_rows) - skipped} failed={failed} skipped={skipped}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
