#!/usr/bin/env python3
"""Validate the human manual review overlay for Fortune Top 100 X account verification.

Static/local only: no secrets, network calls, scraping, SEC calls, workflow triggers,
or data/dashboard mutation.
"""

from __future__ import annotations

import csv
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
MASTER_FILE = REPO_ROOT / "config" / "fortune2025_x_account_verification_master.csv"
READINESS_FILE = REPO_ROOT / "config" / "fortune2025_top100_x_collection_readiness_policy.csv"
PROPOSAL_FILE = REPO_ROOT / "config" / "fortune2025_top100_x_collection_authorization_proposal.csv"
DOC_FILES = [
    REPO_ROOT / "README.md",
    REPO_ROOT / "docs" / "operations" / "fortune_top100_x_account_verification_protocol.md",
    REPO_ROOT / "PROJECT_HISTORY.md",
    REPO_ROOT / "TROUBLESHOOTING_AND_DEBUGGING_LOG.md",
]

ORIGINAL_COLUMNS = [
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
HUMAN_COLUMNS = [
    "human_candidate_is_actual_official",
    "human_actual_x_url_1",
    "human_actual_x_url_2",
    "human_review_status",
    "human_review_batch",
    "final_manual_x_url_primary",
    "final_manual_x_url_secondary",
    "final_manual_account_status",
    "final_manual_scrape_eligible",
]
# Updated to support all batches up to 100
REVIEW_BATCHES = [
    "manual_top20_batch_2026_06_12",
    "manual_rank21_40_batch_2026_06_12",
    "manual_rank41_100_batch_2026_06_12"
]
ALLOWED_HUMAN_VALUES = {"", "0", "1"}
REQUIRED_HUMAN_DOC_PHRASES = [
    "human manual review layer",
    "final_manual_scrape_eligible",
    "preliminary/reference evidence",
    "Ranks 1-100 are `human_reviewed`",
    "Pending human review count is 0",
    "existing `scrape_eligible` must not be treated as final",
]
FORBIDDEN_DOC_PHRASES = [
    "collection has started",
    "scraping has started",
    "mcp has been installed",
    "x api was called",
    "x api has been called",
    "complete historical x coverage is available",
    "complete historical x archive is available",
    "full historical x archive is available",
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


def check_git_status() -> bool:
    result = subprocess.run(
        ["git", "status", "--short", "data", "dashboard/data"],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.stdout.strip():
        report("FAIL", "data/dashboard mutation", "working tree changed under data/ or dashboard/data/\n" + result.stdout.strip())
        return False
    report("PASS", "data/dashboard mutation", "no changes under data/ or dashboard/data/")
    return True


def check_boundary_files() -> bool:
    ok = True
    for path in [READINESS_FILE, PROPOSAL_FILE]:
        if not path.exists():
            report("FAIL", "boundary file", f"missing {rel(path)}")
            ok = False
            continue
        fields, rows = read_csv(path)
        if not rows:
            report("FAIL", "boundary file", f"empty {rel(path)}")
            ok = False
            continue
        row = rows[0]
        if row.get("collection_authorized", "").strip().lower() != "false":
            report("FAIL", "collection authorization boundary", f"{rel(path)} has collection_authorized={row.get('collection_authorized', '')}")
            ok = False
        if row.get("dry_run_only", "").strip().lower() != "true":
            report("FAIL", "dry run boundary", f"{rel(path)} has dry_run_only={row.get('dry_run_only', '')}")
            ok = False
    if ok:
        report("PASS", "boundary files", "readiness and proposal boundaries remain disabled for collection")
    return ok


def check_docs() -> None:
    for path in DOC_FILES:
        if not path.exists():
            report("FAIL", "required doc", f"missing {rel(path)}")
            continue
        text = path.read_text(encoding="utf-8").lower()
        for phrase in FORBIDDEN_DOC_PHRASES:
            if phrase in text:
                report("FAIL", "documentation boundary", f"{rel(path)} implies forbidden state via phrase: {phrase}")
        if path.name == "fortune_top100_x_account_verification_protocol.md":
            required = [
                "final_manual_scrape_eligible",
                "human manual review layer",
                "existing `scrape_eligible` must not be treated as final",
            ]
            missing = [phrase for phrase in required if phrase not in text]
            if missing:
                report("FAIL", "human review documentation", f"{rel(path)} missing: " + ", ".join(missing))
            else:
                report("PASS", "human review documentation", f"{rel(path)} documents the human-review overlay")
        if path.name == "README.md":
            required = [
                "final_manual_scrape_eligible",
                "human manual review layer",
                "existing `scrape_eligible` is no longer the final eligibility signal",
            ]
            missing = [phrase for phrase in required if phrase not in text]
            if missing:
                report("FAIL", "README human review documentation", f"{rel(path)} missing: " + ", ".join(missing))
            else:
                report("PASS", "README human review documentation", f"{rel(path)} documents the human-review overlay")


def main() -> int:
    if not require_file(MASTER_FILE):
        return 1
    check_git_status()
    check_boundary_files()
    check_docs()

    fieldnames, rows = read_csv(MASTER_FILE)
    if len(rows) != 100:
        report("FAIL", "row count", f"expected 100 data rows, found {len(rows)}")
    else:
        report("PASS", "row count", "master contains exactly 100 data rows")

    missing_original = [col for col in ORIGINAL_COLUMNS if col not in fieldnames]
    if missing_original:
        report("FAIL", "original columns", "missing: " + ", ".join(missing_original))
    else:
        report("PASS", "original columns", f"all {len(ORIGINAL_COLUMNS)} original columns present")

    missing_human = [col for col in HUMAN_COLUMNS if col not in fieldnames]
    if missing_human:
        report("FAIL", "human review columns", "missing: " + ", ".join(missing_human))
    else:
        report("PASS", "human review columns", f"all {len(HUMAN_COLUMNS)} human-review columns present")

    ranks = []
    reviewed_rows = 0
    pending_rows = 0
    confirmed_candidate_official = 0
    rejected_with_alternate = 0
    final_eligible_rows = 0

    for index, row in enumerate(rows, start=2):
        prefix = f"line {index} rank={row.get('fortune_rank', '').strip()}"
        try:
            rank = int(row.get("fortune_rank", ""))
        except ValueError:
            report("FAIL", "fortune_rank", f"{prefix} is not an integer")
            continue
        ranks.append(rank)
        if rank < 1 or rank > 100:
            report("FAIL", "fortune_rank range", f"{prefix} outside 1-100")

        human_status = row.get("human_review_status", "").strip()
        human_batch = row.get("human_review_batch", "").strip()
        human_candidate = row.get("human_candidate_is_actual_official", "").strip()
        actual_1 = row.get("human_actual_x_url_1", "").strip()
        actual_2 = row.get("human_actual_x_url_2", "").strip()
        final_primary = row.get("final_manual_x_url_primary", "").strip()
        final_secondary = row.get("final_manual_x_url_secondary", "").strip()
        final_status = row.get("final_manual_account_status", "").strip()
        final_eligible = row.get("final_manual_scrape_eligible", "").strip().lower()
        candidate_url = row.get("candidate_x_url", "").strip()

        if human_candidate not in ALLOWED_HUMAN_VALUES:
            report("FAIL", "human candidate taxonomy", f"{prefix} invalid human_candidate_is_actual_official={human_candidate}")

        if human_status == "human_reviewed":
            reviewed_rows += 1
            if human_candidate == "":
                report("FAIL", "human review coverage", f"{prefix} reviewed row has blank human_candidate_is_actual_official")
            if human_batch not in REVIEW_BATCHES:
                report("FAIL", "human review batch", f"{prefix} reviewed row has unknown batch {human_batch}")

            if human_candidate == "1":
                confirmed_candidate_official += 1
                if final_primary != candidate_url:
                    report("FAIL", "final primary mapping", f"{prefix} candidate=1 but final_manual_x_url_primary differs from candidate_x_url")
                if actual_1:
                    report("FAIL", "human alternate URLs", f"{prefix} candidate=1 should not have human_actual_x_url_1")
                if final_status != "confirmed_candidate_official":
                    report("FAIL", "final account status", f"{prefix} expected confirmed_candidate_official, found {final_status}")
                # Secondary URL is allowed for confirmed candidates (Rule 7)
                if actual_2 and final_secondary != actual_2:
                    report("FAIL", "final secondary mapping", f"{prefix} candidate=1 but final_manual_x_url_secondary does not match human_actual_x_url_2")
            elif human_candidate == "0":
                if not actual_1:
                    report("FAIL", "human alternate URL", f"{prefix} candidate=0 requires human_actual_x_url_1")
                else:
                    rejected_with_alternate += 1
                    if final_primary != actual_1:
                        report("FAIL", "final primary mapping", f"{prefix} candidate=0 but final_manual_x_url_primary does not match human_actual_x_url_1")
                    expected_status = "candidate_rejected_alternate_found"
                    if final_status != expected_status:
                        report("FAIL", "final account status", f"{prefix} expected {expected_status}, found {final_status}")
                    if actual_2 and final_secondary != actual_2:
                        report("FAIL", "final secondary mapping", f"{prefix} candidate=0 but final_manual_x_url_secondary does not match human_actual_x_url_2")
                    if not actual_2 and final_secondary:
                        report("FAIL", "final secondary mapping", f"{prefix} final_manual_x_url_secondary must be blank when no second alternate is provided")
            else:
                report("FAIL", "human review candidate flag", f"{prefix} reviewed row must have human_candidate_is_actual_official=0 or 1")

            if final_eligible != "true":
                report("FAIL", "final eligibility", f"{prefix} reviewed row must have final_manual_scrape_eligible=true")
            if not final_primary:
                report("FAIL", "final eligibility url", f"{prefix} reviewed row must have nonblank final_manual_x_url_primary")
            final_eligible_rows += 1

        elif human_status == "pending_human_review":
            pending_rows += 1
            # Final state check: no pending rows allowed
            report("FAIL", "final pending check", f"{prefix} remains pending_human_review")
        else:
            report("FAIL", "human review status", f"{prefix} invalid human_review_status={human_status}")

    if sorted(ranks) != list(range(1, 101)):
        missing = sorted(set(range(1, 101)) - set(ranks))
        extra = sorted(set(ranks) - set(range(1, 101)))
        report("FAIL", "fortune_rank completeness", f"missing={missing[:10]} extra={extra[:10]}")
    else:
        report("PASS", "fortune_rank completeness", "fortune_rank is unique and complete from 1 to 100")

    if reviewed_rows != 100:
        report("FAIL", "human reviewed count", f"expected 100 reviewed rows, found {reviewed_rows}")
    else:
        report("PASS", "human reviewed count", "100 rows are human reviewed")

    if pending_rows != 0:
        report("FAIL", "pending human review count", f"expected 0 pending rows, found {pending_rows}")
    else:
        report("PASS", "pending human review count", "0 rows remain pending human review")

    report("PASS", "confirmed official count", f"{confirmed_candidate_official} candidate rows are confirmed official")
    report("PASS", "alternate found count", f"{rejected_with_alternate} candidate rows were rejected with alternates found")

    if final_eligible_rows != 100:
        report("FAIL", "final eligibility count", f"expected 100, found {final_eligible_rows}")
    else:
        report("PASS", "final eligibility count", "100 rows are final manual scrape eligible")

    if FAILURES == 0:
        report("PASS", "master human review overlay", "validated all 100 rows as complete")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    sys.exit(main())
