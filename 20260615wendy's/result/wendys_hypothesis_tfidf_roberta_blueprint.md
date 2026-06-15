# Wendy’s TF-IDF 기반 H1-H3 검증 청사진 및 RoBERTa/BERTweet 보조모델 기록

생성 목적: 현재 Wendy’s 데이터에서 `final_humor_binary` 기반 유머 유무 분류를 우선 TF-IDF + Logistic Regression으로 안정화하고, 이후 H1-H3를 순차적으로 검증한다. RoBERTa/BERTweet는 현재 라벨 수 기준으로 실행 가능하지만, 주 분석 모델이 아니라 보조 검증 또는 robustness 모델로 후순위 적용한다.

---

## 1. 현재 방법론 판단 기록

현재 `wendys_humor_review_sheet.csv`에는 사람 코더 및 기존 human label을 우선순위 규칙으로 병합한 최종 유머 유무 라벨이 포함되어 있다.

핵심 라벨:

```text
final_humor_binary
final_humor_source
final_humor_label_available
```

현재 기준:

```text
final_humor_binary = 1 → 유머
final_humor_binary = 0 → 비유머
final_humor_label_available = 1 → 사람 기반 최종 라벨 사용 가능
```

라벨 유효 표본은 전체 978건 중 597건이며, 유머 309건 / 비유머 288건으로 균형이 비교적 양호하다. 따라서 TF-IDF + Logistic Regression으로 유머 유무 분류 모델을 먼저 학습·검증하는 것이 적절하다.

RoBERTa/BERTweet에 대한 판단은 다음과 같다.

```text
과거 68건 또는 168건 라벨 단계:
RoBERTa/BERTweet fine-tuning은 과적합 위험이 커서 후순위 또는 비추천

현재 597건 final_humor_binary 단계:
RoBERTa/BERTweet 실험 가능
다만 주 분석 모델이 아니라 TF-IDF baseline 이후 보조 검증 모델로 사용
```

즉, 현재 전략은 다음으로 고정한다.

```text
1순위: TF-IDF + Logistic Regression
2순위: RoBERTa/BERTweet frozen embedding + Logistic Regression robustness
3순위: 필요 시 RoBERTa/BERTweet fine-tuning optional robustness
```

RoBERTa/BERTweet를 사용할 경우에도 학습 입력은 반드시 다음으로 제한한다.

```text
X = text
y = final_humor_binary
```

다음 변수는 모델 학습에 사용하지 않는다.

```text
model_humor
p_humor
humor_score_rule
p_humor_ml
final_humor_source
reply_count
favorite_count
retweet_count
quote_count
bookmark_count
view_count
engagement 관련 변수
```

---

## 2. 전체 분석 원칙

이번 단계의 목적은 “유의성을 억지로 만드는 것”이 아니라, 사람 코딩 결과를 반영한 텍스트 기반 유머 측정값을 안정화한 뒤 H1-H3를 순차적으로 검증하는 것이다.

분석 원칙:

```text
1. 유머 측정값은 engagement 변수를 사용하지 않고 text만으로 생성한다.
2. H1-H3 검증에서 engagement는 종속변수로만 사용한다.
3. 모든 결과는 관측적 연관성으로 해석한다.
4. 인과관계를 주장하지 않는다.
5. Wendy’s 단일 브랜드 분석이므로 브랜드 고정효과는 포함하지 않는다.
6. 단순 분석 → 통제 분석 → robustness 순서로 진행한다.
```

---

## 3. 핵심 데이터 구조

입력 기준 파일:

```text
20260615wendy's/result/wendys_humor_review_sheet.csv
```

주요 라벨:

```text
final_humor_binary
final_humor_source
final_humor_label_available
```

유머 유무 분류 모델 산출 예정 변수:

```text
p_humor_final_tfidf_logreg
pred_humor_final_050
log1p_p_humor_final_tfidf_logreg
```

유머 타입 분류를 위한 향후 후보 변수:

```text
coder1_type
human_type
coder2_type
final_humor_type
final_humor_type_source
final_humor_type_available
```

주요 engagement 변수:

```text
engagement_total = reply_count + favorite_count + retweet_count + quote_count + bookmark_count
engagement_favorite_retweet = favorite_count + retweet_count
log1p_engagement_total = log(1 + engagement_total)
log1p_engagement_favorite_retweet = log(1 + engagement_favorite_retweet)
```

---

## 4. H1 검증 청사진: 유머 유무와 engagement

### 4.1 가설

```text
H1: Wendy’s 브랜드 게시글에서 유머 존재 수준이 높을수록 post-level engagement가 높을 것이다.
```

### 4.2 측정

주요 IV:

```text
log1p_p_humor_final_tfidf_logreg
```

대안 IV:

