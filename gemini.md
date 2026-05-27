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


## 12. 현재 확인된 자동화 실패 이슈와 Gemini가 반드시 수정해야 할 방향

현재 자동화에서 중요한 문제가 확인되었다. Wendy's는 업데이트되었지만, Coca-Cola와 MoonPie는 실패했거나 최신 데이터/분석 결과가 제대로 반영되지 않은 정황이 있다. Gemini는 이 문제를 단순 재실행으로 처리하지 말고 workflow 구조 문제로 보고 수정해야 한다.

### 12.1 현재 문제 정황

- 최근 원격에는 `Update scraped and analyzed X data for Wendys` 커밋만 확인되었다.
- scheduled matrix 대상은 `Wendys`, `CocaCola`, `MoonPie`이지만 실제 반영은 Wendy's 중심으로만 이루어진 정황이 있다.
- 로컬 기준 데이터 개수는 존재하지만 업데이트 시점이 브랜드별로 다르다.
  - `data/wendys/posts.json`: 959 posts
  - `data/cocacola/posts.json`: 866 posts
  - `data/moonpie/posts.json`: 932 posts
- Coca-Cola와 MoonPie는 최신 scheduled run에서 수집/분석/대시보드 동기화/commit이 끝까지 완료되었는지 반드시 GitHub Actions 로그로 확인해야 한다.

### 12.2 근본 원인으로 의심되는 workflow 구조

현재 `.github/workflows/scrape.yml`은 schedule 실행 시 matrix로 세 브랜드를 병렬 실행한다. 그런데 각 matrix job이 다음 작업을 모두 수행한다.

1. 해당 브랜드 scrape
2. 해당 브랜드 analysis
3. 전체 `export_research_outputs.py`
4. 전체 `sync_dashboard_data.py`
5. commit/push

이 구조는 위험하다.

- 세 matrix job이 같은 `main` 브랜치에 동시에 push한다.
- 각 job은 자기 workspace에서 시작하므로 다른 브랜드 job의 최신 결과를 모를 수 있다.
- `data/analysis/*`와 `dashboard/data/analysis/*`는 전체 브랜드 통합 산출물이므로 병렬 job마다 서로 다른 상태로 재생성될 수 있다.
- push/rebase retry가 있어도 통합 산출물 충돌 또는 overwrite 가능성이 남는다.
- 결과적으로 Wendy's만 반영되고 Coca-Cola/MoonPie가 실패하거나 누락되는 상황이 발생할 수 있다.

### 12.3 Gemini가 구현해야 할 권장 수정 구조

Gemini는 schedule workflow를 다음 구조로 바꾸는 것을 우선 검토해야 한다.

#### 권장 구조 A: matrix scrape + 단일 aggregate analysis/push

1. `scrape` job
   - matrix로 `Wendys`, `CocaCola`, `MoonPie`를 병렬 scrape한다.
   - 각 job은 자기 브랜드의 `data/<brand>/posts.json`과 `scrape_state.json`만 만든다.
   - matrix job에서는 전체 analysis/export/sync/commit/push를 하지 않는다.
   - 각 브랜드 결과를 GitHub Actions artifact로 업로드한다.

2. `aggregate-analysis` job
   - `needs: scrape`
   - 모든 브랜드 artifact를 다운로드한다.
   - artifact를 `data/wendys/`, `data/cocacola/`, `data/moonpie/`에 배치한다.
   - 세 브랜드에 대해 analysis를 순차적으로 실행한다.

```bash
TARGET_USER=Wendys python analyze_posts.py --task all
TARGET_USER=CocaCola python analyze_posts.py --task all
TARGET_USER=MoonPie python analyze_posts.py --task all
python export_research_outputs.py
python sync_dashboard_data.py
```

3. `aggregate-analysis` job에서만 commit/push한다.
   - 이 job이 유일한 writer가 되어야 한다.
   - commit message는 예: `Update scraped and analyzed X data for all brands`
   - push 전 `git fetch origin main` 및 rebase/retry를 유지한다.

이 구조의 장점:

- scrape는 브랜드별 병렬 처리 가능하다.
- analysis/export/sync/push는 단일 job에서 수행되어 통합 산출물 충돌을 막는다.
- Coca-Cola/MoonPie 실패 여부를 artifact 단계에서 명확히 확인할 수 있다.
- dashboard는 항상 세 브랜드가 같은 기준으로 동기화된다.

#### 허용 가능한 대안 B: 브랜드별 scrape workflow와 별도 aggregate workflow

