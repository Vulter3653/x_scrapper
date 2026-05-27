# Gemini 작업 인수인계 가이드라인

이 문서는 `Vulter3653/x_scrapper` 프로젝트를 Gemini가 이어받아 작업할 때 반드시 따라야 하는 엄격한 지침이다. 이 파일의 목적은 기능 요구사항을 다시 해석하는 것이 아니라, 현재 구현 상태를 보존하면서 일관된 방식으로 유지보수와 추가 작업을 수행하게 하는 것이다.

## 1. 프로젝트 목적

이 repo는 X/Twitter 브랜드 계정 게시물을 수집하고, 브랜드별 분석 결과를 정적 Cloudflare Pages 대시보드로 제공한다.

현재 대상 브랜드:

- Wendy's: `Wendys`, slug `wendys`
- Coca-Cola: `CocaCola`, slug `cocacola`
- MoonPie: `MoonPie`, slug `moonpie`

핵심 산출물:

- 브랜드별 원문 게시물: `data/<brand>/posts.json`
- 브랜드별 수집 상태: `data/<brand>/scrape_state.json`
- 브랜드별 LDA 결과: `data/<brand>/lda_topics.json`, `data/<brand>/lda_topics.md`
- 브랜드별 zero-shot 감성 결과: `data/<brand>/zero_shot_sentiment.json`, `data/<brand>/zero_shot_sentiment.md`
- 브랜드별 HSQ 유머 분류 결과: `data/<brand>/hsq_humor_classification.json`, `data/<brand>/hsq_humor_classification.md`
- 논문/보고서용 통합 분석 산출물: `data/analysis/*`
- Cloudflare Pages 대시보드용 복사본: `dashboard/data/*`

## 2. 절대 지켜야 할 원칙

1. 기존 기능을 삭제하지 말 것.
2. 데이터 스키마를 임의로 바꾸지 말 것.
3. 브랜드별 데이터는 반드시 `data/<brand>/` 폴더 구조로 유지할 것.
4. `dashboard/data/`는 배포용 복사본이다. 원본은 `data/`에 두고 `python sync_dashboard_data.py`로 동기화한다.
5. 메인 대시보드와 수동 검토 가이드는 분리된 화면으로 유지한다.
6. `dashboard/review.html`은 읽기 전용 가이드 화면이다. 입력창, 저장 버튼, 다운로드 버튼, 편집 UI를 다시 추가하지 말 것.
7. 수동 검토 결과를 브라우저에서 저장하는 방식으로 만들지 말 것. 실제 변경은 `config/` 또는 `data/analysis/` 파일에 명시적으로 반영해야 한다.
8. GitHub Actions의 자동 push 로직을 수정할 때는 push 충돌 방지용 fetch/rebase/retry 구조를 유지할 것.
9. 민감정보를 commit하지 말 것. `X_AUTH_TOKEN`, `X_CT0`, GitHub token, Cloudflare token은 GitHub Secrets 또는 Cloudflare 환경 변수에만 둔다.
10. 작업 완료 후 반드시 검증 명령을 실행하고, 문제가 없으면 commit/push한다.

## 3. 주요 파일 역할

### Scraper

- `scrape_x.py`
  - Playwright 기반 X 게시물 수집기.
  - `TARGET_USER` 기준으로 브랜드를 선택한다.
  - 출력은 기본적으로 `data/<brand>/posts.json` 및 `data/<brand>/scrape_state.json`이다.
  - 최소 필요 컬럼은 게시물 본문, 날짜, 좋아요 수, 리트윗 수, 댓글 수, quote 수, 링크다.

### Analysis

- `analyze_posts.py`
  - LDA, zero-shot sentiment, HSQ humor classification을 수행한다.
  - `TARGET_USER` 환경변수로 대상 브랜드를 결정한다.
  - LDA topic 수는 고정 입력값이 아니라 coherence 기준으로 선택한다.
  - 현재 workflow는 `LDA_MIN_TOPICS=2`, `LDA_MAX_TOPICS=9`로 실행한다.
  - 감성 라벨 설정은 `config/sentiment_labels.json`을 사용한다.
  - HSQ 유머 라벨 설정은 `config/humor_labels.json`을 사용한다.
  - LDA 불용어는 `config/lda_stopwords.txt`를 사용한다.

### Research Export

- `export_research_outputs.py`
  - 브랜드별 분석 결과를 통합해 논문/보고서용 테이블을 만든다.
  - 주요 산출물:
    - `data/analysis/joined_posts.csv/json`
    - `data/analysis/sampling_audit_candidates.csv/json`
    - `data/analysis/table4_humor_sentiment_engagement.csv/json`
    - `data/analysis/table5_engagement_robustness_by_humor.csv/json`
    - `data/analysis/correlation_coefficients.csv/json`
    - `data/analysis/research_export_summary.md`

