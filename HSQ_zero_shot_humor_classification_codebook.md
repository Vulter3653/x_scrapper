# HSQ 기반 네 가지 유머 유형 Zero-shot Classification Codebook

## 1. 작업 목적

본 문서는 AI agent가 별도의 PDF 파일이나 논문 원문을 제공받지 않아도, 입력된 유머 텍스트를 네 가지 유머 유형으로 zero-shot 분류할 수 있도록 설계한 self-contained codebook이다.

분류 범주는 다음 네 가지로 고정한다.

1. **Affiliative humor**
2. **Self-enhancing humor**
3. **Aggressive humor**
4. **Self-defeating humor**

본 코드북은 Humor Styles Questionnaire, HSQ에서 제시된 네 가지 유머 스타일 개념을 텍스트 분류 기준으로 변환한 것이다.  
즉, 원문 문항을 그대로 복제하는 방식이 아니라, 각 문항군이 측정하는 핵심 개념을 바탕으로 분류 규칙을 구성한다.

---

## 2. AI Agent Role Instruction

너는 유머 텍스트를 네 가지 유머 유형으로 분류하는 연구 보조 AI agent이다.

너는 외부 PDF 파일, 논문 원문, 척도 원문을 참조하지 않는다.  
너는 아래 코드북에 제시된 개념 정의, 판단 기준, 배제 기준, 의사결정 규칙만을 사용하여 입력 텍스트를 분류한다.

분류 대상은 단문, 소셜미디어 게시글, 댓글, 광고 문구, 브랜드 간 대화, 소비자 반응, 인터뷰 발화, 설문 응답 등 모든 형태의 텍스트일 수 있다.

최종 라벨은 반드시 다음 네 가지 중 하나만 선택한다.

```text
Affiliative humor
Self-enhancing humor
Aggressive humor
Self-defeating humor
```

---

## 3. Theoretical Classification Axes

유머 유형은 두 가지 축으로 판단한다.

### 3.1 방향성: 유머가 누구를 향하는가?

- **Other / Relationship-oriented**: 타인, 집단, 관계, 사회적 상호작용을 향함
- **Self-oriented**: 자기 자신, 자신의 감정, 자신의 상황을 향함

### 3.2 기능: 유머가 어떤 효과를 만드는가?

- **Benign / Adaptive**: 관계 형성, 긴장 완화, 감정 조절, 스트레스 대처
- **Harmful / Maladaptive**: 타인 조롱, 비하, 공격, 자기비하, 자기희생, 회피

### 3.3 2 x 2 분류 구조

| 방향성 | 기능 | 분류 라벨 |
|---|---|---|
| 타인 / 관계 지향 | 긍정적·적응적 | **Affiliative humor** |
| 자기 지향 | 긍정적·적응적 | **Self-enhancing humor** |
| 타인 / 관계 지향 | 부정적·손상적 | **Aggressive humor** |
| 자기 지향 | 부정적·손상적 | **Self-defeating humor** |

---

## 4. Label Definitions and Coding Rules

## 4.1 Affiliative Humor

### Definition

Affiliative humor는 타인을 즐겁게 하거나, 관계를 원활하게 만들거나, 사회적 긴장을 완화하기 위해 사용되는 유머이다.  
핵심 기능은 **관계 형성, 분위기 완화, 친밀감 형성, 사회적 상호작용 촉진**이다.

### Inclusion Criteria

다음 조건이 강하게 나타나면 Affiliative humor로 분류한다.

- 타인을 웃게 하거나 즐겁게 하려는 목적이 중심이다.
- 대화나 집단 분위기를 부드럽게 만든다.
- 사회적 긴장이나 어색함을 완화한다.
- 친밀감, 유대감, 관계 형성을 강화한다.
- 특정 개인이나 집단을 공격하거나 비하하지 않는다.
- 자기농담이 있더라도 과도한 자기비하가 아니라 가벼운 분위기 조성 수준이다.
- 유머의 주된 효과가 사람들 사이의 긍정적 상호작용이다.

### Exclusion Criteria

다음 경우에는 Affiliative humor로 분류하지 않는다.

- 타인의 약점, 실수, 외모, 능력, 집단 정체성을 조롱하면 **Aggressive humor**로 분류한다.
- 자기 자신을 과도하게 낮추어 타인의 인정이나 웃음을 얻으려 하면 **Self-defeating humor**로 분류한다.
- 어려운 상황에서 자기 자신을 북돋는 감정 조절이 중심이면 **Self-enhancing humor**로 분류한다.

### Typical Cues

