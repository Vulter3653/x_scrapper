# coder3 Batch2 Integration Audit — training-label v3

생성일: 2026-06-19

## 입력 데이터
| 파일 | 행수 |
|:---|---:|
| v2 combined template (기준) | 3,095 |
| coder3 batch2 제출 | 500 |
| **v3 최종** | **3,595** |

## 중복 감지 (3중 기준)
| 중복 유형 | 건수 |
|:---|---:|
| candidate_id 중복 | 0 |
| tweet_id 중복 | 0 |
| text_hash 중복 | 0 |
| **비중복 (실제 추가)** | **500** |

_중복 없음 — coder3 batch2 전량 신규 데이터_


## coder3 batch2 presence 분포
| 값 | 의미 | 건수 | training 처리 |
|:---|:---|---:|:---|
| 0 | non-humorous | 392 | binary training 포함 |
| 1 | humorous | 105 | binary + type training |
| 2 | reviewed ambiguous | 3 | **제외** (v3 파일에는 유지, human_notes='coder3_batch2_v3') |

## coder3 batch2 type 분포 (training 포함분, presence=1 & type 1-4)
| type | 유형 | 건수 |
|:---|:---|---:|
| 1 | aggressive | 6 |
| 2 | affiliative | 54 |
| 3 | self-enhancing | 41 |
| 4 | self-defeating | 4 |

## v2 → v3 변화 요약
| 지표 | v2 | v3 | 변화 |
|:---|---:|---:|---:|
| 총 행수 | 3,095 | 3,595 | **+500** |
| binary training eligible | 3,077 | 3,574 | +497 |
| presence=0 (non-humorous) | 1,741 | 2,133 | +392 |
| presence=1 (humorous) | 1,336 | 1,441 | +105 |
| presence=2 (ambiguous) | 18 | 21 | +3 |
| type training eligible | 1,305 | 1,410 | +105 |
| aggressive (type=1) | 175 | 181 | +6 |
| affiliative (type=2) | 616 | 670 | +54 |
| self_enhancing (type=3) | 465 | 506 | +41 |
| self_defeating (type=4) | 49 | 53 | +4 |

## 다음 단계 (사용자 승인 후)
- [ ] v3 classifier 재훈련 (`apply_domain_adapted_classifier.py --template v3`)
- [ ] 전체 corpus 재분류
- [ ] H1/H2/H3 데이터셋 재빌드
- [ ] simple OLS baseline v3 실행

## 파일 목록
| 파일 | 위치 | 용도 |
|:---|:---|:---|
| `coder3_batch2_integration_audit.md` | data/audit/ | 이 문서 |
| `coder3_batch2_integration_audit.csv` | data/audit/ | 행별 중복 감지 상세 |
| `training_labels_v3_with_coder3_batch2.csv` | data/human_labeling_template/ | v3 training label 전체 |
| `training_labels_v3_distribution.csv` | data/human_labeling_template/ | v3 분포 요약 |
| `v2_vs_v3_label_distribution_comparison.csv` | data/human_labeling_template/ | v2↔v3 비교 |
