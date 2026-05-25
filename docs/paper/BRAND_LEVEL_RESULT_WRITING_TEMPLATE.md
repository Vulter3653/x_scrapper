# Brand-level Result Writing Template

본 문서는 Wendy's, Coca-Cola, MoonPie의 X Brand Communication 분석 결과를 논문 Results 및 Discussion section에 서술하기 위한 Brand-level writing template이다. 본 문서는 AI Agent 평가와 관련되지 않으며, 논문 작성에서 Brand-specific findings를 체계적으로 서술하기 위한 목적을 가진다.

## 1. Brand-level Result Writing Logic

각 Brand 결과 서술은 다음 논리 순서로 작성한다.

```text
1. Brand-level data overview
2. Dominant Humor Type
3. Dominant Sentiment
4. Humor × Sentiment pattern
5. Engagement pattern
6. Robustness interpretation
7. Classification reliability caution
8. Theoretical and managerial implication
```

이 구조는 단순히 어느 Brand가 더 높은 Engagement를 얻었는지를 보여주는 것이 아니라, Brand Communication Strategy가 어떤 Humor Type과 Sentiment 조합을 통해 구성되는지 설명하는 데 초점을 둔다.

## 2. Common Writing Template

아래 문단 구조는 모든 Brand에 공통적으로 적용할 수 있다.

```text
[Brand]의 X post를 분석한 결과, 해당 Brand는 [Dominant Humor Type]을 상대적으로 많이 활용하는 것으로 나타났다. 이는 [Brand]의 Brand Communication이 [relationship-building / self-enhancing / provocative / self-deprecating] humor style에 기반하고 있음을 시사한다. Sentiment Label의 분포를 함께 살펴보면, [Dominant Sentiment]가 가장 높은 비중을 차지하였으며, 이는 해당 Brand의 communication tone이 전반적으로 [positive / neutral / negative] 방향성을 가진다는 점을 보여준다.

Humor × Sentiment 조합을 분석한 결과, [Most Frequent Combination]이 가장 빈번하게 관찰되었다. Engagement 측면에서는 [Highest Engagement Combination]의 Median Engagement가 가장 높게 나타났다. 이는 동일한 Humor Type이라도 어떤 Sentiment Label과 결합되는지에 따라 audience response가 달라질 수 있음을 시사한다.

Engagement Robustness 결과를 보면, [Humor Type]은 Average Engagement뿐만 아니라 Median Engagement, 75th Percentile, 90th Percentile에서도 [consistent / skewed / unstable] pattern을 보였다. 따라서 해당 Humor Type의 성과는 [전반적으로 안정적인 반응 / 일부 viral post에 의존한 반응]으로 해석할 수 있다.

다만 Zero-shot Classification에 기반한 결과이므로, Low-confidence cases와 ambiguous posts에 대해서는 Sampling Audit을 통한 보완적 검토가 필요하다.
```

## 3. Wendy's Writing Template

Wendy's는 일반적으로 social media에서 witty, confrontational, and playful brand voice로 알려져 있으므로, 분석 결과에서 Aggressive Humor 또는 teasing-based communication이 높게 나타나는지 확인하는 것이 중요하다.

### 3.1 Result Paragraph Template

```text
Wendy's의 X post를 분석한 결과, [Dominant Humor Type]이 가장 높은 비중을 차지하였다. 특히 Aggressive Humor가 높은 비중을 보이는 경우, 이는 Wendy's의 Brand Communication이 타 브랜드 또는 소비자와의 상호작용에서 teasing, ridicule, playful confrontation을 활용하는 전략과 연결될 수 있다. 이러한 Humor Type은 단순한 정보 전달보다 attention generation과 audience engagement를 유도하는 방식으로 기능할 가능성이 있다.

Sentiment 측면에서는 [Dominant Sentiment]가 가장 많이 나타났으며, Aggressive Humor와 Negative Sentiment가 결합된 posts는 [N]개로 전체의 [X%]를 차지하였다. 이 조합은 Wendy's의 communication style이 playful aggression과 critical tone을 결합하는 방식으로 구성될 수 있음을 보여준다.

Engagement 결과를 보면, [Highest Engagement Humor Type]의 Median Engagement가 가장 높게 나타났다. 만약 Aggressive Humor의 Median Engagement 또는 90th Percentile Engagement가 높게 나타난다면, 이는 Wendy's의 provocative humor strategy가 audience response를 유도하는 데 효과적일 수 있음을 시사한다. 반대로 Aggressive Humor의 평균은 높지만 Median Engagement가 낮다면, 해당 효과는 일부 viral posts에 의해 주도되었을 가능성이 있다.
```

