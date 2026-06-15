"""
run_wendys_h2_step1_aggressive_vs_other.py

목적: H2 1단계 — model-based humor-only 표본(n=564)에서
      aggressive vs other_humor의 engagement 직접 비교.

주 분석: pred_humor_type_group_model ∈ {aggressive, other_humor}, n=564
부가 검증: final_humor_type_group ∈ {aggressive, other_humor}, n=278

H1/H3 수행 없음. 시간 FE 없음. post format controls 없음.
새 변수 생성 없음. posts.json 수정 없음.

IV: is_aggressive_humor (기존 H3 파일에 존재)
기준 범주: other_humor (is_aggressive_humor=0)
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

H3_FILE   = os.path.join(DATA_DIR,   "wendys_h3_aggressive_vs_other_intensity_dataset.csv")
MB_FILE   = os.path.join(RESULT_DIR, "wendys_model_based_humor_type_full_predictions.csv")
RV_FILE   = os.path.join(RESULT_DIR, "wendys_humor_review_sheet.csv")

DATASET_OUT = os.path.join(DATA_DIR,   "wendys_h2_step1_aggressive_vs_other_dataset.csv")
MB_RES_OUT  = os.path.join(RESULT_DIR, "wendys_h2_step1_model_based_direct_results.csv")
HV_RES_OUT  = os.path.join(RESULT_DIR, "wendys_h2_step1_human_validation_results.csv")
DIAG_OUT    = os.path.join(RESULT_DIR, "wendys_h2_step1_diagnostics.csv")
SUMMARY_OUT = os.path.join(RESULT_DIR, "wendys_h2_step1_summary.md")

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
    "sample_type", "model_name", "dv", "iv",
    "n", "aggressive_n", "other_humor_n",
    "aggressive_mean", "other_humor_mean", "mean_difference",
    "coefficient", "p_value",
    "r_squared", "adj_r_squared", "aic", "bic",
    "welch_t", "welch_p",
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
print("[1] 데이터 로드 및 병합 확인")
with open(H3_FILE, newline="", encoding="utf-8") as f:
    h3_rows = list(csv.DictReader(f))
with open(RV_FILE, newline="", encoding="utf-8") as f:
    rv_map = {r["id"]: r for r in csv.DictReader(f)}

h3_ids = [r["id"] for r in h3_rows]
rv_ids = list(rv_map.keys())
unmatched_rv = [pid for pid in h3_ids if pid not in rv_map]
dup_h3 = len(h3_ids) != len(set(h3_ids))
dup_rv = len(rv_ids) != len(set(rv_ids))

print(f"  H3 n={len(h3_rows)}, review_sheet n={len(rv_map)}")
print(f"  unmatched (rv): {len(unmatched_rv)}")
print(f"  duplicate keys — h3:{dup_h3}, rv:{dup_rv}")
if unmatched_rv or dup_h3 or dup_rv:
    print("  ERROR: 병합 불안정 — 중단")
    raise SystemExit(1)

# 병합: H3 + review_sheet의 final_humor_type_group 추가
merged_all = []
for r in h3_rows:
    base = dict(r)
    base["final_humor_type_group"] = rv_map[r["id"]].get("final_humor_type_group", "")
    merged_all.append(base)

assert len(merged_all) == 978, f"전체 n 오류: {len(merged_all)}"
print(f"  병합 완료: n={len(merged_all)}")

# ─── 2. 표본 필터링 ─────────────────────────────────────────────────────────
print("[2] H2 표본 필터링")

# Model-based: aggressive + other_humor only
mb_sample = [r for r in merged_all
             if r.get("pred_humor_type_group_model") in ("aggressive", "other_humor")]
mb_agg   = [r for r in mb_sample if r.get("is_aggressive_humor") == "1"]
mb_other = [r for r in mb_sample if r.get("is_aggressive_humor") == "0"]

print(f"  model-based humor-only: n={len(mb_sample)}")
print(f"    aggressive n={len(mb_agg)}, other_humor n={len(mb_other)}")
assert len(mb_sample) == 564, f"model-based n 오류: {len(mb_sample)}"
assert len(mb_agg)   == 200, f"aggressive n 오류: {len(mb_agg)}"
assert len(mb_other) == 364, f"other_humor n 오류: {len(mb_other)}"

# Human validation: final_humor_type_group ∈ {aggressive, other_humor}
hv_sample = [r for r in merged_all
             if r.get("final_humor_type_group") in ("aggressive", "other_humor")]
hv_agg   = [r for r in hv_sample if r.get("final_humor_type_group") == "aggressive"]
hv_other = [r for r in hv_sample if r.get("final_humor_type_group") == "other_humor"]

print(f"  human validation: n={len(hv_sample)}")
print(f"    aggressive n={len(hv_agg)}, other_humor n={len(hv_other)}")
assert len(hv_sample) == 278, f"human-coded n 오류: {len(hv_sample)}"
assert len(hv_agg)   == 95,  f"human aggressive n 오류: {len(hv_agg)}"
assert len(hv_other) == 183, f"human other_humor n 오류: {len(hv_other)}"

# non_humor 제외 확인
non_in_mb = sum(1 for r in mb_sample if r.get("pred_humor_type_group_model") == "non_humor")
non_in_hv = sum(1 for r in hv_sample if r.get("final_humor_type_group") == "non_humor")
print(f"  non_humor in mb_sample: {non_in_mb} (기대: 0)")
print(f"  non_humor in hv_sample: {non_in_hv} (기대: 0)")

# ─── 3. Dataset 저장 ─────────────────────────────────────────────────────
print("[3] Dataset 저장")
with open(DATASET_OUT, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(merged_all[0].keys()), extrasaction="ignore")
    w.writeheader(); w.writerows(merged_all)
print(f"  → {DATASET_OUT}")

# ─── 4. OLS 인프라 ──────────────────────────────────────────────────────
def simple_ols(x_binary, y):
    """Y ~ const + x_binary (단순 OLS)"""
    n = len(y)
    X = np.column_stack([np.ones(n), x_binary])
    p = 2
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
    beta   = float(coef[1])
    se_b   = float(se_arr[1])
    t_b    = beta / se_b if se_b > 0 else float("nan")
    p_b    = float(2 * stats.t.sf(abs(t_b), df=df_r)) if not math.isnan(t_b) else float("nan")
    return dict(beta=beta, p=p_b, r2=r2, adj_r2=adj_r2, aic=aic, bic=bic, n=n)

# ─── 5. 회귀 실행 함수 ───────────────────────────────────────────────────
def run_h2_direct(rows_agg, rows_other, iv_col_name, sample_type):
    """aggressive(1) vs other_humor(0) 단순 OLS + Welch t-test"""
    all_rows = rows_agg + rows_other
    x_binary = np.array([1.0 if r in rows_agg else 0.0 for r in all_rows])

    results = []
    for dv in DVS:
        y_agg   = np.array([safe_float(r.get(dv, "")) or 0.0 for r in rows_agg])
        y_other = np.array([safe_float(r.get(dv, "")) or 0.0 for r in rows_other])
        y_all   = np.concatenate([y_agg, y_other])

        agg_mean   = float(np.mean(y_agg))
        other_mean = float(np.mean(y_other))
        mean_diff  = agg_mean - other_mean

        # Welch t-test
        welch_res = stats.ttest_ind(y_agg, y_other, equal_var=False)
        welch_t   = float(welch_res.statistic)
        welch_p   = float(welch_res.pvalue)

        # OLS
        fit = simple_ols(x_binary, y_all)
        if fit is None:
            results.append(dict(zip(RESULT_FIELDS, [
                sample_type, "M_aggressive_vs_other", dv, iv_col_name,
                len(all_rows), len(rows_agg), len(rows_other),
                fmt4(agg_mean), fmt4(other_mean), fmt4(mean_diff),
                "RANK_DEFICIENT", "FAIL",
                "FAIL", "FAIL", "FAIL", "FAIL",
                fmt4(welch_t), fmt4(welch_p), "FAIL",
            ])))
            continue

        beta = fit["beta"]
        pval = fit["p"]
        flag = interp_flag(beta, pval)

        results.append({
            "sample_type":       sample_type,
            "model_name":        "M_aggressive_vs_other",
            "dv":                dv,
            "iv":                iv_col_name,
            "n":                 fit["n"],
            "aggressive_n":      len(rows_agg),
            "other_humor_n":     len(rows_other),
            "aggressive_mean":   fmt4(agg_mean),
            "other_humor_mean":  fmt4(other_mean),
            "mean_difference":   fmt4(mean_diff),
            "coefficient":       fmt4(beta),
            "p_value":           fmt4(pval),
            "r_squared":         fmt4(fit["r2"]),
            "adj_r_squared":     fmt4(fit["adj_r2"]),
            "aic":               fmt4(fit["aic"]),
            "bic":               fmt4(fit["bic"]),
            "welch_t":           fmt4(welch_t),
            "welch_p":           fmt4(welch_p),
            "interpretation_flag": flag,
        })
    return results

# ─── 6. 분석 실행 ───────────────────────────────────────────────────────────
print("[4] Model-based H2 direct test (n=564)")
mb_results = run_h2_direct(mb_agg, mb_other, "is_aggressive_humor", "model_based_n564")

print("[5] Human validation H2 direct test (n=278)")
# is_aggressive_humor는 final_humor_type_group 기반으로 in-memory에서만 구분
hv_results = run_h2_direct(hv_agg, hv_other, "final_humor_type_group_aggressive_dummy",
                            "human_validation_n278")

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

mb_primary = get_r(mb_results, "M_aggressive_vs_other", "log1p_engagement_total")
hv_primary = get_r(hv_results, "M_aggressive_vs_other", "log1p_engagement_total")

diag_rows = [
    ("model_based_humor_only_n",     len(mb_sample)),
    ("model_based_aggressive_n",     len(mb_agg)),
    ("model_based_other_humor_n",    len(mb_other)),
    ("human_validation_n",           len(hv_sample)),
    ("human_aggressive_n",           len(hv_agg)),
    ("human_other_humor_n",          len(hv_other)),
    ("non_humor_in_mb_sample",       non_in_mb),
    ("non_humor_in_hv_sample",       non_in_hv),
    ("sample_reduced_by_missing",    "no"),
    ("rank_deficient_any",           any(r.get("interpretation_flag")=="FAIL"
                                         for r in mb_results+hv_results)),
    ("log1p_view_count_used",        False),
    ("time_fe_used",                 False),
    ("post_format_controls_used",    False),
    ("year_quarter_fe_used",         False),
    ("new_vars_created",             False),
    ("H1_performed",                 False),
    ("H3_performed",                 False),
    ("original_posts_json_modified", posts_json_modified),
    ("mb_primary_dv_agg_mean",       mb_primary.get("aggressive_mean","n/a")),
    ("mb_primary_dv_other_mean",     mb_primary.get("other_humor_mean","n/a")),
    ("mb_primary_dv_mean_diff",      mb_primary.get("mean_difference","n/a")),
    ("mb_primary_dv_beta",           mb_primary.get("coefficient","n/a")),
    ("mb_primary_dv_p",              mb_primary.get("p_value","n/a")),
    ("mb_primary_dv_welch_t",        mb_primary.get("welch_t","n/a")),
    ("mb_primary_dv_welch_p",        mb_primary.get("welch_p","n/a")),
    ("mb_primary_dv_flag",           mb_primary.get("interpretation_flag","n/a")),
    ("hv_primary_dv_agg_mean",       hv_primary.get("aggressive_mean","n/a")),
    ("hv_primary_dv_other_mean",     hv_primary.get("other_humor_mean","n/a")),
    ("hv_primary_dv_mean_diff",      hv_primary.get("mean_difference","n/a")),
    ("hv_primary_dv_beta",           hv_primary.get("coefficient","n/a")),
    ("hv_primary_dv_p",              hv_primary.get("p_value","n/a")),
    ("hv_primary_dv_welch_t",        hv_primary.get("welch_t","n/a")),
    ("hv_primary_dv_welch_p",        hv_primary.get("welch_p","n/a")),
    ("hv_primary_dv_flag",           hv_primary.get("interpretation_flag","n/a")),
]

with open(DIAG_OUT, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=["metric","value"])
    w.writeheader()
    for k, v in diag_rows:
        w.writerow({"metric": k, "value": v})
print(f"  → {DIAG_OUT}")

# ─── 9. Summary Markdown ─────────────────────────────────────────────────────
print("[8] Summary 작성")

def tbl_results(results, label):
    lines = [
        "| DV | agg_mean | other_mean | diff | β | p | sig | Welch_t | Welch_p | Welch_sig | 판정 |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for r in results:
        lines.append(
            f"| {r['dv']} | {r['aggressive_mean']} | {r['other_humor_mean']} "
            f"| {r['mean_difference']} | {r['coefficient']} | {r['p_value']} "
            f"| {star(r['p_value'])} | {r['welch_t']} | {r['welch_p']} "
            f"| {star(r['welch_p'])} | {r['interpretation_flag']} |"
        )
    return "\n".join(lines)

summary_md = f"""# Wendy's H2 Step 1: Aggressive vs Other Humor Direct Test 결과

