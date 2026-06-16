"""
H3 Centered Moderation Model
-------------------------------
H3: log(Engagement) = β0 + β1*Humor + β2*IC + β3*IC² + β4*(Humor×IC) + β5*(Humor×IC²) + controls + FE
H3 지지: β4 > 0 AND β5 < 0, both p < .05
IC = 유머비율LOO분기 평균중심화 (mean-centered within H3 sample)
"""

import csv
import math
import os

# ── 경로 ────────────────────────────────────────────────────────────────────
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_IN = os.path.join(BASE, "data", "wendys_h1_h2_h3_r_replication_dataset.csv")
DATA_OUT = os.path.join(BASE, "data", "wendys_h3_moderation_centered_interaction_dataset.csv")
RESULT_DIR = os.path.join(BASE, "result")
RESULT_CSV = os.path.join(RESULT_DIR, "wendys_h3_moderation_centered_interaction_results.csv")

# ── t-분포 p-value (standard library only) ───────────────────────────────────
def _betacf(x, a, b):
    MAXIT, EPS, FPMIN = 300, 3.0e-10, 1.0e-300
    qab, qap, qam = a + b, a + 1.0, a - 1.0
    c = 1.0
    d = 1.0 - qab * x / qap
    if abs(d) < FPMIN:
        d = FPMIN
    d = 1.0 / d
    h = d
    for m in range(1, MAXIT + 1):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        if abs(d) < FPMIN: d = FPMIN
        c = 1.0 + aa / c
        if abs(c) < FPMIN: c = FPMIN
        d = 1.0 / d
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        if abs(d) < FPMIN: d = FPMIN
        c = 1.0 + aa / c
        if abs(c) < FPMIN: c = FPMIN
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) <= EPS:
            break
    return h

def _betainc(a, b, x):
    if x <= 0.0: return 0.0
    if x >= 1.0: return 1.0
    lbeta = math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b)
    bt = math.exp(lbeta + a * math.log(x) + b * math.log(1.0 - x))
    if x < (a + 1.0) / (a + b + 2.0):
        return bt * _betacf(x, a, b) / a
    else:
        return 1.0 - bt * _betacf(1.0 - x, b, a) / b

def t_pvalue_twotail(t_stat, df):
    t = abs(t_stat)
    x = float(df) / (float(df) + t * t)
    return _betainc(float(df) / 2.0, 0.5, x)

# ── 행렬 연산 (list-of-lists, row-major) ─────────────────────────────────────
def mat_transpose(A):
    if not A: return []
    return [[A[r][c] for r in range(len(A))] for c in range(len(A[0]))]

def mat_mul(A, B):
    ra, ca = len(A), len(A[0])
    rb, cb = len(B), len(B[0])
    assert ca == rb
    C = [[0.0] * cb for _ in range(ra)]
    for i in range(ra):
        for k in range(ca):
            if A[i][k] == 0.0:
                continue
            for j in range(cb):
                C[i][j] += A[i][k] * B[k][j]
    return C

def mat_vec_mul(A, v):
    return [sum(A[i][j] * v[j] for j in range(len(v))) for i in range(len(A))]

def mat_inv(A):
    """Gauss-Jordan elimination with partial pivoting."""
    n = len(A)
    M = [A[i][:] + [1.0 if i == j else 0.0 for j in range(n)] for i in range(n)]
    for col in range(n):
        pivot = max(range(col, n), key=lambda r: abs(M[r][col]))
        M[col], M[pivot] = M[pivot], M[col]
        if abs(M[col][col]) < 1e-14:
            raise ValueError(f"Matrix is singular or near-singular at col {col}")
        scale = M[col][col]
        M[col] = [v / scale for v in M[col]]
        for row in range(n):
            if row != col:
                factor = M[row][col]
                M[row] = [M[row][k] - factor * M[col][k] for k in range(2 * n)]
    return [row[n:] for row in M]

