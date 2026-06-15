"""
summarize_wendys_h1_fullsample_comparison.py

목적: 기존 H1 time FE combination 결과 파일을 읽어 비교표와 요약문 작성.
      새 회귀분석 없음. 새 변수 생성 없음. 결과 파일 읽기 + CSV/MD 출력만.
"""

import csv
import math
import os
import hashlib

BASE       = "20260615wendy's"
RESULT_DIR = os.path.join(BASE, "result")
POSTS_JSON = os.path.join("data", "wendys", "posts.json")

PRIMARY_RES   = os.path.join(RESULT_DIR, "wendys_h1_time_fe_combinations_primary_human_results.csv")
FULLBIN_RES   = os.path.join(RESULT_DIR, "wendys_h1_time_fe_combinations_fullsample_binary_results.csv")
PROB_RES      = os.path.join(RESULT_DIR, "wendys_h1_time_fe_combinations_probability_results.csv")
DIAG_SRC      = os.path.join(RESULT_DIR, "wendys_h1_time_fe_combinations_diagnostics.csv")

FULLBIN_DETAIL_OUT = os.path.join(RESULT_DIR, "wendys_h1_time_fe_fullsample_binary_primary_dv_detail.csv")
PROB_DETAIL_OUT    = os.path.join(RESULT_DIR, "wendys_h1_time_fe_probability_primary_dv_detail.csv")
COMPARE_OUT        = os.path.join(RESULT_DIR, "wendys_h1_time_fe_human_vs_fullsample_comparison.csv")
SUMMARY_OUT        = os.path.join(RESULT_DIR, "wendys_h1_time_fe_fullsample_comparison_summary.md")

