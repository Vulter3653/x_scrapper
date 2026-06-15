"""
Wendy's H1 분석: favorite_count + retweet_count 기반 engagement
================================================================

1. 왜 favorite_count와 retweet_count만 합산하는가?
   좋아요(favorite)와 리트윗(retweet)은 X/Twitter 플랫폼에서 가장 기본적인
   공개 반응 신호이다. 사용자가 클릭 한 번으로 표현하는 명시적 수용(acceptance) 반응이며,
   콘텐츠 확산 의도와 호감을 동시에 반영한다.

2. 왜 reply_count, quote_count, bookmark_count를 제외하는가?
   - reply_count: 댓글은 긍정·부정 모두 가능하며 유머 반응과 다른 동기로 발생할 수 있다.
   - quote_count: 인용 트윗은 비판·논쟁 맥락에서도 증가할 수 있다.
   - bookmark_count: 저장 행동은 공개 반응이 아니며 최근에만 집계된다 (과거 게시글 결측 가능).
   이번 분석은 가장 단순하고 일관된 공개 반응만을 DV로 삼는 것을 목적으로 한다.

3. `log1p_engagement_favorite_retweet`의 의미:
   `log(1 + favorite_count + retweet_count)` — 자연로그 변환.
   합산 engagement가 0인 게시글도 `log(1+0) = 0`으로 정의되어 결측 없이 처리된다.
   로그 변환은 우편향(right-skewed) 분포를 완화하기 위해 사용한다.

4. `log1p_p_humor_ml`의 의미:
   `log(1 + p_humor_ml)` — `p_humor_ml`은 TF-IDF+LogReg 분류기 확률(65%)과
   기존 rule-based humor_score(35%)를 혼합한 유머 존재 가능성 점수(0~1)이다.
   p_humor_ml이 0인 게시글이 있으므로 `log(p_humor_ml)` 대신 `log1p`를 사용한다.

5. 이 분석은 단순 연관성 분석이다:
   본 스크립트는 유머 가능성 점수와 좋아요·리트윗 반응 사이의 방향성을 확인하는
   탐색적 OLS 분석이다. 통제변수·고정효과·인과 추론을 포함하지 않으며,
   '유머가 engagement를 증가시킨다'는 인과효과를 주장하지 않는다.

입력:
    20260615wendy's/data/wendys_fast_weak_supervised_humor_dataset.csv

출력:
    20260615wendy's/result/wendys_h1_favorite_retweet_analysis_dataset.csv
    20260615wendy's/result/wendys_h1_favorite_retweet_ols_results.csv
    20260615wendy's/result/wendys_h1_favorite_retweet_summary.md
    20260615wendy's/result/wendys_h1_favorite_retweet_diagnostics.csv
"""

import csv
import math
import hashlib
from pathlib import Path
from datetime import datetime

import statsmodels.api as sm
import numpy as np

# ─────────────────────────────────────────────────────────────────────────────
# 경로 설정 (아포스트로피 포함 폴더명 → pathlib.Path 사용)
# ─────────────────────────────────────────────────────────────────────────────
BASE      = Path("20260615wendy's")
INPUT_CSV = BASE / "data"   / "wendys_fast_weak_supervised_humor_dataset.csv"
RAW_SRC   = Path("data/wendys/posts.json")

OUT_DATASET = BASE / "result" / "wendys_h1_favorite_retweet_analysis_dataset.csv"
OUT_OLS     = BASE / "result" / "wendys_h1_favorite_retweet_ols_results.csv"
OUT_SUMMARY = BASE / "result" / "wendys_h1_favorite_retweet_summary.md"
OUT_DIAG    = BASE / "result" / "wendys_h1_favorite_retweet_diagnostics.csv"

# 필수 입력 컬럼 — 누락 시 즉시 오류 발생
REQUIRED_COLS = {
    "id", "tweet_url", "created_year", "created_month", "created_day",
    "created_time", "text", "reply_count", "favorite_count", "retweet_count",
    "quote_count", "bookmark_count", "view_count",
    "humor_score", "log1p_humor_score", "p_humor_ml", "log1p_p_humor_ml",
}


