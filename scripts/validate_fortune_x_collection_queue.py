#!/usr/bin/env python3
"""Validate the Fortune Top 100 human-reviewed X collection queue scaffold.

Static/local only: no secrets, network calls, scraping, SEC calls, workflow triggers,
or data/dashboard mutation.
"""

from __future__ import annotations

import csv
import subprocess
import sys
from collections import defaultdict
from pathlib import Path
from urllib.parse import urlparse

REPO_ROOT = Path(__file__).resolve().parents[1]
MASTER_FILE = REPO_ROOT / "config" / "fortune2025_x_account_verification_master.csv"
QUEUE_FILE = REPO_ROOT / "config" / "fortune2025_top100_verified_x_collection_queue.csv"
SCHEMA_FILE = REPO_ROOT / "config" / "schemas" / "fortune2025_top100_verified_x_collection_queue.schema.json"

REQUIRED_QUEUE_COLUMNS = [
    "fortune_rank",
    "company_name",
    "normalized_company_name",
    "collection_x_handle",
    "collection_x_url",
    "secondary_x_url",
    "final_manual_account_status",
    "human_review_batch",
    "collection_status",
    "collection_authorized",
    "dry_run_only",
    "data_mutation_allowed",
    "dashboard_sync_allowed",
    "queue_source",
    "eligibility_source_field",
    "collection_priority",
    "collection_scope",
    "collection_start_policy",
    "collection_end_policy",
    "max_posts_policy",
    "notes",
]

ALLOWED_COLLECTION_STATUSES = {"queued_not_collected", "blocked", "collected", "failed"}
ALLOWED_FINAL_STATUSES = {"confirmed_candidate_official", "candidate_rejected_alternate_found"}
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


def is_true(value: str) -> bool:
    return value.strip().lower() == "true"


def handle_from_url(url: str) -> str:
    parsed = urlparse(url.strip())
    parts = [part for part in parsed.path.split("/") if part]
    if not parts:
        return ""
    return "@" + parts[0]


def validate_required_files() -> None:
    for path in [MASTER_FILE, QUEUE_FILE, SCHEMA_FILE]:
        if path.exists():
            report("PASS", "required file", f"found {rel(path)}")
        else:
            report("FAIL", "required file", f"missing {rel(path)}")


