# Wendy's H3 Joint Decomposition: Aggressive + Other Humor Proportion — 분석 요약

## 1. 분석 목적
aggressive humor proportion과 other humor proportion을 같은 quadratic model에 동시에 포함하여 두 유머 유형의 비중 효과를 분리하고, other humor의 U자형 패턴이 aggressive humor proportion의 결과를 가렸는지(masking) 확인한다.

## 2. 이 분석은 H3 Decomposition Analysis
이 분석은 H3-pre, H3-main, H3-supplemental을 대체하지 않는다. 두 비중 변수를 동시에 통제했을 때 각각의 quadratic 효과가 어떻게 달라지는지 확인하는 추가 분해 분석이다.

## 3. 기존 H3 분석과의 차이
- H3-pre: humor_proportion_quarter_loo (전체 유머 비중) 단독
- H3-main: aggressive_humor_proportion_quarter_loo 단독
- H3-supplemental: other_humor_proportion_quarter_loo 단독
- **H3-decomposition**: aggressive + other humor proportion 동시 투입 (total humor proportion 제외)

## 4. 사용한 파일
- H3 base: `wendys_h3_aggressive_vs_other_intensity_dataset.csv`
- Post format source: `wendys_fast_weak_supervised_humor_dataset.csv`

## 5. 직전 commit push 여부
직전 commit 9ac621c (H3 supplemental other humor): **push 완료**

## 6. 병합 여부 및 병합 안정성
- 병합 key: `id` / left=978, right=978, merged=978
- 미매칭: 0건, duplicate key: 0건
- quarter_total_posts >= 10 후 n: 960
- text_length / hashtag_count / mention_count 결측: 0건

## 7. 원본 posts.json 변경 없음 확인
data/wendys/posts.json 원본 파일은 수정하지 않았다.

## 8. 새 통제변수 생성 없음 확인
새로운 통제변수는 생성하지 않았다. squared term은 H3 quadratic 검정을 위한 필수 모형항이다.

## 9. Frequency Count 변수 미사용 확인
포스트 수 기반 frequency count 변수는 사용하지 않았다.

## 10. Total Humor Proportion 미사용 확인
humor_proportion_quarter_loo는 이번 joint model에 포함하지 않았다. aggressive + other 비중의 합이 total humor proportion과 구조적으로 연결되므로, 중복 투입에 따른 식별 문제를 방지하기 위함이다.

## 11. Quadratic Term 설명
aggressive_humor_proportion_quarter_loo_sq 및 other_humor_proportion_quarter_loo_sq는 H3 quadratic 가설 검정을 위한 필수 모형항이며, 산출 dataset에 `_sq` suffix로 표시하였다.

## 12. 분석 표본 구성
- 원본 n: 978 → quarter_total_posts >= 10 후 n: 960
- unique year_quarter: 25

## 13. quarter_total_posts >= 10 필터 적용 결과
- n=960, unique year_quarter=25

## 14. Predictor별 기술통계
- aggressive_humor_proportion_quarter_loo: min=0.0000, max=0.3377, mean=0.2062, std=0.0703
- other_humor_proportion_quarter_loo: min=0.0000, max=0.6667, mean=0.3740, std=0.1557

## 15. Aggressive-Other Predictor 상관관계
- pairwise_corr(agg, oth) = -0.2641
- 두 predictor 간 낮은 음적 상관이 존재하여, joint model에서 독립적인 추정이 가능하다.

## 16. M0 결과 (baseline joint quadratic)
**Aggressive**: β1=-2.5905(p=0.4398), β2=6.1978(p=0.4442), tp=0.2090(in_range=True), 판정=aggressive_not_support
**Other Humor**: γ1=1.7725(p=0.2810), γ2=-1.4915(p=0.5001), tp=0.5942(in_range=True), 판정=other_not_support

## 17. M1 결과 (+ time FE)
**Aggressive**: β1=-3.7278(p=0.3078), β2=0.3261(p=0.9721), tp=5.7153(in_range=False), 판정=aggressive_not_support
**Other Humor**: γ1=-7.3535(p=0.0040), γ2=7.7001(p=0.0096), tp=0.4775(in_range=True), 판정=other_U_shape

## 18. M2 결과 (+ time FE + post format controls)
**Aggressive**: β1=-2.3560(p=0.4944), β2=-3.7276(p=0.6722), tp=-0.3160(in_range=False), 판정=aggressive_not_support
**Other Humor**: γ1=-7.7528(p=0.0013), γ2=8.1417(p=0.0037), tp=0.4761(in_range=True), 판정=other_U_shape

## 19. Primary DV 기준 Aggressive Proportion 결과 해석
- M0: aggressive_not_support
- M1: aggressive_not_support
- M2: aggressive_not_support

## 20. Primary DV 기준 Other Humor Proportion 결과 해석
- M0: other_not_support
- M1: other_U_shape
- M2: other_U_shape

## 21. Supplemental DV 기준 결과 요약 (M2)
  - log1p_engagement_favorite_retweet: agg=aggressive_not_support, oth=other_U_shape
  - log1p_favorite_count: agg=aggressive_not_support, oth=other_U_shape
  - log1p_retweet_count: agg=aggressive_not_support, oth=other_U_shape
  - log1p_reply_count: agg=aggressive_directional_only, oth=other_U_shape
  - log1p_quote_count: agg=aggressive_not_support, oth=other_U_shape
  - log1p_bookmark_count: agg=aggressive_not_support, oth=other_U_shape

## 22. Masking 여부 판단
joint model에서도 aggressive humor proportion의 역 U자형 효과는 확인되지 않았다. other humor proportion의 U자형 패턴은 aggressive humor proportion과 독립적으로 존재하며, masking 효과는 관찰되지 않았다.

## 23. 기존 H3 분석과의 비교
- H3-main 단독 (Step 3 M8): aggressive_not_support
- H3-supplemental 단독 (M8): other_U_shape (β2>0, p<.01, turning point ≈ 0.44)
- H3-decomposition M0: agg=aggressive_not_support, oth=other_not_support
- H3-decomposition M2: agg=aggressive_not_support, oth=other_U_shape

## 24. H3 역 U자형 가설에 대한 최종 해석
- H3-pre, H3-main, H3-supplemental(other humor 단독) 모든 분석에서 역 U자형 관계는 지지되지 않았다.
- other humor proportion에서는 U자형 패턴(β2>0)이 일관되게 관찰되었으나, 이는 역 U자형 가설과 반대 방향이다.
- joint decomposition model에서도 이 패턴의 변화 여부를 위 결과에서 확인할 수 있다.

## 25. 인과관계 주의사항
본 분석은 관측적 연관성(observational association) 분석이며, 인과관계(causal relationship)를 의미하지 않는다.

## 26. H1/H2 분석 미수행 확인
H1·H2 분석은 이번 작업에서 수행하지 않았다. 새로운 유머 분류 모델도 학습하지 않았다.

## 27. 다음 단계
다음 단계는 사용자 승인 후 결정한다.