# Humor IV — HSQ-Based Codebook for Brand SNS Text Classification

**Reference:** Martin, R. A., Puhlik-Doris, P., Larsen, G., Gray, J., & Weir, K. (2003). Individual differences in uses of humor and their relation to psychological well-being: Development of the Humor Styles Questionnaire. *Journal of Research in Personality, 37*(1), 48–75.

**Scope:** This codebook adapts the Humor Styles Questionnaire (HSQ) four-humor-type taxonomy for ML-based classification of brand social media posts. HSQ was originally developed as a self-report individual psychology measure; the definitions below are adapted for use as a supervised text-classification target, not a psychological instrument.

---

## 1. Four Humor Type Definitions

### 1.1 Affiliative Humor

**HSQ definition (original):** Using humor to facilitate relationships, reduce tension, amuse others, and say funny things in a benign way that does not target any person or group.

**Brand SNS operational definition:** Humor that strengthens the brand's relationship with its audience through shared amusement, community building, or warm, inclusive levity. Does not mock, belittle, or demean anyone.

---

### 1.2 Self-Enhancing Humor

**HSQ definition (original):** Maintaining a humorous outlook even in the face of stress or adversity; using humor to cope with difficult situations in a self-confident way.

**Brand SNS operational definition:** Humor that reframes a difficult business situation, market challenge, operational setback, or public criticism in a light or optimistic way. The brand laughs *with* the situation rather than deflecting blame onto others.

---

### 1.3 Aggressive Humor

**HSQ definition (original):** Using humor to criticize, manipulate, or put down others (individuals, groups); includes sarcasm, teasing, ridicule, and disparagement.

**Brand SNS operational definition:** Humor that mocks, ridicules, belittles, attacks, or disparages a third party — competitors, individuals, out-groups, public figures, institutions, or trends — in order to generate amusement at their expense.

---

### 1.4 Self-Defeating Humor

**HSQ definition (original):** Excessively self-deprecating humor; allowing others to laugh at oneself; using humor to hide negative feelings; engaging in humor to seek approval even at one's own expense.

**Brand SNS operational definition:** Humor that makes the brand itself the butt of the joke in an excessive or approval-seeking way. Includes joking about the brand's own failures, weaknesses, or embarrassments beyond what genuine self-enhancing reframing would justify.

---

## 2. Brand SNS Context Adaptations

| Type | Brand SNS Signal |
|------|-----------------|
| **Affiliative** | Polls, shared jokes with fans, celebration of community milestones, warm holiday posts, relatable everyday humor |
| **Self-Enhancing** | "We struggled with X but here's our take…" framing; turning a product recall or delay into a lighthearted story; resilience-themed humor |
| **Aggressive** | Competitor comparison jokes, roasting trending topics, mocking a cultural figure, sarcastic product comparisons |
| **Self-Defeating** | "Honestly, our app was down and we deserve the complaints" style jokes; self-mockery used to solicit forgiveness or engagement |

---

## 3. Aggressive Humor Cues

Posts should be considered aggressive humor candidates if they contain **any of the following cue types**. Multiple cues increase confidence.

| Cue | Description |
|-----|-------------|
| **Sarcasm** | Saying the opposite of what is meant to mock or undercut |
| **Ridicule** | Directly making fun of a person, group, competitor, or idea |
| **Mockery** | Imitating or exaggerating another's behavior or product to highlight absurdity |
| **Derision** | Expressing contempt or scorn through humor |
| **Put-down** | A joke that demeans or diminishes the target |
| **Disparagement** | Humor that represents the target as inferior, incompetent, or ridiculous |
| **Hostile teasing** | Teasing that carries genuine contempt or seeks to embarrass |
| **Hostile comparison** | Comparing a competitor or target unfavorably in a joking register |
| **Offensive joke** | Humor that a reasonable audience would find hurtful, demeaning, or discriminatory |
| **Humor at another's expense** | Any joke structured so that a third party (not the brand's own audience) is the target |

---

## 4. Self-Defeating Humor Cues

| Cue | Description |
|-----|-------------|
| **Brand self-deprecation** | The brand explicitly mocks its own product, decision, or action |
| **Making the brand the butt** | The joke is structured so the brand looks foolish, incompetent, or helpless |
| **Joking about own weakness** | Admitting faults in a joking way beyond what self-enhancement would cover |
| **Joking about own failure** | Treating a genuine brand failure as the punchline |
| **Excessive self-mockery** | Self-deprecation that seems approval-seeking or disproportionate to the actual failure |
| **Inviting others to laugh at the brand** | Explicitly asking the audience to join in ridiculing the brand |
| **Humor used to cover a problem** | Using self-deprecating humor as deflection when a serious response would be more appropriate |

---

## 5. Boundary Rules

### 5.1 Affiliative vs. Aggressive
- Friendly teasing, inclusive joking, relationship-building humor with the brand's own audience → **affiliative**
- Ridicule, put-down, out-group attack, hostile teasing targeting a third party → **aggressive**
- Rule of thumb: *who is the target?* If the audience is in on the joke together = affiliative. If a third party is the target = aggressive.

### 5.2 Self-Enhancing vs. Self-Defeating
- Optimistic, resilient reframing of genuine difficulty → **self-enhancing**
- Excessive, approval-seeking, or disproportionate self-mockery → **self-defeating**
- Rule of thumb: Does the brand appear confident and in control of the reframing? → self-enhancing. Does the brand appear to be seeking absolution or attention through self-degradation? → self-defeating.

### 5.3 Ambiguous Cases
- Posts that could be aggressive OR self-enhancing (e.g., joking about a competitor who also challenged the brand) → code primary type; note secondary signal
- Posts with multiple cue types from different categories → code primary type as the dominant signal; record secondary label
- Posts where humor is unclear or context-dependent → label `ambiguous`; preserve for soft-label IV construction

---

## 6. Interpretation Limits and Constraints

> **These constraints are non-negotiable.**

1. **HSQ is an individual psychology instrument.** These definitions are adapted for brand SNS text classification only. HSQ subscale scores must not be computed or interpreted for brand entities.

2. **No brand personality or psychological profiling.** Classification of brand humor style is a content variable, not a brand personality or psychological assessment.

3. **v2 aggressive candidates are not ground truth.** `v2_aggressive_candidate_count` is a candidate signal requiring human validation. It should not be labeled, interpreted, or cited as a confirmed aggressive classification.

4. **No causal claims.** Classification results describe *what type of humor was posted*, not *why* or *with what effect*.

5. **No Brand Equity interpretation.** Even if aggressive humor posts are associated with abnormal returns, this must not be interpreted as evidence that humor *causes* changes in brand equity or market value.

6. **Ambiguous posts are preserved.** Ambiguous posts should NOT be dropped. They should be assigned probability-weighted scores using `ml_humor_probability × type_base_rate` for soft-label IV construction.

7. **HSQ codebook applies only to existing ML pipeline output.** The codebook does not authorize re-running, re-labeling, or modifying the raw humor classification outputs.

---

*Created: Gate 5.1 — Paper-grounded Humor IV Reconstruction Repair*
*Reference commit: d4c20be22c71185bd3bb7609d76a20acc5e060b8*
