"""
run_wendys_h2_step3_post_format_controls.py

목적: H2 Step 3 — aggressive vs other_humor 직접 비교에
      최종 시간 FE(year/month/hour) + post format controls(text_length, hashtag_count, mention_count)
      조합(M0~M7)을 추가하여 H2 결과가 강건한지 확인한다.

주 분석: pred_humor_type_group_model ∈ {aggressive, other_humor}, n=564
부가 검증: final_humor_type_group ∈ {aggressive, other_humor}, n=278
"""

import csv
import math
import hashlib
import os

import numpy as np
from scipy import stats

# ─── 경로 ─────────────────────────────────────────────────────────────────────
BASE       = "20260615wendy's"
DATA_DIR   = os.path.join(BASE, "data")
RESULT_DIR = os.path.join(BASE, "result")
POSTS_JSON = os.path.join("data", "wendys", "posts.json")

H3_FILE    = os.path.join(DATA_DIR,   "wendys_h3_aggressive_vs_other_intensity_dataset.csv")
HUMOR_FILE = os.path.join(DATA_DIR,   "wendys_fast_weak_supervised_humor_dataset.csv")
RV_FILE    = os.path.join(RESULT_DIR, "wendys_humor_review_sheet.csv")

DATASET_OUT = os.path.join(DATA_DIR,   "wendys_h2_step3_post_format_controls_dataset.csv")
MB_RES_OUT  = os.path.join(RESULT_DIR, "wendys_h2_step3_post_format_model_based_results.csv")
HV_RES_OUT  = os.path.join(RESULT_DIR, "wendys_h2_step3_post_format_human_validation_results.csv")
DIAG_OUT    = os.path.join(RESULT_DIR, "wendys_h2_step3_post_format_diagnostics.csv")
SUMMARY_OUT = os.path.join(RESULT_DIR, "wendys_h2_step3_post_format_summary.md")

DVS = [
    "log1p_engagement_total",
    "log1p_engagement_favorite_retweet",
    "log1p_favorite_count",
    "log1p_retweet_count",
    "log1p_reply_count",
    "log1p_quote_count",
    "log1p_bookmark_count",
]

POST_FORMAT_VARS = ["text_length", "hashtag_count", "mention_count"]

MODEL_SPECS = [
    ("M0_time_fe_only",               [],                                         0, "none"),
    ("M1_time_fe_text",               ["text_length"],                            1, "text_length"),
    ("M2_time_fe_hashtag",            ["hashtag_count"],                          1, "hashtag_count"),
    ("M3_time_fe_mention",            ["mention_count"],                          1, "mention_count"),
    ("M4_time_fe_text_hashtag",       ["text_length","hashtag_count"],            2, "text_length+hashtag_count"),
    ("M5_time_fe_text_mention",       ["text_length","mention_count"],            2, "text_length+mention_count"),
    ("M6_time_fe_hashtag_mention",    ["hashtag_count","mention_count"],          2, "hashtag_count+mention_count"),
    ("M7_time_fe_all_post_format",    ["text_length","hashtag_count","mention_count"], 3, "text_length+hashtag_count+mention_count"),
]
MODEL_ORDER = [s[0] for s in MODEL_SPECS]

RESULT_FIELDS = [
    "sample_type", "model_name", "dv", "iv",
    "n", "aggressive_n", "other_humor_n",
    "aggressive_mean", "other_humor_mean", "mean_difference",
    "coefficient", "p_value",
    "r_squared", "adj_r_squared", "aic", "bic",
    "included_time_fe", "included_post_format_variables",
    "number_of_post_format_variables",
    "interpretation_flag",
]

# ─── 유틸 ─────────────────────────────────────────────────────────────────────
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

# ─── 0. posts.json 보호 ───────────────────────────────────────────────────────
print("[0] posts.json 보호 확인")
hash_before = None
try:
    with open(POSTS_JSON, "rb") as f:
        hash_before = hashlib.md5(f.read()).hexdigest()
    print(f"  md5: {hash_before}")
except FileNotFoundError:
    print("  posts.json 없음 (정상)")

