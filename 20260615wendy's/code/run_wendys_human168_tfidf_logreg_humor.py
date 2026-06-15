"""
run_wendys_human168_tfidf_logreg_humor.py

wendys_humor_review_sheet.csv에 통합된 168건 human label을 seed로
TF-IDF + Logistic Regression을 재학습하고, 978건 전체에 새로운 유머 확률을 예측한다.
결과로 review sheet의 model_humor / p_humor / humor_grade를 업데이트한다.

입력:
    20260615wendy's/result/wendys_humor_review_sheet.csv   (labels: 168건)
    20260615wendy's/data/wendys_fast_weak_supervised_humor_dataset.csv  (engagement DV용)

출력:
    20260615wendy's/result/wendys_humor_review_sheet.csv              (업데이트)
    20260615wendy's/result/wendys_human168_tfidf_logreg_full_predictions.csv
    20260615wendy's/result/wendys_human168_tfidf_logreg_validation_results.csv
    20260615wendy's/result/wendys_human168_tfidf_logreg_error_audit.csv
    20260615wendy's/result/wendys_human168_tfidf_logreg_h1_ols_results.csv
    20260615wendy's/result/wendys_human168_tfidf_logreg_summary.md
    20260615wendy's/result/wendys_human168_tfidf_logreg_diagnostics.csv
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

BASE        = Path("20260615wendy's")
REVIEW_CSV  = BASE / "result" / "wendys_humor_review_sheet.csv"
FULL_CSV    = BASE / "data"   / "wendys_fast_weak_supervised_humor_dataset.csv"
RAW_SRC     = Path("data/wendys/posts.json")

OUT_FULL    = BASE / "result" / "wendys_human168_tfidf_logreg_full_predictions.csv"
OUT_VAL     = BASE / "result" / "wendys_human168_tfidf_logreg_validation_results.csv"
OUT_AUDIT   = BASE / "result" / "wendys_human168_tfidf_logreg_error_audit.csv"
OUT_H1      = BASE / "result" / "wendys_human168_tfidf_logreg_h1_ols_results.csv"
OUT_SUMMARY = BASE / "result" / "wendys_human168_tfidf_logreg_summary.md"
OUT_DIAG    = BASE / "result" / "wendys_human168_tfidf_logreg_diagnostics.csv"

RANDOM_SEED = 42


def md5_file(p):
    return hashlib.md5(p.read_bytes()).hexdigest()


def safe_float(v, default=0.0):
    try: return float(v)
    except: return default


def safe_int(v, default=0):
    try: return int(float(v))
    except: return default


def median_of(lst):
    s = sorted(x for x in lst if x is not None and math.isfinite(x))
    n = len(s)
    if not s: return float("nan")
    return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2.0


def pearson_r(xs, ys):
    n = len(xs)
    if n < 2: return float("nan")
    mx = sum(xs) / n; my = sum(ys) / n
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    dx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    dy = math.sqrt(sum((y - my) ** 2 for y in ys))
    return num / (dx * dy) if dx * dy > 0 else float("nan")


URL_RE     = re.compile(r"https?://\S+")
MENTION_RE = re.compile(r"@\w+")


def preprocess(text):
    t = URL_RE.sub("<URL>", text)
    t = MENTION_RE.sub("<MENTION>", t)
    t = re.sub(r"#(\w+)", r"\1", t)
    return t.lower().strip()


def run_ols(x_vals, y_vals):
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
    if beta > 0 and p < 0.05: return "H1 예비적 지지"
    elif beta > 0: return "H1 방향성 지지"
    return "H1 지지 없음"


def humor_grade(p):
    if p >= 0.65: return "high"
    elif p >= 0.50: return "medium"
    elif p >= 0.35: return "low"
    return "very_low"


def main():
    np.random.seed(RANDOM_SEED)
    raw_md5_before = md5_file(RAW_SRC)

    # ── 1. review sheet 로드 (labels + text)
    print("[1] Review sheet 로드 중...")
    with open(REVIEW_CSV, newline="", encoding="utf-8") as f:
        review_rows = list(csv.DictReader(f))
    assert len(review_rows) == 978, f"review sheet 행 수 오류: {len(review_rows)}"

    # ── 2. human label 추출 (human_coded=1, human_humor_binary in 0/1)
    print("[2] Human label 추출 중...")
    labeled = []
    n_humor = n_nonhumor = n_missing = 0
    for r in review_rows:
        if r.get("human_coded") != "1":
            continue
        bin_val = r.get("human_humor_binary", "").strip()
        if bin_val == "1":
            n_humor += 1
        elif bin_val == "0":
            n_nonhumor += 1
        else:
            n_missing += 1
            continue
        labeled.append({
            "id":                 r["id"],
            "text":               r.get("text", ""),
            "clean_input":        preprocess(r.get("text", "")),
            "human_humor_binary": int(bin_val),
            "human_humor_label":  r.get("human_humor_label", ""),
            "human_type":         r.get("human_type", ""),
        })

    n_labeled = len(labeled)
    print(f"  human_coded=1 합계: {n_humor+n_nonhumor+n_missing}건  "
          f"사용(label 있음): {n_labeled}건  "
          f"(humor={n_humor}, non_humor={n_nonhumor}, 결측제외={n_missing})")

    # ── 3. full dataset 로드 (engagement DV용)
    print("[3] 전체 978건 데이터 로드 중 (engagement DV용)...")
    with open(FULL_CSV, newline="", encoding="utf-8") as f:
        full_rows = list(csv.DictReader(f))
    assert len(full_rows) == 978
    full_index = {str(r["id"]): r for r in full_rows}

    # ── 4. 파이프라인 정의
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

    X_texts = [r["clean_input"]        for r in labeled]
    y_labs  = [r["human_humor_binary"] for r in labeled]
    n_pos, n_neg = sum(y_labs), n_labeled - sum(y_labs)

    # ── 5. Cross-validation
    min_class = min(n_pos, n_neg)
    n_splits  = 5 if min_class >= 5 else (3 if min_class >= 3 else None)
    if n_splits is None:
        print("[FAIL] 클래스 수 부족 — CV 불가", file=sys.stderr); sys.exit(1)

    print(f"[4] StratifiedKFold CV (k={n_splits}) 실행 중...")
    cv = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=RANDOM_SEED)
    cv_res = cross_validate(
        pipe, X_texts, y_labs, cv=cv,
        scoring=["accuracy", "precision", "recall", "f1",
                 "roc_auc", "balanced_accuracy"],
        error_score="raise",
    )
    cv_m = {k.replace("test_", ""): v for k, v in cv_res.items() if k.startswith("test_")}
    for k, v in cv_m.items():
        print(f"  {k}: mean={v.mean():.4f}  std={v.std():.4f}")

    val_rows = [{"fold": i+1, **{k: "%.4f" % v[i] for k, v in cv_m.items()}}
                for i in range(n_splits)]
    val_rows += [{"fold": "mean", **{k: "%.4f" % v.mean() for k, v in cv_m.items()}},
                 {"fold": "std",  **{k: "%.4f" % v.std()  for k, v in cv_m.items()}}]
    val_cols = ["fold"] + list(cv_m.keys())
    with open(OUT_VAL, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=val_cols)
        w.writeheader(); w.writerows(val_rows)

    # ── 6. OOF 예측 + error audit
    print("[5] OOF 예측 중...")
    oof_probs = cross_val_predict(pipe, X_texts, y_labs, cv=cv, method="predict_proba")

    pipe_tmp = Pipeline([
        ("tfidf", TfidfVectorizer(lowercase=True, ngram_range=(1,2),
                                   min_df=1, max_df=0.95, sublinear_tf=True)),
        ("clf",   LogisticRegression(class_weight="balanced", solver="liblinear",
                                      max_iter=1000, random_state=RANDOM_SEED)),
    ])
    pipe_tmp.fit(X_texts, y_labs)
    classes = list(pipe_tmp.named_steps["clf"].classes_)
    pos_idx = classes.index(1) if 1 in classes else 1

    oof_p    = oof_probs[:, pos_idx]
    oof_pred = (oof_p >= 0.5).astype(int)

    err_map = {(1,1):"true_positive",(0,0):"true_negative",
               (0,1):"false_positive",(1,0):"false_negative"}
    error_rows = []
    for i, rec in enumerate(labeled):
        y_true = rec["human_humor_binary"]
        y_hat  = int(oof_pred[i])
        prob   = float(oof_p[i])
        raw    = full_index.get(rec["id"], {})
        error_rows.append({
            "id":                          rec["id"],
            "tweet_url":                   raw.get("tweet_url", ""),
            "text":                        rec["text"],
            "human_humor_binary":          y_true,
            "oof_p_humor":                 "%.6f" % prob,
            "oof_pred_humor":              y_hat,
            "error_type":                  err_map.get((y_true, y_hat), "unknown"),
            "human_humor_label":           rec["human_humor_label"],
            "human_type":                  rec["human_type"],
        })

    err_counts = {}
    for r in error_rows:
        err_counts[r["error_type"]] = err_counts.get(r["error_type"], 0) + 1
    print(f"  OOF 오류: {err_counts}")

    audit_cols = ["id","tweet_url","text","human_humor_binary",
                  "oof_p_humor","oof_pred_humor","error_type",
                  "human_humor_label","human_type"]
    with open(OUT_AUDIT, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=audit_cols, quoting=csv.QUOTE_ALL)
        w.writeheader(); w.writerows(error_rows)

    # ── 7. 전체 모델 학습 → 978건 확장 예측
    print("[6] 전체 모델 학습 → 978건 확장 예측 중...")
    pipe.fit(X_texts, y_labs)

    review_id_order = [r["id"] for r in review_rows]
    all_texts = [preprocess(r.get("text", "")) for r in review_rows]
    all_proba = pipe.predict_proba(all_texts)
    all_p     = [float(pr[pos_idx]) for pr in all_proba]
    pred_050  = [1 if p >= 0.5 else 0 for p in all_p]
    lp_new    = [math.log1p(p) for p in all_p]

    p_by_id = {review_id_order[i]: all_p[i] for i in range(978)}

    n_ge050  = sum(1 for p in all_p if p >= 0.5)
    hs_vals  = [safe_float(full_index.get(r["id"], {}).get("humor_score", 0))  for r in review_rows]
    pml_vals = [safe_float(full_index.get(r["id"], {}).get("p_humor_ml", 0))   for r in review_rows]
    corr_hs  = pearson_r(all_p, hs_vals)
    corr_pml = pearson_r(all_p, pml_vals)
    print(f"  mean={sum(all_p)/978:.4f}  >=0.5: {n_ge050} ({n_ge050/978*100:.1f}%)")
    print(f"  r(humor_score)={corr_hs:.4f}  r(p_humor_ml)={corr_pml:.4f}")

    # 전체 예측 파일 저장
    pred_cols = ["id","tweet_url","text","humor_score","p_humor_ml",
                 "p_humor_human168","pred_humor_human168_050","log1p_p_humor_human168"]
    pred_out  = []
    for i, r in enumerate(review_rows):
        fr = full_index.get(r["id"], {})
        pred_out.append({
            "id":                   r["id"],
            "tweet_url":            r.get("tweet_url",""),
            "text":                 r.get("text",""),
            "humor_score":          fr.get("humor_score",""),
            "p_humor_ml":           fr.get("p_humor_ml",""),
            "p_humor_human168":     "%.6f" % all_p[i],
            "pred_humor_human168_050": pred_050[i],
            "log1p_p_humor_human168": "%.6f" % lp_new[i],
        })
    with open(OUT_FULL, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=pred_cols, quoting=csv.QUOTE_ALL)
        w.writeheader(); w.writerows(pred_out)

    # ── 8. Review sheet 업데이트 (model_humor, p_humor, humor_grade, model_vs_human)
    print("[7] Review sheet 업데이트 중...")
    updated_rows = []
    for i, r in enumerate(review_rows):
        row = dict(r)
        p   = all_p[i]
        mb  = pred_050[i]
        row["model_humor"]  = mb
        row["p_humor"]      = "%.4f" % p
        row["humor_grade"]  = humor_grade(p)
        # model_vs_human 재계산
        hb = row.get("human_humor_binary", "").strip()
        if row.get("human_coded") != "1":
            row["model_vs_human"] = "no_human"
        elif hb == "":
            row["model_vs_human"] = "label_missing"
        elif str(mb) == hb:
            row["model_vs_human"] = "match"
        else:
            row["model_vs_human"] = "mismatch"
        updated_rows.append(row)

    review_cols = list(review_rows[0].keys())
    with open(REVIEW_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=review_cols, quoting=csv.QUOTE_ALL)
        w.writeheader(); w.writerows(updated_rows)
    print(f"  → {REVIEW_CSV}")

    # match/mismatch 집계
    match_cnt    = sum(1 for r in updated_rows if r["model_vs_human"] == "match")
    mismatch_cnt = sum(1 for r in updated_rows if r["model_vs_human"] == "mismatch")
    print(f"  model_vs_human: match={match_cnt}, mismatch={mismatch_cnt}")

    # ── 9. H1 단순 OLS
    print("[8] H1 단순 OLS 실행 중...")
    dv_specs = {k: [] for k in [
        "log1p_engagement_total","log1p_engagement_fav_rt",
        "log1p_favorite_count","log1p_retweet_count",
        "log1p_reply_count","log1p_quote_count","log1p_bookmark_count"]}
    for r in review_rows:
        fr  = full_index.get(r["id"], {})
        fav = safe_int(fr.get("favorite_count",0))
        rt  = safe_int(fr.get("retweet_count",0))
        rep = safe_int(fr.get("reply_count",0))
        qt  = safe_int(fr.get("quote_count",0))
        bm  = safe_int(fr.get("bookmark_count",0))
        dv_specs["log1p_engagement_total"].append(math.log1p(fav+rt+rep+qt+bm))
        dv_specs["log1p_engagement_fav_rt"].append(math.log1p(fav+rt))
        dv_specs["log1p_favorite_count"].append(math.log1p(fav))
        dv_specs["log1p_retweet_count"].append(math.log1p(rt))
        dv_specs["log1p_reply_count"].append(math.log1p(rep))
        dv_specs["log1p_quote_count"].append(math.log1p(qt))
        dv_specs["log1p_bookmark_count"].append(math.log1p(bm))

    h1_rows = []
    main_res = None
    for dv_name, y_dv in dv_specs.items():
        res = run_ols(lp_new, y_dv)
        print(f"  {dv_name}: β={res['beta']:.4f}  p={res['p']:.4f}  R²={res['r2']:.4f}  → {h1_label(res['beta'],res['p'])}")
        h1_rows.append({
            "dv":                     dv_name,
            "n_obs":                  res["n_obs"],
            "iv":                     "log1p_p_humor_human168",
            "beta":                   "%.6f" % res["beta"],
            "se":                     "%.6f" % res["se"],
            "t_value":                "%.4f"  % res["t"],
            "p_value":                "%.6f" % res["p"],
            "ci_lower_95":            "%.6f" % res["ci_lo"],
            "ci_upper_95":            "%.6f" % res["ci_hi"],
            "r_squared":              "%.6f" % res["r2"],
            "h1_interpretation":      h1_label(res["beta"], res["p"]),
        })
        if dv_name == "log1p_engagement_total":
            main_res = res

    h1_cols = ["dv","n_obs","iv","beta","se","t_value","p_value",
               "ci_lower_95","ci_upper_95","r_squared","h1_interpretation"]
    with open(OUT_H1, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=h1_cols)
        w.writeheader(); w.writerows(h1_rows)

    # ── 10. Diagnostics
    diag_entries = [
        ("seed_label_source",           "wendys_humor_review_sheet.csv"),
        ("n_human_coded_total",         n_humor + n_nonhumor + n_missing),
        ("n_labeled_used",              n_labeled),
        ("n_humor",                     n_humor),
        ("n_nonhumor",                  n_nonhumor),
        ("n_missing_excluded",          n_missing),
        ("n_splits",                    n_splits),
        ("cv_accuracy_mean",            "%.4f" % cv_m["accuracy"].mean()),
        ("cv_f1_mean",                  "%.4f" % cv_m["f1"].mean()),
        ("cv_roc_auc_mean",             "%.4f" % cv_m["roc_auc"].mean()),
        ("p_humor_mean",                "%.4f" % (sum(all_p)/978)),
        ("p_humor_median",              "%.4f" % median_of(all_p)),
        ("p_humor_ge_050_count",        n_ge050),
        ("p_humor_ge_050_share",        "%.4f" % (n_ge050/978)),
        ("corr_humor_score",            "%.4f" % corr_hs),
        ("corr_p_humor_ml",             "%.4f" % corr_pml),
        ("match_count",                 match_cnt),
        ("mismatch_count",              mismatch_cnt),
    ]
    with open(OUT_DIAG, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(["metric","value"]); w.writerows(diag_entries)

    # ── 11. 한국어 요약 마크다운
    _write_summary(n_labeled, n_humor, n_nonhumor, n_missing,
                   n_splits, cv_m, err_counts,
                   all_p, hs_vals, pml_vals, n_ge050, corr_hs, corr_pml,
                   h1_rows, main_res, match_cnt, mismatch_cnt)

    # ── 12. 검증
    raw_md5_after = md5_file(RAW_SRC)
    checks = [
        (REVIEW_CSV.exists(),          "review sheet 존재"),
        (n_labeled >= 100,             f"human label >= 100건 (실제: {n_labeled})"),
        (set(y_labs) == {0, 1},        "0/1 클래스 모두 존재"),
        (n_humor > 0 and n_nonhumor > 0, "유머·비유머 모두 존재"),
        (len(all_p) == 978,            f"예측 978건 생성 (실제: {len(all_p)})"),
        (all(0.0 <= p <= 1.0 for p in all_p), "p_humor ∈ [0,1]"),
        (OUT_FULL.exists(),            "full predictions 파일 존재"),
        (OUT_VAL.exists(),             "CV 결과 파일 존재"),
        (OUT_H1.exists(),              "H1 OLS 결과 파일 존재"),
        (OUT_SUMMARY.exists(),         "요약 마크다운 존재"),
        (raw_md5_before == raw_md5_after, "posts.json 미변경"),
    ]
    print("\n=== 검증 ===")
    all_pass = True
    for i, (ok, desc) in enumerate(checks, 1):
        s = "PASS" if ok else "FAIL"
        if not ok: all_pass = False
        print(f"  [{s}] {i:2d}. {desc}")
    if not all_pass:
        raise RuntimeError("검증 실패 — 커밋하지 않음")
    print("\n완료.")


def _write_summary(n_used, n_humor, n_nonhumor, n_missing,
                   n_splits, cv_m, err_counts,
                   all_p, hs_vals, pml_vals, n_ge050, corr_hs, corr_pml,
                   h1_rows, mr, match_cnt, mismatch_cnt):
    n_all = 978

    def cv_row(k):
        return f"| {k} | {cv_m[k].mean():.4f} | {cv_m[k].std():.4f} |"

    h1_table = "| 종속변수 | β | p | R² | H1 해석 |\n|---|---|---|---|---|\n"
    for r in h1_rows:
        h1_table += f"| `{r['dv']}` | {r['beta']} | {r['p_value']} | {r['r_squared']} | {r['h1_interpretation']} |\n"

    tp = err_counts.get("true_positive", 0)
    tn = err_counts.get("true_negative", 0)
    fp = err_counts.get("false_positive", 0)
    fn = err_counts.get("false_negative", 0)

    def h1_label(beta, p):
        b = float(beta); pv = float(p)
        if b > 0 and pv < 0.05: return "H1 예비적 지지"
        elif b > 0: return "H1 방향성 지지"
        return "H1 지지 없음"

    summary = f"""# Wendy's human-coded 168건 seed label 기반 TF-IDF LogReg 유머 분류 요약 (v2)

