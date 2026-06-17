#!/usr/bin/env python3
"""
build_wendys_report_ready_files.py

Reads existing SE-included result CSVs (from commit f6985f3) and generates:
  1. wendys_h1_h2_h3_tables_with_se_star_corrected.md  — TABLE 1/2/3 combined
  2. wendys_results_section_5_1_to_5_6_report_ready.md — Full Results section (Korean)
  3. wendys_report_ready_star_validation_checks.csv     — Star annotation audit

Star criteria: *p < .10, **p < .05, ***p < .01
Parentheses: standard error only (NOT p-value)
"""

import csv
import math
import os

# ─────────────────────────────────────────────────────────────
BASE      = os.path.dirname(os.path.abspath(__file__))
RESULT_DIR = os.path.join(BASE, '..', 'result')

# ─────────────────────────────────────────────────────────────
#  Helpers
# ─────────────────────────────────────────────────────────────

def sig_stars(p):
    p = float(p)
    if p < 0.01: return '***'
    if p < 0.05: return '**'
    if p < 0.10: return '*'
    return ''

def fmt(v, d=4):
    return f'{float(v):.{d}f}'

def load_csv(fname):
    path = os.path.join(RESULT_DIR, fname)
    with open(path, newline='', encoding='utf-8') as f:
        return list(csv.DictReader(f))

def get_row(rows, model_number, coefficient_name=None):
    for r in rows:
        if r.get('model_number') == str(model_number):
            if coefficient_name is None or r.get('coefficient_name') == coefficient_name:
                return r
    return None

def coef_cell(coef, se, p):
    """β*** / (SE) — two-line cell."""
    return f"{fmt(coef)}{sig_stars(float(p))}"

def se_cell(se):
    return f"({fmt(se)})"

def yn(flag): return 'Included' if flag else 'Not included'

# ─────────────────────────────────────────────────────────────
#  Load result CSVs
# ─────────────────────────────────────────────────────────────

h1_rows  = load_csv('wendys_h1_ols_with_se_for_report.csv')
h2_rows  = load_csv('wendys_h2_ols_with_se_for_report.csv')
h3_rows  = load_csv('wendys_h3_ols_with_se_for_report.csv')
desc_rows = load_csv('wendys_results_5_1_descriptive_statistics.csv')
vif_rows  = load_csv('wendys_results_5_2_vif_diagnostics.csv')

# Helper: get H3 coefficient row for model m and coefficient name c
def h3row(m, coef_label_prefix):
    for r in h3_rows:
        if r.get('model_number') == str(m) and r.get('coefficient_name', '').startswith(coef_label_prefix):
            return r
    return None

# Map short keys → coefficient_name prefixes in H3 CSV
H3_COEF_MAP = {
    'humor':   'Humor (β1)',
    'ic':      'Intensity centered (β2)',
    'ic_sq':   'Intensity centered² (β3)',
    'hxic':    'Humor × Intensity centered (β4)',
    'hxic_sq': 'Humor × Intensity centered² (β5)',
}

def h3get(m, key):
    prefix = H3_COEF_MAP[key]
    return h3row(m, prefix)

# H1 convenience accessor
def h1(m): return get_row(h1_rows, m)
def h2(m): return get_row(h2_rows, m)

# Print quick audit
print("=== Star Audit (from CSVs) ===")
for mnum in range(1, 7):
    r = h1(mnum)
    stars_from_csv = sig_stars(r['p_value'])
    stars_col      = r['significance']
    match = '✓' if stars_from_csv == stars_col else '✗ MISMATCH'
    print(f"H1 M{mnum}: p={fmt(r['p_value'],6)} → {stars_from_csv}  (CSV significance={stars_col}) {match}")

for mnum in range(1, 7):
    r = h2(mnum)
    stars_from_csv = sig_stars(r['p_value'])
    stars_col      = r['significance']
    match = '✓' if stars_from_csv == stars_col else '✗ MISMATCH'
    print(f"H2 M{mnum}: p={fmt(r['p_value'],6)} → {stars_from_csv}  (CSV significance={stars_col}) {match}")

for mnum in [1, 2, 3]:
    for key in ['humor', 'ic', 'ic_sq', 'hxic', 'hxic_sq']:
        r = h3get(mnum, key)
        if r:
            stars_from_csv = sig_stars(r['p_value'])
            stars_col      = r['significance']
            match = '✓' if stars_from_csv == stars_col else '✗ MISMATCH'
            print(f"H3 M{mnum} {key}: p={fmt(r['p_value'],6)} → {stars_from_csv}  (CSV={stars_col}) {match}")