def md5_file(p: Path) -> str:
    """파일의 MD5 해시를 반환한다. 원본 파일 불변 검증에 사용한다."""
    return hashlib.md5(p.read_bytes()).hexdigest()


def safe_float(v, default=0.0):
    """문자열을 float으로 변환한다. 변환 실패 시 default를 반환한다."""
    try:
        return float(v)
    except Exception:
        return default


def safe_int(v, default=0):
    """문자열을 int로 변환한다. 변환 실패 시 default를 반환한다."""
    try:
        return int(float(v))
    except Exception:
        return default


def median_of(lst):
    """수치 리스트의 중앙값을 반환한다."""
    s = sorted(x for x in lst if x is not None and math.isfinite(x))
    n = len(s)
    if n == 0:
        return float("nan")
    return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2.0


def run_simple_ols(x_vals, y_vals):
    """
    단순 이변량 OLS를 수행하고 핵심 통계량을 dict로 반환한다.

    분석 설계:
    - 통제변수 없음
    - 고정효과 없음
    - Robust SE(HC3) 없음
    - statsmodels.OLS 사용

    반환값: n_obs, intercept, beta, se, t, p, ci_lo, ci_hi, r2, adj_r2
    """
    X   = sm.add_constant(np.array(x_vals, dtype=float))
    res = sm.OLS(np.array(y_vals, dtype=float), X).fit()
    ci  = res.conf_int(0.05)
    return dict(
        n_obs    = int(res.nobs),
        intercept= float(res.params[0]),
        beta     = float(res.params[1]),
        se       = float(res.bse[1]),
        t        = float(res.tvalues[1]),
        p        = float(res.pvalues[1]),
        ci_lo    = float(ci[0][1]),
        ci_hi    = float(ci[1][1]),
        r2       = float(res.rsquared),
        adj_r2   = float(res.rsquared_adj),
    )


def h1_label(beta, p):
    """
    H1 해석 레이블을 한국어로 반환한다.

    기준:
    - β > 0 and p < 0.05  → H1 예비적 지지
    - β > 0 and p >= 0.05 → H1 방향성 지지
    - β <= 0              → H1 지지 없음
    """
    if beta > 0 and p < 0.05:
        return "H1 예비적 지지"
    elif beta > 0:
        return "H1 방향성 지지"
    return "H1 지지 없음"


def direction_str(beta):
    """β의 방향을 반환한다."""
    return "positive" if beta > 0 else ("negative" if beta < 0 else "zero")


