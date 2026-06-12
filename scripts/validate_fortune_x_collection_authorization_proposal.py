#!/usr/bin/env python3
"""Validate the Fortune Top 100 X collection authorization proposal.

Static/local only: no secrets, network calls, X scraping, X APIs, MCP install,
browser automation, SEC downloads, workflow triggers, or data/dashboard mutation.
"""

from __future__ import annotations

import csv
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
QUEUE_FILE = REPO_ROOT / "config" / "fortune2025_top100_verified_x_collection_queue.csv"
READINESS_FILE = REPO_ROOT / "config" / "fortune2025_top100_x_collection_readiness_policy.csv"
PROPOSAL_FILE = REPO_ROOT / "config" / "fortune2025_top100_x_collection_authorization_proposal.csv"
SCHEMA_FILE = REPO_ROOT / "config" / "schemas" / "fortune2025_top100_x_collection_authorization_proposal.schema.json"
DOC_FILE = REPO_ROOT / "docs" / "operations" / "fortune_top100_x_collection_authorization_proposal.md"
QUEUE_VALIDATOR = REPO_ROOT / "scripts" / "validate_fortune_x_collection_queue.py"
READINESS_VALIDATOR = REPO_ROOT / "scripts" / "validate_fortune_x_collection_readiness.py"

REQUIRED_COLUMNS = [
    "proposal_id",
    "queue_file",
    "eligible_account_count",
    "proposed_collection_method",
    "proposed_access_method",
    "x_api_required",
    "mcp_required",
    "browser_automation_required",
    "authentication_required",
    "collection_authorized",
    "dry_run_only",
    "proposed_date_window",
    "proposed_max_posts_per_account",
    "proposed_rate_limit_policy",
    "proposed_retry_policy",
    "proposed_failure_status_values",
    "proposed_raw_output_path",
    "proposed_processed_output_path",
    "proposed_audit_log_path",
    "dashboard_sync_allowed",
    "data_mutation_allowed",
    "risk_level",
    "approval_required_before_execution",
    "notes",
]

REQUIRED_DOC_PHRASES = [
    "This proposal does not authorize collection",
    "does not install MCP",
    "does not call X API",
    "does not modify `data/`",
    "does not modify `dashboard/data/`",
    "does not authorize dashboard sync",
    "retrievable timeline posts only",
    "No complete historical X archive claim is allowed",
    "Explicit collection authorization commit",
    "fixed date window",
    "Maximum posts per account",
    "Rate-limit handling policy",
    "Per-account audit log",
]

