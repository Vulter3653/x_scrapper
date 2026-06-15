"""
Wendy's human-coded seed label 기반 TF-IDF + Logistic Regression 유머 분류 검증 및 전체 확장
=============================================================================================

1. 이 스크립트의 목적:
   사람이 직접 코딩한 Wendy's 유머 라벨(68건)을 seed label로 사용하여
   TF-IDF + Logistic Regression 텍스트 분류 모델을 학습·검증하고,
   전체 Wendy's 978개 게시글에 유머 확률(p_humor_tfidf_logreg_human)을 확장 예측한다.

2. human-coded seed label을 사용하는 이유:
   기존 rule-based humor_score와 weak-supervised p_humor_ml은 사람이 직접 판단하지 않은
   자동 측정값이다. 사람이 유머라고 판단한 게시글이 실제로 어떤 텍스트 특성을 가지는지를
   직접 학습하면 더 인간 중심적인 유머 탐지가 가능하다.

3. TF-IDF + Logistic Regression을 사용하는 이유:
   - 68건의 소규모 라벨에서 과적합 없이 학습 가능한 단순 선형 모델
   - 텍스트 특성(어떤 단어/bigram이 유머와 연관되는지) 해석 가능
   - 빠르고 재현 가능한 결과
   - Pamuksuz et al. (2021) 방법론과 일관된 축소 pipeline

4. engagement 변수를 모델 학습에 사용하지 않는 이유:
   engagement(좋아요, 리트윗 등)는 H1 분석의 종속변수이다.
   이를 유머 분류 모델 학습에 사용하면 독립변수와 종속변수가 기계적으로 연결되는
   순환 편의(circular bias)가 발생한다.
   따라서 모델 학습에는 오직 text와 human_humor_binary만 사용한다.

5. 전체 978개 확장 예측의 한계:
   현재 seed label은 68건으로 소규모이며, review_priority 기준 선발(비무작위) 표본이다.
   따라서 확장 예측 결과는 exploratory calibration이며 최종 확정 라벨이 아니다.

6. H1 재분석의 의미:
   p_humor_tfidf_logreg_human을 IV로 사용하여 H1(유머 → engagement)을 재검토한다.
   이는 human-coded seed label로 보정된 유머 측정값으로 동일한 H1 회귀를 반복하는 것이다.

7. 인과분석이 아니라 관측적 연관성 분석:
   본 분석은 유머 가능성 점수와 engagement 지표의 통계적 연관성을 보는 것이며,
   '유머가 engagement를 증가시킨다'는 인과관계를 주장하지 않는다.

입력:
    20260615wendy's/data/wendys_partial_human_coded_humor_labels.csv
    20260615wendy's/data/wendys_fast_weak_supervised_humor_dataset.csv

출력:
    20260615wendy's/data/wendys_human_tfidf_logreg_humor_dataset.csv
    20260615wendy's/result/wendys_human_tfidf_logreg_validation_results.csv
    20260615wendy's/result/wendys_human_tfidf_logreg_full_predictions.csv
    20260615wendy's/result/wendys_human_tfidf_logreg_h1_ols_results.csv
    20260615wendy's/result/wendys_human_tfidf_logreg_error_audit.csv
    20260615wendy's/result/wendys_human_tfidf_logreg_summary.md
    20260615wendy's/result/wendys_human_tfidf_logreg_diagnostics.csv
"""

import csv
import hashlib
import math
import re
import sys
from pathlib import Path
from datetime import datetime

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, cross_validate, cross_val_predict
from sklearn.pipeline import Pipeline
import statsmodels.api as sm

# ─────────────────────────────────────────────────────────────────────────────
# 경로 설정 (아포스트로피 포함 폴더 → pathlib.Path)
# ─────────────────────────────────────────────────────────────────────────────
BASE         = Path("20260615wendy's")
HUMAN_CSV    = BASE / "data"   / "wendys_partial_human_coded_humor_labels.csv"
FULL_CSV     = BASE / "data"   / "wendys_fast_weak_supervised_humor_dataset.csv"
RAW_SRC      = Path("data/wendys/posts.json")

OUT_DATASET  = BASE / "data"   / "wendys_human_tfidf_logreg_humor_dataset.csv"
OUT_VAL      = BASE / "result" / "wendys_human_tfidf_logreg_validation_results.csv"
OUT_FULL     = BASE / "result" / "wendys_human_tfidf_logreg_full_predictions.csv"
OUT_H1       = BASE / "result" / "wendys_human_tfidf_logreg_h1_ols_results.csv"
OUT_AUDIT    = BASE / "result" / "wendys_human_tfidf_logreg_error_audit.csv"
OUT_SUMMARY  = BASE / "result" / "wendys_human_tfidf_logreg_summary.md"
OUT_DIAG     = BASE / "result" / "wendys_human_tfidf_logreg_diagnostics.csv"

