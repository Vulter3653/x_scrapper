# Classifier Performance Improvement Summary

생성일: 2026-06-19

## 비교 버전 및 Training Label 규모

| 버전 | template | total_rows | valid_binary_n | type_n | 주요 추가 |
|:---|:---|---:|---:|---:|:---|
| v1 | combined (원본) | 2,498 | 2,480 | 1,027 | batch1 + batch2 (coder1/2) |
| v2 | combined_v2 (Wendy's) | 3,095 | 3,077 | 1,305 | Wendy's 597건 추가 |
| v3 | v3 (coder3 batch2) | 3,595 | 3,574 | 1,410 | coder3 batch2 497건 추가 |

---

## Presence Classifier 성능 (5-fold CV)

| 지표 | v1 | v2 | v3 | v1→v2 | v2→v3 | v1→v3 |
|:---|---:|---:|---:|---:|---:|---:|
| valid_binary_n | 2,480 | 3,077 | 3,574 | +597 | +497 | +1094 |
| AUC | 0.8008 | 0.7769 | 0.777 | -0.0239 | +0.0001 | -0.0238 |
| F1 | 0.6874 | 0.6857 | 0.659 | -0.0017 | -0.0267 | -0.0284 |
| Accuracy | 0.7347 | 0.714 | 0.7082 | -0.0207 | -0.0058 | -0.0265 |
| Precision | 0.6713 | 0.6559 | 0.6236 | -0.0154 | -0.0323 | -0.0477 |
| Recall | 0.705 | 0.7186 | 0.6995 | +0.0136 | -0.0191 | -0.0055 |

### Confusion Matrix (전 fold 누적)

**v1:**
| | pred Non | pred Humor |
|:---|---:|---:|
| **actual Non** | 1098 | 355 |
| **actual Humor** | 303 | 724 |

**v2:**
| | pred Non | pred Humor |
|:---|---:|---:|
| **actual Non** | 1237 | 504 |
| **actual Humor** | 376 | 960 |

**v3:**
| | pred Non | pred Humor |
|:---|---:|---:|
| **actual Non** | 1523 | 610 |
| **actual Humor** | 433 | 1008 |

---

## Type Classifier 성능 (stratified k-fold CV)

| 지표 | v1 | v2 | v3 | v1→v2 | v2→v3 | v1→v3 |
|:---|---:|---:|---:|---:|---:|---:|
| type_n | 1,027 | 1,305 | 1,410 | +278 | +105 | +383 |
| macro_F1 | 0.3729 | 0.3749 | 0.3738 | +0.0020 | -0.0011 | +0.0009 |
| weighted_F1 | 0.5319 | 0.5074 | 0.519 | -0.0245 | +0.0116 | -0.0129 |
| overall_acc | 0.5404 | 0.5111 | 0.5213 | -0.0293 | +0.0102 | -0.0191 |

### Confusion Matrix (type, v3)

| | pred_agg | pred_aff | pred_se | pred_sd |
|:---|---:|---:|---:|---:|
| **aggressive** | 63 | 51 | 11 | 11 |
| **affiliative** | 62 | 418 | 7 | 7 |
| **self_enhancing** | 18 | 18 | 2 | 2 |
| **self_defeating** | 18 | 18 | 2 | 2 |

---

## Aggressive Class 성능 변화 (H2/H3 핵심 지표)

| 지표 | v1 | v2 | v3 | v1→v2 | v2→v3 | v1→v3 |
|:---|---:|---:|---:|---:|---:|---:|
| n_aggressive | 80 | 175 | 181 | +95 | +6 | +101 |
| aggressive_precision | 0.25 | 0.3016 | 0.2986 | +0.0516 | -0.0030 | +0.0486 |
| aggressive_recall | 0.2 | 0.3257 | 0.3481 | +0.1257 | +0.0224 | +0.1481 |
| aggressive_F1 | 0.2222 | 0.3132 | 0.3214 | +0.0910 | +0.0082 | +0.0992 |

---

## Self-Defeating Class 성능 변화 (H2-3 예외 해석 근거)

| 지표 | v1 | v2 | v3 | v1→v2 | v2→v3 | v1→v3 |
|:---|---:|---:|---:|---:|---:|---:|
| n_self_defeating | 34 | 49 | 53 | +15 | +4 | +19 |
| sd_precision | 0.3 | 0.1429 | 0.0769 | -0.1571 | -0.0660 | -0.2231 |
| sd_recall | 0.0882 | 0.0612 | 0.0377 | -0.0270 | -0.0235 | -0.0505 |
| sd_F1 | 0.1364 | 0.0857 | 0.0506 | -0.0507 | -0.0351 | -0.0858 |

---

## 보수적 해석

### 1. Training label coverage 변화
v1 → v2 → v3 순으로 valid binary label이 2,480 → 3,077 → 3,574으로 증가했다.
type training label은 1027 → 1305 → 1410으로 증가했다.

### 2. Presence classifier 성능 변화
AUC 변화: v1(0.8008) → v2(0.7769) → v3(0.777).
Wendy's labels 추가(v2) 이후 AUC가 소폭 변동하였으며, coder3 추가(v3)는 거의 동일 수준을 유지했다.
Presence classifier 성능은 크게 향상되었다기보다 **안정적으로 유지**되었다고 보는 것이 적절하다.

### 3. Type classifier 성능 변화
macro F1: v1(0.3729) → v2(0.3749) → v3(0.3738).
전체 macro F1은 제한적이지만, aggressive class의 학습 데이터가 80 → 181으로 증가하면서
H2/H3 측정 기반은 일부 개선되었다.

### 4. Aggressive class 성능 한계
aggressive precision/recall/F1이 0.30 수준에 머물러 있다.
이는 H2-1, H2-2, H3 full-sample 결과의 해석 시 **분류기 측정 오차(measurement error)** 를
반드시 한계로 명시해야 함을 의미한다.

### 5. Self-defeating class 한계
v3 기준 n_self_defeating=53, F1=0.0506.
이 클래스는 소수 클래스(minority class)로, precision/recall 모두 매우 낮다.
H2-3의 "Aggressive − Self-Defeating not supported" 결과는
분류기가 self-defeating을 정확히 분류하지 못하는 한계가 결과에 영향을 미쳤을 수 있다.
따라서 이 결과는 신중하게 해석해야 한다.

### 6. Downstream simple OLS 결과와의 연결
v3 classifier 기준 full-sample H1 WHE = +1.1665*** (지지됨).
H2-1 (Other weighted avg) = +0.8495*** (지지됨), H2-2 (SELF weighted avg) = +0.4384*** (지지됨).
H2-3 Agg − SD = −0.2483** (opposite direction) — classifier 측정 오차 가능성 존재.
H3 turning point = 0.561, in range → H3 지지됨.
이 결과들은 classifier AUC=0.777, aggressive F1=0.321 수준의 분류기에 기반하므로,
measurement error를 통제한 추가 분석(FE 모델 등)에서 검증이 필요하다.

---

> 생성: compare_classifier_versions.py | 2026-06-19
