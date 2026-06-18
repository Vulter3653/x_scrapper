#!/usr/bin/env python3
"""Year-serial, company-parallel humor backfill runner.

Years are processed in serial order (start_year → end_year, or target_year only).
Within each year, eligible companies run in parallel up to max_parallel_companies.
Outputs staged to data/backfill/yearly_humor/{year}/ — does NOT touch data/raw,
dashboard/data, or the integrated corpus.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import subprocess
import sys
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

RECOVERABLE_STATUSES = frozenset({
    "recoverable_failed_timeout",
    "recoverable_failed_network",
    "recoverable_failed_browser",
    "recoverable_failed_temporary_x_error",
})
TERMINAL_STATUSES = frozenset({
    "terminal_account_unavailable",
    "terminal_account_protected",
    "terminal_account_suspended",
    "terminal_created_after_year",
    "terminal_no_observable_posts_for_year",
})

SUMMARY_FIELDS = [
    "target_year", "target_company_count", "attempted_company_count",
    "success_count", "recoverable_failure_count", "terminal_status_count",
    "skipped_not_active_count", "posts_collected", "new_unique_posts",
    "duplicate_posts", "min_date", "max_date", "retry_round", "completed_at",
]

RESULT_FIELDS = [
    "fortune_rank", "company_name", "handle", "sample_group",
    "target_year", "status", "attempts",
    "posts_collected_raw", "posts_on_or_before_year", "new_unique_posts",
    "duplicate_posts", "min_date", "max_date",
    "reached_cutoff_date", "stopped_reason", "scrolls_completed",
    "retry_round", "last_error",
]


def slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_") or "target"


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


def classify_error(exc_text: str) -> str:
    t = exc_text.lower()
    if "timeout" in t or "timed out" in t:
        return "recoverable_failed_timeout"
    if "network" in t or "connection" in t or "dns" in t:
        return "recoverable_failed_network"
    if "protected" in t or "private" in t:
        return "terminal_account_protected"
    if "suspended" in t or "not found" in t or "does not exist" in t:
        return "terminal_account_unavailable"
    if "rate limit" in t or "temporarily" in t or "too many" in t:
        return "recoverable_failed_temporary_x_error"
    return "recoverable_failed_browser"


def collect_company(target: dict, year: int, args: argparse.Namespace) -> dict[str, Any]:
    handle = (target.get("handle") or "").strip()
    company = target.get("company_name", "")
    rank = target.get("fortune_rank", "")
    group = target.get("sample_group", "")
    slug = f"y{year}__{slugify(group)}__{slugify(company)}__{slugify(handle.lstrip('@'))}"

    posts_dir = OUT_ROOT / str(year) / "posts" / slug
    posts_dir.mkdir(parents=True, exist_ok=True)
    raw_path = posts_dir / "collected_posts_raw.json"
    filtered_path = posts_dir / f"posts_on_or_before_{year}.json"
    state_path = posts_dir / "scrape_state.json"
    metrics_path = posts_dir / "scrape_metrics.json"

    cutoff = datetime.fromisoformat(f"{year}-12-31T23:59:59+00:00")
    status = "recoverable_failed_browser"
    last_error = ""
    attempts = 0

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
            "MAX_SCROLLS": str(args.max_scrolls),
            "HEADLESS": "true",
            "STOP_ON_EXISTING": "0",
            "SCRAPE_METRICS_FILE": str(metrics_path),
            "CUTOFF_DATE": f"{year}-12-31",
        })
        attempts = 1
        try:
            subprocess.run(
                [sys.executable, str(SCRAPER)],
                env=env, check=True, timeout=3000,
            )
            status = "success"
        except subprocess.TimeoutExpired as exc:
            last_error = f"timeout after {exc.timeout}s"
            status = "recoverable_failed_timeout"
        except subprocess.CalledProcessError as exc:
            last_error = f"exit {exc.returncode}"
            status = classify_error(str(exc))
        except Exception as exc:
            last_error = str(exc)
            status = classify_error(last_error)

    raw_posts = load_json(raw_path)
    ids_seen: set[str] = set()
    filtered: list[dict[str, Any]] = []
    duplicate_posts = 0
    dates: list[datetime] = []

    for post in raw_posts:
        tid = str(
            post.get("id") or post.get("tweet_id") or post.get("rest_id") or ""
        ).strip()
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

    if status == "success" and raw_posts and not filtered:
        earliest_raw = min(
            (dt for p in raw_posts for dt in [parse_date(p.get("created_at"))] if dt),
            default=None,
        )
        if earliest_raw and earliest_raw.year > year:
            status = "terminal_created_after_year"

    save_json(filtered_path, filtered)
    metrics = json.loads(metrics_path.read_text(encoding="utf-8")) if metrics_path.exists() else {}
    reached_cutoff = any(
        (parse_date(p.get("created_at")) or datetime.max.replace(tzinfo=timezone.utc)) <= cutoff
        for p in raw_posts
    )

    return {
        "fortune_rank": rank,
        "company_name": company,
        "handle": handle,
        "sample_group": group,
        "target_year": year,
        "status": status,
        "attempts": attempts,
        "posts_collected_raw": len(raw_posts),
        "posts_on_or_before_year": len(filtered),
        "new_unique_posts": len(filtered) - duplicate_posts,
        "duplicate_posts": duplicate_posts,
        "min_date": min(dates).date().isoformat() if dates else "",
        "max_date": max(dates).date().isoformat() if dates else "",
        "reached_cutoff_date": str(reached_cutoff),
        "stopped_reason": metrics.get("stop_reason", ""),
        "scrolls_completed": metrics.get("scrolls_completed", ""),
        "retry_round": args.retry_round,
        "last_error": last_error,
    }


def collect_year(year: int, all_targets: list[dict], args: argparse.Namespace) -> dict[str, Any]:
    year_audit = OUT_ROOT / str(year) / "audit"

    if args.target_scope == "failed_only":
        failed_path = year_audit / f"year_{year}_failed_targets.csv"
        recoverable_handles = {
            r["handle"] for r in read_csv(failed_path)
            if r.get("status", "") in RECOVERABLE_STATUSES
        }
        active = [t for t in all_targets if (t.get("handle") or "").strip() in recoverable_handles]
    else:
        active = [t for t in all_targets if t.get("active_in_year", "true") in ("true", "unknown")]

    skipped_count = len(all_targets) - len(active)
    print(f"  year={year}: active={len(active)} skipped={skipped_count}")

    results: list[dict[str, Any]] = []

    if not args.prepare_only and active:
        max_workers = min(args.max_parallel_companies, len(active))
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            futures = {pool.submit(collect_company, t, year, args): t for t in active}
            for future in as_completed(futures):
                try:
                    result = future.result()
                except Exception as exc:
                    t = futures[future]
                    result = {
                        "fortune_rank": t.get("fortune_rank", ""),
                        "company_name": t.get("company_name", ""),
                        "handle": (t.get("handle") or "").strip(),
                        "sample_group": t.get("sample_group", ""),
                        "target_year": year,
                        "status": "recoverable_failed_browser",
                        "attempts": 1,
                        "posts_collected_raw": 0,
                        "posts_on_or_before_year": 0,
                        "new_unique_posts": 0,
                        "duplicate_posts": 0,
                        "min_date": "",
                        "max_date": "",
                        "reached_cutoff_date": "False",
                        "stopped_reason": "",
                        "scrolls_completed": "",
                        "retry_round": args.retry_round,
                        "last_error": str(exc),
                    }
                results.append(result)
                print(f"    {result['company_name']} ({result['handle']}): {result['status']}")

    success = [r for r in results if r["status"] == "success"]
    recoverable = [r for r in results if r["status"] in RECOVERABLE_STATUSES]
    terminal = [r for r in results if r["status"] in TERMINAL_STATUSES]

    year_audit.mkdir(parents=True, exist_ok=True)
    write_csv(year_audit / f"year_{year}_target_companies.csv", results, RESULT_FIELDS)
    write_csv(year_audit / f"year_{year}_failed_targets.csv", recoverable, RESULT_FIELDS)
    write_csv(year_audit / f"year_{year}_terminal_targets.csv", terminal, RESULT_FIELDS)

    all_dates = [r["min_date"] for r in results if r.get("min_date")] + \
                [r["max_date"] for r in results if r.get("max_date")]
    total_posts = sum(int(r.get("posts_on_or_before_year", 0) or 0) for r in results)
    total_dupes = sum(int(r.get("duplicate_posts", 0) or 0) for r in results)

    summary: dict[str, Any] = {
        "target_year": year,
        "target_company_count": len(active) + skipped_count,
        "attempted_company_count": len(results),
        "success_count": len(success),
        "recoverable_failure_count": len(recoverable),
        "terminal_status_count": len(terminal),
        "skipped_not_active_count": skipped_count,
        "posts_collected": total_posts,
        "new_unique_posts": total_posts - total_dupes,
        "duplicate_posts": total_dupes,
        "min_date": min(all_dates) if all_dates else "",
        "max_date": max(all_dates) if all_dates else "",
        "retry_round": args.retry_round,
        "completed_at": datetime.now(timezone.utc).isoformat(),
    }
    write_csv(year_audit / f"year_{year}_summary.csv", [summary], SUMMARY_FIELDS)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Year-serial, company-parallel humor backfill runner."
    )
    parser.add_argument("--start-year", type=int, default=MIN_YEAR)
    parser.add_argument("--end-year", type=int, default=MAX_YEAR)
    parser.add_argument("--target-year", type=int, default=None,
                        help="Process this single year only.")
    parser.add_argument("--max-posts-per-account", type=int, default=0)
    parser.add_argument("--max-scrolls", type=int, default=3500)
    parser.add_argument("--max-parallel-companies", type=int, default=2)
    parser.add_argument("--target-scope", choices=["all", "failed_only"], default="all")
    parser.add_argument("--retry-round", type=int, default=0)
    parser.add_argument("--prepare-only", action="store_true",
                        help="Write audit summaries without running the scraper.")
    args = parser.parse_args()

    years = ([args.target_year]
             if args.target_year
             else list(range(args.start_year, args.end_year + 1)))

    all_summaries: list[dict[str, Any]] = []

    for year in years:
        print(f"\n=== year={year} ===")
        target_csv = OUT_ROOT / str(year) / "audit" / f"year_{year}_target_companies.csv"
        if not target_csv.exists():
            print(f"  target file missing for year={year}; "
                  f"run build_yearly_humor_backfill_targets.py first — skipping")
            continue

        targets = read_csv(target_csv)
        summary = collect_year(year, targets, args)
        all_summaries.append(summary)

        rec = summary["recoverable_failure_count"]
        print(f"  year={year} done: success={summary['success_count']} "
              f"recoverable={rec} terminal={summary['terminal_status_count']} "
              f"posts={summary['posts_collected']}")

        if args.target_scope == "failed_only" and rec == 0:
            print(f"  recoverable_failure_count=0 for year={year}; stopping.")
            break

    if all_summaries:
        GLOBAL_AUDIT.mkdir(parents=True, exist_ok=True)
        global_path = GLOBAL_AUDIT / "year_target_summary.csv"
        existing = read_csv(global_path)
        run_years = {s["target_year"] for s in all_summaries}
        merged = [r for r in existing if r.get("target_year") not in run_years]
        merged += all_summaries
        merged.sort(key=lambda r: int(r.get("target_year", 0) or 0))
        write_csv(global_path, merged, SUMMARY_FIELDS)

    total_rec = sum(s["recoverable_failure_count"] for s in all_summaries)
    print(f"\n=== done. years_processed={len(all_summaries)} "
          f"total_recoverable_failures={total_rec} ===")
    if args.target_scope == "failed_only" and total_rec == 0:
        print("All recoverable failures resolved. COMPLETE.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
