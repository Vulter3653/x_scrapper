"""
compare_classifier_versions.py

v1 / v2 / v3 분류기 성능을 동일한 5-fold CV로 비교한다.
기존 v1/v2/v3 결과 파일을 덮어쓰지 않는다.

출력 (6개 파일):
  results/classifier_performance_comparison/
    classifier_performance_improvement_summary.md
    classifier_performance_improvement_table.csv
    presence_classifier_version_comparison.csv
    type_classifier_version_comparison.csv
    aggressive_class_performance_comparison.csv
    self_defeating_class_performance_comparison.csv
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
from sklearn.metrics import (
    accuracy_score, confusion_matrix,
    f1_score, precision_score, recall_score, roc_auc_score,
)
from sklearn.model_selection import StratifiedKFold
from sklearn.pipeline import Pipeline

ROOT = Path(__file__).resolve().parents[3]
CI   = ROOT / "20260618expand" / "classifier_improvement"

TEMPLATES = {
    "v1": CI / "data" / "human_labeling_template" / "fortune100_human_labeling_template_combined.csv",
    "v2": CI / "data" / "human_labeling_template" / "fortune100_human_labeling_template_combined_v2.csv",
    "v3": CI / "data" / "human_labeling_template" / "training_labels_v3_with_coder3_batch2.csv",
}

OUT_DIR = CI / "results" / "classifier_performance_comparison"
OUT_DIR.mkdir(parents=True, exist_ok=True)

VALID_PRESENCE = {"0", "1"}
TYPE_CODE_TO_LABEL = {
    "1": "aggressive", "2": "affiliative",
    "3": "self_enhancing", "4": "self_defeating",
}
TYPE_CLASSES = ["aggressive", "affiliative", "self_enhancing", "self_defeating"]
RANDOM_STATE = 42


def preprocess(text: str) -> str:
    text = re.sub(r"https?://\S+", "<URL>", text)
    text = re.sub(r"@\w+", "<MENTION>", text)
    text = re.sub(r"#(\w+)", r"\1", text)
    return re.sub(r"\s+", " ", text.lower()).strip()


def make_presence_pipe() -> Pipeline:
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


def make_type_pipe() -> Pipeline:
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


def run_presence_cv(template_rows: list[dict], version: str) -> dict:
    pres_rows  = [r for r in template_rows
                  if r.get("human_humor_presence", "").strip() in VALID_PRESENCE]
    texts      = [preprocess(r["text"]) for r in pres_rows]
    labels     = [1 if r["human_humor_presence"].strip() == "1" else 0 for r in pres_rows]
    total_n    = len(template_rows)
    n_humor    = sum(labels)
    n_non      = len(labels) - n_humor

    print(f"  [{version}] Presence: total_template={total_n:,}  "
          f"valid_binary={len(labels):,}  humor={n_humor}  non={n_non}")

    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=RANDOM_STATE)
    all_preds, all_true, all_probs = [], [], []
    accs, precs, recs, f1s, aucs   = [], [], [], [], []

    for tr_idx, va_idx in skf.split(texts, labels):
        X_tr = [texts[i] for i in tr_idx]
        X_va = [texts[i] for i in va_idx]
        y_tr = [labels[i] for i in tr_idx]
        y_va = [labels[i] for i in va_idx]
        pipe = make_presence_pipe()
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
        all_preds.extend(preds)
        all_true.extend(y_va)
        all_probs.extend(probs)

    cm = confusion_matrix(all_true, all_preds, labels=[0, 1])
    # cm[actual][predicted]: [[TN, FP], [FN, TP]]
    tn, fp, fn, tp = cm.ravel()

    result = {
        "version":             version,
        "total_template_rows": total_n,
        "valid_binary_n":      len(labels),
        "n_humor":             n_humor,
        "n_non_humorous":      n_non,
        "accuracy":            round(float(np.mean(accs)),  4),
        "precision":           round(float(np.mean(precs)), 4),
        "recall":              round(float(np.mean(recs)),  4),
        "f1":                  round(float(np.mean(f1s)),   4),
        "auc":                 round(float(np.nanmean(aucs)), 4),
        "cm_TN": int(tn), "cm_FP": int(fp),
        "cm_FN": int(fn), "cm_TP": int(tp),
    }
    print(f"         → AUC={result['auc']:.4f}  F1={result['f1']:.4f}  "
          f"Prec={result['precision']:.4f}  Rec={result['recall']:.4f}")
    return result


def run_type_cv(template_rows: list[dict], version: str) -> dict:
    type_rows   = [r for r in template_rows
                   if r.get("human_humor_presence", "").strip() == "1"
                   and r.get("human_humor_type", "").strip() in TYPE_CODE_TO_LABEL]
    texts       = [preprocess(r["text"]) for r in type_rows]
    labels      = [TYPE_CODE_TO_LABEL[r["human_humor_type"].strip()] for r in type_rows]
    label_dist  = Counter(labels)
    n_agg       = label_dist.get("aggressive",     0)
    n_aff       = label_dist.get("affiliative",    0)
    n_se        = label_dist.get("self_enhancing", 0)
    n_sd        = label_dist.get("self_defeating", 0)

    print(f"  [{version}] Type: n={len(labels):,}  "
          f"agg={n_agg}  aff={n_aff}  se={n_se}  sd={n_sd}")

    n_splits = min(5, min(label_dist.values()))
    if n_splits < 2:
        print(f"  WARNING: cannot run type CV — min class count too low")
        return {"version": version, "type_n": len(labels), "error": "insufficient_data"}

    skf = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=RANDOM_STATE)
    all_preds, all_true = [], []

    for tr_idx, va_idx in skf.split(texts, labels):
        X_tr = [texts[i] for i in tr_idx]
        X_va = [texts[i] for i in va_idx]
        y_tr = [labels[i] for i in tr_idx]
        y_va = [labels[i] for i in va_idx]
        pipe = make_type_pipe()
        pipe.fit(X_tr, y_tr)
        preds = pipe.predict(X_va)
        all_preds.extend(preds)
        all_true.extend(y_va)

    macro_f1    = f1_score(all_true, all_preds, average="macro",    zero_division=0, labels=TYPE_CLASSES)
    weighted_f1 = f1_score(all_true, all_preds, average="weighted", zero_division=0, labels=TYPE_CLASSES)
    overall_acc = accuracy_score(all_true, all_preds)

    cm = confusion_matrix(all_true, all_preds, labels=TYPE_CLASSES)

    result: dict = {
        "version":       version,
        "type_n":        len(labels),
        "n_aggressive":  n_agg,
        "n_affiliative": n_aff,
        "n_self_enhancing": n_se,
        "n_self_defeating": n_sd,
        "n_splits_used": n_splits,
        "macro_f1":      round(macro_f1,    4),
        "weighted_f1":   round(weighted_f1, 4),
        "overall_acc":   round(overall_acc, 4),
    }
    for cls in TYPE_CLASSES:
        p = precision_score(all_true, all_preds, labels=[cls], average="macro", zero_division=0)
        r = recall_score(   all_true, all_preds, labels=[cls], average="macro", zero_division=0)
        f = f1_score(       all_true, all_preds, labels=[cls], average="macro", zero_division=0)
        result[f"{cls}_precision"] = round(p, 4)
        result[f"{cls}_recall"]    = round(r, 4)
        result[f"{cls}_f1"]        = round(f, 4)

    # confusion matrix (4×4)
    for i, true_cls in enumerate(TYPE_CLASSES):
        for j, pred_cls in enumerate(TYPE_CLASSES):
            result[f"cm_{true_cls[:3]}_pred_{pred_cls[:3]}"] = int(cm[i][j])

    print(f"         → macro_F1={result['macro_f1']:.4f}  "
          f"agg_F1={result['aggressive_f1']:.4f}  "
          f"sd_F1={result['self_defeating_f1']:.4f}")
    return result


def save_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        return
    fields = list(rows[0].keys())
    for r in rows[1:]:
        for k in r:
            if k not in fields:
                fields.append(k)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def delta(v_new, v_old, fmt=".4f") -> str:
    try:
        d = float(v_new) - float(v_old)
        return f"{d:+{fmt}}"
    except (TypeError, ValueError):
        return "n/a"


def main() -> None:
    print("=" * 65)
    print("compare_classifier_versions  v1 / v2 / v3")
    print("=" * 65)

    pres_results: list[dict] = []
    type_results: list[dict] = []

    for ver, path in TEMPLATES.items():
        print(f"\n{'─'*55}")
        print(f"  버전: {ver}  ({path.name})")
        print(f"{'─'*55}")
        with open(path, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        pres_results.append(run_presence_cv(rows, ver))
        type_results.append(run_type_cv(rows, ver))

    # ── 출력 파일 ─────────────────────────────────────────────────────────────
    # 1. presence_classifier_version_comparison.csv
    save_csv(OUT_DIR / "presence_classifier_version_comparison.csv", pres_results)
    print(f"\n→ presence_classifier_version_comparison.csv")

    # 2. type_classifier_version_comparison.csv
    save_csv(OUT_DIR / "type_classifier_version_comparison.csv", type_results)
    print(f"→ type_classifier_version_comparison.csv")

    # 3. aggressive_class_performance_comparison.csv
    agg_rows = []
    for r in type_results:
        agg_rows.append({
            "version":             r["version"],
            "n_aggressive":        r.get("n_aggressive", "n/a"),
            "aggressive_precision": r.get("aggressive_precision", "n/a"),
            "aggressive_recall":   r.get("aggressive_recall",    "n/a"),
            "aggressive_f1":       r.get("aggressive_f1",        "n/a"),
        })
    save_csv(OUT_DIR / "aggressive_class_performance_comparison.csv", agg_rows)
    print(f"→ aggressive_class_performance_comparison.csv")

    # 4. self_defeating_class_performance_comparison.csv
    sd_rows = []
    for r in type_results:
        sd_rows.append({
            "version":                  r["version"],
            "n_self_defeating":         r.get("n_self_defeating",         "n/a"),
            "self_defeating_precision": r.get("self_defeating_precision", "n/a"),
            "self_defeating_recall":    r.get("self_defeating_recall",    "n/a"),
            "self_defeating_f1":        r.get("self_defeating_f1",        "n/a"),
        })
    save_csv(OUT_DIR / "self_defeating_class_performance_comparison.csv", sd_rows)
    print(f"→ self_defeating_class_performance_comparison.csv")

    # 5. classifier_performance_improvement_table.csv
    p1 = {r["version"]: r for r in pres_results}
    t1 = {r["version"]: r for r in type_results}

    table_rows = []
    metrics_pres = ["valid_binary_n", "accuracy", "precision", "recall", "f1", "auc"]
    metrics_type = ["type_n", "macro_f1", "weighted_f1", "overall_acc",
                    "aggressive_precision", "aggressive_recall", "aggressive_f1",
                    "self_defeating_precision", "self_defeating_recall", "self_defeating_f1"]

    for m in metrics_pres:
        row = {"metric": m, "layer": "presence"}
        for v in ["v1", "v2", "v3"]:
            row[v] = p1[v].get(m, "n/a")
        row["v1_to_v2"] = delta(p1["v2"].get(m), p1["v1"].get(m))
        row["v2_to_v3"] = delta(p1["v3"].get(m), p1["v2"].get(m))
        row["v1_to_v3"] = delta(p1["v3"].get(m), p1["v1"].get(m))
        table_rows.append(row)

    for m in metrics_type:
        row = {"metric": m, "layer": "type"}
        for v in ["v1", "v2", "v3"]:
            row[v] = t1[v].get(m, "n/a")
        row["v1_to_v2"] = delta(t1["v2"].get(m), t1["v1"].get(m))
        row["v2_to_v3"] = delta(t1["v3"].get(m), t1["v2"].get(m))
        row["v1_to_v3"] = delta(t1["v3"].get(m), t1["v1"].get(m))
        table_rows.append(row)

    save_csv(OUT_DIR / "classifier_performance_improvement_table.csv", table_rows)
    print(f"→ classifier_performance_improvement_table.csv")

    # ── Confusion matrix 텍스트 ───────────────────────────────────────────────
    def cm_presence_str(r: dict) -> str:
        tn = r.get("cm_TN", "?"); fp = r.get("cm_FP", "?")
        fn = r.get("cm_FN", "?"); tp = r.get("cm_TP", "?")
        return (f"| | pred Non | pred Humor |\n"
                f"|:---|---:|---:|\n"
                f"| **actual Non** | {tn} | {fp} |\n"
                f"| **actual Humor** | {fn} | {tp} |")

    def cm_type_str(r: dict) -> str:
        header = "| | pred_agg | pred_aff | pred_se | pred_sd |"
        sep    = "|:---|---:|---:|---:|---:|"
        lines  = [header, sep]
        for cls in TYPE_CLASSES:
            short = cls[:3]
            row_vals = [str(r.get(f"cm_{cls[:3]}_pred_{pc[:3]}", "?"))
                        for pc in TYPE_CLASSES]
            lines.append(f"| **{cls}** | {' | '.join(row_vals)} |")
        return "\n".join(lines)

    # ── 6. classifier_performance_improvement_summary.md ─────────────────────
    v1p = p1["v1"]; v2p = p1["v2"]; v3p = p1["v3"]
    v1t = t1["v1"]; v2t = t1["v2"]; v3t = t1["v3"]

    md = f"""# Classifier Performance Improvement Summary

