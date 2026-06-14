# Brand Equity and Market Reaction Linkage Readiness Plan

## A. 목적

이 문서는 x_scrapper의 H1-H3 humor variables를 Brand Equity 및 market-based outcome과 결합하기 위한 **readiness layer**를 정의한다.

이 단계는 회귀분석 실행이 아니다. 무엇이 준비되었고, 무엇이 부족하며, 어떤 순서로 결합 가능성을 확보해야 하는지를 확인하는 작업이다.

---

## B. DV 역할 구분

### Tobin's Q — Primary Brand Equity Proxy

Simon & Sullivan (1993)의 financial-market-based brand equity 접근에 따르면, 기업 가치 기반 Brand Equity proxy는 **Tobin's Q**를 통해 구성하는 것이 이론적으로 가장 직접적이다.

- **Tobin's Q** = (market value of equity + book value of liabilities) / book value of assets
- **역할**: long-run / level-based market valuation proxy for Brand Equity
- **현재 상태**: x_scrapper에 financial statement panel 없음. **MISSING**.
- **필요 자료**: market capitalization, book value of assets, book value of liabilities, ticker/CIK crosswalk

### CAR — Short-Window Market Reaction Proxy

- **역할**: event-study based short-window capital market response proxy
- CAR은 Tobin's Q의 대체물이 아니다.
- CAR은 direct consumer-based brand equity가 아니다.
- CAR = market-based firm value response / capital market response (10-K filing 이벤트 기준)
- **출처**: korea_uni repo의 event study 결과

**허용 표현**:
- market-based brand equity proxy
- market-based firm value response
- capital market response
- short-window market reaction proxy
- event-study based value response

**금지 표현**:
- CAR이 Tobin's Q와 동일하다
- CAR이 direct consumer-based brand equity
- CAR 결과를 causal brand equity effect로 해석

### AbnormalVolume — Investor Attention Proxy

- **역할**: investor attention / trading attention proxy
- Tobin's Q도 CAR도 아님. 투자자 관심도 지표.
- **출처**: korea_uni repo의 market extension 결과

---

## C. 현재 준비 상태 요약

| 항목 | 상태 |
|------|------|
| Humor firm-period variables (H1-H3) | 준비 완료. 3,767 rows. `company_name × period` unique key. |
| Ticker / CIK crosswalk | 불완전. `fortune2025_top100_10k_report_index.csv` 존재하나 SEC API 403으로 인해 `sec_ticker`, `sec_cik` 모두 미해결. |
| Tobin's Q / financial statement panel | **없음**. x_scrapper에 해당 자료 없음. |
| korea_uni 이벤트 스터디 자료 | **없음**. 사용자가 수동으로 `data/external/korea_uni/`에 복사해야 함. |
| CAR outcomes (korea_uni) | 잠재적으로 활용 가능. 파일 복사 후 판단 가능. |
| AbnormalVolume outcomes (korea_uni) | 잠재적으로 활용 가능. 파일 복사 후 판단 가능. |

---

## D. Tobin's Q 필수 입력 자료

Tobin's Q 계산에 필요하나 x_scrapper에 없는 자료:

| 자료 | 필요 이유 | 해결 경로 |
|------|-----------|-----------|
| Monthly / annual market capitalization | Tobin's Q 분자 (시장가치) | Compustat CRSP, Yahoo Finance 등 |
| Book value of total assets | Tobin's Q 분모 | Compustat 재무제표 연간 파일 |
| Book value of liabilities | Tobin's Q 분자 구성 | Compustat 재무제표 |
| Preferred stock (if applicable) | Tobin's Q 정확도 | Compustat |
| Fiscal year-end alignment | 기간 매핑 | 회사별 FY 주기 확인 |
| Ticker / CIK crosswalk (완전) | 조인 키 | EDGAR 수동 조회 또는 korea_uni crosswalk 활용 |
| Financial statement panel (firm-year) | 분석 단위 | Compustat GVKEY 기준 |

---

## E. CAR Linkage 경로

korea_uni 파일을 수동 복사한 경우에만 CAR linkage 계산 가능.

복사 경로:

```
korea_uni/data/derived/causal/ai_10k_event_study_analysis_dataset.csv
→ x_scrapper/data/external/korea_uni/ai_10k_event_study_analysis_dataset.csv

korea_uni/data/derived/market_extension/post_filing_market_reaction_estimates.csv
→ x_scrapper/data/external/korea_uni/post_filing_market_reaction_estimates.csv

korea_uni/data/derived/market_extension/market_data_collection_report.csv
→ x_scrapper/data/external/korea_uni/market_data_collection_report.csv
```

