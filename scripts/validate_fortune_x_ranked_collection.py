#!/usr/bin/env python3
"""Validate ranked Fortune X collection outputs and workflow scaffold."""

from __future__ import annotations

import argparse
import csv
import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = REPO_ROOT / "data" / "raw" / "fortune_x_2025_ranked"
SUMMARY_FILE = REPO_ROOT / "data" / "audit" / "fortune_x_2025_ranked_collection_summary.csv"
WORKFLOW_FILE = REPO_ROOT / ".github" / "workflows" / "collect-fortune-x-ranked.yml"
RUNNER_FILE = REPO_ROOT / "scripts" / "run_fortune_x_ranked_collection.py"
MERGE_FILE = REPO_ROOT / "scripts" / "merge_fortune_x_ranked_collection_shards.py"

REQUIRED_POST_COLUMNS = {
    "fortune_rank", "company_name", "official_x_handle", "tweet_id", "created_at", "text",
    "tweet_url", "reply_count", "repost_count", "like_count", "quote_count",
    "view_count_available", "media_present", "media_type", "collected_at", "collection_method",
    "max_posts_cap", "source_folder", "source_x_handle", "source_x_url", "account_role",
    "account_index",
}
REQUIRED_ACCOUNT_AUDIT_COLUMNS = {
    "fortune_rank", "company_name", "account_index", "account_role", "source_x_handle",
    "source_x_url", "folder", "attempted", "status", "posts_collected", "retryable",
    "error_type", "error_message", "started_at", "completed_at",
}
REQUIRED_SUMMARY_COLUMNS = [
    "fortune_rank", "company_name", "official_x_handle", "folder", "attempted", "status",
    "posts_collected", "error_type", "error_message", "started_at", "completed_at",
]
FORBIDDEN_TRACKED_PATTERNS = ("session", "cache", "screenshot", "trace", "auth_token", "ct0")
FORBIDDEN_API_MARKERS = ("api.x.com", "api.twitter.com", "bearer_token", "Authorization: Bearer")
QUICK_SMOKE_RANKS = {1, 5, 14, 25, 29, 43, 67, 78, 80, 100}

FAILURES = 0
WARNINGS = 0


def report(status: str, check: str, detail: str) -> None:
    global FAILURES, WARNINGS
    print(f"{status}: {check} - {detail}")
    if status == "FAIL":
        FAILURES += 1
    elif status == "WARN":
        WARNINGS += 1


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return reader.fieldnames or [], list(reader)


def git_status(paths: list[str]) -> str:
    result = subprocess.run(["git", "status", "--short", *paths], cwd=REPO_ROOT, text=True, capture_output=True, check=False)
    return result.stdout.strip()


def check_dashboard_clean() -> None:
    output = git_status(["dashboard/data"])
    if output:
        report("FAIL", "dashboard/data mutation", output)
    else:
        report("PASS", "dashboard/data mutation", "no changes under dashboard/data/")


