#!/usr/bin/env python3
"""Event-aware diagnostic v3: #NationalRoastDay as campaign context signal.

PURPOSE: DIAGNOSTIC ONLY. NOT for candidate selection or deployment.

#NationalRoastDay is Wendy's official campaign event where they publicly roast
competitor brands. It appears 17 times in training data (all wendys_human_type,
13 aggressive + 4 affiliative). This script tests whether the hashtag functions
as a useful campaign event context signal or a source-specific shortcut.

Design rationale:
  - The hashtag marks a specific campaign event with a known real-world context
    (aggressive brand roasting). It is NOT a random brand token.
  - However, because all 17 event posts are from wendys_human_type, a model that
    learns #NationalRoastDay = aggressive may be exploiting source identity, not
    the underlying aggressive humor pattern.
  - Variant D (delete token + add binary event feature) separates these two:
    it tells the model "this is an event post" without letting it use the raw
    subword patterns of the hashtag.

Text variant comparison (A–F):
  A. original_text — unmodified baseline
  C. NationalRoastDay token deleted (deletion masking sensitivity check)
  D. NationalRoastDay deleted from text + explicit event dummy feature column
  E. Non-event posts only (17 event rows excluded from training AND test)
  F. Event posts only — single held-out eval (train on non-event, test on event)
  (B is implicit: variant A with per-event-status reporting)

Core evaluations:
  1. Full 5-fold CV across seeds (variants A, C, D)
  2. Non-event-only CV (variant E: 909 rows, 126 aggressive)
  3. Train non-event → test event (transfer eval: can model find event-aggressive?)
  4. Train event → test non-event (reverse transfer; 17 train rows — unstable)
  5. Source held-out (train_batch1_test_wendys, train_wendys_test_batch1)
  6. Source held-out stratified by event status
  7. Company GroupKFold within batch1 (non-event aggressive only)
  8. Feature importance — event vs non-event top features

Key prohibitions (enforced by design):
  - Does NOT apply classifiers to integrated corpus
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

BASE = Path(__file__).resolve().parents[1]
TRAINING_CSV = BASE / "data" / "type_training_leakage_filtered_variants.csv"
DIAG_DIR = BASE / "diagnostics"

RANDOM_SEEDS = list(range(10))
N_CV_FOLDS = 5

# Campaign event regex: catches all orthographic variants
CAMPAIGN_RE = re.compile(
    r"#?national\s?roast\s?day|#?nationalroastday|#?roastday",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Feature vocabulary for the has_* event dummy variables
# ---------------------------------------------------------------------------
def add_event_flags(rows: list[dict]) -> None:
    """Add event flag columns to each row dict (in place)."""
    for r in rows:
        t = r["text_original"]
        r["has_national_roast_day"] = int(bool(CAMPAIGN_RE.search(t)))
        # Separate marker: any "roast" verb (broader event signal)
        r["has_roast_event_marker"] = int(bool(re.search(r"\broast\b", t, re.IGNORECASE)))
        # Campaign aggressive context: event post AND aggressive-leaning cues
        r["campaign_aggressive_context"] = int(
            r["has_national_roast_day"] == 1
            and re.search(r"\broast\b|\bburn\b|\bwreck\b|\bsavage\b", t, re.IGNORECASE) is not None
        )


def remove_campaign_token(text: str) -> str:
    """Remove #NationalRoastDay token (and close variants) from text."""
    return CAMPAIGN_RE.sub("", text).strip()


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
# sklearn helpers
# ---------------------------------------------------------------------------
def _sk():
    from sklearn.linear_model import LogisticRegression
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.pipeline import Pipeline
    from sklearn.model_selection import GroupKFold, StratifiedKFold
    from sklearn.metrics import (
        average_precision_score, roc_auc_score,
        f1_score, precision_score, recall_score,
    )
    from scipy.sparse import hstack, csr_matrix
    return (LogisticRegression, TfidfVectorizer, Pipeline,
            GroupKFold, StratifiedKFold,
            average_precision_score, roc_auc_score,
            f1_score, precision_score, recall_score,
            hstack, csr_matrix)


def _make_word_char_vectorizer():
    (_, TV, *_) = _sk()
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.pipeline import FeatureUnion
    word = TfidfVectorizer(analyzer="word", ngram_range=(1, 2), min_df=1,
                           sublinear_tf=True, max_features=50_000)
    char = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), min_df=1,
                           sublinear_tf=True, max_features=30_000)
    return FeatureUnion([("word", word), ("char", char)])


def _clf(C: float = 0.1):
    from sklearn.linear_model import LogisticRegression
    return LogisticRegression(C=C, class_weight="balanced", max_iter=1000,
                              solver="liblinear", random_state=42)


