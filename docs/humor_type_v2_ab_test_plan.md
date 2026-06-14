# Humor Type v2 A/B Test Plan

> **Classifier type notice**: v2 direct classifier is a rule/cue-based prototype for A/B evaluation, not a production LLM classifier. `classify_humor_type_v2_direct.py` implements this codebook as a local lexical scoring function. It does not call any external API or model; all decisions are made from keyword/phrase match scores. This is intentional for rapid, cost-free evaluation before committing to an LLM-based replacement.

## 1. 왜 v2가 필요한가

현재 full-chain classification 결과(68,020 rows, 99 companies, run 27500086401)의 주요 문제:

| 지표 | 현재 값 | 목표 |
|------|---------|------|
| ambiguous_or_review | ~48% (32,749 rows) | <20% |
| aggressive | 0.15% (105 rows) | 1–3% |
| self_defeating | 0.06% (41 rows) | 0.5–2% |
| affiliative/self_enhancing 구분 정확도 | 불명확 | 검증 필요 |

세 가지 근본 원인:
1. **presence gate에서 넘어온 ambiguous rows**: 기존 2-stage 파이프라인에서 presence=ambiguous인 행은 humor type 단계에 진입하지 않고 ambiguous_or_review로 처리됨. 이 행들이 전체의 48%를 차지.
2. **aggressive/self_defeating 탐지 cue 부족**: v1 cue 사전은 개인 SNS 패턴(roast, clown, oops 등)에 치중. Fortune 500 브랜드의 미묘한 경쟁적 어조나 자기비하 패턴을 포착하지 못함.
3. **URL-dominant 텍스트 과분류**: 링크가 포함된 정상 프로모션 포스트가 humor 판정을 받은 뒤 적합한 type cue가 없어 affiliative에 할당됨.

---

## 2. 기존 2-stage pipeline vs v2 direct classifier

### 기존 pipeline (v1)

```
Input CSV
  → [Stage 1] classify_humor_presence_local.py (TF-IDF + rule cues)
      → presence: humor / non_humor / ambiguous
  → [Stage 2] classify_humor_type_zero_shot.py (local HSQ cues)
      → humor_type: affiliative / self_enhancing / aggressive / self_defeating
      → non_humor → not_applicable
      → ambiguous → ambiguous_or_review (DEFERRED, not classified)
  → merge_humor_full_chain_outputs.py
      → humor_full_chain_master.csv
```

**한계**: ambiguous인 행은 Stage 2에서 강제 분류되지 않음 → ambiguous_or_review 누적.

### v2 direct classifier

```
Input CSV (전체 포스트, presence gate 없음)
  → [Single stage] classify_humor_type_v2_direct.py
      → v2_humor_label: affiliative / self_enhancing / aggressive /
                         self_defeating / not_humor / ambiguous_review
      (ambiguous_review는 진짜 판단 불가 케이스만 해당)
```

**차이점**:
- presence gate 없이 전체 포스트에 직접 5-class 분류 적용
- not_humor를 명시적 class로 포함해 비유머 포스트를 강제 분류
- aggressive/self_defeating cue를 브랜드 X 포스트 특성에 맞게 확장
- 동점 시에만 ambiguous_review 배정 (임계값 기반 forced-choice)

---

## 3. 전면 교체가 아니라 A/B test로 시작하는 이유

v2는 local rule-based 분류기이므로:
- 실제 정확도 검증 없이 교체하면 오분류 패턴이 달라질 뿐 개선 보장이 없음
- v1 결과가 이미 66k 행에 대해 존재하며 downstream 분석이 이 결과에 의존
- A/B test를 통해 v1과 v2의 실제 disagreement 패턴을 확인한 뒤 전면 교체 여부 결정

A/B test 목표:
1. ambiguous_or_review 중 v2가 확정 label을 부여하는 비율
2. aggressive/self_defeating 탐지 증가 여부 (질적 확인 필요)
3. v1 humor row 중 v2가 not_humor로 재분류하는 비율 (precision 지표)
4. 회사별 label 분포 변화 이상 여부

---

## 4. 평가 지표

| 지표 | 계산 방법 | 기준 (통과 임계값) |
|------|-----------|------------------|
| Ambiguous 해소율 | (resolved_to_humor + resolved_to_not_humor) / total_ambiguous | >50% |
| v2 ambiguous_review 비율 | ambiguous_review count / total sample | <15% |
| Aggressive 증가 | v2_aggressive - v1_aggressive | >0 (방향성) |
| Self-defeating 증가 | v2_self_defeating - v1_self_defeating | >0 (방향성) |
| humor→not_humor 재분류율 | humor_to_not_humor / v1_humor | <20% (과도한 역분류 방지) |
| 전체 agreement율 | agree_count / total | 참고용 (기준 없음) |

---

## 5. 신규 파일 목록

| 파일 | 역할 |
|------|------|
| `config/humor_type_codebook_v2.json` | v2 라벨 정의, 판단 기준, boundary case |
| `scripts/classify_humor_type_v2_direct.py` | v2 직접 5-class 분류기 |
| `scripts/build_humor_type_ab_test_sample.py` | stratified sample 생성 |
| `scripts/compare_humor_type_v1_v2.py` | v1 vs v2 비교 리포트 |
| `.github/workflows/run-humor-type-v2-ab-test.yml` | GitHub Actions 워크플로우 |
| `docs/humor_type_v2_ab_test_plan.md` | 이 문서 |

---

## 6. 다음 실행 방법

### 사전 조건
- `Run Humor Full Chain Classification` 워크플로우가 완료되어 `data/derived/humor/full_chain/humor_full_chain_master.csv`가 존재해야 함

### Step 1: A/B test 실행
GitHub Actions → **Run Humor Type v2 A/B Test** 워크플로우 수동 실행

권장 입력값:
| 파라미터 | 값 |
|----------|----|
| `sample_size_mode` | `default_stratified` |
| `random_seed` | `42` |
| `master_path` | `data/derived/humor/full_chain/humor_full_chain_master.csv` |
| `commit_results` | `true` |

### Step 2: 결과 확인
- `data/audit/humor/evaluation/humor_type_v1_v2_summary.json` — 집계 지표
- `data/audit/humor/evaluation/humor_type_v1_v2_comparison.csv` — 행별 비교 (v1/v2 label, transition_type)
- `data/audit/humor/evaluation/humor_type_ab_test_sample_manifest.json` — 샘플 구성 확인

### Step 3: 전면 교체 결정 기준
평가 지표 기준을 충족하고, aggressive/self_defeating 증가 사례를 수동으로 확인한 뒤:
- v2를 전면 교체: `classify_humor_type_v2_direct.py`를 기존 full-chain workflow에 통합
- 추가 튜닝 후 재평가: cue 사전 수정 → 재실행
- v1 유지: 결과 차이가 유의미하지 않거나 오분류가 증가한 경우

### 주의사항
- 이 workflow는 sample A/B test 전용. full_all_posts 재분류가 아님.
- v2 직접 분류기는 로컬 rule-based 방식이며 Gemini API를 사용하지 않음.
- 기존 `data/derived/humor/full_chain/humor_full_chain_master.csv`는 수정하지 않음.
