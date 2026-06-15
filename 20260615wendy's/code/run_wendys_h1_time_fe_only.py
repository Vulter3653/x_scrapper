"""
run_wendys_h1_time_fe_only.py

목적: H1 분석 — baseline에 시간 고정효과(created_year, created_month, created_hour)를
      순차적으로 추가하여 유머 여부와 post-level engagement 관계 확인.

이번 작업은 H1에만 한정. H2/H3 수행 없음. 새 변수 생성 없음.

모형:
  M1: Y ~ humor (baseline)
  M2: Y ~ humor + year_FE
  M3: Y ~ humor + year_FE + month_FE
  M4: Y ~ humor + year_FE + month_FE + hour_FE

시간 FE 처리: created_year, created_month, created_hour 모두 categorical dummy.
SE: conventional (MSE-based). p_value: 양측 t-test.
"""

import csv
import math
import os
import hashlib

import numpy as np
from scipy import stats

# ─── 경로 ────────────────────────────────────────────────────────────────────
BASE       = "20260615wendy's"
DATA_DIR   = os.path.join(BASE, "data")
RESULT_DIR = os.path.join(BASE, "result")
POSTS_JSON = os.path.join("data", "wendys", "posts.json")

PRED_FILE = os.path.join(RESULT_DIR, "wendys_final_humor_presence_full_predictions.csv")
H3_FILE   = os.path.join(DATA_DIR,   "wendys_h3_aggressive_vs_other_intensity_dataset.csv")

DATASET_OUT     = os.path.join(DATA_DIR,   "wendys_h1_time_fe_only_dataset.csv")
PRIMARY_RES_OUT = os.path.join(RESULT_DIR, "wendys_h1_time_fe_primary_human_results.csv")
FULLBIN_RES_OUT = os.path.join(RESULT_DIR, "wendys_h1_time_fe_fullsample_binary_results.csv")
PROB_RES_OUT    = os.path.join(RESULT_DIR, "wendys_h1_time_fe_probability_results.csv")
DIAG_OUT        = os.path.join(RESULT_DIR, "wendys_h1_time_fe_diagnostics.csv")
SUMMARY_OUT     = os.path.join(RESULT_DIR, "wendys_h1_time_fe_summary.md")

DVS = [
    "log1p_engagement_total",
    "log1p_engagement_favorite_retweet",
    "log1p_favorite_count",
    "log1p_retweet_count",
    "log1p_reply_count",
    "log1p_quote_count",
    "log1p_bookmark_count",
]

# ─── 유틸 ────────────────────────────────────────────────────────────────────
def safe_float(v):
    if v in ("", None, "nan"): return None
    if isinstance(v, str):
        if v.lower() == "true":  return 1.0
        if v.lower() == "false": return 0.0
    try: return float(v)
    except: return None

def fmt4(v):
    if v is None or (isinstance(v, float) and math.isnan(v)): return "nan"
    if isinstance(v, float) and math.isinf(v): return "inf"
    return str(round(float(v), 4))

def star(p):
    if math.isnan(p): return ""
    if p < 0.001: return "***"
    if p < 0.01:  return "**"
    if p < 0.05:  return "*"
    if p < 0.10:  return "†"
    return ""

def interp_flag(beta, p):
    if math.isnan(beta) or math.isnan(p): return "unknown"
    if beta > 0 and p < 0.05:  return "supports_H1"
    if beta > 0 and p < 0.10:  return "weak_support"
    if beta > 0:               return "positive_not_significant"
    return "not_support"

def sorted_unique(rows, col, as_int=False):
    vals = sorted(set(r[col] for r in rows), key=lambda x: int(x) if as_int else x)
    return vals

# ─── 0. posts.json 보호 ────────────────────────────────────────────────────
print("[0] posts.json 보호 확인")
hash_before = None
try:
    with open(POSTS_JSON, "rb") as f:
        hash_before = hashlib.md5(f.read()).hexdigest()
    print(f"  md5: {hash_before}")
except FileNotFoundError:
    print("  posts.json 없음 (정상)")

# ─── 1. 데이터 로드 및 병합 ───────────────────────────────────────────────
print("[1] 데이터 로드 및 병합")
with open(PRED_FILE, newline="", encoding="utf-8") as f:
    pred_rows = list(csv.DictReader(f))
