"""validate_coder_labeling_splits.py"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CI = ROOT / "20260618expand" / "classifier_improvement"
SPLITS_DIR = CI / "data" / "human_labeling_template" / "coder_splits"
CODERS = ["coder1", "coder2", "coder3"]
ROWS_PER_CODER = 500
TOTAL_ROWS = 1500


def main() -> int:
    failures: list[str] = []

    # 1. coder 파일 존재 확인
    for coder in CODERS:
        p = SPLITS_DIR / f"{coder}_labeling_template.csv"
        if not p.exists():
            failures.append(f"파일 없음: {p.name}")

    # 2. LABELING_GUIDE.md 존재 및 내용 확인
    guide = SPLITS_DIR / "LABELING_GUIDE.md"
    if not guide.exists():
        failures.append("파일 없음: LABELING_GUIDE.md")
    else:
        guide_text = guide.read_text(encoding="utf-8")
        if "기업 자신감" not in guide_text and "corporate assertive" not in guide_text.lower():
            failures.append("LABELING_GUIDE.md에 기업 자신감 표현 vs 공격적 유머 구분 안내가 없음")
        for val in ["humor", "non_humor", "uncertain", "aggressive", "affiliative",
                    "self_enhancing", "self_defeating", "non_humorous"]:
            if val not in guide_text:
                failures.append(f"LABELING_GUIDE.md에 허용값 누락: {val}")

    # 3. 각 coder 파일 구조 검증
    cid_sets: dict[str, set[str]] = {}
    tid_sets: dict[str, set[str]] = {}

    for coder in CODERS:
        p = SPLITS_DIR / f"{coder}_labeling_template.csv"
        if not p.exists():
            continue

        with p.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            fieldnames = list(reader.fieldnames or [])
            rows = list(reader)

        # 행수 확인
        if len(rows) != ROWS_PER_CODER:
            failures.append(f"{coder}: {ROWS_PER_CODER}행 필요, {len(rows)}행 있음")

        # 필수 컬럼 존재 확인
        for col in ["본문", "유머_존재여부", "유머_유형", "배정_코더", "검토_상태"]:
            if col not in fieldnames:
                failures.append(f"{coder}: 필수 컬럼 없음 — '{col}'")

        # 컬럼 순서: 본문 → 유머_존재여부 → 유머_유형
        if "본문" in fieldnames and "유머_존재여부" in fieldnames:
            idx_text = fieldnames.index("본문")
            idx_hhp = fieldnames.index("유머_존재여부")
            if idx_hhp != idx_text + 1:
                failures.append(
                    f"{coder}: '유머_존재여부'는 '본문' 바로 다음 컬럼이어야 함 "
                    f"(본문@{idx_text}, 유머_존재여부@{idx_hhp})"
                )

        if "유머_존재여부" in fieldnames and "유머_유형" in fieldnames:
            idx_hhp = fieldnames.index("유머_존재여부")
            idx_hht = fieldnames.index("유머_유형")
            if idx_hht != idx_hhp + 1:
                failures.append(
                    f"{coder}: '유머_유형'은 '유머_존재여부' 바로 다음 컬럼이어야 함 "
                    f"(유머_존재여부@{idx_hhp}, 유머_유형@{idx_hht})"
                )

        # 배정_코더 값이 파일명과 일치
        wrong_coder = [r for r in rows if r.get("배정_코더", "") != coder]
        if wrong_coder:
            failures.append(f"{coder}: {len(wrong_coder)}행의 배정_코더 값이 파일명과 다름")

        # 검토_상태 기본값 = pending
        non_pending = [r for r in rows if r.get("검토_상태", "") != "pending"]
        if non_pending:
            failures.append(f"{coder}: {len(non_pending)}행의 검토_상태가 'pending'이 아님")

        # 유머_존재여부, 유머_유형은 빈칸
        non_blank_presence = [r for r in rows if r.get("유머_존재여부", "").strip()]
        non_blank_type = [r for r in rows if r.get("유머_유형", "").strip()]
        if non_blank_presence:
            failures.append(f"{coder}: {len(non_blank_presence)}행의 유머_존재여부가 빈칸이 아님")
        if non_blank_type:
            failures.append(f"{coder}: {len(non_blank_type)}행의 유머_유형이 빈칸이 아님")

        # 파일 내 후보_ID 중복 확인
        if "후보_ID" in fieldnames:
            all_file_cids = [r["후보_ID"] for r in rows]
            if len(set(all_file_cids)) != len(all_file_cids):
                failures.append(f"{coder}: 파일 내 후보_ID 중복 있음")
            cid_sets[coder] = set(all_file_cids)
        if "트윗_ID" in fieldnames:
            tid_sets[coder] = {r["트윗_ID"] for r in rows}

    # 4. 코더 간 중복 확인
    coders_with_cids = [c for c in CODERS if c in cid_sets]
    for i, c1 in enumerate(coders_with_cids):
        for c2 in coders_with_cids[i+1:]:
            cid_overlap = cid_sets[c1] & cid_sets[c2]
            if cid_overlap:
                failures.append(f"후보_ID 중복: {c1}과 {c2} 사이 {len(cid_overlap)}개")
            if c1 in tid_sets and c2 in tid_sets:
                tid_overlap = tid_sets[c1] & tid_sets[c2]
                if tid_overlap:
                    failures.append(f"트윗_ID 중복: {c1}과 {c2} 사이 {len(tid_overlap)}개")

    # 5. 전체 배정 행수 = 1,500
    total = sum(len(v) for v in cid_sets.values())
    if len(coders_with_cids) == len(CODERS) and total != TOTAL_ROWS:
        failures.append(f"전체 배정 행수 = {total}, 필요: {TOTAL_ROWS}")

    # 6. 요약 파일 존재 확인
    summary_files = list(SPLITS_DIR.glob("coder_assignment_summary*.csv"))
    if not summary_files:
        failures.append("요약 파일 없음: coder_assignment_summary*.csv (최소 1개 필요)")

    if failures:
        print("VALIDATION FAIL")
        for f in failures:
            print(f"- {f}")
        return 1
    print("VALIDATION PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
