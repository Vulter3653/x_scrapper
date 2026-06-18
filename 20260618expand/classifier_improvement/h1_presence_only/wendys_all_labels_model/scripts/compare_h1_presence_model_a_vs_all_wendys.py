"""Compare H1 Model A vs Model C using all usable Wendy's labels.

Model A: batch1_fortune100 only.
Model C: batch1_fortune100 + all usable Wendy's human H1 labels.
No integrated-corpus classification, regressions, H2/H3, or type/aggressive models.
"""
from __future__ import annotations

import csv
import re
import sys
from pathlib import Path
from typing import Iterable

PYPACKAGES = Path("/home/user/.local/pypackages")
if str(PYPACKAGES) not in sys.path:
    sys.path.insert(0, str(PYPACKAGES))

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, precision_score, recall_score, roc_auc_score
from sklearn.model_selection import StratifiedKFold
from sklearn.pipeline import FeatureUnion, Pipeline

ROOT = Path(__file__).resolve().parents[5]
H1 = ROOT / "20260618expand" / "classifier_improvement" / "h1_presence_only"
INTEGRATION = H1 / "wendys_all_labels_integration"
BASE = H1 / "wendys_all_labels_model"
DATA = BASE / "data"
DIAG = BASE / "diagnostics"
EXPANDED = INTEGRATION / "data" / "expanded_h1_presence_training_with_all_wendys.csv"
SUMMARY = DIAG / "wendys_label_integration_summary.csv"

MODEL_ID_A = "model_a_batch1_only"
MODEL_ID_C = "model_c_batch1_plus_all_wendys"
ARCH = "word_char_comb__lr_liblin_C01"
RANDOM_STATE = 42
N_SPLITS = 5
OLD_MODEL_A_WENDYS68_F1 = 0.6869
WENDYS_TOKENS = ["wendy", "wendys", "wendy's", "wendy’s", "@wendys", "frosty", "baconator", "nuggs"]

OUT_METRICS = DATA / "model_a_vs_model_c_metrics.csv"
OUT_SOURCE = DATA / "source_aware_metrics.csv"
OUT_HELDOUT = DATA / "wendys_heldout_metrics_all_wendys.csv"
OUT_CM = DATA / "model_a_vs_model_c_confusion_matrices.csv"
OUT_C_PRED = DATA / "model_c_oof_predictions.csv"
OUT_A_HELDOUT_PRED = DATA / "model_a_wendys_all_heldout_predictions.csv"
OUT_TRAIN_DIAG = DIAG / "training_data_diagnostics.csv"
OUT_LEAK = DIAG / "wendys_leakage_feature_diagnostic.csv"
OUT_FEATURES_C = DIAG / "top_feature_weights_model_c.csv"
OUT_VALID_SUMMARY = DIAG / "validation_summary.csv"


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
    return Pipeline([
        ("vec", FeatureUnion([
            ("word", TfidfVectorizer(analyzer="word", ngram_range=(1, 2), max_features=5000, min_df=2, max_df=0.95, sublinear_tf=True)),
            ("char", TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), max_features=5000, min_df=2, max_df=0.95, sublinear_tf=True)),
        ])),
        ("clf", LogisticRegression(solver="liblinear", C=0.1, class_weight="balanced", max_iter=2000, random_state=RANDOM_STATE)),
    ])


def metric_row(model_id: str, eval_scope: str, eval_mode: str, y_true: Iterable[int], proba: Iterable[float], pred: Iterable[int]) -> dict[str, object]:
    y = np.array(list(y_true), dtype=int)
    p = np.array(list(proba), dtype=float)
    pr = np.array(list(pred), dtype=int)
    auc = roc_auc_score(y, p) if len(set(y.tolist())) == 2 else np.nan
    return {
        "model_id": model_id,
        "architecture": ARCH,
        "eval_scope": eval_scope,
        "eval_mode": eval_mode,
        "n_rows": int(len(y)),
        "humor_count": int(y.sum()),
        "non_humor_count": int(len(y) - y.sum()),
        "auc": round(float(auc), 4) if not np.isnan(auc) else "NA",
        "f1": round(float(f1_score(y, pr, zero_division=0)), 4),
        "precision": round(float(precision_score(y, pr, zero_division=0)), 4),
        "recall": round(float(recall_score(y, pr, zero_division=0)), 4),
        "accuracy": round(float(accuracy_score(y, pr)), 4),
    }


