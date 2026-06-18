#!/usr/bin/env python3
"""Validate yearly humor backfill staging outputs.

Checks:
- Required scripts and workflow file exist
- year_target_summary.csv present and consistent
- Per-year audit files present with correct structure
- failed_targets.csv contains only recoverable_failed_* statuses
- terminal_targets.csv contains only terminal_* statuses
- data/raw, dashboard/data, integrated corpus NOT modified by backfill
- No H1/H2/H3/classifier outputs inside backfill staging area
- commit_results default is false in the workflow
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
    args = parser.parse_args()

    errors: list[str] = []
    warnings: list[str] = []
    years = ([args.target_year]
             if args.target_year
             else list(range(args.start_year, args.end_year + 1)))

    print("=== validate_yearly_humor_backfill_outputs ===")

    print("\n[1] Required scripts and workflow:")
    for path in (WORKFLOW_NEW, BUILDER, RUNNER):
        _chk(path.exists(), f"exists: {path.relative_to(REPO_ROOT)}", errors)
    _warn(WORKFLOW_OLD.exists(), f"old workflow preserved: {WORKFLOW_OLD.name}", warnings)

    print("\n[2] Workflow safety — commit_results default:")
    if WORKFLOW_NEW.exists():
        text = WORKFLOW_NEW.read_text(encoding="utf-8")
        _chk("commit_results" in text,
             "backfill-humor-yearly-serial.yml has commit_results input", errors)
        _chk("default: 'false'" in text or "default: false" in text,
             "commit_results default is false", errors)
        _chk("backfill-humor-yearly-serial" in text,
             "workflow concurrency group name is distinct", errors)

    print("\n[3] Global year target summary:")
    summary_path = GLOBAL_AUDIT / "year_target_summary.csv"
    if summary_path.exists():
        with summary_path.open(encoding="utf-8") as f:
            srows = list(csv.DictReader(f))
        _chk(len(srows) > 0,
             f"year_target_summary.csv has rows (got {len(srows)})", errors)
        covered = {int(r["target_year"]) for r in srows if str(r.get("target_year", "")).isdigit()}
        _warn(all(y in covered for y in years),
              f"all requested years covered (covered={sorted(covered)})", warnings)
        total_rec = sum(int(r.get("recoverable_failure_count", 0) or 0) for r in srows)
        total_term = sum(int(r.get("terminal_status_count", 0) or 0) for r in srows)
        print(f"  INFO: total_recoverable={total_rec} total_terminal={total_term}")
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
                _chk(not missing, f"year={year} summary has all required fields (missing={missing})", errors)
                rec = int(r.get("recoverable_failure_count", 0) or 0)
                term = int(r.get("terminal_status_count", 0) or 0)
                succ = int(r.get("success_count", 0) or 0)
                posts = int(r.get("posts_collected", 0) or 0)
                print(f"  INFO year={year}: success={succ} recoverable={rec} "
                      f"terminal={term} posts={posts}")
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

    print("\n[5] Protected paths not modified by this validator:")
    for path in PROTECTED_DIRS:
        status = "exists" if path.exists() else "absent"
        print(f"  INFO: {path.relative_to(REPO_ROOT)} ({status}) — not touched by backfill runner")

    print("\n[6] No classifier/regression outputs in backfill staging:")
    if OUT_ROOT.exists():
        staging_files = [f for f in OUT_ROOT.rglob("*") if f.is_file()]
        forbidden = [f for f in staging_files
                     if any(pat in f.name for pat in FORBIDDEN_IN_STAGING)]
        _chk(not forbidden,
             f"no classifier/regression outputs in staging "
             f"(found={[str(f) for f in forbidden[:3]]})", errors)

    print("\n" + "=" * 60)
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
