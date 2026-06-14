# CAR Symmetric Event-Window Panel Plan

## A. 목적 및 DV 역할 구분

### 전체 DV 구조

| DV | 역할 | 상태 |
|----|------|------|
| **Tobin's Q** | Primary Brand Equity proxy (long-run, level-based) | **보류** — 재무제표 panel 미확보. Scaffold 유지 중. |
| **CAR[-1,+1]** | Short-window market reaction proxy (primary, 현재 실행 가능) | **구현 완료** |
| **CAR[-3,+3]** | Medium-window robustness proxy | Daily AR 파일 필요 — 현재 missing |
| **CAR[-5,+5]** | Wider-window robustness proxy | Daily AR 파일 필요 — 현재 missing |
| AbnormalVolume | Investor attention proxy (별도 분석) | 기존 korea_uni 파일에 존재 |

**Tobin's Q 보류 상태**: `docs/tobins_q_brand_equity_dv_construction_plan.md` 및 `data/derived/brand_equity/tobins_q_brand_equity_panel.csv` scaffold 유지. financial statement panel 확보 후 재개.

### 허용 표현

- "CAR is a short-window capital market response proxy."
- "CAR is a market-based brand/value response proxy."
- "CAR is a secondary DV while Tobin's Q is deferred."

### 금지 표현

| 금지 | 이유 |
|------|------|
| "CAR = Tobin's Q" | 서로 다른 측정 대상 (단기 반응 vs. 장기 수준) |
| "CAR = direct Brand Equity" | CAR은 market reaction이지 brand value measurement가 아님 |
| "CAR = consumer-based brand equity" | 완전히 다른 개념 |
| "CAR result = causal brand equity effect" | 회귀분석의 인과 해석 금지 |

---

## B. CAR Window 정의

### 구현된 symmetric windows

| 변수 | 공식 | 기간 | 역할 |
|------|------|------|------|
| **CAR_m1_p1** | sum(AR for day ∈ {-1, 0, +1}) | 3일 | Primary proxy — 현재 272/273 available |
| **CAR_m3_p3** | sum(AR for day ∈ {-3,...,+3}) | 7일 | Robustness — daily AR 파일 필요 |
| **CAR_m5_p5** | sum(AR for day ∈ {-5,...,+5}) | 11일 | Robustness — daily AR 파일 필요; 혼재 이벤트 위험 증가 |

여기서 `day`는 filing date 기준 trading-day index이다.

### asymmetric windows와의 구분 (중요)

| 기존 변수 | Window | 동일 여부 |
|-----------|--------|-----------|
| CAR_0_p3 | [0, +3] | **≠ CAR_m3_p3** ([−3,+3]) |
| CAR_0_p5 | [0, +5] | **≠ CAR_m5_p5** ([−5,+5]) |

- CAR_0_p3를 CAR_m3_p3으로 이름만 바꾸는 것은 **금지**.
- CAR_0_p3, CAR_0_p5는 post-filing asymmetric windows이며, 별도 보조 분석에만 사용.

---

## C. 현재 데이터 상태

### CAR_m1_p1

- **출처**: `data/external/korea_uni/ai_10k_event_study_analysis_dataset.csv` — 직접 컬럼으로 존재
- **가용 rows**: 272/273 (1 row는 market_data_status=failed)
- **별도 계산 불필요**: direct column

### CAR_m3_p3, CAR_m5_p5

- **계산 방법**: `event_window_daily_abnormal_returns.csv`의 event_day 컬럼 기준 누적합
- **파일 상태**: `data/external/korea_uni/event_window_daily_abnormal_returns.csv` — **존재하지 않음**
- **현재 값**: 모든 rows에서 empty (`data_available_flag = false`)
- **임의 계산 금지**: 파일 없이 추정 또는 보정 불가

### daily_abnormal_return 파일 컬럼 요건

파일이 추후 제공되면 아래 컬럼이 필요하다:

| 컬럼 | 설명 |
|------|------|
| ticker | 종목 코드 (대문자) |
| filing_date | 10-K 신고일 (YYYY-MM-DD) |
| event_day | 신고일 기준 trading-day index (−5 ~ +5) |
| abnormal_return | 해당 거래일의 비정상수익률 |

파일 경로: `data/external/korea_uni/event_window_daily_abnormal_returns.csv`

---

## D. Humor Variables와의 연결 (Alignment)

H1-H3 humor variables 단위: `company_name × YYYY-MM (period)`  
CAR 단위: `company_name/ticker × filing_date`

### Alignment 규칙

