"""
run_wendys_h2_step2_time_fe.py

목적: H2 2단계 — aggressive vs other_humor 비교에 시간 FE(year/month/hour) 조합 추가.
      M0(baseline) ~ M7(all FE)의 8개 모형 비교.

주 분석: pred_humor_type_group_model ∈ {aggressive, other_humor}, n=564
부가 검증: final_humor_type_group ∈ {aggressive, other_humor}, n=278

H1/H3 없음. post format controls 없음. 새 변수 생성 없음.
IV: is_aggressive_humor (기존 H3 파일 변수). 기준 범주: other_humor.
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

H3_FILE  = os.path.join(DATA_DIR,   "wendys_h3_aggressive_vs_other_intensity_dataset.csv")
RV_FILE  = os.path.join(RESULT_DIR, "wendys_humor_review_sheet.csv")

DATASET_OUT = os.path.join(DATA_DIR,   "wendys_h2_step2_time_fe_dataset.csv")
MB_RES_OUT  = os.path.join(RESULT_DIR, "wendys_h2_step2_time_fe_model_based_results.csv")
HV_RES_OUT  = os.path.join(RESULT_DIR, "wendys_h2_step2_time_fe_human_validation_results.csv")
DIAG_OUT    = os.path.join(RESULT_DIR, "wendys_h2_step2_time_fe_diagnostics.csv")
SUMMARY_OUT = os.path.join(RESULT_DIR, "wendys_h2_step2_time_fe_summary.md")

DVS = [
    "log1p_engagement_total",
    "log1p_engagement_favorite_retweet",
    "log1p_favorite_count",
    "log1p_retweet_count",
    "log1p_reply_count",
    "log1p_quote_count",
    "log1p_bookmark_count",
]

MODEL_ORDER = [
    "M0_baseline",
    "M1_year_fe",
    "M2_month_fe",
    "M3_hour_fe",
    "M4_year_month_fe",
    "M5_year_hour_fe",
    "M6_month_hour_fe",
    "M7_year_month_hour_fe",
]

RESULT_FIELDS = [
    "sample_type", "model_name", "dv", "iv",
    "n", "aggressive_n", "other_humor_n",
    "aggressive_mean", "other_humor_mean", "mean_difference",
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

def star(p_str):
    try: p = float(p_str)
    except (ValueError, TypeError): return ""
    if math.isnan(p): return ""
    if p < 0.001: return "***"
    if p < 0.01:  return "**"
    if p < 0.05:  return "*"
    if p < 0.10:  return "†"
    return ""

def interp_flag(beta, p):
    if math.isnan(beta) or math.isnan(p): return "unknown"
    if beta > 0 and p < 0.05:  return "supports_H2"
    if beta > 0 and p < 0.10:  return "weak_support"
    if beta > 0:               return "positive_not_significant"
    return "not_support"

def sorted_unique(rows, col, as_int=False):
    return sorted(set(r[col] for r in rows), key=lambda x: int(x) if as_int else x)

def get_r(results, model, dv):
    return next((r for r in results if r["model_name"] == model and r["dv"] == dv), {})

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
with open(H3_FILE, newline="", encoding="utf-8") as f:
    h3_rows = list(csv.DictReader(f))
with open(RV_FILE, newline="", encoding="utf-8") as f:
    rv_map = {r["id"]: r for r in csv.DictReader(f)}

h3_ids = [r["id"] for r in h3_rows]
unmatched = [pid for pid in h3_ids if pid not in rv_map]
dup_h3 = len(h3_ids) != len(set(h3_ids))
dup_rv = len(rv_map) != len(set(rv_map.keys()))

print(f"  H3 n={len(h3_rows)}, rv n={len(rv_map)}, unmatched={len(unmatched)}")
if unmatched or dup_h3 or dup_rv:
    print("  ERROR: 병합 불안정 — 중단")
    raise SystemExit(1)

merged_all = []
for r in h3_rows:
    base = dict(r)
    base["final_humor_type_group"] = rv_map[r["id"]].get("final_humor_type_group", "")
    merged_all.append(base)

assert len(merged_all) == 978

# ─── 2. 표본 필터링 ─────────────────────────────────────────────────────────
print("[2] H2 표본 필터링")

mb_sample = [r for r in merged_all
             if r.get("pred_humor_type_group_model") in ("aggressive", "other_humor")]
mb_agg    = [r for r in mb_sample if r.get("is_aggressive_humor") == "1"]
mb_other  = [r for r in mb_sample if r.get("is_aggressive_humor") == "0"]

hv_sample = [r for r in merged_all
             if r.get("final_humor_type_group") in ("aggressive", "other_humor")]
hv_agg    = [r for r in hv_sample if r.get("final_humor_type_group") == "aggressive"]
hv_other  = [r for r in hv_sample if r.get("final_humor_type_group") == "other_humor"]

print(f"  model-based: n={len(mb_sample)}, agg={len(mb_agg)}, other={len(mb_other)}")
print(f"  human valid: n={len(hv_sample)}, agg={len(hv_agg)}, other={len(hv_other)}")

assert len(mb_sample)==564 and len(mb_agg)==200 and len(mb_other)==364
assert len(hv_sample)==278 and len(hv_agg)==95 and len(hv_other)==183

non_in_mb = sum(1 for r in mb_sample if r.get("pred_humor_type_group_model")=="non_humor")
non_in_hv = sum(1 for r in hv_sample if r.get("final_humor_type_group")=="non_humor")
print(f"  non_humor in samples: mb={non_in_mb}, hv={non_in_hv}")

# ─── 3. Dataset 저장 ─────────────────────────────────────────────────────
print("[3] Dataset 저장")
with open(DATASET_OUT, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(merged_all[0].keys()), extrasaction="ignore")
    w.writeheader(); w.writerows(merged_all)
print(f"  → {DATASET_OUT}")

# ─── 4. OLS 인프라 ──────────────────────────────────────────────────────
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
    coef   = XtXinv @ (X.T @ y)
    resid  = y - X @ coef
    sse    = float(resid @ resid)
    sst    = float(np.sum((y - y.mean()) ** 2))
    df_r   = n - p
    mse    = sse / df_r if df_r > 0 else float("nan")
    r2     = 1 - sse / sst if sst > 0 else float("nan")
    adj_r2 = 1 - (1 - r2) * (n - 1) / df_r if df_r > 0 and sst > 0 else float("nan")
    aic    = n * math.log(sse / n) + 2 * p if sse > 0 else float("nan")
    bic    = n * math.log(sse / n) + p * math.log(n) if sse > 0 else float("nan")
    se_arr = np.sqrt(np.maximum(np.diag(mse * XtXinv), 0.0))
    t_arr  = np.where(se_arr > 0, coef / se_arr, float("nan"))
    p_arr  = np.array([
        2 * float(stats.t.sf(abs(t_arr[i]), df=df_r))
        if df_r > 0 and not math.isnan(t_arr[i]) else float("nan")
        for i in range(p)
    ])
    return dict(coef=coef, pval=p_arr, r2=r2, adj_r2=adj_r2,
                aic=aic, bic=bic, n=n, labels=None)

# ─── 5. 회귀 실행 함수 ───────────────────────────────────────────────────
def run_time_fe_models(rows_agg, rows_other, iv_col, sample_type):
    rows = rows_agg + rows_other

    all_years  = sorted_unique(rows, "created_year")
    all_months = sorted_unique(rows, "created_month", as_int=True)
    all_hours  = sorted_unique(rows, "created_hour",  as_int=True)
    YD = [y for y in all_years  if y != all_years[0]]
    MD = [m for m in all_months if m != all_months[0]]
    HD = [h for h in all_hours  if h != all_hours[0]]

    print(f"  [{sample_type}] n={len(rows)}, base year={all_years[0]}, month={all_months[0]}, hour={all_hours[0]}")
    print(f"    dummies: year({len(YD)}), month({len(MD)}), hour({len(HD)})")

    model_specs = [
        ("M0_baseline",          None, None, None, 0, "none"),
        ("M1_year_fe",           YD,   None, None, 1, "year_FE"),
        ("M2_month_fe",          None, MD,   None, 1, "month_FE"),
        ("M3_hour_fe",           None, None, HD,   1, "hour_FE"),
        ("M4_year_month_fe",     YD,   MD,   None, 2, "year_FE+month_FE"),
        ("M5_year_hour_fe",      YD,   None, HD,   2, "year_FE+hour_FE"),
        ("M6_month_hour_fe",     None, MD,   HD,   2, "month_FE+hour_FE"),
        ("M7_year_month_hour_fe",YD,   MD,   HD,   3, "year_FE+month_FE+hour_FE"),
    ]

    agg_means   = {dv: float(np.mean([safe_float(r.get(dv,"")) or 0.0 for r in rows_agg])) for dv in DVS}
    other_means = {dv: float(np.mean([safe_float(r.get(dv,"")) or 0.0 for r in rows_other])) for dv in DVS}

    results = []
    for dv in DVS:
        y = np.array([safe_float(r.get(dv,"")) or 0.0 for r in rows])
        x_iv = np.array([safe_float(r.get(iv_col,"")) or 0.0 for r in rows])

        for mname, yd, md, hd, n_time, fe_desc in model_specs:
            X, labels = make_X(rows, iv_col, yd, md, hd)
            fit = ols_fit(X, y)

            if fit is None:
                results.append(dict(zip(RESULT_FIELDS, [
                    sample_type, mname, dv, iv_col,
                    len(rows), len(rows_agg), len(rows_other),
                    fmt4(agg_means[dv]), fmt4(other_means[dv]),
                    fmt4(agg_means[dv]-other_means[dv]),
                    "RANK_DEFICIENT", "FAIL",
                    "FAIL", "FAIL", "FAIL", "FAIL",
                    fe_desc, n_time, "FAIL",
                ])))
                continue

            iv_idx = labels.index(iv_col)
            beta = float(fit["coef"][iv_idx])
            pval = float(fit["pval"][iv_idx])

            results.append({
                "sample_type":             sample_type,
                "model_name":              mname,
                "dv":                      dv,
                "iv":                      iv_col,
                "n":                       fit["n"],
                "aggressive_n":            len(rows_agg),
                "other_humor_n":           len(rows_other),
                "aggressive_mean":         fmt4(agg_means[dv]),
                "other_humor_mean":        fmt4(other_means[dv]),
                "mean_difference":         fmt4(agg_means[dv]-other_means[dv]),
                "coefficient":             fmt4(beta),
                "p_value":                 fmt4(pval),
                "r_squared":               fmt4(fit["r2"]),
                "adj_r_squared":           fmt4(fit["adj_r2"]),
                "aic":                     fmt4(fit["aic"]),
                "bic":                     fmt4(fit["bic"]),
                "included_time_fe":        fe_desc,
                "number_of_time_variables":n_time,
                "interpretation_flag":     interp_flag(beta, pval),
            })
    return results

# ─── 6. 분석 실행 ───────────────────────────────────────────────────────────
print("[4] Model-based H2 time FE (n=564)")
mb_results = run_time_fe_models(mb_agg, mb_other, "is_aggressive_humor", "model_based_n564")

print("[5] Human validation H2 time FE (n=278)")
# human validation: in-memory binary (final_humor_type_group=="aggressive" → 1)
# H3 파일에는 is_aggressive_humor가 model-based 기준이므로,
# human validation에서는 final_humor_type_group 기반 binary를 row에 임시 추가하여 사용
for r in hv_sample:
    r["_hv_agg_dummy"] = "1" if r.get("final_humor_type_group") == "aggressive" else "0"
hv_results = run_time_fe_models(hv_agg, hv_other, "_hv_agg_dummy", "human_validation_n278")

# ─── 7. 결과 저장 ───────────────────────────────────────────────────────────
print("[6] 결과 저장")
for path, res in [(MB_RES_OUT, mb_results), (HV_RES_OUT, hv_results)]:
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=RESULT_FIELDS)
        w.writeheader(); w.writerows(res)
    print(f"  → {path} ({len(res)}건)")

# ─── 8. 진단 ────────────────────────────────────────────────────────────────
print("[7] Diagnostics")
posts_json_modified = False
if hash_before:
    try:
        with open(POSTS_JSON, "rb") as f:
            h_now = hashlib.md5(f.read()).hexdigest()
        posts_json_modified = (h_now != hash_before)
    except FileNotFoundError:
        pass

mb_m0 = get_r(mb_results, "M0_baseline",           "log1p_engagement_total")
mb_m7 = get_r(mb_results, "M7_year_month_hour_fe",  "log1p_engagement_total")
hv_m0 = get_r(hv_results, "M0_baseline",           "log1p_engagement_total")
hv_m7 = get_r(hv_results, "M7_year_month_hour_fe",  "log1p_engagement_total")

diag_rows = [
    ("model_based_humor_only_n",  len(mb_sample)),
    ("model_based_aggressive_n",  len(mb_agg)),
    ("model_based_other_humor_n", len(mb_other)),
    ("human_validation_n",        len(hv_sample)),
    ("human_aggressive_n",        len(hv_agg)),
    ("human_other_humor_n",       len(hv_other)),
    ("non_humor_in_mb",           non_in_mb),
    ("non_humor_in_hv",           non_in_hv),
    ("sample_reduced_by_missing", "no"),
    ("rank_deficient_any",        any(r.get("interpretation_flag")=="FAIL"
                                      for r in mb_results+hv_results)),
    ("log1p_view_count_used",     False),
    ("post_format_controls_used", False),
    ("year_quarter_fe_used",      False),
    ("new_vars_created",          False),
    ("H1_performed",              False),
    ("H3_performed",              False),
    ("original_posts_json_modified", posts_json_modified),
    ("mb_M0_beta",   mb_m0.get("coefficient","n/a")),
    ("mb_M0_p",      mb_m0.get("p_value","n/a")),
    ("mb_M0_flag",   mb_m0.get("interpretation_flag","n/a")),
    ("mb_M7_beta",   mb_m7.get("coefficient","n/a")),
    ("mb_M7_p",      mb_m7.get("p_value","n/a")),
    ("mb_M7_flag",   mb_m7.get("interpretation_flag","n/a")),
    ("hv_M0_beta",   hv_m0.get("coefficient","n/a")),
    ("hv_M0_p",      hv_m0.get("p_value","n/a")),
    ("hv_M7_beta",   hv_m7.get("coefficient","n/a")),
    ("hv_M7_p",      hv_m7.get("p_value","n/a")),
]

with open(DIAG_OUT, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=["metric","value"])
    w.writeheader()
    for k, v in diag_rows:
        w.writerow({"metric": k, "value": v})
print(f"  → {DIAG_OUT}")

# ─── 9. Summary Markdown ─────────────────────────────────────────────────────
print("[8] Summary 작성")

def tbl_by_model(results, dv="log1p_engagement_total"):
    rows_dv = [r for r in results if r["dv"]==dv and r["model_name"] in MODEL_ORDER]
    rows_dv.sort(key=lambda r: MODEL_ORDER.index(r["model_name"]))
    lines = [
        "| n_time | model | included_FE | β | p | sig | R² | adj_R² | 판정 |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for r in rows_dv:
        lines.append(
            f"| {r['number_of_time_variables']} | {r['model_name']} "
            f"| {r['included_time_fe']} "
            f"| {r['coefficient']} | {r['p_value']} | {star(r['p_value'])} "
            f"| {r['r_squared']} | {r['adj_r_squared']} | {r['interpretation_flag']} |"
        )
    return "\n".join(lines)

def tbl_m7_all_dv(results, model="M7_year_month_hour_fe"):
    rows_m = [r for r in results if r["model_name"]==model]
    lines = [
        "| DV | β | p | sig | R² | 판정 |",
        "|---|---|---|---|---|---|",
    ]
    for r in rows_m:
        lines.append(
            f"| {r['dv']} | {r['coefficient']} | {r['p_value']} "
            f"| {star(r['p_value'])} | {r['r_squared']} | {r['interpretation_flag']} |"
        )
    return "\n".join(lines)

def change_tbl(mb, hv, dv="log1p_engagement_total"):
    lines = [
        "| n_time | model | mb_β | mb_p | mb_sig | hv_β | hv_p | hv_sig |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for mname in MODEL_ORDER:
        rm = get_r(mb, mname, dv)
        rh = get_r(hv, mname, dv)
        lines.append(
            f"| {rm.get('number_of_time_variables','')} | {mname} "
            f"| {rm.get('coefficient','')} | {rm.get('p_value','')} | {star(rm.get('p_value',''))} "
            f"| {rh.get('coefficient','')} | {rh.get('p_value','')} | {star(rh.get('p_value',''))} |"
        )
    return "\n".join(lines)

# model-based sample 시간 변수 정보
mb_years  = sorted_unique(mb_agg+mb_other, "created_year")
mb_months = sorted_unique(mb_agg+mb_other, "created_month", as_int=True)
mb_hours  = sorted_unique(mb_agg+mb_other, "created_hour",  as_int=True)

summary_md = f"""# Wendy's H2 Step 2: Aggressive vs Other Humor with Time Fixed Effects 결과