생성일시: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}

> 기존 69건(원본 human labels) + 추가 99건(human_coded_check)을 통합한 **168건**을
> seed label로 재학습한 결과이다.

---

## 1. 작업 목적

기존 69건에서 168건으로 확대된 human-coded seed label을 사용하여
TF-IDF + Logistic Regression 분류 모델을 재학습하고,
전체 978건 유머 확률(`p_humor_human168`)을 재예측한다.
`wendys_humor_review_sheet.csv`의 `model_humor`, `p_humor`, `humor_grade` 컬럼을 업데이트한다.

---

## 2. Human label 현황

| 항목 | 건수 |
|------|------|
| 학습에 사용된 레이블 | {n_used} |
| humor = 1 | {n_humor} |
| non_humor = 0 | {n_nonhumor} |
| 결측 제외 | {n_missing} |

---

## 3. 모델 구조

```
TfidfVectorizer(ngram_range=(1,2), min_df=1, max_df=0.95, sublinear_tf=True)
→ LogisticRegression(class_weight="balanced", solver="liblinear")
```

engagement 변수는 학습에 사용하지 않음.

---

## 4. Cross-validation 결과 (StratifiedKFold, k={n_splits})

| 지표 | 평균 | 표준편차 |
|------|------|---------|
{cv_row('accuracy')}
{cv_row('precision')}
{cv_row('recall')}
{cv_row('f1')}
{cv_row('roc_auc')}
{cv_row('balanced_accuracy')}

