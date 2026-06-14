# Humor Hypothesis Variable Construction Plan

## A. 연구 목적

이 문서는 브랜드 SNS humor classification 결과를 **H1-H3 가설 검증용 회귀 변수**로 변환하는 과정을 정의한다.

현재 humor classification 작업의 목적은:
- Descriptive evidence 또는 dashboard 구축이 **아니다**.
- Measurement-validity step이다: v1 full-chain 분류 결과를 firm-period 수준의 regression-ready 독립변수로 변환한다.

**Regression unit**: `company_name × period (YYYY-MM)`. 이것이 분석의 관측 단위다. 하나의 기업이 같은 월에 복수의 X 계정(`source_x_handle`)을 운용하는 경우, 모든 계정의 포스트 카운트를 합산하여 **1개의 firm-period 행**으로 집약한다. `source_x_handle_list`와 `source_x_handle_count`가 어떤 계정이 합산되었는지를 기록한다.

가설:

> **H1.** 브랜드의 SNS에서 활용되는 Humor는 Brand Equity를 증가시킬 것이다.
>
> **H2.** Aggressive Humor가 다른 Humor Type보다 Brand Equity에 미치는 영향이 더 클 것이다.
>
> **H3.** Aggressive Humor Usage Intensity는 Aggressive Humor가 Brand Equity에 미치는 영향을 역 U자형으로 조절할 것이다.

---

## B. 가설별 변수 연결

| 가설 | 핵심 독립변수 / 조절변수 | 비고 |
|------|--------------------------|------|
| H1 | `humor_share`, `humor_count`, `log_humor_count`, `humor_presence_any` | Humor 사용 여부 및 강도 |
| H2 | `aggressive_share`, `affiliative_share`, `self_enhancing_share`, `self_defeating_share` | Type별 상대적 효과 비교 |
| H3 | `aggressive_humor_usage_intensity`, `aggressive_humor_usage_intensity_sq` | 역 U자형 조절 검증용 squared term |

**H3 intensity 정의 주의사항**: `aggressive_humor_usage_intensity`는 메시지 수준의 주관적 강도(semantic intensity)가 아니다. 이것은 **firm-period 수준의 사용 강도(usage intensity)**, 즉 해당 기업의 전체 포스트 중 aggressive humor 포스트의 비율(`aggressive_count / total_posts`)이다.

**Rare class 희소성 주의**: aggressive(전체 68k 기준 ~105건)와 self_defeating(~41건)는 firm-period 수준에서 거의 대부분의 셀이 0이다. `h3_sparsity_diagnostics` manifest 필드에서 `nonzero_aggressive_firm_period_count`와 `aggressive_intensity_zero_share`를 확인한 뒤 분석 전략(zero-inflated model 등)을 결정해야 한다.

---

## C. H1 변수 정의

| 변수 | 정의 | Ambiguity 처리 |
|------|------|----------------|
| `humor_count` | `COUNT(humor_presence == 'humor')` | ambiguous 포함 안 됨 |
| `humor_share` | `humor_count / total_posts` | conservative (ambiguous → 분자에 0) |
| `log_humor_count` | `log(1 + humor_count)` | conservative |
| `humor_presence_any` | `1 if humor_count > 0` | conservative |
| `humor_share_ambiguity_as_zero` | `humor_count / total_posts` | ambiguous를 non-humor로 명시 처리 |
| `humor_share_ambiguity_excluded` | `humor_count / (humor_count + non_humor_count)` | ambiguous 행을 분자/분모에서 제외 |
| `humor_share_ambiguity_as_missing` | ambiguity_rate < 0.50 이면 humor_share, 그 외 NA | 고-ambiguity 기업-기간 결측 처리 |

---

## D. H2 변수 정의

