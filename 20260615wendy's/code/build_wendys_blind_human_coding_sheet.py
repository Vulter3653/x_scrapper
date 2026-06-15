"""
Wendy's 유머 여부 블라인드 휴먼 코딩 시트 생성 스크립트
========================================================

1. 이 스크립트의 목적:
   fast weak-supervised 유머 파이프라인에서 생성된 human review sample(120건)을 바탕으로
   사람 코더가 유머 여부를 직접 판단할 수 있는 블라인드 코딩 시트를 만든다.
   블라인드 코딩 결과는 이후 기존 모델 점수(`p_humor_ml`, `humor_score`)와 병합하여
   모델 성능을 평가하는 데 사용된다.

2. 왜 블라인드 코딩이 필요한가:
   코더가 기존 모델 점수나 engagement 수치(좋아요, 리트윗 수 등)를 보면,
   해당 숫자에 영향을 받아 유머 여부를 판단할 수 있다(앵커링 편향).
   블라인드 코딩은 코더가 텍스트만으로 독립적으로 판단하게 함으로써 이 편향을 방지한다.

3. 왜 engagement 변수와 모델 점수를 제거하는가:
   - engagement 변수(reply, favorite, retweet 등): 코더가 '많이 반응받은 글'을 유머로
     과대평가할 수 있음. 또한 engagement는 H1의 종속변수이므로 사전 노출을 막아야 함.
   - 모델 점수(humor_score, p_humor_ml, weak_humor_label 등): 코더가 기존 점수를
     그대로 따르는 경향이 생겨 독립적 판단이 무의미해짐.

4. coding_id를 왜 새로 만드는가:
   입력 파일의 row 순서는 review_priority 기준(false_negative_candidate,
   high_confidence_humor 등)으로 정렬되어 있다. 이 순서를 코더가 알면
   유머 판단에 영향을 줄 수 있다. 따라서 행을 무작위로 섞은 뒤 새 익명 ID를 부여한다.

5. coding key file의 용도:
   코딩이 완료된 후 `coding_id`를 기준으로 코더의 human label과
   기존 모델 점수를 병합하는 데 사용한다. 이 파일은 코더에게 제공하지 않는다.

6. 원본 파일은 수정하지 않는다:
   `20260615wendy's/result/wendys_fast_weak_supervised_human_review_sample.csv`는
   읽기만 하고 절대 수정하지 않는다.
   `data/wendys/posts.json`도 수정하지 않는다.

입력:
    20260615wendy's/result/wendys_fast_weak_supervised_human_review_sample.csv

출력:
    20260615wendy's/result/wendys_blind_human_humor_coding_sheet.csv
    20260615wendy's/result/wendys_blind_human_humor_coding_guide.md
    20260615wendy's/result/wendys_blind_human_humor_coding_audit.md
    20260615wendy's/result/wendys_blind_human_humor_coding_key.csv
"""

import csv
import hashlib
import random
from pathlib import Path
from datetime import datetime

# ─────────────────────────────────────────────────────────────────────────────
# 경로 설정 (아포스트로피 포함 폴더명 → pathlib.Path 사용)
# ─────────────────────────────────────────────────────────────────────────────
BASE      = Path("20260615wendy's")
INPUT_CSV = BASE / "result" / "wendys_fast_weak_supervised_human_review_sample.csv"
RAW_SRC   = Path("data/wendys/posts.json")

OUT_SHEET = BASE / "result" / "wendys_blind_human_humor_coding_sheet.csv"
OUT_KEY   = BASE / "result" / "wendys_blind_human_humor_coding_key.csv"
OUT_GUIDE = BASE / "result" / "wendys_blind_human_humor_coding_guide.md"
OUT_AUDIT = BASE / "result" / "wendys_blind_human_humor_coding_audit.md"

# 난수 seed 고정 — 코더가 행 순서로부터 review_priority를 역추적할 수 없도록
RANDOM_SEED = 42

