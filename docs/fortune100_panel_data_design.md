# Fortune 100 X Panel Data Architecture Report

## 1. Repository 구조 확인

현재 저장소는 세 계정 `Wendys`, `CocaCola`, `MoonPie`를 대상으로 다음 구조를 사용한다.

```text
data/<account>/posts.json
data/<account>/scrape_state.json
data/<account>/lda_topics.json
data/<account>/zero_shot_sentiment.json
data/<account>/hsq_humor_classification.json
dashboard/data/<account>/
```

Fortune 100 확장에서도 이 구조를 유지한다. 이번 단계에서는 전체 수집이나 기존 코드 refactor를 실행하지 않았다. 먼저 cohort source, firm master schema, 공식 X 계정 검수 절차, panel schema, batch 수집 경계를 고정한다.

## 2. Fortune source 접근 결과

검수일: `2026-06-01`

Primary source:

- Fortune company index: <https://fortune.com/companies/>

Fallback source:

- Official Fortune 500 ranking page: <https://fortune.com/ranking/fortune500/>

### 접근 결과

`https://fortune.com/companies/`는 Fortune company index다. 검색 엔진에 노출된 공식 페이지 설명에서는 Fortune ranking filter와 company index가 확인되지만, company index 전체를 Fortune 100 cohort로 사용할 수 없다. 알파벳순 index 전체를 Fortune 100으로 오인하면 안 된다.

로컬 자동화 환경에서 `curl -L`로 company index와 ranking fallback에 직접 접근하면 CloudFront가 다음 응답을 반환했다.

```text
403 ERROR
Request blocked.
```

따라서 현재 환경에서는 다음 항목을 신뢰성 있게 자동 추출할 수 없다.

- 정적 HTML 내 전체 rank table
- embedded client-side JSON
- pagination endpoint
- filter API endpoint
- Fortune company detail URL

Fortune 공식 ranking 페이지의 검색 인덱스에서는 현재 접근 가능한 최신 Fortune 500 목록이 `2025` 목록으로 노출된다. 이번 설계는 `fortune_year=2025`를 사용하되, 전체 100개 cohort는 Fortune 공식 페이지를 브라우저에서 수동 검수하거나 허용된 접근 경로를 확보한 뒤 확정해야 한다.

### robots / terms 유의사항

직접 접근 제한이 확인되었으므로 이를 우회하는 scraper를 구현하지 않는다. Fortune 페이지 수집은 robots, terms, 접근 정책을 사람이 확인한 뒤 허용 범위에서 수행해야 한다. 이 문서는 자동 접근 제한을 우회하는 방법을 제공하지 않는다.

## 3. Fortune 100 cohort 구성 방식

운영 master:

```text
config/fortune100_firm_master.csv
```

현재 운영 master에는 header만 존재한다. 전체 100개를 공식 source로 검증하지 못했으므로 임의 데이터는 추가하지 않았다.

공식 ranking index에서 검증 가능한 상위 10개 sample은 다음 파일에 분리했다.

```text
config/fortune100_firm_master_sample.csv
```

샘플도 미확정 필드는 비워 두고 `needs_manual_review`로 기록했다.

### 전체 cohort 확정 검증 조건

전체 master를 작성할 때 반드시 아래를 검증한다.

```text
row_count == 100
fortune_rank 집합 == {1, 2, ..., 100}
fortune_rank 중복 == 0
firm_name 빈 값 == 0
fortune_ranking_source_url 빈 값 == 0
fortune_year == 최신 접근 가능 Fortune 500 연도
```

### firm_id 규칙

```text
f{fortune_year}_{fortune_rank:03d}_{normalized_firm_name}
```

예:

```text
f2025_001_walmart
f2025_007_alphabet
```

## 4. X account 매핑 방식

공식 X 계정은 추정만으로 확정하지 않는다. 후보 파일:

```text
config/fortune100_account_candidates.csv
```

검증 우선순위:

1. 기업 공식 홈페이지 social link
2. 기업 공식 newsroom, media, contact page
3. X profile verified badge 및 공식 홈페이지 연결
4. Fortune company profile social link
5. 수동 검수

계정 역할을 반드시 분리한다.

```text
corporate
customer_support
product_brand
regional
investor_relations
newsroom
other
```