RANDOM_SEED  = 42


def md5_file(p: Path) -> str:
    """파일 MD5 해시 반환 — 원본 불변 검증용."""
    return hashlib.md5(p.read_bytes()).hexdigest()


def safe_float(v, default=0.0):
    try:
        return float(v)
    except Exception:
        return default


def safe_int(v, default=0):
    try:
        return int(float(v))
    except Exception:
        return default


def median_of(lst):
    s = sorted(x for x in lst if x is not None and math.isfinite(x))
    n = len(s)
    if not s:
        return float("nan")
    return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2.0


def pearson_r(xs, ys):
    """Pearson 상관계수 계산 (scipy 없이)."""
    n = len(xs)
    if n < 2:
        return float("nan")
    mx = sum(xs) / n;  my = sum(ys) / n
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    dx  = math.sqrt(sum((x - mx) ** 2 for x in xs))
    dy  = math.sqrt(sum((y - my) ** 2 for y in ys))
    return num / (dx * dy) if dx * dy > 0 else float("nan")


# 전처리 정규식
URL_RE     = re.compile(r"https?://\S+")
MENTION_RE = re.compile(r"@\w+")


def preprocess(text: str) -> str:
    """
    텍스트 최소 전처리:
    - 소문자 변환
    - URL → <URL>
    - @mention → <MENTION>
    - 해시태그는 # 기호만 제거하여 단어 보존
    - 이모지·구두점은 TF-IDF vectorizer에 위임
    유머는 비격식 표현·이모지·과장된 문장부호에 의존할 수 있으므로 과도하게 제거하지 않는다.
    """
    t = URL_RE.sub("<URL>", text)
    t = MENTION_RE.sub("<MENTION>", t)
    t = re.sub(r"#(\w+)", r"\1", t)   # # 기호만 제거, 단어 보존
    return t.lower().strip()


def run_ols(x_vals, y_vals):
    """단순 이변량 OLS. IV: log1p_p_humor_tfidf_logreg_human."""
    X   = sm.add_constant(np.array(x_vals, dtype=float))
    res = sm.OLS(np.array(y_vals, dtype=float), X).fit()
    ci  = res.conf_int(0.05)
    return dict(
        n_obs=int(res.nobs), intercept=float(res.params[0]),
        beta=float(res.params[1]), se=float(res.bse[1]),
        t=float(res.tvalues[1]), p=float(res.pvalues[1]),
        ci_lo=float(ci[0][1]), ci_hi=float(ci[1][1]),
        r2=float(res.rsquared), adj_r2=float(res.rsquared_adj),
    )


def h1_label(beta, p):
    if beta > 0 and p < 0.05:
        return "H1 예비적 지지"
    elif beta > 0:
        return "H1 방향성 지지"
    return "H1 지지 없음"


def direction_str(beta):
    return "positive" if beta > 0 else ("negative" if beta < 0 else "zero")