# ─── 1. 데이터 로드 및 병합 ──────────────────────────────────────────────────
print("[1] 데이터 로드 및 병합")
with open(H3_FILE, newline="", encoding="utf-8") as f:
    h3_rows = list(csv.DictReader(f))
with open(HUMOR_FILE, newline="", encoding="utf-8") as f:
    humor_map = {r["id"]: r for r in csv.DictReader(f)}
with open(RV_FILE, newline="", encoding="utf-8") as f:
    rv_map = {r["id"]: r for r in csv.DictReader(f)}

left_n  = len(h3_rows)
right_n = len(humor_map)
h3_ids  = [r["id"] for r in h3_rows]
dup_h3  = len(h3_ids) != len(set(h3_ids))
dup_hr  = len(humor_map) != len(set(humor_map.keys()))
unmatched_pf  = [i for i in h3_ids if i not in humor_map]
unmatched_rv  = [i for i in h3_ids if i not in rv_map]

print(f"  H3 n={left_n}(dup={dup_h3}), humor n={right_n}(dup={dup_hr})")
print(f"  unmatched H3->humor={len(unmatched_pf)}, H3->rv={len(unmatched_rv)}")

if unmatched_pf or unmatched_rv or dup_h3 or dup_hr:
    print("  ERROR: 병합 불안정 — 중단")
    raise SystemExit(1)

# 병합
merged_all = []
for r in h3_rows:
    base = dict(r)
    base["text_length"]   = humor_map[r["id"]]["text_length"]
    base["hashtag_count"] = humor_map[r["id"]]["hashtag_count"]
    base["mention_count"] = humor_map[r["id"]]["mention_count"]
    base["final_humor_type_group"] = rv_map[r["id"]].get("final_humor_type_group", "")
    merged_all.append(base)

merged_n = len(merged_all)
print(f"  병합 후 n={merged_n} (기대:978)")
assert merged_n == 978

# 결측 확인
pf_miss = {v: sum(1 for r in merged_all if safe_float(r.get(v,"")) is None)
           for v in POST_FORMAT_VARS}
print(f"  post format 결측: {pf_miss}")
if any(v > 0 for v in pf_miss.values()):
    print("  ERROR: post format 결측 존재 — 중단")
    raise SystemExit(1)

# ─── 2. 표본 필터링 ──────────────────────────────────────────────────────────
print("[2] H2 표본 필터링")

mb_sample = [r for r in merged_all
             if r.get("pred_humor_type_group_model") in ("aggressive", "other_humor")]
mb_agg    = [r for r in mb_sample if r.get("is_aggressive_humor") == "1"]
mb_other  = [r for r in mb_sample if r.get("is_aggressive_humor") == "0"]

hv_sample = [r for r in merged_all
             if r.get("final_humor_type_group") in ("aggressive", "other_humor")]
hv_agg    = [r for r in hv_sample if r.get("final_humor_type_group") == "aggressive"]
hv_other  = [r for r in hv_sample if r.get("final_humor_type_group") == "other_humor"]

non_in_mb = sum(1 for r in mb_sample if r.get("pred_humor_type_group_model") == "non_humor")
non_in_hv = sum(1 for r in hv_sample if r.get("final_humor_type_group") == "non_humor")

print(f"  mb: n={len(mb_sample)}, agg={len(mb_agg)}, other={len(mb_other)}, non_humor={non_in_mb}")
print(f"  hv: n={len(hv_sample)}, agg={len(hv_agg)}, other={len(hv_other)}, non_humor={non_in_hv}")

assert len(mb_sample)==564 and len(mb_agg)==200 and len(mb_other)==364
assert len(hv_sample)==278 and len(hv_agg)==95  and len(hv_other)==183

# post format 추가로 인한 sample size 변화 없음 확인 (결측 없음)
mb_with_pf = [r for r in mb_sample
              if all(safe_float(r.get(v,"")) is not None for v in POST_FORMAT_VARS)]
hv_with_pf = [r for r in hv_sample
              if all(safe_float(r.get(v,"")) is not None for v in POST_FORMAT_VARS)]
print(f"  post format 추가 후 mb n={len(mb_with_pf)}, hv n={len(hv_with_pf)}")
assert len(mb_with_pf)==564 and len(hv_with_pf)==278