## 1. 분석 목적

H2 분석 1단계로, 전체 978건에서 예측된 model-based humor type을 기준으로 aggressive humor와 other humor 게시글의 post-level engagement를 직접 비교한다. non_humor는 이번 direct test에서 제외하였다. 시간 고정효과 및 post format controls는 이번 작업에서 추가하지 않는다.

---

## 2. H2 가설

H2: Wendy's 브랜드 게시글에서 aggressive humor는 other humor보다 post-level engagement가 높을 것이다.

판정 기준: β > 0 and p < .05 → supports_H2 / β > 0 and p < .10 → weak_support / β > 0 and p ≥ .10 → positive_not_significant / β ≤ 0 → not_support

---

## 3. 사용한 파일

| 파일 | 역할 |
|---|---|
| wendys_h3_aggressive_vs_other_intensity_dataset.csv | DV (log1p_*), is_aggressive_humor, pred_humor_type_group_model |
| wendys_humor_review_sheet.csv | final_humor_type_group (human validation용) |

---

## 4. 원본 posts.json 변경 없음 확인

data/wendys/posts.json 변경 여부: **{posts_json_modified}**

---

## 5. 새 변수 생성 없음 확인

이번 작업에서는 새로운 변수를 생성하지 않았다. is_aggressive_humor는 기존 H3 파일에 이미 존재하는 변수이다. Human validation IV는 final_humor_type_group 문자열 기반으로 in-memory에서만 구분하였으며, 새 컬럼으로 저장하지 않았다.

