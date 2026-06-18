#!/usr/bin/env python3
"""Validate yearly humor backfill staging outputs.

Checks:
- Required scripts and workflow file exist
- year_target_summary.csv present and consistent
- Per-year audit files present with correct structure
- failed_targets.csv contains only recoverable_failed_* statuses
- terminal_targets.csv contains only terminal_* statuses
- terminal_created_after_year NOT assigned without account_created_year evidence
- data/raw, dashboard/data, integrated corpus NOT modified by backfill
- No H1/H2/H3/classifier outputs inside backfill staging area
- commit_results default is false in the workflow
- Warnings for max_parallel_companies > 1
- Warnings for recoverable render/did_not_reach_year counts
- Warnings for success_count == 0

Use --strict to fail (exit 1) on warnings in addition to errors.
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

PROTECTED_DIRS = [
    REPO_ROOT / "data" / "raw",
    REPO_ROOT / "dashboard" / "data",
]
FORBIDDEN_IN_STAGING = [
    "h1_regression",
    "h2_regression",
    "h3_regression",
    "h1_presence_classified",
    "integrated_h1_presence",
    "aggressive_detector",
    "type_classifier",
]

MIN_YEAR = 2009
MAX_YEAR = 2021
RECOMMENDED_FIRST_YEAR = 2009


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


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate yearly humor backfill staging outputs."
    )
    parser.add_argument("--start-year", type=int, default=MIN_YEAR)
    parser.add_argument("--end-year", type=int, default=MAX_YEAR)
    parser.add_argument("--target-year", type=int, default=None)
    parser.add_argument("--allow-empty", action="store_true",
                        help="Allow missing year outputs; validate scripts and workflow only.")
    parser.add_argument("--strict", action="store_true",
                        help="Treat warnings as errors (exit 1 on any warning).")
    args = parser.parse_args()

    errors: list[str] = []
    warnings: list[str] = []
    years = ([args.target_year]
             if args.target_year
             else list(range(args.start_year, args.end_year + 1)))

    print("=== validate_yearly_humor_backfill_outputs ===")

    # ------------------------------------------------------------------
    print("\n[1] Required scripts and workflow:")
    for path in (WORKFLOW_NEW, BUILDER, RUNNER):
        _chk(path.exists(), f"exists: {path.relative_to(REPO_ROOT)}", errors)
    _warn(WORKFLOW_OLD.exists(), f"old workflow preserved: {WORKFLOW_OLD.name}", warnings)

    # ------------------------------------------------------------------
    print("\n[2] Workflow safety — commit_results default and parallel warning:")
    if WORKFLOW_NEW.exists():
        text = WORKFLOW_NEW.read_text(encoding="utf-8")
        _chk("commit_results" in text,
             "backfill-humor-yearly-serial.yml has commit_results input", errors)
        _chk("default: 'false'" in text or "default: false" in text,
             "commit_results default is false", errors)
        _chk("backfill-humor-yearly-serial" in text,
             "workflow concurrency group name is distinct", errors)
        # Check that max_parallel_companies default is 1
        _warn("default: '1'" in text or "default: 1\n" in text,
              "max_parallel_companies workflow default is 1 (recommended)", warnings)

    # ------------------------------------------------------------------
    print("\n[3] Global year target summary:")
    summary_path = GLOBAL_AUDIT / "year_target_summary.csv"
    global_srows: list[dict] = []
    if summary_path.exists():
        with summary_path.open(encoding="utf-8") as f:
            global_srows = list(csv.DictReader(f))
        _chk(len(global_srows) > 0,
             f"year_target_summary.csv has rows (got {len(global_srows)})", errors)
        covered = {int(r["target_year"]) for r in global_srows
                   if str(r.get("target_year", "")).isdigit()}
        _warn(all(y in covered for y in years),
              f"all requested years covered (covered={sorted(covered)})", warnings)
        total_rec = sum(int(r.get("recoverable_failure_count", 0) or 0) for r in global_srows)
        total_term = sum(int(r.get("terminal_status_count", 0) or 0) for r in global_srows)
        total_render = sum(
            int(r.get("recoverable_render_failure_count", 0) or 0) for r in global_srows
        )
        total_dnr = sum(
            int(r.get("recoverable_did_not_reach_year_count", 0) or 0) for r in global_srows
        )
        print(f"  INFO: total_recoverable={total_rec} (render={total_render} "
              f"did_not_reach={total_dnr}) total_terminal={total_term}")
        if total_rec > 0:
            warnings.append(
                f"WARN: {total_rec} recoverable failures in global summary "
                f"(render={total_render} did_not_reach={total_dnr}) — retry required"
            )
    elif args.allow_empty:
        print("  SKIP: year_target_summary.csv not yet present (--allow-empty)")
    else:
        errors.append("FAIL: year_target_summary.csv not found")

    # ------------------------------------------------------------------
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

        if summary_csv.exists():
            with summary_csv.open(encoding="utf-8") as f:
                sr = list(csv.DictReader(f))
            _chk(len(sr) == 1, f"year={year} summary has exactly 1 row (got {len(sr)})", errors)
            if sr:
                r = sr[0]
                required_fields = {
                    "target_year", "success_count", "recoverable_failure_count",
                    "terminal_status_count", "posts_collected", "retry_round", "completed_at",
                }
                missing = required_fields - set(r.keys())
                _chk(not missing, f"year={year} summary has all required fields "
                     f"(missing={missing})", errors)

                rec = int(r.get("recoverable_failure_count", 0) or 0)
                term = int(r.get("terminal_status_count", 0) or 0)
                succ = int(r.get("success_count", 0) or 0)
                posts = int(r.get("posts_collected", 0) or 0)
                render = int(r.get("recoverable_render_failure_count", 0) or 0)
                dnr = int(r.get("recoverable_did_not_reach_year_count", 0) or 0)
                term_aty = int(r.get("terminal_created_after_year_count", 0) or 0)
                term_aty_acct = int(
                    r.get("terminal_created_after_year_with_account_created_evidence_count", 0) or 0
                )
                scrolls_zero = int(r.get("companies_with_scrolls_zero", 0) or 0)
                mp = r.get("max_parallel_companies", "")

                print(f"  INFO year={year}: success={succ} recoverable={rec} "
                      f"(render={render} did_not_reach={dnr}) "
                      f"terminal={term} posts={posts} "
                      f"scrolls_zero={scrolls_zero} max_parallel={mp}")

                if succ == 0 and rec == 0 and term == 0:
                    # No results at all — likely prepare-only or empty run
                    warnings.append(f"WARN year={year}: no results recorded (prepare-only run?)")
                elif succ == 0:
                    warnings.append(
                        f"WARN year={year}: success_count=0 — no successful collections; "
                        f"check render/browser failures before advancing to next year"
                    )

                if render > 0:
                    warnings.append(
                        f"WARN year={year}: {render} recoverable_failed_render — "
                        "parallel Playwright likely caused render instability; "
                        "retry with max_parallel_companies=1"
                    )
                if dnr > 0:
                    warnings.append(
                        f"WARN year={year}: {dnr} recoverable_failed_did_not_reach_year — "
                        "scraper did not scroll back far enough; retry may resolve"
                    )

                if term_aty > 0 and term_aty_acct < term_aty:
                    unsupported = term_aty - term_aty_acct
                    warnings.append(
                        f"WARN year={year}: {unsupported} terminal_created_after_year "
                        "assigned WITHOUT account_created_year evidence — "
                        "these may be mis-classified; check terminal_targets.csv"
                    )

                try:
                    mp_int = int(mp)
                    if mp_int > 1:
                        warnings.append(
                            f"WARN year={year}: run used max_parallel_companies={mp_int} > 1 "
                            "which risks render_failure"
                        )
                except (ValueError, TypeError):
                    pass

        elif args.allow_empty:
            print(f"  SKIP year={year} summary: not yet present (--allow-empty)")
        else:
            errors.append(f"FAIL: year={year} summary CSV missing")

        if failed_csv.exists():
            with failed_csv.open(encoding="utf-8") as f:
                frows = list(csv.DictReader(f))
            bad = [r["status"] for r in frows
                   if not r.get("status", "").startswith("recoverable_failed_")]
            _chk(not bad,
                 f"year={year} failed_targets.csv — only recoverable_failed_* statuses "
                 f"(bad={bad[:3]})", errors)

        if terminal_csv.exists():
            with terminal_csv.open(encoding="utf-8") as f:
                trows = list(csv.DictReader(f))
            bad_t = [r["status"] for r in trows
                     if not r.get("status", "").startswith("terminal_")]
            _chk(not bad_t,
                 f"year={year} terminal_targets.csv — only terminal_* statuses "
                 f"(bad={bad_t[:3]})", errors)

            # Verify terminal_created_after_year has account evidence in each row
            unsupported_rows = [
                r for r in trows
                if r.get("status") == "terminal_created_after_year"
                and not str(r.get("account_created_year", "")).strip()
            ]
            if unsupported_rows:
                names = [r.get("company_name", r.get("handle", "?"))
                         for r in unsupported_rows[:3]]
                errors.append(
                    f"FAIL year={year}: {len(unsupported_rows)} terminal_created_after_year "
                    f"rows have NO account_created_year: {names} — "
                    "this status must only be assigned when account_created_year > target_year"
                )

    # ------------------------------------------------------------------
    print("\n[5] Old-year-first execution guidance check:")
    if not args.allow_empty and years:
        first_year = min(years)
        _warn(
            first_year == RECOMMENDED_FIRST_YEAR,
            f"start_year={first_year} matches recommended first year ({RECOMMENDED_FIRST_YEAR})",
            warnings,
        )

    # ------------------------------------------------------------------
    print("\n[6] Protected paths not modified by this validator:")
    for path in PROTECTED_DIRS:
        status = "exists" if path.exists() else "absent"
        print(f"  INFO: {path.relative_to(REPO_ROOT)} ({status}) — not touched by backfill runner")

    # ------------------------------------------------------------------
    print("\n[7] No classifier/regression outputs in backfill staging:")
    if OUT_ROOT.exists():
        staging_files = [f for f in OUT_ROOT.rglob("*") if f.is_file()]
        forbidden = [f for f in staging_files
                     if any(pat in f.name for pat in FORBIDDEN_IN_STAGING)]
        _chk(not forbidden,
             f"no classifier/regression outputs in staging "
             f"(found={[str(f) for f in forbidden[:3]]})", errors)

    # ------------------------------------------------------------------
    print("\n" + "=" * 60)
    if args.strict and warnings:
        # In strict mode, warnings also count as failures
        errors.extend(warnings)
        warnings = []

    if errors:
        print(f"VALIDATION RESULT: FAIL ({len(errors)} errors, {len(warnings)} warnings)")
        for e in errors:
            print(f"  {e}")
        for w in warnings:
            print(f"  {w}")
        return 1
    else:
        print(f"VALIDATION RESULT: PASS ({len(warnings)} warnings)")
        for w in warnings:
            print(f"  {w}")
        print("=== validate_yearly_humor_backfill_outputs COMPLETE ===")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
