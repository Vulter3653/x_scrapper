"""
scripts/build_wendys_human_label_raw_link.py

Wendy's partial human-coded humor labels를 raw posts.json과 연결하여
분석 가능한 human-label linked dataset을 생성한다.

연결 기준:
  global_post_id의 마지막 segment(tweet_id)를 posts.json의 id 필드와 exact match.
  텍스트 동일 여부는 검수용으로만 사용하고, 연결 성공 여부는 id match로만 결정한다.

제약사항:
  - data/wendys/posts.json 수정 금지
  - dashboard/data/ 수정 금지
  - X API, 스크래핑, browser automation 사용 금지
  - human label은 "Wendy's partial human review sample"로만 취급
  - gold label 또는 전체 정답으로 일반화하지 않는다
"""

import argparse
import csv
import json
import sys
import re
import unicodedata
from pathlib import Path
from datetime import datetime

# ─────────────────────────────────────────────────────────────────────────────
# 필수 컬럼 정의
# ─────────────────────────────────────────────────────────────────────────────
HUMAN_REQUIRED_COLS = {"global_post_id", "company_name", "date", "text", "humor", "type"}
RAW_REQUIRED_FIELDS = {"id"}

# 출력 컬럼 (지정 순서)
OUTPUT_COLS = [
    "global_post_id",
    "tweet_id",
    "company_name",
    "source_x_handle",
    "human_label_source",
    "human_label_scope",
    "human_humor_label_raw",
    "human_humor_binary",
    "human_humor_type_raw",
    "human_humor_type_normalized",
    "label_missing_flag",
    "raw_match_status",
    "raw_text_match_status",
    "human_text",
    "raw_text",
    "text_normalized_equal",
    "created_at_human",
    "created_at_raw",
    "tweet_url",
    "reply_count",
    "favorite_count",
    "retweet_count",
    "quote_count",
    "bookmark_count",
    "view_count",
    "lang",
    "conversation_id",
    "is_quote_status",
    "raw_source",
    "raw_scraped_at",
]

# humor 값 정규화 매핑
HUMOR_TO_BINARY = {
    "humor":      "1",
    "non_humor":  "0",
    "none":       "0",
    "":           "",   # blank → label_missing_flag = true
}

# type 값 정규화 매핑
TYPE_NORMALIZE = {
    "affiliative":    "affiliative",
    "self-enhancing": "self_enhancing",
    "self_enhancing": "self_enhancing",
    "aggressive":     "aggressive",
    "self-defeating": "self_defeating",
    "self_defeating": "self_defeating",
    "none":           "none",
    "":               "none",
}


def normalize_text(t: str) -> str:
    """텍스트를 소문자 변환 + 공백 정규화 + HTML 엔티티 제거로 정규화한다."""
    t = t.strip()
    t = t.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    t = unicodedata.normalize("NFKC", t)
    t = re.sub(r"\s+", " ", t).lower()
    return t


def parse_args():
    p = argparse.ArgumentParser(
        description="Wendy's human humor labels를 raw posts.json과 연결한다."
    )
    p.add_argument(
        "--human-labels",
        default="data/manual_labels/wendys_human_humor_labels.csv",
        help="사람이 코딩한 humor label CSV",
    )
    p.add_argument(
        "--raw-posts",
        default="data/wendys/posts.json",
        help="Wendy's raw posts JSON",
    )
    p.add_argument(
        "--out-csv",
        default="data/derived/humor/human_labels/wendys_human_label_raw_linked.csv",
        help="연결 결과 CSV 출력 경로",
    )
    p.add_argument(
        "--out-audit",
        default="data/audit/humor/human_labels/wendys_human_label_raw_link_audit.json",
        help="Audit JSON 출력 경로",
    )
    return p.parse_args()