def _metrics(y_true, y_prob, y_pred, zero_div=0):
    (LR, TV, Pipe, GKF, SKF,
     ap, roc, f1, prec, rec, hstack, csr) = _sk()
    n_pos = int(y_true.sum())
    n_neg = int((y_true == 0).sum())
    pr_auc = float(ap(y_true, y_prob)) if n_pos > 0 else 0.0
    roc_auc = float(roc(y_true, y_prob)) if n_pos > 0 and n_neg > 0 else 0.0
    f1_val = float(f1(y_true, y_pred, zero_division=zero_div))
    prec_val = float(prec(y_true, y_pred, zero_division=zero_div))
    rec_val = float(rec(y_true, y_pred, zero_division=zero_div))
    return pr_auc, roc_auc, f1_val, prec_val, rec_val


def _cv_aggregate(results: list[tuple]) -> dict:
    pr_aucs = [r[0] for r in results]
    roc_aucs = [r[1] for r in results]
    f1s = [r[2] for r in results]
    precs = [r[3] for r in results]
    recs = [r[4] for r in results]
    return {
        "pr_auc_mean": round(float(np.mean(pr_aucs)), 4),
        "pr_auc_std": round(float(np.std(pr_aucs)), 4),
        "roc_auc_mean": round(float(np.mean(roc_aucs)), 4),
        "f1_mean": round(float(np.mean(f1s)), 4),
        "precision_mean": round(float(np.mean(precs)), 4),
        "recall_mean": round(float(np.mean(recs)), 4),
        "n_folds_used": len(results),
    }


# ---------------------------------------------------------------------------
# Feature builders for each variant
# ---------------------------------------------------------------------------
def _build_text_features_cv(X_texts, y, variant_name, seeds, n_folds, event_flags=None):
    """Run multi-seed StratifiedKFold CV. Returns list of (pr_auc, roc, f1, prec, rec)."""
    (LR, TV, Pipe, GKF, SKF,
     ap, roc, f1, prec, rec, hstack, csr) = _sk()

    results = []
    use_event_dummy = variant_name == "variant_D_event_dummy" and event_flags is not None

    for seed in seeds:
        skf = SKF(n_splits=n_folds, shuffle=True, random_state=seed)
        for tr, te in skf.split(X_texts, y):
            y_tr, y_te = y[tr], y[te]
            if y_te.sum() == 0 or y_tr.sum() == 0:
                continue

            feat = _make_word_char_vectorizer()
            X_tr_text = feat.fit_transform(np.array(X_texts)[tr])
            X_te_text = feat.transform(np.array(X_texts)[te])

            if use_event_dummy:
                ev_tr = csr(np.array(event_flags)[tr].reshape(-1, 1), dtype=np.float64)
                ev_te = csr(np.array(event_flags)[te].reshape(-1, 1), dtype=np.float64)
                X_tr = hstack([X_tr_text, ev_tr])
                X_te = hstack([X_te_text, ev_te])
            else:
                X_tr, X_te = X_tr_text, X_te_text

            clf = _clf()
            clf.fit(X_tr, y_tr)
            prob = clf.predict_proba(X_te)[:, 1]
            pred = (prob >= 0.5).astype(int)
            results.append(_metrics(y_te, prob, pred))

    return results


# ---------------------------------------------------------------------------
# Experiment 1: Full CV — variant comparison A, C, D
# ---------------------------------------------------------------------------
def exp1_variant_comparison(rows: list[dict]) -> list[dict]:
    y = np.array([1 if r["humor_type"] == "aggressive" else 0 for r in rows])
    n_pos = int(y.sum())
    n_total = len(rows)

    texts_A = [r["text_original"] for r in rows]
    texts_C = [remove_campaign_token(r["text_original"]) for r in rows]
    texts_D = texts_C  # same text as C, but adds event dummy in CV
    has_event = [r["has_national_roast_day"] for r in rows]

    output = []
    for vname, texts, event_flags in [
        ("variant_A_original_text", texts_A, None),
        ("variant_C_token_deleted", texts_C, None),
        ("variant_D_event_dummy", texts_D, has_event),
    ]:
        print(f"  {vname}...")
        fold_results = _build_text_features_cv(texts, y, vname, RANDOM_SEEDS, N_CV_FOLDS, event_flags)
        agg = _cv_aggregate(fold_results)
        # Split PR-AUC by event status within held-out folds (approximate)
        row_out = {
            "experiment": "full_cv_variant_comparison",
            "variant": vname,
            "n_rows": n_total,
            "n_aggressive": n_pos,
            "n_event_rows": int(sum(has_event)),
            **agg,
            "diagnostic_note": _variant_note(vname),
        }
        output.append(row_out)
        print(f"    PR-AUC={agg['pr_auc_mean']} F1={agg['f1_mean']}")
    return output


def _variant_note(vname: str) -> str:
    notes = {
        "variant_A_original_text":
            "Baseline: raw text including #NationalRoastDay token",
        "variant_C_token_deleted":
            "Deletion masking: #NationalRoastDay removed; tests sensitivity to token presence",
        "variant_D_event_dummy":
            "Event-aware: token deleted from text + binary has_national_roast_day column added; "
            "separates text-level signal from event-level signal",
    }
    return notes.get(vname, "")