def cm_rows(model_id: str, eval_scope: str, y_true: Iterable[int], pred: Iterable[int]) -> list[dict[str, object]]:
    cm = confusion_matrix(list(y_true), list(pred), labels=[0, 1])
    names = ["non_humor", "humor"]
    return [{"model_id": model_id, "eval_scope": eval_scope, "actual_label": names[i], "predicted_label": names[j], "count": int(cm[i, j])} for i in range(2) for j in range(2)]


def dataset(rows: list[dict[str, str]], source_filter: str | None = None) -> list[dict[str, str]]:
    return [r for r in rows if source_filter is None or r.get("source") == source_filter]


def evaluate_oof(rows: list[dict[str, str]], model_id: str) -> tuple[dict[str, object], list[dict[str, object]], np.ndarray, np.ndarray]:
    texts = [preprocess(r["text"]) for r in rows]
    y = np.array([int(r["humor_presence_binary"]) for r in rows], dtype=int)
    proba = np.full(len(rows), np.nan)
    pred = np.zeros(len(rows), dtype=int)
    cv = StratifiedKFold(n_splits=N_SPLITS, shuffle=True, random_state=RANDOM_STATE)
    for tr, te in cv.split(texts, y):
        pipe = make_pipeline()
        pipe.fit([texts[i] for i in tr], y[tr])
        fold_p = pipe.predict_proba([texts[i] for i in te])[:, 1]
        proba[te] = fold_p
        pred[te] = (fold_p >= 0.5).astype(int)
    return metric_row(model_id, "all_training_rows", "oof_stratified_5fold_cv", y, proba, pred), cm_rows(model_id, "all_training_rows", y, pred), proba, pred


def heldout_a_to_wendys(batch1: list[dict[str, str]], wendys: list[dict[str, str]]) -> tuple[dict[str, object], list[dict[str, object]], list[dict[str, object]]]:
    pipe = make_pipeline()
    pipe.fit([preprocess(r["text"]) for r in batch1], [int(r["humor_presence_binary"]) for r in batch1])
    y = [int(r["humor_presence_binary"]) for r in wendys]
    p = pipe.predict_proba([preprocess(r["text"]) for r in wendys])[:, 1]
    pred = (p >= 0.5).astype(int)
    rows = []
    for r, prob, pr in zip(wendys, p, pred):
        rows.append({
            "row_id": r["row_id"], "tweet_id": r.get("tweet_id", ""), "tweet_url": r.get("tweet_url", ""),
            "true_label": r["humor_presence_binary"], "pred_probability": round(float(prob), 6), "pred_t50": int(pr),
        })
    return metric_row(MODEL_ID_A, "wendys_all_human_heldout", "train_batch1_test_all_wendys", y, p, pred), cm_rows(MODEL_ID_A, "wendys_all_human_heldout", y, pred), rows


def source_metrics(model_id: str, rows: list[dict[str, str]], proba: np.ndarray, pred: np.ndarray) -> list[dict[str, object]]:
    y = np.array([int(r["humor_presence_binary"]) for r in rows], dtype=int)
    out = []
    for source in sorted({r["source"] for r in rows}):
        idx = [i for i, r in enumerate(rows) if r["source"] == source]
        out.append(metric_row(model_id, source, "oof_stratified_5fold_cv_source_subset", y[idx], proba[idx], pred[idx]))
    return out