| 변수 | 정의 | 해석 |
|------|------|------|
| `affiliative_count` | `COUNT(humor_type == 'affiliative')` | 포용적 유머 |
| `self_enhancing_count` | `COUNT(humor_type == 'self_enhancing')` | 자기 긍정적 유머 |
| `aggressive_count` | `COUNT(humor_type == 'aggressive')` | 공격적 유머 (rare class, 탐색적) |
| `self_defeating_count` | `COUNT(humor_type == 'self_defeating')` | 자기비하 유머 (very rare, 탐색적) |
| `{type}_share` | `{type}_count / total_posts` | 전체 포스트 대비 비율 |
| `aggressive_minus_other_humor_share` | `aggressive_share − (affiliative_share + self_enhancing_share + self_defeating_share)` | Aggressive 유머의 상대적 우세 |
| `rare_negative_humor_count` | `aggressive_count + self_defeating_count` | 두 희귀 클래스 통합 (표본 크기 확보용) |
| `rare_negative_humor_share` | `rare_negative_humor_count / total_posts` | 통합 희귀 클래스 비율 |
| `v2_aggressive_candidate_count` | v2가 aggressive으로 분류한 행 수 (company-level, 진단용) | Production label 아님 |

### H2 회귀 설계 및 공선성 주의

H2의 type-share 변수는 모두 `type_count / total_posts`로 정의된다. 따라서 네 개의 type-share 합은 항상 1이 아니라 `humor_share`와 같아진다.

```text
aggressive_share
+ affiliative_share
+ self_enhancing_share
+ self_defeating_share
= humor_share
```

이에 따라 H2 회귀모형에서는 다음 원칙을 적용한다.

- 4개 type-share 변수를 모두 투입하는 경우, `humor_share`를 같은 회귀식에 동시에 포함하지 않는다.
- `humor_share`를 별도로 통제해야 하는 경우, 4개 type-share 중 하나를 reference category로 제외한다.
- 기본 reference category 후보는 `affiliative_share`이다. Affiliative humor는 사회적 유대와 친화성을 나타내는 상대적으로 표준적인 positive humor baseline으로 해석할 수 있기 때문이다.
- H2의 핵심 검정은 단순히 `aggressive_share` 계수의 유의성만 보는 것이 아니라, type-share 계수 간 차이 검정으로 수행한다.

예상 검정:

```text
H0: β_aggressive = β_affiliative
H0: β_aggressive = β_self_enhancing
H0: β_aggressive = β_self_defeating
```

권장 진단:

- H2 회귀 전 type-share 변수 간 correlation matrix를 확인한다.
- H2 회귀 후 VIF 또는 equivalent collinearity diagnostics를 확인한다.
- `aggressive`와 `self_defeating`은 rare class이므로, `rare_negative_humor_share`를 보조 분석 변수로 유지한다.
- `v2_aggressive_candidate_count`는 label 보정 변수가 아니라 disagreement/candidate diagnostic 변수로만 사용한다.

---

## E. H3 변수 정의

| 변수 | 정의 | H3에서의 역할 |
|------|------|--------------|
| `aggressive_humor_usage_intensity` | `aggressive_count / total_posts` | H3 조절변수 (주) |
| `aggressive_humor_usage_intensity_sq` | `(aggressive_count / total_posts)²` | 역 U자형 검증용 (음수 계수 기대) |
| `log_aggressive_count` | `log(1 + aggressive_count)` | 로그 변환 (분포 왜도 보정) |
| `aggressive_presence_any` | `1 if aggressive_count > 0` | 이항 처리변수 |
| `aggressive_share_ambiguity_excluded` | `aggressive_count / (humor_count + non_humor_count)` | Robustness 조절변수 |
| `rare_negative_humor_usage_intensity` | `(aggressive + self_defeating) / total_posts` | H3 robustness (통합 희귀 클래스) |
| `rare_negative_humor_usage_intensity_sq` | 위의 제곱 | Robustness 역 U자형 |

### Interaction-ready 변수

| 변수 | 공식 | 목적 |
|------|------|------|
| `humor_share_x_aggressive_intensity` | `humor_share × aggressive_humor_usage_intensity` | H1 × H3 교호작용 |
| `humor_share_x_aggressive_intensity_sq` | `humor_share × aggressive_humor_usage_intensity_sq` | H1 × H3 역 U자형 교호작용 |
| `aggressive_presence_x_aggressive_intensity` | `aggressive_presence_any × aggressive_humor_usage_intensity` | 이항 × 연속형 교호작용 |
| `aggressive_presence_x_aggressive_intensity_sq` | `aggressive_presence_any × aggressive_humor_usage_intensity_sq` | 이항 × 제곱 교호작용 |

