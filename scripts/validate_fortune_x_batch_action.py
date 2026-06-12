#!/usr/bin/env python3
"""Validate the Fortune Top 100 X batch collection action scaffold.

This validator is static/local only. It does not read secrets, scrape X, call X
APIs, install MCP, trigger GitHub Actions, or mutate data/dashboard outputs.
"""

from __future__ import annotations

import csv
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_FILE = REPO_ROOT / ".github" / "workflows" / "collect-fortune-x-batches.yml"
RUNNER_FILE = REPO_ROOT / "scripts" / "run_fortune_x_collection_batch.py"
QUEUE_FILE = REPO_ROOT / "config" / "fortune2025_top100_verified_x_collection_queue.csv"
DOC_FILE = REPO_ROOT / "docs" / "operations" / "fortune_top100_x_batch_collection_action_design.md"
SCRAPER_FILE = REPO_ROOT / "src" / "x_scrapper" / "collection" / "x_scraper.py"

FAILURES = 0
WARNINGS = 0

REQUIRED_WORKFLOW_PHRASES = [
    "workflow_dispatch:",
    "max-parallel: 2",
    "batch_index: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]",
    "--batch-size 10",
    "--concurrency-per-batch 10",
    "--max-posts-per-account",
    "AUTHORIZE_FORTUNE_X_COLLECTION",
    "persist-credentials: false",
]

FORBIDDEN_WORKFLOW_PHRASES = [
    "push:",
    "schedule:",
    "sync_dashboard_data.py",
    "gh workflow run",
    "git push",
    "mcp",
    "x api",
]

REQUIRED_RUNNER_PHRASES = [
    "--execute",
    "concurrency-per-batch must remain 10",
    "batch-size must remain 10",
    "max-posts-per-account must remain 50",
    "X_AUTH_TOKEN",
    "X_CT0",
    "scrape_x.py",
    "RAW_ROOT",
    "AUDIT_ROOT",
]

REQUIRED_DOC_PHRASES = [
    "maximum concurrent accounts is 20",
    "two batches run at the same time",
    "10 accounts per batch",
    "No X API is introduced",
    "No MCP is installed",
    "No dashboard sync is performed",
    "No complete historical X coverage claim is allowed",
]


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


def check_file(path: Path) -> bool:
    if path.exists():
        report("PASS", "required file", f"found {rel(path)}")
        return True
    report("FAIL", "required file", f"missing {rel(path)}")
    return False


def check_git_status() -> None:
    result = subprocess.run(
        ["git", "status", "--short", "dashboard/data"],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.stdout.strip():
        report("FAIL", "dashboard/data mutation", result.stdout.strip())
    else:
        report("PASS", "dashboard/data mutation", "no working tree changes under dashboard/data/")


def check_queue() -> None:
    if not QUEUE_FILE.exists():
        return
    with QUEUE_FILE.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) == 100:
        report("PASS", "queue row count", "queue has 100 rows")
    else:
        report("FAIL", "queue row count", f"expected 100 rows, found {len(rows)}")
    bad = [row.get("fortune_rank", "?") for row in rows if row.get("queue_source") != "human_final_manual_review" or row.get("eligibility_source_field") != "final_manual_scrape_eligible"]
    if bad:
        report("FAIL", "queue source", "non-human-final queue rows: " + ", ".join(bad[:20]))
    else:
        report("PASS", "queue source", "all rows use human_final_manual_review/final_manual_scrape_eligible")


def require_phrases(path: Path, phrases: list[str], check_name: str) -> None:
    text = path.read_text(encoding="utf-8")
    missing = [phrase for phrase in phrases if phrase not in text]
    if missing:
        report("FAIL", check_name, "missing: " + ", ".join(missing))
    else:
        report("PASS", check_name, "required phrases present")


def reject_phrases(path: Path, phrases: list[str], check_name: str) -> None:
    text = path.read_text(encoding="utf-8").lower()
    found = [phrase for phrase in phrases if phrase.lower() in text]
    if found:
        report("FAIL", check_name, "forbidden phrases present: " + ", ".join(found))
    else:
        report("PASS", check_name, "forbidden trigger/sync/API/MCP phrases absent")


def check_scraper_cap() -> None:
    if not SCRAPER_FILE.exists():
        return
    text = SCRAPER_FILE.read_text(encoding="utf-8")
    required = ["MAX_POSTS", "capped_records", "MAX_POSTS reached"]
    missing = [phrase for phrase in required if phrase not in text]
    if missing:
        report("FAIL", "scraper max posts cap", "missing: " + ", ".join(missing))
    else:
        report("PASS", "scraper max posts cap", "existing scraper path supports MAX_POSTS cap")


def main() -> int:
    workflow_ok = check_file(WORKFLOW_FILE)
    runner_ok = check_file(RUNNER_FILE)
    doc_ok = check_file(DOC_FILE)
    check_file(QUEUE_FILE)
    check_git_status()
    check_queue()
    if workflow_ok:
        require_phrases(WORKFLOW_FILE, REQUIRED_WORKFLOW_PHRASES, "workflow batch controls")
        reject_phrases(WORKFLOW_FILE, FORBIDDEN_WORKFLOW_PHRASES, "workflow forbidden behavior")
    if runner_ok:
        require_phrases(RUNNER_FILE, REQUIRED_RUNNER_PHRASES, "runner execution controls")
    if doc_ok:
        require_phrases(DOC_FILE, REQUIRED_DOC_PHRASES, "batch action documentation")
    check_scraper_cap()
    return 1 if FAILURES else 0


if __name__ == "__main__":
    sys.exit(main())