def feature_names(pipe: Pipeline) -> np.ndarray:
    vec = pipe.named_steps["vec"]
    names = []
    for name, transformer in vec.transformer_list:
        names.extend([f"{name}__{f}" for f in transformer.get_feature_names_out()])
    return np.array(names)


def feature_and_leakage(rows: list[dict[str, str]]) -> tuple[list[dict[str, object]], list[dict[str, object]], str]:
    pipe = make_pipeline()
    pipe.fit([preprocess(r["text"]) for r in rows], [int(r["humor_presence_binary"]) for r in rows])
    names = feature_names(pipe)
    weights = pipe.named_steps["clf"].coef_[0]
    pos = np.argsort(weights)[-50:][::-1]
    neg = np.argsort(weights)[:50]
    feat_rows = []
    for rank, idx in enumerate(pos, start=1):
        feat_rows.append({"model_id": MODEL_ID_C, "direction": "positive_humor", "rank": rank, "feature": names[idx], "weight": round(float(weights[idx]), 6)})
    for rank, idx in enumerate(neg, start=1):
        feat_rows.append({"model_id": MODEL_ID_C, "direction": "negative_non_humor", "rank": rank, "feature": names[idx], "weight": round(float(weights[idx]), 6)})
    top10 = {names[i].lower() for i in list(pos[:10]) + list(neg[:10])}
    leak_rows = []
    fail = False
    warn = False
    for token in WENDYS_TOKENS:
        matches = [(names[i], float(weights[i])) for i in range(len(names)) if token in names[i].lower()]
        matches = sorted(matches, key=lambda x: abs(x[1]), reverse=True)[:20]
        if any(token in f for f in top10):
            fail = True
        elif matches:
            warn = True
        if not matches:
            leak_rows.append({"diagnostic_token": token, "feature": "", "weight": "", "rank_abs_weight": "", "leakage_flag": "PASS", "note": "no matching feature"})
        for rank, (feature, weight) in enumerate(matches, start=1):
            leak_rows.append({"diagnostic_token": token, "feature": feature, "weight": round(weight, 6), "rank_abs_weight": rank, "leakage_flag": "WARN", "note": "Wendy-specific feature present; inspect before deployment"})
    flag = "FAIL" if fail else ("WARN" if warn else "PASS")
    for row in leak_rows:
        if row["leakage_flag"] != "PASS":
            row["leakage_flag"] = flag
    return feat_rows, leak_rows, flag


def summary_value(metric: str) -> int:
    if not SUMMARY.exists():
        return 0
    for row in read_csv(SUMMARY):
        if row.get("metric") == metric:
            return int(float(row.get("value", 0)))
    return 0