# ─────────────────────────────────────────────────────────────────────────────
# 메인 실행
# ─────────────────────────────────────────────────────────────────────────────
def main():
    np.random.seed(RANDOM_SEED)
    raw_md5_before = md5_file(RAW_SRC)

    # ────────────────────────────────────────────────────
    # 단계 1. Human label 파일 읽기 및 정리
    # ────────────────────────────────────────────────────
    print("[1] Human label 로드 중...")
    with open(HUMAN_CSV, newline="", encoding="utf-8-sig") as f:
        human_rows = list(csv.DictReader(f))
    n_human_file = len(human_rows)

    n_humor = n_nonhumor = n_none_as_0 = n_missing_excluded = 0
    labeled = []
    for r in human_rows:
        humor_raw = str(r.get("humor", "")).strip().lower()
        gid       = r.get("global_post_id", "").strip()
        tid       = gid.rsplit(":", 1)[-1].strip()  # tweet_id 추출

        if humor_raw == "humor":
            binary = 1;  n_humor += 1
        elif humor_raw in ("non_humor", "none"):
            binary = 0
            if humor_raw == "none":
                n_none_as_0 += 1
            else:
                n_nonhumor += 1
        elif humor_raw == "":
            n_missing_excluded += 1
            continue
        else:
            n_missing_excluded += 1
            continue

        labeled.append({
            "tweet_id":           tid,
            "global_post_id":     gid,
            "human_humor_binary": binary,
            "human_text":         r.get("text", "").strip(),
            "humor_raw":          humor_raw,
            "type_raw":           r.get("type", "").strip(),
        })

    n_labeled = len(labeled)
    print(f"  파일 행: {n_human_file} / 사용 행: {n_labeled} (humor={n_humor}, "
          f"non_humor={n_nonhumor}, none→0={n_none_as_0}, 제외={n_missing_excluded})")

    # ────────────────────────────────────────────────────
    # 단계 2. 전체 978건 데이터 로드
    # ────────────────────────────────────────────────────
    print("[2] 전체 978건 데이터 로드 중...")
    with open(FULL_CSV, newline="", encoding="utf-8") as f:
        full_rows = list(csv.DictReader(f))
    assert len(full_rows) == 978, f"전체 행 수 오류: {len(full_rows)}"
    full_index = {str(r["id"]): r for r in full_rows}
    print(f"  전체: {len(full_rows)}건")

    # ────────────────────────────────────────────────────
    # 단계 3. Human label과 전체 데이터 병합
    # engagement 변수는 분류기 학습에 사용하지 않는다.
    # ────────────────────────────────────────────────────
    print("[3] Human label ↔ 전체 데이터 병합 중...")
    n_merged = n_unmatched = 0
    for rec in labeled:
        raw = full_index.get(rec["tweet_id"])
        if raw:
            rec["raw_text"]       = raw.get("text", "")
            rec["clean_input"]    = preprocess(rec["human_text"] or rec["raw_text"])
            rec["humor_score"]    = safe_float(raw.get("humor_score", 0))
            rec["p_humor_ml"]     = safe_float(raw.get("p_humor_ml", 0))
            rec["matched"]        = True
            n_merged += 1
        else:
            rec["raw_text"]    = ""
            rec["clean_input"] = preprocess(rec["human_text"])
            rec["humor_score"] = 0.0
            rec["p_humor_ml"]  = 0.0
            rec["matched"]     = False
            n_unmatched += 1

    print(f"  병합 성공: {n_merged} / 실패: {n_unmatched}")

    # ────────────────────────────────────────────────────
    # 단계 4. TF-IDF + Logistic Regression 정의
    # ────────────────────────────────────────────────────
    # 모델 학습에는 text와 human_humor_binary만 사용한다.
    # engagement 변수는 절대 사용하지 않는다.
    pipe = Pipeline([
        ("tfidf", TfidfVectorizer(
            lowercase=True, ngram_range=(1, 2),
            min_df=1, max_df=0.95, sublinear_tf=True,
        )),
        ("clf", LogisticRegression(
            class_weight="balanced", solver="liblinear",
            max_iter=1000, random_state=RANDOM_SEED,
        )),
    ])

    X_texts = [r["clean_input"]    for r in labeled]
    y_labs  = [r["human_humor_binary"] for r in labeled]
    n_pos   = sum(y_labs)
    n_neg   = n_labeled - n_pos

    # ────────────────────────────────────────────────────
    # 단계 5. Cross-validation (StratifiedKFold)
    # 라벨 수가 작으므로 fold 수를 클래스 최솟값에 맞춰 결정한다.
    # ────────────────────────────────────────────────────
    min_class = min(n_pos, n_neg)
    if min_class >= 5:
        n_splits = 5
    elif min_class >= 3:
        n_splits = 3
    else:
        print("[FAIL] 클래스 수가 너무 작아 CV 불가 (min_class < 3)", file=sys.stderr)
        sys.exit(1)

    print(f"[4] StratifiedKFold CV (k={n_splits}) 실행 중...")
    cv = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=RANDOM_SEED)
    cv_res = cross_validate(
        pipe, X_texts, y_labs, cv=cv,
        scoring=["accuracy", "precision", "recall", "f1",
                 "roc_auc", "balanced_accuracy"],
        error_score="raise",
    )
    cv_metrics = {
        "accuracy":          cv_res["test_accuracy"],
        "precision":         cv_res["test_precision"],
        "recall":            cv_res["test_recall"],
        "f1":                cv_res["test_f1"],
        "roc_auc":           cv_res["test_roc_auc"],
        "balanced_accuracy": cv_res["test_balanced_accuracy"],
    }
    for k, v in cv_metrics.items():
        print(f"  {k}: mean={v.mean():.4f}  std={v.std():.4f}")

    # CV 결과 저장
    val_rows = []
    for fold_i in range(n_splits):
        row = {"fold": fold_i + 1}
        for k, v in cv_metrics.items():
            row[k] = "%.4f" % v[fold_i]
        val_rows.append(row)
    # 평균 행 추가
    avg_row = {"fold": "mean"}
    std_row = {"fold": "std"}
    for k, v in cv_metrics.items():
        avg_row[k] = "%.4f" % v.mean()
        std_row[k] = "%.4f" % v.std()
    val_rows += [avg_row, std_row]

    val_cols = ["fold", "accuracy", "precision", "recall",
                "f1", "roc_auc", "balanced_accuracy"]
    with open(OUT_VAL, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=val_cols)
        w.writeheader(); w.writerows(val_rows)

    # ────────────────────────────────────────────────────
    # 단계 6. Out-of-fold 예측 및 error audit
    # ────────────────────────────────────────────────────
    print("[5] OOF 예측 중...")
    oof_probs = cross_val_predict(
        pipe, X_texts, y_labs, cv=cv, method="predict_proba",
    )
    # predict_proba 결과에서 클래스 순서 확인 후 P(humor=1) 추출
    pipe_tmp = Pipeline([
        ("tfidf", TfidfVectorizer(
            lowercase=True, ngram_range=(1, 2),
            min_df=1, max_df=0.95, sublinear_tf=True,
        )),
        ("clf", LogisticRegression(
            class_weight="balanced", solver="liblinear",
            max_iter=1000, random_state=RANDOM_SEED,
        )),
    ])
    pipe_tmp.fit(X_texts, y_labs)
    classes = list(pipe_tmp.named_steps["clf"].classes_)
    pos_idx = classes.index(1) if 1 in classes else 1

    oof_p    = oof_probs[:, pos_idx]
    oof_pred = (oof_p >= 0.5).astype(int)

    error_rows = []
    for i, rec in enumerate(labeled):
        y_true = rec["human_humor_binary"]
        y_hat  = int(oof_pred[i])
        prob   = float(oof_p[i])
        if y_true == 1 and y_hat == 1:
            err = "true_positive"
        elif y_true == 0 and y_hat == 0:
            err = "true_negative"
        elif y_true == 0 and y_hat == 1:
            err = "false_positive"
        else:
            err = "false_negative"
        raw = full_index.get(rec["tweet_id"], {})
        error_rows.append({
            "id":                          rec["tweet_id"],
            "tweet_url":                   raw.get("tweet_url", ""),
            "text":                        rec["human_text"] or raw.get("text", ""),
            "human_humor_binary":          y_true,
            "oof_p_humor_tfidf_logreg":    "%.6f" % prob,
            "oof_pred_humor_tfidf_logreg": y_hat,
            "error_type":                  err,
            "humor":                       rec["humor_raw"],
            "type":                        rec["type_raw"],
        })

    audit_cols = ["id", "tweet_url", "text", "human_humor_binary",
                  "oof_p_humor_tfidf_logreg", "oof_pred_humor_tfidf_logreg",
                  "error_type", "humor", "type"]
    with open(OUT_AUDIT, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=audit_cols, quoting=csv.QUOTE_ALL)
        w.writeheader(); w.writerows(error_rows)
    print(f"  → {OUT_AUDIT}")

    # OOF 오류 집계
    err_counts = {}
    for r in error_rows:
        err_counts[r["error_type"]] = err_counts.get(r["error_type"], 0) + 1
    print(f"  OOF 오류: {err_counts}")

    # ────────────────────────────────────────────────────
    # 단계 7. 전체 모델 학습 → 978건 확장 예측
    # human label 전체를 사용하여 최종 모델 재학습
    # ────────────────────────────────────────────────────
    print("[6] 전체 모델 학습 → 978건 확장 예측 중...")
    pipe.fit(X_texts, y_labs)
    # 978건 전처리
    all_texts = [preprocess(r.get("text", "")) for r in full_rows]
    all_proba = pipe.predict_proba(all_texts)
    all_p     = all_proba[:, pos_idx]

    # 기존 humor_score / p_humor_ml 로드
    hs_vals  = [safe_float(r.get("humor_score", 0))  for r in full_rows]
    pml_vals = [safe_float(r.get("p_humor_ml",  0))  for r in full_rows]

    # 새 변수 생성
    p_new    = [float(p) for p in all_p]
    lp_new   = [math.log1p(p) for p in p_new]
    pred_050 = [1 if p >= 0.5 else 0 for p in p_new]

    # 전체 데이터에 새 변수 추가
    for i, r in enumerate(full_rows):
        r["p_humor_tfidf_logreg_human"]     = "%.6f" % p_new[i]
        r["pred_humor_tfidf_logreg_050"]    = pred_050[i]
        r["log1p_p_humor_tfidf_logreg_human"] = "%.6f" % lp_new[i]

    # engagement DV 계산
    for r in full_rows:
        fav = safe_int(r.get("favorite_count", 0))
        rt  = safe_int(r.get("retweet_count",  0))
        rep = safe_int(r.get("reply_count",    0))
        qt  = safe_int(r.get("quote_count",    0))
        bm  = safe_int(r.get("bookmark_count", 0))
        r["_eng_total"]  = fav + rt + rep + qt + bm
        r["_eng_fav_rt"] = fav + rt
        r["_fav"] = fav; r["_rt"] = rt; r["_rep"] = rep
        r["_qt"]  = qt;  r["_bm"] = bm

    # ────────────────────────────────────────────────────
    # 단계 8. 데이터셋 파일 저장 (978건)
    # ────────────────────────────────────────────────────
    print("[7] 데이터셋 저장 중...")
    ds_add_cols = ["p_humor_tfidf_logreg_human", "pred_humor_tfidf_logreg_050",
                   "log1p_p_humor_tfidf_logreg_human"]
    base_cols = list(csv.DictReader(open(FULL_CSV, newline="", encoding="utf-8")).fieldnames)
    ds_cols   = [c for c in base_cols if not c.startswith("_")] + ds_add_cols
    with open(OUT_DATASET, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=ds_cols, extrasaction="ignore")
        w.writeheader(); w.writerows(full_rows)
    print(f"  → {OUT_DATASET}")

    # full predictions (간결 버전)
    pred_cols = ["id", "tweet_url", "text",
                 "humor_score", "p_humor_ml",
                 "p_humor_tfidf_logreg_human", "pred_humor_tfidf_logreg_050",
                 "log1p_p_humor_tfidf_logreg_human"]
    with open(OUT_FULL, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=pred_cols, extrasaction="ignore", quoting=csv.QUOTE_ALL)
        w.writeheader(); w.writerows(full_rows)
    print(f"  → {OUT_FULL}")

    # ────────────────────────────────────────────────────
    # 단계 9. 기존 점수와 비교 (상관)
    # ────────────────────────────────────────────────────
    corr_hs  = pearson_r(p_new, hs_vals)
    corr_pml = pearson_r(p_new, pml_vals)
    n_ge050  = sum(1 for p in p_new if p >= 0.5)
    print(f"  p_humor_tfidf_logreg_human: mean={sum(p_new)/978:.4f}, "
          f">=0.5: {n_ge050} ({n_ge050/978*100:.1f}%)")
    print(f"  r(humor_score): {corr_hs:.4f}  r(p_humor_ml): {corr_pml:.4f}")

    # ────────────────────────────────────────────────────
    # 단계 10. H1 단순 OLS (log1p_p_humor_tfidf_logreg_human → engagement DVs)
    # 통제변수·고정효과·robust SE 없음
    # ────────────────────────────────────────────────────
    print("[8] H1 단순 OLS 실행 중...")
    x_iv = lp_new
    dv_specs = [
        ("log1p_engagement_total",            [math.log1p(r["_eng_total"])  for r in full_rows]),
        ("log1p_engagement_favorite_retweet", [math.log1p(r["_eng_fav_rt"]) for r in full_rows]),
        ("log1p_favorite_count",              [math.log1p(r["_fav"])        for r in full_rows]),
        ("log1p_retweet_count",               [math.log1p(r["_rt"])         for r in full_rows]),
        ("log1p_reply_count",                 [math.log1p(r["_rep"])        for r in full_rows]),
        ("log1p_quote_count",                 [math.log1p(r["_qt"])         for r in full_rows]),
        ("log1p_bookmark_count",              [math.log1p(r["_bm"])         for r in full_rows]),
    ]
    h1_rows = []
    main_res = None
    for dv_name, y_dv in dv_specs:
        res = run_ols(x_iv, y_dv)
        print(f"  {dv_name}: β={res['beta']:.4f}  p={res['p']:.4f}  R²={res['r2']:.4f}")
        row = {
            "dv":                                  dv_name,
            "model_name":                          "Simple OLS",
            "n_obs":                               res["n_obs"],
            "iv":                                  "log1p_p_humor_tfidf_logreg_human",
            "intercept":                           "%.6f" % res["intercept"],
            "beta_log1p_p_humor_tfidf_logreg_human": "%.6f" % res["beta"],
            "standard_error":                      "%.6f" % res["se"],
            "t_value":                             "%.4f"  % res["t"],
            "p_value":                             "%.6f" % res["p"],
            "ci_lower_95":                         "%.6f" % res["ci_lo"],
            "ci_upper_95":                         "%.6f" % res["ci_hi"],
            "r_squared":                           "%.6f" % res["r2"],
            "adj_r_squared":                       "%.6f" % res["adj_r2"],
            "direction":                           direction_str(res["beta"]),
            "h1_interpretation":                   h1_label(res["beta"], res["p"]),
            "notes": "단순 OLS; 통제변수 없음; FE 없음; 표준 SE; IV=log1p_p_humor_tfidf_logreg_human",
        }
        h1_rows.append(row)
        if dv_name == "log1p_engagement_total":
            main_res = res

    h1_cols = ["dv", "model_name", "n_obs", "iv", "intercept",
               "beta_log1p_p_humor_tfidf_logreg_human", "standard_error",
               "t_value", "p_value", "ci_lower_95", "ci_upper_95",
               "r_squared", "adj_r_squared", "direction", "h1_interpretation", "notes"]
    with open(OUT_H1, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=h1_cols)
        w.writeheader(); w.writerows(h1_rows)
    print(f"  → {OUT_H1}")

    # ────────────────────────────────────────────────────
    # 단계 11. Diagnostics 파일 저장
    # ────────────────────────────────────────────────────
    diag_entries = [
        ("total_full_rows",              978),
        ("human_file_rows",              n_human_file),
        ("human_labeled_rows_used",      n_labeled),
        ("human_label_humor_count",      n_humor),
        ("human_label_nonhumor_count",   n_nonhumor + n_none_as_0),
        ("human_label_missing_excluded", n_missing_excluded),
        ("merged_human_label_rows",      n_merged),
        ("unmatched_human_label_rows",   n_unmatched),
        ("classifier_trained",           True),
        ("n_splits",                     n_splits),
        ("cv_accuracy_mean",             "%.4f" % cv_metrics["accuracy"].mean()),
        ("cv_accuracy_std",              "%.4f" % cv_metrics["accuracy"].std()),
        ("cv_precision_mean",            "%.4f" % cv_metrics["precision"].mean()),
        ("cv_precision_std",             "%.4f" % cv_metrics["precision"].std()),
        ("cv_recall_mean",               "%.4f" % cv_metrics["recall"].mean()),
        ("cv_recall_std",                "%.4f" % cv_metrics["recall"].std()),
        ("cv_f1_mean",                   "%.4f" % cv_metrics["f1"].mean()),
        ("cv_f1_std",                    "%.4f" % cv_metrics["f1"].std()),
        ("cv_roc_auc_mean",              "%.4f" % cv_metrics["roc_auc"].mean()),
        ("cv_roc_auc_std",               "%.4f" % cv_metrics["roc_auc"].std()),
        ("cv_balanced_accuracy_mean",    "%.4f" % cv_metrics["balanced_accuracy"].mean()),
        ("cv_balanced_accuracy_std",     "%.4f" % cv_metrics["balanced_accuracy"].std()),
        ("p_humor_tfidf_logreg_human_min",     "%.4f" % min(p_new)),
        ("p_humor_tfidf_logreg_human_mean",    "%.4f" % (sum(p_new)/978)),
        ("p_humor_tfidf_logreg_human_median",  "%.4f" % median_of(p_new)),
        ("p_humor_tfidf_logreg_human_max",     "%.4f" % max(p_new)),
        ("p_humor_tfidf_logreg_human_ge_050_count", n_ge050),
        ("p_humor_tfidf_logreg_human_ge_050_share", "%.4f" % (n_ge050/978)),
        ("correlation_with_humor_score", "%.4f" % corr_hs),
        ("correlation_with_p_humor_ml",  "%.4f" % corr_pml),
    ]
    with open(OUT_DIAG, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["metric", "value"])
        w.writerows(diag_entries)

    # ────────────────────────────────────────────────────
    # 단계 12. 한국어 요약 마크다운 생성
    # ────────────────────────────────────────────────────
    raw_md5_after = md5_file(RAW_SRC)
    _write_summary(
        n_human_file, n_labeled, n_humor, n_nonhumor + n_none_as_0,
        n_none_as_0, n_missing_excluded, n_merged, n_unmatched,
        n_splits, cv_metrics, err_counts,
        p_new, hs_vals, pml_vals, n_ge050, corr_hs, corr_pml,
        h1_rows, main_res,
    )
    print(f"  → {OUT_SUMMARY}")

    # ────────────────────────────────────────────────────
    # 단계 13. 검증 (17개 항목)
    # ────────────────────────────────────────────────────
    checks = [
        (HUMAN_CSV.exists(),
         "human-coded label 파일 존재"),
        (FULL_CSV.exists(),
         "전체 Wendy's 데이터 978건 파일 존재"),
        (n_labeled >= 60,
         f"human label 사용 행 수 >= 60건 (실제: {n_labeled})"),
        (set(y_labs) == {0, 1},
         "human_humor_binary가 0/1로만 구성"),
        (n_humor > 0 and (n_nonhumor + n_none_as_0) > 0,
         "유머와 비유머 클래스 모두 존재"),
        (True,
         "TF-IDF + Logistic Regression 모델 학습 완료 (설계 보장)"),
        (OUT_VAL.exists(),
         "cross-validation 결과 파일 존재"),
        (True,
         "engagement 변수는 classifier training에 미사용 (설계 보장)"),
        (len(p_new) == 978,
         f"전체 978건에 p_humor_tfidf_logreg_human 생성 (실제: {len(p_new)})"),
        (all(0.0 <= p <= 1.0 for p in p_new),
         "p_humor_tfidf_logreg_human ∈ [0, 1]"),
        (all(math.isfinite(v) for v in lp_new),
         "log1p_p_humor_tfidf_logreg_human 유한값"),
        (OUT_H1.exists(),
         "H1 OLS 결과 파일 존재"),
        (OUT_SUMMARY.exists(),
         "summary markdown 존재 (한글 작성)"),
        (OUT_DIAG.exists(),
         "diagnostics 파일 존재"),
        (OUT_AUDIT.exists(),
         "error audit 파일 존재"),
        (raw_md5_before == raw_md5_after,
         "data/wendys/posts.json 미변경 (MD5 동일)"),
        (all(str(p).startswith(str(BASE))
             for p in [OUT_DATASET, OUT_VAL, OUT_FULL, OUT_H1,
                       OUT_AUDIT, OUT_SUMMARY, OUT_DIAG]),
         "모든 새 파일이 20260615wendy's/ 내부에 위치"),
    ]

    print("\n=== 검증 (17개 항목) ===")
    all_pass = True
    for i, (ok, desc) in enumerate(checks, 1):
        s = "PASS" if ok else "FAIL"
        if not ok:
            all_pass = False
        print("  [%s] %2d. %s" % (s, i, desc))
    print("\n  전체 통과: %s" % all_pass)
    if not all_pass:
        raise RuntimeError("검증 실패 — 커밋하지 않음")
    print("\n완료.")


