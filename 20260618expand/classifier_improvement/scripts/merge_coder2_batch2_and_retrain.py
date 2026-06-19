"""
merge_coder2_batch2_and_retrain.py

coder2 batch2 레이블(한글 컬럼)을 combined 템플릿에 병합하고
분류기를 재훈련·재적용한다.

Steps:
  1. coder2 batch2 (Korean cols) → English cols 변환
  2. fortune100_human_labeling_template_combined.csv 에 append
  3. apply_domain_adapted_classifier.py 재실행 (내부 재훈련 포함)
  4. build_h1h2h3_from_domain_adapted.py 재실행
"""

from __future__ import annotations

import csv
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

PYPACKAGES = Path("/home/user/.local/pypackages")
if str(PYPACKAGES) not in sys.path:
    sys.path.insert(0, str(PYPACKAGES))

ROOT = Path(__file__).resolve().parents[3]
CI   = ROOT / "20260618expand" / "classifier_improvement"

CODER2_B2  = ROOT / "coder2_labeling_template_batch2.csv"
COMBINED   = CI / "data" / "human_labeling_template" / "fortune100_human_labeling_template_combined.csv"
INTEGRATED = (CI / "h1_presence_only" / "integrated_collected_corpus" / "data"
              / "integrated_h1_presence_classified_posts.csv")

# 한글 → 영문 컬럼 매핑
KR_TO_EN = {
    "후보_ID":          "candidate_id",
    "﻿후보_ID":    "candidate_id",
    "표본_층화":        "sampling_stratum",
    "Fortune_순위":     "fortune_rank",
    "회사명":           "company_name",
    "X_계정":           "source_x_handle",
    "트윗_ID":          "tweet_id",
    "트윗_URL":         "tweet_url",
    "작성일시":         "created_at",
    "본문":             "text",
    "총_인게이지먼트":  "total_engagement",
    "웬디스_유머_존재여부": "wendys_transfer_humor_presence",
    "웬디스_유머_유형": "wendys_transfer_humor_type",
    "풀체인_유머_존재여부": "full_chain_humor_presence",
    "풀체인_유머_유형": "full_chain_humor_type",
    "분류기_불일치":    "classifier_disagreement_flag",
    "유머_존재여부":    "human_humor_presence",
    "유머_유형":        "human_humor_type",
    "배정_코더":        "reviewer_id",
    "검토_상태":        "review_status",
}

COMBINED_COLS = [
    "candidate_id", "sampling_stratum", "fortune_rank", "company_name",
    "source_x_handle", "tweet_id", "tweet_url", "created_at", "text",
    "total_engagement", "wendys_transfer_humor_presence", "wendys_transfer_humor_type",
    "full_chain_humor_presence", "full_chain_humor_type", "classifier_disagreement_flag",
    "human_humor_presence", "human_humor_type",
    "human_confidence", "human_notes", "reviewer_id", "review_status",
]


def load_coder2_b2() -> list[dict]:
    """coder2 batch2 파일 읽기 (한글 컬럼 → 영문 변환)."""
    with open(CODER2_B2, newline="", encoding="utf-8-sig") as f:
        raw = list(csv.DictReader(f))

    converted = []
    for r in raw:
        row: dict = {v: "" for v in COMBINED_COLS}
        for kr, val in r.items():
            en = KR_TO_EN.get(kr.strip())
            if en and en in row:
                row[en] = val.strip()
        # 미입력 필드 기본값
        row.setdefault("human_confidence", "")
        row.setdefault("human_notes", "")
        # tweet_id 지수 표기 → 정수 문자열 변환
        tid = row.get("tweet_id", "")
        if tid and "E" in tid.upper():
            try:
                row["tweet_id"] = str(int(float(tid)))
            except ValueError:
                pass
        converted.append(row)
    return converted


def main() -> None:
    print("=== merge_coder2_batch2_and_retrain ===\n")

    # ── Step 1: coder2 batch2 변환 ─────────────────────────────────────────
    c2_rows = load_coder2_b2()
    print(f"coder2 batch2 로드: {len(c2_rows)} rows")
    pres_dist = Counter(r["human_humor_presence"] for r in c2_rows)
    type_dist = Counter(r["human_humor_type"] for r in c2_rows)
    print(f"  presence dist: {dict(pres_dist)}")
    print(f"  type dist:     {dict(type_dist)}")

    # ── Step 2: 기존 combined 로드 및 중복 확인 ────────────────────────────
    with open(COMBINED, newline="", encoding="utf-8") as f:
        existing = list(csv.DictReader(f))
    existing_ids = {r["candidate_id"] for r in existing}
    c2_ids = {r["candidate_id"] for r in c2_rows}

    duplicates = c2_ids & existing_ids
    if duplicates:
        print(f"  경고: 이미 combined에 있는 ID {len(duplicates)}개 — 제외")
        c2_rows = [r for r in c2_rows if r["candidate_id"] not in existing_ids]

    merged = existing + c2_rows
    print(f"\nMerged 템플릿: {len(existing)} + {len(c2_rows)} = {len(merged)} rows")

    pres_all = Counter(r["human_humor_presence"] for r in merged)
    type_all = Counter(r["human_humor_type"] for r in merged)
    valid_pres = sum(1 for r in merged if r["human_humor_presence"] in ("0", "1"))
    valid_type = sum(1 for r in merged
                     if r["human_humor_presence"] == "1"
                     and r["human_humor_type"] in ("1", "2", "3", "4"))
    print(f"  전체 presence: {dict(pres_all)}")
    print(f"  전체 type:     {dict(type_all)}")
    print(f"  유효 presence 레이블: {valid_pres}")
    print(f"  유효 type 레이블:     {valid_type}")

    # combined 파일 덮어쓰기
    with open(COMBINED, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COMBINED_COLS, extrasaction="ignore")
        w.writeheader()
        w.writerows(merged)
    print(f"\n→ {COMBINED.name} 업데이트 완료 ({len(merged)} rows)")

    # ── Step 3: 분류기 재훈련 + 재적용 ────────────────────────────────────
    print("\n[Step 3] apply_domain_adapted_classifier.py 재실행 ...")
    apply_script = CI / "scripts" / "apply_domain_adapted_classifier.py"
    result = subprocess.run(
        [sys.executable, str(apply_script),
         "--template", str(COMBINED),
         "--input",    str(INTEGRATED)],
        cwd=str(ROOT),
        capture_output=False,
    )
    if result.returncode != 0:
        print("ERROR: apply_domain_adapted_classifier 실패")
        raise SystemExit(result.returncode)

    # ── Step 4: H1/H2/H3 데이터셋 재빌드 ─────────────────────────────────
    print("\n[Step 4] build_h1h2h3_from_domain_adapted.py 재실행 ...")
    build_script = CI / "scripts" / "build_h1h2h3_from_domain_adapted.py"
    result = subprocess.run(
        [sys.executable, str(build_script)],
        cwd=str(ROOT),
        capture_output=False,
    )
    if result.returncode != 0:
        print("ERROR: build_h1h2h3 실패")
        raise SystemExit(result.returncode)

    print("\n=== merge_coder2_batch2_and_retrain COMPLETE ===")


if __name__ == "__main__":
    main()
