#!/usr/bin/env python3
"""Build a stratified sample from the full-chain master for humor type A/B testing.

Samples rows from the existing full-chain master CSV to create a balanced evaluation
set that covers all humor type labels, including the long tail (aggressive, self_defeating)
that are under-represented in the full dataset.

Input:
  data/derived/humor/full_chain/humor_full_chain_master.csv

Outputs:
  data/derived/humor/evaluation/humor_type_ab_test_sample.csv
  data/audit/humor/evaluation/humor_type_ab_test_sample_manifest.json
"""

import argparse
import csv
import json
import random
import sys
from pathlib import Path

DEFAULT_INPUT = Path("data/derived/humor/full_chain/humor_full_chain_master.csv")
DEFAULT_OUTPUT = Path("data/derived/humor/evaluation/humor_type_ab_test_sample.csv")
DEFAULT_MANIFEST = Path("data/audit/humor/evaluation/humor_type_ab_test_sample_manifest.json")

# Strata definitions: (stratum_name, master_column, master_value, max_n)
# ambiguous_or_review: humor_type == ambiguous_or_review
# HSQ types: humor_type == {affiliative, self_enhancing, aggressive, self_defeating}
# non_humor: humor_presence == non_humor OR humor_type == not_applicable
STRATA = [
    ("ambiguous_or_review", "humor_type", "ambiguous_or_review", 300),
    ("self_enhancing",      "humor_type", "self_enhancing",      150),
    ("affiliative",         "humor_type", "affiliative",         150),
    ("aggressive",          "humor_type", "aggressive",          100),
    ("self_defeating",      "humor_type", "self_defeating",      100),
    ("non_humor",           "humor_type", "not_applicable",      200),
]


def load_master(path: Path) -> list[dict]:
    if not path.exists():
        raise FileNotFoundError(
            f"Full-chain master not found: {path}\n"
            "Run the 'Run Humor Full Chain Classification' workflow first."
        )
    with path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            raise ValueError(f"Master CSV has no header: {path}")
        return list(reader)


def build_sample(
    rows: list[dict],
    strata: list[tuple],
    seed: int,
) -> tuple[list[dict], dict]:
    rng = random.Random(seed)

    all_sampled_ids: set[str] = set()
    sampled_rows: list[dict] = []
    manifest_strata: list[dict] = {}

    for stratum_name, col, value, max_n in strata:
        pool = [
            r for r in rows
            if r.get(col, "").strip() == value
            and r.get("global_post_id", "") not in all_sampled_ids
        ]
        available = len(pool)
        shortfall = max(0, max_n - available)
        take = min(max_n, available)
        selected = rng.sample(pool, take) if take < available else list(pool)
        for r in selected:
            all_sampled_ids.add(r.get("global_post_id", ""))
        sampled_rows.extend(selected)
        manifest_strata[stratum_name] = {
            "filter_column": col,
            "filter_value": value,
            "requested": max_n,
            "available": available,
            "sampled": take,
            "shortfall": shortfall,
        }

    return sampled_rows, manifest_strata


def build_manifest(
    input_path: Path,
    output_path: Path,
    manifest_path: Path,
    total_master_rows: int,
    total_sampled: int,
    strata_detail: dict,
    seed: int,
) -> dict:
    return {
        "input_path": str(input_path),
        "output_path": str(output_path),
        "manifest_path": str(manifest_path),
        "total_master_rows": total_master_rows,
        "total_sampled": total_sampled,
        "random_seed": seed,
        "strata": strata_detail,
        "notes": [
            "Sample is stratified by humor_type from the full-chain master.",
            "non_humor stratum uses humor_type == not_applicable.",
            "If a stratum had fewer rows than requested, all available rows were included.",
            "Shortfall > 0 indicates under-represented class in the full-chain master.",
            "This sample is intended for v1 vs v2 A/B comparison only, not for training.",
        ],
    }


def main():
    parser = argparse.ArgumentParser(
        description="Build stratified sample from full-chain master for humor type A/B test."
    )
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility")
    args = parser.parse_args()

    print(f"Loading master from: {args.input}")
    rows = load_master(args.input)
    print(f"  Master rows: {len(rows)}")

    sampled_rows, strata_detail = build_sample(rows, STRATA, seed=args.seed)
    print(f"  Total sampled: {len(sampled_rows)}")

    if not sampled_rows:
        print("ERROR: No rows were sampled. Check that the master CSV is non-empty.", file=sys.stderr)
        sys.exit(1)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys()) if rows else []

    # Add v1_label alias columns for clarity in comparison
    out_fields = fieldnames + ["stratum"]
    with args.output.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=out_fields, extrasaction="ignore")
        writer.writeheader()
        for r in sampled_rows:
            ht = r.get("humor_type", "")
            stratum = ht if ht != "not_applicable" else "non_humor"
            writer.writerow({**r, "stratum": stratum})

    manifest = build_manifest(
        input_path=args.input,
        output_path=args.output,
        manifest_path=args.manifest,
        total_master_rows=len(rows),
        total_sampled=len(sampled_rows),
        strata_detail=strata_detail,
        seed=args.seed,
    )
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(f"\nSample written to: {args.output}")
    print(f"Manifest written to: {args.manifest}")
    print("\nStrata summary:")
    for stratum_name, detail in strata_detail.items():
        shortfall_note = f"  *** SHORTFALL={detail['shortfall']}" if detail["shortfall"] > 0 else ""
        print(f"  {stratum_name}: sampled={detail['sampled']} / requested={detail['requested']}{shortfall_note}")


if __name__ == "__main__":
    main()
