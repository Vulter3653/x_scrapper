"""
run_batch1_presence_model_search.py

Searches over TF-IDF + classifier combinations for humor presence detection.
All metrics are out-of-fold (OOF) based — no in-sample evaluation.

Evaluation design:
  - StratifiedKFold(5, shuffle=True, random_state=42) for main CV
  - OOF predictions concatenated across all folds → metrics computed once
  - Firm-held-out evaluation for top-5 models by OOF AUC

Outputs (batch1_only_improvement/results/):
  presence_model_comparison_cv.csv
  presence_oof_confusion_matrix.csv   (best model by OOF AUC)

NOTE: threshold_sensitivity is NOT computed here (it is CV-based, done in evaluate script).
NOTE: No in-sample metrics. All confusion matrices are OOF-based.
"""

from __future__ import annotations

import csv
import re
import sys
import time
from collections import Counter
from pathlib import Path

PYPACKAGES = Path("/home/user/.local/pypackages")
if str(PYPACKAGES) not in sys.path:
    sys.path.insert(0, str(PYPACKAGES))

import numpy as np
from sklearn.calibration import CalibratedClassifierCV
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression, SGDClassifier
from sklearn.metrics import (
    accuracy_score, average_precision_score, confusion_matrix,
    f1_score, precision_score, recall_score, roc_auc_score,
)
from sklearn.model_selection import StratifiedKFold
from sklearn.naive_bayes import ComplementNB
from sklearn.pipeline import FeatureUnion, Pipeline
from sklearn.svm import LinearSVC

ROOT = Path(__file__).resolve().parents[4]
CI = ROOT / "20260618expand" / "classifier_improvement"
B1 = CI / "batch1_only_improvement"
DATA_DIR = B1 / "data"
RES_DIR = B1 / "results"

IN_PRESENCE = DATA_DIR / "batch1_presence_training_data.csv"
OUT_CV = RES_DIR / "presence_model_comparison_cv.csv"
OUT_OOF_CM = RES_DIR / "presence_oof_confusion_matrix.csv"

RANDOM_STATE = 42
N_SPLITS = 5
PROVISIONAL_AUC = 0.75
BASELINE_AUC = 0.7674   # from 3aade94 batch1 LogReg random 5-fold CV


def preprocess(text: str, normalize_urls: bool = True, normalize_mentions: bool = True,
               preserve_hashtags: bool = True) -> str:
    if normalize_urls:
        text = re.sub(r"https?://\S+", "<URL>", text)
    if normalize_mentions:
        text = re.sub(r"@\w+", "<MENTION>", text)
    if preserve_hashtags:
        text = re.sub(r"#(\w+)", r"\1", text)
    return re.sub(r"\s+", " ", text.lower()).strip()


def make_word_vec(ngram=(1, 2), max_features=5000, min_df=2, sublinear_tf=True):
    return TfidfVectorizer(
        analyzer="word", ngram_range=ngram, max_features=max_features,
        min_df=min_df, max_df=0.95, sublinear_tf=sublinear_tf,
    )


def make_char_vec(ngram=(3, 5), max_features=5000, min_df=2, sublinear_tf=True):
    return TfidfVectorizer(
        analyzer="char_wb", ngram_range=ngram, max_features=max_features,
        min_df=min_df, max_df=0.95, sublinear_tf=sublinear_tf,
    )


def make_combined_vec(word_mf=5000, char_mf=5000, min_df=2):
    return FeatureUnion([
        ("word", TfidfVectorizer(analyzer="word", ngram_range=(1, 2), max_features=word_mf,
                                 min_df=min_df, max_df=0.95, sublinear_tf=True)),
        ("char", TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), max_features=char_mf,
                                 min_df=min_df, max_df=0.95, sublinear_tf=True)),
    ])