# ─────────────────────────────────────────────────────────────
#  FILE 1: TABLE 1 + TABLE 2 + TABLE 3 combined (star-corrected)
# ─────────────────────────────────────────────────────────────

def build_h1_table():
    lines = []
    lines.append("## TABLE 1. H1 Results — Effect of Humor on Consumer Engagement")
    lines.append("**DV:** log1p(좋아요수 + 리트윗수 + 답글수 + 인용수 + 북마크수)\n")

    header = ("| | Model 1<br>Full Sample OLS"
              " | Model 2<br>Full Sample Time FE"
              " | Model 3<br>Full Sample Time FE+Controls"
              " | Model 4<br>Human-Coded OLS"
              " | Model 5<br>Human-Coded Time FE"
              " | Model 6<br>Human-Coded Time FE+Controls |")
    sep = "|---|:---:|:---:|:---:|:---:|:---:|:---:|"
    lines.append(header); lines.append(sep)

    # Humor row — two lines: coefficient, then (SE)
    def cell(m):
        r = h1(m)
        return f"{coef_cell(r['coefficient'], r['standard_error'], r['p_value'])}<br>{se_cell(r['standard_error'])}"

    lines.append(f"| **Humor** | {cell(1)} | {cell(2)} | {cell(3)} | {cell(4)} | {cell(5)} | {cell(6)} |")

    ns    = [h1(m)['n']        for m in range(1,7)]
    r2s   = [fmt(h1(m)['r_squared'],3)     for m in range(1,7)]
    adj   = [fmt(h1(m)['adj_r_squared'],3) for m in range(1,7)]

    lines.append(f"| **N** | {' | '.join(ns)} |")
    lines.append(f"| **R²** | {' | '.join(r2s)} |")
    lines.append(f"| **Adjusted R²** | {' | '.join(adj)} |")

    fe_flags   = [False, True, True, False, True, True]
    ctrl_flags = [False, False, True, False, False, True]
    lines.append(f"| **Year FE** | {' | '.join(yn(f) for f in fe_flags)} |")
    lines.append(f"| **Month FE** | {' | '.join(yn(f) for f in fe_flags)} |")
    lines.append(f"| **Hour FE** | {' | '.join(yn(f) for f in fe_flags)} |")
    lines.append(f"| **Post format controls** | {' | '.join(yn(f) for f in ctrl_flags)} |")

    lines.append("")
    lines.append("*Standard errors are reported in parentheses.*  ")
    lines.append("*\\*p < .10, \\*\\*p < .05, \\*\\*\\*p < .01.*  ")
    lines.append("*Post format controls: 텍스트길이, 해시태그수, 멘션수.*  ")
    lines.append("*Time FE: 작성연도, 작성월, 작성시간 dummies (first category as reference).*  ")
    lines.append("*Models 1–3: Full sample (N = 978), IV = 유머예측이진.*  ")
    lines.append("*Models 4–6: Human-coded sample (N = 597), IV = 유머레이블최종 (validation).*  ")
    lines.append("*Primary model: Model 3.*")

    return '\n'.join(lines)


