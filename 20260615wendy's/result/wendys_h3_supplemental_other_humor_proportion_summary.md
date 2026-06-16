# Wendy's H3 Supplemental: Other Humor Proportion Quadratic Test — 분석 요약

## 1. 분석 목적
Wendy's H3 추가 분석으로, aggressive humor를 제외한 other humor usage intensity (other_humor_proportion_quarter_loo)가 post-level engagement와 어떤 비선형 관계를 갖는지 확인한다.

## 2. 이 분석은 H3 Supplemental Analysis
이 분석은 H3-pre 또는 H3-main을 대체하지 않는다. general humor, aggressive humor, other humor proportion을 분리했을 때 어떤 패턴이 나오는지 확인하는 보조 분석이다.

## 3. H3-pre, H3-main과의 차이
- H3-pre: humor_proportion_quarter_loo (전체 유머 비중)
- H3-main: aggressive_humor_proportion_quarter_loo (aggressive humor 비중)
- H3-supplemental: other_humor_proportion_quarter_loo (비공격적 유머 비중)

## 4. 사용한 파일
- H3 base: `wendys_h3_aggressive_vs_other_intensity_dataset.csv`
- Post format source: `wendys_fast_weak_supervised_humor_dataset.csv`

## 5. 병합 여부 및 병합 안정성
- 병합 key: `id`
- left n: 978, right n: 978, merged n: 978
- 미매칭: 0건, duplicate key: 0건
- quarter_total_posts >= 10 후 n: 960
- text_length / hashtag_count / mention_count 결측: 0건

## 6. 원본 posts.json 변경 없음 확인
data/wendys/posts.json 원본 파일은 수정하지 않았다.

## 7. 새 통제변수 생성 없음 확인
새로운 통제변수는 생성하지 않았다. squared term은 분석용 모형항으로만 생성하였고, 산출 dataset에 `_sq` suffix로 표시하였다.

## 8. Frequency Count 변수 미사용 확인
포스트 수 기반 frequency count 변수는 사용하지 않았다.

## 9. Quadratic Term 설명
other_humor_proportion_quarter_loo_sq는 역 U자형 가설 검정을 위한 필수 모형항이며, 원본 파일은 수정하지 않고 산출 dataset에만 포함하였다.

## 10. 분석 표본 구성
- 원본 n: 978 → quarter_total_posts >= 10 후 n: 960
- unique year_quarter: 25

## 11. quarter_total_posts >= 10 필터 적용 결과
- n=960, unique year_quarter=25

## 12. 사용한 Predictor
- `other_humor_proportion_quarter_loo` (LOO quarter-level other humor proportion)
- 관측 범위: [0.0000, 0.6667]
- mean=0.3740, std=0.1557
- aggressive_humor_proportion, humor_proportion(general)은 모형에 포함하지 않았다.

## 13. 사용한 시간 변수
- created_year FE (categorical, drop_first=True)
- created_month FE (categorical, drop_first=True)
- created_hour FE (categorical, drop_first=True)
- year_quarter FE, quarter FE, day_of_week는 사용하지 않았다.

## 14. 사용한 Post Format 변수 3개
- text_length, hashtag_count, mention_count

## 15. 제외한 변수
- emoji_count, url_count, is_quote_status, is_retweet_text
- log1p_view_count (view_count 계열 전체)
- frequency count 계열 전체
- humor_proportion_quarter_loo, aggressive_humor_proportion_quarter_loo

## 16. Primary DV 기준 M0, M1, M8 결과
- M0 (baseline): β1=1.8261(p=0.2659), β2=-1.6771(p=0.4437), tp=0.5444(in_range=True), 판정=directional_only
- M1 (time FE): β1=-6.4318(p=0.0115), β2=7.2371(p=0.0142), tp=0.4444(in_range=True), 판정=U_shape
- M8 (time FE + all format): β1=-6.8614(p=0.0043), β2=7.8688(p=0.0047), tp=0.4360(in_range=True), 판정=U_shape


### Primary DV (log1p_engagement_total) 모형별 결과
- M0 (time=none, fmt=none): β1=1.8261(p=0.2659), β2=-1.6771(p=0.4437), tp=0.5444(in_range=True), 판정=directional_only
- M1 (time=time FE, fmt=none): β1=-6.4318(p=0.0115), β2=7.2371(p=0.0142), tp=0.4444(in_range=True), 판정=U_shape
- M2 (time=time FE, fmt=text_length): β1=-6.5285(p=0.0090), β2=7.5500(p=0.0091), tp=0.4324(in_range=True), 판정=U_shape
- M3 (time=time FE, fmt=hashtag_count): β1=-6.2688(p=0.0131), β2=6.8336(p=0.0196), tp=0.4587(in_range=True), 판정=U_shape
- M4 (time=time FE, fmt=mention_count): β1=-6.8662(p=0.0045), β2=7.7766(p=0.0055), tp=0.4415(in_range=True), 판정=U_shape
- M5 (time=time FE, fmt=text_length+hashtag_count): β1=-6.4140(p=0.0101), β2=7.2582(p=0.0120), tp=0.4418(in_range=True), 판정=U_shape
- M6 (time=time FE, fmt=text_length+mention_count): β1=-6.8887(p=0.0041), β2=7.9315(p=0.0044), tp=0.4343(in_range=True), 판정=U_shape
- M7 (time=time FE, fmt=hashtag_count+mention_count): β1=-6.7931(p=0.0050), β2=7.6167(p=0.0066), tp=0.4459(in_range=True), 판정=U_shape
- M8 (time=time FE, fmt=text_length+hashtag_count+mention_count): β1=-6.8614(p=0.0043), β2=7.8688(p=0.0047), tp=0.4360(in_range=True), 판정=U_shape

## 17. Supplemental DV 기준 결과 요약 (M8)
  - log1p_engagement_favorite_retweet: U_shape
  - log1p_favorite_count: U_shape
  - log1p_retweet_count: U_shape
  - log1p_reply_count: U_shape
  - log1p_quote_count: U_shape
  - log1p_bookmark_count: U_shape

## 18. Turning Point 및 관측 범위 내 위치 여부
- predictor 관측 범위: [0.0000, 0.6667]
- M0 tp=0.5444, in_range=True
- M1 tp=0.4444, in_range=True
- M8 tp=0.4360, in_range=True

## 19. Other Humor Proportion 결과 판정
- M0: **directional_only**
- M1: **U_shape**
- M8: **U_shape**

## 20. 기존 H3-pre, H3-main 결과와 비교
- H3-pre (humor_proportion_quarter_loo): Step 1~3 전체에서 not_support (β2>0, U자형 경향)
- H3-main (aggressive_humor_proportion_quarter_loo): Step 1~3 전체에서 not_support (일부 모형 directional_only, mention_count 통제 시 weak_support 출현)
- H3-supplemental (other_humor_proportion_quarter_loo): M0=directional_only, M8=U_shape

## 21. 인과관계 주의사항
본 분석은 관측적 연관성(observational association) 분석이며, 인과관계(causal relationship)를 의미하지 않는다.

## 22. H1/H2 분석 미수행 확인
H1·H2 분석은 이번 작업에서 수행하지 않았다. 새로운 유머 분류 모델도 학습하지 않았다.

## 23. 다음 단계
다음 단계는 사용자 승인 후 결정한다.