```text
분위기를 풀다
다 같이 웃다
어색함을 줄이다
친구들과 농담하다
사람들을 즐겁게 하다
가볍게 웃어넘기다
관계를 부드럽게 만들다
```

---

## 4.2 Self-enhancing Humor

### Definition

Self-enhancing humor는 스트레스, 실패, 우울, 불쾌한 상황 속에서도 자기 자신이 유머러스한 관점을 유지하여 감정을 조절하는 유머이다.  
핵심 기능은 **자기 감정 조절, 스트레스 대처, 부정적 상황의 재해석, 심리적 회복**이다.

### Inclusion Criteria

다음 조건이 강하게 나타나면 Self-enhancing humor로 분류한다.

- 화자가 자신의 어려운 상황을 유머러스하게 재해석한다.
- 우울, 스트레스, 실패, 좌절, 불안 상황에서 스스로를 북돋기 위해 유머를 사용한다.
- 타인을 웃기는 것보다 자기 자신의 기분 회복이나 감정 조절이 중심이다.
- 문제 상황의 부조리함, 우스운 면, 아이러니를 발견한다.
- 자기 자신을 완전히 깎아내리기보다, 상황을 견디기 위한 유머를 사용한다.
- 고통스러운 상황을 현실적으로 인식하되, 유머를 통해 심리적 거리를 확보한다.

### Exclusion Criteria

다음 경우에는 Self-enhancing humor로 분류하지 않는다.

- 자기비하가 지나치고 타인의 웃음이나 승인을 얻기 위한 목적이면 **Self-defeating humor**로 분류한다.
- 타인을 조롱하거나 비난하여 자신의 우월감을 표현하면 **Aggressive humor**로 분류한다.
- 주된 목적이 타인과의 관계 형성이나 집단 분위기 완화이면 **Affiliative humor**로 분류한다.

### Typical Cues

```text
힘들지만 웃어넘기다
스트레스를 농담으로 다루다
상황의 웃긴 면을 찾다
우울할 때 스스로를 웃게 만들다
이 상황도 나중엔 웃긴 이야기가 될 것이다
내 인생이 시트콤 같다
```

---

## 4.3 Aggressive Humor

### Definition

Aggressive humor는 타인을 조롱, 비하, 풍자, 놀림, 멸시, 공격하는 유머이다.  
겉으로는 농담처럼 보이더라도, 특정 개인이나 집단을 낮추거나 상처를 줄 가능성이 크면 Aggressive humor로 분류한다.

### Inclusion Criteria

다음 조건이 강하게 나타나면 Aggressive humor로 분류한다.

- 타인의 실수, 약점, 외모, 능력, 지위, 행동을 웃음거리로 만든다.
- 조롱, 비꼼, 비하, 멸시, 놀림, 풍자, sarcasm이 포함된다.
- 상대방이 불쾌감, 수치심, 모욕감을 느낄 가능성이 있다.
- 유머를 통해 타인을 비판, 압박, 배제, 조작, 지배하려는 성격이 있다.
- 웃음의 핵심이 관계 형성이 아니라 타인 깎아내리기이다.
- 특정 집단에 대한 성차별적, 인종차별적, 계층적, 직업적, 외모 기반 비하가 포함된다.
- 브랜드 간 대화에서 경쟁 브랜드를 조롱하거나 깎아내린다.
- 소비자, 고객, 경쟁자, 특정 집단을 웃음거리로 만든다.

### Exclusion Criteria

다음 경우에는 Aggressive humor로 분류하지 않는다.

- 특정 대상에 대한 비하 없이 사람들을 즐겁게 하고 분위기를 부드럽게 만들면 **Affiliative humor**로 분류한다.
- 자기 자신을 대상으로 한 과도한 비하이면 **Self-defeating humor**로 분류한다.
- 부정적 상황을 자기 감정 조절 목적으로 재해석하면 **Self-enhancing humor**로 분류한다.

### Typical Cues

```text
비꼬다
조롱하다
놀리다
깎아내리다
무시하다
한심하다
멍청하다
수준이 낮다
저 사람은 답이 없다
경쟁 브랜드를 우스꽝스럽게 만들다
상대방의 실수를 웃음거리로 만들다
```

---

## 4.4 Self-defeating Humor

### Definition

Self-defeating humor는 타인의 웃음, 호감, 승인, 수용을 얻기 위해 자기 자신을 과도하게 낮추는 유머이다.  
핵심 기능은 **자기비하, 자기희생, 승인 추구, 부정적 감정의 은폐**이다.

### Inclusion Criteria

다음 조건이 강하게 나타나면 Self-defeating humor로 분류한다.

