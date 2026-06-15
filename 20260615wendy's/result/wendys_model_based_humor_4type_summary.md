# Wendy's 탐색적 4-type 유머 분류 결과

## 주의

이 결과는 exploratory 4-type classification이다.
Primary 결과는 반드시 `aggressive vs other_humor` 이진 모델을 기준으로 해석해야 한다.

4-type model은 exploratory 전용. self-defeating=15건(<20건 기준 미달)이므로 primary로 사용하지 않음.

## 4-type 학습 표본

| 타입 | 건수 |
|---|---|
| affiliative | 106건 |
| aggressive | 95건 |
| self-enhancing | 62건 |
| self-defeating | 15건 |


## 검증 결과 (5-fold OOF)

- OOF accuracy: 0.4568
- OOF macro-F1: 0.3421
