# Wendy's 사람 코딩 결과 점검 보고

생성일시: 2026-06-15 17:26 UTC

> 이번 작업은 사람 코딩 결과 점검만 수행하였다.
> 유머 타입 분류 모델, H2 회귀분석, t-test는 수행하지 않았다.

---

## 1. 작업 목적

H2 분석 전에 `wendys_humor_review_sheet.csv`에 들어 있는 사람 코딩 결과를 점검한다.
유머 유무 라벨 분포, 유머 타입 값 품질, 코더 간 불일치를 진단하여
H2 진행 가능 여부를 판단한다.

---

## 2. 입력 파일

```text
20260615wendy's/result/wendys_humor_review_sheet.csv
```

| 항목 | 값 |
|------|-----|
| 전체 행 수 | 978건 |
| 컬럼 수 | 23개 |
| 누락 컬럼 | 없음 |

---

## 3. 유머 유무 라벨 분포

| 출처 | 유효 | 유머 | 비유머 | 결측 | 유머 비율 |
|------|------|------|--------|------|---------|
| coder1 | 250 | 173 | 77 | 728 | 69.2% |
| human | 167 | 83 | 84 | 811 | 49.7% |
| coder2 | 404 | 136 | 268 | 574 | 33.7% |
| final | 597 | 309 | 288 | 381 | 51.8% |


---

## 4. final_humor_source별 기여

`final_humor_binary`는 coder1 > human > coder2 우선순위 규칙으로 구성되었다.

| 출처 | 건수 | 유머 | 비유머 | 비율 |
|---|---|---|---|---|
| coder1 | 250 | 173 | 77 | 41.9% |
| coder2 | 248 | 90 | 158 | 41.5% |
| human | 99 | 46 | 53 | 16.6% |


---

## 5. 유머 타입 값 분포

### coder1_type

| 값 | 건수 | 비율 |
|---|---|---|
| `none` | 76 | 30.4% |
| `affiliative` | 74 | 29.6% |
| `aggressive` | 51 | 20.4% |
| `self-enhancing` | 38 | 15.2% |
| `self-defeating` | 9 | 3.6% |
| `self-enchancing` ⚠️ | 2 | 0.8% |


### human_type

| 값 | 건수 | 비율 |
|---|---|---|
| `none` | 30 | 44.1% |
| `affiliative` | 21 | 30.9% |
| `aggressive` | 13 | 19.1% |
| `self-enhancing` | 3 | 4.4% |
| `self-defeating` | 1 | 1.5% |


### coder2_type

| 값 | 건수 | 비율 |
|---|---|---|
| `none` | 326 | 70.6% |
| `aggressive` | 58 | 12.6% |
| `affiliative` | 29 | 6.3% |
| `self-enhancing` | 21 | 4.5% |
| `affliative` ⚠️ | 19 | 4.1% |
| `self-defeating` | 6 | 1.3% |
| `self_enhancing` ⚠️ | 2 | 0.4% |
| `self-affliative` ⚠️ | 1 | 0.2% |


---

## 6. type 값 정규화 필요성

정규화 필요 여부: **필요**

발견된 오타/이상값:

  - `coder1`: `self-enchancing` → `self-enhancing` (2건)
  - `coder2`: `affliative` → `affiliative` (19건)
  - `coder2`: `self_enhancing` → `self-enhancing` (2건)
  - `coder2`: `self-affliative` → `affiliative` (1건)

알 수 없는 값: 없음

정규화 제안:

| 원본값 | 제안 정규화값 | 출처 | 건수 |
|--------|------------|------|------|
| `self-enchancing` | `self-enhancing` | coder1 | 2 |
| `affliative` | `affiliative` | coder2 | 19 |
| `self_enhancing` | `self-enhancing` | coder2 | 2 |
| `self-affliative` | `affiliative` | coder2 | 1 |


---

## 7. 코더 간 불일치 점검

| 비교 | 겹침 | 일치 | 불일치 | 일치율 |
|---|---|---|---|---|
| coder1 vs human (binary) | 68 | 68 | 0 | 100.0% |
| coder1 vs coder2 (binary) | 83 | 28 | 55 | 33.7% |
| human vs coder2 (binary) | 73 | 42 | 31 | 57.5% |
| coder1 vs human (type) | 38 | 38 | 0 | 100.0% |
| coder1 vs coder2 (type) | 17 | 5 | 12 | 29.4% |
| human vs coder2 (type) | 0 | 0 | 0 | 0.0% |


---

## 8. H2 수행 가능성 판단

### final_humor_type 후보 진단 (실제 컬럼 미생성, 진단 전용)

`final_humor_source` 기준으로 type 값을 가져왔을 때의 분포:

| 유머 타입 | 후보 건수 |
|----------|---------|
| aggressive | 90건 |
| affiliative | 100건 |
| self-enhancing | 59건 |
| self-defeating | 14건 |
| type 없음/none | 46건 |
| 합계 (유머 전체) | 309건 |

- 유머 행 중 type 유효 비율: 263/309 = 85.1%
- 비유머인데 type이 유머 타입으로 들어간 경우: 1건

### H2 판단 기준

```text
aggressive >= 30건: H2 단순 t-test 및 OLS 가능
aggressive 15~29건: H2 탐색적으로만 가능
aggressive < 15건: H2 회귀분석 보류 권장
```

**현재 aggressive 후보: 90건**

### 결론

## **H2 수행 가능**

이유: aggressive 후보가 30건 이상이므로 type 정규화 후 H2 단순 t-test 및 OLS 진행 가능.

단, type 정규화 완료 전까지는 H2 분석을 진행하지 않는다.

---

## 9. 다음 단계

1. **type 정규화 수행**
   - 오타 수정: 4건
   - `affliative` → `affiliative`, `self-enchancing` → `self-enhancing` 등
   - `none`, 공란 → 처리 규칙 결정 필요

2. **final_humor_type 컬럼 생성**
   - `final_humor_source` 기준으로 해당 코더의 type 값 적용
   - 정규화 후 적용

3. **H2 분석 진행** (type 정규화 완료 후)
   - aggressive vs 기타 유머 타입 engagement 비교
   - 표본 크기 재확인 후 진행