def build_grid() -> list[dict]:
    RS = RANDOM_STATE
    grid = []

    vec_configs = [
        ("word_12_5k",   make_word_vec((1, 2), 5000,  2),  "word", "(1,2)", 5000,  2, True),
        ("word_12_10k",  make_word_vec((1, 2), 10000, 2),  "word", "(1,2)", 10000, 2, True),
        ("word_13_5k",   make_word_vec((1, 3), 5000,  2),  "word", "(1,3)", 5000,  2, True),
        ("word_12_md1",  make_word_vec((1, 2), 5000,  1),  "word", "(1,2)", 5000,  1, True),
        ("char_35_5k",   make_char_vec((3, 5), 5000,  2),  "char_wb", "(3,5)", 5000, 2, True),
        ("word_char_comb", make_combined_vec(5000, 5000, 2), "word+char", "(1,2)+(3,5)", 10000, 2, True),
    ]

    clf_configs = [
        ("lr_liblin_bal",  LogisticRegression(class_weight="balanced", solver="liblinear",
                                              C=1.0, max_iter=2000, random_state=RS)),
        ("lr_lbfgs_bal",   LogisticRegression(class_weight="balanced", solver="lbfgs",
                                              C=1.0, max_iter=2000, random_state=RS)),
        ("lr_liblin_C01",  LogisticRegression(class_weight="balanced", solver="liblinear",
                                              C=0.1, max_iter=2000, random_state=RS)),
        ("lr_liblin_C10",  LogisticRegression(class_weight="balanced", solver="liblinear",
                                              C=10.0, max_iter=2000, random_state=RS)),
        ("svc_cal_bal",    CalibratedClassifierCV(
                               LinearSVC(class_weight="balanced", max_iter=2000, random_state=RS),
                               cv=3)),
        ("cnb",            ComplementNB(alpha=0.1)),
        ("sgd_log",        SGDClassifier(loss="log_loss", class_weight="balanced",
                                         random_state=RS, max_iter=1000)),
    ]

    for vec_name, vec, vec_type, ngram_str, mf, md, stf in vec_configs:
        for clf_name, clf in clf_configs:
            # ComplementNB doesn't work with FeatureUnion (may produce negatives) — skip
            if clf_name == "cnb" and vec_name == "word_char_comb":
                continue
            grid.append({
                "model_id":      f"{vec_name}__{clf_name}",
                "vectorizer_name": vec_name,
                "vectorizer_type": vec_type,
                "ngram_range":   ngram_str,
                "max_features":  mf,
                "min_df":        md,
                "sublinear_tf":  stf,
                "classifier":    clf_name,
                "vec":           vec,
                "clf":           clf,
            })

    return grid


def evaluate_oof(pipeline: Pipeline, texts: list[str], labels: list[int],
                 cv: StratifiedKFold) -> tuple[np.ndarray, np.ndarray]:
    oof_proba = np.full(len(labels), np.nan)
    oof_pred = np.zeros(len(labels), dtype=int)
    y_arr = np.array(labels)

    for tr_idx, va_idx in cv.split(texts, y_arr):
        X_tr = [texts[i] for i in tr_idx]
        X_va = [texts[i] for i in va_idx]
        y_tr = y_arr[tr_idx].tolist()
        pipeline.fit(X_tr, y_tr)

        if hasattr(pipeline, "predict_proba"):
            proba = pipeline.predict_proba(X_va)[:, 1]
        else:
            df = pipeline.decision_function(X_va)
            proba = (df - df.min()) / (df.ptp() + 1e-9)

        oof_proba[va_idx] = proba
        oof_pred[va_idx] = pipeline.predict(X_va)

    return oof_proba, oof_pred


def firm_held_out_f1(pipeline: Pipeline, texts: list[str], labels: list[int],
                     companies: list[str]) -> tuple[float, int]:
    unique_firms = sorted(set(companies))
    f1_scores: list[float] = []
    for firm in unique_firms:
        tr_idx = [i for i, c in enumerate(companies) if c != firm]
        va_idx = [i for i, c in enumerate(companies) if c == firm]
        if len(va_idx) < 1 or len(set(labels[i] for i in tr_idx)) < 2:
            continue
        X_tr = [texts[i] for i in tr_idx]
        X_va = [texts[i] for i in va_idx]
        y_tr = [labels[i] for i in tr_idx]
        y_va = [labels[i] for i in va_idx]
        pipeline.fit(X_tr, y_tr)
        preds = pipeline.predict(X_va)
        f1_scores.append(f1_score(y_va, preds, zero_division=0))
    return (float(np.mean(f1_scores)) if f1_scores else 0.0), len(f1_scores)


