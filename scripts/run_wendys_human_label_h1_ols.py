"""
scripts/run_wendys_human_label_h1_ols.py

Wendy's Partial Human-Coded Label — H1 단순 OLS 분석
=====================================================

이 스크립트의 목적:
    `data/derived/humor/human_labels/wendys_human_label_raw_linked.csv`에 저장된
    사람이 직접 코딩한 유머 레이블(human_humor_binary)을 독립변수(IV)로 사용하여,
    Wendy's 게시글 수준의 engagement 반응과의 연관성을 단순 OLS로 검토한다.

IV 정의:
    human_humor_binary = 1 (유머) / 0 (비유머)
    -- 머신러닝 점수가 아닌 사람이 직접 판단한 이진 레이블
    -- label_missing_flag = true인 행(1건)은 분석에서 제외

DV 목록 (log1p 변환):
    log1p_engagement_total        = log(1 + reply + favorite + retweet + quote + bookmark)
    log1p_engagement_fav_rt       = log(1 + favorite + retweet)
    log1p_favorite_count
    log1p_retweet_count
    log1p_reply_count
    log1p_quote_count
    log1p_bookmark_count

회귀식:
    log1p_DV_i = α + β × human_humor_binary_i + ε_i

분석 설계:
    - 단순 이변량 OLS (statsmodels)
    - 통제변수 없음 / 고정효과 없음 / Robust SE 없음
    - 이 분석은 Wendy's partial human review sample(68건)에 국한된 탐색적 분석이다
    - 인과효과를 주장하지 않는다

중요 제약:
    - data/wendys/posts.json 수정 금지
    - dashboard/data/ 수정 금지
    - human label을 전체 gold label로 일반화하지 않는다

입력:
    data/derived/humor/human_labels/wendys_human_label_raw_linked.csv

출력:
    data/derived/humor/human_labels/wendys_human_label_h1_ols_results.csv
    data/derived/humor/human_labels/wendys_human_label_h1_ols_summary.md
"""

import csv
import math
import sys
from pathlib import Path
from datetime import datetime

import numpy as np
import statsmodels.api as sm

# ─────────────────────────────────────────────────────────────────────────────
# 경로 설정
# ─────────────────────────────────────────────────────────────────────────────
INPUT_CSV  = Path("data/derived/humor/human_labels/wendys_human_label_raw_linked.csv")
OUT_RESULT = Path("data/derived/humor/human_labels/wendys_human_label_h1_ols_results.csv")
OUT_SUMMARY= Path("data/derived/humor/human_labels/wendys_human_label_h1_ols_summary.md")


def safe_int(v, default=0):
    try:
        return int(float(v))
    except Exception:
        return default


def median_of(lst):
    s = sorted(x for x in lst if x is not None and math.isfinite(x))
    n = len(s)
    if not s:
        return float("nan")
    return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2.0


def run_ols(x_vals, y_vals):
    """
    단순 이변량 OLS를 실행하고 핵심 통계량을 반환한다.
    IV(x)는 human_humor_binary (0/1 dummy).
    """
    X   = sm.add_constant(np.array(x_vals, dtype=float))
    res = sm.OLS(np.array(y_vals, dtype=float), X).fit()
    ci  = res.conf_int(0.05)
    return dict(
        n_obs     = int(res.nobs),
        intercept = float(res.params[0]),
        beta      = float(res.params[1]),
        se        = float(res.bse[1]),
        t         = float(res.tvalues[1]),
        p         = float(res.pvalues[1]),
        ci_lo     = float(ci[0][1]),
        ci_hi     = float(ci[1][1]),
        r2        = float(res.rsquared),
        adj_r2    = float(res.rsquared_adj),
    )


def h1_label(beta, p):
    """H1 해석 레이블 (한국어)"""
    if beta > 0 and p < 0.05:
        return "H1 예비적 지지"
    elif beta > 0:
        return "H1 방향성 지지"
    return "H1 지지 없음"


def direction_str(beta):
    return "positive" if beta > 0 else ("negative" if beta < 0 else "zero")


