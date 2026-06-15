"""
update_wendys_humor_review_sheet_with_check.py

ch_wendys_humor_review_sheet.csv에 포함된 추가 사람 평가(human_coded_check)를
원본 wendys_humor_review_sheet.csv에 반영한다.

처리 규칙:
  - human_coded_check=1 → human_humor_label="humor", human_humor_binary=1
  - human_coded_check=0 → human_humor_label="non_humor", human_humor_binary=0
  - 기존 69건(human_coded=1)은 수정하지 않는다.
  - 새로 코딩된 행: human_coded=1, human_coded_check 값 기록
  - model_vs_human 재계산: match / mismatch / label_missing / no_human
"""

import csv
from pathlib import Path

BASE        = Path("20260615wendy's")
ORIG_CSV    = BASE / "result" / "wendys_humor_review_sheet.csv"
CH_CSV      = Path("/home/user/marketingstrategy/ch_wendys_humor_review_sheet.csv")
OUT_CSV     = BASE / "result" / "wendys_humor_review_sheet.csv"

def extract_tid(url):
    return url.rstrip("/").rsplit("/", 1)[-1].strip() if url else ""

def match_status(model_bin, human_bin):
    if human_bin == "":
        return "label_missing"
    if str(model_bin) == str(human_bin):
        return "match"
    return "mismatch"

def main():
    # 1. ch_ 파일에서 human_coded_check 매핑 구축 (tweet_id → '0' or '1')
    raw = CH_CSV.read_bytes()
    text = raw.decode("latin-1")
    ch_rows = list(csv.DictReader(text.splitlines()))

    check_map = {}
    for r in ch_rows:
        val = (r.get("human_coded_check") or "").strip()
        if val in ("0", "1"):
            tid = extract_tid(r.get("tweet_url", ""))
            if tid:
                check_map[tid] = val

    print(f"ch_ 파일 human_coded_check 유효 매핑: {len(check_map)}건  "
          f"(1={sum(1 for v in check_map.values() if v=='1')}, "
          f"0={sum(1 for v in check_map.values() if v=='0')})")

    # 2. 원본 리뷰 시트 로드
    with open(ORIG_CSV, newline="", encoding="utf-8") as f:
        orig_rows = list(csv.DictReader(f))

    orig_cols = list(orig_rows[0].keys())

    # human_coded_check 컬럼이 없으면 추가
    if "human_coded_check" not in orig_cols:
        out_cols = (orig_cols[:orig_cols.index("human_coded") + 1]
                    + ["human_coded_check"]
                    + orig_cols[orig_cols.index("human_coded") + 1:])
    else:
        out_cols = orig_cols

    # 3. 반영
    n_updated = 0
    n_skipped_existing = 0
    out_rows = []

    for r in orig_rows:
        row = dict(r)
        tid = str(row.get("id", "")).strip()

        # human_coded_check 초기화
        if "human_coded_check" not in row:
            row["human_coded_check"] = ""

        if tid in check_map:
            if row.get("human_coded") == "1":
                # 기존 69건 — 수정하지 않고 check 값만 기록
                row["human_coded_check"] = check_map[tid]
                n_skipped_existing += 1
            else:
                # 신규 사람 판단 반영
                val = check_map[tid]
                row["human_coded_check"]  = val
                row["human_coded"]        = "1"
                row["human_humor_binary"] = val
                row["human_humor_label"]  = "humor" if val == "1" else "non_humor"
                # human_type은 신규 코딩에 없으므로 공란 유지
                row["model_vs_human"] = match_status(row.get("model_humor", ""), val)
                n_updated += 1

        out_rows.append(row)

    # 4. 저장
    with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=out_cols, quoting=csv.QUOTE_ALL, extrasaction="ignore")
        w.writeheader()
        w.writerows(out_rows)

    # 5. 요약
    n_human_total   = sum(1 for r in out_rows if r.get("human_coded") == "1")
    n_humor         = sum(1 for r in out_rows if r.get("human_humor_binary") == "1")
    n_nonhumor      = sum(1 for r in out_rows if r.get("human_humor_binary") == "0")
    n_match         = sum(1 for r in out_rows if r.get("model_vs_human") == "match")
    n_mismatch      = sum(1 for r in out_rows if r.get("model_vs_human") == "mismatch")

    print(f"\n저장: {OUT_CSV}")
    print(f"전체 행: {len(out_rows)}")
    print(f"신규 사람 판단 반영: {n_updated}건")
    print(f"기존 코딩(수정 없음, check값만 추가): {n_skipped_existing}건")
    print(f"총 human_coded=1: {n_human_total}건  (유머={n_humor}, 비유머={n_nonhumor})")
    print(f"model_vs_human — match: {n_match}건 / mismatch: {n_mismatch}건")

if __name__ == "__main__":
    main()