---

## 6. Model-based Humor-only Sample 구성

| 항목 | 값 |
|---|---|
| 전체 humor-only n | {len(mb_sample)} |
| aggressive n | {len(mb_agg)} |
| other_humor n | {len(mb_other)} |
| non_humor 포함 여부 | {non_in_mb > 0} |
| 결측으로 sample 감소 | False |
| 기준 범주 | other_humor (is_aggressive_humor=0) |

---

## 7. Human-coded Validation Sample 구성

| 항목 | 값 |
|---|---|
| 전체 human humor-only n | {len(hv_sample)} |
| aggressive n | {len(hv_agg)} |
| other_humor n | {len(hv_other)} |
| non_humor 포함 여부 | {non_in_hv > 0} |
| 결측으로 sample 감소 | False |
| 기준 범주 | other_humor |

---

## 8. Model-based H2 Direct Test 결과

**표본: n={len(mb_sample)}, IV=is_aggressive_humor, 기준=other_humor**

{tbl_results(mb_results, "model-based")}

* p<.05, ** p<.01, *** p<.001, † p<.10 (conventional SE 기준)

---

## 9. Human-coded Validation H2 결과 (부가 검증)

**표본: n={len(hv_sample)}, IV=final_humor_type_group(aggressive dummy), 기준=other_humor**