def ols_fit(X_rows, y_vals):
    """
    X_rows: list of row vectors (already includes intercept column)
    y_vals: list of floats
    Returns: coefficients, se, t_stats, p_vals, r2, adj_r2, aic, bic
    """
    n = len(y_vals)
    k = len(X_rows[0])
    df_e = n - k

    # XtX[i][j] = sum_l X[l][i] * X[l][j]
    XtX = [[sum(X_rows[l][i] * X_rows[l][j] for l in range(n))
             for j in range(k)] for i in range(k)]
    # Xty[i] = sum_l X[l][i] * y[l]
    Xty = [sum(X_rows[l][i] * y_vals[l] for l in range(n)) for i in range(k)]

    XtX_inv = mat_inv(XtX)
    coefs = mat_vec_mul(XtX_inv, Xty)

    y_hat = [sum(coefs[j] * X_rows[i][j] for j in range(k)) for i in range(n)]
    residuals = [y_vals[i] - y_hat[i] for i in range(n)]
    sse = sum(r ** 2 for r in residuals)
    y_mean = sum(y_vals) / n
    sst = sum((yi - y_mean) ** 2 for yi in y_vals)

    r2 = 1.0 - sse / sst if sst > 0 else 0.0
    adj_r2 = 1.0 - (1.0 - r2) * (n - 1) / df_e

    mse = sse / df_e
    ses = [math.sqrt(max(XtX_inv[j][j] * mse, 0.0)) for j in range(k)]
    t_stats = [coefs[j] / ses[j] if ses[j] > 0 else float("nan") for j in range(k)]
    p_vals = [t_pvalue_twotail(t, df_e) if not math.isnan(t) else float("nan")
              for t in t_stats]

    aic = n * math.log(sse / n) + 2 * k
    bic = n * math.log(sse / n) + k * math.log(n)

    return coefs, ses, t_stats, p_vals, r2, adj_r2, aic, bic

# ── 데이터 로드 ──────────────────────────────────────────────────────────────
print("Loading data ...")
with open(DATA_IN, encoding="utf-8-sig") as f:
    all_rows = list(csv.DictReader(f))

# H3 표본
h3 = [r for r in all_rows if r["H3분석표본"] == "1"]
n_h3 = len(h3)
print(f"H3분석표본 n = {n_h3}")
assert n_h3 == 960, f"Expected 960, got {n_h3}"

quarters = sorted(set(r["연도분기"] for r in h3))
q_count = len(quarters)
print(f"quarter_count = {q_count}")
assert q_count == 25, f"Expected 25, got {q_count}"

# 결측 확인
missing_intensity = sum(1 for r in h3 if r["유머비율LOO분기"] in ("", "NA", "None"))
assert missing_intensity == 0, f"유머비율LOO분기 결측 {missing_intensity}개"
print("유머비율LOO분기 결측 없음 ✓")

humor_vals = [int(r["유머예측이진"]) for r in h3]
assert set(humor_vals) <= {0, 1}, "유머예측이진 0/1 외 값 존재"
print("유머예측이진 0/1 확인 ✓")

# ── 평균중심화 ────────────────────────────────────────────────────────────────
raw_intensity = [float(r["유머비율LOO분기"]) for r in h3]
mean_raw = sum(raw_intensity) / len(raw_intensity)
min_raw = min(raw_intensity)
max_raw = max(raw_intensity)

ic = [v - mean_raw for v in raw_intensity]
ic_sq = [v ** 2 for v in ic]
mean_centered = sum(ic) / len(ic)

print(f"intensity_mean_raw = {mean_raw:.6f}")
print(f"intensity_mean_centered ≈ {mean_centered:.2e}  (should be ~0)")
assert abs(mean_centered) < 1e-10, f"평균중심화 오류: mean = {mean_centered}"

# interaction terms
humor_x_ic = [humor_vals[i] * ic[i] for i in range(n_h3)]
humor_x_ic_sq = [humor_vals[i] * ic_sq[i] for i in range(n_h3)]

# sample row 검증
i_test = next(i for i in range(n_h3) if humor_vals[i] == 1)
expected_ic = raw_intensity[i_test] - mean_raw
expected_xic = 1 * expected_ic
assert abs(humor_x_ic[i_test] - expected_xic) < 1e-12, "interaction term 오류"
print("interaction term sample 검증 ✓")

# DVs
dv_total = [math.log1p(float(r["좋아요수"]) + float(r["리트윗수"]) +
                        float(r["답글수"]) + float(r["인용수"]) + float(r["북마크수"]))
            for r in h3]

# ── 데이터셋 저장 ─────────────────────────────────────────────────────────────
print("Saving dataset ...")
dataset_rows = []
for i, r in enumerate(h3):
    dataset_rows.append({
        "게시물ID": r["게시물ID"],
        "작성일": r["작성일"],
        "작성연도": r["작성연도"],
        "작성월": r["작성월"],
        "작성시간": r["작성시간"],
        "연도분기": r["연도분기"],
        "log1p_engagement_total": round(dv_total[i], 8),
        "유머예측이진": r["유머예측이진"],
        "유머비율LOO분기": r["유머비율LOO분기"],
        "유머비율LOO분기_평균중심화": round(ic[i], 10),
        "유머비율LOO분기_평균중심화제곱": round(ic_sq[i], 10),
        "유머X유머강도중심화": round(humor_x_ic[i], 10),
        "유머X유머강도중심화제곱": round(humor_x_ic_sq[i], 10),
        "텍스트길이": r["텍스트길이"],
        "해시태그수": r["해시태그수"],
        "멘션수": r["멘션수"],
        "H3분석표본": r["H3분석표본"],
    })

