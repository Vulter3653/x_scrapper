#!/usr/bin/env python3
"""Diagnostic experiments v2 for leakage-filtered humor type classifiers.

PURPOSE: DIAGNOSTIC ONLY. NOT for candidate selection or deployment.
All results should be interpreted as diagnostic evidence, not performance claims.

Runs five diagnostic experiments:
  1. Company-GroupKFold within batch1 (cross-company generalization)
  2. Word n-gram only vs. word+char n-gram feature type comparison
  3. Hard masking v2: adds #NationalRoastDay campaign event tokens
     (critical missing token — top feature in all existing variants)
  4. High-precision aggressive threshold sweep (Prec >= 0.5/0.6/0.7)
  5. Additional human labeling requirement estimate via learning curve

Key finding encoded here:
  #NationalRoastDay is a Wendy's-specific campaign event hashtag absent from
  batch1_fortune100, appears in 16 training rows (12 aggressive), and is the
  #1 weighted feature in EVERY existing masking variant. This is the primary
  unresolved leakage driver after all existing mask groups.

Absolute prohibitions (enforced by design):
  - Does NOT apply classifiers to the integrated corpus
  - Does NOT use model-predicted 564 type rows as training labels
  - Does NOT run H1/H2/H3 regressions
  - Does NOT modify data/raw, dashboard/data, or workflow files
  - Does NOT declare candidate status
"""

from __future__ import annotations

import csv
import re
import sys
import warnings
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np

warnings.filterwarnings("ignore")

REPO_ROOT = Path(__file__).resolve().parents[5]
BASE = Path(__file__).resolve().parents[1]
TRAINING_CSV = BASE / "data" / "type_training_leakage_filtered_variants.csv"
DIAG_DIR = BASE / "diagnostics"

N_CV_FOLDS = 5
RANDOM_SEEDS = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]   # 10 seeds for diagnostic stability
THRESHOLD_GRID = [0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8]


# ---------------------------------------------------------------------------
# hard masking v2 — adds campaign event tokens absent from existing masks
# ---------------------------------------------------------------------------
CAMPAIGN_EVENT_TOKENS = [
    "nationalroastday", "#nationalroastday", "national roast day",
    "roastday", "#roastday",
]

def apply_hard_mask_v2(text: str) -> str:
    """Apply mask_all_leakage_groups plus campaign event tokens."""
    # Campaign event hashtags (case-insensitive)
    for tok in CAMPAIGN_EVENT_TOKENS:
        text = re.sub(re.escape(tok), "[CAMPAIGN_EVENT_TOKEN]", text, flags=re.IGNORECASE)
    return text


def write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def load_training_data() -> list[dict]:
    with TRAINING_CSV.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


# ---------------------------------------------------------------------------
# sklearn imports — late import so compile check doesn't need them installed
# ---------------------------------------------------------------------------
def _imports():
    from sklearn.linear_model import LogisticRegression
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.pipeline import Pipeline, FeatureUnion
    from sklearn.model_selection import GroupKFold, StratifiedKFold, cross_val_predict
    from sklearn.metrics import (
        average_precision_score, roc_auc_score,
        f1_score, precision_score, recall_score, accuracy_score,
        precision_recall_curve,
    )
    return (LogisticRegression, TfidfVectorizer, Pipeline, FeatureUnion,
            GroupKFold, StratifiedKFold, cross_val_predict,
            average_precision_score, roc_auc_score,
            f1_score, precision_score, recall_score, accuracy_score,
            precision_recall_curve)


def make_word_char_pipeline(C: float = 0.1) -> Any:
    (LR, TV, Pipe, FU, *_) = _imports()
    word_tfidf = TV(analyzer="word", ngram_range=(1, 2), min_df=1,
                    sublinear_tf=True, max_features=50_000)
    char_tfidf = TV(analyzer="char_wb", ngram_range=(3, 5), min_df=1,
                    sublinear_tf=True, max_features=30_000)
    return Pipe([
        ("features", FU([("word", word_tfidf), ("char", char_tfidf)])),
        ("clf", LR(C=C, class_weight="balanced", max_iter=1000,
                   solver="liblinear", random_state=42)),
    ])


def make_word_only_pipeline(C: float = 0.1) -> Any:
    (LR, TV, Pipe, *_) = _imports()
    word_tfidf = TV(analyzer="word", ngram_range=(1, 2), min_df=1,
                    sublinear_tf=True, max_features=50_000)
    return Pipe([
        ("features", word_tfidf),
        ("clf", LR(C=C, class_weight="balanced", max_iter=1000,
                   solver="liblinear", random_state=42)),
    ])