## 1. 분석 목적

H2 Step 1에서 확인한 aggressive humor > other humor 관계가 Year FE, Month FE, Hour FE를 순차적으로 추가했을 때에도 유지되는지 확인한다. 8개 시간 FE 조합 모형(M0~M7)을 비교한다. post format controls는 이번 단계에서 추가하지 않는다.

---

## 2. H2 가설

H2: Wendy's 브랜드 게시글에서 aggressive humor는 other humor보다 post-level engagement가 높을 것이다.

---

## 3. 사용한 파일

| 파일 | 역할 |
|---|---|
| wendys_h3_aggressive_vs_other_intensity_dataset.csv | DV, is_aggressive_humor, 시간 변수 |
| wendys_humor_review_sheet.csv | final_humor_type_group (human validation) |

---

## 4. 원본 posts.json 변경 없음 확인

data/wendys/posts.json 변경 여부: **{posts_json_modified}**

---

## 5. 새 변수 생성 없음 확인

새로운 변수를 생성하지 않았다. is_aggressive_humor는 기존 H3 파일의 변수이다. Human validation IV는 in-memory에서만 사용하였다. post format 변수 미사용.

---

## 6. Model-based Humor-only Sample 구성

| 항목 | 값 |
|---|---|
| n | {len(mb_agg)+len(mb_other)} |
| aggressive n | {len(mb_agg)} |
| other_humor n | {len(mb_other)} |
| non_humor 포함 | {non_in_mb>0} |
| 기준 범주 | other_humor (is_aggressive_humor=0) |
| 기준 연도 (year FE) | {mb_years[0]} |
| 기준 월 (month FE) | {mb_months[0]} |
| 기준 시간 (hour FE) | {mb_hours[0]} |