# ---------------------------------------------------------------------------
# Experiment 2: Non-event-only CV (variant E)
# ---------------------------------------------------------------------------
def exp2_non_event_cv(rows: list[dict]) -> list[dict]:
    (LR, TV, Pipe, GKF, SKF,
     ap, roc, f1, prec, rec, hstack, csr) = _sk()

    non_event = [r for r in rows if not r["has_national_roast_day"]]
    y = np.array([1 if r["humor_type"] == "aggressive" else 0 for r in non_event])
    texts = [r["text_original"] for r in non_event]
    n_pos = int(y.sum())
    n_total = len(non_event)

    print(f"  variant_E_non_event_only: n={n_total} aggressive={n_pos}...")
    fold_results = _build_text_features_cv(texts, y, "E", RANDOM_SEEDS, N_CV_FOLDS)
    agg = _cv_aggregate(fold_results)

    return [{
        "experiment": "non_event_only_cv",
        "variant": "variant_E_non_event_only",
        "n_rows": n_total,
        "n_aggressive": n_pos,
        "n_event_rows": 0,
        **agg,
        "diagnostic_note":
            "CV trained and tested only on non-event posts; measures Fortune100-generalizable signal",
    }]


# ---------------------------------------------------------------------------
# Experiment 3: Cross-event transfer (variant F and reverse)
# ---------------------------------------------------------------------------
def exp3_cross_event_transfer(rows: list[dict]) -> list[dict]:
    (LR, TV, Pipe, GKF, SKF,
     ap, roc, f1, prec, rec, hstack, csr) = _sk()

    event_rows = [r for r in rows if r["has_national_roast_day"]]
    non_event_rows = [r for r in rows if not r["has_national_roast_day"]]

    y_event = np.array([1 if r["humor_type"] == "aggressive" else 0 for r in event_rows])
    y_non_event = np.array([1 if r["humor_type"] == "aggressive" else 0 for r in non_event_rows])

    output = []

    # Transfer A: train non-event → test event
    print("  train_non_event -> test_event...")
    for vname, tr_texts, te_texts, extra_note in [
        ("variant_A_original_text",
         [r["text_original"] for r in non_event_rows],
         [r["text_original"] for r in event_rows],
         "tests if aggressive language in non-event posts transfers to event context"),
        ("variant_C_token_deleted",
         [remove_campaign_token(r["text_original"]) for r in non_event_rows],
         [remove_campaign_token(r["text_original"]) for r in event_rows],
         "same but event posts have token deleted; tests pure language transfer"),
    ]:
        pr_aucs, f1s, precs, recs = [], [], [], []
        for seed in RANDOM_SEEDS:
            feat = _make_word_char_vectorizer()
            X_tr = feat.fit_transform(tr_texts)
            X_te = feat.transform(te_texts)
            clf = _clf()
            if y_non_event.sum() == 0:
                continue
            clf.fit(X_tr, y_non_event)
            if len(y_event) == 0:
                continue
            prob = clf.predict_proba(X_te)[:, 1]
            pred = (prob >= 0.5).astype(int)
            if y_event.sum() > 0:
                pr_aucs.append(float(ap(y_event, prob)))
                f1s.append(float(f1(y_event, pred, zero_division=0)))
                precs.append(float(prec(y_event, pred, zero_division=0)))
                recs.append(float(rec(y_event, pred, zero_division=0)))

        output.append({
            "experiment": "cross_event_transfer",
            "eval_scope": "train_non_event__test_event",
            "variant": vname,
            "n_train": len(non_event_rows),
            "n_test": len(event_rows),
            "n_train_aggressive": int(y_non_event.sum()),
            "n_test_aggressive": int(y_event.sum()),
            "n_test_affiliative": int((y_event == 0).sum()),
            "pr_auc_mean": round(float(np.mean(pr_aucs)), 4) if pr_aucs else None,
            "f1_mean": round(float(np.mean(f1s)), 4) if f1s else None,
            "precision_mean": round(float(np.mean(precs)), 4) if precs else None,
            "recall_mean": round(float(np.mean(recs)), 4) if recs else None,
            "n_seeds": len(pr_aucs),
            "extra_note": extra_note,
        })
        print(f"    {vname}: PR-AUC={output[-1]['pr_auc_mean']} F1={output[-1]['f1_mean']}")

    # Transfer B: train on full data → report event-only performance
    print("  train_all -> test_event_only (single fold)...")
    for vname, all_texts in [
        ("variant_A_original_text", [r["text_original"] for r in rows]),
        ("variant_C_token_deleted",
         [remove_campaign_token(r["text_original"]) for r in rows]),
    ]:
        # Event posts are IN training — this is the "inflated" estimate
        y_all = np.array([1 if r["humor_type"] == "aggressive" else 0 for r in rows])
        has_ev = np.array([r["has_national_roast_day"] for r in rows])

        pr_aucs, f1s = [], []
        for seed in RANDOM_SEEDS:
            feat = _make_word_char_vectorizer()
            X_all = feat.fit_transform(all_texts)
            clf = _clf()
            clf.fit(X_all, y_all)
            # Evaluate only event subset
            X_ev = X_all[has_ev == 1]
            y_ev = y_all[has_ev == 1]
            if len(y_ev) == 0 or y_ev.sum() == 0:
                continue
            prob = clf.predict_proba(X_ev)[:, 1]
            pred = (prob >= 0.5).astype(int)
            pr_aucs.append(float(ap(y_ev, prob)))
            f1s.append(float(f1(y_ev, pred, zero_division=0)))

        output.append({
            "experiment": "cross_event_transfer",
            "eval_scope": "train_all__test_event_only_subset",
            "variant": vname,
            "n_train": len(rows),
            "n_test": int(has_ev.sum()),
            "n_train_aggressive": int(y_all.sum()),
            "n_test_aggressive": int(y_all[has_ev == 1].sum()),
            "n_test_affiliative": int((y_all[has_ev == 1] == 0).sum()),
            "pr_auc_mean": round(float(np.mean(pr_aucs)), 4) if pr_aucs else None,
            "f1_mean": round(float(np.mean(f1s)), 4) if f1s else None,
            "precision_mean": None,
            "recall_mean": None,
            "n_seeds": len(pr_aucs),
            "extra_note": "event posts included in training — inflated estimate; compare with train_non_event version",
        })
        print(f"    train_all→event {vname}: PR-AUC={output[-1]['pr_auc_mean']}")

    return output


