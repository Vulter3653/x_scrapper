#!/usr/bin/env python3
"""Run ranked Fortune 2025 Top 100 X collection through the existing collector.

This script keeps the repository's existing Playwright/browser collector path and
runs accounts sequentially by Fortune rank. It does not use the official X API,
MCP, dashboard sync, screenshots, traces, or browser session persistence.
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
from urllib.parse import urlparse

REPO_ROOT = Path(__file__).resolve().parents[1]
QUEUE_FILE = REPO_ROOT / "config" / "fortune2025_top100_verified_x_collection_queue.csv"
SCRAPER_ENTRYPOINT = REPO_ROOT / "scrape_x.py"
OUTPUT_ROOT = REPO_ROOT / "data" / "raw" / "fortune_x_2025_ranked"
SUMMARY_FILE = REPO_ROOT / "data" / "audit" / "fortune_x_2025_ranked_collection_summary.csv"
REQUIRED_SECRETS = ("X_AUTH_TOKEN", "X_CT0")
COLLECTION_METHOD = "capped browser-based collection of observable public posts"

POST_COLUMNS = [
    "fortune_rank", "company_name", "official_x_handle", "tweet_id", "created_at", "text",
    "tweet_url", "reply_count", "repost_count", "like_count", "quote_count",
    "view_count_available", "media_present", "media_type", "collected_at", "collection_method",
    "max_posts_cap", "source_folder", "source_x_handle", "source_x_url", "account_role",
    "account_index",
]

ACCOUNT_AUDIT_COLUMNS = [
    "fortune_rank", "company_name", "account_index", "account_role", "source_x_handle",
    "source_x_url", "folder", "attempted", "status", "posts_collected", "retryable",
    "error_type", "error_message", "started_at", "completed_at",
]

SUMMARY_COLUMNS = [
    "fortune_rank", "company_name", "official_x_handle", "folder", "attempted", "status",
    "posts_collected", "error_type", "error_message", "started_at", "completed_at",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class TrustedXAccount:
    account_index: int
    account_role: str
    source_x_url: str
    source_x_handle: str

    @property
    def target_user(self) -> str:
        return self.source_x_handle.strip().lstrip("@")


@dataclass(frozen=True)
class QueueCompany:
    fortune_rank: int
    company_name: str
    normalized_company_name: str
    official_x_handle: str
    collection_x_url: str
    secondary_x_url: str
    trusted_accounts: tuple[TrustedXAccount, ...]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Collect Fortune 2025 ranked X accounts sequentially.")
    parser.add_argument("--queue-file", default=str(QUEUE_FILE))
    parser.add_argument("--start-rank", type=int, default=1)
    parser.add_argument("--end-rank", type=int, default=100)
    parser.add_argument("--max-posts", type=int, default=0)
    parser.add_argument("--summary-file", default=str(SUMMARY_FILE))
    parser.add_argument("--retries", type=int, default=2)
    parser.add_argument("--retry-delay-seconds", type=float, default=90.0)
    parser.add_argument("--collector-timeout-seconds", type=float, default=1200.0)
    parser.add_argument("--max-scrolls", type=int, default=2500)
    parser.add_argument("--scroll-delay-seconds", default="1.5")
    parser.add_argument("--idle-scroll-limit", type=int, default=80)
    parser.add_argument("--page-timeout-ms", type=int, default=120000)
    parser.add_argument("--previous-output-root", default="")
    parser.add_argument("--headless", default="true", choices=["true", "false"])
    return parser.parse_args()


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return slug or "value"


def split_url_cell(value: str) -> list[str]:
    parts = re.split(r"[\s,;|]+", value.strip()) if value.strip() else []
    return [part.strip() for part in parts if part.strip()]


def normalize_x_url(value: str) -> str:
    raw = value.strip()
    if not raw:
        return ""
    if raw.startswith("@"):
        raw = f"https://x.com/{raw.lstrip('@')}"
    if not re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", raw):
        raw = f"https://{raw}"
    parsed = urlparse(raw)
    host = parsed.netloc.lower().removeprefix("www.")
    if host not in {"x.com", "twitter.com"}:
        return ""
    segments = [segment for segment in parsed.path.split("/") if segment]
    if not segments:
        return ""
    handle = segments[0].strip().lstrip("@")
    if not re.match(r"^[A-Za-z0-9_]{1,15}$", handle):
        return ""
    return f"https://x.com/{handle}"


def extract_handle_from_x_url(value: str) -> str:
    normalized = normalize_x_url(value)
    if not normalized:
        return ""
    return urlparse(normalized).path.strip("/").split("/", 1)[0]


def trusted_accounts_from_row(row: dict[str, str]) -> tuple[TrustedXAccount, ...]:
    candidates: list[tuple[str, str]] = []
    primary = normalize_x_url(row.get("collection_x_url", ""))
    if primary:
        candidates.append(("primary", primary))
    for secondary in split_url_cell(row.get("secondary_x_url", "")):
        normalized = normalize_x_url(secondary)
        if normalized:
            candidates.append(("secondary", normalized))

    accounts: list[TrustedXAccount] = []
    seen_urls: set[str] = set()
    for role, url in candidates:
        key = url.lower()
        if key in seen_urls:
            continue
        seen_urls.add(key)
        handle = extract_handle_from_x_url(url)
        if not handle:
            continue
        accounts.append(
            TrustedXAccount(
                account_index=len(accounts) + 1,
                account_role=role,
                source_x_url=url,
                source_x_handle=f"@{handle}",
            )
        )
    return tuple(accounts)


def company_folder_name(company: QueueCompany, seen: set[str]) -> str:
    base = f"{company.fortune_rank:03d}_{slugify(company.company_name)}"
    folder = base
    if folder in seen:
        folder = f"{base}_{slugify(company.normalized_company_name)}"
    seen.add(folder)
    return folder


def account_folder_name(account: TrustedXAccount) -> str:
    handle = account.source_x_handle.lstrip("@")
    return f"{account.account_index:02d}_{account.account_role}_{slugify(handle)}"


def read_queue(path: Path, start_rank: int, end_rank: int) -> list[QueueCompany]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    companies: list[QueueCompany] = []
    for row in rows:
        rank = int(row["fortune_rank"])
        if rank < start_rank or rank > end_rank:
            continue
        if row.get("queue_source") != "human_final_manual_review":
            continue
        if row.get("eligibility_source_field") != "final_manual_scrape_eligible":
            continue
        accounts = trusted_accounts_from_row(row)
        companies.append(
            QueueCompany(
                fortune_rank=rank,
                company_name=row["company_name"],
                normalized_company_name=row["normalized_company_name"],
                official_x_handle=row.get("collection_x_handle", "").strip(),
                collection_x_url=row.get("collection_x_url", "").strip(),
                secondary_x_url=row.get("secondary_x_url", "").strip(),
                trusted_accounts=accounts,
            )
        )
    return sorted(companies, key=lambda company: company.fortune_rank)


def post_value(post: dict[str, Any], key: str) -> Any:
    value = post.get(key)
    return value if value is not None else ""


def write_posts_csv(
    path: Path,
    company: QueueCompany,
    trusted_account: TrustedXAccount,
    source_folder: str,
    posts: list[dict[str, Any]],
    max_posts: int,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    collected_at = utc_now()
    capped_posts = posts[:max_posts] if max_posts else posts
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=POST_COLUMNS)
        writer.writeheader()
        for post in capped_posts:
            writer.writerow({
                "fortune_rank": company.fortune_rank,
                "company_name": company.company_name,
                "official_x_handle": company.official_x_handle,
                "tweet_id": str(post_value(post, "id")),
                "created_at": post_value(post, "created_at"),
                "text": post_value(post, "text"),
                "tweet_url": post_value(post, "tweet_url"),
                "reply_count": post_value(post, "reply_count"),
                "repost_count": post_value(post, "retweet_count"),
                "like_count": post_value(post, "favorite_count"),
                "quote_count": post_value(post, "quote_count"),
                "view_count_available": "true" if post.get("view_count") not in (None, "") else "false",
                "media_present": "false",
                "media_type": "",
                "collected_at": collected_at,
                "collection_method": COLLECTION_METHOD,
                "max_posts_cap": max_posts,
                "source_folder": source_folder,
                "source_x_handle": trusted_account.source_x_handle,
                "source_x_url": trusted_account.source_x_url,
                "account_role": trusted_account.account_role,
                "account_index": trusted_account.account_index,
            })


def write_audit_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_csv_rows(path: Path, columns: list[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, "") for column in columns})


def sanitize_error(value: str) -> str:
    sanitized = value
    for secret_name in REQUIRED_SECRETS:
        secret_value = os.getenv(secret_name)
        if secret_value:
            sanitized = sanitized.replace(secret_value, "[REDACTED]")
    return sanitized[-1000:].replace("\r", " ").replace("\n", " ")


def credential_missing() -> bool:
    return any(not os.getenv(name) for name in REQUIRED_SECRETS)


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


def load_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def is_true(value: Any) -> bool:
    return value is True or (isinstance(value, str) and value.strip().lower() == "true")


def is_false(value: Any) -> bool:
    return value is False or (isinstance(value, str) and value.strip().lower() == "false")


def zero_posts_terminal_state(state: dict[str, Any], posts_count: int) -> bool:
    return (
        is_true(state.get("profile_loaded"))
        and is_true(state.get("account_exists"))
        and is_false(state.get("login_wall"))
        and is_false(state.get("error_page"))
        and posts_count == 0
    )


def retryable_status(status: str) -> bool:
    return status not in {"success", "no_observable_posts"}


def collect_trusted_account(
    company: QueueCompany,
    trusted_account: TrustedXAccount,
    company_folder: str,
    account_folder: str,
    args: argparse.Namespace,
) -> dict[str, Any]:
    started_at = utc_now()
    account_path = OUTPUT_ROOT / company_folder / "accounts" / account_folder
    posts_csv = account_path / "posts.csv"
    audit_json = account_path / "audit.json"
    tmp_posts_json = account_path / "_collector_posts.json"
    tmp_state_json = account_path / "_collector_state.json"
    source_folder = str(account_path.relative_to(REPO_ROOT))

    base_audit = {
        "fortune_rank": company.fortune_rank,
        "company_name": company.company_name,
        "official_x_handle": company.official_x_handle,
        "account_index": trusted_account.account_index,
        "account_role": trusted_account.account_role,
        "source_x_handle": trusted_account.source_x_handle,
        "source_x_url": trusted_account.source_x_url,
        "folder": source_folder,
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
    }

    if credential_missing():
        write_posts_csv(posts_csv, company, trusted_account, source_folder, [], args.max_posts)
        audit = {**base_audit, "completed_at": utc_now(), "error_type": "credential_missing", "error_message": "required X cookie secrets are missing"}
        write_audit_json(audit_json, audit)
        return audit

    account_path.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env.update({
        "TARGET_USER": trusted_account.target_user,
        "BRAND_DIR": str(account_path),
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
                timeout=args.collector_timeout_seconds,
            )
            completed_at = utc_now()
            if result.returncode == 0:
                posts = load_posts(tmp_posts_json)
                state = load_state(tmp_state_json)
                if posts:
                    status = "success"
                    error_type = ""
                    error_message = ""
                elif zero_posts_terminal_state(state, len(posts)):
                    status = "no_observable_posts"
                    error_type = "no_observable_posts"
                    error_message = "profile loaded but no observable posts were collected"
                else:
                    status = "failed"
                    error_type = "zero_posts_uncertain"
                    error_message = "collector returned success but produced zero posts and profile validity was uncertain"
            else:
                posts = []
                status = "failed"
                error_type = "collector_failed"
                error_message = sanitize_error((result.stdout or "") + " " + (result.stderr or ""))
            write_posts_csv(posts_csv, company, trusted_account, source_folder, posts, args.max_posts)
            capped_posts = posts[:args.max_posts] if args.max_posts else posts
            audit = {
                **base_audit,
                "attempted": True,
                "status": status,
                "posts_collected": len(capped_posts),
                "completed_at": completed_at,
                "error_type": error_type,
                "error_message": error_message,
                "browser_collection_used": True,
                "retryable": retryable_status(status),
            }
        except subprocess.TimeoutExpired as exc:
            write_posts_csv(posts_csv, company, trusted_account, source_folder, [], args.max_posts)
            audit = {
                **base_audit,
                "attempted": True,
                "status": "failed",
                "posts_collected": 0,
                "completed_at": utc_now(),
                "error_type": "collector_timeout",
                "error_message": sanitize_error(str(exc)),
                "browser_collection_used": True,
                "retryable": True,
            }
        except Exception as exc:
            write_posts_csv(posts_csv, company, trusted_account, source_folder, [], args.max_posts)
            audit = {
                **base_audit,
                "attempted": True,
                "status": "failed",
                "posts_collected": 0,
                "completed_at": utc_now(),
                "error_type": type(exc).__name__,
                "error_message": sanitize_error(str(exc)),
                "browser_collection_used": True,
                "retryable": True,
            }

        if not audit.get("retryable", retryable_status(str(audit.get("status", "")))):
            break
        if attempt < attempts:
            print(
                f"retry_rank={company.fortune_rank:03d} account={trusted_account.source_x_handle} "
                f"attempt={attempt + 1}/{attempts} delay_seconds={args.retry_delay_seconds}",
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


def read_account_posts(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return list(reader)


def merge_company_posts(company_path: Path, account_folders: list[str]) -> int:
    merged: list[dict[str, str]] = []
    seen_tweet_ids: set[str] = set()
    for folder in account_folders:
        posts_path = company_path / "accounts" / folder / "posts.csv"
        for row in read_account_posts(posts_path):
            tweet_id = (row.get("tweet_id") or "").strip()
            if tweet_id:
                if tweet_id in seen_tweet_ids:
                    continue
                seen_tweet_ids.add(tweet_id)
            merged.append(row)
    write_csv_rows(company_path / "posts.csv", POST_COLUMNS, merged)
    return len(merged)


def company_status(account_audits: list[dict[str, Any]]) -> str:
    if not account_audits:
        return "skipped"
    statuses = {audit.get("status") for audit in account_audits}
    if statuses == {"success"}:
        return "success"
    if statuses == {"no_observable_posts"}:
        return "no_observable_posts"
    if "success" in statuses and statuses <= {"success", "no_observable_posts"}:
        return "success"
    if "success" in statuses:
        return "partial_success"
    if "no_observable_posts" in statuses and statuses <= {"no_observable_posts", "skipped"}:
        return "no_observable_posts"
    if statuses == {"skipped"}:
        return "skipped"
    return "failed"


def write_company_outputs(company: QueueCompany, company_folder: str, account_audits: list[dict[str, Any]], account_folders: list[str], args: argparse.Namespace) -> dict[str, Any]:
    company_path = OUTPUT_ROOT / company_folder
    posts_collected = merge_company_posts(company_path, account_folders)
    status = company_status(account_audits)
    attempted = any(bool(audit.get("attempted")) for audit in account_audits)
    error_rows = [audit for audit in account_audits if audit.get("error_type")]
    started_values = [str(audit.get("started_at") or "") for audit in account_audits if audit.get("started_at")]
    completed_values = [str(audit.get("completed_at") or "") for audit in account_audits if audit.get("completed_at")]

    account_audit_rows = []
    for audit in account_audits:
        account_audit_rows.append({
            "fortune_rank": audit.get("fortune_rank", ""),
            "company_name": audit.get("company_name", ""),
            "account_index": audit.get("account_index", ""),
            "account_role": audit.get("account_role", ""),
            "source_x_handle": audit.get("source_x_handle", ""),
            "source_x_url": audit.get("source_x_url", ""),
            "folder": audit.get("folder", ""),
            "attempted": str(audit.get("attempted", False)).lower(),
            "status": audit.get("status", ""),
            "posts_collected": audit.get("posts_collected", ""),
            "retryable": str(audit.get("retryable", retryable_status(str(audit.get("status", ""))))).lower(),
            "error_type": audit.get("error_type", ""),
            "error_message": audit.get("error_message", ""),
            "started_at": audit.get("started_at", ""),
            "completed_at": audit.get("completed_at", ""),
        })
    write_csv_rows(company_path / "account_audit.csv", ACCOUNT_AUDIT_COLUMNS, account_audit_rows)

    company_audit = {
        "fortune_rank": company.fortune_rank,
        "company_name": company.company_name,
        "official_x_handle": company.official_x_handle,
        "collection_x_url": company.collection_x_url,
        "secondary_x_url": company.secondary_x_url,
        "folder": str(company_path.relative_to(REPO_ROOT)),
        "attempted": attempted,
        "status": status,
        "posts_collected": posts_collected,
        "account_count": len(account_audits),
        "accounts": account_audits,
        "max_posts_cap": args.max_posts,
        "started_at": min(started_values) if started_values else "",
        "completed_at": max(completed_values) if completed_values else "",
        "error_type": ";".join(sorted({str(row.get("error_type")) for row in error_rows if row.get("error_type")})),
        "error_message": " | ".join(str(row.get("error_message", "")) for row in error_rows if row.get("error_message"))[:1000],
        "collection_method": COLLECTION_METHOD,
        "browser_collection_used": any(bool(audit.get("browser_collection_used")) for audit in account_audits),
        "x_api_used": False,
    }
    write_audit_json(company_path / "audit.json", company_audit)
    return company_audit


def skipped_company(company: QueueCompany, company_folder: str, args: argparse.Namespace, error_type: str, error_message: str) -> dict[str, Any]:
    company_path = OUTPUT_ROOT / company_folder
    write_csv_rows(company_path / "posts.csv", POST_COLUMNS, [])
    write_csv_rows(company_path / "account_audit.csv", ACCOUNT_AUDIT_COLUMNS, [])
    audit = {
        "fortune_rank": company.fortune_rank,
        "company_name": company.company_name,
        "official_x_handle": company.official_x_handle,
        "collection_x_url": company.collection_x_url,
        "secondary_x_url": company.secondary_x_url,
        "folder": str(company_path.relative_to(REPO_ROOT)),
        "attempted": False,
        "status": "skipped",
        "posts_collected": 0,
        "account_count": 0,
        "accounts": [],
        "max_posts_cap": args.max_posts,
        "started_at": utc_now(),
        "completed_at": utc_now(),
        "error_type": error_type,
        "error_message": error_message,
        "collection_method": COLLECTION_METHOD,
        "browser_collection_used": False,
        "x_api_used": False,
    }
    write_audit_json(company_path / "audit.json", audit)
    return audit


def main() -> int:
    args = parse_args()
    if args.start_rank < 1 or args.end_rank > 100 or args.start_rank > args.end_rank:
        raise SystemExit("rank range must be within 1-100 and start_rank <= end_rank")
    if args.max_posts < 0:
        raise SystemExit("max_posts must be >= 0")
    if args.retries < 0:
        raise SystemExit("retries must be >= 0")
    if args.retry_delay_seconds < 0:
        raise SystemExit("retry_delay_seconds must be >= 0")
    if args.collector_timeout_seconds < 0:
        raise SystemExit("collector_timeout_seconds must be >= 0")

    companies = read_queue(Path(args.queue_file), args.start_rank, args.end_rank)
    seen_folders: set[str] = set()
    summary_rows: list[dict[str, Any]] = []

    for company in companies:
        company_folder = company_folder_name(company, seen_folders)
        if not company.trusted_accounts:
            print(f"collect_rank={company.fortune_rank:03d} company={company.company_name} trusted_accounts=0", flush=True)
            audit = skipped_company(company, company_folder, args, "missing_trusted_url", "missing trusted X URL")
        else:
            print(
                f"collect_rank={company.fortune_rank:03d} company={company.company_name} "
                f"trusted_accounts={len(company.trusted_accounts)}",
                flush=True,
            )
            account_audits: list[dict[str, Any]] = []
            account_folders: list[str] = []
            for trusted_account in company.trusted_accounts:
                folder = account_folder_name(trusted_account)
                account_folders.append(folder)
                print(
                    f"collect_rank={company.fortune_rank:03d} account={trusted_account.source_x_handle} "
                    f"role={trusted_account.account_role} index={trusted_account.account_index}",
                    flush=True,
                )
                account_audits.append(collect_trusted_account(company, trusted_account, company_folder, folder, args))
                time.sleep(1)
            audit = write_company_outputs(company, company_folder, account_audits, account_folders, args)

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

    write_csv_rows(Path(args.summary_file), SUMMARY_COLUMNS, summary_rows)
    failed = sum(1 for row in summary_rows if row["status"] == "failed")
    skipped = sum(1 for row in summary_rows if row["status"] == "skipped")
    print(f"ranked_collection_complete attempted={len(summary_rows) - skipped} failed={failed} skipped={skipped}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