---

## 7. Human-coded Validation Sample 구성

| 항목 | 값 |
|---|---|
| n | {len(hv_agg)+len(hv_other)} |
| aggressive n | {len(hv_agg)} |
| other_humor n | {len(hv_other)} |
| non_humor 포함 | {non_in_hv>0} |

---

## 8. 사용한 시간 고정효과 조합

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

## 9. Model-based H2 결과 (primary DV)

**표본: n={len(mb_agg)+len(mb_other)}, IV=is_aggressive_humor, 기준=other_humor**

{tbl_by_model(mb_results, "log1p_engagement_total")}

* p<.05, ** p<.01, *** p<.001, † p<.10 (conventional SE 기준)

---

## 10. Model-based M7 기준 전체 DV

{tbl_m7_all_dv(mb_results, "M7_year_month_hour_fe")}

---

## 11. Human-coded Validation 결과 (primary DV, 부가 검증)

**표본: n={len(hv_agg)+len(hv_other)}, IV=final_humor_type_group(aggressive dummy)**

{tbl_by_model(hv_results, "log1p_engagement_total")}

---

## 12. Human-coded Validation M7 기준 전체 DV

{tbl_m7_all_dv(hv_results, "M7_year_month_hour_fe")}

---

## 13. Baseline 대비 시간 FE 추가 후 β, p-value 변화 (primary DV)

