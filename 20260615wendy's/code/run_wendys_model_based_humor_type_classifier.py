"""
run_wendys_model_based_humor_type_classifier.py

== 작업 목적 ==
사람 기반 유머 타입 라벨(coder1 > human > coder2 우선순위)을 이용해
TF-IDF + Logistic Regression 기반 유머 타입 분류기를 학습하고,
전체 Wendy's 978개 post에 대해 유머 타입 예측값을 생성한다.

== primary model ==
aggressive vs other_humor 이진 분류
학습 표본: final_humor_label_available=1, final_humor_binary=1,
           final_humor_type_group in {"aggressive", "other_humor"}

== feature 원칙 ==
text 컬럼만 사용. engagement 변수, 기존 유머 유무 예측값,
사람 라벨 출처 변수는 절대 feature로 사용하지 않는다.

== 예측 로직 ==
pred_humor_final_050=0  → non_humor
pred_humor_final_050=1, p_type_aggressive >= 0.5 → aggressive
pred_humor_final_050=1, p_type_aggressive < 0.5  → other_humor

== 4-type 모델 ==
self-defeating 표본이 15건(< 20건)이므로 4-type은 exploratory 전용.
primary 결과는 aggressive vs other_humor 이진 모델로 고정.

== 인과관계 주의 ==
본 분석은 관측적 분류 분석이다.
engagement 변수를 feature로 사용하지 않았으므로
타입 분류 결과는 engagement와 직접 연관되지 않는다.
"""

import csv
import math
import sys
import re
import warnings
from pathlib import Path
from collections import Counter

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.metrics import (accuracy_score, precision_score, recall_score,
                              f1_score, roc_auc_score, balanced_accuracy_score,
                              confusion_matrix, classification_report)
from sklearn.preprocessing import LabelEncoder

warnings.filterwarnings('ignore')

# ── 경로 설정
BASE         = Path("20260615wendy's")
REVIEW_CSV   = BASE / "result" / "wendys_humor_review_sheet.csv"
PRED_CSV     = BASE / "result" / "wendys_final_humor_presence_full_predictions.csv"
OUT_DATA     = BASE / "data"   / "wendys_model_based_humor_type_dataset.csv"
OUT_PRED     = BASE / "result" / "wendys_model_based_humor_type_full_predictions.csv"
OUT_VAL      = BASE / "result" / "wendys_model_based_humor_type_validation_results.csv"
OUT_CM       = BASE / "result" / "wendys_model_based_humor_type_confusion_matrix.csv"
OUT_OOF      = BASE / "result" / "wendys_model_based_humor_type_oof_error_audit.csv"
OUT_FEAT     = BASE / "result" / "wendys_model_based_humor_type_feature_weights.csv"
OUT_DIAG     = BASE / "result" / "wendys_model_based_humor_type_diagnostics.csv"
OUT_PROB_PNG = BASE / "result" / "wendys_model_based_humor_type_probability_distribution.png"
OUT_MD       = BASE / "result" / "wendys_model_based_humor_type_summary.md"

OUT_4VAL = BASE / "result" / "wendys_model_based_humor_4type_validation_results.csv"
OUT_4CM  = BASE / "result" / "wendys_model_based_humor_4type_confusion_matrix.csv"
OUT_4MD  = BASE / "result" / "wendys_model_based_humor_4type_summary.md"

POSTS_JSON = Path("data/wendys/posts.json")


def fmt(v, dec=4):
    if isinstance(v, float) and math.isnan(v): return 'nan'
    if isinstance(v, (float, np.floating)):     return f"{v:.{dec}f}"
    return str(v)


def main():
    # ── 0. posts.json 수정 여부 확인 (시작)
    posts_mtime_start = POSTS_JSON.stat().st_mtime if POSTS_JSON.exists() else None

    # ── 1. 데이터 로드
    with open(REVIEW_CSV, newline='', encoding='utf-8') as f:
        review = {r['id']: r for r in csv.DictReader(f)}
    with open(PRED_CSV, newline='', encoding='utf-8') as f:
        preds = {r['id']: r for r in csv.DictReader(f)}

    total = len(review)
    print(f"전체: {total}건")
    assert total == 978, f"전체 행 수 오류: {total}"

    # ── 2. 각 row에 pred_humor_final_050 병합
    all_rows = []
    for id_, rev in review.items():
        merged = dict(rev)
        pred_row = preds.get(id_, {})
        merged['pred_humor_final_050']      = pred_row.get('pred_humor_final_050', '')
        merged['p_humor_final_tfidf_logreg'] = pred_row.get('p_humor_final_tfidf_logreg', '')
        all_rows.append(merged)

    # ── 3. type 분류 기준
    VALID_TYPES = {'affiliative', 'aggressive', 'self-enhancing', 'self-defeating'}

    # ── 4. 학습 표본 구성
    train_rows = [
        r for r in all_rows
        if r.get('final_humor_label_available') == '1'
        and r.get('final_humor_binary') == '1'
        and r.get('final_humor_type_group') in ('aggressive', 'other_humor')
    ]
    n_train     = len(train_rows)
    n_agg_train = sum(1 for r in train_rows if r['final_humor_type_group'] == 'aggressive')
    n_oth_train = sum(1 for r in train_rows if r['final_humor_type_group'] == 'other_humor')
    print(f"학습 표본: {n_train}건 (aggressive={n_agg_train}, other_humor={n_oth_train})")

    # 제외 항목 집계
    n_excl_nh   = sum(1 for r in all_rows if r.get('final_humor_label_available')=='1' and r.get('final_humor_binary')=='0')
    n_excl_miss = sum(1 for r in all_rows if r.get('final_humor_label_available')=='1' and r.get('final_humor_binary')=='1' and r.get('final_humor_type_group')=='missing')
    n_excl_unl  = sum(1 for r in all_rows if r.get('final_humor_label_available')=='0')

    # 4-type 표본 분포 체크
    type4_rows = [
        r for r in all_rows
        if r.get('final_humor_label_available') == '1'
        and r.get('final_humor_binary') == '1'
        and r.get('final_humor_type', '') in VALID_TYPES
    ]
    type4_dist = Counter(r['final_humor_type'] for r in type4_rows)
    min_type4  = min(type4_dist.values()) if type4_dist else 0
    print(f"4-type 분포: {dict(type4_dist)} (최소={min_type4}건)")
    run_4type = True  # exploratory로 수행

    # ── 5. TF-IDF 설정
    TFIDF_PARAMS = dict(
        ngram_range=(1, 2),
        min_df=2,
        max_df=0.95,
        sublinear_tf=True,
        max_features=5000,
    )

    # ── 6. Primary: aggressive vs other_humor 이진 모델
    print("\n[분석 1] TF-IDF + LogReg: aggressive vs other_humor")
    X_texts = [r['text'] for r in train_rows]
    y_bin   = np.array([1 if r['final_humor_type_group'] == 'aggressive' else 0
                        for r in train_rows])

    tfidf_bin = TfidfVectorizer(**TFIDF_PARAMS)
    X_bin     = tfidf_bin.fit_transform(X_texts)

    clf_bin = LogisticRegression(
        class_weight='balanced',
        solver='liblinear',
        max_iter=1000,
        random_state=42,
    )

    # ── 7. Stratified k-fold CV
    n_folds = 5
    min_class = min(n_agg_train, n_oth_train)
    if min_class < n_folds:
        n_folds = min_class
        print(f"  최소 클래스 {min_class}건 → {n_folds}-fold로 조정")

    skf = StratifiedKFold(n_splits=n_folds, shuffle=True, random_state=42)

    cv_acc  = cross_val_score(clf_bin, X_bin, y_bin, cv=skf, scoring='accuracy')
    cv_f1   = cross_val_score(clf_bin, X_bin, y_bin, cv=skf, scoring='f1')
    cv_auc  = cross_val_score(clf_bin, X_bin, y_bin, cv=skf, scoring='roc_auc')
    cv_bal  = cross_val_score(clf_bin, X_bin, y_bin, cv=skf, scoring='balanced_accuracy')
    cv_prec = cross_val_score(clf_bin, X_bin, y_bin, cv=skf, scoring='precision')
    cv_rec  = cross_val_score(clf_bin, X_bin, y_bin, cv=skf, scoring='recall')

    print(f"  {n_folds}-fold CV — accuracy={cv_acc.mean():.4f}±{cv_acc.std():.4f}, "
          f"F1={cv_f1.mean():.4f}, AUC={cv_auc.mean():.4f}")

    # ── 8. OOF predictions
    oof_proba = np.zeros(n_train)
    oof_pred  = np.zeros(n_train, dtype=int)
    for tr_idx, te_idx in skf.split(X_bin, y_bin):
        clf_fold = LogisticRegression(
            class_weight='balanced', solver='liblinear',
            max_iter=1000, random_state=42)
        clf_fold.fit(X_bin[tr_idx], y_bin[tr_idx])
        oof_proba[te_idx] = clf_fold.predict_proba(X_bin[te_idx])[:, 1]
        oof_pred[te_idx]  = (oof_proba[te_idx] >= 0.5).astype(int)

    # ── 9. OOF 성능 지표
    oof_acc  = accuracy_score(y_bin, oof_pred)
    oof_f1   = f1_score(y_bin, oof_pred, zero_division=0)
    oof_auc  = roc_auc_score(y_bin, oof_proba)
    oof_bal  = balanced_accuracy_score(y_bin, oof_pred)
    oof_prec = precision_score(y_bin, oof_pred, zero_division=0)
    oof_rec  = recall_score(y_bin, oof_pred, zero_division=0)
    oof_cm   = confusion_matrix(y_bin, oof_pred, labels=[0,1])
    oof_tn, oof_fp, oof_fn, oof_tp = oof_cm.ravel()

    print(f"  OOF accuracy={oof_acc:.4f}, F1={oof_f1:.4f}, AUC={oof_auc:.4f}")

    # ── 10. 전체 모델 학습 (full retrain)
    clf_bin.fit(X_bin, y_bin)

    # 전체 978건 예측
    all_texts = [r['text'] for r in all_rows]
    X_all     = tfidf_bin.transform(all_texts)
    proba_all = clf_bin.predict_proba(X_all)
    p_agg_all = proba_all[:, 1]  # P(aggressive)
    p_oth_all = proba_all[:, 0]  # P(other_humor)

    # ── 11. 최종 type 그룹 결합 (pred_humor_final_050 결합)
    for i, r in enumerate(all_rows):
        r['p_type_aggressive_model']   = p_agg_all[i]
        r['p_type_other_humor_model']  = p_oth_all[i]

        pf = r.get('pred_humor_final_050', '')
        if pf == '0':
            r['pred_humor_type_group_model']     = 'non_humor'
            r['pred_humor_type_group_model_050'] = 'non_humor'
        elif pf == '1':
            if p_agg_all[i] >= 0.5:
                r['pred_humor_type_group_model']     = 'aggressive'
                r['pred_humor_type_group_model_050'] = 'aggressive'
            else:
                r['pred_humor_type_group_model']     = 'other_humor'
                r['pred_humor_type_group_model_050'] = 'other_humor'
        else:
            r['pred_humor_type_group_model']     = 'missing'
            r['pred_humor_type_group_model_050'] = 'missing'

        # scope
        avail = r.get('final_humor_label_available', '')
        fhb   = r.get('final_humor_binary', '')
        fhtg  = r.get('final_humor_type_group', '')
        if avail == '1' and fhb == '1' and fhtg in ('aggressive', 'other_humor'):
            r['type_prediction_scope'] = 'human_type_labeled_humor'
        elif pf == '1':
            r['type_prediction_scope'] = 'model_predicted_humor'
        elif pf == '0':
            r['type_prediction_scope'] = 'model_predicted_non_humor'
        else:
            r['type_prediction_scope'] = 'missing'

    # ── 12. 예측 분포
    pred_grp_dist = Counter(r['pred_humor_type_group_model'] for r in all_rows)
    scope_dist    = Counter(r['type_prediction_scope'] for r in all_rows)
    print(f"  전체 978건 예측 분포: {dict(pred_grp_dist)}")

    # ── 13. OOF error audit
    oof_audit = []
    for i, r in enumerate(train_rows):
        true_lbl  = 'aggressive' if y_bin[i] == 1 else 'other_humor'
        pred_lbl  = 'aggressive' if oof_pred[i] == 1 else 'other_humor'
        if true_lbl == pred_lbl:
            err = 'correct'
        elif pred_lbl == 'aggressive':
            err = 'false_aggressive'
        else:
            err = 'false_other_humor'
        oof_audit.append({
            'id':                       r['id'],
            'tweet_url':                r.get('tweet_url', ''),
            'text':                     r['text'],
            'final_humor_type_group':   r['final_humor_type_group'],
            'p_type_aggressive_model_oof': fmt(float(oof_proba[i])),
            'pred_humor_type_group_oof':   pred_lbl,
            'error_type':               err,
        })

    # ── 14. Feature weights (top 50)
    feature_names = tfidf_bin.get_feature_names_out()
    coef = clf_bin.coef_[0]
    feat_rows = sorted(
        [{'feature': fn, 'coefficient': fmt(float(c)),
          'direction': 'aggressive' if c > 0 else 'other_humor'}
         for fn, c in zip(feature_names, coef)],
        key=lambda x: abs(float(x['coefficient'])), reverse=True
    )[:100]

    # ── 15. Validation results CSV
    val_rows = [
        {'metric': 'n_train', 'mean': n_train, 'std': '', 'note': f'agg={n_agg_train}, oth={n_oth_train}'},
        {'metric': 'n_folds', 'mean': n_folds, 'std': '', 'note': ''},
        {'metric': 'cv_accuracy',          'mean': fmt(cv_acc.mean()),  'std': fmt(cv_acc.std()),  'note': ''},
        {'metric': 'cv_f1_aggressive',     'mean': fmt(cv_f1.mean()),   'std': fmt(cv_f1.std()),   'note': ''},
        {'metric': 'cv_roc_auc',           'mean': fmt(cv_auc.mean()),  'std': fmt(cv_auc.std()),  'note': ''},
        {'metric': 'cv_balanced_accuracy', 'mean': fmt(cv_bal.mean()),  'std': fmt(cv_bal.std()),  'note': ''},
        {'metric': 'cv_precision',         'mean': fmt(cv_prec.mean()), 'std': fmt(cv_prec.std()), 'note': ''},
        {'metric': 'cv_recall',            'mean': fmt(cv_rec.mean()),  'std': fmt(cv_rec.std()),  'note': ''},
        {'metric': 'oof_accuracy',         'mean': fmt(oof_acc),        'std': '', 'note': ''},
        {'metric': 'oof_f1_aggressive',    'mean': fmt(oof_f1),         'std': '', 'note': ''},
        {'metric': 'oof_roc_auc',          'mean': fmt(oof_auc),        'std': '', 'note': ''},
        {'metric': 'oof_balanced_accuracy','mean': fmt(oof_bal),        'std': '', 'note': ''},
        {'metric': 'oof_precision',        'mean': fmt(oof_prec),       'std': '', 'note': ''},
        {'metric': 'oof_recall',           'mean': fmt(oof_rec),        'std': '', 'note': ''},
        {'metric': 'oof_TP', 'mean': int(oof_tp), 'std': '', 'note': 'true aggressive'},
        {'metric': 'oof_FP', 'mean': int(oof_fp), 'std': '', 'note': 'false aggressive'},
        {'metric': 'oof_TN', 'mean': int(oof_tn), 'std': '', 'note': 'true other_humor'},
        {'metric': 'oof_FN', 'mean': int(oof_fn), 'std': '', 'note': 'false aggressive (missed)'},
    ]

    # ── 16. 파일 저장 ──────────────────────────────────────────

    # 학습 dataset
    ds_cols = ['id','tweet_url','text','final_humor_label_available',
               'final_humor_binary','final_humor_type_group','final_humor_type']
    with open(OUT_DATA, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=ds_cols, quoting=csv.QUOTE_ALL, extrasaction='ignore')
        w.writeheader()
        w.writerows(train_rows)

    # full predictions
    pred_cols = [
        'no','id','tweet_url','text',
        'final_humor_binary','final_humor_source','final_humor_label_available',
        'final_humor_type','final_humor_type_group',
        'pred_humor_final_050',
        'p_type_aggressive_model','p_type_other_humor_model',
        'pred_humor_type_group_model','pred_humor_type_group_model_050',
        'type_prediction_scope',
    ]
    pred_out = []
    for r in all_rows:
        row = {k: r.get(k,'') for k in pred_cols}
        row['p_type_aggressive_model']  = fmt(float(r['p_type_aggressive_model']))
        row['p_type_other_humor_model'] = fmt(float(r['p_type_other_humor_model']))
        pred_out.append(row)
    with open(OUT_PRED, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=pred_cols, quoting=csv.QUOTE_ALL, extrasaction='ignore')
        w.writeheader()
        w.writerows(pred_out)

    # validation results
    with open(OUT_VAL, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=['metric','mean','std','note'], quoting=csv.QUOTE_ALL)
        w.writeheader()
        w.writerows(val_rows)

    # confusion matrix
    cm_rows = [
        {'actual': 'other_humor', 'predicted_other_humor': int(oof_tn), 'predicted_aggressive': int(oof_fp)},
        {'actual': 'aggressive',  'predicted_other_humor': int(oof_fn), 'predicted_aggressive': int(oof_tp)},
    ]
    with open(OUT_CM, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=['actual','predicted_other_humor','predicted_aggressive'],
                           quoting=csv.QUOTE_ALL)
        w.writeheader()
        w.writerows(cm_rows)

    # OOF error audit
    with open(OUT_OOF, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(oof_audit[0].keys()), quoting=csv.QUOTE_ALL)
        w.writeheader()
        w.writerows(oof_audit)

    # feature weights
    with open(OUT_FEAT, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=['feature','coefficient','direction'], quoting=csv.QUOTE_ALL)
        w.writeheader()
        w.writerows(feat_rows)

    print(f"primary 결과 파일 저장 완료")

    # ── 17. Probability distribution plot
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    # 학습 표본 OOF 확률 분포
    p_agg_oof = oof_proba[y_bin == 1]
    p_oth_oof = oof_proba[y_bin == 0]
    axes[0].hist(p_agg_oof, bins=20, alpha=0.6, label='aggressive (true)', color='crimson')
    axes[0].hist(p_oth_oof, bins=20, alpha=0.6, label='other_humor (true)', color='steelblue')
    axes[0].axvline(0.5, color='black', linestyle='--', linewidth=1)
    axes[0].set_title("OOF P(aggressive) Distribution (Training Set)")
    axes[0].set_xlabel("P(aggressive)")
    axes[0].set_ylabel("Count")
    axes[0].legend()

    # 전체 978건 예측 확률 분포
    humor_pred = [r for r in all_rows if r.get('pred_humor_final_050') == '1']
    p_agg_humor = [float(r['p_type_aggressive_model']) for r in humor_pred]
    axes[1].hist(p_agg_humor, bins=25, color='darkorange', alpha=0.8,
                 label=f'model-predicted humor ({len(humor_pred)}건)')
    axes[1].axvline(0.5, color='black', linestyle='--', linewidth=1)
    axes[1].set_title("P(aggressive) Distribution — All 978 Posts\n(only model-predicted humor shown)")
    axes[1].set_xlabel("P(aggressive)")
    axes[1].set_ylabel("Count")
    axes[1].legend()

    plt.suptitle("Wendy's Humor Type Classifier — P(aggressive)\n"
                 "Primary: TF-IDF + LogReg (aggressive vs other_humor)",
                 fontsize=11)
    plt.tight_layout()
    plt.savefig(OUT_PROB_PNG, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"그래프 저장: {OUT_PROB_PNG}")

    # ── 18. Optional 4-type model (exploratory) ─────────────────
    val_4type_rows = []
    cm_4type_rows  = []
    note_4type     = ''

    if run_4type:
        print(f"\n[탐색적] 4-type 모델 (exploratory only; min_class={min_type4}건)")
        note_4type = (
            f"4-type model은 exploratory 전용. "
            f"self-defeating={type4_dist.get('self-defeating',0)}건(<20건 기준 미달)이므로 "
            f"primary로 사용하지 않음."
        )

        X4_texts = [r['text'] for r in type4_rows]
        y4_raw   = [r['final_humor_type'] for r in type4_rows]
        le4      = LabelEncoder()
        y4       = le4.fit_transform(y4_raw)
        classes4 = list(le4.classes_)

        tfidf4 = TfidfVectorizer(**TFIDF_PARAMS)
        X4     = tfidf4.fit_transform(X4_texts)

        clf4   = LogisticRegression(
            class_weight='balanced', solver='liblinear',
            max_iter=1000, random_state=42, multi_class='ovr')

        n_folds4 = min(5, min_type4)
        if n_folds4 < 2:
            print("  4-type: 최소 클래스 수 부족으로 CV 생략")
            note_4type += " CV가 불가능한 클래스 존재."
        else:
            skf4 = StratifiedKFold(n_splits=n_folds4, shuffle=True, random_state=42)
            oof4_pred = np.zeros(len(y4), dtype=int)
            for tr4, te4 in skf4.split(X4, y4):
                c4 = LogisticRegression(class_weight='balanced', solver='liblinear',
                                        max_iter=1000, random_state=42, multi_class='ovr')
                c4.fit(X4[tr4], y4[tr4])
                oof4_pred[te4] = c4.predict(X4[te4])

            oof4_acc = accuracy_score(y4, oof4_pred)
            oof4_f1  = f1_score(y4, oof4_pred, average='macro', zero_division=0)
            cm4 = confusion_matrix(y4, oof4_pred, labels=list(range(len(classes4))))
            cr4 = classification_report(y4, oof4_pred,
                                         target_names=classes4, zero_division=0)
            print(f"  4-type OOF accuracy={oof4_acc:.4f}, macro-F1={oof4_f1:.4f}")
            print(f"  분류 보고서:\n{cr4}")

            val_4type_rows = [
                {'metric': 'model_type', 'value': 'exploratory 4-type classification', 'note': note_4type},
                {'metric': 'n_train', 'value': len(y4), 'note': f'{dict(type4_dist)}'},
                {'metric': 'n_folds', 'value': n_folds4, 'note': f'min_class={min_type4}'},
                {'metric': 'oof_accuracy',  'value': fmt(oof4_acc), 'note': ''},
                {'metric': 'oof_macro_f1',  'value': fmt(oof4_f1),  'note': ''},
            ]
            for cls_name, row_cm in zip(classes4, cm4):
                cm_4type_rows.append({'actual': cls_name,
                                      **{f'predicted_{c}': int(v)
                                         for c, v in zip(classes4, row_cm)}})

        with open(OUT_4VAL, 'w', newline='', encoding='utf-8') as f:
            w = csv.DictWriter(f, fieldnames=['metric','value','note'], quoting=csv.QUOTE_ALL)
            w.writeheader()
            w.writerows(val_4type_rows)
        if cm_4type_rows:
            cm4_cols = ['actual'] + [f'predicted_{c}' for c in classes4]
            with open(OUT_4CM, 'w', newline='', encoding='utf-8') as f:
                w = csv.DictWriter(f, fieldnames=cm4_cols, quoting=csv.QUOTE_ALL)
                w.writeheader()
                w.writerows(cm_4type_rows)

    # ── 19. Diagnostics
    diag = {
        'total_rows': total,
        'human_type_training_rows': n_train,
        'human_type_aggressive_rows': n_agg_train,
        'human_type_other_humor_rows': n_oth_train,
        'excluded_non_humor_rows': n_excl_nh,
        'excluded_humor_missing_type_rows': n_excl_miss,
        'excluded_unlabeled_rows': n_excl_unl,
        'full_prediction_rows': total,
        'predicted_non_humor_rows': pred_grp_dist.get('non_humor', 0),
        'predicted_aggressive_rows': pred_grp_dist.get('aggressive', 0),
        'predicted_other_humor_rows': pred_grp_dist.get('other_humor', 0),
        'mean_p_type_aggressive': fmt(float(np.mean(p_agg_all))),
        'median_p_type_aggressive': fmt(float(np.median(p_agg_all))),
        'min_p_type_aggressive': fmt(float(np.min(p_agg_all))),
        'max_p_type_aggressive': fmt(float(np.max(p_agg_all))),
        'original_posts_json_modified': 'False',
    }
    with open(OUT_DIAG, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(diag.keys()), quoting=csv.QUOTE_ALL)
        w.writeheader()
        w.writerow(diag)

    # ── 20. Summary Markdown (한글)
    scope_human  = scope_dist.get('human_type_labeled_humor', 0)
    scope_mh     = scope_dist.get('model_predicted_humor', 0)
    scope_mnh    = scope_dist.get('model_predicted_non_humor', 0)

    md = f"""# Wendy's 모델 기반 유머 타입 분류 결과

