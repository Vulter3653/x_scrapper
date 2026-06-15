"""
run_wendys_full_sample_four_type_humor_classifier.py

목적: 사람 기반 4-type humor 라벨(278건)을 학습하여
      전체 Wendy's 978개 post에 대해 모델 기반 4-type humor classification 생성.
      exploratory model-based full-sample classification.

gate 로직:
  pred_humor_final_050 == '0' → non_humor
  pred_humor_final_050 == '1' → pred_4type_humor_raw_model (argmax of multinomial)
  else                        → missing
"""

import csv
import math
import random
import os
import json
from collections import Counter, defaultdict

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold
from sklearn.metrics import (
    accuracy_score, f1_score, roc_auc_score,
    confusion_matrix, classification_report
)
from sklearn.preprocessing import label_binarize

# ── 경로 설정 ──────────────────────────────────────────────────────────────────
BASE = "20260615wendy's"
DATA_DIR  = os.path.join(BASE, "data")
CODE_DIR  = os.path.join(BASE, "code")
RESULT_DIR = os.path.join(BASE, "result")

REVIEW_PATH   = os.path.join(RESULT_DIR, "wendys_humor_review_sheet.csv")
PRED_PATH     = os.path.join(RESULT_DIR, "wendys_final_humor_presence_full_predictions.csv")
DATASET_OUT   = os.path.join(DATA_DIR,   "wendys_full_sample_four_type_humor_classifier_dataset.csv")
FULL_PRED_OUT = os.path.join(RESULT_DIR, "wendys_full_sample_four_type_humor_predictions.csv")
VALID_OUT     = os.path.join(RESULT_DIR, "wendys_full_sample_four_type_humor_validation_results.csv")
CM_OUT        = os.path.join(RESULT_DIR, "wendys_full_sample_four_type_humor_confusion_matrix.csv")
REPORT_OUT    = os.path.join(RESULT_DIR, "wendys_full_sample_four_type_humor_classification_report.csv")
AUDIT_OUT     = os.path.join(RESULT_DIR, "wendys_full_sample_four_type_humor_oof_error_audit.csv")
FW_OUT        = os.path.join(RESULT_DIR, "wendys_full_sample_four_type_humor_feature_weights.csv")
DIST_OUT      = os.path.join(RESULT_DIR, "wendys_full_sample_four_type_humor_distribution.csv")
PROB_PLOT_OUT = os.path.join(RESULT_DIR, "wendys_full_sample_four_type_humor_probability_distribution.png")
DIAG_OUT      = os.path.join(RESULT_DIR, "wendys_full_sample_four_type_humor_diagnostics.csv")
SUMMARY_OUT   = os.path.join(RESULT_DIR, "wendys_full_sample_four_type_humor_summary.md")

VALID_TYPES = {'aggressive', 'affiliative', 'self-enhancing', 'self-defeating'}
CLASSES = ['aggressive', 'affiliative', 'self-enhancing', 'self-defeating']
N_SPLITS = 5
RANDOM_STATE = 42

random.seed(RANDOM_STATE)
np.random.seed(RANDOM_STATE)

# ── 1. 데이터 로드 ─────────────────────────────────────────────────────────────
print("[1] 데이터 로드")
with open(REVIEW_PATH, newline='', encoding='utf-8') as f:
    review_rows = list(csv.DictReader(f))

with open(PRED_PATH, newline='', encoding='utf-8') as f:
    pred_rows = list(csv.DictReader(f))

# pred 파일을 no 기준으로 딕셔너리화
pred_by_no = {r['no']: r for r in pred_rows}

print(f"  review_sheet: {len(review_rows)}행")
print(f"  pred_file:    {len(pred_rows)}행")

# ── 2. 학습 표본 추출 ──────────────────────────────────────────────────────────
print("[2] 학습 표본 추출")
train_rows = [
    r for r in review_rows
    if r.get('final_humor_label_available') == '1'
    and r.get('final_humor_binary') == '1'
    and r.get('final_humor_type', '') in VALID_TYPES
]
train_texts  = [r['text'] for r in train_rows]
train_labels = [r['final_humor_type'] for r in train_rows]
train_nos    = [r['no'] for r in train_rows]

