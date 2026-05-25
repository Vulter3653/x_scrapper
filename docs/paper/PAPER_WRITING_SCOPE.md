# Paper Writing Scope

본 문서는 `x_scrapper` 프로젝트에서 생성된 수집·분석 결과를 논문 작성에 활용하기 위한 범위를 정의한다. 본 작업은 AI Agent 평가와 직접 관련된 작업이 아니며, 논문 작성에서 필요한 연구방법, 결과 제시, 강건성 검토, 브랜드별 해석을 체계화하는 데 한정한다.

## 1. Scope

본 문서 세트의 목적은 다음과 같다.

- X Brand Communication 데이터를 논문 결과 섹션에 사용할 수 있도록 정리한다.
- HSQ Humor Classification, Zero-shot Sentiment, LDA Topic, Engagement 결과를 논문용 분석 근거로 구조화한다.
- Sampling Audit을 통해 Zero-shot Classification 결과의 신뢰성을 검토할 수 있는 절차를 제시한다.
- Brand-level Results를 논문 문체로 작성할 수 있는 서술 틀을 제공한다.
- Dashboard에서 확인되는 결과를 그대로 평가 지표로 해석하지 않고, 논문 결과 해석의 보조 근거로 사용한다.

## 2. Out of Scope

다음 항목은 본 작업의 범위에서 제외한다.

- AI Agent 성능 평가
- Agent Architecture 비교
- LLM benchmark 평가
- Tool-use accuracy 평가
- Agent autonomy 평가
- Demo performance 평가
- Dashboard 자체의 사용성 평가

즉, 본 문서 세트는 `AI Agent evaluation`이 아니라 `marketing communication paper writing`에만 초점을 둔다.

## 3. Paper-facing Analysis Units

논문 작성에서 사용할 주요 분석 단위는 다음과 같다.

| Unit | Definition | Paper Use |
|---|---|---|
| Brand | Wendy's, Coca-Cola, MoonPie | Brand-level comparative analysis |
| Post | X/Twitter post-level observation | Unit of analysis |
| Humor Type | HSQ-based humor classification | Main explanatory content category |
| Sentiment | Zero-shot sentiment label | Emotional tone indicator |
| Engagement | Likes, replies, retweets, quotes combined | Outcome-oriented descriptive metric |
| Topic | LDA topic assignment | Content theme control or descriptive grouping |
| Confidence Score | Zero-shot classification confidence | Audit and robustness criterion |

## 4. Recommended Paper Section Placement

| Paper Section | Related Output |
|---|---|
| Method | Data collection, classification procedure, Sampling Audit protocol |
| Measures | Humor Type, Sentiment, Engagement, Topic, Confidence Score |
| Descriptive Results | Brand-level post volume, Humor Type distribution, Sentiment distribution |
| Main Results | Humor × Sentiment × Engagement patterns |
| Robustness / Reliability | Sampling Audit, Low-confidence Review, Engagement Robustness |
| Discussion | Brand communication interpretation and managerial implications |
| Limitations | Zero-shot classification limitation, platform data limitation, external validity |

## 5. Writing Principle

논문 작성에서는 다음 원칙을 따른다.

- 주요 분석 키워드는 English term으로 유지한다.
- 설명 문장은 학문적 한국어 문체로 작성한다.
- Dashboard 결과는 시각적 보조 자료로 사용하되, 논문에서는 Table과 Text 중심으로 제시한다.
- Zero-shot Classification 결과는 확정적 사실이 아니라 model-based classification으로 표현한다.
- Sampling Audit을 통해 Classification reliability를 보완한다.
