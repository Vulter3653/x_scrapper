#!/usr/bin/env python3
"""Validate the Fortune Top 100 X collection method decision.

Static/local only: no secrets, network calls, X scraping, X APIs, MCP install,
browser automation, SEC downloads, workflow triggers, or data/dashboard mutation.
"""

from __future__ import annotations

import csv
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DECISION_FILE = REPO_ROOT / "config" / "fortune2025_top100_x_collection_method_decision.csv"
SCHEMA_FILE = REPO_ROOT / "config" / "schemas" / "fortune2025_top100_x_collection_method_decision.schema.json"
QUEUE_FILE = REPO_ROOT / "config" / "fortune2025_top100_verified_x_collection_queue.csv"
DOC_FILE = REPO_ROOT / "docs" / "operations" / "fortune_top100_x_collection_method_decision.md"
AUTH_DOC_FILE = REPO_ROOT / "docs" / "operations" / "fortune_top100_x_collection_authorization_proposal.md"

REQUIRED_COLUMNS = [
    "decision_id", "queue_file", "queue_row_count", "queue_source",
    "eligibility_source_field", "selected_collection_method", "selected_access_method",
    "extends_existing_workflow", "x_api_required", "mcp_required",
    "browser_automation_required", "authentication_required", "collection_authorized",
    "dry_run_only", "data_mutation_allowed", "dashboard_sync_allowed",
    "raw_output_path", "processed_output_path", "audit_log_path",
    "authorization_required_before_execution", "notes",
]

EXPECTED_VALUES = {
    "decision_id": "fortune_top100_x_collection_method_decision_v1",
    "queue_file": "config/fortune2025_top100_verified_x_collection_queue.csv",
    "queue_row_count": "100",
    "queue_source": "human_final_manual_review",
    "eligibility_source_field": "final_manual_scrape_eligible",
    "selected_collection_method": "extend_existing_collection_workflow",
    "selected_access_method": "existing_repo_collection_path",
    "extends_existing_workflow": "true",
    "x_api_required": "false",
    "mcp_required": "false",
    "browser_automation_required": "false",
    "authentication_required": "to_be_confirmed_before_execution",
    "collection_authorized": "false",
    "dry_run_only": "true",
    "data_mutation_allowed": "false",
    "dashboard_sync_allowed": "false",
    "raw_output_path": "not_defined_until_collection_authorized",
    "processed_output_path": "not_defined_until_collection_authorized",
    "audit_log_path": "not_defined_until_collection_authorized",
    "authorization_required_before_execution": "true",
}

REQUIRED_DOC_PHRASES = [
    "100 human-final eligible accounts",
    "queue_source=human_final_manual_review",
    "eligibility_source_field=final_manual_scrape_eligible",
    "old `scrape_eligible` field is preliminary/reference only",
    "scrape_x.py",
    "src/x_scrapper/collection/x_scraper.py",
    ".github/workflows/scrape.yml",
    "extend_existing_collection_workflow",
    "least disruptive",
    "No complete historical X coverage claim is allowed",
    "This decision does not authorize collection",
    "This decision does not call X API",
    "This decision does not install MCP",
    "This decision does not run browser automation",
    "This decision does not modify `data/`",
    "This decision does not modify `dashboard/data/`",
]

FORBIDDEN_DOC_PHRASES = [
    "collection has started",
    "scraping has started",
    "x api was called",
    "x api has been called",
    "mcp was installed",
    "mcp has been installed",
    "browser automation was executed",
    "browser automation has been executed",
    "complete historical x coverage is available",
    "complete historical x archive is available",
    "raw output created",
    "processed output created",
]

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


def require_file(path: Path) -> bool:
    if path.exists():
        report("PASS", "required file", f"found {rel(path)}")
        return True
    report("FAIL", "required file", f"missing {rel(path)}")
    return False


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


def validate_decision() -> None:
    files_ok = all(require_file(path) for path in [DECISION_FILE, SCHEMA_FILE, QUEUE_FILE, DOC_FILE])
    check_git_status()
    if not files_ok:
        return

    queue_fields, queue_rows = read_csv(QUEUE_FILE)
    decision_fields, decision_rows = read_csv(DECISION_FILE)

    missing = [column for column in REQUIRED_COLUMNS if column not in decision_fields]
    if missing:
        report("FAIL", "required method decision columns", "missing: " + ", ".join(missing))
        return
    report("PASS", "required method decision columns", f"all {len(REQUIRED_COLUMNS)} required columns present")

    if len(decision_rows) != 1:
        report("FAIL", "decision row count", f"expected 1 decision row, found {len(decision_rows)}")
        return
    report("PASS", "decision row count", "one active method decision row")

    decision = {key: (value or "").strip() for key, value in decision_rows[0].items()}
    for column, expected in EXPECTED_VALUES.items():
        if decision[column] != expected:
            report("FAIL", column, f"expected {expected}, found {decision[column]}")
        else:
            report("PASS", column, f"{column}={expected}")

    if len(queue_rows) != 100:
        report("FAIL", "queue row count", f"expected 100 queue rows, found {len(queue_rows)}")
    else:
        report("PASS", "queue row count", "queue has 100 rows")

    for path_col in ["raw_output_path", "processed_output_path", "audit_log_path"]:
        value = decision[path_col]
        if value.startswith(("data/", "dashboard/data/")) or value.endswith((".json", ".csv", ".jsonl", ".md")):
            report("FAIL", path_col, f"{path_col} implies concrete output path: {value}")

    combined = " ".join(decision.values()).lower()
    forbidden_policy = [
        "collection_authorized=true", "dry_run_only=false", "data_mutation_allowed=true",
        "dashboard_sync_allowed=true", "x_api_required=true", "mcp_required=true",
        "browser_automation_required=true", "complete historical",
    ]
    found_policy = [phrase for phrase in forbidden_policy if phrase in combined]
    if found_policy:
        report("FAIL", "method decision boundary", "decision implies forbidden state: " + ", ".join(found_policy))
    else:
        report("PASS", "method decision boundary", "decision keeps collection/API/MCP/browser/output boundaries disabled")

    doc_text = DOC_FILE.read_text(encoding="utf-8")
    missing_doc = [phrase for phrase in REQUIRED_DOC_PHRASES if phrase not in doc_text]
    if missing_doc:
        report("FAIL", "method decision documentation", "missing: " + ", ".join(missing_doc))
    else:
        report("PASS", "method decision documentation", "required method decision content documented")

    docs_to_check = [DOC_FILE]
    if AUTH_DOC_FILE.exists():
        docs_to_check.append(AUTH_DOC_FILE)
    for path in docs_to_check:
        text = path.read_text(encoding="utf-8").lower()
        found = [phrase for phrase in FORBIDDEN_DOC_PHRASES if phrase in text]
        if found:
            report("FAIL", "documentation boundary", f"{rel(path)} implies forbidden state: " + ", ".join(found))
    if FAILURES == 0:
        report("PASS", "documentation boundary", "docs do not imply collection, API call, MCP install, browser automation, or complete historical coverage")


def main() -> int:
    validate_decision()
    return 1 if FAILURES else 0


if __name__ == "__main__":
    sys.exit(main())
