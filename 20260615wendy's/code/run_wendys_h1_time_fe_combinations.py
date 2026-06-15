"""
run_wendys_h1_time_fe_combinations.py

목적: H1 분석에서 created_year, created_month, created_hour 시간 변수를
      1개 / 2개 조합 / 3개 전체로 나누어 8가지 모형 비교.

이번 작업은 H1에만 한정. H2/H3 수행 없음. 새 변수 생성 없음.

모형:
  M0: Y ~ humor (baseline)
  M1: Y ~ humor + year_FE
  M2: Y ~ humor + month_FE
  M3: Y ~ humor + hour_FE
  M4: Y ~ humor + year_FE + month_FE
  M5: Y ~ humor + year_FE + hour_FE
  M6: Y ~ humor + month_FE + hour_FE
  M7: Y ~ humor + year_FE + month_FE + hour_FE

시간 FE: created_year, created_month, created_hour 모두 categorical dummy.
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

DATASET_OUT     = os.path.join(DATA_DIR,   "wendys_h1_time_fe_combinations_dataset.csv")
PRIMARY_RES_OUT = os.path.join(RESULT_DIR, "wendys_h1_time_fe_combinations_primary_human_results.csv")
FULLBIN_RES_OUT = os.path.join(RESULT_DIR, "wendys_h1_time_fe_combinations_fullsample_binary_results.csv")
PROB_RES_OUT    = os.path.join(RESULT_DIR, "wendys_h1_time_fe_combinations_probability_results.csv")
DIAG_OUT        = os.path.join(RESULT_DIR, "wendys_h1_time_fe_combinations_diagnostics.csv")
SUMMARY_OUT     = os.path.join(RESULT_DIR, "wendys_h1_time_fe_combinations_summary.md")

DVS = [
    "log1p_engagement_total",
    "log1p_engagement_favorite_retweet",
    "log1p_favorite_count",
    "log1p_retweet_count",
    "log1p_reply_count",
    "log1p_quote_count",
    "log1p_bookmark_count",
]

RESULT_FIELDS = [
    "sample_type", "model_name", "dv", "iv", "n",
    "coefficient", "p_value",
    "r_squared", "adj_r_squared", "aic", "bic",
    "included_time_fe", "number_of_time_variables",
    "interpretation_flag",
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
    return sorted(set(r[col] for r in rows), key=lambda x: int(x) if as_int else x)

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
    h3_map = {r["id"]: r for r in csv.DictReader(f)}

merged = []
for pr in pred_rows:
    base = dict(h3_map[pr["id"]])
    for k, v in pr.items():
        base[k] = v
    merged.append(base)

assert len(merged) == 978,  f"전체 n 오류: {len(merged)}"
primary = [r for r in merged if r.get("final_humor_label_available") == "1"]
assert len(primary) == 597, f"primary n 오류: {len(primary)}"
print(f"  전체 n={len(merged)}, primary n={len(primary)}")

# ─── 2. Dataset 저장 ─────────────────────────────────────────────────────
print("[2] Dataset 저장")
with open(DATASET_OUT, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(merged[0].keys()), extrasaction="ignore")
    w.writeheader(); w.writerows(merged)
print(f"  → {DATASET_OUT}")

# ─── 3. OLS 인프라 ──────────────────────────────────────────────────────
def make_X(rows, iv_col, year_dummies=None, month_dummies=None, hour_dummies=None):
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

def ols_fit(X, y):
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
        2 * float(stats.t.sf(abs(t_arr[i]), df=df_r))
        if df_r > 0 and not math.isnan(t_arr[i]) else float("nan")
        for i in range(p)
    ])
    return dict(coef=coef, se=se_arr, t=t_arr, pval=p_arr,
                r2=r2, adj_r2=adj_r2, aic=aic, bic=bic, n=n)

# ─── 4. 회귀 실행 함수 ───────────────────────────────────────────────────
def run_combinations(rows, iv_col, sample_type):
    all_years  = sorted_unique(rows, "created_year")
    all_months = sorted_unique(rows, "created_month", as_int=True)
    all_hours  = sorted_unique(rows, "created_hour",  as_int=True)

    base_year  = all_years[0]
    base_month = all_months[0]
    base_hour  = all_hours[0]

    YD = [y for y in all_years  if y != base_year]
    MD = [m for m in all_months if m != base_month]
    HD = [h for h in all_hours  if h != base_hour]

    print(f"  [{sample_type}] base year={base_year}, month={base_month}, hour={base_hour}")
    print(f"    dummies: year({len(YD)}), month({len(MD)}), hour({len(HD)})")

    # (model_name, use_year, use_month, use_hour, n_time_vars, fe_desc)
    model_specs = [
        ("M0_baseline",          False, False, False, 0, "none"),
        ("M1_year_fe",           True,  False, False, 1, "year_FE"),
        ("M2_month_fe",          False, True,  False, 1, "month_FE"),
        ("M3_hour_fe",           False, False, True,  1, "hour_FE"),
        ("M4_year_month_fe",     True,  True,  False, 2, "year_FE+month_FE"),
        ("M5_year_hour_fe",      True,  False, True,  2, "year_FE+hour_FE"),
        ("M6_month_hour_fe",     False, True,  True,  2, "month_FE+hour_FE"),
        ("M7_year_month_hour_fe",True,  True,  True,  3, "year_FE+month_FE+hour_FE"),
    ]

    results = []
    for dv in DVS:
        y = np.array([safe_float(r.get(dv, "")) or 0.0 for r in rows])

        for mname, use_y, use_m, use_h, n_time, fe_desc in model_specs:
            yd = YD if use_y else None
            md = MD if use_m else None
            hd = HD if use_h else None

            X, labels = make_X(rows, iv_col, yd, md, hd)
            fit = ols_fit(X, y)

            if fit is None:
                results.append(dict(zip(RESULT_FIELDS, [
                    sample_type, mname, dv, iv_col, len(rows),
                    "RANK_DEFICIENT", "FAIL",
                    "FAIL", "FAIL", "FAIL", "FAIL",
                    fe_desc, n_time, "FAIL",
                ])))
                continue

            iv_idx = labels.index(iv_col)
            beta = float(fit["coef"][iv_idx])
            pval = float(fit["pval"][iv_idx])

            results.append({
                "sample_type":            sample_type,
                "model_name":             mname,
                "dv":                     dv,
                "iv":                     iv_col,
                "n":                      fit["n"],
                "coefficient":            fmt4(beta),
                "p_value":                fmt4(pval),
                "r_squared":              fmt4(fit["r2"]),
                "adj_r_squared":          fmt4(fit["adj_r2"]),
                "aic":                    fmt4(fit["aic"]),
                "bic":                    fmt4(fit["bic"]),
                "included_time_fe":       fe_desc,
                "number_of_time_variables": n_time,
                "interpretation_flag":    interp_flag(beta, pval),
            })
    return results

# ─── 5. 분석 실행 ───────────────────────────────────────────────────────────
print("[3] Primary human-labeled H1 (n=597, IV=final_humor_binary)")
primary_results = run_combinations(primary, "final_humor_binary", "primary_human_n597")

print("[4] Full-sample binary H1 (n=978, IV=pred_humor_final_050)")
fullbin_results = run_combinations(merged, "pred_humor_final_050", "fullsample_binary_n978")

print("[5] Probability-based H1 (n=978, IV=p_humor_final_tfidf_logreg)")
prob_results = run_combinations(merged, "p_humor_final_tfidf_logreg", "probability_n978")

# ─── 6. 결과 저장 ───────────────────────────────────────────────────────────
print("[6] 결과 저장")
for path, res in [
    (PRIMARY_RES_OUT, primary_results),
    (FULLBIN_RES_OUT, fullbin_results),
    (PROB_RES_OUT,    prob_results),
]:
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=RESULT_FIELDS)
        w.writeheader(); w.writerows(res)
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

diag_rows = [
    ("primary_n",                    len(primary)),
    ("full_n",                       len(merged)),
    ("primary_humor_1",              sum(1 for r in primary if r.get("final_humor_binary")=="1")),
    ("primary_humor_0",              sum(1 for r in primary if r.get("final_humor_binary")=="0")),
    ("full_predicted_humor_1",       sum(1 for r in merged if r.get("pred_humor_final_050")=="1")),
    ("full_predicted_humor_0",       sum(1 for r in merged if r.get("pred_humor_final_050")=="0")),
    ("primary_year_unique",          len(sorted_unique(primary, "created_year"))),
    ("primary_year_values",          str(sorted_unique(primary, "created_year"))),
    ("primary_month_unique",         len(sorted_unique(primary, "created_month", as_int=True))),
    ("primary_hour_unique",          len(sorted_unique(primary, "created_hour",  as_int=True))),
    ("full_year_unique",             len(sorted_unique(merged,  "created_year"))),
    ("full_year_values",             str(sorted_unique(merged,  "created_year"))),
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
    ("original_posts_json_modified", posts_json_modified),
]
# primary 주요 모형 결과 추가
for mname in ["M0_baseline","M1_year_fe","M2_month_fe","M3_hour_fe",
              "M4_year_month_fe","M5_year_hour_fe","M6_month_hour_fe","M7_year_month_hour_fe"]:
    r = get_r(primary_results, mname, "log1p_engagement_total")
    diag_rows.append((f"primary_{mname}_beta",   r.get("coefficient","n/a")))
    diag_rows.append((f"primary_{mname}_p_value",r.get("p_value","n/a")))
    diag_rows.append((f"primary_{mname}_flag",   r.get("interpretation_flag","n/a")))

with open(DIAG_OUT, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=["metric","value"])
    w.writeheader()
    for k, v in diag_rows:
        w.writerow({"metric": k, "value": v})
print(f"  → {DIAG_OUT}")

# ─── 8. Summary Markdown ─────────────────────────────────────────────────────
print("[8] Summary 작성")

def tbl_by_model(results, dv="log1p_engagement_total"):
    rows_dv = [r for r in results if r["dv"] == dv]
    lines = [
        "| n_time | model | β | p_value | sig | R² | adj_R² | flag |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for r in rows_dv:
        pv = r["p_value"]
        sig = star(float(pv)) if pv not in ("FAIL","nan") else ""
        lines.append(
            f"| {r['number_of_time_variables']} | {r['model_name']} "
            f"| {r['coefficient']} | {r['p_value']} | {sig} "
            f"| {r['r_squared']} | {r['adj_r_squared']} | {r['interpretation_flag']} |"
        )
    return "\n".join(lines)

def tbl_m7_all_dv(results, model="M7_year_month_hour_fe"):
    rows_m = [r for r in results if r["model_name"] == model]
    lines = [
        "| DV | β | p_value | sig | R² | flag |",
        "|---|---|---|---|---|---|",
    ]
    for r in rows_m:
        pv = r["p_value"]
        sig = star(float(pv)) if pv not in ("FAIL","nan") else ""
        lines.append(
            f"| {r['dv']} | {r['coefficient']} | {r['p_value']} "
            f"| {sig} | {r['r_squared']} | {r['interpretation_flag']} |"
        )
    return "\n".join(lines)

def tbl_n_time(results, n_time, dv="log1p_engagement_total"):
    rows_filtered = [r for r in results if r["dv"]==dv and r["number_of_time_variables"]==n_time]
    lines = [
        "| model | included_time_fe | β | p_value | sig | R² | flag |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in rows_filtered:
        pv = r["p_value"]
        sig = star(float(pv)) if pv not in ("FAIL","nan") else ""
        lines.append(
            f"| {r['model_name']} | {r['included_time_fe']} "
            f"| {r['coefficient']} | {r['p_value']} | {sig} "
            f"| {r['r_squared']} | {r['interpretation_flag']} |"
        )
    return "\n".join(lines)

def change_tbl(results, dv="log1p_engagement_total"):
    model_order = [
        "M0_baseline","M1_year_fe","M2_month_fe","M3_hour_fe",
        "M4_year_month_fe","M5_year_hour_fe","M6_month_hour_fe","M7_year_month_hour_fe"
    ]
    lines = [
        "| n_time | model | β | p_value | sig | R² | AIC | BIC |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for mname in model_order:
        r = get_r(results, mname, dv)
        if not r: continue
        pv = r["p_value"]
        sig = star(float(pv)) if pv not in ("FAIL","nan") else ""
        lines.append(
            f"| {r['number_of_time_variables']} | {r['model_name']} "
            f"| {r['coefficient']} | {r['p_value']} | {sig} "
            f"| {r['r_squared']} | {r['aic']} | {r['bic']} |"
        )
    return "\n".join(lines)

# 주요 수치 추출
pr_m0 = get_r(primary_results, "M0_baseline",          "log1p_engagement_total")
pr_m7 = get_r(primary_results, "M7_year_month_hour_fe","log1p_engagement_total")

primary_year_base  = sorted_unique(primary, "created_year")[0]
primary_month_base = sorted_unique(primary, "created_month", as_int=True)[0]
primary_hour_base  = sorted_unique(primary, "created_hour",  as_int=True)[0]
n_YD = len(sorted_unique(primary, "created_year")) - 1
n_MD = len(sorted_unique(primary, "created_month", as_int=True)) - 1
n_HD = len(sorted_unique(primary, "created_hour",  as_int=True)) - 1

summary_md = f"""# Wendy's H1 Time Fixed Effects Combination Check 결과