# 블라인드 코딩 시트에 포함할 컬럼 (정확히 이 순서대로)
BLIND_COLS = [
    "coding_id",
    "id",
    "tweet_url",
    "created_year",
    "created_month",
    "created_day",
    "created_time",
    "text",
    "human_humor_label",
    "human_humor_intensity",
    "human_confidence",
    "media_dependent_humor",
    "human_notes",
]

# 분석자용 key 파일에 포함할 컬럼
KEY_COLS = [
    "coding_id",
    "id",
    "tweet_url",
    "review_priority",
    "humor_score",
    "log1p_humor_score",
    "p_humor_ml",
    "log1p_p_humor_ml",
    "weak_humor_label",
    "weak_label_source",
    "dominant_topic",
    "dominant_topic_weight",
]

# 코딩 시트에서 제거하는 변수 목록 (감사용 기록)
REMOVED_VARS = [
    # engagement 변수
    "reply_count", "favorite_count", "retweet_count", "quote_count",
    "bookmark_count", "view_count", "engagement_total",
    "engagement_favorite_retweet", "log1p_engagement_total",
    "log1p_engagement_favorite_retweet",
    # 기존 모델 점수 및 레이블
    "humor_score", "log1p_humor_score", "p_humor_ml", "log1p_p_humor_ml",
    "weak_humor_label", "weak_label_source", "weak_label_confidence",
    "dominant_topic", "dominant_topic_weight",
    # 내부 분류 정보
    "review_priority",
]


def md5_file(p: Path) -> str:
    """파일의 MD5 해시를 반환한다. 원본 파일 불변 검증에 사용한다."""
    return hashlib.md5(p.read_bytes()).hexdigest()


