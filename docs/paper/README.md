# Paper Writing Documents

본 폴더는 `x_scrapper` 프로젝트의 분석 결과를 논문 작성에 활용하기 위한 문서 세트이다. 이 문서들은 AI Agent evaluation을 위한 것이 아니라, X Brand Communication 연구의 Method, Results, Robustness, Discussion section을 작성하기 위한 자료이다.

## 1. Folder Purpose

`docs/paper/`의 목적은 다음과 같다.

- Dashboard에서 확인한 분석 결과를 논문용 Table/Figure/Text 구조로 전환한다.
- Zero-shot Classification 결과를 논문 Method와 Robustness section에서 설명할 수 있도록 정리한다.
- Brand-level findings를 학술적 문체로 서술하기 위한 template을 제공한다.
- 논문 작성 시 사용해야 하는 핵심 분석 키워드를 정리한다.

## 2. Document List

| Document | Purpose | Paper Section |
|---|---|---|
| `PAPER_WRITING_SCOPE.md` | 논문 작성 범위와 제외 범위 정의 | Overall framing |
| `SAMPLING_AUDIT_PROTOCOL.md` | Zero-shot Classification reliability 검토 절차 | Method, Robustness |
| `RESULTS_SECTION_STRUCTURE.md` | Results section Table/Figure/Text 구성 | Results |
| `BRAND_LEVEL_RESULT_WRITING_TEMPLATE.md` | Brand-specific results 서술 템플릿 | Results, Discussion |

## 3. Recommended Paper Structure

논문 전체 구조는 다음과 같이 구성할 수 있다.

```text
Abstract
1. Introduction
2. Literature Review
  2.1 Brand Communication on Social Media
  2.2 Humor in Marketing Communication
  2.3 HSQ Humor Type
  2.4 Sentiment and Consumer Response
3. Method
  3.1 Data Collection
  3.2 Measures
  3.3 Humor Type Classification
  3.4 Sentiment Classification
  3.5 Sampling Audit Protocol
4. Results
  4.1 Descriptive Statistics
  4.2 Brand-level Distribution of Humor Type and Sentiment
  4.3 Humor Type 2×2 Matrix
  4.4 Humor × Sentiment × Engagement Patterns
  4.5 Engagement Robustness by Humor Type
  4.6 Brand-level Interpretation
  4.7 Classification Reliability and Sampling Audit
5. Discussion
  5.1 Theoretical Implications
  5.2 Managerial Implications
  5.3 Limitations and Future Research
6. Conclusion
```

## 4. Core English Keywords

논문에서는 주요 분석 키워드를 English term으로 유지하는 것이 적절하다.

| English Keyword | Korean Explanation |
|---|---|
| Brand Communication | 브랜드의 social media communication 방식 |
| Humor Type | HSQ framework 기반 humor classification category |
| Affiliative Humor | 관계 형성 또는 social bonding을 위한 humor |
| Self-enhancing Humor | 긍정적 자기표현 또는 brand self-image를 강화하는 humor |
| Aggressive Humor | teasing, ridicule, attack, superiority를 포함하는 humor |
| Self-defeating Humor | self-deprecation 또는 self-mockery를 포함하는 humor |
| Sentiment | post의 정서적 tone |
| Engagement | likes, replies, retweets, quotes의 합산 지표 |
| Topic | LDA를 통해 식별한 content theme |
| Confidence Score | Zero-shot Classification의 label confidence |
| Low-confidence cases | classification score가 낮아 수동 검토가 필요한 cases |
| Sampling Audit | model-based classification 결과를 human review로 검토하는 절차 |
| Engagement Robustness | 평균값 외에 median, percentile, maximum으로 engagement pattern을 검토하는 방식 |

## 5. Writing Rules

논문 작성 시 다음 원칙을 따른다.

1. Dashboard 자체를 연구대상이나 평가대상으로 서술하지 않는다.
2. Dashboard는 post-level data와 classification outputs를 확인하는 analysis support tool로만 언급한다.
3. AI Agent evaluation, agent autonomy, tool-use performance 등은 본 논문의 결과 해석 범위에 포함하지 않는다.
4. `Humor Type`, `Sentiment`, `Engagement`, `Topic`, `Confidence Score` 등 주요 키워드는 English term으로 유지한다.
5. 결과 해석에서는 causal language를 피하고 association-based language를 사용한다.
6. Zero-shot Classification 결과는 `model-based classification` 또는 `model-generated label`로 표현한다.
7. 사람이 느낀 감정으로 단정하지 않고, post가 특정 Sentiment Label로 분류되었다고 표현한다.
8. Sampling Audit 결과가 없는 경우, classification reliability를 제한적으로만 주장한다.

## 6. Table and Figure Plan

| Output | Title | Source Document |
|---|---|---|
| Table 1 | Descriptive Statistics by Brand | `RESULTS_SECTION_STRUCTURE.md` |
| Table 2 | Distribution of Humor Type by Brand | `RESULTS_SECTION_STRUCTURE.md` |
| Table 3 | Distribution of Sentiment by Brand | `RESULTS_SECTION_STRUCTURE.md` |
| Figure 1 | HSQ Humor Type 2×2 Matrix | `RESULTS_SECTION_STRUCTURE.md` |
| Table 4 | Humor × Sentiment × Engagement Summary | `RESULTS_SECTION_STRUCTURE.md` |
| Table 5 | Engagement Robustness by Humor Type | `RESULTS_SECTION_STRUCTURE.md` |
| Table 6 | Sampling Audit Results | `SAMPLING_AUDIT_PROTOCOL.md` |

## 7. Recommended Writing Workflow

논문 작성은 다음 순서로 진행하는 것이 효율적이다.

```text
Step 1. PAPER_WRITING_SCOPE.md로 연구 범위 확정
Step 2. RESULTS_SECTION_STRUCTURE.md를 기준으로 Table/Figure 구성
Step 3. SAMPLING_AUDIT_PROTOCOL.md를 Method/Robustness section에 반영
Step 4. BRAND_LEVEL_RESULT_WRITING_TEMPLATE.md를 이용해 Brand별 Results 문단 작성
Step 5. Discussion에서 Brand Communication Strategy와 Managerial Implications 도출
Step 6. Limitations에서 Zero-shot Classification과 Sampling Audit 한계를 명시
```

## 8. Notes for Paper Writing

- Results section은 Dashboard 화면 순서가 아니라 논문 논리 순서를 따라야 한다.
- Brand-level result는 단순 수치 비교가 아니라 Brand Voice와 Communication Strategy 관점에서 해석한다.
- Engagement는 consumer response의 proxy로 사용하되, purchase intention이나 brand attitude로 직접 해석하지 않는다.
- Aggressive Humor는 높은 Engagement와 동시에 controversy 가능성을 가질 수 있으므로 Sentiment와 함께 해석한다.
- Affiliative Humor는 Positive Sentiment와 결합될 때 relationship-oriented communication으로 해석할 수 있다.
- Self-enhancing Humor와 Self-defeating Humor는 Brand Personality Performance 관점에서 해석할 수 있다.