# ---------------------------------------------------------------------------
# Experiment 1: Company-GroupKFold within batch1
# ---------------------------------------------------------------------------
def exp1_company_groupkfold(rows: list[dict]) -> list[dict]:
    (LR, TV, Pipe, FU, GKF, SKF, cvp,
     ap, roc, f1, prec, rec, acc, prc) = _imports()

    batch1 = [r for r in rows if r["source"] == "batch1_fortune100"]
    texts_orig = [r["text_original"] for r in batch1]
    texts_mask = [r["text_mask_all_leakage_groups"] for r in batch1]
    y_agg = np.array([1 if r["humor_type"] == "aggressive" else 0 for r in batch1])
    y_type = np.array([r["humor_type"] for r in batch1])
    companies = np.array([r["company_name"] for r in batch1])

    n_pos = y_agg.sum()
    n_neg = (y_agg == 0).sum()
    print(f"  [exp1] batch1 n={len(batch1)} aggressive={n_pos} non_aggressive={n_neg}")

    # GroupKFold by company (within batch1 only)
    groups = companies
    unique_companies = np.unique(groups)
    n_groups = len(unique_companies)
    n_folds = min(N_CV_FOLDS, n_groups)
    gkf = GKF(n_splits=n_folds)

    results = []
    for variant_name, texts in [("original_text_batch1_gkf", texts_orig),
                                  ("mask_all_leakage_groups_batch1_gkf", texts_mask)]:
        X = np.array(texts)
        pr_aucs, roc_aucs, f1s, precs, recs = [], [], [], [], []
        for fold, (tr_idx, te_idx) in enumerate(gkf.split(X, y_agg, groups=groups)):
            X_tr, X_te = X[tr_idx], X[te_idx]
            y_tr, y_te = y_agg[tr_idx], y_agg[te_idx]
            if y_te.sum() == 0 or y_tr.sum() == 0:
                continue  # skip folds with no positives
            pipe = make_word_char_pipeline()
            pipe.fit(X_tr, y_tr)
            prob = pipe.predict_proba(X_te)[:, 1]
            pred = (prob >= 0.5).astype(int)
            pr_aucs.append(float(ap(y_te, prob)))
            roc_aucs.append(float(roc(y_te, prob)) if len(np.unique(y_te)) > 1 else 0.0)
            f1s.append(float(f1(y_te, pred, zero_division=0)))
            precs.append(float(prec(y_te, pred, zero_division=0)))
            recs.append(float(rec(y_te, pred, zero_division=0)))

        results.append({
            "experiment": "company_groupkfold",
            "variant": variant_name,
            "n_rows": len(batch1),
            "n_folds": n_folds,
            "n_aggressive_positive": int(n_pos),
            "n_unique_groups": n_groups,
            "pr_auc_mean": round(float(np.mean(pr_aucs)), 4) if pr_aucs else None,
            "pr_auc_std": round(float(np.std(pr_aucs)), 4) if pr_aucs else None,
            "roc_auc_mean": round(float(np.mean(roc_aucs)), 4) if roc_aucs else None,
            "f1_mean": round(float(np.mean(f1s)), 4) if f1s else None,
            "precision_mean": round(float(np.mean(precs)), 4) if precs else None,
            "recall_mean": round(float(np.mean(recs)), 4) if recs else None,
            "n_valid_folds": len(pr_aucs),
            "diagnostic_note":
                "batch1_only GroupKFold by company; shows within-Fortune100 generalization",
        })
        print(f"    {variant_name}: PR-AUC={results[-1]['pr_auc_mean']} "
              f"F1={results[-1]['f1_mean']} (n_folds={len(pr_aucs)})")

    return results


# ---------------------------------------------------------------------------
# Experiment 2: Word-only vs Word+Char feature comparison
# ---------------------------------------------------------------------------
def exp2_feature_type_comparison(rows: list[dict]) -> list[dict]:
    (LR, TV, Pipe, FU, GKF, SKF, cvp,
     ap, roc, f1, prec, rec, acc, prc) = _imports()

    texts_orig = [r["text_original"] for r in rows]
    texts_mask = [r["text_mask_all_leakage_groups"] for r in rows]
    y_agg = np.array([1 if r["humor_type"] == "aggressive" else 0 for r in rows])
    sources = np.array([r["source"] for r in rows])

    results = []
    for variant_name, texts in [("original_text", texts_orig),
                                  ("mask_all_leakage_groups", texts_mask)]:
        X = np.array(texts)
        for feat_type, pipe_fn in [("word_only", make_word_only_pipeline),
                                    ("word_char", make_word_char_pipeline)]:
            pr_aucs, f1s, precs, recs = [], [], [], []
            for seed in RANDOM_SEEDS:
                skf = SKF(n_splits=5, shuffle=True, random_state=seed)
                for tr, te in skf.split(X, y_agg):
                    X_tr, X_te = X[tr], X[te]
                    y_tr, y_te = y_agg[tr], y_agg[te]
                    if y_te.sum() == 0:
                        continue
                    pipe = pipe_fn()
                    pipe.fit(X_tr, y_tr)
                    prob = pipe.predict_proba(X_te)[:, 1]
                    pred = (prob >= 0.5).astype(int)
                    pr_aucs.append(float(ap(y_te, prob)))
                    f1s.append(float(f1(y_te, pred, zero_division=0)))
                    precs.append(float(prec(y_te, pred, zero_division=0)))
                    recs.append(float(rec(y_te, pred, zero_division=0)))

            results.append({
                "experiment": "feature_type_comparison",
                "variant": variant_name,
                "feature_type": feat_type,
                "n_rows": len(rows),
                "n_seeds": len(RANDOM_SEEDS),
                "pr_auc_mean": round(float(np.mean(pr_aucs)), 4) if pr_aucs else None,
                "pr_auc_std": round(float(np.std(pr_aucs)), 4) if pr_aucs else None,
                "f1_mean": round(float(np.mean(f1s)), 4) if f1s else None,
                "precision_mean": round(float(np.mean(precs)), 4) if precs else None,
                "recall_mean": round(float(np.mean(recs)), 4) if recs else None,
                "diagnostic_note":
                    "word_only drops char n-grams; detects source-cue leakage via char patterns",
            })
            print(f"    {variant_name} {feat_type}: PR-AUC={results[-1]['pr_auc_mean']} "
                  f"F1={results[-1]['f1_mean']}")

    return results


