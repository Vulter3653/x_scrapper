# Wendy's H3 Step 3: Proportion Quadratic + Time FE + Post Format Controls — 분석 요약

## 1. 분석 목적
Wendy's H3 분석의 3단계로, 비중 기반 LOO proportion quadratic model에 시간 변수(created_year, created_month, created_hour)와 post format controls(text_length, hashtag_count, mention_count)를 추가하여, Step 1·2에서 확인된 H3 불지지 결과가 post-level format 차이를 고려한 뒤에도 유지되는지 확인한다.

## 2. H3 가설
H3: Wendy's의 humor usage intensity는 post-level engagement와 역 U자형 관계를 가질 것이다. 즉, 낮은 수준에서 중간 수준까지는 engagement가 증가하지만, 일정 수준을 넘어서면 감소할 것이다.

## 3. H3-pre와 H3-main 구분
- **H3-pre**: general humor usage intensity (humor_proportion_quarter_loo)의 역 U자형 관계
- **H3-main**: aggressive humor usage intensity (aggressive_humor_proportion_quarter_loo)의 역 U자형 관계

## 4. 사용한 파일
- H3-pre base: `wendys_humor_frequency_proportion_post_level_dataset.csv`
- H3-main base: `wendys_h3_aggressive_vs_other_intensity_dataset.csv`
- Post format source: `wendys_fast_weak_supervised_humor_dataset.csv`
- 참조: Step 2 결과 파일 (비교용)

## 5. 병합 여부 및 병합 안정성
- 병합 key: `id`
- left n (base files): 978
- right n (format file): 978
- merged n: 978 (1:1 완전 매칭, 미매칭 0건, duplicate key 없음)
- quarter_total_posts >= 10 필터 후 n: 960 (H3-pre), 960 (H3-main)
- text_length / hashtag_count / mention_count 결측: 0건

## 6. 원본 posts.json 변경 없음 확인
data/wendys/posts.json 원본 파일은 수정하지 않았다.

## 7. 새 통제변수 생성 없음 확인
새로운 통제변수는 생성하지 않았다. quadratic term, 시간 FE dummy, post format 변수는 모두 기존 파일에서 가져오거나 분석용 모형항으로만 생성하였다.

## 8. Frequency Count 변수 미사용 확인
포스트 수 기반 frequency count 변수는 사용하지 않았다.

## 9. Quadratic Term 설명
squared term은 H3 역 U자형 가설 검정을 위한 필수 모형항이며, 산출용 dataset에 `_sq` suffix로 명확히 표시하였다.

## 10. 분석 표본 구성
- H3-pre: n=978 (원본) → n=960 (quarter_total_posts >= 10 후)
- H3-main: n=978 (원본) → n=960 (quarter_total_posts >= 10 후)

## 11. quarter_total_posts >= 10 필터 적용 결과
- H3-pre: n=960, unique year_quarter=25
- H3-main: n=960, unique year_quarter=25

## 12. 사용한 Predictor
- H3-pre: `humor_proportion_quarter_loo` (LOO quarter-level general humor proportion)
- H3-main: `aggressive_humor_proportion_quarter_loo` (LOO quarter-level aggressive humor proportion)

## 13. 사용한 시간 변수
- created_year FE (categorical, drop_first=True)
- created_month FE (categorical, drop_first=True)
- created_hour FE (categorical, drop_first=True)
- year_quarter FE, quarter FE, day_of_week는 사용하지 않았다.

## 14. 사용한 Post Format 변수 3개
- text_length
- hashtag_count
- mention_count

## 15. 제외한 변수
- emoji_count, url_count, is_quote_status, is_retweet_text
- log1p_view_count (view_count 계열 전체 제외)
- frequency count 계열 전체 제외

## 16. H3-pre: General Humor Proportion Quadratic 결과

### H3-pre - Primary DV (log1p_engagement_total) 모형별 결과
- M0 (fmt=none): β1=-6.6063(p=0.0114), β2=4.5366(p=0.0406), tp=0.7281(in_range=True), 판정=not_support
- M1 (fmt=text_length): β1=-7.2246(p=0.0048), β2=5.2149(p=0.0167), tp=0.6927(in_range=True), 판정=not_support
- M2 (fmt=hashtag_count): β1=-6.4337(p=0.0129), β2=4.2098(p=0.0555), tp=0.7641(in_range=True), 판정=not_support
- M3 (fmt=mention_count): β1=-5.8857(p=0.0177), β2=3.8706(p=0.0662), tp=0.7603(in_range=True), 판정=not_support
- M4 (fmt=text_length+hashtag_count): β1=-7.0374(p=0.0059), β2=4.9205(p=0.0237), tp=0.7151(in_range=True), 판정=not_support
- M5 (fmt=text_length+mention_count): β1=-6.3630(p=0.0098), β2=4.3822(p=0.0364), tp=0.7260(in_range=True), 판정=not_support
- M6 (fmt=hashtag_count+mention_count): β1=-5.8523(p=0.0183), β2=3.7758(p=0.0730), tp=0.7750(in_range=True), 판정=not_support
- M7 (fmt=text_length+hashtag_count+mention_count): β1=-6.3289(p=0.0103), β2=4.3189(p=0.0395), tp=0.7327(in_range=True), 판정=not_support