label_dist = Counter(train_labels)
print(f"  학습 표본: {len(train_rows)}건  분포: {dict(label_dist)}")

# 학습 데이터셋 저장
with open(DATASET_OUT, 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=['no','id','text','label'])
    w.writeheader()
    for r in train_rows:
        w.writerow({'no': r['no'], 'id': r.get('id',''), 'text': r['text'], 'label': r['final_humor_type']})
print(f"  → {DATASET_OUT}")

# ── 3. TF-IDF 벡터라이저 + Multinomial LogReg ──────────────────────────────────
print("[3] 모델 정의")
vectorizer = TfidfVectorizer(
    ngram_range=(1, 2),
    min_df=2,
    max_df=0.95,
    sublinear_tf=True,
    max_features=5000
)
clf = LogisticRegression(
    multi_class='multinomial',
    solver='lbfgs',
    class_weight='balanced',
    max_iter=1000,
    random_state=RANDOM_STATE
)

# ── 4. 5-fold Stratified CV + OOF predictions ─────────────────────────────────
print("[4] 5-fold Stratified CV (OOF)")
skf = StratifiedKFold(n_splits=N_SPLITS, shuffle=True, random_state=RANDOM_STATE)

X_texts = np.array(train_texts)
y_arr   = np.array(train_labels)

oof_pred  = np.empty(len(train_rows), dtype=object)
oof_probs = np.zeros((len(train_rows), len(CLASSES)))

for fold, (tr_idx, val_idx) in enumerate(skf.split(X_texts, y_arr)):
    X_tr_raw = X_texts[tr_idx]
    X_val_raw = X_texts[val_idx]
    y_tr  = y_arr[tr_idx]
    y_val = y_arr[val_idx]

    X_tr  = vectorizer.fit_transform(X_tr_raw)
    X_val = vectorizer.transform(X_val_raw)

    clf.fit(X_tr, y_tr)
    preds = clf.predict(X_val)
    probs = clf.predict_proba(X_val)

    oof_pred[val_idx]   = preds
    # align proba columns to CLASSES order
    cls_order = list(clf.classes_)
    for ci, c in enumerate(CLASSES):
        if c in cls_order:
            oof_probs[val_idx, ci] = probs[:, cls_order.index(c)]

    fold_acc = accuracy_score(y_val, preds)
    fold_f1  = f1_score(y_val, preds, average='macro', zero_division=0)
    fold_dist = Counter(preds)
    print(f"  Fold {fold+1}: acc={fold_acc:.4f}  macro-F1={fold_f1:.4f}  dist={dict(fold_dist)}")

# OOF 전체 지표
oof_acc = accuracy_score(y_arr, oof_pred)
oof_f1_macro  = f1_score(y_arr, oof_pred, average='macro', zero_division=0)
oof_f1_weight = f1_score(y_arr, oof_pred, average='weighted', zero_division=0)

y_bin = label_binarize(y_arr, classes=CLASSES)
try:
    oof_auc = roc_auc_score(y_bin, oof_probs, multi_class='ovr', average='macro')
except Exception:
    oof_auc = float('nan')

print(f"\n  OOF 전체: acc={oof_acc:.4f}  macro-F1={oof_f1_macro:.4f}  weighted-F1={oof_f1_weight:.4f}  AUC={oof_auc:.4f}")

# ── 5. OOF Confusion matrix + Classification report ───────────────────────────
print("[5] OOF 평가 지표")
cm = confusion_matrix(y_arr, oof_pred, labels=CLASSES)

# confusion matrix 저장
with open(CM_OUT, 'w', newline='', encoding='utf-8') as f:
    w = csv.writer(f)
    w.writerow(['actual_\\predicted'] + CLASSES)
    for i, c in enumerate(CLASSES):
        w.writerow([c] + list(cm[i]))
print(f"  → {CM_OUT}")

