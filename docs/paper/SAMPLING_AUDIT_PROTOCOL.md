# Sampling Audit Protocol for Paper Writing

본 문서는 X Brand Communication 연구에서 사용된 Zero-shot Sentiment Classification과 HSQ Humor Classification 결과의 신뢰성을 논문에서 보완하기 위한 Sampling Audit 절차를 제시한다. 본 절차는 AI Agent 평가가 아니라, 논문 내 Classification reliability를 검토하기 위한 연구방법론적 보완 장치이다.

## 1. Purpose

Zero-shot Classification은 대규모 social media post를 효율적으로 분류할 수 있다는 장점이 있지만, 개별 post의 문맥, irony, sarcasm, brand-specific tone을 완전히 반영하지 못할 수 있다. 따라서 본 연구는 classification 결과를 그대로 확정적 사실로 간주하지 않고, Sampling Audit을 통해 분류 신뢰성을 보완한다.

Sampling Audit의 목적은 다음과 같다.

- Humor Type classification의 face validity를 확인한다.
- Sentiment classification의 interpretive consistency를 확인한다.
- Low-confidence cases가 특정 brand, humor type, sentiment label에 집중되어 있는지 확인한다.
- 논문에서 classification-based result의 robustness를 설명할 수 있는 근거를 확보한다.

## 2. Audit Population

Audit population은 분석 대상 post-level dataset 전체이다. 각 observation은 하나의 X/Twitter post를 의미하며, 다음 변수를 포함한다.

| Variable | Description |
|---|---|
| `brand` | Brand account: Wendy's, Coca-Cola, MoonPie |
| `post_id` | Unique post identifier |
| `text` | Post text |
| `humor_label` | Zero-shot HSQ Humor Classification result |
| `humor_score` | Confidence Score for humor_label |
| `sentiment_label` | Zero-shot Sentiment Classification result |
| `sentiment_score` | Confidence Score for sentiment_label |
| `engagement` | Likes + replies + retweets + quotes |
| `topic_id` | LDA Topic assignment if available |

## 3. Sampling Strategy

본 연구는 단순 random sampling보다 stratified sampling을 우선한다. 이는 Humor Type과 Sentiment Label의 분포가 불균형할 가능성이 있기 때문이다.

### 3.1 Stratified Sampling by Humor Type

각 Humor Type에서 일정 수의 posts를 추출한다.

| Humor Type | Suggested Audit Sample |
|---|---:|
| Affiliative Humor | 10-20 posts |
| Self-enhancing Humor | 10-20 posts |
| Aggressive Humor | 10-20 posts |
| Self-defeating Humor | 10-20 posts |
| Unknown / unlabeled | 5-10 posts |

### 3.2 Stratified Sampling by Sentiment

각 Sentiment Label에서도 일정 수의 posts를 추출한다.

| Sentiment Label | Suggested Audit Sample |
|---|---:|
| Positive | 10-20 posts |
| Neutral | 10-20 posts |
| Negative | 10-20 posts |
| Unknown / unlabeled | 5-10 posts |

### 3.3 Low-confidence Oversampling

Classification Score가 낮은 cases는 수동 검토 우선순위가 높다. 본 연구는 다음 기준을 Low-confidence로 정의한다.

```text
humor_score < 0.50
sentiment_score < 0.50
```

Low-confidence cases는 별도로 oversampling한다. 특히 다음 조건에 해당하는 posts를 우선 검토한다.

- humor_score < 0.50
- sentiment_score < 0.50
- both humor_score and sentiment_score < 0.50
- Aggressive Humor로 분류되었으나 confidence가 낮은 cases
- Negative Sentiment로 분류되었으나 confidence가 낮은 cases

## 4. Human Coding Procedure

Sampling Audit에서 human coder는 각 sampled post를 검토하고 다음 항목을 기록한다.

| Field | Description |
|---|---|
| `human_humor_label` | Human-coded Humor Type |
| `human_sentiment_label` | Human-coded Sentiment Label |
| `agreement_humor` | Whether human_humor_label matches model humor_label |
| `agreement_sentiment` | Whether human_sentiment_label matches model sentiment_label |
| `ambiguity_flag` | Whether the post is ambiguous, sarcastic, context-dependent, or hard to classify |
| `memo` | Qualitative explanation |

