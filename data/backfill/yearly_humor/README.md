# Yearly Humor Backfill — Runbook

## 수집 원칙: Oldest-Year-First

**수집 순서: 2009 → 2010 → 2011 → ... → 2021**

각 연도는 이전 연도의 recoverable failure가 0이 될 때만 다음 연도로 이동한다.
전체 범위(2009–2021) 동시 실행은 2009 단일 연도 안정성 테스트 이후에만 권장.

### 이유

- oldest-first로 수집해야 가장 희소한 초기 데이터(2009–2015)가 먼저 확보됨
- render_failure 같은 불안정 요인을 작은 연도(post 수 적음) 부터 검증
- 각 연도 성공률 확인 → 병렬도/스크롤 수 파라미터 튜닝 후 다음 연도 진행

---

## 권장 실행 파라미터

### 1단계: 2009 단일 연도 안정성 테스트

```
workflow: Yearly Humor Backfill Serial Years
inputs:
  target_year: 2009
  start_year: 2009
  end_year: 2009
  max_posts_per_account: 0
  max_scrolls: 3500
  max_parallel_companies: 1
  target_scope: all
  retry_round: 0
  commit_results: false
```

### 2단계: 2009 실패분 재시도

```
workflow: Yearly Humor Backfill Serial Years
inputs:
  target_year: 2009
  max_parallel_companies: 1
  target_scope: failed_only
  retry_round: 1
  commit_results: false
```

- `recoverable_failure_count == 0`이 될 때까지 retry_round를 올리며 반복
- failed_only mode는 `recoverable_failed_*` 상태인 기업만 재시도함
- terminal 상태(`terminal_created_after_year` 등)는 재시도 대상이 아님

### 3단계: 2009 완료 후 2010으로 이동

2009 `recoverable_failure_count == 0` 또는 terminal-only 상태 확인 후:

```
target_year: 2010
target_scope: all
retry_round: 0
commit_results: false
```

반복하여 2021까지 진행.

### 4단계: 결과 commit

각 연도 또는 전체 완료 후:

```
commit_results: true
```

---

## Status 코드 설명

### Recoverable (재시도 가능)

| Status | 의미 | 조치 |
|---|---|---|
| `recoverable_failed_render` | Playwright render 실패 | max_parallel=1로 재시도 |
| `recoverable_failed_did_not_reach_year` | 스크롤이 target year까지 도달하지 못함 | max_scrolls 증가 후 재시도 |
| `recoverable_failed_timeout` | 3000s timeout 초과 | 재시도 |
| `recoverable_failed_network` | 네트워크/DNS 오류 | 재시도 |
| `recoverable_failed_browser` | 일반 브라우저 오류 | 재시도 |
| `recoverable_failed_temporary_x_error` | X rate limit / 일시 오류 | 대기 후 재시도 |

### Terminal (재시도 불가)

| Status | 의미 | 근거 |
|---|---|---|
| `terminal_created_after_year` | 계정이 target year 이후 생성 | `account_created_year > target_year` 확인 필수 |
| `terminal_no_observable_posts_for_year` | 수집 성공이나 포스트 없음 | 계정 존재하나 해당 연도 포스트 없음 |
| `terminal_account_protected` | 비공개 계정 | |
| `terminal_account_suspended` | 정지된 계정 | |
| `terminal_account_unavailable` | 계정 없음/삭제됨 | |

### 중요: terminal_created_after_year 판정 기준

`terminal_created_after_year`는 반드시 `account_created_year > target_year`가
확인된 경우에만 부여.

`earliest_observed_post_year > target_year`만으로는 terminal 판정 불가 —
이것은 "아직 충분히 스크롤하지 못했다"는 의미로 `recoverable_failed_did_not_reach_year`로 처리.

---

## 주의사항

### max_parallel_companies

- **기본값: 1 (권장)**
- 동일 runner에서 Playwright 병렬 실행 → render_failure 대량 발생 위험
- 2021 테스트: max_parallel=2에서 93개 render_failure 발생 (1개만 성공)
- 2 이상은 render 안정성 확인 후에만 사용

### 실행 금지 사항

- 실제 scraping 실행 전에 `build_yearly_humor_backfill_targets.py` 선실행 필수
- `commit_results: true`는 안정성 확인 후에만 사용
- 기존 run 취소/재실행 없이 이 workflow와 병행 실행 가능
  (concurrency group: `backfill-humor-yearly-serial`)

---

## 디렉토리 구조

```
data/backfill/yearly_humor/
  audit/
    year_target_summary.csv       # 전체 연도 요약 (global)
  {year}/
    audit/
      year_{year}_target_companies.csv   # 기업별 수집 결과
      year_{year}_failed_targets.csv     # recoverable 실패만
      year_{year}_terminal_targets.csv   # terminal 상태만
      year_{year}_summary.csv            # 연도 요약
    posts/
      y{year}__{group}__{company}__{handle}/
        collected_posts_raw.json
        posts_on_or_before_{year}.json
        scraper_stdout_tail.txt    # 실패 원인 분석용 로그
        scraper_stderr_tail.txt
        scraper_combined_tail.txt
        scraper_exit_status.json
        scrape_metrics.json
```

---

## Validation

```bash
# 기본 검증 (출력 없을 때)
python scripts/validate_yearly_humor_backfill_outputs.py --allow-empty

# 특정 연도 검증
python scripts/validate_yearly_humor_backfill_outputs.py --target-year 2009

# 엄격 모드 (warning도 FAIL)
python scripts/validate_yearly_humor_backfill_outputs.py --target-year 2009 --strict
```