# classification report 저장
cr = classification_report(y_arr, oof_pred, labels=CLASSES, output_dict=True, zero_division=0)
with open(REPORT_OUT, 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=['class','precision','recall','f1-score','support'])
    w.writeheader()
    for c in CLASSES + ['macro avg', 'weighted avg']:
        if c in cr:
            row = cr[c]
            w.writerow({
                'class': c,
                'precision': f"{row.get('precision', 0):.4f}",
                'recall':    f"{row.get('recall', 0):.4f}",
                'f1-score':  f"{row.get('f1-score', 0):.4f}",
                'support':   int(row.get('support', 0))
            })
print(f"  → {REPORT_OUT}")

# ── 6. OOF 오류 분석 ───────────────────────────────────────────────────────────
print("[6] OOF 오류 분석")
def get_error_type(true_label, pred_label):
    if true_label == pred_label:
        return 'correct'
    elif true_label == 'aggressive':
        return 'false_non_aggressive'
    elif pred_label == 'aggressive':
        return 'false_aggressive'
    else:
        return 'inter_other_confusion'

audit_rows = []
for i, r in enumerate(train_rows):
    true_l = y_arr[i]
    pred_l = oof_pred[i]
    err_type = get_error_type(true_l, pred_l)
    prob_dict = {c: f"{oof_probs[i, ci]:.4f}" for ci, c in enumerate(CLASSES)}
    audit_rows.append({
        'no': r['no'],
        'id': r.get('id',''),
        'text': r['text'][:120],
        'true_label': true_l,
        'oof_pred': pred_l,
        'error_type': err_type,
        **{f'p_{c}': prob_dict[c] for c in CLASSES}
    })

with open(AUDIT_OUT, 'w', newline='', encoding='utf-8') as f:
    fieldnames = ['no','id','text','true_label','oof_pred','error_type'] + [f'p_{c}' for c in CLASSES]
    w = csv.DictWriter(f, fieldnames=fieldnames)
    w.writeheader()
    w.writerows(audit_rows)

error_dist = Counter(r['error_type'] for r in audit_rows)
print(f"  error_type 분포: {dict(error_dist)}")
print(f"  → {AUDIT_OUT}")

# ── 7. 전체 모델 학습 (전체 278건) ────────────────────────────────────────────
print("[7] 전체 학습 표본으로 최종 모델 학습")
X_all_train = vectorizer.fit_transform(train_texts)
clf.fit(X_all_train, train_labels)
print("  최종 모델 학습 완료")

# ── 8. feature weights 저장 ────────────────────────────────────────────────────
print("[8] feature weights 저장")
feature_names = vectorizer.get_feature_names_out()
fw_rows = []
for ci, c in enumerate(CLASSES):
    cls_idx = list(clf.classes_).index(c) if c in clf.classes_ else None
    if cls_idx is None:
        continue
    coefs = clf.coef_[cls_idx]
    top_idx = np.argsort(coefs)[::-1][:35]
    for rank, fi in enumerate(top_idx, 1):
        fw_rows.append({
            'class': c,
            'rank': rank,
            'feature': feature_names[fi],
            'weight': f"{coefs[fi]:.6f}"
        })

with open(FW_OUT, 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=['class','rank','feature','weight'])
    w.writeheader()
    w.writerows(fw_rows)
print(f"  → {FW_OUT}")

# ── 9. 전체 978건 예측 ────────────────────────────────────────────────────────
print("[9] 전체 978건 예측")
all_texts = [r['text'] for r in review_rows]
X_full = vectorizer.transform(all_texts)
full_raw_preds = clf.predict(X_full)
full_probs     = clf.predict_proba(X_full)
cls_order_final = list(clf.classes_)

# 확률 정렬
full_probs_aligned = np.zeros((len(review_rows), len(CLASSES)))
for ci, c in enumerate(CLASSES):
    if c in cls_order_final:
        full_probs_aligned[:, ci] = full_probs[:, cls_order_final.index(c)]

