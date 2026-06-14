# Tobin's Q Brand Equity DV Construction Plan

## A. 목적

이 문서는 H1–H3 humor hypothesis regression에서 **primary Brand Equity DV**로 사용할 Tobin's Q firm-year panel의 구성 계획을 정의한다.

Tobin's Q는 Simon & Sullivan (1993)의 financial-market-based Brand Equity 접근에 기반한다.  
CAR은 Tobin's Q의 대체재가 아니다 — CAR은 단기 이벤트 스터디 market reaction proxy이며, Tobin's Q는 장기 level-based firm value proxy이다.

---

## B. 이론적 배경

### Simon & Sullivan (1993) 접근

- Brand Equity를 재무 시장 데이터에서 분리 가능한 구성요소로 정의
- 기업의 market value가 book value를 초과하는 부분이 intangible asset (브랜드 자산 포함)을 반영한다고 간주
- Tobin's Q가 높을수록 시장이 기업의 intangible value를 높게 평가한다는 함의

### Tobin's Q — 공식

```
tobins_q = (market_cap + total_liabilities) / total_assets
market_cap = stock_price_fiscal_year_end × shares_outstanding
```

**공식 종류**: Chung & Pruitt (1994) simplified approximation  
(Perfect & Wiles (1994) 또는 Hall, Cummins, Laderman, & Mundy (1988)의 full form 대비 단순화)

**데이터 접근성**: simplified form은 Compustat Fundamentals Annual 4개 변수로 구성 가능.

---

## C. DV 역할 구분 (혼동 금지)

| 변수 | 역할 | 시간 지평 | 비고 |
|------|------|-----------|------|
| **Tobin's Q** | Primary Brand Equity proxy (firm value level) | 장기 (fiscal year-level) | **본 문서의 대상** |
| CAR | Short-window market reaction proxy (event study) | 단기 (filing 전후 수일) | Tobin's Q ≠ CAR |
| AbnormalVolume | Investor attention / trading attention proxy | 단기 | Tobin's Q ≠ AbnormalVolume |

**금지 표현**:
- "CAR은 Tobin's Q와 동일한 Brand Equity 지표이다"
- "CAR 결과를 Tobin's Q의 대리지표로 사용한다"
- "AbnormalVolume이 Brand Equity를 반영한다"
- "humor→CAR 관계는 humor→Brand Equity의 causal effect이다"

---

## D. 현재 데이터 상태

### 보유 식별자 (korea_uni event study 기준)

| 항목 | 상태 |
|------|------|
| company_name | 92개 기업 |
| ticker | 92개 |
| CIK | 92개 |
| fiscal_year | 2023, 2024, 2025 |
| filing_date | 273 rows (10-K 신고일) |
| **total_assets** | **MISSING** |
| **total_liabilities** | **MISSING** |
| **market_cap** | **MISSING** |
| **shares_outstanding** | **MISSING** |
| **stock_price_fiscal_year_end** | **MISSING** |
| **tobins_q** | **계산 불가** |

현재 상태: 273 firm-year scaffold rows 구성 가능하나 Tobin's Q 계산에 필요한 재무 데이터가 모두 없음.  
모든 rows의 `data_available_flag = false`, `tobins_q = ""`.

---

## E. 필요 자료 및 해결 경로

| 재무 항목 | 역할 | 권장 출처 | Compustat 변수 | SEC XBRL 개념 |
|-----------|------|-----------|----------------|---------------|
| total_assets | Tobin's Q 분모 | SEC EDGAR XBRL 또는 Compustat | `at` (Fundamentals Annual) | `us-gaap/Assets`, form 10-K |
| total_liabilities | Tobin's Q 분자 (부채 장부가) | SEC EDGAR XBRL 또는 Compustat | `lt` (Fundamentals Annual) | `us-gaap/Liabilities`, form 10-K |
| shares_outstanding | market_cap 도출 | CRSP, Compustat, 또는 SEC XBRL | `csho` (Fundamentals Annual) | `us-gaap/CommonStockSharesOutstanding` |
| stock_price_fiscal_year_end | market_cap 도출 | CRSP daily, Yahoo Finance | `prcc_f` (CRSP-Compustat merged) | N/A (market data) |
| market_cap | Tobin's Q 분자 (시장가치) | price × shares 도출 또는 Compustat `mkvalt` | `mkvalt` | N/A |

### Join 키