def main():
    args = parse_args()

    human_path = Path(args.human_labels)
    raw_path   = Path(args.raw_posts)
    out_csv    = Path(args.out_csv)
    out_audit  = Path(args.out_audit)

    # ─────────────────────────────────────────────────────────────
    # 단계 1. 입력 파일 존재 확인
    # ─────────────────────────────────────────────────────────────
    if not human_path.exists():
        print(f"[FAIL] human labels 파일 없음: {human_path}", file=sys.stderr)
        sys.exit(1)
    if not raw_path.exists():
        print(f"[FAIL] raw posts 파일 없음: {raw_path}", file=sys.stderr)
        sys.exit(1)

    # ─────────────────────────────────────────────────────────────
    # 단계 2. Human labels CSV 읽기 및 필수 컬럼 확인
    # ─────────────────────────────────────────────────────────────
    with open(human_path, newline="", encoding="utf-8-sig") as f:
        reader      = csv.DictReader(f)
        actual_cols = set(reader.fieldnames or [])
        missing_cols = HUMAN_REQUIRED_COLS - actual_cols
        if missing_cols:
            print(f"[FAIL] human CSV 필수 컬럼 누락: {sorted(missing_cols)}", file=sys.stderr)
            sys.exit(1)
        human_rows = list(reader)

    n_input = len(human_rows)
    print(f"[1] human labels 입력 행: {n_input}건")

    # ─────────────────────────────────────────────────────────────
    # 단계 3. Duplicate 검사 — global_post_id 및 tweet_id
    # ─────────────────────────────────────────────────────────────
    from collections import Counter
    gpid_counts  = Counter(r["global_post_id"] for r in human_rows)
    dup_gpids    = {k: v for k, v in gpid_counts.items() if v > 1}
    if dup_gpids:
        print(f"[FAIL] duplicate global_post_id 존재: {dup_gpids}", file=sys.stderr)
        sys.exit(1)

    # tweet_id 추출 및 중복 확인
    def extract_tweet_id(gpid: str) -> str:
        return gpid.rsplit(":", 1)[-1].strip()

    tweet_id_counts = Counter(extract_tweet_id(r["global_post_id"]) for r in human_rows)
    dup_tids        = {k: v for k, v in tweet_id_counts.items() if v > 1}
    if dup_tids:
        print(f"[FAIL] duplicate tweet_id 존재: {dup_tids}", file=sys.stderr)
        sys.exit(1)

    print(f"[2] duplicate 없음 (global_post_id / tweet_id 모두 고유)")

    # ─────────────────────────────────────────────────────────────
    # 단계 4. Raw posts.json 읽기 및 id 인덱스 구성
    # ─────────────────────────────────────────────────────────────
    with open(raw_path, encoding="utf-8") as f:
        raw_posts = json.load(f)

    for post in raw_posts:
        if "id" not in post:
            print("[FAIL] raw posts에 'id' 필드 누락된 항목이 있음", file=sys.stderr)
            sys.exit(1)

    # id → post 딕셔너리 (str 기준)
    raw_index = {str(post["id"]): post for post in raw_posts}
    print(f"[3] raw posts 로드: {len(raw_index)}건")

    # ─────────────────────────────────────────────────────────────
    # 단계 5. 연결 수행 및 출력 행 구성
    # ─────────────────────────────────────────────────────────────
    output_rows     = []
    matched_ids     = []
    unmatched_ids   = []
    label_missing   = []
    text_mismatches = []
    n_none_humor    = 0  # 'none' 값으로 비유머 처리된 건수

    for hr in human_rows:
        gpid     = hr["global_post_id"]
        tweet_id = extract_tweet_id(gpid)
        raw      = raw_index.get(tweet_id)

        # id 매칭
        if raw:
            raw_match_status = "matched"
            matched_ids.append(tweet_id)
        else:
            raw_match_status = "unmatched"
            unmatched_ids.append(tweet_id)
            raw = {}  # 빈 dict로 처리

        # human_humor_label_raw 및 binary 정규화
        humor_raw = hr.get("humor", "").strip()
        if humor_raw == "none":
            n_none_humor += 1
        humor_binary    = HUMOR_TO_BINARY.get(humor_raw, "")
        label_miss_flag = "true" if humor_raw == "" else "false"
        if humor_raw == "":
            label_missing.append(tweet_id)

        # type 정규화
        type_raw  = hr.get("type", "").strip()
        type_norm = TYPE_NORMALIZE.get(type_raw, type_raw)  # 알 수 없는 값은 그대로

        # 텍스트 비교 (검수용 — id match에는 영향 없음)
        human_text = hr.get("text", "").strip()
        raw_text   = str(raw.get("text", "")).strip()
        h_norm     = normalize_text(human_text)
        r_norm     = normalize_text(raw_text)
        text_norm_equal     = "true" if h_norm == r_norm else "false"
        raw_text_match_status = "match" if h_norm == r_norm else "mismatch"
        if raw_match_status == "matched" and raw_text_match_status == "mismatch":
            text_mismatches.append(tweet_id)

        row = {
            "global_post_id":            gpid,
            "tweet_id":                  tweet_id,
            "company_name":              hr.get("company_name", "").strip(),
            "source_x_handle":           "@Wendys",
            "human_label_source":        "Wendy's partial human review sample",
            "human_label_scope":         "partial",
            "human_humor_label_raw":     humor_raw,
            "human_humor_binary":        humor_binary,
            "human_humor_type_raw":      type_raw,
            "human_humor_type_normalized": type_norm,
            "label_missing_flag":        label_miss_flag,
            "raw_match_status":          raw_match_status,
            "raw_text_match_status":     raw_text_match_status if raw_match_status == "matched" else "no_raw",
            "human_text":                human_text,
            "raw_text":                  raw_text,
            "text_normalized_equal":     text_norm_equal if raw_match_status == "matched" else "no_raw",
            "created_at_human":          hr.get("date", "").strip(),
            "created_at_raw":            str(raw.get("created_at", "")).strip(),
            "tweet_url":                 str(raw.get("tweet_url", "")).strip(),
            "reply_count":               str(raw.get("reply_count", "")).strip(),
            "favorite_count":            str(raw.get("favorite_count", "")).strip(),
            "retweet_count":             str(raw.get("retweet_count", "")).strip(),
            "quote_count":               str(raw.get("quote_count", "")).strip(),
            "bookmark_count":            str(raw.get("bookmark_count", "")).strip(),
            "view_count":                str(raw.get("view_count", "")).strip(),
            "lang":                      str(raw.get("lang", "")).strip(),
            "conversation_id":           str(raw.get("conversation_id", "")).strip(),
            "is_quote_status":           str(raw.get("is_quote_status", "")).strip(),
            "raw_source":                str(raw.get("source", "")).strip(),
            "raw_scraped_at":            str(raw.get("scraped_at", "")).strip(),
        }
        output_rows.append(row)

    n_output = len(output_rows)
    print(f"[4] 연결 완료: matched={len(matched_ids)}, unmatched={len(unmatched_ids)}, "
          f"label_missing={len(label_missing)}, text_mismatch={len(text_mismatches)}")

    # ─────────────────────────────────────────────────────────────
    # 단계 6. 출력 행 수 검증
    # ─────────────────────────────────────────────────────────────
    if n_output != n_input:
        print(f"[FAIL] 출력 행 수({n_output}) ≠ 입력 행 수({n_input})", file=sys.stderr)
        sys.exit(1)

    # ─────────────────────────────────────────────────────────────
    # 단계 7. 출력 디렉터리 생성 및 CSV 저장
    # ─────────────────────────────────────────────────────────────
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f, fieldnames=OUTPUT_COLS,
            quoting=csv.QUOTE_ALL, extrasaction="ignore"
        )
        writer.writeheader()
        writer.writerows(output_rows)
    print(f"[5] linked CSV 저장: {out_csv}")

    # ─────────────────────────────────────────────────────────────
    # 단계 8. Audit JSON 생성
    # ─────────────────────────────────────────────────────────────
    audit = {
        "generated_at":          datetime.utcnow().isoformat() + "Z",
        "script":                "scripts/build_wendys_human_label_raw_link.py",
        "inputs": {
            "human_labels_path": str(human_path),
            "raw_posts_path":    str(raw_path),
        },
        "outputs": {
            "linked_csv":  str(out_csv),
            "audit_json":  str(out_audit),
        },
        "summary": {
            "n_input_human_rows":     n_input,
            "n_output_rows":          n_output,
            "n_matched":              len(matched_ids),
            "n_unmatched":            len(unmatched_ids),
            "n_label_missing":        len(label_missing),
            "n_text_mismatch":        len(text_mismatches),
            "n_raw_posts":            len(raw_index),
            "none_humor_as_nonhumor": n_none_humor,
        },
        "humor_value_counts": {
            k: sum(1 for r in human_rows if r["humor"].strip() == k)
            for k in ["humor", "non_humor", "none", ""]
        },
        "type_value_counts": {
            k: sum(1 for r in human_rows if r["type"].strip() == k)
            for k in ["affiliative", "aggressive", "self-enhancing", "self-defeating",
                      "self_enhancing", "self_defeating", "none", ""]
        },
        "unmatched_tweet_ids":    unmatched_ids,
        "label_missing_tweet_ids": label_missing,
        "text_mismatch_tweet_ids": text_mismatches,
        "raw_data_modified":      False,
        "dashboard_data_modified": False,
        "notes": [
            "human labels는 Wendy's partial human review sample로만 취급한다.",
            "전체 정답(gold label)이나 full human annotation으로 일반화하지 않는다.",
            "id exact match 실패 행은 unmatched로 처리하며 임의 매칭하지 않는다.",
            "'none' humor 값은 비유머(0)로 정규화하되 human_humor_label_raw에 원본값을 보존한다.",
            "text mismatch가 있어도 id match가 성공한 행은 연결을 유지하고 raw_text_match_status=mismatch로 표시한다.",
        ],
    }

    out_audit.parent.mkdir(parents=True, exist_ok=True)
    with open(out_audit, "w", encoding="utf-8") as f:
        json.dump(audit, f, ensure_ascii=False, indent=2)
    print(f"[6] audit JSON 저장: {out_audit}")

    # ─────────────────────────────────────────────────────────────
    # 최종 요약 출력
    # ─────────────────────────────────────────────────────────────
    print()
    print("=== 완료 요약 ===")
    print(f"  입력 행 수      : {n_input}")
    print(f"  출력 행 수      : {n_output}")
    print(f"  id 매칭 성공    : {len(matched_ids)}")
    print(f"  id 매칭 실패    : {len(unmatched_ids)}")
    print(f"  label 결측      : {len(label_missing)}")
    print(f"  text mismatch   : {len(text_mismatches)}")
    if unmatched_ids:
        print(f"  unmatched IDs   : {unmatched_ids}")
    if label_missing:
        print(f"  label 결측 IDs  : {label_missing}")
    print(f"  → {out_csv}")
    print(f"  → {out_audit}")


if __name__ == "__main__":
    main()