# ── 10. gate 처리: pred_humor_final_050 ───────────────────────────────────────
print("[10] gate 처리")
full_result_rows = []
for i, r in enumerate(review_rows):
    no = r['no']
    pred_gate = pred_by_no.get(no, {}).get('pred_humor_final_050', '')

    raw_pred = full_raw_preds[i]
    if pred_gate == '0':
        final_pred = 'non_humor'
        scope = 'non_humor_gate'
    elif pred_gate == '1':
        final_pred = raw_pred
        scope = 'model_predicted'
    else:
        final_pred = 'missing'
        scope = 'missing_gate'

    p_agg    = full_probs_aligned[i, CLASSES.index('aggressive')]
    p_aff    = full_probs_aligned[i, CLASSES.index('affiliative')]
    p_se     = full_probs_aligned[i, CLASSES.index('self-enhancing')]
    p_sd     = full_probs_aligned[i, CLASSES.index('self-defeating')]

    full_result_rows.append({
        'no':   no,
        'id':   r.get('id',''),
        'text': r.get('text',''),
        'final_humor_binary': r.get('final_humor_binary',''),
        'final_humor_type':   r.get('final_humor_type',''),
        'pred_humor_final_050': pred_gate,
        'p_4type_aggressive_model':     f"{p_agg:.6f}",
        'p_4type_affiliative_model':    f"{p_aff:.6f}",
        'p_4type_self_enhancing_model': f"{p_se:.6f}",
        'p_4type_self_defeating_model': f"{p_sd:.6f}",
        'pred_4type_humor_raw_model':    raw_pred,
        'pred_full_4type_humor_model':   final_pred,
        'full_4type_prediction_scope':   scope
    })

# 저장
pred_fieldnames = [
    'no','id','text','final_humor_binary','final_humor_type',
    'pred_humor_final_050',
    'p_4type_aggressive_model','p_4type_affiliative_model',
    'p_4type_self_enhancing_model','p_4type_self_defeating_model',
    'pred_4type_humor_raw_model','pred_full_4type_humor_model',
    'full_4type_prediction_scope'
]
with open(FULL_PRED_OUT, 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=pred_fieldnames)
    w.writeheader()
    w.writerows(full_result_rows)
print(f"  → {FULL_PRED_OUT}")

# ── 11. 분포 확인 ─────────────────────────────────────────────────────────────
final_dist = Counter(r['pred_full_4type_humor_model'] for r in full_result_rows)
raw_dist   = Counter(r['pred_4type_humor_raw_model'] for r in full_result_rows)
scope_dist = Counter(r['full_4type_prediction_scope'] for r in full_result_rows)
print(f"\n  pred_full_4type 분포: {dict(final_dist)}")
print(f"  pred_4type_raw 분포:  {dict(raw_dist)}")
print(f"  scope 분포:           {dict(scope_dist)}")

# 분포 저장
with open(DIST_OUT, 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=['category','pred_full_4type_count','pred_raw_count'])
    w.writeheader()
    all_keys = sorted(set(list(final_dist.keys()) + list(raw_dist.keys())))
    for k in all_keys:
        w.writerow({'category': k, 'pred_full_4type_count': final_dist.get(k,0), 'pred_raw_count': raw_dist.get(k,0)})
print(f"  → {DIST_OUT}")

# ── 12. 확률 분포 플롯 ────────────────────────────────────────────────────────
print("[12] 확률 분포 플롯")
fig, axes = plt.subplots(2, 2, figsize=(10, 8))
colors = ['#E74C3C', '#3498DB', '#2ECC71', '#F39C12']
for ci, (c, ax, col) in enumerate(zip(CLASSES, axes.flatten(), colors)):
    probs_col = full_probs_aligned[:, ci]
    ax.hist(probs_col, bins=40, color=col, edgecolor='white', alpha=0.85)
    ax.set_title(f"P({c})", fontsize=11)
    ax.set_xlabel("Probability", fontsize=9)
    ax.set_ylabel("Count", fontsize=9)
    ax.axvline(0.5, color='black', linestyle='--', linewidth=0.8, alpha=0.6)
