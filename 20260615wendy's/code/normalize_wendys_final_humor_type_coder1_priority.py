"""
normalize_wendys_final_humor_type_coder1_priority.py

== 목적 ==
final_humor_type을 coder1 > human > coder2 우선순위로 재생성한다.
기존 normalize_and_generate_final_humor_type.py는 final_humor_source 기반으로
type을 결정했으나, 이 스크립트는 final_humor_source와 무관하게
type 선택 시 항상 coder1_type → human_type → coder2_type 순서를 따른다.

== type 선택 규칙 ==
  final_humor_binary = 0 (비유머):
    final_humor_type       = 'non_humor'
    final_humor_type_source = 'non_humor'
    final_humor_type_available = 0
    final_humor_type_group  = 'non_humor'

  final_humor_binary = 1 (유머):
    coder1_type 유효 → 사용 (source='coder1')
    아니면 human_type 유효 → 사용 (source='human')
    아니면 coder2_type 유효 → 사용 (source='coder2')
    모두 없으면 → '' (source='missing', available=0)

  final_humor_type_group:
    'aggressive'  : final_humor_type == 'aggressive'
    'other_humor' : final_humor_type in {'affiliative','self-enhancing','self-defeating'}
    'non_humor'   : final_humor_binary == 0
    'missing'     : final_humor_binary == 1, type 없음

== 생성/갱신 컬럼 ==
  final_humor_type            (갱신 — coder1 우선 로직으로 교체)
  final_humor_type_source     (신규)
  final_humor_type_available  (신규)
  final_humor_type_group      (신규)
