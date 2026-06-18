"""
train_domain_adapted_humor_presence_classifier.py

Trains binary humor presence classifier on Fortune Top 100 human labels.
Requires: fortune100_human_labeling_template.csv with human_humor_presence filled.

Classifier candidates:
  A. TF-IDF + Logistic Regression (baseline)
  B. TF-IDF + LinearSVC with calibration

Evaluation modes:
  1. random train/test split (default)
  2. firm-held-out validation

Run after human labels are collected.
"""

from __future__ import annotations

import argparse
import csv
import math
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
    accuracy_score, f1_score, precision_score, recall_score, roc_auc_score,
    confusion_matrix,
)
from sklearn.model_selection import StratifiedKFold
from sklearn.pipeline import Pipeline
from sklearn.svm import LinearSVC

ROOT = Path(__file__).resolve().parents[3]
CI = ROOT / "20260618expand" / "classifier_improvement"

TEMPLATE = CI / "data" / "human_labeling_template" / "fortune100_human_labeling_template.csv"
OUT_METRICS = CI / "results" / "presence_classifier_metrics.csv"
OUT_CM = CI / "results" / "confusion_matrices" / "presence_confusion_matrix.csv"
OUT_THRESHOLD = CI / "results" / "threshold_sensitivity.csv"
OUT_DIAG = CI / "data" / "diagnostics" / "presence_classifier_diagnostics.csv"
OUT_REPORT = CI / "reports" / "validation_report.md"

# Numeric coding (human input): 0=non_humor, 1=humor, 2=uncertain (excluded from training)
VALID_PRESENCE = {"0", "1"}
PRESENCE_CODE_TO_LABEL = {"0": "non_humor", "1": "humor"}
RANDOM_STATE = 42

# Provisional acceptance thresholds — NOT pass/fail gates; documented minimums
PROVISIONAL_F1_THRESHOLD = 0.70
PROVISIONAL_AUC_THRESHOLD = 0.75
PROVISIONAL_IMPROVEMENT_OVER_WENDY_AUC = 0.7095  # from model_transfer CV


def preprocess(text: str) -> str:
    text = re.sub(r"https?://\S+", "<URL>", text)
    text = re.sub(r"@\w+", "<MENTION>", text)
    text = re.sub(r"#(\w+)", r"\1", text)
    return re.sub(r"\s+", " ", text.lower()).strip()


def build_logreg_pipeline() -> Pipeline:
    return Pipeline([
        ("tfidf", TfidfVectorizer(
            lowercase=True, ngram_range=(1, 2),
            min_df=2, max_df=0.95, sublinear_tf=True,
        )),
        ("clf", LogisticRegression(
            class_weight="balanced", solver="liblinear",
            max_iter=2000, random_state=RANDOM_STATE,
        )),
    ])


def build_svm_pipeline() -> Pipeline:
    return Pipeline([
        ("tfidf", TfidfVectorizer(
            lowercase=True, ngram_range=(1, 2),
            min_df=2, max_df=0.95, sublinear_tf=True,
        )),
        ("clf", CalibratedClassifierCV(
            LinearSVC(class_weight="balanced", max_iter=2000, random_state=RANDOM_STATE),
            cv=5,
        )),
    ])


def evaluate_pipeline(
    pipe: Pipeline,
    texts: list[str],
    labels: list[int],
    firms: list[str],
    model_name: str,
) -> list[dict]:
    results = []
    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=RANDOM_STATE)

    # 1. Random 5-fold CV
    accs, precs, recs, f1s, aucs = [], [], [], [], []
    for tr_idx, va_idx in skf.split(texts, labels):
        X_tr = [texts[i] for i in tr_idx]
        X_va = [texts[i] for i in va_idx]
        y_tr = [labels[i] for i in tr_idx]
        y_va = [labels[i] for i in va_idx]
        pipe.fit(X_tr, y_tr)
        preds = pipe.predict(X_va)
        probs = pipe.predict_proba(X_va)[:, 1]
        accs.append(accuracy_score(y_va, preds))
        precs.append(precision_score(y_va, preds, zero_division=0))
        recs.append(recall_score(y_va, preds, zero_division=0))
        f1s.append(f1_score(y_va, preds, zero_division=0))
        try:
            aucs.append(roc_auc_score(y_va, probs))
        except Exception:
            aucs.append(float("nan"))
    results.append({
        "model": model_name,
        "eval_mode": "random_5fold_cv",
        "accuracy": round(float(np.mean(accs)), 4),
        "precision": round(float(np.mean(precs)), 4),
        "recall": round(float(np.mean(recs)), 4),
        "f1": round(float(np.mean(f1s)), 4),
        "auc": round(float(np.nanmean(aucs)), 4),
        "n_labeled": len(labels),
        "humor_count": sum(labels),
        "non_humor_count": len(labels) - sum(labels),
        "provisional_auc_threshold": PROVISIONAL_AUC_THRESHOLD,
        "meets_provisional_auc": "yes" if float(np.nanmean(aucs)) >= PROVISIONAL_AUC_THRESHOLD else "no (provisional)",
    })

    # 2. Firm-held-out validation
    unique_firms = list(set(firms))
    if len(unique_firms) >= 5:
        firm_accs, firm_f1s = [], []
        for held_firm in unique_firms[:min(10, len(unique_firms))]:
            tr_idx = [i for i, f in enumerate(firms) if f != held_firm]
            va_idx = [i for i, f in enumerate(firms) if f == held_firm]
            if not va_idx:
                continue
            X_tr = [texts[i] for i in tr_idx]
            X_va = [texts[i] for i in va_idx]
            y_tr = [labels[i] for i in tr_idx]
            y_va = [labels[i] for i in va_idx]
            if len(set(y_tr)) < 2:
                continue
            pipe.fit(X_tr, y_tr)
            preds = pipe.predict(X_va)
            firm_accs.append(accuracy_score(y_va, preds))
            firm_f1s.append(f1_score(y_va, preds, zero_division=0))
        if firm_accs:
            results.append({
                "model": model_name,
                "eval_mode": "firm_held_out",
                "accuracy": round(float(np.mean(firm_accs)), 4),
                "f1": round(float(np.mean(firm_f1s)), 4),
                "n_labeled": len(labels),
                "note": f"averaged over {len(firm_accs)} firm holdouts",
            })

    return results