**주의**: GitHub Actions workflow에서 외부 repo를 clone하지 않는다. network download 금지. 사용자가 수동 복사한 경우에만 읽는다.

---

## F. Date Alignment Rule

x_scrapper humor 변수: `company_name × YYYY-MM`
CAR outcome: `company_name / ticker × filing_date`

### Rule 1: Same-Month Alignment

```
humor period == filing_date의 YYYY-MM
```

**한계**: filing 이후 같은 달의 humor posts가 포함되어 simultaneity 위험 존재. 분석에서는 sensitivity check로만 활용 권장.

### Rule 2: Pre-Filing Lag Alignment (권장)

```
humor period == filing_month - 1
또는 humor period ∈ [filing_month - 3, filing_month - 1]
```

**권장 이유**: temporal ordering 보장. humor 활동이 filing 이전에 관측됨. 인과 방향성 혼동 위험 감소.

이번 단계에서는 alignment별 coverage만 계산. 회귀분석 실행 없음.

---

## G. Future-Date Audit

korea_uni 자료에 현재 날짜(`reference_date`) 이후의 filing/event date가 포함될 수 있다. Manifest에 다음을 기록:

- `future_event_count`: 미래 event 수
- `future_event_share`: 전체 event 중 미래 event 비율
- `future_event_date_min`, `future_event_date_max`: 미래 event 날짜 범위
- `requires_date_audit`: 미래 event 존재 시 `true`

`requires_date_audit == true`이면 `regression_ready == false`.

---

## H. 금지사항

| 항목 | 상태 |
|------|------|
| korea_uni repo 수정 | 금지 |
| 외부 repo clone | 금지 |
| network download | 금지 |
| SEC collection 실행 | 금지 |
| market data collection 실행 | 금지 |
| X collection 실행 | 금지 |
| Brand Equity 값 임의 생성 | 금지 |
| Tobin's Q 임의 계산 | 금지 |
| CAR을 Tobin's Q와 동일하다고 표현 | 금지 |
| CAR을 direct brand equity로 표현 | 금지 |
| regression 실행 | 금지 (이 단계) |
| causal claim | 금지 |
| dashboard 수정 | 금지 |
| raw data 수정 | 금지 |
| humor output 수정 | 금지 |

---

## I. 산출물

`Build Brand Equity Market Reaction Linkage Readiness` workflow 실행 시 생성:

| 파일 | 내용 |
|------|------|
| `data/derived/brand_equity_linkage/brand_equity_market_reaction_linkage_readiness.csv` | 3,767 company_name × period rows. DV linkage 가능성 플래그 포함. |
| `data/derived/brand_equity_linkage/dv_candidate_variable_dictionary.csv` | 13개 DV 후보 코드북 (Tobin's Q, CAR, AbnormalVolume, placebo). |
| `data/derived/brand_equity_linkage/brand_equity_market_reaction_missing_inputs.csv` | 회귀분석 전 확보 필요한 누락 자료 목록. |
| `data/audit/brand_equity_linkage/brand_equity_market_reaction_linkage_manifest.json` | 실행 manifest. `regression_ready`, `reason_regression_not_ready`, constraint flags 포함. |

---

## J. 다음 단계

```
[현재] Linkage Readiness 평가 (무엇이 준비됐는가)
  ↓
[수동 작업] Ticker/CIK 수동 보완 (fortune2025_top100_10k_report_index.csv)
  ↓
[수동 작업] korea_uni 파일을 data/external/korea_uni/ 에 복사
  ↓
[재실행] Build Brand Equity Market Reaction Linkage Readiness (korea_uni 파일 포함)
  ↓
[검토] CAR linkage coverage 확인 (matched_company_count, same_month vs prefiling_lag)
  ↓
[보류] Tobin's Q financial panel 확보 (Compustat 등)
  ↓
[보류 후 가능] H1-H3 regression script 구성
```

---

## K. Workflow 실행 방법

GitHub Actions → **Build Brand Equity Market Reaction Linkage Readiness** → 수동 실행

권장 초기 실행 (korea_uni 파일 없이):

| 파라미터 | 값 |
|----------|----|
| `commit_results` | `false` |
| `humor_variables_path` | `data/derived/humor/hypothesis_variables/humor_firm_period_hypothesis_variables.csv` |
| `humor_manifest_path` | `data/audit/humor/hypothesis_variables/humor_hypothesis_variables_manifest.json` |
| `korea_uni_event_dataset_path` | `data/external/korea_uni/ai_10k_event_study_analysis_dataset.csv` (없으면 warning만 출력) |

Artifact 확인 후 `regression_ready=false`와 `reason_regression_not_ready` 내용을 검토하라.
