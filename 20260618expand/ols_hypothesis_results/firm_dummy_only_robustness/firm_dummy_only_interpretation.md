# H1/H2/H3 기업 Dummy Only Robustness 분석

**생성일**: 2026-06-19
**기준 commit**: 1926e25 (two-basis plain OLS)
**SE 유형**: Classical OLS (s²×(X'X)⁻¹) — HC3/robust SE 미사용
**분석 성격**: PRELIMINARY ROBUSTNESS CHECK ONLY

---

## 1. 분석 목적

기존 1926e25 two-basis plain OLS (통제 변수 없음, 시간 FE 없음) 결과를 기준으로,
기업별 불변 특성(firm-level fixed effects)을 통제했을 때 H1/H2/H3 핵심 계수의
방향과 유의성이 유지되는지 확인한다.

---

## 2. 기업 dummy를 넣는 이유

기업별로 규모(팔로워 수), 산업, 브랜드 전략, 콘텐츠 스타일 등이 다르다.
이 기업 고유 특성들이 모두 humor 전략과 engagement에 동시에 영향을 미칠 수 있다.
Plain OLS (기업 통제 없음)에서는 이 기업 수준 confounders가 추정에 들어간다.
기업 dummy를 추가하면 기업 내(within-firm) 또는 기업 간(between-firm) variation에서
humor의 영향을 분리할 수 있다.

---

## 3. company_id 생성 방식

1. 모든 분석 파일에서 `company_name` 컬럼을 수집
2. 전체 unique company_name을 알파벳 오름차순으로 정렬
3. 순번(1, 2, 3...)을 company_id로 부여
4. 총 99개 기업이 등록됨
5. 결과 파일: `firm_dummy_company_id_map.csv`

---

## 4. 기준 기업 선택 방식

각 분석 데이터셋 내에서 관측치가 가장 많은 기업을 기준 기업(reference firm)으로 선택.
기준 기업의 dummy를 제외함으로써 다중공선성(perfect collinearity)을 방지한다.

| 분석 | 기준 기업 | 관측치 |
|---|---|---|
| Batch1 H1 | Home Depot | n_obs=1482 |
| Full H1   | General Dynamics | n_obs=68039 |
| Batch1 H2 | Walt Disney | n_obs=648 |
| Full H2   | Home Depot | n_obs=28177 |
| Full H3   | Home Depot | n_periods=3532 |

---

## 5. dummy variable 생성 방식

1. 각 데이터셋에서 unique company_name 추출
2. 기준 기업 제외 후 나머지를 `firm_dummy_{company_id}` 컬럼으로 생성
3. 해당 행의 company_name이 일치하면 1, 아니면 0으로 인코딩
4. X 행렬 = [intercept | focal_IV(s) | firm_dummy_2 | firm_dummy_3 | ...]
5. k_effective = 1 (intercept) + n_focal_IVs + (n_firms - 1)

---

## 6. company_id numeric covariate 미사용 확인

- **firm_dummy_included** = true
- **company_id_used_as_numeric** = false — company_id를 연속형 공변량으로 넣지 않음
- 이는 "기업 번호가 클수록 engagement가 다르다"는 잘못된 가정을 피하기 위함

---

## 7. C(company_id) 미사용 확인

- **c_company_formula_used** = false
- statsmodels formula API (`C(company_id)`)를 사용하지 않음
- 명시적 binary dummy column을 직접 생성하여 OLS에 포함

---

## 8. 시간 고정효과 미포함 확인

- **time_fe_included** = false
- year, month, week, day, hour FE 전혀 포함하지 않음
- 시간 FE는 별도 robustness 파일(`time_fixed_effects_robustness/`)에서 다룸

---

## 9. 기본 controls 미포함 확인

- **controls_included** = false
- text_length, hashtag_count, mention_count 등 미포함
- 이번 분석은 오직 "핵심 IV + 기업 dummy"만 포함

---

## 10. H1 결과

**가설**: 유머 post → 더 높은 engagement

| | Batch1 Human-coded | Full-sample Predicted |
|---|---|---|
| N | 1482 | 68039 |
| N_firms | 97 | 99 |
| N_dummies | 96 | 98 |
| β(humor) | **0.240636** | **0.202458** |
| SE | 0.084375 | 0.012171 |
| t | 2.852 | 16.6342 |
| p | 0.004409 | 0.0 |
| 판정 | *** | *** |
| Adj R² | 0.712805 | 0.623886 |
| ref 기업 | Home Depot | General Dynamics |

비교 (1926e25 plain OLS): Batch1=1.214982*** / Full=1.145709***

---

## 11. H2-1 결과

**가설**: Aggressive humor → other humor보다 높은 engagement

| | Batch1 Human-coded (n_agg=44) | Full-sample Predicted |
|---|---|---|
| N | 648 | 28177 |
| N_firms | 88 | 97 |
| β(aggressive) | **0.118795** | **-0.101486** |
| SE | 0.276753 | 0.017216 |
| p | 0.667911 | 0.0 |
| 판정 | ns | *** |

비교 (1926e25): Batch1=0.712293* / Full=0.083304***

주의:
- Batch1: n_agg=44 → 검정력 낮음 + 기업 dummy 추가 시 SE 증가
- Full: classifier NOT_A_CANDIDATE (#NationalRoastDay leakage); type prediction 신뢰도 낮음

---

## 12. H2-2 결과

**가설**: Four humor types 비교 (ref=affiliative)

| | Batch1 (인간 코딩) | Full (예측값) |
|---|---|---|
| β(aggressive) | **0.20598** | **-0.111675** |
| stars(agg) | ns | *** |
| β(self_enhancing) | 0.085896 | -0.090349 |
| β(self_defeating) | 0.562923 | -0.110542 |
| N | 648 | 28177 |

비교 (1926e25 agg): Batch1=0.848772* / Full=0.101494***

---

## 13. H3 결과

**가설**: Firm aggressive intensity → engagement (역 U자형)

| | Batch1 (기업 단면) | Full (기업-월 패널) |
|---|---|---|
| 상태 | **not_applicable** | success |
| 이유 | firm cross-section: n=88, n_dummies=87 → rank deficient | firm-month panel: n=3532, firms=97 |
| β1 (intensity) | — | **-2.072017** *** |
| β2 (intensity_sq) | — | **2.939911** *** |
| turning point | — | 0.3524 |
| in_range | — | True |
| N_firms | — | 97 |
| Adj R² | — | 0.771721 |

비교 (1926e25): Batch1=β1=1.401675 ns / Full=β1=9.649312* β2=-10.252277*

---

## 14. 기존 plain OLS와 비교

| 가설 | Basis | 1926e25 β | 기업 dummy β | 방향 유지 | 유의성 변화 |
|---|---|---|---|---|---|
| H1 | Batch1 | 1.214982*** | 0.240636*** | yes | — |
| H1 | Full | 1.145709*** | 0.202458*** | yes | — |
| H2-1 | Batch1 | 0.712293* | 0.118795ns | yes | — |
| H2-1 | Full | 0.083304*** | -0.101486*** | no | — |
| H2-2 | Batch1 | 0.848772* | 0.20598ns | — | — |
| H2-2 | Full | 0.101494*** | -0.111675*** | — | — |
| H3 β1 | Batch1 | 1.401675 (β1) | not_applicable | — | — |
| H3 β1 | Full | 9.649312 (β1) | -2.072017*** | — | — |

---

## 15. 기업 dummy 추가 후 가장 안정적인 가설

**H1**이 가장 안정적으로 예상:
- 양 basis에서 계수 방향 양수 유지
- Full H1은 n=68,039으로 기업 dummy(~98개) 추가 후에도 충분한 검정력

---

## 16. 기업 dummy 추가 후 가장 민감한 가설

**H2 Batch1**이 가장 민감:
- n_agg=44의 낮은 검정력 + firm dummies(87개) 추가 → SE 증가
- H3 Batch1은 구조적으로 불가능(firm cross-section)

---

## 17. Limitation

1. **H3 Batch1**: firm cross-section에서 firm dummy 불가 → 기업 고정효과 통제 없음
2. **Full H2/H3**: classifier NOT_A_CANDIDATE; 예측 레이블 자체에 leakage 존재
3. **Batch1 H2-1**: n_agg=44 → firm dummy 추가 시 검정력 급감 가능
4. **기업 간 variation 흡수**: firm dummy는 기업 간 차이를 통제하지만, within-firm temporal dynamics는 미통제
5. **Measurement error**: Full H1 IV = classifier predicted label → attenuation bias 가능

---

## 18. 다음 판단 지점

1. H1 양 basis에서 기업 dummy 후에도 양수 + 유의 → H1 firm-level confound 제거 후에도 유지
2. H2 Batch1 firm dummy 추가 후 유의성 유지 여부 → 기업 효과가 H2 추정에 얼마나 영향 주는지
3. H3 Full (firm-month panel): β1>0, β2<0 패턴이 firm FE 후에도 유지되는지 → within-firm inverted-U
4. 향후 고려: company-level clustered SE (별도 robustness), time FE + firm FE 동시 포함

---

## 19. 금지사항 준수

- [x] 시간 고정효과 미포함 (time_fe_included = false)
- [x] year/month/week/day/hour FE 없음
- [x] text_length/hashtag_count/mention_count controls 없음
- [x] C(company_id) 미사용 (c_company_formula_used = false)
- [x] company_id numeric covariate 미사용 (company_id_used_as_numeric = false)
- [x] backfill/workflow 파일 미수정
- [x] 기존 1926e25 결과 파일 삭제/덮어쓰기 없음
- [x] 기존 time FE 결과 파일 삭제/덮어쓰기 없음
- [x] HC3/robust SE 미사용 (Classical OLS SE만)
- [x] 새 prediction/classifier 없음
- [x] H2/H3 formal supported 미선언

---

*생성 스크립트*: `run_firm_dummy_only_robustness.py`
*출력 폴더*: `firm_dummy_only_robustness/`
*생성일*: 2026-06-19
