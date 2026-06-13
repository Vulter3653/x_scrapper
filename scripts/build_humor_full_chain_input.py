#!/usr/bin/env python3
"""Build a stable input file for the humor classification full chain.

Supports two sampling modes:
1. full/global mode: row_limit controls the first N valid rows, 0 means all rows;
2. per-company mode: per_company_limit controls the first N valid rows per company.

For the existing GitHub Actions UI, per-company mode can also be requested through
--limit with this syntax: company:<per_company_limit>:<expected_companies>.
Example: --limit company:100:102 samples up to 100 posts per company and records
an expected-company warning if the detected company count is not 102.
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


def parse_limit_mode(limit_value, per_company_limit, expected_companies):
    raw = str(limit_value or "0").strip()
    if raw.lower().startswith("company:"):
        parts = raw.split(":")
        if len(parts) not in {2, 3}:
            raise ValueError("company limit syntax must be company:<per_company_limit> or company:<per_company_limit>:<expected_companies>")
        per_company_limit = int(parts[1])
        if len(parts) == 3 and parts[2] != "":
            expected_companies = int(parts[2])
        return 0, per_company_limit, expected_companies, raw
    return int(raw), per_company_limit, expected_companies, raw


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=Path("data/derived/humor/humor_classification_input.csv"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--limit", default="0", help="0 means all rows; company:100:102 enables per-company sampling")
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

    row_limit, per_company_limit, expected_companies, raw_limit = parse_limit_mode(
        args.limit,
        args.per_company_limit,
        args.expected_companies,
    )

    if row_limit < 0:
        raise ValueError("--limit cannot be negative")
    if per_company_limit < 0:
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

            if per_company_limit:
                if selected_by_company[company] >= per_company_limit:
                    continue
            elif row_limit and len(rows) >= row_limit:
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
    if expected_companies and args.expected_companies_mode != "off" and company_count != expected_companies:
        msg = (
            f"Expected {expected_companies} companies, found {company_count}. "
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
    if per_company_limit:
        shortfall_by_company = {
            company: per_company_limit - selected
            for company, selected in selected_by_company.items()
            if selected < per_company_limit
        }

    manifest = {
        "input": str(args.input),
        "output": str(args.output),
        "sampling_mode": "per_company" if per_company_limit else "global_or_full",
        "raw_limit_input": raw_limit,
        "requested_limit": row_limit,
        "per_company_limit": per_company_limit,
        "expected_companies": expected_companies,
        "expected_companies_mode": args.expected_companies_mode,
        "actual_companies": company_count,
        "target_rows_if_all_companies_full": company_count * per_company_limit if per_company_limit else None,
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
