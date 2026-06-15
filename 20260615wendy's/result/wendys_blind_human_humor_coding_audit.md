# Wendy's 블라인드 휴먼 코딩 시트 생성 Audit

생성일시: 2026-06-15 12:25 UTC

---

## 1. 입력 파일

```
20260615wendy's/result/wendys_fast_weak_supervised_human_review_sample.csv
```

## 2. 출력 파일

```
20260615wendy's/result/wendys_blind_human_humor_coding_sheet.csv   ← 코더용 블라인드 코딩 시트
20260615wendy's/result/wendys_blind_human_humor_coding_key.csv     ← 분석자용 key 파일 (코더에게 제공하지 않음)
20260615wendy's/result/wendys_blind_human_humor_coding_guide.md   ← 코더용 가이드 (한글)
20260615wendy's/result/wendys_blind_human_humor_coding_audit.md   ← 이 파일
```

## 3. 전체 입력 행 수

```
120건
```

## 4. blind coding sheet 행 수

```
120건
```

## 5. coding key 행 수

```
120건
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

- `reply_count`
- `favorite_count`
- `retweet_count`
- `quote_count`
- `bookmark_count`
- `view_count`
- `engagement_total`
- `engagement_favorite_retweet`
- `log1p_engagement_total`
- `log1p_engagement_favorite_retweet`
- `humor_score`
- `log1p_humor_score`
- `p_humor_ml`
- `log1p_p_humor_ml`
- `weak_humor_label`
- `weak_label_source`
- `weak_label_confidence`
- `dominant_topic`
- `dominant_topic_weight`
- `review_priority`

**제거 이유:**
- engagement 변수(reply, favorite, retweet 등): 코더가 반응 수치를 보면 앵커링 편향이 발생할 수 있음.
  또한 engagement는 H1 분석의 종속변수이므로 사전 노출을 차단해야 함.
- 모델 점수(humor_score, p_humor_ml 등): 코더가 기존 점수를 따르게 되면
  독립적 판단이 무의미해짐.
- review_priority: 어떤 이유로 선발된 행인지를 코더가 알면 판단에 영향을 줄 수 있음.

## 8. blind sheet에 포함된 변수 목록

- `coding_id`
- `id`
- `tweet_url`
- `created_year`
- `created_month`
- `created_day`
- `created_time`
- `text`
- `human_humor_label`
- `human_humor_intensity`
- `human_confidence`
- `media_dependent_humor`
- `human_notes`

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
| `data/wendys/posts.json` | 변경 없음 (MD5 동일) |
| `20260615wendy's/result/wendys_fast_weak_supervised_human_review_sample.csv` | 읽기만 함, 수정하지 않음 |
