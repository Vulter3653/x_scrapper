# X Brand Intelligence Scraper and Dashboard

이 프로젝트는 X/Twitter 브랜드 계정의 포스트를 쿠키 기반 Playwright 브라우저 세션으로 수집하고, 수집 결과에 대해 LDA topic analysis, zero-shot sentiment analysis, HSQ 기반 zero-shot humor classification을 실행한 뒤 Cloudflare Pages 정적 대시보드로 확인하는 프로젝트입니다.

## Current Scope

현재 운영 대상 브랜드는 다음 세 계정입니다.

- `Wendys`
- `CocaCola`
- `MoonPie`

저장소의 표준 데이터 구조는 브랜드별 폴더 구조입니다.

```text
data/<account>/posts.json
data/<account>/scrape_state.json
data/<account>/lda_topics.json
data/<account>/lda_topics.md
data/<account>/zero_shot_sentiment.json
data/<account>/zero_shot_sentiment.md
data/<account>/hsq_humor_classification.json
data/<account>/hsq_humor_classification.md
```

Cloudflare Pages 배포용 복사본은 다음 위치에 동기화됩니다.

```text
dashboard/data/<account>/
```

## Scraper

현재 scraper는 `scrape_x.py`이며, Playwright 기반으로 실제 Chromium 브라우저를 실행합니다. 브라우저에 X cookie를 주입한 뒤 `https://x.com/{TARGET_USER}` 프로필을 열고 스크롤하면서 X 웹앱의 GraphQL 응답을 캡처합니다.

사용하는 repository secrets는 다음과 같습니다.

```text
X_AUTH_TOKEN
X_CT0
```

로컬 실행 예시는 다음과 같습니다.

```bash
source venv/bin/activate
export X_AUTH_TOKEN='브라우저 auth_token 쿠키 값'
export X_CT0='브라우저 ct0 쿠키 값'
export TARGET_USER='Wendys'
export MAX_SCROLLS='2500'
export SCROLL_DELAY_SECONDS='1.25'
export IDLE_SCROLL_LIMIT='60'
python scrape_x.py
```

`MAX_SCROLLS`는 최대 스크롤 횟수이고, `IDLE_SCROLL_LIMIT`은 새 포스트가 더 이상 캡처되지 않을 때 멈추는 기준입니다. 중간에 중단되어도 이미 캡처한 포스트는 `data/<account>/posts.json`에 누적 저장됩니다.

## GitHub Actions

주요 workflow는 다음과 같습니다.

- `Scrape X Posts`: 수집, 분석, dashboard sync, commit/push를 실행합니다.
- `Run LDA Analysis`: 기존 `posts.json`을 기준으로 LDA만 실행합니다.
- `Run Zero-Shot Sentiment`: 기존 `posts.json`을 기준으로 zero-shot sentiment만 실행합니다.
- `Run HSQ Humor Classification`: 기존 `posts.json`을 기준으로 HSQ humor classification만 실행합니다.
- `Dashboard Check`: dashboard 정적 파일과 JavaScript 문법, deprecated overlay script 미사용 여부를 검증합니다.

### Daily Schedule

현재 `Scrape X Posts` workflow는 매일 한국 시간 00:37(KST)에 자동 실행되도록 설정되어 있습니다.

```text
cron: 37 15 * * * UTC
KST: 매일 00:37
```

스케줄 실행에서는 `Wendys`, `CocaCola`, `MoonPie`가 matrix job으로 병렬 실행됩니다. 수동 실행(`workflow_dispatch`)에서는 입력한 `target_user` 한 계정만 실행됩니다.

스케줄 실행 후 동일 job에서 다음 분석이 자동 실행됩니다.

```bash
python analyze_posts.py --task all
```

자동 분석의 LDA 후보 범위는 기본적으로 2-9 topics입니다.

### Dashboard Check Workflow

`dashboard-check.yml`은 dashboard 관련 파일이 변경될 때 실행됩니다. 주요 검증 항목은 다음과 같습니다.

```text
필수 파일 존재 여부
- dashboard/index.html
- dashboard/app.js
- dashboard/styles.css
- dashboard/brand-visual.css

JavaScript 문법 검증
- node --check dashboard/app.js
- node --check dashboard/localize-ko.js

불안정 overlay script 미사용 확인
- brand-view-ko.js가 index.html에 로드되지 않는지 확인
- humor-matrix.js가 index.html에 로드되지 않는지 확인

React 내부 통합 여부 확인
- BrandScopeVisual 컴포넌트 존재
- HumorQuadrantMatrix 컴포넌트 존재
```

## Analysis Outputs

### LDA Topic Analysis

- 출력 파일: `data/<account>/lda_topics.json`, `data/<account>/lda_topics.md`
- 토픽 수는 고정값이 아니라 후보 범위에서 NPMI-style coherence가 가장 높은 값을 선택합니다.