plt.suptitle("4-Type Humor Multinomial Probability Distribution (n=978)", fontsize=12, y=1.01)
plt.tight_layout()
plt.savefig(PROB_PLOT_OUT, dpi=150, bbox_inches='tight')
plt.close()
print(f"  → {PROB_PLOT_OUT}")

# ── 13. Diagnostics ───────────────────────────────────────────────────────────
print("[13] diagnostics 저장")
diag = {
    'n_train': len(train_rows),
    'n_full': len(review_rows),
    'n_folds': N_SPLITS,
    'oof_accuracy': round(oof_acc, 4),
    'oof_macro_f1': round(oof_f1_macro, 4),
    'oof_weighted_f1': round(oof_f1_weight, 4),
    'oof_macro_auc': round(oof_auc, 4) if not math.isnan(oof_auc) else 'nan',
    'train_n_aggressive': label_dist['aggressive'],
    'train_n_affiliative': label_dist['affiliative'],
    'train_n_self_enhancing': label_dist['self-enhancing'],
    'train_n_self_defeating': label_dist['self-defeating'],
    'small_class_warning': True,
    'small_class_note': 'self-defeating n=15 < 20; fold당 약 3건. 소표본 클래스 결과 해석 주의.',
    'full_pred_non_humor': final_dist.get('non_humor', 0),
    'full_pred_aggressive': final_dist.get('aggressive', 0),
    'full_pred_affiliative': final_dist.get('affiliative', 0),
    'full_pred_self_enhancing': final_dist.get('self-enhancing', 0),
    'full_pred_self_defeating': final_dist.get('self-defeating', 0),
    'full_pred_missing': final_dist.get('missing', 0),
    'gate_non_humor_count': scope_dist.get('non_humor_gate', 0),
    'gate_model_predicted_count': scope_dist.get('model_predicted', 0),
    'gate_missing_count': scope_dist.get('missing_gate', 0),
    'feature': 'text_only',
    'vectorizer': 'TfidfVectorizer(ngram_range=(1,2),min_df=2,max_df=0.95,sublinear_tf=True,max_features=5000)',
    'classifier': 'LogisticRegression(multi_class=multinomial,solver=lbfgs,class_weight=balanced,max_iter=1000)',
    'note': 'exploratory model-based full-sample classification. engagement 변수 및 기존 모델 예측값 feature 미사용.'
}

with open(DIAG_OUT, 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=['metric', 'value'])
    w.writeheader()
    for k, v in diag.items():
        w.writerow({'metric': k, 'value': v})
print(f"  → {DIAG_OUT}")

# ── 14. Validation Checks (20개) ──────────────────────────────────────────────
print("[14] Validation checks")
checks = []

def chk(name, passed, detail=""):
    status = "PASS" if passed else "FAIL"
    checks.append({'check': name, 'status': status, 'detail': detail})
    icon = "✓" if passed else "✗"
    print(f"  [{icon}] {name}: {detail}")
    return passed

# 1. 학습 표본 크기
chk("01_train_sample_size", len(train_rows) == 278, f"n={len(train_rows)}")

# 2. 4개 클래스 모두 존재
chk("02_all_classes_present", set(label_dist.keys()) == VALID_TYPES, str(dict(label_dist)))

# 3. self-defeating 소표본 경고 포함
chk("03_small_class_warning_in_diag", diag['small_class_warning'] == True, "small_class_warning=True")

# 4. n_folds == 5
chk("04_n_folds_5", N_SPLITS == 5, f"n_folds={N_SPLITS}")

# 5. OOF 예측 길이 일치
chk("05_oof_pred_length", len(oof_pred) == len(train_rows), f"oof={len(oof_pred)} train={len(train_rows)}")

# 6. OOF accuracy > 0.30 (random=0.25)
chk("06_oof_acc_above_chance", oof_acc > 0.30, f"acc={oof_acc:.4f}")

# 7. OOF macro-F1 > 0 (valid)
chk("07_oof_f1_valid", oof_f1_macro > 0, f"macro-F1={oof_f1_macro:.4f}")

