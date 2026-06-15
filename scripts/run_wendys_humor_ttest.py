"""
scripts/run_wendys_humor_ttest.py

Wendy's Human-Coded Labels — 유머 vs 비유머 독립표본 t-검정
=============================================================

분석 목적:
    사람이 코딩한 유머(1) vs 비유머(0) 게시글 간에
    각 engagement 지표의 평균 차이가 통계적으로 유의한지 검정한다.

검정 방법:
    Welch's independent samples t-test (등분산 가정 불필요)
    양측 검정 (two-tailed)

분석 변수:
    원본 스케일: reply_count, favorite_count, retweet_count,
                 quote_count, bookmark_count, engagement_total, engagement_fav_rt
    로그 스케일: log1p 변환 후 동일 7개 DV

입력:
    data/derived/humor/human_labels/wendys_human_label_raw_linked.csv

출력:
    data/derived/humor/human_labels/wendys_humor_ttest_results.csv
    data/derived/humor/human_labels/wendys_humor_ttest_summary.md
"""

import csv
import math
import sys
from pathlib import Path
from datetime import datetime
from scipy import stats

INPUT_CSV  = Path("data/derived/humor/human_labels/wendys_human_label_raw_linked.csv")
OUT_RESULT = Path("data/derived/humor/human_labels/wendys_humor_ttest_results.csv")
OUT_SUMMARY= Path("data/derived/humor/human_labels/wendys_humor_ttest_summary.md")


def safe_int(v, default=0):
    try:
        return int(float(v))
    except Exception:
        return default