수집 대상은 원칙적으로 `corporate` 계정이다. parent company와 product brand를 혼동하지 않는다. 공식 계정이 없거나 모호하면 `include_flag=0`, `x_handle_confidence=not_found` 또는 `low`, `exclusion_reason`을 기록한다.

## 5. 새로 생성한 파일

```text
config/fortune100_firm_master.csv
config/fortune100_firm_master.schema.json
config/fortune100_account_candidates.csv
config/fortune100_firm_master_sample.csv
docs/fortune100_panel_data_design.md
docs/fortune100_collection_audit_protocol.md
```

## 6. 수정이 필요한 기존 파일

이번 단계에서는 아래 파일을 변경하지 않았다. 후속 구현에서 순차적으로 수정해야 한다.

### `scrape_x.py`

현재 단일 `TARGET_USER` 구조를 유지한다. 다음 firm metadata를 선택적 환경변수로 받도록 확장한다.

```text
FIRM_ID
FORTUNE_YEAR
FORTUNE_RANK
FIRM_NAME
X_HANDLE
COLLECTION_BATCH_ID
```

각 output record와 `scrape_state.json`에 metadata를 추가한다. 기존 3개 브랜드 환경에서는 값이 없어도 동작해야 한다.

### `analyze_posts.py`

기존 분석 기능을 유지한다.

- post ID 기준 cache 재사용
- 이미 분석된 게시물 skip
- 신규 게시물만 분석
- 계정별 실패 로그 기록
- 한 기업 실패가 전체 batch를 중단하지 않도록 orchestration layer에서 격리

### `export_research_outputs.py`

현재 `BRAND_SLUGS = ("wendys", "cocacola", "moonpie")` 하드코딩이 있다. 후속 단계에서 master 기반 동적 export로 교체한다.

- `config/fortune100_firm_master.csv` 읽기
- `include_flag == 1`만 export
- 기존 3개 브랜드 backward compatibility 유지
- `data/panel/post_level_panel.csv`
- `data/panel/firm_day_panel.csv`
- `data/panel/firm_month_panel.csv`

### `sync_dashboard_data.py`

후속 단계에서 다음을 추가한다.

- `data/panel/` -> `dashboard/data/panel/`
- `dashboard/data/firm_index.json`
- master metadata 기반 firm index 생성

### `dashboard/app.js`

현재 `ACCOUNTS`가 세 브랜드로 하드코딩되어 있다. 후속 단계에서:

- `dashboard/data/firm_index.json` fetch
- firm search
- pagination
- Fortune rank range filter
- industry filter
- sector filter
- 선택된 firm만 detail JSON lazy load

100개 기업 전체 데이터를 최초 렌더링에서 동시에 가져오지 않는다.

### `.github/workflows/scrape.yml`

현재 세 계정 matrix가 고정되어 있다. Fortune 100에서는 master 기반 batch selector를 추가한다. 기존 일일 3개 브랜드 자동화는 깨뜨리지 않는다.

## 7. Post-level panel schema

관측 단위:

```text
firm_id x x_handle x post_id
```

필수 열:

| Column | Type | Description |
|---|---|---|
| `firm_id` | string | Firm master key |
| `fortune_year` | integer | Fortune ranking year |
| `fortune_rank` | integer | Fortune 500 rank, restricted to 1-100 |
| `firm_name` | string | Fortune firm name |
| `industry` | string | Fortune industry |
| `sector` | string | Fortune sector |
| `x_handle` | string | Official corporate X handle |
| `post_id` | string | X post ID |
| `tweet_url` | string | X post URL |
| `created_at` | timestamp string | Raw X timestamp |
| `date` | date | UTC calendar date |
| `year` | integer | UTC year |
| `month` | string | UTC year-month |
| `week` | string | ISO week |
| `text` | string | Post text |
| `lang` | string | X language code |
| `reply_count` | integer | Reply count |
| `favorite_count` | integer | Like count |
| `retweet_count` | integer | Retweet count |
| `quote_count` | integer | Quote count |
| `bookmark_count` | integer | Bookmark count when available |
| `view_count` | integer | View count when available |
| `total_engagement` | integer | Reply + favorite + retweet + quote |
| `log_total_engagement` | float | `log(1 + total_engagement)` |
| `conversation_id` | string | X conversation ID |
| `is_quote_status` | boolean | Quote status flag |
| `has_url` | boolean | URL included |
| `hashtag_count` | integer | Hashtag count |
| `mention_count` | integer | Mention count |
| `text_length` | integer | Character length |
| `word_count` | integer | Token-like word count |
| `sentiment_label` | string | Zero-shot sentiment label |
| `sentiment_score` | float | Zero-shot sentiment score |
| `humor_type` | string | HSQ humor label |
| `humor_score` | float | HSQ humor score |
| `topic_id` | string | LDA topic key |
| `topic_score` | float | Topic assignment score or probability |
| `source` | string | Collection source, e.g. `browser_graphql` |
| `scraped_at` | timestamp | Collection timestamp |
| `collection_batch_id` | string | Batch execution key |
| `collection_status` | string | Success, partial, failed |
| `collection_note` | string | Coverage and error note |