def check_scaffold() -> None:
    for path in [WORKFLOW_FILE, RUNNER_FILE, MERGE_FILE]:
        if path.exists():
            report("PASS", "required scaffold", f"found {rel(path)}")
        else:
            report("FAIL", "required scaffold", f"missing {rel(path)}")
    if WORKFLOW_FILE.exists():
        text = WORKFLOW_FILE.read_text(encoding="utf-8")
        required = [
            "workflow_dispatch:",
            "contents: write",
            "fortune-x-ranked-collection",
            "collection_mode",
            "quick_smoke",
            "coverage_smoke",
            "full_collection",
            "custom",
            "quick_smoke_rank_${rank}_skipped",
            "Resolve collection mode settings",
            "steps.mode.outputs.max_posts",
            "collect-phase-1:",
            "collect-phase-2:",
            "collect-phase-3:",
            "collect-phase-4:",
            "aggregate-ranked-shards:",
            "needs: collect-phase-1",
            "needs: collect-phase-2",
            "needs: collect-phase-3",
            "strategy:",
            "matrix:",
            "rank: [1, 2, 3",
            "rank: [26, 27, 28",
            "rank: [51, 52, 53",
            "rank: [76, 77, 78",
            "actions/upload-artifact",
            "actions/download-artifact",
            "fortune-x-ranked-phase-*-rank-*",
            "retry_delay_seconds",
            "--retry-delay-seconds",
            "collector_timeout_seconds",
            "--collector-timeout-seconds",
            "--previous-output-root",
            "python scripts/run_fortune_x_ranked_collection.py",
            "python scripts/merge_fortune_x_ranked_collection_shards.py",
            "git push",
        ]
        missing = [item for item in required if item not in text]
        if missing:
            report("FAIL", "workflow controls", "missing: " + ", ".join(missing))
        else:
            report("PASS", "workflow controls", "phased rank-matrix collection workflow controls present")
        phase_needs = [
            ("collect-phase-2:", "needs: collect-phase-1"),
            ("collect-phase-3:", "needs: collect-phase-2"),
            ("collect-phase-4:", "needs: collect-phase-3"),
        ]
        missing_needs = [need for _, need in phase_needs if need not in text]
        aggregate_needs = ["- collect-phase-1", "- collect-phase-2", "- collect-phase-3", "- collect-phase-4"]
        missing_needs.extend(need for need in aggregate_needs if need not in text)
        if missing_needs:
            report("FAIL", "workflow phase ordering", "missing: " + ", ".join(missing_needs))
        else:
            report("PASS", "workflow phase ordering", "collect phases are sequential and aggregate needs all phases")
        forbidden = ["schedule:", "sync_dashboard_data.py", *FORBIDDEN_API_MARKERS]
        found = [item for item in forbidden if item in text]
        if found:
            report("FAIL", "workflow forbidden behavior", "found: " + ", ".join(found))
        else:
            report("PASS", "workflow forbidden behavior", "no schedule, dashboard sync, or X API markers")


def check_x_api_absent() -> None:
    files = [RUNNER_FILE, WORKFLOW_FILE]
    found: list[str] = []
    for path in files:
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        for marker in FORBIDDEN_API_MARKERS:
            if marker in text:
                found.append(f"{rel(path)}:{marker}")
    if found:
        report("FAIL", "X API usage markers", "; ".join(found))
    else:
        report("PASS", "X API usage markers", "no X API endpoint or bearer-token marker in ranked collector files")


def check_tracked_sensitive_files() -> None:
    result = subprocess.run(["git", "status", "--short"], cwd=REPO_ROOT, text=True, capture_output=True, check=False)
    bad = []
    for line in result.stdout.splitlines():
        path = line[3:].strip() if len(line) > 3 else line.strip()
        lower = path.lower()
        if any(pattern in lower for pattern in FORBIDDEN_TRACKED_PATTERNS):
            bad.append(path)
    if bad:
        report("FAIL", "secret/session/cache/screenshot/trace files", ", ".join(bad))
    else:
        report("PASS", "secret/session/cache/screenshot/trace files", "no suspicious tracked or pending file paths")