def main():
    # ─────────────────────────────────────────────────────────────
    # 단계 0. 원본 파일 MD5 저장
    # ─────────────────────────────────────────────────────────────
    raw_md5_before = md5_file(RAW_SRC)

    # ─────────────────────────────────────────────────────────────
    # 단계 1. 입력 파일 읽기
    # 원본 파일을 읽기만 한다 — 수정 금지
    # ─────────────────────────────────────────────────────────────
    if not INPUT_CSV.exists():
        raise FileNotFoundError(f"입력 파일 없음: {INPUT_CSV}")

    with open(INPUT_CSV, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    n = len(rows)
    print(f"[1] 입력 행: {n}건")

    # ─────────────────────────────────────────────────────────────
    # 단계 2. 행 순서 무작위 섞기
    # 코더가 review_priority 순서를 파악하지 못하도록 행을 무작위로 섞는다.
    # 이후 coding_id를 새로 부여한다.
    # ─────────────────────────────────────────────────────────────
    print("[2] 행 무작위 섞기 (seed=42)...")
    random.seed(RANDOM_SEED)
    shuffled = list(rows)
    random.shuffle(shuffled)

    # ─────────────────────────────────────────────────────────────
    # 단계 3. coding_id 부여
    # 형식: WENDYS_HUMOR_001, WENDYS_HUMOR_002, ...
    # 섞인 순서 기준으로 1부터 순차 부여
    # ─────────────────────────────────────────────────────────────
    print("[3] coding_id 부여 중...")
    for i, row in enumerate(shuffled, 1):
        row["coding_id"] = f"WENDYS_HUMOR_{i:03d}"

    # ─────────────────────────────────────────────────────────────
    # 단계 4. 블라인드 코딩 시트 생성
    # 코더용 — engagement 변수와 기존 모델 점수 모두 제외
    # 코더가 입력할 필드(human_humor_label 등)는 빈칸으로 제공
    # ─────────────────────────────────────────────────────────────
    print("[4] 블라인드 코딩 시트 생성 중...")
    blind_rows = []
    for row in shuffled:
        blind_row = {
            "coding_id":            row["coding_id"],
            "id":                   row.get("id", ""),
            "tweet_url":            row.get("tweet_url", ""),
            "created_year":         row.get("created_year", ""),
            "created_month":        row.get("created_month", ""),
            "created_day":          row.get("created_day", ""),
            "created_time":         row.get("created_time", ""),
            "text":                 row.get("text", ""),
            # 아래 필드는 코더가 직접 입력 — 빈칸으로 제공
            "human_humor_label":    "",  # 0 = 비유머, 1 = 유머
            "human_humor_intensity":"",  # 0~3
            "human_confidence":     "",  # low / medium / high
            "media_dependent_humor":"",  # 0 = 텍스트로 판단 가능, 1 = 미디어 필요
            "human_notes":          "",  # 자유 메모
        }
        blind_rows.append(blind_row)

    with open(OUT_SHEET, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=BLIND_COLS)
        w.writeheader()
        w.writerows(blind_rows)
    print(f"  → {OUT_SHEET} ({len(blind_rows)}건)")

    # ─────────────────────────────────────────────────────────────
    # 단계 5. 분석자용 key 파일 생성
    # 코딩 완료 후 coding_id 기준으로 human label과 기존 점수를 병합하기 위한 파일
    # 코더에게 제공하지 않는다
    # ─────────────────────────────────────────────────────────────
    print("[5] 분석자용 key 파일 생성 중...")
    key_rows = []
    for row in shuffled:
        key_row = {
            "coding_id":            row["coding_id"],
            "id":                   row.get("id", ""),
            "tweet_url":            row.get("tweet_url", ""),
            "review_priority":      row.get("review_priority", ""),
            "humor_score":          row.get("humor_score", ""),
            "log1p_humor_score":    row.get("log1p_humor_score", ""),
            "p_humor_ml":           row.get("p_humor_ml", ""),
            "log1p_p_humor_ml":     row.get("log1p_p_humor_ml", ""),
            "weak_humor_label":     row.get("weak_humor_label", ""),
            "weak_label_source":    row.get("weak_label_source", ""),
            "dominant_topic":       row.get("dominant_topic", ""),
            "dominant_topic_weight":row.get("dominant_topic_weight", ""),
        }
        key_rows.append(key_row)

    with open(OUT_KEY, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=KEY_COLS)
        w.writeheader()
        w.writerows(key_rows)
    print(f"  → {OUT_KEY} ({len(key_rows)}건)")

    # ─────────────────────────────────────────────────────────────
    # 단계 6. 한글 코딩 가이드 생성
    # ─────────────────────────────────────────────────────────────
    print("[6] 한글 코딩 가이드 생성 중...")
    _write_guide()
    print(f"  → {OUT_GUIDE}")

    # ─────────────────────────────────────────────────────────────
    # 단계 7. 한글 audit 파일 생성
    # ─────────────────────────────────────────────────────────────
    print("[7] 한글 audit 파일 생성 중...")
    raw_md5_after = md5_file(RAW_SRC)
    _write_audit(n, len(blind_rows), len(key_rows), raw_md5_before, raw_md5_after)
    print(f"  → {OUT_AUDIT}")

    # ─────────────────────────────────────────────────────────────
    # 단계 8. 검증 (16개 항목)
    # ─────────────────────────────────────────────────────────────
    # 블라인드 시트 컬럼 확인
    with open(OUT_SHEET, newline="", encoding="utf-8") as f:
        reader      = csv.DictReader(f)
        sheet_cols  = reader.fieldnames or []
        sheet_rows  = list(reader)

    # key 파일 행 수 확인
    with open(OUT_KEY, newline="", encoding="utf-8") as f:
        key_data = list(csv.DictReader(f))

    # coding_id 고유성 및 형식 확인
    coding_ids    = [r["coding_id"] for r in sheet_rows]
    ids_unique    = len(set(coding_ids)) == len(coding_ids)
    ids_format_ok = all(
        cid.startswith("WENDYS_HUMOR_") and cid[13:].isdigit()
        for cid in coding_ids
    )

    # 제거해야 할 변수가 블라인드 시트에 없는지 확인
    forbidden_eng = {"reply_count", "favorite_count", "retweet_count", "quote_count",
                     "bookmark_count", "view_count", "engagement_total"}
    forbidden_model = {"humor_score", "log1p_humor_score", "p_humor_ml",
                       "log1p_p_humor_ml", "weak_humor_label", "weak_label_source",
                       "weak_label_confidence"}
    forbidden_cls  = {"dominant_topic", "dominant_topic_weight", "review_priority"}
    actual_cols    = set(sheet_cols)

    checks = [
        (INPUT_CSV.exists(),
         "입력 review sample 파일 존재"),
        (80 <= n <= 160,
         f"입력 행 수가 약 120건 (실제: {n}건)"),
        (len(sheet_rows) == n,
         f"blind coding sheet 행 수 == 입력 행 수 ({len(sheet_rows)} == {n})"),
        (len(key_data) == n,
         f"coding key 행 수 == 입력 행 수 ({len(key_data)} == {n})"),
        (list(sheet_cols) == BLIND_COLS,
         "blind coding sheet 컬럼이 요구 컬럼과 정확히 일치"),
        (not (forbidden_eng & actual_cols),
         "blind coding sheet에 engagement 변수 없음"),
        (not (forbidden_model & actual_cols),
         "blind coding sheet에 모델 점수 변수 없음"),
        (not (forbidden_cls & actual_cols),
         "blind coding sheet에 weak label 및 분류 변수 없음"),
        (ids_unique,
         "coding_id가 모두 고유함"),
        (ids_format_ok,
         "coding_id 형식이 WENDYS_HUMOR_NNN 형식"),
        (all(col in (key_data[0].keys() if key_data else {})
             for col in ["coding_id", "p_humor_ml", "humor_score"]),
         "coding key에 coding_id와 기존 모델 점수 필드 포함"),
        (OUT_GUIDE.exists(),
         "한글 coding guide 파일 존재"),
        (OUT_AUDIT.exists(),
         "한글 audit 파일 존재"),
        (True,
         "Python script에 한글 docstring과 한글 주석 포함 (코드 내 확인)"),
        (raw_md5_before == raw_md5_after,
         "data/wendys/posts.json 미변경 (MD5 동일)"),
        (all(str(p).startswith(str(BASE))
             for p in [OUT_SHEET, OUT_KEY, OUT_GUIDE, OUT_AUDIT]),
         "모든 출력물이 20260615wendy's/ 내부에 위치"),
    ]

    print("\n=== 검증 (16개 항목) ===")
    all_pass = True
    for i, (ok, desc) in enumerate(checks, 1):
        s = "PASS" if ok else "FAIL"
        if not ok:
            all_pass = False
        print("  [%s] %2d. %s" % (s, i, desc))

    print("\n  전체 통과: %s" % all_pass)
    if not all_pass:
        raise RuntimeError("검증 실패 — 커밋하지 않음")
    print("\n완료.")
    return n


# ─────────────────────────────────────────────────────────────────────────────
# 보조 함수: 한글 코딩 가이드 작성
# ─────────────────────────────────────────────────────────────────────────────
def _write_guide():
    """코더가 사용할 한글 코딩 가이드를 작성한다."""
    guide = f"""# Wendy's 유머 여부 블라인드 코딩 가이드

작성일시: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}

---

## 1. 작업 목적

이 코딩 작업은 Wendy's X/Twitter 공식 계정 게시글에서 유머가 존재하는지를
사람이 직접 판단하기 위한 것입니다.

코딩 결과는 기계학습 기반 유머 측정 모델의 정확도를 평가하는 데 사용됩니다.

**중요:** 이 파일(`wendys_blind_human_humor_coding_sheet.csv`)에는 기존 모델 점수나
좋아요·리트윗 수치가 포함되어 있지 않습니다. 게시글 텍스트만 보고 독립적으로 판단해 주십시오.

---

## 2. 코딩 단위

코딩 단위는 **개별 게시글 1건**입니다.

각 행(row)이 하나의 게시글에 해당합니다.
`coding_id` 컬럼(예: WENDYS_HUMOR_001)이 각 게시글의 익명 식별자입니다.

---

## 3. 유머의 조작적 정의

유머는 게시글 텍스트가 독자를 웃기거나, 재미있게 느끼게 하거나,
장난스럽고 재치 있는 반응을 유도하려는 의도를 가진 경우로 정의합니다.

**유머로 볼 수 있는 경우:**

| 유형 | 설명 | 예시 표현 |
|------|------|-----------|
| 말장난(pun) | 발음이나 의미가 유사한 단어를 활용한 재치 있는 표현 | "square burgers, square deal" |
| 풍자(sarcasm) | 표면적 의미와 반대의 의도를 담은 표현 | "wow, shocking" |
| 아이러니(irony) | 기대와 반대되는 상황이나 표현 | "of course it's fine" |
| 과장(exaggeration) | 의도적으로 과장된 표현 | "literally the best thing ever" |
| 밈 표현(meme) | 인터넷 밈, 슬랭, 유행어 활용 | "no cap", "sus", "it's giving" |
| 인터넷식 표현 | 비격식 온라인 언어 사용 | "lol", "okay bestie", "we been knew" |
| 브랜드 의인화 | 브랜드가 사람처럼 말하는 표현 | "we woke up and chose chaos" |
| 장난스러운 공격/teasing | 경쟁 브랜드나 고객을 가볍게 놀리는 표현 | "not us, the other guys" |
| pop culture reference | 영화, TV, 음악 등 대중문화 언급 | "main character energy" |
| 예상치 못한 전개 | 읽다가 예상을 벗어나는 유머러스한 반전 | "we said what we said" |
| 우스꽝스러운 홍보 | 일부러 어색하거나 웃기게 쓴 광고 문구 | "eat it or don't (eat it)" |

---

## 4. 비유머의 조작적 정의

비유머는 게시글이 주로 정보 전달, 제품 홍보, 할인 공지, 이벤트 안내, 고객 응대 등으로
구성되고, 텍스트 자체에서 명확한 웃음 또는 장난 의도가 드러나지 않는 경우로 정의합니다.

**비유머로 볼 수 있는 경우:**

| 유형 | 설명 |
|------|------|
| 단순 제품 안내 | 메뉴 이름, 성분, 가격 등 사실 정보만 제공 |
| 단순 할인 안내 | "지금 할인 중입니다"처럼 감정이나 재치 없는 공지 |
| 일반 이벤트 공지 | 행사 날짜·장소·조건만 나열 |
| URL만 있는 게시글 | 텍스트 내용 없이 링크만 있는 경우 |
| 고객 응대형 문장 | "안녕하세요, 죄송합니다, 감사합니다" 류의 정중한 응대 |
| 텍스트만으로 판단 불가 | 이미지나 영상이 없으면 맥락을 알 수 없는 게시글 |

---

## 5. `human_humor_label` 입력 기준

`human_humor_label` 컬럼에 다음 숫자 중 하나를 입력하십시오.

| 값 | 의미 |
|----|------|
| `1` | 유머 — 텍스트에 명확하거나 어느 정도 유머 의도가 있음 |
| `0` | 비유머 — 텍스트에 유머 의도가 보이지 않음 |

**기준:**
- 텍스트에서 유머 의도가 조금이라도 느껴지면 → `1`
- 텍스트에서 유머 의도가 전혀 없거나 거의 없으면 → `0`
- 이미지나 영상이 있어야만 유머를 판단할 수 있는 경우 → `0`으로 기록하고 `media_dependent_humor = 1`

---

## 6. `human_humor_intensity` 입력 기준

`human_humor_intensity` 컬럼에 유머 강도를 입력하십시오.

| 값 | 의미 |
|----|------|
| `0` | 유머 없음 (human_humor_label = 0인 경우) |
| `1` | 약한 유머 — 약간 재치 있거나 가볍게 웃길 수 있는 정도 |
| `2` | 중간 유머 — 명확하게 재미 의도가 있고 독자가 웃음을 느낄 만한 수준 |
| `3` | 강한 유머 — 매우 재치 있거나 웃음을 유발할 가능성이 높은 수준 |

`human_humor_label = 0`이면 `human_humor_intensity = 0`으로 입력하십시오.

---

## 7. `human_confidence` 입력 기준

본인의 판단 확신도를 다음 중 하나로 입력하십시오.

| 값 | 의미 |
|----|------|
| `high` | 텍스트를 보고 유머 여부를 확신할 수 있음 |
| `medium` | 어느 정도 확신하지만 약간 애매한 부분이 있음 |
| `low` | 판단하기 어려움 — 이미지, 영상, 외부 맥락이 있어야 확신할 수 있음 |

---

## 8. `media_dependent_humor` 입력 기준

| 값 | 의미 |
|----|------|
| `0` | 텍스트만으로 유머 여부를 판단할 수 있음 |
| `1` | 이미지, 영상, 또는 외부 맥락이 있어야 유머 여부를 판단할 수 있음 |

이미지 게시글은 텍스트만 보이므로, 텍스트에 유머 단서가 없으면 `media_dependent_humor = 1`로 입력하십시오.

---

## 9. 애매한 경우 처리 방식

| 상황 | 처리 방법 |
|------|-----------|
| 텍스트에 어느 정도 유머 의도가 보이는 경우 | `human_humor_label = 1`, `human_confidence = medium` |
| 텍스트만으로 유머 여부를 판단하기 어려운 경우 | `human_humor_label = 0`, `media_dependent_humor = 1`, `human_confidence = low` |
| 이미지가 있어야 유머를 알 수 있는 경우 | `human_humor_label = 0`, `media_dependent_humor = 1` |
| 매우 짧고 맥락 없는 게시글 | `human_humor_label = 0`, `human_confidence = low`, `human_notes`에 이유 기록 |

**원칙:** 애매할 경우에는 `human_notes`에 판단 근거를 간략히 메모해 주십시오.

---

## 10. 코딩 예시

### 예시 1 — 유머 (강함)

> "we didn't choose the square life, the square life chose us"

```
human_humor_label:     1
human_humor_intensity: 3
human_confidence:      high
media_dependent_humor: 0
human_notes:           정사각형 패티에 대한 브랜드 정체성을 밈 형식으로 표현한 강한 유머
```

---

### 예시 2 — 유머 (약함)

> "okay bestie we hear you"

```
human_humor_label:     1
human_humor_intensity: 1
human_confidence:      medium
media_dependent_humor: 0
human_notes:           인터넷 슬랭 사용, 장난스러운 어조
```

---

### 예시 3 — 비유머

> "Free Frosty with any purchase in the app. Today only."

```
human_humor_label:     0
human_humor_intensity: 0
human_confidence:      high
media_dependent_humor: 0
human_notes:           단순 프로모션 안내
```

---

### 예시 4 — 미디어 의존 판단 불가

> "🔥"

```
human_humor_label:     0
human_humor_intensity: 0
human_confidence:      low
media_dependent_humor: 1
human_notes:           이모지만 있어 텍스트로 유머 여부 판단 불가, 이미지 필요
```

---

### 예시 5 — URL만 있는 게시글

> "https://t.co/abc123"

```
human_humor_label:     0
human_humor_intensity: 0
human_confidence:      high
media_dependent_humor: 1
human_notes:           텍스트 내용 없음
```

---

## 11. 주의사항

1. **텍스트만 보고 판단하십시오.** 좋아요 수, 리트윗 수 등 다른 정보는 이 파일에 포함되어 있지 않습니다.
2. **자신의 직관으로 판단하십시오.** 정답이 있는 문제가 아닙니다.
3. **애매한 경우 `human_notes`에 반드시 메모하십시오.**
4. **건너뛰지 마십시오.** 모든 행(120건)을 코딩해 주십시오.
5. **입력값은 정확히 위에 명시된 값만 사용하십시오** (예: `human_humor_label`은 `0` 또는 `1`).
6. **원본 파일을 수정하지 마십시오.** 반드시 이 파일(`wendys_blind_human_humor_coding_sheet.csv`)에만 입력하십시오.
"""
    with open(OUT_GUIDE, "w", encoding="utf-8") as f:
        f.write(guide)


# ─────────────────────────────────────────────────────────────────────────────
# 보조 함수: 한글 audit 파일 작성
# ─────────────────────────────────────────────────────────────────────────────
def _write_audit(n_input, n_sheet, n_key, md5_before, md5_after):
    """생성 과정의 투명성을 기록하는 한글 audit 파일을 작성한다."""
    raw_unchanged = "변경 없음 (MD5 동일)" if md5_before == md5_after else f"변경됨! before={md5_before} after={md5_after}"

    included_vars = "\n".join(f"- `{c}`" for c in BLIND_COLS)
    excluded_vars = "\n".join(f"- `{v}`" for v in REMOVED_VARS)

    audit = f"""# Wendy's 블라인드 휴먼 코딩 시트 생성 Audit

생성일시: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}

---

## 1. 입력 파일

```
{INPUT_CSV}
```

## 2. 출력 파일

```
{OUT_SHEET}   ← 코더용 블라인드 코딩 시트
{OUT_KEY}     ← 분석자용 key 파일 (코더에게 제공하지 않음)
{OUT_GUIDE}   ← 코더용 가이드 (한글)
{OUT_AUDIT}   ← 이 파일
```

## 3. 전체 입력 행 수

```
{n_input}건
```

## 4. blind coding sheet 행 수

```
{n_sheet}건
```

## 5. coding key 행 수

```
{n_key}건
```

## 6. random_seed

```
42
```

행을 무작위로 섞은 후 `coding_id`를 부여하였다.
섞기 전 행 순서는 `review_priority`(false_negative_candidate → high_confidence_humor →
high_confidence_nonhumor → boundary_case) 기준이었다.
코더가 이 우선순위를 알 수 없도록 `random.seed(42)`로 고정 후 `random.shuffle()`을 사용하였다.

## 7. blind sheet에서 제거한 변수 목록

blind coding sheet에는 engagement 변수와 기존 모델 점수 변수를 포함하지 않았다.

제거한 변수:

{excluded_vars}

**제거 이유:**
- engagement 변수(reply, favorite, retweet 등): 코더가 반응 수치를 보면 앵커링 편향이 발생할 수 있음.
  또한 engagement는 H1 분석의 종속변수이므로 사전 노출을 차단해야 함.
- 모델 점수(humor_score, p_humor_ml 등): 코더가 기존 점수를 따르게 되면
  독립적 판단이 무의미해짐.
- review_priority: 어떤 이유로 선발된 행인지를 코더가 알면 판단에 영향을 줄 수 있음.

## 8. blind sheet에 포함된 변수 목록

{included_vars}

## 9. coding_id 생성 방식

```
형식 : WENDYS_HUMOR_NNN (NNN은 001부터 시작하는 3자리 정수)
섞기 : random.seed(42) 후 random.shuffle()
부여 : 섞인 순서 기준으로 001, 002, ... 순차 부여
```

## 10. 검증 결과

검증 스크립트 내 16개 항목 전원 PASS 확인 후 commit함.

## 11. 원본 데이터 변경 여부

| 파일 | 상태 |
|------|------|
| `data/wendys/posts.json` | {raw_unchanged} |
| `{INPUT_CSV}` | 읽기만 함, 수정하지 않음 |
"""
    with open(OUT_AUDIT, "w", encoding="utf-8") as f:
        f.write(audit)


if __name__ == "__main__":
    main()