def check_git_status() -> None:
    result = subprocess.run(
        ["git", "status", "--short", "data", "dashboard/data"],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.stdout.strip():
        report("FAIL", "data/dashboard mutation", "working tree changed under data/ or dashboard/data/\n" + result.stdout.strip())
    else:
        report("PASS", "data/dashboard mutation", "no changes under data/ or dashboard/data/")


def validate_queue() -> None:
    if not MASTER_FILE.exists() or not QUEUE_FILE.exists():
        return

    master_fields, master_rows = read_csv(MASTER_FILE)
    queue_fields, queue_rows = read_csv(QUEUE_FILE)

    missing = [column for column in REQUIRED_QUEUE_COLUMNS if column not in queue_fields]
    if missing:
        report("FAIL", "required queue columns", "missing: " + ", ".join(missing))
        return
    report("PASS", "required queue columns", f"all {len(REQUIRED_QUEUE_COLUMNS)} required columns present")

    if "scrape_eligible" in queue_fields:
        report("FAIL", "old eligibility field", "queue must not carry old scrape_eligible as final eligibility")
    else:
        report("PASS", "old eligibility field", "queue does not carry old scrape_eligible")

    master_by_rank = {row["fortune_rank"].strip(): row for row in master_rows}
    expected_rows = [row for row in master_rows if is_true(row.get("final_manual_scrape_eligible", ""))]
    if len(expected_rows) != 100:
        report("FAIL", "master final eligibility count", f"expected 100 final_manual_scrape_eligible rows, found {len(expected_rows)}")
    else:
        report("PASS", "master final eligibility count", "100 rows are final manual scrape eligible")

    if len(queue_rows) != 100:
        report("FAIL", "queue row count", f"expected 100 queue rows, found {len(queue_rows)}")
    elif len(queue_rows) != len(expected_rows):
        report("FAIL", "queue row count", f"queue has {len(queue_rows)} rows but master has {len(expected_rows)} final eligible rows")
    else:
        report("PASS", "queue row count", "queue row count matches final_manual_scrape_eligible count: 100")

    expected_ranks = {row["fortune_rank"].strip() for row in expected_rows}
    queue_ranks = {row["fortune_rank"].strip() for row in queue_rows}
    missing_ranks = sorted(expected_ranks - queue_ranks, key=int)
    extra_ranks = sorted(queue_ranks - expected_ranks, key=int)
    if missing_ranks:
        report("FAIL", "queue source completeness", "missing final eligible ranks: " + ", ".join(missing_ranks[:20]))
    if extra_ranks:
        report("FAIL", "queue source restriction", "queue contains non-final-eligible ranks: " + ", ".join(extra_ranks[:20]))
    if not missing_ranks and not extra_ranks:
        report("PASS", "queue source restriction", "queue contains exactly the final manually eligible ranks")

    handles: defaultdict[str, list[int]] = defaultdict(list)
    for index, row in enumerate(queue_rows, start=2):
        prefix = f"line {index} rank={row.get('fortune_rank', '')}"
        rank = row["fortune_rank"].strip()
        master = master_by_rank.get(rank)
        if not master:
            report("FAIL", "master row link", f"{prefix} has no matching master row")
            continue

        collection_url = row["collection_x_url"].strip()
        collection_handle = row["collection_x_handle"].strip()
        secondary_url = row["secondary_x_url"].strip()
        final_primary = master.get("final_manual_x_url_primary", "").strip()
        final_secondary = master.get("final_manual_x_url_secondary", "").strip()
        handles[collection_handle.lower()].append(index)

        if not is_true(master.get("final_manual_scrape_eligible", "")):
            report("FAIL", "master final eligibility", f"{prefix} does not come from final_manual_scrape_eligible=true")
        if collection_url != final_primary:
            report("FAIL", "collection URL mapping", f"{prefix} collection_x_url differs from master final_manual_x_url_primary")
        if secondary_url != final_secondary:
            report("FAIL", "secondary URL mapping", f"{prefix} secondary_x_url differs from master final_manual_x_url_secondary")
        if collection_handle != handle_from_url(final_primary):
            report("FAIL", "collection handle mapping", f"{prefix} collection_x_handle={collection_handle} does not match final URL")
        if row["final_manual_account_status"].strip() != master.get("final_manual_account_status", "").strip():
            report("FAIL", "final status mapping", f"{prefix} final_manual_account_status differs from master")
        if row["human_review_batch"].strip() != master.get("human_review_batch", "").strip():
            report("FAIL", "human batch mapping", f"{prefix} human_review_batch differs from master")

        exact_expectations = {
            "collection_status": "queued_not_collected",
            "collection_authorized": "false",
            "dry_run_only": "true",
            "data_mutation_allowed": "false",
            "dashboard_sync_allowed": "false",
            "queue_source": "human_final_manual_review",
            "eligibility_source_field": "final_manual_scrape_eligible",
            "collection_priority": "top100_human_final",
            "collection_scope": "timeline_posts_if_accessible",
            "collection_start_policy": "to_be_defined_before_collection",
            "collection_end_policy": "to_be_defined_before_collection",
            "max_posts_policy": "to_be_defined_before_collection",
        }
        for column, expected in exact_expectations.items():
            if row[column].strip() != expected:
                report("FAIL", column, f"{prefix} expected {expected}, found {row[column]}")
        if row["collection_status"].strip() not in ALLOWED_COLLECTION_STATUSES:
            report("FAIL", "collection status taxonomy", f"{prefix} invalid collection_status={row['collection_status']}")
        if row["final_manual_account_status"].strip() not in ALLOWED_FINAL_STATUSES:
            report("FAIL", "final manual status", f"{prefix} invalid final_manual_account_status={row['final_manual_account_status']}")
        if not collection_url:
            report("FAIL", "collection URL", f"{prefix} has empty collection_x_url")
        if not collection_handle:
            report("FAIL", "collection handle", f"{prefix} has empty collection_x_handle")
        if "scrape_eligible" in row.get("eligibility_source_field", "") and row["eligibility_source_field"].strip() != "final_manual_scrape_eligible":
            report("FAIL", "eligibility source", f"{prefix} uses old scrape_eligible eligibility")

    duplicate_handles = {handle: lines for handle, lines in handles.items() if handle and len(lines) > 1}
    if duplicate_handles:
        bad = [f"{handle} lines={lines}" for handle, lines in duplicate_handles.items()]
        report("WARN", "duplicate collection handles", "; ".join(bad[:10]))
    else:
        report("PASS", "duplicate collection handles", "no duplicate collection_x_handle values")

    if FAILURES == 0:
        report("PASS", "queue rows", f"validated {len(queue_rows)} human-final queue rows")


def main() -> int:
    validate_required_files()
    check_git_status()
    validate_queue()
    return 1 if FAILURES else 0


if __name__ == "__main__":
    sys.exit(main())