## 1. 분석 목적

유머 게시글 여부(Humor_i)와 post-level engagement 간 관계가 created_year, created_month, created_hour를 1개 / 2개 조합 / 3개 전체로 추가했을 때 각각 어떻게 변화하는지 확인한다. 이번 작업은 H1에만 한정하며, H2와 H3는 수행하지 않았다.

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

## 6. 사용한 시간 변수 조합

| 변수 | 처리 방식 | primary 기준 범주 | primary 더미 수 |
|---|---|---|---|
| created_year | categorical FE (더미) | {primary_year_base} | {n_YD} |
| created_month | categorical FE (더미) | {primary_month_base} | {n_MD} |
| created_hour | categorical FE (더미) | {primary_hour_base} | {n_HD} |

기준 범주는 각 변수 내 최솟값으로 자동 설정하였다.

모형 구성:

| 모형 | 포함 FE | 시간 변수 수 |
|---|---|---|
| M0_baseline | none | 0 |
| M1_year_fe | year_FE | 1 |
| M2_month_fe | month_FE | 1 |
| M3_hour_fe | hour_FE | 1 |
| M4_year_month_fe | year_FE+month_FE | 2 |
| M5_year_hour_fe | year_FE+hour_FE | 2 |
| M6_month_hour_fe | month_FE+hour_FE | 2 |
| M7_year_month_hour_fe | year_FE+month_FE+hour_FE | 3 |

