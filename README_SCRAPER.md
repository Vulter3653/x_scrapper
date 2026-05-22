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


## 독립 실행 및 병렬 처리

GitHub Actions는 세 개 workflow로 분리되어 있습니다.

- `Scrape X Posts`: X 포스트 수집만 실행
- `Run LDA Analysis`: 기존 `{account}_posts.json`을 읽어 LDA만 실행
- `Run Zero-Shot Sentiment`: 기존 `{account}_posts.json`을 읽어 zero-shot 감성분석만 실행

따라서 스크래퍼, LDA, 감성분석을 각각 따로 실행할 수 있고, 이미 `{account}_posts.json`이 있는 경우 LDA와 감성분석은 동시에 실행할 수 있습니다. 새 수집 결과를 분석해야 한다면 먼저 `Scrape X Posts`가 결과 파일을 push한 뒤 LDA/감성분석을 실행하세요.

분석 결과 파일:

- `{account}_lda_topics.json`
- `{account}_lda_topics.md`

LDA는 입력된 고정 토픽 수를 사용하지 않고, 후보 범위 안에서 여러 LDA 모델을 학습한 뒤 토픽 단어의 NPMI coherence가 가장 높은 토픽 수를 자동 선택합니다.
- `{account}_zero_shot_sentiment.json`
- `{account}_zero_shot_sentiment.md`

예: `target_user=Wendys`이면 `wendys_lda_topics.json`, `wendys_zero_shot_sentiment.json`이 생성됩니다.

Zero-shot 감성분석 기본값:

- 모델: `typeform/distilbert-base-uncased-mnli`
- 후보 라벨: `positive`, `neutral`, `negative`
- 기준 문장: `This post expresses a {} sentiment.`

LDA workflow 입력값:

- `target_user`: 분석 대상 계정명
- `analysis_max_posts`: `0`이면 전체 포스트 분석, 숫자를 넣으면 최신 N개만 분석
- `lda_min_topics`: 자동 선택 후보 토픽 수의 최솟값
- `lda_max_topics`: 자동 선택 후보 토픽 수의 최댓값

감성분석 workflow 입력값:

- `target_user`: 분석 대상 계정명
- `analysis_max_posts`: `0`이면 전체 포스트 분석, 숫자를 넣으면 최신 N개만 분석
- `sentiment_labels`: zero-shot 후보 라벨 목록

GitHub Actions 무료 실행 시간을 줄이고 싶으면 `analysis_max_posts=300`처럼 먼저 샘플 분석을 권장합니다. 전체 감성분석은 모델 다운로드와 zero-shot 추론 때문에 시간이 더 걸립니다.

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


## Cloudflare 대시보드

정적 대시보드는 `dashboard/` 폴더에 있습니다.

Cloudflare Pages 설정:

- Build command: 비워둠
- Build output directory: `dashboard`
- Functions directory: 기본값 `functions`
- Framework preset: None/static

대시보드 기능:

- Wendy's / CocaCola 계정 전환
- 포스트 수, 기간, 참여 지표 요약
- 월별 포스팅량 차트
- 좋아요/댓글/리트윗/인용 비중 차트
- 포스트 검색, 연도 필터, 정렬
- LDA 결과 표시
- zero-shot 감성분석 결과 표시
- Cloudflare Function을 통한 GitHub Actions 실행

GitHub Actions 실행 버튼을 쓰려면 Cloudflare 환경변수를 설정해야 합니다.

- `DASHBOARD_ADMIN_TOKEN`: 대시보드에서 입력할 관리자 토큰
- `GH_ACTIONS_TOKEN`: GitHub Actions workflow dispatch 권한이 있는 GitHub token
- `GITHUB_OWNER`: 기본값 `Vulter3653`
- `GITHUB_REPO`: 기본값 `x_scrapper`
- `GITHUB_REF`: 기본값 `main`

보안 원칙:

- GitHub token은 브라우저에 절대 노출하지 않습니다.
- 브라우저는 `/api/dispatch`에 관리자 토큰만 보내고, Cloudflare Function이 GitHub API를 호출합니다.
- 공개 대시보드라면 `DASHBOARD_ADMIN_TOKEN`을 충분히 길고 예측 불가능하게 설정하세요.

데이터 동기화:

- `sync_dashboard_data.py`가 루트의 `{account}_*.json` 결과를 `dashboard/data/`로 복사합니다.
- Scrape, LDA, Sentiment workflow는 결과 생성 후 자동으로 이 동기화 스크립트를 실행합니다.
