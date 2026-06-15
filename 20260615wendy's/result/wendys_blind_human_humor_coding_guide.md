# Wendy's 유머 여부 블라인드 코딩 가이드

작성일시: 2026-06-15 12:25 UTC

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
