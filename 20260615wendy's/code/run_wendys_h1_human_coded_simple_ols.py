"""
H1 Human-Coded Sample Simple OLS
---------------------------------
표본: H1인간검증표본 == 1, 유머레이블최종 in {0, 1}
IV:  유머레이블최종 (binary dummy)
DVs: log1p 변환 7개 engagement 지표
"""

import csv
import math
import os

# ── 경로 ─────────────────────────────────────────────────────────────────────
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_FILE = os.path.join(BASE, "data", "wendys_h1_h2_h3_r_replication_dataset.csv")
RESULT_DIR = os.path.join(BASE, "result")
RESULT_FILE = os.path.join(RESULT_DIR, "wendys_h1_human_coded_simple_ols_results.csv")

# ── t-분포 p-value 계산 (standard library only) ───────────────────────────────
def _betacf(x, a, b):
    """Continued fraction evaluation for incomplete beta function (NR algorithm)."""
    MAXIT = 300
    EPS = 3.0e-10
    FPMIN = 1.0e-300

    qab = a + b
    qap = a + 1.0
    qam = a - 1.0
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
        if abs(d) < FPMIN:
            d = FPMIN
        c = 1.0 + aa / c
        if abs(c) < FPMIN:
            c = FPMIN
        d = 1.0 / d
        h *= d * c

        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        if abs(d) < FPMIN:
            d = FPMIN
        c = 1.0 + aa / c
        if abs(c) < FPMIN:
            c = FPMIN
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) <= EPS:
            break

    return h


def _betainc(a, b, x):
    """Regularized incomplete beta function I(x; a, b)."""
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    lbeta = math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b)
    bt = math.exp(lbeta + a * math.log(x) + b * math.log(1.0 - x))
    if x < (a + 1.0) / (a + b + 2.0):
        return bt * _betacf(x, a, b) / a
    else:
        return 1.0 - bt * _betacf(1.0 - x, b, a) / b


def t_pvalue_twotail(t_stat, df):
    """Two-tailed p-value from t-distribution."""
    t = abs(t_stat)
    x = float(df) / (float(df) + t * t)
    return _betainc(float(df) / 2.0, 0.5, x)


# ── OLS 함수 (intercept + 1 predictor) ────────────────────────────────────────
def simple_ols(x_vals, y_vals):
    """
    Returns: coef, intercept, se, t_stat, p_val, r2, adj_r2
    Simple OLS: y = b0 + b1*x
    """
    n = len(x_vals)
    assert n == len(y_vals) and n > 2

    x_mean = sum(x_vals) / n
    y_mean = sum(y_vals) / n

    ss_xx = sum((xi - x_mean) ** 2 for xi in x_vals)
    ss_xy = sum((xi - x_mean) * (yi - y_mean) for xi, yi in zip(x_vals, y_vals))
    ss_yy = sum((yi - y_mean) ** 2 for yi in y_vals)

    b1 = ss_xy / ss_xx
    b0 = y_mean - b1 * x_mean

    y_hat = [b0 + b1 * xi for xi in x_vals]
    sse = sum((yi - yhi) ** 2 for yi, yhi in zip(y_vals, y_hat))
    sst = ss_yy

    r2 = 1.0 - sse / sst if sst > 0 else 0.0
    adj_r2 = 1.0 - (1.0 - r2) * (n - 1) / (n - 2)

    mse = sse / (n - 2)
    se_b1 = math.sqrt(mse / ss_xx)

    t_stat = b1 / se_b1
    p_val = t_pvalue_twotail(t_stat, n - 2)

    return b1, b0, se_b1, t_stat, p_val, r2, adj_r2


# ── 데이터 로드 ─────────────────────────────────────────────────────────────────
print("Loading data ...")
with open(DATA_FILE, encoding="utf-8-sig") as f:
    all_rows = list(csv.DictReader(f))

print(f"Total rows: {len(all_rows)}")

# 표본 필터: H1인간검증표본 == 1, 유머레이블최종 in {0, 1}
sample = [
    r for r in all_rows
    if r["H1인간검증표본"] == "1"
    and r["유머레이블최종"] in ("0", "1", "0.0", "1.0")
]

n_total = len(sample)
humor_rows = [r for r in sample if float(r["유머레이블최종"]) == 1.0]
nonhumor_rows = [r for r in sample if float(r["유머레이블최종"]) == 0.0]
n_humor = len(humor_rows)
n_nonhumor = len(nonhumor_rows)

print(f"H1 human-coded sample n = {n_total}")
print(f"  humor n    = {n_humor}")
print(f"  non-humor n = {n_nonhumor}")

# 기대값 검증
assert n_total == 597, f"Expected 597, got {n_total}"
assert n_humor == 309, f"Expected 309, got {n_humor}"
assert n_nonhumor == 288, f"Expected 288, got {n_nonhumor}"
print("Sample size validation PASSED")

# ── DV 정의 ────────────────────────────────────────────────────────────────────
def get_dv(row, dv_name):
    fav   = float(row["좋아요수"])
    rt    = float(row["리트윗수"])
    reply = float(row["답글수"])
    quote = float(row["인용수"])
    bm    = float(row["북마크수"])
    if dv_name == "log1p_engagement_total":
        return math.log1p(fav + rt + reply + quote + bm)
    elif dv_name == "log1p_engagement_favorite_retweet":
        return math.log1p(fav + rt)
    elif dv_name == "log1p_favorite_count":
        return math.log1p(fav)
    elif dv_name == "log1p_retweet_count":
        return math.log1p(rt)
    elif dv_name == "log1p_reply_count":
        return math.log1p(reply)
    elif dv_name == "log1p_quote_count":
        return math.log1p(quote)
    elif dv_name == "log1p_bookmark_count":
        return math.log1p(bm)
    else:
        raise ValueError(f"Unknown DV: {dv_name}")


DV_NAMES = [
    "log1p_engagement_total",
    "log1p_engagement_favorite_retweet",
    "log1p_favorite_count",
    "log1p_retweet_count",
    "log1p_reply_count",
    "log1p_quote_count",
    "log1p_bookmark_count",
]

IV_COL = "유머레이블최종"

# ── 회귀 실행 ──────────────────────────────────────────────────────────────────
def significance_star(p):
    if p < 0.01:
        return "***"
    elif p < 0.05:
        return "**"
    elif p < 0.10:
        return "*"
    else:
        return ""


def interp_flag(coef, p):
    if coef > 0 and p < 0.05:
        return "supports_H1"
    elif coef > 0 and p < 0.10:
        return "weak_support"
    elif coef > 0:
        return "positive_not_significant"
    else:
        return "not_support"


results = []

for dv_name in DV_NAMES:
    x_vals = [float(r[IV_COL]) for r in sample]
    y_vals = [get_dv(r, dv_name) for r in sample]

    humor_y   = [get_dv(r, dv_name) for r in humor_rows]
    nonhumor_y = [get_dv(r, dv_name) for r in nonhumor_rows]
    humor_mean   = sum(humor_y) / len(humor_y)
    nonhumor_mean = sum(nonhumor_y) / len(nonhumor_y)

    coef, intercept, se, t_stat, p_val, r2, adj_r2 = simple_ols(x_vals, y_vals)

    sig = significance_star(p_val)
    flag = interp_flag(coef, p_val)

    row = {
        "sample_type": "human_coded_n597",
        "model_name": "Simple_OLS",
        "dv": dv_name,
        "iv": IV_COL,
        "n": n_total,
        "humor_n": n_humor,
        "nonhumor_n": n_nonhumor,
        "humor_mean": round(humor_mean, 6),
        "nonhumor_mean": round(nonhumor_mean, 6),
        "coefficient": round(coef, 6),
        "standard_error": round(se, 6),
        "t_value": round(t_stat, 4),
        "p_value": round(p_val, 6),
        "r_squared": round(r2, 6),
        "adj_r_squared": round(adj_r2, 6),
        "significance": sig,
        "interpretation_flag": flag,
        "included_time_fe": "none",
        "included_post_format_variables": "none",
        "notes": "Simple OLS, no FE, no controls",
    }
    results.append(row)
    print(f"  {dv_name}: β={coef:.4f} SE={se:.4f} p={p_val:.4f} R²={r2:.4f} {flag}")

# ── 결과 저장 ──────────────────────────────────────────────────────────────────
FIELDNAMES = [
    "sample_type", "model_name", "dv", "iv", "n", "humor_n", "nonhumor_n",
    "humor_mean", "nonhumor_mean", "coefficient", "standard_error",
    "t_value", "p_value", "r_squared", "adj_r_squared",
    "significance", "interpretation_flag",
    "included_time_fe", "included_post_format_variables", "notes",
]

with open(RESULT_FILE, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
    writer.writeheader()
    writer.writerows(results)

print(f"\nResults saved to: {RESULT_FILE}")

# ── Primary DV sanity check ─────────────────────────────────────────────────
primary = next(r for r in results if r["dv"] == "log1p_engagement_total")
print("\n── Primary DV sanity check ──────────────────────────────────────────")
print(f"  n         = {primary['n']}        (expected 597)")
print(f"  humor_n   = {primary['humor_n']}       (expected 309)")
print(f"  nonhumor_n= {primary['nonhumor_n']}       (expected 288)")
print(f"  coefficient = {primary['coefficient']}  (expected ≈ 0.5043)")
print(f"  std_error   = {primary['standard_error']}  (expected ≈ 0.1418)")
print(f"  p_value     = {primary['p_value']}  (expected ≈ 0.0004)")
print(f"  r_squared   = {primary['r_squared']}  (expected ≈ 0.0208)")
print(f"  adj_r_sq    = {primary['adj_r_squared']}  (expected ≈ 0.0192)")
print(f"  flag        = {primary['interpretation_flag']}")

print("\nDone.")