모든 재무 panel을 아래 중 하나로 결합:
- `ticker × fiscal_year`
- `cik × fiscal_year`
- `compustat_gvkey × fiscal_year` (GVKEY → ticker 또는 CIK crosswalk 경유)

---

## F. 파일 저장 규칙 (재무 panel 확보 후)

```
data/external/financial_panel/sec_xbrl_financial_panel.csv
  → company_name, ticker, cik, fiscal_year, total_assets, total_liabilities, shares_outstanding

data/external/financial_panel/market_price_panel.csv
  → ticker, fiscal_year, fiscal_year_end_date, stock_price_fiscal_year_end, shares_outstanding_market
```

외부 panel이 준비되면 `--financial-panel` argument로 script에 공급.  
script는 join 후 자동으로 Tobin's Q 계산을 시도한다.

---

## G. Scaffold 구조 (현재 단계)

`build_tobins_q_brand_equity_panel.py` 실행 시:

1. `ai_10k_event_study_analysis_dataset.csv` (273 rows)에서 company_name, ticker, cik, fiscal_year, filing_date 추출
2. `--financial-panel` 미제공 → 모든 재무 컬럼 empty
3. 각 row: `data_available_flag = false`, `tobins_q = ""`, `missing_component_reason = "total_assets; total_liabilities; market_cap; shares_outstanding; stock_price_fiscal_year_end"`
4. Manifest: `tobins_q_available = false`, `regression_ready_with_tobins_q = false`, constraint flags all `false`

`--financial-panel` 공급 시:

1. ticker 또는 cik로 재무 panel join
2. complete rows에 대해 Tobin's Q 자동 계산
3. 누락 rows는 그대로 empty — 임의 추정 없음

---

## H. 산출물

| 파일 | 내용 |
|------|------|
| `data/derived/brand_equity/tobins_q_brand_equity_panel.csv` | firm-year panel (273 rows scaffold). `tobins_q`, `data_available_flag`, `missing_component_reason` 포함. |
| `data/derived/brand_equity/tobins_q_missing_components.csv` | 누락 재무 항목 목록 및 해결 경로. |
| `data/audit/brand_equity/tobins_q_brand_equity_manifest.json` | 실행 manifest. `tobins_q_available`, `regression_ready_with_tobins_q`, constraint flags. |

---

## I. 제약 사항 (Constraint Flags)

아래 flag는 모든 실행에서 반드시 `false`여야 한다.

| Flag | 의미 |
|------|------|
| `external_data_downloaded` | 외부 데이터 다운로드 없음 |
| `sec_collection_run` | SEC EDGAR API 호출 없음 |
| `market_data_collection_run` | 시장 가격 데이터 수집 없음 |
| `tobins_q_imputed` | Tobin's Q 추정 또는 보정 없음 |
| `car_used_as_tobins_q` | CAR을 Tobin's Q로 대체 사용하지 않음 |
| `raw_data_modified` | 원천 데이터 수정 없음 |
| `humor_outputs_modified` | humor analysis 출력 수정 없음 |

---

## J. Humor-Tobin's Q 연결 계획 (회귀분석 단계)

Tobin's Q panel이 완성되면:

```
humor_firm_period_hypothesis_variables.csv
  × tobins_q_brand_equity_panel.csv
  [join on company_name → company_name, fiscal_year → YYYY from period]
→ H1 regression: tobins_q ~ humor_presence_rate + controls
→ H2 regression: tobins_q ~ humor_type_aggressive_rate + humor_type_affiliative_rate + controls
→ H3 regression: tobins_q ~ aggressive_intensity + aggressive_intensity² + controls
```

**Period → fiscal_year 매핑**: humor period `YYYY-MM`을 fiscal_year `YYYY`로 aggregation 후 join.  
세부 aggregation 규칙 (FY 기준 vs. calendar year)은 regression script 단계에서 결정.

---

## K. 다음 단계

```
[현재] Tobin's Q scaffold 구성 (식별자 보유, 재무 데이터 없음)
  ↓
[수동 작업] SEC EDGAR XBRL 또는 Compustat에서 total_assets, total_liabilities 획득
  ↓
[수동 작업] CRSP / Yahoo Finance에서 stock_price_fiscal_year_end, shares_outstanding 획득
  ↓
[재실행] build_tobins_q_brand_equity_panel.py --financial-panel <path>
  ↓
[검토] tobins_q_available=true, regression_ready_with_tobins_q=true 확인
  ↓
[다음] H1-H3 regression script 구성 (humor_variables × tobins_q_panel join)
```
