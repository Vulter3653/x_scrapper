# Results Section Structure for Paper Writing

본 문서는 X Brand Communication 연구의 Results section을 구성하기 위한 논문 작성용 구조를 제시한다. 본 구조는 Dashboard UI 평가가 아니라, 논문 내 empirical results를 체계적으로 제시하기 위한 Table/Figure/Text 배치 기준이다.

## 1. Recommended Results Flow

Results section은 다음 순서로 구성하는 것이 적절하다.

```text
4. Results
  4.1 Descriptive Statistics
  4.2 Brand-level Distribution of Humor Type and Sentiment
  4.3 Humor Type 2×2 Matrix
  4.4 Humor × Sentiment × Engagement Patterns
  4.5 Engagement Robustness by Humor Type
  4.6 Brand-level Interpretation
  4.7 Classification Reliability and Sampling Audit
```

이 순서는 단순 descriptive results에서 시작하여, humor classification의 이론적 구조, engagement pattern, robustness, reliability check로 확장되는 흐름이다.

## 2. Section 4.1 Descriptive Statistics

### Purpose

분석 dataset의 기본 구조를 제시한다.

### Suggested Table

**Table 1. Descriptive Statistics by Brand**

| Brand | Number of Posts | Period | Average Engagement | Median Engagement | Positive Share | Negative Share |
|---|---:|---|---:|---:|---:|---:|
| Wendy's |  |  |  |  |  |  |
| Coca-Cola |  |  |  |  |  |  |
| MoonPie |  |  |  |  |  |  |
| Total |  |  |  |  |  |  |

### Suggested Text

```text
Table 1 reports descriptive statistics for the post-level dataset. The unit of analysis is an individual X/Twitter post. Engagement is operationalized as the sum of likes, replies, retweets, and quotes. The table provides the number of observations, observation period, average and median engagement, and the distribution of Sentiment Labels by brand.
```

## 3. Section 4.2 Brand-level Distribution of Humor Type and Sentiment

### Purpose

Brand별 Humor Type과 Sentiment가 어떻게 다르게 나타나는지 제시한다.

### Suggested Table

**Table 2. Distribution of Humor Type by Brand**

| Brand | Affiliative Humor | Self-enhancing Humor | Aggressive Humor | Self-defeating Humor | Unknown |
|---|---:|---:|---:|---:|---:|
| Wendy's |  |  |  |  |  |
| Coca-Cola |  |  |  |  |  |
| MoonPie |  |  |  |  |  |

**Table 3. Distribution of Sentiment by Brand**

| Brand | Positive | Neutral | Negative | Unknown |
|---|---:|---:|---:|---:|
| Wendy's |  |  |  |  |
| Coca-Cola |  |  |  |  |
| MoonPie |  |  |  |  |

### Suggested Text

```text
Tables 2 and 3 show brand-level differences in Humor Type and Sentiment Label distributions. These descriptive results indicate whether each brand relies more heavily on relationship-oriented humor, self-oriented humor, aggressive humor, or self-deprecating humor, and whether the emotional tone of the posts differs across brands.
```

## 4. Section 4.3 Humor Type 2×2 Matrix

### Purpose

HSQ framework를 기반으로 Humor Type을 이론적 2×2 구조로 제시한다.

### Conceptual Mapping

**Figure 1. HSQ Humor Type 2×2 Matrix**

|  | Self-focused | Other-focused |
|---|---|---|
| Adaptive / Positive | Self-enhancing Humor | Affiliative Humor |
| Maladaptive / Negative | Self-defeating Humor | Aggressive Humor |

### Suggested Text

```text
Figure 1 maps the four HSQ Humor Types into a 2×2 conceptual structure. The horizontal axis distinguishes whether humor is self-focused or other-focused, while the vertical axis distinguishes whether the humor is adaptive/positive or maladaptive/negative. This structure provides the theoretical basis for interpreting brand humor strategies.
```

## 5. Section 4.4 Humor × Sentiment × Engagement Patterns

### Purpose

Humor Type이 Sentiment와 결합될 때 Engagement가 어떻게 달라지는지 제시한다.

### Suggested Table

**Table 4. Humor × Sentiment × Engagement Summary**

| Humor Type | Sentiment | Number of Posts | Share | Average Engagement | Median Engagement | Average Humor Score | Average Sentiment Score |
|---|---|---:|---:|---:|---:|---:|---:|
| Affiliative Humor | Positive |  |  |  |  |  |  |
| Affiliative Humor | Neutral |  |  |  |  |  |  |
| Affiliative Humor | Negative |  |  |  |  |  |  |
| Aggressive Humor | Positive |  |  |  |  |  |  |
| Aggressive Humor | Neutral |  |  |  |  |  |  |
| Aggressive Humor | Negative |  |  |  |  |  |  |

### Suggested Text

