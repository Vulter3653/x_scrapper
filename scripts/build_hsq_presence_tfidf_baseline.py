#!/usr/bin/env python3
"""Train a TF-IDF Logistic Regression baseline from HSQ seed datasets.

This script implements option 2 in the humor classification pipeline:
1. combine high-intensity humor seeds and hard-negative non-humor seeds;
2. create stratified train/test splits;
3. train a lightweight TF-IDF Logistic Regression classifier;
4. evaluate against teacher pseudo-labels and export diagnostics.

Important: the evaluation target is the HSQ teacher pseudo-label, not a human-gold
label. Human validation must be used before claiming final classification accuracy.
"""

import argparse
import csv
import json
import random
from collections import Counter
from pathlib import Path

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    precision_recall_fscore_support,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline

COMBINED_FIELDS = [
    "global_post_id",
    "text",
    "presence_label",
    "seed_bucket",
    "seed_strength_score",
    "teacher_presence_confidence",
    "teacher_humor_type",
    "teacher_type_confidence",
    "target_of_humor",
    "humor_function",
    "harm_potential",
    "key_cues",
    "hard_negative_category",
    "sample_group",
    "company_name",
    "created_at",
    "source_file",
]

PREDICTION_FIELDS = COMBINED_FIELDS + [
    "predicted_presence_label",
    "predicted_humor_probability",
    "prediction_correct",
]


def read_csv(path):
    if not path.exists():
        raise FileNotFoundError(f"CSV not found: {path}")
    with path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            raise ValueError(f"CSV has no header: {path}")
        return list(reader)


def write_csv(path, rows, fieldnames):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def as_float(value, default=0.0):
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def normalize_text(text):
    return " ".join((text or "").split())


def row_from_seed(row, label, source_file):
    return {
        "global_post_id": row.get("global_post_id", ""),
        "text": normalize_text(row.get("text", "")),
        "presence_label": label,
        "seed_bucket": row.get("seed_bucket", ""),
        "seed_strength_score": row.get("seed_strength_score", ""),
        "teacher_presence_confidence": row.get("teacher_presence_confidence", ""),
        "teacher_humor_type": row.get("teacher_humor_type", ""),
        "teacher_type_confidence": row.get("teacher_type_confidence", ""),
        "target_of_humor": row.get("target_of_humor", ""),
        "humor_function": row.get("humor_function", ""),
        "harm_potential": row.get("harm_potential", ""),
        "key_cues": row.get("key_cues", ""),
        "hard_negative_category": row.get("hard_negative_category", ""),
        "sample_group": row.get("sample_group", ""),
        "company_name": row.get("company_name", ""),
        "created_at": row.get("created_at", ""),
        "source_file": source_file,
    }


def dedupe_by_id(rows):
    seen = set()
    deduped = []
    duplicate_count = 0
    for idx, row in enumerate(rows):
        gid = row.get("global_post_id") or f"missing_id_{idx}"
        if gid in seen:
            duplicate_count += 1
            continue
        seen.add(gid)
        deduped.append(row)
    return deduped, duplicate_count


def sample_rows(rows, limit, rng):
    rows = list(rows)
    if limit <= 0 or len(rows) <= limit:
        return rows
    rng.shuffle(rows)
    return rows[:limit]