# ---------------------------------------------------------------------------
# Experiment 4: Source held-out stratified by event status
# ---------------------------------------------------------------------------
def exp4_source_heldout(rows: list[dict]) -> list[dict]:
    (LR, TV, Pipe, GKF, SKF,
     ap, roc, f1, prec, rec, hstack, csr) = _sk()

    batch1 = [r for r in rows if r["source"] == "batch1_fortune100"]
    wendys = [r for r in rows if r["source"] == "wendys_human_type"]
    wendys_event = [r for r in wendys if r["has_national_roast_day"]]
    wendys_non_event = [r for r in wendys if not r["has_national_roast_day"]]

    y_batch1 = np.array([1 if r["humor_type"] == "aggressive" else 0 for r in batch1])
    y_wendys = np.array([1 if r["humor_type"] == "aggressive" else 0 for r in wendys])
    y_wendys_event = np.array([1 if r["humor_type"] == "aggressive" else 0 for r in wendys_event])
    y_wendys_non_event = np.array([1 if r["humor_type"] == "aggressive" else 0 for r in wendys_non_event])

    output = []

    for vname, texts_all, texts_batch1, texts_wendys, texts_wne, texts_we in [
        ("variant_A_original_text",
         [r["text_original"] for r in rows],
         [r["text_original"] for r in batch1],
         [r["text_original"] for r in wendys],
         [r["text_original"] for r in wendys_non_event],
         [r["text_original"] for r in wendys_event]),
        ("variant_C_token_deleted",
         [remove_campaign_token(r["text_original"]) for r in rows],
         [remove_campaign_token(r["text_original"]) for r in batch1],
         [remove_campaign_token(r["text_original"]) for r in wendys],
         [remove_campaign_token(r["text_original"]) for r in wendys_non_event],
         [remove_campaign_token(r["text_original"]) for r in wendys_event]),
    ]:
        for scope, tr_texts, tr_labels, te_texts, te_labels, note in [
            ("train_batch1_test_wendys_all",
             texts_batch1, y_batch1, texts_wendys, y_wendys,
             "can batch1-trained model find aggressive in all Wendy's posts?"),
            ("train_batch1_test_wendys_non_event",
             texts_batch1, y_batch1, texts_wne, y_wendys_non_event,
             "can batch1-trained model find aggressive in Wendy's non-event posts?"),
            ("train_batch1_test_wendys_event_only",
             texts_batch1, y_batch1, texts_we, y_wendys_event,
             "can batch1-trained model find aggressive in NationalRoastDay event posts?"),
            ("train_wendys_test_batch1",
             texts_wendys, y_wendys, texts_batch1, y_batch1,
             "can Wendy's-trained model find aggressive in Fortune100 posts?"),
            ("train_wendys_non_event_test_batch1",
             texts_wne, y_wendys_non_event, texts_batch1, y_batch1,
             "can Wendy's NON-event-trained model find aggressive in Fortune100 posts?"),
        ]:
            if te_labels.sum() == 0 or tr_labels.sum() == 0 or len(te_labels) < 2:
                output.append({
                    "experiment": "source_heldout_event_stratified",
                    "eval_scope": scope,
                    "variant": vname,
                    "n_train": len(tr_texts),
                    "n_test": len(te_texts),
                    "n_train_aggressive": int(tr_labels.sum()),
                    "n_test_aggressive": int(te_labels.sum()),
                    "pr_auc": None,
                    "f1": None,
                    "precision": None,
                    "recall": None,
                    "note": f"SKIP: n_test_aggressive={te_labels.sum()} (insufficient)",
                })
                continue

            pr_aucs, f1s, precs, recs = [], [], [], []
            for seed in RANDOM_SEEDS:
                feat = _make_word_char_vectorizer()
                X_tr = feat.fit_transform(tr_texts)
                X_te = feat.transform(te_texts)
                clf = _clf()
                clf.fit(X_tr, tr_labels)
                prob = clf.predict_proba(X_te)[:, 1]
                pred = (prob >= 0.5).astype(int)
                if te_labels.sum() > 0 and (te_labels == 0).sum() > 0:
                    pr_aucs.append(float(ap(te_labels, prob)))
                elif te_labels.sum() > 0:
                    pr_aucs.append(0.0)
                f1s.append(float(f1(te_labels, pred, zero_division=0)))
                precs.append(float(prec(te_labels, pred, zero_division=0)))
                recs.append(float(rec(te_labels, pred, zero_division=0)))

            output.append({
                "experiment": "source_heldout_event_stratified",
                "eval_scope": scope,
                "variant": vname,
                "n_train": len(tr_texts),
                "n_test": len(te_texts),
                "n_train_aggressive": int(tr_labels.sum()),
                "n_test_aggressive": int(te_labels.sum()),
                "pr_auc": round(float(np.mean(pr_aucs)), 4) if pr_aucs else None,
                "f1": round(float(np.mean(f1s)), 4) if f1s else None,
                "precision": round(float(np.mean(precs)), 4) if precs else None,
                "recall": round(float(np.mean(recs)), 4) if recs else None,
                "note": note,
            })
            print(f"    {scope} {vname[-10:]}: F1={output[-1]['f1']}")

    return output