> 회귀 분석 전 두 구성 변수를 평균 중심화(mean-centering)한 후 교호작용 항을 계산하는 것을 권장한다.

---

## F. Ambiguity Handling 기준

| 처리 방식 | 공식 | 권장 용도 |
|-----------|------|-----------|
| `conservative` (기본) | ambiguous = non-humor로 처리 (분자: 0, 분모: 포함) | 주 분석 |
| `ambiguity_as_zero` | conservative와 동일, 명시적 레이블 | 민감도 분석 레이블용 |
| `ambiguity_excluded` | ambiguous 행을 분자/분모 모두 제거 | 강건성 검증 |
| `ambiguity_as_missing` | ambiguity_rate ≥ 0.50이면 NA | 극단적 ambiguity 제거 |

`high_ambiguity_flag == 1` (ambiguity_rate ≥ 0.50)인 기업-기간은 주 분석에서 제외하거나 robustness 확인용으로 유지할 수 있다.

---

## G. v2 사용 규칙

- **v2는 production classifier가 아니다.**
- v2는 disagreement detector / candidate generator로만 사용한다.
- v2 label을 production label로 쓰지 않는다.
- v2 candidate count는 company-level diagnostic flag로만 사용한다 (period-specific 아님).
- v2 label이 v1보다 더 정확하다는 의미가 아니다.
- 전체 68,020 rows를 v2로 재분류하지 않는다.
- `v2_aggressive_candidate_count`는 A/B 941-row 샘플 기준 회사 수준 합계이며, 개별 기업-기간에 반복 기재된다.

---

## H. Limitations (한계)

| 한계 | 설명 |
|------|------|
| No human label | 현재 모든 변수는 v1 operational label이다. 정확도를 측정할 기준이 없다. |
| No gold-label performance claim | Precision, Recall, F1 측정 불가. v1이 "정답"이라는 의미가 아니다. |
| No accuracy / precision / recall | Human adjudication 없이 성능 주장 불가. |
| Rare class exploratory only | aggressive (105/68k), self_defeating (41/68k)는 탐색적 증거로만 해석. |
| Calibration deferred | Cue/threshold adjustment는 human review 완료 후에만 가능. |
| High ambiguity burden | 전체의 ~48%가 ambiguous_or_review. 특히 firm-period 수준에서 일부는 50.5%가 high_ambiguity_flag. |
| v2 not period-specific | v2 candidate count는 기간 구분 없는 회사 수준 집계. 기간별 정보 없음. |

---

## I. 산출물 목록

`Build Humor Hypothesis Variables` workflow 실행 시 생성:

| 파일 | 내용 |
|------|------|
| `data/derived/humor/hypothesis_variables/humor_firm_period_hypothesis_variables.csv` | 전체 H1/H2/H3 변수. **Unique key: `company_name × period`.** 복수 핸들은 합산. `source_x_handle_count`, `source_x_handle_list` 컬럼 포함. |
| `data/derived/humor/hypothesis_variables/humor_h1_variables.csv` | H1 전용 서브셋 (full과 동일 row 수) |
| `data/derived/humor/hypothesis_variables/humor_h2_type_variables.csv` | H2 전용 서브셋 (full과 동일 row 수) |
| `data/derived/humor/hypothesis_variables/humor_h3_intensity_variables.csv` | H3 전용 서브셋 (full과 동일 row 수) |
| `data/derived/humor/hypothesis_variables/humor_variable_dictionary.csv` | 변수 코드북 (38개 변수) |
| `data/audit/humor/hypothesis_variables/humor_hypothesis_variables_manifest.json` | 실행 manifest. `company_period_duplicate_count`, `source_x_handle_collapsed`, `h3_sparsity_diagnostics` 포함. |

---

## J. 다음 단계

```
[현재] Hypothesis variable construction (firm-period 변수 생성)
  ↓
[선택] Brand Equity 종속변수 데이터 확보 및 조인
  ↓
[선택] Descriptive statistics by hypothesis group
  ↓
[보류] Human review (346-row priority sample 수동 라벨링)
  ↓
[보류 후 가능] Rare class 검증 → cue/threshold calibration
  ↓
[보류 후 가능] H1-H3 regression analysis
```