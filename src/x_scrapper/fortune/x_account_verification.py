#!/usr/bin/env python3
"""Check direct X profile candidates for Fortune 2025 ranked companies.

The first-pass candidate is https://x.com/{normalized firm name}, for example
Amazon -> https://x.com/amazon. This script does not certify an account as the
official corporate account. It only checks whether the direct profile URL appears
accessible when authenticated X cookies are available.
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import os
import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from x_scrapper.paths import AUDIT_ROOT, CONFIG_ROOT, REPO_ROOT
from typing import Iterable

try:
    from playwright.async_api import TimeoutError as PlaywrightTimeoutError
    from playwright.async_api import async_playwright
except Exception:  # pragma: no cover - import error is reported in main.
    PlaywrightTimeoutError = Exception
    async_playwright = None

DEFAULT_INPUT = REPO_ROOT / "fortune2025_itemListElement_rows.csv"
DEFAULT_OUTPUT = CONFIG_ROOT / "fortune2025_top100_x_direct_check.csv"
DEFAULT_AUDIT = AUDIT_ROOT / "fortune2025_top100_x_direct_profile_audit.csv"
DEFAULT_ACCOUNT_INDEX = CONFIG_ROOT / "fortune2025_top100_x_account_index.csv"

RESULT_FIELDS = [
    "fortune_year",
    "fortune_rank",
    "firm_name",
    "entity_type",
    "fortune_company_url",
    "direct_x_handle_candidate",
    "direct_x_profile_url",
    "direct_profile_exists",
    "direct_check_status",
    "x_access_method",
    "page_title",
    "current_url",
    "checked_at",
    "needs_manual_review",
    "notes",
]

ACCOUNT_INDEX_FIELDS = [
    "fortune_year",
    "fortune_rank",
    "firm_name",
    "entity_type",
    "fortune_company_url",
    "official_x_account_status",
    "direct_x_profile_exists",
    "direct_x_handle_candidate",
    "direct_x_profile_url",
    "direct_check_status",
    "x_access_method",
    "page_title",
    "current_url",
    "needs_manual_review",
    "review_decision",
    "reviewed_x_handle",
    "reviewed_x_profile_url",
    "source_file",
    "notes",
    "generated_at",
]

AUDIT_FIELDS = [
    "fortune_rank",
    "firm_name",
    "direct_x_profile_url",
    "attempted_at",
    "status",
    "direct_profile_exists",
    "error_type",
    "error_message",
    "page_title",
    "current_url",
    "elapsed_seconds",
    "notes",
]

UNAVAILABLE_PATTERNS = [
    "This account doesn",
    "This account doesn't exist",
    "Try searching for another",
    "Hmm...this page doesn",
    "Page not found",
]
LOGIN_PATTERNS = [
    "Sign in to X",
    "Log in to X",
    "Login to X",
    "Sign in",
]
RATE_LIMIT_PATTERNS = [
    "rate limit",
    "Something went wrong",
    "Try again",
]
PROFILE_MARKERS = [
    "data-testid=\"UserName\"",
    "data-testid=\"UserDescription\"",
    "Followers",
    "Following",
]


@dataclass
class FortuneRow:
    fortune_year: str
    fortune_rank: int
    firm_name: str
    entity_type: str
    fortune_company_url: str


def normalize_handle_candidate(name: str) -> str:
    """Convert a Fortune firm name to the first-pass direct X handle candidate."""
    normalized = name.strip().lower()
    normalized = normalized.replace("&", "and")
    normalized = normalized.replace("+", "plus")
    normalized = re.sub(r"[^a-z0-9]+", "", normalized)
    return normalized


def read_fortune_rows(path: Path, limit: int) -> list[FortuneRow]:
    rows: list[FortuneRow] = []
    with path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for raw in reader:
            rank_text = (raw.get("fortune 2025 rank") or raw.get("fortune_rank") or "").strip()
            if not rank_text:
                continue
            try:
                rank = int(rank_text)
            except ValueError:
                continue
            if limit and rank > limit:
                continue
            rows.append(
                FortuneRow(
                    fortune_year="2025",
                    fortune_rank=rank,
                    firm_name=(raw.get("name") or raw.get("firm_name") or "").strip(),
                    entity_type=(raw.get("type") or raw.get("entity_type") or "").strip(),
                    fortune_company_url=(raw.get("id") or raw.get("fortune_company_url") or "").strip(),
                )
            )
    rows.sort(key=lambda row: row.fortune_rank)
    return rows


def write_csv(path: Path, fieldnames: list[str], rows: Iterable[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def base_result(row: FortuneRow, checked_at: str, status: str, exists: str, notes: str, page_title: str = "", current_url: str = "") -> dict[str, str]:
    handle = normalize_handle_candidate(row.firm_name)
    return {
        "fortune_year": row.fortune_year,
        "fortune_rank": str(row.fortune_rank),
        "firm_name": row.firm_name,
        "entity_type": row.entity_type,
        "fortune_company_url": row.fortune_company_url,
        "direct_x_handle_candidate": f"@{handle}" if handle else "",
        "direct_x_profile_url": f"https://x.com/{handle}" if handle else "",
        "direct_profile_exists": exists,
        "direct_check_status": status,
        "x_access_method": "authenticated_playwright" if os.getenv("X_AUTH_TOKEN") and os.getenv("X_CT0") else "not_checked_missing_credentials",
        "page_title": page_title,
        "current_url": current_url,
        "checked_at": checked_at,
        "needs_manual_review": "1",
        "notes": notes,
    }



def build_account_index_rows(results: list[dict[str, str]], generated_at: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for result in results:
        rows.append({
            "fortune_year": result["fortune_year"],
            "fortune_rank": result["fortune_rank"],
            "firm_name": result["firm_name"],
            "entity_type": result["entity_type"],
            "fortune_company_url": result["fortune_company_url"],
            "official_x_account_status": "unknown",
            "direct_x_profile_exists": result["direct_profile_exists"],
            "direct_x_handle_candidate": result["direct_x_handle_candidate"],
            "direct_x_profile_url": result["direct_x_profile_url"],
            "direct_check_status": result["direct_check_status"],
            "x_access_method": result["x_access_method"],
            "page_title": result["page_title"],
            "current_url": result["current_url"],
            "needs_manual_review": "1",
            "review_decision": "",
            "reviewed_x_handle": "",
            "reviewed_x_profile_url": "",
            "source_file": "fortune2025_itemListElement_rows.csv; fortune2025_top100_x_direct_check.csv",
            "notes": result["notes"],
            "generated_at": generated_at,
        })
    return rows

def audit_row(row: FortuneRow, url: str, attempted_at: str, status: str, exists: str, elapsed: float, notes: str, error_type: str = "", error_message: str = "", page_title: str = "", current_url: str = "") -> dict[str, str]:
    return {
        "fortune_rank": str(row.fortune_rank),
        "firm_name": row.firm_name,
        "direct_x_profile_url": url,
        "attempted_at": attempted_at,
        "status": status,
        "direct_profile_exists": exists,
        "error_type": error_type,
        "error_message": error_message[:500],
        "page_title": page_title,
        "current_url": current_url,
        "elapsed_seconds": f"{elapsed:.3f}",
        "notes": notes,
    }


def classify_html(html: str, title: str, current_url: str) -> tuple[str, str, str]:
    haystack = f"{title}\n{current_url}\n{html}"
    if any(pattern.lower() in haystack.lower() for pattern in UNAVAILABLE_PATTERNS):
        return "not_found", "no", "Direct X URL rendered a not-found/unavailable account message."
    if any(pattern.lower() in haystack.lower() for pattern in LOGIN_PATTERNS):
        return "login_challenge", "unknown", "X required login or presented a login challenge."
    if any(pattern.lower() in haystack.lower() for pattern in RATE_LIMIT_PATTERNS):
        return "rate_limited_or_transient", "unknown", "X returned a transient/rate-limit style page."
    if any(marker in html for marker in PROFILE_MARKERS):
        return "profile_accessible", "yes", "Direct X profile markers were detected. This does not prove official corporate ownership."
    if "x.com" in current_url.lower() and title:
        return "ambiguous_render", "unknown", "X page rendered but profile/not-found markers were inconclusive."
    return "selector_not_found", "unknown", "X page rendered without recognized profile or unavailable markers."


async def run_authenticated_checks(rows: list[FortuneRow], args: argparse.Namespace) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    if async_playwright is None:
        raise RuntimeError("playwright is not installed. Install requirements-scrape.txt first.")

    auth_token = os.getenv("X_AUTH_TOKEN")
    ct0 = os.getenv("X_CT0")
    checked_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    results: list[dict[str, str]] = []
    audits: list[dict[str, str]] = []

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=args.headless)
        context = await browser.new_context(viewport={"width": 1280, "height": 900})
        await context.add_cookies(
            [
                {"name": "auth_token", "value": auth_token, "domain": ".x.com", "path": "/", "httpOnly": True, "secure": True, "sameSite": "None"},
                {"name": "ct0", "value": ct0, "domain": ".x.com", "path": "/", "httpOnly": False, "secure": True, "sameSite": "Lax"},
            ]
        )
        page = await context.new_page()
        for row in rows:
            handle = normalize_handle_candidate(row.firm_name)
            url = f"https://x.com/{handle}"
            started = time.monotonic()
            status = "error"
            exists = "unknown"
            notes = ""
            error_type = ""
            error_message = ""
            title = ""
            current_url = ""
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=args.timeout_ms)
                await page.wait_for_timeout(args.delay_ms)
                title = await page.title()
                current_url = page.url
                html = await page.content()
                status, exists, notes = classify_html(html, title, current_url)
            except PlaywrightTimeoutError as exc:
                status = "timeout"
                error_type = type(exc).__name__
                error_message = str(exc)
                notes = "Timed out while loading direct X profile URL."
            except Exception as exc:  # pragma: no cover - network/UI dependent
                status = "error"
                error_type = type(exc).__name__
                error_message = str(exc)
                notes = "Unexpected error while checking direct X profile URL."
            elapsed = time.monotonic() - started
            results.append(base_result(row, checked_at, status, exists, notes, title, current_url))
            audits.append(audit_row(row, url, checked_at, status, exists, elapsed, notes, error_type, error_message, title, current_url))
            print(f"{row.fortune_rank}: {row.firm_name} -> {url} status={status} exists={exists}", flush=True)
        await browser.close()
    return results, audits


def run_missing_credentials(rows: list[FortuneRow]) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    checked_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    results = []
    audits = []
    notes = "X_AUTH_TOKEN and/or X_CT0 missing; generated direct URL candidates but did not verify profile existence."
    for row in rows:
        result = base_result(row, checked_at, "not_checked_missing_credentials", "unknown", notes)
        results.append(result)
        audits.append(audit_row(row, result["direct_x_profile_url"], checked_at, "not_checked_missing_credentials", "unknown", 0.0, notes, "missing_credentials", "X_AUTH_TOKEN and/or X_CT0 is not set."))
    return results, audits


async def async_main(args: argparse.Namespace) -> int:
    rows = read_fortune_rows(args.input, args.rank_limit)
    if not rows:
        raise SystemExit(f"No Fortune rows found in {args.input}")
    if not os.getenv("X_AUTH_TOKEN") or not os.getenv("X_CT0"):
        results, audits = run_missing_credentials(rows)
    else:
        results, audits = await run_authenticated_checks(rows, args)
    write_csv(args.output, RESULT_FIELDS, results)
    write_csv(args.audit, AUDIT_FIELDS, audits)
    generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    account_index_rows = build_account_index_rows(results, generated_at)
    write_csv(args.account_index, ACCOUNT_INDEX_FIELDS, account_index_rows)
    print(f"wrote {len(results)} rows to {args.output}")
    print(f"wrote {len(audits)} rows to {args.audit}")
    print(f"wrote {len(account_index_rows)} rows to {args.account_index}")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check direct https://x.com/{company-name} profile candidates for Fortune 2025 rows.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--audit", type=Path, default=DEFAULT_AUDIT)
    parser.add_argument("--account-index", type=Path, default=DEFAULT_ACCOUNT_INDEX)
    parser.add_argument("--rank-limit", type=int, default=100, help="Highest Fortune rank to include. Default 100 for stable Fortune top 100 checks.")
    parser.add_argument("--timeout-ms", type=int, default=30000)
    parser.add_argument("--delay-ms", type=int, default=1500)
    parser.add_argument("--headless", default=os.getenv("HEADLESS", "true").lower() in {"1", "true", "yes"}, action=argparse.BooleanOptionalAction)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    return asyncio.run(async_main(args))


if __name__ == "__main__":
    raise SystemExit(main())
