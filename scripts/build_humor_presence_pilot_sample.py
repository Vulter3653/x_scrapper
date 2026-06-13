#!/usr/bin/env python3
"""Build an integrity-checked pilot sample for humor presence classification.

This script is intentionally strict for GitHub Actions pilots:
- only whitelisted sample groups are allowed;
- benchmark shortfalls are filled from Fortune rows when possible;
- the final sample must equal the requested target unless --allow-shortfall is set;
- a JSON manifest is written for downstream audit and integrity validation.
"""

import argparse
import csv
import json
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

ALLOWED_SAMPLE_GROUPS = {
    "benchmark_aggressive_wendys",
    "benchmark_self_defeating_moonpie",
    "fortune_top100_ranked",
}


def clean_text(row):
    return (row.get("text") or row.get("full_text") or row.get("content") or row.get("body") or "").strip()


def read_rows(path):
    if not path.exists():
        raise FileNotFoundError(f"Input file not found: {path}")

    rows = []
    skipped_empty_text = 0
    invalid_groups = Counter()

    with path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            raise ValueError(f"Input CSV has no header: {path}")

        fieldnames = list(reader.fieldnames)
        for source_index, row in enumerate(reader, start=1):
            group = (row.get("sample_group") or "").strip()
            if group not in ALLOWED_SAMPLE_GROUPS:
                invalid_groups[group or "missing_sample_group"] += 1
                continue

            text = clean_text(row)
            if not text:
                skipped_empty_text += 1
                continue

            row["sample_group"] = group
            row["text"] = text
            row["_source_row_index"] = str(source_index)
            rows.append(row)

    return fieldnames, rows, skipped_empty_text, invalid_groups


def dedupe_by_global_post_id(rows):
    """Remove duplicate non-empty global_post_id rows while preserving blank-id rows."""
    seen = set()
    output = []
    duplicate_nonblank_ids = 0

    for row in rows:
        gid = (row.get("global_post_id") or "").strip()
        if gid:
            if gid in seen:
                duplicate_nonblank_ids += 1
                continue
            seen.add(gid)
        output.append(row)

    return output, duplicate_nonblank_ids


def sample_rows(rows, n, rng):
    if n <= 0:
        return []
    if len(rows) <= n:
        return list(rows)
    return rng.sample(rows, n)


def sample_fortune_balanced(rows, n, rng):
    if n <= 0:
        return []
    if len(rows) <= n:
        return list(rows)

    by_company = defaultdict(list)
    for row in rows:
        by_company[row.get("company_name", "unknown")].append(row)

    companies = list(by_company)
    rng.shuffle(companies)
    for company_rows in by_company.values():
        rng.shuffle(company_rows)

    sampled = []
    active = list(companies)
    while len(sampled) < n and active:
        next_active = []
        for company in active:
            if by_company[company]:
                sampled.append(by_company[company].pop())
                if by_company[company]:
                    next_active.append(company)
            if len(sampled) >= n:
                break
        active = next_active

    return sampled


def write_csv(path, rows, fieldnames):
    path.parent.mkdir(parents=True, exist_ok=True)
    output_fields = [field for field in fieldnames if field != "_source_row_index"]
    if "text" not in output_fields:
        output_fields.append("text")

    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=output_fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=Path("data/derived/humor/humor_classification_input.csv"))
    parser.add_argument("--output", type=Path, default=Path("data/derived/humor/humor_presence_pilot_sample.csv"))
    parser.add_argument("--manifest", type=Path, default=Path("data/audit/humor_presence_pilot_sample_manifest.json"))
    parser.add_argument("--fortune-n", type=int, default=500)
    parser.add_argument("--wendys-n", type=int, default=150)
    parser.add_argument("--moonpie-n", type=int, default=150)
    parser.add_argument("--target-total", type=int, default=None)
    parser.add_argument("--allow-shortfall", action="store_true")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    rng = random.Random(args.seed)
    target_total = args.target_total or (args.fortune_n + args.wendys_n + args.moonpie_n)

    fieldnames, rows, skipped_empty_text, invalid_groups = read_rows(args.input)
    rows, duplicate_nonblank_ids = dedupe_by_global_post_id(rows)

    groups = defaultdict(list)
    for row in rows:
        groups[row["sample_group"]].append(row)

    wendys = groups["benchmark_aggressive_wendys"]
    moonpie = groups["benchmark_self_defeating_moonpie"]
    fortune = groups["fortune_top100_ranked"]

    wendys_target = min(args.wendys_n, len(wendys))
    moonpie_target = min(args.moonpie_n, len(moonpie))
    benchmark_shortfall = (args.wendys_n - wendys_target) + (args.moonpie_n - moonpie_target)
    fortune_target = args.fortune_n + benchmark_shortfall

    sampled_wendys = sample_rows(wendys, wendys_target, rng)
    sampled_moonpie = sample_rows(moonpie, moonpie_target, rng)

    selected_ids = {r.get("global_post_id") for r in sampled_wendys + sampled_moonpie if r.get("global_post_id")}
    fortune_pool = [r for r in fortune if not r.get("global_post_id") or r.get("global_post_id") not in selected_ids]
    sampled_fortune = sample_fortune_balanced(fortune_pool, fortune_target, rng)

    pilot_sample = sampled_wendys + sampled_moonpie + sampled_fortune
    rng.shuffle(pilot_sample)

    manifest = {
        "input": str(args.input),
        "output": str(args.output),
        "target_total": target_total,
        "requested_targets": {
            "fortune_top100_ranked": args.fortune_n,
            "benchmark_aggressive_wendys": args.wendys_n,
            "benchmark_self_defeating_moonpie": args.moonpie_n,
        },
        "available_after_filter": {
            "fortune_top100_ranked": len(fortune),
            "benchmark_aggressive_wendys": len(wendys),
            "benchmark_self_defeating_moonpie": len(moonpie),
        },
        "sampled": {
            "fortune_top100_ranked": len(sampled_fortune),
            "benchmark_aggressive_wendys": len(sampled_wendys),
            "benchmark_self_defeating_moonpie": len(sampled_moonpie),
        },
        "benchmark_shortfall_filled_by_fortune": benchmark_shortfall,
        "final_rows": len(pilot_sample),
        "skipped_empty_text_rows": skipped_empty_text,
        "invalid_sample_group_rows": dict(invalid_groups),
        "duplicate_nonblank_global_post_id_rows_removed": duplicate_nonblank_ids,
        "allowed_sample_groups": sorted(ALLOWED_SAMPLE_GROUPS),
        "seed": args.seed,
    }

    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    if len(pilot_sample) != target_total and not args.allow_shortfall:
        print(json.dumps(manifest, indent=2, ensure_ascii=False), file=sys.stderr)
        raise SystemExit(
            f"Pilot sample integrity failure: requested {target_total} rows, built {len(pilot_sample)} rows. "
            "Either provide enough source rows or explicitly pass --allow-shortfall."
        )

    write_csv(args.output, pilot_sample, fieldnames)
    print(json.dumps(manifest, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