---

## 7. Primary Human-labeled H1 결과

**표본: n={len(primary)}, IV=final_humor_binary**

### 7-1. Primary DV: log1p_engagement_total (전체 모형)

{tbl_by_model(primary_results, "log1p_engagement_total")}

* p<.05, ** p<.01, *** p<.001, † p<.10 (conventional SE 기준)

### 7-2. M7 (전체 FE) 기준 전체 DV

{tbl_m7_all_dv(primary_results, "M7_year_month_hour_fe")}

---

## 8. Supplemental Full-sample Binary H1 결과

**표본: n={len(merged)}, IV=pred_humor_final_050**

### 8-1. Primary DV: log1p_engagement_total (전체 모형)

{tbl_by_model(fullbin_results, "log1p_engagement_total")}

### 8-2. M7 기준 전체 DV

{tbl_m7_all_dv(fullbin_results, "M7_year_month_hour_fe")}

---

## 9. Probability-based Supplemental H1 결과

**표본: n={len(merged)}, IV=p_humor_final_tfidf_logreg (0~1 확률값)**

### 9-1. Primary DV: log1p_engagement_total (전체 모형)

{tbl_by_model(prob_results, "log1p_engagement_total")}

### 9-2. M7 기준 전체 DV

{tbl_m7_all_dv(prob_results, "M7_year_month_hour_fe")}

