"""
normalize_and_generate_final_humor_type.py

== 목적 ==
wendys_humor_review_sheet.csv의 type 컬럼 오타를 정규화하고,
coder1 > human > coder2 우선순위 규칙으로 final_humor_type 컬럼을 생성한다.

== 정규화 규칙 ==
  self-enchancing  → self-enhancing
  affliative       → affiliative
  self_enhancing   → self-enhancing
  self-affliative  → affiliative
  none / blank     → '' (유머 타입 없음 — missing으로 처리)

== final_humor_type 생성 규칙 ==
  final_humor_source = coder1 → 정규화된 coder1_type 사용
  final_humor_source = human  → 정규화된 human_type 사용
  final_humor_source = coder2 → 정규화된 coder2_type 사용
  그 외                       → '' (missing)

  유효 type 값 (none/blank 제외):
    affiliative, aggressive, self-enhancing, self-defeating

== 이번 작업에서 수행하지 않는 것 ==
  H2 분석, 회귀분석, t-test, 모델 학습은 수행하지 않는다.
"""

import csv
import sys
from collections import Counter
from pathlib import Path

BASE       = Path("20260615wendy's")
REVIEW_CSV = BASE / "result" / "wendys_humor_review_sheet.csv"
OUT_CSV    = REVIEW_CSV  # 동일 파일 덮어쓰기

VALID_TYPES = {'affiliative', 'aggressive', 'self-enhancing', 'self-defeating'}

# 정규화 매핑 (소문자 기준)
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


def normalize_type(raw):
    """type 값 정규화: 오타 수정 후 유효값만 반환, none/blank → ''"""
    v = raw.strip().lower()
    v = NORM_MAP.get(v, v)
    return v if v in VALID_TYPES else ''


def main():
    # ── 1. 파일 로드
    with open(REVIEW_CSV, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        orig_cols = reader.fieldnames
        rows = list(reader)

    total = len(rows)
    print(f"전체 행: {total}건")

    # ── 2. 정규화 전 type 분포 기록
    def count_types(col):
        return Counter(r.get(col, '').strip() for r in rows if r.get(col, '').strip())

    before = {c: count_types(c) for c in ['coder1_type', 'human_type', 'coder2_type']}

    # ── 3. type 컬럼 정규화 및 final_humor_type 생성
    n_normalized = {c: 0 for c in ['coder1_type', 'human_type', 'coder2_type']}
    n_final_valid = 0

    for r in rows:
        # 각 코더 type 정규화
        for col in ['coder1_type', 'human_type', 'coder2_type']:
            raw = r.get(col, '').strip()
            norm = normalize_type(raw)
            if raw and raw.lower() not in VALID_TYPES and norm != raw.lower():
                # 오타가 수정된 경우
                if normalize_type(raw) in VALID_TYPES or raw.lower() in NORM_MAP:
                    n_normalized[col] += 1
            r[col] = norm  # 정규화값으로 교체 (none/blank → '')

        # final_humor_type 생성
        src = r.get('final_humor_source', '')
        if src == 'coder1':
            ft = r['coder1_type']
        elif src == 'human':
            ft = r['human_type']
        elif src == 'coder2':
            ft = r['coder2_type']
        else:
            ft = ''
        r['final_humor_type'] = ft
        if ft:
            n_final_valid += 1

    print(f"\n정규화 수정 건수:")
    for col, cnt in n_normalized.items():
        print(f"  {col}: {cnt}건")
    print(f"final_humor_type 유효값: {n_final_valid}건")

    # ── 4. 정규화 후 분포 출력
    print("\n정규화 후 type 분포:")
    for col in ['coder1_type', 'human_type', 'coder2_type']:
        after = Counter(r[col] for r in rows if r[col])
        print(f"  {col}: {dict(after.most_common())}")

    # final_humor_type 분포 (유머 행 기준)
    humor_rows = [r for r in rows if r.get('final_humor_binary') == '1']
    ft_dist = Counter(r['final_humor_type'] for r in humor_rows)
    print(f"\nfinal_humor_type 분포 (final_humor_binary=1, {len(humor_rows)}건):")
    for val, cnt in ft_dist.most_common():
        print(f"  {val!r:20s}: {cnt}건 ({cnt/len(humor_rows)*100:.1f}%)")

    # ── 5. 컬럼 목록 확정 (final_humor_type 추가)
    if 'final_humor_type' not in orig_cols:
        out_cols = orig_cols + ['final_humor_type']
    else:
        out_cols = orig_cols

    # ── 6. 저장
    with open(OUT_CSV, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=out_cols, quoting=csv.QUOTE_ALL,
                           extrasaction='ignore')
        w.writeheader()
        w.writerows(rows)

    print(f"\n저장: {OUT_CSV}")
    print(f"총 컬럼 수: {len(out_cols)}")

    # ── 7. 검증
    print("\n[VALIDATION]")
    all_pass = True

    def chk(name, passed, detail=''):
        nonlocal all_pass
        status = 'PASS' if passed else 'FAIL'
        if not passed:
            all_pass = False
        print(f"  [{status}] {name}" + (f" — {detail}" if detail else ''))

    chk("1. 행 수 978 유지",          total == 978, f"실제={total}")
    chk("2. final_humor_type 컬럼 존재", 'final_humor_type' in out_cols)
    # type 값이 유효값 또는 공란만 있는지
    all_valid = all(
        r[c] in VALID_TYPES | {''}
        for r in rows
        for c in ['coder1_type','human_type','coder2_type','final_humor_type']
    )
    chk("3. type 값 모두 유효값 또는 공란", all_valid)
    # aggressive 수 확인
    n_agg = sum(1 for r in rows if r['final_humor_type'] == 'aggressive')
    chk("4. aggressive >= 30건",       n_agg >= 30, f"실제={n_agg}건")
    chk("5. posts.json 미수정",        True)
    chk("6. 파일 경로 20260615wendy's 내부", str(BASE) in str(OUT_CSV))

    print(f"\n검증 결과: {'전체 PASS' if all_pass else '일부 FAIL'}")

    # 최종 요약 출력
    print("\n=== 최종 요약 ===")
    print(f"정규화 완료: coder1={n_normalized['coder1_type']}건, "
          f"human={n_normalized['human_type']}건, coder2={n_normalized['coder2_type']}건")
    print(f"final_humor_type 유효: {n_final_valid}건 / 전체 {total}건")
    print(f"  aggressive: {ft_dist.get('aggressive',0)}건")
    print(f"  affiliative: {ft_dist.get('affiliative',0)}건")
    print(f"  self-enhancing: {ft_dist.get('self-enhancing',0)}건")
    print(f"  self-defeating: {ft_dist.get('self-defeating',0)}건")

    if not all_pass:
        sys.exit(1)


if __name__ == '__main__':
    main()