```text
pred_humor_final_050
final_humor_binary  # labeled sample t-test 및 labeled-only 분석용
```

주요 DV:

```text
log1p_engagement_total
```

보조 DV:

```text
log1p_engagement_favorite_retweet
log1p_favorite_count
log1p_retweet_count
log1p_reply_count
log1p_quote_count
log1p_bookmark_count
```

### 4.3 1차 분석

단순 OLS:

```text
log1p_engagement_total_i
= α + β log1p_p_humor_final_tfidf_logreg_i + ε_i
```

해석 기준:

```text
β > 0 and p < .05 → H1 예비적 지지
β > 0 and p ≥ .05 → H1 방향성 지지
β ≤ 0 → H1 지지 없음
```

### 4.4 labeled sample t-test

사람 라벨이 있는 597건에서 다음 비교를 수행한다.

```text
유머(final_humor_binary=1) vs 비유머(final_humor_binary=0)
```

검정:

```text
Welch’s independent samples t-test
```

중심 결과:

```text
log1p_engagement_total
log1p_engagement_favorite_retweet
log1p_favorite_count
log1p_retweet_count
```

### 4.5 통제 OLS 확장

단순 OLS 이후 통제 분석을 수행한다.

```text
log1p_engagement_total_i
= α
+ β log1p_p_humor_final_tfidf_logreg_i
+ γ1 log1p_text_length_i
+ γ2 url_count_i
+ γ3 hashtag_count_i
+ γ4 mention_count_i
+ γ5 is_quote_status_i
+ γ6 is_retweet_text_i
+ δ_year
+ λ_month
+ ε_i
```

Wendy’s 단일 브랜드 분석이므로 브랜드 고정효과는 포함하지 않는다.

---

## 5. H2 검증 청사진: aggressive humor의 상대적 효과

### 5.1 가설

```text
H2: Aggressive humor는 다른 유머 유형보다 post-level engagement와 더 강한 양의 연관성을 가질 것이다.
```

### 5.2 전제

H2는 유머 유무 분류가 아니라 유머 타입 분류가 필요하다. 따라서 H1용 유머 유무 모델이 안정화된 후 타입 라벨을 구성한다.

최종 타입 라벨 생성 규칙:

```text
final_humor_source = coder1 → final_humor_type = coder1_type
final_humor_source = human  → final_humor_type = human_type
final_humor_source = coder2 → final_humor_type = coder2_type
```

철자 및 값 정규화:

```text
affliative → affiliative
agressive → aggressive
none / non_humor / blank → non_humor 또는 missing
```

### 5.3 H2 핵심 변수

```text
aggressive_humor_binary = 1 if final_humor_type == aggressive else 0
other_humor_binary = 1 if final_humor_binary == 1 and final_humor_type != aggressive else 0
non_humor = reference category
```

필요 시 텍스트 모델로 다음 확률을 생성한다.

```text
p_aggressive_final_tfidf_logreg
pred_aggressive_final_050
```

단, 타입별 표본 수가 충분한지 먼저 확인한다.

### 5.4 H2 기본 회귀식

전체 표본 기준:

```text
log1p_engagement_total_i
= α
+ β1 aggressive_humor_i
+ β2 other_humor_i
+ ε_i
```

해석:

```text
β1 > 0 → aggressive humor는 non-humor보다 engagement가 높음
β2 > 0 → other humor는 non-humor보다 engagement가 높음
β1 > β2 → aggressive humor가 other humor보다 더 강한 연관성
```

H2의 핵심 검정:

```text
H0: β1 = β2
H2: β1 > β2
```

실무적으로는 다음 두 분석을 병행한다.

```text
1. 전체 표본: non-humor를 기준범주로 aggressive vs other humor 비교
2. humor-only 표본: aggressive humor vs non-aggressive humor 비교
```

Humor-only 식:

```text
log1p_engagement_total_i
= α + β aggressive_humor_i + ε_i
```

β > 0이면 aggressive humor가 다른 유머보다 engagement가 높다는 방향이다.

### 5.5 통제 확장

```text
log1p_engagement_total_i
= α
+ β1 aggressive_humor_i
+ β2 other_humor_i
+ controls_i
+ δ_year
+ λ_month
+ ε_i
```

---

## 6. H3 검증 청사진: aggressive humor usage intensity의 역 U자형 조절효과

### 6.1 가설

```text
H3: Aggressive humor usage intensity는 aggressive humor와 post-level engagement의 관계를 역 U자형으로 조절할 것이다.
```

해석:

```text
낮은 수준에서 중간 수준까지 aggressive humor usage intensity가 증가할수록 aggressive humor의 engagement 효과는 강화되지만, 일정 수준 이후에는 그 효과가 약화될 것이다.
```