{tbl_results(hv_results, "human-coded")}

---

## 10. 평균 차이와 회귀 결과 비교 (primary DV: log1p_engagement_total)

| 표본 | agg_mean | other_mean | 차이 | β (OLS) | p | Welch_p | 판정 |
|---|---|---|---|---|---|---|---|
| model-based (n={len(mb_sample)}) | {mb_primary.get("aggressive_mean","n/a")} | {mb_primary.get("other_humor_mean","n/a")} | {mb_primary.get("mean_difference","n/a")} | {mb_primary.get("coefficient","n/a")} | {mb_primary.get("p_value","n/a")} | {mb_primary.get("welch_p","n/a")} | {mb_primary.get("interpretation_flag","n/a")} |
| human-coded (n={len(hv_sample)}) | {hv_primary.get("aggressive_mean","n/a")} | {hv_primary.get("other_humor_mean","n/a")} | {hv_primary.get("mean_difference","n/a")} | {hv_primary.get("coefficient","n/a")} | {hv_primary.get("p_value","n/a")} | {hv_primary.get("welch_p","n/a")} | {hv_primary.get("interpretation_flag","n/a")} |

OLS β와 mean_difference가 동일한 것은 단순 이진 회귀에서 상수가 other_humor 평균이고 β가 평균 차이를 나타내기 때문이다.

