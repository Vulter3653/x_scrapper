# Fortune 100 X Collection Audit Protocol

## 1. 목적

Fortune 100 기업의 X 수집 가능성을 기업별로 기록한다. X 접근 제한, 로그인 challenge, 계정 부재, 오래된 게시물 탐색 한계를 조용히 무시하지 않는다.

## 2. Audit 관측 단위

```text
firm_id x collection_batch_id x scrape_attempt
```

권장 파일:

```text
data/panel/collection_audit.csv
data/panel/collection_audit.json
```

## 3. 필수 열

```text
firm_id
firm_name
x_handle
profile_accessible
tweets_rendered
first_visible_post_date
oldest_collected_post_date
newest_collected_post_date
post_count_collected
scrolls_completed
idle_stop_triggered
blocked_or_login_challenge
error_type
error_message
last_successful_scrape_at
needs_manual_review
collection_batch_id
scrape_attempt
scraped_at
```

## 4. 상태 정의

### `profile_accessible`

- `1`: X profile URL이 로드됨
- `0`: profile URL 자체를 열지 못함

### `tweets_rendered`

- `1`: `[data-testid="tweet"]` selector가 렌더링됨
- `0`: selector가 렌더링되지 않음

### `blocked_or_login_challenge`

- `1`: login challenge, rate limit, suspicious activity, empty protected page 등 차단 정황
- `0`: 명시적 차단 정황 없음

### `needs_manual_review`

- `1`: 계정 공식성, profile 접근성, coverage, 오류 원인을 사람이 확인해야 함
- `0`: 자동 수집 결과가 검수 조건을 충족

## 5. error_type 표준값

```text
none
missing_official_handle
ambiguous_handle
profile_not_found
profile_protected
login_challenge
rate_limited
tweets_not_rendered
browser_timeout
graphql_response_missing
partial_collection
analysis_failed
unknown
```

## 6. 수집 전 계정 검수

각 firm에 대해:

1. `config/fortune100_account_candidates.csv` 확인
2. corporate 계정 우선 선택
3. official website social link 저장
4. X verified profile 상태 저장
5. parent company와 product brand 구분
6. support 계정은 primary handle로 사용하지 않음
7. 공식 계정이 없으면 `include_flag=0`
8. 모호하면 `include_flag=0`, `exclusion_reason=ambiguous_handle`

## 7. 소규모 dry run

전체 Fortune 100 실행 전 rank 1-10 batch로만 검증한다.

권장 초기값:

```text
batch_id=batch_01_dry_run
rank_min=1
rank_max=10
max_scrolls=25
scroll_delay_seconds=1.25
idle_scroll_limit=10
analysis_task=none
```

dry run에서는 분석 모델을 실행하지 않는다. profile 접근성과 게시물 렌더링만 확인한다.

## 8. 본 수집 실행

dry run을 통과한 firm만 본 수집 대상으로 전환한다.

권장 batch:

```text
batch_01: rank 1-10
batch_02: rank 11-20
...
batch_10: rank 91-100
```

각 batch는 독립적으로 재실행 가능해야 한다. 한 기업 실패가 다른 기업 데이터를 삭제하거나 aggregate export를 덮어쓰면 안 된다.

## 9. Artifact 및 실패 보존

기업별 artifact:

```text
staging/data/<account>/posts.json
staging/data/<account>/scrape_state.json
staging/audit/<firm_id>.json
```

실패 시:

- posts가 없더라도 audit JSON 업로드
- `error_type`, `error_message` 기록
- `needs_manual_review=1`
- 이전 성공 데이터를 삭제하지 않음
- aggregate job은 성공 artifact만 merge

## 10. Coverage 검수

수집 성공 후 다음을 확인한다.

```text
post_count_collected > 0
newest_collected_post_date != ""
scrolls_completed >= 0
collection_batch_id != ""
```

추가 수동 검수 조건:

- 게시물 수가 지나치게 적음
- newest post가 현재 시점보다 현저히 오래됨
- profile은 열렸지만 tweet selector가 없음
- 반복 idle stop이 너무 빠르게 발생
- 이전 run 대비 게시물 수가 감소
- 기업 계정이 아닌 product/support 계정 정황

## 11. Analysis 실행 경계

분석은 수집 audit 이후 별도 단계에서 수행한다.

- dry run: `analysis_task=none`
- 검증 batch: `analysis_task=lda`
- 승인된 batch: `analysis_task=all`

100개 기업 전체 zero-shot 분석을 최초 실행에서 강제하지 않는다.

## 12. Dashboard 반영 경계

dashboard에는 승인된 firm만 표시한다.

```text
include_flag == 1
collection_status in {"success", "partial"}
```

`partial`은 coverage warning badge를 표시한다. failed firm은 삭제하지 않고 audit 화면 또는 별도 보고서에서 확인 가능해야 한다.

