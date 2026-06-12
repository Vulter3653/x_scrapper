#!/usr/bin/env python3
"""Validate the Fortune Top 100 verified X collection queue scaffold.

Static/local only: no secrets, network calls, scraping, SEC calls, workflow triggers,
or data/dashboard mutation.
"""

from __future__ import annotations

import csv
import sys
from collections import Counter, defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
MASTER_FILE = REPO_ROOT / "config" / "fortune2025_x_account_verification_master.csv"
QUEUE_FILE = REPO_ROOT / "config" / "fortune2025_top100_verified_x_collection_queue.csv"
SCHEMA_FILE = REPO_ROOT / "config" / "schemas" / "fortune2025_top100_verified_x_collection_queue.schema.json"

REQUIRED_QUEUE_COLUMNS = [
    "fortune_rank",
    "company_name",
    "normalized_company_name",
    "official_x_account_status",
    "official_x_handle",
    "official_x_url",
    "evidence_source_url",
    "evidence_source_type",
    "evidence_strength",
    "confidence",
    "scrape_eligible",
    "collection_status",
    "collection_priority",
    "collection_scope",
    "collection_start_policy",
    "collection_end_policy",
    "max_posts_policy",
    "notes",
]

ELIGIBLE_STATUSES = {"official", "brand_official"}
BLOCKED_STATUSES = {"blocked", "inaccessible", "no_account_found", "ambiguous", "unknown", "do_not_scrape", "subsidiary_only"}
ALLOWED_COLLECTION_STATUSES = {"queued_not_collected", "blocked", "collected", "failed"}
ALLOWED_CONFIDENCE = {"high", "medium"}
BLOCKED_EVIDENCE_TYPES = {"manual_search_only", "not_reviewed"}
BLOCKED_EVIDENCE_STRENGTHS = {"none", "level_6", "level_7", "level_8"}
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


def master_scrape_eligible(row: dict[str, str]) -> bool:
    return (
        is_true(row.get("scrape_eligible", ""))
        and row.get("official_x_account_status", "").strip() in ELIGIBLE_STATUSES
        and bool(row.get("official_x_handle", "").strip())
        and bool(row.get("official_x_url", "").strip())
        and bool(row.get("evidence_source_url", "").strip())
        and row.get("confidence", "").strip() in ALLOWED_CONFIDENCE
        and row.get("evidence_source_type", "").strip() not in BLOCKED_EVIDENCE_TYPES
        and row.get("evidence_strength", "").strip() not in BLOCKED_EVIDENCE_STRENGTHS
    )


def validate_required_files() -> None:
    for path in [MASTER_FILE, QUEUE_FILE, SCHEMA_FILE]:
        if path.exists():
            report("PASS", "required file", f"found {rel(path)}")
        else:
            report("FAIL", "required file", f"missing {rel(path)}")


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

    expected_rows = [row for row in master_rows if master_scrape_eligible(row)]
    if len(queue_rows) != len(expected_rows):
        report("FAIL", "queue row count", f"queue has {len(queue_rows)} rows but master has {len(expected_rows)} scrape-eligible rows")
    else:
        report("PASS", "queue row count", f"queue row count matches master scrape-eligible count: {len(queue_rows)}")

    expected_keys = {(row["fortune_rank"], row["official_x_handle"].strip().lower()) for row in expected_rows}
    queue_keys = {(row["fortune_rank"], row["official_x_handle"].strip().lower()) for row in queue_rows}
    missing_keys = sorted(expected_keys - queue_keys)
    extra_keys = sorted(queue_keys - expected_keys)
    if missing_keys:
        report("FAIL", "queue source completeness", "missing eligible master rows: " + "; ".join(f"rank={rank} handle={handle}" for rank, handle in missing_keys[:10]))
    if extra_keys:
        report("FAIL", "queue source restriction", "queue contains rows not eligible in master: " + "; ".join(f"rank={rank} handle={handle}" for rank, handle in extra_keys[:10]))
    if not missing_keys and not extra_keys:
        report("PASS", "queue source restriction", "queue contains exactly the master scrape-eligible rank/handle pairs")

    handles: defaultdict[str, list[int]] = defaultdict(list)
    for index, row in enumerate(queue_rows, start=2):
        prefix = f"line {index} rank={row.get('fortune_rank', '')}"
        status = row["official_x_account_status"].strip()
        evidence_type = row["evidence_source_type"].strip()
        evidence_strength = row["evidence_strength"].strip()
        confidence = row["confidence"].strip()
        collection_status = row["collection_status"].strip()
        handle = row["official_x_handle"].strip()
        notes = row["notes"].strip().lower()
        handles[handle.lower()].append(index)

        if not is_true(row["scrape_eligible"]):
            report("FAIL", "queue scrape eligibility", f"{prefix} has scrape_eligible={row['scrape_eligible']}")
        if status not in ELIGIBLE_STATUSES:
            report("FAIL", "queue account status", f"{prefix} has non-eligible status={status}")
        if status in BLOCKED_STATUSES:
            report("FAIL", "blocked status exclusion", f"{prefix} includes blocked status={status}")
        if not handle:
            report("FAIL", "official handle", f"{prefix} has empty official_x_handle")
        if not row["official_x_url"].strip():
            report("FAIL", "official X URL", f"{prefix} has empty official_x_url")
        if not row["evidence_source_url"].strip():
            report("FAIL", "evidence URL", f"{prefix} has empty evidence_source_url")
        if evidence_type in BLOCKED_EVIDENCE_TYPES:
            report("FAIL", "evidence source type gate", f"{prefix} has evidence_source_type={evidence_type}")
        if evidence_strength in BLOCKED_EVIDENCE_STRENGTHS:
            report("FAIL", "evidence strength gate", f"{prefix} has evidence_strength={evidence_strength}")
        if confidence not in ALLOWED_CONFIDENCE:
            report("FAIL", "confidence gate", f"{prefix} has confidence={confidence}")
        if collection_status not in ALLOWED_COLLECTION_STATUSES:
            report("FAIL", "collection status taxonomy", f"{prefix} has collection_status={collection_status}")
        if collection_status != "queued_not_collected":
            report("WARN", "collection status default", f"{prefix} has non-default collection_status={collection_status}")
        if row["collection_priority"].strip() != "top100_verified":
            report("FAIL", "collection priority default", f"{prefix} has collection_priority={row['collection_priority']}")
        if row["collection_scope"].strip() != "timeline_posts_if_accessible":
            report("FAIL", "collection scope default", f"{prefix} has collection_scope={row['collection_scope']}")
        for column in ["collection_start_policy", "collection_end_policy", "max_posts_policy"]:
            if row[column].strip() != "to_be_defined_before_collection":
                report("FAIL", "collection policy default", f"{prefix} has {column}={row[column]}")
        if handle and len(handles[handle.lower()]) > 1 and "duplicate" not in notes:
            report("FAIL", "duplicate official handle", f"{prefix} duplicate handle {handle} lacks duplicate documentation in notes")

    duplicate_handles = {handle: lines for handle, lines in handles.items() if handle and len(lines) > 1}
    if duplicate_handles:
        bad = [f"{handle} lines={lines}" for handle, lines in duplicate_handles.items()]
        report("FAIL", "duplicate official handles", "; ".join(bad[:10]))
    else:
        report("PASS", "duplicate official handles", "no duplicate official_x_handle values")

    if FAILURES == 0:
        report("PASS", "queue rows", f"validated {len(queue_rows)} queue rows")


def main() -> int:
    validate_required_files()
    validate_queue()
    return 1 if FAILURES else 0


if __name__ == "__main__":
    sys.exit(main())
