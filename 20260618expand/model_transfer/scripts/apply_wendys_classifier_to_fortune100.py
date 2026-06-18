"""
apply_wendys_classifier_to_fortune100.py

Trains the same TF-IDF + Logistic Regression pipeline used in the Wendy's
analysis on Wendy's labeled data, then applies it to Fortune Top 100 posts.

Stage 1: binary humor presence (text + final_humor_binary labels from Wendy's)
Stage 2: four-type humor (text + final_humor_type labels, humorous posts only)

No new inference method is introduced. This is a transfer of the same
classifier architecture trained on the same Wendy's labeled data.
"""

from __future__ import annotations

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
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold
from sklearn.metrics import accuracy_score, f1_score, roc_auc_score
from sklearn.pipeline import Pipeline

ROOT = Path(__file__).resolve().parents[3]
WENDYS_REVIEW = ROOT / "20260615wendy's" / "result" / "wendys_humor_review_sheet.csv"
FORTUNE_MASTER = ROOT / "20260618expand" / "data" / "processed" / "fortune100_post_master.csv"
MT = ROOT / "20260618expand" / "model_transfer"

OUT_CLASSIFIED = MT / "data" / "classified" / "fortune100_wendys_model_humor_classification.csv"
OUT_DIAG_PRESENCE = MT / "data" / "diagnostics" / "humor_presence_frequency.csv"
OUT_DIAG_TYPE = MT / "data" / "diagnostics" / "humor_type_frequency.csv"
OUT_DIAG_SPARSITY = MT / "data" / "diagnostics" / "aggressive_humor_sparsity.csv"
OUT_DIAG_COVERAGE = MT / "data" / "diagnostics" / "classification_coverage.csv"
OUT_AUDIT = MT / "reports" / "classifier_transfer_audit.md"

CLASSES_4TYPE = ["aggressive", "affiliative", "self-enhancing", "self-defeating"]
RANDOM_STATE = 42


def preprocess(text: str) -> str:
    text = re.sub(r"https?://\S+", "<URL>", text)
    text = re.sub(r"@\w+", "<MENTION>", text)
    text = re.sub(r"#(\w+)", r"\1", text)
    text = text.lower()
    text = re.sub(r"\s+", " ", text).strip()
    return text


def load_wendys_labels() -> tuple[list[str], list[int], list[str], list[str]]:
    with open(WENDYS_REVIEW, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    labeled = [
        r for r in rows
        if r.get("final_humor_label_available") == "1"
        and r.get("final_humor_binary") in ("0", "1")
    ]
    texts_bin = [preprocess(r["text"]) for r in labeled]
    labels_bin = [int(r["final_humor_binary"]) for r in labeled]

    typed = [
        r for r in labeled
        if r.get("final_humor_binary") == "1"
        and r.get("final_humor_type", "") in set(CLASSES_4TYPE)
    ]
    texts_type = [preprocess(r["text"]) for r in typed]
    labels_type = [r["final_humor_type"] for r in typed]

    print(f"Wendy's labeled (binary): {len(labeled)} rows  "
          f"humor={sum(labels_bin)}  nonhumor={len(labels_bin)-sum(labels_bin)}")
    print(f"Wendy's labeled (4-type): {len(typed)} rows  {dict(Counter(labels_type))}")
    return texts_bin, labels_bin, texts_type, labels_type


def build_binary_pipeline() -> Pipeline:
    return Pipeline([
        ("tfidf", TfidfVectorizer(
            lowercase=True, ngram_range=(1, 2),
            min_df=2, max_df=0.95, sublinear_tf=True,
        )),
        ("clf", LogisticRegression(
            class_weight="balanced", solver="liblinear",
            max_iter=1000, random_state=RANDOM_STATE,
        )),
    ])


def build_type_pipeline() -> tuple[TfidfVectorizer, LogisticRegression]:
    vec = TfidfVectorizer(
        ngram_range=(1, 2), min_df=2, max_df=0.95,
        sublinear_tf=True, max_features=5000,
    )
    clf = LogisticRegression(
        solver="lbfgs",
        class_weight="balanced", max_iter=1000, random_state=RANDOM_STATE,
    )
    return vec, clf


def cv_evaluate_binary(pipe: Pipeline, texts: list[str], labels: list[int]) -> dict:
    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=RANDOM_STATE)
    accs, f1s, aucs = [], [], []
    for tr_idx, va_idx in skf.split(texts, labels):
        X_tr = [texts[i] for i in tr_idx]
        X_va = [texts[i] for i in va_idx]
        y_tr = [labels[i] for i in tr_idx]
        y_va = [labels[i] for i in va_idx]
        pipe.fit(X_tr, y_tr)
        preds = pipe.predict(X_va)
        probs = pipe.predict_proba(X_va)[:, 1]
        accs.append(accuracy_score(y_va, preds))
        f1s.append(f1_score(y_va, preds, zero_division=0))
        aucs.append(roc_auc_score(y_va, probs))
    return {"cv_acc": float(np.mean(accs)), "cv_f1": float(np.mean(f1s)),
            "cv_auc": float(np.mean(aucs))}