# ---------------------------------------------------------------------------
# Experiment 5: Company GroupKFold within batch1 (non-event only)
# ---------------------------------------------------------------------------
def exp5_company_groupkfold(rows: list[dict]) -> list[dict]:
    (LR, TV, Pipe, GKF, SKF,
     ap, roc, f1, prec, rec, hstack, csr) = _sk()

    batch1 = [r for r in rows if r["source"] == "batch1_fortune100"]
    y = np.array([1 if r["humor_type"] == "aggressive" else 0 for r in batch1])
    companies = np.array([r["company_name"] for r in batch1])
    n_unique = len(np.unique(companies))
    n_folds = min(N_CV_FOLDS, n_unique)

    output = []
    for vname, texts in [
        ("variant_A_original_text", [r["text_original"] for r in batch1]),
        ("variant_C_token_deleted",
         [remove_campaign_token(r["text_original"]) for r in batch1]),
    ]:
        X = np.array(texts)
        gkf = GKF(n_splits=n_folds)
        pr_aucs, f1s, precs, recs = [], [], [], []
        for tr_idx, te_idx in gkf.split(X, y, groups=companies):
            y_tr, y_te = y[tr_idx], y[te_idx]
            if y_te.sum() == 0 or y_tr.sum() == 0:
                continue
            feat = _make_word_char_vectorizer()
            X_tr = feat.fit_transform(X[tr_idx])
            X_te = feat.transform(X[te_idx])
            clf = _clf()
            clf.fit(X_tr, y_tr)
            prob = clf.predict_proba(X_te)[:, 1]
            pred = (prob >= 0.5).astype(int)
            if y_te.sum() > 0 and (y_te == 0).sum() > 0:
                pr_aucs.append(float(ap(y_te, prob)))
            f1s.append(float(f1(y_te, pred, zero_division=0)))
            precs.append(float(prec(y_te, pred, zero_division=0)))
            recs.append(float(rec(y_te, pred, zero_division=0)))

        output.append({
            "experiment": "company_groupkfold_batch1",
            "variant": vname,
            "n_rows": len(batch1),
            "n_aggressive": int(y.sum()),
            "n_unique_companies": n_unique,
            "n_folds": n_folds,
            "n_valid_folds": len(pr_aucs),
            "pr_auc_mean": round(float(np.mean(pr_aucs)), 4) if pr_aucs else None,
            "f1_mean": round(float(np.mean(f1s)), 4) if f1s else None,
            "precision_mean": round(float(np.mean(precs)), 4) if precs else None,
            "recall_mean": round(float(np.mean(recs)), 4) if recs else None,
            "note": "GroupKFold by company_name within batch1_fortune100 only; "
                    "batch1 has 0 event posts so token deletion makes no difference",
        })
        print(f"    {vname}: PR-AUC={output[-1]['pr_auc_mean']} F1={output[-1]['f1_mean']}")

    return output