{change_tbl(mb_results, hv_results, "log1p_engagement_total")}

mb=model_based, hv=human_validation

---

## 14. H2 주 분석 판정

**Model-based M7 (전체 시간 FE) 기준:**

| 표본 | β | p | 판정 |
|---|---|---|---|
| Model-based (n={len(mb_agg)+len(mb_other)}) | {mb_m7.get("coefficient","n/a")} | {mb_m7.get("p_value","n/a")} | {mb_m7.get("interpretation_flag","n/a")} |
| Human validation (n={len(hv_agg)+len(hv_other)}) | {hv_m7.get("coefficient","n/a")} | {hv_m7.get("p_value","n/a")} | {hv_m7.get("interpretation_flag","n/a")} |

---

## 15. 사람 코딩 결과는 부가 검증

Human validation 결과(n={len(hv_sample)})는 부가 검증이며 주 분석을 대체하지 않는다.

---

## 16. Non_humor 제외 확인

H2 direct test에서 non_humor는 제외하였다. model-based in-sample: {non_in_mb}건, human validation in-sample: {non_in_hv}건.

---

## 17. 인과관계 아님 — 관측적 연관성 분석

본 분석은 관측적 연관성 분석이며, aggressive humor 여부가 engagement를 인과적으로 변화시켰다는 주장을 할 수 없다.

