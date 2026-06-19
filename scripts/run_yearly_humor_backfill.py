#!/usr/bin/env python3
"""Year-serial, company-parallel humor backfill runner.

Years are processed in serial order (start_year -> end_year, or target_year only).
Within each year, eligible companies run in parallel up to max_parallel_companies.

Smoke diagnostics are intentionally separate from full historical runs:
  - --smoke caps the run to a small selected set, max_scrolls <= 300, and a
    per-company timeout of 180s unless explicitly overridden.
  - A 99-company, max_scrolls=3500 run is a full historical run, not smoke.

Outputs staged to data/backfill/yearly_humor/{year}/ — does NOT touch data/raw,
dashboard/data, classifier outputs, or the integrated corpus.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import statistics
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRAPER = REPO_ROOT / "scrape_x.py"
OUT_ROOT = REPO_ROOT / "data" / "backfill" / "yearly_humor"
GLOBAL_AUDIT = OUT_ROOT / "audit"

MIN_YEAR = 2009
MAX_YEAR = 2021
LOG_TAIL_CHARS = 8000
SMOKE_MAX_SCROLLS_CAP = 300
SMOKE_DEFAULT_LIMIT_COMPANIES = 3
SMOKE_DEFAULT_COMPANY_TIMEOUT_SECONDS = 180
DEFAULT_COMPANY_TIMEOUT_SECONDS = 300

RECOVERABLE_STATUSES = frozenset({
    "recoverable_failed_timeout",
    "recoverable_failed_company_timeout",
    "recoverable_failed_network",
    "recoverable_failed_browser",
    "recoverable_failed_render",
    "recoverable_failed_did_not_reach_year",
    "recoverable_failed_temporary_x_error",
})
TERMINAL_STATUSES = frozenset({
    "terminal_account_unavailable",
    "terminal_account_protected",
    "terminal_account_suspended",
    "terminal_created_after_year",
    "terminal_no_observable_posts_for_year",
})
RENDER_FAILURE_SUBTYPES = frozenset({
    "render_failure_login_or_auth",
    "render_failure_rate_limit_or_block",
    "render_failure_selector_missing",
    "render_failure_timeout",
    "render_failure_unknown",
})

SUMMARY_FIELDS = [
    "target_year", "target_company_count", "attempted_company_count",
    "success_count", "recoverable_failure_count", "terminal_status_count",
    "skipped_not_active_count", "posts_collected", "new_unique_posts",
    "duplicate_posts", "min_date", "max_date", "retry_round", "completed_at",
    "smoke_mode", "full_target_company_count", "selected_company_count",
    "input_max_scrolls", "effective_max_scrolls", "max_scrolls_cap_reason",
    "per_company_timeout_seconds", "total_elapsed_seconds",
    "median_company_elapsed_seconds", "max_company_elapsed_seconds",
    "timeout_count", "company_timeout_count", "render_failure_count",
    "render_failure_login_or_auth_count", "render_failure_rate_limit_or_block_count",
    "render_failure_selector_missing_count", "render_failure_timeout_count",
    "render_failure_unknown_count", "did_not_reach_year_count",
    "companies_with_raw_posts_count", "companies_with_zero_scroll_count",
    "min_seen_date_overall", "max_seen_date_overall",
    "median_scrolls_completed", "max_scrolls_completed",
    "recoverable_render_failure_count", "recoverable_did_not_reach_year_count",
    "terminal_created_after_year_count",
    "terminal_created_after_year_with_account_created_evidence_count",
    "companies_with_scrolls_zero",
    "companies_with_raw_posts_but_no_target_year_posts",
    "max_parallel_companies", "run_mode", "validation_status",
    "validation_warning_count",
]

RESULT_FIELDS = [
    "fortune_rank", "company_name", "handle", "sample_group",
    "account_created_year", "target_year", "status", "attempts",
    "posts_collected_raw", "posts_on_or_before_year", "new_unique_posts",
    "duplicate_posts", "min_date", "max_date", "reached_cutoff_date",
    "stopped_reason", "scrolls_completed", "retry_round", "last_error",
    "smoke_mode", "full_target_company_count", "selected_company_count",
    "input_max_scrolls", "effective_max_scrolls", "max_scrolls_cap_reason",
    "per_company_timeout_seconds", "company_timeout_triggered",
    "failure_subtype", "elapsed_seconds", "stdout_tail_path", "stderr_tail_path",
    "combined_tail_path", "exit_status_path", "min_date_seen", "max_date_seen",
    "raw_collected", "posts_on_or_before_target_year",
]


def slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_") or "target"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def parse_bool_text(value: Any) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


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
            return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc)
        except ValueError:
            continue
    return None


def parse_year_int(value: Any) -> int | None:
    s = str(value or "").strip()
    if re.fullmatch(r"\d{4}", s):
        y = int(s)
        return y if 1990 <= y <= 2030 else None
    m = re.match(r"(\d{4})-", s)
    if m:
        y = int(m.group(1))
        return y if 1990 <= y <= 2030 else None
    return None


def load_json(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except Exception:
        return []


def save_json(path: Path, posts: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(posts, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def median(values: list[float]) -> str:
    return f"{statistics.median(values):.3f}" if values else ""


def max_number(values: list[float]) -> str:
    return f"{max(values):.3f}" if values else ""


def classify_failure_subtype(exc_text: str, log_text: str = "") -> str:
    combined = (exc_text + " " + log_text).lower()
    if any(token in combined for token in ("login", "auth", "unauthorized", "cookie", "sign in", "signin")):
        return "render_failure_login_or_auth"
    if any(token in combined for token in ("rate limit", "too many", "blocked", "429", "temporarily restricted")):
        return "render_failure_rate_limit_or_block"
    if any(token in combined for token in ("selector", "locator", "not visible", "no element", "elementhandle", "queryselector")):
        return "render_failure_selector_missing"
    if any(token in combined for token in ("timeout", "timed out", "page timeout", "navigation timeout")):
        return "render_failure_timeout"
    if any(token in combined for token in ("render", "browser", "playwright", "chromium", "target closed")):
        return "render_failure_unknown"
    return ""


def classify_error(exc_text: str, log_text: str = "") -> str:
    combined = (exc_text + " " + log_text).lower()
    if "timeout" in combined or "timed out" in combined:
        return "recoverable_failed_timeout"
    if "network" in combined or "connection" in combined or "dns" in combined:
        return "recoverable_failed_network"
    if "protected" in combined or "private" in combined:
        return "terminal_account_protected"
    if "suspended" in combined or "not found" in combined or "does not exist" in combined:
        return "terminal_account_unavailable"
    if "rate limit" in combined or "temporarily" in combined or "too many" in combined:
        return "recoverable_failed_temporary_x_error"
    if classify_failure_subtype(exc_text, log_text):
        return "recoverable_failed_render"
    return "recoverable_failed_browser"


def is_retryable_result(row: dict[str, Any]) -> bool:
    status = str(row.get("status", ""))
    if status in TERMINAL_STATUSES or status.startswith("terminal_"):
        return False
    if status in RECOVERABLE_STATUSES or status.startswith("recoverable_failed_"):
        return True
    subtype = str(row.get("failure_subtype", ""))
    return subtype in RENDER_FAILURE_SUBTYPES


def _coerce_output(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


def _save_logs(posts_dir: Path, stdout: str, stderr: str, exit_code: int,
               timed_out: bool = False) -> dict[str, str]:
    stdout_tail = stdout[-LOG_TAIL_CHARS:]
    stderr_tail = stderr[-LOG_TAIL_CHARS:]
    combined_tail = (stdout_tail + "\n---STDERR---\n" + stderr_tail)[-LOG_TAIL_CHARS:]
    paths = {
        "stdout_tail_path": posts_dir / "scraper_stdout_tail.txt",
        "stderr_tail_path": posts_dir / "scraper_stderr_tail.txt",
        "combined_tail_path": posts_dir / "scraper_combined_tail.txt",
        "exit_status_path": posts_dir / "scraper_exit_status.json",
    }
    try:
        paths["stdout_tail_path"].write_text(stdout_tail, encoding="utf-8")
        paths["stderr_tail_path"].write_text(stderr_tail, encoding="utf-8")
        paths["combined_tail_path"].write_text(combined_tail, encoding="utf-8")
        paths["exit_status_path"].write_text(
            json.dumps({"exit_code": exit_code, "timed_out": timed_out}, ensure_ascii=False),
            encoding="utf-8",
        )
    except Exception:
        pass
    return {k: str(v.relative_to(REPO_ROOT)) for k, v in paths.items()}


def normalize_handle(handle: str) -> str:
    h = str(handle or "").strip()
    return f"@{h.lstrip('@').strip().lower()}" if h else ""


def select_targets(all_targets: list[dict], year: int, args: argparse.Namespace) -> tuple[list[dict], int, int]:
    if args.target_scope == "failed_only":
        failed_path = OUT_ROOT / str(year) / "audit" / f"year_{year}_failed_targets.csv"
        recoverable_handles = {
            normalize_handle(r.get("handle", "")) for r in read_csv(failed_path) if is_retryable_result(r)
        }
        active = [t for t in all_targets if normalize_handle(t.get("handle", "")) in recoverable_handles]
    else:
        active = [t for t in all_targets if t.get("active_in_year", "true") in ("true", "unknown")]

    skipped_count = len(all_targets) - len(active)
    if args.handles:
        requested = {normalize_handle(h) for h in args.handles.split(",") if h.strip()}
        active = [t for t in active if normalize_handle(t.get("handle", "")) in requested]
    elif args.limit_companies is not None:
        active = active[:max(args.limit_companies, 0)]
    return active, skipped_count, len(all_targets)


def collect_company(target: dict, year: int, args: argparse.Namespace) -> dict[str, Any]:
    handle = normalize_handle(target.get("handle") or "")
    company = target.get("company_name", "")
    rank = target.get("fortune_rank", "")
    group = target.get("sample_group", "")
    acct_yr_val = parse_year_int(target.get("account_created_year"))
    index = int(target.get("_company_index", 0) or 0)
    selected_total = int(target.get("_selected_company_count", 0) or 0)
    full_total = int(target.get("_full_target_company_count", 0) or 0)
    slug = f"y{year}__{slugify(group)}__{slugify(company)}__{slugify(handle.lstrip('@'))}"

    posts_dir = OUT_ROOT / str(year) / "posts" / slug
    posts_dir.mkdir(parents=True, exist_ok=True)
    raw_path = posts_dir / "collected_posts_raw.json"
    filtered_path = posts_dir / f"posts_on_or_before_{year}.json"
    state_path = posts_dir / "scrape_state.json"
    metrics_path = posts_dir / "scrape_metrics.json"

    cutoff = datetime.fromisoformat(f"{year}-12-31T23:59:59+00:00")
    status = "recoverable_failed_browser"
    failure_subtype = ""
    last_error = ""
    attempts = 0
    company_timeout_triggered = False
    start_ts = time.monotonic()
    start_iso = utc_now_iso()

    print(
        f"[yearly-backfill] year={year} smoke={str(args.smoke).lower()} "
        f"company={index}/{selected_total} full_total={full_total} handle={handle} "
        f"status=start input_max_scrolls={args.input_max_scrolls} "
        f"effective_max_scrolls={args.effective_max_scrolls} "
        f"timeout={args.per_company_timeout_seconds} retry_round={args.retry_round} "
        f"started_at={start_iso}",
        flush=True,
    )

    log_paths = _save_logs(posts_dir, "", "", 0, timed_out=False)
    if not SCRAPER.exists():
        last_error = f"scraper not found: {SCRAPER}"
    else:
        env = os.environ.copy()
        env.update({
            "TARGET_USER": handle,
            "BRAND_DIR": str(posts_dir),
            "OUTPUT_FILE": str(raw_path),
            "STATE_FILE": str(state_path),
            "MAX_POSTS": str(args.max_posts_per_account),
            "MAX_SCROLLS": str(args.effective_max_scrolls),
            "HEADLESS": "true",
            "STOP_ON_EXISTING": "0",
            "SCRAPE_METRICS_FILE": str(metrics_path),
            "CUTOFF_DATE": f"{year}-12-31",
            "YEARLY_BACKFILL_FAIL_FAST_RENDER": "1" if args.fail_fast_render else "0",
        })
        attempts = 1
        try:
            timeout = None if args.per_company_timeout_seconds == 0 else args.per_company_timeout_seconds
            proc = subprocess.run(
                [sys.executable, str(SCRAPER)],
                env=env,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            stdout = proc.stdout or ""
            stderr = proc.stderr or ""
            log_paths = _save_logs(posts_dir, stdout, stderr, proc.returncode, timed_out=False)
            combined_log = stdout + "\n" + stderr
            if proc.returncode == 0:
                status = "success"
            else:
                stderr_snippet = stderr[-1200:].replace("\n", " | ")
                last_error = f"exit {proc.returncode} | {stderr_snippet}"
                status = classify_error(f"exit {proc.returncode}", combined_log)
                failure_subtype = classify_failure_subtype(last_error, combined_log)
        except subprocess.TimeoutExpired as exc:
            stdout = _coerce_output(exc.stdout)
            stderr = _coerce_output(exc.stderr)
            elapsed_timeout = exc.timeout if exc.timeout is not None else args.per_company_timeout_seconds
            last_error = f"company timeout after {elapsed_timeout}s"
            status = "recoverable_failed_company_timeout"
            failure_subtype = "render_failure_timeout"
            company_timeout_triggered = True
            log_paths = _save_logs(posts_dir, stdout, stderr, -1, timed_out=True)
        except Exception as exc:
            last_error = str(exc)
            status = classify_error(last_error, "")
            failure_subtype = classify_failure_subtype(last_error, "")
            log_paths = _save_logs(posts_dir, "", last_error, -1, timed_out=False)

    raw_posts = load_json(raw_path)
    ids_seen: set[str] = set()
    filtered: list[dict[str, Any]] = []
    duplicate_posts = 0
    dates: list[datetime] = []

    for post in raw_posts:
        tid = str(post.get("id") or post.get("tweet_id") or post.get("rest_id") or "").strip()
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

    if status == "success":
        if acct_yr_val is not None and acct_yr_val > year:
            status = "terminal_created_after_year"
        elif raw_posts and not filtered:
            earliest_raw = min((dt for p in raw_posts for dt in [parse_date(p.get("created_at"))] if dt), default=None)
            if earliest_raw and earliest_raw.year > year:
                status = "recoverable_failed_did_not_reach_year"
        elif not raw_posts:
            status = "terminal_no_observable_posts_for_year"

    save_json(filtered_path, filtered)
    metrics = json.loads(metrics_path.read_text(encoding="utf-8")) if metrics_path.exists() else {}
    reached_cutoff = any((parse_date(p.get("created_at")) or datetime.max.replace(tzinfo=timezone.utc)) <= cutoff for p in raw_posts)
    elapsed = time.monotonic() - start_ts
    scrolls_completed = metrics.get("scrolls_completed", "")
    stopped_reason = metrics.get("stop_reason", "")
    min_date = min(dates).date().isoformat() if dates else ""
    max_date = max(dates).date().isoformat() if dates else ""

    if status == "recoverable_failed_render" and not failure_subtype:
        failure_subtype = "render_failure_unknown"

    print(
        f"[yearly-backfill] year={year} smoke={str(args.smoke).lower()} "
        f"company={index}/{selected_total} full_total={full_total} handle={handle} "
        f"status={status} subtype={failure_subtype or ''} scrolls={scrolls_completed} "
        f"elapsed={elapsed:.1f}s stopped_reason={stopped_reason} "
        f"raw_collected={len(raw_posts)} posts_on_or_before_target_year={len(filtered)} "
        f"min_date_seen={min_date} max_date_seen={max_date} ended_at={utc_now_iso()}",
        flush=True,
    )

    return {
        "fortune_rank": rank,
        "company_name": company,
        "handle": handle,
        "sample_group": group,
        "account_created_year": acct_yr_val or "",
        "target_year": year,
        "status": status,
        "attempts": attempts,
        "posts_collected_raw": len(raw_posts),
        "raw_collected": len(raw_posts),
        "posts_on_or_before_year": len(filtered),
        "posts_on_or_before_target_year": len(filtered),
        "new_unique_posts": max(len(filtered) - duplicate_posts, 0),
        "duplicate_posts": duplicate_posts,
        "min_date": min_date,
        "max_date": max_date,
        "min_date_seen": min_date,
        "max_date_seen": max_date,
        "reached_cutoff_date": str(reached_cutoff),
        "stopped_reason": stopped_reason,
        "scrolls_completed": scrolls_completed,
        "retry_round": args.retry_round,
        "last_error": last_error,
        "smoke_mode": str(args.smoke),
        "full_target_company_count": full_total,
        "selected_company_count": selected_total,
        "input_max_scrolls": args.input_max_scrolls,
        "effective_max_scrolls": args.effective_max_scrolls,
        "max_scrolls_cap_reason": args.max_scrolls_cap_reason,
        "per_company_timeout_seconds": args.per_company_timeout_seconds,
        "company_timeout_triggered": str(company_timeout_triggered),
        "failure_subtype": failure_subtype,
        "elapsed_seconds": f"{elapsed:.3f}",
        **log_paths,
    }


def failure_result(target: dict, year: int, args: argparse.Namespace, exc: Exception) -> dict[str, Any]:
    return {
        "fortune_rank": target.get("fortune_rank", ""),
        "company_name": target.get("company_name", ""),
        "handle": normalize_handle(target.get("handle") or ""),
        "sample_group": target.get("sample_group", ""),
        "account_created_year": target.get("account_created_year", ""),
        "target_year": year,
        "status": "recoverable_failed_browser",
        "attempts": 1,
        "posts_collected_raw": 0,
        "raw_collected": 0,
        "posts_on_or_before_year": 0,
        "posts_on_or_before_target_year": 0,
        "new_unique_posts": 0,
        "duplicate_posts": 0,
        "min_date": "",
        "max_date": "",
        "min_date_seen": "",
        "max_date_seen": "",
        "reached_cutoff_date": "False",
        "stopped_reason": "future_exception",
        "scrolls_completed": "",
        "retry_round": args.retry_round,
        "last_error": str(exc),
        "smoke_mode": str(args.smoke),
        "full_target_company_count": getattr(args, "full_target_company_count", ""),
        "selected_company_count": getattr(args, "selected_company_count", ""),
        "input_max_scrolls": args.input_max_scrolls,
        "effective_max_scrolls": args.effective_max_scrolls,
        "max_scrolls_cap_reason": args.max_scrolls_cap_reason,
        "per_company_timeout_seconds": args.per_company_timeout_seconds,
        "company_timeout_triggered": "False",
        "failure_subtype": classify_failure_subtype(str(exc), "") or "render_failure_unknown",
        "elapsed_seconds": "0.000",
        "stdout_tail_path": "",
        "stderr_tail_path": "",
        "combined_tail_path": "",
        "exit_status_path": "",
    }


def collect_year(year: int, all_targets: list[dict], args: argparse.Namespace) -> dict[str, Any]:
    year_start = time.monotonic()
    year_audit = OUT_ROOT / str(year) / "audit"
    active, skipped_count, full_total = select_targets(all_targets, year, args)
    selected_count = len(active)
    if args.smoke and args.handles and selected_count == 0:
        requested = ",".join(sorted({normalize_handle(h) for h in args.handles.split(",") if h.strip()}))
        available_sample = ",".join(sorted({normalize_handle(t.get("handle", "")) for t in all_targets if t.get("handle")} )[:10])
        raise RuntimeError(
            "smoke targeted handles matched zero companies: "
            f"requested={requested or args.handles!r}; "
            f"full_target_company_count={full_total}; "
            f"available_handle_sample={available_sample}"
        )
    args.full_target_company_count = full_total
    args.selected_company_count = selected_count

    for idx, target in enumerate(active, start=1):
        target["_company_index"] = idx
        target["_selected_company_count"] = selected_count
        target["_full_target_company_count"] = full_total

    print(
        f"  year={year}: selected={selected_count} full_targets={full_total} "
        f"skipped={skipped_count} max_parallel={args.max_parallel_companies} "
        f"smoke={args.smoke}",
        flush=True,
    )
    if args.smoke:
        print(
            f"[yearly-backfill] smoke mode active: selected_company_count={selected_count} "
            f"input_max_scrolls={args.input_max_scrolls} "
            f"effective_max_scrolls={args.effective_max_scrolls} "
            f"per_company_timeout_seconds={args.per_company_timeout_seconds}",
            flush=True,
        )

    results: list[dict[str, Any]] = []
    if not args.prepare_only and active:
        max_workers = min(args.max_parallel_companies, len(active))
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            futures = {pool.submit(collect_company, t, year, args): t for t in active}
            for future in as_completed(futures):
                try:
                    result = future.result()
                except Exception as exc:
                    result = failure_result(futures[future], year, args, exc)
                results.append(result)
                print(f"    {result['company_name']} ({result['handle']}): {result['status']}", flush=True)

    success = [r for r in results if r["status"] == "success"]
    recoverable = [r for r in results if is_retryable_result(r)]
    terminal = [r for r in results if r["status"] in TERMINAL_STATUSES]

    year_audit.mkdir(parents=True, exist_ok=True)
    write_csv(year_audit / f"year_{year}_target_companies.csv", results, RESULT_FIELDS)
    write_csv(year_audit / f"year_{year}_failed_targets.csv", recoverable, RESULT_FIELDS)
    write_csv(year_audit / f"year_{year}_terminal_targets.csv", terminal, RESULT_FIELDS)

    all_dates = [r["min_date"] for r in results if r.get("min_date")] + [r["max_date"] for r in results if r.get("max_date")]
    total_posts = sum(int(r.get("posts_on_or_before_year", 0) or 0) for r in results)
    total_dupes = sum(int(r.get("duplicate_posts", 0) or 0) for r in results)
    elapsed_values = [float(r.get("elapsed_seconds", 0) or 0) for r in results]
    scroll_values = []
    for r in results:
        try:
            if str(r.get("scrolls_completed", "")).strip() != "":
                scroll_values.append(float(r.get("scrolls_completed", 0) or 0))
        except (TypeError, ValueError):
            pass

    def subtype_count(name: str) -> int:
        return sum(1 for r in results if r.get("failure_subtype") == name)

    render_fail_count = sum(1 for r in results if r.get("failure_subtype") in RENDER_FAILURE_SUBTYPES or r["status"] == "recoverable_failed_render")
    did_not_reach_count = sum(1 for r in results if r["status"] == "recoverable_failed_did_not_reach_year")
    term_after_year_count = sum(1 for r in results if r["status"] == "terminal_created_after_year")
    term_after_year_acct_evidence_count = sum(
        1 for r in results if r["status"] == "terminal_created_after_year" and str(r.get("account_created_year", "")).strip()
    )
    scrolls_zero_count = sum(1 for r in results if str(r.get("scrolls_completed", "")).strip() in ("0", ""))
    raw_but_no_filtered_count = sum(
        1 for r in results if int(r.get("posts_collected_raw", 0) or 0) > 0 and int(r.get("posts_on_or_before_year", 0) or 0) == 0
    )
    total_elapsed = time.monotonic() - year_start

    summary: dict[str, Any] = {
        "target_year": year,
        "target_company_count": full_total,
        "attempted_company_count": len(results),
        "success_count": len(success),
        "recoverable_failure_count": len(recoverable),
        "terminal_status_count": len(terminal),
        "skipped_not_active_count": skipped_count,
        "posts_collected": total_posts,
        "new_unique_posts": max(total_posts - total_dupes, 0),
        "duplicate_posts": total_dupes,
        "min_date": min(all_dates) if all_dates else "",
        "max_date": max(all_dates) if all_dates else "",
        "retry_round": args.retry_round,
        "completed_at": utc_now_iso(),
        "smoke_mode": str(args.smoke),
        "full_target_company_count": full_total,
        "selected_company_count": selected_count,
        "input_max_scrolls": args.input_max_scrolls,
        "effective_max_scrolls": args.effective_max_scrolls,
        "max_scrolls_cap_reason": args.max_scrolls_cap_reason,
        "per_company_timeout_seconds": args.per_company_timeout_seconds,
        "total_elapsed_seconds": f"{total_elapsed:.3f}",
        "median_company_elapsed_seconds": median(elapsed_values),
        "max_company_elapsed_seconds": max_number(elapsed_values),
        "timeout_count": sum(1 for r in results if r["status"] in {"recoverable_failed_timeout", "recoverable_failed_company_timeout"}),
        "company_timeout_count": sum(1 for r in results if parse_bool_text(r.get("company_timeout_triggered"))),
        "render_failure_count": render_fail_count,
        "render_failure_login_or_auth_count": subtype_count("render_failure_login_or_auth"),
        "render_failure_rate_limit_or_block_count": subtype_count("render_failure_rate_limit_or_block"),
        "render_failure_selector_missing_count": subtype_count("render_failure_selector_missing"),
        "render_failure_timeout_count": subtype_count("render_failure_timeout"),
        "render_failure_unknown_count": subtype_count("render_failure_unknown"),
        "did_not_reach_year_count": did_not_reach_count,
        "companies_with_raw_posts_count": sum(1 for r in results if int(r.get("posts_collected_raw", 0) or 0) > 0),
        "companies_with_zero_scroll_count": scrolls_zero_count,
        "min_seen_date_overall": min(all_dates) if all_dates else "",
        "max_seen_date_overall": max(all_dates) if all_dates else "",
        "median_scrolls_completed": median(scroll_values),
        "max_scrolls_completed": max_number(scroll_values),
        "recoverable_render_failure_count": render_fail_count,
        "recoverable_did_not_reach_year_count": did_not_reach_count,
        "terminal_created_after_year_count": term_after_year_count,
        "terminal_created_after_year_with_account_created_evidence_count": term_after_year_acct_evidence_count,
        "companies_with_scrolls_zero": scrolls_zero_count,
        "companies_with_raw_posts_but_no_target_year_posts": raw_but_no_filtered_count,
        "max_parallel_companies": args.max_parallel_companies,
        "run_mode": args.target_scope,
        "validation_status": "pending",
        "validation_warning_count": 0,
    }
    write_csv(year_audit / f"year_{year}_summary.csv", [summary], SUMMARY_FIELDS)
    return summary


def parse_args() -> argparse.Namespace:
    raw_argv = sys.argv[1:]
    parser = argparse.ArgumentParser(
        description=(
            "Year-serial, company-parallel humor backfill runner. Use --smoke for "
            "a 3-company, max_scrolls<=300, per-company-timeout=180s diagnostic. "
            "A 99-company max_scrolls=3500 run is a full historical run, not smoke."
        )
    )
    parser.add_argument("--start-year", type=int, default=MIN_YEAR)
    parser.add_argument("--end-year", type=int, default=MAX_YEAR)
    parser.add_argument("--target-year", type=int, default=None, help="Process this single year only.")
    parser.add_argument("--max-posts-per-account", type=int, default=0)
    parser.add_argument("--max-scrolls", type=int, default=3500)
    parser.add_argument(
        "--max-parallel-companies", type=int, default=1,
        help="Max companies in parallel per year. Default: 1. Smoke mode forces 1.",
    )
    parser.add_argument("--target-scope", choices=["all", "failed_only"], default="all")
    parser.add_argument("--retry-round", type=int, default=0)
    parser.add_argument("--prepare-only", action="store_true", help="Write audit summaries without running the scraper.")
    parser.add_argument("--smoke", action="store_true", help="Run a short diagnostic: default 3 companies, max_scrolls capped at 300, timeout 180s.")
    parser.add_argument("--limit-companies", type=int, default=None, help="Run only the first N selected companies. Smoke default: 3.")
    parser.add_argument("--handles", default="", help="Comma-separated handles to run, e.g. @Delta,@Walmart. Overrides --limit-companies.")
    parser.add_argument("--per-company-timeout-seconds", type=int, default=None, help="Hard timeout per company. Default: 300; smoke default: 180; 0 disables.")
    parser.add_argument("--fail-fast-render", action="store_true", help="Mark render/auth/block-like failures as recoverable quickly when surfaced by scraper logs.")
    args = parser.parse_args()

    args.input_max_scrolls = args.max_scrolls
    args.effective_max_scrolls = args.max_scrolls
    args.max_scrolls_cap_reason = "none"

    explicit_limit = "--limit-companies" in raw_argv
    explicit_timeout = "--per-company-timeout-seconds" in raw_argv
    if args.per_company_timeout_seconds is None:
        args.per_company_timeout_seconds = DEFAULT_COMPANY_TIMEOUT_SECONDS

    if args.smoke:
        args.max_parallel_companies = 1
        if not args.handles and not explicit_limit:
            args.limit_companies = SMOKE_DEFAULT_LIMIT_COMPANIES
        if args.max_scrolls > SMOKE_MAX_SCROLLS_CAP:
            args.effective_max_scrolls = SMOKE_MAX_SCROLLS_CAP
            args.max_scrolls_cap_reason = "smoke_cap_300"
        else:
            args.max_scrolls_cap_reason = "smoke_user_max_scrolls_within_cap"
        if not explicit_timeout:
            args.per_company_timeout_seconds = SMOKE_DEFAULT_COMPANY_TIMEOUT_SECONDS
    return args


def main() -> int:
    args = parse_args()

    if args.max_parallel_companies > 1:
        print(
            f"WARNING: max_parallel_companies={args.max_parallel_companies} > 1. "
            "Parallel Playwright instances on the same runner risk render_failure. "
            "Use 1 unless render stability has been verified.",
            file=sys.stderr,
            flush=True,
        )

    years = [args.target_year] if args.target_year else list(range(args.start_year, args.end_year + 1))
    all_summaries: list[dict[str, Any]] = []

    for year in years:
        print(f"\n=== year={year} ===", flush=True)
        target_csv = OUT_ROOT / str(year) / "audit" / f"year_{year}_target_companies.csv"
        if not target_csv.exists():
            print(f"  target file missing for year={year}; run build_yearly_humor_backfill_targets.py first — skipping", flush=True)
            continue

        targets = read_csv(target_csv)
        summary = collect_year(year, targets, args)
        all_summaries.append(summary)

        rec = summary["recoverable_failure_count"]
        render = summary.get("recoverable_render_failure_count", 0)
        dnr = summary.get("recoverable_did_not_reach_year_count", 0)
        print(
            f"  year={year} done: success={summary['success_count']} "
            f"recoverable={rec} (render={render} did_not_reach={dnr}) "
            f"terminal={summary['terminal_status_count']} posts={summary['posts_collected']}",
            flush=True,
        )

        if args.target_scope == "failed_only" and rec == 0:
            print(f"  recoverable_failure_count=0 for year={year}; stopping.", flush=True)
            break

    if all_summaries:
        GLOBAL_AUDIT.mkdir(parents=True, exist_ok=True)
        global_path = GLOBAL_AUDIT / "year_target_summary.csv"
        existing = read_csv(global_path)
        run_years = {str(s["target_year"]) for s in all_summaries}
        merged = [r for r in existing if str(r.get("target_year")) not in run_years]
        merged += all_summaries
        merged.sort(key=lambda r: int(r.get("target_year", 0) or 0))
        write_csv(global_path, merged, SUMMARY_FIELDS)

    total_rec = sum(int(s["recoverable_failure_count"]) for s in all_summaries)
    print(f"\n=== done. years_processed={len(all_summaries)} total_recoverable_failures={total_rec} ===", flush=True)
    if args.target_scope == "failed_only" and total_rec == 0:
        print("All recoverable failures resolved. COMPLETE.", flush=True)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
