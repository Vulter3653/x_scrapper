#!/usr/bin/env python3
"""Build a stable full-post input file for the humor classification chain."""

import argparse
import csv
import json
import re
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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=Path("data/derived/humor/humor_classification_input.csv"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--limit", type=int, default=0, help="0 means all rows")
    args = parser.parse_args()

    if not args.input.exists():
        raise FileNotFoundError(f"Input CSV not found: {args.input}")

    rows = []
    skipped_empty_text = 0
    duplicate_ids_rewritten = 0
    synthetic_ids_created = 0
    seen_ids = Counter()

    with args.input.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            raise ValueError(f"Input CSV has no header: {args.input}")
        source_fields = list(reader.fieldnames)

        for source_row_index, row in enumerate(reader, start=1):
            text = text_from_row(row)
            if not text:
                skipped_empty_text += 1
                continue

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
            out["text"] = text
            out["source_row_index"] = str(source_row_index)
            rows.append(out)

            if args.limit and len(rows) >= args.limit:
                break

    output_fields = []
    for field in STANDARD_FIELDS + source_fields + ["source_row_index"]:
        if field not in output_fields:
            output_fields.append(field)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=output_fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

    manifest = {
        "input": str(args.input),
        "output": str(args.output),
        "requested_limit": args.limit,
        "output_rows": len(rows),
        "skipped_empty_text_rows": skipped_empty_text,
        "synthetic_ids_created": synthetic_ids_created,
        "duplicate_ids_rewritten": duplicate_ids_rewritten,
        "sample_group_distribution": dict(Counter(r.get("sample_group", "") for r in rows)),
        "company_count": len(set(r.get("company_name", "") for r in rows)),
        "company_distribution_top20": dict(Counter(r.get("company_name", "") for r in rows).most_common(20)),
    }

    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
