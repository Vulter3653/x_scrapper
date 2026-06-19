#!/usr/bin/env python3
"""Validate yearly humor backfill staging outputs.

This validator is intentionally structural. A smoke run can PASS with
success_count=0 when selected companies all record recoverable failures with the
expected schema, because the smoke objective is fast diagnostics rather than data
yield.
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
OUT_ROOT = REPO_ROOT / "data" / "backfill" / "yearly_humor"
GLOBAL_AUDIT = OUT_ROOT / "audit"

WORKFLOW_NEW = REPO_ROOT / ".github" / "workflows" / "backfill-humor-yearly-serial.yml"
WORKFLOW_OLD = REPO_ROOT / ".github" / "workflows" / "backfill-humor-collection-through-2021.yml"
BUILDER = REPO_ROOT / "scripts" / "build_yearly_humor_backfill_targets.py"
RUNNER = REPO_ROOT / "scripts" / "run_yearly_humor_backfill.py"

PROTECTED_DIRS = [REPO_ROOT / "data" / "raw", REPO_ROOT / "dashboard" / "data"]
FORBIDDEN_IN_STAGING = [
    "h1_regression", "h2_regression", "h3_regression", "h1_presence_classified",
    "integrated_h1_presence", "aggressive_detector", "type_classifier",
]

MIN_YEAR = 2009
MAX_YEAR = 2021
RECOMMENDED_FIRST_YEAR = 2009
RECOVERABLE_STATUSES = {
    "recoverable_failed_timeout",
    "recoverable_failed_company_timeout",
    "recoverable_failed_network",
    "recoverable_failed_browser",
    "recoverable_failed_render",
    "recoverable_failed_did_not_reach_year",
    "recoverable_failed_temporary_x_error",
}
TERMINAL_STATUSES = {
    "terminal_account_unavailable",
    "terminal_account_protected",
    "terminal_account_suspended",
    "terminal_created_after_year",
    "terminal_no_observable_posts_for_year",
}
RENDER_FAILURE_SUBTYPES = {
    "render_failure_login_or_auth",
    "render_failure_rate_limit_or_block",
    "render_failure_selector_missing",
    "render_failure_timeout",
    "render_failure_unknown",
}
SUMMARY_EXTENDED_FIELDS = {
    "smoke_mode", "full_target_company_count", "selected_company_count",
    "attempted_company_count", "input_max_scrolls", "effective_max_scrolls",
    "max_scrolls_cap_reason", "per_company_timeout_seconds",
    "total_elapsed_seconds", "median_company_elapsed_seconds",
    "max_company_elapsed_seconds", "timeout_count", "company_timeout_count",
    "render_failure_count", "render_failure_login_or_auth_count",
    "render_failure_rate_limit_or_block_count", "render_failure_selector_missing_count",
    "render_failure_timeout_count", "render_failure_unknown_count",
    "did_not_reach_year_count", "companies_with_raw_posts_count",
    "companies_with_zero_scroll_count", "min_seen_date_overall",
    "max_seen_date_overall", "median_scrolls_completed", "max_scrolls_completed",
}
RESULT_EXTENDED_FIELDS = {
    "smoke_mode", "full_target_company_count", "selected_company_count",
    "input_max_scrolls", "effective_max_scrolls", "max_scrolls_cap_reason",
    "per_company_timeout_seconds", "company_timeout_triggered", "failure_subtype",
    "elapsed_seconds", "stdout_tail_path", "stderr_tail_path", "combined_tail_path",
    "exit_status_path", "min_date_seen", "max_date_seen", "raw_collected",
}


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def to_int(value: object) -> int:
    try:
        return int(float(str(value or "0")))
    except (TypeError, ValueError):
        return 0


def is_true(value: object) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "y"}


def _chk(cond: bool, msg: str, errors: list[str]) -> None:
    if cond:
        print(f"  PASS: {msg}")
    else:
        errors.append(f"FAIL: {msg}")


def _warn(cond: bool, msg: str, warnings: list[str]) -> None:
    if cond:
        print(f"  OK:   {msg}")
    else:
        warnings.append(f"WARN: {msg}")


def validate_status_rows(year: int, rows: list[dict[str, str]], summary: dict[str, str], errors: list[str], warnings: list[str]) -> None:
    statuses = [r.get("status", "") for r in rows]
    known_bad = [s for s in statuses if s and s not in RECOVERABLE_STATUSES and s not in TERMINAL_STATUSES and s != "success"]
    _chk(not known_bad, f"year={year} statuses are known values (bad={known_bad[:3]})", errors)

    succ = sum(1 for s in statuses if s == "success")
    rec = sum(1 for r in rows if r.get("status", "") in RECOVERABLE_STATUSES or r.get("failure_subtype", "") in RENDER_FAILURE_SUBTYPES)
    term = sum(1 for s in statuses if s in TERMINAL_STATUSES)
    status_total = succ + rec + term
    selected = to_int(summary.get("selected_company_count") or summary.get("attempted_company_count"))
    attempted = to_int(summary.get("attempted_company_count"))

    _chk(status_total == len(rows), f"year={year} status count sum equals company result rows ({status_total}/{len(rows)})", errors)
    _chk(attempted == len(rows), f"year={year} attempted_company_count equals result rows ({attempted}/{len(rows)})", errors)
    if selected:
        _chk(attempted == selected, f"year={year} attempted_company_count equals selected_company_count ({attempted}/{selected})", errors)

    if is_true(summary.get("smoke_mode")):
        full = to_int(summary.get("full_target_company_count"))
        _chk(selected > 0, f"year={year} smoke selected_company_count is nonzero ({selected})", errors)
        _chk(selected <= full if full else True, f"year={year} smoke selected count can be below full target count ({selected}/{full})", errors)
        _chk(to_int(summary.get("effective_max_scrolls")) <= 300, f"year={year} smoke effective_max_scrolls <= 300", errors)
        _chk(to_int(summary.get("per_company_timeout_seconds")) in (0, 180) or to_int(summary.get("per_company_timeout_seconds")) <= 300,
             f"year={year} smoke timeout is short/explicit", errors)

    if succ == 0:
        warnings.append(f"WARN year={year}: success_count=0; acceptable for smoke/schema diagnostics but data quality remains failed")

    bad_failed = [r.get("status", "") for r in rows if r.get("status", "") in TERMINAL_STATUSES and r.get("failure_subtype", "") in RENDER_FAILURE_SUBTYPES]
    _chk(not bad_failed, f"year={year} terminal statuses are not marked as render retry failures", errors)


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate yearly humor backfill staging outputs.")
    parser.add_argument("--start-year", type=int, default=MIN_YEAR)
    parser.add_argument("--end-year", type=int, default=MAX_YEAR)
    parser.add_argument("--target-year", type=int, default=None)
    parser.add_argument("--allow-empty", action="store_true", help="Allow missing year outputs; validate scripts and workflow only.")
    parser.add_argument("--strict", action="store_true", help="Treat warnings as errors.")
    args = parser.parse_args()

    errors: list[str] = []
    warnings: list[str] = []
    years = [args.target_year] if args.target_year else list(range(args.start_year, args.end_year + 1))

    print("=== validate_yearly_humor_backfill_outputs ===")

    print("\n[1] Required scripts and workflow:")
    for path in (WORKFLOW_NEW, BUILDER, RUNNER):
        _chk(path.exists(), f"exists: {path.relative_to(REPO_ROOT)}", errors)
    _warn(WORKFLOW_OLD.exists(), f"old workflow preserved: {WORKFLOW_OLD.name}", warnings)

    print("\n[2] Workflow safety and smoke inputs:")
    if WORKFLOW_NEW.exists():
        text = WORKFLOW_NEW.read_text(encoding="utf-8")
        _chk("commit_results" in text, "workflow has commit_results input", errors)
        _chk("default: 'false'" in text or "default: false" in text, "commit_results default is false", errors)
        _chk("backfill-humor-yearly-serial" in text, "workflow concurrency group is distinct", errors)
        _chk("smoke" in text and "limit_companies" in text and "per_company_timeout_seconds" in text and "handles" in text,
             "workflow exposes smoke/limit/handles/time-limit inputs", errors)
        _warn("default: '1'" in text or "default: 1" in text, "max_parallel_companies default is 1", warnings)

    print("\n[3] Global year target summary:")
    summary_path = GLOBAL_AUDIT / "year_target_summary.csv"
    global_srows = read_csv(summary_path)
    if global_srows:
        covered = {to_int(r.get("target_year")) for r in global_srows if to_int(r.get("target_year"))}
        _warn(all(y in covered for y in years), f"all requested years covered (covered={sorted(covered)})", warnings)
        total_rec = sum(to_int(r.get("recoverable_failure_count")) for r in global_srows)
        print(f"  INFO: total_recoverable={total_rec}")
    elif args.allow_empty:
        print("  SKIP: year_target_summary.csv not yet present (--allow-empty)")
    else:
        errors.append("FAIL: year_target_summary.csv not found")

    print("\n[4] Per-year audit structure:")
    for year in years:
        year_dir = OUT_ROOT / str(year)
        audit_dir = year_dir / "audit"
        if not year_dir.exists():
            if args.allow_empty:
                print(f"  SKIP year={year}: not yet present (--allow-empty)")
                continue
            errors.append(f"FAIL: year={year} directory missing")
            continue

        target_csv = audit_dir / f"year_{year}_target_companies.csv"
        summary_csv = audit_dir / f"year_{year}_summary.csv"
        failed_csv = audit_dir / f"year_{year}_failed_targets.csv"
        terminal_csv = audit_dir / f"year_{year}_terminal_targets.csv"

        _chk(target_csv.exists(), f"year={year} target_companies.csv exists", errors)
        target_rows = read_csv(target_csv)
        summary_rows = read_csv(summary_csv)
        if summary_rows:
            _chk(len(summary_rows) == 1, f"year={year} summary has exactly 1 row", errors)
            summary = summary_rows[0]
            base_fields = {"target_year", "success_count", "recoverable_failure_count", "terminal_status_count", "posts_collected", "retry_round", "completed_at"}
            missing_base = base_fields - set(summary)
            _chk(not missing_base, f"year={year} summary has base fields (missing={missing_base})", errors)
            missing_ext = SUMMARY_EXTENDED_FIELDS - set(summary)
            if is_true(summary.get("smoke_mode")):
                _chk(not missing_ext, f"year={year} smoke summary has extended fields (missing={missing_ext})", errors)
            elif missing_ext:
                warnings.append(f"WARN year={year}: summary lacks new smoke diagnostic fields; old artifact schema")
            validate_status_rows(year, target_rows, summary, errors, warnings)
        elif args.allow_empty:
            print(f"  SKIP year={year} summary: not yet present (--allow-empty)")
        else:
            errors.append(f"FAIL: year={year} summary CSV missing")

        if target_rows:
            missing_result_ext = RESULT_EXTENDED_FIELDS - set(target_rows[0])
            if any(is_true(r.get("smoke_mode")) for r in target_rows):
                _chk(not missing_result_ext, f"year={year} smoke result rows have extended fields (missing={missing_result_ext})", errors)
            elif missing_result_ext:
                warnings.append(f"WARN year={year}: result rows lack new company diagnostic fields; old artifact schema")

        failed_rows = read_csv(failed_csv)
        if failed_rows:
            bad = [r.get("status", "") for r in failed_rows if r.get("status", "") not in RECOVERABLE_STATUSES and not r.get("status", "").startswith("recoverable_failed_")]
            _chk(not bad, f"year={year} failed_targets.csv contains only recoverable statuses (bad={bad[:3]})", errors)

        terminal_rows = read_csv(terminal_csv)
        if terminal_rows:
            bad_t = [r.get("status", "") for r in terminal_rows if not r.get("status", "").startswith("terminal_")]
            _chk(not bad_t, f"year={year} terminal_targets.csv contains only terminal statuses (bad={bad_t[:3]})", errors)
            unsupported_rows = [r for r in terminal_rows if r.get("status") == "terminal_created_after_year" and not str(r.get("account_created_year", "")).strip()]
            _chk(not unsupported_rows, f"year={year} terminal_created_after_year has account_created_year evidence", errors)

    print("\n[5] Old-year-first execution guidance check:")
    if not args.allow_empty and years:
        first_year = min(years)
        _warn(first_year == RECOMMENDED_FIRST_YEAR, f"start_year={first_year} matches recommended first year ({RECOMMENDED_FIRST_YEAR})", warnings)

    print("\n[6] Protected paths not modified by this validator:")
    for path in PROTECTED_DIRS:
        status = "exists" if path.exists() else "absent"
        print(f"  INFO: {path.relative_to(REPO_ROOT)} ({status}) — not touched by validator")

    print("\n[7] No classifier/regression outputs in backfill staging:")
    if OUT_ROOT.exists():
        staging_files = [f for f in OUT_ROOT.rglob("*") if f.is_file()]
        forbidden = [f for f in staging_files if any(pat in f.name for pat in FORBIDDEN_IN_STAGING)]
        _chk(not forbidden, f"no classifier/regression outputs in staging (found={[str(f) for f in forbidden[:3]]})", errors)

    print("\n" + "=" * 60)
    if args.strict and warnings:
        errors.extend(warnings)
        warnings = []
    if errors:
        print(f"VALIDATION RESULT: FAIL ({len(errors)} errors, {len(warnings)} warnings)")
        for e in errors:
            print(f"  {e}")
        for w in warnings:
            print(f"  {w}")
        return 1
    print(f"VALIDATION RESULT: PASS ({len(warnings)} warnings)")
    for w in warnings:
        print(f"  {w}")
    print("=== validate_yearly_humor_backfill_outputs COMPLETE ===")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