## 8. Firm-day panel schema

관측 단위:

```text
firm_id x date
```

필수 열:

```text
firm_id
fortune_year
fortune_rank
firm_name
industry
sector
date
post_count
reply_sum
favorite_sum
retweet_sum
quote_sum
bookmark_sum
view_sum
total_engagement_sum
total_engagement_mean
total_engagement_median
log_total_engagement_mean
positive_post_share
neutral_post_share
negative_post_share
humor_post_share
affiliative_humor_share
self_enhancing_humor_share
aggressive_humor_share
self_defeating_humor_share
non_humorous_share
url_share
avg_text_length
avg_word_count
viral_post_count
collection_coverage_flag
```

`firm_month_panel.csv`는 동일 지표를 `firm_id x month`로 집계한다.

## 9. Collection audit protocol

상세 절차는 다음 문서에 정의했다.

```text
docs/fortune100_collection_audit_protocol.md
```

수집 실패 기업을 삭제하지 않는다. 실패도 panel coverage를 해석하는 데이터다.

## 10. GitHub Actions batch 설계

Fortune 100 전체를 한 번에 실행하지 않는다.

workflow dispatch 입력:

```text
batch_id
rank_min
rank_max
target_firm_id
target_handle
max_scrolls
scroll_delay_seconds
idle_scroll_limit
analysis_task
```

기본 batch:

```text
batch_01: rank 1-10
batch_02: rank 11-20
...
batch_10: rank 91-100
```

권장 구조:

1. master CSV를 읽어 `include_flag == 1` 및 `x_handle != ""` 필터
2. rank range 또는 target firm으로 collection matrix 생성
3. 기업별 scrape 결과와 audit JSON을 artifact로 저장
4. 실패 기업도 audit artifact 유지
5. aggregate job이 성공 artifact를 병합
6. 분석은 `analysis_task` 기준으로 제한 실행
7. panel export 및 dashboard sync는 단일 writer job에서만 수행
8. commit/push도 단일 writer job에서만 수행

## 11. 현재 자동화 가능한 부분

- 기존 단일 X profile Playwright 수집
- 계정별 `posts.json` 증분 병합
- 계정별 LDA, sentiment, HSQ humor 분석
- batch artifact 수집 구조
- master 기반 firm metadata 주입
- post-level 및 firm-day export
- dashboard firm index 생성

## 12. 수동 검수가 필요한 부분

- Fortune 2025 rank 1-100 전체 확정
- Fortune company detail URL
- company index 접근 정책 검토
- 기업별 공식 website
- 공식 corporate X handle
- verified badge 상태
- parent company / product brand / support account 분리
- X profile 접근 가능성
- 수집 coverage 및 oldest visible post 검수

## 13. 다음 실행 명령어

이번 단계에서는 전체 X 수집을 실행하지 않는다.

파일 형식 검증:

```bash
python -m json.tool config/fortune100_firm_master.schema.json
python - <<'PY'
import csv
from pathlib import Path
for path in [
    Path("config/fortune100_firm_master.csv"),
    Path("config/fortune100_firm_master_sample.csv"),
    Path("config/fortune100_account_candidates.csv"),
]:
    rows = list(csv.DictReader(path.open(encoding="utf-8")))
    print(path, len(rows), "rows")
PY
```

후속 구현이 완료된 뒤 소규모 batch만 실행한다.

```text
batch_01: rank 1-10
```

