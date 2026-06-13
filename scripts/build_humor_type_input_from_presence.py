#!/usr/bin/env python3
"""Build humor-type input from humor presence results."""

import argparse
import csv
import json
from collections import Counter
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--presence-results", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args()

    if not args.presence_results.exists():
        raise FileNotFoundError(f"Presence results not found: {args.presence_results}")

    with args.presence_results.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            raise ValueError("Presence results have no header")
        fieldnames = list(reader.fieldnames)
        rows = list(reader)

    humor_rows = [r for r in rows if r.get("humor_presence") == "humor"]

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(humor_rows)

    manifest = {
        "presence_rows": len(rows),
        "humor_type_input_rows": len(humor_rows),
        "presence_distribution": dict(Counter(r.get("humor_presence", "") for r in rows)),
        "company_distribution_top20": dict(Counter(r.get("company_name", "") for r in humor_rows).most_common(20)),
    }
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