def main():
    # ─────────────────────────────────────────────────────────────
    # 단계 1. 데이터 읽기 및 유효 행 필터링
    # label_missing_flag = true인 행(1건) 제외
    # ─────────────────────────────────────────────────────────────
    if not INPUT_CSV.exists():
        print(f"[FAIL] 입력 파일 없음: {INPUT_CSV}", file=sys.stderr)
        sys.exit(1)

    with open(INPUT_CSV, newline="", encoding="utf-8") as f:
        all_rows = list(csv.DictReader(f))

    # label이 있는 행만 사용 (human_humor_binary가 0 또는 1)
    valid_rows = [
        r for r in all_rows
        if r.get("label_missing_flag", "true") == "false"
        and r.get("human_humor_binary", "") in ("0", "1")
    ]
    n_total  = len(all_rows)
    n_valid  = len(valid_rows)
    n_skip   = n_total - n_valid
    print(f"[1] 전체 행: {n_total}건 / 분석 사용: {n_valid}건 (제외: {n_skip}건 — label 결측)")

    # ─────────────────────────────────────────────────────────────
    # 단계 2. IV 및 DV 구성
    # IV: human_humor_binary (0/1)
    # engagement는 정수 변환 후 log1p 적용
    # ─────────────────────────────────────────────────────────────
    humor_binary = [int(r["human_humor_binary"]) for r in valid_rows]
    n_humor      = sum(humor_binary)
    n_nonhumor   = n_valid - n_humor
    print(f"[2] IV — humor(1): {n_humor}건 / non-humor(0): {n_nonhumor}건")

    def eng_vals(r):
        return (safe_int(r["reply_count"]) + safe_int(r["favorite_count"]) +
                safe_int(r["retweet_count"]) + safe_int(r["quote_count"]) +
                safe_int(r["bookmark_count"]))

    for r in valid_rows:
        fav  = safe_int(r["favorite_count"])
        rt   = safe_int(r["retweet_count"])
        rep  = safe_int(r["reply_count"])
        qt   = safe_int(r["quote_count"])
        bm   = safe_int(r["bookmark_count"])
        tot  = fav + rt + rep + qt + bm
        r["_eng_total"]  = tot
        r["_eng_fav_rt"] = fav + rt
        r["_fav"]  = fav
        r["_rt"]   = rt
        r["_rep"]  = rep
        r["_qt"]   = qt
        r["_bm"]   = bm

    # DV 정의: (변수명, 레이블, 값 생성 함수)
    dv_specs = [
        ("log1p_engagement_total",   lambda r: math.log1p(r["_eng_total"])),
        ("log1p_engagement_fav_rt",  lambda r: math.log1p(r["_eng_fav_rt"])),
        ("log1p_favorite_count",     lambda r: math.log1p(r["_fav"])),
        ("log1p_retweet_count",      lambda r: math.log1p(r["_rt"])),
        ("log1p_reply_count",        lambda r: math.log1p(r["_rep"])),
        ("log1p_quote_count",        lambda r: math.log1p(r["_qt"])),
        ("log1p_bookmark_count",     lambda r: math.log1p(r["_bm"])),
    ]

    # ─────────────────────────────────────────────────────────────
    # 단계 3. 단순 OLS 실행
    # 회귀식: log1p_DV_i = α + β × human_humor_binary_i + ε_i
    # ─────────────────────────────────────────────────────────────
    print("[3] 단순 OLS 실행 중...")
    ols_rows = []
    main_res = None

    for dv_name, dv_fn in dv_specs:
        y   = [dv_fn(r) for r in valid_rows]
        res = run_ols(humor_binary, y)
        print(f"  {dv_name}: β={res['beta']:.4f}  SE={res['se']:.4f}  "
              f"p={res['p']:.4f}  R²={res['r2']:.4f}")

        row = {
            "dv":                       dv_name,
            "iv":                       "human_humor_binary",
            "model_name":               "Simple OLS",
            "n_obs":                    res["n_obs"],
            "n_humor":                  n_humor,
            "n_nonhumor":               n_nonhumor,
            "intercept":                "%.6f" % res["intercept"],
            "beta_human_humor_binary":  "%.6f" % res["beta"],
            "standard_error":           "%.6f" % res["se"],
            "t_value":                  "%.4f"  % res["t"],
            "p_value":                  "%.6f" % res["p"],
            "ci_lower_95":              "%.6f" % res["ci_lo"],
            "ci_upper_95":              "%.6f" % res["ci_hi"],
            "r_squared":                "%.6f" % res["r2"],
            "adj_r_squared":            "%.6f" % res["adj_r2"],
            "direction":                direction_str(res["beta"]),
            "h1_interpretation":        h1_label(res["beta"], res["p"]),
            "notes": ("단순 이변량 OLS; IV=human_humor_binary(0/1); "
                      "통제변수 없음; FE 없음; 표준 SE; "
                      "Wendy's partial human review sample"),
        }
        ols_rows.append(row)
        if dv_name == "log1p_engagement_total":
            main_res = res

    # ─────────────────────────────────────────────────────────────
    # 단계 4. 결과 CSV 저장
    # ─────────────────────────────────────────────────────────────
    result_cols = [
        "dv", "iv", "model_name", "n_obs", "n_humor", "n_nonhumor",
        "intercept", "beta_human_humor_binary", "standard_error",
        "t_value", "p_value", "ci_lower_95", "ci_upper_95",
        "r_squared", "adj_r_squared", "direction", "h1_interpretation", "notes",
    ]
    OUT_RESULT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_RESULT, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=result_cols)
        w.writeheader()
        w.writerows(ols_rows)
    print(f"[4] 결과 CSV 저장: {OUT_RESULT}")

    # ─────────────────────────────────────────────────────────────
    # 단계 5. 한국어 요약 마크다운 생성
    # ─────────────────────────────────────────────────────────────
    _write_summary(valid_rows, ols_rows, main_res, n_total, n_valid, n_skip,
                   n_humor, n_nonhumor, humor_binary, dv_specs)
    print(f"[5] 요약 저장: {OUT_SUMMARY}")
    print("\n완료.")