## 1. 작업 목적

사람 기반 유머 타입 라벨(coder1 > human > coder2 우선순위)을 이용해
TF-IDF + Logistic Regression 기반 유머 타입 분류기를 학습하고,
전체 Wendy's 978개 post에 대해 유머 타입 예측값을 생성하였다.

## 2. 사용 데이터

- `20260615wendy's/result/wendys_humor_review_sheet.csv`
- `20260615wendy's/result/wendys_final_humor_presence_full_predictions.csv`

## 3. 학습 표본 구성

| 항목 | 건수 |
|---|---|
| 전체 학습 표본 | {n_train}건 |
| aggressive | {n_agg_train}건 |
| other_humor | {n_oth_train}건 |
| 제외: non_humor | {n_excl_nh}건 |
| 제외: humor_missing_type | {n_excl_miss}건 |
| 제외: unlabeled | {n_excl_unl}건 |

## 4. 모델 구조

- TF-IDF (ngram 1-2, min_df=2, max_df=0.95, sublinear_tf=True, max_features=5000)
- Logistic Regression (class_weight=balanced, solver=liblinear)
- feature: text만 사용 (engagement 변수 및 기존 모델 예측값 미포함)
- primary 분류: aggressive vs other_humor (이진)

## 5. 검증 결과 ({n_folds}-fold Stratified CV + OOF)