### Dashboard Sync

- `sync_dashboard_data.py`
  - `data/<brand>/` 및 `data/analysis/` 결과를 `dashboard/data/`로 복사한다.
  - Cloudflare Pages는 `dashboard/`를 output directory로 사용하므로 이 동기화가 필요하다.

### Dashboard

- `dashboard/index.html`
  - 메인 X Brand Intelligence Dashboard.
  - React UMD 기반 정적 대시보드다.

- `dashboard/app.js`
  - 메인 대시보드의 핵심 UI와 분석 시각화.
  - Overview, Descriptives, Model-free Evidence, Posting, Topics, Sentiment, Humor, Posts 등 기존 섹션을 유지해야 한다.

- `dashboard/review.html`
  - 사람이 해야 할 판단 기준을 안내하는 별도 페이지.
  - 현재 의도는 `작업 수행 화면`이 아니라 `읽기 전용 가이드 화면`이다.

- `dashboard/research-review.js`
  - `review.html`에서 사용하는 읽기 전용 가이드 컴포넌트.
  - 포함 내용:
    - 이 페이지에서 하는 일과 하지 않는 일
    - Sampling Audit 판단 기준
    - Zero-shot 감성/유머 분류 가이드라인
    - LDA Stopword 추가 가이드라인
    - LDA Topic 해석 가이드라인
    - 수정 반영 절차
  - 금지: textarea/select 기반 수동 편집 UI, 다운로드 버튼, 브라우저 내 저장 기능.

- `dashboard/styles.css`, `dashboard/brand-visual.css`
  - 메인 대시보드와 review guide의 CSS.
  - 모바일 반응형을 깨뜨리지 말 것.

## 4. GitHub Actions 구조

주요 workflow:

- `.github/workflows/scrape.yml`
  - 수집, LDA, 감성, HSQ 유머 분석, export, dashboard sync, commit/push까지 수행한다.
  - schedule 실행 시 `Wendys`, `CocaCola`, `MoonPie` matrix로 병렬 실행한다.
  - 현재 cron은 `37 15 * * *` UTC다. 이는 한국시간 기준 00:37이다.
  - 사용자가 “KST 00:01”을 다시 요구하면 cron은 `1 15 * * *` UTC로 수정해야 한다.
  - secrets `X_AUTH_TOKEN`, `X_CT0`가 반드시 필요하다.

- `.github/workflows/lda.yml`
  - LDA 단독 실행용.

- `.github/workflows/sentiment.yml`
  - zero-shot sentiment 단독 실행용.

- `.github/workflows/humor.yml`
  - HSQ humor classification 단독 실행용.

- `.github/workflows/dashboard-check.yml`
  - 정적 대시보드 필수 파일과 JS 문법, review guide 문자열을 검증한다.

주의:

- workflow에서 Node 20 deprecation warning을 피하기 위해 `FORCE_JAVASCRIPT_ACTIONS_TO_NODE24` 또는 Node 24 설정을 유지한다.
- 자동 commit/push 단계는 remote 최신화 문제를 피하기 위해 push 실패 시 fetch/rebase/retry를 유지한다.

## 5. 수동 검토와 성능 개선 방식

사용자는 zero-shot과 LDA 성능을 사람이 직접 판단해 개선하려고 한다. 이 작업은 아래 순서로 해야 한다.

1. `dashboard/review.html`에서 판단 기준과 예시를 확인한다.
2. 수동으로 문제 패턴을 찾는다.
3. 반복 오분류가 확인될 때만 config를 수정한다.
4. LDA 토픽 해석을 방해하는 단어가 반복될 때만 `config/lda_stopwords.txt`에 추가한다.
5. 아래 명령으로 재분석한다.

```bash
python analyze_posts.py --task all
python export_research_outputs.py
python sync_dashboard_data.py
```

감성/유머 수정 기준:

- 감성 라벨은 기본적으로 `positive`, `neutral`, `negative`를 유지한다.
- HSQ 유머 라벨은 다음을 유지한다.
  - `Affiliative humor`
  - `Self-enhancing humor`
  - `Aggressive humor`
  - `Self-defeating humor`
  - `Non-humorous brand message`
- `Non-humorous brand message`는 일반 홍보/안내/고객응대 게시물이 강제로 유머로 분류되는 문제를 줄이기 위한 필수 라벨이다.

LDA 수정 기준:

- 불용어는 보수적으로 추가한다.
- 제품명, 캠페인명, 브랜드 톤을 드러내는 단어는 제거하지 않는다.
- topic 수는 coherence 기준 자동 선택을 유지한다.
- workflow 분석 범위는 topic 후보 2-9개를 유지한다.

