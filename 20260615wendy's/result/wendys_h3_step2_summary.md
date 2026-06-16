# Wendy's H3 Step 2: Proportion-Based Quadratic Test with Time Variables — 분석 요약

## 1. 분석 목적
Wendy's H3 분석의 2단계로, Step 1에서 사용한 비중 기반 LOO proportion quadratic model에 시간 변수(created_year, created_month, created_hour)를 추가하여, H3의 역 U자형 관계가 시간 효과를 고려한 뒤에도 유지되는지 확인한다.

## 2. H3 가설
H3: Wendy's의 humor usage intensity는 post-level engagement와 역 U자형 관계를 가질 것이다. 즉, 낮은 수준에서 중간 수준까지는 engagement가 증가하지만, 일정 수준을 넘어서면 감소할 것이다.

## 3. H3-pre와 H3-main 구분
- **H3-pre**: general humor usage intensity (humor_proportion_quarter_loo)의 역 U자형 관계
- **H3-main**: aggressive humor usage intensity (aggressive_humor_proportion_quarter_loo)의 역 U자형 관계

## 4. 사용한 파일
- H3-pre: `wendys_humor_frequency_proportion_post_level_dataset.csv`
- H3-main: `wendys_h3_aggressive_vs_other_intensity_dataset.csv`
- 참조: Step 1 결과 파일 (비교용)

## 5. 원본 posts.json 변경 없음 확인
data/wendys/posts.json 원본 파일은 수정하지 않았다.

## 6. 새 통제변수 생성 없음 확인
이번 분석에서 새로운 통제변수는 생성하지 않았다. quadratic term 및 시간 FE dummy는 분석용 모형항으로만 사용하였다.

## 7. Frequency Count 변수 미사용 확인
포스트 수 기반 frequency count 변수는 사용하지 않았다. 비중 기반 LOO proportion 변수만 H3 predictor로 사용하였다.

## 8. Quadratic Term 설명
squared term은 H3 역 U자형 가설 검정을 위한 필수 모형항이며, 산출용 dataset에 `_sq` suffix로 명확히 표시하였다.

## 9. 분석 표본 구성
- H3-pre base 파일: wendys_humor_frequency_proportion_post_level_dataset.csv (전체 n=978 before filter)
- H3-main base 파일: wendys_h3_aggressive_vs_other_intensity_dataset.csv (전체 n=978 before filter)

## 10. quarter_total_posts >= 10 필터 적용 결과
- H3-pre filtered: n=960, unique year_quarter=25
- H3-main filtered: n=960, unique year_quarter=25

## 11. 사용한 Predictor 설명
- H3-pre: `humor_proportion_quarter_loo` (LOO quarter-level general humor proportion)
- H3-main: `aggressive_humor_proportion_quarter_loo` (LOO quarter-level aggressive humor proportion)
- non-LOO proportion, month-level proportion, frequency count 변수는 사용하지 않았다.

## 12. 사용한 시간 변수 조합
- M0: 없음 (baseline quadratic only)
- M1: created_year FE
- M2: created_month FE
- M3: created_hour FE
- M4: created_year + created_month FE
- M5: created_year + created_hour FE
- M6: created_month + created_hour FE
- M7: created_year + created_month + created_hour FE
- year_quarter FE, quarter FE, day_of_week는 사용하지 않았다.

## 13. H3-pre: General Humor Proportion Quadratic 결과

### H3-pre - Primary DV (log1p_engagement_total) 모형별 결과
- M0 (none): β1=0.1917(p=0.9288), β2=0.3153(p=0.8708), tp=-0.3040(in_range=False), 판정=not_support
- M1 (created_year): β1=-4.6777(p=0.0608), β2=2.2617(p=0.2818), tp=1.0341(in_range=False), 판정=not_support
- M2 (created_month): β1=-0.3622(p=0.8661), β2=0.9349(p=0.6322), tp=0.1937(in_range=True), 판정=not_support
- M3 (created_hour): β1=0.1349(p=0.9502), β2=0.3398(p=0.8618), tp=-0.1984(in_range=False), 판정=not_support
- M4 (created_year+created_month): β1=-6.0393(p=0.0185), β2=4.0517(p=0.0631), tp=0.7453(in_range=True), 판정=not_support
- M5 (created_year+created_hour): β1=-4.9650(p=0.0493), β2=2.5045(p=0.2387), tp=0.9912(in_range=False), 판정=not_support
- M6 (created_month+created_hour): β1=-0.5388(p=0.8038), β2=1.0519(p=0.5938), tp=0.2561(in_range=True), 판정=not_support
- M7 (created_year+created_month+created_hour): β1=-6.6063(p=0.0114), β2=4.5366(p=0.0406), tp=0.7281(in_range=True), 판정=not_support