def check_outputs(allow_empty_before_run: bool) -> None:
    if allow_empty_before_run:
        report("PASS", "output validation", "skipped detailed raw output checks before collection run")
        return
    if not OUTPUT_ROOT.exists():
        report("FAIL", "output root", f"missing {rel(OUTPUT_ROOT)}")
        return
    report("PASS", "output root", f"found {rel(OUTPUT_ROOT)}")

    folders = sorted([path for path in OUTPUT_ROOT.iterdir() if path.is_dir()])
    bad_folders = [path.name for path in folders if not re.match(r"^\d{3}_[a-z0-9_]+$", path.name)]
    if bad_folders:
        report("FAIL", "folder naming", "invalid folders: " + ", ".join(bad_folders[:20]))
    else:
        report("PASS", "folder naming", f"{len(folders)} folders follow rank zero-padding rule")

    all_tweet_ids: list[str] = []
    missing_text = 0
    missing_created_at = 0
    post_file_count = 0
    malformed_rows = 0
    for folder in folders:
        posts_path = folder / "posts.csv"
        audit_path = folder / "audit.json"
        account_audit_path = folder / "account_audit.csv"
        accounts_path = folder / "accounts"
        if not posts_path.exists():
            report("FAIL", "company posts.csv", f"missing {rel(posts_path)}")
            continue
        if not audit_path.exists():
            report("FAIL", "company audit.json", f"missing {rel(audit_path)}")
        else:
            try:
                audit = json.loads(audit_path.read_text(encoding="utf-8"))
                if audit.get("x_api_used") is not False:
                    report("FAIL", "audit x_api_used", f"{rel(audit_path)} x_api_used is not false")
            except Exception as exc:
                report("FAIL", "audit.json parse", f"{rel(audit_path)}: {exc}")
        if not account_audit_path.exists():
            report("FAIL", "account_audit.csv", f"missing {rel(account_audit_path)}")
        else:
            account_fields, _ = read_csv(account_audit_path)
            missing_account_cols = sorted(REQUIRED_ACCOUNT_AUDIT_COLUMNS - set(account_fields))
            if missing_account_cols:
                report("FAIL", "account_audit.csv columns", f"{rel(account_audit_path)} missing: " + ", ".join(missing_account_cols))
        if not accounts_path.exists():
            report("FAIL", "account raw folder", f"missing {rel(accounts_path)}")
        else:
            account_dirs = sorted(path for path in accounts_path.iterdir() if path.is_dir())
            if not account_dirs:
                report("FAIL", "account raw folder", f"no account folders under {rel(accounts_path)}")
            for account_dir in account_dirs:
                account_posts = account_dir / "posts.csv"
                account_audit = account_dir / "audit.json"
                if not account_posts.exists():
                    report("FAIL", "account posts.csv", f"missing {rel(account_posts)}")
                else:
                    account_post_fields, _ = read_csv(account_posts)
                    account_missing_cols = sorted(REQUIRED_POST_COLUMNS - set(account_post_fields))
                    if account_missing_cols:
                        report("FAIL", "account posts.csv columns", f"{rel(account_posts)} missing: " + ", ".join(account_missing_cols))
                if not account_audit.exists():
                    report("FAIL", "account audit.json", f"missing {rel(account_audit)}")
        fields, rows = read_csv(posts_path)
        missing_cols = sorted(REQUIRED_POST_COLUMNS - set(fields))
        if missing_cols:
            report("FAIL", "company posts.csv columns", f"{rel(posts_path)} missing: " + ", ".join(missing_cols))
        post_file_count += 1
        for row in rows:
            if None in row or any(v is None for v in row.values()):
                malformed_rows += 1
            tweet_id = (row.get("tweet_id") or "").strip()
            text = (row.get("text") or "").strip()
            created_at = (row.get("created_at") or "").strip()
            if tweet_id:
                all_tweet_ids.append(tweet_id)
            if not text:
                missing_text += 1
            if not created_at:
                missing_created_at += 1
    duplicates = sum(count - 1 for count in Counter(all_tweet_ids).values() if count > 1)
    report("PASS", "posts.csv files", f"checked {post_file_count} posts.csv files")
    report("PASS", "duplicate tweet_id count", str(duplicates))
    report("PASS", "missing text count", str(missing_text))
    report("PASS", "missing created_at count", str(missing_created_at))
    if malformed_rows:
        report("FAIL", "malformed posts.csv rows", str(malformed_rows))
    else:
        report("PASS", "malformed posts.csv rows", "0")


def expected_ranks_for_mode(collection_mode: str, start_rank: int, end_rank: int) -> set[int]:
    if collection_mode == "quick_smoke":
        return {rank for rank in QUICK_SMOKE_RANKS if start_rank <= rank <= end_rank}
    return set(range(start_rank, end_rank + 1))


