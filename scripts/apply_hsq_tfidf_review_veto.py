#!/usr/bin/env python3
"""Apply a TF-IDF review/veto layer to an HSQ full-chain master dataset.

This script keeps the HSQ codebook classifier as the primary classifier and uses
an empirically calibrated TF-IDF Logistic Regression model only as a review/veto
signal. It is not intended to replace the HSQ classifier.

Decision rule:
- If HSQ says humor but TF-IDF humor probability is below the operating threshold,
  demote final_humor_presence to ambiguous_or_review and mark review.
- If HSQ says ambiguous and TF-IDF probability is high, keep ambiguous but mark a
  humor-candidate review signal.
- If HSQ says non_humor and TF-IDF probability is high, keep non_humor but mark a
  possible false-negative review signal.
"""

import argparse
import csv
import json
import random
from collections import Counter
from pathlib import Path

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

OUTPUT_EXTRA_FIELDS = [
    "tfidf_humor_probability",
    "tfidf_operating_threshold",
    "tfidf_review_signal",
    "final_humor_presence",
    "final_humor_type",
    "final_humor_presence_source",
    "final_humor_review_flag",
    "final_humor_review_reason",
]


def read_csv(path):
    if not path.exists():
        raise FileNotFoundError(f"CSV not found: {path}")
    with path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            raise ValueError(f"CSV has no header: {path}")
        return list(reader), list(reader.fieldnames)


def write_csv(path, rows, fieldnames):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def normalize_text(text):
    return " ".join((text or "").split())


def dedupe_by_id(rows):
    seen = set()
    out = []
    dup = 0
    for i, row in enumerate(rows):
        gid = row.get("global_post_id") or f"missing_id_{i}"
        if gid in seen:
            dup += 1
            continue
        seen.add(gid)
        out.append(row)
    return out, dup


def sample_rows(rows, limit, rng):
    rows = list(rows)
    if limit <= 0 or len(rows) <= limit:
        return rows
    rng.shuffle(rows)
    return rows[:limit]


def seed_to_training_rows(humor_seed_rows, hard_negative_rows, max_negative_ratio, rng):
    humor = []
    for row in humor_seed_rows:
        text = normalize_text(row.get("text", ""))
        if text:
            humor.append({"text": text, "label": "humor", "global_post_id": row.get("global_post_id", "")})

    non_humor = []
    for row in hard_negative_rows:
        text = normalize_text(row.get("text", ""))
        if text:
            non_humor.append({"text": text, "label": "non_humor", "global_post_id": row.get("global_post_id", "")})

    humor, humor_dup = dedupe_by_id(humor)
    non_humor, non_dup = dedupe_by_id(non_humor)

    max_negative = max(1, int(len(humor) * max_negative_ratio))
    non_humor = sample_rows(non_humor, max_negative, rng)
    combined = humor + non_humor
    rng.shuffle(combined)
    return combined, humor_dup, non_dup


def train_tfidf(training_rows, max_features, ngram_max, random_state):
    texts = [r["text"] for r in training_rows]
    labels = [r["label"] for r in training_rows]
    if len(set(labels)) != 2:
        raise ValueError(f"Expected both humor and non_humor labels, got {sorted(set(labels))}")

    model = Pipeline([
        ("tfidf", TfidfVectorizer(
            lowercase=True,
            strip_accents="unicode",
            ngram_range=(1, ngram_max),
            min_df=2,
            max_df=0.95,
            max_features=max_features,
            sublinear_tf=True,
        )),
        ("clf", LogisticRegression(
            max_iter=2000,
            class_weight="balanced",
            solver="liblinear",
            random_state=random_state,
        )),
    ])
    model.fit(texts, labels)
    return model