# ---------------------------------------------------------------------------
# Experiment 3: Hard masking v2 — NationalRoastDay
# ---------------------------------------------------------------------------
def exp3_hard_masking_v2(rows: list[dict]) -> list[dict]:
    (LR, TV, Pipe, FU, GKF, SKF, cvp,
     ap, roc, f1, prec, rec, acc, prc) = _imports()

    y_agg = np.array([1 if r["humor_type"] == "aggressive" else 0 for r in rows])
    sources = [r["source"] for r in rows]
    n_pos = y_agg.sum()

    # Build hard_mask_v2 text: apply on top of mask_all_leakage_groups
    texts_mask_v2 = [
        apply_hard_mask_v2(r["text_mask_all_leakage_groups"]) for r in rows
    ]
    # Count how many rows were changed
    changed = sum(
        1 for r, t in zip(rows, texts_mask_v2)
        if t != r["text_mask_all_leakage_groups"]
    )
    wendys_changed = sum(
        1 for r, t in zip(rows, texts_mask_v2)
        if t != r["text_mask_all_leakage_groups"] and r["source"] == "wendys_human_type"
    )
    agg_changed = sum(
        1 for r, t, lbl in zip(rows, texts_mask_v2, y_agg)
        if t != r["text_mask_all_leakage_groups"] and lbl == 1
    )
    print(f"  [exp3] hard_mask_v2 changes: {changed} rows "
          f"(wendys={wendys_changed} aggressive={agg_changed})")

    results_metrics = []
    results_heldout = []
    results_top_feat = []

    for variant_name, texts in [("mask_all_leakage_groups", [r["text_mask_all_leakage_groups"] for r in rows]),
                                  ("hard_mask_v2_nationalroastday", texts_mask_v2)]:
        X = np.array(texts)
        pr_aucs, f1s, precs, recs = [], [], [], []
        skf = SKF(n_splits=5, shuffle=True, random_state=0)
        for seed in RANDOM_SEEDS:
            skf = SKF(n_splits=5, shuffle=True, random_state=seed)
            for tr, te in skf.split(X, y_agg):
                X_tr, X_te = X[tr], X[te]
                y_tr, y_te = y_agg[tr], y_agg[te]
                if y_te.sum() == 0:
                    continue
                pipe = make_word_char_pipeline()
                pipe.fit(X_tr, y_tr)
                prob = pipe.predict_proba(X_te)[:, 1]
                pred = (prob >= 0.5).astype(int)
                pr_aucs.append(float(ap(y_te, prob)))
                f1s.append(float(f1(y_te, pred, zero_division=0)))
                precs.append(float(prec(y_te, pred, zero_division=0)))
                recs.append(float(rec(y_te, pred, zero_division=0)))

        results_metrics.append({
            "experiment": "hard_masking_v2",
            "variant": variant_name,
            "n_rows": len(rows),
            "n_aggressive": int(n_pos),
            "n_changed_rows": changed if "v2" in variant_name else 0,
            "n_changed_aggressive": agg_changed if "v2" in variant_name else 0,
            "n_changed_wendys": wendys_changed if "v2" in variant_name else 0,
            "pr_auc_mean": round(float(np.mean(pr_aucs)), 4) if pr_aucs else None,
            "pr_auc_std": round(float(np.std(pr_aucs)), 4) if pr_aucs else None,
            "f1_mean": round(float(np.mean(f1s)), 4) if f1s else None,
            "precision_mean": round(float(np.mean(precs)), 4) if precs else None,
            "recall_mean": round(float(np.mean(recs)), 4) if recs else None,
            "leakage_token_added": "nationalroastday,roastday" if "v2" in variant_name else "",
            "diagnostic_note":
                "mask_all + NationalRoastDay campaign event token; tests if rank-1 leakage feature drives signal",
        })
        print(f"    {variant_name}: PR-AUC={results_metrics[-1]['pr_auc_mean']} "
              f"F1={results_metrics[-1]['f1_mean']}")

        # Source held-out
        batch1_idx = [i for i, r in enumerate(rows) if r["source"] == "batch1_fortune100"]
        wendys_idx = [i for i, r in enumerate(rows) if r["source"] == "wendys_human_type"]
        for scope, tr_idx, te_idx in [
            ("train_batch1_test_wendys", batch1_idx, wendys_idx),
            ("train_wendys_test_batch1", wendys_idx, batch1_idx),
        ]:
            X_tr = X[tr_idx]
            X_te = X[te_idx]
            y_tr = y_agg[tr_idx]
            y_te = y_agg[te_idx]
            if y_te.sum() == 0 or y_tr.sum() == 0:
                continue
            pipe = make_word_char_pipeline()
            pipe.fit(X_tr, y_tr)
            prob = pipe.predict_proba(X_te)[:, 1]
            pred = (prob >= 0.5).astype(int)
            results_heldout.append({
                "experiment": "hard_masking_v2_source_heldout",
                "variant": variant_name,
                "eval_scope": scope,
                "n_rows": len(te_idx),
                "n_aggressive_in_test": int(y_te.sum()),
                "pr_auc": round(float(ap(y_te, prob)), 4),
                "roc_auc": round(float(roc(y_te, prob)) if len(np.unique(y_te)) > 1 else 0.0, 4),
                "f1": round(float(f1(y_te, pred, zero_division=0)), 4),
                "precision": round(float(prec(y_te, pred, zero_division=0)), 4),
                "recall": round(float(rec(y_te, pred, zero_division=0)), 4),
            })

        # Top features
        batch1_X = X[batch1_idx]
        wendys_X = X[wendys_idx]
        all_X = X
        y_tr = y_agg
        pipe = make_word_char_pipeline()
        pipe.fit(all_X, y_tr)
        feat_names = pipe.named_steps["features"].get_feature_names_out()
        coefs = pipe.named_steps["clf"].coef_[0]
        top_idx = np.argsort(np.abs(coefs))[::-1][:25]
        for rank, idx in enumerate(top_idx, 1):
            feat = feat_names[idx]
            lkg_flag = "FAIL" if any(
                tok in feat.lower()
                for tok in ["wendy", "nationalroastday", "roastday", "frosty", "baconator",
                            "burgking", "burger king", "mcdonalds", "taco bell"]
            ) else "PASS"
            results_top_feat.append({
                "experiment": "hard_masking_v2_top_features",
                "variant": variant_name,
                "rank": rank,
                "feature": feat,
                "weight": round(float(coefs[idx]), 6),
                "leakage_flag": lkg_flag,
            })

    return results_metrics, results_heldout, results_top_feat