def threshold_sensitivity(pipe: Pipeline, texts: list[str], labels: list[int]) -> list[dict]:
    pipe.fit(texts, labels)
    probs = pipe.predict_proba(texts)[:, 1]
    rows = []
    for lo, hi, label in [
        (0.0, 0.40, "low_threshold_0.40"),
        (0.0, 0.50, "threshold_0.50"),
        (0.0, 0.60, "threshold_0.60"),
    ]:
        classified = [1 if p > hi else 0 for p in probs]
        uncertain = sum(1 for p in probs if lo < p <= hi) if lo > 0 else 0
        rows.append({
            "threshold": hi,
            "humor_count": sum(classified),
            "non_humor_count": len(classified) - sum(classified),
            "uncertain_count": uncertain,
            "f1": round(float(f1_score(labels, classified, zero_division=0)), 4),
        })
    # Abstention: uncertain if 0.4 <= p <= 0.6
    abstain_preds = []
    for p in probs:
        if p >= 0.6:
            abstain_preds.append(1)
        elif p <= 0.4:
            abstain_preds.append(0)
        else:
            abstain_preds.append(-1)  # uncertain
    non_abstain = [(l, p) for l, p in zip(labels, abstain_preds) if p != -1]
    if non_abstain:
        y_true_na, y_pred_na = zip(*non_abstain)
        rows.append({
            "threshold": "0.4-0.6 abstention",
            "humor_count": sum(1 for p in abstain_preds if p == 1),
            "non_humor_count": sum(1 for p in abstain_preds if p == 0),
            "uncertain_count": sum(1 for p in abstain_preds if p == -1),
            "f1": round(float(f1_score(list(y_true_na), list(y_pred_na), zero_division=0)), 4),
        })
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--smoke", action="store_true",
                        help="Use only first 200 labeled rows for quick smoke test")
    args = parser.parse_args()

    print("=== train_domain_adapted_humor_presence_classifier ===")

    if not TEMPLATE.exists():
        print(f"ERROR: template not found: {TEMPLATE}")
        print("Run build_fortune_labeling_candidates.py and build_human_labeling_template.py first,")
        print("then fill in human_humor_presence labels.")
        raise SystemExit(1)

    with open(TEMPLATE, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    labeled = [r for r in rows
               if r.get("human_humor_presence", "").strip() in VALID_PRESENCE]
    print(f"  Total rows: {len(rows)}  Labeled: {len(labeled)}")

    if len(labeled) < 50:
        print("ERROR: fewer than 50 labeled rows. Cannot train classifier.")
        raise SystemExit(1)

    if args.smoke:
        labeled = labeled[:200]
        print(f"  Smoke mode: using first {len(labeled)} rows")

    label_dist = Counter(
        PRESENCE_CODE_TO_LABEL[r["human_humor_presence"].strip()]
        for r in labeled
    )
    print(f"  Label distribution: {dict(label_dist)}")

    texts = [preprocess(r["text"]) for r in labeled]
    labels = [1 if r["human_humor_presence"].strip() == "1" else 0 for r in labeled]
    firms = [r["company_name"] for r in labeled]

    all_results = []

    print("\n  Training LogReg...")
    lr_pipe = build_logreg_pipeline()
    all_results.extend(evaluate_pipeline(lr_pipe, texts, labels, firms, "logreg"))

    print("  Training LinearSVC + calibration...")
    svm_pipe = build_svm_pipeline()
    all_results.extend(evaluate_pipeline(svm_pipe, texts, labels, firms, "linearsvc_calibrated"))

    # Threshold sensitivity on best model (LogReg)
    lr_pipe.fit(texts, labels)
    thresh_rows = threshold_sensitivity(lr_pipe, texts, labels)

    # Write outputs
    OUT_METRICS.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_METRICS, "w", newline="", encoding="utf-8") as f:
        keys = list(all_results[0].keys())
        w = csv.DictWriter(f, fieldnames=keys, extrasaction="ignore")
        w.writeheader()
        w.writerows(all_results)
    print(f"\n  Metrics → {OUT_METRICS}")

    OUT_THRESHOLD.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_THRESHOLD, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(thresh_rows[0].keys()))
        w.writeheader()
        w.writerows(thresh_rows)
    print(f"  Threshold sensitivity → {OUT_THRESHOLD}")

    # Confusion matrix (final model, full labeled set)
    lr_pipe.fit(texts, labels)
    preds = lr_pipe.predict(texts)
    cm = confusion_matrix(labels, preds, labels=[1, 0])
    OUT_CM.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_CM, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["actual\\predicted", "humor", "non_humor"])
        w.writerow(["humor"] + list(cm[0]))
        w.writerow(["non_humor"] + list(cm[1]))
    print(f"  Confusion matrix → {OUT_CM}")

    print("\n  5-fold CV Results:")
    for r in all_results:
        if r.get("eval_mode") == "random_5fold_cv":
            print(f"    {r['model']}: F1={r['f1']}  AUC={r.get('auc','n/a')}  "
                  f"meets_provisional={r.get('meets_provisional_auc','')}")

    print("=== train_domain_adapted_humor_presence_classifier COMPLETE ===")


if __name__ == "__main__":
    main()