DATA_OUT_COLS = [
    "게시물ID", "작성일", "작성연도", "작성월", "작성시간", "연도분기",
    "log1p_engagement_total", "유머예측이진",
    "유머비율LOO분기", "유머비율LOO분기_평균중심화",
    "유머비율LOO분기_평균중심화제곱",
    "유머X유머강도중심화", "유머X유머강도중심화제곱",
    "텍스트길이", "해시태그수", "멘션수", "H3분석표본",
]
with open(DATA_OUT, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=DATA_OUT_COLS)
    w.writeheader()
    w.writerows(dataset_rows)
print(f"Dataset saved: {DATA_OUT} ({len(dataset_rows)} rows)")

# ── Fixed Effect 더미 생성 ────────────────────────────────────────────────────
def make_dummies(col_vals):
    """Reference = first sorted category (dropped)."""
    cats = sorted(set(col_vals))
    ref = cats[0]
    non_ref = cats[1:]
    dummy_mat = {}
    for cat in non_ref:
        dummy_mat[cat] = [1 if v == cat else 0 for v in col_vals]
    return non_ref, dummy_mat

year_vals = [r["작성연도"] for r in h3]
month_vals = [r["작성월"] for r in h3]
hour_vals = [r["작성시간"] for r in h3]

year_cats, year_dm = make_dummies(year_vals)
month_cats, month_dm = make_dummies(month_vals)
hour_cats, hour_dm = make_dummies(hour_vals)

# ── 모형 빌더 ────────────────────────────────────────────────────────────────
def build_X(include_fe, include_controls):
    """Build design matrix rows.
    Core predictors: intercept, Humor, IC, IC², Humor×IC, Humor×IC²
    """
    X = []
    for i in range(n_h3):
        row = [
            1.0,                  # intercept
            float(humor_vals[i]), # Humor
            ic[i],                # IC
            ic_sq[i],             # IC²
            humor_x_ic[i],        # Humor×IC
            humor_x_ic_sq[i],     # Humor×IC²
        ]
        if include_controls:
            row += [
                float(h3[i]["텍스트길이"]),
                float(h3[i]["해시태그수"]),
                float(h3[i]["멘션수"]),
            ]
        if include_fe:
            for cat in year_cats:
                row.append(float(year_dm[cat][i]))
            for cat in month_cats:
                row.append(float(month_dm[cat][i]))
            for cat in hour_cats:
                row.append(float(hour_dm[cat][i]))
        X.append(row)
    return X

# ── 3개 모형 실행 ─────────────────────────────────────────────────────────────
model_specs = [
    ("M0_simple_interaction",  False, False, "none", "none"),
    ("M1_time_fe",             True,  False, "year_FE+month_FE+hour_FE", "none"),
    ("M2_time_fe_controls",    True,  True,  "year_FE+month_FE+hour_FE",
     "텍스트길이+해시태그수+멘션수"),
]

def sig_star(p):
    if p < 0.01: return "***"
    if p < 0.05: return "**"
    if p < 0.10: return "*"
    return ""

def interp_h3(coef4, p4, coef5, p5):
    if coef4 > 0 and coef5 < 0 and p4 < 0.05 and p5 < 0.05:
        return "supports_H3"
    if coef4 > 0 and coef5 < 0 and (p4 < 0.10 or p5 < 0.10):
        return "weak_support"
    return "not_support"

results = []
humor_n = sum(1 for v in humor_vals if v == 1)
nonhumor_n = sum(1 for v in humor_vals if v == 0)