### 3.2 Discussion Sentence

```text
These findings suggest that Wendy's may benefit from a distinctive and provocative brand voice, but the interpretation should be tempered by the possibility that Aggressive Humor may generate both engagement and controversy.
```

한국어 논문 문체:

```text
이러한 결과는 Wendy's가 차별적이고 도발적인 Brand Voice를 통해 audience attention을 확보할 가능성을 보여준다. 그러나 Aggressive Humor는 높은 Engagement와 동시에 논쟁적 반응을 유발할 수 있으므로, 해당 결과는 Sentiment pattern 및 Low-confidence cases와 함께 신중하게 해석될 필요가 있다.
```

## 4. Coca-Cola Writing Template

Coca-Cola는 일반적으로 positive emotion, happiness, togetherness, and global brand identity와 연결되는 Brand이다. 따라서 Affiliative Humor 또는 Positive Sentiment가 높게 나타나는지 확인하는 것이 중요하다.

### 4.1 Result Paragraph Template

```text
Coca-Cola의 X post를 분석한 결과, [Dominant Humor Type]이 가장 높은 비중을 차지하였다. 만약 Affiliative Humor가 두드러진다면, 이는 Coca-Cola의 Brand Communication이 shared amusement, social bonding, and positive association을 중심으로 구성된다는 점을 시사한다. 이러한 humor style은 브랜드가 소비자와 정서적 유대감을 형성하는 데 활용될 수 있다.

Sentiment Label의 분포에서는 [Dominant Sentiment]가 가장 높은 비중을 차지하였다. Positive Sentiment가 높은 경우, 이는 Coca-Cola의 communication tone이 happiness, celebration, and emotional warmth를 강조하는 방향으로 구성되어 있음을 보여준다.

Humor × Sentiment 분석에서 Affiliative Humor × Positive Sentiment 조합이 높은 비중을 차지한다면, 이는 Coca-Cola가 humor를 통해 긍정적 관계 형성과 brand warmth를 동시에 강화하고 있음을 의미한다. Engagement Robustness 결과에서 해당 조합의 Median Engagement가 높게 나타난다면, 이러한 관계 지향적 communication style이 audience response에도 긍정적으로 연결될 가능성이 있다.
```

### 4.2 Discussion Sentence

```text
These findings would be consistent with the interpretation that Coca-Cola relies on emotionally positive and relationship-oriented brand communication rather than confrontational humor.
```

한국어 논문 문체:

```text
이러한 결과는 Coca-Cola가 confrontational humor보다는 emotionally positive하고 relationship-oriented한 Brand Communication에 의존한다는 해석과 일치한다. 특히 Affiliative Humor와 Positive Sentiment가 결합된 posts가 높은 Engagement를 보인다면, 이는 브랜드의 warmth-oriented communication strategy가 audience response와 연결될 수 있음을 시사한다.
```

## 5. MoonPie Writing Template

MoonPie는 absurd, self-aware, and playful brand voice를 활용하는 Brand로 해석될 수 있다. 따라서 Self-enhancing Humor, Self-defeating Humor, 또는 unusual playful tone이 어떻게 나타나는지 확인하는 것이 중요하다.

### 5.1 Result Paragraph Template