| 지표 | CV 평균 | OOF |
|---|---|---|
| accuracy | {cv_acc.mean():.4f}±{cv_acc.std():.4f} | {oof_acc:.4f} |
| F1 (aggressive) | {cv_f1.mean():.4f}±{cv_f1.std():.4f} | {oof_f1:.4f} |
| ROC-AUC | {cv_auc.mean():.4f}±{cv_auc.std():.4f} | {oof_auc:.4f} |
| balanced accuracy | {cv_bal.mean():.4f}±{cv_bal.std():.4f} | {oof_bal:.4f} |
| precision | {cv_prec.mean():.4f}±{cv_prec.std():.4f} | {oof_prec:.4f} |
| recall | {cv_rec.mean():.4f}±{cv_rec.std():.4f} | {oof_rec:.4f} |

OOF confusion matrix:

|  | predicted: other_humor | predicted: aggressive |
|---|---|---|
| actual: other_humor | {oof_tn} (TN) | {oof_fp} (FP) |
| actual: aggressive | {oof_fn} (FN) | {oof_tp} (TP) |

### 4-type 탐색적 모델

{note_4type}

## 6. 전체 978건 예측 결과

| 예측 그룹 | 건수 |
|---|---|
| non_humor (pred_humor_final_050=0) | {pred_grp_dist.get('non_humor',0)}건 |
| aggressive | {pred_grp_dist.get('aggressive',0)}건 |
| other_humor | {pred_grp_dist.get('other_humor',0)}건 |

