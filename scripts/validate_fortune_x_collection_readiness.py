#!/usr/bin/env python3
"""Validate the Fortune Top 100 X dry-run collection readiness policy.

Static/local only: no secrets, network calls, X scraping, X APIs, MCP install,
SEC downloads, workflow triggers, or data/dashboard mutation.
"""

from __future__ import annotations

import csv
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
QUEUE_FILE = REPO_ROOT / "config" / "fortune2025_top100_verified_x_collection_queue.csv"
POLICY_FILE = REPO_ROOT / "config" / "fortune2025_top100_x_collection_readiness_policy.csv"
SCHEMA_FILE = REPO_ROOT / "config" / "schemas" / "fortune2025_top100_x_collection_readiness_policy.schema.json"
QUEUE_VALIDATOR = REPO_ROOT / "scripts" / "validate_fortune_x_collection_queue.py"
DOC_FILE = REPO_ROOT / "docs" / "operations" / "fortune_top100_x_dry_run_collection_readiness_protocol.md"

REQUIRED_COLUMNS = [
    "policy_id", "queue_file", "eligible_account_count", "dry_run_only",
    "collection_authorized", "access_method", "mcp_required", "api_required",
    "browser_required", "rate_limit_policy", "max_posts_per_account",
    "date_window_policy", "retry_policy", "failure_status_values",
    "audit_log_required", "output_path_policy", "dashboard_sync_default",
    "data_mutation_allowed", "queue_source", "eligibility_source_field", "notes",
]

REQUIRED_AUDIT_FIELDS = [
    "fortune_rank", "company_name", "collection_x_handle", "collection_x_url",
    "collection_attempted_at", "collection_method", "collection_status",
    "posts_requested", "posts_collected", "earliest_post_date", "latest_post_date",
    "failure_reason", "rate_limit_observed", "auth_required", "raw_output_path",
    "processed_output_path", "dashboard_synced", "notes",
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


def validate_queue_validator() -> None:
    if not QUEUE_VALIDATOR.exists():
        report("FAIL", "queue validator", f"missing {rel(QUEUE_VALIDATOR)}")
        return
    result = subprocess.run([sys.executable, str(QUEUE_VALIDATOR)], cwd=REPO_ROOT, text=True, capture_output=True, check=False)
    if result.returncode != 0:
        detail = (result.stdout + result.stderr).strip().splitlines()[:8]
        report("FAIL", "queue validator", "queue validator failed: " + " | ".join(detail))
    else:
        report("PASS", "queue validator", "validated human-final source queue before readiness checks")


def validate_policy() -> None:
    files_ok = all(require_file(path) for path in [QUEUE_FILE, POLICY_FILE, SCHEMA_FILE, DOC_FILE])
    validate_queue_validator()
    if not files_ok:
        return

    queue_fields, queue_rows = read_csv(QUEUE_FILE)
    policy_fields, policy_rows = read_csv(POLICY_FILE)
    missing = [column for column in REQUIRED_COLUMNS if column not in policy_fields]
    if missing:
        report("FAIL", "required readiness policy columns", "missing: " + ", ".join(missing))
        return
    report("PASS", "required readiness policy columns", f"all {len(REQUIRED_COLUMNS)} required columns present")

    if len(policy_rows) != 1:
        report("FAIL", "policy row count", f"expected 1 policy row, found {len(policy_rows)}")
        return
    report("PASS", "policy row count", "one active dry-run readiness policy row")

    policy = {key: (value or "").strip() for key, value in policy_rows[0].items()}
    if len(queue_rows) != 100:
        report("FAIL", "queue row count", f"expected 100 queue rows, found {len(queue_rows)}")
    try:
        actual_count = int(policy["eligible_account_count"])
    except ValueError:
        report("FAIL", "eligible account count", f"not an integer: {policy['eligible_account_count']}")
        actual_count = -1
    if actual_count != 100 or actual_count != len(queue_rows):
        report("FAIL", "eligible account count", f"policy has {actual_count}, queue has {len(queue_rows)}, expected 100")
    else:
        report("PASS", "eligible account count", "policy matches human-final queue row count: 100")

    exact_expectations = {
        "queue_file": "config/fortune2025_top100_verified_x_collection_queue.csv",
        "dry_run_only": "true",
        "collection_authorized": "false",
        "data_mutation_allowed": "false",
        "dashboard_sync_default": "disabled",
        "output_path_policy": "no_output_until_collection_authorized",
        "audit_log_required": "true",
        "access_method": "to_be_decided",
        "mcp_required": "to_be_decided",
        "api_required": "to_be_decided",
        "browser_required": "to_be_decided",
        "queue_source": "human_final_manual_review",
        "eligibility_source_field": "final_manual_scrape_eligible",
    }
    for column, expected in exact_expectations.items():
        if policy[column] != expected:
            report("FAIL", column, f"expected {expected}, found {policy[column]}")
        else:
            report("PASS", column, f"{column}={expected}")

    for column in ["rate_limit_policy", "max_posts_per_account", "date_window_policy", "retry_policy"]:
        if policy[column] != "to_be_defined_before_collection":
            report("FAIL", column, f"expected to_be_defined_before_collection, found {policy[column]}")
        else:
            report("PASS", column, f"{column}=to_be_defined_before_collection")

    failure_values = {value.strip() for value in policy["failure_status_values"].split(",") if value.strip()}
    required_failure_values = {"blocked", "failed", "inaccessible", "rate_limited", "auth_required"}
    if failure_values != required_failure_values:
        report("FAIL", "failure status values", f"expected {sorted(required_failure_values)}, found {sorted(failure_values)}")
    else:
        report("PASS", "failure status values", "controlled future failure statuses are defined")

    combined = " ".join(policy.values()).lower()
    forbidden_authorization_phrases = [
        "collection_authorized=true", "scraping authorized", "scrape authorized",
        "mcp installed", "mcp_required=true", "api_required=true", "complete historical",
        "all historical x posts", "scrape_eligible is the final", "old scrape_eligible as final",
    ]
    found = [phrase for phrase in forbidden_authorization_phrases if phrase in combined]
    if found:
        report("FAIL", "readiness boundary wording", "policy implies forbidden state: " + ", ".join(found))
    else:
        report("PASS", "readiness boundary wording", "policy does not imply scraping, MCP, API, old eligibility, or complete historical coverage")

    doc_text = DOC_FILE.read_text(encoding="utf-8")
    required_doc_phrases = [
        "dry-run readiness protocol only", "does not authorize scraping",
        "does not authorize MCP installation", "does not authorize X API usage",
        "does not authorize dashboard sync", "does not authorize `data/` or `dashboard/data/` mutation",
        "limited to retrievable timeline posts", "No complete historical X coverage claim is allowed",
        "audit log", "explicit collection authorization commit", "final_manual_scrape_eligible",
        "human_final_manual_review", "100 accounts",
    ]
    missing_doc = [phrase for phrase in required_doc_phrases if phrase not in doc_text]
    if missing_doc:
        report("FAIL", "protocol boundary documentation", "missing: " + ", ".join(missing_doc))
    else:
        report("PASS", "protocol boundary documentation", "required dry-run boundaries documented")

    missing_audit = [field for field in REQUIRED_AUDIT_FIELDS if field not in doc_text]
    if missing_audit:
        report("FAIL", "future audit fields", "missing: " + ", ".join(missing_audit))
    else:
        report("PASS", "future audit fields", f"all {len(REQUIRED_AUDIT_FIELDS)} audit fields documented")


def main() -> int:
    validate_policy()
    return 1 if FAILURES else 0


if __name__ == "__main__":
    sys.exit(main())
