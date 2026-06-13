#!/usr/bin/env python3
"""Build HSQ validation samples, pseudo-labels, and seed datasets.

This script implements the B-path for the humor classification project:
1. keep the HSQ codebook-based local classifier as the teacher model;
2. extract high-confidence pseudo-labels from the full master dataset;
3. create a compact human validation sample with coding columns;
4. build high-intensity humor seeds and hard-negative non-humor seeds for
   later TF-IDF/RoBERTa/BERTweet comparison.

The script does not train a transformer. It creates the auditable inputs needed
before transformer fine-tuning or comparison is defensible. Pseudo-labels remain
teacher labels, not gold labels.
"""

import argparse
import csv
import json
import random
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

TYPE_LABELS = {"affiliative", "self_enhancing", "aggressive", "self_defeating"}
PRESENCE_LABELS = {"humor", "non_humor"}

HARD_NEGATIVE_PATTERNS = {
    "promotion_event": [
        "vote", "votes", "bracket", "championship", "final four", "giveaway", "sweepstakes",
        "use code", "promo code", "limited time", "with purchase", "available now", "back on the menu",
        "shop now", "order now", "download now", "register now", "available all day", "while supplies last",
    ],
    "support_reply": [
        "please contact", "dm us", "send us a dm", "customer support", "support team", "sorry for",
        "sorry about", "help you", "assist you", "assistance", "reach out", "teamcare", "call us",
    ],
    "corporate_announcement": [
        "announces", "announced", "released", "general availability", "customers are using",
        "price-performance", "infrastructure", "deployment", "earnings", "quarterly", "investor",
        "financial results", "webcast", "conference call", "annual report", "filing", "dividend",
    ],
    "csr_news": [
        "donate", "donation", "community", "proud to", "honored to", "congratulations", "award",
        "sustainability", "volunteer", "relief", "patients", "clinical", "research", "partnership",
    ],
    "brand_engagement_nonhumor": [
        "thanks for", "thank you", "join us", "meet us", "learn more", "read more", "find out more",
        "watch live", "listen now", "apply today", "we're hiring", "we are hiring", "join our team",
    ],
}

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
    "matched_type_cues",
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
    "seed_strength_score",
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
    "seed_strength_score",
    "sample_group",
    "company_name",
    "created_at",
]

SEED_FIELDS = [
    "seed_bucket",
    "global_post_id",
    "tweet_id",
    "sample_group",
    "company_name",
    "source_x_handle",
    "created_at",
    "text",
    "teacher_presence_label",
    "teacher_presence_confidence",
    "teacher_humor_type",
    "teacher_type_confidence",
    "target_of_humor",
    "humor_function",
    "harm_potential",
    "key_cues",
    "hard_negative_category",
    "seed_strength_score",
    "pseudo_source",
]


def normalize_text(text):
    return re.sub(r"\s+", " ", (text or "").strip())


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


def sort_by_strength(rows, reverse=True):
    return sorted(rows, key=lambda r: as_float(r.get("seed_strength_score")), reverse=reverse)


def detect_hard_negative_category(text):
    lower = normalize_text(text).lower()
    matched = []
    for category, patterns in HARD_NEGATIVE_PATTERNS.items():
        if any(pattern in lower for pattern in patterns):
            matched.append(category)
    return ";".join(matched)


def compute_humor_seed_strength(row):
    presence_conf = as_float(row.get("humor_presence_confidence"))
    type_conf = as_float(row.get("humor_type_confidence"))
    key_cues = row.get("humor_type_key_cues") or row.get("matched_type_cues") or ""
    cue_bonus = 0.08 if key_cues else 0.0
    harm_bonus = 0.04 if row.get("harm_potential") in {"medium", "high"} else 0.0
    rare_bonus = 0.06 if row.get("humor_type") in {"aggressive", "self_defeating"} else 0.0
    return round((0.55 * presence_conf) + (0.35 * type_conf) + cue_bonus + harm_bonus + rare_bonus, 6)