for mname, use_fe, use_ctrl, fe_label, ctrl_label in model_specs:
    print(f"\nRunning {mname} ...")
    X = build_X(use_fe, use_ctrl)
    coefs, ses, ts, ps, r2, adj_r2, aic, bic = ols_fit(X, dv_total)

    # coef indices: 0=intercept, 1=Humor, 2=IC, 3=IC², 4=Humor×IC, 5=Humor×IC²
    # controls (if present): 6,7,8; FE dummies follow
    c1, c2, c3, c4, c5 = coefs[1], coefs[2], coefs[3], coefs[4], coefs[5]
    p1, p2, p3, p4, p5 = ps[1], ps[2], ps[3], ps[4], ps[5]
    s1, s2, s3, s4, s5 = ses[1], ses[2], ses[3], ses[4], ses[5]

    flag = interp_h3(c4, p4, c5, p5)

    print(f"  β_Humor = {c1:.4f} (p={p1:.4f})")
    print(f"  β_IC    = {c2:.4f} (p={p2:.4f})")
    print(f"  β_IC²   = {c3:.4f} (p={p3:.4f})")
    print(f"  β4 H×IC = {c4:.4f} (p={p4:.4f})  β4>0: {c4>0}")
    print(f"  β5 H×IC²= {c5:.4f} (p={p5:.4f})  β5<0: {c5<0}")
    print(f"  R²={r2:.4f}  Adj R²={adj_r2:.4f}  flag={flag}")

    results.append({
        "model_name": mname,
        "dv": "log1p_engagement_total",
        "n": n_h3,
        "quarter_count": q_count,
        "humor_n": humor_n,
        "nonhumor_n": nonhumor_n,
        "intensity_mean_raw": round(mean_raw, 6),
        "intensity_min_raw": round(min_raw, 6),
        "intensity_max_raw": round(max_raw, 6),
        "intensity_mean_centered": round(mean_centered, 14),
        "coef_humor": round(c1, 6),
        "p_humor": round(p1, 6),
        "coef_intensity_centered": round(c2, 6),
        "p_intensity_centered": round(p2, 6),
        "coef_intensity_centered_sq": round(c3, 6),
        "p_intensity_centered_sq": round(p3, 6),
        "coef_humor_x_intensity_centered": round(c4, 6),
        "p_humor_x_intensity_centered": round(p4, 6),
        "coef_humor_x_intensity_centered_sq": round(c5, 6),
        "p_humor_x_intensity_centered_sq": round(p5, 6),
        "h3_condition_beta4_positive": c4 > 0,
        "h3_condition_beta5_negative": c5 < 0,
        "h3_condition_beta4_significant": p4 < 0.05,
        "h3_condition_beta5_significant": p5 < 0.05,
        "r_squared": round(r2, 6),
        "adj_r_squared": round(adj_r2, 6),
        "aic": round(aic, 4),
        "bic": round(bic, 4),
        "included_time_fe": fe_label,
        "included_post_format_controls": ctrl_label,
        "interpretation_flag": flag,
    })

# ── 결과 CSV 저장 ─────────────────────────────────────────────────────────────
RESULT_COLS = [
    "model_name", "dv", "n", "quarter_count", "humor_n", "nonhumor_n",
    "intensity_mean_raw", "intensity_min_raw", "intensity_max_raw",
    "intensity_mean_centered",
    "coef_humor", "p_humor",
    "coef_intensity_centered", "p_intensity_centered",
    "coef_intensity_centered_sq", "p_intensity_centered_sq",
    "coef_humor_x_intensity_centered", "p_humor_x_intensity_centered",
    "coef_humor_x_intensity_centered_sq", "p_humor_x_intensity_centered_sq",
    "h3_condition_beta4_positive", "h3_condition_beta5_negative",
    "h3_condition_beta4_significant", "h3_condition_beta5_significant",
    "r_squared", "adj_r_squared", "aic", "bic",
    "included_time_fe", "included_post_format_controls", "interpretation_flag",
]

with open(RESULT_CSV, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=RESULT_COLS)
    w.writeheader()
    w.writerows(results)
print(f"\nResults saved: {RESULT_CSV}")

# ── Primary model summary ─────────────────────────────────────────────────────
primary = next(r for r in results if r["model_name"] == "M2_time_fe_controls")
print("\n── H3 Primary Model (M2) Summary ───────────────────────────────────────")
print(f"  DV: log1p_engagement_total,  n = {primary['n']}")
print(f"  β4 (Humor×IC)  = {primary['coef_humor_x_intensity_centered']:+.4f}  "
      f"p = {primary['p_humor_x_intensity_centered']:.4f}  "
      f"β4>0: {primary['h3_condition_beta4_positive']}")
print(f"  β5 (Humor×IC²) = {primary['coef_humor_x_intensity_centered_sq']:+.4f}  "
      f"p = {primary['p_humor_x_intensity_centered_sq']:.4f}  "
      f"β5<0: {primary['h3_condition_beta5_negative']}")
print(f"  R² = {primary['r_squared']:.4f},  Adj R² = {primary['adj_r_squared']:.4f}")
print(f"  H3 interpretation: {primary['interpretation_flag']}")
print("\nDone.")