```text
Table 4 examines the joint distribution of Humor Type and Sentiment Label and reports engagement outcomes for each combination. This analysis allows us to assess whether certain types of humor are associated with higher engagement only when combined with particular emotional tones. For example, Aggressive Humor combined with Negative Sentiment may indicate more controversial or provocative brand communication, whereas Affiliative Humor combined with Positive Sentiment may reflect relationship-oriented communication.
```

## 6. Section 4.5 Engagement Robustness by Humor Type

### Purpose

Humor Type별 Engagement 결과가 평균에 의해 왜곡되는지, 또는 분포 전반에서 안정적인 차이가 있는지 검토한다.

### Suggested Table

**Table 5. Engagement Robustness by Humor Type**

| Humor Type | Number of Posts | Share | Average Engagement | Median Engagement | 75th Percentile | 90th Percentile | Maximum Engagement | Average Humor Score |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Affiliative Humor |  |  |  |  |  |  |  |  |
| Self-enhancing Humor |  |  |  |  |  |  |  |  |
| Aggressive Humor |  |  |  |  |  |  |  |  |
| Self-defeating Humor |  |  |  |  |  |  |  |  |

### Suggested Text

```text
Table 5 reports additional distributional engagement metrics by Humor Type. Because social media engagement is often highly skewed, average engagement alone may be driven by a small number of viral posts. Therefore, we report median engagement, the 75th percentile, the 90th percentile, and maximum engagement. This allows us to assess whether a Humor Type is associated with consistently higher engagement or merely with occasional extreme reactions.
```

## 7. Section 4.6 Brand-level Interpretation

### Purpose

Brand별 communication pattern을 논문 문체로 해석한다.

### Suggested Subsections

```text
4.6.1 Wendy's
4.6.2 Coca-Cola
4.6.3 MoonPie
```

각 Brand subsection은 다음 순서로 작성한다.

1. Dominant Humor Type
2. Dominant Sentiment
3. Humor × Sentiment pattern
4. Engagement pattern
5. Classification reliability caution
6. Representative examples if needed

### Suggested Text Structure

```text
[Brand] shows a relatively high share of [Dominant Humor Type], suggesting that its brand communication strategy is characterized by [interpretation]. The engagement pattern further indicates that [Humor Type] is associated with [higher/lower/more skewed] engagement compared with other humor categories. In particular, the combination of [Humor Type] and [Sentiment Label] appears to be an important pattern in explaining audience response.
```

한국어 논문 문체 예시는 다음과 같다.

```text
[Brand]의 게시물에서는 [Dominant Humor Type]이 상대적으로 높은 비중을 차지하였다. 이는 해당 Brand의 communication strategy가 [관계 형성형 / 자기표현형 / 도발적 / 자기비하적] humor style에 기반하고 있음을 시사한다. Engagement 지표를 함께 고려할 때, [Humor Type]은 다른 유형에 비해 [더 높은 / 더 낮은 / 더 편향된] 반응을 보였다. 특히 [Humor Type]과 [Sentiment Label]의 결합은 audience response를 설명하는 중요한 패턴으로 해석될 수 있다.
```

## 8. Section 4.7 Classification Reliability and Sampling Audit

### Purpose

Zero-shot Classification 결과의 신뢰성과 한계를 제시한다.

### Suggested Table

**Table 6. Sampling Audit Results**

| Audit Category | Sample Size | Agreement Rate | Ambiguity Share | Notes |
|---|---:|---:|---:|---|
| Humor Type |  |  |  |  |
| Sentiment |  |  |  |  |
| Low-confidence cases |  |  |  |  |

### Suggested Text

```text
To assess the reliability of the model-based classification, we conducted a Sampling Audit. The audit was designed to evaluate whether the zero-shot Humor Type and Sentiment Labels were substantively consistent with human interpretation. We used stratified sampling by Humor Type and Sentiment Label and oversampled low-confidence cases. The results provide a reliability check for the classification-based analysis and help identify ambiguous or context-dependent posts.
```

## 9. Figure and Table Placement Recommendation

| Order | Output | Placement |
|---:|---|---|
| 1 | Table 1. Descriptive Statistics by Brand | Section 4.1 |
| 2 | Table 2. Distribution of Humor Type by Brand | Section 4.2 |
| 3 | Table 3. Distribution of Sentiment by Brand | Section 4.2 |
| 4 | Figure 1. HSQ Humor Type 2×2 Matrix | Section 4.3 |
| 5 | Table 4. Humor × Sentiment × Engagement Summary | Section 4.4 |
| 6 | Table 5. Engagement Robustness by Humor Type | Section 4.5 |
| 7 | Table 6. Sampling Audit Results | Section 4.7 |

## 10. Writing Caution

논문에서는 Dashboard를 직접 평가 대상으로 제시하지 않는다. Dashboard는 분석 결과를 확인하고 Table/Figure를 생성하는 보조 도구로 간주한다. 따라서 Results section에서는 Dashboard UI가 아니라, post-level data와 classification outputs에 기반한 empirical pattern을 중심으로 서술한다.