with open(H3_FILE, newline="", encoding="utf-8") as f:
    h3_list = list(csv.DictReader(f))
    h3_map  = {r["id"]: r for r in h3_list}

# h3 기준 + pred 컬럼 덮어쓰기
merged = []
for pr in pred_rows:
    base = dict(h3_map[pr["id"]])
    for k, v in pr.items():
        base[k] = v
    merged.append(base)

assert len(merged) == 978, f"전체 n 오류: {len(merged)}"
primary = [r for r in merged if r.get("final_humor_label_available") == "1"]
assert len(primary) == 597, f"primary n 오류: {len(primary)}"
print(f"  전체 n={len(merged)}, primary n={len(primary)}")

# ─── 2. Dataset 저장 ─────────────────────────────────────────────────────
print("[2] Dataset 저장")
all_fields = list(merged[0].keys())
with open(DATASET_OUT, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=all_fields, extrasaction="ignore")
    w.writeheader()
    w.writerows(merged)
print(f"  → {DATASET_OUT}")

# ─── 3. OLS 인프라 ──────────────────────────────────────────────────────
def make_design_matrix(rows, iv_col, year_dummies, month_dummies, hour_dummies):
    """Design matrix: constant + IV + time FE dummies."""
    n = len(rows)
    cols, labels = [np.ones(n)], ["_const"]

    cols.append(np.array([safe_float(r.get(iv_col, "")) or 0.0 for r in rows]))
    labels.append(iv_col)

    for y in (year_dummies or []):
        cols.append(np.array([1.0 if r["created_year"] == y else 0.0 for r in rows]))
        labels.append(f"year_{y}")

    for m in (month_dummies or []):
        cols.append(np.array([1.0 if r["created_month"] == m else 0.0 for r in rows]))
        labels.append(f"month_{m}")

    for h in (hour_dummies or []):
        cols.append(np.array([1.0 if r["created_hour"] == h else 0.0 for r in rows]))
        labels.append(f"hour_{h}")

    return np.column_stack(cols), labels

def ols_estimate(X, y):
    """OLS 추정. conventional SE 기반 t-test. None 반환 시 rank deficient."""
    n, p = X.shape
    XtX = X.T @ X
    if np.linalg.matrix_rank(XtX) < p:
        return None
    try:
        XtXinv = np.linalg.inv(XtX)
    except np.linalg.LinAlgError:
        return None

    coef  = XtXinv @ (X.T @ y)
    resid = y - X @ coef
    sse   = float(resid @ resid)
    sst   = float(np.sum((y - y.mean()) ** 2))
    df_r  = n - p
    mse   = sse / df_r if df_r > 0 else float("nan")
    r2    = 1 - sse / sst if sst > 0 else float("nan")
    adj_r2 = 1 - (1 - r2) * (n - 1) / df_r if df_r > 0 and sst > 0 else float("nan")
    aic   = n * math.log(sse / n) + 2 * p if sse > 0 else float("nan")
    bic   = n * math.log(sse / n) + p * math.log(n) if sse > 0 else float("nan")

    se_arr = np.sqrt(np.maximum(np.diag(mse * XtXinv), 0.0))
    t_arr  = np.where(se_arr > 0, coef / se_arr, float("nan"))
    p_arr  = np.array([
        2 * float(stats.t.sf(abs(t_arr[i]), df=df_r)) if df_r > 0 and not math.isnan(t_arr[i]) else float("nan")
        for i in range(p)
    ])
    return dict(coef=coef, se=se_arr, t=t_arr, pval=p_arr,
                r2=r2, adj_r2=adj_r2, aic=aic, bic=bic, df_r=df_r, n=n)

# ─── 4. 회귀 실행 함수 ───────────────────────────────────────────────────
RESULT_FIELDS = [
    "sample_type", "model_name", "dv", "iv", "n",
    "coefficient", "p_value",
    "r_squared", "adj_r_squared", "aic", "bic",
    "included_time_fe", "interpretation_flag",
]