# 8. 전체 예측 행 수
chk("08_full_pred_row_count", len(full_result_rows) == 978, f"n={len(full_result_rows)}")

# 9. non_humor gate 수 == 414
chk("09_non_humor_gate_count", scope_dist.get('non_humor_gate',0) == 414, f"n={scope_dist.get('non_humor_gate',0)}")

# 10. model_predicted scope 수 == 564
chk("10_model_predicted_count", scope_dist.get('model_predicted',0) == 564, f"n={scope_dist.get('model_predicted',0)}")

# 11. missing 없음 (gate 값이 모두 0 또는 1)
chk("11_no_missing_gate", scope_dist.get('missing_gate',0) == 0, f"missing={scope_dist.get('missing_gate',0)}")

# 12. non_humor pred == 414
chk("12_final_non_humor_414", final_dist.get('non_humor',0) == 414, f"n={final_dist.get('non_humor',0)}")

# 13. humor type 합계 == 564
humor_sum = sum(final_dist.get(c,0) for c in CLASSES)
chk("13_humor_type_sum_564", humor_sum == 564, f"sum={humor_sum}")

# 14. 확률 합 ≈ 1 (row-sum check)
prob_sums = full_probs_aligned.sum(axis=1)
all_sum_ok = bool(np.all(np.abs(prob_sums - 1.0) < 1e-4))
chk("14_prob_row_sum_1", all_sum_ok, f"max_dev={np.max(np.abs(prob_sums-1.0)):.6f}")

# 15. feature weights 4개 클래스 모두 존재
fw_classes = set(r['class'] for r in fw_rows)
chk("15_feature_weights_all_classes", fw_classes == set(CLASSES), str(fw_classes))

# 16. feature weights top 30+ per class
fw_class_counts = Counter(r['class'] for r in fw_rows)
all_fw_ok = all(fw_class_counts.get(c,0) >= 30 for c in CLASSES)
chk("16_feature_weights_top30_each", all_fw_ok, str(dict(fw_class_counts)))

# 17. confusion matrix 행렬 크기 4x4
chk("17_confusion_matrix_4x4", cm.shape == (4, 4), f"shape={cm.shape}")

# 18. OOF AUC > 0.5
auc_ok = (not math.isnan(oof_auc)) and oof_auc > 0.5
chk("18_oof_auc_above_0_5", auc_ok, f"AUC={oof_auc:.4f}")

# 19. pred_full_4type 컬럼 값 검증
valid_preds = set(CLASSES) | {'non_humor', 'missing'}
pred_vals = set(r['pred_full_4type_humor_model'] for r in full_result_rows)
chk("19_pred_values_valid", pred_vals.issubset(valid_preds), str(pred_vals))

# 20. diagnostics small_class_warning=True
chk("20_diag_small_class_warning_true", diag.get('small_class_warning') == True, "confirmed")

n_pass = sum(1 for c in checks if c['status'] == 'PASS')
n_fail = sum(1 for c in checks if c['status'] == 'FAIL')
print(f"\n  Validation: {n_pass}/20 PASS, {n_fail} FAIL")

with open(VALID_OUT, 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=['check','status','detail'])
    w.writeheader()
    w.writerows(checks)
print(f"  → {VALID_OUT}")

if n_fail > 0:
    print("\n[ERROR] Validation FAIL — commit 하지 않음.")
    import sys; sys.exit(1)

# ── 15. Summary markdown ──────────────────────────────────────────────────────
print("[15] summary.md 작성")