REQUIRED_AUDIT_FIELDS = [
    "fortune_rank",
    "company_name",
    "official_x_handle",
    "official_x_url",
    "collection_attempted_at",
    "collection_method",
    "collection_status",
    "posts_requested",
    "posts_collected",
    "earliest_post_date",
    "latest_post_date",
    "failure_reason",
    "rate_limit_observed",
    "auth_required",
    "raw_output_path",
    "processed_output_path",
    "dashboard_synced",
    "notes",
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


def run_validator(path: Path, label: str) -> None:
    if not path.exists():
        report("FAIL", label, f"missing {rel(path)}")
        return
    result = subprocess.run(
        [sys.executable, str(path)],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        detail = (result.stdout + result.stderr).strip().splitlines()[:10]
        report("FAIL", label, f"{label} failed: " + " | ".join(detail))
    else:
        report("PASS", label, f"{label} passed")


def validate_proposal() -> None:
    files_ok = all(require_file(path) for path in [QUEUE_FILE, READINESS_FILE, PROPOSAL_FILE, SCHEMA_FILE, DOC_FILE])
    run_validator(QUEUE_VALIDATOR, "queue validator")
    run_validator(READINESS_VALIDATOR, "readiness validator")
    if not files_ok:
        return

    queue_fields, queue_rows = read_csv(QUEUE_FILE)
    proposal_fields, proposal_rows = read_csv(PROPOSAL_FILE)
    missing = [column for column in REQUIRED_COLUMNS if column not in proposal_fields]
    if missing:
        report("FAIL", "required proposal columns", "missing: " + ", ".join(missing))
        return
    report("PASS", "required proposal columns", f"all {len(REQUIRED_COLUMNS)} required columns present")

    if len(proposal_rows) != 1:
        report("FAIL", "proposal row count", f"expected 1 proposal row, found {len(proposal_rows)}")
        return
    report("PASS", "proposal row count", "one active authorization proposal row")

    proposal = {key: (value or "").strip() for key, value in proposal_rows[0].items()}
    try:
        actual_count = int(proposal["eligible_account_count"])
    except ValueError:
        report("FAIL", "eligible account count", f"not an integer: {proposal['eligible_account_count']}")
        actual_count = -1
    if actual_count != len(queue_rows):
        report("FAIL", "eligible account count", f"proposal has {actual_count}, queue has {len(queue_rows)}")
    else:
        report("PASS", "eligible account count", f"proposal matches queue row count: {len(queue_rows)}")

    expected_values = {
        "queue_file": "config/fortune2025_top100_verified_x_collection_queue.csv",
        "collection_authorized": "false",
        "dry_run_only": "true",
        "data_mutation_allowed": "false",
        "dashboard_sync_allowed": "false",
        "approval_required_before_execution": "true",
        "proposed_raw_output_path": "not_defined_until_collection_authorized",
        "proposed_processed_output_path": "not_defined_until_collection_authorized",
        "proposed_audit_log_path": "not_defined_until_collection_authorized",
        "risk_level": "pre_execution_design_only",
    }
    for column, expected in expected_values.items():
        if proposal[column] != expected:
            report("FAIL", column, f"expected {expected}, found {proposal[column]}")
        else:
            report("PASS", column, f"{column}={expected}")

    for column in ["proposed_collection_method", "proposed_access_method"]:
        if proposal[column] != "to_be_selected":
            report("FAIL", column, f"expected to_be_selected, found {proposal[column]}")
        else:
            report("PASS", column, f"{column}=to_be_selected")
    for column in ["x_api_required", "mcp_required", "browser_automation_required", "authentication_required"]:
        if proposal[column] != "to_be_decided":
            report("FAIL", column, f"expected to_be_decided, found {proposal[column]}")
        else:
            report("PASS", column, f"{column}=to_be_decided")
    for column in ["proposed_date_window", "proposed_max_posts_per_account", "proposed_rate_limit_policy", "proposed_retry_policy"]:
        if proposal[column] != "to_be_defined_before_execution":
            report("FAIL", column, f"expected to_be_defined_before_execution, found {proposal[column]}")
        else:
            report("PASS", column, f"{column}=to_be_defined_before_execution")

    failure_values = {value.strip() for value in proposal["proposed_failure_status_values"].split(",") if value.strip()}
    expected_failure_values = {"blocked", "failed", "inaccessible", "rate_limited", "auth_required", "no_decided"}
    if failure_values != expected_failure_values:
        report("FAIL", "proposed failure status values", f"expected {sorted(expected_failure_values)}, found {sorted(failure_values)}")
    else:
        report("PASS", "proposed failure status values", "controlled proposed failure statuses are defined")

    combined_policy = " ".join(proposal.values()).lower()
    forbidden_policy_phrases = [
        "collection_authorized=true",
        "dry_run_only=false",
        "data_mutation_allowed=true",
        "dashboard_sync_allowed=true",
        "scraping authorized",
        "scrape authorized",
        "mcp installed",
        "x api called",
        "api has been called",
        "complete historical",
        "all historical x posts",
    ]
    found_policy = [phrase for phrase in forbidden_policy_phrases if phrase in combined_policy]
    if found_policy:
        report("FAIL", "proposal policy boundary", "policy implies forbidden state: " + ", ".join(found_policy))
    else:
        report("PASS", "proposal policy boundary", "policy does not imply collection, MCP, API use, mutation, or complete history")

    output_values = [proposal["proposed_raw_output_path"], proposal["proposed_processed_output_path"], proposal["proposed_audit_log_path"]]
    if any(value.startswith(("data/", "dashboard/data/")) or value.endswith((".json", ".csv", ".jsonl")) for value in output_values):
        report("FAIL", "output path boundary", "proposal defines concrete output path before authorization")
    else:
        report("PASS", "output path boundary", "output paths remain undefined until authorization")

    doc_text = DOC_FILE.read_text(encoding="utf-8")
    missing_doc = [phrase for phrase in REQUIRED_DOC_PHRASES if phrase not in doc_text]
    if missing_doc:
        report("FAIL", "proposal documentation", "missing: " + ", ".join(missing_doc))
    else:
        report("PASS", "proposal documentation", "required proposal boundaries and controls documented")

    missing_audit = [field for field in REQUIRED_AUDIT_FIELDS if field not in doc_text]
    if missing_audit:
        report("FAIL", "future audit fields", "missing: " + ", ".join(missing_audit))
    else:
        report("PASS", "future audit fields", f"all {len(REQUIRED_AUDIT_FIELDS)} audit fields documented")

    forbidden_doc_phrases = [
        "collection_authorized=true",
        "dry_run_only=false",
        "data_mutation_allowed=true",
        "dashboard_sync_allowed=true",
        "mcp_required=true",
        "x_api_required=true",
        "complete historical x archive is available",
    ]
    doc_lower = doc_text.lower()
    found_doc = [phrase for phrase in forbidden_doc_phrases if phrase in doc_lower]
    if found_doc:
        report("FAIL", "proposal text boundary", "document implies forbidden state: " + ", ".join(found_doc))
    else:
        report("PASS", "proposal text boundary", "document does not imply authorized collection, MCP install, API call, or complete archive")


def main() -> int:
    validate_proposal()
    return 1 if FAILURES else 0


if __name__ == "__main__":
    sys.exit(main())