## 6. Dashboard 유지보수 규칙

1. 메인 대시보드는 `dashboard/index.html` + `dashboard/app.js` 중심이다.
2. review guide는 `dashboard/review.html` + `dashboard/research-review.js` 중심이다.
3. 메인 대시보드에 action 실행 버튼을 다시 추가하지 말 것.
4. review guide에 직접 작업 UI를 다시 추가하지 말 것.
5. 모바일에서 차트/카드가 화면 밖으로 넘치지 않게 유지한다.
6. chart는 empty state를 가져야 한다.
7. 긴 텍스트는 line clamp 또는 카드형 요약으로 처리한다.
8. 브랜드별/감성별/토픽별 비교는 현재 계산 로직을 재사용하고 중복 구현을 피한다.
9. `dashboard-check.yml`에서 확인하는 문자열을 바꾸는 경우 workflow도 함께 갱신한다.

## 7. Cloudflare Pages 설정

Cloudflare Pages 설정은 다음을 유지한다.

- Framework preset: None/static
- Build command: 비움
- Build output directory: `dashboard`
- Root directory: `/`

배포 페이지:

- 메인 대시보드: `https://x-scrapper.pages.dev/`
- 수동 검토 가이드: `https://x-scrapper.pages.dev/review.html`

## 8. 필수 검증 명령

작업 후 가능한 범위에서 아래를 실행한다.

```bash
node --check dashboard/app.js
node --check dashboard/research-review.js
python -m py_compile scrape_x.py analyze_posts.py export_research_outputs.py sync_dashboard_data.py
python export_research_outputs.py
python sync_dashboard_data.py
git status --short
```

대시보드 관련 작업이면 최소한 다음은 반드시 실행한다.

```bash
node --check dashboard/app.js
node --check dashboard/research-review.js
```

분석 코드 관련 작업이면 최소한 다음은 반드시 실행한다.

```bash
python -m py_compile scrape_x.py analyze_posts.py export_research_outputs.py sync_dashboard_data.py
```

## 9. Commit / Push 규칙

사용자는 작업 진행 시 자동 push를 선호한다. 로컬에서만 업데이트하라는 명시가 없으면 작업 완료 후 commit/push한다.

권장 절차:

```bash
git status --short
git add -A
git commit -m "명확한 변경 요약"
git pull --rebase origin main
git push origin main
```

주의:

- 사용자 변경사항을 되돌리지 말 것.
- 작업과 무관한 파일을 임의로 정리하지 말 것.
- `git reset --hard`, `git checkout --`, 강제 push는 사용자가 명시적으로 요청하지 않는 한 금지한다.
- push 실패 시 원격 변경을 확인하고 rebase 후 다시 push한다.

## 10. 현재 완료된 주요 작업 이력

최근 핵심 변경:

- 브랜드별 폴더 구조 도입: `data/<brand>/...`
- MoonPie 수집 및 대시보드 대상 추가
- scrape 후 LDA, sentiment, HSQ humor, export, dashboard sync 자동화
- LDA topic 수를 coherence 기준으로 자동 선택
- coherence 후보 범위 2-9 적용
- HSQ zero-shot humor classification 추가
- correlation coefficients 분석 추가
- 연구용 export table 추가
- 메인 대시보드 UI/UX 및 반응형 개선
- 수동 검토 기능을 별도 화면으로 분리
- `review.html`을 읽기 전용 가이드 화면으로 전환

## 11. 절대 혼동하지 말 것

- `review.html`은 검토 작업을 수행하는 화면이 아니다. 기준을 설명하는 가이드다.
- 사람이 판단한 결과는 브라우저 화면이 아니라 repo 파일에 명시적으로 반영해야 한다.
- `dashboard/data/`는 원본 데이터 저장소가 아니다. 배포용 복사본이다.
- `config/` 변경 후에는 반드시 재분석과 sync를 수행해야 한다.
- schedule 시간은 UTC 기준이다. 한국시간 00:01은 UTC 15:01이다.
- X 수집은 무료 방식의 브라우저/cookie 기반 scraping이다. 공식 유료 API 전제를 넣지 말 것.

## 12. 다음 작업을 시작하기 전 체크리스트

1. `git status --short`로 dirty 상태 확인.
2. 사용자의 최신 요청이 “로컬만 수정”인지 “push까지”인지 확인.
3. 관련 파일을 먼저 읽고 기존 패턴을 따른다.
4. 작업 범위 외 refactor는 하지 않는다.
5. 검증 명령을 실행한다.
6. 결과를 commit/push하고 커밋 해시를 보고한다.
