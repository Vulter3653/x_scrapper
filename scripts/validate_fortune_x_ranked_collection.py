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
    "max_posts_cap", "source_folder",
}
REQUIRED_SUMMARY_COLUMNS = [
    "fortune_rank", "company_name", "official_x_handle", "folder", "attempted", "status",
    "posts_collected", "error_type", "error_message", "started_at", "completed_at",
]
FORBIDDEN_TRACKED_PATTERNS = ("session", "cache", "screenshot", "trace", "auth_token", "ct0")
FORBIDDEN_API_MARKERS = ("api.x.com", "api.twitter.com", "bearer_token", "Authorization: Bearer")

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
            "strategy:",
            "matrix:",
            "actions/upload-artifact",
            "actions/download-artifact",
            "python scripts/run_fortune_x_ranked_collection.py",
            "python scripts/merge_fortune_x_ranked_collection_shards.py",
            "git push",
        ]
        missing = [item for item in required if item not in text]
        if missing:
            report("FAIL", "workflow controls", "missing: " + ", ".join(missing))
        else:
            report("PASS", "workflow controls", "matrix ranked collection workflow controls present")
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
    if not OUTPUT_ROOT.exists():
        if allow_empty_before_run:
            report("PASS", "output root", f"{rel(OUTPUT_ROOT)} absent before first run is allowed")
        else:
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
    for folder in folders:
        posts_path = folder / "posts.csv"
        audit_path = folder / "audit.json"
        if not posts_path.exists():
            report("FAIL", "posts.csv", f"missing {rel(posts_path)}")
            continue
        if not audit_path.exists():
            report("FAIL", "audit.json", f"missing {rel(audit_path)}")
        else:
            try:
                audit = json.loads(audit_path.read_text(encoding="utf-8"))
                if audit.get("x_api_used") is not False:
                    report("FAIL", "audit x_api_used", f"{rel(audit_path)} x_api_used is not false")
            except Exception as exc:
                report("FAIL", "audit.json parse", f"{rel(audit_path)}: {exc}")
        fields, rows = read_csv(posts_path)
        missing_cols = sorted(REQUIRED_POST_COLUMNS - set(fields))
        if missing_cols:
            report("FAIL", "posts.csv columns", f"{rel(posts_path)} missing: " + ", ".join(missing_cols))
        post_file_count += 1
        for row in rows:
            tweet_id = row.get("tweet_id", "").strip()
            if tweet_id:
                all_tweet_ids.append(tweet_id)
            if not row.get("text", "").strip():
                missing_text += 1
            if not row.get("created_at", "").strip():
                missing_created_at += 1
    duplicates = sum(count - 1 for count in Counter(all_tweet_ids).values() if count > 1)
    report("PASS", "posts.csv files", f"checked {post_file_count} posts.csv files")
    report("PASS", "duplicate tweet_id count", str(duplicates))
    report("PASS", "missing text count", str(missing_text))
    report("PASS", "missing created_at count", str(missing_created_at))


def check_summary(allow_empty_before_run: bool, summary_file: Path, expected_start_rank: int | None, expected_end_rank: int | None) -> None:
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
            expected = set(range(expected_start_rank, expected_end_rank + 1))
            present = {int(row["fortune_rank"]) for row in rows if row.get("fortune_rank", "").isdigit()}
            missing_ranks = sorted(expected - present)
            if missing_ranks:
                report("FAIL", "summary rank coverage", "missing ranks: " + ", ".join(str(rank) for rank in missing_ranks))
            else:
                report("PASS", "summary rank coverage", f"rows cover ranks {expected_start_rank}-{expected_end_rank}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--allow-empty-before-run", action="store_true")
    parser.add_argument("--summary-file", default=str(SUMMARY_FILE))
    parser.add_argument("--expected-start-rank", type=int)
    parser.add_argument("--expected-end-rank", type=int)
    args = parser.parse_args()
    check_scaffold()
    check_dashboard_clean()
    check_x_api_absent()
    check_tracked_sensitive_files()
    check_summary(args.allow_empty_before_run, Path(args.summary_file), args.expected_start_rank, args.expected_end_rank)
    check_outputs(args.allow_empty_before_run)
    return 1 if FAILURES else 0


if __name__ == "__main__":
    sys.exit(main())