**Supplemental DVs (M7 기준)**:
  - log1p_engagement_favorite_retweet: β1=-6.4338(p=0.0147), β2=4.2767(p=0.0561), tp=0.7522(in_range=True), 판정=not_support
  - log1p_favorite_count: β1=-6.9581(p=0.0260), β2=4.5872(p=0.0839), tp=0.7584(in_range=True), 판정=not_support
  - log1p_retweet_count: β1=-7.6313(p=0.0047), β2=5.4707(p=0.0169), tp=0.6975(in_range=True), 판정=not_support
  - log1p_reply_count: β1=-6.9722(p=0.0054), β2=5.7367(p=0.0070), tp=0.6077(in_range=True), 판정=not_support
  - log1p_quote_count: β1=-6.9610(p=0.0128), β2=5.4409(p=0.0219), tp=0.6397(in_range=True), 판정=not_support
  - log1p_bookmark_count: β1=-8.1912(p=0.0011), β2=5.6224(p=0.0085), tp=0.7284(in_range=True), 판정=not_support

## 14. H3-main: Aggressive Humor Proportion Quadratic 결과

### H3-main - Primary DV (log1p_engagement_total) 모형별 결과
- M0 (none): β1=-1.4598(p=0.6530), β2=2.5539(p=0.7388), tp=0.2858(in_range=True), 판정=not_support
- M1 (created_year): β1=-6.0378(p=0.0757), β2=9.9964(p=0.2296), tp=0.3020(in_range=True), 판정=not_support
- M2 (created_month): β1=3.1770(p=0.3336), β2=-11.2573(p=0.1520), tp=0.1411(in_range=True), 판정=directional_only
- M3 (created_hour): β1=-2.2342(p=0.4895), β2=5.3534(p=0.4832), tp=0.2087(in_range=True), 판정=not_support
- M4 (created_year+created_month): β1=-2.1959(p=0.5302), β2=-3.4880(p=0.6875), tp=-0.3148(in_range=False), 판정=not_support
- M5 (created_year+created_hour): β1=-7.0357(p=0.0394), β2=13.5347(p=0.1069), tp=0.2599(in_range=True), 판정=not_support
- M6 (created_month+created_hour): β1=2.2687(p=0.4904), β2=-8.2050(p=0.2976), tp=0.1382(in_range=True), 판정=directional_only
- M7 (created_year+created_month+created_hour): β1=-3.3810(p=0.3386), β2=0.7974(p=0.9277), tp=2.1199(in_range=False), 판정=not_support

**Supplemental DVs (M7 기준)**:
  - log1p_engagement_favorite_retweet: β1=-3.8164(p=0.2851), β2=2.0071(p=0.8213), tp=0.9507(in_range=False), 판정=not_support
  - log1p_favorite_count: β1=-3.4685(p=0.4127), β2=0.9575(p=0.9276), tp=1.8113(in_range=False), 판정=not_support
  - log1p_retweet_count: β1=-3.6163(p=0.3209), β2=-0.6494(p=0.9429), tp=-2.7843(in_range=False), 판정=not_support
  - log1p_reply_count: β1=0.1671(p=0.9606), β2=-8.7727(p=0.2976), tp=0.0095(in_range=True), 판정=directional_only
  - log1p_quote_count: β1=-1.3502(p=0.7210), β2=-3.9895(p=0.6718), tp=-0.1692(in_range=False), 판정=not_support
  - log1p_bookmark_count: β1=-6.9014(p=0.0432), β2=9.3309(p=0.2718), tp=0.3698(in_range=False), 판정=not_support

## 15. Primary DV 기준 시간 변수 조합별 결과 요약
H3-pre M0 (baseline): β1=0.1917(p=0.9288), β2=0.3153(p=0.8708), tp=-0.3040(in_range=False), 판정=not_support
H3-pre M7 (full time): β1=-6.6063(p=0.0114), β2=4.5366(p=0.0406), tp=0.7281(in_range=True), 판정=not_support
H3-main M0 (baseline): β1=-1.4598(p=0.6530), β2=2.5539(p=0.7388), tp=0.2858(in_range=True), 판정=not_support
H3-main M7 (full time): β1=-3.3810(p=0.3386), β2=0.7974(p=0.9277), tp=2.1199(in_range=False), 판정=not_support

## 16. Supplemental DV 기준 결과 요약
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
  - log1p_reply_count: directional_only
  - log1p_quote_count: not_support
  - log1p_bookmark_count: not_support

## 17. Turning Point 및 관측 범위 내 위치 여부
- H3-pre predictor 관측 범위: [0.1579, 0.9167]
  M0 tp=-0.3040, in_range=False
  M7 tp=0.7281, in_range=True
- H3-main predictor 관측 범위: [0.0000, 0.3377]
  M0 tp=0.2858, in_range=True
  M7 tp=2.1199, in_range=False

## 18. H3-pre 판정
- M0 (baseline): **not_support**
- M7 (full time FE): **not_support**

## 19. H3-main 판정
- M0 (baseline): **not_support**
- M7 (full time FE): **not_support**

## 20. 인과관계 주의사항
본 분석은 관측적 연관성(observational association) 분석이며, 인과관계(causal relationship)를 의미하지 않는다.

## 21. H1/H2 분석 미수행 확인
H1·H2 분석은 이번 작업에서 수행하지 않았다. 새로운 유머 분류 모델도 학습하지 않았다.

## 22. 다음 단계
다음 단계에서 post format controls를 추가할 수 있으나, 사용자 승인 후 진행한다.