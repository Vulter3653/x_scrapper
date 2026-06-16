# Wendy's H3 Step 1 Quadratic Intensity Direct Test — 분석 요약

## 1. 분석 목적
Wendy's H3 분석의 1단계로, 전체 데이터 기반 model-based intensity 변수를 사용하여 humor usage intensity와 post-level engagement 간 역 U자형 관계가 존재하는지 확인한다.

## 2. H3 가설
H3: Wendy's의 humor usage intensity는 post-level engagement와 역 U자형 관계를 가질 것이다. 즉, 낮은 수준에서 중간 수준까지는 engagement가 증가하지만, 일정 수준을 넘어서면 engagement가 감소할 것이다.

## 3. H3-pre와 H3-main 구분
- **H3-pre**: general humor usage intensity (humor_proportion_quarter_loo)의 역 U자형 관계
- **H3-main**: aggressive humor usage intensity (aggressive_humor_proportion_quarter_loo)의 역 U자형 관계

## 4. 사용한 파일
- H3-pre: `wendys_humor_frequency_proportion_post_level_dataset.csv`
- H3-main: `wendys_h3_aggressive_vs_other_intensity_dataset.csv`

## 5. 원본 posts.json 변경 없음 확인
data/wendys/posts.json 원본 파일은 수정하지 않았다. 분석은 기존 파생 파일만 사용한다.

## 6. 새 통제변수 생성 없음 확인
이번 분석에서 새로운 통제변수는 생성하지 않았다. quadratic term은 H3 가설 검정을 위한 필수 모형항으로만 사용하였다.

## 7. Quadratic term 설명
H3 검정에는 역 U자형 관계를 포착하기 위해 quadratic term이 필요하다. 이는 새로운 통제변수가 아니라 H3 가설 검정을 위한 필수 모형항이다. squared term은 회귀식 내부의 분석용 항으로만 생성하였으며, 산출용 dataset에 `_sq` suffix로 명확히 표시하였다.

## 8. 분석 표본 구성
- H3-pre base 파일: wendys_humor_frequency_proportion_post_level_dataset.csv (전체 n=1330)
- H3-main base 파일: wendys_h3_aggressive_vs_other_intensity_dataset.csv (전체 n=978)

## 9. quarter_total_posts >= 10 필터 적용 결과
- H3-pre filtered: n=960, unique year_quarter=25
- H3-main filtered: n=960, unique year_quarter=25
- Primary DV 분석 표본 (결측 제외 후): H3-pre n=960, H3-main n=960

## 10. 사용한 Predictor 설명
- H3-pre primary predictor: `humor_proportion_quarter_loo` (LOO quarter-level general humor proportion)
- H3-main primary predictor: `aggressive_humor_proportion_quarter_loo` (LOO quarter-level aggressive humor proportion)
- LOO 변수는 focal post가 자기 자신이 속한 quarter-level proportion에 기계적으로 반영되는 문제를 줄이기 위한 변수이다.
- non-LOO proportion 변수, month-level proportion 변수, frequency count 변수는 사용하지 않았다.

## 11. H3-pre: General Humor Proportion Quadratic 결과
**Primary DV (log1p_engagement_total)**:
  β1=0.1917 (p=0.9288), β2=0.3153 (p=0.8708), turning_point=-0.3040 (in_range=False), 판정=not_support

**Supplemental DVs**:
  - log1p_engagement_favorite_retweet: β1=0.9007 (p=0.6789), β2=-0.2385 (p=0.9034), turning_point=1.8886 (in_range=False), 판정=directional_only
  - log1p_favorite_count: β1=0.2497 (p=0.9217), β2=0.1766 (p=0.9387), turning_point=-0.7070 (in_range=False), 판정=not_support
  - log1p_retweet_count: β1=-1.2437 (p=0.5711), β2=0.8951 (p=0.6517), turning_point=0.6947 (in_range=True), 판정=not_support
  - log1p_reply_count: β1=-4.7579 (p=0.0192), β2=4.7182 (p=0.0102), turning_point=0.5042 (in_range=True), 판정=not_support
  - log1p_quote_count: β1=-3.8747 (p=0.0878), β2=3.9189 (p=0.0560), turning_point=0.4944 (in_range=True), 판정=not_support
  - log1p_bookmark_count: β1=-6.9036 (p=0.0007), β2=3.7052 (p=0.0442), turning_point=0.9316 (in_range=False), 판정=not_support