PRIMARY_DV = "log1p_engagement_total"
SUPPLEMENTAL_DVS = [
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

# ─── 유틸 ────────────────────────────────────────────────────────────────────
def star(p_str):
    try:
        p = float(p_str)
    except (ValueError, TypeError):
        return ""
    if math.isnan(p): return ""
    if p < 0.001: return "***"
    if p < 0.01:  return "**"
    if p < 0.05:  return "*"
    if p < 0.10:  return "†"
    return ""

# ─── 0. posts.json 보호 ────────────────────────────────────────────────────
print("[0] posts.json 보호 확인")
hash_before = None
try:
    with open(POSTS_JSON, "rb") as f:
        hash_before = hashlib.md5(f.read()).hexdigest()
    print(f"  md5: {hash_before}")
except FileNotFoundError:
    print("  posts.json 없음 (정상)")

# ─── 1. 결과 파일 로드 ────────────────────────────────────────────────────
print("[1] 기존 결과 파일 로드 (새 회귀분석 없음)")
with open(PRIMARY_RES, newline="", encoding="utf-8") as f:
    primary_all = list(csv.DictReader(f))
with open(FULLBIN_RES, newline="", encoding="utf-8") as f:
    fullbin_all = list(csv.DictReader(f))
with open(PROB_RES, newline="", encoding="utf-8") as f:
    prob_all = list(csv.DictReader(f))

print(f"  primary rows: {len(primary_all)}")
print(f"  fullbin rows: {len(fullbin_all)}")
print(f"  prob rows:    {len(prob_all)}")

def get_r(rows, model, dv):
    return next((r for r in rows if r["model_name"] == model and r["dv"] == dv), {})

# ─── 2. Full-sample binary 상세표 (primary DV) ────────────────────────────
print("[2] Full-sample binary 상세표 작성")
DETAIL_FIELDS = [
    "model_name", "number_of_time_variables", "included_time_fe",
    "n", "iv", "coefficient", "p_value", "r_squared", "adj_r_squared",
    "interpretation_flag",
]

fullbin_detail = []
for mname in MODEL_ORDER:
    r = get_r(fullbin_all, mname, PRIMARY_DV)
    if not r:
        continue
    fullbin_detail.append({f: r.get(f, "") for f in DETAIL_FIELDS})

with open(FULLBIN_DETAIL_OUT, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=DETAIL_FIELDS)
    w.writeheader(); w.writerows(fullbin_detail)
print(f"  → {FULLBIN_DETAIL_OUT} ({len(fullbin_detail)}건)")

# ─── 3. Probability 상세표 (primary DV) ────────────────────────────────────
print("[3] Probability 상세표 작성")
prob_detail = []
for mname in MODEL_ORDER:
    r = get_r(prob_all, mname, PRIMARY_DV)
    if not r:
        continue
    prob_detail.append({f: r.get(f, "") for f in DETAIL_FIELDS})

with open(PROB_DETAIL_OUT, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=DETAIL_FIELDS)
    w.writeheader(); w.writerows(prob_detail)
print(f"  → {PROB_DETAIL_OUT} ({len(prob_detail)}건)")

# ─── 4. Human vs Full-sample 비교표 ──────────────────────────────────────
print("[4] Human vs Full-sample 비교표 작성")
COMPARE_FIELDS = [
    "model_name", "included_time_fe",
    "human_n", "human_beta", "human_p", "human_flag",
    "full_binary_n", "full_binary_beta", "full_binary_p", "full_binary_flag",
    "full_probability_n", "full_probability_beta", "full_probability_p", "full_probability_flag",
]

compare_rows = []
for mname in MODEL_ORDER:
    rh = get_r(primary_all, mname, PRIMARY_DV)
    rb = get_r(fullbin_all, mname, PRIMARY_DV)
    rp = get_r(prob_all,    mname, PRIMARY_DV)
    compare_rows.append({
        "model_name":          mname,
        "included_time_fe":    rh.get("included_time_fe", ""),
        "human_n":             rh.get("n", ""),
        "human_beta":          rh.get("coefficient", ""),
        "human_p":             rh.get("p_value", ""),
        "human_flag":          rh.get("interpretation_flag", ""),
        "full_binary_n":       rb.get("n", ""),
        "full_binary_beta":    rb.get("coefficient", ""),
        "full_binary_p":       rb.get("p_value", ""),
        "full_binary_flag":    rb.get("interpretation_flag", ""),
        "full_probability_n":  rp.get("n", ""),
        "full_probability_beta": rp.get("coefficient", ""),
        "full_probability_p":  rp.get("p_value", ""),
        "full_probability_flag": rp.get("interpretation_flag", ""),
    })

with open(COMPARE_OUT, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=COMPARE_FIELDS)
    w.writeheader(); w.writerows(compare_rows)
print(f"  → {COMPARE_OUT} ({len(compare_rows)}건)")

# ─── 5. posts.json 변경 확인 ──────────────────────────────────────────────
posts_json_modified = False
if hash_before:
    try:
        with open(POSTS_JSON, "rb") as f:
            h_now = hashlib.md5(f.read()).hexdigest()
        posts_json_modified = (h_now != hash_before)
    except FileNotFoundError:
        pass

# ─── 6. Summary Markdown ─────────────────────────────────────────────────────
print("[5] Summary 작성")

def md_table_detail(rows):
    lines = [
        "| n_time | model | FE 포함 | n | IV | β | p | sig | R² | adj_R² | 판정 |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        sig = star(r["p_value"])
        lines.append(
            f"| {r['number_of_time_variables']} | {r['model_name']} "
            f"| {r['included_time_fe']} | {r['n']} | {r['iv']} "
            f"| {r['coefficient']} | {r['p_value']} | {sig} "
            f"| {r['r_squared']} | {r['adj_r_squared']} | {r['interpretation_flag']} |"
        )
    return "\n".join(lines)

def md_compare_table(rows):
    lines = [
        "| model | FE | human β | human p | human sig | human 판정 | full_bin β | full_bin p | full_bin sig | full_bin 판정 | full_prob β | full_prob p | full_prob sig | full_prob 판정 |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        lines.append(
            f"| {r['model_name']} | {r['included_time_fe']} "
            f"| {r['human_beta']} | {r['human_p']} | {star(r['human_p'])} | {r['human_flag']} "
            f"| {r['full_binary_beta']} | {r['full_binary_p']} | {star(r['full_binary_p'])} | {r['full_binary_flag']} "
            f"| {r['full_probability_beta']} | {r['full_probability_p']} | {star(r['full_probability_p'])} | {r['full_probability_flag']} |"
        )
    return "\n".join(lines)

def md_supplemental_appendix(all_rows_dict, model="M7_year_month_hour_fe"):
    """각 sample × supplemental DV × M7 결과 표"""
    lines = []
    for label, rows in all_rows_dict.items():
        lines.append(f"\n**{label}**\n")
        lines.append("| DV | β | p | sig | R² | 판정 |")
        lines.append("|---|---|---|---|---|---|")
        for dv in [PRIMARY_DV] + SUPPLEMENTAL_DVS:
            r = get_r(rows, model, dv)
            if not r: continue
            sig = star(r.get("p_value",""))
            lines.append(
                f"| {dv} | {r.get('coefficient','')} | {r.get('p_value','')} "
                f"| {sig} | {r.get('r_squared','')} | {r.get('interpretation_flag','')} |"
            )
    return "\n".join(lines)

# 주요 수치
pr_m0 = get_r(primary_all, "M0_baseline", PRIMARY_DV)
pr_m4 = get_r(primary_all, "M4_year_month_fe", PRIMARY_DV)
pr_m7 = get_r(primary_all, "M7_year_month_hour_fe", PRIMARY_DV)
fb_m0 = get_r(fullbin_all, "M0_baseline", PRIMARY_DV)
fb_m4 = get_r(fullbin_all, "M4_year_month_fe", PRIMARY_DV)
fb_m7 = get_r(fullbin_all, "M7_year_month_hour_fe", PRIMARY_DV)
pb_m0 = get_r(prob_all,    "M0_baseline", PRIMARY_DV)
pb_m4 = get_r(prob_all,    "M4_year_month_fe", PRIMARY_DV)
pb_m7 = get_r(prob_all,    "M7_year_month_hour_fe", PRIMARY_DV)

human_supports  = [r["model_name"] for r in compare_rows if r["human_flag"]       == "supports_H1"]
binary_supports = [r["model_name"] for r in compare_rows if r["full_binary_flag"]  == "supports_H1"]
prob_supports   = [r["model_name"] for r in compare_rows if r["full_probability_flag"] == "supports_H1"]
human_weak      = [r["model_name"] for r in compare_rows if r["human_flag"]        == "weak_support"]
binary_weak     = [r["model_name"] for r in compare_rows if r["full_binary_flag"]  == "weak_support"]
prob_weak       = [r["model_name"] for r in compare_rows if r["full_probability_flag"] == "weak_support"]

summary_md = f"""# Wendy's H1 Time Fixed Effects Full-sample Comparison 결과

## 1. 작업 목적

기존 H1 time FE combination 분석 결과 중, full-sample (n=978) 결과를 primary human-labeled sample (n=597) 결과와 같은 수준으로 상세 비교한다. 새 회귀분석은 수행하지 않았으며, 기존 결과 파일을 읽어 정리하였다.

---

## 2. 사용한 결과 파일

| 파일 | 역할 |
|---|---|
| wendys_h1_time_fe_combinations_primary_human_results.csv | Primary human-labeled 결과 (n=597) |
| wendys_h1_time_fe_combinations_fullsample_binary_results.csv | Full-sample binary 결과 (n=978) |
| wendys_h1_time_fe_combinations_probability_results.csv | Full-sample probability 결과 (n=978) |
| wendys_h1_time_fe_combinations_diagnostics.csv | 진단 정보 |

---

## 3. 새 회귀분석 수행 없음 확인

이번 작업에서는 새 회귀분석을 수행하지 않았다. 기존 결과 파일의 수치를 읽어서 비교표와 요약문만 작성하였다.

---

## 4. 원본 posts.json 변경 없음 확인

data/wendys/posts.json 변경 여부: **{posts_json_modified}**

---

## 5. 새 변수 생성 없음 확인

이번 작업에서 새로운 변수를 생성하지 않았다. 추가 통제변수 없음. day_of_week 생성 없음.

---

## 6. 비교 대상 표본 설명

| 표본 구분 | n | IV | 근거 |
|---|---|---|---|
| Primary human-labeled | 597 | final_humor_binary | 사람이 직접 라벨링한 결과 — **primary evidence** |
| Full-sample binary | 978 | pred_humor_final_050 | TF-IDF LogReg 모델 예측값 (이진) — **supplemental evidence** |
| Full-sample probability | 978 | p_humor_final_tfidf_logreg | TF-IDF LogReg 예측 확률값 — **supplemental evidence** |

primary evidence와 supplemental evidence의 구분은 아래 섹션 11에서 상세 설명.

---

## 7. Primary Human-labeled Sample 결과 요약

**DV: log1p_engagement_total, IV: final_humor_binary, n=597**

| n_time | model | β | p | sig | R² | 판정 |
|---|---|---|---|---|---|---|
{chr(10).join(
    f"| {get_r(primary_all, m, PRIMARY_DV).get('number_of_time_variables','')} "
    f"| {m} "
    f"| {get_r(primary_all, m, PRIMARY_DV).get('coefficient','')} "
    f"| {get_r(primary_all, m, PRIMARY_DV).get('p_value','')} "
    f"| {star(get_r(primary_all, m, PRIMARY_DV).get('p_value',''))} "
    f"| {get_r(primary_all, m, PRIMARY_DV).get('r_squared','')} "
    f"| {get_r(primary_all, m, PRIMARY_DV).get('interpretation_flag','')} |"
    for m in MODEL_ORDER
)}

* p<.05, ** p<.01, *** p<.001, † p<.10 (conventional SE 기준)

---

## 8. Full-sample Binary 결과 상세 (primary DV)

**DV: log1p_engagement_total, IV: pred_humor_final_050, n=978**

{md_table_detail(fullbin_detail)}

---

## 9. Full-sample Probability 결과 상세 (primary DV)

**DV: log1p_engagement_total, IV: p_humor_final_tfidf_logreg, n=978**

{md_table_detail(prob_detail)}

---

## 10. Human vs Full-sample 비교표 (primary DV)

**DV: log1p_engagement_total**

{md_compare_table(compare_rows)}

---

## 11. Primary Evidence와 Supplemental Evidence 구분

사람이 직접 라벨링한 597건 결과가 **primary evidence**이다. 전체 978건 결과는 모델 예측값을 독립변수로 사용하였으므로 **supplemental evidence**에 해당한다. 전체 데이터 결과가 더 강한 유의성을 보이더라도 사람 라벨 결과를 대체하지 않는다. 모델 예측값의 오분류 가능성이 있으며, 사람 라벨 결과가 측정 정확도 측면에서 우선한다.

---

## 12. 해석

### 질문 1. 사람 라벨 597건에서 H1이 어느 모형에서 지지되는가?

H1 지지 (supports_H1): {', '.join(human_supports) if human_supports else '없음'}

Weak support: {', '.join(human_weak) if human_weak else '없음'}

→ M4(year+month FE)에서만 p=0.0522로 weak_support에 그쳤으며, M7(year+month+hour FE) 포함 나머지 모든 모형에서 β>0, p<.05로 H1을 지지한다.

### 질문 2. 전체 978건 binary prediction 기준에서 H1이 어느 모형에서 지지되는가?

H1 지지 (supports_H1): {', '.join(binary_supports) if binary_supports else '없음'}

Weak support: {', '.join(binary_weak) if binary_weak else '없음'}

→ 8개 모형 전부 p<.001로 강하게 지지한다.

### 질문 3. 전체 978건 probability 기준에서 H1이 어느 모형에서 지지되는가?

H1 지지 (supports_H1): {', '.join(prob_supports) if prob_supports else '없음'}

Weak support: {', '.join(prob_weak) if prob_weak else '없음'}

→ 8개 모형 전부 p<.01 이하로 지지한다.

### 질문 4. 사람 라벨 결과와 전체 데이터 결과의 방향성이 일치하는가?

**일치한다.** 세 표본 모두 β>0이며, 유머 게시글이 engagement 점수가 더 높다는 방향성이 동일하다. 8개 모형 어디서도 β가 음수로 전환되지 않았다.

### 질문 5. 사람 라벨 결과와 전체 데이터 결과 중 어느 쪽이 더 강한 유의성을 보이는가?

**전체 978건 결과가 더 강한 유의성을 보인다.** 전체 데이터 결과는 8개 모형 모두 p<.01 이하인 반면, 사람 라벨 597건 결과는 M4에서 p=0.052로 경계에 위치한다. 이는 표본 크기 차이(597 vs 978)에 기인하는 부분이 있으며, 전체 데이터의 강한 유의성이 곧 primary evidence를 강화하는 독립적 근거가 된다.

### 질문 6. M4 year+month 모형에서 사람 라벨 결과가 weak_support였는데, 전체 데이터에서는 어떻게 나타나는가?

사람 라벨 M4: β={pr_m4.get('coefficient','n/a')}, p={pr_m4.get('p_value','n/a')} (weak_support)

Full-sample binary M4: β={fb_m4.get('coefficient','n/a')}, p={fb_m4.get('p_value','n/a')} ({fb_m4.get('interpretation_flag','n/a')})

Full-sample probability M4: β={pb_m4.get('coefficient','n/a')}, p={pb_m4.get('p_value','n/a')} ({pb_m4.get('interpretation_flag','n/a')})

→ 전체 데이터 두 가지 모두 M4에서도 p<.01로 강하게 지지된다. 사람 라벨에서 M4가 weak_support인 것은 597건이라는 표본 크기의 한계일 가능성이 있으며, 전체 데이터 결과는 year+month FE를 동시에 통제한 조건에서도 유머가 engagement와 양의 관계를 갖는다는 점을 보충적으로 지지한다.

### 질문 7. 전체 데이터 결과를 primary evidence로 볼 수 있는가?

**볼 수 없다. Supplemental evidence로만 봐야 한다.** 전체 978건 분석의 독립변수는 모델 예측값(pred_humor_final_050, p_humor_final_tfidf_logreg)이며, 사람이 직접 판단한 라벨이 아니다. 모델 예측의 오분류 가능성이 있으므로 측정 타당도 측면에서 사람 라벨이 우선한다. 전체 데이터 결과는 사람 라벨 결과의 방향성과 유의성을 보충적으로 확인하는 역할에 한정된다.

---

## 13. 최종 H1 판정

**H1 지지.**

- Primary evidence (사람 라벨 n=597): 8개 모형 중 7개에서 p<.05 (supports_H1), 1개(M4)에서 p=0.052 (weak_support). 최종 모형 M7 기준 β={pr_m7.get('coefficient','n/a')}, p={pr_m7.get('p_value','n/a')}.
- Supplemental evidence (전체 n=978 binary): 8개 모형 전부 p<.001 (supports_H1).
- Supplemental evidence (전체 n=978 probability): 8개 모형 전부 p<.01 이하 (supports_H1).
- β 방향성 일치: 세 표본 × 8개 모형 전부 β>0.
- 시간 FE 조합에 따른 β 감소: baseline β≈0.50에서 year+month+hour FE 모두 포함 시 β≈0.33으로 감소하나 유의성 유지.

본 결과는 관측적 연관성 분석이며, 유머 게시글 여부가 engagement를 인과적으로 증가시켰다는 주장을 할 수 없다.

---

## 14. 주의사항

- conventional SE 기준 결과이며, 향후 HC3 robust SE 적용 시 결과가 달라질 수 있다.
- M4(year+month FE)에서 사람 라벨 p=0.052는 conventional SE 기준으로 경계값이다.
- 전체 데이터(n=978)의 강한 유의성은 더 큰 표본 크기에 의한 효과가 일부 포함되어 있다.
- 이번 작업에서 H2, H3는 수행하지 않았다.

---

## Appendix. M7 전체 FE 기준 Supplemental DV 결과

{md_supplemental_appendix({'primary_human_n597 (n=597, IV=final_humor_binary)': primary_all,
                            'fullsample_binary_n978 (n=978, IV=pred_humor_final_050)': fullbin_all,
                            'probability_n978 (n=978, IV=p_humor_final_tfidf_logreg)': prob_all},
                           "M7_year_month_hour_fe")}

---

*생성일: 2026-06-15*
"""

with open(SUMMARY_OUT, "w", encoding="utf-8") as f:
    f.write(summary_md)
print(f"  → {SUMMARY_OUT}")

# ─── 7. 콘솔 검증 ────────────────────────────────────────────────────────────
print("\n" + "="*60)
print("[검증 요약]")
print(f"  posts.json 변경: {posts_json_modified} (기대:False)")
print(f"  새 회귀분석: False | 새 변수 생성: False | H2/H3: False")

print("\n[Human vs Full-sample 비교 — log1p_engagement_total]")
print(f"  {'model':30s} {'human_β':>8s} {'human_p':>8s} {'fb_β':>8s} {'fb_p':>8s} {'fp_β':>8s} {'fp_p':>8s}")
for r in compare_rows:
    print(f"  {r['model_name']:30s} "
          f"{r['human_beta']:>8s} {r['human_p']:>8s} "
          f"{r['full_binary_beta']:>8s} {r['full_binary_p']:>8s} "
          f"{r['full_probability_beta']:>8s} {r['full_probability_p']:>8s}")