---

## 10. 시간 변수 1개 추가 결과 비교 (Primary sample, DV=log1p_engagement_total)

{tbl_n_time(primary_results, 1, "log1p_engagement_total")}

---

## 11. 시간 변수 2개 조합 결과 비교 (Primary sample, DV=log1p_engagement_total)

{tbl_n_time(primary_results, 2, "log1p_engagement_total")}

---

## 12. 시간 변수 3개 전체 조합 결과 (Primary sample, DV=log1p_engagement_total)

{tbl_n_time(primary_results, 3, "log1p_engagement_total")}

---

## 13. Baseline 대비 β 및 p-value 변화

**Primary sample, primary DV (log1p_engagement_total)**

{change_tbl(primary_results, "log1p_engagement_total")}

---

## 14. 최종 해석

**Primary model 결과 (M7, primary sample n={len(primary)}, conventional SE 기준):**

- IV: final_humor_binary
- DV: log1p_engagement_total
- β = {pr_m7.get("coefficient","n/a")}, p = {pr_m7.get("p_value","n/a")}
- **판정: {pr_m7.get("interpretation_flag","n/a")}**

Baseline (M0)의 β = {pr_m0.get("coefficient","n/a")} (p={pr_m0.get("p_value","n/a")})에서 시간 FE 조합에 따른 β의 변화는 위 표(섹션 13)에 정리되어 있다. 어떤 시간 변수 조합을 추가하더라도 β의 방향성과 유의성 유지 여부를 확인하는 것이 이번 분석의 핵심이다.

