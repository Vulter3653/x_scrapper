"""
train_domain_adapted_humor_type_classifier.py

Trains four-type humor classifier on Fortune Top 100 human labels.
Trains only on posts where human_humor_presence == 'humor'.
Requires: fortune100_human_labeling_template.csv with both
          human_humor_presence and human_humor_type filled.

Classes: aggressive | affiliative | self_enhancing | self_defeating

Reports per-class metrics with special attention to aggressive precision/recall
(key for H2/H3 validity) and self_defeating (small expected sample).
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from collections import Counter
from pathlib import Path

PYPACKAGES = Path("/home/user/.local/pypackages")
if str(PYPACKAGES) not in sys.path:
    sys.path.insert(0, str(PYPACKAGES))

import numpy as np
from sklearn.calibration import CalibratedClassifierCV
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score, f1_score, precision_score, recall_score,
    confusion_matrix, classification_report,
)
from sklearn.model_selection import StratifiedKFold
from sklearn.pipeline import Pipeline
from sklearn.svm import LinearSVC

ROOT = Path(__file__).resolve().parents[3]
CI = ROOT / "20260618expand" / "classifier_improvement"

TEMPLATE = CI / "data" / "human_labeling_template" / "fortune100_human_labeling_template.csv"
OUT_METRICS = CI / "results" / "type_classifier_metrics.csv"
OUT_CM = CI / "results" / "confusion_matrices" / "type_confusion_matrix.csv"

CLASSES = ["aggressive", "affiliative", "self_enhancing", "self_defeating"]
# Numeric coding (human input): 1=AGGRESSIVE, 2=AFFILIATIVE, 3=SELF-ENHANCING, 4=SELF-DEFEATING
TYPE_CODE_TO_LABEL = {
    "1": "aggressive",
    "2": "affiliative",
    "3": "self_enhancing",
    "4": "self_defeating",
}
VALID_TYPES = set(TYPE_CODE_TO_LABEL.keys())
RANDOM_STATE = 42

# Provisional acceptance criteria (NOT hard gates — documented minimums)
PROVISIONAL_AGG_PRECISION = 0.60
PROVISIONAL_MACRO_F1 = 0.3448  # Wendy's transfer model baseline
WENDYS_TRANSFER_MACRO_F1 = 0.3448


def preprocess(text: str) -> str:
    text = re.sub(r"https?://\S+", "<URL>", text)
    text = re.sub(r"@\w+", "<MENTION>", text)
    text = re.sub(r"#(\w+)", r"\1", text)
    return re.sub(r"\s+", " ", text.lower()).strip()


def build_logreg_pipeline() -> Pipeline:
    return Pipeline([
        ("tfidf", TfidfVectorizer(
            ngram_range=(1, 2), min_df=1, max_df=0.95,
            sublinear_tf=True, max_features=5000,
        )),
        ("clf", LogisticRegression(
            class_weight="balanced", solver="lbfgs",
            max_iter=2000, random_state=RANDOM_STATE,
        )),
    ])


def build_svm_pipeline() -> Pipeline:
    return Pipeline([
        ("tfidf", TfidfVectorizer(
            ngram_range=(1, 2), min_df=1, max_df=0.95,
            sublinear_tf=True, max_features=5000,
        )),
        ("clf", CalibratedClassifierCV(
            LinearSVC(class_weight="balanced", max_iter=2000, random_state=RANDOM_STATE),
            cv=3,
        )),
    ])


def evaluate_type_pipeline(
    pipe: Pipeline,
    texts: list[str],
    labels: list[str],
    firms: list[str],
    model_name: str,
) -> list[dict]:
    label_dist = Counter(labels)
    n_splits = min(5, min(label_dist.values()))
    if n_splits < 2:
        print(f"  WARNING: cannot CV — min class count={min(label_dist.values())}")
        return []

    skf = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=RANDOM_STATE)
    all_preds, all_true = [], []

    for tr_idx, va_idx in skf.split(texts, labels):
        X_tr = [texts[i] for i in tr_idx]
        X_va = [texts[i] for i in va_idx]
        y_tr = [labels[i] for i in tr_idx]
        y_va = [labels[i] for i in va_idx]
        pipe.fit(X_tr, y_tr)
        preds = pipe.predict(X_va)
        all_preds.extend(preds)
        all_true.extend(y_va)

    results = []
    macro_f1 = f1_score(all_true, all_preds, average="macro", zero_division=0, labels=CLASSES)
    weighted_f1 = f1_score(all_true, all_preds, average="weighted", zero_division=0, labels=CLASSES)
    overall_acc = accuracy_score(all_true, all_preds)

    row = {
        "model": model_name,
        "eval_mode": f"stratified_{n_splits}fold_cv",
        "macro_f1": round(macro_f1, 4),
        "weighted_f1": round(weighted_f1, 4),
        "overall_accuracy": round(overall_acc, 4),
        "n_labeled_humor_posts": len(labels),
        "wendys_transfer_baseline_macro_f1": WENDYS_TRANSFER_MACRO_F1,
        "improves_over_wendys_baseline": "yes" if macro_f1 > WENDYS_TRANSFER_MACRO_F1 else "no",
        "provisional_macro_f1_threshold": PROVISIONAL_MACRO_F1,
    }
    for cls in CLASSES:
        p = precision_score(all_true, all_preds, labels=[cls], average="macro", zero_division=0)
        r = recall_score(all_true, all_preds, labels=[cls], average="macro", zero_division=0)
        f = f1_score(all_true, all_preds, labels=[cls], average="macro", zero_division=0)
        row[f"{cls}_precision"] = round(p, 4)
        row[f"{cls}_recall"] = round(r, 4)
        row[f"{cls}_f1"] = round(f, 4)
    row["aggressive_meets_provisional_precision"] = (
        "yes" if row.get("aggressive_precision", 0) >= PROVISIONAL_AGG_PRECISION
        else "no (provisional)"
    )
    row["label_dist"] = str(dict(Counter(labels)))
    results.append(row)
    return results


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--smoke", action="store_true")
    args = parser.parse_args()

    print("=== train_domain_adapted_humor_type_classifier ===")

    if not TEMPLATE.exists():
        print(f"ERROR: template not found: {TEMPLATE}")
        print("Fill in human_humor_presence and human_humor_type labels first.")
        raise SystemExit(1)

    with open(TEMPLATE, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    # Only train on humor posts (presence=1) with valid type label (1/2/3/4)
    typed = [r for r in rows
             if r.get("human_humor_presence", "").strip() == "1"
             and r.get("human_humor_type", "").strip() in VALID_TYPES]
    print(f"  Humor posts with valid type label: {len(typed)}")

    if len(typed) < 20:
        print("ERROR: fewer than 20 typed rows. Cannot train type classifier.")
        raise SystemExit(1)

    if args.smoke:
        typed = typed[:min(100, len(typed))]
        print(f"  Smoke mode: {len(typed)} rows")

    dist = Counter(
        TYPE_CODE_TO_LABEL[r["human_humor_type"].strip()] for r in typed
    )
    print(f"  Type distribution: {dict(dist)}")

    texts = [preprocess(r["text"]) for r in typed]
    labels = [TYPE_CODE_TO_LABEL[r["human_humor_type"].strip()] for r in typed]
    firms = [r.get("company_name", "") for r in typed]

    all_results = []
    print("  Training LogReg type classifier...")
    lr = build_logreg_pipeline()
    all_results.extend(evaluate_type_pipeline(lr, texts, labels, firms, "logreg_type"))

    print("  Training LinearSVC type classifier...")
    svm = build_svm_pipeline()
    all_results.extend(evaluate_type_pipeline(svm, texts, labels, firms, "linearsvc_type"))

    if all_results:
        OUT_METRICS.parent.mkdir(parents=True, exist_ok=True)
        keys = list(all_results[0].keys())
        with open(OUT_METRICS, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=keys, extrasaction="ignore")
            w.writeheader()
            w.writerows(all_results)
        print(f"  Metrics → {OUT_METRICS}")

        # Confusion matrix
        lr.fit(texts, labels)
        preds = lr.predict(texts)
        cm = confusion_matrix(labels, preds, labels=CLASSES)
        OUT_CM.parent.mkdir(parents=True, exist_ok=True)
        with open(OUT_CM, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["actual\\predicted"] + CLASSES)
            for i, cls in enumerate(CLASSES):
                w.writerow([cls] + list(cm[i]))
        print(f"  Confusion matrix → {OUT_CM}")

        print("\n  Type classifier results:")
        for r in all_results:
            print(f"    {r['model']}: macro-F1={r['macro_f1']}  "
                  f"agg-prec={r.get('aggressive_precision','?')}  "
                  f"improves={r.get('improves_over_wendys_baseline','?')}")

    print("=== train_domain_adapted_humor_type_classifier COMPLETE ===")


if __name__ == "__main__":
    main()
