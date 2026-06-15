"""
run_wendys_h1_literature_post_format_controls.py

목적: H1 분석에서 시간 FE(year+month+hour) 기반 모형에 문헌 기반 post format 변수
      (text_length, hashtag_count, mention_count, emoji_count)를 순차적으로 추가.

주 분석: full-sample (n=978) — pred_humor_final_050, p_humor_final_tfidf_logreg
부가 검증: human-labeled (n=597) — final_humor_binary

새 변수 생성 없음. H2/H3 수행 없음. posts.json 수정 없음.

모형:
  M0: humor + year_FE + month_FE + hour_FE
  M1: M0 + text_length
  M2: M1 + hashtag_count
  M3: M2 + mention_count
  M4: M3 + emoji_count
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

PRED_FILE  = os.path.join(RESULT_DIR, "wendys_final_humor_presence_full_predictions.csv")
H3_FILE    = os.path.join(DATA_DIR,   "wendys_h3_aggressive_vs_other_intensity_dataset.csv")
FAST_FILE  = os.path.join(DATA_DIR,   "wendys_fast_weak_supervised_humor_dataset.csv")

DATASET_OUT   = os.path.join(DATA_DIR,   "wendys_h1_literature_post_format_dataset.csv")
FB_RES_OUT    = os.path.join(RESULT_DIR, "wendys_h1_literature_post_format_fullsample_binary_results.csv")
FP_RES_OUT    = os.path.join(RESULT_DIR, "wendys_h1_literature_post_format_fullsample_probability_results.csv")
HV_RES_OUT    = os.path.join(RESULT_DIR, "wendys_h1_literature_post_format_human_validation_results.csv")
DIAG_OUT      = os.path.join(RESULT_DIR, "wendys_h1_literature_post_format_diagnostics.csv")
SUMMARY_OUT   = os.path.join(RESULT_DIR, "wendys_h1_literature_post_format_summary.md")

DVS = [
    "log1p_engagement_total",
    "log1p_engagement_favorite_retweet",
    "log1p_favorite_count",
    "log1p_retweet_count",
    "log1p_reply_count",
    "log1p_quote_count",
    "log1p_bookmark_count",
]

POST_FORMAT_VARS = ["text_length", "hashtag_count", "mention_count", "emoji_count"]

RESULT_FIELDS = [
    "sample_type", "model_name", "dv", "iv", "n",
    "coefficient", "p_value",
    "r_squared", "adj_r_squared", "aic", "bic",
    "included_time_fe", "included_post_format_variables",
    "number_of_post_format_variables", "interpretation_flag",
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
print("[1] 데이터 로드 및 병합 확인")
with open(PRED_FILE, newline="", encoding="utf-8") as f:
    pred_rows = list(csv.DictReader(f))
with open(H3_FILE, newline="", encoding="utf-8") as f:
    h3_map = {r["id"]: r for r in csv.DictReader(f)}
with open(FAST_FILE, newline="", encoding="utf-8") as f:
    fast_map = {r["id"]: r for r in csv.DictReader(f)}

print(f"  pred n={len(pred_rows)}, h3 n={len(h3_map)}, fast n={len(fast_map)}")
print(f"  pred ∩ h3:   {sum(1 for r in pred_rows if r['id'] in h3_map)}")
print(f"  pred ∩ fast: {sum(1 for r in pred_rows if r['id'] in fast_map)}")
unmatched_h3   = [r['id'] for r in pred_rows if r['id'] not in h3_map]
unmatched_fast = [r['id'] for r in pred_rows if r['id'] not in fast_map]
print(f"  unmatched h3: {len(unmatched_h3)}, fast: {len(unmatched_fast)}")
if unmatched_h3 or unmatched_fast:
    print("  ERROR: 병합 불안정 — 중단")
    raise SystemExit(1)

# duplicate key 확인
pred_ids = [r['id'] for r in pred_rows]
dup_pred = len(pred_ids) != len(set(pred_ids))
dup_h3   = len(h3_map) != len(list(h3_map.keys()))
dup_fast = len(fast_map) != len(list(fast_map.keys()))
print(f"  duplicate keys — pred:{dup_pred}, h3:{dup_h3}, fast:{dup_fast}")
if dup_pred or dup_h3 or dup_fast:
    print("  ERROR: duplicate key 존재 — 중단")
    raise SystemExit(1)

# 3-way 병합: h3 기본 + pred 덮어쓰기 + fast 중 post format 변수만 추가
FAST_COLS_TO_ADD = POST_FORMAT_VARS  # text_length, hashtag_count, mention_count, emoji_count
merged = []
for pr in pred_rows:
    pid = pr["id"]
    base = dict(h3_map[pid])
    for k, v in pr.items():
        base[k] = v
    for col in FAST_COLS_TO_ADD:
        base[col] = fast_map[pid].get(col, "")
    merged.append(base)

assert len(merged) == 978, f"전체 n 오류: {len(merged)}"
primary = [r for r in merged if r.get("final_humor_label_available") == "1"]
assert len(primary) == 597, f"primary n 오류: {len(primary)}"
print(f"  3-way 병합 완료: full n={len(merged)}, primary n={len(primary)}")

# post format 변수 결측 확인
for col in POST_FORMAT_VARS:
    missing = sum(1 for r in merged if r.get(col, "") in ("", None, "nan"))
    print(f"  {col}: missing={missing}/{len(merged)}")
if any(sum(1 for r in merged if r.get(col, "") in ("", None, "nan")) > 0 for col in POST_FORMAT_VARS):
    print("  ERROR: post format 변수 결측 존재 — 중단")
    raise SystemExit(1)

# ─── 2. Dataset 저장 ─────────────────────────────────────────────────────
print("[2] Dataset 저장")
with open(DATASET_OUT, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(merged[0].keys()), extrasaction="ignore")
    w.writeheader(); w.writerows(merged)
print(f"  → {DATASET_OUT}")

# ─── 3. OLS 인프라 ──────────────────────────────────────────────────────
def make_X(rows, iv_col, year_dummies, month_dummies, hour_dummies, format_vars=None):
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
    for fv in (format_vars or []):
        cols.append(np.array([safe_float(r.get(fv, "")) or 0.0 for r in rows]))
        labels.append(fv)
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
def run_post_format_models(rows, iv_col, sample_type):
    all_years  = sorted_unique(rows, "created_year")
    all_months = sorted_unique(rows, "created_month", as_int=True)
    all_hours  = sorted_unique(rows, "created_hour",  as_int=True)

    YD = [y for y in all_years  if y != all_years[0]]
    MD = [m for m in all_months if m != all_months[0]]
    HD = [h for h in all_hours  if h != all_hours[0]]

    print(f"  [{sample_type}] base year={all_years[0]}, month={all_months[0]}, hour={all_hours[0]}")
    print(f"    year_dummies({len(YD)}), month_dummies({len(MD)}), hour_dummies({len(HD)})")

    # M0~M4: post format 변수 누적 추가
    model_specs = [
        ("M0_time_fe_only",         [],                                                     0),
        ("M1_add_text_length",      ["text_length"],                                        1),
        ("M2_add_hashtag",          ["text_length","hashtag_count"],                        2),
        ("M3_add_mention",          ["text_length","hashtag_count","mention_count"],         3),
        ("M4_add_emoji",            ["text_length","hashtag_count","mention_count","emoji_count"], 4),
    ]

    results = []
    for dv in DVS:
        y = np.array([safe_float(r.get(dv, "")) or 0.0 for r in rows])

        for mname, fmt_vars, n_fmt in model_specs:
            fe_desc  = "year_FE+month_FE+hour_FE"
            fmt_desc = "+".join(fmt_vars) if fmt_vars else "none"

            X, labels = make_X(rows, iv_col, YD, MD, HD, fmt_vars if fmt_vars else None)
            fit = ols_fit(X, y)

            if fit is None:
                results.append(dict(zip(RESULT_FIELDS, [
                    sample_type, mname, dv, iv_col, len(rows),
                    "RANK_DEFICIENT", "FAIL",
                    "FAIL", "FAIL", "FAIL", "FAIL",
                    fe_desc, fmt_desc, n_fmt, "FAIL",
                ])))
                continue

            iv_idx = labels.index(iv_col)
            beta = float(fit["coef"][iv_idx])
            pval = float(fit["pval"][iv_idx])

            results.append({
                "sample_type":                  sample_type,
                "model_name":                   mname,
                "dv":                           dv,
                "iv":                           iv_col,
                "n":                            fit["n"],
                "coefficient":                  fmt4(beta),
                "p_value":                      fmt4(pval),
                "r_squared":                    fmt4(fit["r2"]),
                "adj_r_squared":                fmt4(fit["adj_r2"]),
                "aic":                          fmt4(fit["aic"]),
                "bic":                          fmt4(fit["bic"]),
                "included_time_fe":             fe_desc,
                "included_post_format_variables": fmt_desc,
                "number_of_post_format_variables": n_fmt,
                "interpretation_flag":          interp_flag(beta, pval),
            })
    return results

# ─── 5. 분석 실행 ───────────────────────────────────────────────────────────
print("[3] Full-sample binary H1 (n=978, IV=pred_humor_final_050)")
fb_results = run_post_format_models(merged, "pred_humor_final_050", "fullsample_binary_n978")

print("[4] Full-sample probability H1 (n=978, IV=p_humor_final_tfidf_logreg)")
fp_results = run_post_format_models(merged, "p_humor_final_tfidf_logreg", "probability_n978")

print("[5] Human-labeled validation H1 (n=597, IV=final_humor_binary)")
hv_results = run_post_format_models(primary, "final_humor_binary", "human_validation_n597")

# ─── 6. 결과 저장 ───────────────────────────────────────────────────────────
print("[6] 결과 저장")
for path, res in [
    (FB_RES_OUT, fb_results),
    (FP_RES_OUT, fp_results),
    (HV_RES_OUT, hv_results),
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
    ("full_n",                       len(merged)),
    ("primary_n",                    len(primary)),
    ("full_predicted_humor_1",       sum(1 for r in merged if r.get("pred_humor_final_050")=="1")),
    ("full_predicted_humor_0",       sum(1 for r in merged if r.get("pred_humor_final_050")=="0")),
    ("human_humor_1",                sum(1 for r in primary if r.get("final_humor_binary")=="1")),
    ("human_humor_0",                sum(1 for r in primary if r.get("final_humor_binary")=="0")),
    ("merge_key",                    "id"),
    ("pred_n_before_merge",          len(pred_rows)),
    ("h3_n_before_merge",            len(h3_map)),
    ("fast_n_before_merge",          len(fast_map)),
    ("merged_n",                     len(merged)),
    ("unmatched_h3",                 len(unmatched_h3)),
    ("unmatched_fast",               len(unmatched_fast)),
    ("duplicate_key_pred",           dup_pred),
    ("duplicate_key_h3",             dup_h3),
    ("duplicate_key_fast",           dup_fast),
    ("full_n_maintained",            len(merged)==978),
    ("primary_n_maintained",         len(primary)==597),
]
for col in POST_FORMAT_VARS:
    miss = sum(1 for r in merged if r.get(col, "") in ("", None, "nan"))
    diag_rows.append((f"{col}_missing", miss))
    diag_rows.append((f"{col}_sample_reduced", miss > 0))

diag_rows += [
    ("sample_reduced_by_post_format", False),
    ("rank_deficient_any",           any(r.get("interpretation_flag")=="FAIL"
                                         for r in fb_results+fp_results+hv_results)),
    ("se_type",                      "conventional_MSE"),
    ("url_count_used",               False),
    ("is_quote_status_used",         False),
    ("is_retweet_text_used",         False),
    ("view_count_used",              False),
    ("year_quarter_fe_used",         False),
    ("day_of_week_created",          False),
    ("image_video_vars_used",        False),
    ("H2_performed",                 False),
    ("H3_performed",                 False),
    ("new_vars_created",             False),
    ("original_posts_json_modified", posts_json_modified),
]
# 주요 결과
for mname in ["M0_time_fe_only","M1_add_text_length","M2_add_hashtag","M3_add_mention","M4_add_emoji"]:
    for label, res in [("fullbin", fb_results), ("prob", fp_results), ("human", hv_results)]:
        r = get_r(res, mname, "log1p_engagement_total")
        diag_rows.append((f"{label}_{mname}_beta",   r.get("coefficient","n/a")))
        diag_rows.append((f"{label}_{mname}_p",      r.get("p_value","n/a")))
        diag_rows.append((f"{label}_{mname}_flag",   r.get("interpretation_flag","n/a")))

with open(DIAG_OUT, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=["metric","value"])
    w.writeheader()
    for k, v in diag_rows:
        w.writerow({"metric": k, "value": v})
print(f"  → {DIAG_OUT}")

# ─── 8. Summary Markdown ─────────────────────────────────────────────────────
print("[8] Summary 작성")

MODEL_ORDER = ["M0_time_fe_only","M1_add_text_length","M2_add_hashtag","M3_add_mention","M4_add_emoji"]

def tbl_primary_dv(results, dv="log1p_engagement_total"):
    rows_dv = [r for r in results if r["dv"] == dv and r["model_name"] in MODEL_ORDER]
    rows_dv.sort(key=lambda r: MODEL_ORDER.index(r["model_name"]))
    lines = [
        "| n_fmt | model | included_format_vars | β | p | sig | R² | adj_R² | 판정 |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for r in rows_dv:
        sig = star(r["p_value"])
        lines.append(
            f"| {r['number_of_post_format_variables']} | {r['model_name']} "
            f"| {r['included_post_format_variables']} "
            f"| {r['coefficient']} | {r['p_value']} | {sig} "
            f"| {r['r_squared']} | {r['adj_r_squared']} | {r['interpretation_flag']} |"
        )
    return "\n".join(lines)

def tbl_m4_all_dv(results, model="M4_add_emoji"):
    rows_m = [r for r in results if r["model_name"] == model]
    lines = [
        "| DV | β | p | sig | R² | 판정 |",
        "|---|---|---|---|---|---|",
    ]
    for r in rows_m:
        sig = star(r["p_value"])
        lines.append(
            f"| {r['dv']} | {r['coefficient']} | {r['p_value']} "
            f"| {sig} | {r['r_squared']} | {r['interpretation_flag']} |"
        )
    return "\n".join(lines)

def change_tbl_3way(fb_res, fp_res, hv_res, dv="log1p_engagement_total"):
    lines = [
        "| model | fb_β | fb_p | fb_sig | fp_β | fp_p | fp_sig | hv_β | hv_p | hv_sig |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for mname in MODEL_ORDER:
        rb = get_r(fb_res, mname, dv)
        rp = get_r(fp_res, mname, dv)
        rh = get_r(hv_res, mname, dv)
        lines.append(
            f"| {mname} "
            f"| {rb.get('coefficient','')} | {rb.get('p_value','')} | {star(rb.get('p_value',''))} "
            f"| {rp.get('coefficient','')} | {rp.get('p_value','')} | {star(rp.get('p_value',''))} "
            f"| {rh.get('coefficient','')} | {rh.get('p_value','')} | {star(rh.get('p_value',''))} |"
        )
    return "\n".join(lines)

fb_m0 = get_r(fb_results, "M0_time_fe_only", "log1p_engagement_total")
fb_m4 = get_r(fb_results, "M4_add_emoji",    "log1p_engagement_total")
fp_m0 = get_r(fp_results, "M0_time_fe_only", "log1p_engagement_total")
fp_m4 = get_r(fp_results, "M4_add_emoji",    "log1p_engagement_total")
hv_m0 = get_r(hv_results, "M0_time_fe_only", "log1p_engagement_total")
hv_m4 = get_r(hv_results, "M4_add_emoji",    "log1p_engagement_total")

summary_md = f"""# Wendy's H1 Literature-based Post Format Controls 결과

