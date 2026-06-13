#!/usr/bin/env python3
"""Train a TF-IDF Logistic Regression baseline from HSQ seed datasets.

This script implements option 2 in the humor classification pipeline:
1. combine high-intensity humor seeds and hard-negative non-humor seeds;
2. create stratified train/test splits;
3. train a lightweight TF-IDF Logistic Regression classifier;
4. evaluate against teacher pseudo-labels and export diagnostics;
5. search for an operating threshold using a nested coarse-to-fine procedure.

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

THRESHOLD_SWEEP_FIELDS = [
    "stage",
    "threshold",
    "accuracy",
    "macro_precision",
    "macro_recall",
    "macro_f1",
    "weighted_precision",
    "weighted_recall",
    "weighted_f1",
    "humor_precision",
    "humor_recall",
    "humor_f1",
    "humor_support",
    "non_humor_precision",
    "non_humor_recall",
    "non_humor_f1",
    "non_humor_support",
    "true_humor_pred_humor",
    "true_humor_pred_non_humor",
    "true_non_humor_pred_humor",
    "true_non_humor_pred_non_humor",
]

RECOMMENDATION_FIELDS = [
    "recommendation_name",
    "selection_rule",
    "threshold",
    "accuracy",
    "macro_f1",
    "humor_precision",
    "humor_recall",
    "humor_f1",
    "non_humor_precision",
    "non_humor_recall",
    "non_humor_f1",
    "false_positive_count",
    "false_negative_count",
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


def label_from_threshold(probability, threshold):
    return "humor" if probability >= threshold else "non_humor"


def evaluate_threshold(y_true, humor_probabilities, threshold, stage):
    threshold = min(max(float(threshold), 0.0), 1.0)
    y_pred = [label_from_threshold(prob, threshold) for prob in humor_probabilities]
    labels_order = ["humor", "non_humor"]
    cm = confusion_matrix(y_true, y_pred, labels=labels_order)
    report = classification_report(y_true, y_pred, labels=labels_order, output_dict=True, zero_division=0)
    precision_macro, recall_macro, f1_macro, _ = precision_recall_fscore_support(
        y_true, y_pred, average="macro", zero_division=0
    )
    precision_weighted, recall_weighted, f1_weighted, _ = precision_recall_fscore_support(
        y_true, y_pred, average="weighted", zero_division=0
    )
    h = report.get("humor", {})
    nh = report.get("non_humor", {})
    return {
        "stage": stage,
        "threshold": f"{threshold:.6f}",
        "accuracy": accuracy_score(y_true, y_pred),
        "macro_precision": precision_macro,
        "macro_recall": recall_macro,
        "macro_f1": f1_macro,
        "weighted_precision": precision_weighted,
        "weighted_recall": recall_weighted,
        "weighted_f1": f1_weighted,
        "humor_precision": h.get("precision", 0.0),
        "humor_recall": h.get("recall", 0.0),
        "humor_f1": h.get("f1-score", 0.0),
        "humor_support": h.get("support", 0.0),
        "non_humor_precision": nh.get("precision", 0.0),
        "non_humor_recall": nh.get("recall", 0.0),
        "non_humor_f1": nh.get("f1-score", 0.0),
        "non_humor_support": nh.get("support", 0.0),
        "true_humor_pred_humor": int(cm[0][0]),
        "true_humor_pred_non_humor": int(cm[0][1]),
        "true_non_humor_pred_humor": int(cm[1][0]),
        "true_non_humor_pred_non_humor": int(cm[1][1]),
    }


def threshold_range(start, stop, step):
    scale = int(round(1 / step))
    start_i = int(round(start * scale))
    stop_i = int(round(stop * scale))
    return [round(i / scale, 6) for i in range(start_i, stop_i + 1)]


def as_threshold(row):
    return as_float(row.get("threshold"))


def metric_change_score(left, right):
    return (
        abs(as_float(left["humor_precision"]) - as_float(right["humor_precision"]))
        + abs(as_float(left["humor_recall"]) - as_float(right["humor_recall"]))
        + abs(as_float(left["macro_f1"]) - as_float(right["macro_f1"]))
    )


def largest_change_interval(rows):
    if len(rows) < 2:
        return {"left": 0.0, "right": 1.0, "change_score": 0.0}
    best_left = rows[0]
    best_right = rows[1]
    best_score = -1.0
    for left, right in zip(rows[:-1], rows[1:]):
        score = metric_change_score(left, right)
        if score > best_score:
            best_left, best_right, best_score = left, right, score
    return {"left": as_threshold(best_left), "right": as_threshold(best_right), "change_score": best_score}


def dedupe_threshold_rows(rows):
    out = {}
    for row in rows:
        key = (row["stage"], row["threshold"])
        out[key] = row
    return list(out.values())


def build_nested_threshold_sweep(y_true, humor_probabilities, precision_floor, recall_floor, relaxed_recall_floor):
    # 1) Full coarse check from 0.10 through 1.00. This is a diagnostic grid,
    # not an assumption that 0.50 is the balanced point.
    coarse_thresholds = threshold_range(0.10, 1.00, 0.10)
    coarse_rows = [evaluate_threshold(y_true, humor_probabilities, t, "coarse_0.10_full_0.10_to_1.00") for t in coarse_thresholds]
    coarse_interval = largest_change_interval(coarse_rows)

    # 2) Refine the largest-change 0.10 interval at 0.01 resolution.
    fine01_thresholds = threshold_range(coarse_interval["left"], coarse_interval["right"], 0.01)
    fine01_rows = [evaluate_threshold(y_true, humor_probabilities, t, "fine_0.01_largest_0.10_interval") for t in fine01_thresholds]
    fine01_interval = largest_change_interval(fine01_rows)

    # 3) Refine the largest-change 0.01 interval at 0.001 resolution.
    fine001_thresholds = threshold_range(fine01_interval["left"], fine01_interval["right"], 0.001)
    fine001_rows = [evaluate_threshold(y_true, humor_probabilities, t, "fine_0.001_largest_0.01_interval") for t in fine001_thresholds]
    fine001_interval = largest_change_interval(fine001_rows)

    # 4) Refine the largest-change 0.001 interval at 0.0001 resolution.
    fine0001_thresholds = threshold_range(fine001_interval["left"], fine001_interval["right"], 0.0001)
    fine0001_rows = [evaluate_threshold(y_true, humor_probabilities, t, "fine_0.0001_largest_0.001_interval") for t in fine0001_thresholds]
    fine0001_interval = largest_change_interval(fine0001_rows)

    # 5) Exact diagnostic: evaluate every threshold where predictions can actually change.
    unique_probs = sorted(set(round(p, 12) for p in humor_probabilities))
    exact_thresholds = {0.0, 1.0}
    exact_thresholds.update(unique_probs)
    for left, right in zip(unique_probs[:-1], unique_probs[1:]):
        exact_thresholds.add(round((left + right) / 2.0, 12))
    exact_rows = [evaluate_threshold(y_true, humor_probabilities, t, "exact_unique_probability") for t in sorted(exact_thresholds)]

    all_rows = dedupe_threshold_rows(coarse_rows + fine01_rows + fine001_rows + fine0001_rows + exact_rows)
    recommendations = choose_recommendations(all_rows, precision_floor, recall_floor, relaxed_recall_floor)
    selected = choose_operating_recommendation(recommendations)

    metadata = {
        "default_threshold_note": "0.50 is only the default probability cutoff for binary classification; it is not assumed to be the balanced operating point.",
        "nested_search_design": [
            "coarse 0.10 grid over 0.10-1.00",
            "0.01 grid inside the largest-change 0.10 interval",
            "0.001 grid inside the largest-change 0.01 interval",
            "0.0001 grid inside the largest-change 0.001 interval",
            "exact sweep over unique predicted probabilities and midpoints",
        ],
        "coarse_largest_change_interval": coarse_interval,
        "fine01_largest_change_interval": fine01_interval,
        "fine001_largest_change_interval": fine001_interval,
        "fine0001_largest_change_interval": fine0001_interval,
        "coarse_threshold_count": len(coarse_rows),
        "fine01_threshold_count": len(fine01_rows),
        "fine001_threshold_count": len(fine001_rows),
        "fine0001_threshold_count": len(fine0001_rows),
        "exact_threshold_count": len(exact_rows),
        "all_threshold_count": len(all_rows),
        "selected_threshold_source": selected.get("stage", "") if selected else "",
    }
    return all_rows, recommendations, selected, metadata


def row_sort_tuple(row):
    return (
        as_float(row.get("macro_f1")),
        as_float(row.get("humor_f1")),
        as_float(row.get("humor_precision")),
        as_float(row.get("humor_recall")),
        -abs(as_float(row.get("threshold")) - 0.50),
    )


def best_row(rows, predicate=None, key_func=None):
    candidates = [r for r in rows if predicate(r)] if predicate else list(rows)
    if not candidates:
        return None
    return max(candidates, key=key_func or row_sort_tuple)


def choose_recommendations(rows, precision_floor, recall_floor, relaxed_recall_floor):
    strict = best_row(
        rows,
        predicate=lambda r: as_float(r["humor_precision"]) >= precision_floor and as_float(r["humor_recall"]) >= recall_floor,
        key_func=row_sort_tuple,
    )
    relaxed = best_row(
        rows,
        predicate=lambda r: as_float(r["humor_precision"]) >= precision_floor and as_float(r["humor_recall"]) >= relaxed_recall_floor,
        key_func=row_sort_tuple,
    )
    recall_constrained = best_row(
        rows,
        predicate=lambda r: as_float(r["humor_recall"]) >= recall_floor,
        key_func=lambda r: (
            as_float(r["humor_precision"]),
            as_float(r["macro_f1"]),
            as_float(r["humor_f1"]),
            -abs(as_float(r["threshold"]) - 0.50),
        ),
    )
    precision_constrained = best_row(
        rows,
        predicate=lambda r: as_float(r["humor_precision"]) >= precision_floor,
        key_func=lambda r: (
            as_float(r["humor_recall"]),
            as_float(r["macro_f1"]),
            as_float(r["humor_f1"]),
            -abs(as_float(r["threshold"]) - 0.50),
        ),
    )
    macro_best = best_row(rows, key_func=lambda r: (
        as_float(r["macro_f1"]),
        as_float(r["humor_f1"]),
        as_float(r["humor_precision"]),
        as_float(r["humor_recall"]),
        -abs(as_float(r["threshold"]) - 0.50),
    ))
    humor_f1_best = best_row(rows, key_func=lambda r: (
        as_float(r["humor_f1"]),
        as_float(r["macro_f1"]),
        as_float(r["humor_precision"]),
        as_float(r["humor_recall"]),
        -abs(as_float(r["threshold"]) - 0.50),
    ))

    specs = [
        ("best_strict_balance", f"humor_precision>={precision_floor} and humor_recall>={recall_floor}; maximize macro_f1", strict),
        ("best_relaxed_balance", f"humor_precision>={precision_floor} and humor_recall>={relaxed_recall_floor}; maximize macro_f1", relaxed),
        ("best_precision_given_recall_floor", f"humor_recall>={recall_floor}; maximize humor_precision", recall_constrained),
        ("best_recall_given_precision_floor", f"humor_precision>={precision_floor}; maximize humor_recall", precision_constrained),
        ("best_macro_f1", "maximize macro_f1", macro_best),
        ("best_humor_f1", "maximize humor_f1", humor_f1_best),
    ]
    out = []
    for name, rule, row in specs:
        if not row:
            continue
        rec = dict(row)
        rec["recommendation_name"] = name
        rec["selection_rule"] = rule
        rec["false_positive_count"] = row["true_non_humor_pred_humor"]
        rec["false_negative_count"] = row["true_humor_pred_non_humor"]
        out.append(rec)
    return out


def choose_operating_recommendation(recommendations):
    priority = ["best_strict_balance", "best_relaxed_balance", "best_macro_f1", "best_humor_f1"]
    by_name = {r["recommendation_name"]: r for r in recommendations}
    for name in priority:
        if name in by_name:
            return by_name[name]
    return recommendations[0] if recommendations else None


def make_prediction_rows(test_rows, probabilities, humor_idx, threshold):
    prediction_rows = []
    for row, prob in zip(test_rows, probabilities):
        humor_probability = float(prob[humor_idx]) if humor_idx is not None else 0.0
        pred = label_from_threshold(humor_probability, threshold)
        out = dict(row)
        out["predicted_presence_label"] = pred
        out["predicted_humor_probability"] = f"{humor_probability:.8f}"
        out["prediction_correct"] = str(pred == row["presence_label"]).lower()
        prediction_rows.append(out)
    return prediction_rows


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
    parser.add_argument("--precision-floor", type=float, default=0.80)
    parser.add_argument("--recall-floor", type=float, default=0.90)
    parser.add_argument("--relaxed-recall-floor", type=float, default=0.85)
    args = parser.parse_args()

    if not (0.05 <= args.test_size <= 0.50):
        raise ValueError("--test-size must be between 0.05 and 0.50")
    if args.max_negative_ratio < 1.0:
        raise ValueError("--max-negative-ratio must be at least 1.0")
    if not (0.0 <= args.precision_floor <= 1.0 and 0.0 <= args.recall_floor <= 1.0 and 0.0 <= args.relaxed_recall_floor <= 1.0):
        raise ValueError("precision/recall floors must be between 0 and 1")

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

    probabilities = model.predict_proba(x_test)
    class_index = {label: idx for idx, label in enumerate(model.classes_)}
    humor_idx = class_index.get("humor")
    if humor_idx is None:
        raise SystemExit("Trained classifier does not expose a humor class probability.")
    humor_probabilities = [float(prob[humor_idx]) for prob in probabilities]

    default_threshold = 0.50
    default_eval = evaluate_threshold(y_test, humor_probabilities, default_threshold, "default_0.50")
    default_predictions = make_prediction_rows(test_rows, probabilities, humor_idx, default_threshold)

    threshold_rows, recommendations, selected_rec, threshold_metadata = build_nested_threshold_sweep(
        y_test,
        humor_probabilities,
        args.precision_floor,
        args.recall_floor,
        args.relaxed_recall_floor,
    )
    threshold_rows.append(default_eval)
    threshold_rows = dedupe_threshold_rows(threshold_rows)
    recommendations = choose_recommendations(threshold_rows, args.precision_floor, args.recall_floor, args.relaxed_recall_floor)
    selected_rec = choose_operating_recommendation(recommendations)
    selected_threshold = as_float(selected_rec["threshold"]) if selected_rec else default_threshold
    calibrated_predictions = make_prediction_rows(test_rows, probabilities, humor_idx, selected_threshold)

    labels_order = ["humor", "non_humor"]
    default_cm = confusion_matrix(y_test, [r["predicted_presence_label"] for r in default_predictions], labels=labels_order)
    default_report = classification_report(
        y_test,
        [r["predicted_presence_label"] for r in default_predictions],
        labels=labels_order,
        output_dict=True,
        zero_division=0,
    )

    report_rows = []
    for label, metrics in default_report.items():
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
            cm_rows.append({"actual_label": actual, "predicted_label": predicted, "count": int(default_cm[i][j])})

    recommendation_rows = []
    for rec in recommendations:
        recommendation_rows.append({
            "recommendation_name": rec.get("recommendation_name", ""),
            "selection_rule": rec.get("selection_rule", ""),
            "threshold": rec.get("threshold", ""),
            "accuracy": rec.get("accuracy", ""),
            "macro_f1": rec.get("macro_f1", ""),
            "humor_precision": rec.get("humor_precision", ""),
            "humor_recall": rec.get("humor_recall", ""),
            "humor_f1": rec.get("humor_f1", ""),
            "non_humor_precision": rec.get("non_humor_precision", ""),
            "non_humor_recall": rec.get("non_humor_recall", ""),
            "non_humor_f1": rec.get("non_humor_f1", ""),
            "false_positive_count": rec.get("false_positive_count", ""),
            "false_negative_count": rec.get("false_negative_count", ""),
        })

    top_feature_rows = top_features_from_model(model, args.top_features)

    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    combined_path = output_dir / "hsq_train_presence_seed_combined.csv"
    train_path = output_dir / "hsq_train_presence_tfidf_train.csv"
    test_path = output_dir / "hsq_train_presence_tfidf_test.csv"
    predictions_path = output_dir / "hsq_presence_tfidf_predictions.csv"
    calibrated_predictions_path = output_dir / "hsq_presence_tfidf_calibrated_predictions.csv"
    report_path = output_dir / "hsq_presence_tfidf_classification_report.csv"
    cm_path = output_dir / "hsq_presence_tfidf_confusion_matrix.csv"
    top_features_path = output_dir / "hsq_presence_tfidf_top_features.csv"
    threshold_sweep_path = output_dir / "hsq_presence_tfidf_threshold_sweep.csv"
    threshold_recommendations_path = output_dir / "hsq_presence_tfidf_threshold_recommendations.csv"
    summary_path = output_dir / "hsq_presence_tfidf_summary.json"

    write_csv(combined_path, combined_rows, COMBINED_FIELDS)
    write_csv(train_path, train_rows, COMBINED_FIELDS)
    write_csv(test_path, test_rows, COMBINED_FIELDS)
    write_csv(predictions_path, default_predictions, PREDICTION_FIELDS)
    write_csv(calibrated_predictions_path, calibrated_predictions, PREDICTION_FIELDS)
    write_csv(report_path, report_rows, ["label", "precision", "recall", "f1_score", "support"])
    write_csv(cm_path, cm_rows, ["actual_label", "predicted_label", "count"])
    write_csv(top_features_path, top_feature_rows, ["direction", "feature", "coefficient"])
    write_csv(threshold_sweep_path, threshold_rows, THRESHOLD_SWEEP_FIELDS)
    write_csv(threshold_recommendations_path, recommendation_rows, RECOMMENDATION_FIELDS)

    summary = {
        "task": "HSQ presence TF-IDF Logistic Regression baseline with nested threshold sweep",
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
        "default_threshold": default_threshold,
        "default_threshold_metrics": default_eval,
        "precision_floor": args.precision_floor,
        "recall_floor": args.recall_floor,
        "relaxed_recall_floor": args.relaxed_recall_floor,
        "threshold_search_metadata": threshold_metadata,
        "selected_operating_threshold": selected_threshold,
        "selected_operating_recommendation": selected_rec,
        "threshold_recommendations": recommendations,
        "output_files": {
            "combined": str(combined_path),
            "train": str(train_path),
            "test": str(test_path),
            "default_predictions": str(predictions_path),
            "calibrated_predictions": str(calibrated_predictions_path),
            "classification_report_default_0_50": str(report_path),
            "confusion_matrix_default_0_50": str(cm_path),
            "top_features": str(top_features_path),
            "threshold_sweep": str(threshold_sweep_path),
            "threshold_recommendations": str(threshold_recommendations_path),
            "summary": str(summary_path),
        },
        "recommended_next_step": "Use selected_operating_threshold as a TF-IDF review/veto calibration candidate, then inspect calibrated false positives/false negatives against the human validation sample before trying RoBERTa/BERTweet.",
    }
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
