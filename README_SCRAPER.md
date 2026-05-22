# Wendy's X Posts Scraper

이 프로젝트는 Wendy's X 계정(`@Wendys`)의 포스트를 쿠키 기반 세션으로 수집해 JSON 파일로 저장합니다. 실제 브라우저로 `x.com` 프로필을 열고 스크롤하면서 X가 내려주는 GraphQL 응답을 캡처합니다. 결과는 ID 기준으로 누적 병합하며, 새 응답을 받을 때마다 결과 파일과 상태 파일을 즉시 저장합니다.

## 현재 방식

- 라이브러리: `playwright`
- 인증: 브라우저에서 추출한 `auth_token`, `ct0` 쿠키
- 기본 대상: `Wendys`
- 기본 출력: `wendys_posts.json`
- 진행 상태: `wendys_scrape_state.json`
- 기본 수집 범위: 프로필 타임라인에서 로드되는 Wendy's 포스트

브라우저 스크롤 기반이므로 내부 API 병렬 요청보다 느리지만, 현재 `twikit`의 client-transaction 파싱 실패를 피할 수 있는 무료 방식입니다.

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
export MAX_SCROLLS='2500'
export SCROLL_DELAY_SECONDS='1.25'
export IDLE_SCROLL_LIMIT='60'
python scrape_x.py
```

`MAX_SCROLLS`는 최대 스크롤 횟수이고, `IDLE_SCROLL_LIMIT`은 새 포스트가 더 이상 캡처되지 않을 때 멈추는 기준입니다. 중간에 중단되어도 이미 캡처한 포스트는 `wendys_posts.json`에 누적 저장됩니다.

## GitHub Actions 즉시 실행

이제 매일 자동 실행하지 않습니다. 전체 수집이 필요할 때 GitHub Actions의 `Scrape Wendy's X Posts` 워크플로우를 수동 실행합니다.

필수 repository secrets:

- `X_AUTH_TOKEN`: X 브라우저 쿠키의 `auth_token`
- `X_CT0`: X 브라우저 쿠키의 `ct0`

권장 수동 실행 입력값:

- `target_user`: `Wendys`
- `max_scrolls`: `2500`
- `scroll_delay_seconds`: `1.25`
- `idle_scroll_limit`: `60`

워크플로우는 최대 6시간 실행되며 결과 파일과 상태 파일을 커밋합니다. 실행 도중 타임아웃되더라도 마지막으로 저장된 페이지까지는 워크스페이스에 기록되지만, GitHub Actions가 강제 종료되면 커밋 단계까지 도달하지 못할 수 있습니다. 이 경우 같은 입력값으로 다시 실행하면 저장소에 남은 상태 파일 기준으로 이어받습니다.

## 결과 파일

`wendys_posts.json`은 다음 필드를 포함합니다.

- `id`
- `tweet_url`: 해당 포스팅 링크
- `created_at`: 작성 날짜
- `text`: 포스팅 글
- `favorite_count`: 좋아요 수
- `retweet_count`: 리트윗 수
- `reply_count`: 댓글 수
- `quote_count`: 인용 수
- `bookmark_count`: 북마크 수
- `view_count`: 조회 수
- `lang`
- `source`

동일 포스트가 여러 타임라인에서 발견되면 ID 기준으로 하나로 병합하고 `source_type`에 출처를 합칩니다.

## 주의

- 쿠키 값은 비밀번호와 유사하게 취급해야 하며 저장소에 커밋하지 마세요.
- X가 응답 제한, 로그인 검증, 일시 차단을 걸 수 있습니다. 이 경우 재시도 후에도 실패할 수 있습니다.
- 너무 낮은 `PAGE_DELAY_SECONDS` 값은 수집 실패 가능성을 높입니다.