# ─── 3. Dataset 저장 ──────────────────────────────────────────────────────────
print("[3] Dataset 저장")
with open(DATASET_OUT, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(merged_all[0].keys()), extrasaction="ignore")
    w.writeheader(); w.writerows(merged_all)
print(f"  → {DATASET_OUT}")

# ─── 4. OLS 인프라 ───────────────────────────────────────────────────────────
def make_X(rows, iv_col, year_dummies, month_dummies, hour_dummies, pf_vars):
    n = len(rows)
    cols, labels = [np.ones(n)], ["_const"]
    # IV
    cols.append(np.array([safe_float(r.get(iv_col, "")) or 0.0 for r in rows]))
    labels.append(iv_col)
    # Year FE
    for y in year_dummies:
        cols.append(np.array([1.0 if r["created_year"] == y else 0.0 for r in rows]))
        labels.append(f"year_{y}")
    # Month FE
    for m in month_dummies:
        cols.append(np.array([1.0 if r["created_month"] == m else 0.0 for r in rows]))
        labels.append(f"month_{m}")
    # Hour FE
    for h in hour_dummies:
        cols.append(np.array([1.0 if r["created_hour"] == h else 0.0 for r in rows]))
        labels.append(f"hour_{h}")
    # Post format
    for v in pf_vars:
        cols.append(np.array([safe_float(r.get(v, "")) or 0.0 for r in rows]))
        labels.append(v)
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
    se    = np.sqrt(np.maximum(np.diag(mse * XtXinv), 0.0))
    t     = np.where(se > 0, coef / se, float("nan"))
    pval  = np.array([
        2 * float(stats.t.sf(abs(t[i]), df=df_r))
        if df_r > 0 and not math.isnan(t[i]) else float("nan")
        for i in range(p)
    ])
    return dict(coef=coef, pval=pval, r2=r2, adj_r2=adj_r2, aic=aic, bic=bic, n=n)

# ─── 5. 회귀 실행 함수 ───────────────────────────────────────────────────────
def run_models(rows_agg, rows_other, iv_col, sample_type):
    rows = rows_agg + rows_other

    all_years  = sorted_unique(rows, "created_year")
    all_months = sorted_unique(rows, "created_month", as_int=True)
    all_hours  = sorted_unique(rows, "created_hour",  as_int=True)
    YD = [y for y in all_years  if y != all_years[0]]
    MD = [m for m in all_months if m != all_months[0]]
    HD = [h for h in all_hours  if h != all_hours[0]]

    print(f"  [{sample_type}] n={len(rows)}, base year={all_years[0]}, month={all_months[0]}, hour={all_hours[0]}")
    print(f"    time FE dummies: year({len(YD)}), month({len(MD)}), hour({len(HD)})")

    agg_means   = {dv: float(np.mean([safe_float(r.get(dv,"")) or 0.0 for r in rows_agg])) for dv in DVS}
    other_means = {dv: float(np.mean([safe_float(r.get(dv,"")) or 0.0 for r in rows_other])) for dv in DVS}

    results = []
    for dv in DVS:
        y = np.array([safe_float(r.get(dv,"")) or 0.0 for r in rows])

        for mname, pf_vars, n_pf, pf_desc in MODEL_SPECS:
            X, labels = make_X(rows, iv_col, YD, MD, HD, pf_vars)
            fit = ols_fit(X, y)

            if fit is None:
                results.append({f: "FAIL" for f in RESULT_FIELDS})
                results[-1].update(dict(
                    sample_type=sample_type, model_name=mname, dv=dv, iv=iv_col,
                    n=len(rows), aggressive_n=len(rows_agg), other_humor_n=len(rows_other),
                    included_time_fe="year_FE+month_FE+hour_FE",
                    included_post_format_variables=pf_desc if pf_desc!="none" else "none",
                    number_of_post_format_variables=n_pf,
                    interpretation_flag="RANK_DEFICIENT",
                ))
                continue

            iv_idx = labels.index(iv_col)
            beta = float(fit["coef"][iv_idx])
            pval = float(fit["pval"][iv_idx])

            results.append({
                "sample_type":                   sample_type,
                "model_name":                    mname,
                "dv":                            dv,
                "iv":                            iv_col,
                "n":                             fit["n"],
                "aggressive_n":                  len(rows_agg),
                "other_humor_n":                 len(rows_other),
                "aggressive_mean":               fmt4(agg_means[dv]),
                "other_humor_mean":              fmt4(other_means[dv]),
                "mean_difference":               fmt4(agg_means[dv]-other_means[dv]),
                "coefficient":                   fmt4(beta),
                "p_value":                       fmt4(pval),
                "r_squared":                     fmt4(fit["r2"]),
                "adj_r_squared":                 fmt4(fit["adj_r2"]),
                "aic":                           fmt4(fit["aic"]),
                "bic":                           fmt4(fit["bic"]),
                "included_time_fe":              "year_FE+month_FE+hour_FE",
                "included_post_format_variables": pf_desc if pf_desc != "none" else "none",
                "number_of_post_format_variables": n_pf,
                "interpretation_flag":           interp_flag(beta, pval),
            })
    return results

