#!/usr/bin/env python3
"""Run one Fortune Top 100 X collection batch through the existing scraper path.

The script defaults to dry-run planning. It only invokes ``python scrape_x.py``
when ``--execute`` is supplied, required X cookie environment variables exist,
and the caller selects a concrete batch. It does not call X APIs, install MCP,
run dashboard sync, or write dashboard/data.
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

REPO_ROOT = Path(__file__).resolve().parents[1]
QUEUE_FILE = REPO_ROOT / "config" / "fortune2025_top100_verified_x_collection_queue.csv"
SCRAPER_ENTRYPOINT = REPO_ROOT / "scrape_x.py"
RAW_ROOT = REPO_ROOT / "data" / "raw" / "fortune_x_collection"
AUDIT_ROOT = REPO_ROOT / "data" / "audit" / "fortune_x_collection"
REQUIRED_SECRET_NAMES = ("X_AUTH_TOKEN", "X_CT0")
ALLOWED_QUEUE_SOURCE = "human_final_manual_review"
ALLOWED_ELIGIBILITY_SOURCE = "final_manual_scrape_eligible"


@dataclass(frozen=True)
class QueueAccount:
    fortune_rank: int
    company_name: str
    normalized_company_name: str
    collection_x_handle: str
    collection_x_url: str
    secondary_x_url: str

    @property
    def target_user(self) -> str:
        return self.collection_x_handle.strip().lstrip("@")

    @property
    def output_slug(self) -> str:
        return f"rank{self.fortune_rank:03d}_{self.normalized_company_name}"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a bounded Fortune X collection batch.")
    parser.add_argument("--queue-file", default=str(QUEUE_FILE), help="Human-final Fortune X queue CSV.")
    parser.add_argument("--batch-index", type=int, required=True, help="1-based batch index to run.")
    parser.add_argument("--batch-size", type=int, default=10, help="Accounts per batch. Default: 10.")
    parser.add_argument("--concurrency-per-batch", type=int, default=10, help="Concurrent accounts inside this batch. Default: 10.")
    parser.add_argument("--run-id", default=datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S"), help="Run identifier for output paths.")
    parser.add_argument("--max-posts-per-account", type=int, default=50, help="MAX_POSTS passed to the scraper.")
    parser.add_argument("--max-scrolls", type=int, default=250, help="MAX_SCROLLS passed to the scraper.")
    parser.add_argument("--scroll-delay-seconds", default="1.25", help="SCROLL_DELAY_SECONDS passed to the scraper.")
    parser.add_argument("--idle-scroll-limit", type=int, default=20, help="IDLE_SCROLL_LIMIT passed to the scraper.")
    parser.add_argument("--page-timeout-ms", type=int, default=60000, help="PAGE_TIMEOUT_MS passed to the scraper.")
    parser.add_argument("--headless", default="true", choices=["true", "false"], help="HEADLESS passed to the scraper.")
    parser.add_argument("--execute", action="store_true", help="Actually invoke the existing scraper. Omit for dry-run planning.")
    return parser.parse_args()


def read_queue(path: Path) -> list[QueueAccount]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))

    accounts: list[QueueAccount] = []
    for line_number, row in enumerate(rows, start=2):
        if row.get("queue_source", "").strip() != ALLOWED_QUEUE_SOURCE:
            raise ValueError(f"line {line_number}: unsupported queue_source")
        if row.get("eligibility_source_field", "").strip() != ALLOWED_ELIGIBILITY_SOURCE:
            raise ValueError(f"line {line_number}: unsupported eligibility_source_field")
        if row.get("collection_authorized", "").strip().lower() != "false":
            raise ValueError(f"line {line_number}: queue file must remain planning-state collection_authorized=false")
        if row.get("dry_run_only", "").strip().lower() != "true":
            raise ValueError(f"line {line_number}: queue file must remain planning-state dry_run_only=true")
        handle = row.get("collection_x_handle", "").strip()
        url = row.get("collection_x_url", "").strip()
        if not handle or not url:
            raise ValueError(f"line {line_number}: missing collection handle or URL")
        accounts.append(
            QueueAccount(
                fortune_rank=int(row["fortune_rank"]),
                company_name=row["company_name"],
                normalized_company_name=row["normalized_company_name"],
                collection_x_handle=handle,
                collection_x_url=url,
                secondary_x_url=row.get("secondary_x_url", ""),
            )
        )
    return accounts


def select_batch(accounts: list[QueueAccount], batch_index: int, batch_size: int) -> list[QueueAccount]:
    if batch_index < 1:
        raise ValueError("batch-index must be >= 1")
    start = (batch_index - 1) * batch_size
    stop = start + batch_size
    selected = accounts[start:stop]
    if not selected:
        raise ValueError(f"batch-index {batch_index} selected no accounts")
    return selected


def check_auth_available() -> None:
    missing = [name for name in REQUIRED_SECRET_NAMES if not os.getenv(name)]
    if missing:
        names = ", ".join(missing)
        raise RuntimeError(f"required X cookie environment variables are missing: {names}")


def ensure_safe_limits(args: argparse.Namespace) -> None:
    if args.batch_size != 10:
        raise ValueError("batch-size must remain 10 for Fortune Top 100 batch design")
    if args.concurrency_per_batch != 10:
        raise ValueError("concurrency-per-batch must remain 10 so two batches equal 20 concurrent accounts")
    if args.max_posts_per_account != 50:
        raise ValueError("max-posts-per-account must remain 50 for the bounded run")


def output_paths(account: QueueAccount, run_id: str) -> tuple[Path, Path, Path]:
    account_dir = RAW_ROOT / run_id / account.output_slug
    return account_dir, account_dir / "posts.json", account_dir / "scrape_state.json"


def audit_path(run_id: str, batch_index: int) -> Path:
    return AUDIT_ROOT / run_id / f"batch_{batch_index:02d}_collection_audit.csv"


def audit_columns() -> list[str]:
    return [
        "run_id", "batch_index", "fortune_rank", "company_name", "normalized_company_name",
        "collection_x_handle", "collection_x_url", "collection_status", "posts_collected",
        "first_post_timestamp", "last_post_timestamp", "error_type", "error_message_sanitized",
        "started_at", "finished_at", "raw_output_path", "state_output_path",
    ]


def sanitize_error(value: str) -> str:
    sanitized = value.replace(os.getenv("X_AUTH_TOKEN", "__NO_AUTH_TOKEN__"), "[REDACTED]")
    sanitized = sanitized.replace(os.getenv("X_CT0", "__NO_CT0__"), "[REDACTED]")
    return sanitized[-500:].replace("\n", " ").replace("\r", " ")


def load_posts_summary(posts_path: Path) -> tuple[int, str, str]:
    if not posts_path.exists():
        return 0, "", ""
    try:
        posts = json.loads(posts_path.read_text(encoding="utf-8"))
    except Exception:
        return 0, "", ""
    timestamps = [str(post.get("created_at") or "") for post in posts if isinstance(post, dict) and post.get("created_at")]
    return len(posts), (timestamps[-1] if timestamps else ""), (timestamps[0] if timestamps else "")


def write_audit(rows: Iterable[dict[str, str]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=audit_columns())
        writer.writeheader()
        writer.writerows(rows)


async def run_account(account: QueueAccount, args: argparse.Namespace, semaphore: asyncio.Semaphore) -> dict[str, str]:
    async with semaphore:
        started_at = datetime.now(timezone.utc).isoformat()
        account_dir, posts_path, state_path = output_paths(account, args.run_id)
        account_dir.mkdir(parents=True, exist_ok=True)
        env = os.environ.copy()
        env.update({
            "TARGET_USER": account.target_user,
            "BRAND_DIR": str(account_dir),
            "OUTPUT_FILE": str(posts_path),
            "STATE_FILE": str(state_path),
            "MAX_POSTS": str(args.max_posts_per_account),
            "MAX_SCROLLS": str(args.max_scrolls),
            "SCROLL_DELAY_SECONDS": str(args.scroll_delay_seconds),
            "IDLE_SCROLL_LIMIT": str(args.idle_scroll_limit),
            "PAGE_TIMEOUT_MS": str(args.page_timeout_ms),
            "HEADLESS": args.headless,
        })
        process = await asyncio.create_subprocess_exec(
            sys.executable,
            str(SCRAPER_ENTRYPOINT),
            cwd=REPO_ROOT,
            env=env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        output_bytes, _ = await process.communicate()
        finished_at = datetime.now(timezone.utc).isoformat()
        output = output_bytes.decode("utf-8", errors="replace") if output_bytes else ""
        posts_collected, first_ts, last_ts = load_posts_summary(posts_path)
        if process.returncode == 0 and posts_collected > 0:
            status = "collected"
            error_type = ""
            error_message = ""
        elif process.returncode == 0:
            status = "collected_zero_posts"
            error_type = "no_posts_detected"
            error_message = "scraper completed with zero posts"
        else:
            status = "failed_unknown"
            error_type = "unknown_error"
            error_message = sanitize_error(output)
        return {
            "run_id": args.run_id,
            "batch_index": str(args.batch_index),
            "fortune_rank": str(account.fortune_rank),
            "company_name": account.company_name,
            "normalized_company_name": account.normalized_company_name,
            "collection_x_handle": account.collection_x_handle,
            "collection_x_url": account.collection_x_url,
            "collection_status": status,
            "posts_collected": str(posts_collected),
            "first_post_timestamp": first_ts,
            "last_post_timestamp": last_ts,
            "error_type": error_type,
            "error_message_sanitized": error_message,
            "started_at": started_at,
            "finished_at": finished_at,
            "raw_output_path": str(posts_path.relative_to(REPO_ROOT)),
            "state_output_path": str(state_path.relative_to(REPO_ROOT)),
        }


async def run_batch(selected: list[QueueAccount], args: argparse.Namespace) -> list[dict[str, str]]:
    semaphore = asyncio.Semaphore(args.concurrency_per_batch)
    tasks = [run_account(account, args, semaphore) for account in selected]
    return await asyncio.gather(*tasks)


def print_plan(selected: list[QueueAccount], args: argparse.Namespace) -> None:
    print(f"RUN_ID={args.run_id}")
    print(f"batch_index={args.batch_index}")
    print(f"batch_size={args.batch_size}")
    print(f"concurrency_per_batch={args.concurrency_per_batch}")
    print("dry_run=true")
    for account in selected:
        account_dir, posts_path, state_path = output_paths(account, args.run_id)
        print(
            f"PLAN rank={account.fortune_rank:03d} handle={account.collection_x_handle} "
            f"posts={posts_path.relative_to(REPO_ROOT)} state={state_path.relative_to(REPO_ROOT)}"
        )


def main() -> int:
    args = parse_args()
    ensure_safe_limits(args)
    accounts = read_queue(Path(args.queue_file))
    if len(accounts) != 100:
        raise RuntimeError(f"expected 100 queue accounts, found {len(accounts)}")
    selected = select_batch(accounts, args.batch_index, args.batch_size)
    if not args.execute:
        print_plan(selected, args)
        return 0
    check_auth_available()
    rows = asyncio.run(run_batch(selected, args))
    write_audit(rows, audit_path(args.run_id, args.batch_index))
    failures = [row for row in rows if row["collection_status"] not in {"collected", "collected_zero_posts"}]
    print(f"batch_complete={args.batch_index} accounts={len(rows)} failures={len(failures)}")
    return 1 if failures else 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"FAIL: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise SystemExit(1)
