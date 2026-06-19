"""
build_batch2_training_data.py

Reads all completed batch2 coder split files (Korean columns),
maps them to the canonical English-column format used by batch1,
and produces:

  data/human_labeling_template/fortune100_human_labeling_template_batch2.csv
      — batch2 completed rows only (English columns, same schema as batch1 master)

  data/human_labeling_template/fortune100_human_labeling_template_combined.csv
      — batch1 (1,500 rows) + batch2 completed rows stacked vertically

Only rows with 유머_존재여부 in {"0","1"} are included (uncertain/blank excluded).

Outputs are UTF-8 (no BOM) to match the batch1 master template encoding.
"""

from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path

ROOT     = Path(__file__).resolve().parents[3]
CI       = ROOT / "20260618expand" / "classifier_improvement"
SPLITS   = CI / "data" / "human_labeling_template" / "coder_splits"
BATCH1   = CI / "data" / "human_labeling_template" / "fortune100_human_labeling_template.csv"
OUT_B2   = CI / "data" / "human_labeling_template" / "fortune100_human_labeling_template_batch2.csv"
OUT_COMB = CI / "data" / "human_labeling_template" / "fortune100_human_labeling_template_combined.csv"

CODERS = ["coder1", "coder2", "coder3"]
VALID_PRESENCE = {"0", "1"}

# Korean → English column mapping (inverse of COL_MAP in build scripts)
KO_TO_EN: dict[str, str] = {
    "후보_ID":            "candidate_id",
    "표본_층화":          "sampling_stratum",
    "Fortune_순위":       "fortune_rank",
    "회사명":             "company_name",
    "X_계정":             "source_x_handle",
    "트윗_ID":            "tweet_id",
    "트윗_URL":           "tweet_url",
    "작성일시":           "created_at",
    "본문":               "text",
    "유머_존재여부":      "human_humor_presence",
    "유머_유형":          "human_humor_type",
    "배정_코더":          "assigned_coder",
    "검토_상태":          "review_status",
    "총_인게이지먼트":    "total_engagement",
    "로그_총_인게이지먼트": "log_total_engagement",
    "웬디스_유머_존재여부": "wendys_transfer_humor_presence",
    "웬디스_유머_점수":   "wendys_transfer_humor_score",
    "웬디스_유머_유형":   "wendys_transfer_humor_type",
    "웬디스_유형_점수":   "wendys_transfer_type_score",
    "풀체인_유머_존재여부": "full_chain_humor_presence",
    "풀체인_유머_유형":   "full_chain_humor_type",
    "분류기_불일치":      "classifier_disagreement_flag",
    "불확실성_점수":      "uncertainty_score",
}

# Canonical output columns matching batch1 master template
OUT_FIELDS = [
    "candidate_id", "sampling_stratum", "fortune_rank", "company_name",
    "source_x_handle", "tweet_id", "tweet_url", "created_at", "text",
    "total_engagement", "wendys_transfer_humor_presence",
    "wendys_transfer_humor_type", "full_chain_humor_presence",
    "full_chain_humor_type", "classifier_disagreement_flag",
    "human_humor_presence", "human_humor_type",
    "human_confidence", "human_notes", "reviewer_id", "review_status",
]


def translate_row(row: dict) -> dict:
    en = {}
    for ko_key, val in row.items():
        en_key = KO_TO_EN.get(ko_key.lstrip("﻿"), ko_key)
        en[en_key] = val
    # fields not in Korean template → empty
    for f in OUT_FIELDS:
        en.setdefault(f, "")
    return en


def load_completed_batch2() -> list[dict]:
    rows: list[dict] = []
    seen_ids: set[str] = set()

    for coder in CODERS:
        path = SPLITS / f"{coder}_labeling_template_batch2.csv"
        if not path.exists():
            print(f"  [skip] {path.name} 없음")
            continue

        try:
            with open(path, encoding="utf-8-sig", newline="") as f:
                raw = list(csv.DictReader(f))
        except UnicodeDecodeError:
            with open(path, encoding="cp949", newline="") as f:
                raw = list(csv.DictReader(f))

        completed = [r for r in raw
                     if r.get("유머_존재여부", "").strip() in VALID_PRESENCE]
        for r in completed:
            en = translate_row(r)
            cid = en.get("candidate_id", "")
            if cid and cid not in seen_ids:
                seen_ids.add(cid)
                rows.append(en)

        print(f"  {coder} batch2: {len(raw)}행, 유효 라벨 {len(completed)}행")

    return rows


def load_batch1() -> list[dict]:
    with open(BATCH1, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=OUT_FIELDS, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def main() -> None:
    print("=== build_batch2_training_data ===\n")

    print("[1] batch2 완성 라벨 로드")
    b2_rows = load_completed_batch2()
    print(f"  batch2 합계: {len(b2_rows)}행")
    dist = Counter(r["human_humor_presence"] for r in b2_rows)
    print(f"  유머 분포: {dict(dist)} (0=비유머 1=유머)")
    type_dist = Counter(r["human_humor_type"] for r in b2_rows if r["human_humor_presence"] == "1")
    print(f"  유머_유형 분포 (유머 포스트만): {dict(type_dist)}")

    print()
    print("[2] batch2 전용 파일 저장")
    write_csv(OUT_B2, b2_rows)
    print(f"  → {OUT_B2.name}  ({len(b2_rows)}행)")

    print()
    print("[3] batch1 로드")
    b1_rows = load_batch1()
    b1_labeled = [r for r in b1_rows if r.get("human_humor_presence", "").strip() in VALID_PRESENCE]
    print(f"  batch1: {len(b1_rows)}행, 유효 라벨 {len(b1_labeled)}행")

    print()
    print("[4] 통합 파일 저장 (batch1 + batch2)")
    combined = b1_rows + b2_rows
    write_csv(OUT_COMB, combined)
    print(f"  → {OUT_COMB.name}  ({len(combined)}행 = batch1 {len(b1_rows)} + batch2 {len(b2_rows)})")

    combined_labeled = [r for r in combined if r.get("human_humor_presence", "").strip() in VALID_PRESENCE]
    dist_all = Counter(r["human_humor_presence"] for r in combined_labeled)
    print(f"  통합 유머 분포: {dict(dist_all)}")

    print()
    print("=== COMPLETE ===")
    print(f"  훈련용: {OUT_COMB.name}")
    print(f"  batch2 전용: {OUT_B2.name}")


if __name__ == "__main__":
    main()