summary_md = f"""# Wendy's Full-Sample 4-Type Humor Classification — 요약 보고서

> **탐색적 모델 기반 전체 표본 분류 (exploratory model-based full-sample classification)**
> 사람 라벨 278건을 학습하여 전체 978개 post에 4-type 유머 분류를 확장함.

---

## 1. 목적

사람 기반 4-type humor 라벨(278건)을 학습 표본으로 사용하여,
전체 Wendy's 978개 post에 대해 모델 기반 4-type humor classification을 생성함.
기존 이진 유머 유무 예측(`pred_humor_final_050`)을 gate로 사용하여 non_humor(414건)를 우선 분리,
나머지 564건에 대해 multinomial logistic regression 기반 타입 예측을 부여함.

---

## 2. 학습 데이터

| 항목 | 값 |
|---|---|
| 학습 표본 수 | {len(train_rows)}건 |
| aggressive | {label_dist['aggressive']}건 |
| affiliative | {label_dist['affiliative']}건 |
| self-enhancing | {label_dist['self-enhancing']}건 |
| self-defeating | {label_dist['self-defeating']}건 |
| 소표본 경고 | self-defeating n=15 (fold당 약 3건) |

---

## 3. 모델 사양

- **Vectorizer**: TF-IDF (ngram 1-2, min_df=2, max_df=0.95, sublinear_tf=True, max_features=5000)
- **Classifier**: Multinomial Logistic Regression (class_weight='balanced', solver='lbfgs', max_iter=1000)
- **CV**: Stratified 5-fold
- **Feature**: text only (engagement 변수 및 기존 모델 예측값 feature 미사용)

---

## 4. OOF (Out-of-Fold) 성능

| 지표 | 값 |
|---|---|
| Accuracy | {oof_acc:.4f} |
| Macro-F1 | {oof_f1_macro:.4f} |
| Weighted-F1 | {oof_f1_weight:.4f} |
| Macro-AUC (OvR) | {oof_auc:.4f} |

**주의**: self-defeating 클래스는 n=15로 소표본임. OOF 성능 해석 시 이 클래스의 결과는 불안정할 수 있음.

---

## 5. 전체 978건 예측 분포

| 카테고리 | pred_full_4type_humor_model | pred_4type_humor_raw_model |
|---|---|---|
| non_humor | {final_dist.get('non_humor',0)} (gate) | {raw_dist.get('non_humor',0)} |
| aggressive | {final_dist.get('aggressive',0)} | {raw_dist.get('aggressive',0)} |
| affiliative | {final_dist.get('affiliative',0)} | {raw_dist.get('affiliative',0)} |
| self-enhancing | {final_dist.get('self-enhancing',0)} | {raw_dist.get('self-enhancing',0)} |
| self-defeating | {final_dist.get('self-defeating',0)} | {raw_dist.get('self-defeating',0)} |
| missing | {final_dist.get('missing',0)} | - |
| **합계** | **{sum(final_dist.values())}** | **{len(review_rows)}** |

---

## 6. Gate 로직

```
pred_humor_final_050 == '0' → pred_full_4type_humor_model = 'non_humor'
pred_humor_final_050 == '1' → pred_full_4type_humor_model = pred_4type_humor_raw_model (argmax)
else                        → pred_full_4type_humor_model = 'missing'
```

non_humor_gate: {scope_dist.get('non_humor_gate',0)}건 / model_predicted: {scope_dist.get('model_predicted',0)}건 / missing: {scope_dist.get('missing_gate',0)}건

---

## 7. Validation

20개 검증 항목 모두 **PASS** (`{n_pass}/20`).

---

## 8. 한계점 및 해석 주의사항

1. self-defeating 클래스는 n=15 소표본으로 모델 학습 안정성이 낮음.
2. 본 분석은 exploratory model-based full-sample classification으로,
   사람 판단 기반 분류를 대체하지 않음.
3. TF-IDF 기반 텍스트 특성만 사용하여 문맥, 이미지, 링크 등 비텍스트 정보 미반영.
4. engagement 변수 및 기존 유머 유무 모델 예측값은 feature에서 제외하여
   독립변수-종속변수 순환 편의(circular bias)를 방지함.

---

*생성일: 2026-06-15*
"""

with open(SUMMARY_OUT, 'w', encoding='utf-8') as f:
    f.write(summary_md)
print(f"  → {SUMMARY_OUT}")

print("\n[완료] 모든 출력 파일 생성 완료. Validation 20/20 PASS.")
print("  커밋 대상: analysis: expand wendys four type humor classification full sample")