def _write_summary(valid_rows, ols_rows, mr, n_total, n_valid, n_skip,
                   n_humor, n_nonhumor, humor_binary, dv_specs):
    """한국어 분석 요약을 마크다운으로 작성한다."""

    # DV별 그룹 평균 계산 (유머 vs 비유머)
    def grp_means(dv_fn):
        humor_vals    = [dv_fn(r) for r, h in zip(valid_rows, humor_binary) if h == 1]
        nonhumor_vals = [dv_fn(r) for r, h in zip(valid_rows, humor_binary) if h == 0]
        return (sum(humor_vals)/len(humor_vals) if humor_vals else float("nan"),
                sum(nonhumor_vals)/len(nonhumor_vals) if nonhumor_vals else float("nan"))

    dv_fn_map = {name: fn for name, fn in dv_specs}

    # OLS 결과 테이블
    ols_table = ("| 종속변수 (DV) | β | SE | p-value | R² | H1 해석 |\n"
                 "|---|---|---|---|---|---|\n")
    for row in ols_rows:
        ols_table += (f"| `{row['dv']}` | {row['beta_human_humor_binary']} "
                      f"| {row['standard_error']} | {row['p_value']} "
                      f"| {row['r_squared']} | {row['h1_interpretation']} |\n")

    # 그룹 평균 테이블
    grp_table = ("| 종속변수 | 유머(1) 평균 | 비유머(0) 평균 | 차이 |\n"
                 "|---|---|---|---|\n")
    for dv_name, dv_fn in dv_specs:
        hm, nhm = grp_means(dv_fn)
        grp_table += f"| `{dv_name}` | {hm:.4f} | {nhm:.4f} | {hm-nhm:+.4f} |\n"

    summary = f"""# Wendy's 사람 코딩 레이블 기반 H1 단순 OLS 분석

생성일시: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}

---

## 1. 작업 목적

`data/derived/humor/human_labels/wendys_human_label_raw_linked.csv`에 저장된
사람이 직접 코딩한 유머 레이블(`human_humor_binary`)을 IV로 사용하여
Wendy's 게시글 수준 engagement와의 연관성을 탐색적으로 검토한다.

이 분석은 기존 rule-based `humor_score` 및 weak-supervised `p_humor_ml`과 달리,
**사람이 직접 판단한 이진 레이블**을 IV로 사용한다는 점에서 구별된다.

> **중요:** 이 표본은 Wendy's partial human review sample({n_valid}건)이며,
> 전체 978건 게시글에 대한 gold label이 아니다.

---

## 2. 표본 구성

| 항목 | 값 |
|------|-----|
| 전체 linked 행 수 | {n_total}건 |
| label 결측 제외 | {n_skip}건 |
| **분석 사용 행 수** | **{n_valid}건** |
| 유머(human_humor_binary = 1) | {n_humor}건 ({n_humor/n_valid*100:.1f}%) |
| 비유머(human_humor_binary = 0) | {n_nonhumor}건 ({n_nonhumor/n_valid*100:.1f}%) |

---

## 3. IV 정의

```
human_humor_binary
  = 1  유머 ('humor')
  = 0  비유머 ('non_humor' 또는 'none')
  제외  공란(label_missing_flag = true)
```

`human_humor_binary`는 연속형 확률값이 아닌 이진 더미 변수이다.
따라서 β는 유머 게시글과 비유머 게시글 간의 log1p engagement 차이를 나타낸다.

---

## 4. 회귀식

```
log1p_DV_i = α + β × human_humor_binary_i + ε_i
```

각 항의 의미:
- `i` : 개별 Wendy's 게시글
- `log1p_DV_i` : engagement 지표의 log(1+x) 변환값
- `human_humor_binary_i` : 사람이 코딩한 유머 더미 (1=유머, 0=비유머)
- `β` : 유머 게시글과 비유머 게시글 간의 log1p engagement 평균 차이
- `ε_i` : 오차항

모델 설정: 단순 이변량 OLS / 통제변수 없음 / 고정효과 없음 / 표준 SE (HC3 미사용)

---

## 5. 그룹별 평균 비교

{grp_table}

---

## 6. 단순 OLS 결과

{ols_table}

주요 결과 (`log1p_engagement_total`):

| 파라미터 | 값 |
|----------|-----|
| n_obs | {mr['n_obs']} |
| Intercept (α) | {mr['intercept']:.6f} |
| β (`human_humor_binary`) | {mr['beta']:.6f} |
| Standard Error | {mr['se']:.6f} |
| t-value | {mr['t']:.4f} |
| p-value | {mr['p']:.4f} |
| 95% CI | [{mr['ci_lo']:.6f}, {mr['ci_hi']:.6f}] |
| R² | {mr['r2']:.6f} |
| Adj. R² | {mr['adj_r2']:.6f} |
| **H1 해석** | **{h1_label(mr['beta'], mr['p'])}** |

---

## 7. H1 해석

`human_humor_binary`는 `log1p_engagement_total`과
**{'양의' if mr['beta'] > 0 else '음의'} 방향**을 보였다.
(β = {mr['beta']:.6f}, SE = {mr['se']:.6f}, p = {mr['p']:.4f}, R² = {mr['r2']:.6f})

**{h1_label(mr['beta'], mr['p'])}**

---

## 8. 한계

- 이 분석은 Wendy's partial human review sample({n_valid}건)에 국한된다.
  전체 978건에 대한 human label이 아니므로 결과를 일반화할 수 없다.
- 표본이 `review_priority`(false_negative_candidate, high_confidence_humor 등)
  기준으로 선발되었으므로 무작위 표본이 아니다. 선택 편의(selection bias)가 존재한다.
- 단순 OLS이므로 통제변수(게시 시점, 미디어 유형, 캠페인 등)를 포함하지 않는다.
- 본 분석은 관측적 연관성 분석이며 인과관계를 주장할 수 없다.
- `human_humor_binary`는 단일 코더의 판단이며 inter-rater reliability 미검증 상태이다.
"""
    with open(OUT_SUMMARY, "w", encoding="utf-8") as f:
        f.write(summary)


if __name__ == "__main__":
    main()