# ─── 6. 분석 실행 ─────────────────────────────────────────────────────────────
print("[4] Model-based H2 (n=564)")
mb_results = run_models(mb_agg, mb_other, "is_aggressive_humor", "model_based_n564")

print("[5] Human validation H2 (n=278)")
for r in hv_sample:
    r["_hv_agg_dummy"] = "1" if r.get("final_humor_type_group") == "aggressive" else "0"
hv_agg_list   = [r for r in hv_sample if r["_hv_agg_dummy"] == "1"]
hv_other_list = [r for r in hv_sample if r["_hv_agg_dummy"] == "0"]
hv_results = run_models(hv_agg_list, hv_other_list, "_hv_agg_dummy", "human_validation_n278")

# ─── 7. 결과 저장 ─────────────────────────────────────────────────────────────
print("[6] 결과 저장")
for path, res in [(MB_RES_OUT, mb_results), (HV_RES_OUT, hv_results)]:
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=RESULT_FIELDS)
        w.writeheader(); w.writerows(res)
    print(f"  → {path} ({len(res)}건)")

# ─── 8. Diagnostics ──────────────────────────────────────────────────────────
print("[7] Diagnostics")
posts_json_modified = False
if hash_before:
    try:
        with open(POSTS_JSON, "rb") as f:
            h_now = hashlib.md5(f.read()).hexdigest()
        posts_json_modified = (h_now != hash_before)
    except FileNotFoundError:
        pass

mb_m0 = get_r(mb_results, "M0_time_fe_only",          "log1p_engagement_total")
mb_m7 = get_r(mb_results, "M7_time_fe_all_post_format","log1p_engagement_total")
hv_m0 = get_r(hv_results, "M0_time_fe_only",          "log1p_engagement_total")
hv_m7 = get_r(hv_results, "M7_time_fe_all_post_format","log1p_engagement_total")

rank_fail = any(r.get("interpretation_flag") in ("FAIL","RANK_DEFICIENT")
                for r in mb_results + hv_results)

view_count_used   = "log1p_view_count" in DVS
emoji_used        = any("emoji_count" in str(list(r.keys())) for r in mb_results[:1])
url_used          = any("url_count" in str(list(r.keys())) for r in mb_results[:1])
is_quote_used     = "is_quote_status" in POST_FORMAT_VARS
is_retweet_used   = "is_retweet_text" in POST_FORMAT_VARS
day_of_week_used  = False
posting_int_used  = any(v in ("quarter_aggressive_posts","quarter_other_humor_posts",
                               "aggressive_humor_frequency_quarter")
                        for v in POST_FORMAT_VARS)
year_quarter_used = False