---

## 11. H2 주 분석 판정

**Model-based primary DV (log1p_engagement_total) 기준:**

- aggressive mean = {mb_primary.get("aggressive_mean","n/a")}
- other_humor mean = {mb_primary.get("other_humor_mean","n/a")}
- β = {mb_primary.get("coefficient","n/a")}, p = {mb_primary.get("p_value","n/a")}
- **판정: {mb_primary.get("interpretation_flag","n/a")}**

---

## 12. 사람 코딩 결과는 부가 검증

Human validation 결과(n={len(hv_sample)})는 부가 검증이며, 주 분석(model-based n={len(mb_sample)})을 대체하지 않는다.

---

## 13. Non_humor 제외 확인

H2 direct test에서 non_humor 게시글은 제외하였다. model-based 표본의 non_humor in-sample: {non_in_mb}건, human validation in-sample: {non_in_hv}건.

---

## 14. 인과관계 아님 — 관측적 연관성 분석

본 분석은 관측적 연관성 분석이며, aggressive humor 여부가 engagement를 인과적으로 증가/감소시켰다는 주장을 할 수 없다.

---

## 15. 다음 단계

다음 단계에서 시간 고정효과(created_year, created_month, created_hour FE)를 추가할 수 있으나, 사용자 승인 후 진행한다.

---

*생성일: 2026-06-15*
"""

with open(SUMMARY_OUT, "w", encoding="utf-8") as f:
    f.write(summary_md)
print(f"  → {SUMMARY_OUT}")

# ─── 10. 최종 검증 출력 ──────────────────────────────────────────────────────
print("\n" + "="*60)
print("[검증 요약]")
print(f"  model-based humor-only n={len(mb_sample)} (기대:564): {'OK' if len(mb_sample)==564 else 'FAIL'}")
print(f"  model-based aggressive n={len(mb_agg)} (기대:200): {'OK' if len(mb_agg)==200 else 'FAIL'}")
print(f"  model-based other_humor n={len(mb_other)} (기대:364): {'OK' if len(mb_other)==364 else 'FAIL'}")
print(f"  human-coded n={len(hv_sample)} (기대:278): {'OK' if len(hv_sample)==278 else 'FAIL'}")
print(f"  human agg n={len(hv_agg)} (기대:95): {'OK' if len(hv_agg)==95 else 'FAIL'}")
print(f"  human other n={len(hv_other)} (기대:183): {'OK' if len(hv_other)==183 else 'FAIL'}")
print(f"  non_humor 제외: mb={non_in_mb==0}, hv={non_in_hv==0}")
print(f"  posts.json 변경: {posts_json_modified} (기대:False)")
rank_fail = any(r.get("interpretation_flag")=="FAIL" for r in mb_results+hv_results)
print(f"  rank deficient: {rank_fail} (기대:False)")
print(f"  H1/H3: False | time_fe: False | post_format: False | 새변수: False")

print("\n[Model-based H2 — log1p_engagement_total]")
r = mb_primary
print(f"  agg_mean={r.get('aggressive_mean')}  other_mean={r.get('other_humor_mean')}  diff={r.get('mean_difference')}")
print(f"  β={r.get('coefficient')}  p={r.get('p_value')} {star(r.get('p_value',''))}  Welch_p={r.get('welch_p')} {star(r.get('welch_p',''))}")
print(f"  판정: {r.get('interpretation_flag')}")

print("\n[Human validation H2 — log1p_engagement_total]")
r = hv_primary
print(f"  agg_mean={r.get('aggressive_mean')}  other_mean={r.get('other_humor_mean')}  diff={r.get('mean_difference')}")
print(f"  β={r.get('coefficient')}  p={r.get('p_value')} {star(r.get('p_value',''))}  Welch_p={r.get('welch_p')} {star(r.get('welch_p',''))}")
print(f"  판정: {r.get('interpretation_flag')}")

print("\n[전체 DV 결과 — model-based]")
for r in mb_results:
    print(f"  {r['dv']:42s} β={r['coefficient']:8s} p={r['p_value']:8s} "
          f"{star(r['p_value']):4s} {r['interpretation_flag']}")
