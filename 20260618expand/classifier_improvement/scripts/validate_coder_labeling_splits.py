"""validate_coder_labeling_splits.py

Validates batch1 and batch2 coder labeling split files.

Usage:
  python validate_coder_labeling_splits.py                # template mode (default)
  python validate_coder_labeling_splits.py --mode template  # blanks allowed
  python validate_coder_labeling_splits.py --mode labeled   # strict: all cells must be filled

Numeric coding scheme:
  유머_존재여부 (human_humor_presence): 0=비유머, 1=유머, 2=애매함
  유머_유형     (human_humor_type):     1=AGGRESSIVE, 2=AFFILIATIVE,
                                        3=SELF-ENHANCING, 4=SELF-DEFEATING
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CI = ROOT / "20260618expand" / "classifier_improvement"
SPLITS_DIR = CI / "data" / "human_labeling_template" / "coder_splits"
CODERS = ["coder1", "coder2", "coder3"]
ROWS_PER_CODER = 500
TOTAL_ROWS = 3000  # batch1 (1500) + batch2 (1500)

# Numeric allowed values
VALID_PRESENCE = {"0", "1", "2"}
VALID_TYPE = {"1", "2", "3", "4"}

# Column name aliases (Korean or English)
PRESENCE_COLS = {"유머_존재여부", "human_humor_presence"}
TYPE_COLS = {"유머_유형", "human_humor_type"}
TEXT_COLS = {"본문", "text"}
CAND_ID_COLS = {"후보_ID", "candidate_id"}
TWEET_ID_COLS = {"트윗_ID", "tweet_id"}
CODER_COLS = {"배정_코더", "assigned_coder"}
STATUS_COLS = {"검토_상태", "review_status"}


def find_col(fieldnames: list[str], aliases: set[str]) -> str | None:
    for f in fieldnames:
        if f in aliases:
            return f
    return None


def validate_file(
    path: Path,
    coder: str,
    batch: str,
    mode: str,
    failures: list[str],
    warnings: list[str],
) -> tuple[set[str], set[str]]:
    """Validate one coder file. Returns (candidate_id_set, tweet_id_set)."""
    if not path.exists():
        failures.append(f"[{batch}][{coder}] 파일 없음: {path.name}")
        return set(), set()

    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames or [])
        rows = list(reader)

    tag = f"[{batch}][{coder}]"

    # A/B: row count
    if len(rows) != ROWS_PER_CODER:
        failures.append(f"{tag} {ROWS_PER_CODER}행 필요, {len(rows)}행 있음")

    # Column existence
    col_presence = find_col(fieldnames, PRESENCE_COLS)
    col_type = find_col(fieldnames, TYPE_COLS)
    col_text = find_col(fieldnames, TEXT_COLS)
    col_cid = find_col(fieldnames, CAND_ID_COLS)
    col_tid = find_col(fieldnames, TWEET_ID_COLS)
    col_coder = find_col(fieldnames, CODER_COLS)
    col_status = find_col(fieldnames, STATUS_COLS)

    for col, name in [
        (col_text, "본문/text"),
        (col_presence, "유머_존재여부/human_humor_presence"),
        (col_type, "유머_유형/human_humor_type"),
        (col_coder, "배정_코더/assigned_coder"),
        (col_status, "검토_상태/review_status"),
    ]:
        if col is None:
            failures.append(f"{tag} 필수 컬럼 없음: {name}")

    # F: text → presence immediately adjacent (G requirement)
    if col_text and col_presence:
        idx_text = fieldnames.index(col_text)
        idx_pres = fieldnames.index(col_presence)
        if idx_pres != idx_text + 1:
            failures.append(
                f"{tag} '{col_presence}'은 '{col_text}' 바로 다음 컬럼이어야 함 "
                f"(text@{idx_text}, presence@{idx_pres})"
            )

    # G: presence → type immediately adjacent
    if col_presence and col_type:
        idx_pres = fieldnames.index(col_presence)
        idx_type = fieldnames.index(col_type)
        if idx_type != idx_pres + 1:
            failures.append(
                f"{tag} '{col_type}'은 '{col_presence}' 바로 다음 컬럼이어야 함 "
                f"(presence@{idx_pres}, type@{idx_type})"
            )

    # 배정_코더 값 확인
    if col_coder:
        wrong_coder = [r for r in rows if r.get(col_coder, "") != coder]
        if wrong_coder:
            failures.append(f"{tag} {len(wrong_coder)}행의 배정_코더 값이 '{coder}'와 다름")

    # 검토_상태 기본값 (template mode에서만)
    if col_status and mode == "template":
        non_pending = [r for r in rows if r.get(col_status, "") != "pending"]
        if non_pending:
            failures.append(f"{tag} {len(non_pending)}행의 검토_상태가 'pending'이 아님")

    # H/I/J/K: 허용값 및 교차 검증
    if col_presence and col_type:
        bad_presence: list[str] = []
        bad_type: list[str] = []
        type_when_non_humor: list[str] = []  # J
        missing_type: list[str] = []         # K (labeled mode only)

        for i, r in enumerate(rows, start=2):
            pres = r.get(col_presence, "").strip()
            typ = r.get(col_type, "").strip()

            # H: presence value
            if mode == "template":
                if pres not in VALID_PRESENCE and pres != "":
                    bad_presence.append(f"행{i}={repr(pres)}")
            else:  # labeled: blank not allowed
                if pres not in VALID_PRESENCE:
                    bad_presence.append(f"행{i}={repr(pres) if pres else 'blank'}")

            # I: type value
            if typ not in VALID_TYPE and typ != "":
                bad_type.append(f"행{i}={repr(typ)}")

            # J: presence=0/2 but type is not blank
            if pres in ("0", "2") and typ != "":
                type_when_non_humor.append(
                    f"행{i} (존재여부={pres}, 유형={repr(typ)})"
                )

            # K: labeled mode — presence=1 requires type 1/2/3/4
            if mode == "labeled" and pres == "1" and typ == "":
                missing_type.append(f"행{i}")

        if bad_presence:
            failures.append(
                f"{tag} 유머_존재여부 허용값 위반 ({len(bad_presence)}건): "
                + ", ".join(bad_presence[:5])
            )
        if bad_type:
            failures.append(
                f"{tag} 유머_유형 허용값 위반 ({len(bad_type)}건): "
                + ", ".join(bad_type[:5])
            )
        if type_when_non_humor:
            # J: this is always a FAIL (template AND labeled modes)
            failures.append(
                f"{tag} 유머_존재여부=0/2인데 유머_유형 입력됨 ({len(type_when_non_humor)}건): "
                + ", ".join(type_when_non_humor[:5])
            )
        if missing_type:
            failures.append(
                f"{tag} [labeled] 유머_존재여부=1인데 유머_유형 공란 ({len(missing_type)}건): "
                + ", ".join(missing_type[:5])
            )

    # Collect IDs
    cid_set: set[str] = set()
    tid_set: set[str] = set()
    if col_cid:
        all_cids = [r.get(col_cid, "") for r in rows]
        if len(set(all_cids)) != len(all_cids):
            failures.append(f"{tag} 파일 내 후보_ID 중복 있음")
        cid_set = set(all_cids)
    if col_tid:
        tid_set = {r.get(col_tid, "") for r in rows}

    return cid_set, tid_set


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate coder labeling split files.")
    parser.add_argument(
        "--mode",
        choices=["template", "labeled"],
        default="template",
        help=(
            "template: 입력칸 공란 허용 (라벨링 전 템플릿 검증). "
            "labeled: 엄격 모드 — 모든 입력칸이 유효한 숫자여야 함 (라벨링 완료 후 검증)."
        ),
    )
    args = parser.parse_args()
    mode = args.mode

    failures: list[str] = []
    warnings: list[str] = []

    # LABELING_GUIDE.md 존재 및 내용 확인
    guide = SPLITS_DIR / "LABELING_GUIDE.md"
    if not guide.exists():
        failures.append("파일 없음: LABELING_GUIDE.md")
    else:
        guide_text = guide.read_text(encoding="utf-8")
        if "기업 자신감" not in guide_text:
            failures.append("LABELING_GUIDE.md에 기업 자신감 표현 vs 공격적 유머 구분 안내가 없음")
        for val in ["AGGRESSIVE", "AFFILIATIVE", "SELF-ENHANCING", "SELF-DEFEATING"]:
            if val not in guide_text:
                failures.append(f"LABELING_GUIDE.md에 유머 유형 누락: {val}")
        for code in ["`0`", "`1`", "`2`"]:
            if code not in guide_text:
                failures.append(f"LABELING_GUIDE.md에 유머_존재여부 코드 누락: {code}")

    # 각 coder 파일 검증 (batch1 + batch2)
    all_cids: dict[str, set[str]] = {}
    all_tids: dict[str, set[str]] = {}

    for coder in CODERS:
        p1 = SPLITS_DIR / f"{coder}_labeling_template.csv"
        cids1, tids1 = validate_file(p1, coder, "batch1", mode, failures, warnings)
        all_cids[f"batch1_{coder}"] = cids1
        all_tids[f"batch1_{coder}"] = tids1

        p2 = SPLITS_DIR / f"{coder}_labeling_template_batch2.csv"
        cids2, tids2 = validate_file(p2, coder, "batch2", mode, failures, warnings)
        all_cids[f"batch2_{coder}"] = cids2
        all_tids[f"batch2_{coder}"] = tids2

    # D: 전체 행수 = 3,000
    keys_with_data = [k for k, v in all_cids.items() if v]
    total = sum(len(v) for v in all_cids.values())
    if len(keys_with_data) == 6 and total != TOTAL_ROWS:
        failures.append(f"전체 배정 행수 = {total}, 필요: {TOTAL_ROWS}")

    # E: 교차 중복 확인 (후보_ID + 트윗_ID)
    keys = list(all_cids.keys())
    for i, k1 in enumerate(keys):
        for k2 in keys[i + 1:]:
            cid_overlap = all_cids[k1] & all_cids[k2]
            if cid_overlap:
                failures.append(
                    f"후보_ID 중복: {k1}과 {k2} 사이 {len(cid_overlap)}개"
                )
            tid_overlap = all_tids.get(k1, set()) & all_tids.get(k2, set())
            if tid_overlap:
                failures.append(
                    f"트윗_ID 중복: {k1}과 {k2} 사이 {len(tid_overlap)}개"
                )

    # 요약 파일 존재 확인
    summary_files = list(SPLITS_DIR.glob("coder_assignment_summary*.csv"))
    if not summary_files:
        failures.append("요약 파일 없음: coder_assignment_summary*.csv (최소 1개 필요)")

    # 결과 출력
    print(f"[mode={mode}] 파일 6개 (batch1×3 + batch2×3), 총 {TOTAL_ROWS}행 대상")
    if warnings:
        print("WARNINGS:")
        for w in warnings:
            print(f"  WARNING: {w}")
    if failures:
        print("VALIDATION FAIL")
        for err in failures:
            print(f"- {err}")
        return 1

    print("VALIDATION PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
