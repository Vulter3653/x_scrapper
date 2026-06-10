# X Account Discovery Audit Report

## 1. 실행 요약

- Workflow: `Discover Fortune X Accounts`
- Input file: `config/fortune100_firm_master_sample.csv`
- Firm limit: `10`
- Candidates rows: `199`
- Recommendations rows: `10`
- Audit rows: `53`

이번 discovery는 X 검색 자체는 작동했다. 10개 기업에서 199개 candidate가 수집되었고 46개 query가 `success`였다. 그러나 recommendation 결과에서 `single_high_confidence_candidate`는 확인되지 않았다. 따라서 모든 기업은 manual review가 필요하며, X 검색 결과만으로 공식 계정을 확정하지 않는다.

## 2. 입력 파일

- `config/fortune100_account_candidates.csv`
- `data/audit/x_account_discovery_recommendations.csv`
- `data/audit/x_account_discovery_audit.csv`
- `docs/x_account_discovery_method.md`

## 3. Candidate row count

- 수집된 candidate: `199` rows
- 기업 수: `10`
- 수동 검수 queue: `10` rows

## 4. Recommendation status distribution

- `login_or_rate_limited`: 3
- `low_confidence_only`: 6
- `multiple_ambiguous_candidates`: 1

## 5. Audit status distribution

- `login_challenge`: 3
- `selector_not_found`: 4
- `success`: 46

## 6. Credential / selector / rate-limit 문제

- Credentials는 workflow에서 제공되었고 실제 X 검색이 수행되었다.
- `login_challenge`: `3` rows. Walmart, UnitedHealth Group, Apple 검수 시 검색 또는 profile 접근 제한을 고려해야 한다.
- `selector_not_found`: `4` rows. Cencora query에서 반복되었다.
- Alphabet, Exxon Mobil, McKesson, Cencora에 `@MoonPie`가 반복 추천되었다. 이는 공식 계정 evidence가 아니라 검색 UI selector 또는 결과 갱신 문제 가능성을 보여준다.

## 7. 기업별 top candidate 요약

| Rank | Firm | Recommended handle | Role | Score | Confidence | Recommendation status | Priority |
| ---: | --- | --- | --- | ---: | --- | --- | --- |
| 1 | Walmart | `@walmartcompany_` | corporate | 70 | high | login_or_rate_limited | high |
| 2 | Amazon | `@amazonmusic` | unknown | 60 | low | multiple_ambiguous_candidates | high |
| 3 | UnitedHealth Group | `@keliixxxe` | unknown | 50 | low | login_or_rate_limited | high |
| 4 | Apple | `@Apple` | unknown | 70 | low | login_or_rate_limited | high |
| 5 | CVS Health | `@CVSHealth` | customer_support | 40 | low | low_confidence_only | medium |
| 6 | Berkshire Hathaway | `@bhhsfoxroach` | corporate | 40 | low | low_confidence_only | medium |
| 7 | Alphabet | `@MoonPie` | unknown | 10 | not_found | low_confidence_only | medium |
| 8 | Exxon Mobil | `@MoonPie` | unknown | 10 | not_found | low_confidence_only | medium |
| 9 | McKesson | `@MoonPie` | unknown | 10 | not_found | low_confidence_only | medium |
| 10 | Cencora | `@MoonPie` | unknown | 0 | not_found | low_confidence_only | high |

## 8. High-priority manual review 기업

- **Walmart**: `@walmartcompany_`. recommendation_status=login_or_rate_limited; login_challenge_count=1
- **Amazon**: `@amazonmusic`. recommendation_status=multiple_ambiguous_candidates; corporate_account_may_be_ambiguous; recommended_confidence=low
- **UnitedHealth Group**: `@keliixxxe`. recommendation_status=login_or_rate_limited; login_challenge_count=1; corporate_account_may_be_ambiguous; recommended_confidence=low
- **Apple**: `@Apple`. recommendation_status=login_or_rate_limited; login_challenge_count=1; corporate_account_may_be_ambiguous; recommended_confidence=low
- **Cencora**: `@MoonPie`. recommendation_status=low_confidence_only; selector_not_found_count=4; recommended_confidence=not_found; unrelated_repeated_handle_possible_search_ui_contamination

Priority distribution:

- `high`: 5
- `medium`: 5

## 9. 자동 확정하지 않은 이유

X 검색 결과와 점수는 공식성의 증거가 아니다. 기업 공식 홈페이지 social link, X profile external URL, verified status, account role을 사람이 별도로 확인해야 한다. Product brand, support, careers, regional, newsroom 계정은 parent corporate account와 구분해야 한다. 이번 결과에는 login challenge, selector failure, 무관한 반복 handle도 포함되어 있어 자동 반영이 부적절하다.

## 10. 다음 단계

1. `data/audit/x_account_manual_review_queue.csv`를 사람이 검수한다.
2. 공식 홈페이지 social link와 profile external URL이 일치하는지 확인한다.
3. 검수 완료 기업만 별도 approved mapping 파일에 기록한다.
4. approved mapping만 firm master에 반영한다.
5. sample 10개 기업에 대해 post collection test를 실행한다.