diag_rows = [
    ("merge_key", "id"),
    ("left_n_h3", left_n),
    ("right_n_humor", right_n),
    ("merged_n", merged_n),
    ("unmatched_h3_to_humor", len(unmatched_pf)),
    ("unmatched_h3_to_rv", len(unmatched_rv)),
    ("dup_h3_key", dup_h3),
    ("dup_humor_key", dup_hr),
    ("model_based_humor_only_n", len(mb_sample)),
    ("model_based_aggressive_n", len(mb_agg)),
    ("model_based_other_humor_n", len(mb_other)),
    ("human_validation_n", len(hv_sample)),
    ("human_aggressive_n", len(hv_agg)),
    ("human_other_humor_n", len(hv_other)),
    ("mb_n_unchanged_after_pf_join", len(mb_with_pf)==564),
    ("hv_n_unchanged_after_pf_join", len(hv_with_pf)==278),
    ("non_humor_in_mb", non_in_mb),
    ("non_humor_in_hv", non_in_hv),
    ("text_length_missing", pf_miss["text_length"]),
    ("hashtag_count_missing", pf_miss["hashtag_count"]),
    ("mention_count_missing", pf_miss["mention_count"]),
    ("emoji_count_used", emoji_used),
    ("url_count_used", url_used),
    ("is_quote_status_used", is_quote_used),
    ("is_retweet_text_used", is_retweet_used),
    ("day_of_week_used", day_of_week_used),
    ("posting_intensity_used", posting_int_used),
    ("log1p_view_count_used", view_count_used),
    ("year_quarter_fe_used", year_quarter_used),
    ("time_fe_vars", "created_year+created_month+created_hour"),
    ("post_format_vars", "text_length+hashtag_count+mention_count"),
    ("H1_performed", False),
    ("H3_performed", False),
    ("new_vars_created", False),
    ("rank_deficient_any", rank_fail),
    ("original_posts_json_modified", posts_json_modified),
    ("mb_M0_beta", mb_m0.get("coefficient","n/a")),
    ("mb_M0_p",    mb_m0.get("p_value","n/a")),
    ("mb_M0_flag", mb_m0.get("interpretation_flag","n/a")),
    ("mb_M7_beta", mb_m7.get("coefficient","n/a")),
    ("mb_M7_p",    mb_m7.get("p_value","n/a")),
    ("mb_M7_flag", mb_m7.get("interpretation_flag","n/a")),
    ("hv_M0_beta", hv_m0.get("coefficient","n/a")),
    ("hv_M0_p",    hv_m0.get("p_value","n/a")),
    ("hv_M7_beta", hv_m7.get("coefficient","n/a")),
    ("hv_M7_p",    hv_m7.get("p_value","n/a")),
]

with open(DIAG_OUT, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=["metric","value"])
    w.writeheader()
    for k, v in diag_rows:
        w.writerow({"metric": k, "value": v})
print(f"  → {DIAG_OUT}")

# ─── 9. Summary Markdown ──────────────────────────────────────────────────────
print("[8] Summary 작성")

