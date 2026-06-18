"""
build_coder_labeling_splits.py

Splits the 1,500-row Fortune Top 100 labeling template into three 500-row
files for three coders (random seed 42, simple shuffle-and-split).
All column names and guide text are in Korean.

Outputs:
  data/human_labeling_template/coder_splits/coder1_labeling_template.csv
  data/human_labeling_template/coder_splits/coder2_labeling_template.csv
  data/human_labeling_template/coder_splits/coder3_labeling_template.csv
  data/human_labeling_template/coder_splits/coder_assignment_summary_by_coder.csv
  data/human_labeling_template/coder_splits/coder_assignment_summary_by_stratum.csv
  data/human_labeling_template/coder_splits/LABELING_GUIDE.md
"""

from __future__ import annotations

import csv
import random
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CI = ROOT / "20260618expand" / "classifier_improvement"

TEMPLATE = CI / "data" / "human_labeling_template" / "fortune100_human_labeling_template.csv"
CANDIDATES = CI / "data" / "labeling_candidates" / "fortune100_labeling_candidates.csv"
SPLITS_DIR = CI / "data" / "human_labeling_template" / "coder_splits"

RANDOM_SEED = 42
CODERS = ["coder1", "coder2", "coder3"]

# 영문 원본 컬럼명 → 한국어 출력 컬럼명 매핑
COL_MAP: dict[str, str] = {
    "candidate_id":                   "후보_ID",
    "sampling_stratum":               "표본_층화",
    "fortune_rank":                   "Fortune_순위",
    "company_name":                   "회사명",
    "source_x_handle":                "X_계정",
    "tweet_id":                       "트윗_ID",
    "tweet_url":                      "트윗_URL",
    "created_at":                     "작성일시",
    "text":                           "본문",
    "human_humor_presence":           "유머_존재여부",
    "human_humor_type":               "유머_유형",
    "assigned_coder":                 "배정_코더",
    "review_status":                  "검토_상태",
    "total_engagement":               "총_인게이지먼트",
    "log_total_engagement":           "로그_총_인게이지먼트",
    "wendys_transfer_humor_presence": "웬디스_유머_존재여부",
    "wendys_transfer_humor_score":    "웬디스_유머_점수",
    "wendys_transfer_humor_type":     "웬디스_유머_유형",
    "wendys_transfer_type_score":     "웬디스_유형_점수",
    "full_chain_humor_presence":      "풀체인_유머_존재여부",
    "full_chain_humor_type":          "풀체인_유머_유형",
    "classifier_disagreement_flag":   "분류기_불일치",
    "uncertainty_score":              "불확실성_점수",
    "human_confidence":               "신뢰도",
    "human_notes":                    "메모",
    "reviewer_id":                    "검토자_ID",
}

# 코더가 직접 입력하는 필수 컬럼 순서 (한국어 이름 기준)
PRIORITY_COLS_KO = [
    "후보_ID",
    "표본_층화",
    "Fortune_순위",
    "회사명",
    "X_계정",
    "트윗_ID",
    "트윗_URL",
    "작성일시",
    "본문",
    "유머_존재여부",   # ← 코더 입력 1번
    "유머_유형",       # ← 코더 입력 2번
    "배정_코더",
    "검토_상태",
]
REFERENCE_COLS_KO = [
    "총_인게이지먼트",
    "로그_총_인게이지먼트",
    "웬디스_유머_존재여부",
    "웬디스_유머_점수",
    "웬디스_유머_유형",
    "웬디스_유형_점수",
    "풀체인_유머_존재여부",
    "풀체인_유머_유형",
    "분류기_불일치",
    "불확실성_점수",
]