def cv_evaluate_type(vec: TfidfVectorizer, clf: LogisticRegression,
                     texts: list[str], labels: list[str]) -> dict:
    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=RANDOM_STATE)
    accs, f1s = [], []
    texts_arr = np.array(texts)
    labels_arr = np.array(labels)
    for tr_idx, va_idx in skf.split(texts_arr, labels_arr):
        X_tr_raw = texts_arr[tr_idx]
        X_va_raw = texts_arr[va_idx]
        y_tr = labels_arr[tr_idx]
        y_va = labels_arr[va_idx]
        X_tr = vec.fit_transform(X_tr_raw)
        X_va = vec.transform(X_va_raw)
        clf.fit(X_tr, y_tr)
        preds = clf.predict(X_va)
        accs.append(accuracy_score(y_va, preds))
        f1s.append(f1_score(y_va, preds, average="macro", zero_division=0))
    return {"cv_acc": float(np.mean(accs)), "cv_macro_f1": float(np.mean(f1s))}


def load_fortune_posts() -> list[dict]:
    with open(FORTUNE_MASTER, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def main() -> None:
    print("=== apply_wendys_classifier_to_fortune100 ===")

    # 1. Load Wendy's labels
    texts_bin, labels_bin, texts_type, labels_type = load_wendys_labels()

    # 2. Binary classifier: CV then full-train
    print("\n--- Stage 1: Binary humor presence ---")
    bin_pipe = build_binary_pipeline()
    cv_bin = cv_evaluate_binary(bin_pipe, texts_bin, labels_bin)
    print(f"CV binary: acc={cv_bin['cv_acc']:.4f}  f1={cv_bin['cv_f1']:.4f}  auc={cv_bin['cv_auc']:.4f}")
    bin_pipe.fit(texts_bin, labels_bin)

    # 3. Four-type classifier: CV then full-train
    print("\n--- Stage 2: Four-type humor ---")
    type_vec, type_clf = build_type_pipeline()
    cv_type = cv_evaluate_type(type_vec, type_clf, texts_type, labels_type)
    print(f"CV 4-type: acc={cv_type['cv_acc']:.4f}  macro-F1={cv_type['cv_macro_f1']:.4f}")
    X_type_all = type_vec.fit_transform(texts_type)
    type_clf.fit(X_type_all, labels_type)

    # 4. Load Fortune 100 posts
    print("\n--- Applying to Fortune 100 posts ---")
    fortune_rows = load_fortune_posts()
    print(f"Fortune 100 posts: {len(fortune_rows)}")

    all_texts_pp = [preprocess(r.get("text", "")) for r in fortune_rows]

    # Binary predictions
    bin_probs = bin_pipe.predict_proba(all_texts_pp)[:, 1]
    bin_preds = (bin_probs >= 0.5).astype(int)

    # Four-type predictions (for all posts; gate applied in final label)
    X_type_fortune = type_vec.transform(all_texts_pp)
    type_raw_preds = type_clf.predict(X_type_fortune)
    type_probs = type_clf.predict_proba(X_type_fortune)

    cls_order = list(type_clf.classes_)

    def get_type_prob(probs_row: np.ndarray, cls: str) -> float:
        if cls in cls_order:
            return float(probs_row[cls_order.index(cls)])
        return 0.0

    # 5. Build output rows
    classified = []
    n_classified = 0
    n_failed = 0
    for i, row in enumerate(fortune_rows):
        text = row.get("text", "")
        if not text.strip():
            n_failed += 1
            status = "empty_text"
        else:
            n_classified += 1
            status = "ok"

        presence = int(bin_preds[i])
        presence_score = float(bin_probs[i])

        # Gate: non-humor posts → humor_type = non_humorous
        if presence == 1:
            humor_type = type_raw_preds[i]
            type_score = max(
                get_type_prob(type_probs[i], c) for c in CLASSES_4TYPE
            )
        else:
            humor_type = "non_humorous"
            type_score = 0.0

        tp_row = type_probs[i] if presence == 1 else np.zeros(len(cls_order))

        classified.append({
            "fortune_rank":          row.get("fortune_rank", ""),
            "company_name":          row.get("company_name", ""),
            "source_x_handle":       row.get("source_x_handle", ""),
            "tweet_id":              row.get("tweet_id", ""),
            "tweet_url":             row.get("tweet_url", ""),
            "created_at":            row.get("created_at", ""),
            "text":                  text,
            "humor_presence":        str(presence),
            "humor_presence_score":  f"{presence_score:.6f}",
            "humor_type":            humor_type,
            "humor_type_score":      f"{type_score:.6f}",
            "aggressive_humor":      str(1) if (presence == 1 and humor_type == "aggressive") else "0",
            "affiliative_humor":     str(1) if (presence == 1 and humor_type == "affiliative") else "0",
            "self_enhancing_humor":  str(1) if (presence == 1 and humor_type == "self-enhancing") else "0",
            "self_defeating_humor":  str(1) if (presence == 1 and humor_type == "self-defeating") else "0",
            "non_humorous":          str(1) if presence == 0 else "0",
            "classification_model_source":  "wendys_tfidf_logreg_trained_on_wendys_labeled_597rows",
            "classification_model_version": "tfidf_ngram12_logreg_liblinear_balanced_random42",
            "classification_threshold":     "0.5",
            "classification_confidence":    f"{max(presence_score, 1-presence_score):.6f}",
            "classification_status":        status,
        })

    # 6. Write classified output
    OUT_CLASSIFIED.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(classified[0].keys())
    with open(OUT_CLASSIFIED, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(classified)
    print(f"Classified output: {OUT_CLASSIFIED}  ({len(classified)} rows)")

    # 7. Diagnostics
    humor_count = sum(1 for r in classified if r["humor_presence"] == "1")
    non_humor_count = sum(1 for r in classified if r["humor_presence"] == "0")
    type_dist = Counter(r["humor_type"] for r in classified)
    agg_count = type_dist.get("aggressive", 0)

    # humor_presence frequency
    with open(OUT_DIAG_PRESENCE, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["humor_presence_value", "count", "pct"])
        w.writeheader()
        total = len(classified)
        for val, cnt in [("1 (humor)", humor_count), ("0 (non_humor)", non_humor_count)]:
            w.writerow({"humor_presence_value": val, "count": cnt, "pct": f"{cnt/total*100:.2f}"})

    # humor_type frequency
    with open(OUT_DIAG_TYPE, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["humor_type", "count", "pct"])
        w.writeheader()
        for t, cnt in sorted(type_dist.items(), key=lambda x: -x[1]):
            w.writerow({"humor_type": t, "count": cnt, "pct": f"{cnt/total*100:.2f}"})

    # aggressive sparsity
    with open(OUT_DIAG_SPARSITY, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["metric", "value"])
        w.writeheader()
        w.writerow({"metric": "total_posts", "value": total})
        w.writerow({"metric": "aggressive_humor_posts", "value": agg_count})
        w.writerow({"metric": "aggressive_pct", "value": f"{agg_count/total*100:.4f}"})
        w.writerow({"metric": "h3_confirmatory_feasible", "value": "no" if agg_count < 300 else "yes"})

    # classification coverage
    with open(OUT_DIAG_COVERAGE, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["metric", "value"])
        w.writeheader()
        w.writerow({"metric": "total_input_posts", "value": total})
        w.writerow({"metric": "classified_ok", "value": n_classified})
        w.writerow({"metric": "classification_failed_empty_text", "value": n_failed})
        w.writerow({"metric": "cv_binary_accuracy", "value": f"{cv_bin['cv_acc']:.4f}"})
        w.writerow({"metric": "cv_binary_f1", "value": f"{cv_bin['cv_f1']:.4f}"})
        w.writerow({"metric": "cv_binary_auc", "value": f"{cv_bin['cv_auc']:.4f}"})
        w.writerow({"metric": "cv_4type_accuracy", "value": f"{cv_type['cv_acc']:.4f}"})
        w.writerow({"metric": "cv_4type_macro_f1", "value": f"{cv_type['cv_macro_f1']:.4f}"})
        w.writerow({"metric": "wendys_training_n_binary", "value": len(labels_bin)})
        w.writerow({"metric": "wendys_training_n_4type", "value": len(labels_type)})

    print(f"\nPresence: humor={humor_count} ({humor_count/total*100:.1f}%)  "
          f"non_humor={non_humor_count} ({non_humor_count/total*100:.1f}%)")
    print(f"Type distribution: {dict(type_dist)}")

    # 8. Audit report
    with open(OUT_AUDIT, "w", encoding="utf-8") as f:
        f.write(f"""# Classifier Transfer Audit

## Wendy's Classifier Summary

| Item | Value |
|---|---|
| Model | TF-IDF + Logistic Regression (two-stage) |
| Stage 1 | Binary humor presence (humor vs. non-humor) |
| Stage 2 | Four-type multinomial (aggressive/affiliative/self-enhancing/self-defeating) |
| Training source | `20260615wendy's/result/wendys_humor_review_sheet.csv` |
| Training labels (binary) | {len(labels_bin)} labeled rows |
| Training labels (4-type) | {len(labels_type)} humorous rows with valid type |
| 4-type class distribution | {dict(Counter(labels_type))} |
| Saved model artifact | None — model retrained from Wendy's labels at runtime |
| Threshold (binary) | 0.5 |

## Stage 1 (Binary) Hyperparameters

```
TfidfVectorizer(lowercase=True, ngram_range=(1, 2), min_df=2, max_df=0.95, sublinear_tf=True)
LogisticRegression(class_weight='balanced', solver='liblinear', max_iter=1000, random_state=42)
```

CV result (Stratified 5-fold on Wendy's labeled data):

| Metric | Value |
|---|---|
| Accuracy | {cv_bin['cv_acc']:.4f} |
| F1 | {cv_bin['cv_f1']:.4f} |
| ROC-AUC | {cv_bin['cv_auc']:.4f} |

## Stage 2 (Four-Type) Hyperparameters

```
TfidfVectorizer(ngram_range=(1, 2), min_df=2, max_df=0.95, sublinear_tf=True, max_features=5000)
LogisticRegression(multi_class='multinomial', solver='lbfgs', class_weight='balanced',
                   max_iter=1000, random_state=42)
```

CV result (Stratified 5-fold on Wendy's 4-type labeled data):

| Metric | Value |
|---|---|
| Accuracy | {cv_type['cv_acc']:.4f} |
| Macro-F1 | {cv_type['cv_macro_f1']:.4f} |

## Fortune Top 100 Classification Result

| Metric | Value |
|---|---|
| Total input posts | {total} |
| Classified OK | {n_classified} |
| Failed (empty text) | {n_failed} |
| humor_presence = 1 | {humor_count} ({humor_count/total*100:.2f}%) |
| humor_presence = 0 | {non_humor_count} ({non_humor_count/total*100:.2f}%) |

Humor type distribution:

| Type | Count |
|---|---|
{"".join(f"| {t} | {cnt} |" + chr(10) for t, cnt in sorted(type_dist.items(), key=lambda x: -x[1]))}

## Claim Boundary

- This applies the Wendy's-trained classifier to Fortune Top 100 posts.
- This is a model-transfer classification, not a newly human-validated Fortune-wide classifier.
- Full-sample model-based classification remains the main empirical evidence.
- Human-coded labels are supplemental validation evidence only.
- Engagement is an engagement-based brand equity proxy, not brand equity itself.
- X engagement metrics are point-in-time captures.
- The analysis is observational evidence and does not support unrestricted causal claims.
""")

    print(f"\nAudit report: {OUT_AUDIT}")
    print("\n=== apply_wendys_classifier_to_fortune100 COMPLETE ===")


if __name__ == "__main__":
    main()