def run_h1_models(rows, iv_col, sample_type):
    """4 models × 7 DVs. 반환: list of dicts."""
    all_years  = sorted_unique(rows, "created_year")
    all_months = sorted_unique(rows, "created_month", as_int=True)
    all_hours  = sorted_unique(rows, "created_hour",  as_int=True)

    base_year  = all_years[0]
    base_month = all_months[0]
    base_hour  = all_hours[0]

    year_dummies  = [y for y in all_years  if y != base_year]
    month_dummies = [m for m in all_months if m != base_month]
    hour_dummies  = [h for h in all_hours  if h != base_hour]

    print(f"  [{sample_type}]")
    print(f"    base: year={base_year}, month={base_month}, hour={base_hour}")
    print(f"    year_dummies({len(year_dummies)}): {year_dummies}")
    print(f"    month_dummies({len(month_dummies)}), hour_dummies({len(hour_dummies)})")

    model_specs = [
        ("M1_baseline",           None,         None,          None),
        ("M2_year_fe",            year_dummies, None,          None),
        ("M3_year_month_fe",      year_dummies, month_dummies, None),
        ("M4_year_month_hour_fe", year_dummies, month_dummies, hour_dummies),
    ]

    results = []
    for dv in DVS:
        y = np.array([safe_float(r.get(dv, "")) or 0.0 for r in rows])
        for mname, yd, md, hd in model_specs:
            fe_parts = (["year_FE"] if yd else []) + (["month_FE"] if md else []) + (["hour_FE"] if hd else [])
            fe_desc  = "+".join(fe_parts) if fe_parts else "none"

            X, labels = make_design_matrix(rows, iv_col, yd, md, hd)
            fit = ols_estimate(X, y)

            if fit is None:
                results.append(dict(zip(RESULT_FIELDS, [
                    sample_type, mname, dv, iv_col, len(rows),
                    "RANK_DEFICIENT", "FAIL",
                    "FAIL", "FAIL", "FAIL", "FAIL",
                    fe_desc, "FAIL",
                ])))
                continue

            iv_idx = labels.index(iv_col)
            beta = float(fit["coef"][iv_idx])
            pval = float(fit["pval"][iv_idx])

            results.append({
                "sample_type":       sample_type,
                "model_name":        mname,
                "dv":                dv,
                "iv":                iv_col,
                "n":                 fit["n"],
                "coefficient":       fmt4(beta),
                "p_value":           fmt4(pval),
                "r_squared":         fmt4(fit["r2"]),
                "adj_r_squared":     fmt4(fit["adj_r2"]),
                "aic":               fmt4(fit["aic"]),
                "bic":               fmt4(fit["bic"]),
                "included_time_fe":  fe_desc,
                "interpretation_flag": interp_flag(beta, pval),
            })
    return results

# ─── 5. 분석 실행 ───────────────────────────────────────────────────────────
print("[3] Primary human-labeled H1 (n=597, IV=final_humor_binary)")
primary_results = run_h1_models(primary, "final_humor_binary", "primary_human_n597")

print("[4] Full-sample binary H1 (n=978, IV=pred_humor_final_050)")
fullbin_results = run_h1_models(merged, "pred_humor_final_050", "fullsample_binary_n978")

print("[5] Probability-based H1 (n=978, IV=p_humor_final_tfidf_logreg)")
prob_results = run_h1_models(merged, "p_humor_final_tfidf_logreg", "probability_n978")

# ─── 6. 결과 저장 ───────────────────────────────────────────────────────────
print("[6] 결과 저장")
for path, res in [
    (PRIMARY_RES_OUT, primary_results),
    (FULLBIN_RES_OUT, fullbin_results),
    (PROB_RES_OUT,    prob_results),
]:
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=RESULT_FIELDS)
        w.writeheader()
        w.writerows(res)
    print(f"  → {path} ({len(res)}건)")

# ─── 7. 진단 ────────────────────────────────────────────────────────────────
print("[7] Diagnostics")

posts_json_modified = False
if hash_before:
    try:
        with open(POSTS_JSON, "rb") as f:
            h_now = hashlib.md5(f.read()).hexdigest()
        posts_json_modified = (h_now != hash_before)
    except FileNotFoundError:
        pass

def get_r(results, model, dv):
    return next((r for r in results if r["model_name"] == model and r["dv"] == dv), {})