def desc(vals):
    """기술 통계량 반환: n, mean, std, median, min, max"""
    n  = len(vals)
    if n == 0:
        return dict(n=0, mean=float("nan"), std=float("nan"),
                    median=float("nan"), mn=float("nan"), mx=float("nan"))
    mu   = sum(vals) / n
    var  = sum((x - mu)**2 for x in vals) / (n - 1) if n > 1 else 0.0
    s    = sorted(vals)
    med  = s[n//2] if n % 2 else (s[n//2-1] + s[n//2]) / 2
    return dict(n=n, mean=mu, std=math.sqrt(var), median=med, mn=min(vals), mx=max(vals))


def cohen_d(g1, g2):
    """Cohen's d (pooled SD 기준)"""
    n1, n2 = len(g1), len(g2)
    if n1 < 2 or n2 < 2:
        return float("nan")
    m1 = sum(g1)/n1;  m2 = sum(g2)/n2
    v1 = sum((x-m1)**2 for x in g1)/(n1-1)
    v2 = sum((x-m2)**2 for x in g2)/(n2-1)
    sp = math.sqrt(((n1-1)*v1 + (n2-1)*v2) / (n1+n2-2))
    return (m1 - m2) / sp if sp > 0 else float("nan")


def interp_d(d):
    ad = abs(d)
    if ad < 0.2:  return "무시 가능 (negligible)"
    if ad < 0.5:  return "작음 (small)"
    if ad < 0.8:  return "중간 (medium)"
    return "큼 (large)"


def sig_label(p):
    if p < 0.001: return "***"
    if p < 0.01:  return "**"
    if p < 0.05:  return "*"
    if p < 0.10:  return "†"
    return "n.s."


def main():
    if not INPUT_CSV.exists():
        print(f"[FAIL] 입력 파일 없음: {INPUT_CSV}", file=sys.stderr)
        sys.exit(1)

    with open(INPUT_CSV, newline="", encoding="utf-8") as f:
        all_rows = list(csv.DictReader(f))

    valid = [r for r in all_rows
             if r.get("label_missing_flag") == "false"
             and r.get("human_humor_binary") in ("0", "1")]

    humor_rows    = [r for r in valid if r["human_humor_binary"] == "1"]
    nonhumor_rows = [r for r in valid if r["human_humor_binary"] == "0"]
    print(f"유머: {len(humor_rows)}건 / 비유머: {len(nonhumor_rows)}건")

    # DV 스펙 (이름, 원본값 함수, log1p 포함 여부)
    def build(r):
        fav = safe_int(r["favorite_count"])
        rt  = safe_int(r["retweet_count"])
        rep = safe_int(r["reply_count"])
        qt  = safe_int(r["quote_count"])
        bm  = safe_int(r["bookmark_count"])
        return fav, rt, rep, qt, bm

    def dv_raw(rows):
        out = {}
        for r in rows:
            fav, rt, rep, qt, bm = build(r)
            out.setdefault("engagement_total",  []).append(fav+rt+rep+qt+bm)
            out.setdefault("engagement_fav_rt", []).append(fav+rt)
            out.setdefault("favorite_count",    []).append(fav)
            out.setdefault("retweet_count",     []).append(rt)
            out.setdefault("reply_count",       []).append(rep)
            out.setdefault("quote_count",       []).append(qt)
            out.setdefault("bookmark_count",    []).append(bm)
        return out

    h_raw  = dv_raw(humor_rows)
    nh_raw = dv_raw(nonhumor_rows)

    dv_names = ["engagement_total", "engagement_fav_rt", "favorite_count",
                "retweet_count", "reply_count", "quote_count", "bookmark_count"]

    result_rows = []

    for dv in dv_names:
        for scale, fn in [("raw", lambda x: x), ("log1p", math.log1p)]:
            g1 = [fn(v) for v in h_raw[dv]]
            g2 = [fn(v) for v in nh_raw[dv]]
            t_stat, p_val = stats.ttest_ind(g1, g2, equal_var=False)
            d   = cohen_d(g1, g2)
            d1  = desc(g1)
            d2  = desc(g2)
            dv_label = dv if scale == "raw" else f"log1p_{dv}"
            diff_mean = d1["mean"] - d2["mean"]
            result_rows.append({
                "dv":               dv_label,
                "scale":            scale,
                "n_humor":          d1["n"],
                "n_nonhumor":       d2["n"],
                "mean_humor":       "%.4f" % d1["mean"],
                "mean_nonhumor":    "%.4f" % d2["mean"],
                "diff_mean":        "%.4f" % diff_mean,
                "sd_humor":         "%.4f" % d1["std"],
                "sd_nonhumor":      "%.4f" % d2["std"],
                "median_humor":     "%.4f" % d1["median"],
                "median_nonhumor":  "%.4f" % d2["median"],
                "t_stat":           "%.4f" % t_stat,
                "p_value":          "%.6f" % p_val,
                "sig":              sig_label(p_val),
                "cohens_d":         "%.4f" % d if not math.isnan(d) else "",
                "effect_size_interp": interp_d(d),
            })
            print(f"  {dv_label}: diff={diff_mean:+.1f}  t={t_stat:.3f}  "
                  f"p={p_val:.4f}{sig_label(p_val)}  d={d:.3f}")

    OUT_RESULT.parent.mkdir(parents=True, exist_ok=True)
    cols = ["dv","scale","n_humor","n_nonhumor","mean_humor","mean_nonhumor",
            "diff_mean","sd_humor","sd_nonhumor","median_humor","median_nonhumor",
            "t_stat","p_value","sig","cohens_d","effect_size_interp"]
    with open(OUT_RESULT, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader(); w.writerows(result_rows)
    print(f"→ {OUT_RESULT}")

    _write_summary(result_rows, len(humor_rows), len(nonhumor_rows),
                   h_raw, nh_raw, dv_names)
    print(f"→ {OUT_SUMMARY}")


def _write_summary(result_rows, n_h, n_nh, h_raw, nh_raw, dv_names):
    rows_by_dv = {r["dv"]: r for r in result_rows}

    def tbl(scale_key):
        dv_labels = dv_names if scale_key == "raw" else [f"log1p_{d}" for d in dv_names]
        hdr = ("| 변수 | 유머 평균 | 비유머 평균 | 차이 | SD(유머) | SD(비유머) "
               "| t | p | 유의 | Cohen's d | 효과 크기 |\n"
               "|---|---|---|---|---|---|---|---|---|---|---|\n")
        rows_str = ""
        for dl in dv_labels:
            r = rows_by_dv.get(dl, {})
            rows_str += (
                f"| `{dl}` | {r.get('mean_humor','')} | {r.get('mean_nonhumor','')} "
                f"| {r.get('diff_mean','')} | {r.get('sd_humor','')} "
                f"| {r.get('sd_nonhumor','')} | {r.get('t_stat','')} "
                f"| {r.get('p_value','')} | {r.get('sig','')} "
                f"| {r.get('cohens_d','')} | {r.get('effect_size_interp','')} |\n"
            )
        return hdr + rows_str

    # 주요 DV(log1p_engagement_total) 상세
    mr = rows_by_dv.get("log1p_engagement_total", {})

    summary = f"""# Wendy's 유머 vs 비유머 독립표본 t-검정 결과

생성일시: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}

---

## 1. 분석 개요

| 항목 | 내용 |
|------|------|
| 검정 방법 | Welch's independent samples t-test (양측) |
| IV | `human_humor_binary` (1=유머, 0=비유머) |
| 유머 게시글 수 | {n_h}건 |
| 비유머 게시글 수 | {n_nh}건 |
| 데이터 출처 | Wendy's partial human review sample |
| 등분산 가정 | 적용하지 않음 (Welch's t-test) |

> **주의:** 이 표본은 review_priority 기준 선발 표본이며 무작위 표본이 아니다.
> 결과를 전체 978건으로 일반화할 수 없다.

---

## 2. 원본 스케일 결과 (raw counts)

{tbl('raw')}

---

## 3. 로그 변환 스케일 결과 (log1p)

{tbl('log1p')}

---

## 4. 주요 결과 상세 (`log1p_engagement_total`)

| 파라미터 | 값 |
|----------|-----|
| 유머 평균 | {mr.get('mean_humor', '')} |
| 비유머 평균 | {mr.get('mean_nonhumor', '')} |
| 평균 차이 (유머 − 비유머) | {mr.get('diff_mean', '')} |
| SD (유머) | {mr.get('sd_humor', '')} |
| SD (비유머) | {mr.get('sd_nonhumor', '')} |
| t 통계량 | {mr.get('t_stat', '')} |
| p-value | {mr.get('p_value', '')} |
| 유의성 | {mr.get('sig', '')} |
| Cohen's d | {mr.get('cohens_d', '')} |
| 효과 크기 해석 | {mr.get('effect_size_interp', '')} |

---

## 5. 유의성 기호 설명

| 기호 | 기준 |
|------|------|
| *** | p < 0.001 |
| **  | p < 0.01  |
| *   | p < 0.05  |
| †   | p < 0.10  |
| n.s.| p ≥ 0.10  |

---

## 6. 해석

유머 게시글과 비유머 게시글 간의 engagement 차이를
Welch's t-검정으로 검정한 결과는 위 표와 같다.

Cohen's d는 두 집단 간 표준화 평균 차이를 나타내며,
0.2 미만=무시 가능, 0.2–0.5=작음, 0.5–0.8=중간, 0.8 이상=큼으로 해석한다.

---

## 7. 한계

- Wendy's partial human review sample({n_h + n_nh}건) 기반 결과이며 전체 978건 일반화 불가
- 표본이 `review_priority` 기준으로 선발되어 선택 편의(selection bias)가 존재함
- 단일 코더의 판단이며 inter-rater reliability 미검증
- 통제변수 없음 — 게시 시점, 미디어 유형, 팔로워 수 등 교란변수 미통제
- 관측적 연관성 분석이며 인과관계를 주장할 수 없음
"""
    with open(OUT_SUMMARY, "w", encoding="utf-8") as f:
        f.write(summary)


if __name__ == "__main__":
    main()