## 12. H3-main: Aggressive Humor Proportion Quadratic 결과
**Primary DV (log1p_engagement_total)**:
  β1=-1.4598 (p=0.6530), β2=2.5539 (p=0.7388), turning_point=0.2858 (in_range=True), 판정=not_support

**Supplemental DVs**:
  - log1p_engagement_favorite_retweet: β1=-1.2461 (p=0.7051), β2=2.4041 (p=0.7569), turning_point=0.2592 (in_range=True), 판정=not_support
  - log1p_favorite_count: β1=-1.8801 (p=0.6243), β2=1.4932 (p=0.8690), turning_point=0.6295 (in_range=False), 판정=not_support
  - log1p_retweet_count: β1=-2.4857 (p=0.4538), β2=5.2683 (p=0.5009), turning_point=0.2359 (in_range=True), 판정=not_support
  - log1p_reply_count: β1=-1.7449 (p=0.5699), β2=-0.1391 (p=0.9847), turning_point=-6.2712 (in_range=False), 판정=not_support
  - log1p_quote_count: β1=-4.0658 (p=0.2361), β2=6.5645 (p=0.4174), turning_point=0.3097 (in_range=True), 판정=not_support
  - log1p_bookmark_count: β1=-12.5052 (p=0.0001), β2=23.4310 (p=0.0017), turning_point=0.2669 (in_range=True), 판정=not_support

## 13. Primary DV 기준 결과 요약
- H3-pre (log1p_engagement_total): β1=0.1917 (p=0.9288), β2=0.3153 (p=0.8708), turning_point=-0.3040 (in_range=False), 판정=not_support
- H3-main (log1p_engagement_total): β1=-1.4598 (p=0.6530), β2=2.5539 (p=0.7388), turning_point=0.2858 (in_range=True), 판정=not_support

## 14. Supplemental DV 기준 결과 요약
H3-pre supplemental DVs:
  - log1p_engagement_favorite_retweet: directional_only
  - log1p_favorite_count: not_support
  - log1p_retweet_count: not_support
  - log1p_reply_count: not_support
  - log1p_quote_count: not_support
  - log1p_bookmark_count: not_support

H3-main supplemental DVs:
  - log1p_engagement_favorite_retweet: not_support
  - log1p_favorite_count: not_support
  - log1p_retweet_count: not_support
  - log1p_reply_count: not_support
  - log1p_quote_count: not_support
  - log1p_bookmark_count: not_support

## 15. Turning Point 및 관측 범위 내 위치 여부
- H3-pre predictor 관측 범위: [0.1579, 0.9167]
  Primary DV turning point: -0.3040,   in_range: False
- H3-main predictor 관측 범위: [0.0000, 0.3377]
  Primary DV turning point: 0.2858,   in_range: True

## 16. H3-pre 판정
Primary DV 기준: **not_support**

## 17. H3-main 판정
Primary DV 기준: **not_support**

## 18. 인과관계 주의사항
본 분석은 관측적 연관성(observational association) 분석이며, 인과관계(causal relationship)를 의미하지 않는다.

## 19. H1/H2 분석 미수행 확인
H1·H2 분석은 이번 작업에서 수행하지 않았다. 새로운 유머 분류 모델도 학습하지 않았다.

## 20. 다음 단계
다음 단계에서 시간 변수(year FE 등) 또는 post format controls를 추가할 수 있으나, 사용자 승인 후 진행한다.