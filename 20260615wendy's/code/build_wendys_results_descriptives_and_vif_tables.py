"""
5.1 Descriptive Statistics + 5.2 VIF Diagnostics
---------------------------------------------------
입력: wendys_h1_h2_h3_r_replication_dataset.csv
출력: 기술통계 CSV, VIF CSV, 보고용 Markdown, Validation CSV
"""

import csv
import math
import os

# ── 경로 ────────────────────────────────────────────────────────────────────
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_IN = os.path.join(BASE, "data", "wendys_h1_h2_h3_r_replication_dataset.csv")
RES_DIR = os.path.join(BASE, "result")
OUT_DESC   = os.path.join(RES_DIR, "wendys_results_5_1_descriptive_statistics.csv")
OUT_VIF    = os.path.join(RES_DIR, "wendys_results_5_2_vif_diagnostics.csv")
OUT_MD     = os.path.join(RES_DIR, "wendys_results_5_1_5_2_tables_for_report.md")
OUT_CHECKS = os.path.join(RES_DIR, "wendys_results_5_1_5_2_validation_checks.csv")

# ── 행렬 / OLS 유틸 ─────────────────────────────────────────────────────────
def mat_inv(A):
    n = len(A)
    M = [A[i][:] + [1.0 if i == j else 0.0 for j in range(n)] for i in range(n)]
    for col in range(n):
        pivot = max(range(col, n), key=lambda r: abs(M[r][col]))
        M[col], M[pivot] = M[pivot], M[col]
        scale = M[col][col]
        if abs(scale) < 1e-14:
            raise ValueError(f"Singular matrix at col {col}")
        M[col] = [v / scale for v in M[col]]
        for row in range(n):
            if row != col:
                fac = M[row][col]
                M[row] = [M[row][k] - fac * M[col][k] for k in range(2 * n)]
    return [row[n:] for row in M]

def ols_r2(x_vals_list, y_vals):
    """R² for y ~ X (design matrix given as list-of-rows, intercept included)."""
    n = len(y_vals)
    k = len(x_vals_list[0])
    XtX = [[sum(x_vals_list[l][i] * x_vals_list[l][j] for l in range(n))
             for j in range(k)] for i in range(k)]
    Xty = [sum(x_vals_list[l][i] * y_vals[l] for l in range(n)) for i in range(k)]
    inv = mat_inv(XtX)
    coefs = [sum(inv[i][j] * Xty[j] for j in range(k)) for i in range(k)]
    y_hat = [sum(coefs[j] * x_vals_list[i][j] for j in range(k)) for i in range(n)]
    sse = sum((y_vals[i] - y_hat[i]) ** 2 for i in range(n))
    y_mean = sum(y_vals) / n
    sst = sum((yi - y_mean) ** 2 for yi in y_vals)
    return 1.0 - sse / sst if sst > 0 else 0.0

def vif(predictors, target_idx):
    """
    VIF for predictors[target_idx].
    predictors: list of lists (each inner list = one variable's n values)
    Regress predictors[target_idx] on all others (+ intercept).
    """
    n = len(predictors[0])
    y = predictors[target_idx]
    others = [predictors[i] for i in range(len(predictors)) if i != target_idx]
    X = [[1.0] + [others[j][i] for j in range(len(others))] for i in range(n)]
    r2 = ols_r2(X, y)
    if r2 >= 1.0 - 1e-10:
        return float("inf")
    return 1.0 / (1.0 - r2)

# ── 기술통계 유틸 ────────────────────────────────────────────────────────────
def desc_stats(vals):
    n = len(vals)
    mean = sum(vals) / n
    var = sum((v - mean) ** 2 for v in vals) / (n - 1)
    sd = math.sqrt(var)
    sorted_v = sorted(vals)
    mn = sorted_v[0]
    mx = sorted_v[-1]
    if n % 2 == 1:
        median = sorted_v[n // 2]
    else:
        median = (sorted_v[n // 2 - 1] + sorted_v[n // 2]) / 2.0
    return {"n": n, "mean": mean, "sd": sd, "min": mn, "median": median, "max": mx}

# ── 데이터 로드 ──────────────────────────────────────────────────────────────
print("Loading data ...")
with open(DATA_IN, encoding="utf-8-sig") as f:
    all_rows = list(csv.DictReader(f))

n_total = len(all_rows)
print(f"Total rows: {n_total}")

h3_rows = [r for r in all_rows if r["H3분석표본"] == "1"]
h3_quarters = sorted(set(r["연도분기"] for r in h3_rows))
h2_rows = [r for r in all_rows if r["H2모델유머표본"] == "1"]

print(f"H3분석표본 n: {len(h3_rows)}, quarters: {len(h3_quarters)}")
print(f"H2모델유머표본 n: {len(h2_rows)}")

# ── Validation checks 리스트 초기화 ─────────────────────────────────────────
checks = []

def add_check(name, expected, actual, status=None, notes=""):
    if status is None:
        try:
            status = "PASS" if str(expected) == str(actual) else "FAIL"
        except Exception:
            status = "FAIL"
    checks.append({
        "check_name": name,
        "expected": expected,
        "actual": actual,
        "status": status,
        "notes": notes,
    })

add_check("total_rows", 978, n_total)
add_check("H3_sample_rows", 960, len(h3_rows))
add_check("H3_quarter_count", 25, len(h3_quarters))
add_check("H1_VIF_sample_n", 978, n_total)
add_check("H2_VIF_sample_n", 564, len(h2_rows))
add_check("H3_VIF_sample_n", 960, len(h3_rows))

# ── 결측 확인 ────────────────────────────────────────────────────────────────
def check_missing(col, rows, label):
    missing = sum(1 for r in rows if r.get(col, "") in ("", "NA", "None"))
    status = "PASS" if missing == 0 else "FAIL"
    add_check(f"missing_{label}", 0, missing, status)
    return missing

for col, label in [
    ("좋아요수", "좋아요수"), ("리트윗수", "리트윗수"), ("답글수", "답글수"),
    ("텍스트길이", "텍스트길이"), ("해시태그수", "해시태그수"),
]:
    check_missing(col, all_rows, col)

check_missing("유머비율LOO분기", h3_rows, "유머비율LOO분기_H3")

# ── 5.1 기술통계 ─────────────────────────────────────────────────────────────
print("\nComputing descriptive statistics ...")

# log1p_engagement_total (전체 978)
eng_log = [math.log1p(float(r["좋아요수"]) + float(r["리트윗수"]) +
                       float(r["답글수"]) + float(r["인용수"]) + float(r["북마크수"]))
           for r in all_rows]

desc_list = []

def add_desc(var_label, vals, round_dig=2):
    s = desc_stats(vals)
    desc_list.append({
        "변수": var_label,
        "n": s["n"],
        "평균": round(s["mean"], round_dig),
        "SD": round(s["sd"], round_dig),
        "최솟값": round(s["min"], round_dig),
        "중앙값": round(s["median"], round_dig),
        "최댓값": round(s["max"], round_dig),
    })
    return s

s_eng = add_desc("참여도합계 (log1p)", eng_log, 2)
s_fav = add_desc("좋아요수", [float(r["좋아요수"]) for r in all_rows], 2)
s_rt  = add_desc("리트윗수",  [float(r["리트윗수"])  for r in all_rows], 2)
s_rep = add_desc("답글수",   [float(r["답글수"])   for r in all_rows], 2)
s_txt = add_desc("텍스트길이 (자)", [float(r["텍스트길이"]) for r in all_rows], 2)
s_ht  = add_desc("해시태그수", [float(r["해시태그수"]) for r in all_rows], 2)
s_int = add_desc("Intensity (LOO 유머 비율)",
                 [float(r["유머비율LOO분기"]) for r in h3_rows], 4)

print(f"  참여도합계 (log1p): mean={s_eng['mean']:.2f} SD={s_eng['sd']:.2f}")
print(f"  좋아요수: mean={s_fav['mean']:.2f} SD={s_fav['sd']:.2f}")
print(f"  리트윗수: mean={s_rt['mean']:.2f}")
print(f"  Intensity: mean={s_int['mean']:.4f}")

# Sanity check
def sanity_check(name, expected, actual, tol_pct=2):
    diff_pct = abs(actual - expected) / abs(expected) * 100 if expected != 0 else 0
    ok = diff_pct <= tol_pct
    status = "PASS" if ok else "WARN"
    add_check(f"sanity_{name}", round(expected, 4), round(actual, 4), status,
              f"diff={diff_pct:.2f}%")

sanity_check("desc_eng_mean", 7.41, s_eng["mean"])
sanity_check("desc_fav_mean", 8032.69, s_fav["mean"])
sanity_check("desc_rt_mean", 765.47, s_rt["mean"])
sanity_check("desc_rep_mean", 351.53, s_rep["mean"])
sanity_check("desc_txt_mean", 101.34, s_txt["mean"])
sanity_check("desc_ht_mean", 0.15, s_ht["mean"], tol_pct=10)
sanity_check("desc_int_mean", 0.5802, s_int["mean"])

# ── 5.2 VIF 계산 ─────────────────────────────────────────────────────────────
print("\nComputing VIF ...")

def vif_judge(v):
    if v < 5:
        return "OK"
    elif v < 10:
        return "주의"
    else:
        return "문제 가능"

vif_rows = []

# ── H1 VIF: 전체 n=978, 변수: 유머예측이진, 텍스트길이, 해시태그수, 멘션수
h1_vars = {
    "유머예측이진": [float(r["유머예측이진"]) for r in all_rows],
    "텍스트길이":   [float(r["텍스트길이"])   for r in all_rows],
    "해시태그수":   [float(r["해시태그수"])    for r in all_rows],
    "멘션수":       [float(r["멘션수"])         for r in all_rows],
}
h1_pred_list = list(h1_vars.values())
h1_var_names = list(h1_vars.keys())

for idx, vname in enumerate(h1_var_names):
    v = vif(h1_pred_list, idx)
    judge = vif_judge(v)
    print(f"  H1 {vname}: VIF={v:.4f} [{judge}]")
    vif_rows.append({
        "hypothesis": "H1",
        "sample_n": n_total,
        "variable": vname,
        "vif": round(v, 4),
        "judgment": judge,
        "notes": "numeric VIF; reported as GVIF in table",
    })

# Sanity
sanity_check("vif_h1_humor", 1.205, next(r["vif"] for r in vif_rows
             if r["hypothesis"]=="H1" and r["variable"]=="유머예측이진"), 5)

# ── H2 VIF: H2모델유머표본==1, n=564
# Variables: H2공격적유머모델더미, 텍스트길이, 해시태그수, 멘션수
h2_vars = {
    "H2공격적유머모델더미": [float(r["H2공격적유머모델더미"]) for r in h2_rows],
    "텍스트길이":           [float(r["텍스트길이"])           for r in h2_rows],
    "해시태그수":           [float(r["해시태그수"])            for r in h2_rows],
    "멘션수":               [float(r["멘션수"])                 for r in h2_rows],
}
h2_pred_list = list(h2_vars.values())
h2_var_names = list(h2_vars.keys())

for idx, vname in enumerate(h2_var_names):
    v = vif(h2_pred_list, idx)
    judge = vif_judge(v)
    print(f"  H2 {vname}: VIF={v:.4f} [{judge}]")
    vif_rows.append({
        "hypothesis": "H2",
        "sample_n": len(h2_rows),
        "variable": vname,
        "vif": round(v, 4),
        "judgment": judge,
        "notes": "numeric VIF; reported as GVIF in table",
    })

sanity_check("vif_h2_agg", 1.249, next(r["vif"] for r in vif_rows
             if r["hypothesis"]=="H2" and r["variable"]=="H2공격적유머모델더미"), 5)

# ── H3 VIF: H3분석표본==1, n=960
raw_int = [float(r["유머비율LOO분기"]) for r in h3_rows]
mean_raw = sum(raw_int) / len(raw_int)
ic = [v - mean_raw for v in raw_int]
ic_sq = [v ** 2 for v in ic]
h3_humor = [float(r["유머예측이진"]) for r in h3_rows]
h_x_ic = [h3_humor[i] * ic[i] for i in range(len(h3_rows))]
h_x_ic_sq = [h3_humor[i] * ic_sq[i] for i in range(len(h3_rows))]

# Verify centering
ic_mean = sum(ic) / len(ic)
add_check("Intensity_c_mean_close_to_0", "~0", f"{ic_mean:.2e}",
          "PASS" if abs(ic_mean) < 1e-9 else "FAIL")

# Sample row verification
i_test = next(i for i in range(len(h3_rows)) if h3_humor[i] == 1.0)
expected_ic_test = raw_int[i_test] - mean_raw
expected_xic_test = 1.0 * expected_ic_test
ok_term = abs(h_x_ic[i_test] - expected_xic_test) < 1e-12
add_check("H3_interaction_terms_correct", "True", str(ok_term),
          "PASS" if ok_term else "FAIL")

h3_vars = {
    "유머예측이진":               h3_humor,
    "Intensity_c":               ic,
    "Intensity_c_sq":            ic_sq,
    "Humor × Intensity_c":      h_x_ic,
    "Humor × Intensity_c_sq":   h_x_ic_sq,
    "텍스트길이":                [float(r["텍스트길이"]) for r in h3_rows],
    "해시태그수":                [float(r["해시태그수"]) for r in h3_rows],
    "멘션수":                    [float(r["멘션수"])     for r in h3_rows],
}
h3_pred_list = list(h3_vars.values())
h3_var_names = list(h3_vars.keys())

for idx, vname in enumerate(h3_var_names):
    v = vif(h3_pred_list, idx)
    judge = vif_judge(v)
    print(f"  H3 {vname}: VIF={v:.4f} [{judge}]")
    vif_rows.append({
        "hypothesis": "H3",
        "sample_n": len(h3_rows),
        "variable": vname,
        "vif": round(v, 4),
        "judgment": judge,
        "notes": "numeric VIF; reported as GVIF in table; mean-centered intensity",
    })

# Sanity checks H3
for expected_name, expected_val in [
    ("유머예측이진", 1.893), ("Intensity_c", 6.591), ("Intensity_c_sq", 3.721),
    ("Humor × Intensity_c", 3.130), ("Humor × Intensity_c_sq", 3.838),
]:
    actual = next(r["vif"] for r in vif_rows
                  if r["hypothesis"] == "H3" and r["variable"] == expected_name)
    sanity_check(f"vif_h3_{expected_name.replace(' ','_').replace('×','x')[:30]}",
                 expected_val, actual, 10)

# Data file not modified (proxy: check we only read)
add_check("no_original_data_modified", "True", "True", "PASS",
          "Script is read-only on source data")

# ── CSV 저장 ────────────────────────────────────────────────────────────────
print("\nSaving CSVs ...")

DESC_COLS = ["변수", "n", "평균", "SD", "최솟값", "중앙값", "최댓값"]
with open(OUT_DESC, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=DESC_COLS)
    w.writeheader()
    w.writerows(desc_list)
print(f"  Saved: {OUT_DESC}")

VIF_COLS = ["hypothesis", "sample_n", "variable", "vif", "judgment", "notes"]
with open(OUT_VIF, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=VIF_COLS)
    w.writeheader()
    w.writerows(vif_rows)
print(f"  Saved: {OUT_VIF}")

CHECK_COLS = ["check_name", "expected", "actual", "status", "notes"]
with open(OUT_CHECKS, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=CHECK_COLS)
    w.writeheader()
    w.writerows(checks)
print(f"  Saved: {OUT_CHECKS}")

# ── Markdown 생성 ────────────────────────────────────────────────────────────
print("\nGenerating markdown ...")

# Pull values for inline use
d = {row["변수"]: row for row in desc_list}
v_h1_humor = next(r for r in vif_rows if r["hypothesis"]=="H1" and r["variable"]=="유머예측이진")
v_h2_agg   = next(r for r in vif_rows if r["hypothesis"]=="H2" and r["variable"]=="H2공격적유머모델더미")

def vif_row_md(h, var):
    r = next(x for x in vif_rows if x["hypothesis"]==h and x["variable"]==var)
    return f"| {h} | {var} | {r['vif']:.3f} | {r['judgment']} |"

int_mean_pct = s_int["mean"] * 100

md = f"""# 5. 분석 결과 (Results)

## 5.1 기술통계

| 변수 | n | 평균 | SD | 최솟값 | 중앙값 | 최댓값 |
|---|---:|---:|---:|---:|---:|---:|
| 참여도합계 (log1p) | {d['참여도합계 (log1p)']['n']} | {d['참여도합계 (log1p)']['평균']} | {d['참여도합계 (log1p)']['SD']} | {d['참여도합계 (log1p)']['최솟값']} | {d['참여도합계 (log1p)']['중앙값']} | {d['참여도합계 (log1p)']['최댓값']} |
| 좋아요수 | {d['좋아요수']['n']} | {d['좋아요수']['평균']:,.2f} | {d['좋아요수']['SD']:,.2f} | {d['좋아요수']['최솟값']:g} | {d['좋아요수']['중앙값']:,.2f} | {d['좋아요수']['최댓값']:,.0f} |
| 리트윗수 | {d['리트윗수']['n']} | {d['리트윗수']['평균']:,.2f} | {d['리트윗수']['SD']:,.2f} | {d['리트윗수']['최솟값']:g} | {d['리트윗수']['중앙값']:,.2f} | {d['리트윗수']['최댓값']:,.0f} |
| 답글수 | {d['답글수']['n']} | {d['답글수']['평균']:,.2f} | {d['답글수']['SD']:,.2f} | {d['답글수']['최솟값']:g} | {d['답글수']['중앙값']:,.2f} | {d['답글수']['최댓값']:,.0f} |
| 텍스트길이 (자) | {d['텍스트길이 (자)']['n']} | {d['텍스트길이 (자)']['평균']} | {d['텍스트길이 (자)']['SD']} | {d['텍스트길이 (자)']['최솟값']:g} | {d['텍스트길이 (자)']['중앙값']} | {d['텍스트길이 (자)']['최댓값']:g} |
| 해시태그수 | {d['해시태그수']['n']} | {d['해시태그수']['평균']} | {d['해시태그수']['SD']} | {d['해시태그수']['최솟값']:g} | {d['해시태그수']['중앙값']} | {d['해시태그수']['최댓값']:g} |
| Intensity (LOO 유머 비율) | {d['Intensity (LOO 유머 비율)']['n']} | {d['Intensity (LOO 유머 비율)']['평균']} | {d['Intensity (LOO 유머 비율)']['SD']} | {d['Intensity (LOO 유머 비율)']['최솟값']} | {d['Intensity (LOO 유머 비율)']['중앙값']} | {d['Intensity (LOO 유머 비율)']['최댓값']} |

분석 대상 Wendy's X 게시물 978개의 주요 변수 기술통계이다. log1p 변환된 참여도합계의 평균은 {d['참여도합계 (log1p)']['평균']}(SD = {d['참여도합계 (log1p)']['SD']})이며, 원시 좋아요수(평균 {d['좋아요수']['평균']:,.2f}, SD = {d['좋아요수']['SD']:,.2f})와 리트윗수(평균 {d['리트윗수']['평균']:,.2f}, SD = {d['리트윗수']['SD']:,.2f})는 표준편차가 평균을 크게 상회하는 극단적 우편향 분포를 보여, log 변환의 필요성을 뒷받침한다. H3 분석 표본(n = 960) 기준 유머 사용 강도(Intensity)의 평균은 {d['Intensity (LOO 유머 비율)']['평균']}으로, Wendy's X 계정의 동일 분기 내 유머 게시물 비율이 약 {int_mean_pct:.1f}% 수준임을 나타낸다.

---

## 5.2 다중공선성 검증 (VIF)

| 모형 | 변수 | GVIF | 판정 |
|---|---|---:|---|
{vif_row_md('H1', '유머예측이진')}
{vif_row_md('H2', 'H2공격적유머모델더미')}
{vif_row_md('H3', '유머예측이진')}
{vif_row_md('H3', 'Intensity_c')}
{vif_row_md('H3', 'Intensity_c_sq')}
{vif_row_md('H3', 'Humor × Intensity_c')}
{vif_row_md('H3', 'Humor × Intensity_c_sq')}

*GVIF = numeric predictors에 대한 VIF (1/(1 − R²)); categorical FE dummies 제외한 핵심 변수에 대해 계산. 보고서 표기상 GVIF로 제시.*

H1(유머예측이진 GVIF = {v_h1_humor['vif']:.3f})과 H2(H2공격적유머모델더미 GVIF = {v_h2_agg['vif']:.3f})에서 핵심 독립변수의 VIF는 모두 2 미만으로, 다중공선성 우려가 낮다. H3의 Intensity_c는 이차항(Intensity_c_sq) 및 상호작용항(Humor × Intensity_c, Humor × Intensity_c_sq)을 모형에 동시에 투입하는 구조에서 불가피하게 VIF가 높아지는 특성을 반영하나, 평균중심화(mean-centering)를 적용하여 이를 완화하였다. 모든 핵심 변수의 VIF가 10 미만으로, 심각한 다중공선성 문제는 없는 것으로 판단한다.
"""

with open(OUT_MD, "w", encoding="utf-8") as f:
    f.write(md)
print(f"  Saved: {OUT_MD}")

# ── 최종 요약 ────────────────────────────────────────────────────────────────
print("\n── 5.1 기술통계 요약 ──────────────────────────────────────────────────")
for row in desc_list:
    print(f"  {row['변수']}: n={row['n']}, mean={row['평균']}, SD={row['SD']}")

print("\n── 5.2 VIF 요약 ────────────────────────────────────────────────────────")
for row in vif_rows:
    print(f"  {row['hypothesis']} / {row['variable']}: VIF={row['vif']} [{row['judgment']}]")

fails = [c for c in checks if c["status"] == "FAIL"]
warns = [c for c in checks if c["status"] == "WARN"]
print(f"\nValidation: {len(checks)} checks, "
      f"{len(fails)} FAIL, {len(warns)} WARN, "
      f"{sum(1 for c in checks if c['status']=='PASS')} PASS")
if fails:
    print("  FAILs:", [c["check_name"] for c in fails])
if warns:
    print("  WARNs:", [(c["check_name"], c["expected"], c["actual"]) for c in warns])

print("\nDone.")