- 화자가 자신을 과도하게 낮추거나 조롱의 대상으로 만든다.
- 자신의 약점, 실패, 결함, 무능함을 과장하여 웃음을 유도한다.
- 타인의 인정, 호감, 수용을 얻기 위해 자신을 희생하는 방식의 유머를 사용한다.
- 타인이 자신을 놀리거나 웃음거리로 삼는 것을 받아들인다.
- 실제 문제, 불행, 불안, 우울을 농담으로 덮어 감춘다.
- 자기비하가 단순한 겸손이나 가벼운 농담을 넘어 반복적이고 과도하다.
- 유머의 결과가 자기존중의 유지보다 타인의 웃음 확보에 가깝다.

### Exclusion Criteria

다음 경우에는 Self-defeating humor로 분류하지 않는다.

- 어려운 상황을 건강하게 재해석하고 자기 감정을 조절하는 정도라면 **Self-enhancing humor**로 분류한다.
- 가벼운 자기농담으로 분위기를 부드럽게 만드는 정도라면 **Affiliative humor**로 분류한다.
- 타인을 깎아내리는 방식이면 **Aggressive humor**로 분류한다.

### Typical Cues

```text
나는 그냥 웃음거리다
나 같은 사람은 답이 없다
내가 늘 그렇지 뭐
나는 쓸모없지만 웃기긴 하다
나를 놀려도 괜찮다
내 실패담으로 사람들이 웃으면 됐다
나를 깎아내려서 분위기를 살리다
```

---

## 5. Decision Procedure

AI agent는 입력 텍스트를 읽고 다음 순서대로 판단한다.

### Step 1. Identify the target of humor

유머의 주요 대상이 누구인지 판단한다.

```text
self
other_individual
group
brand
competitor
customer
situation
unclear
```

### Step 2. Identify the function of humor

유머의 주요 기능을 판단한다.

```text
relationship_building
tension_reduction
emotion_regulation
coping
disparagement
ridicule
criticism
self_deprecation
approval_seeking
avoidance
unclear
```

### Step 3. Assess harm potential

유머가 누군가에게 손상을 줄 가능성이 있는지 판단한다.

```text
low
medium
high
```

### Step 4. Apply label rule

다음 규칙에 따라 최종 라벨을 선택한다.

```text
타인을 즐겁게 하고 관계를 강화하면 Affiliative humor
자기 감정을 조절하고 스트레스에 대처하면 Self-enhancing humor
타인을 조롱하거나 비하하면 Aggressive humor
자기 자신을 과도하게 깎아내리면 Self-defeating humor
```

---

## 6. Priority Rules for Ambiguous Cases

애매한 경우에는 다음 우선순위를 적용한다.

1. 타인을 웃기더라도 특정 대상을 깎아내리면 **Aggressive humor**를 우선한다.
2. 자기 자신을 웃음 소재로 삼지만 감정 조절이 목적이면 **Self-enhancing humor**를 우선한다.
3. 자기 자신을 웃음 소재로 삼지만 타인의 인정이나 웃음을 얻기 위한 과도한 자기비하이면 **Self-defeating humor**를 우선한다.
4. 상황 자체를 가볍게 농담화하여 집단 분위기를 완화하면 **Affiliative humor**를 우선한다.
5. 브랜드 간 조롱, 경쟁 브랜드 비하, 소비자 조롱, 특정 집단 조롱은 **Aggressive humor**로 분류한다.
6. 가벼운 자기농담이 관계 형성 목적이면 **Affiliative humor**로 볼 수 있으나, 자기비하의 강도가 높으면 **Self-defeating humor**를 우선한다.
7. 유머가 명시적으로 보이지 않거나 문맥이 부족하면 가장 가까운 라벨을 선택하되 confidence를 낮게 부여한다.

---

## 7. Output Format

AI agent는 반드시 아래 JSON 형식으로만 출력한다.

```json
{
  "text_id": "",
  "label": "",
  "confidence": 0.0,
  "secondary_label": "",
  "target_of_humor": "",
  "humor_function": "",
  "harm_potential": "",
  "reason": "",
  "key_cues": []
}
```

### Field Rules

| Field | Description |
|---|---|
| `text_id` | 입력 텍스트의 ID |
| `label` | 네 가지 유머 유형 중 하나 |
| `confidence` | 0.00에서 1.00 사이의 확신도 |
| `secondary_label` | 애매한 경우 두 번째 가능성. 없으면 `"none"` |
| `target_of_humor` | `self`, `other_individual`, `group`, `brand`, `competitor`, `customer`, `situation`, `unclear` 중 하나 |
| `humor_function` | `relationship_building`, `tension_reduction`, `emotion_regulation`, `coping`, `disparagement`, `ridicule`, `criticism`, `self_deprecation`, `approval_seeking`, `avoidance`, `unclear` 중 하나 |
| `harm_potential` | `low`, `medium`, `high` 중 하나 |
| `reason` | 분류 근거를 2-3문장으로 설명 |
| `key_cues` | 판단에 사용한 핵심 표현 또는 단서 |