만약 artifact 구조가 복잡하면 다음도 가능하다.

- 브랜드별 scrape workflow는 `data/<brand>/`만 commit한다.
- 별도 workflow가 모든 브랜드 scrape 완료 후 수동 또는 schedule로 실행되어 analysis/export/sync를 한 번만 수행한다.
- 단, 이 경우에도 `data/analysis/*`와 `dashboard/data/analysis/*`는 단일 job에서만 생성/commit해야 한다.

### 12.4 반드시 피해야 할 수정

- matrix job 각각에서 `export_research_outputs.py`를 계속 실행하지 말 것.
- matrix job 각각에서 `sync_dashboard_data.py`를 계속 실행하지 말 것.
- matrix job 각각이 `data/analysis/*`를 commit하게 두지 말 것.
- matrix job 각각이 같은 `dashboard/data/analysis/*`를 병렬로 commit하게 두지 말 것.
- push retry 횟수만 늘리는 방식으로 해결하지 말 것. 구조를 바꿔야 한다.
- Coca-Cola/MoonPie만 수동 재실행하고 문제 해결로 간주하지 말 것.

### 12.5 Gemini가 확인해야 할 GitHub Actions 로그

Gemini는 수정 전후 다음을 반드시 확인해야 한다.

1. scheduled run에서 matrix 대상이 세 개인지 확인한다.
2. `CocaCola` job의 실패 step을 확인한다.
3. `MoonPie` job의 실패 step을 확인한다.
4. 실패 원인이 scrape인지 analysis인지 push/rebase인지 구분한다.
5. 각 브랜드 artifact 또는 output에 post count가 기록되는지 확인한다.
6. 최종 aggregate job에서 세 브랜드 post count가 모두 표시되는지 확인한다.
7. 최종 commit에 `data/wendys`, `data/cocacola`, `data/moonpie`, `data/analysis`, `dashboard/data` 변경이 함께 반영되는지 확인한다.

### 12.6 자동화 수정 Acceptance Criteria

Gemini가 workflow를 수정한 뒤 다음 기준을 만족해야 한다.

- schedule 실행 시 세 브랜드가 모두 처리된다.
- scrape 단계는 병렬로 실행되어도 된다.
- analysis/export/sync/push는 단일 job에서 한 번만 실행된다.
- 최종 commit은 세 브랜드 결과와 통합 분석 결과를 함께 포함한다.
- `data/analysis/joined_posts.json`에 `wendys`, `cocacola`, `moonpie` 세 브랜드가 모두 포함된다.
- `dashboard/data/wendys/posts.json`, `dashboard/data/cocacola/posts.json`, `dashboard/data/moonpie/posts.json`이 모두 최신 상태다.
- `dashboard/data/analysis/*`가 최종 aggregate 결과 기준으로 갱신된다.
- GitHub Actions summary 또는 log에 브랜드별 post count가 출력된다.
- push 충돌로 실패하지 않는다.
- 실패 시 어느 브랜드가 어느 step에서 실패했는지 error annotation으로 확인 가능하다.

### 12.7 workflow 수정 후 권장 검증 명령

로컬에서 가능한 검증:

```bash
python -m py_compile scrape_x.py analyze_posts.py export_research_outputs.py sync_dashboard_data.py
TARGET_USER=Wendys python analyze_posts.py --task all
TARGET_USER=CocaCola python analyze_posts.py --task all
TARGET_USER=MoonPie python analyze_posts.py --task all
python export_research_outputs.py
python sync_dashboard_data.py
node --check dashboard/app.js
node --check dashboard/research-review.js
```

GitHub Actions에서 필요한 검증:

- workflow_dispatch로 각 브랜드 scrape가 artifact를 생성하는지 확인한다.
- schedule 또는 manual full run으로 aggregate job이 세 브랜드를 모두 분석하고 단일 commit을 push하는지 확인한다.
- 실패한 경우 로그를 보고 `scrape`, `analysis`, `export`, `sync`, `push` 중 어느 단계인지 분리해서 수정한다.

## 13. 다음 작업을 시작하기 전 체크리스트

1. `git status --short`로 dirty 상태 확인.
2. 사용자의 최신 요청이 “로컬만 수정”인지 “push까지”인지 확인.
3. 관련 파일을 먼저 읽고 기존 패턴을 따른다.
4. 작업 범위 외 refactor는 하지 않는다.
5. 검증 명령을 실행한다.
6. 결과를 commit/push하고 커밋 해시를 보고한다.