def compute_negative_seed_strength(row, category):
    presence_conf = as_float(row.get("humor_presence_confidence"))
    pattern_bonus = 0.10 if category else 0.0
    review_bonus = -0.10 if as_bool(row.get("humor_presence_review_flag")) else 0.0
    return round(presence_conf + pattern_bonus + review_bonus, 6)


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
        "matched_type_cues": row.get("matched_type_cues", ""),
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
        "pseudo_source": "hsq_local_teacher_full_data_high_confidence_v2",
        "seed_strength_score": row.get("seed_strength_score", ""),
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
        "key_cues": row.get("humor_type_key_cues") or row.get("matched_type_cues", ""),
        "pseudo_source": "hsq_local_teacher_full_data_high_confidence_v2",
        "seed_strength_score": row.get("seed_strength_score", ""),
        "sample_group": row.get("sample_group", ""),
        "company_name": row.get("company_name", ""),
        "created_at": row.get("created_at", ""),
    }


def make_seed_row(row, bucket, category=""):
    return {
        "seed_bucket": bucket,
        "global_post_id": row.get("global_post_id", ""),
        "tweet_id": row.get("tweet_id", ""),
        "sample_group": row.get("sample_group", ""),
        "company_name": row.get("company_name", ""),
        "source_x_handle": row.get("source_x_handle", ""),
        "created_at": row.get("created_at", ""),
        "text": row.get("text", ""),
        "teacher_presence_label": row.get("humor_presence", ""),
        "teacher_presence_confidence": row.get("humor_presence_confidence", ""),
        "teacher_humor_type": row.get("humor_type", ""),
        "teacher_type_confidence": row.get("humor_type_confidence", ""),
        "target_of_humor": row.get("target_of_humor", ""),
        "humor_function": row.get("humor_function", ""),
        "harm_potential": row.get("harm_potential", ""),
        "key_cues": row.get("humor_type_key_cues") or row.get("matched_type_cues", ""),
        "hard_negative_category": category,
        "seed_strength_score": row.get("seed_strength_score", ""),
        "pseudo_source": "hsq_local_teacher_full_data_seed_v2",
    }