| 정렬 방식 | 규칙 | 권장 여부 |
|-----------|------|-----------|
| `same_month_alignment` | humor period == filing_date의 YYYY-MM | **보조만**: simultaneity risk |
| `prefiling_lag_1m_alignment` | humor period == filing_month − 1 | **권장 주 분석** |
| `prefiling_lag_3m_alignment` | humor period ∈ {filing_month−3, filing_month−2, filing_month−1} | **권장 주 분석 또는 robustness** |

권장 이유 (prefiling lag):
- temporal ordering 보장 (humor 관찰이 filing 이전)
- 인과 방향성 혼동 감소
- same_month는 filing month 내 events가 humor에 반영될 수 있어 simultaneity 문제

### join_ready 플래그

```
join_ready_for_CAR_m1_p1 = CAR_m1_p1_available == true AND (any alignment flag == true)
join_ready_for_CAR_m3_p3 = CAR_m3_p3_available == true AND (any alignment flag == true)
join_ready_for_CAR_m5_p5 = CAR_m5_p5_available == true AND (any alignment flag == true)
```

현재 `join_ready_for_CAR_m3_p3` = false (모두), `join_ready_for_CAR_m5_p5` = false (모두).

---

## E. Industry Homogeneity Control

`industry_homogeneity_control` 컬럼 = `naics_sector_code`

- `naics_code`는 현재 korea_uni 파일에 없음 (empty)
- `naics_sector_code`, `naics_sector_name`은 273/273 available
- 회귀분석에서 industry FE (fixed effect) 또는 cluster variable로 활용

---

## F. 산출물

| 파일 | 내용 |
|------|------|
| `data/derived/car_event_windows/car_symmetric_event_window_panel.csv` | 273 rows. company × filing event별 CAR 값. CAR_m1_p1 direct; m3_p3/m5_p5 empty. |
| `data/derived/car_event_windows/humor_car_linkage_panel.csv` | humor × CAR joined panel. alignment별 플래그 포함. |
| `data/derived/car_event_windows/car_window_variable_dictionary.csv` | 5개 CAR window 코드북. |
| `data/audit/car_event_windows/car_symmetric_event_window_manifest.json` | 실행 manifest. constraint flags 포함. |

---

## G. 제약 사항

아래 manifest flags는 모든 실행에서 반드시 `false`여야 한다:

| Flag | 의미 |
|------|------|
| `car_used_as_tobins_q` | CAR을 Tobin's Q 대체재로 사용하지 않음 |
| `car_used_as_direct_brand_equity` | CAR을 Brand Equity 직접 측정치로 사용하지 않음 |
| `regression_run` | 회귀분석 실행하지 않음 (이 단계) |
| `causal_claim_made` | 인과 주장 없음 |
| `external_data_downloaded` | 외부 데이터 다운로드 없음 |
| `sec_collection_run` | SEC 데이터 수집 없음 |
| `market_data_collection_run` | 시장 데이터 수집 없음 |
| `x_collection_run` | X(트위터) 수집 없음 |
| `raw_data_modified` | 원천 데이터 수정 없음 |
| `humor_outputs_modified` | humor 분석 출력 수정 없음 |

`tobins_q_deferred: true` — Tobin's Q가 primary DV이나 현재 보류 상태임을 명시.

---

## H. 다음 단계

```
[현재] CAR_m1_p1 available (272 rows)
       CAR_m3_p3, CAR_m5_p5 missing (daily AR 필요)

  ↓
[수동 작업] event_window_daily_abnormal_returns.csv를
           data/external/korea_uni/에 복사
           (ticker, filing_date, event_day, abnormal_return 컬럼 필요)
  ↓
[재실행] Build CAR Symmetric Event Window Panel
         → CAR_m3_p3, CAR_m5_p5 자동 계산
  ↓
[보류] Tobin's Q financial statement panel 확보
       → build_tobins_q_brand_equity_panel.py --financial-panel 실행
  ↓
[추후] H1-H3 regression script 구성
       (humor_car_linkage_panel.csv × industry control 기반)
```

---

## I. Workflow 실행 방법

GitHub Actions → **Build CAR Symmetric Event Window Panel** → 수동 실행

초기 실행 (daily AR 없이):

| 파라미터 | 값 |
|----------|----|
| `commit_results` | `false` |
| `humor_variables_path` | `data/derived/humor/hypothesis_variables/humor_firm_period_hypothesis_variables.csv` |
| `humor_manifest_path` | `data/audit/humor/hypothesis_variables/humor_hypothesis_variables_manifest.json` |
| `korea_uni_event_dataset_path` | `data/external/korea_uni/ai_10k_event_study_analysis_dataset.csv` |
| `daily_abnormal_return_path` | `data/external/korea_uni/event_window_daily_abnormal_returns.csv` (없으면 warning만) |

Artifact 확인 후 `CAR_m1_p1_available_rows`, `join_ready_for_CAR_m1_p1_rows` 검토.
