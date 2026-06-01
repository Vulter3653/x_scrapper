# Fortune 100 X Account Candidate Discovery Method

## 1. 목적

이 단계는 Fortune 100 기업의 공식 X 계정을 자동 확정하지 않는다. X user search 결과를 후보로 수집하고 점수화하여 사람이 검토할 수 있는 candidate table과 audit log를 생성한다.

입력:

```text
config/fortune100_firm_master_sample.csv
```

샘플 검증 이후 운영 master가 100개 firm으로 채워지면 동일 스크립트에 다음 파일을 입력할 수 있다.

```text
config/fortune100_firm_master.csv
```

## 2. 실행 파일

```text
scripts/discover_x_account_candidates.py
```

출력:

```text
config/fortune100_account_candidates.csv
data/audit/x_account_discovery_recommendations.csv
data/audit/x_account_discovery_audit.csv
```

출력 파일은 deterministic하게 재생성된다. 기존 결과 보존이 필요하면 `--backup-existing`을 추가하여 `.bak` 파일을 만든다.

## 3. 인증 및 환경변수

기존 `scrape_x.py`와 동일하게 X browser cookie를 사용한다.

```bash
export X_AUTH_TOKEN='...'
export X_CT0='...'
export HEADLESS='true'
export DISCOVERY_MAX_RESULTS='10'
export DISCOVERY_SCROLLS='3'
export DISCOVERY_DELAY_SECONDS='1.25'
```

cookie가 없으면 실제 X 검색을 수행하지 않는다. 대신 모든 firm/query에 대해:

```text
status=error
error_type=missing_credentials
recommendation_status=search_failed
```

를 기록한다. 실패를 조용히 무시하지 않는다.

## 4. 실행 예시

샘플 10개 firm:

```bash
python scripts/discover_x_account_candidates.py \
  --input config/fortune100_firm_master_sample.csv \
  --output config/fortune100_account_candidates.csv \
  --recommendations data/audit/x_account_discovery_recommendations.csv \
  --audit data/audit/x_account_discovery_audit.csv
```

백업 포함:

```bash
python scripts/discover_x_account_candidates.py \
  --backup-existing
```

profile 상세 조회를 생략하는 제한 검증:

```bash
python scripts/discover_x_account_candidates.py \
  --no-profile-details
```

## 5. X 검색 query

각 firm마다 다음 user-search query를 실행한다.

```text
{firm_name}
{firm_name} official
{firm_name} corporation
{firm_name} company
{firm_name} news
```

검색 URL:

```text
https://x.com/search?q=<encoded_query>&f=user
```

검색 결과 selector는 스크립트 상단에서 중앙 관리한다.

```python
USER_RESULT_SELECTORS = [...]
HANDLE_SELECTORS = [...]
DISPLAY_NAME_SELECTORS = [...]
BIO_SELECTORS = [...]
VERIFIED_SELECTORS = [...]
```

X UI 변경으로 selector가 일치하지 않으면 빈 성공으로 처리하지 않는다.

```text
status=selector_not_found
error_type=selector_not_found
```

## 6. Profile detail fetch

검색 결과에서 handle을 찾은 뒤 가능한 경우 profile URL을 열어 다음을 보강한다.

```text
candidate_bio
candidate_external_url
candidate_followers_text
candidate_verified_status
```

profile fetch 실패 시 candidate row는 삭제하지 않는다. `review_note`와 audit log에 오류를 기록한다.

## 7. Role 분류

자동 role은 검토 보조 정보다. 최종 판정이 아니다.

```text
corporate
customer_support
product_brand
regional
investor_relations
newsroom
careers
executive_or_employee
fan_or_unofficial
unknown
```

우선 분류 규칙:

- `support`, `help`, `care`, `customer service`: `customer_support`
- `jobs`, `careers`, `hiring`: `careers`
- `investor`, `IR`, `shareholder`: `investor_relations`
- `news`, `press`, `media`: `newsroom`
- 국가 또는 지역명: `regional`
- `CEO`, `employee`: `executive_or_employee`
- `fan`, `parody`, `unofficial`, `not affiliated`: `fan_or_unofficial`
- `official`, `company`, `corporate`, `global`: `corporate`
- 판단 불가: `unknown`

product brand와 parent company 구분은 수동 검수가 필요하다.

## 8. Candidate scoring

```text
total_candidate_score =
  name_match_score
  + handle_match_score
  + bio_match_score
  + external_url_score
  + verified_score
  + negative_penalty
```

점수 범위:

| Field | Range | Meaning |
|---|---:|---|
| `name_match_score` | 0-30 | display name과 firm name 일치 |
| `handle_match_score` | 0-20 | handle과 firm name 일치 |
| `bio_match_score` | 0-20 | 공식 기업 bio 정황 |
| `external_url_score` | 0-20 | master의 공식 website domain 일치 |
| `verified_score` | 0-10 | verified badge 확인 |
| `negative_penalty` | 0 to -50 | fan, support, careers, regional 등 penalty |

master에 `official_website`가 없으면 `external_url_score=0`이며 `review_note=official_website_missing`을 남긴다.

## 9. Confidence와 recommendation

`high` confidence라도 자동 승인하지 않는다.

```text
review_status=needs_manual_review
needs_manual_review=1
```

recommendation status:

```text
single_high_confidence_candidate
multiple_ambiguous_candidates
low_confidence_only
no_candidate_found
search_failed
login_or_rate_limited
```

최종 계정 확정은 별도 manual review 단계에서 official website evidence와 X profile evidence를 검토한 뒤 수행한다.

## 10. Audit log

audit file:

```text
data/audit/x_account_discovery_audit.csv
```

검색 query마다 상태를 기록한다.

```text
success
no_results
search_ui_failed
selector_not_found
login_challenge
rate_limited
blocked
error
```

login challenge와 rate limit은 별도 flag로도 저장한다.

## 11. 검증 명령

```bash
python -m py_compile scripts/discover_x_account_candidates.py
python scripts/discover_x_account_candidates.py --help
python - <<'PY'
import csv
from pathlib import Path

for path in [
    "config/fortune100_account_candidates.csv",
    "data/audit/x_account_discovery_recommendations.csv",
    "data/audit/x_account_discovery_audit.csv",
]:
    p = Path(path)
    print(path, "exists=", p.exists())
    if p.exists():
        with p.open(encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        print("rows=", len(rows))
        print("columns=", rows[0].keys() if rows else "header-only or empty")
PY
```