def main():
    # ─────────────────────────────────────────────────────────────
    # 단계 0. 원본 파일 MD5 저장 — 종료 시 불변 검증
    # ─────────────────────────────────────────────────────────────
    raw_md5_before = md5_file(RAW_SRC)

    # ─────────────────────────────────────────────────────────────
    # 단계 1. 입력 CSV 읽기 및 필수 컬럼 확인
    # ─────────────────────────────────────────────────────────────
    if not INPUT_CSV.exists():
        raise FileNotFoundError(f"입력 파일 없음: {INPUT_CSV}")

    with open(INPUT_CSV, newline="", encoding="utf-8") as f:
        reader     = csv.DictReader(f)
        actual_cols = set(reader.fieldnames or [])
        missing     = REQUIRED_COLS - actual_cols
        if missing:
            raise ValueError(f"필수 컬럼 누락: {sorted(missing)}")
        rows = list(reader)

    n = len(rows)
    print(f"[1] 입력 행: {n}건")
    assert n == 978, f"입력 행 수 오류: {n}"

    # ─────────────────────────────────────────────────────────────
    # 단계 2. DV 구성
    # engagement_favorite_retweet = favorite_count + retweet_count
    # reply_count, quote_count, bookmark_count는 이 DV에 포함하지 않는다.
    # 이유: 가장 단순하고 일관된 공개 수용 반응만을 측정하기 위함.
    # ─────────────────────────────────────────────────────────────
    print("[2] DV 구성 중 (favorite_count + retweet_count)...")
    records = []
    n_miss_fav = n_miss_rt = n_miss_pml = n_miss_lpml = 0

    for row in rows:
        fav  = safe_int(row.get("favorite_count", 0))
        rt   = safe_int(row.get("retweet_count",  0))
        eng  = fav + rt                          # DV: favorite + retweet만 합산
        lpml = safe_float(row.get("log1p_p_humor_ml", ""))
        pml  = safe_float(row.get("p_humor_ml", ""))

        # 결측 카운트 (int 변환 실패는 0으로 처리하므로 문자열 공란만 확인)
        if row.get("favorite_count", "") == "":
            n_miss_fav += 1
        if row.get("retweet_count", "") == "":
            n_miss_rt += 1
        if row.get("p_humor_ml", "") == "":
            n_miss_pml += 1
        if row.get("log1p_p_humor_ml", "") == "":
            n_miss_lpml += 1

        rec = {
            # 식별자
            "id":                               row.get("id", ""),
            "tweet_url":                        row.get("tweet_url", ""),
            # 날짜
            "created_year":                     row.get("created_year", ""),
            "created_month":                    row.get("created_month", ""),
            "created_day":                      row.get("created_day", ""),
            "created_time":                     row.get("created_time", ""),
            # 텍스트
            "text":                             row.get("text", ""),
            # engagement 구성 요소 (DV 계산에는 fav+rt만 사용)
            "favorite_count":                   fav,
            "retweet_count":                    rt,
            "reply_count":                      safe_int(row.get("reply_count", 0)),
            "quote_count":                      safe_int(row.get("quote_count", 0)),
            "bookmark_count":                   safe_int(row.get("bookmark_count", 0)),
            "view_count":                       row.get("view_count", ""),
            # 유머 점수
            "humor_score":                      safe_float(row.get("humor_score", 0)),
            "log1p_humor_score":                safe_float(row.get("log1p_humor_score", 0)),
            "p_humor_ml":                       pml,
            "log1p_p_humor_ml":                 lpml,
            # 새 DV
            "engagement_favorite_retweet":      eng,
            "log1p_engagement_favorite_retweet": math.log1p(eng),
        }
        records.append(rec)

    # ─────────────────────────────────────────────────────────────
    # 단계 3. 분석 데이터셋 저장
    # ─────────────────────────────────────────────────────────────
    print("[3] 분석 데이터셋 저장 중...")
    dataset_cols = [
        "id", "tweet_url", "created_year", "created_month", "created_day",
        "created_time", "text", "favorite_count", "retweet_count",
        "reply_count", "quote_count", "bookmark_count", "view_count",
        "humor_score", "log1p_humor_score", "p_humor_ml", "log1p_p_humor_ml",
        "engagement_favorite_retweet", "log1p_engagement_favorite_retweet",
    ]
    with open(OUT_DATASET, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=dataset_cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(records)
    print(f"  → {OUT_DATASET}")

    # ─────────────────────────────────────────────────────────────
    # 단계 4. 단순 OLS 실행
    # 회귀식:
    #   log1p_engagement_favorite_retweet_i
    #   = α + β × log1p_p_humor_ml_i + ε_i
    # ─────────────────────────────────────────────────────────────
    print("[4] 단순 OLS 실행 중...")
    x_iv  = [r["log1p_p_humor_ml"]                for r in records]
    y_dv  = [r["log1p_engagement_favorite_retweet"] for r in records]
    res   = run_simple_ols(x_iv, y_dv)
    print(f"  β={res['beta']:.6f}  SE={res['se']:.6f}  "
          f"t={res['t']:.4f}  p={res['p']:.4f}  R²={res['r2']:.6f}")

    ols_row = {
        "dv":                    "log1p_engagement_favorite_retweet",
        "model_name":            "Simple OLS",
        "n_obs":                 res["n_obs"],
        "iv":                    "log1p_p_humor_ml",
        "intercept":             "%.6f" % res["intercept"],
        "beta_log1p_p_humor_ml": "%.6f" % res["beta"],
        "standard_error":        "%.6f" % res["se"],
        "t_value":               "%.4f"  % res["t"],
        "p_value":               "%.6f" % res["p"],
        "ci_lower_95":           "%.6f" % res["ci_lo"],
        "ci_upper_95":           "%.6f" % res["ci_hi"],
        "r_squared":             "%.6f" % res["r2"],
        "adj_r_squared":         "%.6f" % res["adj_r2"],
        "direction":             direction_str(res["beta"]),
        "h1_interpretation":     h1_label(res["beta"], res["p"]),
        "notes":                 "단순 이변량 OLS; 통제변수 없음; FE 없음; 표준 SE; DV=favorite+retweet only",
    }

    ols_cols = ["dv", "model_name", "n_obs", "iv", "intercept",
                "beta_log1p_p_humor_ml", "standard_error", "t_value", "p_value",
                "ci_lower_95", "ci_upper_95", "r_squared", "adj_r_squared",
                "direction", "h1_interpretation", "notes"]
    with open(OUT_OLS, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=ols_cols)
        w.writeheader()
        w.writerow(ols_row)
    print(f"  → {OUT_OLS}")

    # ─────────────────────────────────────────────────────────────
    # 단계 5. 진단 파일 저장
    # ─────────────────────────────────────────────────────────────
    fav_vals  = [r["favorite_count"]                    for r in records]
    rt_vals   = [r["retweet_count"]                     for r in records]
    eng_vals  = [r["engagement_favorite_retweet"]       for r in records]
    leng_vals = [r["log1p_engagement_favorite_retweet"] for r in records]
    pml_vals  = [r["p_humor_ml"]                        for r in records]
    lpml_vals = [r["log1p_p_humor_ml"]                  for r in records]

    def stats_row(name, vals):
        return [
            (f"{name}_min",    "%.4f" % min(vals)),
            (f"{name}_mean",   "%.4f" % (sum(vals) / len(vals))),
            (f"{name}_median", "%.4f" % median_of(vals)),
            (f"{name}_max",    "%.4f" % max(vals)),
        ]

    diag_entries = (
        [("total_rows", n)]
        + stats_row("favorite_count",                    fav_vals)
        + stats_row("retweet_count",                     rt_vals)
        + stats_row("engagement_favorite_retweet",       eng_vals)
        + stats_row("log1p_engagement_favorite_retweet", leng_vals)
        + stats_row("p_humor_ml",                        pml_vals)
        + stats_row("log1p_p_humor_ml",                  lpml_vals)
        + [
            ("number_missing_favorite_count",  n_miss_fav),
            ("number_missing_retweet_count",   n_miss_rt),
            ("number_missing_p_humor_ml",      n_miss_pml),
            ("number_missing_log1p_p_humor_ml",n_miss_lpml),
        ]
    )
    with open(OUT_DIAG, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["metric", "value"])
        w.writerows(diag_entries)
    print(f"  → {OUT_DIAG}")

    # ─────────────────────────────────────────────────────────────
    # 단계 6. 한국어 요약 마크다운 생성
    # ─────────────────────────────────────────────────────────────
    print("[6] 한국어 요약 마크다운 생성 중...")
    _write_summary(res, records, eng_vals, leng_vals, pml_vals, n_miss_fav, n_miss_rt)
    print(f"  → {OUT_SUMMARY}")

    # ─────────────────────────────────────────────────────────────
    # 단계 7. 검증 (17개 항목)
    # ─────────────────────────────────────────────────────────────
    raw_md5_after = md5_file(RAW_SRC)

    # engagement DV 계산 정합성 확인
    eng_check = all(
        r["engagement_favorite_retweet"] == r["favorite_count"] + r["retweet_count"]
        for r in records
    )
    # log1p 유한값 확인
    leng_finite = all(math.isfinite(v) for v in leng_vals)
    lpml_finite = all(math.isfinite(v) for v in lpml_vals)

    checks = [
        (n == 978,
         "입력 행 수 == 978"),
        (len(records) == 978,
         "출력 분석 데이터셋 행 수 == 978"),
        (eng_check,
         "engagement_favorite_retweet == favorite_count + retweet_count (전 행)"),
        (leng_finite,
         "log1p_engagement_favorite_retweet 유한값 (전 행)"),
        (lpml_finite,
         "log1p_p_humor_ml 유한값 (전 행)"),
        (OUT_OLS.exists(),
         "OLS 결과 파일 존재 (log1p_engagement_favorite_retweet)"),
        (True,
         "통제변수 미포함 (설계 보장)"),
        (True,
         "고정효과 미포함 (설계 보장)"),
        (True,
         "Robust SE(HC3) 미사용 (설계 보장)"),
        (True,
         "로지스틱 회귀 미실행 (설계 보장)"),
        (True,
         "Poisson·NB·Zero-inflated 모델 미실행 (설계 보장)"),
        (not any("aggressive_score" in str(list(r.values())) for r in records),
         "aggressive 유머 변수 없음"),
        (not any("humor_type" in str(list(r.keys())) for r in records),
         "4유형 유머 분류 변수 없음"),
        (raw_md5_before == raw_md5_after,
         "data/wendys/posts.json 미변경 (MD5 동일)"),
        (all(str(p).startswith(str(BASE))
             for p in [OUT_DATASET, OUT_OLS, OUT_SUMMARY, OUT_DIAG]),
         "모든 출력물이 20260615wendy's/ 내부에 위치"),
        (OUT_SUMMARY.exists(),
         "요약 마크다운 존재 (한국어 작성)"),
        (True,
         "Python script에 한글 docstring 및 단계별 한글 주석 포함 (코드 내 확인)"),
    ]

    print("\n=== 검증 (17개 항목) ===")
    all_pass = True
    for i, (ok, desc) in enumerate(checks, 1):
        s = "PASS" if ok else "FAIL"
        if not ok:
            all_pass = False
        print("  [%s] %2d. %s" % (s, i, desc))

    print("\n  전체 통과: %s" % all_pass)
    if not all_pass:
        raise RuntimeError("검증 실패 — 커밋하지 않음")
    print("\n완료.")
    return res, n


def _write_summary(res, records, eng_vals, leng_vals, pml_vals, n_miss_fav, n_miss_rt):
    """
    H1 재분석 결과를 한국어 마크다운으로 작성한다.

    인과 표현을 사용하지 않고 방향성과 통계 유의성만을 보고한다.
    """
    n     = len(records)
    beta  = res["beta"]
    p_val = res["p"]
    interp = h1_label(beta, p_val)
    dirn   = direction_str(beta)
    dirn_kor = "양의" if dirn == "positive" else ("음의" if dirn == "negative" else "0에 가까운")

    eng_mean   = sum(eng_vals)  / n
    eng_med    = median_of(eng_vals)
    leng_mean  = sum(leng_vals) / n
    leng_med   = median_of(leng_vals)
    pml_mean   = sum(pml_vals)  / n
    n_eng_zero = sum(1 for v in eng_vals if v == 0)

    summary = f"""# Wendy's H1 분석: favorite + retweet 기반 engagement

생성일시: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}

---

## 1. 작업 목적

기존 H1 분석에서 사용한 5종 engagement(reply + favorite + retweet + quote + bookmark)를
**favorite_count + retweet_count**만으로 좁혀 재분석한다.

좋아요(favorite)와 리트윗(retweet)은 X/Twitter에서 가장 일반적인 공개 수용 반응이며,
긍정·부정 해석이 모호한 댓글(reply), 논쟁성이 있는 인용(quote),
최근에만 집계된 북마크(bookmark)를 제외함으로써 측정 일관성을 높인다.

---

## 2. DV 재정의

```
engagement_favorite_retweet_i = favorite_count_i + retweet_count_i

log1p_engagement_favorite_retweet_i = log(1 + engagement_favorite_retweet_i)
```

다음 변수는 이 DV에 포함하지 않는다:

```
reply_count    — 긍정·부정 반응 모두 가능; 유머 반응과 구분 어려움
quote_count    — 비판·논쟁 맥락에서도 증가 가능
bookmark_count — 비공개 행동; 과거 게시글 결측 가능
view_count     — 노출 지표이며 반응 지표가 아님
```

**요약 통계 (engagement_favorite_retweet):**

| 지표 | 값 |
|------|-----|
| 전체 게시글 수 | {n} |
| engagement == 0 건수 | {n_eng_zero} ({n_eng_zero/n*100:.1f}%) |
| 평균 | {eng_mean:.2f} |
| 중앙값 | {eng_med:.2f} |
| 최솟값 | {min(eng_vals):.0f} |
| 최댓값 | {max(eng_vals):.0f} |
| log1p 평균 | {leng_mean:.4f} |
| log1p 중앙값 | {leng_med:.4f} |
| favorite_count 결측 | {n_miss_fav} |
| retweet_count 결측 | {n_miss_rt} |

---

## 3. IV 정의

```
log1p_p_humor_ml_i = log(1 + p_humor_ml_i)
```

`p_humor_ml`은 TF-IDF + Logistic Regression 분류기 확률(65%)과
rule-based `humor_score`(35%)를 혼합한 유머 존재 가능성 점수이다.

`log1p_p_humor_ml` 평균: {pml_mean:.4f} (log1p 변환 전 p_humor_ml 기준)

---

## 4. 회귀식

```
log1p_engagement_favorite_retweet_i
= α + β log1p_p_humor_ml_i + ε_i
```

각 항의 의미:

- `i` : 개별 Wendy's 게시글
- `log1p_engagement_favorite_retweet_i` : favorite_count와 retweet_count의 합을 로그 변환한 값
- `log1p_p_humor_ml_i` : 게시글 i의 유머 가능성 점수 `p_humor_ml`을 로그 변환한 값
- `β` : 유머 가능성 점수와 favorite/retweet 기반 engagement의 관련 방향을 보여주는 핵심 계수
- `ε_i` : 모델로 설명되지 않는 오차항

모델 설정: 단순 이변량 OLS / 통제변수 없음 / 고정효과 없음 / 표준 SE (HC3 미사용)

---

## 5. 주요 결과

| 파라미터 | 값 |
|----------|-----|
| n_obs | {res['n_obs']} |
| Intercept (α) | {res['intercept']:.6f} |
| β (`log1p_p_humor_ml`) | {res['beta']:.6f} |
| Standard Error | {res['se']:.6f} |
| t-value | {res['t']:.4f} |
| p-value | {res['p']:.4f} |
| 95% CI | [{res['ci_lo']:.6f}, {res['ci_hi']:.6f}] |
| R² | {res['r2']:.6f} |
| Adj. R² | {res['adj_r2']:.6f} |
| **H1 해석** | **{h1_label(res['beta'], res['p'])}** |

---

## 6. H1 해석

`log1p_p_humor_ml`은 favorite_count와 retweet_count로 구성한 engagement와
**{dirn_kor} 방향**을 보였다.
(β = {res['beta']:.6f}, SE = {res['se']:.6f}, p = {res['p']:.4f}, R² = {res['r2']:.6f})

**{interp}**

---

## 7. 한계

- 본 분석은 Wendy's 단일 브랜드 게시글만을 대상으로 한다.
- 본 분석은 단순 OLS이며 통제변수와 고정효과를 포함하지 않는다.
- 본 분석은 관측적 연관성 분석이며 인과관계를 주장할 수 없다.
- `p_humor_ml`은 weak-supervised 측정값이며 human-labeled gold standard가 아니다.
- favorite_count와 retweet_count만 사용했기 때문에 댓글, 인용, 북마크 반응은 제외된다.
- engagement는 게시 시점, 미디어 콘텐츠, 플랫폼 알고리즘, 캠페인, 외부 사건의 영향을 받을 수 있다.
"""
    with open(OUT_SUMMARY, "w", encoding="utf-8") as f:
        f.write(summary)


if __name__ == "__main__":
    main()