## 1. 분석 목적

H1 분석에서 기존 시간 고정효과 모형(year+month+hour FE)에 문헌 기반 post format 통제변수를 순차적으로 추가하여, 유머 게시글 여부와 post-level engagement 간 관계가 게시글 형식 차이를 고려한 뒤에도 유지되는지 확인한다. 주 분석은 full-sample (n=978)이며, 사람 코딩 597건은 부가 검증이다.

---

## 2. 문헌 기반 Post Format 변수

| 문헌 변수명 | Wendy's 데이터 변수 | 결측 여부 |
|---|---|---|
| Text Length | text_length | 없음 |
| # of Hashtags | hashtag_count | 없음 |
| # of Handle tags | mention_count | 없음 |
| # of Emojis | emoji_count | 없음 |

추가하지 않은 변수: url_count, is_quote_status, is_retweet_text, image/video 관련 변수

---

## 3. 사용한 파일

| 파일 | 역할 |
|---|---|
| wendys_final_humor_presence_full_predictions.csv | IV (final_humor_binary, pred_humor_final_050, p_humor_final_tfidf_logreg) |
| wendys_h3_aggressive_vs_other_intensity_dataset.csv | DV (log1p_*), 시간 변수 |
| wendys_fast_weak_supervised_humor_dataset.csv | post format 변수 (text_length 등 4개) |