# ---------------------------------------------------------------------------
# Experiment 6: Feature importance — event vs non-event top features
# ---------------------------------------------------------------------------
def exp6_feature_importance(rows: list[dict]) -> list[dict]:
    (LR, TV, Pipe, GKF, SKF,
     ap, roc, f1, prec, rec, hstack, csr) = _sk()

    y = np.array([1 if r["humor_type"] == "aggressive" else 0 for r in rows])
    has_ev = np.array([r["has_national_roast_day"] for r in rows])

    output = []
    for vname, texts in [
        ("variant_A_original_text", [r["text_original"] for r in rows]),
        ("variant_C_token_deleted",
         [remove_campaign_token(r["text_original"]) for r in rows]),
    ]:
        feat = _make_word_char_vectorizer()
        X = feat.fit_transform(texts)
        clf = _clf()
        clf.fit(X, y)
        feat_names = feat.get_feature_names_out()
        coefs = clf.coef_[0]
        top_idx = np.argsort(np.abs(coefs))[::-1][:30]

        for rank, idx in enumerate(top_idx, 1):
            fname = feat_names[idx]
            weight = float(coefs[idx])
            # Determine if this feature appears more in event vs non-event posts
            X_dense = X[:, idx].toarray().flatten()
            ev_mean = float(X_dense[has_ev == 1].mean()) if has_ev.sum() > 0 else 0.0
            non_ev_mean = float(X_dense[has_ev == 0].mean()) if (has_ev == 0).sum() > 0 else 0.0
            ratio_str = (
                f"{ev_mean/non_ev_mean:.1f}x" if non_ev_mean > 1e-8 else
                ("event_only" if ev_mean > 0 else "zero")
            )
            lkg_flag = "FAIL" if any(
                tok in fname.lower()
                for tok in ["wendy", "nationalroastday", "roastday", "frosty",
                            "nugg", "campaign_event", "competitor_tok", "brand_tok"]
            ) else "PASS"
            output.append({
                "experiment": "feature_importance",
                "variant": vname,
                "rank": rank,
                "feature": fname,
                "weight": round(weight, 6),
                "event_mean_tfidf": round(ev_mean, 6),
                "non_event_mean_tfidf": round(non_ev_mean, 6),
                "event_vs_non_event_ratio": ratio_str,
                "leakage_flag": lkg_flag,
            })

    return output


# ---------------------------------------------------------------------------
# Event feature statistics
# ---------------------------------------------------------------------------
def exp0_event_stats(rows: list[dict]) -> list[dict]:
    event = [r for r in rows if r["has_national_roast_day"]]
    non_event = [r for r in rows if not r["has_national_roast_day"]]

    def stats(subset, label):
        n = len(subset)
        if n == 0:
            return {}
        type_ctr = Counter(r["humor_type"] for r in subset)
        src_ctr = Counter(r["source"] for r in subset)
        return {
            "group": label,
            "n_rows": n,
            "n_aggressive": type_ctr.get("aggressive", 0),
            "n_affiliative": type_ctr.get("affiliative", 0),
            "n_self_enhancing": type_ctr.get("self-enhancing", 0),
            "n_self_defeating": type_ctr.get("self-defeating", 0),
            "pct_aggressive": round(type_ctr.get("aggressive", 0) / n, 4),
            "n_batch1": src_ctr.get("batch1_fortune100", 0),
            "n_wendys": src_ctr.get("wendys_human_type", 0),
            "event_is_exclusive_to_wendys":
                "YES" if src_ctr.get("batch1_fortune100", 0) == 0 else "NO",
            "note":
                "#NationalRoastDay posts are 100% wendys_human_type — "
                "any model learning this token is learning source identity, not humor pattern"
                if src_ctr.get("batch1_fortune100", 0) == 0 else "",
        }

    return [
        stats(event, "event_posts"),
        stats(non_event, "non_event_posts"),
        stats(rows, "all_rows"),
    ]