---

## 15. 인과관계 아님 — 관측적 연관성 분석

본 분석은 관측적 연관성 분석이며, 유머 게시글 여부가 engagement를 증가시켰다는 인과관계를 주장할 수 없다. 시간 고정효과는 연도·월·시간대 수준의 공통 요인을 통제하지만, 관찰되지 않은 개별 게시글의 내용 특성이나 기타 혼동 요인은 통제되지 않는다.

---

## 16. H2/H3 수행 여부

이번 작업에서는 H1 분석만 수행하였으며, H2와 H3는 수행하지 않았다.

---

## 17. 다음 단계

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
print(f"  primary n={len(primary)} (기대:597): {'OK' if len(primary)==597 else 'FAIL'}")
print(f"  full    n={len(merged)} (기대:978): {'OK' if len(merged)==978 else 'FAIL'}")
print(f"  posts.json 변경: {posts_json_modified} (기대:False)")
rank_fail = any(r.get("interpretation_flag")=="FAIL"
                for r in primary_results+fullbin_results+prob_results)
print(f"  rank deficient: {rank_fail} (기대:False)")
print(f"  H2/H3 수행: False | 새 변수 생성: False")

print("\n[Primary DV log1p_engagement_total — 전체 모형]")
for r in [x for x in primary_results if x["dv"]=="log1p_engagement_total"]:
    pv = r["p_value"]
    sig = star(float(pv)) if pv not in ("FAIL","nan") else ""
    print(f"  n_time={r['number_of_time_variables']} {r['model_name']:28s} "
          f"β={r['coefficient']:8s} p={r['p_value']:8s} {sig:4s} {r['interpretation_flag']}")

print("\n[Full-sample binary primary DV]")
for r in [x for x in fullbin_results if x["dv"]=="log1p_engagement_total"]:
    pv = r["p_value"]
    sig = star(float(pv)) if pv not in ("FAIL","nan") else ""
    print(f"  n_time={r['number_of_time_variables']} {r['model_name']:28s} "
          f"β={r['coefficient']:8s} p={r['p_value']:8s} {sig:4s} {r['interpretation_flag']}")

print("\n[Probability primary DV]")
for r in [x for x in prob_results if x["dv"]=="log1p_engagement_total"]:
    pv = r["p_value"]
    sig = star(float(pv)) if pv not in ("FAIL","nan") else ""
    print(f"  n_time={r['number_of_time_variables']} {r['model_name']:28s} "
          f"β={r['coefficient']:8s} p={r['p_value']:8s} {sig:4s} {r['interpretation_flag']}")