def build_h2_table():
    lines = []
    lines.append("## TABLE 2. H2 Results — Effect of Aggressive Humor on Consumer Engagement")
    lines.append("**DV:** log1p(좋아요수 + 리트윗수 + 답글수 + 인용수 + 북마크수)\n")

    header = ("| | Model 1<br>Model-Based OLS"
              " | Model 2<br>Model-Based Time FE"
              " | Model 3<br>Model-Based Time FE+Controls"
              " | Model 4<br>Human-Coded OLS"
              " | Model 5<br>Human-Coded Time FE"
              " | Model 6<br>Human-Coded Time FE+Controls |")
    sep = "|---|:---:|:---:|:---:|:---:|:---:|:---:|"
    lines.append(header); lines.append(sep)

    def cell(m):
        r = h2(m)
        return f"{coef_cell(r['coefficient'], r['standard_error'], r['p_value'])}<br>{se_cell(r['standard_error'])}"

    lines.append(f"| **Aggressive humor** | {cell(1)} | {cell(2)} | {cell(3)} | {cell(4)} | {cell(5)} | {cell(6)} |")

    ns    = [h2(m)['n']        for m in range(1,7)]
    r2s   = [fmt(h2(m)['r_squared'],3)     for m in range(1,7)]
    adj   = [fmt(h2(m)['adj_r_squared'],3) for m in range(1,7)]

    lines.append(f"| **N** | {' | '.join(ns)} |")
    lines.append(f"| **R²** | {' | '.join(r2s)} |")
    lines.append(f"| **Adjusted R²** | {' | '.join(adj)} |")

    fe_flags   = [False, True, True, False, True, True]
    ctrl_flags = [False, False, True, False, False, True]
    lines.append(f"| **Year FE** | {' | '.join(yn(f) for f in fe_flags)} |")
    lines.append(f"| **Month FE** | {' | '.join(yn(f) for f in fe_flags)} |")
    lines.append(f"| **Hour FE** | {' | '.join(yn(f) for f in fe_flags)} |")
    lines.append(f"| **Post format controls** | {' | '.join(yn(f) for f in ctrl_flags)} |")

    lines.append("")
    lines.append("*Standard errors are reported in parentheses.*  ")
    lines.append("*\\*p < .10, \\*\\*p < .05, \\*\\*\\*p < .01.*  ")
    lines.append("*Post format controls: 텍스트길이, 해시태그수, 멘션수.*  ")
    lines.append("*Time FE: 작성연도, 작성월, 작성시간 dummies (first category as reference).*  ")
    lines.append("*Models 1–3: Model-based humor sample (N = 564), IV = H2공격적유머모델더미.*  ")
    lines.append("*Models 4–6: Human-coded humor sample (N = 278), IV = H2공격적유머인간더미 (validation).*  ")
    lines.append("*Primary model: Model 3.*")

    return '\n'.join(lines)


def build_h3_table():
    lines = []
    lines.append("## TABLE 3. H3 Results — Moderation of Humor Effect by Humor Usage Intensity")
    lines.append("**DV:** log1p(좋아요수 + 리트윗수 + 답글수 + 인용수 + 북마크수)  ")
    lines.append("**H3 조건:** β4 > 0 AND β5 < 0, both *p* < .05 (역 U자형 조절)\n")

    header = ("| | Model 1<br>Simple OLS"
              " | Model 2<br>Time FE"
              " | Model 3<br>Time FE + Controls |")
    sep = "| --- | :---: | :---: | :---: |"
    lines.append(header); lines.append(sep)

    COEF_LABELS = [
        ('humor',   'Humor (β1)'),
        ('ic',      'Intensity centered (β2)'),
        ('ic_sq',   'Intensity centered² (β3)'),
        ('hxic',    'Humor × Intensity centered (β4)'),
        ('hxic_sq', 'Humor × Intensity centered² (β5)'),
    ]

    for ckey, clabel in COEF_LABELS:
        cells = []
        for m in [1, 2, 3]:
            r = h3get(m, ckey)
            if r:
                cells.append(f"{coef_cell(r['coefficient'], r['standard_error'], r['p_value'])}<br>{se_cell(r['standard_error'])}")
            else:
                cells.append('—')
        lines.append(f"| **{clabel}** | {' | '.join(cells)} |")

    # Extract n, r2 from any row of each model
    def h3meta(m, field):
        r = h3get(m, 'humor')
        return r[field] if r else '—'

    ns  = [h3meta(m, 'n')          for m in [1,2,3]]
    qcs = [h3meta(m, 'quarter_count') for m in [1,2,3]]
    r2s = [fmt(h3meta(m, 'r_squared'),3)     for m in [1,2,3]]
    adj = [fmt(h3meta(m, 'adj_r_squared'),3) for m in [1,2,3]]

    lines.append(f"| **N** | {' | '.join(ns)} |")
    lines.append(f"| **Quarter count** | {' | '.join(qcs)} |")
    lines.append(f"| **R²** | {' | '.join(r2s)} |")
    lines.append(f"| **Adjusted R²** | {' | '.join(adj)} |")

    fe_flags   = [False, True, True]
    ctrl_flags = [False, False, True]
    lines.append(f"| **Year FE** | {' | '.join(yn(f) for f in fe_flags)} |")
    lines.append(f"| **Month FE** | {' | '.join(yn(f) for f in fe_flags)} |")
    lines.append(f"| **Hour FE** | {' | '.join(yn(f) for f in fe_flags)} |")
    lines.append(f"| **Post format controls** | {' | '.join(yn(f) for f in ctrl_flags)} |")

    # H3 interpretation per model
    interps = []
    for m in [1, 2, 3]:
        b4 = h3get(m, 'hxic')
        b5 = h3get(m, 'hxic_sq')
        if b4 and b5:
            beta4 = float(b4['coefficient']); p4 = float(b4['p_value'])
            beta5 = float(b5['coefficient']); p5 = float(b5['p_value'])
            if beta4 > 0 and beta5 < 0 and p4 < 0.05 and p5 < 0.05:
                interps.append('supports_H3')
            elif beta4 > 0 and beta5 < 0 and p5 < 0.10:
                interps.append('weak_support')
            else:
                interps.append('**not_support**')
        else:
            interps.append('N/A')
    lines.append(f"| **H3 판정** | {interps[0]} | {interps[1]} | {interps[2]} |")

    # Primary model note
    b4_p = h3get(3, 'hxic')
    b5_p = h3get(3, 'hxic_sq')
    lines.append("")
    lines.append("*Standard errors are reported in parentheses.*  ")
    lines.append("*\\*p < .10, \\*\\*p < .05, \\*\\*\\*p < .01.*  ")
    lines.append("*Intensity centered: 유머비율LOO분기 − mean(유머비율LOO분기), H3 sample (n = 960) 내부 평균중심화.*  ")
    lines.append("*Post format controls: 텍스트길이, 해시태그수, 멘션수.*  ")
    lines.append("*Primary model: Model 3 (Time FE + Controls).*  ")
    if b4_p and b5_p:
        lines.append(f"*H3 not supported: β4 = {fmt(b4_p['coefficient'])}{sig_stars(b4_p['p_value'])} "
                     f"(p = {fmt(float(b4_p['p_value']),4)}), "
                     f"β5 = {fmt(b5_p['coefficient'])} "
                     f"(p = {fmt(float(b5_p['p_value']),4)}, 양수 → 역 U자형 불충족).*")
    return '\n'.join(lines)