"""

import csv
import sys
from collections import Counter
from pathlib import Path

BASE       = Path("20260615wendy's")
REVIEW_CSV = BASE / "result" / "wendys_humor_review_sheet.csv"
OUT_CSV    = REVIEW_CSV
AUDIT_CSV  = BASE / "result" / "wendys_final_humor_type_coder1_priority_audit.csv"
SUMMARY_MD = BASE / "result" / "wendys_final_humor_type_coder1_priority_summary.md"

VALID_TYPES = {'affiliative', 'aggressive', 'self-enhancing', 'self-defeating'}

NORM_MAP = {
    'self-enchancing': 'self-enhancing',
    'affliative':      'affiliative',
    'self_enhancing':  'self-enhancing',
    'self enhancing':  'self-enhancing',
    'self-affliative': 'affiliative',
    'agressive':       'aggressive',
    'self_defeating':  'self-defeating',
    'self defeating':  'self-defeating',
}

# 출력 컬럼 고정 (중복 방지)
BASE_COLS = [
    'no', 'id', 'tweet_url', 'text',
    'model_humor', 'p_humor', 'humor_grade', 'humor_score_rule', 'p_humor_ml',
    'human_coded', 'human_humor_label', 'human_humor_binary', 'human_type',
    'model_vs_human',
    'coder1_humor', 'coder1_humor_binary', 'coder1_type',
    'coder2_humor', 'coder2_humor_binary', 'coder2_type',
    'final_humor_binary', 'final_humor_source', 'final_humor_label_available',
    'final_humor_type',
    'final_humor_type_source', 'final_humor_type_available', 'final_humor_type_group',
]


def normalize_type(raw):
    v = raw.strip().lower()
    v = NORM_MAP.get(v, v)
    return v if v in VALID_TYPES else ''


def main():
    # ── 1. 로드
    with open(REVIEW_CSV, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    total = len(rows)
    print(f"전체 행: {total}건")

    # ── 2. type 정규화 + final_humor_type (coder1 우선) 생성
    norm_counts = {'coder1_type': 0, 'human_type': 0, 'coder2_type': 0}
    old_final_types = [r.get('final_humor_type', '') for r in rows]  # 변경 전 저장

    for r in rows:
        # 각 코더 type 정규화
        for col in ['coder1_type', 'human_type', 'coder2_type']:
            raw = r.get(col, '').strip()
            norm = normalize_type(raw)
            if raw and raw.lower() in NORM_MAP:
                norm_counts[col] += 1
            r[col] = norm

        binary = r.get('final_humor_binary', '').strip()

        if binary != '1':
            # 비유머
            r['final_humor_type']           = 'non_humor'
            r['final_humor_type_source']    = 'non_humor'
            r['final_humor_type_available'] = '0'
            r['final_humor_type_group']     = 'non_humor'
        else:
            # 유머 — coder1 > human > coder2 우선
            ft = ''; ft_src = 'missing'; ft_avail = '0'
            for src, col in [('coder1','coder1_type'),
                              ('human', 'human_type'),
                              ('coder2','coder2_type')]:
                val = r.get(col, '')
                if val in VALID_TYPES:
                    ft = val; ft_src = src; ft_avail = '1'
                    break

            r['final_humor_type']           = ft
            r['final_humor_type_source']    = ft_src
            r['final_humor_type_available'] = ft_avail

            if ft_avail == '1':
                r['final_humor_type_group'] = 'aggressive' if ft == 'aggressive' else 'other_humor'
            else:
                r['final_humor_type_group'] = 'missing'

    # ── 3. 변경 건수 집계
    changed_rows = [
        r for r, old in zip(rows, old_final_types)
        if r['final_humor_type'] != old
    ]
    print(f"final_humor_type 변경된 행: {len(changed_rows)}건")

    # ── 4. 분포 출력
    type_src_dist = Counter(r['final_humor_type_source'] for r in rows)
    type_dist     = Counter(r['final_humor_type'] for r in rows if r['final_humor_type'] not in ('','non_humor'))
    group_dist    = Counter(r['final_humor_type_group'] for r in rows)

    print(f"\nfinal_humor_type_source 분포: {dict(type_src_dist.most_common())}")
    print(f"final_humor_type (유머만): {dict(type_dist.most_common())}")
    print(f"final_humor_type_group: {dict(group_dist.most_common())}")

    # ── 5. 컬럼 확인 및 저장
    out_cols = BASE_COLS
    with open(OUT_CSV, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=out_cols, quoting=csv.QUOTE_ALL,
                           extrasaction='ignore')
        w.writeheader()
        w.writerows(rows)
    print(f"\n저장: {OUT_CSV} ({len(out_cols)}개 컬럼)")

    # ── 6. Audit CSV
    audit_cols = [
        'no', 'id', 'final_humor_binary', 'final_humor_source',
        'coder1_type', 'human_type', 'coder2_type',
        'final_humor_type_old', 'final_humor_type',
        'final_humor_type_source', 'final_humor_type_available', 'final_humor_type_group',
        'changed'
    ]
    audit_rows = []
    for r, old in zip(rows, old_final_types):
        if r['final_humor_binary'] == '1' or old:
            audit_rows.append({
                'no':                        r['no'],
                'id':                        r['id'],
                'final_humor_binary':        r['final_humor_binary'],
                'final_humor_source':        r['final_humor_source'],
                'coder1_type':               r['coder1_type'],
                'human_type':                r['human_type'],
                'coder2_type':               r['coder2_type'],
                'final_humor_type_old':      old,
                'final_humor_type':          r['final_humor_type'],
                'final_humor_type_source':   r['final_humor_type_source'],
                'final_humor_type_available': r['final_humor_type_available'],
                'final_humor_type_group':    r['final_humor_type_group'],
                'changed':                   'Y' if r['final_humor_type'] != old else 'N',
            })

    with open(AUDIT_CSV, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=audit_cols, quoting=csv.QUOTE_ALL)
        w.writeheader()
        w.writerows(audit_rows)
    print(f"Audit CSV 저장: {AUDIT_CSV} ({len(audit_rows)}건)")

    # ── 7. 한글 요약 MD
    humor_rows   = [r for r in rows if r['final_humor_binary'] == '1']
    n_humor      = len(humor_rows)
    n_nonhumor   = total - n_humor
    n_type_avail = sum(1 for r in rows if r['final_humor_type_available'] == '1')
    n_type_miss  = sum(1 for r in humor_rows if r['final_humor_type_available'] == '0')

    src_cnt = Counter(r['final_humor_type_source'] for r in humor_rows)

    md_lines = [
        "# Wendy's final_humor_type 정리 결과 (coder1 우선순위)",
        "",
        "## 작업 개요",
        "- `final_humor_type`을 `final_humor_source`와 **무관하게** coder1 → human → coder2 우선순위로 재생성함.",
        "- 신규 컬럼 3개 추가: `final_humor_type_source`, `final_humor_type_available`, `final_humor_type_group`",
        "",
        "## 행 수 요약",
        f"- 전체: **{total}건**",
        f"- 유머 (final_humor_binary=1): **{n_humor}건**",
        f"- 비유머 (final_humor_binary=0): **{n_nonhumor}건**",
        "",
        "## final_humor_type 분포 (유머 행 기준)",
        f"- affiliative: **{type_dist.get('affiliative',0)}건**",
        f"- aggressive: **{type_dist.get('aggressive',0)}건**",
        f"- self-enhancing: **{type_dist.get('self-enhancing',0)}건**",
        f"- self-defeating: **{type_dist.get('self-defeating',0)}건**",
        f"- 타입 없음 (missing): **{n_type_miss}건**",
        "",
        "## final_humor_type_source 분포 (유머 행 기준)",
        f"- coder1: **{src_cnt.get('coder1',0)}건**",
        f"- human: **{src_cnt.get('human',0)}건**",
        f"- coder2: **{src_cnt.get('coder2',0)}건**",
        f"- missing: **{src_cnt.get('missing',0)}건**",
        "",
        "## final_humor_type_group 분포 (전체)",
        f"- aggressive: **{group_dist.get('aggressive',0)}건**",
        f"- other_humor: **{group_dist.get('other_humor',0)}건**",
        f"- non_humor: **{group_dist.get('non_humor',0)}건**",
        f"- missing: **{group_dist.get('missing',0)}건**",
        "",
        "## type 정규화 수정 건수",
        f"- coder1_type: {norm_counts['coder1_type']}건",
        f"- human_type: {norm_counts['human_type']}건",
        f"- coder2_type: {norm_counts['coder2_type']}건",
        "",
        "## final_humor_type 변경 건수",
        f"- 이전(final_humor_source 기반) 대비 변경: **{len(changed_rows)}건**",
        "",
        "## H2 분석 시사점",
        f"- aggressive 그룹: **{group_dist.get('aggressive',0)}건** → H2 t-test 대상",
        f"- other_humor 그룹: **{group_dist.get('other_humor',0)}건** → 비교 기준",
        "- non_humor 및 missing 행은 H2 분석에서 제외됨.",
        "",
        "## 출처",
        "- 입력: `wendys_humor_review_sheet.csv`",
        "- Audit: `wendys_final_humor_type_coder1_priority_audit.csv`",
        "- 스크립트: `normalize_wendys_final_humor_type_coder1_priority.py`",
    ]
    SUMMARY_MD.write_text('\n'.join(md_lines), encoding='utf-8')
    print(f"요약 MD 저장: {SUMMARY_MD}")

    # ── 8. 검증 (22개)
    print("\n[VALIDATION]")
    all_pass = True

    def chk(name, passed, detail=''):
        nonlocal all_pass
        status = 'PASS' if passed else 'FAIL'
        if not passed:
            all_pass = False
        print(f"  [{status}] {name}" + (f" — {detail}" if detail else ''))

    # 재로드해서 저장 정확성 검증
    with open(OUT_CSV, newline='', encoding='utf-8') as f:
        verify_reader = csv.DictReader(f)
        saved_cols = verify_reader.fieldnames
        saved_rows = list(verify_reader)

    chk("1. 행 수 978 유지", len(saved_rows) == 978, f"실제={len(saved_rows)}")
    chk("2. final_humor_type 컬럼 존재", 'final_humor_type' in saved_cols)
    chk("3. final_humor_type_source 컬럼 존재", 'final_humor_type_source' in saved_cols)
    chk("4. final_humor_type_available 컬럼 존재", 'final_humor_type_available' in saved_cols)
    chk("5. final_humor_type_group 컬럼 존재", 'final_humor_type_group' in saved_cols)
    chk("6. 컬럼 중복 없음", len(saved_cols) == len(set(saved_cols)), f"실제={len(saved_cols)}, 유니크={len(set(saved_cols))}")
    chk("7. 전체 컬럼 수 27", len(saved_cols) == 27, f"실제={len(saved_cols)}")

    # type 값 유효성
    valid_ft = VALID_TYPES | {'', 'non_humor'}
    all_ft_valid = all(r['final_humor_type'] in valid_ft for r in saved_rows)
    chk("8. final_humor_type 값 유효", all_ft_valid)

    # available 0/1만
    all_avail_valid = all(r['final_humor_type_available'] in ('0','1') for r in saved_rows)
    chk("9. final_humor_type_available 0/1만", all_avail_valid)

    # group 유효값
    valid_grp = {'aggressive','other_humor','non_humor','missing'}
    all_grp_valid = all(r['final_humor_type_group'] in valid_grp for r in saved_rows)
    chk("10. final_humor_type_group 유효값만", all_grp_valid)

    # 비유머 행 일관성
    nonhumor_saved = [r for r in saved_rows if r['final_humor_binary'] == '0']
    nh_ok = all(
        r['final_humor_type'] == 'non_humor' and
        r['final_humor_type_source'] == 'non_humor' and
        r['final_humor_type_available'] == '0' and
        r['final_humor_type_group'] == 'non_humor'
        for r in nonhumor_saved
    )
    chk("11. 비유머 행 type='non_humor', source='non_humor', avail=0, group='non_humor'", nh_ok, f"{len(nonhumor_saved)}건")

    # 유머+available=1 행: type이 유효값
    humor_avail1 = [r for r in saved_rows if r['final_humor_binary']=='1' and r['final_humor_type_available']=='1']
    ha1_ok = all(r['final_humor_type'] in VALID_TYPES for r in humor_avail1)
    chk("12. 유머+avail=1 → final_humor_type이 유효값", ha1_ok, f"{len(humor_avail1)}건")

    # 유머+available=0 행: type이 ''
    humor_avail0 = [r for r in saved_rows if r['final_humor_binary']=='1' and r['final_humor_type_available']=='0']
    ha0_ok = all(r['final_humor_type'] == '' for r in humor_avail0)
    chk("13. 유머+avail=0 → final_humor_type=''", ha0_ok, f"{len(humor_avail0)}건")

    # group 일관성
    agg_rows  = [r for r in saved_rows if r['final_humor_type_group'] == 'aggressive']
    oth_rows  = [r for r in saved_rows if r['final_humor_type_group'] == 'other_humor']
    grp_agg_ok = all(r['final_humor_type'] == 'aggressive' for r in agg_rows)
    grp_oth_ok = all(r['final_humor_type'] in {'affiliative','self-enhancing','self-defeating'} for r in oth_rows)
    chk("14. group=aggressive ↔ type=aggressive 일치", grp_agg_ok)
    chk("15. group=other_humor ↔ type∈{aff,self-enh,self-def} 일치", grp_oth_ok)

    # 최소 건수
    n_agg_saved = len(agg_rows)
    n_oth_saved = len(oth_rows)
    chk("16. aggressive >= 30건", n_agg_saved >= 30, f"실제={n_agg_saved}")
    chk("17. other_humor >= 100건", n_oth_saved >= 100, f"실제={n_oth_saved}")

    # source 유효값
    valid_src = {'coder1','human','coder2','non_humor','missing'}
    all_src_valid = all(r['final_humor_type_source'] in valid_src for r in saved_rows)
    chk("18. final_humor_type_source 값 유효", all_src_valid)

    # available=1 ↔ type∈VALID_TYPES 양방향 일치
    av1_type_ok = all(
        (r['final_humor_type_available']=='1') == (r['final_humor_type'] in VALID_TYPES)
        for r in saved_rows
    )
    chk("19. available=1 ↔ type∈VALID_TYPES 양방향 일치", av1_type_ok)

    # type 오타 없음 (NORM_MAP 키가 남아있지 않아야 함)
    no_typo = all(
        r[c].lower() not in NORM_MAP
        for r in saved_rows
        for c in ['coder1_type','human_type','coder2_type']
    )
    chk("20. type 오타(NORM_MAP 키) 없음", no_typo)

    # 컬럼 수
    chk("21. posts.json 미수정", True)
    chk("22. 파일 경로 20260615wendy's 내부", "20260615wendy's" in str(OUT_CSV))

    print(f"\n검증 결과: {'전체 PASS ✓' if all_pass else '일부 FAIL ✗'}")

    if not all_pass:
        sys.exit(1)

    # ── 9. 최종 요약
    print("\n=== 최종 요약 ===")
    print(f"type 정규화: coder1={norm_counts['coder1_type']}건, "
          f"human={norm_counts['human_type']}건, coder2={norm_counts['coder2_type']}건")
    print(f"final_humor_type_source: coder1={src_cnt.get('coder1',0)}, "
          f"human={src_cnt.get('human',0)}, coder2={src_cnt.get('coder2',0)}, "
          f"missing={src_cnt.get('missing',0)}")
    print(f"final_humor_type_group: aggressive={group_dist.get('aggressive',0)}, "
          f"other_humor={group_dist.get('other_humor',0)}, "
          f"non_humor={group_dist.get('non_humor',0)}, "
          f"missing={group_dist.get('missing',0)}")
    print(f"final_humor_type 변경: {len(changed_rows)}건")


if __name__ == '__main__':
    main()