def main() -> int:
    DATA.mkdir(parents=True, exist_ok=True)
    DIAG.mkdir(parents=True, exist_ok=True)
    rows = read_csv(EXPANDED)
    batch1 = dataset(rows, "batch1_fortune100")
    wendys = dataset(rows, "wendys_all_human")
    model_c_rows = batch1 + wendys

    metrics_a, cm_a, p_a, pred_a = evaluate_oof(batch1, MODEL_ID_A)
    metrics_c, cm_c, p_c, pred_c = evaluate_oof(model_c_rows, MODEL_ID_C)
    held_metrics, held_cm, held_preds = heldout_a_to_wendys(batch1, wendys)
    source_out = source_metrics(MODEL_ID_A, batch1, p_a, pred_a) + source_metrics(MODEL_ID_C, model_c_rows, p_c, pred_c)
    feat_rows, leak_rows, leakage_flag = feature_and_leakage(model_c_rows)

    auc_a = float(metrics_a["auc"])
    auc_c = float(metrics_c["auc"])
    f1_a = float(metrics_a["f1"])
    f1_c = float(metrics_c["f1"])
    held_f1 = float(held_metrics["f1"])
    candidate_status = "model_c_candidate_only" if (auc_c >= auc_a + 0.005 and f1_c >= f1_a and held_f1 >= OLD_MODEL_A_WENDYS68_F1 and leakage_flag != "FAIL") else "retain_model_a_candidate"

    for row in [metrics_a, metrics_c]:
        row["candidate_status"] = candidate_status
        row["leakage_flag"] = leakage_flag
    held_metrics["candidate_status"] = candidate_status
    held_metrics["leakage_flag"] = leakage_flag

    write_csv(OUT_METRICS, [metrics_a, metrics_c], ["model_id", "architecture", "eval_scope", "eval_mode", "n_rows", "humor_count", "non_humor_count", "auc", "f1", "precision", "recall", "accuracy", "candidate_status", "leakage_flag"])
    write_csv(OUT_SOURCE, source_out, ["model_id", "architecture", "eval_scope", "eval_mode", "n_rows", "humor_count", "non_humor_count", "auc", "f1", "precision", "recall", "accuracy"])
    write_csv(OUT_HELDOUT, [held_metrics], ["model_id", "architecture", "eval_scope", "eval_mode", "n_rows", "humor_count", "non_humor_count", "auc", "f1", "precision", "recall", "accuracy", "candidate_status", "leakage_flag"])
    write_csv(OUT_CM, cm_a + cm_c + held_cm, ["model_id", "eval_scope", "actual_label", "predicted_label", "count"])
    pred_rows_c = []
    for r, prob, pred in zip(model_c_rows, p_c, pred_c):
        pred_rows_c.append({"row_id": r["row_id"], "source": r["source"], "tweet_id": r.get("tweet_id", ""), "true_label": r["humor_presence_binary"], "oof_probability": round(float(prob), 6), "oof_pred_t50": int(pred)})
    write_csv(OUT_C_PRED, pred_rows_c, ["row_id", "source", "tweet_id", "true_label", "oof_probability", "oof_pred_t50"])
    write_csv(OUT_A_HELDOUT_PRED, held_preds, ["row_id", "tweet_id", "tweet_url", "true_label", "pred_probability", "pred_t50"])
    write_csv(OUT_TRAIN_DIAG, [
        {"metric": "model_a_rows", "value": len(batch1)},
        {"metric": "model_c_rows", "value": len(model_c_rows)},
        {"metric": "wendys_all_human_rows", "value": len(wendys)},
        {"metric": "raw_wendys_label_rows", "value": summary_value("raw_wendys_label_rows")},
        {"metric": "excluded_uncertain_or_missing_label_rows", "value": summary_value("excluded_uncertain_or_missing_label_rows")},
        {"metric": "excluded_conflict_rows", "value": summary_value("excluded_conflict_rows")},
        {"metric": "candidate_status", "value": candidate_status},
        {"metric": "leakage_flag", "value": leakage_flag},
    ], ["metric", "value"])
    write_csv(OUT_LEAK, leak_rows, ["diagnostic_token", "feature", "weight", "rank_abs_weight", "leakage_flag", "note"])
    write_csv(OUT_FEATURES_C, feat_rows, ["model_id", "direction", "rank", "feature", "weight"])
    write_csv(OUT_VALID_SUMMARY, [
        {"check": "compare_script_completed", "status": "PASS"},
        {"check": "integrated_corpus_reclassification", "status": "NOT_RUN"},
        {"check": "h1_regression", "status": "NOT_RUN"},
        {"check": "h2_h3", "status": "NOT_RUN"},
        {"check": "type_aggressive", "status": "NOT_RUN"},
    ], ["check", "status"])
    print("Compared Model A vs Model C")
    print(f"model_a_rows={len(batch1)}")
    print(f"model_c_rows={len(model_c_rows)}")
    print(f"wendys_all_human_rows={len(wendys)}")
    print(f"candidate_status={candidate_status}")
    print(f"leakage_flag={leakage_flag}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