def check_summary(allow_empty_before_run: bool, summary_file: Path, expected_start_rank: int | None, expected_end_rank: int | None, collection_mode: str) -> None:
    if not summary_file.exists():
        if allow_empty_before_run:
            report("PASS", "summary csv", f"{rel(summary_file)} absent before first run is allowed")
        else:
            report("FAIL", "summary csv", f"missing {rel(summary_file)}")
        return
    fields, rows = read_csv(summary_file)
    missing = [column for column in REQUIRED_SUMMARY_COLUMNS if column not in fields]
    if missing:
        report("FAIL", "summary columns", "missing: " + ", ".join(missing))
    else:
        report("PASS", "summary columns", "required summary columns present")
    ranks = [int(row["fortune_rank"]) for row in rows if row.get("fortune_rank", "").isdigit()]
    if ranks == sorted(ranks):
        report("PASS", "summary rank ordering", "ranks are ascending")
    else:
        report("FAIL", "summary rank ordering", "summary ranks are not ascending")
    if expected_start_rank is not None or expected_end_rank is not None:
        if expected_start_rank is None or expected_end_rank is None:
            report("FAIL", "summary rank coverage", "both expected start and end ranks are required")
        else:
            expected = expected_ranks_for_mode(collection_mode, expected_start_rank, expected_end_rank)
            present = {int(row["fortune_rank"]) for row in rows if row.get("fortune_rank", "").isdigit()}
            missing_ranks = sorted(expected - present)
            unexpected_ranks = sorted(present - expected)
            if missing_ranks:
                report("FAIL", "summary rank coverage", "missing ranks: " + ", ".join(str(rank) for rank in missing_ranks))
            elif unexpected_ranks and collection_mode == "quick_smoke":
                report("FAIL", "summary rank coverage", "unexpected quick_smoke ranks: " + ", ".join(str(rank) for rank in unexpected_ranks))
            else:
                expected_detail = ",".join(str(rank) for rank in sorted(expected)) if collection_mode == "quick_smoke" else f"{expected_start_rank}-{expected_end_rank}"
                report("PASS", "summary rank coverage", f"rows cover expected {collection_mode} ranks {expected_detail}")

    # A. summary posts_collected vs raw posts.csv row count
    mismatches = 0
    for row in rows:
        rank = row.get("fortune_rank")
        company = row.get("company_name")
        summary_count = int(row.get("posts_collected") or 0)
        folder_str = row.get("folder")
        if not folder_str:
            continue
        folder = REPO_ROOT / folder_str
        posts_path = folder / "posts.csv"

        actual_count = 0
        if posts_path.exists():
            try:
                with posts_path.open(encoding="utf-8-sig", newline="") as f:
                    actual_count = sum(1 for _ in csv.DictReader(f))
            except Exception:
                actual_count = -1

        if summary_count != actual_count:
            report("FAIL", "summary/raw posts count mismatch", f"rank {rank} {company} summary={summary_count} raw={actual_count}")
            mismatches += 1

    if mismatches == 0:
        report("PASS", "summary/raw posts count mismatch", "0")
    else:
        report("FAIL", "summary/raw posts count mismatch", str(mismatches))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--allow-empty-before-run", action="store_true")
    parser.add_argument("--summary-file", default=str(SUMMARY_FILE))
    parser.add_argument("--expected-start-rank", type=int)
    parser.add_argument("--expected-end-rank", type=int)
    parser.add_argument("--collection-mode", default="custom", choices=["quick_smoke", "coverage_smoke", "full_collection", "custom", "smoke_test"])
    args = parser.parse_args()
    check_scaffold()
    check_dashboard_clean()
    check_x_api_absent()
    check_tracked_sensitive_files()
    check_summary(args.allow_empty_before_run, Path(args.summary_file), args.expected_start_rank, args.expected_end_rank, args.collection_mode)
    check_outputs(args.allow_empty_before_run)
    return 1 if FAILURES else 0


if __name__ == "__main__":
    sys.exit(main())
