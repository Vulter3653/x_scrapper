# H1/H2/H3 기업 Dummy + 시간 고정효과 Robustness 분석

**생성일**: 2026-06-19
**기준 commit**: 99e915b (firm dummy only)
**SE 유형**: Classical OLS (s²×(X'X)⁻¹) — HC3/robust SE 미사용
**분석 성격**: PRELIMINARY ROBUSTNESS CHECK ONLY

---

## 1. 분석 목적

기업별 불변 특성(firm FE)과 시간별 공통 충격(time FE)을 동시에 통제했을 때
H1/H2/H3 핵심 계수의 방향과 유의성이 유지되는지 확인한다.

Plain OLS → time FE only → firm dummy only 순서로 robustness를 쌓아왔으며,
이번 분석은 두 FE를 동시에 포함하는 가장 엄격한 버전이다.

---

## 2. 기업 dummy와 시간 FE를 함께 넣는 이유

- **Firm FE**: 기업 규모, 산업, 브랜드 전략 등 시간 불변 특성 통제
- **Time FE**: 경제 상황, 플랫폼 알고리즘 변화 등 모든 기업에 공통된 시간적 충격 통제
- 두 FE를 동시에 통제하면 순수하게 "동일 기업 내에서, 같은 시간 환경 내에서"
  humor 전략의 효과를 추정하는 것에 가까워진다.

---

## 3. company_id 생성 방식

총 99개 기업 등록; 알파벳 오름차순 ID 부여.
결과 파일: `firm_time_fe_company_id_map.csv`

---

## 4. 기업 dummy 생성 방식

- 각 데이터셋에서 관측치가 가장 많은 기업을 기준 기업으로 선택
- 기준 기업 dummy 제외 → (n_firms - 1)개 dummy 생성
- **FWL(Frisch-Waugh-Lovell) 정리 기반 within-cell demeaning으로 동일한 효과 달성**
  (명시적 dummy matrix 생성 없이 pandas groupby로 수학적 동치 결과)

---

## 5. 시간 FE dummy 생성 방식

- 30개 FE 조합: C(5, 1..4) of {year, month, week, day, hour}
- Joint cell = (firm_name, time_fe_label) 형식의 복합 셀 생성
- pandas groupby transform으로 셀 내 평균 차감 (단일 pass, FWL 동치)
- k_eff = k_focal + n_joint_cells + 1 (보수적 자유도 계산)
- Singleton cell(관측치 1개짜리 셀) 자동 흡수 → effective within-obs만 추정에 기여

---

## 6. 기본 controls 미포함 확인

- **controls_included** = false
- text_length, hashtag_count, mention_count 미포함

---

## 7. company_id numeric covariate 미사용 확인

- **company_id_used_as_numeric** = false

---

## 8. C(company_id) 미사용 확인

- **c_company_formula_used** = false

---

## 9. H1 결과 (firm dummy + time FE)

**가설**: 유머 post → 더 높은 engagement

### Year FE 기준 (firm_dummy_year)

| | Batch1 | Full |
|---|---|---|
| β | **0.191164** | **0.170898** |
| SE | 0.088718 | 0.011646 |
| p | 0.031386 | 0.0 |
| 판정 | ** | *** |
| n | 1482 | 68039 |
| n_firms | 97 | 99 |
| n_joint_cells | 313 | 456 |
| df_resid | 1167 | 67581 |
| Adj R² | 0.738786 | 0.665689 |

### 30 모델 전체 요약

| | Batch1 | Full |
|---|---|---|
| 성공 모델 | 30/30 | 30/30 |
| 양수 방향 모델 | 7 | 30 |
| p<.05 유의 모델 | 1 | 30 |
| 방향 안정성 | mixed | positive |
| 결론 | **mixed_direction** | **all_positive_all_sig_p05** |

---

## 10. H2-1 결과 (firm dummy + time FE)

**가설**: Aggressive humor → other humor보다 높은 engagement

### Year FE 기준

| | Batch1 (n_agg=44) | Full (NOT_A_CANDIDATE) |
|---|---|---|
| β | **-0.192808** | **-0.091774** |
| 판정 | ns | *** |

### 30 모델 요약

| | Batch1 | Full |
|---|---|---|
| 성공 모델 | 30/30 | 30/30 |
| 양수 | 29 | 0 |
| 음수 | 1 | 30 |
| p<.05 | 15 | 30 |
| 결론 | **mixed_direction** | **all_negative_all_sig_p05** |

주의:
- Full H2-1: Firm dummy only에서 -0.101***로 역전됨 → Firm+Time FE에서도 전 30모델 음수 *** 확인. 역전 방향 일관적.
- **Batch1 H2-1 HOUR 경고**: hour 포함 조합(15개)에서 β=4.418841** 로 비정상적으로 큰 추정치 관측.
  원인: batch1 648개 humor 포스트를 88개 기업 × 고유 타임스탬프 기반 hour로 분할하면
  (firm, hour) joint cell이 거의 모두 singleton → demeaned data 내 추정 가능 관측치가 극소수.
  이 hour FE 조합의 batch1 결과는 신뢰도가 매우 낮으며 해석 불가로 처리한다.

---

## 11. H2-2 결과 (firm dummy + time FE)

**가설**: Four humor types (ref=affiliative)

### Year FE 기준 (aggressive coefficient)

| | Batch1 | Full |
|---|---|---|
| β(agg) | **-0.163217** | **-0.102528** |
| stars(agg) | ns | *** |
| β(self_enh) | -0.038007 | -0.091746 |
| β(self_def) | 0.534979 | -0.13506 |

### 30 모델 요약

| | Batch1 | Full |
|---|---|---|
| 결론 | **mixed_direction** | **all_negative_all_sig_p05** |

---

## 12. H3 결과 (firm dummy + time FE)

**가설**: Aggressive intensity → engagement (역 U자형)

| | Batch1 | Full (firm-month panel) |
|---|---|---|
| 상태 | **not_applicable** (전체) | 1/30 성공 |
| 이유 | firm cross-section n=88 | year만 가용; month는 firm×month=n → collinear |
| β1 결론 | — | **all_negative_all_sig_p05** |
| firm_dummy_year β1 | — | **-0.965049** *** |
| firm_dummy_year β2 | — | **1.483701** *** |
| turning_point | — | 0.3252 |
| in_range | — | True |

주의: Firm dummy only에서 β1=-2.07***,β2=+2.94*** (U자형 역전). 시간 FE 추가 후 동일 여부 확인.

---

## 13. 기존 plain OLS와 비교

| 가설 | Basis | Plain OLS β | Firm+Time β (year FE) | 방향 변화 |
|---|---|---|---|---|
| H1 | B1 | 1.214982*** | 0.191164** | — |
| H1 | Full | 1.145709*** | 0.170898*** | — |
| H2-1 | B1 | 0.712293* | -0.192808ns | — |
| H2-1 | Full | 0.083304*** | -0.091774*** | — |
| H3 β1 | Full | 9.649312* | -0.965049*** | — |

---

## 14. time FE only 결과와 비교

Time FE only: H1 양 basis 전 30모델 양수 유의.
Firm+Time FE: 위 표 참조. Firm FE 추가 시 계수 추가 축소 예상.

---

## 15. firm dummy only 결과와 비교

| 가설 | Basis | Firm dummy only | Firm+Time (year) | 방향 유지 |
|---|---|---|---|---|
| H1 | B1 | 0.240636*** | 0.191164** | — |
| H1 | Full | 0.202458*** | 0.170898*** | — |
| H2-1 | B1 | 0.118795 ns | -0.192808ns | — |
| H2-1 | Full | -0.101486*** | -0.091774*** | — |
| H3 β1 | Full | -2.072017*** | -0.965049*** | — |

---

## 16. firm + time FE 추가 후 가장 안정적인 가설

**H1**: 양 basis에서 firm dummy only 후에도 양수 유의. Firm+time FE 결과 확인 필요.

---

## 17. firm + time FE 추가 후 가장 민감한 가설

**H2 Full, H3 Full**: Firm dummy only에서 이미 역전됨. Classifier leakage와 복합 가능.
**H2 Batch1**: n_agg=44 → SE 증가로 유의성 더 약해질 것.

---

## 18. Limitation

1. Joint cell saturation: additive FE보다 더 많은 자유도 흡수 (conservative)
2. H3 firm+month: 완전흡수 (firm×period=n) → year FE만 가능
3. Batch1 H3: firm cross-section으로 구조적 불가
4. Classifier leakage: Full H2/H3 해석 불가
5. Singleton cells: fine-grained FE에서 많은 관측치가 추정에 미기여

---

## 19. 다음 판단 지점

1. H1 firm+time FE: 양수 유의 유지 여부
2. H2 Full firm+time FE: 역전(-) 유지 여부 → time FE가 역전 해소하는지
3. H3 Full firm+year FE: U자형 유지 여부

---

## 20. 금지사항 준수

- [x] firm_dummy_included = true
- [x] time_fe_included = true
- [x] controls_included = false
- [x] company_id_used_as_numeric = false
- [x] c_company_formula_used = false
- [x] 기존 plain OLS, time FE only, firm dummy only 결과 파일 미수정
- [x] HC3/robust SE 미사용
- [x] 새 prediction/classifier 없음
- [x] H2/H3 formal supported 미선언

---

*생성 스크립트*: `run_firm_time_fe_robustness.py`
*출력 폴더*: `firm_dummy_time_fe_robustness/`
*생성일*: 2026-06-19