def main() -> None:
    print("=== run_batch1_presence_model_search ===")

    if not IN_PRESENCE.exists():
        raise FileNotFoundError(f"Run build_batch1_only_training_datasets.py first: {IN_PRESENCE}")

    with open(IN_PRESENCE, encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))

    texts_raw = [r["text"] for r in rows]
    labels = [int(r["humor_label"]) for r in rows]
    companies = [r["company_name"] for r in rows]
    texts = [preprocess(t) for t in texts_raw]

    print(f"  Rows: {len(rows)}  humor={sum(labels)}  non_humor={len(labels)-sum(labels)}")
    print(f"  Unique firms: {len(set(companies))}")

    cv = StratifiedKFold(n_splits=N_SPLITS, shuffle=True, random_state=RANDOM_STATE)
    grid = build_grid()
    print(f"  Model grid size: {len(grid)} configurations")

    results: list[dict] = []
    best_auc = -1.0
    best_model_id = ""
    best_oof_proba: np.ndarray | None = None
    best_oof_pred: np.ndarray | None = None

    for i, cfg in enumerate(grid):
        model_id = cfg["model_id"]
        try:
            pipe = Pipeline([("vec", cfg["vec"]), ("clf", cfg["clf"])])
            t0 = time.time()
            oof_proba, oof_pred = evaluate_oof(pipe, texts, labels, cv)
            elapsed = time.time() - t0

            valid_mask = ~np.isnan(oof_proba)
            if valid_mask.sum() < len(labels) * 0.9:
                raise ValueError("Too many NaN OOF probabilities")

            y_arr = np.array(labels)
            oof_p = oof_proba[valid_mask]
            oof_pred_v = oof_pred[valid_mask]
            y_v = y_arr[valid_mask]

            oof_auc = roc_auc_score(y_v, oof_p)
            oof_f1  = f1_score(y_v, oof_pred_v, zero_division=0)
            oof_prec = precision_score(y_v, oof_pred_v, zero_division=0)
            oof_rec  = recall_score(y_v, oof_pred_v, zero_division=0)
            oof_acc  = accuracy_score(y_v, oof_pred_v)
            oof_prauc = average_precision_score(y_v, oof_p)

            row = {
                "model_id":         model_id,
                "vectorizer_type":  cfg["vectorizer_type"],
                "ngram_range":      cfg["ngram_range"],
                "max_features":     cfg["max_features"],
                "min_df":           cfg["min_df"],
                "sublinear_tf":     cfg["sublinear_tf"],
                "classifier":       cfg["classifier"],
                "oof_auc":          round(oof_auc, 4),
                "oof_pr_auc":       round(oof_prauc, 4),
                "oof_f1":           round(oof_f1, 4),
                "oof_precision":    round(oof_prec, 4),
                "oof_recall":       round(oof_rec, 4),
                "oof_accuracy":     round(oof_acc, 4),
                "n_labeled":        len(rows),
                "humor_count":      sum(labels),
                "non_humor_count":  len(labels) - sum(labels),
                "eval_mode":        f"oof_stratified_{N_SPLITS}fold_cv",
                "meets_provisional_auc": "yes" if oof_auc >= PROVISIONAL_AUC else "no",
                "improves_over_baseline_auc": "yes" if oof_auc > BASELINE_AUC else "no",
                "baseline_auc_ref": BASELINE_AUC,
                "elapsed_s":        round(elapsed, 2),
                "status":           "OK",
                "note":             "",
            }
            results.append(row)

            if oof_auc > best_auc:
                best_auc = oof_auc
                best_model_id = model_id
                best_oof_proba = oof_proba.copy()
                best_oof_pred = oof_pred.copy()

            print(f"  [{i+1:2d}/{len(grid)}] {model_id:<45s}  AUC={oof_auc:.4f}  F1={oof_f1:.4f}")

        except Exception as exc:
            print(f"  [{i+1:2d}/{len(grid)}] {model_id:<45s}  ERROR: {exc}")
            results.append({
                "model_id": model_id,
                "vectorizer_type": cfg["vectorizer_type"],
                "ngram_range": cfg["ngram_range"],
                "max_features": cfg["max_features"],
                "min_df": cfg["min_df"],
                "sublinear_tf": cfg["sublinear_tf"],
                "classifier": cfg["classifier"],
                "oof_auc": "error",
                "status": "ERROR",
                "note": str(exc)[:120],
            })

    print(f"\n  Best model: {best_model_id}  OOF AUC={best_auc:.4f}")

    # Firm-held-out for top-5 by OOF AUC
    ok_results = [r for r in results if r.get("status") == "OK"]
    ok_results.sort(key=lambda x: float(x.get("oof_auc", 0)), reverse=True)
    top5 = ok_results[:5]
    print("\n  Running firm-held-out for top-5 models by OOF AUC...")

    grid_by_id = {cfg["model_id"]: cfg for cfg in grid}
    for r in top5:
        cfg = grid_by_id.get(r["model_id"])
        if cfg is None:
            continue
        try:
            pipe = Pipeline([("vec", cfg["vec"]), ("clf", cfg["clf"])])
            fh_f1, n_firms = firm_held_out_f1(pipe, texts, labels, companies)
            r["firm_held_out_f1"] = round(fh_f1, 4)
            r["firm_held_out_n_firms"] = n_firms
            print(f"    {r['model_id']:<45s}  firm-held-out F1={fh_f1:.4f} ({n_firms} firms)")
        except Exception as exc:
            r["firm_held_out_f1"] = "error"
            r["firm_held_out_n_firms"] = 0
            print(f"    {r['model_id']:<45s}  firm-held-out ERROR: {exc}")

    # Write model comparison CSV
    RES_DIR.mkdir(parents=True, exist_ok=True)
    all_keys: list[str] = []
    for r in results:
        for k in r.keys():
            if k not in all_keys:
                all_keys.append(k)
    all_keys = [k for k in all_keys if k not in ("vec", "clf")]

    with open(OUT_CV, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=all_keys, extrasaction="ignore")
        w.writeheader()
        w.writerows(results)
    print(f"\n  Written: {OUT_CV} ({len(results)} rows)")

    # OOF confusion matrix for best model
    if best_oof_pred is not None:
        y_arr = np.array(labels)
        cm = confusion_matrix(y_arr, best_oof_pred, labels=[1, 0])
        with open(OUT_OOF_CM, "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(["eval_mode", "oof_stratified_5fold_cv"])
            w.writerow(["best_model_id", best_model_id])
            w.writerow(["actual\\predicted", "humor", "non_humor"])
            w.writerow(["humor"] + list(cm[0]))
            w.writerow(["non_humor"] + list(cm[1]))
        print(f"  Written: {OUT_OOF_CM}")

    print("=== run_batch1_presence_model_search COMPLETE ===")


if __name__ == "__main__":
    main()
