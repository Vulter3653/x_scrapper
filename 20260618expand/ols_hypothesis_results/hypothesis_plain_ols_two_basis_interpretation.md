# H1/H2/H3 단순 OLS — 두 가지 Measurement Basis 비교 결과

**생성일**: 2026-06-19
**SE 유형**: Classical OLS (s²×(X'X)⁻¹) — HC3/robust SE 미사용
**분석 성격**: PRELIMINARY DIAGNOSTIC ONLY — 최종 가설 검증이 아님
**금지 사항 준수**: scraping/reclassification/new prediction/new classifier 없음

---

## 1. 분석 구조 및 데이터

| | **A. Batch1 Human-coded** | **B. Full-sample Classifier-predicted** |
|---|---|---|
| **H1 IV** | human_humor_presence (0/1) | h1_humor_presence_pred_t50 (0/1) |
| **H1 n** | 1,482 posts (834 non-humor + 648 humor) | 68,039 posts (integrated corpus 전체) |
| **H2 IV** | human_coded humor_type | Wendy's model predicted humor_type |
| **H2 n** | 648 humor posts (batch1_fortune100) | 28,177 humor posts (65,245 total) |
| **H3 IV** | batch1 aggressive intensity | predicted aggressive intensity |
| **H3 n** | 88 firms | 97 firms |
| **DV** | log1p(total_engagement) | log1p(total_engagement) |
| **SE** | Classical OLS | Classical OLS |
| **Measurement validity** | 높음 (인간 코딩) | 낮음 (classifier NOT_A_CANDIDATE) |
| **표본 크기** | 작음 (검정력 부족) | 큼 (coverage 넓음) |

---

## 2. H1 결과: Humor Presence → Engagement

**가설**: 유머 게시물은 비유머 게시물보다 높은 engagement를 보인다.

### A. Batch1 Human-coded H1 (n=1482)

| 모델 | 변수 | β | OLS SE | t | p | 판정 |
|---|---|---|---|---|---|---|
| H1_batch1_simple | human_humor_presence | **1.214982** | — | 8.9766 | — | *** |

- IV: 인간이 직접 코딩한 humor presence (0/1)
- n = 1482 (humor=648, non-humor=834)
- Measurement validity: **높음** — 측정 오차가 상대적으로 낮음

### B. Full-sample Classifier-predicted H1 (n=68039)

| 모델 | 변수 | β | OLS SE | t | p | 판정 |
|---|---|---|---|---|---|---|
| H1_full_simple | h1_humor_presence_pred_t50 | **1.145709** | — | — | — | *** |

- IV: H1 classifier 예측값 (t=0.50); 전체 integrated corpus (68,039)
- Source breakdown: fortune100=65,245 / wendys_legacy=977 / moonpie_legacy=930 / cocacola_legacy=708 / fortune100_raw_append=179
- Measurement limitation: classifier predicted label이므로 measurement error bias 발생 가능

### H1 비교

- **방향 일치 여부**: Batch1과 Full-sample predicted 결과 방향 확인 필요
- **계수 차이**: Full-sample은 훨씬 큰 n으로 SE가 작아져 t-값이 커질 수 있음
- **Interpretation**: 두 결과 모두 preliminary_supported 방향 예상

---

## 3. H2-1 결과: Aggressive vs Other Humor → Engagement

**가설**: Aggressive humor는 other humor보다 engagement에 더 강한 영향을 미친다.

### A. Batch1 Human-coded H2-1 (n=648, n_agg=44)

| 모델 | 변수 | β | t | p |
|---|---|---|---|---|
| H2_1_batch1_simple | aggressive_vs_other | **0.712293** | 1.6866 | * |

- n_aggressive=44, n_other=604
- Measurement validity: **높음** (인간 코딩)
- 주의: n_agg=44는 검정력이 낮음

### B. Full-sample Classifier-predicted H2-1 (n=28,177 humor)

| 모델 | 변수 | β | t | p |
|---|---|---|---|---|
| H2_1_full_simple | predicted_aggressive_vs_other | **0.083304** | — | *** |

- n_pred_aggressive=6,857, n_other=21,320
- **CRITICAL WARNING**: Type classifier = NOT_A_CANDIDATE
  - #NationalRoastDay = rank#1 leakage feature (source shortcut 판정 완료)
  - Source held-out F1=0.0 (Wendy's → Fortune100 transfer)
  - Full-sample H2 결과는 classifier leakage 때문에 편향이 매우 클 수 있음

---

## 4. H2-2 결과: Four Humor Types → Engagement (ref=affiliative)

### A. Batch1 Human-coded H2-2 (n=648)

| 모델 | 변수 | β | p |
|---|---|---|---|
| H2_2_batch1_simple | aggressive (vs affiliative) | **0.848772** | * |

- n: affiliative=321, self-enhancing=259, aggressive=44, self-defeating=24
- self-defeating: n=24 → **underpowered**

### B. Full-sample Classifier-predicted H2-2 (n=28,177)

| 모델 | 변수 | β | p |
|---|---|---|---|
| H2_2_full_simple | predicted_aggressive (vs pred_affiliative) | **0.101494** | *** |

- n: pred_affiliative=19,101, pred_aggressive=6,857, pred_self-enhancing=1,994, pred_self-defeating=225
- **CRITICAL**: classifier NOT_A_CANDIDATE; 예측 분포가 Wendy's model의 leakage 반영

---

## 5. H3 결과: Aggressive Intensity → Firm Engagement (Inverted-U)

**가설**: Firm의 aggressive humor 사용 강도와 engagement 사이에 역 U자형 관계.

### A. Batch1 Human-coded H3 (n_firms=88, intensity>0=24)

| 모델 | 변수 | β | p | 해석 |
|---|---|---|---|---|
| H3_batch1_quadratic | aggressive_intensity | 1.401675 | 0.650252 | β1 |
| H3_batch1_quadratic | aggressive_intensity_sq | -1.91012 | 0.641874 | β2 |

- Turning point: 0.3669 (범위 내: True)
- Inverted-U check: b1>0_b2<0
- n_firms_with_intensity>0: 24/88
- Interpretation level: preliminary_diagnostic

### B. Full-sample Classifier-predicted H3 (n_firms=97, intensity>0=97)

| 모델 | 변수 | β | p | 해석 |
|---|---|---|---|---|
| H3_full_quadratic | predicted_aggressive_intensity | 9.649312 | 0.01425 | β1 |
| H3_full_quadratic | predicted_aggressive_intensity_sq | -10.252277 | 0.0172 | β2 |

- Turning point: 0.4706 (범위 내: True)
- Inverted-U check: b1>0_b2<0
- n_firms_with_intensity>0: 97/97
- **CRITICAL WARNING**: Type classifier NOT_A_CANDIDATE; intensity 분포 자체가 leakage 영향

---

## 6. 두 Measurement Basis 비교

| 가설 | Batch1 β (인간코딩) | Full β (예측) | 방향 일치 | interpretation_level |
|---|---|---|---|---|
| H1 | 1.214982 | 1.145709 | — | preliminary_diagnostic |
| H2-1 | 0.712293 | 0.083304 | — | preliminary_diagnostic |
| H2-2 (agg) | 0.848772 | 0.101494 | — | preliminary_diagnostic |
| H3 β1 | 1.401675 | 9.649312 | — | preliminary_diagnostic |

---

## 7. 가설별 Interpretation Level

| 가설 | Batch1 verdict | Full-sample verdict | 통합 판단 |
|---|---|---|---|
| H1 | preliminary_supported | preliminary_supported | preliminary_supported (caveat: full IV=predicted) |
| H2-1 | mixed | mixed | mixed (n_agg 부족 / classifier leakage) |
| H2-2 | mixed | mixed | mixed (같은 이유) |
| H3 | preliminary_diagnostic | preliminary_diagnostic | preliminary_diagnostic |

---

## 8. 측정 한계 (Measurement Limitations)

### Batch1 Human-coded 한계
1. **소표본**: H1=1,482 / H2=648 / H3=88 firms — 특히 aggressive n=44 검정력 낮음
2. **선택 편향**: batch1은 전략적 샘플링 (humor posts oversampled) → Fortune 100 전체 대표성 낮음
3. **H3 intensity 불안정**: firm당 labeled 게시물 수가 적어 intensity 추정 불안정 (예: 1개 게시물 firm = intensity 0 또는 1.0)

### Full-sample Classifier-predicted 한계
1. **Classifier NOT_A_CANDIDATE**: aggressive/type classifier leakage 미해결
2. **Source shortcut**: #NationalRoastDay가 rank#1 feature → Wendy's aggressive 집중 예측 편향
3. **H1 measurement error**: predicted label이 IV이면 classical measurement error bias (attenuation 또는 과대 추정)
4. **H2/H3 심각한 편향**: 예측 분포 자체가 leakage 반영 → full H2/H3 결과는 참고용에 불과

### 공통 한계
1. **Omitted variables**: follower 수, account age, posting time 등 미통제
2. **Endogeneity**: engagement 기대 → humor 전략 선택 (역인과 가능)
3. **Temporal clustering**: 회사-시간 serial correlation, company-level clustering 무시 → SE 과소 추정 가능

---

## 9. 금지 사항 준수 확인

- [x] scraping 실행 없음
- [x] Playwright 실행 없음
- [x] X API 실행 없음
- [x] integrated corpus 재분류 없음
- [x] 새 classifier training 없음
- [x] 새 prediction 생성 없음
- [x] data/raw 수정 없음
- [x] dashboard/data 수정 없음
- [x] .github/workflows 수정 없음
- [x] 기존 결과 파일 삭제 없음
- [x] H2/H3 formal supported 선언 없음
- [x] candidate/deployment-ready 선언 없음
- [x] HC3/robust SE 사용 없음 (classical OLS SE만 사용)
- [x] Batch1 human-coded와 full-sample predicted 분리 보고

---

*생성 스크립트*: `run_two_basis_plain_ols_hypotheses.py`
*생성일*: 2026-06-19
*SE type*: Classical OLS (s²×(X'X)⁻¹)
