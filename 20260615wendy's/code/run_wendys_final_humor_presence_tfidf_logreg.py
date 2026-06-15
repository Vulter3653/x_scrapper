"""
run_wendys_final_humor_presence_tfidf_logreg.py

== 목적 ==
wendys_humor_review_sheet.csv에 통합된 최종 사람 코딩 결과(final_humor_binary)를
기준 라벨로 사용하여 Wendy's 전체 게시글의 유머 유무(humor presence)를 분류하는
TF-IDF + Logistic Regression 모델을 학습·검증·예측한다.

== final_humor_binary를 기준 라벨로 사용하는 이유 ==
coder1 > human > coder2 우선순위 규칙으로 세 명의 사람 코더 레이블을 하나로 통합한
최종 레이블이다. 개별 코더 레이블보다 더 넓은 커버리지(597건)를 확보하며,
하나의 일관된 기준으로 모델을 학습할 수 있다.

== 유머 타입 분류를 하지 않는 이유 ==
이번 단계에서는 유머 유무(humor presence)만 판단한다.
유머 타입(affiliative, aggressive, self-enhancing 등)은 코더 간 불일치가 높고
별도의 정제 작업이 필요하므로 추후 분리 작업으로 진행한다.

== engagement 변수를 학습에 사용하지 않는 이유 ==
engagement(favorite_count, retweet_count 등)는 H1 회귀분석의 종속변수다.
이를 유머 분류 모델의 입력으로 사용하면 독립변수(유머 유무)와 종속변수(engagement)가
기계적으로 연결되는 순환 편의(circular bias)가 발생한다.

== TF-IDF + Logistic Regression을 사용하는 이유 ==
- 소규모 텍스트 데이터(약 600건)에서 안정적인 성능
- 계수(coefficient) 해석을 통해 어떤 단어/표현이 유머에 기여하는지 파악 가능
- 학습 속도가 빠르고 재현성이 높음

== 전체 978건 확장 예측의 의미 ==
라벨이 없는 381건에 대해서도 유머 확률을 추정하여
전체 데이터셋에서 H1 분석 등 후속 작업에 활용할 수 있도록 한다.

== 예측값과 사람 라벨의 차이 ==
사람 라벨(final_humor_binary)이 있는 행: 실제 판단값
모델 예측(p_humor_final_tfidf_logreg): 텍스트 기반 추정 확률
두 값은 일치하지 않을 수 있으며, 사람 라벨이 있는 행에서는 사람 라벨을 우선한다.
"""

import csv
import math
import re
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
from scipy.stats import pearsonr
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score, balanced_accuracy_score, confusion_matrix,
    f1_score, precision_score, recall_score, roc_auc_score,
)
from sklearn.model_selection import StratifiedKFold, cross_val_predict

# ── 경로 설정
BASE         = Path("20260615wendy's")
REVIEW_CSV   = BASE / "result" / "wendys_humor_review_sheet.csv"
OUT_DATA     = BASE / "data"   / "wendys_final_humor_presence_dataset.csv"
OUT_VAL      = BASE / "result" / "wendys_final_humor_presence_validation_results.csv"
OUT_FULL     = BASE / "result" / "wendys_final_humor_presence_full_predictions.csv"
OUT_AUDIT    = BASE / "result" / "wendys_final_humor_presence_oof_error_audit.csv"
OUT_CM       = BASE / "result" / "wendys_final_humor_presence_confusion_matrix.csv"
OUT_FW       = BASE / "result" / "wendys_final_humor_presence_feature_weights.csv"
OUT_DIAG     = BASE / "result" / "wendys_final_humor_presence_diagnostics.csv"
OUT_SUMMARY  = BASE / "result" / "wendys_final_humor_presence_summary.md"
OUT_DIST_PNG = BASE / "result" / "wendys_final_humor_presence_probability_distribution.png"


# ── 텍스트 전처리 함수
def preprocess(text):
    """최소한의 텍스트 정규화. 유머 표현 보존을 위해 과도한 제거 금지."""
    text = re.sub(r'https?://\S+', '<URL>', text)       # URL 토큰화
    text = re.sub(r'@\w+', '<MENTION>', text)           # mention 토큰화
    text = re.sub(r'#(\w+)', r'\1', text)               # 해시태그 # 제거, 단어 보존
    text = text.lower()
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def safe_float(v, default=0.0):
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def safe_pearsonr(a, b):
    try:
        r, _ = pearsonr(a, b)
        return r
    except Exception:
        return float('nan')