def _write_summary(n_file, n_used, n_humor, n_nonhumor, n_none,
                   n_excl, n_merged, n_unmatched,
                   n_splits, cv_m, err_counts,
                   p_new, hs_vals, pml_vals, n_ge050, corr_hs, corr_pml,
                   h1_rows, mr):
    """한국어 요약 마크다운 작성."""
    n_all = 978

    def cv_row(k):
        return f"| {k} | {cv_m[k].mean():.4f} | {cv_m[k].std():.4f} |"

    h1_table = ("| 종속변수 | β | p | R² | H1 해석 |\n"
                 "|---|---|---|---|---|\n")
    for r in h1_rows:
        h1_table += (f"| `{r['dv']}` | {r['beta_log1p_p_humor_tfidf_logreg_human']} "
                     f"| {r['p_value']} | {r['r_squared']} | {r['h1_interpretation']} |\n")

    tp = err_counts.get("true_positive", 0)
    tn = err_counts.get("true_negative", 0)
    fp = err_counts.get("false_positive", 0)
    fn = err_counts.get("false_negative", 0)

    summary = f"""# Wendy's human-coded seed label 기반 TF-IDF Logistic Regression 유머 분류 검증 요약

생성일시: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}

> **본 결과는 human-coded partial review sample을 기반으로 한 exploratory calibration이다.
> 전체 Wendy's 데이터에 대한 최종 확정 분류로 해석하지 않는다.**

---

## 1. 작업 목적

사람이 직접 코딩한 Wendy's 유머 라벨({n_used}건)을 seed label로 사용하여
TF-IDF + Logistic Regression 분류 모델을 검증하고,
전체 978건에 유머 확률(`p_humor_tfidf_logreg_human`)을 확장 예측한 후
H1을 단순 OLS로 재분석한다.

---

## 2. 입력 데이터

| 파일 | 행 수 |
|------|-------|
| `wendys_partial_human_coded_humor_labels.csv` | {n_file}건 |
| `wendys_fast_weak_supervised_humor_dataset.csv` | {n_all}건 |

---

## 3. Human label 정리 방식

| 항목 | 건수 |
|------|------|
| 원본 파일 행 | {n_file} |
| label 사용 행 | {n_used} |
| humor = 1 | {n_humor} |
| non_humor/none → 0 | {n_nonhumor} (none 처리: {n_none}건) |
| 결측 제외 | {n_excl} |
| 전체 데이터 병합 성공 | {n_merged} |
| 병합 실패 | {n_unmatched} |

라벨 변환 규칙:
- `humor` → 1
- `non_humor`, `none` → 0
- 공란 → 분석 제외

---

## 4. 모델 구조

```
TfidfVectorizer(ngram_range=(1,2), min_df=1, max_df=0.95, sublinear_tf=True)
→ LogisticRegression(class_weight="balanced", solver="liblinear")
```

텍스트 전처리: 소문자 변환, URL→`<URL>`, @mention→`<MENTION>`, `#` 기호 제거(단어 보존)
engagement 변수는 학습에 사용하지 않음.

---

## 5. Cross-validation 결과 (StratifiedKFold, k={n_splits})

| 지표 | 평균 | 표준편차 |
|------|------|---------|
{cv_row('accuracy')}
{cv_row('precision')}
{cv_row('recall')}
{cv_row('f1')}
{cv_row('roc_auc')}
{cv_row('balanced_accuracy')}

> **현재 cross-validation 성능은 표본 수가 작고 표본이 비무작위이므로 참고용으로만 해석한다.**

---

## 6. 오류 분석 (Out-of-fold, threshold=0.5)

| 오류 유형 | 건수 |
|----------|------|
| True Positive  | {tp} |
| True Negative  | {tn} |
| False Positive | {fp} |
| False Negative | {fn} |
| 합계 | {tp+tn+fp+fn} |

상세 내용은 `wendys_human_tfidf_logreg_error_audit.csv` 참조.

---

## 7. 전체 978개 확장 예측 결과

| 지표 | 값 |
|------|-----|
| 최솟값 | {min(p_new):.4f} |
| 평균 | {sum(p_new)/n_all:.4f} |
| 중앙값 | {median_of(p_new):.4f} |
| 최댓값 | {max(p_new):.4f} |
| >= 0.5 (유머 예측) | {n_ge050}건 ({n_ge050/n_all*100:.1f}%) |

---

## 8. 기존 `humor_score`, `p_humor_ml`과의 비교

| 지표 | humor_score | p_humor_ml | p_humor_tfidf_logreg_human |
|------|-------------|------------|--------------------------|
| 평균 | {sum(hs_vals)/n_all:.4f} | {sum(pml_vals)/n_all:.4f} | {sum(p_new)/n_all:.4f} |
| 0 건수 | {sum(1 for v in hs_vals if v==0)} | {sum(1 for v in pml_vals if v==0)} | {sum(1 for v in p_new if v==0)} |

| 상관 | 값 |
|------|-----|
| `p_humor_tfidf_logreg_human` vs `humor_score` | {corr_hs:.4f} |
| `p_humor_tfidf_logreg_human` vs `p_humor_ml` | {corr_pml:.4f} |

---

## 9. H1 단순 OLS 재분석 결과

IV: `log1p_p_humor_tfidf_logreg_human`

{h1_table}

주요 결과 (`log1p_engagement_total`):
β = {mr['beta']:.6f}, SE = {mr['se']:.6f}, p = {mr['p']:.4f}, R² = {mr['r2']:.6f}

**{h1_label(mr['beta'], mr['p'])}**

---

## 10. 해석

`p_humor_tfidf_logreg_human`은 human-coded seed label로 보정된 유머 가능성 점수이다.
기존 `humor_score`(rule-based) 및 `p_humor_ml`(weak-supervised)과의 상관을 보면,
세 측정값이 어느 정도 일치하는지 확인할 수 있다.

H1 방향성은 {'양의 방향으로 나타남' if mr['beta'] > 0 else '음의 방향으로 나타남'}
(β = {mr['beta']:.4f}, p = {mr['p']:.4f}).

---

## 11. 한계

- human-coded label은 현재 partial review sample 기반이며 완전 무작위 표본이 아니다.
- 라벨 수가 약 {n_used}건으로 작기 때문에 TF-IDF Logistic Regression 결과는 exploratory calibration으로 해석해야 한다.
- 단일 코더 기반이므로 inter-rater reliability가 검증되지 않았다.
- `p_humor_tfidf_logreg_human`은 human-coded seed label 기반 예측값이며 최종 확정 라벨이 아니다.
- H1 분석은 관측적 연관성 분석이며 인과관계를 주장할 수 없다.
- engagement 변수는 모델 학습에는 사용하지 않았고, H1의 종속변수로만 사용하였다.
"""
    with open(OUT_SUMMARY, "w", encoding="utf-8") as f:
        f.write(summary)


if __name__ == "__main__":
    main()
