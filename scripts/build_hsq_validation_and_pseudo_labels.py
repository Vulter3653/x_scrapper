#!/usr/bin/env python3
"""Build HSQ validation samples and pseudo-label datasets.

This script implements the B-path for the humor classification project:
1. keep the HSQ codebook-based local classifier as the teacher model;
2. extract high-confidence pseudo-labels for later TF-IDF/RoBERTa/BERTweet experiments;
3. create a compact human validation sample with coding columns.

The script does not train a transformer. It creates the auditable inputs needed
before transformer fine-tuning or comparison is defensible.
"""

import argparse
import csv
import json
import random
from collections import Counter, defaultdict
from pathlib import Path

TYPE_LABELS = {"affiliative", "self_enhancing", "aggressive", "self_defeating"}
PRESENCE_LABELS = {"humor", "non_humor"}

VALIDATION_FIELDS = [
    "validation_bucket",
    "global_post_id",
    "tweet_id",
    "sample_group",
    "company_name",
    "source_x_handle",
    "created_at",
    "text",
    "humor_presence",
    "humor_presence_confidence",
    "humor_presence_review_flag",
    "humor_presence_review_reason",
    "humor_type",
    "humor_type_confidence",
    "humor_type_secondary_label",
    "target_of_humor",
    "humor_function",
    "harm_potential",
    "humor_type_reason",
    "humor_type_key_cues",
    "humor_type_review_flag",
    "sentiment_label",
    "sentiment_confidence",
    "coder_id",
    "human_humor_presence",
    "human_humor_type",
    "human_confidence",
    "human_note",
]

PRESENCE_PSEUDO_FIELDS = [
    "global_post_id",
    "text",
    "pseudo_humor_presence",
    "pseudo_presence_confidence",
    "pseudo_source",
    "sample_group",
    "company_name",
    "created_at",
]

TYPE_PSEUDO_FIELDS = [
    "global_post_id",
    "text",
    "pseudo_humor_type",
    "pseudo_type_confidence",
    "secondary_label",
    "target_of_humor",
    "humor_function",
    "harm_potential",
    "key_cues",
    "pseudo_source",
    "sample_group",
    "company_name",
    "created_at",
]


def as_float(value, default=0.0):
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def as_bool(value):
    return str(value).strip().lower() in {"true", "1", "yes", "y"}


def read_rows(path):
    if not path.exists():
        raise FileNotFoundError(f"Master CSV not found: {path}")
    with path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            raise ValueError(f"CSV has no header: {path}")
        return list(reader)


def write_csv(path, rows, fields):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def pick_rows(rows, limit, rng, used_ids=None):
    candidates = list(rows)
    rng.shuffle(candidates)
    selected = []
    used_ids = used_ids if used_ids is not None else set()
    for row in candidates:
        gid = row.get("global_post_id", "")
        if gid in used_ids:
            continue
        selected.append(row)
        used_ids.add(gid)
        if len(selected) >= limit:
            break
    return selected


def make_validation_row(row, bucket):
    return {
        "validation_bucket": bucket,
        "global_post_id": row.get("global_post_id", ""),
        "tweet_id": row.get("tweet_id", ""),
        "sample_group": row.get("sample_group", ""),
        "company_name": row.get("company_name", ""),
        "source_x_handle": row.get("source_x_handle", ""),
        "created_at": row.get("created_at", ""),
        "text": row.get("text", ""),
        "humor_presence": row.get("humor_presence", ""),
        "humor_presence_confidence": row.get("humor_presence_confidence", ""),
        "humor_presence_review_flag": row.get("humor_presence_review_flag", ""),
        "humor_presence_review_reason": row.get("humor_presence_review_reason", ""),
        "humor_type": row.get("humor_type", ""),
        "humor_type_confidence": row.get("humor_type_confidence", ""),
        "humor_type_secondary_label": row.get("humor_type_secondary_label", ""),
        "target_of_humor": row.get("target_of_humor", ""),
        "humor_function": row.get("humor_function", ""),
        "harm_potential": row.get("harm_potential", ""),
        "humor_type_reason": row.get("humor_type_reason", ""),
        "humor_type_key_cues": row.get("humor_type_key_cues", ""),
        "humor_type_review_flag": row.get("humor_type_review_flag", ""),
        "sentiment_label": row.get("sentiment_label", ""),
        "sentiment_confidence": row.get("sentiment_confidence", ""),
        "coder_id": "",
        "human_humor_presence": "",
        "human_humor_type": "",
        "human_confidence": "",
        "human_note": "",
    }


def make_presence_pseudo_row(row):
    return {
        "global_post_id": row.get("global_post_id", ""),
        "text": row.get("text", ""),
        "pseudo_humor_presence": row.get("humor_presence", ""),
        "pseudo_presence_confidence": row.get("humor_presence_confidence", ""),
        "pseudo_source": "hsq_local_teacher_high_confidence_v1",
        "sample_group": row.get("sample_group", ""),
        "company_name": row.get("company_name", ""),
        "created_at": row.get("created_at", ""),
    }


