"""
run_v3_pipeline.py

training_labels_v3_with_coder3_batch2.csv 기준으로 아래 단계를 실행한다.
  1. 5-fold CV 평가 (presence + type)
  2. 전체 corpus 재분류 (68,039건) → v3 전용 경로 저장
  3. H1/H2/H3 데이터셋 재빌드 → v3 전용 경로 저장
  4. simple OLS baseline 재실행 → simple_ols_baseline_v3_coder3_batch2/ 저장
  5. v2 vs v3 비교 보고서 생성

절대 조건:
  - 기존 v1/v2 결과 덮어쓰기 금지
  - controls, FE, OOF, emoji_count, firm-month aggregation 추가 금지
  - 고정된 첫 번째 simple OLS baseline 수식만 사용
"""
from __future__ import annotations

import csv
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
    accuracy_score, f1_score, precision_score,
    recall_score, roc_auc_score,
)
from sklearn.model_selection import StratifiedKFold
from sklearn.pipeline import Pipeline

ROOT = Path(__file__).resolve().parents[3]
CI   = ROOT / "20260618expand" / "classifier_improvement"

# ── 입력 ──────────────────────────────────────────────────────────────────────
V3_TEMPLATE = CI / "data" / "human_labeling_template" / "training_labels_v3_with_coder3_batch2.csv"
INTEGRATED  = (CI / "h1_presence_only" / "integrated_collected_corpus" / "data"
               / "integrated_h1_presence_classified_posts.csv")

# ── v3 전용 출력 경로 (v1/v2 경로 일체 불변) ─────────────────────────────────
V3_CLASSIFIED  = CI / "data" / "classified"          / "fortune100_domain_adapted_humor_classification_v3.csv"
V3_COMPARISON  = CI / "results"                       / "domain_transfer_comparison_v3.csv"
V3_RR_DIR      = CI / "data" / "regression_ready_v3"
V3_PROC_DIR    = CI / "data" / "processed_v3"
V3_DIAG_DIR    = CI / "data" / "diagnostics_v3"
V3_OLS_DIR     = ROOT / "20260618expand" / "ols_hypothesis_results" / "simple_ols_baseline_v3_coder3_batch2"
V3_CV_DIR      = CI / "results" / "v3_cv_evaluation"

