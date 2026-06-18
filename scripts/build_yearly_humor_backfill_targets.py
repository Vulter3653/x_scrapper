#!/usr/bin/env python3
"""Build per-year target company lists for the yearly serial humor backfill.

Reads config/humor_collection_append_targets.csv, infers earliest observable
post year per company from existing data, and produces:

  data/backfill/yearly_humor/audit/year_target_summary.csv
  data/backfill/yearly_humor/{year}/audit/year_{year}_target_companies.csv

Does NOT modify data/raw, dashboard/data, or integrated corpus files.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
TARGETS_CSV = REPO_ROOT / "config" / "humor_collection_append_targets.csv"
OUT_ROOT = REPO_ROOT / "data" / "backfill" / "yearly_humor"
GLOBAL_AUDIT = OUT_ROOT / "audit"

MIN_YEAR = 2009
MAX_YEAR = 2021

YEAR_SUMMARY_FIELDS = [
    "target_year",
    "target_company_count",
    "no_date_found_count",
    "account_created_year_available_count",
    "earliest_observed_year_available_count",
]

COMPANY_FIELDS = [
    "fortune_rank",
    "company_name",
    "handle",
    "sample_group",
    "account_created_year",
    "earliest_observed_post_year",
    "date_source",
    "active_in_year",
    "audit_status",
]


def slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_") or "target"


def parse_year(value: object) -> int | None:
    s = str(value or "").strip()
    if not s:
        return None
    if re.fullmatch(r"\d{4}", s):
        y = int(s)
        return y if 1990 <= y <= 2030 else None
    m = re.match(r"(\d{4})-", s)
    if m:
        y = int(m.group(1))
        return y if 1990 <= y <= 2030 else None
    m = re.search(r"\b(20\d{2})\b", s)
    if m:
        return int(m.group(1))
    return None


def earliest_year_from_json(path: Path) -> int | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        posts = data if isinstance(data, list) else []
        years = [
            y for p in posts
            for y in [parse_year(p.get("created_at") or p.get("date") or "")]
            if y
        ]
        return min(years) if years else None
    except Exception:
        return None


def earliest_year_from_csv(path: Path) -> int | None:
    try:
        with path.open(encoding="utf-8-sig", newline="") as f:
            years = []
            for row in csv.DictReader(f):
                for col in ("created_at", "date", "timestamp"):
                    y = parse_year(row.get(col, ""))
                    if y:
                        years.append(y)
                        break
        return min(years) if years else None
    except Exception:
        return None


def find_earliest_observed_year(target: dict) -> tuple[int | None, str]:
    rank = target.get("fortune_rank", "")
    handle = target.get("handle", "")
    company = target.get("company_name", "")
    handle_slug = slugify(handle.lstrip("@"))
    company_slug = slugify(company.replace("'", ""))

    candidates: list[tuple[Path, str]] = []

    raw_root = REPO_ROOT / "data" / "raw" / "fortune_x_2025_ranked"
    if raw_root.exists():
        prefix = f"{int(rank):03d}" if str(rank).isdigit() else ""
        if prefix:
            for d in raw_root.glob(f"{prefix}_*"):
                for fname in ("posts.csv", "posts.json"):
                    p = d / fname
                    if p.exists():
                        candidates.append((p, f"fortune_x_2025_ranked/{d.name}"))
        if not candidates:
            for d in raw_root.glob("*"):
                if handle_slug in d.name.lower() or company_slug in d.name.lower():
                    for fname in ("posts.csv", "posts.json"):
                        p = d / fname
                        if p.exists():
                            candidates.append((p, f"fortune_x_2025_ranked/{d.name}"))

    bf_raw = REPO_ROOT / "data" / "backfill" / "humor_through_2021" / "raw"
    if bf_raw.exists():
        for d in bf_raw.glob("*"):
            if handle_slug in d.name.lower() or company_slug in d.name.lower():
                for fname in ("posts_on_or_before_2021.json", "collected_posts_raw.json"):
                    p = d / fname
                    if p.exists():
                        candidates.append((p, f"humor_through_2021/{d.name}"))

    yh_root = REPO_ROOT / "data" / "backfill" / "yearly_humor"
    if yh_root.exists():
        for year_dir in sorted(yh_root.glob("[0-9][0-9][0-9][0-9]")):
            posts_dir = year_dir / "posts"
            if posts_dir.exists():
                for f in posts_dir.rglob(f"*{handle_slug}*"):
                    if f.is_file():
                        candidates.append((f, f"yearly_humor/{year_dir.name}"))

    legacy = REPO_ROOT / "data" / company_slug / "posts.json"
    if legacy.exists():
        candidates.append((legacy, f"data/{company_slug}"))

    best_year: int | None = None
    best_src = ""
    for path, src in candidates:
        y = earliest_year_from_csv(path) if path.suffix == ".csv" else earliest_year_from_json(path)
        if y and (best_year is None or y < best_year):
            best_year = y
            best_src = src

    return best_year, best_src


def build_profiles(targets: list[dict]) -> list[dict]:
    profiles = []
    for t in targets:
        handle = (t.get("handle") or "").strip()
        if not handle:
            continue
        acct_yr = parse_year(t.get("account_created_year"))
        obs_yr, obs_src = find_earliest_observed_year(t)

        if acct_yr:
            date_source = "account_created_year"
            ref_year: int | None = acct_yr
            audit_status = "ok"
        elif obs_yr:
            date_source = f"earliest_observed:{obs_src}"
            ref_year = obs_yr
            audit_status = "ok_observed_only"
        else:
            date_source = "not_found"
            ref_year = None
            audit_status = "no_date_found"

        profiles.append({
            "fortune_rank": t.get("fortune_rank", ""),
            "company_name": t.get("company_name", ""),
            "handle": handle,
            "sample_group": t.get("sample_group", ""),
            "account_created_year": acct_yr or "",
            "earliest_observed_post_year": obs_yr or "",
            "date_source": date_source,
            "_ref_year": ref_year,
            "audit_status": audit_status,
        })
    return profiles


def build_year_rows(profiles: list[dict], year: int, target_scope: str) -> list[dict]:
    rows = []
    for p in profiles:
        acct_yr = int(p["account_created_year"]) if p["account_created_year"] else None
        obs_yr = int(p["earliest_observed_post_year"]) if p["earliest_observed_post_year"] else None

        if acct_yr is not None:
            # account_created_year is authoritative: company did not exist on X before this year
            if acct_yr <= year:
                active = "true"
                status = "ok"
            else:
                active = "false"
                status = "skipped_not_active_in_year"
        elif obs_yr is not None and obs_yr <= year:
            # Confirmed presence on or before this year from observed data
            active = "true"
            status = "ok_observed_only"
        else:
            # obs_yr > year or no date at all.
            # earliest_observed > Y does NOT prove the company was absent before Y —
            # it only means we have not yet collected pre-Y data (the purpose of this backfill).
            # Include in "all" mode so the runner attempts collection.
            if target_scope == "all":
                active = "unknown"
                status = "no_confirmed_pre_year_data" if obs_yr else "no_date_found"
            else:
                active = "false"
                status = "skipped_no_confirmed_data"
        rows.append({
            "fortune_rank": p["fortune_rank"],
            "company_name": p["company_name"],
            "handle": p["handle"],
            "sample_group": p["sample_group"],
            "account_created_year": p["account_created_year"],
            "earliest_observed_post_year": p["earliest_observed_post_year"],
            "date_source": p["date_source"],
            "active_in_year": active,
            "audit_status": status,
        })
    return rows


def write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build per-year target company lists for yearly humor backfill."
    )
    parser.add_argument("--targets", default=str(TARGETS_CSV))
    parser.add_argument("--start-year", type=int, default=MIN_YEAR)
    parser.add_argument("--end-year", type=int, default=MAX_YEAR)
    parser.add_argument("--target-year", type=int, default=None)
    parser.add_argument("--target-scope", choices=["all", "failed_only"], default="all")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print summary without writing files.")
    args = parser.parse_args()

    targets_path = Path(args.targets)
    if not targets_path.exists():
        print(f"ERROR: targets file not found: {targets_path}", file=sys.stderr)
        return 1

    with targets_path.open(encoding="utf-8-sig", newline="") as f:
        raw_targets = list(csv.DictReader(f))
    print(f"Loaded {len(raw_targets)} targets from {targets_path.name}")

    profiles = build_profiles(raw_targets)
    n_acct_yr = sum(1 for p in profiles if p["account_created_year"])
    n_obs_yr = sum(1 for p in profiles if p["earliest_observed_post_year"])
    n_no_date = sum(1 for p in profiles if p["audit_status"] == "no_date_found")
    print(f"Profiles: {len(profiles)} total | account_created_year={n_acct_yr} "
          f"earliest_observed={n_obs_yr} no_date={n_no_date}")

    years = [args.target_year] if args.target_year else list(range(args.start_year, args.end_year + 1))
    year_summary_rows = []

    for year in years:
        year_rows = build_year_rows(profiles, year, args.target_scope)
        active_rows = [r for r in year_rows if r["active_in_year"] in ("true", "unknown")]
        n_nd = sum(1 for r in year_rows if r["audit_status"] == "no_date_found")
        year_summary_rows.append({
            "target_year": year,
            "target_company_count": len(active_rows),
            "no_date_found_count": n_nd,
            "account_created_year_available_count": n_acct_yr,
            "earliest_observed_year_available_count": n_obs_yr,
        })
        print(f"  year={year}: active={len(active_rows)} skipped={len(year_rows)-len(active_rows)} "
              f"no_date={n_nd}")

        if not args.dry_run:
            out = OUT_ROOT / str(year) / "audit" / f"year_{year}_target_companies.csv"
            write_csv(out, year_rows, COMPANY_FIELDS)

    if not args.dry_run:
        summary_path = GLOBAL_AUDIT / "year_target_summary.csv"
        write_csv(summary_path, year_summary_rows, YEAR_SUMMARY_FIELDS)
        print(f"Written: {summary_path}")
    else:
        print("DRY RUN — no files written")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