---

## 4. 병합 안정성 확인

| 항목 | 값 |
|---|---|
| 병합 key | id |
| pred n | {len(pred_rows)} |
| H3 n | {len(h3_map)} |
| fast n | {len(fast_map)} |
| 병합 후 n | {len(merged)} |
| unmatched (H3) | {len(unmatched_h3)} |
| unmatched (fast) | {len(unmatched_fast)} |
| duplicate key | pred={dup_pred}, h3={dup_h3}, fast={dup_fast} |
| full n=978 유지 | {len(merged)==978} |
| primary n=597 유지 | {len(primary)==597} |
| post format 변수 결측으로 sample 감소 | False |

---

## 5. 원본 posts.json 변경 없음 확인

data/wendys/posts.json 변경 여부: **{posts_json_modified}**

---

## 6. 새 변수 생성 없음 확인

이번 작업에서는 새로운 변수를 생성하지 않았다. 기존 파일의 컬럼만 사용하였다. url_count, is_quote_status, is_retweet_text, day_of_week 미사용. log1p_view_count 미사용. year_quarter FE 미사용.

---

## 7. 표본 구성

| 항목 | 값 |
|---|---|
| Full sample (주 분석) | n={len(merged)} |
| Full predicted humor=1 | {sum(1 for r in merged if r.get("pred_humor_final_050")=="1")} |
| Full predicted humor=0 | {sum(1 for r in merged if r.get("pred_humor_final_050")=="0")} |
| Human-labeled sample (부가 검증) | n={len(primary)} |
| Human humor=1 | {sum(1 for r in primary if r.get("final_humor_binary")=="1")} |
| Human humor=0 | {sum(1 for r in primary if r.get("final_humor_binary")=="0")} |