for d in [V3_CLASSIFIED.parent, V3_COMPARISON.parent, V3_RR_DIR,
          V3_PROC_DIR, V3_DIAG_DIR, V3_OLS_DIR, V3_CV_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# ── 참조 스크립트 ──────────────────────────────────────────────────────────────
APPLY_SCRIPT = CI / "scripts" / "apply_domain_adapted_classifier.py"
BUILD_SCRIPT = CI / "scripts" / "build_h1h2h3_from_domain_adapted.py"
OLS_SCRIPT   = (ROOT / "20260618expand" / "ols_hypothesis_results"
                / "simple_ols_baseline_main" / "run_simple_ols_baseline_main.py")

RANDOM_STATE = 42
VALID_PRESENCE = {"0", "1"}
TYPE_CODE_TO_LABEL = {"1": "aggressive", "2": "affiliative",
                      "3": "self_enhancing", "4": "self_defeating"}
TYPE_CLASSES = ["aggressive", "affiliative", "self_enhancing", "self_defeating"]


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


# ── Step 1: CV 평가 ──────────────────────────────────────────────────────────
def step1_cv_evaluation(template_rows: list[dict]) -> dict:
    print("\n" + "─" * 55)
    print("Step 1: 5-fold CV 평가")
    print("─" * 55)

    # Presence CV
    pres_rows = [r for r in template_rows
                 if r.get("human_humor_presence", "").strip() in VALID_PRESENCE]
    texts_bin  = [preprocess(r["text"]) for r in pres_rows]
    labels_bin = [1 if r["human_humor_presence"].strip() == "1" else 0
                  for r in pres_rows]

    print(f"  Presence labels: {len(pres_rows)}"
          f"  (humor={sum(labels_bin)}, non-humor={len(labels_bin)-sum(labels_bin)})")

    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=RANDOM_STATE)
    accs, precs, recs, f1s, aucs = [], [], [], [], []
    for tr_idx, va_idx in skf.split(texts_bin, labels_bin):
        X_tr = [texts_bin[i] for i in tr_idx]
        X_va = [texts_bin[i] for i in va_idx]
        y_tr = [labels_bin[i] for i in tr_idx]
        y_va = [labels_bin[i] for i in va_idx]
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

    pres_cv = {
        "n_labels":   len(pres_rows),
        "humor_n":    sum(labels_bin),
        "accuracy":   round(float(np.mean(accs)),  4),
        "precision":  round(float(np.mean(precs)), 4),
        "recall":     round(float(np.mean(recs)),  4),
        "f1":         round(float(np.mean(f1s)),   4),
        "auc":        round(float(np.nanmean(aucs)), 4),
    }
    print(f"  Presence → AUC={pres_cv['auc']:.4f}  F1={pres_cv['f1']:.4f}")

    # Type CV
    type_rows = [r for r in template_rows
                 if r.get("human_humor_presence", "").strip() == "1"
                 and r.get("human_humor_type", "").strip() in TYPE_CODE_TO_LABEL]
    texts_type  = [preprocess(r["text"]) for r in type_rows]
    labels_type = [TYPE_CODE_TO_LABEL[r["human_humor_type"].strip()] for r in type_rows]

    print(f"  Type labels: {len(type_rows)}")
    label_dist = Counter(labels_type)
    print(f"  Type dist: {dict(label_dist)}")

    n_splits = min(5, min(label_dist.values()))
    skf_type = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=RANDOM_STATE)
    all_preds, all_true = [], []
    for tr_idx, va_idx in skf_type.split(texts_type, labels_type):
        X_tr = [texts_type[i] for i in tr_idx]
        X_va = [texts_type[i] for i in va_idx]
        y_tr = [labels_type[i] for i in tr_idx]
        y_va = [labels_type[i] for i in va_idx]
        pipe = make_type_pipe()
        pipe.fit(X_tr, y_tr)
        preds = pipe.predict(X_va)
        all_preds.extend(preds)
        all_true.extend(y_va)

    macro_f1    = f1_score(all_true, all_preds, average="macro",    zero_division=0, labels=TYPE_CLASSES)
    weighted_f1 = f1_score(all_true, all_preds, average="weighted", zero_division=0, labels=TYPE_CLASSES)

    type_cv = {
        "n_labels":      len(type_rows),
        "n_splits":      n_splits,
        "macro_f1":      round(macro_f1,    4),
        "weighted_f1":   round(weighted_f1, 4),
        "overall_acc":   round(accuracy_score(all_true, all_preds), 4),
        "label_dist":    str(dict(label_dist)),
    }
    for cls in TYPE_CLASSES:
        p = precision_score(all_true, all_preds, labels=[cls], average="macro", zero_division=0)
        r = recall_score(   all_true, all_preds, labels=[cls], average="macro", zero_division=0)
        f = f1_score(       all_true, all_preds, labels=[cls], average="macro", zero_division=0)
        type_cv[f"{cls}_precision"] = round(p, 4)
        type_cv[f"{cls}_recall"]    = round(r, 4)
        type_cv[f"{cls}_f1"]        = round(f, 4)

    print(f"  Type → macro_F1={type_cv['macro_f1']:.4f}")
    print(f"  aggressive  P={type_cv['aggressive_precision']:.4f} "
          f"R={type_cv['aggressive_recall']:.4f} "
          f"F1={type_cv['aggressive_f1']:.4f}")
    print(f"  self_defeating P={type_cv['self_defeating_precision']:.4f} "
          f"R={type_cv['self_defeating_recall']:.4f} "
          f"F1={type_cv['self_defeating_f1']:.4f}")

    # 저장
    with open(V3_CV_DIR / "v3_presence_cv.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(pres_cv.keys()))
        w.writeheader()
        w.writerow(pres_cv)

    with open(V3_CV_DIR / "v3_type_cv.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(type_cv.keys()))
        w.writeheader()
        w.writerow(type_cv)

    print(f"  → {V3_CV_DIR.name}/v3_presence_cv.csv")
    print(f"  → {V3_CV_DIR.name}/v3_type_cv.csv")
    return {"presence": pres_cv, "type": type_cv}


# ── Step 2: 전체 corpus 재분류 ───────────────────────────────────────────────
def step2_classify_corpus() -> None:
    print("\n" + "─" * 55)
    print("Step 2: 전체 corpus 재분류 (v3 전용 경로)")
    print("─" * 55)

    src = APPLY_SCRIPT.read_text(encoding="utf-8")

    # 출력 경로 패치
    src = src.replace(
        'OUT_CLASSIFIED = CI / "data" / "classified" / "fortune100_domain_adapted_humor_classification.csv"',
        f'OUT_CLASSIFIED = Path(r"{V3_CLASSIFIED}")',
    )
    src = src.replace(
        'OUT_COMPARISON = CI / "results" / "domain_transfer_comparison.csv"',
        f'OUT_COMPARISON = Path(r"{V3_COMPARISON}")',
    )
    # template + corpus 경로 고정 (argparse 우회)
    src = src.replace(
        "template_path = args.template if args.template else TEMPLATE",
        f'template_path = Path(r"{V3_TEMPLATE}")',
    )
    src = src.replace(
        "corpus_path = args.input if args.input else MASTER",
        f'corpus_path = Path(r"{INTEGRATED}")',
    )

    exec(compile(src, str(APPLY_SCRIPT), "exec"),
         {"__file__": str(APPLY_SCRIPT), "__name__": "__main__"})
    print(f"  → {V3_CLASSIFIED.name}")


# ── Step 3: H1/H2/H3 재빌드 ──────────────────────────────────────────────────
def step3_build_datasets() -> None:
    print("\n" + "─" * 55)
    print("Step 3: H1/H2/H3 데이터셋 재빌드 (v3 경로)")
    print("─" * 55)

    src = BUILD_SCRIPT.read_text(encoding="utf-8")

    src = src.replace(
        'CLASSIFIED = CI / "data" / "classified" / "fortune100_domain_adapted_humor_classification.csv"',
        f'CLASSIFIED = Path(r"{V3_CLASSIFIED}")',
    )
    src = src.replace(
        'OUT_H1       = CI / "data" / "regression_ready" / "h1_post_level_regression_ready.csv"',
        f'OUT_H1       = Path(r"{V3_RR_DIR / "h1_post_level_regression_ready.csv"}")',
    )
    src = src.replace(
        'OUT_H2       = CI / "data" / "regression_ready" / "h2_post_level_regression_ready.csv"',
        f'OUT_H2       = Path(r"{V3_RR_DIR / "h2_post_level_regression_ready.csv"}")',
    )
    src = src.replace(
        'OUT_H3_PANEL = CI / "data" / "processed" / "h3_firm_month_panel.csv"',
        f'OUT_H3_PANEL = Path(r"{V3_PROC_DIR / "h3_firm_month_panel.csv"}")',
    )
    src = src.replace(
        'OUT_H3_RR    = CI / "data" / "regression_ready" / "h3_firm_period_regression_ready.csv"',
        f'OUT_H3_RR    = Path(r"{V3_RR_DIR / "h3_firm_period_regression_ready.csv"}")',
    )
    src = src.replace(
        'OUT_INCL     = CI / "data" / "diagnostics" / "domain_adapted_regression_sample_inclusion.csv"',
        f'OUT_INCL     = Path(r"{V3_DIAG_DIR / "domain_adapted_regression_sample_inclusion.csv"}")',
    )

    exec(compile(src, str(BUILD_SCRIPT), "exec"),
         {"__file__": str(BUILD_SCRIPT), "__name__": "__main__"})
    print(f"  → {V3_RR_DIR.name}/")


# ── Step 4: simple OLS baseline ───────────────────────────────────────────────
def step4_ols_baseline() -> None:
    print("\n" + "─" * 55)
    print("Step 4: simple OLS baseline (v3)")
    print("─" * 55)

    src = OLS_SCRIPT.read_text(encoding="utf-8")

    src = src.replace(
        "OUT  = Path(__file__).parent",
        f'OUT  = Path(r"{V3_OLS_DIR}")',
    )
    src = src.replace(
        'CLASSIFIED  = CI / "data" / "classified" / "fortune100_domain_adapted_humor_classification.csv"',
        f'CLASSIFIED  = Path(r"{V3_CLASSIFIED}")',
    )
    src = src.replace(
        'H1_RR       = CI / "data" / "regression_ready" / "h1_post_level_regression_ready.csv"',
        f'H1_RR       = Path(r"{V3_RR_DIR / "h1_post_level_regression_ready.csv"}")',
    )
    src = src.replace(
        'H2_RR       = CI / "data" / "regression_ready" / "h2_post_level_regression_ready.csv"',
        f'H2_RR       = Path(r"{V3_RR_DIR / "h2_post_level_regression_ready.csv"}")',
    )
    src = src.replace(
        'TEMPLATE    = CI / "data" / "human_labeling_template" / "fortune100_human_labeling_template_combined.csv"',
        f'TEMPLATE    = Path(r"{V3_TEMPLATE}")',
    )

    exec(compile(src, str(OLS_SCRIPT), "exec"),
         {"__file__": str(OLS_SCRIPT), "__name__": "__main__"})
    print(f"  → {V3_OLS_DIR.name}/")


# ── Step 5: v2 vs v3 비교 ────────────────────────────────────────────────────
def step5_comparison(cv_results: dict) -> None:
    print("\n" + "─" * 55)
    print("Step 5: v2 vs v3 비교 보고서")
    print("─" * 55)

    # v2 CV 결과 로드 (이전 실행 결과가 있으면 사용, 없으면 n/a)
    v2_pres_cv: dict = {}
    v2_type_cv: dict = {}
    for cv_path, store in [
        (CI / "results" / "v2_cv_evaluation" / "v2_presence_cv.csv", "pres"),
        (CI / "results" / "v2_cv_evaluation" / "v2_type_cv.csv",     "type"),
    ]:
        if cv_path.exists():
            with open(cv_path, newline="", encoding="utf-8") as f:
                row = list(csv.DictReader(f))
            if row:
                if store == "pres":
                    v2_pres_cv = row[0]
                else:
                    v2_type_cv = row[0]

    # v3 classified distribution
    with open(V3_CLASSIFIED, newline="", encoding="utf-8") as f:
        v3_cls = list(csv.DictReader(f))
    v3_type_dist = Counter(r["humor_type"] for r in v3_cls)
    v3_total = len(v3_cls)

    # v2 classified distribution (현재 메인 classified 파일)
    V2_CLASSIFIED = CI / "data" / "classified" / "fortune100_domain_adapted_humor_classification.csv"
    v2_type_dist: Counter = Counter()
    v2_total = "n/a"
    if V2_CLASSIFIED.exists():
        with open(V2_CLASSIFIED, newline="", encoding="utf-8") as f:
            v2_cls = list(csv.DictReader(f))
        v2_type_dist = Counter(r["humor_type"] for r in v2_cls)
        v2_total = len(v2_cls)

    rows_out = []

    def add(metric: str, v2_val, v3_val) -> None:
        rows_out.append({"metric": metric, "v2": v2_val, "v3": v3_val})

    # Classifier 성능
    add("presence_n_labels",
        v2_pres_cv.get("n_labels", "n/a"),
        cv_results["presence"]["n_labels"])
    add("presence_auc",
        v2_pres_cv.get("auc", "n/a"),
        cv_results["presence"]["auc"])
    add("presence_f1",
        v2_pres_cv.get("f1",  "n/a"),
        cv_results["presence"]["f1"])
    add("type_n_labels",
        v2_type_cv.get("n_labels", "n/a"),
        cv_results["type"]["n_labels"])
    add("type_macro_f1",
        v2_type_cv.get("macro_f1", "n/a"),
        cv_results["type"]["macro_f1"])
    for cls in TYPE_CLASSES:
        add(f"{cls}_precision",
            v2_type_cv.get(f"{cls}_precision", "n/a"),
            cv_results["type"].get(f"{cls}_precision", 0))
        add(f"{cls}_recall",
            v2_type_cv.get(f"{cls}_recall",    "n/a"),
            cv_results["type"].get(f"{cls}_recall",    0))
        add(f"{cls}_f1",
            v2_type_cv.get(f"{cls}_f1",        "n/a"),
            cv_results["type"].get(f"{cls}_f1",        0))

    # 분류 분포
    for typ in ["non_humorous", "affiliative", "self_enhancing", "aggressive", "self_defeating"]:
        add(f"classified_{typ}", v2_type_dist.get(typ, 0), v3_type_dist.get(typ, 0))
    add("classified_total", v2_total, v3_total)

    out_comp = V3_OLS_DIR / "v2_vs_v3_comparison.csv"
    with open(out_comp, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["metric", "v2", "v3"])
        w.writeheader()
        w.writerows(rows_out)
    print(f"  → {out_comp.name}")

    # 콘솔 요약
    print("\n  [CV 성능 비교]")
    print(f"  {'metric':<32} {'v2':>10} {'v3':>10}")
    print(f"  {'─'*52}")
    key_metrics = ["presence_auc", "presence_f1", "type_macro_f1",
                   "aggressive_precision", "aggressive_recall", "aggressive_f1",
                   "self_defeating_precision", "self_defeating_recall", "self_defeating_f1"]
    for r in rows_out:
        if r["metric"] in key_metrics:
            print(f"  {r['metric']:<32} {str(r['v2']):>10} {str(r['v3']):>10}")

    print("\n  [분류 분포 비교]")
    for r in rows_out:
        if r["metric"].startswith("classified_"):
            print(f"  {r['metric']:<32} {str(r['v2']):>10} {str(r['v3']):>10}")


# ── Main ────────────────────────────────────────────────────────────────────
def main() -> None:
    print("=" * 65)
    print("run_v3_pipeline — training_labels_v3 classifier & OLS")
    print("  기존 v1/v2 경로 불변")
    print("=" * 65)

    # Template 로드
    with open(V3_TEMPLATE, newline="", encoding="utf-8") as f:
        template_rows = list(csv.DictReader(f))
    print(f"\nv3 template: {len(template_rows):,} rows")

    cv_results = step1_cv_evaluation(template_rows)
    step2_classify_corpus()
    step3_build_datasets()
    step4_ols_baseline()
    step5_comparison(cv_results)

    print("\n" + "=" * 65)
    print("run_v3_pipeline COMPLETE")
    print(f"  v3 OLS 결과: {V3_OLS_DIR}")
    print(f"  v3 CV 결과:  {V3_CV_DIR}")
    print("=" * 65)


if __name__ == "__main__":
    main()
