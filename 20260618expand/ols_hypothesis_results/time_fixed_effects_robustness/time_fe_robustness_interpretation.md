# H1/H2/H3 시간 고정효과 Robustness 분석

**생성일**: 2026-06-19  **기준 commit**: 1926e25
**SE 유형**: Classical OLS (s²×(X'X)⁻¹) — HC3/robust SE 미사용
**FE 구현**: Joint interaction cell demeaning (pandas groupby, single-pass)
- 계층적 FE 조합(예: year+month+day)은 가장 세밀한 단위와 동치
- 비계층적 조합(예: month×hour_of_day)은 교차 셀(cross-cell) FE
- 분석 성격: PRELIMINARY ROBUSTNESS CHECK ONLY

---

## 1. 분석 목적

기존 1926e25 two-basis plain OLS 결과가 시간별 공통 충격(time shocks) 통제 후에도
핵심 계수의 방향과 유의성이 유지되는지 확인.

---

## 2. 기존 1926e25 vs 이번 robustness

| 항목 | 1926e25 plain OLS | 이번 time FE robustness |
|---|---|---|
| 시간 통제 | 없음 | 1~4개 FE 조합 30가지 |
| SE 방식 | Classical OLS | Classical OLS (동일) |
| 분리 구조 | Batch1 / Full-sample | 동일 |
| 모델 수 | 4 per basis | 30 × 2 basis per hypothesis |

---

## 3. 시간 FE 조합 (30개)

FE 후보: year / month / week / day / hour
C(5,1)=5 + C(5,2)=10 + C(5,3)=10 + C(5,4)=5 = **30 combinations**

| 데이터 | year | month | week | day | hour |
|---|---|---|---|---|---|
| Batch1 H1 (1,482) | ✅ | ✅ | ✅ | ✅ | ✅ |
| Batch1 H2/H3 (648) | ✅ | ✅ | ✅ | ✅ | ✅ |
| Batch1 H3 firm-level | N/A | N/A | N/A | N/A | N/A |
| Full H1 integrated (68,039) | ✅ | ✅ | ✅ | ✅ | ✅ (hour_of_day) |
| Full H2 h2_post (28,177) | ✅ | ✅ | ✅ | ✅ | ✅ |
| Full H3 firm-month (3,532) | ✅ | ✅ | ❌ | ❌ | ❌ |

---

## 4. H1 결과 요약

**가설**: 유머 post → 더 높은 engagement

| | Batch1 human-coded | Full-sample predicted |
|---|---|---|
| 성공 모델 수 | 30/30 | 30/30 |
| 계수 범위 | 0.615 ~ 1.012 | 1.035 ~ 1.162 |
| 양수 방향 유지 모델 | 30 | 30 |
| p<.05 유의 모델 수 | 15 | 30 |
| 방향 안정성 | yes | yes |
| 결론 | **all_positive_some_sig_p05** | **all_positive_all_sig_p05** |

---

## 5. H2-1 결과 요약

**가설**: Aggressive humor → other humor보다 높은 engagement

| | Batch1 human-coded (n_agg=44) | Full-sample predicted (n_pred_agg=6,857) |
|---|---|---|
| 성공 모델 수 | 30/30 | 30/30 |
| 계수 범위 | 0.065 ~ 0.927 | 0.014 ~ 0.082 |
| 양수 방향 유지 | 30 | 30 |
| p<.05 유의 모델 수 | 2 | 14 |
| 방향 안정성 | yes | yes |
| 결론 | **all_positive_some_sig_p05** | **all_positive_some_sig_p05** |

- Batch1 주의: n_agg=44 → time FE 추가 시 검정력 더욱 낮아짐
- Full 주의: type classifier NOT_A_CANDIDATE; leakage (#NationalRoastDay) 확인됨

---

## 6. H2-2 결과 요약

**가설**: Four humor types 비교 (aggressive coefficient, ref=affiliative)

| | Batch1 human-coded | Full-sample predicted |
|---|---|---|
| 성공 모델 수 | 30/30 | 30/30 |
| 계수 범위 | 0.730 ~ 1.122 | 0.023 ~ 0.085 |
| 양수 방향 유지 | 30 | 30 |
| p<.05 유의 모델 수 | 7 | 14 |
| 방향 안정성 | yes | yes |
| 결론 | **all_positive_some_sig_p05** | **all_positive_some_sig_p05** |

---

## 7. H3 결과 요약

**가설**: Aggressive intensity → engagement (역 U자형)

| | Batch1 human-coded | Full-sample predicted |
|---|---|---|
| 상태 | not_applicable (전체) | 3/30 성공 |
| 이유 | firm-level cross-section; no time dim | week/day/hour 미가용 (year/month만 가능) |
| 계수 범위(β1) | — | 1.484 ~ 1.653 |
| 양수 방향(β1) | — | 3 |
| p<.05 유의(β1) | — | 3 |
| 방향 안정성 | — | yes |
| 결론 | not_applicable | **all_positive_all_sig_p05** |

- Full H3 주의: classifier NOT_A_CANDIDATE; predicted intensity leakage 가능

---

## 8. Batch1 vs Full-sample 비교

| 가설 | Batch1 방향 안정 | Full 방향 안정 | 해석 |
|---|---|---|---|
| H1 | yes | yes | 시간 통제 후 안정성 |
| H2-1 | yes | yes | |
| H2-2 | yes | yes | |
| H3 | N/A | yes | firm-level 한계 |

---

## 9. 가장 안정적인 가설 (time FE 후)

H1이 가장 안정적으로 예상:
- 양 basis에서 계수 양수 방향 유지
- Full H1은 n=68,039으로 time FE 추가 후에도 검정력 충분

---

## 10. 가장 민감한 가설 (time FE 후)

H2 batch1이 가장 민감:
- n_agg=44의 낮은 검정력으로 time FE 추가 시 SE 증가 → 유의성 손실 가능
- 방향성(양수)은 유지될 수 있으나 p-value는 상승 예상

---

## 11. 주요 limitation

1. **Joint interaction FE**: Additive FE가 아닌 joint saturation 사용 → 비계층적 조합에서 더 많은 자유도 흡수 (conservative)
2. **k_eff 근사**: n_joint_cells 기반 계산 → 실제 rank보다 과대 추정 가능 → SE 약간 과대
3. **Batch1 H3**: firm-level → time FE 불가 (fundamental limitation)
4. **Full H3 week/day/hour**: firm-month panel의 period-based 구조 한계
5. **Classifier leakage**: Full H2/H3의 모든 결과는 type classifier leakage 영향 가능

---

## 12. 다음 판단 지점

1. H1 양 basis에서 time FE 후에도 계수 유지 → H1 preliminary robustness 일부 확보
2. H2 batch1 time FE 후 방향성 유지 여부 → 인간 코딩 결과의 time-driven confound 여부 판단
3. H3 full-sample: β1>0, β2<0 패턴이 year/month FE 후에도 유지되는지 확인
4. Company-level clustered SE는 별도 robustness 작업으로 추가 가능

---

## 13. 금지사항 준수

- [x] backfill/workflow 파일 미수정
- [x] 기존 1926e25 결과 파일 삭제/덮어쓰기 없음
- [x] HC3/robust SE 미사용
- [x] 새 prediction/classifier 없음
- [x] H2/H3 formal support 미선언

---

*생성 스크립트*: `run_time_fe_robustness.py`
*출력 폴더*: `time_fixed_effects_robustness/`
*생성일*: 2026-06-19