---

## 8. 사용한 시간 고정효과

created_year FE + created_month FE + created_hour FE (전 모형 공통 포함)

---

## 9. Post Format 변수 추가 순서

M0 → M1(+text_length) → M2(+hashtag_count) → M3(+mention_count) → M4(+emoji_count)

---

## 10. Full-sample Binary H1 결과

**IV: pred_humor_final_050, n={len(merged)}**

### 10-1. Primary DV: log1p_engagement_total

{tbl_primary_dv(fb_results, "log1p_engagement_total")}

* p<.05, ** p<.01, *** p<.001, † p<.10 (conventional SE 기준)

### 10-2. M4 (전체 post format 통제) 기준 전체 DV

{tbl_m4_all_dv(fb_results, "M4_add_emoji")}

---

## 11. Full-sample Probability H1 결과

**IV: p_humor_final_tfidf_logreg, n={len(merged)}**

### 11-1. Primary DV: log1p_engagement_total

{tbl_primary_dv(fp_results, "log1p_engagement_total")}

### 11-2. M4 기준 전체 DV

{tbl_m4_all_dv(fp_results, "M4_add_emoji")}

---

## 12. Human-labeled Validation 결과 (부가 검증)

**IV: final_humor_binary, n={len(primary)}**

### 12-1. Primary DV: log1p_engagement_total

