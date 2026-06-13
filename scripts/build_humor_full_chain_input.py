#!/usr/bin/env python3
"""Build a stable input file for the humor classification full chain.

Supports two sampling modes:
1. full/global mode: row_limit controls the first N valid rows, 0 means all rows;
2. per-company mode: per_company_limit controls the first N valid rows per company.

Expected company-count mismatches are recorded as warnings by default rather than
failing the workflow, so diagnostic runs can still produce artifacts.
"""

import argparse
import csv
import json
import re
import sys
from collections import Counter
from pathlib import Path

STANDARD_FIELDS = [
    "global_post_id",
    "tweet_id",
    "sample_group",
    "company_name",
    "source_x_handle",
    "created_at",
    "text",
]


def normalize_text(text):
    return re.sub(r"\s+", " ", (text or "").strip())


def text_from_row(row):
    return normalize_text(row.get("text") or row.get("full_text") or row.get("content") or row.get("body") or "")


def company_from_row(row, company_field):
    company = normalize_text(row.get(company_field))
    return company or "unknown_company"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=Path("data/derived/humor/humor_classification_input.csv"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--limit", type=int, default=0, help="0 means all rows in global mode")
    parser.add_argument("--per-company-limit", type=int, default=0, help="0 disables per-company sampling")
    parser.add_argument("--expected-companies", type=int, default=0, help="0 disables expected-company check")
    parser.add_argument(
        "--expected-companies-mode",
        choices=["warn", "strict", "off"],
        default="warn",
        help="warn records mismatches, strict exits non-zero, off ignores mismatches",
    )
    parser.add_argument("--company-field", default="company_name")
    args = parser.parse_args()

    if args.limit < 0:
        raise ValueError("--limit cannot be negative")
    if args.per_company_limit < 0:
        raise ValueError("--per-company-limit cannot be negative")
    if not args.input.exists():
        raise FileNotFoundError(f"Input CSV not found: {args.input}")

    rows = []
    skipped_empty_text = 0
    duplicate_ids_rewritten = 0
    synthetic_ids_created = 0
    seen_ids = Counter()
    selected_by_company = Counter()
    available_by_company = Counter()
    warnings = []

    with args.input.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            raise ValueError(f"Input CSV has no header: {args.input}")
        source_fields = list(reader.fieldnames)

        for source_row_index, row in enumerate(reader, start=1):
            company = company_from_row(row, args.company_field)
            text = text_from_row(row)
            if not text:
                skipped_empty_text += 1
                continue

            available_by_company[company] += 1

            if args.per_company_limit:
                if selected_by_company[company] >= args.per_company_limit:
                    continue
            elif args.limit and len(rows) >= args.limit:
                break

            gid = normalize_text(row.get("global_post_id"))
            if not gid:
                gid = f"synthetic_global_post_id_{source_row_index}"
                synthetic_ids_created += 1

            seen_ids[gid] += 1
            if seen_ids[gid] > 1:
                gid = f"{gid}__dup_{seen_ids[gid]}"
                duplicate_ids_rewritten += 1

            out = dict(row)
            out["global_post_id"] = gid
            out["company_name"] = company
            out["text"] = text
            out["source_row_index"] = str(source_row_index)
            rows.append(out)
            selected_by_company[company] += 1

    company_count = len(available_by_company)
    if args.expected_companies and args.expected_companies_mode != "off" and company_count != args.expected_companies:
        msg = (
            f"Expected {args.expected_companies} companies, found {company_count}. "
            "Proceeding because expected-company mode is not strict."
        )
        if args.expected_companies_mode == "strict":
            raise SystemExit(msg)
        warnings.append(msg)
        print(f"WARNING: {msg}", file=sys.stderr)

    output_fields = []
    for field in STANDARD_FIELDS + source_fields + ["source_row_index"]:
        if field not in output_fields:
            output_fields.append(field)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=output_fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

    shortfall_by_company = {}
    if args.per_company_limit:
        shortfall_by_company = {
            company: args.per_company_limit - selected
            for company, selected in selected_by_company.items()
            if selected < args.per_company_limit
        }

    manifest = {
        "input": str(args.input),
        "output": str(args.output),
        "sampling_mode": "per_company" if args.per_company_limit else "global_or_full",
        "requested_limit": args.limit,
        "per_company_limit": args.per_company_limit,
        "expected_companies": args.expected_companies,
        "expected_companies_mode": args.expected_companies_mode,
        "actual_companies": company_count,
        "target_rows_if_all_companies_full": company_count * args.per_company_limit if args.per_company_limit else None,
        "output_rows": len(rows),
        "skipped_empty_text_rows": skipped_empty_text,
        "synthetic_ids_created": synthetic_ids_created,
        "duplicate_ids_rewritten": duplicate_ids_rewritten,
        "shortfall_company_count": len(shortfall_by_company),
        "shortfall_by_company": shortfall_by_company,
        "sample_group_distribution": dict(Counter(r.get("sample_group", "") for r in rows)),
        "company_count": company_count,
        "selected_company_distribution": dict(selected_by_company),
        "available_company_distribution_top20": dict(available_by_company.most_common(20)),
        "selected_company_distribution_top20": dict(selected_by_company.most_common(20)),
        "warnings": warnings,
    }

    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