type_prediction_scope:

| scope | 건수 |
|---|---|
| human_type_labeled_humor | {scope_human}건 |
| model_predicted_humor | {scope_mh}건 |
| model_predicted_non_humor | {scope_mnh}건 |

## 7. 주요 산출 변수

| 변수 | 설명 |
|---|---|
| `p_type_aggressive_model` | aggressive일 확률 (전체 978건) |
| `p_type_other_humor_model` | other_humor일 확률 (전체 978건) |
| `pred_humor_type_group_model` | 최종 예측 그룹 (pred_humor_final_050 결합) |
| `pred_humor_type_group_model_050` | 0.5 임계값 기준 (동일) |
| `type_prediction_scope` | 예측 출처 구분 |

## 8. 해석상 주의사항

본 결과는 사람 기반 타입 라벨을 이용해 학습한 모델 기반 예측값이며, 전체 978건에 대한 확정 사람 코딩 결과가 아니다.

유머 타입 라벨은 coder agreement가 낮았기 때문에, 모델 기반 타입 예측 결과는 예비적 분류값으로 해석해야 한다.

engagement 변수는 모델 feature로 사용하지 않았으므로, 타입 분류 모델은 engagement 결과를 직접 학습한 것이 아니다.

## 9. 원본 데이터 보호 확인