def final_decision(row, prob, threshold, candidate_threshold):
    hsq_presence = row.get("humor_presence", "")
    hsq_type = row.get("humor_type", "")

    if hsq_presence == "humor" and prob < threshold:
        return {
            "tfidf_review_signal": "hsq_humor_below_tfidf_threshold",
            "final_humor_presence": "ambiguous_or_review",
            "final_humor_type": "ambiguous_or_review",
            "final_humor_presence_source": "hsq_tfidf_review_veto",
            "final_humor_review_flag": "true",
            "final_humor_review_reason": "HSQ labeled humor, but TF-IDF hard-negative model assigned humor probability below the calibrated operating threshold.",
        }

    if hsq_presence == "ambiguous" and prob >= candidate_threshold:
        return {
            "tfidf_review_signal": "hsq_ambiguous_tfidf_humor_candidate",
            "final_humor_presence": "ambiguous",
            "final_humor_type": "ambiguous_or_review",
            "final_humor_presence_source": "hsq_primary_tfidf_candidate_signal",
            "final_humor_review_flag": "true",
            "final_humor_review_reason": "HSQ labeled ambiguous, but TF-IDF probability is high enough to mark as a humor candidate for review.",
        }

    if hsq_presence == "non_humor" and prob >= candidate_threshold:
        return {
            "tfidf_review_signal": "hsq_non_humor_tfidf_humor_candidate",
            "final_humor_presence": "non_humor",
            "final_humor_type": "not_applicable",
            "final_humor_presence_source": "hsq_primary_tfidf_candidate_signal",
            "final_humor_review_flag": "true",
            "final_humor_review_reason": "HSQ labeled non_humor, but TF-IDF probability is high enough to mark as a possible false-negative review case.",
        }

    if hsq_presence == "humor":
        return {
            "tfidf_review_signal": "hsq_tfidf_aligned_humor",
            "final_humor_presence": "humor",
            "final_humor_type": hsq_type or "ambiguous_or_review",
            "final_humor_presence_source": "hsq_primary_tfidf_aligned",
            "final_humor_review_flag": row.get("humor_type_review_flag", "false"),
            "final_humor_review_reason": row.get("humor_type_reason", "") if row.get("humor_type_review_flag") == "true" else "",
        }

    if hsq_presence == "non_humor":
        return {
            "tfidf_review_signal": "hsq_tfidf_aligned_non_humor",
            "final_humor_presence": "non_humor",
            "final_humor_type": "not_applicable",
            "final_humor_presence_source": "hsq_primary_tfidf_aligned",
            "final_humor_review_flag": "false",
            "final_humor_review_reason": "",
        }

    return {
        "tfidf_review_signal": "hsq_ambiguous_tfidf_not_high",
        "final_humor_presence": "ambiguous",
        "final_humor_type": "ambiguous_or_review",
        "final_humor_presence_source": "hsq_primary_tfidf_aligned",
        "final_humor_review_flag": "true",
        "final_humor_review_reason": "HSQ humor presence was ambiguous and TF-IDF did not provide a high-confidence humor candidate signal.",
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--master", type=Path, required=True)
    parser.add_argument("--humor-seed", type=Path, required=True)
    parser.add_argument("--hard-negative-seed", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--threshold", type=float, default=0.51455)
    parser.add_argument("--candidate-threshold", type=float, default=0.70)
    parser.add_argument("--max-negative-ratio", type=float, default=4.0)
    parser.add_argument("--max-features", type=int, default=20000)
    parser.add_argument("--ngram-max", type=int, default=2)
    parser.add_argument("--random-state", type=int, default=20260613)
    args = parser.parse_args()

    rng = random.Random(args.random_state)
    master_rows, master_fields = read_csv(args.master)
    humor_seed_rows, _ = read_csv(args.humor_seed)
    hard_negative_rows, _ = read_csv(args.hard_negative_seed)

    training_rows, humor_dup, non_dup = seed_to_training_rows(
        humor_seed_rows,
        hard_negative_rows,
        args.max_negative_ratio,
        rng,
    )
    if len(training_rows) < 100:
        raise SystemExit(f"Training set is too small for review/veto model: {len(training_rows)} rows")

    model = train_tfidf(training_rows, args.max_features, args.ngram_max, args.random_state)
    class_index = {label: idx for idx, label in enumerate(model.classes_)}
    humor_idx = class_index.get("humor")
    if humor_idx is None:
        raise SystemExit("TF-IDF model does not expose a humor probability.")

    texts = [normalize_text(row.get("text", "")) for row in master_rows]
    probabilities = model.predict_proba(texts)

    out_rows = []
    for row, prob_vec in zip(master_rows, probabilities):
        prob = float(prob_vec[humor_idx])
        decision = final_decision(row, prob, args.threshold, args.candidate_threshold)
        out = dict(row)
        out["tfidf_humor_probability"] = f"{prob:.8f}"
        out["tfidf_operating_threshold"] = f"{args.threshold:.6f}"
        out.update(decision)
        out_rows.append(out)

    fieldnames = list(master_fields)
    for field in OUTPUT_EXTRA_FIELDS:
        if field not in fieldnames:
            fieldnames.append(field)

    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    master_out = output_dir / "humor_full_chain_master_hsq_tfidf_review_veto.csv"
    summary_out = output_dir / "hsq_tfidf_review_veto_summary.json"
    signal_csv = output_dir / "hsq_tfidf_review_veto_signal_summary.csv"

    write_csv(master_out, out_rows, fieldnames)

    signal_counts = Counter(row.get("tfidf_review_signal", "") for row in out_rows)
    hsq_counts = Counter(row.get("humor_presence", "") for row in out_rows)
    final_counts = Counter(row.get("final_humor_presence", "") for row in out_rows)
    review_counts = Counter(row.get("final_humor_review_flag", "") for row in out_rows)
    demoted = sum(1 for row in out_rows if row.get("tfidf_review_signal") == "hsq_humor_below_tfidf_threshold")
    high_candidates = sum(1 for row in out_rows if row.get("tfidf_review_signal") in {"hsq_ambiguous_tfidf_humor_candidate", "hsq_non_humor_tfidf_humor_candidate"})

    signal_rows = []
    for signal, count in sorted(signal_counts.items()):
        signal_rows.append({"tfidf_review_signal": signal, "count": count, "rate": count / len(out_rows) if out_rows else 0.0})
    write_csv(signal_csv, signal_rows, ["tfidf_review_signal", "count", "rate"])

    summary = {
        "task": "HSQ primary classifier plus TF-IDF review/veto layer",
        "important_note": "TF-IDF is used only as a review/veto signal. It does not replace the HSQ codebook classifier.",
        "master_rows": len(master_rows),
        "humor_seed_rows": len(humor_seed_rows),
        "hard_negative_seed_rows": len(hard_negative_rows),
        "training_rows_used": len(training_rows),
        "training_distribution": dict(Counter(r["label"] for r in training_rows)),
        "humor_seed_duplicates_removed": humor_dup,
        "hard_negative_duplicates_removed": non_dup,
        "tfidf_operating_threshold": args.threshold,
        "tfidf_candidate_threshold": args.candidate_threshold,
        "hsq_presence_distribution": dict(hsq_counts),
        "final_humor_presence_distribution": dict(final_counts),
        "final_humor_review_flag_distribution": dict(review_counts),
        "tfidf_review_signal_distribution": dict(signal_counts),
        "hsq_humor_demoted_to_review_rows": demoted,
        "tfidf_high_humor_candidate_review_rows": high_candidates,
        "output_files": {
            "master": str(master_out),
            "summary": str(summary_out),
            "signal_summary": str(signal_csv),
        },
        "recommended_next_step": "Inspect demoted HSQ humor rows and high-probability TF-IDF candidate rows before running the RoBERTa/BERTweet-lite experiment.",
    }
    summary_out.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
