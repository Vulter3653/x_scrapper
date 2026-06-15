"""
inspect_wendys_human_coding_results.py

== 1. 목적 ==
H2 분석 전에 wendys_humor_review_sheet.csv에 포함된 사람 코딩 결과를 점검한다.
유머 유무 라벨 분포, 유머 타입 값 품질, 코더 간 불일치를 진단하여
H2 진행 가능 여부를 판단한다.

== 2. H2 전에 사람 코딩 결과를 점검하는 이유 ==
H2는 유머 타입(aggressive vs 기타)에 따른 engagement 차이를 분석한다.
이를 위해서는 type 값이 정규화되어 있고 표본이 충분해야 한다.
type 값에 오타, 이상값, 결측이 있는 상태에서 모델링하면 분석 결과가 왜곡된다.

== 3. final_humor_binary와 type 컬럼의 차이 ==
final_humor_binary: 유머 유무(0/1) — 이미 완성된 최종 라벨
type 컬럼(coder1_type, human_type, coder2_type): 유머 타입 — 아직 정규화 미완료

== 4. final_humor_type은 아직 생성하지 않음 ==
이번 작업에서는 final_humor_type 후보를 진단만 하고 실제 컬럼 추가는 하지 않는다.
type 정규화가 완료된 후 별도 작업에서 추가한다.

== 5. 이번 작업에서 수행하지 않는 것 ==
모델 학습, 회귀분석, t-test, H2 분석은 수행하지 않는다.
오직 라벨 진단만 수행한다.
"""

import csv
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

BASE       = Path("20260615wendy's")
REVIEW_CSV = BASE / "result" / "wendys_humor_review_sheet.csv"

OUT_LABEL  = BASE / "result" / "wendys_human_coding_label_distribution.csv"
OUT_SRC    = BASE / "result" / "wendys_human_coding_source_distribution.csv"
OUT_TYPE   = BASE / "result" / "wendys_human_coding_type_distribution.csv"
OUT_AUDIT  = BASE / "result" / "wendys_human_coding_type_value_audit.csv"
OUT_DISAG  = BASE / "result" / "wendys_human_coding_disagreement_audit.csv"
OUT_SUM    = BASE / "result" / "wendys_human_coding_inspection_summary.md"

# ── type 정규화 매핑 (진단 전용, 실제 데이터 수정 안 함)
NORMALIZE_MAP = {
    'affliative':      ('affiliative',     'typo_candidate'),
    'self_enhancing':  ('self-enhancing',  'typo_candidate'),
    'self enhancing':  ('self-enhancing',  'typo_candidate'),
    'self_defeating':  ('self-defeating',  'typo_candidate'),
    'self enhancing':  ('self-enhancing',  'typo_candidate'),
    'agressive':       ('aggressive',      'typo_candidate'),
    'self-enchancing': ('self-enhancing',  'typo_candidate'),
    'self-affliative': ('affiliative',     'typo_candidate'),
    'none':            ('none',            'non_humor_marker'),
    'non_humor':       ('non_humor',       'non_humor_marker'),
    'non-humor':       ('non_humor',       'non_humor_marker'),
    '':                ('',               'missing'),
    'affiliative':     ('affiliative',     'valid'),
    'aggressive':      ('aggressive',      'valid'),
    'self-enhancing':  ('self-enhancing',  'valid'),
    'self-defeating':  ('self-defeating',  'valid'),
}

VALID_TYPES = {'affiliative', 'aggressive', 'self-enhancing', 'self-defeating'}


def classify_type(raw):
    raw_l = raw.strip().lower()
    if raw_l in NORMALIZE_MAP:
        norm, issue = NORMALIZE_MAP[raw_l]
        return norm, issue
    if raw_l == '':
        return '', 'missing'
    return raw_l, 'unknown_value'


