#!/usr/bin/env python3
"""Validate Fortune Top 100 X account verification readiness.

Static/local only: no secrets, network, scraping, SEC calls, or data mutation.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
FAILURES = 0
WARNINGS = 0

MASTER_FILE = REPO_ROOT / "config" / "fortune2025_x_account_verification_master.csv"
SCHEMA_FILE = REPO_ROOT / "config" / "schemas" / "fortune2025_x_account_verification_master.schema.json"

REQUIRED_MASTER_COLUMNS = [
    "fortune_rank",
    "company_name",
    "normalized_company_name",
    "candidate_x_handle",
    "candidate_x_url",
    "official_x_handle",
    "official_x_url",
    "official_x_account_status",
    "evidence_source_url",
    "evidence_source_type",
    "evidence_strength",
    "confidence",
    "reviewer",
    "review_date",
    "scrape_eligible",
    "manual_verification_required",
    "notes",
]

ALLOWED_STATUSES = {
    "unknown",
    "official",
    "brand_official",
    "subsidiary_only",
    "ambiguous",
    "no_account_found",
    "inaccessible",
    "do_not_scrape",
}
UNCONTROLLED_STATUS_VALUES = {"verified", "valid", "confirmed", "approved"}
EVIDENCE_SOURCE_TYPES = {
    "corporate_footer",
    "newsroom",
    "investor_relations",
    "press_page",
    "contact_page",
    "social_directory",
    "x_profile_backlink",
    "cross_platform_official",
    "manual_search_only",
    "not_found",
    "inaccessible",
}
EVIDENCE_STRENGTHS = {"level_1", "level_2", "level_3", "level_4", "level_5", "level_6", "level_7", "level_8", "none"}
CONFIDENCE_VALUES = {"high", "medium", "low", "blocked"}
SCRAPE_ELIGIBLE_STATUSES = {"official", "brand_official"}
SCRAPE_ELIGIBLE_CONFIDENCE = {"high", "medium"}
MANUAL_REQUIRED_TRUE = {"official", "brand_official", "subsidiary_only", "ambiguous", "do_not_scrape"}
MANUAL_REQUIRED_FALSE = {"unknown", "no_account_found", "inaccessible"}
ACCOUNT_STATUS_COLUMNS = {
    "official_x_account_status",
    "account_status",
    "x_account_status",
    "official_account_status",
    "review_status",
}
READY_MARKER_COLUMNS = {
    "scrape_ready",
    "ready_to_scrape",
    "expansion_ready",
    "collection_ready",
    "include_in_scrape_queue",
    "scrape_eligible",
}
READY_FILENAME_MARKERS = (
    "scrape_ready",
    "scrape-ready",
    "scrape_queue",
    "scrape-queue",
    "expansion_ready",
    "expansion-ready",
    "collection_ready",
    "collection-ready",
)
KNOWN_ACCOUNT_FILES = [
    REPO_ROOT / "config" / "fortune2025_top100_x_account_index.csv",
    REPO_ROOT / "config" / "fortune2025" / "fortune2025_top100_x_account_index.csv",
]


def row(status: str, check: str, detail: str) -> None:
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


def read(path: str) -> str:
    return (REPO_ROOT / path).read_text(encoding="utf-8")


def require_text(path: str, needles: list[str], check: str) -> None:
    text = read(path)
    missing = [needle for needle in needles if needle not in text]
    if missing:
        row("FAIL", check, f"{path} missing: " + ", ".join(missing))
    else:
        row("PASS", check, f"{path} contains {len(needles)} required items")


def is_true(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "y", "ready", "include", "included"}


def is_false(value: str) -> bool:
    return value.strip().lower() in {"0", "false", "no", "n", "", "blocked", "exclude", "excluded"}


def is_ready_file(path: Path) -> bool:
    lower = path.name.lower()
    return any(marker in lower for marker in READY_FILENAME_MARKERS)


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return reader.fieldnames or [], list(reader)


def account_status_columns(fieldnames: list[str]) -> list[str]:
    lowered = {name.lower(): name for name in fieldnames}
    return [lowered[name] for name in ACCOUNT_STATUS_COLUMNS if name in lowered]


def ready_columns(fieldnames: list[str]) -> list[str]:
    return [name for name in fieldnames if name.lower() in READY_MARKER_COLUMNS]


def validate_status_values(path: Path, fieldnames: list[str], records: list[dict[str, str]]) -> None:
    status_cols = account_status_columns(fieldnames)
    ready_cols = ready_columns(fieldnames)
    if not status_cols:
        row("WARN", "account status column", f"{rel(path)} has no controlled account-status column; review before expansion")
        return

    unsupported: list[str] = []
    uncontrolled: list[str] = []
    blocked_ready: list[str] = []
    for index, record in enumerate(records, start=2):
        ready = is_ready_file(path) or any(is_true(record.get(col, "")) for col in ready_cols)
        for col in status_cols:
            value = (record.get(col) or "").strip().lower()
            if not value:
                continue
            if value in UNCONTROLLED_STATUS_VALUES:
                uncontrolled.append(f"line {index} column {col}={value}")
            if value not in ALLOWED_STATUSES:
                unsupported.append(f"line {index} column {col}={value}")
            if ready and value not in SCRAPE_ELIGIBLE_STATUSES:
                blocked_ready.append(f"line {index} status={value}")

    if uncontrolled:
        row("FAIL", "uncontrolled account-status label", f"{rel(path)}: " + "; ".join(uncontrolled[:10]))
    if unsupported:
        row("FAIL", "controlled account-status taxonomy", f"{rel(path)}: " + "; ".join(unsupported[:10]))
    else:
        row("PASS", "controlled account-status taxonomy", f"{rel(path)} account-status values are controlled")

    if blocked_ready:
        row("FAIL", "scrape-ready status gate", f"{rel(path)} includes non-eligible statuses as scrape-ready: " + "; ".join(blocked_ready[:10]))
    elif is_ready_file(path) or ready_cols:
        row("PASS", "scrape-ready status gate", f"{rel(path)} has no non-eligible scrape-ready statuses")
    else:
        row("PASS", "pre-verification account file", f"{rel(path)} is not marked scrape-ready")


def validate_master_file() -> None:
    if not MASTER_FILE.exists():
        row("FAIL", "verification master", f"missing {rel(MASTER_FILE)}")
        return
    fieldnames, records = read_csv(MASTER_FILE)
    missing = [col for col in REQUIRED_MASTER_COLUMNS if col not in fieldnames]
    if missing:
        row("FAIL", "master required columns", "missing: " + ", ".join(missing))
        return
    row("PASS", "master required columns", f"all {len(REQUIRED_MASTER_COLUMNS)} required columns present")

    validate_status_values(MASTER_FILE, fieldnames, records)

    for index, record in enumerate(records, start=2):
        status = record["official_x_account_status"].strip().lower()
        evidence_type = record["evidence_source_type"].strip().lower()
        evidence_strength = record["evidence_strength"].strip().lower()
        confidence = record["confidence"].strip().lower()
        official_url = record["official_x_url"].strip()
        evidence_url = record["evidence_source_url"].strip()
        notes = record["notes"].strip()
        scrape_eligible = is_true(record["scrape_eligible"])
        manual_value = record["manual_verification_required"].strip().lower()

        prefix = f"line {index} rank={record.get('fortune_rank', '')}"
        if evidence_type not in EVIDENCE_SOURCE_TYPES:
            row("FAIL", "evidence_source_type taxonomy", f"{prefix} unsupported value {evidence_type}")
        if evidence_strength not in EVIDENCE_STRENGTHS:
            row("FAIL", "evidence_strength taxonomy", f"{prefix} unsupported value {evidence_strength}")
        if confidence not in CONFIDENCE_VALUES:
            row("FAIL", "confidence taxonomy", f"{prefix} unsupported value {confidence}")
        if status in SCRAPE_ELIGIBLE_STATUSES and not evidence_url:
            row("FAIL", "official evidence URL", f"{prefix} {status} requires evidence_source_url")
        if status in SCRAPE_ELIGIBLE_STATUSES and not official_url:
            row("FAIL", "official X URL", f"{prefix} {status} requires official_x_url")
        if status == "brand_official" and not notes:
            row("FAIL", "brand_official notes", f"{prefix} brand_official requires notes")
        if scrape_eligible and status not in SCRAPE_ELIGIBLE_STATUSES:
            row("FAIL", "scrape eligibility status", f"{prefix} scrape_eligible=true with status={status}")
        if scrape_eligible and confidence not in SCRAPE_ELIGIBLE_CONFIDENCE:
            row("FAIL", "scrape eligibility confidence", f"{prefix} scrape_eligible=true with confidence={confidence}")
        if scrape_eligible and (not evidence_url or not official_url):
            row("FAIL", "scrape eligibility evidence", f"{prefix} scrape_eligible=true without evidence_source_url and official_x_url")
        if confidence == "low" and scrape_eligible:
            row("FAIL", "low confidence scrape gate", f"{prefix} confidence=low cannot be scrape_eligible")
        expected_manual = "true" if status in MANUAL_REQUIRED_TRUE else "false" if status in MANUAL_REQUIRED_FALSE else None
        if expected_manual is not None and manual_value != expected_manual:
            row("FAIL", "manual verification rule", f"{prefix} status={status} requires manual_verification_required={expected_manual}")
        if manual_value not in {"true", "false"}:
            row("FAIL", "manual verification boolean", f"{prefix} manual_verification_required must be true or false")
        if record["scrape_eligible"].strip().lower() not in {"true", "false"}:
            row("FAIL", "scrape eligibility boolean", f"{prefix} scrape_eligible must be true or false")

        if confidence == "low":
            row("WARN", "low confidence", f"{prefix} confidence=low")
        if evidence_type == "manual_search_only":
            row("WARN", "manual search only", f"{prefix} evidence_source_type=manual_search_only")
        if not record["candidate_x_handle"].strip():
            row("WARN", "candidate handle", f"{prefix} candidate_x_handle is empty")
        if official_url and status == "inaccessible":
            row("WARN", "inaccessible official URL", f"{prefix} official_x_url present while status=inaccessible")
        if evidence_strength in {"level_6", "level_7", "level_8"}:
            row("WARN", "weak evidence strength", f"{prefix} evidence_strength={evidence_strength}")
        if status in {"ambiguous", "subsidiary_only", "no_account_found"}:
            row("WARN", "review status", f"{prefix} status={status}")

    if FAILURES == 0:
        row("PASS", "verification master rows", f"validated {len(records)} rows")


def validate_schema() -> None:
    if not SCHEMA_FILE.exists():
        row("FAIL", "schema file", f"missing {rel(SCHEMA_FILE)}")
        return
    payload = json.loads(SCHEMA_FILE.read_text(encoding="utf-8"))
    props = payload.get("properties", {})
    checks = {
        "official_x_account_status": ALLOWED_STATUSES,
        "evidence_source_type": EVIDENCE_SOURCE_TYPES,
        "evidence_strength": EVIDENCE_STRENGTHS,
        "confidence": CONFIDENCE_VALUES,
    }
    for field, allowed in checks.items():
        enum = set(props.get(field, {}).get("enum", []))
        if enum != allowed:
            row("FAIL", "schema enum", f"{field} enum mismatch: expected {sorted(allowed)}, found {sorted(enum)}")
        else:
            row("PASS", "schema enum", f"{field} enum matches controlled taxonomy")
    required = payload.get("required", [])
    missing = [col for col in REQUIRED_MASTER_COLUMNS if col not in required]
    if missing:
        row("FAIL", "schema required columns", "missing: " + ", ".join(missing))
    else:
        row("PASS", "schema required columns", f"all {len(REQUIRED_MASTER_COLUMNS)} master columns required")


def discover_ready_files() -> list[Path]:
    candidates: set[Path] = set()
    for root in [REPO_ROOT / "config", REPO_ROOT / "docs"]:
        if not root.exists():
            continue
        for path in root.rglob("*.csv"):
            if path == MASTER_FILE:
                continue
            if is_ready_file(path):
                candidates.add(path)
    return sorted(candidates)


def validate_known_account_files() -> None:
    for path in KNOWN_ACCOUNT_FILES:
        if not path.exists():
            row("WARN", "known account file", f"{rel(path)} not present; skipped")
            continue
        fieldnames, records = read_csv(path)
        validate_status_values(path, fieldnames, records)
    for path in discover_ready_files():
        fieldnames, records = read_csv(path)
        validate_status_values(path, fieldnames, records)


def validate_docs() -> None:
    required_docs = {
        "AGENT_RULES.md": ["No Fortune 500 scraping before Top 100 official-account verification protocol is validated"],
        "DATA_CLAIM_BOUNDARIES.md": ["SEC 10-K Collection Failure Boundary", "not evidence of usable 10-K corpus"],
        "docs/operations/fortune_expansion_gatekeeping.md": ["No Fortune 500 scraping", "Top 100", "official-account verification"],
        "docs/operations/fortune_top100_x_account_verification_protocol.md": ["account verification only", "Search-result-only evidence is insufficient", "Level 8", "never scrape-eligible"],
    }
    for path, needles in required_docs.items():
        if not (REPO_ROOT / path).exists():
            row("FAIL", "required governance doc", f"missing {path}")
            continue
        require_text(path, needles, f"required governance doc: {path}")


def main() -> int:
    validate_docs()
    validate_schema()
    validate_master_file()
    validate_known_account_files()
    return 1 if FAILURES else 0


if __name__ == "__main__":
    raise SystemExit(main())