**Supplemental DVs (M7 기준)**:
  - log1p_engagement_favorite_retweet: not_support
  - log1p_favorite_count: not_support
  - log1p_retweet_count: not_support
  - log1p_reply_count: not_support
  - log1p_quote_count: not_support
  - log1p_bookmark_count: not_support

## 17. H3-main: Aggressive Humor Proportion Quadratic 결과

### H3-main - Primary DV (log1p_engagement_total) 모형별 결과
- M0 (fmt=none): β1=-3.3810(p=0.3386), β2=0.7974(p=0.9277), tp=2.1199(in_range=False), 판정=not_support
- M1 (fmt=text_length): β1=-3.6225(p=0.2963), β2=1.4334(p=0.8681), tp=1.2636(in_range=False), 판정=not_support
- M2 (fmt=hashtag_count): β1=-3.5363(p=0.3130), β2=0.9722(p=0.9113), tp=1.8188(in_range=False), 판정=not_support
- M3 (fmt=mention_count): β1=-1.6065(p=0.6325), β2=-4.2644(p=0.6103), tp=-0.1884(in_range=False), 판정=not_support
- M4 (fmt=text_length+hashtag_count): β1=-3.6950(p=0.2853), β2=1.4718(p=0.8642), tp=1.2553(in_range=False), 판정=not_support
- M5 (fmt=text_length+mention_count): β1=-1.9320(p=0.5622), β2=-3.3704(p=0.6848), tp=-0.2866(in_range=False), 판정=not_support
- M6 (fmt=hashtag_count+mention_count): β1=-1.7376(p=0.6049), β2=-3.9878(p=0.6335), tp=-0.2179(in_range=False), 판정=not_support
- M7 (fmt=text_length+hashtag_count+mention_count): β1=-1.9777(p=0.5532), β2=-3.2814(p=0.6928), tp=-0.3014(in_range=False), 판정=not_support

**Supplemental DVs (M7 기준)**:
  - log1p_engagement_favorite_retweet: not_support
  - log1p_favorite_count: not_support
  - log1p_retweet_count: not_support
  - log1p_reply_count: weak_support
  - log1p_quote_count: not_support
  - log1p_bookmark_count: not_support

## 18. Primary DV 기준 Post Format 조합별 결과 요약
H3-pre M0 (time only): β1=-6.6063(p=0.0114), β2=4.5366(p=0.0406), tp=0.7281(in_range=True), 판정=not_support
H3-pre M7 (time+all format): β1=-6.3289(p=0.0103), β2=4.3189(p=0.0395), tp=0.7327(in_range=True), 판정=not_support
H3-main M0 (time only): β1=-3.3810(p=0.3386), β2=0.7974(p=0.9277), tp=2.1199(in_range=False), 판정=not_support
H3-main M7 (time+all format): β1=-1.9777(p=0.5532), β2=-3.2814(p=0.6928), tp=-0.3014(in_range=False), 판정=not_support

## 19. Supplemental DV 기준 결과 요약 (M7)
H3-pre (M7):
  - log1p_engagement_favorite_retweet: not_support
  - log1p_favorite_count: not_support
  - log1p_retweet_count: not_support
  - log1p_reply_count: not_support
  - log1p_quote_count: not_support
  - log1p_bookmark_count: not_support

H3-main (M7):
  - log1p_engagement_favorite_retweet: not_support
  - log1p_favorite_count: not_support
  - log1p_retweet_count: not_support
  - log1p_reply_count: weak_support
  - log1p_quote_count: not_support
  - log1p_bookmark_count: not_support

## 20. Turning Point 및 관측 범위 내 위치 여부
- H3-pre predictor 관측 범위: [0.1579, 0.9167]
  M0 tp=0.7281, in_range=True
  M7 tp=0.7327, in_range=True
- H3-main predictor 관측 범위: [0.0000, 0.3377]
  M0 tp=2.1199, in_range=False
  M7 tp=-0.3014, in_range=False

## 21. H3-pre 판정
- M0 (time FE only): **not_support**
- M7 (time FE + all format): **not_support**

## 22. H3-main 판정
- M0 (time FE only): **not_support**
- M7 (time FE + all format): **not_support**

## 23. Step 1·2 결과와의 비교
- Step 1 (baseline quadratic): H3-pre not_support, H3-main not_support
- Step 2 (+ time FE M7): H3-pre not_support, H3-main not_support
- Step 3 M0 (time FE only): H3-pre not_support, H3-main not_support
- Step 3 M7 (time FE + format): H3-pre not_support, H3-main not_support
- post format controls를 추가한 뒤에도 H3 불지지 결과는 일관되게 유지된다.

## 24. 인과관계 주의사항
본 분석은 관측적 연관성(observational association) 분석이며, 인과관계(causal relationship)를 의미하지 않는다.

## 25. H1/H2 분석 미수행 확인
H1·H2 분석은 이번 작업에서 수행하지 않았다. 새로운 유머 분류 모델도 학습하지 않았다.

## 26. 다음 단계
다음 단계는 사용자 승인 후 결정한다.