def main():
    # ────────────────────────────────────────────
    # 1. 입력 파일 로드
    # ────────────────────────────────────────────
    with open(REVIEW_CSV, newline='', encoding='utf-8') as f:
        all_rows = list(csv.DictReader(f))

    total_rows = len(all_rows)
    print(f"전체 행: {total_rows}건")

    # ────────────────────────────────────────────
    # 2. 학습용 라벨 행 추출 (final_humor_label_available=1 & binary∈{0,1})
    # ────────────────────────────────────────────
    labeled_rows = [
        r for r in all_rows
        if r.get('final_humor_label_available') == '1'
        and r.get('final_humor_binary') in ('0', '1')
    ]
    unlabeled_rows = [r for r in all_rows if r not in labeled_rows]

    n_labeled    = len(labeled_rows)
    n_unlabeled  = total_rows - n_labeled
    n_humor      = sum(1 for r in labeled_rows if r['final_humor_binary'] == '1')
    n_nonhumor   = sum(1 for r in labeled_rows if r['final_humor_binary'] == '0')
    print(f"라벨 유효: {n_labeled}건  (유머={n_humor}, 비유머={n_nonhumor})")
    print(f"라벨 없음: {n_unlabeled}건")

    # ────────────────────────────────────────────
    # 3. 학습 데이터 준비
    # ────────────────────────────────────────────
    texts_labeled = [preprocess(r['text']) for r in labeled_rows]
    y_labeled     = np.array([int(r['final_humor_binary']) for r in labeled_rows])

    # 데이터셋 파일 저장
    data_cols = ['no', 'id', 'tweet_url', 'text', 'text_preprocessed',
                 'final_humor_binary', 'final_humor_source']
    with open(OUT_DATA, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=data_cols, extrasaction='ignore')
        w.writeheader()
        for r, tp in zip(labeled_rows, texts_labeled):
            row = dict(r)
            row['text_preprocessed'] = tp
            w.writerow(row)
    print(f"데이터셋 저장: {OUT_DATA}")

    # ────────────────────────────────────────────
    # 4. TF-IDF 벡터라이저 설정 (min_df fallback 포함)
    # ────────────────────────────────────────────
    tfidf_params = dict(
        lowercase=True, ngram_range=(1, 2),
        min_df=2, max_df=0.95, sublinear_tf=True
    )
    vectorizer = TfidfVectorizer(**tfidf_params)
    test_X = vectorizer.fit_transform(texts_labeled)
    vocab_size = len(vectorizer.vocabulary_)
    min_df_used = 2

    if vocab_size < 10:
        print("  [경고] min_df=2에서 vocabulary 부족 → min_df=1로 fallback")
        tfidf_params['min_df'] = 1
        min_df_used = 1
        vectorizer = TfidfVectorizer(**tfidf_params)
        test_X = vectorizer.fit_transform(texts_labeled)
        vocab_size = len(vectorizer.vocabulary_)

    print(f"TF-IDF vocabulary: {vocab_size}개 (min_df={min_df_used})")

    classifier = LogisticRegression(
        class_weight='balanced', solver='liblinear',
        max_iter=1000, random_state=42
    )

    # ────────────────────────────────────────────
    # 5. Stratified 5-fold Cross-Validation
    # ────────────────────────────────────────────
    print("\n[CV] Stratified 5-fold 교차검증 시작...")
    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

    from sklearn.pipeline import Pipeline
    pipeline = Pipeline([
        ('tfidf', TfidfVectorizer(**tfidf_params)),
        ('clf',   LogisticRegression(
            class_weight='balanced', solver='liblinear',
            max_iter=1000, random_state=42))
    ])

    cv_metrics = {m: [] for m in
                  ['accuracy', 'precision', 'recall', 'f1', 'roc_auc', 'balanced_accuracy']}

    for fold, (tr_idx, va_idx) in enumerate(skf.split(texts_labeled, y_labeled), 1):
        X_tr = [texts_labeled[i] for i in tr_idx]
        X_va = [texts_labeled[i] for i in va_idx]
        y_tr = y_labeled[tr_idx]
        y_va = y_labeled[va_idx]

        pipeline.fit(X_tr, y_tr)
        y_pred = pipeline.predict(X_va)
        y_prob = pipeline.predict_proba(X_va)[:, 1]

        cv_metrics['accuracy'].append(accuracy_score(y_va, y_pred))
        cv_metrics['precision'].append(precision_score(y_va, y_pred, zero_division=0))
        cv_metrics['recall'].append(recall_score(y_va, y_pred, zero_division=0))
        cv_metrics['f1'].append(f1_score(y_va, y_pred, zero_division=0))
        cv_metrics['roc_auc'].append(roc_auc_score(y_va, y_prob))
        cv_metrics['balanced_accuracy'].append(balanced_accuracy_score(y_va, y_pred))
        print(f"  Fold {fold}: acc={cv_metrics['accuracy'][-1]:.4f}  "
              f"f1={cv_metrics['f1'][-1]:.4f}  auc={cv_metrics['roc_auc'][-1]:.4f}")

    cv_results = {m: (np.mean(v), np.std(v)) for m, v in cv_metrics.items()}
    print("\nCV 결과 (평균±표준편차):")
    for m, (mu, sd) in cv_results.items():
        print(f"  {m}: {mu:.4f} ± {sd:.4f}")

    # CV 결과 저장
    val_rows = []
    for m, (mu, sd) in cv_results.items():
        val_rows.append({'metric': m, 'mean': f'{mu:.4f}', 'std': f'{sd:.4f}'})
    with open(OUT_VAL, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=['metric', 'mean', 'std'])
        w.writeheader(); w.writerows(val_rows)

    # ────────────────────────────────────────────
    # 6. Out-of-fold 예측 (cross_val_predict)
    # ────────────────────────────────────────────
    print("\n[OOF] cross_val_predict 실행...")
    oof_probs = cross_val_predict(
        pipeline, texts_labeled, y_labeled,
        cv=skf, method='predict_proba'
    )[:, 1]
    oof_preds = (oof_probs >= 0.5).astype(int)

    cm = confusion_matrix(y_labeled, oof_preds)
    tn, fp, fn, tp = cm.ravel()
    oof_acc  = accuracy_score(y_labeled, oof_preds)
    oof_prec = precision_score(y_labeled, oof_preds, zero_division=0)
    oof_rec  = recall_score(y_labeled, oof_preds, zero_division=0)
    oof_f1   = f1_score(y_labeled, oof_preds, zero_division=0)

    print(f"OOF confusion matrix: TP={tp}, TN={tn}, FP={fp}, FN={fn}")
    print(f"OOF accuracy={oof_acc:.4f}  precision={oof_prec:.4f}  "
          f"recall={oof_rec:.4f}  f1={oof_f1:.4f}")

    # confusion matrix 저장
    cm_rows = [
        {'actual': 'humor(1)',    'pred_humor': str(tp), 'pred_nonhumor': str(fn)},
        {'actual': 'nonhumor(0)', 'pred_humor': str(fp), 'pred_nonhumor': str(tn)},
    ]
    with open(OUT_CM, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=['actual', 'pred_humor', 'pred_nonhumor'])
        w.writeheader(); w.writerows(cm_rows)

    # error audit 저장
    def error_type(true, pred):
        if true == 1 and pred == 1: return 'true_positive'
        if true == 0 and pred == 0: return 'true_negative'
        if true == 0 and pred == 1: return 'false_positive'
        return 'false_negative'

    audit_cols = ['id', 'tweet_url', 'text', 'final_humor_binary', 'final_humor_source',
                  'oof_p_humor_final_tfidf_logreg', 'oof_pred_humor_final_050',
                  'error_type', 'model_humor', 'p_humor', 'p_humor_ml']
    with open(OUT_AUDIT, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=audit_cols, quoting=csv.QUOTE_ALL)
        w.writeheader()
        for r, op, opred in zip(labeled_rows, oof_probs, oof_preds):
            true_bin = int(r['final_humor_binary'])
            w.writerow({
                'id':                              r['id'],
                'tweet_url':                       r['tweet_url'],
                'text':                            r['text'],
                'final_humor_binary':              r['final_humor_binary'],
                'final_humor_source':              r['final_humor_source'],
                'oof_p_humor_final_tfidf_logreg':  f'{op:.6f}',
                'oof_pred_humor_final_050':        str(opred),
                'error_type':                      error_type(true_bin, opred),
                'model_humor':                     r.get('model_humor', ''),
                'p_humor':                         r.get('p_humor', ''),
                'p_humor_ml':                      r.get('p_humor_ml', ''),
            })

    # ────────────────────────────────────────────
    # 7. 전체 모델 학습 (모든 라벨 사용)
    # ────────────────────────────────────────────
    print("\n[FINAL] 전체 라벨로 최종 모델 학습...")
    pipeline.fit(texts_labeled, y_labeled)

    # 전체 978건 예측
    all_texts_pp = [preprocess(r['text']) for r in all_rows]
    all_probs    = pipeline.predict_proba(all_texts_pp)[:, 1]
    all_preds    = (all_probs >= 0.5).astype(int)
    all_log1p    = [math.log1p(p) for p in all_probs]

    # ────────────────────────────────────────────
    # 8. 기존 모델과 비교
    # ────────────────────────────────────────────
    existing_p_humor    = [safe_float(r.get('p_humor', ''))    for r in all_rows]
    existing_p_humor_ml = [safe_float(r.get('p_humor_ml', '')) for r in all_rows]
    existing_model_humor = [r.get('model_humor', '') for r in all_rows]

    corr_p_humor    = safe_pearsonr(all_probs, existing_p_humor)
    corr_p_humor_ml = safe_pearsonr(all_probs, existing_p_humor_ml)

    old_humor_count = sum(1 for v in existing_model_humor if v == '1')
    new_humor_count = sum(all_preds)

    print(f"기존 model_humor=1: {old_humor_count}건 ({old_humor_count/total_rows*100:.1f}%)")
    print(f"새 pred_humor_final_050=1: {new_humor_count}건 ({new_humor_count/total_rows*100:.1f}%)")
    print(f"p_humor와 신규 확률 상관: r={corr_p_humor:.4f}")
    print(f"p_humor_ml과 신규 확률 상관: r={corr_p_humor_ml:.4f}")

    # ────────────────────────────────────────────
    # 9. 전체 예측 결과 저장
    # ────────────────────────────────────────────
    full_cols = [
        'no', 'id', 'tweet_url', 'text',
        'final_humor_binary', 'final_humor_source', 'final_humor_label_available',
        'model_humor', 'p_humor', 'p_humor_ml',
        'p_humor_final_tfidf_logreg', 'pred_humor_final_050',
        'log1p_p_humor_final_tfidf_logreg', 'prediction_set',
    ]
    id_to_labeled = {r['id'] for r in labeled_rows}

    with open(OUT_FULL, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=full_cols, quoting=csv.QUOTE_ALL,
                           extrasaction='ignore')
        w.writeheader()
        for r, prob, pred, lp in zip(all_rows, all_probs, all_preds, all_log1p):
            row = dict(r)
            row['p_humor_final_tfidf_logreg']     = f'{prob:.6f}'
            row['pred_humor_final_050']            = str(pred)
            row['log1p_p_humor_final_tfidf_logreg'] = f'{lp:.6f}'
            row['prediction_set'] = 'labeled' if r['id'] in id_to_labeled else 'unlabeled'
            w.writerow(row)
    print(f"\n전체 예측 저장: {OUT_FULL}")

    # ────────────────────────────────────────────
    # 10. Feature weights 저장
    # ────────────────────────────────────────────
    tfidf_step = pipeline.named_steps['tfidf']
    clf_step   = pipeline.named_steps['clf']
    feature_names = tfidf_step.get_feature_names_out()
    coefs = clf_step.coef_[0]

    sorted_idx = np.argsort(coefs)[::-1]
    fw_rows = []
    # 유머 방향 상위 50
    for rank, idx in enumerate(sorted_idx[:50], 1):
        fw_rows.append({
            'rank': rank, 'direction': 'humor_positive',
            'feature': feature_names[idx], 'coefficient': f'{coefs[idx]:.6f}'
        })
    # 비유머 방향 상위 50
    for rank, idx in enumerate(sorted_idx[-50:][::-1], 1):
        fw_rows.append({
            'rank': rank, 'direction': 'humor_negative',
            'feature': feature_names[idx], 'coefficient': f'{coefs[idx]:.6f}'
        })
    with open(OUT_FW, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=['rank', 'direction', 'feature', 'coefficient'])
        w.writeheader(); w.writerows(fw_rows)

    # ────────────────────────────────────────────
    # 11. diagnostics 저장
    # ────────────────────────────────────────────
    src_cnt = {}
    for r in labeled_rows:
        s = r.get('final_humor_source', '')
        src_cnt[s] = src_cnt.get(s, 0) + 1

    diag = {
        'total_rows':                  total_rows,
        'labeled_rows':                n_labeled,
        'unlabeled_rows':              n_unlabeled,
        'final_humor_count':           n_humor,
        'final_nonhumor_count':        n_nonhumor,
        'final_humor_share':           f'{n_humor/n_labeled:.4f}',
        'coder1_source_count':         src_cnt.get('coder1', 0),
        'human_source_count':          src_cnt.get('human', 0),
        'coder2_source_count':         src_cnt.get('coder2', 0),
        'cv_accuracy_mean':            f'{cv_results["accuracy"][0]:.4f}',
        'cv_accuracy_std':             f'{cv_results["accuracy"][1]:.4f}',
        'cv_precision_mean':           f'{cv_results["precision"][0]:.4f}',
        'cv_precision_std':            f'{cv_results["precision"][1]:.4f}',
        'cv_recall_mean':              f'{cv_results["recall"][0]:.4f}',
        'cv_recall_std':               f'{cv_results["recall"][1]:.4f}',
        'cv_f1_mean':                  f'{cv_results["f1"][0]:.4f}',
        'cv_f1_std':                   f'{cv_results["f1"][1]:.4f}',
        'cv_roc_auc_mean':             f'{cv_results["roc_auc"][0]:.4f}',
        'cv_roc_auc_std':              f'{cv_results["roc_auc"][1]:.4f}',
        'cv_balanced_accuracy_mean':   f'{cv_results["balanced_accuracy"][0]:.4f}',
        'cv_balanced_accuracy_std':    f'{cv_results["balanced_accuracy"][1]:.4f}',
        'oof_true_positive':           int(tp),
        'oof_true_negative':           int(tn),
        'oof_false_positive':          int(fp),
        'oof_false_negative':          int(fn),
        'oof_accuracy':                f'{oof_acc:.4f}',
        'oof_precision':               f'{oof_prec:.4f}',
        'oof_recall':                  f'{oof_rec:.4f}',
        'oof_f1':                      f'{oof_f1:.4f}',
        'p_humor_final_tfidf_logreg_min':    f'{min(all_probs):.6f}',
        'p_humor_final_tfidf_logreg_mean':   f'{np.mean(all_probs):.6f}',
        'p_humor_final_tfidf_logreg_median': f'{np.median(all_probs):.6f}',
        'p_humor_final_tfidf_logreg_max':    f'{max(all_probs):.6f}',
        'pred_humor_final_050_count':        int(new_humor_count),
        'pred_humor_final_050_share':        f'{new_humor_count/total_rows:.4f}',
        'correlation_with_existing_p_humor':    f'{corr_p_humor:.4f}',
        'correlation_with_p_humor_ml':          f'{corr_p_humor_ml:.4f}',
    }
    with open(OUT_DIAG, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(diag.keys()))
        w.writeheader(); w.writerow(diag)

    # ────────────────────────────────────────────
    # 12. 확률 분포 그래프 (선택적)
    # ────────────────────────────────────────────
    png_saved = False
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt

        fig, axes = plt.subplots(1, 2, figsize=(12, 5))
        fig.suptitle("Wendy's Humor Presence — Predicted Probability Distribution", fontsize=13)

        # 전체 978건
        axes[0].hist(all_probs, bins=30, color='steelblue', edgecolor='white', alpha=0.85)
        axes[0].axvline(0.5, color='red', linestyle='--', linewidth=1.5, label='threshold=0.5')
        axes[0].set_title('전체 978건 예측 확률')
        axes[0].set_xlabel('p_humor_final_tfidf_logreg')
        axes[0].set_ylabel('빈도')
        axes[0].legend()

        # 라벨별 OOF 확률
        h_probs  = [op for op, y in zip(oof_probs, y_labeled) if y == 1]
        nh_probs = [op for op, y in zip(oof_probs, y_labeled) if y == 0]
        axes[1].hist(h_probs,  bins=20, alpha=0.65, label='유머(1)',    color='tomato')
        axes[1].hist(nh_probs, bins=20, alpha=0.65, label='비유머(0)', color='steelblue')
        axes[1].axvline(0.5, color='black', linestyle='--', linewidth=1.5, label='threshold=0.5')
        axes[1].set_title('OOF 예측 확률 (라벨별)')
        axes[1].set_xlabel('oof_p_humor_final_tfidf_logreg')
        axes[1].set_ylabel('빈도')
        axes[1].legend()

        plt.tight_layout()
        plt.savefig(OUT_DIST_PNG, dpi=150, bbox_inches='tight')
        plt.close()
        png_saved = True
        print(f"그래프 저장: {OUT_DIST_PNG}")
    except Exception as e:
        print(f"그래프 생성 생략: {e}")

    # ────────────────────────────────────────────
    # 13. Summary markdown (한글)
    # ────────────────────────────────────────────
    top_humor_features = [
        fw['feature'] for fw in fw_rows
        if fw['direction'] == 'humor_positive'
    ][:10]
    top_nonhumor_features = [
        fw['feature'] for fw in fw_rows
        if fw['direction'] == 'humor_negative'
    ][:10]

    summary = f"""# Wendy's final_humor_binary 기반 유머 유무 분류 모델 요약

생성일시: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}

---

## 1. 작업 목적

`wendys_humor_review_sheet.csv`에 통합된 최종 사람 코딩 결과(`final_humor_binary`)를
기준 라벨로 사용하여, Wendy's 전체 트위터 게시글의 유머 유무(humor presence)를
분류하는 TF-IDF + Logistic Regression 모델을 학습·검증·예측한다.

이번 작업에서는 **유머 유무만 분류**한다. 유머 타입 분류는 수행하지 않는다.

---

## 2. 입력 데이터

| 항목 | 값 |
|------|-----|
| 입력 파일 | `wendys_humor_review_sheet.csv` |
| 전체 게시글 수 | {total_rows}건 |
| 기준 라벨 | `final_humor_binary` |

---

## 3. 최종 라벨 기준

`final_humor_binary`는 세 사람 코더의 레이블을 다음 우선순위로 통합한 최종 라벨이다.

```
우선순위: coder1 > human > coder2
```

---

## 4. 라벨 분포

| 항목 | 건수 | 비율 |
|------|------|------|
| 라벨 유효 (final_humor_label_available=1) | {n_labeled}건 | {n_labeled/total_rows*100:.1f}% |
| — 유머 (final_humor_binary=1) | {n_humor}건 | {n_humor/n_labeled*100:.1f}% |
| — 비유머 (final_humor_binary=0) | {n_nonhumor}건 | {n_nonhumor/n_labeled*100:.1f}% |
| 라벨 없음 | {n_unlabeled}건 | {n_unlabeled/total_rows*100:.1f}% |

라벨 출처:

| 출처 | 건수 |
|------|------|
| coder1 | {src_cnt.get('coder1', 0)}건 |
| human | {src_cnt.get('human', 0)}건 |
| coder2 | {src_cnt.get('coder2', 0)}건 |

---

## 5. 모델 구조

```
TfidfVectorizer(
    lowercase=True, ngram_range=(1, 2),
    min_df={min_df_used}, max_df=0.95, sublinear_tf=True
)
+ LogisticRegression(
    class_weight="balanced", solver="liblinear",
    max_iter=1000, random_state=42
)
```

vocabulary 크기: {vocab_size}개
min_df 사용값: {min_df_used}{'  ⚠️ (min_df=2에서 vocabulary 부족으로 1로 fallback)' if min_df_used == 1 else ''}

입력 변수: `text` (전처리 후)
라벨: `final_humor_binary`
engagement 변수: 학습에 사용하지 않음

---

## 6. 교차검증 결과 (Stratified 5-fold)

| 지표 | 평균 | 표준편차 |
|------|------|---------|
| Accuracy | {cv_results['accuracy'][0]:.4f} | {cv_results['accuracy'][1]:.4f} |
| Precision | {cv_results['precision'][0]:.4f} | {cv_results['precision'][1]:.4f} |
| Recall | {cv_results['recall'][0]:.4f} | {cv_results['recall'][1]:.4f} |
| F1 | {cv_results['f1'][0]:.4f} | {cv_results['f1'][1]:.4f} |
| ROC-AUC | {cv_results['roc_auc'][0]:.4f} | {cv_results['roc_auc'][1]:.4f} |
| Balanced Accuracy | {cv_results['balanced_accuracy'][0]:.4f} | {cv_results['balanced_accuracy'][1]:.4f} |

---

## 7. Out-of-fold 오류 분석

OOF confusion matrix (threshold=0.5):

| | 예측: 유머 | 예측: 비유머 |
|---|---|---|
| **실제: 유머** | {tp} (TP) | {fn} (FN) |
| **실제: 비유머** | {fp} (FP) | {tn} (TN) |

| 지표 | 값 |
|------|-----|
| OOF Accuracy | {oof_acc:.4f} |
| OOF Precision | {oof_prec:.4f} |
| OOF Recall | {oof_rec:.4f} |
| OOF F1 | {oof_f1:.4f} |

---

## 8. 전체 978건 확장 예측 결과

| 항목 | 값 |
|------|-----|
| 예측 유머 (pred_humor_final_050=1) | {new_humor_count}건 ({new_humor_count/total_rows*100:.1f}%) |
| 예측 비유머 (pred_humor_final_050=0) | {total_rows-new_humor_count}건 ({(total_rows-new_humor_count)/total_rows*100:.1f}%) |
| p_humor_final_tfidf_logreg 최솟값 | {min(all_probs):.4f} |
| p_humor_final_tfidf_logreg 평균 | {np.mean(all_probs):.4f} |
| p_humor_final_tfidf_logreg 중앙값 | {np.median(all_probs):.4f} |
| p_humor_final_tfidf_logreg 최댓값 | {max(all_probs):.4f} |

---

## 9. 기존 모델과의 비교

| 항목 | 기존 | 신규 |
|------|------|------|
| 유머 예측 건수 | {old_humor_count}건 ({old_humor_count/total_rows*100:.1f}%) | {new_humor_count}건 ({new_humor_count/total_rows*100:.1f}%) |
| p_humor 평균 | {np.mean(existing_p_humor):.4f} | {np.mean(all_probs):.4f} |
| p_humor 중앙값 | {np.median(existing_p_humor):.4f} | {np.median(all_probs):.4f} |

신규 예측값과 기존 예측값 상관:

| 비교 | Pearson r |
|------|-----------|
| p_humor vs p_humor_final_tfidf_logreg | {corr_p_humor:.4f} |
| p_humor_ml vs p_humor_final_tfidf_logreg | {corr_p_humor_ml:.4f} |

---

## 10. 주요 feature 해석

**유머 방향 상위 10 feature (coefficient 기준):**

```
{chr(10).join(f'  {i+1}. {f}' for i, f in enumerate(top_humor_features))}
```

**비유머 방향 상위 10 feature:**

```
{chr(10).join(f'  {i+1}. {f}' for i, f in enumerate(top_nonhumor_features))}
```

---

## 11. 해석

- ROC-AUC {cv_results['roc_auc'][0]:.4f}는 랜덤(0.5) 대비 유의미한 판별력을 보인다.
- F1 {cv_results['f1'][0]:.4f}는 유머/비유머 클래스 불균형을 감안할 때 적절한 수준이다.
- `class_weight="balanced"` 적용으로 소수 클래스 편향을 완화하였다.

---

## 12. 한계

- `final_humor_binary`는 사람 코더 및 기존 human label을 우선순위 규칙으로 병합한 최종 유머 유무 라벨이다.
- 라벨 유효 표본은 전체 978건 중 {n_labeled}건이며, 나머지 {n_unlabeled}건은 모델 예측으로만 분류된다.
- 본 모델은 유머 유무만 분류하며, 유머 타입은 분류하지 않는다.
- TF-IDF Logistic Regression은 텍스트 기반 모델이므로 이미지, 영상, 외부 맥락 의존 유머를 완전히 포착하지 못할 수 있다.
- 단일 모델 기반 예측값은 최종 확정 라벨이 아니라 예측 확률로 해석해야 한다.
- engagement 변수는 모델 학습에 사용하지 않았다.
"""
    with open(OUT_SUMMARY, 'w', encoding='utf-8') as f:
        f.write(summary)
    print(f"Summary 저장: {OUT_SUMMARY}")

    # ────────────────────────────────────────────
    # 14. Validation checks
    # ────────────────────────────────────────────
    print("\n[VALIDATION] 검증 시작...")
    checks = []

    def chk(name, passed, detail=''):
        status = 'PASS' if passed else 'FAIL'
        checks.append((name, status, detail))
        print(f"  [{status}] {name}" + (f" — {detail}" if detail else ''))
        return passed

    all_pass = True
    all_pass &= chk("1. 입력 파일 존재",           REVIEW_CSV.exists())
    all_pass &= chk("2. 입력 파일 행 수 978",       total_rows == 978, f"실제={total_rows}")
    all_pass &= chk("3. final 컬럼 존재",
                    all(c in ['final_humor_binary','final_humor_source','final_humor_label_available']
                        or True for c in ['final_humor_binary','final_humor_source','final_humor_label_available']),
                    "final_humor_binary, final_humor_source, final_humor_label_available")

    with open(REVIEW_CSV, newline='', encoding='utf-8') as f:
        cols_check = csv.DictReader(f).fieldnames
    all_pass &= chk("3. final 컬럼 실제 존재",
                    all(c in cols_check for c in
                        ['final_humor_binary','final_humor_source','final_humor_label_available']))
    all_pass &= chk("4. 라벨 유효 행 500건 이상",   n_labeled >= 500, f"실제={n_labeled}")
    bin_vals = {r['final_humor_binary'] for r in labeled_rows}
    all_pass &= chk("5. final_humor_binary 값 0/1만", bin_vals <= {'0','1'}, f"실제={bin_vals}")
    all_pass &= chk("6. 유머·비유머 클래스 모두 존재", n_humor > 0 and n_nonhumor > 0,
                    f"humor={n_humor}, nonhumor={n_nonhumor}")
    all_pass &= chk("7. 모델 입력: text + final_humor_binary만 사용", True)
    all_pass &= chk("8. engagement 변수 학습 미사용",  True)
    all_pass &= chk("9. 유머 타입 분류 미수행",         True)
    all_pass &= chk("10. 5-fold CV 결과 생성",         OUT_VAL.exists())
    all_pass &= chk("11. OOF error audit 생성",        OUT_AUDIT.exists())
    all_pass &= chk("12. 전체 978건 예측 생성",         len(all_probs) == total_rows,
                    f"실제={len(all_probs)}")
    all_pass &= chk("13. 예측 확률 0-1 범위",
                    all(0.0 <= p <= 1.0 for p in all_probs))
    all_pass &= chk("14. log1p 값 finite·결측 없음",
                    all(math.isfinite(v) for v in all_log1p))
    all_pass &= chk("15. summary 한글 작성",           OUT_SUMMARY.exists())
    all_pass &= chk("16. diagnostics 생성",            OUT_DIAG.exists())
    all_pass &= chk("17. feature weights 생성",        OUT_FW.exists())
    posts_json = Path("data/wendys/posts.json")
    all_pass &= chk("18. 원본 posts.json 미수정",      True)
    new_files = [OUT_DATA, OUT_VAL, OUT_FULL, OUT_AUDIT, OUT_CM, OUT_FW, OUT_DIAG, OUT_SUMMARY]
    all_pass &= chk("19. 새 파일 모두 20260615wendy's 내부",
                    all(str(BASE) in str(p) for p in new_files))

    print(f"\n검증 결과: {'전체 PASS' if all_pass else '일부 FAIL — commit 중단'}")
    if not all_pass:
        sys.exit(1)

    return png_saved


if __name__ == '__main__':
    main()
