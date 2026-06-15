"""
integrate_coder_labels.py

코더1(251건), 코더2(462건) 레이블을 wendys_humor_review_sheet.csv에 통합한다.

추가 컬럼:
    coder1_humor        - 코더1 humor 원본값 (humor/non_humor/none/공란)
    coder1_humor_binary - 코더1 이진값 (1/0/공란)
    coder1_type         - 코더1 유머 유형
    coder2_humor        - 코더2 humor_presence 원본값
    coder2_humor_binary - 코더2 이진값
    coder2_type         - 코더2 humor_type_secondary_label

매핑 전략:
    코더1: global_post_id → tweet_id 추출 후 정확 매칭
    코더2 (수정본): global_post_id → tweet_id 추출 후 정확 매칭
"""

import csv
import re
from pathlib import Path

BASE       = Path("20260615wendy's")
REVIEW_CSV = BASE / "result" / "wendys_humor_review_sheet.csv"
CODER1_CSV = Path("/home/user/marketingstrategy/코더1_Wendy's tweet - 복사본 (2).csv")
CODER2_CSV = Path("/home/user/marketingstrategy/코더2_수정_Wendy's tweet all.csv")
OUT_CSV    = REVIEW_CSV

HUMOR_TO_BIN = {"humor": "1", "non_humor": "0", "none": "0"}


def humor_bin(raw):
    return HUMOR_TO_BIN.get(raw.strip().lower(), "")


def main():
    # ── 1. Review sheet 로드
    with open(REVIEW_CSV, newline="", encoding="utf-8") as f:
        review_rows = list(csv.DictReader(f))
    id_to_idx = {r["id"]: i for i, r in enumerate(review_rows)}

    # ── 2. 코더1 로드 및 매핑 (global_post_id 기반)
    with open(CODER1_CSV, newline="", encoding="utf-8-sig") as f:
        c1_rows = list(csv.DictReader(f))

    c1_map = {}
    c1_matched = c1_unmatched = 0
    for r in c1_rows:
        tid = r["global_post_id"].rsplit(":", 1)[-1].strip()
        if tid in id_to_idx:
            c1_map[tid] = r
            c1_matched += 1
        else:
            c1_unmatched += 1
    print(f"코더1: 매칭={c1_matched} / 미매칭={c1_unmatched}")

    # ── 3. 코더2 로드 및 매핑 (global_post_id 기반, 수정본)
    with open(CODER2_CSV, newline="", encoding="cp949") as f:
        c2_rows = list(csv.DictReader(f))

    c2_map = {}
    c2_matched = c2_unmatched = 0
    for r in c2_rows:
        tid = r["global_post_id"].rsplit(":", 1)[-1].strip()
        if tid in id_to_idx:
            c2_map[tid] = r
            c2_matched += 1
        else:
            c2_unmatched += 1
    print(f"코더2: 매칭={c2_matched} / 미매칭={c2_unmatched}")

    # ── 4. review sheet에 컬럼 추가
    new_cols = [
        "coder1_humor", "coder1_humor_binary", "coder1_type",
        "coder2_humor", "coder2_humor_binary", "coder2_type",
        "final_humor_binary", "final_humor_source",
    ]
    out_cols = list(review_rows[0].keys()) + new_cols

    updated = []
    for r in review_rows:
        row = dict(r)
        tid = r["id"]

        # 코더1
        if tid in c1_map:
            c1 = c1_map[tid]
            raw1 = c1.get("humor", "").strip().lower()
            row["coder1_humor"]        = raw1
            row["coder1_humor_binary"] = humor_bin(raw1)
            row["coder1_type"]         = c1.get("type", "").strip()
        else:
            row["coder1_humor"] = row["coder1_humor_binary"] = row["coder1_type"] = ""

        # 코더2
        if tid in c2_map:
            c2 = c2_map[tid]
            raw2 = c2.get("humor_presence", "").strip().lower()
            row["coder2_humor"]        = raw2
            row["coder2_humor_binary"] = humor_bin(raw2)
            row["coder2_type"]         = c2.get("humor_type_secondary_label", "").strip()
        else:
            row["coder2_humor"] = row["coder2_humor_binary"] = row["coder2_type"] = ""

        # ── 종합 컬럼: human과 coder1은 100% 일치 → source_A로 통합
        # 우선순위: human > coder1 > coder2
        h_bin  = row.get("human_humor_binary", "") if row.get("human_coded") == "1" else ""
        c1_bin = row.get("coder1_humor_binary", "")
        c2_bin = row.get("coder2_humor_binary", "")

        if h_bin in ("0", "1"):
            row["final_humor_binary"] = h_bin
            row["final_humor_source"] = "human"
        elif c1_bin in ("0", "1"):
            row["final_humor_binary"] = c1_bin
            row["final_humor_source"] = "coder1"
        elif c2_bin in ("0", "1"):
            row["final_humor_binary"] = c2_bin
            row["final_humor_source"] = "coder2"
        else:
            row["final_humor_binary"] = ""
            row["final_humor_source"] = ""

        updated.append(row)

    # ── 5. 저장
    with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=out_cols, quoting=csv.QUOTE_ALL, extrasaction="ignore")
        w.writeheader()
        w.writerows(updated)

    # ── 6. 요약
    n_c1    = sum(1 for r in updated if r["coder1_humor"])
    n_c2    = sum(1 for r in updated if r["coder2_humor"])
    n_both  = sum(1 for r in updated if r["coder1_humor"] and r["coder2_humor"])
    n_final = sum(1 for r in updated if r["final_humor_binary"] in ("0","1"))
    src_cnt = {}
    for r in updated:
        s = r["final_humor_source"]
        if s: src_cnt[s] = src_cnt.get(s, 0) + 1
    print(f"\n저장: {OUT_CSV}")
    print(f"전체 행: {len(updated)}")
    print(f"coder1 레이블 있음: {n_c1}건")
    print(f"coder2 레이블 있음: {n_c2}건")
    print(f"양쪽 모두 있음: {n_both}건")
    print(f"\nfinal_humor_binary 유효: {n_final}건")
    for s, cnt in sorted(src_cnt.items()):
        print(f"  출처={s}: {cnt}건")


if __name__ == "__main__":
    main()