def top_features_from_model(model, topn):
    vectorizer = model.named_steps["tfidf"]
    classifier = model.named_steps["clf"]
    features = vectorizer.get_feature_names_out()
    classes = list(classifier.classes_)
    coefs = classifier.coef_[0]

    # In binary LogisticRegression, coef_ corresponds to classifier.classes_[1].
    positive_label = classes[1]
    negative_label = classes[0]
    top_positive_idx = coefs.argsort()[::-1][:topn]
    top_negative_idx = coefs.argsort()[:topn]

    rows = []
    for idx in top_positive_idx:
        rows.append({
            "direction": f"toward_{positive_label}",
            "feature": features[idx],
            "coefficient": f"{coefs[idx]:.8f}",
        })
    for idx in top_negative_idx:
        rows.append({
            "direction": f"toward_{negative_label}",
            "feature": features[idx],
            "coefficient": f"{coefs[idx]:.8f}",
        })
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--humor-seed", type=Path, required=True)
    parser.add_argument("--hard-negative-seed", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--test-size", type=float, default=0.25)
    parser.add_argument("--random-state", type=int, default=20260613)
    parser.add_argument("--min-positive", type=int, default=50)
    parser.add_argument("--min-negative", type=int, default=50)
    parser.add_argument("--max-negative-ratio", type=float, default=4.0)
    parser.add_argument("--max-features", type=int, default=20000)
    parser.add_argument("--ngram-max", type=int, default=2)
    parser.add_argument("--top-features", type=int, default=40)
    args = parser.parse_args()

    if not (0.05 <= args.test_size <= 0.50):
        raise ValueError("--test-size must be between 0.05 and 0.50")
    if args.max_negative_ratio < 1.0:
        raise ValueError("--max-negative-ratio must be at least 1.0")

    rng = random.Random(args.random_state)
    humor_raw = read_csv(args.humor_seed)
    negative_raw = read_csv(args.hard_negative_seed)

    humor_rows = [row_from_seed(r, "humor", args.humor_seed.name) for r in humor_raw if normalize_text(r.get("text", ""))]
    negative_rows = [row_from_seed(r, "non_humor", args.hard_negative_seed.name) for r in negative_raw if normalize_text(r.get("text", ""))]

    humor_rows, humor_duplicates = dedupe_by_id(humor_rows)
    negative_rows, negative_duplicates = dedupe_by_id(negative_rows)

    if len(humor_rows) < args.min_positive:
        raise SystemExit(f"Not enough humor seed rows: {len(humor_rows)} < {args.min_positive}")
    if len(negative_rows) < args.min_negative:
        raise SystemExit(f"Not enough hard-negative rows: {len(negative_rows)} < {args.min_negative}")

    max_negative = max(args.min_negative, int(len(humor_rows) * args.max_negative_ratio))
    selected_humor = list(humor_rows)
    selected_negative = sample_rows(negative_rows, max_negative, rng)
    combined_rows = selected_humor + selected_negative
    rng.shuffle(combined_rows)

    labels = [r["presence_label"] for r in combined_rows]
    texts = [r["text"] for r in combined_rows]

    train_rows, test_rows = train_test_split(
        combined_rows,
        test_size=args.test_size,
        random_state=args.random_state,
        stratify=labels,
    )
    x_train = [r["text"] for r in train_rows]
    y_train = [r["presence_label"] for r in train_rows]
    x_test = [r["text"] for r in test_rows]
    y_test = [r["presence_label"] for r in test_rows]

    model = Pipeline([
        ("tfidf", TfidfVectorizer(
            lowercase=True,
            strip_accents="unicode",
            ngram_range=(1, args.ngram_max),
            min_df=2,
            max_df=0.95,
            max_features=args.max_features,
            sublinear_tf=True,
        )),
        ("clf", LogisticRegression(
            max_iter=2000,
            class_weight="balanced",
            solver="liblinear",
            random_state=args.random_state,
        )),
    ])
    model.fit(x_train, y_train)

    predictions = model.predict(x_test)
    probabilities = model.predict_proba(x_test)
    class_index = {label: idx for idx, label in enumerate(model.classes_)}
    humor_idx = class_index.get("humor")

    precision_macro, recall_macro, f1_macro, _ = precision_recall_fscore_support(
        y_test, predictions, average="macro", zero_division=0
    )
    precision_weighted, recall_weighted, f1_weighted, _ = precision_recall_fscore_support(
        y_test, predictions, average="weighted", zero_division=0
    )
    labels_order = ["humor", "non_humor"]
    cm = confusion_matrix(y_test, predictions, labels=labels_order)
    report = classification_report(y_test, predictions, labels=labels_order, output_dict=True, zero_division=0)

    prediction_rows = []
    for row, pred, prob in zip(test_rows, predictions, probabilities):
        out = dict(row)
        out["predicted_presence_label"] = pred
        out["predicted_humor_probability"] = f"{prob[humor_idx]:.8f}" if humor_idx is not None else ""
        out["prediction_correct"] = str(pred == row["presence_label"]).lower()
        prediction_rows.append(out)

    report_rows = []
    for label, metrics in report.items():
        if isinstance(metrics, dict):
            report_rows.append({
                "label": label,
                "precision": metrics.get("precision", 0.0),
                "recall": metrics.get("recall", 0.0),
                "f1_score": metrics.get("f1-score", 0.0),
                "support": metrics.get("support", 0.0),
            })

    cm_rows = []
    for i, actual in enumerate(labels_order):
        for j, predicted in enumerate(labels_order):
            cm_rows.append({"actual_label": actual, "predicted_label": predicted, "count": int(cm[i][j])})

    top_feature_rows = top_features_from_model(model, args.top_features)

    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    combined_path = output_dir / "hsq_train_presence_seed_combined.csv"
    train_path = output_dir / "hsq_train_presence_tfidf_train.csv"
    test_path = output_dir / "hsq_train_presence_tfidf_test.csv"
    predictions_path = output_dir / "hsq_presence_tfidf_predictions.csv"
    report_path = output_dir / "hsq_presence_tfidf_classification_report.csv"
    cm_path = output_dir / "hsq_presence_tfidf_confusion_matrix.csv"
    top_features_path = output_dir / "hsq_presence_tfidf_top_features.csv"
    summary_path = output_dir / "hsq_presence_tfidf_summary.json"

    write_csv(combined_path, combined_rows, COMBINED_FIELDS)
    write_csv(train_path, train_rows, COMBINED_FIELDS)
    write_csv(test_path, test_rows, COMBINED_FIELDS)
    write_csv(predictions_path, prediction_rows, PREDICTION_FIELDS)
    write_csv(report_path, report_rows, ["label", "precision", "recall", "f1_score", "support"])
    write_csv(cm_path, cm_rows, ["actual_label", "predicted_label", "count"])
    write_csv(top_features_path, top_feature_rows, ["direction", "feature", "coefficient"])

    summary = {
        "task": "HSQ presence TF-IDF Logistic Regression baseline",
        "important_note": "Metrics are evaluated against HSQ teacher pseudo-labels, not human-gold labels.",
        "input_humor_seed": str(args.humor_seed),
        "input_hard_negative_seed": str(args.hard_negative_seed),
        "raw_humor_rows": len(humor_raw),
        "raw_hard_negative_rows": len(negative_raw),
        "deduped_humor_rows": len(humor_rows),
        "deduped_hard_negative_rows": len(negative_rows),
        "humor_duplicate_rows_removed": humor_duplicates,
        "hard_negative_duplicate_rows_removed": negative_duplicates,
        "selected_humor_rows": len(selected_humor),
        "selected_non_humor_rows": len(selected_negative),
        "combined_rows": len(combined_rows),
        "combined_distribution": dict(Counter(labels)),
        "train_rows": len(train_rows),
        "train_distribution": dict(Counter(y_train)),
        "test_rows": len(test_rows),
        "test_distribution": dict(Counter(y_test)),
        "test_size": args.test_size,
        "max_negative_ratio": args.max_negative_ratio,
        "max_features": args.max_features,
        "ngram_range": [1, args.ngram_max],
        "accuracy": accuracy_score(y_test, predictions),
        "macro_precision": precision_macro,
        "macro_recall": recall_macro,
        "macro_f1": f1_macro,
        "weighted_precision": precision_weighted,
        "weighted_recall": recall_weighted,
        "weighted_f1": f1_weighted,
        "confusion_matrix_labels": labels_order,
        "confusion_matrix": cm.tolist(),
        "output_files": {
            "combined": str(combined_path),
            "train": str(train_path),
            "test": str(test_path),
            "predictions": str(predictions_path),
            "classification_report": str(report_path),
            "confusion_matrix": str(cm_path),
            "top_features": str(top_features_path),
            "summary": str(summary_path),
        },
        "recommended_next_step": "Inspect false positives/false negatives and top features. Then compare with human-coded validation sample before trying RoBERTa/BERTweet.",
    }
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
