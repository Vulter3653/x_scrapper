#!/usr/bin/env python3
"""Validate Fortune expansion governance readiness.

Static/local only: no secrets, network, scraping, SEC calls, or data mutation.
"""

from __future__ import annotations

import csv
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
FAILURES = 0
WARNINGS = 0

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
SCRAPE_ELIGIBLE_STATUSES = {"official", "brand_official"}
BLOCKED_STATUSES = ALLOWED_STATUSES - SCRAPE_ELIGIBLE_STATUSES
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


def read(path: str) -> str:
    return (REPO_ROOT / path).read_text(encoding="utf-8")


def require(path: str, needles: list[str], check: str) -> None:
    text = read(path)
    missing = [needle for needle in needles if needle not in text]
    if missing:
        row("FAIL", check, f"{path} missing: " + ", ".join(missing))
    else:
        row("PASS", check, f"{path} contains {len(needles)} required items")


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def is_true(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "y", "ready", "include", "included"}


def is_ready_file(path: Path) -> bool:
    lower = path.name.lower()
    return any(marker in lower for marker in READY_FILENAME_MARKERS)


def account_status_columns(fieldnames: list[str]) -> list[str]:
    lowered = {name.lower(): name for name in fieldnames}
    return [lowered[name] for name in ACCOUNT_STATUS_COLUMNS if name in lowered]


def validate_account_file(path: Path) -> None:
    if not path.exists():
        row("WARN", "account file", f"{rel(path)} not present; skipped")
        return

    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = reader.fieldnames or []
        status_cols = account_status_columns(fieldnames)
        ready_cols = [name for name in fieldnames if name.lower() in READY_MARKER_COLUMNS]
        rows = list(reader)

    if not status_cols:
        row("WARN", "account status column", f"{rel(path)} has no controlled account-status column; review before expansion")
        return

    unsupported: list[str] = []
    verified_values: list[str] = []
    blocked_ready: list[str] = []
    for index, record in enumerate(rows, start=2):
        for col in status_cols:
            value = (record.get(col) or "").strip()
            if not value:
                continue
            normalized = value.lower()
            if normalized == "verified":
                verified_values.append(f"line {index} column {col}")
            if normalized not in ALLOWED_STATUSES:
                unsupported.append(f"line {index} column {col}={value}")
            ready_by_file = is_ready_file(path)
            ready_by_column = any(is_true(record.get(col, "")) for col in ready_cols)
            if (ready_by_file or ready_by_column) and normalized in BLOCKED_STATUSES:
                blocked_ready.append(f"line {index} status={value}")

    if verified_values:
        row("FAIL", "uncontrolled status value", f"{rel(path)} uses verified as account status: " + "; ".join(verified_values[:10]))
    if unsupported:
        row("FAIL", "controlled taxonomy", f"{rel(path)} has unsupported account-status values: " + "; ".join(unsupported[:10]))
    else:
        row("PASS", "controlled taxonomy", f"{rel(path)} account-status values are controlled")

    if blocked_ready:
        row("FAIL", "scrape-ready eligibility", f"{rel(path)} treats non-eligible statuses as scrape-ready: " + "; ".join(blocked_ready[:10]))
    elif is_ready_file(path) or ready_cols:
        row("PASS", "scrape-ready eligibility", f"{rel(path)} has only eligible scrape-ready statuses")
    else:
        row("PASS", "pre-verification account file", f"{rel(path)} is not marked scrape-ready")


def discover_ready_files() -> list[Path]:
    candidates: set[Path] = set()
    for root in [REPO_ROOT / "config", REPO_ROOT / "docs"]:
        if not root.exists():
            continue
        for path in root.rglob("*.csv"):
            if is_ready_file(path):
                candidates.add(path)
    return sorted(candidates)


def main() -> int:
    for path in ["AGENT_RULES.md", "DATA_CLAIM_BOUNDARIES.md", "docs/operations/fortune_expansion_gatekeeping.md"]:
        if not (REPO_ROOT / path).exists():
            row("FAIL", "fortune governance file", f"missing {path}")
        else:
            row("PASS", "fortune governance file", f"found {path}")
    if FAILURES:
        return 1

    require("AGENT_RULES.md", sorted(ALLOWED_STATUSES), "controlled taxonomy in AGENT_RULES.md")
    require("DATA_CLAIM_BOUNDARIES.md", sorted(ALLOWED_STATUSES), "controlled taxonomy in DATA_CLAIM_BOUNDARIES.md")
    require("docs/operations/fortune_expansion_gatekeeping.md", sorted(ALLOWED_STATUSES), "controlled taxonomy in fortune gatekeeping")
    require("docs/operations/fortune_expansion_gatekeeping.md", ["No Fortune 500 scraping", "Top 100", "official-account verification"], "Fortune 500 gate claim")

    for path in KNOWN_ACCOUNT_FILES:
        validate_account_file(path)

    for path in discover_ready_files():
        if path not in KNOWN_ACCOUNT_FILES:
            validate_account_file(path)

    schema = REPO_ROOT / "config" / "schemas" / "fortune2025_x_account_verification_master.schema.json"
    if schema.exists():
        schema_text = schema.read_text(encoding="utf-8")
        missing = [status for status in sorted(ALLOWED_STATUSES) if status not in schema_text]
        if missing:
            row("WARN", "schema taxonomy", "schema enum not yet migrated for: " + ", ".join(missing))
        else:
            row("PASS", "schema taxonomy", "schema includes controlled taxonomy")
    else:
        row("WARN", "schema taxonomy", "schema file not found; root governance files still define taxonomy")

    return 1 if FAILURES else 0


if __name__ == "__main__":
    raise SystemExit(main())