# ---------------------------------------------------------------------------
# Experiment 4: High-precision threshold sweep
# ---------------------------------------------------------------------------
def exp4_high_precision_threshold(rows: list[dict]) -> list[dict]:
    (LR, TV, Pipe, FU, GKF, SKF, cvp,
     ap, roc, f1_fn, prec_fn, rec_fn, acc, prc) = _imports()

    y_agg = np.array([1 if r["humor_type"] == "aggressive" else 0 for r in rows])
    results = []

    for variant_name, texts in [
        ("original_text", [r["text_original"] for r in rows]),
        ("mask_all_leakage_groups", [r["text_mask_all_leakage_groups"] for r in rows]),
        ("hard_mask_v2_nationalroastday",
         [apply_hard_mask_v2(r["text_mask_all_leakage_groups"]) for r in rows]),
    ]:
        X = np.array(texts)
        # Collect OOF probabilities across seeds
        all_probs = np.zeros(len(rows))
        all_counts = np.zeros(len(rows))
        for seed in RANDOM_SEEDS:
            skf = SKF(n_splits=5, shuffle=True, random_state=seed)
            probs_this_seed = np.zeros(len(rows))
            for tr, te in skf.split(X, y_agg):
                if y_agg[tr].sum() == 0:
                    continue
                pipe = make_word_char_pipeline()
                pipe.fit(X[tr], y_agg[tr])
                prob = pipe.predict_proba(X[te])[:, 1]
                probs_this_seed[te] = prob
            all_probs += probs_this_seed
            all_counts += 1
        avg_oof_prob = all_probs / np.maximum(all_counts, 1)

        for threshold in THRESHOLD_GRID:
            pred = (avg_oof_prob >= threshold).astype(int)
            n_flagged = pred.sum()
            if n_flagged == 0:
                precision_val = 0.0
                recall_val = 0.0
                f1_val = 0.0
            else:
                precision_val = float(prec_fn(y_agg, pred, zero_division=0))
                recall_val = float(rec_fn(y_agg, pred, zero_division=0))
                f1_val = float(f1_fn(y_agg, pred, zero_division=0))
            results.append({
                "experiment": "high_precision_threshold_sweep",
                "variant": variant_name,
                "threshold": threshold,
                "n_flagged": int(n_flagged),
                "n_true_aggressive": int(y_agg.sum()),
                "precision": round(precision_val, 4),
                "recall": round(recall_val, 4),
                "f1": round(f1_val, 4),
                "meets_prec_50": "yes" if precision_val >= 0.5 else "no",
                "meets_prec_60": "yes" if precision_val >= 0.6 else "no",
                "meets_prec_70": "yes" if precision_val >= 0.7 else "no",
                "operational_note":
                    "averaged OOF prob across 10 seeds; use for triage, not deployment",
            })
        print(f"    {variant_name}: best prec={max(r['precision'] for r in results if r['variant']==variant_name):.3f}")

    return results