def cap_by_label(rows, label_key, max_per_label, rng):
    grouped = defaultdict(list)
    for row in rows:
        grouped[row.get(label_key, "")].append(row)
    output = []
    selected_counts = {}
    available_counts = {}
    for label, label_rows in sorted(grouped.items()):
        available_counts[label] = len(label_rows)
        picked = pick_rows(label_rows, max_per_label, rng)
        selected_counts[label] = len(picked)
        output.extend(picked)
    rng.shuffle(output)
    return output, available_counts, selected_counts


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--master", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--sample-per-bucket", type=int, default=50)
    parser.add_argument("--rare-sample-per-bucket", type=int, default=30)
    parser.add_argument("--presence-confidence", type=float, default=0.70)
    parser.add_argument("--type-confidence", type=float, default=0.60)
    parser.add_argument("--high-intensity-confidence", type=float, default=0.70)
    parser.add_argument("--hard-negative-confidence", type=float, default=0.65)
    parser.add_argument("--max-presence-per-class", type=int, default=5000)
    parser.add_argument("--max-type-per-class", type=int, default=2000)
    parser.add_argument("--min-master-rows", type=int, default=0)
    parser.add_argument("--seed", type=int, default=20260613)
    args = parser.parse_args()

    rng = random.Random(args.seed)
    rows = read_rows(args.master)
    if args.min_master_rows and len(rows) < args.min_master_rows:
        raise SystemExit(
            f"Master row count {len(rows)} is below --min-master-rows={args.min_master_rows}. "
            "Use a full_all_posts full-chain artifact for full-data pseudo-label construction."
        )

    # High-intensity positive humor seeds: obvious humor only.
    high_intensity_humor = []
    for row in rows:
        if row.get("humor_presence") != "humor":
            continue
        if as_float(row.get("humor_presence_confidence")) < args.high_intensity_confidence:
            continue
        if as_bool(row.get("humor_presence_review_flag")):
            continue
        strength = compute_humor_seed_strength(row)
        if strength < args.high_intensity_confidence:
            continue
        enriched = dict(row)
        enriched["seed_strength_score"] = f"{strength:.6f}"
        high_intensity_humor.append(enriched)
    high_intensity_humor = sort_by_strength(high_intensity_humor)

    # Hard-negative seeds: non-humor that can be mistaken for humor because it is social,
    # promotional, event-like, supportive, or brand-engagement language.
    hard_negative_non_humor = []
    for row in rows:
        if row.get("humor_presence") != "non_humor":
            continue
        if as_float(row.get("humor_presence_confidence")) < args.hard_negative_confidence:
            continue
        category = detect_hard_negative_category(row.get("text", ""))
        if not category and as_float(row.get("humor_presence_confidence")) < args.presence_confidence:
            continue
        enriched = dict(row)
        strength = compute_negative_seed_strength(row, category)
        enriched["seed_strength_score"] = f"{strength:.6f}"
        enriched["hard_negative_category"] = category or "high_confidence_non_humor"
        hard_negative_non_humor.append(enriched)
    hard_negative_non_humor = sort_by_strength(hard_negative_non_humor)

    high_conf_humor = [r for r in high_intensity_humor if as_float(r.get("humor_presence_confidence")) >= args.presence_confidence]
    high_conf_non_humor = [r for r in hard_negative_non_humor if as_float(r.get("humor_presence_confidence")) >= args.presence_confidence]
    presence_ambiguous = [r for r in rows if r.get("humor_presence") == "ambiguous"]

    type_high_conf = []
    type_by_label = defaultdict(list)
    for row in high_intensity_humor:
        label = row.get("humor_type")
        if label in TYPE_LABELS:
            type_by_label[label].append(row)
            if as_float(row.get("humor_type_confidence")) >= args.type_confidence and not as_bool(row.get("humor_type_review_flag")):
                type_high_conf.append(row)

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
        ("hard_negative_non_humor", hard_negative_non_humor, args.sample_per_bucket),
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

    presence_pseudo_rows_raw = high_conf_humor + high_conf_non_humor
    type_pseudo_rows_raw = type_high_conf

    presence_balanced_raw, presence_available_counts, presence_selected_counts = cap_by_label(
        presence_pseudo_rows_raw,
        "humor_presence",
        args.max_presence_per_class,
        rng,
    )
    type_balanced_raw, type_available_counts, type_selected_counts = cap_by_label(
        type_pseudo_rows_raw,
        "humor_type",
        args.max_type_per_class,
        rng,
    )

    presence_pseudo_rows = [make_presence_pseudo_row(r) for r in presence_pseudo_rows_raw]
    type_pseudo_rows = [make_type_pseudo_row(r) for r in type_pseudo_rows_raw]
    presence_balanced_rows = [make_presence_pseudo_row(r) for r in presence_balanced_raw]
    type_balanced_rows = [make_type_pseudo_row(r) for r in type_balanced_raw]
    high_intensity_seed_rows = [make_seed_row(r, "high_intensity_humor") for r in high_intensity_humor]
    hard_negative_seed_rows = [
        make_seed_row(r, "hard_negative_non_humor", r.get("hard_negative_category", ""))
        for r in hard_negative_non_humor
    ]

    args.output_dir.mkdir(parents=True, exist_ok=True)
    validation_path = args.output_dir / "hsq_validation_sample.csv"
    presence_pseudo_path = args.output_dir / "hsq_pseudo_train_presence.csv"
    type_pseudo_path = args.output_dir / "hsq_pseudo_train_type.csv"
    presence_balanced_path = args.output_dir / "hsq_pseudo_train_presence_balanced.csv"
    type_balanced_path = args.output_dir / "hsq_pseudo_train_type_class_capped.csv"
    high_intensity_path = args.output_dir / "hsq_high_intensity_humor_seed.csv"
    hard_negative_path = args.output_dir / "hsq_hard_negative_non_humor_seed.csv"
    summary_path = args.output_dir / "hsq_validation_pseudo_summary.json"

    write_csv(validation_path, validation_rows, VALIDATION_FIELDS)
    write_csv(presence_pseudo_path, presence_pseudo_rows, PRESENCE_PSEUDO_FIELDS)
    write_csv(type_pseudo_path, type_pseudo_rows, TYPE_PSEUDO_FIELDS)
    write_csv(presence_balanced_path, presence_balanced_rows, PRESENCE_PSEUDO_FIELDS)
    write_csv(type_balanced_path, type_balanced_rows, TYPE_PSEUDO_FIELDS)
    write_csv(high_intensity_path, high_intensity_seed_rows, SEED_FIELDS)
    write_csv(hard_negative_path, hard_negative_seed_rows, SEED_FIELDS)

    summary = {
        "input_master": str(args.master),
        "row_count": len(rows),
        "min_master_rows": args.min_master_rows,
        "sample_per_bucket": args.sample_per_bucket,
        "rare_sample_per_bucket": args.rare_sample_per_bucket,
        "presence_confidence_threshold": args.presence_confidence,
        "type_confidence_threshold": args.type_confidence,
        "high_intensity_confidence_threshold": args.high_intensity_confidence,
        "hard_negative_confidence_threshold": args.hard_negative_confidence,
        "validation_rows": len(validation_rows),
        "validation_bucket_selected_counts": bucket_counts,
        "validation_bucket_available_counts": bucket_available,
        "high_intensity_humor_seed_rows": len(high_intensity_seed_rows),
        "high_intensity_humor_type_distribution": dict(Counter(r.get("teacher_humor_type") for r in high_intensity_seed_rows)),
        "hard_negative_seed_rows": len(hard_negative_seed_rows),
        "hard_negative_category_distribution": dict(Counter(r.get("hard_negative_category") for r in hard_negative_seed_rows)),
        "presence_pseudo_rows": len(presence_pseudo_rows),
        "presence_pseudo_distribution": dict(Counter(r["pseudo_humor_presence"] for r in presence_pseudo_rows)),
        "presence_balanced_rows": len(presence_balanced_rows),
        "presence_balanced_available_distribution": presence_available_counts,
        "presence_balanced_selected_distribution": presence_selected_counts,
        "type_pseudo_rows": len(type_pseudo_rows),
        "type_pseudo_distribution": dict(Counter(r["pseudo_humor_type"] for r in type_pseudo_rows)),
        "type_class_capped_rows": len(type_balanced_rows),
        "type_class_available_distribution": type_available_counts,
        "type_class_selected_distribution": type_selected_counts,
        "excluded_from_presence_pseudo_rows": len(rows) - len(presence_pseudo_rows),
        "excluded_from_type_pseudo_rows": len(rows) - len(type_pseudo_rows),
        "output_files": {
            "validation_sample": str(validation_path),
            "presence_pseudo": str(presence_pseudo_path),
            "type_pseudo": str(type_pseudo_path),
            "presence_balanced": str(presence_balanced_path),
            "type_class_capped": str(type_balanced_path),
            "high_intensity_humor_seed": str(high_intensity_path),
            "hard_negative_non_humor_seed": str(hard_negative_path),
        },
        "recommended_next_step": "Use full-data high-intensity humor seeds plus hard-negative non-humor seeds for TF-IDF baseline and later RoBERTa/BERTweet comparison. Do not treat pseudo-labels as gold labels.",
    }
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))

    if args.min_master_rows and len(rows) < args.min_master_rows:
        sys.exit(1)


if __name__ == "__main__":
    main()
