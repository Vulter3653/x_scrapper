# Humor Analysis Plan: No Human Label Stage

## 현재 상태 요약

| 항목 | 상태 |
|------|------|
| v1 full-chain master | 68,020 rows, main에 commit됨 |
| v2 A/B test | 941 sample 기준 완료 (agreement 39.53%) |
| human review priority sample | 346 rows 생성됨 |
| human label | **없음** — 이번 단계에서 생성 불가 |
| gold label | **없음** — human adjudication 전까지 정의 불가 |

---

## 1. 현재 가능한 분석과 불가능한 분석

### 가능한 분석

| 분석 유형 | 설명 |
|-----------|------|
| Model-free evidence | v1 operational label 기반 descriptive statistics |
| Distribution audit | humor_presence, humor_type, sentiment 분포 (v1 기준) |
| Disagreement structure | v1-v2 간 transition 패턴 (어디서 충돌하는가) |
| Sensitivity summary | rare class (aggressive, self_defeating) 탐지 신호 방향성 |
| Company-level summary | 99개 회사별 v1 label 분포 |

### 불가능한 분석 (human label 전까지)

| 분석 유형 | 이유 |
|-----------|------|
| Accuracy / Precision / Recall | 정답이 없으므로 측정 불가 |
| Classifier performance comparison | v1과 v2 중 어느 쪽이 맞는지 판단 불가 |
| Gold-label evaluation | human adjudication 없이 정의 불가 |
| Cue/rule calibration | 어떤 cue가 틀렸는지 알 수 없음 |
| Production classifier decision | 정확도 검증 없이 결정 불가 |

---

## 2. v1과 v2의 역할 정의

### v1: operational baseline

- `classify_humor_presence_local.py` + `classify_humor_type_zero_shot.py` 2-stage 파이프라인
- 68,020 rows에 대한 현재 유일한 labeling 결과
- **human label이 없으므로 v1이 "정답"이라는 의미가 아니다**
- 다운스트림 분석(sentiment × humor 교차, 회사별 비교)의 operational foundation으로만 사용

### v2: disagreement detector / candidate generator

- `classify_humor_type_v2_direct.py` (rule/cue-based prototype)
- v1 결과와 비교하여 disagreement가 발생하는 구조를 파악하는 도구
- v2가 v1보다 낫다는 의미가 아니다
- v2 label이 더 정확하다는 의미가 아니다
- **human review candidate를 생성하기 위한 disagreement signal로만 해석한다**
- production classifier로 전환하지 않는다
- 전체 68k rows를 v2로 재분류하지 않는다

---

## 3. v1-v2 agreement 해석 기준

- v1-v2 agreement rate (39.53%)는 **두 분류기의 consistency indicator**다
- accuracy estimate가 아니다
- 39.53% agreement가 "60%가 틀렸다"는 의미가 아니다
- disagreement row가 어느 쪽이 맞는지는 human adjudication 전까지 알 수 없다
- v1-v2 consensus (양측이 동의한 row)를 gold label로 처리하지 않는다

---

## 4. Rare class 해석 기준

aggressive와 self_defeating에 대한 현재 수치:

| 지표 | 값 | 해석 |
|------|-----|------|
| v1 aggressive (68k) | 105 rows | v1 operational label; human 검증 없음 |
| v1 self_defeating (68k) | 41 rows | v1 operational label; human 검증 없음 |
| v2 aggressive (941 sample) | 125 rows | v2 이 샘플에서 aggressive로 분류 |
| v2 self_defeating (941 sample) | 36 rows | v2 이 샘플에서 self_defeating으로 분류 |

**이 수치들은 exploratory evidence다.** human label 전까지 다음 해석은 금지:

- "v2가 더 많은 aggressive를 잡았다" (방향성은 있지만 정확도 불명)
- "rare class가 과소탐지되었다" (비교 기준 없음)
- "v2 aggressive가 정확하다" (human 검증 없음)

허용되는 해석:

- "v2는 v1 대비 이 샘플에서 aggressive를 더 많이 탐지하는 경향을 보인다"
- "P0/P3 human review candidates에서 rare class의 실제 해당 여부를 확인해야 한다"

---

## 5. Human review 단계 (보류 중)

human review는 현재 보류 상태다. 준비된 항목:

- `data/derived/humor/evaluation/humor_type_human_review_priority_sample.csv` (346 rows)
  - P0 (21 rows): v1 ambiguous → v2 aggressive/self_defeating
  - P1 (80 rows): v1 humor → v2 not_humor
  - P2 (68 rows): v1 not_humor → v2 humor
  - P3 (17 rows): v1 affiliative/self_enhancing → v2 aggressive
  - P4 (80 rows): v1 ambiguous → v2 not_humor
  - P5 (80 rows): low v2 confidence or v2 review flag

human review 이후에만 가능해지는 작업:

1. v1 label accuracy 추정
2. v2 classifier precision/recall 계산
3. v2 cue/threshold calibration (adjustment)
4. v2→production 전환 결정
5. rare class 확정 count 보고
6. Gold label dataset 구축

---

## 6. 현재 분석 패키지 구성

`Build Humor No-Human-Label Evidence Package` workflow 실행 시 생성되는 파일:

| 파일 | 내용 |
|------|------|
| `data/derived/humor/evidence/humor_v1_model_free_overall_summary.csv` | 전체 v1 분포 통계 |
| `data/derived/humor/evidence/humor_v1_model_free_company_summary.csv` | 99개 회사별 v1 분포 |
| `data/derived/humor/evidence/humor_v1_v2_disagreement_audit.csv` | v1-v2 transition 구조 분석 |
| `data/derived/humor/evidence/humor_rare_class_sensitivity_summary.csv` | rare class 탐지 신호 요약 |
| `data/audit/humor/evidence/humor_no_human_label_evidence_manifest.json` | 실행 manifest (제약 플래그 포함) |

모든 파일에서 다음 플래그가 false로 기록된다:

```json
{
  "gold_label_created": false,
  "v1_v2_consensus_as_gold": false,
  "v2_production_converted": false,
  "full_chain_overwritten": false,
  "cue_calibration_performed": false
}
```

---

## 7. 다음 단계 순서

```
현재 위치
  ↓
[이번 단계] model-free evidence 생성 (human label 없음)
  ↓
[보류] human review (346-row priority sample 수동 라벨링)
  ↓
[보류 후 가능] gold label 구축
  ↓
[보류 후 가능] v1/v2 accuracy 평가
  ↓
[보류 후 가능] cue calibration (threshold adjustment)
  ↓
[보류 후 가능] production classifier 결정
```