```text
MoonPie의 X post를 분석한 결과, [Dominant Humor Type]이 가장 높은 비중을 차지하였다. Self-enhancing Humor가 높게 나타나는 경우, 이는 MoonPie가 자기표현적이고 긍정적인 brand self-image를 humorous tone으로 강화하고 있음을 의미할 수 있다. 반면 Self-defeating Humor가 높게 나타난다면, 이는 브랜드가 self-deprecation과 self-aware humor를 통해 소비자와 친근한 관계를 형성하려는 전략으로 해석될 수 있다.

Sentiment 분석에서는 [Dominant Sentiment]가 가장 많이 나타났으며, Humor × Sentiment 조합에서는 [Most Frequent Combination]이 두드러졌다. MoonPie의 경우, 단순한 positive or negative tone보다 absurdity, irony, and self-referential humor가 중요한 역할을 할 수 있으므로, Low-confidence 또는 ambiguous cases의 비중을 함께 고려할 필요가 있다.

Engagement Robustness 결과에서 [Humor Type]의 90th Percentile Engagement가 높게 나타난다면, 이는 MoonPie의 humor strategy가 평균적인 반응보다는 특정 posts의 viral response를 통해 성과를 보일 수 있음을 시사한다.
```

### 5.2 Discussion Sentence

```text
These findings may indicate that MoonPie uses humor less as direct persuasion and more as a form of brand personality performance, where absurdity and self-awareness become central to audience engagement.
```

한국어 논문 문체:

```text
이러한 결과는 MoonPie의 Humor Strategy가 직접적 설득보다는 Brand Personality Performance의 형태로 작동할 수 있음을 시사한다. 특히 absurdity와 self-awareness가 결합된 humor style은 소비자에게 독특한 Brand Voice를 인식시키고, 특정 posts에서 높은 Engagement를 유도할 가능성이 있다.
```

## 6. Cross-brand Comparative Writing

세 Brand를 비교하는 문단은 다음 구조로 작성한다.

```text
Across the three brands, the distribution of Humor Type and Sentiment suggests distinct brand communication strategies. Wendy's appears to rely more heavily on [Humor Type], Coca-Cola on [Humor Type], and MoonPie on [Humor Type]. These differences indicate that brand humor on social media is not uniform but reflects brand-specific voice, audience expectations, and communication positioning.

The Humor × Sentiment × Engagement analysis further suggests that engagement outcomes depend not only on Humor Type but also on the emotional tone with which humor is delivered. For example, [Brand A] shows higher engagement when [Humor Type] is paired with [Sentiment], whereas [Brand B] shows stronger engagement for [Different Combination].
```

한국어 논문 문체:

```text
세 Brand를 비교한 결과, Humor Type과 Sentiment Label의 분포는 각 Brand가 서로 다른 Brand Communication Strategy를 활용하고 있음을 보여준다. Wendy's는 [Humor Type], Coca-Cola는 [Humor Type], MoonPie는 [Humor Type]을 상대적으로 많이 활용하는 경향을 보였다. 이는 social media에서의 brand humor가 동일한 방식으로 작동하는 것이 아니라, 각 Brand의 voice, audience expectation, communication positioning에 따라 다르게 구성될 수 있음을 시사한다.

또한 Humor × Sentiment × Engagement 분석은 audience response가 Humor Type만으로 결정되는 것이 아니라, 해당 humor가 어떤 Sentiment tone과 결합되는지에 따라 달라질 수 있음을 보여준다. 예를 들어 [Brand A]는 [Humor Type]이 [Sentiment]와 결합될 때 더 높은 Engagement를 보인 반면, [Brand B]는 [Different Combination]에서 더 강한 반응을 보였다.
```

## 7. Cautionary Language

논문에서는 자동 분류 결과를 과도하게 단정하지 않도록 다음 표현을 사용한다.

| Avoid | Prefer |
|---|---|
| This proves that... | This suggests that... |
| Consumers felt... | The post was classified as... |
| The brand intended... | The communication pattern is consistent with... |
| Aggressive Humor caused engagement | Aggressive Humor is associated with higher engagement |
| The model accurately identified... | The model-based classification indicates... |

## 8. Recommended Placement

| Paper Section | Use |
|---|---|
| Results | Brand-specific empirical patterns |
| Discussion | Interpretation of Brand Communication Strategy |
| Managerial Implications | How brands may use Humor Type and Sentiment strategically |
| Limitations | Model-based classification and context-dependence caution |

## 9. Final Writing Principle

Brand-level result writing should not describe the Dashboard itself. It should describe empirical patterns observed in the post-level dataset. Dashboard outputs should be translated into paper-facing Tables, Figures, and academic interpretation.
