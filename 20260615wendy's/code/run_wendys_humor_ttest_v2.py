"""
run_wendys_humor_ttest_v2.py

최신 wendys_humor_review_sheet.csv 기반 (human_coded=1, human_humor_binary∈{0,1} → 167건)
유머 vs 비유머 Welch's independent samples t-test (v2).

기존 t-test (68건 partial human sample) 대비 업데이트된 분석.

입력:
    20260615wendy's/result/wendys_humor_review_sheet.csv  (labels)
    20260615wendy's/data/wendys_fast_weak_supervised_humor_dataset.csv  (engagement)

출력:
    20260615wendy's/result/wendys_humor_ttest_v2_results.csv
    20260615wendy's/result/wendys_humor_ttest_v2_summary.md
"""

import csv
import math
import sys
from pathlib import Path
from datetime import datetime
from scipy import stats

BASE        = Path("20260615wendy's")
REVIEW_CSV  = BASE / "result" / "wendys_humor_review_sheet.csv"
FULL_CSV    = BASE / "data"   / "wendys_fast_weak_supervised_humor_dataset.csv"
OUT_RESULT  = BASE / "result" / "wendys_humor_ttest_v2_results.csv"
OUT_SUMMARY = BASE / "result" / "wendys_humor_ttest_v2_summary.md"


def safe_int(v, default=0):
    try: return int(float(v))
    except: return default


def desc(vals):
    n = len(vals)
    if n == 0:
        return dict(n=0, mean=float("nan"), std=float("nan"),
                    median=float("nan"), mn=float("nan"), mx=float("nan"))
    mu  = sum(vals) / n
    var = sum((x - mu)**2 for x in vals) / (n - 1) if n > 1 else 0.0
    s   = sorted(vals)
    med = s[n//2] if n % 2 else (s[n//2-1] + s[n//2]) / 2
    return dict(n=n, mean=mu, std=math.sqrt(var), median=med, mn=min(vals), mx=max(vals))


def cohen_d(g1, g2):
    n1, n2 = len(g1), len(g2)
    if n1 < 2 or n2 < 2: return float("nan")
    m1, m2 = sum(g1)/n1, sum(g2)/n2
    v1 = sum((x-m1)**2 for x in g1)/(n1-1)
    v2 = sum((x-m2)**2 for x in g2)/(n2-1)
    sp = math.sqrt(((n1-1)*v1 + (n2-1)*v2) / (n1+n2-2))
    return (m1 - m2) / sp if sp > 0 else float("nan")


def interp_d(d):
    ad = abs(d)
    if ad < 0.2:  return "negligible"
    if ad < 0.5:  return "small"
    if ad < 0.8:  return "medium"
    return "large"


def sig_label(p):
    if p < 0.001: return "***"
    if p < 0.01:  return "**"
    if p < 0.05:  return "*"
    if p < 0.10:  return "†"
    return "n.s."


def main():
    # ── 1. Review sheet에서 human label 추출
    with open(REVIEW_CSV, newline="", encoding="utf-8") as f:
        review_rows = list(csv.DictReader(f))

    labeled_ids = {}
    n_missing = 0
    for r in review_rows:
        if r.get("human_coded") != "1":
            continue
        hb = r.get("human_humor_binary", "").strip()
        if hb in ("0", "1"):
            labeled_ids[r["id"]] = int(hb)
        else:
            n_missing += 1

    n_humor    = sum(1 for v in labeled_ids.values() if v == 1)
    n_nonhumor = sum(1 for v in labeled_ids.values() if v == 0)
    n_labeled  = len(labeled_ids)
    print(f"human_coded=1 중 사용: {n_labeled}건  (유머={n_humor}, 비유머={n_nonhumor}, 결측제외={n_missing})")

    # ── 2. Engagement 데이터 로드
    with open(FULL_CSV, newline="", encoding="utf-8") as f:
        full_rows = {str(r["id"]): r for r in csv.DictReader(f)}

    # ── 3. 유머 / 비유머 그룹별 engagement 수집
    humor_eng    = {k: [] for k in ["total","fav_rt","fav","rt","rep","qt","bm"]}
    nonhumor_eng = {k: [] for k in ["total","fav_rt","fav","rt","rep","qt","bm"]}

    n_eng_missing = 0
    for tid, hb in labeled_ids.items():
        fr = full_rows.get(tid)
        if fr is None:
            n_eng_missing += 1
            continue
        fav = safe_int(fr.get("favorite_count", 0))
        rt  = safe_int(fr.get("retweet_count",  0))
        rep = safe_int(fr.get("reply_count",    0))
        qt  = safe_int(fr.get("quote_count",    0))
        bm  = safe_int(fr.get("bookmark_count", 0))
        target = humor_eng if hb == 1 else nonhumor_eng
        target["total"].append(fav+rt+rep+qt+bm)
        target["fav_rt"].append(fav+rt)
        target["fav"].append(fav)
        target["rt"].append(rt)
        target["rep"].append(rep)
        target["qt"].append(qt)
        target["bm"].append(bm)

    if n_eng_missing:
        print(f"  [경고] engagement 데이터 없는 tweet: {n_eng_missing}건")

    # ── 4. T-test 실행
    dv_map = [
        ("engagement_total",  "total"),
        ("engagement_fav_rt", "fav_rt"),
        ("favorite_count",    "fav"),
        ("retweet_count",     "rt"),
        ("reply_count",       "rep"),
        ("quote_count",       "qt"),
        ("bookmark_count",    "bm"),
    ]

    result_rows = []
    for dv_name, key in dv_map:
        for scale, fn in [("raw", lambda x: x), ("log1p", math.log1p)]:
            g1 = [fn(v) for v in humor_eng[key]]
            g2 = [fn(v) for v in nonhumor_eng[key]]
            t_stat, p_val = stats.ttest_ind(g1, g2, equal_var=False)
            d  = cohen_d(g1, g2)
            d1 = desc(g1)
            d2 = desc(g2)
            label = dv_name if scale == "raw" else f"log1p_{dv_name}"
            result_rows.append({
                "dv":                   label,
                "scale":                scale,
                "n_humor":              d1["n"],
                "n_nonhumor":           d2["n"],
                "mean_humor":           "%.4f" % d1["mean"],
                "mean_nonhumor":        "%.4f" % d2["mean"],
                "diff_mean":            "%.4f" % (d1["mean"] - d2["mean"]),
                "sd_humor":             "%.4f" % d1["std"],
                "sd_nonhumor":          "%.4f" % d2["std"],
                "median_humor":         "%.4f" % d1["median"],
                "median_nonhumor":      "%.4f" % d2["median"],
                "t_stat":               "%.4f" % t_stat,
                "p_value":              "%.6f" % p_val,
                "sig":                  sig_label(p_val),
                "cohens_d":             "%.4f" % d if not math.isnan(d) else "",
                "effect_size_interp":   interp_d(d),
            })
            print(f"  {label}: diff={d1['mean']-d2['mean']:+.2f}  "
                  f"t={t_stat:.3f}  p={p_val:.4f}{sig_label(p_val)}  d={d:.3f}")

    # ── 5. 결과 저장
    cols = ["dv","scale","n_humor","n_nonhumor","mean_humor","mean_nonhumor",
            "diff_mean","sd_humor","sd_nonhumor","median_humor","median_nonhumor",
            "t_stat","p_value","sig","cohens_d","effect_size_interp"]
    with open(OUT_RESULT, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader(); w.writerows(result_rows)
    print(f"\n→ {OUT_RESULT}")

    _write_summary(result_rows, n_humor, n_nonhumor, n_missing)
    print(f"→ {OUT_SUMMARY}")


def _write_summary(result_rows, n_h, n_nh, n_missing):
    by_dv = {r["dv"]: r for r in result_rows}

    dv_names = ["engagement_total","engagement_fav_rt","favorite_count",
                "retweet_count","reply_count","quote_count","bookmark_count"]

    def tbl(scale_key):
        labels = dv_names if scale_key == "raw" else [f"log1p_{d}" for d in dv_names]
        hdr = ("| 변수 | 유머 평균 | 비유머 평균 | 차이 | SD(유머) | SD(비유머) "
               "| t | p | 유의 | Cohen's d | 효과 크기 |\n"
               "|---|---|---|---|---|---|---|---|---|---|---|\n")
        body = ""
        for dl in labels:
            r = by_dv.get(dl, {})
            body += (f"| `{dl}` | {r.get('mean_humor','')} | {r.get('mean_nonhumor','')} "
                     f"| {r.get('diff_mean','')} | {r.get('sd_humor','')} "
                     f"| {r.get('sd_nonhumor','')} | {r.get('t_stat','')} "
                     f"| {r.get('p_value','')} | {r.get('sig','')} "
                     f"| {r.get('cohens_d','')} | {r.get('effect_size_interp','')} |\n")
        return hdr + body

    mr = by_dv.get("log1p_engagement_total", {})

    summary = f"""# Wendy's 유머 vs 비유머 독립표본 t-검정 결과 (v2 — 167건 기준)