---

## 5. 오류 분석 (Out-of-fold, threshold=0.5)

| 유형 | 건수 |
|------|------|
| True Positive  | {tp} |
| True Negative  | {tn} |
| False Positive | {fp} |
| False Negative | {fn} |
| 합계 | {tp+tn+fp+fn} |

---

## 6. 978건 전체 예측 결과

| 지표 | 값 |
|------|-----|
| 최솟값 | {min(all_p):.4f} |
| 평균 | {sum(all_p)/n_all:.4f} |
| 중앙값 | {median_of(all_p):.4f} |
| 최댓값 | {max(all_p):.4f} |
| >= 0.5 (유머 예측) | {n_ge050}건 ({n_ge050/n_all*100:.1f}%) |

---

## 7. 기존 점수 비교

| 상관 | 값 |
|------|-----|
| `p_humor_human168` vs `humor_score` | {corr_hs:.4f} |
| `p_humor_human168` vs `p_humor_ml`  | {corr_pml:.4f} |

---

## 8. Model vs Human 일치 (168건 기준)

| 결과 | 건수 |
|------|------|
| match | {match_cnt} |
| mismatch | {mismatch_cnt} |
| 정확도 (match / 유효라벨) | {match_cnt/(match_cnt+mismatch_cnt)*100:.1f}% |

---

## 9. H1 단순 OLS 결과

IV: `log1p_p_humor_human168`

{h1_table}

주요 결과 (`log1p_engagement_total`):
β = {mr['beta']:.6f}, SE = {mr['se']:.6f}, p = {mr['p']:.4f}, R² = {mr['r2']:.6f}

**{h1_label(str(mr['beta']), str(mr['p']))}**

---

## 10. 한계

- 168건 human-coded sample 기반 — exploratory calibration
- 단일 코더, inter-rater reliability 미검증
- 통제변수 없음 — 관측적 연관성 분석
"""
    with open(OUT_SUMMARY, "w", encoding="utf-8") as f:
        f.write(summary)


if __name__ == "__main__":
    main()