def make_type_pseudo_row(row):
    return {
        "global_post_id": row.get("global_post_id", ""),
        "text": row.get("text", ""),
        "pseudo_humor_type": row.get("humor_type", ""),
        "pseudo_type_confidence": row.get("humor_type_confidence", ""),
        "secondary_label": row.get("humor_type_secondary_label", ""),
        "target_of_humor": row.get("target_of_humor", ""),
        "humor_function": row.get("humor_function", ""),
        "harm_potential": row.get("harm_potential", ""),
        "key_cues": row.get("humor_type_key_cues", ""),
        "pseudo_source": "hsq_local_teacher_high_confidence_v1",
        "sample_group": row.get("sample_group", ""),
        "company_name": row.get("company_name", ""),
        "created_at": row.get("created_at", ""),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--master", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--sample-per-bucket", type=int, default=50)
    parser.add_argument("--rare-sample-per-bucket", type=int, default=30)
    parser.add_argument("--presence-confidence", type=float, default=0.75)
    parser.add_argument("--type-confidence", type=float, default=0.67)
    parser.add_argument("--seed", type=int, default=20260613)
    args = parser.parse_args()

    rng = random.Random(args.seed)
    rows = read_rows(args.master)

    high_conf_humor = [
        r for r in rows
        if r.get("humor_presence") == "humor"
        and as_float(r.get("humor_presence_confidence")) >= args.presence_confidence
        and not as_bool(r.get("humor_presence_review_flag"))
    ]
    high_conf_non_humor = [
        r for r in rows
        if r.get("humor_presence") == "non_humor"
        and as_float(r.get("humor_presence_confidence")) >= args.presence_confidence
        and not as_bool(r.get("humor_presence_review_flag"))
    ]
    presence_ambiguous = [r for r in rows if r.get("humor_presence") == "ambiguous"]

    type_high_conf = [
        r for r in rows
        if r.get("humor_type") in TYPE_LABELS
        and as_float(r.get("humor_type_confidence")) >= args.type_confidence
        and not as_bool(r.get("humor_type_review_flag"))
    ]
    type_by_label = defaultdict(list)
    for row in rows:
        label = row.get("humor_type")
        if label in TYPE_LABELS:
            type_by_label[label].append(row)

    review_rows = [
        r for r in rows
        if as_bool(r.get("humor_type_review_flag"))
        and r.get("humor_presence") == "humor"
    ]
    harm_high_medium = [
        r for r in rows
        if r.get("harm_potential") in {"medium", "high"}
        and r.get("humor_presence") == "humor"
    ]
    rule_ml_conflict = [
        r for r in rows
        if r.get("rule_label") in PRESENCE_LABELS
        and r.get("humor_presence") in PRESENCE_LABELS
        and r.get("rule_label") != r.get("humor_presence")
    ]

    bucket_specs = [
        ("type_aggressive", type_by_label["aggressive"], args.rare_sample_per_bucket),
        ("type_self_defeating", type_by_label["self_defeating"], args.rare_sample_per_bucket),
        ("harm_medium_high", harm_high_medium, args.rare_sample_per_bucket),
        ("presence_ambiguous", presence_ambiguous, args.sample_per_bucket),
        ("type_review", review_rows, args.sample_per_bucket),
        ("presence_high_conf_humor", high_conf_humor, args.sample_per_bucket),
        ("presence_high_conf_non_humor", high_conf_non_humor, args.sample_per_bucket),
        ("type_affiliative", type_by_label["affiliative"], args.sample_per_bucket),
        ("type_self_enhancing", type_by_label["self_enhancing"], args.sample_per_bucket),
        ("rule_ml_conflict", rule_ml_conflict, args.sample_per_bucket),
    ]

    used_validation_ids = set()
    validation_rows = []
    bucket_counts = {}
    bucket_available = {}
    for bucket, candidates, limit in bucket_specs:
        picked = pick_rows(candidates, limit, rng, used_validation_ids)
        validation_rows.extend(make_validation_row(row, bucket) for row in picked)
        bucket_counts[bucket] = len(picked)
        bucket_available[bucket] = len(candidates)

    presence_pseudo_rows = [make_presence_pseudo_row(r) for r in high_conf_humor + high_conf_non_humor]
    type_pseudo_rows = [make_type_pseudo_row(r) for r in type_high_conf]

    args.output_dir.mkdir(parents=True, exist_ok=True)
    validation_path = args.output_dir / "hsq_validation_sample.csv"
    presence_pseudo_path = args.output_dir / "hsq_pseudo_train_presence.csv"
    type_pseudo_path = args.output_dir / "hsq_pseudo_train_type.csv"
    summary_path = args.output_dir / "hsq_validation_pseudo_summary.json"

    write_csv(validation_path, validation_rows, VALIDATION_FIELDS)
    write_csv(presence_pseudo_path, presence_pseudo_rows, PRESENCE_PSEUDO_FIELDS)
    write_csv(type_pseudo_path, type_pseudo_rows, TYPE_PSEUDO_FIELDS)

    summary = {
        "input_master": str(args.master),
        "row_count": len(rows),
        "sample_per_bucket": args.sample_per_bucket,
        "rare_sample_per_bucket": args.rare_sample_per_bucket,
        "presence_confidence_threshold": args.presence_confidence,
        "type_confidence_threshold": args.type_confidence,
        "validation_rows": len(validation_rows),
        "validation_bucket_selected_counts": bucket_counts,
        "validation_bucket_available_counts": bucket_available,
        "presence_pseudo_rows": len(presence_pseudo_rows),
        "presence_pseudo_distribution": dict(Counter(r["pseudo_humor_presence"] for r in presence_pseudo_rows)),
        "type_pseudo_rows": len(type_pseudo_rows),
        "type_pseudo_distribution": dict(Counter(r["pseudo_humor_type"] for r in type_pseudo_rows)),
        "excluded_from_presence_pseudo_rows": len(rows) - len(presence_pseudo_rows),
        "excluded_from_type_pseudo_rows": len(rows) - len(type_pseudo_rows),
        "recommended_next_step": "Use these files for minimal human validation and optional TF-IDF/RoBERTa/BERTweet comparison. Do not treat pseudo-labels as gold labels.",
    }
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