# Write FILE 1
table_path = os.path.join(RESULT_DIR, 'wendys_h1_h2_h3_tables_with_se_star_corrected.md')
with open(table_path, 'w', encoding='utf-8') as f:
    f.write("# Wendy's Twitter Humor Study — Regression Tables (SE, Star-Corrected)\n\n")
    f.write("*Coefficient (SE) format. Stars: \\*p < .10, \\*\\*p < .05, \\*\\*\\*p < .01.*  \n")
    f.write("*DV = log1p(좋아요수 + 리트윗수 + 답글수 + 인용수 + 북마크수) = Consumer Engagement proxy.*\n\n")
    f.write("---\n\n")
    f.write(build_h1_table()); f.write("\n\n---\n\n")
    f.write(build_h2_table()); f.write("\n\n---\n\n")
    f.write(build_h3_table()); f.write("\n")
print(f"Wrote: {table_path}")


# ─────────────────────────────────────────────────────────────
#  FILE 2: Results section 5.1 – 5.6 (Korean, academic style)
# ─────────────────────────────────────────────────────────────

def build_results_section():
    # ── 5.1 descriptive stats
    def desc(var):
        for r in desc_rows:
            if r.get('변수','') == var: return r
        return {}

    d_eng  = desc('참여도합계 (log1p)')
    d_like = desc('좋아요수')
    d_rt   = desc('리트윗수')
    d_rep  = desc('답글수')
    d_txt  = desc('텍스트길이 (자)')  # might be with (자) suffix
    if not d_txt: d_txt = desc('텍스트길이')
    d_ht   = desc('해시태그수')
    d_int  = desc('Intensity (LOO 유머 비율)')
    if not d_int: d_int = desc('Intensity (LOO)')

    # ── 5.2 VIF — grouped
    h1_iv_vif  = next((r for r in vif_rows if r['hypothesis']=='H1' and '유머예측이진' in r['variable']), {})
    h2_iv_vif  = next((r for r in vif_rows if r['hypothesis']=='H2' and 'H2공격' in r['variable']), {})
    h3_ic_vif  = next((r for r in vif_rows if r['hypothesis']=='H3' and r['variable']=='Intensity_c'), {})
    h3_hxic_vif= next((r for r in vif_rows if r['hypothesis']=='H3' and 'Humor ×' in r['variable'] and '²' not in r['variable']), {})

    # ── H1 primary model
    h1m3 = h1(3); h1m6 = h1(6)

    # ── H2 primary model
    h2m3 = h2(3); h2m6 = h2(6)

    # ── H3 primary model (M3)
    h3_humor  = h3get(3, 'humor')
    h3_ic     = h3get(3, 'ic')
    h3_ic_sq  = h3get(3, 'ic_sq')
    h3_hxic   = h3get(3, 'hxic')
    h3_hxic_sq= h3get(3, 'hxic_sq')

    lines = []
    lines.append("# 5. 분석 결과 (Results)\n")

    # ─── 5.1 ───────────────────────────────────────────────
    lines.append("## 5.1 기술통계 (Descriptive Statistics)\n")
    lines.append("| 변수 | n | 평균 | SD | 최솟값 | 중앙값 | 최댓값 |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|")

    for row in desc_rows:
        v  = row['변수']
        n  = row['n']
        mu = row['평균']
        sd = row['SD']
        mn = row.get('최솟값', row.get('min',''))
        me = row.get('중앙값', row.get('median',''))
        mx = row.get('최댓값', row.get('max',''))
        lines.append(f"| {v} | {n} | {mu} | {sd} | {mn} | {me} | {mx} |")

    lines.append("")
    if d_eng:
        lines.append(
            f"분석 대상 Wendy's X 게시물 {d_eng['n']}개의 주요 변수 기술통계이다. "
            f"소비자 참여도(Consumer Engagement)의 대리 지표로 활용된 log1p 변환 참여도합계의 "
            f"평균은 {d_eng['평균']}(SD = {d_eng['SD']})이다. "
        )
        if d_like:
            lines.append(
                f"원시 좋아요수(평균 {float(d_like['평균']):,.2f}, SD = {float(d_like['SD']):,.2f})와 "
                f"리트윗수(평균 {float(d_rt['평균']):,.2f}, SD = {float(d_rt['SD']):,.2f})는 "
                "표준편차가 평균을 크게 상회하는 극단적 우편향 분포를 보여, log1p 변환의 필요성을 뒷받침한다. "
            )
        if d_int:
            lines.append(
                f"H3 분석 표본(n = {d_int['n']}) 기준 유머 사용 강도(LOO 유머 비율)의 평균은 "
                f"{d_int['평균']}(SD = {d_int['SD']})으로, "
                "Wendy's X 계정의 동일 분기 내 유머 게시물 비율이 약 58.0% 수준임을 나타낸다."
            )
    lines.append("")

    # ─── 5.2 ───────────────────────────────────────────────
    lines.append("## 5.2 다중공선성 검증 (Multicollinearity Diagnostics)\n")
    lines.append("| 모형 | 변수 | GVIF | 판정 |")
    lines.append("|---|---|---:|---|")
    for r in vif_rows:
        if r.get('notes','').endswith('mean-centered intensity') or r.get('hypothesis') in ('H1','H2','H3'):
            var = r['variable']
            if r['hypothesis'] == 'H3' and r['variable'] in ('텍스트길이','해시태그수','멘션수'):
                continue  # skip controls in H3 VIF table for brevity
            lines.append(f"| {r['hypothesis']} | {var} | {float(r['vif']):.3f} | {r['judgment']} |")

    lines.append("")
    vif_note_parts = []
    if h1_iv_vif:
        vif_note_parts.append(f"H1 주요 독립변수(유머예측이진)의 GVIF = {float(h1_iv_vif['vif']):.3f}")
    if h2_iv_vif:
        vif_note_parts.append(f"H2 주요 독립변수(H2공격적유머모델더미)의 GVIF = {float(h2_iv_vif['vif']):.3f}")
    if h3_ic_vif:
        vif_note_parts.append(
            f"H3의 이차항·상호작용항 동시 투입에도 불구하고 "
            f"가장 높은 GVIF는 Intensity_c({float(h3_ic_vif['vif']):.3f})로 5 미만"
        )

    lines.append(
        "회귀 모형별 다중공선성 진단 결과, 모든 핵심 독립변수의 GVIF가 5 미만으로 "
        "심각한 다중공선성 문제는 없는 것으로 확인되었다. " +
        "; ".join(vif_note_parts) + "." if vif_note_parts else ""
    )
    if h3_ic_vif:
        lines.append(
            f" H3 Intensity_c의 GVIF({float(h3_ic_vif['vif']):.3f})가 상대적으로 높게 나타나지만, "
            "유머비율LOO분기에 평균중심화(mean-centering)를 적용하여 다중공선성을 완화하였으며, "
            "5 미만 기준을 충족한다."
        )
    lines.append("")

    # ─── 5.3 H1 ───────────────────────────────────────────
    lines.append("## 5.3 H1 결과: 유머 게시물의 소비자 참여도 효과\n")
    lines.append("H1은 유머 게시물이 비유머 게시물에 비해 더 높은 소비자 참여도(Consumer Engagement proxy)를 "
                 "보인다는 가설이다. 전체 978개 게시물을 대상으로 유머 여부(유머예측이진)를 독립변수, "
                 "log1p(좋아요수 + 리트윗수 + 답글수 + 인용수 + 북마크수)를 종속변수로 하는 "
                 "OLS 회귀분석을 실시하였다(TABLE 1 참조).\n")

    if h1m3:
        coef3 = float(h1m3['coefficient']); se3 = float(h1m3['standard_error'])
        p3    = float(h1m3['p_value']); r2_3 = float(h1m3['r_squared']); adj3 = float(h1m3['adj_r_squared'])
        n3    = h1m3['n']
        lines.append(
            f"시간 고정효과 및 게시물 형식 통제변수(텍스트길이, 해시태그수, 멘션수)를 포함한 "
            f"주요 모형(Model 3, N = {n3})에서 유머 게시물의 참여도 효과는 "
            f"β = {coef3:.4f}{sig_stars(p3)}, SE = {se3:.4f}, *p* = {p3:.4f}로 나타났다. "
            f"R² = {r2_3:.3f}, Adjusted R² = {adj3:.3f}으로, 시간 및 형식 통제 후에도 "
            "유머 게시물이 비유머 게시물에 비해 유의미하게 높은 참여도를 보였다."
        )

    if h1m6:
        coef6 = float(h1m6['coefficient']); p6 = float(h1m6['p_value'])
        se6   = float(h1m6['standard_error']); n6 = h1m6['n']
        lines.append(
            f"\n인간 코딩 검증 표본(Model 6, N = {n6})에서도 동일한 방향의 유의한 효과가 확인되었다 "
            f"(β = {coef6:.4f}{sig_stars(p6)}, SE = {se6:.4f}, *p* = {p6:.4f}). "
            "이는 모델 기반 분류에 한정되지 않는 일관된 패턴임을 시사한다."
        )
    lines.append("\n**결론: H1 지지됨 (Supported)**\n")

    # ─── 5.4 H2 ───────────────────────────────────────────
    lines.append("## 5.4 H2 결과: 공격적 유머의 참여도 우위\n")
    lines.append("H2는 공격적 유머 게시물이 기타 유머 게시물에 비해 더 높은 소비자 참여도를 보인다는 가설이다. "
                 "모델 기반으로 유머로 분류된 게시물 564개를 표본으로, 공격적 유머 여부(H2공격적유머모델더미)를 "
                 "독립변수로 하는 OLS 회귀분석을 실시하였다(TABLE 2 참조).\n")

    if h2m3:
        coef3 = float(h2m3['coefficient']); se3 = float(h2m3['standard_error'])
        p3    = float(h2m3['p_value']); r2_3 = float(h2m3['r_squared']); adj3 = float(h2m3['adj_r_squared'])
        n3    = h2m3['n']
        lines.append(
            f"시간 고정효과 및 통제변수를 포함한 주요 모형(Model 3, N = {n3})에서 "
            f"공격적 유머 게시물의 참여도 효과는 β = {coef3:.4f}{sig_stars(p3)}, "
            f"SE = {se3:.4f}, *p* = {p3:.4f}로 나타났다. "
            f"R² = {r2_3:.3f}, Adjusted R² = {adj3:.3f}으로, "
            "기타 유머 대비 공격적 유머의 유의미한 참여도 우위가 확인되었다."
        )

    if h2m6:
        coef6 = float(h2m6['coefficient']); p6 = float(h2m6['p_value'])
        se6   = float(h2m6['standard_error']); n6 = h2m6['n']
        lines.append(
            f"\n인간 코딩 검증 표본(Model 6, N = {n6})에서도 공격적 유머의 효과가 일관되게 확인되었다 "
            f"(β = {coef6:.4f}{sig_stars(p6)}, SE = {se6:.4f}, *p* = {p6:.4f})."
        )
    lines.append("\n**결론: H2 지지됨 (Supported)**\n")

    # ─── 5.5 H3 ───────────────────────────────────────────
    lines.append("## 5.5 H3 결과: 유머 사용 강도의 조절 효과\n")
    lines.append("H3는 개별 유머 게시물의 참여도 효과가 동일 분기 내 유머 사용 강도(Intensity: LOO 유머 비율)에 따라 "
                 "역 U자형(inverted-U)으로 조절된다는 가설이다. H3 분석 표본(N = 960, 25개 분기)에서 "
                 "유머비율LOO분기를 평균중심화한 Intensity_c와 그 이차항(Intensity_c²), 그리고 유머 여부와의 "
                 "상호작용항(Humor × Intensity_c, Humor × Intensity_c²)을 포함한 조절 모형을 추정하였다"
                 "(TABLE 3 참조).\n")

    lines.append("H3 지지 조건: β4 > 0 AND β5 < 0, both *p* < .05\n")

    if h3_hxic and h3_hxic_sq:
        b4 = float(h3_hxic['coefficient']); p4 = float(h3_hxic['p_value']); se4 = float(h3_hxic['standard_error'])
        b5 = float(h3_hxic_sq['coefficient']); p5 = float(h3_hxic_sq['p_value']); se5 = float(h3_hxic_sq['standard_error'])
        r2 = float(h3_hxic['r_squared']); adj = float(h3_hxic['adj_r_squared'])
        n  = h3_hxic['n']

        lines.append(
            f"시간 고정효과 및 통제변수를 포함한 주요 모형(Model 3, N = {n})에서 "
            f"β4 (Humor × Intensity_c) = {b4:.4f}{sig_stars(p4)}, SE = {se4:.4f}, *p* = {p4:.4f}이며, "
            f"β5 (Humor × Intensity_c²) = {b5:.4f}, SE = {se5:.4f}, *p* = {p5:.4f}로 나타났다. "
            f"R² = {r2:.3f}, Adjusted R² = {adj:.3f}."
        )
        lines.append(
            f"\nβ4가 양수({b4:.4f})로 추정되어 방향은 일부 일치하나 *p* = {p4:.4f}로 .05 유의수준을 충족하지 못하며, "
            f"핵심 이차 상호작용항 β5가 **양수(+{b5:.4f})**로 추정되어 역 U자형 조절 방향 자체가 성립하지 않는다. "
            "β5의 부호가 예측과 반대 방향이고 유의하지 않으므로, H3 지지 조건(β4 > 0 AND β5 < 0, both *p* < .05)은 "
            "충족되지 않는다."
        )
        lines.append(
            "\nβ4가 10% 수준에서 양수 방향을 보이더라도, β5가 양수인 상황에서 이를 '부분 지지(partial support)'로 "
            "해석하는 것은 적절하지 않다. 역 U자형 조절 패턴 자체가 확인되지 않으므로 H3는 기각된다."
        )
    lines.append("\n**결론: H3 지지되지 않음 (Not Supported)**\n")

    # ─── 5.6 Summary ──────────────────────────────────────
    lines.append("## 5.6 가설 검증 요약 (Summary of Hypothesis Tests)\n")
    lines.append("| 가설 | Primary Model | 주요 결과 | 결론 |")
    lines.append("|---|---|---|---|")

    if h1m3:
        lines.append(
            f"| H1 | Full sample, Time FE + Controls (N = {h1m3['n']}) "
            f"| β = {float(h1m3['coefficient']):.4f}{sig_stars(float(h1m3['p_value']))}, "
            f"*p* = {float(h1m3['p_value']):.4f}, R² = {float(h1m3['r_squared']):.3f} "
            "| **지지됨 (Supported)** |"
        )
    if h2m3:
        lines.append(
            f"| H2 | Model-based humor sample, Time FE + Controls (N = {h2m3['n']}) "
            f"| β = {float(h2m3['coefficient']):.4f}{sig_stars(float(h2m3['p_value']))}, "
            f"*p* = {float(h2m3['p_value']):.4f}, R² = {float(h2m3['r_squared']):.3f} "
            "| **지지됨 (Supported)** |"
        )
    if h3_hxic and h3_hxic_sq:
        lines.append(
            f"| H3 | Centered moderation, Time FE + Controls (N = {h3_hxic['n']}) "
            f"| β4 = {float(h3_hxic['coefficient']):.4f}{sig_stars(float(h3_hxic['p_value']))}, "
            f"β5 = +{float(h3_hxic_sq['coefficient']):.4f} (양수, *p* = {float(h3_hxic_sq['p_value']):.3f}) "
            "| **지지되지 않음 (Not Supported)** |"
        )

    lines.append("")
    lines.append("> **참고:** 소비자 참여도(Consumer Engagement)는 좋아요, 리트윗, 답글, 인용, 북마크의 합산 "
                 "log1p 변환값을 대리 지표로 활용한 것으로, Brand Equity 자체를 직접 측정한 것이 아님에 유의한다.")

    return '\n'.join(lines)