# ---------------------------------------------------------------------------
# Signal verdict
# ---------------------------------------------------------------------------
def build_signal_verdict(
    exp1: list[dict],
    exp2: list[dict],
    exp3: list[dict],
    exp4: list[dict],
    exp5: list[dict],
) -> list[dict]:
    rows = []

    def _get(results, key, pred=None):
        for r in results:
            if pred is None or pred(r):
                return r.get(key)
        return None

    def add(item, value, evidence, interpretation, judgment, priority="INFO"):
        rows.append({
            "verdict_item": item,
            "value": str(value),
            "evidence": str(evidence),
            "interpretation": interpretation,
            "judgment": judgment,
            "priority": priority,
        })

    # Variant comparison
    pr_A = _get(exp1, "pr_auc_mean", lambda r: "variant_A" in r["variant"])
    pr_C = _get(exp1, "pr_auc_mean", lambda r: "variant_C" in r["variant"])
    pr_D = _get(exp1, "pr_auc_mean", lambda r: "variant_D" in r["variant"])
    f1_A = _get(exp1, "f1_mean", lambda r: "variant_A" in r["variant"])
    f1_C = _get(exp1, "f1_mean", lambda r: "variant_C" in r["variant"])
    f1_D = _get(exp1, "f1_mean", lambda r: "variant_D" in r["variant"])

    token_sensitivity = (float(pr_A or 0) - float(pr_C or 0)) / float(pr_A or 1)
    event_dummy_benefit = (float(pr_D or 0) - float(pr_C or 0)) / float(pr_C or 1)

    add("token_deletion_sensitivity",
        f"PR-AUC: A={pr_A} vs C={pr_C} (drop={token_sensitivity:.3f})",
        "exp1 full CV variant comparison",
        "How much does PR-AUC drop when #NationalRoastDay is deleted? "
        "Large drop → model heavily depends on token.",
        "SHORTCUT" if token_sensitivity > 0.05 else "SIGNAL_GENERALIZES",
        priority="KEY_FINDING")

    add("event_dummy_benefit",
        f"PR-AUC: C={pr_C} vs D={pr_D} (gain={event_dummy_benefit:.3f})",
        "exp1 full CV variant D",
        "Does making the event flag explicit (binary column) recover "
        "performance lost by deleting the token? "
        "Positive gain → event flag adds information beyond raw text.",
        "USEFUL_CONTEXT" if event_dummy_benefit > 0.02 else "NEGLIGIBLE",
        priority="KEY_FINDING")

    # Cross-event transfer
    f1_transfer = _get(exp3, "f1_mean",
                       lambda r: r.get("eval_scope") == "train_non_event__test_event"
                       and "variant_A" in r.get("variant", ""))
    f1_transfer_C = _get(exp3, "f1_mean",
                         lambda r: r.get("eval_scope") == "train_non_event__test_event"
                         and "variant_C" in r.get("variant", ""))
    f1_train_all_event = _get(exp3, "f1_mean",
                              lambda r: r.get("eval_scope") == "train_all__test_event_only_subset"
                              and "variant_A" in r.get("variant", ""))

    add("train_non_event_test_event_f1",
        f"variant_A={f1_transfer} variant_C={f1_transfer_C}",
        "exp3 cross_event_transfer train_non_event__test_event",
        "F1 on event posts when trained ONLY on non-event posts. "
        "High F1 → model learned aggressive language that transfers to event context. "
        "Low F1 → event posts use aggressive language patterns not present in non-event training.",
        "LANGUAGE_GENERALIZES" if (f1_transfer or 0) > 0.3 else "EVENT_SPECIFIC_LANGUAGE",
        priority="KEY_FINDING")

    add("event_token_inflation",
        f"train_all→event F1={f1_train_all_event}, train_non_event→event F1={f1_transfer}",
        "exp3 comparison",
        "Gap between these shows how much event token inclusion inflates event-post performance.",
        f"INFLATED_BY={round((float(f1_train_all_event or 0) - float(f1_transfer or 0)), 3)}",
        priority="KEY_FINDING")

    # Source held-out
    f1_b1_all = _get(exp4, "f1",
                     lambda r: r.get("eval_scope") == "train_batch1_test_wendys_all"
                     and "variant_A" in r.get("variant", ""))
    f1_b1_non_event = _get(exp4, "f1",
                           lambda r: r.get("eval_scope") == "train_batch1_test_wendys_non_event"
                           and "variant_A" in r.get("variant", ""))
    f1_b1_event = _get(exp4, "f1",
                       lambda r: r.get("eval_scope") == "train_batch1_test_wendys_event_only"
                       and "variant_A" in r.get("variant", ""))

    add("source_heldout_batch1_to_wendys",
        f"all={f1_b1_all} non_event={f1_b1_non_event} event_only={f1_b1_event}",
        "exp4 source_heldout_event_stratified",
        "Fortune100-trained model performance on Wendy's posts split by event status. "
        "If event_only >> non_event: event posts use language similar to Fortune100 aggressive. "
        "If event_only << non_event: event posts use event-specific language not in Fortune100.",
        "EVENT_GENERALIZES" if (f1_b1_event or 0) > (f1_b1_non_event or 0) else "EVENT_SPECIFIC",
        priority="KEY_FINDING")

    # Company GroupKFold
    pr_gkf = _get(exp5, "pr_auc_mean", lambda r: "variant_A" in r["variant"])
    add("company_groupkfold_batch1",
        f"PR-AUC={pr_gkf}",
        "exp5 company_groupkfold_batch1",
        "Fortune100 cross-company generalization for aggressive detection. "
        "Unaffected by NationalRoastDay (batch1 has 0 event posts).",
        "POOR_GENERALIZATION" if (pr_gkf or 0) < 0.30 else "MARGINAL",
        priority="INFO")

    # Final verdict
    is_shortcut = token_sensitivity > 0.05
    is_useful = event_dummy_benefit > 0.02
    language_transfers = (f1_transfer or 0) > 0.3

    verdict = (
        "CAMPAIGN_CONTEXT_USEFUL_BUT_NOT_SUFFICIENT"
        if is_useful and language_transfers else
        "SOURCE_SHORTCUT_DOMINANT"
        if is_shortcut and not language_transfers else
        "WEAK_SIGNAL_INVESTIGATE_FURTHER"
    )
    add("final_signal_verdict",
        verdict,
        "Combined evidence from exp1-exp5",
        "Composite judgment: is #NationalRoastDay a useful campaign signal or a source shortcut?",
        verdict,
        priority="FINAL")

    add("candidate_status",
        "NOT_A_CANDIDATE",
        "All evaluations are diagnostic only",
        "No variant has cleared leakage threshold, source-held-out minimum, or threshold quality bar.",
        "NOT_A_CANDIDATE",
        priority="CRITICAL")

    return rows


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> int:
    print("=== run_type_classifier_diagnostic_v3 ===")
    print("PURPOSE: EVENT-AWARE DIAGNOSTIC — not for candidate selection\n")

    try:
        import sklearn  # noqa: F401
    except ImportError:
        print("ERROR: scikit-learn not installed", file=sys.stderr)
        return 1

    rows = load_training_data()
    add_event_flags(rows)
    print(f"Loaded {len(rows)} rows | event={sum(r['has_national_roast_day'] for r in rows)} "
          f"| aggressive={sum(1 for r in rows if r['humor_type']=='aggressive')}")

    n_event = sum(r['has_national_roast_day'] for r in rows)
    n_event_agg = sum(1 for r in rows if r['has_national_roast_day'] and r['humor_type'] == 'aggressive')
    n_non_event = len(rows) - n_event
    n_non_event_agg = sum(1 for r in rows if not r['has_national_roast_day'] and r['humor_type'] == 'aggressive')
    print(f"  event posts: {n_event} ({n_event_agg} aggressive, {n_event - n_event_agg} non-aggressive)")
    print(f"  non-event posts: {n_non_event} ({n_non_event_agg} aggressive)\n")

    # Exp 0: Event stats
    print("[EXP 0] Event statistics...")
    exp0 = exp0_event_stats(rows)
    write_csv(DIAG_DIR / "diag_v3_event_stats.csv", exp0,
              ["group", "n_rows", "n_aggressive", "n_affiliative", "n_self_enhancing",
               "n_self_defeating", "pct_aggressive", "n_batch1", "n_wendys",
               "event_is_exclusive_to_wendys", "note"])

    # Exp 1: Full CV variant comparison
    print("[EXP 1] Full CV variant comparison (A, C, D)...")
    exp1 = exp1_variant_comparison(rows)
    write_csv(DIAG_DIR / "diag_v3_variant_comparison.csv", exp1,
              ["experiment", "variant", "n_rows", "n_aggressive", "n_event_rows",
               "pr_auc_mean", "pr_auc_std", "roc_auc_mean", "f1_mean",
               "precision_mean", "recall_mean", "n_folds_used", "diagnostic_note"])
    print()

    # Exp 2: Non-event-only CV
    print("[EXP 2] Non-event-only CV (variant E)...")
    exp2 = exp2_non_event_cv(rows)
    write_csv(DIAG_DIR / "diag_v3_non_event_cv.csv", exp2,
              ["experiment", "variant", "n_rows", "n_aggressive", "n_event_rows",
               "pr_auc_mean", "pr_auc_std", "roc_auc_mean", "f1_mean",
               "precision_mean", "recall_mean", "n_folds_used", "diagnostic_note"])
    print()

    # Exp 3: Cross-event transfer
    print("[EXP 3] Cross-event transfer...")
    exp3 = exp3_cross_event_transfer(rows)
    write_csv(DIAG_DIR / "diag_v3_cross_event_transfer.csv", exp3,
              ["experiment", "eval_scope", "variant", "n_train", "n_test",
               "n_train_aggressive", "n_test_aggressive", "n_test_affiliative",
               "pr_auc_mean", "f1_mean", "precision_mean", "recall_mean",
               "n_seeds", "extra_note"])
    print()

    # Exp 4: Source held-out event-stratified
    print("[EXP 4] Source held-out (stratified by event)...")
    exp4 = exp4_source_heldout(rows)
    write_csv(DIAG_DIR / "diag_v3_source_heldout_event.csv", exp4,
              ["experiment", "eval_scope", "variant", "n_train", "n_test",
               "n_train_aggressive", "n_test_aggressive",
               "pr_auc", "f1", "precision", "recall", "note"])
    print()

    # Exp 5: Company GroupKFold
    print("[EXP 5] Company GroupKFold (batch1)...")
    exp5 = exp5_company_groupkfold(rows)
    write_csv(DIAG_DIR / "diag_v3_company_groupkfold.csv", exp5,
              ["experiment", "variant", "n_rows", "n_aggressive", "n_unique_companies",
               "n_folds", "n_valid_folds",
               "pr_auc_mean", "f1_mean", "precision_mean", "recall_mean", "note"])
    print()

    # Exp 6: Feature importance
    print("[EXP 6] Feature importance (event vs non-event signal)...")
    exp6 = exp6_feature_importance(rows)
    write_csv(DIAG_DIR / "diag_v3_feature_importance.csv", exp6,
              ["experiment", "variant", "rank", "feature", "weight",
               "event_mean_tfidf", "non_event_mean_tfidf",
               "event_vs_non_event_ratio", "leakage_flag"])
    print()

    # Signal verdict
    print("[VERDICT] Building event-aware signal verdict...")
    verdict = build_signal_verdict(exp1, exp2, exp3, exp4, exp5)
    write_csv(DIAG_DIR / "diag_v3_signal_verdict.csv", verdict,
              ["verdict_item", "value", "evidence", "interpretation", "judgment", "priority"])

    # Print key findings
    key = [r for r in verdict if r["priority"] in ("KEY_FINDING", "FINAL", "CRITICAL")]
    print("\n=== KEY FINDINGS ===")
    for r in key:
        print(f"  [{r['priority']}] {r['verdict_item']}: {r['value']}")
        print(f"    → {r['judgment']}")

    print(f"\n=== All outputs → {DIAG_DIR} ===")
    print("candidate_status: NOT_A_CANDIDATE (diagnostic only)")
    print("=== run_type_classifier_diagnostic_v3 COMPLETE ===")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