{tbl_primary_dv(hv_results, "log1p_engagement_total")}

### 12-2. M4 기준 전체 DV

{tbl_m4_all_dv(hv_results, "M4_add_emoji")}

---

## 13. Post Format 변수 추가 전후 β, p-value 변화 (primary DV)

{change_tbl_3way(fb_results, fp_results, hv_results, "log1p_engagement_total")}

fb=full_binary, fp=full_probability, hv=human_validation

---

## 14. H1 주 분석 판정

**Full-sample binary 기준 (n={len(merged)}, IV=pred_humor_final_050, DV=log1p_engagement_total):**

| 모형 | β | p | 판정 |
|---|---|---|---|
| M0 (time FE only) | {fb_m0.get("coefficient","n/a")} | {fb_m0.get("p_value","n/a")} | {fb_m0.get("interpretation_flag","n/a")} |
| M4 (all format controls) | {fb_m4.get("coefficient","n/a")} | {fb_m4.get("p_value","n/a")} | {fb_m4.get("interpretation_flag","n/a")} |

**Full-sample probability 기준:**

| 모형 | β | p | 판정 |
|---|---|---|---|
| M0 | {fp_m0.get("coefficient","n/a")} | {fp_m0.get("p_value","n/a")} | {fp_m0.get("interpretation_flag","n/a")} |
| M4 | {fp_m4.get("coefficient","n/a")} | {fp_m4.get("p_value","n/a")} | {fp_m4.get("interpretation_flag","n/a")} |