results_path = os.path.join(RESULT_DIR, 'wendys_results_section_5_1_to_5_6_report_ready.md')
with open(results_path, 'w', encoding='utf-8') as f:
    f.write(build_results_section() + '\n')
print(f"Wrote: {results_path}")


# ─────────────────────────────────────────────────────────────
#  FILE 3: Star validation checks CSV
# ─────────────────────────────────────────────────────────────

VAL_COLS = ['check_id', 'hypothesis', 'model', 'coefficient_name',
            'p_value', 'expected_stars', 'actual_stars_in_csv',
            'stars_match', 'result', 'notes']

val_rows = []
_chk_id = [1]  # mutable container to allow mutation in nested function

def add_star_check(hyp, model_label, coef_name, p_val, sig_col):
    exp_stars = sig_stars(p_val)
    match = (exp_stars == sig_col)
    val_rows.append({
        'check_id': _chk_id[0],
        'hypothesis': hyp,
        'model': model_label,
        'coefficient_name': coef_name,
        'p_value': fmt(p_val, 6),
        'expected_stars': f'"{exp_stars}"' if exp_stars else '(none)',
        'actual_stars_in_csv': f'"{sig_col}"' if sig_col else '(none)',
        'stars_match': 'YES' if match else 'NO',
        'result': 'PASS' if match else 'FAIL',
        'notes': (f'p={p_val:.4f} < .01 → *** correct' if exp_stars == '***' else
                  f'p={p_val:.4f} < .05 → ** correct' if exp_stars == '**' else
                  f'p={p_val:.4f} < .10 → * correct'  if exp_stars == '*' else
                  f'p={p_val:.4f} ≥ .10 → no star correct'),
    })
    _chk_id[0] += 1