LABELING_GUIDE_TEXT = """\
# 라벨링 가이드 — Fortune Top 100 유머 인간 코딩

이 파일은 코더 배정 템플릿(`coder1_labeling_template.csv`, `coder2_labeling_template.csv`,
`coder3_labeling_template.csv`)을 사용하는 코더를 위한 코딩 지침입니다.

---

## 템플릿 사용 방법

1. 배정된 CSV 파일을 열어 주세요.
2. 각 행의 `본문` 열을 읽어 주세요.
3. 다음 두 열에만 입력하세요.
   - `유머_존재여부`
   - `유머_유형`
4. 나머지 열은 절대 수정하지 마세요.
5. 열을 추가, 삭제, 이름 변경하지 마세요.

---

## 유머_존재여부

**허용 값:**

| 값 | 의미 |
|---|---|
| `humor` | 게시글에 의도적 유머 표현이 있음 |
| `non_humor` | 정보 전달, 홍보, 공지, 캠페인 안내 등 유머 표현이 없음 |
| `uncertain` | 유머 여부 판단이 애매함; 확신하기 어려움 |

**판단 기준:**

> "이 게시글은 의도적으로 웃기려 하는가?"

- 예 → `humor`
- 아니오 → `non_humor`
- 판단 불가 → `uncertain`

---

## 유머_유형

**허용 값:**

| 값 | 사용 조건 |
|---|---|
| `aggressive` | 특정 대상을 깎아내리거나, 조롱하거나, 공격적으로 놀리는 유머 |
| `affiliative` | 따뜻함, 유대감, 공동체 의식을 형성하는 유머 |
| `self_enhancing` | 상황의 우스꽝스러움을 즐기는 유머; 브랜드 자신이 상황을 웃음으로 승화 |
| `self_defeating` | 브랜드가 자기 자신을 희화화하는 자조적 유머 |
| `non_humorous` | `유머_존재여부` = `non_humor`일 때 사용 |
| `uncertain` | `유머_존재여부` = `uncertain`일 때 또는 유형 판단이 애매할 때 사용 |

**`유머_존재여부` 값에 따른 입력 규칙:**

```
유머_존재여부 = humor
  → aggressive / affiliative / self_enhancing / self_defeating 중 하나 입력

유머_존재여부 = non_humor
  → non_humorous 입력

유머_존재여부 = uncertain
  → uncertain 입력
```

---

## 핵심 구분: 기업 자신감 표현 vs. 공격적 유머

이것이 Fortune Top 100 코딩에서 가장 중요한 구분입니다.

**기업의 자신감 있는 언어는, 명확한 유머 단서와 특정 대상을 향한 조롱·비꼬기·로스트식 언어·놀림·비하가 동시에 있지 않는 한, `aggressive`로 코딩해서는 안 됩니다.**

| 특징 | 기업 자신감 표현 | 공격적 유머 |
|---|---|---|
| 어조 | 자신감 있고 단호함 | 농담·로스트·비꼬기 |
| 대상 | 없음 (자사 제품·서비스 언급) | 명확한 대상 (경쟁사, 기관 등) |
| 유머 단서 | 없음 | 명시적 농담 구조 또는 희극적 표현 |
| 예시 | "우리는 시장 1위입니다." | "미안, [경쟁사]야, 이번에도 우리가 이겼네 😏" |

**기본 규칙:** 명확한 농담이 없고 비웃음의 대상이 없다면 `aggressive`가 아닌 `non_humor`로 코딩하세요.

---

## 판단 불가 케이스

다음 상황에서는 `uncertain`을 사용하세요.

- 문화적 맥락이 필요한 유머 의도
- 가볍게 장난스럽지만 브랜드 개성인지 유머인지 모호한 경우
- 전체 본문을 읽은 뒤에도 판단이 어려운 경우

불확실할 때는 억지로 라벨을 붙이지 마세요.

---

## 참고 열 (수정 금지)

다음 열은 참고용으로 미리 채워져 있습니다. 수정하지 마세요.

- `웬디스_유머_존재여부` / `웬디스_유머_유형` — Wendy's 분류기 출력값
- `풀체인_유머_존재여부` / `풀체인_유머_유형` — full-chain 분류기 출력값
- `분류기_불일치` — 두 분류기가 다른 결과를 낸 경우 1
- `불확실성_점수` — 분류기 불확실성 (높을수록 판단이 어려운 게시글)
- `배정_코더` — 내 코더 배정 식별자 (수정 금지)
- `검토_상태` — 검토 완료 전: `pending` 유지. 완료 후: `complete`로 변경

---

## 입력값 요약표

| 열 이름 | 허용 값 |
|---|---|
| 유머_존재여부 | `humor` / `non_humor` / `uncertain` |
| 유머_유형 | `aggressive` / `affiliative` / `self_enhancing` / `self_defeating` / `non_humorous` / `uncertain` |

※ 입력값은 반드시 위 목록 중 하나를 **영문 소문자**로 입력하세요.
"""


def load_template() -> tuple[list[dict], list[str]]:
    for path in [TEMPLATE, CANDIDATES]:
        if path.exists():
            with path.open("r", encoding="utf-8", newline="") as f:
                reader = csv.DictReader(f)
                rows = list(reader)
                return rows, list(reader.fieldnames or [])
    raise FileNotFoundError("Neither template nor candidates file found.")