### 6.2 Wendy’s 단일 브랜드에서 intensity 정의

Wendy’s 단일 브랜드에서는 firm-level cross-sectional intensity를 사용할 수 없다. 따라서 시간 단위별 usage intensity를 사용한다.

권장 단위:

```text
year-month 또는 quarter
```

단, 월별 post 수가 너무 적으면 quarter를 사용한다.

Aggressive humor usage intensity:

```text
aggressive_intensity_t
= period t의 aggressive humor posts 수 / period t의 전체 posts 수
```

기계적 상관을 줄이기 위해 leave-one-out intensity도 생성한다.

```text
aggressive_intensity_loo_i
= 같은 period 내에서 post i를 제외하고 계산한 aggressive humor 비율
```

### 6.3 H3 핵심 변수

```text
aggressive_humor_i
aggressive_intensity_loo_i
aggressive_intensity_loo_sq_i = aggressive_intensity_loo_i^2
```

### 6.4 H3 기본 모형

```text
log1p_engagement_total_i
= α
+ β1 aggressive_humor_i
+ β2 aggressive_intensity_loo_i
+ β3 aggressive_intensity_loo_sq_i
+ β4 aggressive_humor_i × aggressive_intensity_loo_i
+ β5 aggressive_humor_i × aggressive_intensity_loo_sq_i
+ ε_i
```

역 U자형 조절효과의 핵심은 다음이다.

```text
β4 > 0
β5 < 0
```

즉, aggressive humor의 효과가 intensity 증가 초반에는 강화되지만, 높은 intensity에서는 약화되는 패턴이다.

### 6.5 H3의 현실적 제약

H3는 H1/H2보다 훨씬 어렵다.

필요 조건:

```text
1. aggressive type label이 충분해야 함
2. period별 aggressive intensity가 충분히 변동해야 함
3. period별 post 수가 너무 적으면 intensity가 불안정함
4. 단일 브랜드 분석이므로 일반화가 제한됨
```

따라서 H3는 바로 본 분석으로 주장하지 말고 다음 순서로 접근한다.

```text
1. aggressive label 수 확인
2. period별 aggressive_intensity 분포 확인
3. 0이 과도하게 많으면 H3는 탐색적 분석으로 제한
4. quadratic 및 interaction 결과를 방향성 중심으로 보고
```

---

## 7. TF-IDF 분석 완료 후 RoBERTa/BERTweet 고려 절차

TF-IDF 기반 H1-H3 분석을 먼저 완료한 뒤, 다음 조건에서 RoBERTa/BERTweet를 고려한다.

### 7.1 적용 조건

```text
1. final_humor_binary 기준 TF-IDF 모델 성능이 충분히 보고됨
2. H1 결과가 TF-IDF 기준으로 정리됨
3. H2/H3를 위한 type label 분포가 확인됨
4. RoBERTa/BERTweet 실행 환경이 감당 가능함
```

### 7.2 우선 방식

Full fine-tuning보다 먼저 frozen embedding 방식을 사용한다.

```text
BERTweet 또는 Twitter-RoBERTa embedding 추출
→ Logistic Regression 학습
→ 5-fold CV
→ 전체 978건 예측
→ TF-IDF 결과와 비교
```

### 7.3 비교 기준

```text
CV F1
CV ROC-AUC
OOF confusion matrix
전체 humor 예측 비율
TF-IDF와 RoBERTa/BERTweet 예측 일치율
불일치 사례 audit
H1 결과 유지 여부
```

### 7.4 활용 위치

RoBERTa/BERTweet는 다음처럼 위치시킨다.

```text
주 분석: TF-IDF + Logistic Regression
보조 검증: BERTweet/Twitter-RoBERTa embedding classifier
선택적 robustness: full fine-tuning
```

---

## 8. 실행 순서

현재 우선순위는 다음으로 고정한다.

```text
1. final_humor_binary 기반 유머 유무 TF-IDF 분류 모델 완성
2. H1: 유머 유무와 engagement 관계 검증
3. final_humor_type 생성 및 타입별 표본 수 점검
4. H2: aggressive humor vs other humor 비교
5. H3: aggressive humor usage intensity의 역 U자형 조절효과 탐색
6. TF-IDF 결과 고정 후 RoBERTa/BERTweet 보조 검증 고려
```

---

## 9. 보고 원칙

보고 문장에서는 다음 표현을 사용한다.

```text
유머 가능성이 높은 게시글일수록 engagement가 높게 나타났다.
유머 게시글은 비유머 게시글보다 engagement가 높게 나타났다.
```

다음 표현은 사용하지 않는다.

```text
유머가 engagement를 증가시켰다.
유머가 engagement의 원인이다.
```

최종적으로 H1-H3는 모두 관측적 연관성 분석으로 보고한다.
