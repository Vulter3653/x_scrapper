"""
build_wendys_humor_review_sheet.py

978건 전체 게시글에 대해 사람이 한눈에 확인하기 쉬운 통합 리뷰 시트를 생성한다.

출력 컬럼:
  no                  - 행 번호 (1~978)
  id                  - tweet ID
  tweet_url           - 원문 URL
  text                - 게시글 텍스트
  model_humor         - 모델 유머 예측 (1=유머, 0=비유머, threshold 0.5)
  p_humor             - 모델 유머 확률 (0~1)
  humor_score_rule    - 기존 규칙 기반 점수
  p_humor_ml          - 기존 weak-supervised 점수
  human_coded         - 사람이 직접 판단했는지 여부 (1=예, 0=아니오)
  human_humor_label   - 사람 판단 원본값 (humor/non_humor/none, 없으면 공란)
  human_humor_binary  - 사람 판단 이진값 (1/0, 없으면 공란)
  human_type          - 사람 판단 유머 유형 (없으면 공란)
  model_vs_human      - 사람 판단이 있을 때 모델과 일치 여부 (match/mismatch/no_human)
"""

import csv
import math
from pathlib import Path

BASE = Path("20260615wendy's")

PRED_CSV  = BASE / "result" / "wendys_human_tfidf_logreg_full_predictions.csv"
HUMAN_CSV = BASE / "data"   / "wendys_partial_human_coded_humor_labels.csv"
OUT_CSV   = BASE / "result" / "wendys_humor_review_sheet.csv"

# 사람 코딩 라벨 변환
HUMOR_TO_BINARY = {"humor": 1, "non_humor": 0, "none": 0}

def main():
    # 978건 모델 예측 로드
    with open(PRED_CSV, newline="", encoding="utf-8") as f:
        pred_rows = list(csv.DictReader(f))

    # 사람 코딩 파일 로드 및 tweet_id 인덱싱
    with open(HUMAN_CSV, newline="", encoding="utf-8-sig") as f:
        human_rows = list(csv.DictReader(f))

    human_map = {}
    for r in human_rows:
        tid = r["global_post_id"].rsplit(":", 1)[-1].strip()
        human_map[tid] = r

    # 통합 시트 생성
    out_rows = []
    for i, pr in enumerate(pred_rows, 1):
        tid       = str(pr["id"])
        model_bin = int(pr.get("pred_humor_tfidf_logreg_050", 0))
        p_humor   = float(pr.get("p_humor_tfidf_logreg_human", 0))
        hr        = human_map.get(tid)

        if hr:
            humor_raw    = str(hr.get("humor", "")).strip().lower()
            human_binary = HUMOR_TO_BINARY.get(humor_raw, "") if humor_raw else ""
            if humor_raw == "":
                human_coded    = 1
                human_binary   = ""
                label_missing  = True
            else:
                human_coded    = 1
                label_missing  = False

            human_type = str(hr.get("type", "")).strip()

            if label_missing or human_binary == "":
                match_status = "label_missing"
            elif int(human_binary) == model_bin:
                match_status = "match"
            else:
                match_status = "mismatch"
        else:
            humor_raw    = ""
            human_binary = ""
            human_coded  = 0
            human_type   = ""
            match_status = "no_human"

        # p_humor 등급 (사람 읽기 편의용)
        if p_humor >= 0.65:
            humor_grade = "높음"
        elif p_humor >= 0.50:
            humor_grade = "보통"
        elif p_humor >= 0.35:
            humor_grade = "낮음"
        else:
            humor_grade = "매우낮음"

        out_rows.append({
            "no":                  i,
            "id":                  tid,
            "tweet_url":           pr.get("tweet_url", ""),
            "text":                pr.get("text", ""),
            "model_humor":         model_bin,
            "p_humor":             "%.4f" % p_humor,
            "humor_grade":         humor_grade,
            "humor_score_rule":    pr.get("humor_score", ""),
            "p_humor_ml":          pr.get("p_humor_ml", ""),
            "human_coded":         human_coded,
            "human_humor_label":   humor_raw,
            "human_humor_binary":  human_binary,
            "human_type":          human_type,
            "model_vs_human":      match_status,
        })

    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    cols = ["no", "id", "tweet_url", "text",
            "model_humor", "p_humor", "humor_grade",
            "humor_score_rule", "p_humor_ml",
            "human_coded", "human_humor_label", "human_humor_binary",
            "human_type", "model_vs_human"]
    with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols, quoting=csv.QUOTE_ALL)
        w.writeheader()
        w.writerows(out_rows)

    # 요약 출력
    n_model_humor   = sum(1 for r in out_rows if r["model_humor"] == 1)
    n_human_coded   = sum(1 for r in out_rows if r["human_coded"] == 1)
    n_match         = sum(1 for r in out_rows if r["model_vs_human"] == "match")
    n_mismatch      = sum(1 for r in out_rows if r["model_vs_human"] == "mismatch")
    n_human_humor   = sum(1 for r in out_rows if str(r["human_humor_binary"]) == "1")
    n_human_nonhumor= sum(1 for r in out_rows if str(r["human_humor_binary"]) == "0")

    print(f"저장: {OUT_CSV}")
    print(f"전체 행: {len(out_rows)}")
    print(f"모델 유머 예측 (model_humor=1): {n_model_humor}건 ({n_model_humor/978*100:.1f}%)")
    print(f"사람 판단 있음 (human_coded=1): {n_human_coded}건")
    print(f"  └ 사람 유머=1: {n_human_humor}건 / 사람 비유머=0: {n_human_nonhumor}건")
    print(f"모델 vs 사람 — match: {n_match}건 / mismatch: {n_mismatch}건")

if __name__ == "__main__":
    main()