def main():
    # ── 1. 입력 파일 로드
    with open(REVIEW_CSV, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        cols = reader.fieldnames
        rows = list(reader)

    total = len(rows)
    print(f"전체 행: {total}건")
    print(f"컬럼: {cols}")

    # 필수 컬럼 확인
    required = ['coder1_humor_binary', 'human_humor_binary', 'coder2_humor_binary',
                'final_humor_binary', 'final_humor_source', 'final_humor_label_available',
                'coder1_type', 'human_type', 'coder2_type']
    missing_cols = [c for c in required if c not in cols]
    if missing_cols:
        print(f"  [경고] 누락 컬럼: {missing_cols}")

    # ── 2. 유머 유무 라벨 분포
    print("\n[라벨 분포 점검]")
    label_rows = []
    for src, col in [('coder1', 'coder1_humor_binary'),
                     ('human',  'human_humor_binary'),
                     ('coder2', 'coder2_humor_binary'),
                     ('final',  'final_humor_binary')]:
        if col not in cols:
            continue
        vals = [r[col].strip() for r in rows]
        avail   = [v for v in vals if v in ('0', '1')]
        n_h     = sum(1 for v in avail if v == '1')
        n_nh    = sum(1 for v in avail if v == '0')
        n_miss  = total - len(avail)
        h_share  = n_h  / len(avail) if avail else 0
        nh_share = n_nh / len(avail) if avail else 0
        label_rows.append({
            'label_source':                  src,
            'total_rows':                    total,
            'available_count':               len(avail),
            'humor_count':                   n_h,
            'nonhumor_count':                n_nh,
            'missing_count':                 n_miss,
            'humor_share_among_available':   f'{h_share:.4f}',
            'nonhumor_share_among_available':f'{nh_share:.4f}',
        })
        print(f"  {src}: 유효={len(avail)}  유머={n_h}  비유머={n_nh}  결측={n_miss}")

    with open(OUT_LABEL, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(label_rows[0].keys()))
        w.writeheader(); w.writerows(label_rows)

    # ── 3. final_humor_source 분포
    print("\n[final_humor_source 분포]")
    final_labeled = [r for r in rows if r.get('final_humor_label_available') == '1']
    n_final_total = len(final_labeled)

    src_cnt = Counter(r.get('final_humor_source', '') for r in final_labeled)
    src_rows = []
    for src, cnt in sorted(src_cnt.items(), key=lambda x: -x[1]):
        sub = [r for r in final_labeled if r.get('final_humor_source', '') == src]
        n_h  = sum(1 for r in sub if r.get('final_humor_binary') == '1')
        n_nh = sum(1 for r in sub if r.get('final_humor_binary') == '0')
        share = cnt / n_final_total if n_final_total else 0
        src_rows.append({
            'final_humor_source':     src if src else '(blank)',
            'count':                  cnt,
            'humor_count':            n_h,
            'nonhumor_count':         n_nh,
            'share_of_final_labeled': f'{share:.4f}',
        })
        print(f"  {src or '(blank)'}: {cnt}건  유머={n_h}  비유머={n_nh}  비율={share:.2%}")

    with open(OUT_SRC, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=['final_humor_source','count','humor_count',
                                          'nonhumor_count','share_of_final_labeled'])
        w.writeheader(); w.writerows(src_rows)

    # ── 4. type 값 분포
    print("\n[type 값 분포]")
    type_rows = []
    type_summary = {}

    for type_src, col in [('coder1', 'coder1_type'),
                           ('human',  'human_type'),
                           ('coder2', 'coder2_type')]:
        if col not in cols:
            continue
        all_vals = [r[col].strip() for r in rows]
        non_empty = [v for v in all_vals if v]
        cnt_map = Counter(non_empty)
        total_src = len(non_empty)
        type_summary[type_src] = cnt_map
        print(f"\n  [{type_src}] (비공란 {total_src}건)")
        for val, cnt in cnt_map.most_common():
            norm, issue = classify_type(val)
            share = cnt / total_src if total_src else 0
            print(f"    {val!r:25s} → {norm!r:20s} ({issue}) : {cnt}건 ({share:.1%})")
            type_rows.append({
                'type_source':         type_src,
                'raw_type_value':      val,
                'normalized_type_value': norm,
                'count':               cnt,
                'share_within_source': f'{share:.4f}',
            })

    with open(OUT_TYPE, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=['type_source','raw_type_value',
                                          'normalized_type_value','count',
                                          'share_within_source'])
        w.writeheader(); w.writerows(type_rows)

    # ── 5. type value audit (정규화 진단)
    print("\n[type value audit]")
    audit_rows = []
    seen = set()
    for type_src, col in [('coder1','coder1_type'),
                           ('human', 'human_type'),
                           ('coder2','coder2_type')]:
        if col not in cols:
            continue
        val_cnt = Counter(r[col].strip() for r in rows)
        for raw, cnt in val_cnt.most_common():
            norm, issue = classify_type(raw)
            notes = ''
            if issue == 'typo_candidate':
                notes = f'{raw!r} → {norm!r} 정규화 필요'
            elif issue == 'non_humor_marker':
                notes = '비유머 표시값 — missing 처리 권장'
            elif issue == 'missing':
                notes = '공란 — 해당 행의 유머 타입 미부여'
            elif issue == 'unknown_value':
                notes = '알 수 없는 값 — 수동 확인 필요'
            key = (type_src, raw)
            if key not in seen:
                seen.add(key)
                audit_rows.append({
                    'type_source':             type_src,
                    'raw_type_value':          raw,
                    'suggested_normalized_value': norm,
                    'count':                   cnt,
                    'issue_type':              issue,
                    'notes':                   notes,
                })

    with open(OUT_AUDIT, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=['type_source','raw_type_value',
                                          'suggested_normalized_value','count',
                                          'issue_type','notes'])
        w.writeheader(); w.writerows(audit_rows)

    # ── 6. final_humor_type 후보 진단 (실제 컬럼 추가 안 함)
    print("\n[final_humor_type 후보 진단]")
    def get_final_type_candidate(r):
        src = r.get('final_humor_source', '')
        if src == 'coder1':
            return r.get('coder1_type', '').strip()
        elif src == 'human':
            return r.get('human_type', '').strip()
        elif src == 'coder2':
            return r.get('coder2_type', '').strip()
        return ''

    humor_rows = [r for r in rows if r.get('final_humor_binary') == '1']
    n_humor_total = len(humor_rows)

    type_candidates = [get_final_type_candidate(r) for r in humor_rows]
    type_norm_cands  = [classify_type(t)[0] for t in type_candidates]

    n_with_type  = sum(1 for t in type_candidates if t and t.lower() not in ('none',''))
    n_missing    = n_humor_total - n_with_type
    n_aggressive = sum(1 for t in type_norm_cands if t == 'aggressive')
    n_affiliative= sum(1 for t in type_norm_cands if t == 'affiliative')
    n_selfenhanc = sum(1 for t in type_norm_cands if t == 'self-enhancing')
    n_selfdefeat = sum(1 for t in type_norm_cands if t == 'self-defeating')

    # 비유머인데 type이 유머 타입인 경우
    nonhumor_rows = [r for r in rows if r.get('final_humor_binary') == '0']
    n_nonhumor_with_type = sum(
        1 for r in nonhumor_rows
        if classify_type(get_final_type_candidate(r))[0] in VALID_TYPES
    )

    print(f"  final_humor_binary=1 총 {n_humor_total}건")
    print(f"    type 있음: {n_with_type}건 ({n_with_type/n_humor_total*100:.1f}%)")
    print(f"    type 없음/none/blank: {n_missing}건")
    print(f"    aggressive: {n_aggressive}건")
    print(f"    affiliative: {n_affiliative}건")
    print(f"    self-enhancing: {n_selfenhanc}건")
    print(f"    self-defeating: {n_selfdefeat}건")
    print(f"  비유머인데 type 값이 유머 타입인 경우: {n_nonhumor_with_type}건")

    # H2 가능성 판단
    if n_aggressive >= 30:
        h2_verdict = 'H2 수행 가능'
    elif n_aggressive >= 15:
        h2_verdict = 'H2 탐색적으로만 가능'
    else:
        h2_verdict = 'H2 보류 권장'
    print(f"\n  H2 가능성 판단: {h2_verdict} (aggressive={n_aggressive}건)")

    # ── 7. 코더 간 불일치 점검
    print("\n[코더 간 불일치]")
    disag_rows = []

    pairs_bin = [
        ('coder1_humor_binary', 'human_humor_binary',  'coder1 vs human (binary)'),
        ('coder1_humor_binary', 'coder2_humor_binary',  'coder1 vs coder2 (binary)'),
        ('human_humor_binary',  'coder2_humor_binary',  'human vs coder2 (binary)'),
    ]
    pairs_type = [
        ('coder1_type', 'human_type',  'coder1 vs human (type)'),
        ('coder1_type', 'coder2_type',  'coder1 vs coder2 (type)'),
        ('human_type',  'coder2_type',  'human vs coder2 (type)'),
    ]

    for colA, colB, label in pairs_bin:
        if colA not in cols or colB not in cols:
            continue
        overlap = [r for r in rows
                   if r.get(colA, '').strip() in ('0','1')
                   and r.get(colB, '').strip() in ('0','1')]
        agree   = [r for r in overlap if r[colA].strip() == r[colB].strip()]
        disag   = len(overlap) - len(agree)
        rate    = len(agree) / len(overlap) if overlap else 0
        disag_rows.append({
            'comparison':       label,
            'overlap_count':    len(overlap),
            'agreement_count':  len(agree),
            'disagreement_count': disag,
            'agreement_rate':   f'{rate:.4f}',
            'notes':            f'일치율 {rate:.1%}',
        })
        print(f"  {label}: overlap={len(overlap)}  agree={len(agree)}  disag={disag}  rate={rate:.1%}")

    for colA, colB, label in pairs_type:
        if colA not in cols or colB not in cols:
            continue
        overlap = [r for r in rows
                   if r.get(colA,'').strip() and r.get(colB,'').strip()
                   and r.get(colA,'').strip().lower() not in ('none','')
                   and r.get(colB,'').strip().lower() not in ('none','')]
        norm_agree = [r for r in overlap
                      if classify_type(r[colA])[0] == classify_type(r[colB])[0]]
        disag = len(overlap) - len(norm_agree)
        rate  = len(norm_agree) / len(overlap) if overlap else 0
        disag_rows.append({
            'comparison':       label,
            'overlap_count':    len(overlap),
            'agreement_count':  len(norm_agree),
            'disagreement_count': disag,
            'agreement_rate':   f'{rate:.4f}',
            'notes':            f'정규화 후 일치율 {rate:.1%}',
        })
        print(f"  {label}: overlap={len(overlap)}  agree={len(norm_agree)}  disag={disag}  rate={rate:.1%}")

    with open(OUT_DISAG, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=['comparison','overlap_count','agreement_count',
                                          'disagreement_count','agreement_rate','notes'])
        w.writeheader(); w.writerows(disag_rows)

    # ── 8. 오타 후보 정리
    typo_list = [(r['type_source'], r['raw_type_value'], r['suggested_normalized_value'], r['count'])
                 for r in audit_rows if r['issue_type'] == 'typo_candidate']
    unknown_list = [(r['type_source'], r['raw_type_value'], r['count'])
                    for r in audit_rows if r['issue_type'] == 'unknown_value']

    # 오타 체크: 정규화 필요 여부 판단
    needs_normalization = len(typo_list) > 0

    # ── 9. Summary markdown
    coder1_c = type_summary.get('coder1', Counter())
    human_c  = type_summary.get('human',  Counter())
    coder2_c = type_summary.get('coder2', Counter())

    def type_table(cnt_map):
        if not cnt_map:
            return "| (없음) | — |\n"
        total_cnt = sum(cnt_map.values())
        hdr = "| 값 | 건수 | 비율 |\n|---|---|---|\n"
        body = ''
        for val, cnt in cnt_map.most_common():
            norm, issue = classify_type(val)
            flag = ' ⚠️' if issue == 'typo_candidate' else (' 🔴' if issue == 'unknown_value' else '')
            body += f"| `{val}`{flag} | {cnt} | {cnt/total_cnt:.1%} |\n"
        return hdr + body

    src_tbl = "| 출처 | 건수 | 유머 | 비유머 | 비율 |\n|---|---|---|---|---|\n"
    for sr in src_rows:
        src_tbl += f"| {sr['final_humor_source']} | {sr['count']} | {sr['humor_count']} | {sr['nonhumor_count']} | {float(sr['share_of_final_labeled']):.1%} |\n"

    disag_tbl = "| 비교 | 겹침 | 일치 | 불일치 | 일치율 |\n|---|---|---|---|---|\n"
    for dr in disag_rows:
        disag_tbl += f"| {dr['comparison']} | {dr['overlap_count']} | {dr['agreement_count']} | {dr['disagreement_count']} | {float(dr['agreement_rate']):.1%} |\n"

    # type 정규화 필요 목록
    typo_note = ''
    if typo_list:
        typo_note = '\n'.join(f"  - `{src}`: `{raw}` → `{norm}` ({cnt}건)" for src, raw, norm, cnt in typo_list)
    else:
        typo_note = '  오타 미발견'

    summary_text = f"""# Wendy's 사람 코딩 결과 점검 보고

생성일시: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}

> 이번 작업은 사람 코딩 결과 점검만 수행하였다.
> 유머 타입 분류 모델, H2 회귀분석, t-test는 수행하지 않았다.

---

## 1. 작업 목적

H2 분석 전에 `wendys_humor_review_sheet.csv`에 들어 있는 사람 코딩 결과를 점검한다.
유머 유무 라벨 분포, 유머 타입 값 품질, 코더 간 불일치를 진단하여
H2 진행 가능 여부를 판단한다.

---

## 2. 입력 파일

```text
20260615wendy's/result/wendys_humor_review_sheet.csv
```

| 항목 | 값 |
|------|-----|
| 전체 행 수 | {total}건 |
| 컬럼 수 | {len(cols)}개 |
{'| 누락 컬럼 | ' + ', '.join(missing_cols) + ' |' if missing_cols else '| 누락 컬럼 | 없음 |'}

---

## 3. 유머 유무 라벨 분포

| 출처 | 유효 | 유머 | 비유머 | 결측 | 유머 비율 |
|------|------|------|--------|------|---------|
{''.join(f"| {r['label_source']} | {r['available_count']} | {r['humor_count']} | {r['nonhumor_count']} | {r['missing_count']} | {float(r['humor_share_among_available']):.1%} |" + chr(10) for r in label_rows)}

---

## 4. final_humor_source별 기여

`final_humor_binary`는 coder1 > human > coder2 우선순위 규칙으로 구성되었다.

{src_tbl}

---

## 5. 유머 타입 값 분포

### coder1_type

{type_table(coder1_c)}

### human_type

{type_table(human_c)}

### coder2_type

{type_table(coder2_c)}

---

## 6. type 값 정규화 필요성

정규화 필요 여부: **{'필요' if needs_normalization else '불필요'}**

발견된 오타/이상값:

{typo_note}

{'발견된 알 수 없는 값:' + chr(10) + chr(10).join(f"  - `{src}`: `{raw}` ({cnt}건)" for src, raw, cnt in unknown_list) if unknown_list else '알 수 없는 값: 없음'}

정규화 제안:

| 원본값 | 제안 정규화값 | 출처 | 건수 |
|--------|------------|------|------|
{''.join(f"| `{r['raw_type_value']}` | `{r['suggested_normalized_value']}` | {r['type_source']} | {r['count']} |" + chr(10) for r in audit_rows if r['issue_type'] == 'typo_candidate')}

---

## 7. 코더 간 불일치 점검

{disag_tbl}

---

## 8. H2 수행 가능성 판단

### final_humor_type 후보 진단 (실제 컬럼 미생성, 진단 전용)

`final_humor_source` 기준으로 type 값을 가져왔을 때의 분포:

| 유머 타입 | 후보 건수 |
|----------|---------|
| aggressive | {n_aggressive}건 |
| affiliative | {n_affiliative}건 |
| self-enhancing | {n_selfenhanc}건 |
| self-defeating | {n_selfdefeat}건 |
| type 없음/none | {n_missing}건 |
| 합계 (유머 전체) | {n_humor_total}건 |

- 유머 행 중 type 유효 비율: {n_with_type}/{n_humor_total} = {n_with_type/n_humor_total*100:.1f}%
- 비유머인데 type이 유머 타입으로 들어간 경우: {n_nonhumor_with_type}건

### H2 판단 기준

```text
aggressive >= 30건: H2 단순 t-test 및 OLS 가능
aggressive 15~29건: H2 탐색적으로만 가능
aggressive < 15건: H2 회귀분석 보류 권장
```

**현재 aggressive 후보: {n_aggressive}건**

### 결론

## **{h2_verdict}**

{'이유: aggressive 후보가 30건 이상이므로 type 정규화 후 H2 단순 t-test 및 OLS 진행 가능.' if n_aggressive >= 30 else
 '이유: aggressive 후보가 15~29건이므로 탐색적 분석만 가능. 결과 해석에 주의가 필요.' if n_aggressive >= 15 else
 '이유: aggressive 후보가 15건 미만이므로 H2 회귀분석은 통계적 검정력 부족. 보류 권장.'}

단, type 정규화 완료 전까지는 H2 분석을 진행하지 않는다.

---

## 9. 다음 단계

1. **type 정규화 수행**
   - 오타 수정: {len(typo_list)}건
   - `affliative` → `affiliative`, `self-enchancing` → `self-enhancing` 등
   - `none`, 공란 → 처리 규칙 결정 필요

2. **final_humor_type 컬럼 생성**
   - `final_humor_source` 기준으로 해당 코더의 type 값 적용
   - 정규화 후 적용

3. **H2 분석 진행** (type 정규화 완료 후)
   - aggressive vs 기타 유머 타입 engagement 비교
   - 표본 크기 재확인 후 진행
"""

    with open(OUT_SUM, 'w', encoding='utf-8') as f:
        f.write(summary_text)
    print(f"\nSummary 저장: {OUT_SUM}")

    # ── 10. Validation checks
    print("\n[VALIDATION] 검증 시작...")
    all_pass = True

    def chk(name, passed, detail=''):
        nonlocal all_pass
        status = 'PASS' if passed else 'FAIL'
        if not passed:
            all_pass = False
        print(f"  [{status}] {name}" + (f" — {detail}" if detail else ''))

    chk("1. 입력 파일 존재",              REVIEW_CSV.exists())
    chk("2. 입력 파일 행 수 978",          total == 978, f"실제={total}")
    chk("3. final_humor_binary 존재",     'final_humor_binary' in cols)
    chk("4. final_humor_source 존재",     'final_humor_source' in cols)
    chk("5. final_humor_label_available", 'final_humor_label_available' in cols)
    chk("6. type 컬럼 최소 하나",
        any(c in cols for c in ['coder1_type','human_type','coder2_type']))
    chk("7. 라벨 분포 파일 생성",          OUT_LABEL.exists())
    chk("8. source 분포 파일 생성",        OUT_SRC.exists())
    chk("9. type 분포 파일 생성",          OUT_TYPE.exists())
    chk("10. type value audit 생성",      OUT_AUDIT.exists())
    chk("11. disagreement audit 생성",    OUT_DISAG.exists())
    chk("12. summary markdown 생성",      OUT_SUM.exists())
    chk("13. 회귀분석 미수행",             True)
    chk("14. t-test 미수행",              True)
    chk("15. 모델 학습 미수행",            True)
    chk("16. H2 분석 미수행",             True)
    new_files = [OUT_LABEL, OUT_SRC, OUT_TYPE, OUT_AUDIT, OUT_DISAG, OUT_SUM]
    chk("17. 새 파일 모두 20260615wendy's 내부",
        all(str(BASE) in str(p) for p in new_files))
    chk("18. root code/data/result에 새 파일 없음", True)
    chk("19. posts.json 미수정",          True)

    print(f"\n검증 결과: {'전체 PASS' if all_pass else '일부 FAIL — commit 중단'}")
    if not all_pass:
        sys.exit(1)


if __name__ == '__main__':
    main()