pr_m1 = get_r(primary_results, "M1_baseline",           "log1p_engagement_total")
pr_m4 = get_r(primary_results, "M4_year_month_hour_fe", "log1p_engagement_total")

diag_rows = [
    ("primary_n",                    len(primary)),
    ("full_n",                       len(merged)),
    ("primary_humor_1",              sum(1 for r in primary if r.get("final_humor_binary")=="1")),
    ("primary_humor_0",              sum(1 for r in primary if r.get("final_humor_binary")=="0")),
    ("full_predicted_humor_1",       sum(1 for r in merged if r.get("pred_humor_final_050")=="1")),
    ("full_predicted_humor_0",       sum(1 for r in merged if r.get("pred_humor_final_050")=="0")),
    ("primary_year_unique",          len(sorted_unique(primary, "created_year"))),
    ("primary_month_unique",         len(sorted_unique(primary, "created_month", as_int=True))),
    ("primary_hour_unique",          len(sorted_unique(primary, "created_hour",  as_int=True))),
    ("full_year_unique",             len(sorted_unique(merged,  "created_year"))),
    ("full_month_unique",            len(sorted_unique(merged,  "created_month", as_int=True))),
    ("full_hour_unique",             len(sorted_unique(merged,  "created_hour",  as_int=True))),
    ("sample_reduced_by_missing",    "no"),
    ("rank_deficient_any",           any(r.get("interpretation_flag")=="FAIL"
                                         for r in primary_results+fullbin_results+prob_results)),
    ("se_type",                      "conventional_MSE"),
    ("view_count_used",              False),
    ("post_format_vars_used",        False),
    ("posting_intensity_used",       False),
    ("year_quarter_fe_used",         False),
    ("day_of_week_created",          False),
    ("H2_performed",                 False),
    ("H3_performed",                 False),
    ("new_vars_created",             False),
    ("primary_M1_beta",              pr_m1.get("coefficient","n/a")),
    ("primary_M1_p_value",           pr_m1.get("p_value","n/a")),
    ("primary_M4_beta",              pr_m4.get("coefficient","n/a")),
    ("primary_M4_p_value",           pr_m4.get("p_value","n/a")),
    ("primary_M4_flag",              pr_m4.get("interpretation_flag","n/a")),
    ("original_posts_json_modified", posts_json_modified),
]

with open(DIAG_OUT, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=["metric", "value"])
    w.writeheader()
    for k, v in diag_rows:
        w.writerow({"metric": k, "value": v})
print(f"  → {DIAG_OUT}")

# ─── 8. Summary Markdown ─────────────────────────────────────────────────────
print("[8] Summary 작성")