---

## 8. Batch Classification Input Format

복수 텍스트를 분류할 경우 다음 형식으로 입력한다.

```json
[
  {
    "text_id": "text_001",
    "text": "분류할 텍스트"
  },
  {
    "text_id": "text_002",
    "text": "분류할 텍스트"
  }
]
```

복수 텍스트에 대한 출력은 다음 형식으로 제공한다.

```json
[
  {
    "text_id": "text_001",
    "label": "",
    "confidence": 0.0,
    "secondary_label": "",
    "target_of_humor": "",
    "humor_function": "",
    "harm_potential": "",
    "reason": "",
    "key_cues": []
  },
  {
    "text_id": "text_002",
    "label": "",
    "confidence": 0.0,
    "secondary_label": "",
    "target_of_humor": "",
    "humor_function": "",
    "harm_potential": "",
    "reason": "",
    "key_cues": []
  }
]
```

---

## 9. Example Classifications

### Example 1: Affiliative Humor

#### Input

```json
{
  "text_id": "example_001",
  "text": "회의 분위기가 너무 무거워서 가벼운 농담을 했더니 다들 웃으면서 긴장이 풀렸다."
}
```

#### Output

```json
{
  "text_id": "example_001",
  "label": "Affiliative humor",
  "confidence": 0.91,
  "secondary_label": "none",
  "target_of_humor": "situation",
  "humor_function": "tension_reduction",
  "harm_potential": "low",
  "reason": "이 텍스트는 무거운 회의 분위기를 완화하고 사람들 사이의 긴장을 낮추기 위해 유머를 사용한 사례이다. 특정 대상을 공격하거나 자기 자신을 과도하게 낮추지 않으므로 Affiliative humor로 분류한다.",
  "key_cues": ["회의 분위기가 너무 무거워서", "다들 웃으면서", "긴장이 풀렸다"]
}
```

---

### Example 2: Self-enhancing Humor

#### Input

```json
{
  "text_id": "example_002",
  "text": "요즘 일이 너무 힘들지만, 이 정도면 내 인생도 시트콤 한 시즌쯤은 찍은 것 같다고 생각하니 조금 웃겼다."
}
```

#### Output

```json
{
  "text_id": "example_002",
  "label": "Self-enhancing humor",
  "confidence": 0.88,
  "secondary_label": "none",
  "target_of_humor": "situation",
  "humor_function": "coping",
  "harm_potential": "low",
  "reason": "화자는 힘든 상황을 유머러스하게 재해석하여 자신의 감정을 완화하고 있다. 타인을 웃기거나 자기 자신을 과도하게 낮추는 것이 아니라 스트레스 대처가 중심이므로 Self-enhancing humor로 분류한다.",
  "key_cues": ["일이 너무 힘들지만", "시트콤 한 시즌", "조금 웃겼다"]
}
```

---

### Example 3: Aggressive Humor

#### Input

```json
{
  "text_id": "example_003",
  "text": "그 사람 발표는 너무 엉망이라서 발표자료보다 마이크가 더 열심히 일한 것 같았다."
}
```

#### Output

```json
{
  "text_id": "example_003",
  "label": "Aggressive humor",
  "confidence": 0.86,
  "secondary_label": "Affiliative humor",
  "target_of_humor": "other_individual",
  "humor_function": "disparagement",
  "harm_potential": "high",
  "reason": "이 텍스트는 특정 사람의 발표 능력을 조롱하고 비하하는 방식으로 웃음을 유도한다. 유머의 핵심 대상이 타인의 부족함이므로 Aggressive humor로 분류한다.",
  "key_cues": ["발표는 너무 엉망", "마이크가 더 열심히 일한 것"]
}
```

---

### Example 4: Self-defeating Humor

#### Input

```json
{
  "text_id": "example_004",
  "text": "나는 그냥 조별과제에서 인간 장식품 역할이라도 잘해야지. 다들 나 때문에 웃으면 그걸로 됐다."
}
```

#### Output

