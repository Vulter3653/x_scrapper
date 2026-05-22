# Wendy's X Posts Scraper

이 프로젝트는 Wendy's X 계정(`@Wendys`)의 포스트를 쿠키 기반 세션으로 수집해 JSON 파일로 저장합니다. 기본 실행은 `Tweets`와 `Replies` 타임라인을 동시에 진행하고, 결과는 ID 기준으로 누적 병합합니다. 긴 실행이 중단되어도 손실을 줄이도록 각 페이지를 받을 때마다 결과 파일과 커서 상태를 즉시 저장합니다.

## 현재 방식

- 라이브러리: `twikit`
- 인증: 브라우저에서 추출한 `auth_token`, `ct0` 쿠키
- 기본 대상: `Wendys`
- 기본 출력: `wendys_posts.json`
- 진행 상태: `wendys_scrape_state.json`
- 기본 수집 범위: `Tweets,Replies`

X 타임라인은 다음 페이지 커서를 이전 응답에서 받아야 하므로 한 타임라인 안의 페이지 요청은 순차 진행됩니다. 대신 `Tweets`와 `Replies` 같은 서로 다른 타임라인은 병렬로 실행합니다.

## 로컬 실행

```bash
source venv/bin/activate
export X_AUTH_TOKEN='브라우저 auth_token 쿠키 값'
export X_CT0='브라우저 ct0 쿠키 값'
python scrape_x.py
```

선택 환경변수:

```bash
export TARGET_USER='Wendys'
export TWEET_TYPES='Tweets,Replies'
export PAGE_SIZE='100'
export MAX_PAGES_PER_TYPE='0'
export PAGE_DELAY_SECONDS='0.5'
export RESET_CURSOR='false'
python scrape_x.py
```

`MAX_PAGES_PER_TYPE=0`은 다음 커서가 없어질 때까지 계속 수집한다는 뜻입니다. 중간에 중단되면 `wendys_scrape_state.json`의 커서에서 이어서 실행합니다. 새로 최신 페이지부터 다시 시작하려면 `RESET_CURSOR=true`를 사용합니다.

## GitHub Actions 즉시 실행

이제 매일 자동 실행하지 않습니다. 전체 수집이 필요할 때 GitHub Actions의 `Scrape Wendy's X Posts` 워크플로우를 수동 실행합니다.

필수 repository secrets:

- `X_AUTH_TOKEN`: X 브라우저 쿠키의 `auth_token`
- `X_CT0`: X 브라우저 쿠키의 `ct0`

권장 수동 실행 입력값:

- `target_user`: `Wendys`
- `tweet_types`: `Tweets,Replies`
- `page_size`: `100`
- `max_pages_per_type`: `0`
- `page_delay_seconds`: `0.5`
- `reset_cursor`: 첫 전체 실행이면 `true`, 이어받기면 `false`

워크플로우는 최대 6시간 실행되며 결과 파일과 상태 파일을 커밋합니다. 실행 도중 타임아웃되더라도 마지막으로 저장된 페이지까지는 워크스페이스에 기록되지만, GitHub Actions가 강제 종료되면 커밋 단계까지 도달하지 못할 수 있습니다. 이 경우 같은 입력값으로 다시 실행하면 저장소에 남은 상태 파일 기준으로 이어받습니다.

## 결과 파일

`wendys_posts.json`은 다음 필드를 포함합니다.

- `id`
- `created_at`
- `text`
- `retweet_count`
- `favorite_count`
- `reply_count`
- `quote_count`
- `view_count`
- `lang`
- `source_type`

동일 포스트가 여러 타임라인에서 발견되면 ID 기준으로 하나로 병합하고 `source_type`에 출처를 합칩니다.

## 주의

- 쿠키 값은 비밀번호와 유사하게 취급해야 하며 저장소에 커밋하지 마세요.
- X가 응답 제한, 로그인 검증, 일시 차단을 걸 수 있습니다. 이 경우 재시도 후에도 실패할 수 있습니다.
- 너무 낮은 `PAGE_DELAY_SECONDS` 값은 수집 실패 가능성을 높입니다.