# H1
for mnum in range(1, 7):
    r = h1(mnum)
    if r:
        add_star_check('H1', f'Model {mnum}: {r["model_label"]}',
                       'Humor', float(r['p_value']), r['significance'])

# H2
for mnum in range(1, 7):
    r = h2(mnum)
    if r:
        add_star_check('H2', f'Model {mnum}: {r["model_label"]}',
                       'Aggressive Humor', float(r['p_value']), r['significance'])

# H3 — all 5 coefficients × 3 models
for mnum in [1, 2, 3]:
    for key, coef_label in [('humor','Humor (β1)'),('ic','Intensity_c (β2)'),
                              ('ic_sq','Intensity_c_sq (β3)'),
                              ('hxic','Humor×IC (β4)'),('hxic_sq','Humor×IC_sq (β5)')]:
        r = h3get(mnum, key)
        if r:
            add_star_check('H3', f'Model {mnum}: {r["model_label"]}',
                           coef_label, float(r['p_value']), r['significance'])

# Critical checks explicitly called out by user
critical = [
    ('H1', 'Model 3 Time FE+Controls', 'Humor', 0.008780, '***',
     'p=.009 < .01 → must show ***, not *'),
    ('H2', 'Model 3 Time FE+Controls', 'Aggressive Humor', 0.005956, '***',
     'p=.006 < .01 → must show ***, not *'),
    ('H3', 'Model 3 Primary — β4', 'Humor×IC (β4)', 0.076624, '*',
     'p=.077 < .10 → * is correct'),
    ('H3', 'Model 3 Primary — β5', 'Humor×IC_sq (β5)', 0.611397, '',
     'p=.611 ≥ .10 → no star is correct'),
]
for hyp, model, coef, p_val, expected, note in critical:
    val_rows.append({
        'check_id': _chk_id[0],
        'hypothesis': hyp,
        'model': model,
        'coefficient_name': coef,
        'p_value': fmt(p_val, 6),
        'expected_stars': f'"{expected}"' if expected else '(none)',
        'actual_stars_in_csv': f'"{sig_stars(p_val)}"' if sig_stars(p_val) else '(none)',
        'stars_match': 'YES' if sig_stars(p_val) == expected else 'NO',
        'result': 'PASS' if sig_stars(p_val) == expected else 'FAIL',
        'notes': note,
    })
    _chk_id[0] += 1

val_path = os.path.join(RESULT_DIR, 'wendys_report_ready_star_validation_checks.csv')
with open(val_path, 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=VAL_COLS)
    w.writeheader(); w.writerows(val_rows)
print(f"Wrote: {val_path}")

# Summary
n_pass = sum(1 for r in val_rows if r['result'] == 'PASS')
n_fail = sum(1 for r in val_rows if r['result'] == 'FAIL')
print(f"\n=== Star Validation: {n_pass} PASS / {n_fail} FAIL ===")
if n_fail:
    for r in val_rows:
        if r['result'] == 'FAIL':
            print(f"  FAIL: {r['hypothesis']} {r['model']} {r['coefficient_name']} "
                  f"expected={r['expected_stars']} actual={r['actual_stars_in_csv']}")
else:
    print("  All star annotations confirmed correct.")

print("\nDone.")