def build_fieldnames(source_fieldnames: list[str]) -> list[str]:
    priority_set = set(PRIORITY_COLS_KO)
    ref_set = set(REFERENCE_COLS_KO)

    # source cols not yet mapped or in priority
    leftover = []
    for src_col in source_fieldnames:
        ko = COL_MAP.get(src_col, src_col)
        if ko not in priority_set and ko not in ref_set:
            leftover.append(ko)

    ref_present = [c for c in REFERENCE_COLS_KO
                   if any(COL_MAP.get(s, s) == c for s in source_fieldnames)]

    return PRIORITY_COLS_KO + ref_present + leftover


def translate_row(row: dict) -> dict:
    """Map English source column names to Korean output column names."""
    return {COL_MAP.get(k, k): v for k, v in row.items()}


def main() -> None:
    print("=== build_coder_labeling_splits (한국어) ===")

    rows, source_fieldnames = load_template()
    print(f"  입력 행수: {len(rows)}")
    assert len(rows) == 1500, f"Expected 1500 rows, got {len(rows)}"

    cids = [r["candidate_id"] for r in rows]
    assert len(set(cids)) == len(cids), "Duplicate candidate_ids in input"

    rng = random.Random(RANDOM_SEED)
    rng.shuffle(rows)
    splits = {
        "coder1": rows[0:500],
        "coder2": rows[500:1000],
        "coder3": rows[1000:1500],
    }

    fieldnames = build_fieldnames(source_fieldnames)
    SPLITS_DIR.mkdir(parents=True, exist_ok=True)

    for coder, coder_rows in splits.items():
        out = SPLITS_DIR / f"{coder}_labeling_template.csv"
        with out.open("w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            w.writeheader()
            for row in coder_rows:
                row_ko = translate_row(row)
                row_ko["유머_존재여부"] = ""
                row_ko["유머_유형"] = ""
                row_ko["배정_코더"] = coder
                row_ko["검토_상태"] = "pending"
                w.writerow(row_ko)
        print(f"  {coder}: {len(coder_rows)}행 → {out.name}")

    # 코더별 요약
    by_coder_path = SPLITS_DIR / "coder_assignment_summary_by_coder.csv"
    with by_coder_path.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=[
            "배정_코더", "행수", "고유_후보ID수", "고유_트윗ID수", "비고",
        ])
        w.writeheader()
        all_cids: set = set()
        all_tids: set = set()
        overlap_cid = 0
        overlap_tid = 0
        for coder, coder_rows in splits.items():
            cids_set = {r["candidate_id"] for r in coder_rows}
            tids_set = {r["tweet_id"] for r in coder_rows}
            w.writerow({
                "배정_코더": coder,
                "행수": len(coder_rows),
                "고유_후보ID수": len(cids_set),
                "고유_트윗ID수": len(tids_set),
                "비고": "",
            })
            overlap_cid += len(cids_set & all_cids)
            overlap_tid += len(tids_set & all_tids)
            all_cids |= cids_set
            all_tids |= tids_set
        w.writerow({
            "배정_코더": "합계",
            "행수": 1500,
            "고유_후보ID수": len(all_cids),
            "고유_트윗ID수": len(all_tids),
            "비고": f"후보ID_중복={overlap_cid} 트윗ID_중복={overlap_tid}",
        })
    print(f"  코더별 요약 → {by_coder_path.name}")

    # 층화별 요약
    by_stratum_path = SPLITS_DIR / "coder_assignment_summary_by_stratum.csv"
    stratum_counts: dict[str, dict[str, int]] = defaultdict(
        lambda: {"coder1": 0, "coder2": 0, "coder3": 0}
    )
    for coder, coder_rows in splits.items():
        for r in coder_rows:
            stratum_counts[r.get("sampling_stratum", "unknown")][coder] += 1
    with by_stratum_path.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=["표본_층화", "코더1", "코더2", "코더3", "합계"])
        w.writeheader()
        for stratum, counts in sorted(stratum_counts.items()):
            total = sum(counts.values())
            w.writerow({
                "표본_층화": stratum,
                "코더1": counts["coder1"],
                "코더2": counts["coder2"],
                "코더3": counts["coder3"],
                "합계": total,
            })
    print(f"  층화별 요약 → {by_stratum_path.name}")

    guide_path = SPLITS_DIR / "LABELING_GUIDE.md"
    guide_path.write_text(LABELING_GUIDE_TEXT, encoding="utf-8")
    print(f"  라벨링 가이드 → {guide_path.name}")

    print("=== build_coder_labeling_splits COMPLETE ===")


if __name__ == "__main__":
    main()