def tbl_by_model(results, dv="log1p_engagement_total"):
    rows_dv = [r for r in results if r["dv"]==dv]
    rows_dv.sort(key=lambda r: MODEL_ORDER.index(r["model_name"]) if r["model_name"] in MODEL_ORDER else 99)
    lines = [
        "| n_pf | model | post_format_vars | β | p | sig | R² | adj_R² | 판정 |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for r in rows_dv:
        lines.append(
            f"| {r['number_of_post_format_variables']} | {r['model_name']} "
            f"| {r['included_post_format_variables']} "
            f"| {r['coefficient']} | {r['p_value']} | {star(r['p_value'])} "
            f"| {r['r_squared']} | {r['adj_r_squared']} | {r['interpretation_flag']} |"
        )
    return "\n".join(lines)

def tbl_m7_all_dv(results, model="M7_time_fe_all_post_format"):
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
        "| n_pf | model | mb_β | mb_p | mb_sig | hv_β | hv_p | hv_sig |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for mname in MODEL_ORDER:
        rm = get_r(mb, mname, dv)
        rh = get_r(hv, mname, dv)
        lines.append(
            f"| {rm.get('number_of_post_format_variables','')} | {mname} "
            f"| {rm.get('coefficient','')} | {rm.get('p_value','')} | {star(rm.get('p_value',''))} "
            f"| {rh.get('coefficient','')} | {rh.get('p_value','')} | {star(rh.get('p_value',''))} |"
        )
    return "\n".join(lines)

summary_md = f"""# Wendy's H2 Step 3: Aggressive vs Other Humor — Post Format Controls 결과

## 1. 분석 목적

H2 Step 2에서 year/month/hour FE를 모두 추가한 이후에도 aggressive humor > other humor 관계가 유지되었다. Step 3에서는 문헌 기반 post format controls(text_length, hashtag_count, mention_count)를 8개 조합(M0~M7)으로 투입하여 H2 관계의 강건성을 추가 확인한다.

---

## 2. H2 가설

H2: Wendy's 브랜드 게시글에서 aggressive humor는 other humor보다 post-level engagement가 높을 것이다.

---

## 3. 사용한 파일

| 파일 | 역할 |
|---|---|
| wendys_h3_aggressive_vs_other_intensity_dataset.csv | DV, is_aggressive_humor, 시간 변수 |
| wendys_fast_weak_supervised_humor_dataset.csv | text_length, hashtag_count, mention_count |
| wendys_humor_review_sheet.csv | final_humor_type_group (human validation) |

---

## 4. 병합 안정성

| 항목 | 값 |
|---|---|
| 병합 key | id |
| left n (H3) | {left_n} |
| right n (humor dataset) | {right_n} |
| merged n | {merged_n} |
| unmatched (H3→humor) | {len(unmatched_pf)} |
| unmatched (H3→rv) | {len(unmatched_rv)} |
| duplicate key (H3) | {dup_h3} |
| duplicate key (humor) | {dup_hr} |
| mb n 변화 | {len(mb_with_pf)} (기대 564) |
| hv n 변화 | {len(hv_with_pf)} (기대 278) |

병합 결과 안정적. sample size 변화 없음.

---

## 5. 원본 posts.json 변경 없음 확인

data/wendys/posts.json 변경 여부: **{posts_json_modified}**

---

## 6. 새 변수 생성 없음 확인

text_length, hashtag_count, mention_count은 기존 wendys_fast_weak_supervised_humor_dataset.csv의 변수이다. is_aggressive_humor는 기존 H3 파일 변수이다. human validation IV는 in-memory에서만 사용하였다. 새 변수 생성 없음.

---

## 7. Model-based Humor-only Sample 구성

| 항목 | 값 |
|---|---|
| n | {len(mb_agg)+len(mb_other)} |
| aggressive n | {len(mb_agg)} |
| other_humor n | {len(mb_other)} |
| non_humor 포함 | {non_in_mb>0} |
| 기준 범주 | other_humor (is_aggressive_humor=0) |

---

## 8. Human-coded Validation Sample 구성

| 항목 | 값 |
|---|---|
| n | {len(hv_agg)+len(hv_other)} |
| aggressive n | {len(hv_agg)} |
| other_humor n | {len(hv_other)} |
| non_humor 포함 | {non_in_hv>0} |

---

## 9. 사용한 시간 고정효과

created_year FE, created_month FE, created_hour FE (전체 조합, M0~M7 공통)

---

## 10. 사용한 Post Format 변수

| 변수 | 결측 |
|---|---|
| text_length | {pf_miss['text_length']}건 |
| hashtag_count | {pf_miss['hashtag_count']}건 |
| mention_count | {pf_miss['mention_count']}건 |

---

## 11. 제외한 변수

emoji_count, url_count, is_quote_status, is_retweet_text, day_of_week, log1p_view_count, year_quarter FE, posting intensity 변수 전체 미사용.

---

## 12. Model-based H2 결과 (primary DV: log1p_engagement_total)

**표본: n={len(mb_agg)+len(mb_other)}, IV=is_aggressive_humor, 기준=other_humor**

{tbl_by_model(mb_results, "log1p_engagement_total")}

* p<.05, ** p<.01, *** p<.001, † p<.10 (conventional SE 기준)

---

## 13. Model-based M7 기준 전체 DV

{tbl_m7_all_dv(mb_results, "M7_time_fe_all_post_format")}

---

## 14. Human-coded Validation 결과 (primary DV, 부가 검증)

**표본: n={len(hv_agg)+len(hv_other)}, IV=final_humor_type_group(aggressive dummy)**

{tbl_by_model(hv_results, "log1p_engagement_total")}

---

## 15. Human-coded Validation M7 기준 전체 DV

{tbl_m7_all_dv(hv_results, "M7_time_fe_all_post_format")}

---

## 16. Time FE only 대비 Post Format 추가 후 β, p-value 변화 (primary DV)

{change_tbl(mb_results, hv_results, "log1p_engagement_total")}

mb=model_based, hv=human_validation

---

## 17. H2 주 분석 판정

**Model-based M7 (Time FE + all post format controls) 기준:**

| 표본 | β | p | 판정 |
|---|---|---|---|
| Model-based (n={len(mb_agg)+len(mb_other)}) | {mb_m7.get("coefficient","n/a")} | {mb_m7.get("p_value","n/a")} | {mb_m7.get("interpretation_flag","n/a")} |
| Human validation (n={len(hv_agg)+len(hv_other)}) | {hv_m7.get("coefficient","n/a")} | {hv_m7.get("p_value","n/a")} | {hv_m7.get("interpretation_flag","n/a")} |

---

## 18. 사람 코딩 결과는 부가 검증

Human validation 결과(n={len(hv_sample)})는 부가 검증이다. primary evidence는 model-based 결과이며, 사람 코딩은 전체 데이터 분류의 기준 라벨 및 검증층으로 해석한다.

---

## 19. Non_humor 제외 확인

H2 direct test에서 non_humor는 제외하였다. model-based in-sample: {non_in_mb}건, human validation in-sample: {non_in_hv}건.

---

## 20. 인과관계 아님 — 관측적 연관성 분석

본 분석은 관측적 연관성 분석이며, aggressive humor 여부가 engagement를 인과적으로 변화시켰다는 주장을 할 수 없다.

---

## 21. H1/H3 수행하지 않음 확인

이번 작업에서 H1 및 H3 분석은 수행하지 않았다. H2 direct test만 실시하였다.

---

## 22. 다음 단계

다음 단계는 사용자 승인 후 결정한다.

---

*생성일: 2026-06-15*
"""

with open(SUMMARY_OUT, "w", encoding="utf-8") as f:
    f.write(summary_md)
print(f"  → {SUMMARY_OUT}")

# ─── 10. 최종 검증 출력 ───────────────────────────────────────────────────────
print("\n" + "="*60)
print("[검증 요약]")
print(f"  병합 안정: left={left_n}, right={right_n}, merged={merged_n}, unmatched={len(unmatched_pf)}")
print(f"  mb n=564: {'OK' if len(mb_sample)==564 else 'FAIL'}, agg=200: {'OK' if len(mb_agg)==200 else 'FAIL'}, other=364: {'OK' if len(mb_other)==364 else 'FAIL'}")
print(f"  hv n=278: {'OK' if len(hv_sample)==278 else 'FAIL'}, agg=95: {'OK' if len(hv_agg)==95 else 'FAIL'}, other=183: {'OK' if len(hv_other)==183 else 'FAIL'}")
print(f"  non_humor 제외: mb={non_in_mb==0}, hv={non_in_hv==0}")
print(f"  posts.json 변경: {posts_json_modified} (기대:False)")
print(f"  rank deficient: {rank_fail} (기대:False)")
print(f"  view_count 사용: {view_count_used} | emoji: False | url: False | H1/H3: False | 새변수: False")
print(f"  text_length/hashtag_count/mention_count 결측: {list(pf_miss.values())}")

print("\n[Model-based primary DV — log1p_engagement_total]")
for mname in MODEL_ORDER:
    r = get_r(mb_results, mname, "log1p_engagement_total")
    n_pf = r.get("number_of_post_format_variables","")
    print(f"  n_pf={n_pf} {r.get('model_name',''):36s} "
          f"β={r.get('coefficient',''):8s} p={r.get('p_value',''):8s} "
          f"{star(r.get('p_value','')):4s} {r.get('interpretation_flag','')}")

print("\n[Human validation primary DV]")
for mname in MODEL_ORDER:
    r = get_r(hv_results, mname, "log1p_engagement_total")
    n_pf = r.get("number_of_post_format_variables","")
    print(f"  n_pf={n_pf} {r.get('model_name',''):36s} "
          f"β={r.get('coefficient',''):8s} p={r.get('p_value',''):8s} "
          f"{star(r.get('p_value','')):4s} {r.get('interpretation_flag','')}")