생성일시: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}

> **이 결과는 최신 human-coded 168건(label 결측 1건 제외 → 167건) 기준 분석이다.**
> 구버전(68건 partial human sample) t-test 결과는 `wendys_humor_ttest_summary.md` 참조.

---

## 1. 분석 개요

| 항목 | 내용 |
|------|------|
| 검정 방법 | Welch's independent samples t-test (양측) |
| IV | `human_humor_binary` (1=유머, 0=비유머) |
| 유머 게시글 수 | {n_h}건 |
| 비유머 게시글 수 | {n_nh}건 |
| 총 사용 표본 | {n_h+n_nh}건 |
| label 결측 제외 | {n_missing}건 |
| 데이터 출처 | `wendys_humor_review_sheet.csv` (v2, 168건 통합 human label) |
| 등분산 가정 | 적용하지 않음 (Welch's t-test) |

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
| 유머 평균 | {mr.get('mean_humor','')} |
| 비유머 평균 | {mr.get('mean_nonhumor','')} |
| 평균 차이 (유머 − 비유머) | {mr.get('diff_mean','')} |
| SD (유머) | {mr.get('sd_humor','')} |
| SD (비유머) | {mr.get('sd_nonhumor','')} |
| t 통계량 | {mr.get('t_stat','')} |
| p-value | {mr.get('p_value','')} |
| 유의성 | {mr.get('sig','')} |
| Cohen's d | {mr.get('cohens_d','')} |
| 효과 크기 해석 | {mr.get('effect_size_interp','')} |

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

## 6. 구버전(68건) 대비 변경 사항

| 항목 | v1 (68건) | v2 (167건) |
|------|-----------|-----------|
| humor | 37건 | {n_h}건 |
| non_humor | 31건 | {n_nh}건 |
| 총 표본 | 68건 | {n_h+n_nh}건 |

---

## 7. 한계

- 단일 코더 기반 — inter-rater reliability 미검증
- 통제변수 없음 (게시 시점, 미디어 유형 등 교란변수 미통제)
- 관측적 연관성 분석이며 인과관계를 주장할 수 없음
"""
    with open(OUT_SUMMARY, "w", encoding="utf-8") as f:
        f.write(summary)


if __name__ == "__main__":
    main()