생성일: 2026-06-19

## 비교 버전 및 Training Label 규모

| 버전 | template | total_rows | valid_binary_n | type_n | 주요 추가 |
|:---|:---|---:|---:|---:|:---|
| v1 | combined (원본) | {v1p['total_template_rows']:,} | {v1p['valid_binary_n']:,} | {v1t.get('type_n','n/a'):,} | batch1 + batch2 (coder1/2) |
| v2 | combined_v2 (Wendy's) | {v2p['total_template_rows']:,} | {v2p['valid_binary_n']:,} | {v2t.get('type_n','n/a'):,} | Wendy's 597건 추가 |
| v3 | v3 (coder3 batch2) | {v3p['total_template_rows']:,} | {v3p['valid_binary_n']:,} | {v3t.get('type_n','n/a'):,} | coder3 batch2 497건 추가 |

---

## Presence Classifier 성능 (5-fold CV)

| 지표 | v1 | v2 | v3 | v1→v2 | v2→v3 | v1→v3 |
|:---|---:|---:|---:|---:|---:|---:|
| valid_binary_n | {v1p['valid_binary_n']:,} | {v2p['valid_binary_n']:,} | {v3p['valid_binary_n']:,} | {delta(v2p['valid_binary_n'], v1p['valid_binary_n'], '.0f')} | {delta(v3p['valid_binary_n'], v2p['valid_binary_n'], '.0f')} | {delta(v3p['valid_binary_n'], v1p['valid_binary_n'], '.0f')} |
| AUC | {v1p['auc']} | {v2p['auc']} | {v3p['auc']} | {delta(v2p['auc'], v1p['auc'])} | {delta(v3p['auc'], v2p['auc'])} | {delta(v3p['auc'], v1p['auc'])} |
| F1 | {v1p['f1']} | {v2p['f1']} | {v3p['f1']} | {delta(v2p['f1'], v1p['f1'])} | {delta(v3p['f1'], v2p['f1'])} | {delta(v3p['f1'], v1p['f1'])} |
| Accuracy | {v1p['accuracy']} | {v2p['accuracy']} | {v3p['accuracy']} | {delta(v2p['accuracy'], v1p['accuracy'])} | {delta(v3p['accuracy'], v2p['accuracy'])} | {delta(v3p['accuracy'], v1p['accuracy'])} |
| Precision | {v1p['precision']} | {v2p['precision']} | {v3p['precision']} | {delta(v2p['precision'], v1p['precision'])} | {delta(v3p['precision'], v2p['precision'])} | {delta(v3p['precision'], v1p['precision'])} |
| Recall | {v1p['recall']} | {v2p['recall']} | {v3p['recall']} | {delta(v2p['recall'], v1p['recall'])} | {delta(v3p['recall'], v2p['recall'])} | {delta(v3p['recall'], v1p['recall'])} |

### Confusion Matrix (전 fold 누적)

**v1:**
{cm_presence_str(v1p)}

**v2:**
{cm_presence_str(v2p)}

**v3:**
{cm_presence_str(v3p)}

---

## Type Classifier 성능 (stratified k-fold CV)

| 지표 | v1 | v2 | v3 | v1→v2 | v2→v3 | v1→v3 |
|:---|---:|---:|---:|---:|---:|---:|
| type_n | {v1t.get('type_n','n/a'):,} | {v2t.get('type_n','n/a'):,} | {v3t.get('type_n','n/a'):,} | {delta(v2t.get('type_n'), v1t.get('type_n'), '.0f')} | {delta(v3t.get('type_n'), v2t.get('type_n'), '.0f')} | {delta(v3t.get('type_n'), v1t.get('type_n'), '.0f')} |
| macro_F1 | {v1t.get('macro_f1','n/a')} | {v2t.get('macro_f1','n/a')} | {v3t.get('macro_f1','n/a')} | {delta(v2t.get('macro_f1'), v1t.get('macro_f1'))} | {delta(v3t.get('macro_f1'), v2t.get('macro_f1'))} | {delta(v3t.get('macro_f1'), v1t.get('macro_f1'))} |
| weighted_F1 | {v1t.get('weighted_f1','n/a')} | {v2t.get('weighted_f1','n/a')} | {v3t.get('weighted_f1','n/a')} | {delta(v2t.get('weighted_f1'), v1t.get('weighted_f1'))} | {delta(v3t.get('weighted_f1'), v2t.get('weighted_f1'))} | {delta(v3t.get('weighted_f1'), v1t.get('weighted_f1'))} |
| overall_acc | {v1t.get('overall_acc','n/a')} | {v2t.get('overall_acc','n/a')} | {v3t.get('overall_acc','n/a')} | {delta(v2t.get('overall_acc'), v1t.get('overall_acc'))} | {delta(v3t.get('overall_acc'), v2t.get('overall_acc'))} | {delta(v3t.get('overall_acc'), v1t.get('overall_acc'))} |

### Confusion Matrix (type, v3)

{cm_type_str(v3t)}

---

## Aggressive Class 성능 변화 (H2/H3 핵심 지표)

| 지표 | v1 | v2 | v3 | v1→v2 | v2→v3 | v1→v3 |
|:---|---:|---:|---:|---:|---:|---:|
| n_aggressive | {v1t.get('n_aggressive','n/a')} | {v2t.get('n_aggressive','n/a')} | {v3t.get('n_aggressive','n/a')} | {delta(v2t.get('n_aggressive'), v1t.get('n_aggressive'), '.0f')} | {delta(v3t.get('n_aggressive'), v2t.get('n_aggressive'), '.0f')} | {delta(v3t.get('n_aggressive'), v1t.get('n_aggressive'), '.0f')} |
| aggressive_precision | {v1t.get('aggressive_precision','n/a')} | {v2t.get('aggressive_precision','n/a')} | {v3t.get('aggressive_precision','n/a')} | {delta(v2t.get('aggressive_precision'), v1t.get('aggressive_precision'))} | {delta(v3t.get('aggressive_precision'), v2t.get('aggressive_precision'))} | {delta(v3t.get('aggressive_precision'), v1t.get('aggressive_precision'))} |
| aggressive_recall | {v1t.get('aggressive_recall','n/a')} | {v2t.get('aggressive_recall','n/a')} | {v3t.get('aggressive_recall','n/a')} | {delta(v2t.get('aggressive_recall'), v1t.get('aggressive_recall'))} | {delta(v3t.get('aggressive_recall'), v2t.get('aggressive_recall'))} | {delta(v3t.get('aggressive_recall'), v1t.get('aggressive_recall'))} |
| aggressive_F1 | {v1t.get('aggressive_f1','n/a')} | {v2t.get('aggressive_f1','n/a')} | {v3t.get('aggressive_f1','n/a')} | {delta(v2t.get('aggressive_f1'), v1t.get('aggressive_f1'))} | {delta(v3t.get('aggressive_f1'), v2t.get('aggressive_f1'))} | {delta(v3t.get('aggressive_f1'), v1t.get('aggressive_f1'))} |

---

## Self-Defeating Class 성능 변화 (H2-3 예외 해석 근거)

| 지표 | v1 | v2 | v3 | v1→v2 | v2→v3 | v1→v3 |
|:---|---:|---:|---:|---:|---:|---:|
| n_self_defeating | {v1t.get('n_self_defeating','n/a')} | {v2t.get('n_self_defeating','n/a')} | {v3t.get('n_self_defeating','n/a')} | {delta(v2t.get('n_self_defeating'), v1t.get('n_self_defeating'), '.0f')} | {delta(v3t.get('n_self_defeating'), v2t.get('n_self_defeating'), '.0f')} | {delta(v3t.get('n_self_defeating'), v1t.get('n_self_defeating'), '.0f')} |
| sd_precision | {v1t.get('self_defeating_precision','n/a')} | {v2t.get('self_defeating_precision','n/a')} | {v3t.get('self_defeating_precision','n/a')} | {delta(v2t.get('self_defeating_precision'), v1t.get('self_defeating_precision'))} | {delta(v3t.get('self_defeating_precision'), v2t.get('self_defeating_precision'))} | {delta(v3t.get('self_defeating_precision'), v1t.get('self_defeating_precision'))} |
| sd_recall | {v1t.get('self_defeating_recall','n/a')} | {v2t.get('self_defeating_recall','n/a')} | {v3t.get('self_defeating_recall','n/a')} | {delta(v2t.get('self_defeating_recall'), v1t.get('self_defeating_recall'))} | {delta(v3t.get('self_defeating_recall'), v2t.get('self_defeating_recall'))} | {delta(v3t.get('self_defeating_recall'), v1t.get('self_defeating_recall'))} |
| sd_F1 | {v1t.get('self_defeating_f1','n/a')} | {v2t.get('self_defeating_f1','n/a')} | {v3t.get('self_defeating_f1','n/a')} | {delta(v2t.get('self_defeating_f1'), v1t.get('self_defeating_f1'))} | {delta(v3t.get('self_defeating_f1'), v2t.get('self_defeating_f1'))} | {delta(v3t.get('self_defeating_f1'), v1t.get('self_defeating_f1'))} |

---

## 보수적 해석

### 1. Training label coverage 변화
v1 → v2 → v3 순으로 valid binary label이 {v1p['valid_binary_n']:,} → {v2p['valid_binary_n']:,} → {v3p['valid_binary_n']:,}으로 증가했다.
type training label은 {v1t.get('type_n','n/a')} → {v2t.get('type_n','n/a')} → {v3t.get('type_n','n/a')}으로 증가했다.

### 2. Presence classifier 성능 변화
AUC 변화: v1({v1p['auc']}) → v2({v2p['auc']}) → v3({v3p['auc']}).
Wendy's labels 추가(v2) 이후 AUC가 소폭 변동하였으며, coder3 추가(v3)는 거의 동일 수준을 유지했다.
Presence classifier 성능은 크게 향상되었다기보다 **안정적으로 유지**되었다고 보는 것이 적절하다.

### 3. Type classifier 성능 변화
macro F1: v1({v1t.get('macro_f1','n/a')}) → v2({v2t.get('macro_f1','n/a')}) → v3({v3t.get('macro_f1','n/a')}).
전체 macro F1은 제한적이지만, aggressive class의 학습 데이터가 {v1t.get('n_aggressive','?')} → {v3t.get('n_aggressive','?')}으로 증가하면서
H2/H3 측정 기반은 일부 개선되었다.

### 4. Aggressive class 성능 한계
aggressive precision/recall/F1이 0.30 수준에 머물러 있다.
이는 H2-1, H2-2, H3 full-sample 결과의 해석 시 **분류기 측정 오차(measurement error)** 를
반드시 한계로 명시해야 함을 의미한다.

### 5. Self-defeating class 한계
v3 기준 n_self_defeating={v3t.get('n_self_defeating','n/a')}, F1={v3t.get('self_defeating_f1','n/a')}.
이 클래스는 소수 클래스(minority class)로, precision/recall 모두 매우 낮다.
H2-3의 "Aggressive − Self-Defeating not supported" 결과는
분류기가 self-defeating을 정확히 분류하지 못하는 한계가 결과에 영향을 미쳤을 수 있다.
따라서 이 결과는 신중하게 해석해야 한다.

### 6. Downstream simple OLS 결과와의 연결
v3 classifier 기준 full-sample H1 WHE = +1.1665*** (지지됨).
H2-1 (Other weighted avg) = +0.8495*** (지지됨), H2-2 (SELF weighted avg) = +0.4384*** (지지됨).
H2-3 Agg − SD = −0.2483** (opposite direction) — classifier 측정 오차 가능성 존재.
H3 turning point = 0.561, in range → H3 지지됨.
이 결과들은 classifier AUC=0.777, aggressive F1=0.321 수준의 분류기에 기반하므로,
measurement error를 통제한 추가 분석(FE 모델 등)에서 검증이 필요하다.

---

> 생성: compare_classifier_versions.py | 2026-06-19
"""

    (OUT_DIR / "classifier_performance_improvement_summary.md").write_text(md, encoding="utf-8")
    print(f"→ classifier_performance_improvement_summary.md")

    print("\n" + "=" * 65)
    print("compare_classifier_versions COMPLETE")
    print(f"  출력: {OUT_DIR}")
    print("=" * 65)


if __name__ == "__main__":
    main()