def make_table_by_model(results, dv="log1p_engagement_total"):
    rows_dv = [r for r in results if r["dv"] == dv]
    lines = [
        "| model | β | p_value | sig | R² | adj_R² | flag |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in rows_dv:
        pv = r["p_value"]
        sig = star(float(pv)) if pv not in ("FAIL", "nan") else ""
        lines.append(
            f"| {r['model_name']} | {r['coefficient']} | {r['p_value']} "
            f"| {sig} | {r['r_squared']} | {r['adj_r_squared']} | {r['interpretation_flag']} |"
        )
    return "\n".join(lines)

def make_table_by_dv(results, model="M4_year_month_hour_fe"):
    rows_m = [r for r in results if r["model_name"] == model]
    lines = [
        "| DV | β | p_value | sig | R² | flag |",
        "|---|---|---|---|---|---|",
    ]
    for r in rows_m:
        pv = r["p_value"]
        sig = star(float(pv)) if pv not in ("FAIL", "nan") else ""
        lines.append(
            f"| {r['dv']} | {r['coefficient']} | {r['p_value']} "
            f"| {sig} | {r['r_squared']} | {r['interpretation_flag']} |"
        )
    return "\n".join(lines)

def change_table(results, dv="log1p_engagement_total"):
    lines = [
        "| model | β | p_value | R² | adj_R² | 포함 FE |",
        "|---|---|---|---|---|---|",
    ]
    for mname in ["M1_baseline","M2_year_fe","M3_year_month_fe","M4_year_month_hour_fe"]:
        r = get_r(results, mname, dv)
        if not r: continue
        lines.append(
            f"| {r['model_name']} | {r['coefficient']} | {r['p_value']} "
            f"| {r['r_squared']} | {r['adj_r_squared']} | {r['included_time_fe']} |"
        )
    return "\n".join(lines)

primary_year_base  = sorted_unique(primary, "created_year")[0]
primary_month_base = sorted_unique(primary, "created_month", as_int=True)[0]
primary_hour_base  = sorted_unique(primary, "created_hour",  as_int=True)[0]
n_year_dum  = len(sorted_unique(primary, "created_year")) - 1
n_month_dum = len(sorted_unique(primary, "created_month", as_int=True)) - 1
n_hour_dum  = len(sorted_unique(primary, "created_hour",  as_int=True)) - 1

summary_md = f"""# Wendy's H1 Time Fixed Effects Only Regression 결과

## 1. 분석 목적

유머 게시글 여부(Humor_i)와 post-level engagement 간 관계가 시간 효과(연도·월·시간대)를 통제한 뒤에도 유지되는지 확인한다. Baseline 모형에 시간 고정효과를 순차적으로 추가하여 β 계수의 변화를 추적한다. 이번 작업은 H1에만 한정하며, H2와 H3는 수행하지 않았다.

---

## 2. 사용한 파일

| 파일 | 역할 |
|---|---|
| wendys_final_humor_presence_full_predictions.csv | IV (final_humor_binary, pred_humor_final_050, p_humor_final_tfidf_logreg) |
| wendys_h3_aggressive_vs_other_intensity_dataset.csv | DV (log1p_*), 시간 변수 (created_year/month/hour) |

---

## 3. 원본 posts.json 변경 없음 확인

data/wendys/posts.json 변경 여부: **{posts_json_modified}**

---

## 4. 새 변수 생성 없음 확인

이번 작업에서는 새로운 변수를 생성하지 않았다. 기존 파일에 존재하는 컬럼만 사용하였다. day_of_week 생성 없음. text_length 등 포맷 변수 미사용. quarter_total_posts, month_total_posts 미사용. log1p_view_count 미사용. year_quarter FE 미사용.

---

## 5. 표본 구성

| 항목 | 값 |
|---|---|
| Primary sample | final_humor_label_available=1, n={len(primary)} |
| Primary humor=1 | {sum(1 for r in primary if r.get("final_humor_binary")=="1")} |
| Primary humor=0 | {sum(1 for r in primary if r.get("final_humor_binary")=="0")} |
| Full sample | n={len(merged)} |
| Full predicted humor=1 (pred_humor_final_050) | {sum(1 for r in merged if r.get("pred_humor_final_050")=="1")} |
| Full predicted humor=0 | {sum(1 for r in merged if r.get("pred_humor_final_050")=="0")} |
| 결측으로 인한 sample 감소 | 없음 |

---

## 6. 사용한 시간 고정효과

| 변수 | 처리 방식 | primary 기준 범주 | primary 더미 수 |
|---|---|---|---|
| created_year | categorical FE (더미) | {primary_year_base} | {n_year_dum} |
| created_month | categorical FE (더미) | {primary_month_base} | {n_month_dum} |
| created_hour | categorical FE (더미) | {primary_hour_base} | {n_hour_dum} |
| year_quarter FE | 미사용 | — | — |
| day_of_week | 존재하지 않음, 생성 안 함 | — | — |

기준 범주는 각 변수 내 최솟값(가장 이른 연도·월·시간)으로 자동 설정하였다.

---

## 7. Primary Human-labeled H1 결과

**표본: n={len(primary)}, IV=final_humor_binary**

### 7-1. Primary DV: log1p_engagement_total (모형별)

{make_table_by_model(primary_results, "log1p_engagement_total")}

* p<.05, ** p<.01, *** p<.001, † p<.10 (conventional SE 기준)

### 7-2. M4 (year+month+hour FE) 기준 전체 DV

{make_table_by_dv(primary_results, "M4_year_month_hour_fe")}

---

## 8. Supplemental Full-sample Binary H1 결과

**표본: n={len(merged)}, IV=pred_humor_final_050**

### 8-1. Primary DV: log1p_engagement_total (모형별)

{make_table_by_model(fullbin_results, "log1p_engagement_total")}

### 8-2. M4 기준 전체 DV

{make_table_by_dv(fullbin_results, "M4_year_month_hour_fe")}

---

## 9. Probability-based Supplemental H1 결과

**표본: n={len(merged)}, IV=p_humor_final_tfidf_logreg (0~1 확률값)**

### 9-1. Primary DV: log1p_engagement_total (모형별)

{make_table_by_model(prob_results, "log1p_engagement_total")}

### 9-2. M4 기준 전체 DV

{make_table_by_dv(prob_results, "M4_year_month_hour_fe")}

---

## 10. Baseline 대비 시간 고정효과 추가 후 β 및 p-value 변화

**Primary sample, primary DV (log1p_engagement_total)**

{change_table(primary_results, "log1p_engagement_total")}

---

## 11. 최종 해석

**Primary model 결과 (M4, primary sample n={len(primary)}, conventional SE 기준):**

- IV: final_humor_binary
- DV: log1p_engagement_total
- β = {pr_m4.get("coefficient","n/a")}, p = {pr_m4.get("p_value","n/a")}
- **판정: {pr_m4.get("interpretation_flag","n/a")}**

Baseline (M1)의 β = {pr_m1.get("coefficient","n/a")} (p={pr_m1.get("p_value","n/a")})에서 시간 FE를 순차적으로 추가한 후의 변화는 위 표(섹션 10)에 정리되어 있다.

---

## 12. 인과관계 아님 — 관측적 연관성 분석

본 분석은 관측적 연관성 분석이며, 유머 게시글 여부가 engagement를 증가시켰다는 인과관계를 주장할 수 없다. 시간 고정효과는 연도·월·시간대 수준의 공통 요인을 통제하지만, 관찰되지 않은 개별 게시글의 내용 특성이나 기타 혼동 요인은 통제되지 않는다.

---

## 13. H2/H3 수행 여부

이번 작업에서는 H1 분석만 수행하였으며, H2와 H3는 수행하지 않았다.

---

## 14. 다음 단계

다음 단계에서 추가할 수 있는 변수(post format: text_length, is_quote_status 등; posting intensity: quarter_total_posts 등; log1p_view_count 등)는 사용자 승인 후 결정한다.

---

*생성일: 2026-06-15*
"""

with open(SUMMARY_OUT, "w", encoding="utf-8") as f:
    f.write(summary_md)
print(f"  → {SUMMARY_OUT}")

# ─── 9. 최종 검증 출력 ───────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("[검증 요약]")
print(f"  primary n={len(primary)}  (기대:597): {'OK' if len(primary)==597 else 'FAIL'}")
print(f"  full    n={len(merged)} (기대:978): {'OK' if len(merged)==978 else 'FAIL'}")
print(f"  posts.json 변경: {posts_json_modified} (기대:False)")
rank_fail = any(r.get("interpretation_flag") == "FAIL"
                for r in primary_results + fullbin_results + prob_results)
print(f"  rank deficient: {rank_fail} (기대:False)")
print(f"  H2/H3 수행: False")
print(f"  새 변수 생성: False")

print("\n[Primary DV log1p_engagement_total 주요 결과]")
for r in [x for x in primary_results if x["dv"] == "log1p_engagement_total"]:
    pv = r["p_value"]
    sig = star(float(pv)) if pv not in ("FAIL", "nan") else ""
    print(f"  {r['model_name']:30s} β={r['coefficient']:8s} p={r['p_value']:8s} {sig:4s} {r['interpretation_flag']}")

print("\n[Full-sample binary primary DV]")
for r in [x for x in fullbin_results if x["dv"] == "log1p_engagement_total"]:
    pv = r["p_value"]
    sig = star(float(pv)) if pv not in ("FAIL", "nan") else ""
    print(f"  {r['model_name']:30s} β={r['coefficient']:8s} p={r['p_value']:8s} {sig:4s} {r['interpretation_flag']}")

print("\n[Probability primary DV]")
for r in [x for x in prob_results if x["dv"] == "log1p_engagement_total"]:
    pv = r["p_value"]
    sig = star(float(pv)) if pv not in ("FAIL", "nan") else ""
    print(f"  {r['model_name']:30s} β={r['coefficient']:8s} p={r['p_value']:8s} {sig:4s} {r['interpretation_flag']}")
