"""
run_batch1_aggressive_detector_search.py

Builds aggressive-vs-non-aggressive-humor binary detector.
Only trained on humor rows (presence=1): n=648, aggressive=44, non_aggressive=604.

Evaluation design:
  - RepeatedStratifiedKFold(n_splits=5, n_repeats=5, random_state=42) for stability
  - OOF predictions (single-repeat stratified 5-fold) for confusion matrix
  - Threshold analysis is OOF-based (not in-sample)

Provisional usability criteria (both must be met):
  - aggressive precision >= 0.60   (OOF-based)
  - aggressive recall    >= 0.20   (OOF-based)

Outputs (batch1_only_improvement/results/):
  aggressive_detector_model_comparison_cv.csv
  aggressive_detector_threshold_cv.csv        (OOF-based sweep)
  aggressive_detector_oof_confusion_matrix.csv (best model by OOF PR-AUC)

NOTE: All thresholds chosen from OOF predictions only. No in-sample thresholding.
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
    f1_score, precision_recall_curve, precision_score, recall_score, roc_auc_score,
)
from sklearn.model_selection import RepeatedStratifiedKFold, StratifiedKFold
from sklearn.naive_bayes import ComplementNB
from sklearn.pipeline import FeatureUnion, Pipeline
from sklearn.svm import LinearSVC

ROOT = Path(__file__).resolve().parents[4]
CI = ROOT / "20260618expand" / "classifier_improvement"
B1 = CI / "batch1_only_improvement"
DATA_DIR = B1 / "data"
RES_DIR = B1 / "results"

IN_AGG = DATA_DIR / "batch1_aggressive_detector_training_data.csv"
OUT_CV = RES_DIR / "aggressive_detector_model_comparison_cv.csv"
OUT_THRESH = RES_DIR / "aggressive_detector_threshold_cv.csv"
OUT_OOF_CM = RES_DIR / "aggressive_detector_oof_confusion_matrix.csv"

RANDOM_STATE = 42
N_SPLITS = 5
N_REPEATS = 5
TARGET_PRECISION = 0.60
TARGET_RECALL = 0.20
AGGRESSIVE_LABEL = 1


def preprocess(text: str) -> str:
    text = re.sub(r"https?://\S+", "<URL>", text)
    text = re.sub(r"@\w+", "<MENTION>", text)
    text = re.sub(r"#(\w+)", r"\1", text)
    return re.sub(r"\s+", " ", text.lower()).strip()


def make_word_vec(ngram=(1, 2), max_features=5000, min_df=1, sublinear_tf=True):
    return TfidfVectorizer(
        analyzer="word", ngram_range=ngram, max_features=max_features,
        min_df=min_df, max_df=0.98, sublinear_tf=sublinear_tf,
    )


def make_char_vec(ngram=(3, 5), max_features=5000, min_df=1, sublinear_tf=True):
    return TfidfVectorizer(
        analyzer="char_wb", ngram_range=ngram, max_features=max_features,
        min_df=min_df, max_df=0.98, sublinear_tf=sublinear_tf,
    )


def make_combined_vec(word_mf=5000, char_mf=3000, min_df=1):
    return FeatureUnion([
        ("word", TfidfVectorizer(analyzer="word", ngram_range=(1, 2), max_features=word_mf,
                                 min_df=min_df, max_df=0.98, sublinear_tf=True)),
        ("char", TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), max_features=char_mf,
                                 min_df=min_df, max_df=0.98, sublinear_tf=True)),
    ])


def build_grid() -> list[dict]:
    RS = RANDOM_STATE
    grid = []

    vec_configs = [
        ("word_12_5k",    make_word_vec((1, 2), 5000,  1), "word",    "(1,2)", 5000,  1, True),
        ("word_12_10k",   make_word_vec((1, 2), 10000, 1), "word",    "(1,2)", 10000, 1, True),
        ("word_13_5k",    make_word_vec((1, 3), 5000,  1), "word",    "(1,3)", 5000,  1, True),
        ("char_35_5k",    make_char_vec((3, 5), 5000,  1), "char_wb", "(3,5)", 5000,  1, True),
        ("word_char_comb", make_combined_vec(5000, 3000, 1), "word+char", "(1,2)+(3,5)", 8000, 1, True),
    ]

    clf_configs = [
        ("lr_liblin_bal",   LogisticRegression(class_weight="balanced", solver="liblinear",
                                               C=1.0, max_iter=2000, random_state=RS)),
        ("lr_liblin_C01",   LogisticRegression(class_weight="balanced", solver="liblinear",
                                               C=0.1, max_iter=2000, random_state=RS)),
        ("lr_liblin_C5",    LogisticRegression(class_weight="balanced", solver="liblinear",
                                               C=5.0, max_iter=2000, random_state=RS)),
        ("svc_cal_bal",     CalibratedClassifierCV(
                                LinearSVC(class_weight="balanced", max_iter=2000, random_state=RS),
                                cv=3)),
        ("sgd_log_bal",     SGDClassifier(loss="log_loss", class_weight="balanced",
                                          random_state=RS, max_iter=1000, n_iter_no_change=20)),
        ("cnb",             ComplementNB(alpha=0.1)),
    ]

    for vec_name, vec, vec_type, ngram_str, mf, md, stf in vec_configs:
        for clf_name, clf in clf_configs:
            if clf_name == "cnb" and vec_name == "word_char_comb":
                continue
            grid.append({
                "model_id":        f"{vec_name}__{clf_name}",
                "vectorizer_name": vec_name,
                "vectorizer_type": vec_type,
                "ngram_range":     ngram_str,
                "max_features":    mf,
                "min_df":          md,
                "sublinear_tf":    stf,
                "classifier":      clf_name,
                "vec":             vec,
                "clf":             clf,
            })

    return grid


def oof_single_fold(pipeline: Pipeline, texts: list[str], labels: list[int],
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


def repeated_cv_metrics(pipeline: Pipeline, texts: list[str], labels: list[int]) -> dict:
    rskf = RepeatedStratifiedKFold(n_splits=N_SPLITS, n_repeats=N_REPEATS, random_state=RANDOM_STATE)
    y_arr = np.array(labels)
    aucs, praucs, precs, recs, f1s = [], [], [], [], []
    for tr_idx, va_idx in rskf.split(texts, y_arr):
        X_tr = [texts[i] for i in tr_idx]
        X_va = [texts[i] for i in va_idx]
        y_tr = y_arr[tr_idx].tolist()
        y_va = y_arr[va_idx]
        pipeline.fit(X_tr, y_tr)
        if hasattr(pipeline, "predict_proba"):
            proba = pipeline.predict_proba(X_va)[:, 1]
        else:
            df = pipeline.decision_function(X_va)
            proba = (df - df.min()) / (df.ptp() + 1e-9)
        preds = pipeline.predict(X_va)
        if len(set(y_va)) >= 2:
            aucs.append(roc_auc_score(y_va, proba))
            praucs.append(average_precision_score(y_va, proba))
        precs.append(precision_score(y_va, preds, zero_division=0))
        recs.append(recall_score(y_va, preds, zero_division=0))
        f1s.append(f1_score(y_va, preds, zero_division=0))
    return {
        "repeated_cv_roc_auc_mean": round(float(np.nanmean(aucs)), 4) if aucs else None,
        "repeated_cv_roc_auc_std":  round(float(np.nanstd(aucs)), 4)  if aucs else None,
        "repeated_cv_pr_auc_mean":  round(float(np.nanmean(praucs)), 4) if praucs else None,
        "repeated_cv_pr_auc_std":   round(float(np.nanstd(praucs)), 4)  if praucs else None,
        "repeated_cv_precision_mean": round(float(np.mean(precs)), 4),
        "repeated_cv_recall_mean":    round(float(np.mean(recs)), 4),
        "repeated_cv_f1_mean":        round(float(np.mean(f1s)), 4),
        "repeated_cv_n_splits":       N_SPLITS,
        "repeated_cv_n_repeats":      N_REPEATS,
    }


def threshold_sweep(oof_proba: np.ndarray, y: np.ndarray,
                    model_id: str) -> list[dict]:
    rows = []
    n_total = len(y)
    n_pos = int(y.sum())
    thresholds = np.arange(0.05, 0.96, 0.05)
    for thr in thresholds:
        pred = (oof_proba >= thr).astype(int)
        covered = int(pred.sum())
        abstained = n_total - covered
        if covered == 0:
            rows.append({
                "model_id": model_id,
                "threshold": round(float(thr), 2),
                "oof_precision": 0.0, "oof_recall": 0.0, "oof_f1": 0.0,
                "n_predicted_aggressive": 0, "n_abstained": abstained,
                "coverage_rate": 0.0,
                "meets_precision_target": "no",
                "meets_recall_target": "no",
                "meets_provisional_criteria": "no",
                "eval_basis": "oof_5fold_cv",
            })
            continue
        prec = precision_score(y, pred, zero_division=0)
        rec  = recall_score(y, pred, zero_division=0)
        f1   = f1_score(y, pred, zero_division=0)
        meets_prec = prec >= TARGET_PRECISION
        meets_rec  = rec  >= TARGET_RECALL
        rows.append({
            "model_id":                  model_id,
            "threshold":                 round(float(thr), 2),
            "oof_precision":             round(float(prec), 4),
            "oof_recall":                round(float(rec), 4),
            "oof_f1":                    round(float(f1), 4),
            "n_predicted_aggressive":    covered,
            "n_abstained":               abstained,
            "coverage_rate":             round(covered / n_total, 4),
            "meets_precision_target":    "yes" if meets_prec else "no",
            "meets_recall_target":       "yes" if meets_rec else "no",
            "meets_provisional_criteria": "yes" if (meets_prec and meets_rec) else "no",
            "eval_basis":                "oof_5fold_cv",
        })
    return rows


def firm_held_out(pipeline: Pipeline, texts: list[str], labels: list[int],
                  companies: list[str]) -> tuple[float, float, float, int]:
    unique_firms = sorted(set(companies))
    precs, recs, f1s = [], [], []
    for firm in unique_firms:
        tr_idx = [i for i, c in enumerate(companies) if c != firm]
        va_idx = [i for i, c in enumerate(companies) if c == firm]
        if len(va_idx) < 1:
            continue
        y_va = [labels[i] for i in va_idx]
        y_tr = [labels[i] for i in tr_idx]
        if len(set(y_tr)) < 2 or sum(y_va) == 0:
            continue
        X_tr = [texts[i] for i in tr_idx]
        X_va = [texts[i] for i in va_idx]
        pipeline.fit(X_tr, y_tr)
        preds = pipeline.predict(X_va)
        precs.append(precision_score(y_va, preds, zero_division=0))
        recs.append(recall_score(y_va, preds, zero_division=0))
        f1s.append(f1_score(y_va, preds, zero_division=0))
    n = len(f1s)
    return (
        round(float(np.mean(precs)), 4) if precs else 0.0,
        round(float(np.mean(recs)), 4)  if recs  else 0.0,
        round(float(np.mean(f1s)), 4)   if f1s   else 0.0,
        n,
    )


def main() -> None:
    print("=== run_batch1_aggressive_detector_search ===")

    if not IN_AGG.exists():
        raise FileNotFoundError(f"Run build_batch1_only_training_datasets.py first: {IN_AGG}")

    with open(IN_AGG, encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))

    texts_raw = [r["text"] for r in rows]
    labels = [int(r["aggressive_label"]) for r in rows]
    companies = [r["company_name"] for r in rows]
    texts = [preprocess(t) for t in texts_raw]

    agg_n = sum(labels)
    nonagg_n = len(labels) - agg_n
    print(f"  Rows: {len(rows)}  aggressive={agg_n}  non_aggressive_humor={nonagg_n}")
    print(f"  Aggressive base rate: {agg_n/len(labels):.3f}")
    print(f"  Unique firms: {len(set(companies))}")
    print(f"  WARNING: n=44 aggressive positives — CV metrics will be noisy")
    print(f"  Provisional thresholds: precision>={TARGET_PRECISION}, recall>={TARGET_RECALL}")

    cv_oof = StratifiedKFold(n_splits=N_SPLITS, shuffle=True, random_state=RANDOM_STATE)
    grid = build_grid()
    print(f"  Grid size: {len(grid)} configurations")

    results: list[dict] = []
    best_prauc = -1.0
    best_model_id = ""
    best_oof_proba: np.ndarray | None = None
    best_oof_pred: np.ndarray | None = None
    all_thresh_rows: list[dict] = []

    y_arr = np.array(labels)

    for i, cfg in enumerate(grid):
        model_id = cfg["model_id"]
        try:
            pipe = Pipeline([("vec", cfg["vec"]), ("clf", cfg["clf"])])
            t0 = time.time()

            # OOF single-fold pass for confusion matrix and threshold sweep
            oof_proba, oof_pred = oof_single_fold(pipe, texts, labels, cv_oof)
            elapsed_oof = time.time() - t0

            valid_mask = ~np.isnan(oof_proba)
            if valid_mask.sum() < len(labels) * 0.9:
                raise ValueError("Too many NaN OOF probabilities")

            oof_p = oof_proba[valid_mask]
            oof_pred_v = oof_pred[valid_mask]
            y_v = y_arr[valid_mask]

            oof_prauc = average_precision_score(y_v, oof_p)
            oof_auc   = roc_auc_score(y_v, oof_p)
            oof_prec  = precision_score(y_v, oof_pred_v, zero_division=0)
            oof_rec   = recall_score(y_v, oof_pred_v, zero_division=0)
            oof_f1    = f1_score(y_v, oof_pred_v, zero_division=0)

            # Threshold sweep on OOF probabilities
            thresh_rows = threshold_sweep(oof_proba, y_arr, model_id)
            all_thresh_rows.extend(thresh_rows)
            any_meets = any(r["meets_provisional_criteria"] == "yes" for r in thresh_rows)

            # Best threshold for precision >= 0.60
            best_thr_row = None
            candidates_prec = [r for r in thresh_rows
                                if r["meets_precision_target"] == "yes"
                                and r["meets_recall_target"] == "yes"]
            if candidates_prec:
                best_thr_row = max(candidates_prec, key=lambda x: x["oof_f1"])

            # Repeated CV for stability
            t1 = time.time()
            rep_metrics = repeated_cv_metrics(
                Pipeline([("vec", cfg["vec"]), ("clf", cfg["clf"])]),
                texts, labels
            )
            elapsed_rep = time.time() - t1

            row = {
                "model_id":          model_id,
                "vectorizer_type":   cfg["vectorizer_type"],
                "ngram_range":       cfg["ngram_range"],
                "max_features":      cfg["max_features"],
                "min_df":            cfg["min_df"],
                "classifier":        cfg["classifier"],
                "oof_pr_auc":        round(oof_prauc, 4),
                "oof_roc_auc":       round(oof_auc, 4),
                "oof_precision":     round(oof_prec, 4),
                "oof_recall":        round(oof_rec, 4),
                "oof_f1":            round(oof_f1, 4),
                "n_total":           len(rows),
                "n_aggressive":      agg_n,
                "n_non_aggressive":  nonagg_n,
                "eval_mode":         f"oof_stratified_{N_SPLITS}fold_cv",
                "any_threshold_meets_criteria": "yes" if any_meets else "no",
                "best_threshold":    best_thr_row["threshold"] if best_thr_row else "none",
                "best_thr_precision": best_thr_row["oof_precision"] if best_thr_row else "n/a",
                "best_thr_recall":   best_thr_row["oof_recall"] if best_thr_row else "n/a",
                "best_thr_f1":       best_thr_row["oof_f1"] if best_thr_row else "n/a",
                "best_thr_coverage": best_thr_row["coverage_rate"] if best_thr_row else "n/a",
                "threshold_basis":   "oof_5fold_cv (NOT in-sample)",
                **rep_metrics,
                "elapsed_s": round(elapsed_oof + elapsed_rep, 2),
                "status": "OK",
                "note": "",
            }
            results.append(row)

            if oof_prauc > best_prauc:
                best_prauc = oof_prauc
                best_model_id = model_id
                best_oof_proba = oof_proba.copy()
                best_oof_pred = oof_pred.copy()

            meets_str = "MEETS CRITERIA" if any_meets else ""
            print(f"  [{i+1:2d}/{len(grid)}] {model_id:<50s}  "
                  f"PR-AUC={oof_prauc:.4f}  prec={oof_prec:.4f}  "
                  f"rec={oof_rec:.4f}  {meets_str}")

        except Exception as exc:
            print(f"  [{i+1:2d}/{len(grid)}] {model_id:<50s}  ERROR: {exc}")
            results.append({
                "model_id": model_id,
                "vectorizer_type": cfg["vectorizer_type"],
                "ngram_range": cfg["ngram_range"],
                "max_features": cfg["max_features"],
                "min_df": cfg["min_df"],
                "classifier": cfg["classifier"],
                "oof_pr_auc": "error",
                "status": "ERROR",
                "note": str(exc)[:120],
            })

    print(f"\n  Best model: {best_model_id}  OOF PR-AUC={best_prauc:.4f}")

    # Firm-held-out for top-3 by OOF PR-AUC
    ok_results = [r for r in results if r.get("status") == "OK"]
    ok_results.sort(key=lambda x: float(x.get("oof_pr_auc", 0) or 0), reverse=True)
    print("\n  Running firm-held-out for top-3 models by OOF PR-AUC...")

    grid_by_id = {cfg["model_id"]: cfg for cfg in grid}
    for r in ok_results[:3]:
        cfg = grid_by_id.get(r["model_id"])
        if cfg is None:
            continue
        try:
            pipe = Pipeline([("vec", cfg["vec"]), ("clf", cfg["clf"])])
            fh_prec, fh_rec, fh_f1, n_firms = firm_held_out(pipe, texts, labels, companies)
            r["firm_held_out_precision"] = fh_prec
            r["firm_held_out_recall"]    = fh_rec
            r["firm_held_out_f1"]        = fh_f1
            r["firm_held_out_n_firms"]   = n_firms
            print(f"    {r['model_id']:<50s}  FH prec={fh_prec:.4f}  rec={fh_rec:.4f}  "
                  f"f1={fh_f1:.4f}  ({n_firms} firms)")
        except Exception as exc:
            print(f"    {r['model_id']:<50s}  FH ERROR: {exc}")

    # Write CSV outputs
    RES_DIR.mkdir(parents=True, exist_ok=True)
    all_keys: list[str] = []
    for r in results:
        for k in r.keys():
            if k not in all_keys and k not in ("vec", "clf"):
                all_keys.append(k)

    with open(OUT_CV, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=all_keys, extrasaction="ignore")
        w.writeheader()
        w.writerows(results)
    print(f"\n  Written: {OUT_CV} ({len(results)} rows)")

    if all_thresh_rows:
        thresh_keys = list(all_thresh_rows[0].keys())
        with open(OUT_THRESH, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=thresh_keys)
            w.writeheader()
            w.writerows(all_thresh_rows)
        print(f"  Written: {OUT_THRESH} ({len(all_thresh_rows)} rows)")

    # OOF confusion matrix for best model
    if best_oof_pred is not None:
        cm = confusion_matrix(y_arr, best_oof_pred, labels=[1, 0])
        with open(OUT_OOF_CM, "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(["eval_mode", "oof_stratified_5fold_cv"])
            w.writerow(["best_model_id", best_model_id])
            w.writerow(["n_aggressive_actual", int(agg_n)])
            w.writerow(["n_non_aggressive_actual", int(nonagg_n)])
            w.writerow(["actual\\predicted", "aggressive", "non_aggressive_humor"])
            w.writerow(["aggressive"] + list(cm[0]))
            w.writerow(["non_aggressive_humor"] + list(cm[1]))
        print(f"  Written: {OUT_OOF_CM}")

    # Summary
    any_pass = any(
        r.get("any_threshold_meets_criteria") == "yes"
        for r in results if r.get("status") == "OK"
    )
    print(f"\n  Any model meets provisional criteria (prec>={TARGET_PRECISION}, "
          f"rec>={TARGET_RECALL}): {'YES' if any_pass else 'NO'}")
    if not any_pass:
        print("  Aggressive detector remains not usable for H2/H3 main analysis.")
        print("  Batch1 alone is insufficient for reliable aggressive classification.")

    print("=== run_batch1_aggressive_detector_search COMPLETE ===")


if __name__ == "__main__":
    main()