---

## 18. 다음 단계

다음 단계에서 post format controls(text_length, hashtag_count, mention_count 등)를 추가할 수 있으나, 사용자 승인 후 진행한다.

---

*생성일: 2026-06-15*
"""

with open(SUMMARY_OUT, "w", encoding="utf-8") as f:
    f.write(summary_md)
print(f"  → {SUMMARY_OUT}")

# ─── 10. 최종 검증 출력 ──────────────────────────────────────────────────────
print("\n" + "="*60)
print("[검증 요약]")
print(f"  mb n={len(mb_sample)} (기대:564): {'OK' if len(mb_sample)==564 else 'FAIL'}")
print(f"  mb agg={len(mb_agg)}/other={len(mb_other)} (기대:200/364): {'OK' if len(mb_agg)==200 else 'FAIL'}")
print(f"  hv n={len(hv_sample)} (기대:278): {'OK' if len(hv_sample)==278 else 'FAIL'}")
print(f"  non_humor 제외: mb={non_in_mb==0}, hv={non_in_hv==0}")
print(f"  posts.json 변경: {posts_json_modified} (기대:False)")
rank_fail = any(r.get("interpretation_flag")=="FAIL" for r in mb_results+hv_results)
print(f"  rank deficient: {rank_fail} (기대:False)")
print(f"  H1/H3: False | post_format: False | 새변수: False")

print("\n[Model-based primary DV — log1p_engagement_total]")
for mname in MODEL_ORDER:
    r = get_r(mb_results, mname, "log1p_engagement_total")
    n_t = r.get("number_of_time_variables","")
    print(f"  n_time={n_t} {r.get('model_name',''):28s} "
          f"β={r.get('coefficient',''):8s} p={r.get('p_value',''):8s} "
          f"{star(r.get('p_value','')):4s} {r.get('interpretation_flag','')}")

print("\n[Human validation primary DV]")
for mname in MODEL_ORDER:
    r = get_r(hv_results, mname, "log1p_engagement_total")
    n_t = r.get("number_of_time_variables","")
    print(f"  n_time={n_t} {r.get('model_name',''):28s} "
          f"β={r.get('coefficient',''):8s} p={r.get('p_value',''):8s} "
          f"{star(r.get('p_value','')):4s} {r.get('interpretation_flag','')}")
