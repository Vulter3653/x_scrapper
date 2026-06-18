# H1/H2/H3 단순 OLS Preliminary Results — Interpretation

**생성일**: 2026-06-18  
**분석 성격**: PRELIMINARY DIAGNOSTIC ONLY — 최종 가설 검증이 아님  
**대상**: Fortune 100 전체 (Wendy's-only 제외)  
**분류기 상태**: NOT_A_CANDIDATE (aggressive/type classifier leakage 미해결)

---

## 1. 분석 목적

현재 사용 가능한 데이터와 기존 prediction output 기반으로 H1, H2, H3의 방향성을 preliminary하게 확인한다.  
분류기 measurement validity 문제가 미해결 상태이므로 어떤 결과도 최종 가설 지지/기각으로 해석하지 않는다.

---

## 2. 사용 데이터

| 분석 | 파일 | n | Label 종류 |
|---|---|---|---|
| H1 | `fortune100_h1_presence_classified_posts.csv` | 65,245 posts | **PREDICTED** (H1 classifier t=0.50) |
| H2, H3 | `type_training_leakage_filtered_variants.csv` (batch1_fortune100만) | 648 posts / 88 firms | **HUMAN-CODED** |
| H3 DV | `fortune100_h1_presence_classified_posts.csv` (firm-level 집계) | 88 firms | 실측 engagement |

- **H1 IV는 모델 예측값** — 분류기 오분류가 OLS coefficient에 measurement error bias를 발생시킴
- **H2/H3 type label은 인간 코딩** — batch1_fortune100 humor posts (48 명, 재코딩 후 최종값)
- Wendy's legacy data(977 posts), MoonPie(930), Coca-Cola(708)은 분석에서 **제외**
- 564개 model-predicted type rows는 **training label로 사용하지 않음** (분석 대상에 포함 안 됨)

---

## 3. H1 결과: Humor presence → Engagement

**가설**: Humor presence는 post-level engagement에 긍정적 영향을 미친다.

| 모델 | 변수 | Coefficient | Robust SE (HC3) | t | p | stars |
|---|---|---|---|---|---|---|
| H1_simple | humor_presence_pred_t50 | **0.9551** | 0.0167 | 57.28 | < 0.001 | *** |
| H1_simple | intercept | 3.0713 | 0.0089 | 345.2 | < 0.001 | *** |
| H1_simple_controls | humor_presence_pred_t50 | **0.9988** | 0.0175 | 57.22 | < 0.001 | *** |

- n = 65,245 / R² ≈ 0.065 (simple), 0.069 (controls)
- 종속변수: log1p(total_engagement) / 통제변수: text_length, hashtag_count, mention_count
- hashtag_count는 유의한 부적 관계 (controls model)

**해석 (interpretation_level = preliminary_diagnostic)**:

Humor presence 예측값(t=0.50)이 log engagement와 강하게 정적으로 연관됨(β=0.955, ***).  
e^0.955 ≈ 2.6배 차이로, 예측된 humor posts는 non-humor posts보다 평균적으로 약 2.6배 높은 engagement.

**그러나**: H1 IV가 classifier predicted label이므로 이 결과는 classifier가 높은 engagement posts를 humor로 예측하는 경향을 반영할 수 있음. 즉, reverse causality 또는 correlated predictor error의 가능성을 배제할 수 없음.

**Preliminary verdict**: `preliminary_supported` — 방향성은 가설과 일치하나 measurement limitation으로 인해 최종 지지 불가.

---

## 4. H2-1차 결과: Aggressive vs Other Humor → Engagement

**가설**: Aggressive humor는 other humor보다 engagement에 더 강한 긍정적 영향을 미친다.

| 모델 | 변수 | Coefficient | Robust SE (HC3) | t | p | stars |
|---|---|---|---|---|---|---|
| H2_1_simple | aggressive_vs_other | **0.7123** | 0.4277 | 1.666 | 0.096 | * |
| H2_1_simple | intercept | 4.3918 | 0.1101 | 39.88 | < 0.001 | *** |
| H2_1_simple_controls | aggressive_vs_other | 0.6494 | 0.4254 | 1.526 | 0.127 | ns |
| H2_1_simple_controls | hashtag_count | −0.4122 | 0.1206 | −3.42 | < 0.001 | *** |

- n = 648 (aggressive: 44, other: 604) / R² ≈ 0.004 (simple), 0.022 (controls)
- 종속변수: log1p(total_engagement) / label: HUMAN-CODED batch1_fortune100
- **Label source: 인간 코딩** — measurement error 상대적으로 낮음

**해석 (interpretation_level = preliminary_diagnostic)**:

단순 모델(p=0.096, *)에서 aggressive humor가 other humor보다 log engagement 0.71 높음.  
통제 후(p=0.127)는 유의성 상실. aggressive posts: n=44 (전체 648 중 6.8%) — 통계적 검정력 부족.

**주의**: H2-1의 n_aggressive=44는 충분한 검정력을 제공하지 않음. 통제 후 유의성이 사라지는 것은 표본 크기 문제일 수 있음(β 방향성은 유지됨).

**Preliminary verdict**: `mixed` — 방향성은 가설과 일치, p<0.10 (simple model), 통제 후 유의성 상실. 추가 데이터 필요.

---

## 5. H2-2차 결과: Four Humor Types → Engagement (ref=affiliative)

| 모델 | 변수 | Coefficient | Robust SE (HC3) | t | p | stars |
|---|---|---|---|---|---|---|
| H2_2_four_type_simple | **aggressive** | **0.8488** | 0.4386 | 1.935 | 0.053 | * |
| H2_2_four_type_simple | self_enhancing | 0.2376 | 0.2253 | 1.055 | 0.292 | ns |
| H2_2_four_type_simple | self_defeating | 0.8704 | 0.6845 | 1.272 | 0.204 | ns |
| H2_2_four_type_controls | **aggressive** | **0.7606** | 0.4387 | 1.733 | 0.083 | * |

- n=648, type counts: affiliative=321, self-enhancing=259, aggressive=44, self-defeating=24
- R² ≈ 0.007 (simple), 0.022 (controls)
- Self-defeating: n=24 → **underpowered**

**Pairwise mean log-engagement 비교** (ref=log1p 기준):

| 비교 | Mean Diff (log) | 해석 |
|---|---|---|
| aggressive vs affiliative | **+0.849** | aggressive가 약 e^0.849 ≈ 2.3배 |
| aggressive vs self-enhancing | **+0.611** | aggressive가 약 e^0.611 ≈ 1.8배 |
| aggressive vs self-defeating | −0.022 | 차이 없음 (self-defeating n=24, underpowered) |

**Intercept (= affiliative mean)** = 4.255 → e^4.255 ≈ 70.4 mean engagement (raw scale에서의 median-adjusted 해석 필요)

**해석 (interpretation_level = preliminary_diagnostic)**:

Aggressive humor가 affiliative 기준 대비 가장 높은 coefficient(β=0.849, p=0.053, *)를 보임.  
Self-defeating vs affiliative 차이는 유사한 방향(+0.870)이나 n=24로 완전히 underpowered.  
Controls 포함 시 aggressive p=0.083(*) — 약한 유의성 유지.

**Preliminary verdict**: `mixed` — aggressive coefficient가 양수이고 marginally significant, 그러나 표본 크기(n_agg=44, n_sd=24) 및 classifier leakage 한계로 인해 preliminary.

---

## 6. H3 결과: Aggressive Intensity → Firm Engagement (Inverted U)

**가설**: Aggressive humor usage intensity와 engagement 사이에 역 U자형 관계.

| 모델 | 변수 | Coefficient | Robust SE (HC3) | t | p | stars |
|---|---|---|---|---|---|---|
| H3_linear_only | aggressive_intensity | 1.3668 | 1.2410 | 1.101 | 0.274 | ns |
| H3_quadratic | **aggressive_intensity** | **4.2034** | 4.7830 | 0.879 | 0.382 | ns |
| H3_quadratic | **aggressive_intensity_sq** | **−4.2146** | 10.9493 | −0.385 | 0.701 | ns |

- n_firms = 88 / n_firms_with_aggressive_intensity > 0 = **24** (64 firms = intensity 0)
- intensity range: 0.0 – 1.0 (Goldman Sachs = 1.0, 1개 labeled post에서 aggressive)
- Turning point = **−4.20 / (2 × −4.21) = 0.499** — 관측 범위 내
- R² ≈ 0.012 (linear), 0.013 (quadratic)

**해석 (interpretation_level = preliminary_diagnostic / 실질적 NOT_INTERPRETABLE)**:

수치적으로 b1>0, b2<0 (역 U 패턴)이 확인되고 turning point(0.50)가 범위 내에 있으나:
- **두 계수 모두 비유의적** (p=0.38, p=0.70)
- 64/88 firms (73%)의 intensity=0 → 사실상 이진 구분에 가까움
- Goldman Sachs처럼 1개 labeled humor post에서 aggressive → intensity=1.0은 매우 불안정한 추정

**Preliminary verdict**: `NOT_INTERPRETABLE` — 수치 패턴은 가설과 일치하나 통계적 검정력 완전 부족. 최소 20–30개 firm에 안정적인 aggressive humor posts 분포 필요.

---

## 7. 가설별 해석 가능 수준 (interpretation_level)

| 가설 | interpretation_level | preliminary_verdict |
|---|---|---|
| H1 | preliminary_diagnostic | preliminary_supported (**caveat: IV는 예측값**) |
| H2-1 | preliminary_diagnostic | mixed (simple p<.10, controls ns; n_agg=44 부족) |
| H2-2 | preliminary_diagnostic | mixed (aggressive marginally significant, self-defeating underpowered) |
| H3 | NOT_INTERPRETABLE | NOT_INTERPRETABLE (b1/b2 모두 비유의적, 64/88 firms intensity=0) |

---

## 8. Measurement Limitation

### H1 IV Measurement Error
- `h1_humor_presence_pred_t50`는 classifier predicted label (binary)
- Classifier AUC ≈ 0.82 — false positive / false negative 존재
- 예측값을 IV로 사용하면 attenuation bias 또는 correlated error 발생 가능
- 실제 coefficients는 true humor presence와의 correlation 수준에 따라 달라짐
- **가장 중요한 limitation**: classifier가 engagement가 높은 특성(감정 표현, 비공식 언어 등)을 humor로 분류하면 β 과대 추정

### H2/H3 Small Sample
- batch1_fortune100 human-coded type labels: 총 648 posts / 88 firms
- aggressive: 44 posts, self-defeating: 24 posts → 검정력 부족
- Fortune 100 표본에서 aggressive humor frequency가 낮음 (6.8%)

### H3 Firm-level Aggregation
- 88 firms의 aggressive intensity 중 64개 = 0.0 (이분 분포)
- 소수 labeled posts에서 intensity 계산 → 극단값 불안정 (Goldman Sachs: 1.0 = 1/1)
- Labeled sample은 full corpus의 일부 (engagement-based 또는 random sampling)

---

## 9. Classifier Limitation

### H1 Classifier (h1_humor_presence)
- Training: batch1_fortune100 human-coded labels + Wendy's human labels (1,482 posts expanded)
- 최근 leakage audit에서 Wendy's-specific tokens (wendy, wendys) 등이 top features임 확인
- Fortune 100 corpus 적용 시: source-specific leakage 영향이 상대적으로 낮을 수 있으나 미검증

### H2/H3 Type Classifier
- **현재 classifier_status: NOT_A_CANDIDATE**
- Aggressive binary detector: leakage_flag=FAIL (모든 6 variants)
- Source held-out F1=0.0 (train_batch1_test_wendys and vice versa)
- `#NationalRoastDay` = rank #1 leakage feature (source shortcut 판정 완료)
- **따라서 H2/H3는 classifier predicted type을 사용하지 않고, human-coded labels만 사용함**
  — 이 선택으로 측정 validity는 개선되지만 표본 크기 제약 발생

---

## 10. Why Results Should Not Yet Be Treated as Final Causal Evidence

1. **IV measurement error (H1)**: Predicted humor label이 IV이므로 비고전적 측정오차 발생. true β와 관측 β 사이에 체계적 편향 가능.

2. **Omitted variable bias**: 회사 크기, follower 수, 계정 인지도, 게시 시간 등 중요 통제변수 미포함. 단순 OLS는 omitted variable에 취약.

3. **Endogeneity**: Engagement가 높을 것으로 예상되는 상황에서 aggressive humor를 사용할 가능성 (strategic selection). Humor → Engagement가 아닌 Engagement expectation → Humor 방향일 수 있음.

4. **Temporal structure 무시**: Post-level OLS가 serial correlation (같은 회사의 연속 게시물) 및 company-level clustering을 무시함. Standard errors가 과소 추정될 수 있음.

5. **Sample representativeness**: batch1_fortune100 648 posts는 전략적 샘플링 (humor posts oversample)이므로 Fortune 100 전체 모집단을 대표하지 않음.

6. **H3 근본 문제**: Aggressive intensity 변수가 labeled 648 posts에서만 계산되어 회사 전체 행동을 대표하지 못함. 실제 회사의 aggressive humor 전략을 반영하지 않을 수 있음.

---

## 11. Next Decision Point

| 우선순위 | 조치 | 목적 |
|---|---|---|
| 1 | aggressive type labels 추가 수집 (Fortune 100, 최소 150+ aggressive posts) | H2/H3 검정력 확보 |
| 2 | H1 classifier leakage audit 완료 및 최종 validation | H1 IV 신뢰성 개선 |
| 3 | H3용 firm-level panel 구성 (firm × year 또는 firm × quarter) | H3 inverted-U 재검증 |
| 4 | Clustered standard errors (company-level) 적용 | 통계 타당성 개선 |
| 5 | 통제변수 추가 (follower_count, account_age, posting_time) | 추정 편향 감소 |

**Current action**: 위 제약 조건을 명확히 기록하고, preliminary direction 확인 후 classifier 개선 및 labeling 우선순위 결정에 활용한다.

---

*생성 스크립트*: `run_simple_ols_hypotheses.py`  
*candidate_status*: NOT_A_CANDIDATE (type/aggressive classifier)  
*prohibited_actions*: 모두 준수 (scraping/reclassification/new labeling/workflow 수정 없음)