```json
{
  "text_id": "example_004",
  "label": "Self-defeating humor",
  "confidence": 0.89,
  "secondary_label": "Self-enhancing humor",
  "target_of_humor": "self",
  "humor_function": "self_deprecation",
  "harm_potential": "high",
  "reason": "화자는 타인의 웃음이나 수용을 얻기 위해 자신을 과도하게 낮추고 있다. 자기비하가 중심이며 자기존중보다는 자기희생적 유머에 가깝기 때문에 Self-defeating humor로 분류한다.",
  "key_cues": ["인간 장식품", "나 때문에 웃으면 그걸로 됐다"]
}
```

---

## 10. Minimal Prompt for Direct Agent Use

아래 프롬프트는 실제 AI agent의 system prompt 또는 classification prompt에 그대로 삽입할 수 있다.

```text
You are a research assistant AI agent that classifies humorous text into one of four humor styles: Affiliative humor, Self-enhancing humor, Aggressive humor, and Self-defeating humor.

Use only the following codebook.

Affiliative humor refers to humor used to amuse others, facilitate relationships, reduce social tension, and create a friendly interpersonal atmosphere. It is other-oriented and benign.

Self-enhancing humor refers to humor used to maintain a humorous perspective on one's own life, regulate negative emotion, and cope with stress or adversity. It is self-oriented and benign.

Aggressive humor refers to humor that ridicules, mocks, criticizes, teases, disparages, humiliates, or puts down another person, group, brand, customer, or competitor. It is other-oriented and potentially harmful.

Self-defeating humor refers to humor that excessively puts oneself down, makes oneself the butt of the joke, seeks approval through self-ridicule, or hides negative feelings through joking. It is self-oriented and potentially harmful.

Decision rules:
- If the humor builds relationships or reduces social tension without harming a target, classify it as Affiliative humor.
- If the humor helps the speaker cope with stress or reinterpret their own situation, classify it as Self-enhancing humor.
- If the humor mocks, criticizes, or disparages another person, group, brand, customer, or competitor, classify it as Aggressive humor.
- If the humor excessively ridicules the speaker themself to gain approval or hide negative feelings, classify it as Self-defeating humor.
- If a text both makes people laugh and disparages a target, prioritize Aggressive humor.
- If a text uses self-directed humor, distinguish healthy coping from excessive self-ridicule. Healthy coping is Self-enhancing humor; excessive self-ridicule is Self-defeating humor.

Return only JSON in this format:
{
  "text_id": "",
  "label": "",
  "confidence": 0.0,
  "secondary_label": "",
  "target_of_humor": "",
  "humor_function": "",
  "harm_potential": "",
  "reason": "",
  "key_cues": []
}
```

---

## 11. Methodological Description for Research Report

논문 또는 보고서의 방법론 파트에는 다음과 같이 작성할 수 있다.

> 본 연구는 Humor Styles Questionnaire에서 제시된 네 가지 유머 스타일 개념을 텍스트 분류 코드북으로 변환한 뒤, 이를 기준으로 AI agent 기반 zero-shot classification을 수행하였다. 분류 범주는 affiliative humor, self-enhancing humor, aggressive humor, self-defeating humor로 구성하였다. AI agent는 각 텍스트에 대해 유머의 대상, 기능, 손상 가능성을 순차적으로 판단한 후 하나의 최종 라벨을 부여하였다. 또한 분류 신뢰도, 보조 라벨, 핵심 단서, 판단 근거를 함께 출력하도록 설계하였다.

---

## 12. Notes for Reliability Check

zero-shot classification 결과를 연구 데이터로 사용할 경우, 다음 검증 절차를 권장한다.

1. 전체 데이터 중 일부 표본을 무작위 추출한다.
2. 인간 코더 2인 이상이 동일한 코드북을 사용하여 독립 코딩한다.
3. AI agent의 분류 결과와 인간 코더의 분류 결과를 비교한다.
4. Cohen's kappa 또는 Krippendorff's alpha를 사용하여 일치도를 확인한다.
5. 일치도가 낮은 유형은 코드북의 배제 기준과 우선순위 규칙을 수정한다.
6. 최종 코드북을 고정한 뒤 전체 데이터에 재분류를 수행한다.

---

## 13. Important Limitation

이 분류 방식은 원척도 문항을 응답자에게 제시하여 개인의 성향을 측정하는 방식이 아니다.  
따라서 본 방법은 **개인의 humor style trait 측정**이 아니라, **텍스트 단위의 humor style classification**으로 해석해야 한다.

즉, 한 사용자의 특정 게시글이 Aggressive humor로 분류되었다고 해서, 해당 사용자가 전반적으로 aggressive humor 성향을 가진다고 단정할 수 없다.  
텍스트 단위 분류 결과를 개인 수준 특성으로 해석하려면 다수의 텍스트 관측치와 추가적인 검증이 필요하다.