### Zero-Shot Sentiment Analysis

- 출력 파일: `data/<account>/zero_shot_sentiment.json`, `data/<account>/zero_shot_sentiment.md`
- 기본 모델: `typeform/distilbert-base-uncased-mnli`
- 기본 후보 라벨: `positive`, `neutral`, `negative`
- 기본 hypothesis template: `This post expresses a {} sentiment.`

### HSQ Humor Classification

- 출력 파일: `data/<account>/hsq_humor_classification.json`, `data/<account>/hsq_humor_classification.md`
- 코드북: `HSQ_zero_shot_humor_classification_codebook.md`
- 후보 라벨:
  - `Affiliative humor`
  - `Self-enhancing humor`
  - `Aggressive humor`
  - `Self-defeating humor`
- 실행 태스크: `python analyze_posts.py --task humor`

## React Cloudflare Dashboard

정적 대시보드는 `dashboard/` 폴더에 있습니다. 현재 대시보드는 기존 vanilla HTML dashboard에서 React UMD 기반 정적 dashboard로 전환되었습니다. 별도 Vite/build step 없이 Cloudflare Pages static deployment 구조를 유지합니다.

Cloudflare Pages 설정은 다음과 같습니다.

```text
Build command: 비워둠
Build output directory: dashboard
Functions directory: functions
Framework preset: None/static
```

React dashboard의 주요 기능은 다음과 같습니다.

- `All Brands` 통합 분석 view
- `Wendy's`, `Coca-Cola`, `MoonPie` 브랜드별 분석 view
- Dataset Status: Posts, LDA, Sentiment, HSQ Humor 가용 상태 표시
- Executive Summary: 총 포스트 수, 기간, engagement, viral share, dominant humor 표시
- Descriptive Analysis: 데이터셋 및 engagement profile 요약
- Brand Comparison: 브랜드별 posting volume, engagement, sentiment, humor 비교
- Brand-Level Visualization: 선택한 브랜드 기준 월별 게시량, 월별 참여도, 감성 분포, 토픽 분포, 2×2 유머 분포도, 상위 게시물 표시
- Model-Free Evidence: humor type, sentiment, viral composition 기반 관찰 패턴 제시
- Posting & Engagement: 월별 posting volume 및 engagement mix
- Sentiment Analysis: zero-shot sentiment 분포 및 브랜드별 비교
- Humor Analysis: HSQ humor type distribution, aggressive humor focus, humor-by-brand 비교
- Topic Analysis: LDA topic share, topic-engagement-humor 연결 분석
- Post Explorer: sentiment, humor, topic, engagement, X 원문 링크 확인
- 반응형 UI: desktop/tablet/mobile 대응

대시보드는 다음 JSON을 직접 fetch합니다.

```text
dashboard/data/<account>/posts.json
dashboard/data/<account>/lda_topics.json
dashboard/data/<account>/zero_shot_sentiment.json
dashboard/data/<account>/hsq_humor_classification.json
dashboard/data/<account>/scrape_state.json
```

## Dashboard Stability Rules

대시보드 안정성을 위해 다음 원칙을 유지합니다.

```text
모든 UI는 dashboard/app.js 내부 React 컴포넌트에서 렌더링한다.
React 외부에서 .content, .tabs, #root 내부 DOM을 직접 삽입하거나 제거하지 않는다.
MutationObserver 기반 overlay script를 사용하지 않는다.
브랜드별 시각화와 2×2 유머 분포도는 React state(selected)를 기준으로 렌더링한다.
```

Deprecated overlay 파일은 제거되었습니다.

```text
dashboard/brand-view-ko.js
dashboard/humor-matrix.js
```

## Data Synchronization

`synchronize_dashboard_data.py`가 아니라 현재 사용되는 동기화 스크립트는 다음입니다.

```text
sync_dashboard_data.py
```

이 스크립트는 `data/<account>/` 결과를 `dashboard/data/<account>/`로 복사합니다. `Scrape X Posts`, LDA, sentiment, humor workflow는 결과 생성 후 dashboard data sync를 실행하도록 구성되어 있습니다.

## Notes and Risks

- X cookie 값은 비밀번호와 유사하게 취급해야 하며 저장소에 커밋하면 안 됩니다.
- X가 응답 제한, 로그인 검증, 일시 차단을 걸 수 있습니다.
- X 웹 타임라인이 모든 과거 포스트를 항상 노출한다고 보장할 수 없습니다.
- likes, replies, retweets, views 등 engagement metric은 수집 이후에도 변할 수 있습니다.
- LDA는 짧은 social post에서 exploratory analysis로 해석해야 합니다.
- Zero-shot sentiment와 humor classification은 모델 기반 추정값이며, 수동 검증 또는 sampling audit이 필요할 수 있습니다.