**판정: H1 지지 여부 — full-sample binary M4 기준: {fb_m4.get("interpretation_flag","n/a")}**

---

## 15. 사람 코딩 결과는 부가 검증

사람 코딩 597건 결과는 부가 검증이며, 주 분석(full-sample n=978)을 대체하지 않는다. Human validation M0 β={hv_m0.get("coefficient","n/a")} (p={hv_m0.get("p_value","n/a")}), M4 β={hv_m4.get("coefficient","n/a")} (p={hv_m4.get("p_value","n/a")}).

---

## 16. 인과관계 아님 — 관측적 연관성 분석

본 분석은 관측적 연관성 분석이며, 유머 게시글 여부가 engagement를 증가시켰다는 인과관계를 주장할 수 없다. 시간 고정효과 및 post format 변수는 측정 가능한 일부 혼동 요인을 통제하지만, 관찰되지 않은 개별 게시글의 콘텐츠 특성은 통제되지 않는다.

---

## 17. H2/H3 수행 여부

이번 작업에서는 H1 분석만 수행하였으며, H2와 H3는 수행하지 않았다.

---

## 18. 다음 단계

다음 단계에서 추가할 수 있는 변수(posting intensity: quarter_total_posts 등; log1p_view_count 등)는 사용자 승인 후 결정한다.

---

*생성일: 2026-06-15*
"""

with open(SUMMARY_OUT, "w", encoding="utf-8") as f:
    f.write(summary_md)
print(f"  → {SUMMARY_OUT}")

# ─── 9. 최종 검증 출력 ───────────────────────────────────────────────────────
print("\n" + "="*60)
print("[검증 요약]")
print(f"  full n={len(merged)} (기대:978): {'OK' if len(merged)==978 else 'FAIL'}")
print(f"  primary n={len(primary)} (기대:597): {'OK' if len(primary)==597 else 'FAIL'}")
print(f"  posts.json 변경: {posts_json_modified} (기대:False)")
rank_fail = any(r.get("interpretation_flag")=="FAIL" for r in fb_results+fp_results+hv_results)
print(f"  rank deficient: {rank_fail} (기대:False)")
print(f"  H2/H3: False | 새 변수: False | url_count: False | view_count: False")

print("\n[Full-binary primary DV — log1p_engagement_total]")
for mname in MODEL_ORDER:
    r = get_r(fb_results, mname, "log1p_engagement_total")
    print(f"  {r.get('model_name',''):28s} β={r.get('coefficient',''):8s} p={r.get('p_value',''):8s} "
          f"{star(r.get('p_value','')):4s} {r.get('interpretation_flag','')}")

print("\n[Full-probability primary DV]")
for mname in MODEL_ORDER:
    r = get_r(fp_results, mname, "log1p_engagement_total")
    print(f"  {r.get('model_name',''):28s} β={r.get('coefficient',''):8s} p={r.get('p_value',''):8s} "
          f"{star(r.get('p_value','')):4s} {r.get('interpretation_flag','')}")

print("\n[Human validation primary DV]")
for mname in MODEL_ORDER:
    r = get_r(hv_results, mname, "log1p_engagement_total")
    print(f"  {r.get('model_name',''):28s} β={r.get('coefficient',''):8s} p={r.get('p_value',''):8s} "
          f"{star(r.get('p_value','')):4s} {r.get('interpretation_flag','')}")