## 5. Coding Guideline

### 5.1 Humor Type Coding

Human coder는 HSQ framework에 따라 다음 기준을 적용한다.

| Humor Type | Coding Criterion |
|---|---|
| Affiliative Humor | Humor intended to build connection, social bonding, or shared amusement |
| Self-enhancing Humor | Humor used to maintain a positive brand self-image or optimistic stance |
| Aggressive Humor | Humor involving teasing, ridicule, insult, superiority, or attack toward others |
| Self-defeating Humor | Humor involving self-deprecation, self-mockery, or lowering the self/brand |

### 5.2 Sentiment Coding

Sentiment coding은 post의 dominant emotional tone을 기준으로 한다.

| Sentiment | Coding Criterion |
|---|---|
| Positive | Clearly favorable, cheerful, celebratory, supportive, or appreciative tone |
| Neutral | Informational, ambiguous, or emotionally balanced tone |
| Negative | Critical, hostile, disappointed, mocking, angry, or clearly unfavorable tone |

## 6. Reliability Check

Sampling Audit 결과는 다음 방식으로 보고할 수 있다.

| Reliability Indicator | Description |
|---|---|
| Humor Agreement Rate | Share of sampled posts where model humor_label matches human_humor_label |
| Sentiment Agreement Rate | Share of sampled posts where model sentiment_label matches human_sentiment_label |
| Low-confidence Error Rate | Disagreement rate among low-confidence cases |
| Ambiguity Share | Share of posts flagged as ambiguous/context-dependent |

가능하다면 두 명 이상의 human coder가 독립적으로 coding하고, Cohen's Kappa 또는 percent agreement를 보고한다. 단일 coder만 활용하는 경우에는 `manual validation check`로 제한적으로 표현한다.

## 7. Suggested Paper Text

다음 문단은 Method 또는 Robustness Checks section에 사용할 수 있다.

```text
To assess the reliability of the model-based classification, we conducted a Sampling Audit of the zero-shot Humor Type and Sentiment labels. Because the distribution of Humor Type and Sentiment was uneven across brands, we used a stratified sampling procedure by Humor Type and Sentiment Label. We also oversampled low-confidence cases, defined as observations with either humor_score or sentiment_score below 0.50. Each sampled post was manually reviewed according to the HSQ framework and a three-category sentiment coding scheme. The audit was used to assess whether the model-generated labels were substantively consistent with human interpretation and to identify ambiguous or context-dependent cases.
```

한국어 논문 문체로는 다음과 같이 작성할 수 있다.

```text
본 연구는 model-based classification 결과의 신뢰성을 보완하기 위해 Zero-shot Humor Type 및 Sentiment Label에 대한 Sampling Audit을 수행하였다. Humor Type과 Sentiment Label의 분포가 브랜드별로 불균형할 수 있으므로, 단순 무작위 추출이 아니라 Humor Type과 Sentiment Label을 기준으로 한 층화 표본추출을 적용하였다. 또한 humor_score 또는 sentiment_score가 0.50 미만인 Low-confidence cases를 추가적으로 과대표집하여, 분류가 불확실한 사례를 우선적으로 검토하였다. 표본으로 추출된 각 post는 HSQ framework와 세 범주의 Sentiment coding 기준에 따라 수동 검토되었으며, 이를 통해 model-generated labels가 연구자의 해석과 실질적으로 일치하는지를 확인하였다.
```

## 8. Reporting Recommendation

논문에서는 Sampling Audit 결과를 다음 표로 제시하는 것이 적절하다.

| Audit Category | Sample Size | Agreement Rate | Ambiguity Share |
|---|---:|---:|---:|
| Humor Type | N | % | % |
| Sentiment | N | % | % |
| Low-confidence cases | N | % | % |

## 9. Limitation Statement

Sampling Audit을 수행하더라도 classification 결과는 여전히 model-based approximation이다. 따라서 논문에서는 다음과 같은 제한점을 명시한다.

```text
Although the Sampling Audit provides evidence of classification reliability, the Humor Type and Sentiment labels remain model-assisted classifications. Some posts may contain sarcasm, implicit humor, brand-specific references, or contextual meanings that are difficult to classify without additional conversational context. Therefore, the classification results should be interpreted as structured analytical proxies rather than definitive psychological states of consumers or brands.
```
