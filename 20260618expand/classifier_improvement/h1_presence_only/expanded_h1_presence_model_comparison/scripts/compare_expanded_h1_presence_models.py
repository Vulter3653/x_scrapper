"""Compare expanded H1 humor-presence Model A vs Model B.

Model A: batch1-only human labels.
Model B: batch1 + Wendy's human labels.

This script runs only H1 presence model comparison. It does not classify the
integrated corpus, run H1 regressions, or touch H2/H3/type/aggressive models.
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Iterable

PYPACKAGES = Path("/home/user/.local/pypackages")
if str(PYPACKAGES) not in sys.path:
    sys.path.insert(0, str(PYPACKAGES))

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import confusion_matrix, f1_score, precision_score, recall_score, roc_auc_score
from sklearn.model_selection import StratifiedKFold
from sklearn.pipeline import FeatureUnion, Pipeline

ROOT = Path(__file__).resolve().parents[5]
BASE = ROOT / "20260618expand" / "classifier_improvement" / "h1_presence_only" / "expanded_h1_presence_model_comparison"
EXPANDED = ROOT / "20260618expand" / "classifier_improvement" / "h1_presence_only" / "expanded_h1_presence_training" / "data" / "expanded_h1_presence_training_dataset.csv"
DATA_DIR = BASE / "data"
DIAG_DIR = BASE / "diagnostics"
RES_DIR = BASE / "results"

MODEL_ID = "word_char_comb__lr_liblin_C01"
RANDOM_STATE = 42
N_SPLITS = 5
EXPECTED = {
    "batch1_only": 1482,
    "batch1_plus_wendys_human": 1550,
    "wendys_held_out_test": 68,
}
WENDYS_TOKENS = ["wendy", "wendys", "wendy's", "frosty", "baconator", "nuggs", "@wendys"]

OUT_TRAINING_DIAG = DIAG_DIR / "training_data_diagnostics.csv"
OUT_METRICS = RES_DIR / "model_comparison_metrics.csv"
OUT_CM = RES_DIR / "model_comparison_confusion_matrices.csv"
OUT_SOURCE = RES_DIR / "source_aware_subset_metrics.csv"
OUT_WENDYS = RES_DIR / "wendys_held_out_metrics.csv"
OUT_WENDYS_CM = RES_DIR / "wendys_held_out_confusion_matrix.csv"
OUT_FEATURES = RES_DIR / "top_feature_weights.csv"
OUT_LEAKAGE = DIAG_DIR / "wendys_leakage_feature_diagnostic.csv"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def preprocess(text: str) -> str:
    text = re.sub(r"https?://\S+", "<URL>", text or "")
    text = re.sub(r"@\w+", "<MENTION>", text)
    text = re.sub(r"#(\w+)", r"\1", text)
    return re.sub(r"\s+", " ", text.lower()).strip()


def make_pipeline() -> Pipeline:
    vec = FeatureUnion([
        ("word", TfidfVectorizer(analyzer="word", ngram_range=(1, 2), max_features=5000,
                                  min_df=2, max_df=0.95, sublinear_tf=True)),
        ("char", TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), max_features=5000,
                                  min_df=2, max_df=0.95, sublinear_tf=True)),
    ])
    clf = LogisticRegression(class_weight="balanced", solver="liblinear", C=0.1,
                             max_iter=2000, random_state=RANDOM_STATE)
    return Pipeline([("vec", vec), ("clf", clf)])


def metric_row(model_name: str, eval_scope: str, y_true: Iterable[int], proba: Iterable[float], pred: Iterable[int]) -> dict[str, object]:
    y = np.array(list(y_true), dtype=int)
    p = np.array(list(proba), dtype=float)
    pr = np.array(list(pred), dtype=int)
    auc = roc_auc_score(y, p) if len(set(y.tolist())) == 2 else np.nan
    return {
        "model_name": model_name,
        "model_id": MODEL_ID,
        "eval_scope": eval_scope,
        "eval_mode": "oof_stratified_5fold_cv" if "held_out" not in eval_scope else "wendys_held_out",
        "n_rows": int(len(y)),
        "humor_count": int(y.sum()),
        "non_humor_count": int(len(y) - y.sum()),
        "auc": round(float(auc), 4) if not np.isnan(auc) else "NA",
        "f1": round(float(f1_score(y, pr, zero_division=0)), 4),
        "precision": round(float(precision_score(y, pr, zero_division=0)), 4),
        "recall": round(float(recall_score(y, pr, zero_division=0)), 4),
    }


def cm_rows(model_name: str, eval_scope: str, y_true: Iterable[int], pred: Iterable[int]) -> list[dict[str, object]]:
    cm = confusion_matrix(list(y_true), list(pred), labels=[0, 1])
    labels = ["non_humor", "humor"]
    rows = []
    for i, actual in enumerate(labels):
        for j, predicted in enumerate(labels):
            rows.append({
                "model_name": model_name,
                "eval_scope": eval_scope,
                "actual_label": actual,
                "predicted_label": predicted,
                "count": int(cm[i, j]),
            })
    return rows


def load_training_rows(input_path: Path = EXPANDED) -> list[dict[str, str]]:
    rows = read_csv(input_path)
    required = {"source", "text", "humor_presence_binary", "company_name"}
    missing = required - set(rows[0]) if rows else required
    if missing:
        raise ValueError(f"expanded dataset missing columns: {sorted(missing)}")
    return rows


def dataset_for(rows: list[dict[str, str]], model_name: str) -> list[dict[str, str]]:
    if model_name == "batch1_only":
        return [r for r in rows if r["source"] == "batch1_fortune100"]
    if model_name == "batch1_plus_wendys_human":
        return rows
    raise ValueError(model_name)


def summarize_training(rows: list[dict[str, str]]) -> list[dict[str, object]]:
    out = []
    for model_name in ["batch1_only", "batch1_plus_wendys_human"]:
        subset = dataset_for(rows, model_name)
        labels = [int(r["humor_presence_binary"]) for r in subset]
        sources = Counter(r["source"] for r in subset)
        out.append({
            "model_name": model_name,
            "model_id": MODEL_ID,
            "training_scope": "batch1 only" if model_name == "batch1_only" else "batch1 + Wendy's human labels",
            "valid_rows": len(subset),
            "humor_count": sum(labels),
            "non_humor_count": len(labels) - sum(labels),
            "batch1_rows": sources.get("batch1_fortune100", 0),
            "wendys_rows": sources.get("wendys_human", 0),
        })
    return out


def evaluate_oof(rows: list[dict[str, str]], model_name: str) -> tuple[list[dict[str, object]], list[dict[str, object]], list[dict[str, object]], np.ndarray, np.ndarray]:
    texts = [preprocess(r["text"]) for r in rows]
    labels = np.array([int(r["humor_presence_binary"]) for r in rows], dtype=int)
    sources = [r["source"] for r in rows]
    cv = StratifiedKFold(n_splits=N_SPLITS, shuffle=True, random_state=RANDOM_STATE)
    oof_proba = np.full(len(rows), np.nan)
    oof_pred = np.zeros(len(rows), dtype=int)
    for train_idx, test_idx in cv.split(texts, labels):
        pipe = make_pipeline()
        pipe.fit([texts[i] for i in train_idx], labels[train_idx])
        proba = pipe.predict_proba([texts[i] for i in test_idx])[:, 1]
        oof_proba[test_idx] = proba
        oof_pred[test_idx] = (proba >= 0.5).astype(int)
    metrics = [metric_row(model_name, "all_training_rows", labels, oof_proba, oof_pred)]
    cms = cm_rows(model_name, "all_training_rows", labels, oof_pred)
    source_rows = []
    for source in sorted(set(sources)):
        idx = [i for i, s in enumerate(sources) if s == source]
        source_rows.append(metric_row(model_name, source, labels[idx], oof_proba[idx], oof_pred[idx]))
    return metrics, cms, source_rows, oof_proba, oof_pred


def evaluate_wendys_held_out(rows: list[dict[str, str]]) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    train = [r for r in rows if r["source"] == "batch1_fortune100"]
    test = [r for r in rows if r["source"] == "wendys_human"]
    pipe = make_pipeline()
    pipe.fit([preprocess(r["text"]) for r in train], [int(r["humor_presence_binary"]) for r in train])
    y = [int(r["humor_presence_binary"]) for r in test]
    proba = pipe.predict_proba([preprocess(r["text"]) for r in test])[:, 1]
    pred = (proba >= 0.5).astype(int)
    return [metric_row("batch1_only", "wendys_held_out", y, proba, pred)], cm_rows("batch1_only", "wendys_held_out", y, pred)


def feature_names(pipe: Pipeline) -> np.ndarray:
    vec: FeatureUnion = pipe.named_steps["vec"]
    names: list[str] = []
    for transformer_name, transformer in vec.transformer_list:
        for feature in transformer.get_feature_names_out():
            names.append(f"{transformer_name}__{feature}")
    return np.array(names)


def fit_feature_outputs(rows: list[dict[str, str]], model_name: str) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    pipe = make_pipeline()
    texts = [preprocess(r["text"]) for r in rows]
    labels = [int(r["humor_presence_binary"]) for r in rows]
    pipe.fit(texts, labels)
    names = feature_names(pipe)
    coefs = pipe.named_steps["clf"].coef_[0]
    order_pos = np.argsort(coefs)[-50:][::-1]
    order_neg = np.argsort(coefs)[:50]
    feature_rows: list[dict[str, object]] = []
    for rank, idx in enumerate(order_pos, start=1):
        feature_rows.append({"model_name": model_name, "direction": "positive_humor", "rank": rank, "feature": names[idx], "weight": round(float(coefs[idx]), 6)})
    for rank, idx in enumerate(order_neg, start=1):
        feature_rows.append({"model_name": model_name, "direction": "negative_non_humor", "rank": rank, "feature": names[idx], "weight": round(float(coefs[idx]), 6)})
    leakage_rows = []
    for token in WENDYS_TOKENS:
        matched = [(name, coefs[i]) for i, name in enumerate(names) if token in name.lower()]
        top = sorted(matched, key=lambda item: abs(float(item[1])), reverse=True)[:20]
        if not top:
            leakage_rows.append({"model_name": model_name, "diagnostic_token": token, "feature": "", "weight": "", "note": "no matching feature"})
        for name, weight in top:
            leakage_rows.append({"model_name": model_name, "diagnostic_token": token, "feature": name, "weight": round(float(weight), 6), "note": "source-specific token diagnostic"})
    return feature_rows, leakage_rows


def dry_run(rows: list[dict[str, str]]) -> None:
    diag = summarize_training(rows)
    print("DRY RUN: no model training executed")
    for row in diag:
        print(f"{row['model_name']}: valid_rows={row['valid_rows']} humor={row['humor_count']} non_humor={row['non_humor_count']}")
    wendys = sum(1 for r in rows if r["source"] == "wendys_human")
    print(f"wendys_held_out_test_rows={wendys}")


def run(input_path: Path = EXPANDED) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    DIAG_DIR.mkdir(parents=True, exist_ok=True)
    RES_DIR.mkdir(parents=True, exist_ok=True)
    rows = load_training_rows(input_path)
    diag_rows = summarize_training(rows)
    write_csv(OUT_TRAINING_DIAG, diag_rows, ["model_name", "model_id", "training_scope", "valid_rows", "humor_count", "non_humor_count", "batch1_rows", "wendys_rows"])

    metric_rows: list[dict[str, object]] = []
    cm_out: list[dict[str, object]] = []
    source_rows: list[dict[str, object]] = []
    feature_rows: list[dict[str, object]] = []
    leakage_rows: list[dict[str, object]] = []

    for model_name in ["batch1_only", "batch1_plus_wendys_human"]:
        subset = dataset_for(rows, model_name)
        metrics, cms, source_metrics, _, _ = evaluate_oof(subset, model_name)
        metric_rows.extend(metrics)
        cm_out.extend(cms)
        source_rows.extend(source_metrics)
        features, leakage = fit_feature_outputs(subset, model_name)
        feature_rows.extend(features)
        leakage_rows.extend(leakage)

    w_metrics, w_cm = evaluate_wendys_held_out(rows)
    write_csv(OUT_METRICS, metric_rows, ["model_name", "model_id", "eval_scope", "eval_mode", "n_rows", "humor_count", "non_humor_count", "auc", "f1", "precision", "recall"])
    write_csv(OUT_CM, cm_out, ["model_name", "eval_scope", "actual_label", "predicted_label", "count"])
    write_csv(OUT_SOURCE, source_rows, ["model_name", "model_id", "eval_scope", "eval_mode", "n_rows", "humor_count", "non_humor_count", "auc", "f1", "precision", "recall"])
    write_csv(OUT_WENDYS, w_metrics, ["model_name", "model_id", "eval_scope", "eval_mode", "n_rows", "humor_count", "non_humor_count", "auc", "f1", "precision", "recall"])
    write_csv(OUT_WENDYS_CM, w_cm, ["model_name", "eval_scope", "actual_label", "predicted_label", "count"])
    write_csv(OUT_FEATURES, feature_rows, ["model_name", "direction", "rank", "feature", "weight"])
    write_csv(OUT_LEAKAGE, leakage_rows, ["model_name", "diagnostic_token", "feature", "weight", "note"])
    print(f"Wrote model comparison outputs to {BASE.relative_to(ROOT)}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare expanded H1 presence Model A vs Model B.")
    parser.add_argument("--dry-run", action="store_true", help="Load inputs and print expected model row counts without fitting models.")
    parser.add_argument("--input", type=Path, default=EXPANDED, help="Expanded H1 presence training dataset path.")
    args = parser.parse_args()
    rows = load_training_rows(args.input)
    if args.dry_run:
        dry_run(rows)
        return 0
    run(args.input)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