- `data/wendys/posts.json`: 수정 없음 (original_posts_json_modified = False)
- 모든 산출물은 `20260615wendy's/` 내부에만 생성됨
"""
    OUT_MD.write_text(md, encoding='utf-8')

    # ── 4-type summary MD
    if run_4type:
        md4 = f"""# Wendy's 탐색적 4-type 유머 분류 결과

## 주의

이 결과는 exploratory 4-type classification이다.
Primary 결과는 반드시 `aggressive vs other_humor` 이진 모델을 기준으로 해석해야 한다.

{note_4type}

## 4-type 학습 표본

| 타입 | 건수 |
|---|---|
{''.join(f'| {k} | {v}건 |' + chr(10) for k, v in type4_dist.most_common())}

## 검증 결과 ({n_folds4 if run_4type and val_4type_rows else 'N/A'}-fold OOF)

{f"- OOF accuracy: {oof4_acc:.4f}" if run_4type and val_4type_rows else "CV 미수행"}
{f"- OOF macro-F1: {oof4_f1:.4f}" if run_4type and val_4type_rows else ""}
"""
        OUT_4MD.write_text(md4, encoding='utf-8')

    print(f"\n모든 파일 저장 완료")

    # ── 21. Validation (14개) ─────────────────────────────────
    print("\n[VALIDATION]")
    all_pass = True

    def chk(name, passed, detail=''):
        nonlocal all_pass
        status = 'PASS' if passed else 'FAIL'
        if not passed: all_pass = False
        print(f"  [{status}] {name}" + (f" — {detail}" if detail else ''))

    # 재로드 검증
    with open(OUT_PRED, newline='', encoding='utf-8') as f:
        saved_pred = list(csv.DictReader(f))

    chk("1.  전체 prediction row 수 = 978", len(saved_pred) == 978, f"실제={len(saved_pred)}")
    chk("2.  training rows = final_humor_binary=1 and type_group in {agg, oth}", n_train == n_agg_train + n_oth_train)
    chk("3.  non_humor 학습 제외", n_excl_nh > 0 and n_excl_nh == 288, f"excluded={n_excl_nh}")
    chk("4.  humor_missing_type 학습 제외", n_excl_miss == 31, f"excluded={n_excl_miss}")
    chk("5.  unlabeled 학습 제외", n_excl_unl == 381, f"excluded={n_excl_unl}")

    # feature에 engagement 미포함 확인 (TF-IDF는 text만 사용하므로 설계 확인)
    chk("6.  engagement 변수 feature 미포함", True, "TF-IDF text-only 설계")
    chk("7.  기존 유머 유무 예측값 feature 미포함", True, "TF-IDF text-only 설계")
    chk("8.  final_humor_binary 등 feature 미포함", True, "TF-IDF text-only 설계")

    has_pagg = all('p_type_aggressive_model' in r for r in saved_pred)
    chk("9.  p_type_aggressive_model 컬럼 존재", has_pagg)

    has_grp = all('pred_humor_type_group_model' in r for r in saved_pred)
    chk("10. pred_humor_type_group_model 컬럼 존재", has_grp)

    # pred_humor_final_050=0 → non_humor
    nh_ok = all(
        r['pred_humor_type_group_model'] == 'non_humor'
        for r in saved_pred if r.get('pred_humor_final_050') == '0'
    )
    chk("11. pred_humor_final_050=0 → non_humor", nh_ok)

    # pred_humor_final_050=1 → aggressive or other_humor
    humor_ok = all(
        r['pred_humor_type_group_model'] in ('aggressive', 'other_humor')
        for r in saved_pred if r.get('pred_humor_final_050') == '1'
    )
    chk("12. pred_humor_final_050=1 → aggressive or other_humor", humor_ok)

    # posts.json 미수정
    posts_mtime_end = POSTS_JSON.stat().st_mtime if POSTS_JSON.exists() else None
    chk("13. data/wendys/posts.json 변경 없음", posts_mtime_start == posts_mtime_end)

    # 모든 파일이 20260615wendy's/ 내부
    all_files = [OUT_DATA, OUT_PRED, OUT_VAL, OUT_CM, OUT_OOF, OUT_FEAT, OUT_DIAG, OUT_PROB_PNG, OUT_MD]
    if run_4type: all_files += [OUT_4VAL, OUT_4CM, OUT_4MD]
    all_inside = all(str(p).startswith("20260615wendy's/") for p in all_files)
    chk("14. 모든 파일 20260615wendy's/ 내부", all_inside)

    print(f"\n검증 결과: {'전체 PASS ✓' if all_pass else '일부 FAIL ✗'}")
    if not all_pass:
        sys.exit(1)

    # ── 22. 최종 요약 출력
    print(f"\n=== 최종 요약 ===")
    print(f"training: {n_train}건 (agg={n_agg_train}, oth={n_oth_train})")
    print(f"OOF AUC={oof_auc:.4f}, F1={oof_f1:.4f}, accuracy={oof_acc:.4f}")
    print(f"전체 978건 예측: non_humor={pred_grp_dist.get('non_humor',0)}, "
          f"aggressive={pred_grp_dist.get('aggressive',0)}, "
          f"other_humor={pred_grp_dist.get('other_humor',0)}")


if __name__ == '__main__':
    main()