# ---------------------------------------------------------------------------
# Experiment 5: Labeling requirement estimate
# ---------------------------------------------------------------------------
def exp5_labeling_requirement(rows: list[dict]) -> list[dict]:
    (LR, TV, Pipe, FU, GKF, SKF, cvp,
     ap, roc, f1_fn, prec_fn, rec_fn, acc, prc) = _imports()

    texts = [r["text_mask_all_leakage_groups"] for r in rows]
    y_agg = np.array([1 if r["humor_type"] == "aggressive" else 0 for r in rows])
    sources = [r["source"] for r in rows]

    n_total = len(rows)
    n_pos = int(y_agg.sum())
    n_neg = n_total - n_pos
    pos_rate = n_pos / n_total
    batch1_agg = sum(1 for r in rows if r["source"] == "batch1_fortune100"
                     and r["humor_type"] == "aggressive")

    # Learning curve: subsample training data, measure PR-AUC
    curve_rows = []
    sample_fracs = [0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
    X = np.array(texts)
    rng = np.random.RandomState(42)
    for frac in sample_fracs:
        pr_aucs_frac = []
        n_sample = max(20, int(n_total * frac))
        for seed in range(5):
            skf = SKF(n_splits=5, shuffle=True, random_state=seed)
            for tr, te in skf.split(X, y_agg):
                if y_agg[te].sum() == 0:
                    continue
                # Subsample training set
                n_tr_sample = max(10, int(len(tr) * frac))
                if n_tr_sample < len(tr):
                    rng_s = np.random.RandomState(seed * 100 + n_tr_sample)
                    tr_sub = rng_s.choice(tr, n_tr_sample, replace=False)
                else:
                    tr_sub = tr
                if y_agg[tr_sub].sum() == 0:
                    continue
                pipe = make_word_char_pipeline()
                pipe.fit(X[tr_sub], y_agg[tr_sub])
                prob = pipe.predict_proba(X[te])[:, 1]
                pr_aucs_frac.append(float(ap(y_agg[te], prob)))
        if pr_aucs_frac:
            curve_rows.append({
                "experiment": "labeling_requirement_learning_curve",
                "n_training_rows": int(n_total * frac),
                "n_aggressive_rows": int(n_pos * frac),
                "training_fraction": round(frac, 2),
                "pr_auc_mean": round(float(np.mean(pr_aucs_frac)), 4),
                "pr_auc_std": round(float(np.std(pr_aucs_frac)), 4),
                "variant": "mask_all_leakage_groups",
            })
            print(f"    frac={frac:.1f} n={int(n_total*frac)} PR-AUC={curve_rows[-1]['pr_auc_mean']}")

    # Simple extrapolation: fit line to log(n) → PR-AUC
    ns = np.array([r["n_training_rows"] for r in curve_rows], dtype=float)
    pr_means = np.array([r["pr_auc_mean"] for r in curve_rows])
    if len(ns) >= 3:
        log_ns = np.log(ns)
        slope, intercept = np.polyfit(log_ns, pr_means, 1)
        target_pr_auc_values = [0.50, 0.55, 0.60]
        for target in target_pr_auc_values:
            if slope > 0:
                n_needed = int(np.exp((target - intercept) / slope))
            else:
                n_needed = -1
            curve_rows.append({
                "experiment": "labeling_requirement_extrapolation",
                "target_pr_auc": target,
                "estimated_n_rows_needed": n_needed,
                "estimated_n_aggressive_rows_needed": int(n_needed * pos_rate) if n_needed > 0 else -1,
                "current_n_rows": n_total,
                "current_n_aggressive": n_pos,
                "current_batch1_aggressive": batch1_agg,
                "slope_log_fit": round(slope, 6),
                "intercept_log_fit": round(intercept, 6),
                "diagnostic_note":
                    "log-linear extrapolation; treat as rough order-of-magnitude estimate only",
                "n_training_rows": "",
                "n_aggressive_rows": "",
                "training_fraction": "",
                "pr_auc_mean": "",
                "pr_auc_std": "",
                "variant": "mask_all_leakage_groups",
            })
    return curve_rows


# ---------------------------------------------------------------------------
# FP/FN examples with text
# ---------------------------------------------------------------------------
def extract_fp_fn_examples(rows: list[dict]) -> tuple[list[dict], list[dict]]:
    (LR, TV, Pipe, FU, GKF, SKF, cvp,
     ap, roc, f1_fn, prec_fn, rec_fn, acc, prc) = _imports()

    text_by_id = {r["row_id"]: r for r in rows}
    y_agg = np.array([1 if r["humor_type"] == "aggressive" else 0 for r in rows])

    all_oof_prob = np.zeros(len(rows))
    count = np.zeros(len(rows))
    X_orig = np.array([r["text_original"] for r in rows])
    skf = SKF(n_splits=5, shuffle=True, random_state=0)
    for tr, te in skf.split(X_orig, y_agg):
        if y_agg[tr].sum() == 0:
            continue
        pipe = make_word_char_pipeline()
        pipe.fit(X_orig[tr], y_agg[tr])
        prob = pipe.predict_proba(X_orig[te])[:, 1]
        all_oof_prob[te] += prob
        count[te] += 1
    avg_prob = all_oof_prob / np.maximum(count, 1)

    # FP: true=0, avg_oof_prob > 0.5
    fp_rows = []
    for i, r in enumerate(rows):
        if y_agg[i] == 0 and avg_prob[i] > 0.5:
            fp_rows.append({
                "example_type": "false_positive",
                "row_id": r["row_id"],
                "source": r["source"],
                "company_name": r.get("company_name", ""),
                "true_label": r["humor_type"],
                "true_aggressive": 0,
                "pred_aggressive_prob": round(float(avg_prob[i]), 4),
                "text": r["text_original"][:200],
                "suspected_leakage_cue": _detect_leakage_cues(r["text_original"]),
            })
    fp_rows.sort(key=lambda x: -x["pred_aggressive_prob"])

    # FN: true=1, avg_oof_prob < 0.4
    fn_rows = []
    for i, r in enumerate(rows):
        if y_agg[i] == 1 and avg_prob[i] < 0.4:
            fn_rows.append({
                "example_type": "false_negative",
                "row_id": r["row_id"],
                "source": r["source"],
                "company_name": r.get("company_name", ""),
                "true_label": r["humor_type"],
                "true_aggressive": 1,
                "pred_aggressive_prob": round(float(avg_prob[i]), 4),
                "text": r["text_original"][:200],
                "suspected_leakage_cue": _detect_leakage_cues(r["text_original"]),
            })
    fn_rows.sort(key=lambda x: x["pred_aggressive_prob"])

    return fp_rows, fn_rows


def _detect_leakage_cues(text: str) -> str:
    text_l = text.lower()
    cues = []
    if "nationalroastday" in text_l or "national roast day" in text_l:
        cues.append("nationalroastday_hashtag")
    if "wendy" in text_l:
        cues.append("wendy_brand")
    if any(t in text_l for t in ["frosty", "baconator", "nuggs"]):
        cues.append("wendy_product")
    if any(t in text_l for t in ["burger king", "mcdonald", "taco bell"]):
        cues.append("competitor_reference")
    if "should" in text_l:
        cues.append("modal_should")
    if "roast" in text_l:
        cues.append("roast_verb")
    return ";".join(cues) if cues else "none_detected"


# ---------------------------------------------------------------------------
# Audit report summary
# ---------------------------------------------------------------------------
def build_audit_report(exp1, exp2, exp3_m, exp3_h, exp3_f, exp4, exp5) -> list[dict]:
    rows = []

    def add(item, value, evidence, interpretation, priority="info"):
        rows.append({
            "audit_item": item,
            "value": str(value),
            "evidence": str(evidence),
            "interpretation": interpretation,
            "priority": priority,
        })

    # Critical issues
    add("nationalroastday_in_mask_all",
        "FALSE",
        "#NationalRoastDay is rank-1 feature in ALL 6 existing variants including mask_all_leakage_groups",
        "Critical unresolved leakage. This hashtag is Wendy's-exclusive (wendys_count=16, batch1_count=0) "
        "and 12/16 rows are aggressive. Must be masked before any performance interpretation is valid.",
        priority="CRITICAL")

    add("source_heldout_f1_aggressive",
        "0.0 for both train_batch1_test_wendys and train_wendys_test_batch1",
        "aggressive_filtered_full_eval_source_heldout.csv: f1=0.0 for all 6 variants",
        "Model learns source-specific cues only. Cannot generalize across sources. "
        "F1=0.0 on held-out source means any cross-source application will have zero recall.",
        priority="CRITICAL")

    add("threshold_pass_rate",
        "0/210 (zero thresholds pass primary or secondary criteria, all variants)",
        "aggressive_filtered_full_eval_thresholds.csv",
        "No operational threshold meets quality bar. Not deployable at any precision/recall trade-off point.",
        priority="CRITICAL")

    add("all_variants_leakage_fail",
        "FAIL for all 6 variants (aggressive) and all 6 variants (4-class type)",
        "leakage_flag=FAIL in both summary CSVs",
        "Wendy-specific tokens (wendy, wendys, wendy's) remain in top-3 features for aggressive class "
        "even after mask_all_leakage_groups. char n-grams amplify leakage via sub-word patterns.",
        priority="CRITICAL")

    # Performance summary
    add("aggressive_pr_auc_range",
        "0.3508–0.3747 across 6 variants",
        "aggressive_filtered_full_eval_summary.csv",
        "Low PR-AUC for imbalanced binary (139 pos / 787 neg). "
        "Masking does not improve performance — leakage was inflating apparent performance.",
        priority="WARNING")

    add("four_class_macro_f1_range",
        "0.4075–0.4194 across 6 variants",
        "type_filtered_metrics.csv",
        "Moderate macro-F1. Dominated by affiliative (support=427, F1~0.60) and self-enhancing (F1~0.45-0.47). "
        "Self-defeating extremely poor (support=39, F1=0.13-0.18).",
        priority="WARNING")

    add("self_defeating_label_count",
        "39 samples total",
        "type_filtered_per_class_metrics.csv support=39",
        "Insufficient training data for self-defeating. F1 will remain below 0.25 "
        "regardless of other improvements. Additional human labeling is prerequisite.",
        priority="WARNING")

    # Feature audit
    add("top_feature_rank1",
        "word__nationalroastday (weight=0.21) for both original_text and mask_all_leakage_groups",
        "aggressive_filtered_full_eval_top_features.csv rank=1",
        "Campaign event hashtag is #1 feature — stronger than any actual humor/language signal. "
        "This inflates in-fold performance and catastrophically fails on held-out source.",
        priority="CRITICAL")

    add("char_ngrams_from_roast",
        "char n-grams oas, oast, onal, nal, roast, roas dominate ranks 3-20",
        "aggressive_filtered_full_eval_top_features.csv",
        "char_wb TF-IDF is learning sub-word patterns of nationalroastday and roast. "
        "These will be absent in Fortune 100 general corpus, causing zero transfer.",
        priority="CRITICAL")

    add("competitor_token_in_mask_all_rank2",
        "word__competitor_token rank=2 in mask_all_leakage_groups (weight=0.198)",
        "aggressive_filtered_full_eval_top_features.csv variant=mask_all_leakage_groups",
        "When nationalroastday is not masked, masking competitor names creates a new "
        "leakage token [COMPETITOR_TOKEN] that signals Wendy's identity. "
        "Hard_mask_v2 should resolve if nationalroastday is properly masked.",
        priority="WARNING")

    # Diagnostic experiments needed
    add("hard_mask_v2_status", "SCHEDULED (exp3)",
        "run_type_classifier_diagnostic_v2.py exp3",
        "Add #NationalRoastDay to mask list. Expect PR-AUC to DROP if leakage was inflating it.",
        priority="ACTION_REQUIRED")

    add("company_groupkfold_status", "SCHEDULED (exp1)",
        "run_type_classifier_diagnostic_v2.py exp1",
        "Within-batch1 company-GroupKFold tests Fortune 100 cross-company generalization. "
        "Aggressive is sparse per company (mode=3-6 per company) — expect low F1.",
        priority="ACTION_REQUIRED")

    add("word_vs_char_feature_status", "SCHEDULED (exp2)",
        "run_type_classifier_diagnostic_v2.py exp2",
        "If word+char >> word-only, char n-grams are carrying source-cue signal. "
        "If similar, leakage is primarily word-level.",
        priority="ACTION_REQUIRED")

    add("candidate_status",
        "NOT_A_CANDIDATE",
        "All variants: leakage_flag=FAIL, threshold_pass=0, source_heldout_f1=0.0",
        "No variant meets minimum quality criteria. Do not apply to integrated corpus "
        "or Fortune 100 posts. Diagnostic experiments must complete first.",
        priority="CRITICAL")

    return rows


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> int:
    print("=== run_type_classifier_diagnostic_v2 ===")
    print("PURPOSE: DIAGNOSTIC ONLY — not for candidate selection\n")

    try:
        from sklearn.linear_model import LogisticRegression  # noqa: F401
    except ImportError:
        print("ERROR: scikit-learn not installed. Cannot run experiments.", file=sys.stderr)
        print("Run: pip install scikit-learn")
        # Still write the static audit report and scaffold
        _write_static_outputs()
        return 1

    rows = load_training_data()
    print(f"Loaded {len(rows)} training rows from {TRAINING_CSV.name}")
    print(f"  Sources: {Counter(r['source'] for r in rows)}")
    print(f"  Aggressive: {sum(1 for r in rows if r['humor_type']=='aggressive')}")
    print(f"  self-defeating: {sum(1 for r in rows if r['humor_type']=='self-defeating')}")
    print()

    # Exp 1: Company GroupKFold
    print("[EXP 1] Company-GroupKFold within batch1...")
    exp1_results = exp1_company_groupkfold(rows)
    write_csv(DIAG_DIR / "diag_company_groupkfold.csv", exp1_results,
              ["experiment", "variant", "n_rows", "n_folds", "n_aggressive_positive",
               "n_unique_groups", "pr_auc_mean", "pr_auc_std", "roc_auc_mean",
               "f1_mean", "precision_mean", "recall_mean", "n_valid_folds", "diagnostic_note"])
    print()

    # Exp 2: Feature type comparison
    print("[EXP 2] Word-only vs Word+Char feature comparison...")
    exp2_results = exp2_feature_type_comparison(rows)
    write_csv(DIAG_DIR / "diag_feature_type_comparison.csv", exp2_results,
              ["experiment", "variant", "feature_type", "n_rows", "n_seeds",
               "pr_auc_mean", "pr_auc_std", "f1_mean", "precision_mean", "recall_mean",
               "diagnostic_note"])
    print()

    # Exp 3: Hard masking v2
    print("[EXP 3] Hard masking v2 (NationalRoastDay)...")
    exp3_metrics, exp3_heldout, exp3_topfeat = exp3_hard_masking_v2(rows)
    write_csv(DIAG_DIR / "diag_hard_masking_v2_metrics.csv", exp3_metrics,
              ["experiment", "variant", "n_rows", "n_aggressive", "n_changed_rows",
               "n_changed_aggressive", "n_changed_wendys",
               "pr_auc_mean", "pr_auc_std", "f1_mean", "precision_mean", "recall_mean",
               "leakage_token_added", "diagnostic_note"])
    write_csv(DIAG_DIR / "diag_hard_masking_v2_source_heldout.csv", exp3_heldout,
              ["experiment", "variant", "eval_scope", "n_rows", "n_aggressive_in_test",
               "pr_auc", "roc_auc", "f1", "precision", "recall"])
    write_csv(DIAG_DIR / "diag_hard_masking_v2_top_features.csv", exp3_topfeat,
              ["experiment", "variant", "rank", "feature", "weight", "leakage_flag"])
    print()

    # Exp 4: High-precision threshold
    print("[EXP 4] High-precision aggressive threshold sweep...")
    exp4_results = exp4_high_precision_threshold(rows)
    write_csv(DIAG_DIR / "diag_high_precision_threshold.csv", exp4_results,
              ["experiment", "variant", "threshold", "n_flagged", "n_true_aggressive",
               "precision", "recall", "f1",
               "meets_prec_50", "meets_prec_60", "meets_prec_70", "operational_note"])
    print()

    # Exp 5: Labeling requirement
    print("[EXP 5] Labeling requirement estimate...")
    exp5_results = exp5_labeling_requirement(rows)
    write_csv(DIAG_DIR / "diag_labeling_requirement.csv", exp5_results,
              ["experiment", "n_training_rows", "n_aggressive_rows", "training_fraction",
               "pr_auc_mean", "pr_auc_std", "variant",
               "target_pr_auc", "estimated_n_rows_needed",
               "estimated_n_aggressive_rows_needed", "current_n_rows", "current_n_aggressive",
               "current_batch1_aggressive", "slope_log_fit", "intercept_log_fit",
               "diagnostic_note"])
    print()

    # FP/FN examples
    print("[FP/FN] Extracting representative false positive/negative examples...")
    fp_examples, fn_examples = extract_fp_fn_examples(rows)
    ex_fields = ["example_type", "row_id", "source", "company_name",
                 "true_label", "true_aggressive", "pred_aggressive_prob",
                 "text", "suspected_leakage_cue"]
    write_csv(DIAG_DIR / "diag_fp_examples.csv", fp_examples[:30], ex_fields)
    write_csv(DIAG_DIR / "diag_fn_examples.csv", fn_examples[:30], ex_fields)
    print(f"  FP examples (true=0, prob>0.5): {len(fp_examples)}")
    print(f"  FN examples (true=1, prob<0.4): {len(fn_examples)}")
    print()

    # Audit report
    print("[AUDIT] Building audit report...")
    audit = build_audit_report(
        exp1_results, exp2_results, exp3_metrics,
        exp3_heldout, exp3_topfeat, exp4_results, exp5_results
    )
    write_csv(DIAG_DIR / "diag_audit_report.csv", audit,
              ["audit_item", "value", "evidence", "interpretation", "priority"])
    print()

    # Print critical findings
    critical = [r for r in audit if r["priority"] == "CRITICAL"]
    print("=== CRITICAL FINDINGS ===")
    for r in critical:
        print(f"  [{r['priority']}] {r['audit_item']}")
        print(f"    value: {r['value'][:80]}")
        print(f"    interpretation: {r['interpretation'][:120]}")

    print(f"\n=== All outputs → {DIAG_DIR} ===")
    print("candidate_status: NOT_A_CANDIDATE (diagnostic only)")
    print("=== run_type_classifier_diagnostic_v2 COMPLETE ===")
    return 0


def _write_static_outputs() -> None:
    """Write audit report and scaffold even if sklearn is unavailable."""
    print("Writing static audit report (no sklearn experiments)...")
    audit = build_audit_report([], [], [], [], [], [], [])
    write_csv(DIAG_DIR / "diag_audit_report.csv", audit,
              ["audit_item", "value", "evidence", "interpretation", "priority"])
    print(f"Written: {DIAG_DIR}/diag_audit_report.csv")


if __name__ == "__main__":
    raise SystemExit(main())
