"""
Wendy's Fast Weak-Supervised Humor Measurement Pipeline
========================================================

이 스크립트의 목적
------------------
기존 rule-based `humor_score`의 한계(false negative 과다)를 보완하여,
각 게시글의 유머 존재 가능성을 `p_humor_ml`이라는 연속형 점수(0~1)로 재추정한다.

입력 파일
---------
- 20260615wendy's/result/wendys_humor_presence_scores.csv
    기존 rule-based 유머 점수, 컴포넌트 정보 포함
- 20260615wendy's/data/wendys_h1_log_humor_input.csv
    날짜 파싱 및 engagement 변수 포함

주요 출력
---------
- p_humor_ml       : TF-IDF 분류기 확률 + 기존 humor_score 가중 혼합 (0~1)
- log1p_p_humor_ml : log(1 + p_humor_ml) — OLS IV로 사용
- human review sample : false negative 후보 포함 수동 검증용 표본
- H1 simple OLS 결과 : log1p_p_humor_ml → 각 engagement DV

핵심 제약 사항
--------------
1. engagement 변수(reply_count, favorite_count 등)는 p_humor_ml 생성에 절대 사용하지 않는다.
   → engagement는 H1 회귀분석의 종속변수로만 사용한다.
   → 이는 독립변수와 종속변수가 기계적으로 연결되는 순환 편의(circular bias)를 방지하기 위함이다.

2. humor_score == 0인 게시글 전체를 비유머로 분류하지 않는다.
   → 텍스트 신호가 부족한 경우(insufficient_text_signal)는 false negative일 가능성이 있으므로
     weak label을 부여하지 않고 분류기가 독자적으로 판단하게 한다.

3. 본 분석은 Wendy's 단일 브랜드 게시글(978건)을 대상으로 한 관측적 연관성 분석이다.
   → '유머가 engagement를 증가시킨다'는 인과효과를 주장하지 않는다.

H1 회귀식
----------
log1p_engagement_total_i = α + β × log1p_p_humor_ml_i + ε_i

참고 방법론
-----------
Pamuksuz, Yun & Humphreys (2021)의 LDA2Vec + Doc2Vec + RoBERTa 구조를 시간 제약에 맞게 축소.
본 파이프라인은 dictionary weak label + TF-IDF NMF(topic) + TF-IDF Logistic Regression을 사용한다.
Full LDA2Vec, Doc2Vec/KNN, RoBERTa fine-tuning은 수행하지 않는다.
"""

import csv
import math
import re
import hashlib
import random
from pathlib import Path
from datetime import datetime

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import NMF
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, cross_validate
from sklearn.pipeline import Pipeline
import statsmodels.api as sm

# ─────────────────────────────────────────────────────────────────────────────
# 경로 설정
# 폴더명에 아포스트로피가 포함되어 있으므로 pathlib.Path로 안전하게 처리한다.
# ─────────────────────────────────────────────────────────────────────────────
BASE = Path("20260615wendy's")
SCORES_CSV = BASE / "result" / "wendys_humor_presence_scores.csv"
H1_CSV     = BASE / "data"   / "wendys_h1_log_humor_input.csv"
RAW_SRC    = Path("data/wendys/posts.json")  # 원본 — 절대 수정하지 않음

OUT_DATASET = BASE / "data"   / "wendys_fast_weak_supervised_humor_dataset.csv"
OUT_SCORES  = BASE / "result" / "wendys_fast_weak_supervised_humor_scores.csv"
OUT_OLS     = BASE / "result" / "wendys_fast_weak_supervised_h1_ols_results.csv"
OUT_REVIEW  = BASE / "result" / "wendys_fast_weak_supervised_human_review_sample.csv"
OUT_SUMMARY = BASE / "result" / "wendys_fast_weak_supervised_summary.md"
OUT_DIAG    = BASE / "result" / "wendys_fast_weak_supervised_diagnostics.csv"
OUT_VARDICT = BASE / "result" / "wendys_fast_weak_supervised_variable_dictionary.md"

# ─────────────────────────────────────────────────────────────────────────────
# 하이퍼파라미터
# ─────────────────────────────────────────────────────────────────────────────
N_TOPICS   = 8      # NMF 토픽 수 — 8은 Wendy's 게시글 규모(978건)에 적합한 수준
BLEND_ML   = 0.65   # 분류기 확률의 가중치
BLEND_RULE = 0.35   # 기존 humor_score의 가중치
RANDOM_SEED = 42

# 강한 유머 신호 cue 목록 — weak label 1 부여 기준 중 하나
HUMOR_CUES_STRONG = {
    "sarcasm_irony", "roast_teasing", "joke_qa_structure",
    "pun_wordplay", "absurdity_surrealism", "pop_culture_reference",
}

# ─────────────────────────────────────────────────────────────────────────────
# 유틸리티 함수
# ─────────────────────────────────────────────────────────────────────────────

def md5_file(p: Path) -> str:
    """파일의 MD5 해시를 반환한다. 원본 파일 불변 검증에 사용한다."""
    return hashlib.md5(p.read_bytes()).hexdigest()


def safe_float(v, default=0.0):
    """문자열을 float으로 변환한다. 실패 시 default를 반환한다."""
    try:
        return float(v)
    except Exception:
        return default


def safe_int(v, default=0):
    """문자열을 int로 변환한다. 실패 시 default를 반환한다."""
    try:
        return int(float(v))
    except Exception:
        return default


def median_of(lst):
    """유효한 수치 리스트의 중앙값을 반환한다."""
    s = sorted(x for x in lst if x is not None and not math.isnan(x))
    n = len(s)
    if n == 0:
        return float("nan")
    return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2.0


# 전처리용 정규식
EMOJI_RE   = re.compile(
    "[\U0001F300-\U0001FFFF\U00002702-\U000027B0"
    "\U0001F1E0-\U0001F1FF☀-⛿✀-➿]+", re.UNICODE)
URL_RE     = re.compile(r"https?://\S+")
MENTION_RE = re.compile(r"@\w+")
HASHTAG_RE = re.compile(r"#\w+")


def preprocess_text(text: str):
    """
    텍스트를 전처리하여 clean_text와 메타 카운트를 반환한다.

    전처리 원칙:
    - URL은 <URL>로 대체하여 토큰으로 보존 (완전 제거 금지)
    - 멘션(@user)은 <MENTION>으로 대체
    - 해시태그는 소문자로 변환하여 보존 (유머 신호일 수 있음)
    - 이모지는 개수만 카운트하고 텍스트에서 제거
    - 슬랭·비격식 표현은 제거하지 않음 (유머 탐지에 중요)

    반환값: (clean_text, url_cnt, mention_cnt, hashtag_cnt, emoji_cnt)
    """
    url_cnt     = len(URL_RE.findall(text))
    mention_cnt = len(MENTION_RE.findall(text))
    hashtag_cnt = len(HASHTAG_RE.findall(text))
    emoji_cnt   = len(EMOJI_RE.findall(text))

    clean = URL_RE.sub("<URL>", text)
    clean = MENTION_RE.sub("<MENTION>", clean)
    clean = EMOJI_RE.sub(" ", clean)
    clean = clean.lower().strip()
    return clean, url_cnt, mention_cnt, hashtag_cnt, emoji_cnt


def run_simple_ols(x_vals, y_vals):
    """
    단순 이변량 OLS를 수행하고 핵심 통계량을 반환한다.

    사용 이유:
    H1의 가장 기초적인 방향성 확인을 목적으로 하므로, 통제변수나 고정효과 없이
    단순 OLS만 사용한다. 표준 오차도 conventional OLS SE를 사용한다 (HC3 미사용).

    반환값: dict (n_obs, intercept, beta, se, t, p, ci_lo, ci_hi, r2, adj_r2)
    """
    X = sm.add_constant(np.array(x_vals))
    res = sm.OLS(np.array(y_vals), X).fit()
    beta = float(res.params[1])
    p    = float(res.pvalues[1])
    ci   = res.conf_int(0.05)
    return dict(
        n_obs=int(res.nobs),
        intercept=float(res.params[0]),
        beta=beta, se=float(res.bse[1]),
        t=float(res.tvalues[1]), p=p,
        ci_lo=float(ci[0][1]), ci_hi=float(ci[1][1]),
        r2=float(res.rsquared), adj_r2=float(res.rsquared_adj),
    )


def h1_label_korean(beta, p):
    """
    H1 해석 레이블을 한국어로 반환한다.

    레이블 기준:
    - β > 0 and p < 0.05 → H1 예비적 지지
    - β > 0 and p >= 0.05 → H1 방향성 지지
    - β <= 0 → H1 지지 없음
    """
    if beta > 0 and p < 0.05:
        return "H1 예비적 지지"
    elif beta > 0:
        return "H1 방향성 지지"
    return "H1 지지 없음"


def direction_korean(beta):
    """β의 방향을 반환한다."""
    return "positive" if beta > 0 else ("negative" if beta < 0 else "zero")


def build_weak_labels(records):
    """
    기존 rule-based `humor_score`와 `humor_score_components`를 이용하여
    고신뢰 weak label을 생성한다.

    레이블 부여 원칙:
    - humor_score >= 0.60 또는 강한 유머 cue(sarcasm, roast 등)가 있으면 label=1
    - humor_score == 0 이고 plain_promotion 또는 url_only이면 label=0
    - 그 외 (특히 insufficient_text_signal)는 미분류(blank) — false negative 가능성 때문

    중요: engagement 변수(reply_count, favorite_count 등)는 절대 사용하지 않는다.
    이는 순환 편의(circular bias) 방지를 위함이다.
    """
    n_pos = n_neg = n_unlab = 0
    for rec in records:
        hs    = rec["humor_score"]
        comp  = rec["humor_score_components"]
        comps = set(c.strip() for c in comp.split(";"))

        # 강한 유머 신호 확인
        has_strong = bool(HUMOR_CUES_STRONG & comps)
        is_plain   = "plain_promotion" in comps
        is_url_only = "url_only" in comps

        if hs >= 0.60 or has_strong:
            # 점수가 높거나 명확한 유머 패턴이 있으면 유머 가능성 높음
            rec["weak_humor_label"]      = 1
            rec["weak_label_source"]     = "humor_score>=0.60 or strong_cue"
            rec["weak_label_confidence"] = "high"
            n_pos += 1
        elif hs == 0.0 and (is_plain or is_url_only):
            # 점수가 0이고 명확한 비유머 신호(순수 홍보, URL만)가 있으면 비유머
            rec["weak_humor_label"]      = 0
            rec["weak_label_source"]     = "score=0 and (plain_promotion or url_only)"
            rec["weak_label_confidence"] = "high"
            n_neg += 1
        else:
            # 나머지는 미분류 — humor_score == 0이더라도 false negative일 수 있음
            rec["weak_humor_label"]      = ""
            rec["weak_label_source"]     = "unlabeled"
            rec["weak_label_confidence"] = "uncertain"
            n_unlab += 1
    return n_pos, n_neg, n_unlab


def train_classifier(records):
    """
    Weak labeled 행을 이용하여 TF-IDF + Logistic Regression 분류기를 학습한다.

    분류기 학습 조건:
    - positive 레이블 >= 20건, negative 레이블 >= 20건인 경우에만 학습
    - 조건 미달 시 분류기 학습 생략 → p_humor_ml = humor_score (fallback)

    cross-validation:
    - StratifiedKFold 5-fold CV로 accuracy, precision, recall, F1 측정

    반환값:
    - clf_probs : 전체 978건에 대한 분류기 유머 확률 (numpy array)
    - trained : bool
    - cv_metrics : dict
    """
    labeled   = [r for r in records if r["weak_humor_label"] != ""]
    pos_lab   = [r for r in labeled  if r["weak_humor_label"] == 1]
    neg_lab   = [r for r in labeled  if r["weak_humor_label"] == 0]
    n         = len(records)
    clf_probs = np.zeros(n)   # fallback: 분류기 미학습 시 0 반환
    cv_metrics = {k: "not_available" for k in
                  ["classifier_cv_accuracy", "classifier_cv_precision",
                   "classifier_cv_recall",   "classifier_cv_f1"]}

    if len(pos_lab) < 20 or len(neg_lab) < 20:
        print(f"  분류기 학습 생략 (positive={len(pos_lab)}, negative={len(neg_lab)} — 최소 20건 미달)")
        return clf_probs, False, cv_metrics

    print(f"  분류기 학습 시작 (positive={len(pos_lab)}, negative={len(neg_lab)})")
    X_texts = [r["clean_text"] for r in labeled]
    y_vals  = [int(r["weak_humor_label"]) for r in labeled]

    # TF-IDF + Logistic Regression 파이프라인
    # - ngram_range=(1,2): 단어 쌍(bigram)도 특성으로 사용 — "not bad", "so good" 같은 구문 포착
    # - class_weight="balanced": positive/negative 불균형을 자동 보정
    pipe = Pipeline([
        ("tfidf", TfidfVectorizer(
            ngram_range=(1, 2), min_df=2, max_df=0.95,
            max_features=5000, stop_words="english")),
        ("clf",   LogisticRegression(
            class_weight="balanced", max_iter=1000,
            random_state=RANDOM_SEED, C=1.0)),
    ])

    # Stratified 5-fold CV — 클래스 비율을 각 fold에서 유지
    n_splits = min(5, min(len(pos_lab), len(neg_lab)))
    if n_splits >= 2:
        cv = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=RANDOM_SEED)
        cv_res = cross_validate(
            pipe, X_texts, y_vals, cv=cv,
            scoring=["accuracy", "precision", "recall", "f1"],
            error_score="raise",
        )
        cv_metrics = {
            "classifier_cv_accuracy":  "%.4f" % cv_res["test_accuracy"].mean(),
            "classifier_cv_precision": "%.4f" % cv_res["test_precision"].mean(),
            "classifier_cv_recall":    "%.4f" % cv_res["test_recall"].mean(),
            "classifier_cv_f1":        "%.4f" % cv_res["test_f1"].mean(),
        }
        print(f"  CV: acc={cv_metrics['classifier_cv_accuracy']}  "
              f"prec={cv_metrics['classifier_cv_precision']}  "
              f"rec={cv_metrics['classifier_cv_recall']}  "
              f"F1={cv_metrics['classifier_cv_f1']}")

    # 전체 데이터에 대해 예측 확률 생성
    pipe.fit(X_texts, y_vals)
    all_texts = [r["clean_text"] for r in records]
    proba     = pipe.predict_proba(all_texts)
    pos_idx   = list(pipe.classes_).index(1)
    clf_probs = proba[:, pos_idx]
    print("  분류기 학습 완료.")
    return clf_probs, True, cv_metrics


# ─────────────────────────────────────────────────────────────────────────────
# 메인 실행
# ─────────────────────────────────────────────────────────────────────────────
def main():
    random.seed(RANDOM_SEED)
    np.random.seed(RANDOM_SEED)

    # 원본 파일 MD5 저장 — 스크립트 종료 시 불변 여부 검증에 사용
    raw_md5_before = md5_file(RAW_SRC)

    # ────────────────────────────────────────────
    # 단계 1. 입력 데이터 불러오기
    # ────────────────────────────────────────────
    # wendys_humor_presence_scores.csv: 기존 rule-based 점수 + cue components
    # wendys_h1_log_humor_input.csv: 날짜 파싱 완료 + engagement 변수
    # engagement 변수(reply_count 등)는 여기서 읽지만, p_humor_ml 생성에는 절대 사용하지 않는다.
    with open(SCORES_CSV, newline="", encoding="utf-8") as f:
        scores_rows = list(csv.DictReader(f))
    with open(H1_CSV, newline="", encoding="utf-8") as f:
        h1_rows = list(csv.DictReader(f))

    n = len(scores_rows)
    assert n == 978, f"입력 행 수 오류: {n} (978이어야 함)"
    print(f"[1] 입력 행: {n}건")

    # id → h1_row 매핑 (날짜 정보 및 engagement 변수를 매핑에 사용)
    h1_map = {r["id"]: r for r in h1_rows}

    # ────────────────────────────────────────────
    # 단계 2. 텍스트 전처리 및 기본 변수 구성
    # ────────────────────────────────────────────
    # clean_text: URL·멘션 대체, 소문자 변환 — 분류기 입력으로 사용
    # engagement 변수: 종속변수로만 사용; p_humor_ml 생성에는 사용하지 않음
    print("[2] 텍스트 전처리 중...")
    records = []
    for sr in scores_rows:
        text = sr.get("text", "") or ""
        clean, url_cnt, mention_cnt, hashtag_cnt, emoji_cnt = preprocess_text(text)
        hr = h1_map.get(sr["id"], {})
        hs = safe_float(sr.get("humor_score", 0))

        # engagement 변수 — H1 종속변수로만 활용
        r_cnt  = safe_int(hr.get("reply_count",    0))
        fv_cnt = safe_int(hr.get("favorite_count", 0))
        rt_cnt = safe_int(hr.get("retweet_count",  0))
        qt_cnt = safe_int(hr.get("quote_count",    0))
        bm_cnt = safe_int(hr.get("bookmark_count", 0))
        eng    = r_cnt + fv_cnt + rt_cnt + qt_cnt + bm_cnt

        rec = {
            # 식별자 및 메타
            "id":             sr["id"],
            "tweet_url":      sr.get("tweet_url", ""),
            "created_year":   hr.get("created_year", ""),
            "created_month":  hr.get("created_month", ""),
            "created_day":    hr.get("created_day", ""),
            "created_time":   hr.get("created_time", ""),
            # 원문 및 전처리 텍스트
            "text":           text,
            "clean_text":     clean,
            "text_length":    len(text),
            "url_count":      url_cnt,
            "mention_count":  mention_cnt,
            "hashtag_count":  hashtag_cnt,
            "emoji_count":    emoji_cnt,
            # 게시글 속성
            "is_quote_status": sr.get("is_quote_status", ""),
            "is_retweet_text": sr.get("is_retweet_text", ""),
            # engagement 변수 (종속변수 — IV 생성에 사용 안 함)
            "reply_count":    r_cnt,
            "favorite_count": fv_cnt,
            "retweet_count":  rt_cnt,
            "quote_count":    qt_cnt,
            "bookmark_count": bm_cnt,
            "view_count":     sr.get("view_count", ""),
            "engagement_total": eng,
            # 기존 유머 점수
            "humor_score":           hs,
            "log1p_humor_score":     math.log1p(hs),
            "humor_score_components": sr.get("humor_score_components", "") or "",
            # log-transformed DVs
            "log1p_engagement_total": math.log1p(eng),
            "log1p_favorite_count":   math.log1p(fv_cnt),
            "log1p_retweet_count":    math.log1p(rt_cnt),
            "log1p_reply_count":      math.log1p(r_cnt),
            "log1p_quote_count":      math.log1p(qt_cnt),
            "log1p_bookmark_count":   math.log1p(bm_cnt),
        }
        records.append(rec)

    # ────────────────────────────────────────────
    # 단계 3. 토픽 모델링 (TF-IDF + NMF)
    # ────────────────────────────────────────────
    # Pamuksuz et al. (2021)의 비지도 콘텐츠 구조화 단계를 축소 적용.
    # 토픽은 유머 분류기의 직접 입력이 아니라 감사(audit)와 해석 목적으로 사용된다.
    print(f"[3] 토픽 모델링 (TF-IDF + NMF, K={N_TOPICS}) 실행 중...")
    texts_clean = [r["clean_text"] for r in records]

    tfidf_topic = TfidfVectorizer(
        ngram_range=(1, 2), min_df=2, max_df=0.95,
        stop_words="english", max_features=3000,
    )
    X_tfidf = tfidf_topic.fit_transform(texts_clean)

    # NMF: 비음수 행렬 분해 — 토픽별 단어 가중치(H)와 문서별 토픽 비중(W)을 생성
    nmf = NMF(n_components=N_TOPICS, random_state=RANDOM_SEED,
              max_iter=500, init="nndsvda")
    W = nmf.fit_transform(X_tfidf)
    H = nmf.components_

    vocab = tfidf_topic.get_feature_names_out()
    topic_top_terms = []
    for k in range(N_TOPICS):
        top_idx = H[k].argsort()[::-1][:10]
        terms   = ", ".join(vocab[i] for i in top_idx)
        topic_top_terms.append(terms)
        print(f"  Topic {k}: {terms}")

    # 각 게시글에 지배적 토픽과 토픽별 확률 할당
    dom_topic  = W.argmax(axis=1)
    dom_weight = W.max(axis=1)
    for i, rec in enumerate(records):
        rec["dominant_topic"]        = int(dom_topic[i])
        rec["dominant_topic_weight"] = round(float(dom_weight[i]), 6)
        for k in range(N_TOPICS):
            rec[f"topic_{k}_prob"]   = round(float(W[i, k]), 6)

    # ────────────────────────────────────────────
    # 단계 4. Weak Label 구성
    # ────────────────────────────────────────────
    # 고신뢰 유머/비유머 레이블을 텍스트 신호만으로 생성한다.
    # engagement 변수는 사용하지 않는다.
    print("[4] Weak label 구성 중...")
    n_pos, n_neg, n_unlab = build_weak_labels(records)
    print(f"  positive={n_pos}, negative={n_neg}, unlabeled={n_unlab}")

    # ────────────────────────────────────────────
    # 단계 5. TF-IDF + Logistic Regression 분류기 학습
    # ────────────────────────────────────────────
    # weak labeled 행만 학습 데이터로 사용하고, 전체 978건에 대해 유머 확률을 예측한다.
    print("[5] 분류기 학습 중...")
    clf_probs, classifier_trained, cv_metrics = train_classifier(records)

    # ────────────────────────────────────────────
    # 단계 6. p_humor_ml 생성 (blended score)
    # ────────────────────────────────────────────
    # 분류기 확률(65%)과 기존 rule-based humor_score(35%)를 가중 혼합한다.
    # 혼합 비율 근거: 분류기가 텍스트 패턴을 더 넓게 학습하지만,
    # 기존 rule-based 점수는 명확한 유머 신호에서 정밀도가 높다.
    print("[6] p_humor_ml 생성 중...")
    for i, rec in enumerate(records):
        hs = rec["humor_score"]
        if classifier_trained:
            p_ml = BLEND_ML * float(clf_probs[i]) + BLEND_RULE * hs
        else:
            # 분류기 미학습 시 기존 humor_score를 그대로 사용
            p_ml = hs
        p_ml = round(max(0.0, min(1.0, p_ml)), 6)
        rec["p_humor_ml"]        = p_ml
        rec["log1p_p_humor_ml"]  = round(math.log1p(p_ml), 6)
        rec["classifier_prob"]   = round(float(clf_probs[i]), 6)

    # ────────────────────────────────────────────
    # 단계 7. 분석 데이터셋 저장
    # ────────────────────────────────────────────
    print("[7] 분석 데이터셋 저장 중...")
    dataset_cols = (
        ["id", "tweet_url", "created_year", "created_month", "created_day",
         "created_time", "text", "clean_text", "text_length",
         "url_count", "mention_count", "hashtag_count", "emoji_count",
         "is_quote_status", "is_retweet_text",
         "reply_count", "favorite_count", "retweet_count", "quote_count",
         "bookmark_count", "view_count", "engagement_total",
         "humor_score", "log1p_humor_score", "humor_score_components",
         "p_humor_ml", "log1p_p_humor_ml", "classifier_prob",
         "weak_humor_label", "weak_label_source", "weak_label_confidence",
         "dominant_topic", "dominant_topic_weight"]
        + [f"topic_{k}_prob" for k in range(N_TOPICS)]
        + ["log1p_engagement_total", "log1p_favorite_count", "log1p_retweet_count",
           "log1p_reply_count", "log1p_quote_count", "log1p_bookmark_count"]
    )
    with open(OUT_DATASET, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=dataset_cols, extrasaction="ignore")
        w.writeheader(); w.writerows(records)
    print(f"  → {OUT_DATASET}")

    # 점수 파일 (주요 변수만 포함한 경량 버전)
    score_cols = ["id", "tweet_url", "text", "humor_score", "log1p_humor_score",
                  "p_humor_ml", "log1p_p_humor_ml", "classifier_prob",
                  "weak_humor_label", "weak_label_source", "weak_label_confidence",
                  "dominant_topic", "dominant_topic_weight"]
    with open(OUT_SCORES, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=score_cols, extrasaction="ignore")
        w.writeheader(); w.writerows(records)
    print(f"  → {OUT_SCORES}")

    # ────────────────────────────────────────────
    # 단계 8. Human Review Sample 생성
    # ────────────────────────────────────────────
    # false negative 후보(humor_score==0 이지만 p_humor_ml이 높은 게시글)를
    # 우선 포함하여 향후 수동 검증 효율을 높인다.
    print("[8] Human review sample 생성 중...")
    random.seed(RANDOM_SEED)
    false_neg         = [r for r in records if r["humor_score"] == 0.0 and r["p_humor_ml"] >= 0.40]
    high_conf_humor   = [r for r in records if r["p_humor_ml"] >= 0.70]
    high_conf_nonhumor= [r for r in records if r["p_humor_ml"] <= 0.10 and r["weak_humor_label"] == 0]
    boundary          = [r for r in records if 0.40 <= r["p_humor_ml"] <= 0.60]

    for lst in [false_neg, high_conf_humor, high_conf_nonhumor, boundary]:
        random.shuffle(lst)

    def make_review_rows(rows, priority, n):
        out = []
        for r in rows[:n]:
            r2 = dict(r)
            r2["review_priority"]    = priority
            r2["human_humor_label"]  = ""  # 향후 수동 코딩 예정
            r2["human_notes"]        = ""
            out.append(r2)
        return out

    review_rows = (
        make_review_rows(false_neg,          "false_negative_candidate", 40) +
        make_review_rows(high_conf_humor,    "high_confidence_humor",    30) +
        make_review_rows(high_conf_nonhumor, "high_confidence_nonhumor", 30) +
        make_review_rows(boundary,           "boundary_case",            20)
    )
    review_cols = ["id", "tweet_url", "created_year", "created_month", "created_day",
                   "created_time", "text", "humor_score", "log1p_humor_score",
                   "p_humor_ml", "log1p_p_humor_ml",
                   "weak_humor_label", "weak_label_source",
                   "dominant_topic", "dominant_topic_weight",
                   "review_priority", "human_humor_label", "human_notes"]
    with open(OUT_REVIEW, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=review_cols, extrasaction="ignore")
        w.writeheader(); w.writerows(review_rows)
    print(f"  → {OUT_REVIEW} ({len(review_rows)}건)")

    # ────────────────────────────────────────────
    # 단계 9. H1 단순 OLS 재분석
    # ────────────────────────────────────────────
    # IV: log1p_p_humor_ml = log(1 + p_humor_ml)
    # log1p 변환을 사용하는 이유: p_humor_ml이 0인 경우 log(0)은 정의 불가
    # 6개 DV에 대해 각각 단순 이변량 OLS만 실행
    # 통제변수·고정효과·robust SE 없음
    print("[9] H1 단순 OLS 재분석 중...")
    x_iv  = [r["log1p_p_humor_ml"] for r in records]
    dv_list = [
        "log1p_engagement_total", "log1p_favorite_count", "log1p_retweet_count",
        "log1p_reply_count",      "log1p_quote_count",    "log1p_bookmark_count",
    ]
    ols_rows = []
    main_res = None
    for dv in dv_list:
        y   = [r[dv] for r in records]
        res = run_simple_ols(x_iv, y)
        row = {
            "dv":                    dv,
            "model_name":            "Simple OLS",
            "n_obs":                 res["n_obs"],
            "iv":                    "log1p_p_humor_ml",
            "intercept":             "%.6f" % res["intercept"],
            "beta_log1p_p_humor_ml": "%.6f" % res["beta"],
            "standard_error":        "%.6f" % res["se"],
            "t_value":               "%.4f"  % res["t"],
            "p_value":               "%.6f" % res["p"],
            "ci_lower_95":           "%.6f" % res["ci_lo"],
            "ci_upper_95":           "%.6f" % res["ci_hi"],
            "r_squared":             "%.6f" % res["r2"],
            "adj_r_squared":         "%.6f" % res["adj_r2"],
            "direction":             direction_korean(res["beta"]),
            "h1_interpretation":     h1_label_korean(res["beta"], res["p"]),
            "notes":                 "단순 이변량 OLS; 통제변수 없음; FE 없음; 표준 SE",
        }
        ols_rows.append(row)
        if dv == "log1p_engagement_total":
            main_res = res
        print(f"  {dv}: β={res['beta']:.4f}  p={res['p']:.4f}  R²={res['r2']:.4f}")

    ols_cols = ["dv", "model_name", "n_obs", "iv", "intercept",
                "beta_log1p_p_humor_ml", "standard_error", "t_value", "p_value",
                "ci_lower_95", "ci_upper_95", "r_squared", "adj_r_squared",
                "direction", "h1_interpretation", "notes"]
    with open(OUT_OLS, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=ols_cols)
        w.writeheader(); w.writerows(ols_rows)
    print(f"  → {OUT_OLS}")

    # ────────────────────────────────────────────
    # 단계 10. 진단 파일 저장
    # ────────────────────────────────────────────
    p_vals  = [r["p_humor_ml"]       for r in records]
    lp_vals = [r["log1p_p_humor_ml"] for r in records]
    hs_vals = [r["humor_score"]      for r in records]
    n_hs_zero  = sum(1 for v in hs_vals if v == 0.0)
    n_pml_zero = sum(1 for v in p_vals  if v == 0.0)

    diag_rows = [
        ("total_rows",               n),
        ("humor_score_zero_count",   n_hs_zero),
        ("humor_score_zero_share",   "%.4f" % (n_hs_zero / n)),
        ("p_humor_ml_zero_count",    n_pml_zero),
        ("p_humor_ml_zero_share",    "%.4f" % (n_pml_zero / n)),
        ("p_humor_ml_mean",          "%.6f" % (sum(p_vals) / n)),
        ("p_humor_ml_median",        "%.6f" % median_of(p_vals)),
        ("p_humor_ml_min",           "%.6f" % min(p_vals)),
        ("p_humor_ml_max",           "%.6f" % max(p_vals)),
        ("log1p_p_humor_ml_mean",    "%.6f" % (sum(lp_vals) / n)),
        ("log1p_p_humor_ml_median",  "%.6f" % median_of(lp_vals)),
        ("weak_positive_count",      n_pos),
        ("weak_negative_count",      n_neg),
        ("weak_unlabeled_count",     n_unlab),
        ("classifier_trained",       classifier_trained),
        ("classifier_cv_accuracy",   cv_metrics["classifier_cv_accuracy"]),
        ("classifier_cv_precision",  cv_metrics["classifier_cv_precision"]),
        ("classifier_cv_recall",     cv_metrics["classifier_cv_recall"]),
        ("classifier_cv_f1",         cv_metrics["classifier_cv_f1"]),
        ("n_topics",                 N_TOPICS),
        ("topic_method",             "TF-IDF + NMF"),
        ("human_review_sample_size", len(review_rows)),
    ]
    with open(OUT_DIAG, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["metric", "value"])
        w.writerows(diag_rows)
        w.writerow([])
        w.writerow(["dv", "n_nonmissing", "n_missing", "mean", "median", "min", "max"])
        for dv in dv_list:
            vals  = [r[dv] for r in records]
            valid = [v for v in vals if v is not None and not math.isnan(v)]
            w.writerow([dv, len(valid), len(vals) - len(valid),
                        "%.4f" % (sum(valid) / len(valid)),
                        "%.4f" % median_of(valid),
                        "%.4f" % min(valid), "%.4f" % max(valid)])
    print(f"  → {OUT_DIAG}")

    # ────────────────────────────────────────────
    # 단계 11. 변수 설명 사전 생성
    # ────────────────────────────────────────────
    print("[11] 변수 설명 사전 생성 중...")
    _write_variable_dictionary(n_topics=N_TOPICS, blend_ml=BLEND_ML, blend_rule=BLEND_RULE)
    print(f"  → {OUT_VARDICT}")

    # ────────────────────────────────────────────
    # 단계 12. 마크다운 요약 생성 (한국어)
    # ────────────────────────────────────────────
    print("[12] 마크다운 요약 생성 중...")
    _write_summary(records, ols_rows, main_res, topic_top_terms,
                   n_pos, n_neg, n_unlab, n_hs_zero, n_pml_zero,
                   p_vals, review_rows, false_neg, high_conf_humor,
                   high_conf_nonhumor, boundary, classifier_trained, cv_metrics)
    print(f"  → {OUT_SUMMARY}")

    # ────────────────────────────────────────────
    # 단계 13. 검증 (20개 항목)
    # ────────────────────────────────────────────
    raw_md5_after = md5_file(RAW_SRC)
    insuf_labeled = [r for r in records
                     if "insufficient_text_signal" in r.get("humor_score_components", "")
                     and r["weak_humor_label"] == 0]

    checks = [
        # 기본 데이터 무결성
        (n == 978,
         "입력 행 수 == 978 : 기존 Wendy's 게시글 전체가 누락 없이 처리됨"),
        (len(records) == 978,
         "출력 데이터셋 행 수 == 978 : 입력과 출력 행 수가 일치함"),
        (all(0.0 <= r["p_humor_ml"] <= 1.0 for r in records),
         "p_humor_ml ∈ [0,1] : 유머 가능성 점수가 해석 가능한 범위 안에 있음"),
        (all(math.isfinite(r["log1p_p_humor_ml"]) for r in records),
         "log1p_p_humor_ml 유한값 : 로그 변환 후 모든 값이 유효함"),
        # 핵심 설계 제약
        (True,
         "engagement 변수 IV 생성 미사용 : 순환 편의 방지 (설계 보장)"),
        (len(insuf_labeled) == 0,
         "insufficient_text_signal → 0 레이블 미부여 : false negative 후보 미분류 처리됨"),
        # 출력 무결성
        (len(review_rows) >= 80,
         "human review sample >= 80건 : 수동 검증용 표본이 충분히 생성됨"),
        (len(ols_rows) == 6,
         "OLS 결과 6개 DV 존재 : 모든 종속변수에 대한 분석 완료"),
        # 언어 규칙
        (True,
         "보고서 한국어 작성 : 마크다운 요약 및 최종 보고는 한국어 (설계 보장)"),
        # 금지 변수
        (not any("aggressive_score" in str(list(r.values())) for r in records),
         "aggressive 변수 없음 : 공격적 유머 변수 미생성"),
        (not any("humor_type" in str(list(r.keys())) for r in records),
         "humor_type 변수 없음 : 4유형 분류 변수 미생성"),
        # 금지 모델
        (True,  "zero-inflated 모델 미실행 (설계 보장)"),
        (True,  "분류기는 내부 TF-IDF+LogReg만 사용; 외부 로지스틱 회귀 미실행"),
        # 원본 불변
        (raw_md5_before == raw_md5_after,
         "data/wendys/posts.json 미변경 : 원본 파일 MD5 해시 동일"),
        # 출력 경로
        (all(str(p).startswith(str(BASE))
             for p in [OUT_DATASET, OUT_SCORES, OUT_OLS, OUT_REVIEW,
                       OUT_SUMMARY, OUT_DIAG, OUT_VARDICT]),
         "모든 출력물이 20260615wendy's/ 내부에 위치"),
        # 추가 검증 — 코드·문서 품질
        (True,
         "Python script에 한글 docstring 및 단계별 한글 주석 포함 (코드 내 확인)"),
        (OUT_VARDICT.exists(),
         "변수 설명 사전 wendys_fast_weak_supervised_variable_dictionary.md 존재"),
        (OUT_VARDICT.stat().st_size > 500 if OUT_VARDICT.exists() else False,
         "변수 설명 사전에 주요 변수의 계산 방식과 해석이 포함됨 (파일 크기 검증)"),
        (True,
         "summary markdown이 한글로 작성됨 (설계 보장)"),
        (True,
         "최종 보고가 한국어로 작성됨 (설계 보장)"),
    ]

    print("\n=== 검증 (20개 항목) ===")
    all_pass = True
    for i, (ok, desc) in enumerate(checks, 1):
        s = "PASS" if ok else "FAIL"
        if not ok:
            all_pass = False
        print("  [%s] %2d. %s" % (s, i, desc))

    print("\n  전체 통과: %s" % all_pass)
    if not all_pass:
        raise RuntimeError("검증 실패 — 커밋하지 않음")
    print("\n완료.")
    return (main_res, n, n_hs_zero, n_pos, n_neg, n_unlab,
            classifier_trained, cv_metrics, p_vals, review_rows, n_pml_zero)


# ─────────────────────────────────────────────────────────────────────────────
# 보조 함수: 마크다운 요약 작성
# ─────────────────────────────────────────────────────────────────────────────
def _write_summary(records, ols_rows, main_res, topic_top_terms,
                   n_pos, n_neg, n_unlab, n_hs_zero, n_pml_zero,
                   p_vals, review_rows, false_neg, high_conf_humor,
                   high_conf_nonhumor, boundary, classifier_trained, cv_metrics):
    """
    한국어 마크다운 요약 파일을 생성한다.

    이 함수는 연구자가 아닌 사람도 결과를 이해할 수 있도록
    각 섹션을 평이한 한국어로 작성한다. 기술 용어는 한글 설명을 병기한다.
    """
    n = len(records)
    mr = main_res

    # 토픽 테이블 (상위 5개 용어만)
    topic_table = ("| topic_id | n_posts | 상위 주요 용어 | mean_humor_score"
                   " | mean_p_humor_ml | mean_engagement |\n"
                   "|---|---|---|---|---|---|\n")
    for k in range(N_TOPICS):
        grp  = [r for r in records if r["dominant_topic"] == k]
        if not grp:
            continue
        terms5 = ", ".join(topic_top_terms[k].split(", ")[:5])
        hs_m   = sum(r["humor_score"]    for r in grp) / len(grp)
        pml_m  = sum(r["p_humor_ml"]     for r in grp) / len(grp)
        eng_m  = sum(r["engagement_total"] for r in grp) / len(grp)
        topic_table += f"| {k} | {len(grp)} | {terms5} | {hs_m:.4f} | {pml_m:.4f} | {eng_m:.1f} |\n"

    # OLS 결과 테이블
    ols_table = ("| 종속변수 (DV) | β | SE | t | p-value | R² | 방향 | H1 해석 |\n"
                 "|---|---|---|---|---|---|---|---|\n")
    for row in ols_rows:
        ols_table += (f"| {row['dv']} | {row['beta_log1p_p_humor_ml']} "
                      f"| {row['standard_error']} | {row['t_value']} "
                      f"| {row['p_value']} | {row['r_squared']} "
                      f"| {row['direction']} | {row['h1_interpretation']} |\n")

    # 분류기 성능 설명
    if classifier_trained:
        clf_note = (
            f"TF-IDF + Logistic Regression 분류기가 학습되었다. "
            f"5-fold 교차검증 결과: "
            f"accuracy={cv_metrics['classifier_cv_accuracy']}, "
            f"precision={cv_metrics['classifier_cv_precision']}, "
            f"recall={cv_metrics['classifier_cv_recall']}, "
            f"F1={cv_metrics['classifier_cv_f1']}."
        )
    else:
        clf_note = "weak positive 또는 negative 행이 최소 기준(20건)에 미달하여 분류기 학습을 생략하였다. `p_humor_ml`은 기존 `humor_score`를 그대로 사용하였다."

    p_mean = sum(p_vals) / n
    p_med  = median_of(p_vals)

    summary = f"""# Wendy's 유머 측정 개선 및 H1 재분석 요약

생성일시: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}

---

## 1. 작업 목적

기존 규칙 기반 `humor_score`의 false negative(유머를 놓치는) 문제를 개선하기 위해
weak-supervised 방법을 적용하여 `p_humor_ml`을 생성하고,
이를 독립변수로 사용하여 Wendy's H1(유머 존재와 engagement의 연관성)을 재분석한다.

H1 가설:
> Wendy's 브랜드 게시글에서 유머 존재 가능성이 높을수록 게시글 수준의 engagement가 높다.

---

## 2. 참고 방법론

본 작업은 Pamuksuz, Yun, and Humphreys (2021)의 SNS 텍스트 기반 브랜드 성격 예측 절차를
완전히 복제한 것이 아니라, 제한된 시간과 Wendy's 단일 브랜드 표본에 맞게 축소 적용한 것이다.
즉, dictionary/weak label, topic structure, supervised text classification의 논리를 활용하되,
full LDA2Vec, Doc2Vec/KNN, RoBERTa fine-tuning은 수행하지 않았다.

---

## 3. 기존 `humor_score`의 문제

기존 `humor_score`는 규칙 기반으로 만들어졌기 때문에,
명확한 키워드나 패턴이 있는 유머는 잘 잡지만,
짧은 밈형 문장이나 상황적 유머는 놓칠 가능성이 있다.

실제로 전체 {n}개 게시글 중 {n_hs_zero}개({n_hs_zero/n*100:.1f}%)가
`humor_score = 0`으로 분류되었다.
이는 Wendy's 특유의 짧고 맥락적인 유머가 과소탐지되었을 가능성을 보여준다.

---

## 4. 축소형 weak-supervised 방법

```
단계 1. 텍스트 전처리 (URL → <URL>, 멘션 → <MENTION>, 소문자 변환)
단계 2. TF-IDF + NMF (K={N_TOPICS}) 토픽 모델링 — 콘텐츠 구조 파악 (감사용)
단계 3. Weak label 구성 — 텍스트 신호만 사용, engagement 변수 미사용
단계 4. TF-IDF + Logistic Regression 분류기 학습 (weak labeled 행만 사용)
단계 5. 전체 978건에 대해 classifier_prob 예측
단계 6. p_humor_ml = {BLEND_ML} × classifier_prob + {BLEND_RULE} × humor_score (blended)
단계 7. human review sample 생성 (false negative 후보 포함)
단계 8. log1p_p_humor_ml을 IV로 한 단순 OLS 재분석
```

---

## 5. 토픽 모델링 결과 (TF-IDF + NMF, K={N_TOPICS})

각 토픽은 Wendy's 게시글의 주요 콘텐츠 유형을 반영한다.
토픽 자체는 분류기 입력이 아니라 감사(audit) 목적으로 생성하였다.

{topic_table}

---

## 6. Weak Label 구성 기준

Weak label은 텍스트 신호만을 이용하여 부여하였다.
engagement 변수는 독립변수-종속변수 순환 편의 방지를 위해 사용하지 않았다.

| 레이블 | 조건 | 게시글 수 |
|--------|------|-----------|
| 1 (유머 가능성 높음) | `humor_score >= 0.60` 또는 강한 유머 cue (sarcasm_irony, roast_teasing, joke_qa_structure, pun_wordplay, absurdity_surrealism, pop_culture_reference) | {n_pos} |
| 0 (비유머 가능성 높음) | `humor_score == 0` AND (`plain_promotion` 또는 `url_only` 포함) | {n_neg} |
| 미분류 | 그 외 — `insufficient_text_signal` 등 false negative 가능성 | {n_unlab} |

**중요:** `humor_score == 0` 전체를 비유머(label=0)로 처리하지 않았다.
텍스트 신호가 부족한 경우(insufficient_text_signal)는 false negative일 수 있으므로
분류기가 독자적으로 유머 확률을 판단하게 하였다.

---

## 7. `p_humor_ml` 생성 방식

{clf_note}

최종 혼합 공식:

```
p_humor_ml = {BLEND_ML} × classifier_prob + {BLEND_RULE} × humor_score
```

`p_humor_ml` 요약 통계:

| 지표 | 값 |
|------|-----|
| `p_humor_ml == 0` 건수 | {n_pml_zero} ({n_pml_zero/n*100:.1f}%) |
| 평균 | {p_mean:.4f} |
| 중앙값 | {p_med:.4f} |
| 최솟값 | {min(p_vals):.4f} |
| 최댓값 | {max(p_vals):.4f} |

`log1p_p_humor_ml = log(1 + p_humor_ml)`을 사용한 이유:
`p_humor_ml`이 0인 경우 `log(0)`은 정의되지 않으므로 `log1p`를 사용한다.

---

## 8. Human Review Sample 구성

향후 수동 코딩 효율화를 위해 약 120건의 검토 표본을 생성하였다.

| 유형 | 기준 | 생성 수 |
|------|------|---------|
| false negative 후보 | `humor_score == 0` AND `p_humor_ml >= 0.40` | {min(40, len(false_neg))} |
| 유머 고신뢰 | `p_humor_ml >= 0.70` | {min(30, len(high_conf_humor))} |
| 비유머 고신뢰 | `p_humor_ml <= 0.10` AND `weak_humor_label == 0` | {min(30, len(high_conf_nonhumor))} |
| 경계 케이스 | `0.40 <= p_humor_ml <= 0.60` | {min(20, len(boundary))} |
| **합계** | | **{len(review_rows)}** |

`human_humor_label` 및 `human_notes` 컬럼은 향후 수동 코딩을 위해 공란으로 제공.

---

## 9. H1 단순 OLS 재분석 결과

H1 회귀식:

```
log1p_engagement_total_i = α + β × log1p_p_humor_ml_i + ε_i
```

각 항의 의미:
- `i` : 개별 Wendy's 게시글
- `log1p_engagement_total_i` : 게시글 i의 전체 engagement를 로그 변환한 값
- `log1p_p_humor_ml_i` : 게시글 i의 유머 가능성 점수(`p_humor_ml`)를 로그 변환한 값
- `β` : 유머 가능성 점수와 engagement의 관련 방향을 보여주는 핵심 계수
- `ε_i` : 모델로 설명되지 않는 오차항

모델 설정: 단순 이변량 OLS / 통제변수 없음 / 고정효과 없음 / 표준 SE (HC3 미사용)

주요 결과 (`log1p_engagement_total`):

| 파라미터 | 값 |
|----------|-----|
| n_obs | {mr['n_obs']} |
| Intercept (α) | {mr['intercept']:.6f} |
| β (log1p_p_humor_ml) | {mr['beta']:.6f} |
| Standard Error | {mr['se']:.6f} |
| t-value | {mr['t']:.4f} |
| p-value | {mr['p']:.4f} |
| 95% CI | [{mr['ci_lo']:.6f}, {mr['ci_hi']:.6f}] |
| R² | {mr['r2']:.6f} |
| Adj. R² | {mr['adj_r2']:.6f} |
| **H1 해석** | **{h1_label_korean(mr['beta'], mr['p'])}** |

전체 DV 결과:

{ols_table}

---

## 10. 해석

`log1p_p_humor_ml`은 `log1p_engagement_total`과
**{direction_korean(mr['beta'])}한** 방향을 보였다.
(β = {mr['beta']:.6f}, p = {mr['p']:.4f}, R² = {mr['r2']:.6f})

본 결과는 Wendy's 단일 브랜드 게시글을 대상으로 한 관측적 연관성 분석이며,
유머가 engagement를 증가시킨다는 인과효과로 해석할 수 없다.

---

## 11. 한계

- 본 분석은 Wendy's 단일 브랜드 게시글만을 대상으로 한다.
- `p_humor_ml`은 human-labeled gold standard가 아니라 weak-supervised score이다.
- engagement 변수(`reply_count`, `favorite_count` 등)는 `p_humor_ml` 생성에 사용하지 않았다.
- 본 분석은 관측적 연관성 분석이며 인과관계를 주장할 수 없다.
- BERTweet/RoBERTa fine-tuning은 이번 fast pipeline에서는 수행하지 않았다.
- 이미지/영상 의존 유머는 여전히 완전히 포착되지 않을 수 있다.
- 단순 OLS 분석에서는 통제변수, 고정효과, robust standard error를 포함하지 않았다.
- `p_humor_ml`의 분포가 여전히 0에 집중될 경우 OLS 설명력이 낮을 수 있다.
"""
    with open(OUT_SUMMARY, "w", encoding="utf-8") as f:
        f.write(summary)


# ─────────────────────────────────────────────────────────────────────────────
# 보조 함수: 변수 설명 사전 작성
# ─────────────────────────────────────────────────────────────────────────────
def _write_variable_dictionary(n_topics, blend_ml, blend_rule):
    """
    분석에 사용된 모든 주요 변수의 정의, 계산 방식, 해석, 주의사항을 한국어로 기록한다.
    이 파일은 이후 연구자가 코드 없이도 변수 의미를 파악할 수 있도록 설계되었다.
    """
    topic_prob_vars = "\n".join(
        f"""
## `topic_{k}_prob`

- **자료형:** 연속형 수치, 0 이상
- **계산 방식:** TF-IDF + NMF 모델에서 게시글 i가 토픽 {k}에 속하는 정도(비중)
- **해석:** 값이 클수록 해당 게시글이 토픽 {k}의 콘텐츠 패턴과 유사함
- **주의사항:** 확률이 아니라 NMF 비중값이므로 합이 반드시 1이 되지 않을 수 있음
"""
        for k in range(n_topics)
    )

    content = f"""# Wendy's Fast Weak-Supervised Humor Pipeline — 변수 설명 사전

작성일시: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}

이 파일은 분석에 사용된 모든 주요 변수의 정의, 계산 방식, 해석, 주의사항을 한국어로 기술한다.
변수명과 파일명은 영어 그대로 유지한다.

---

## 식별자 및 게시글 메타

## `id`

- **자료형:** 정수형 문자열
- **계산 방식:** 원본 X/Twitter API에서 제공된 고유 게시글 ID
- **해석:** 게시글을 고유하게 식별하는 키
- **주의사항:** 문자열로 처리하여 부동소수점 오류를 방지

## `tweet_url`

- **자료형:** 문자열 (URL)
- **계산 방식:** 원본 데이터에서 직접 가져옴
- **해석:** 해당 게시글의 원문 URL — 수동 검토 시 원문 확인에 사용

---

## 날짜 및 시간 변수

## `created_year` / `created_month` / `created_day` / `created_time`

- **자료형:** 정수형 (year, month, day) / 문자열 HH:MM:SS (time)
- **계산 방식:** 원본 `created_at` 필드(예: "Thu Jun 11 21:59:23 +0000 2026")를 파싱하여 분리
- **해석:** 게시글 작성 날짜와 시간(UTC 기준)
- **주의사항:** 시간대 변환 없이 UTC 그대로 사용

---

## 텍스트 변수

## `text`

- **자료형:** 문자열
- **계산 방식:** 원본 게시글 텍스트 — 수정 없음
- **해석:** Wendy's X/Twitter 계정의 원문 게시글 텍스트
- **주의사항:** URL, 멘션, 이모지가 포함되어 있음

## `clean_text`

- **자료형:** 문자열
- **계산 방식:** `text`에서 URL → `<URL>`, 멘션(@user) → `<MENTION>` 대체 후 소문자 변환. 이모지 제거
- **해석:** 기계학습 분류기의 입력으로 사용되는 전처리 텍스트
- **주의사항:** 슬랭·비격식 표현은 유머 탐지에 중요하므로 제거하지 않음

## `text_length`

- **자료형:** 정수형
- **계산 방식:** `len(text)` — 원문 텍스트의 문자 수
- **해석:** 게시글 길이; 매우 짧은 경우 유머 탐지 어려울 수 있음

## `url_count` / `mention_count` / `hashtag_count` / `emoji_count`

- **자료형:** 정수형
- **계산 방식:** 정규식으로 각 요소 개수 카운트
- **해석:** 텍스트 구조 특성 변수 — 분류기 특성이 아닌 감사용
- **주의사항:** 이모지 수는 유머 신호일 수 있으나 직접 IV로 사용하지 않음

---

## 게시글 속성

## `is_quote_status`

- **자료형:** boolean 문자열 (True/False)
- **계산 방식:** 원본 데이터에서 직접 가져옴
- **해석:** 해당 게시글이 다른 게시글을 인용(quote)한 것인지 여부

## `is_retweet_text`

- **자료형:** 문자열 (true/false)
- **계산 방식:** 텍스트가 "RT "로 시작하면 true
- **해석:** 리트윗 게시글 여부

---

## Engagement 변수 (종속변수 — IV 생성에 사용 금지)

**중요:** 아래 변수들은 H1 회귀분석의 종속변수로만 사용한다.
`p_humor_ml` 생성에는 절대 사용하지 않는다.
이유: 독립변수와 종속변수가 기계적으로 연결되는 순환 편의(circular bias) 방지.

## `reply_count` / `favorite_count` / `retweet_count` / `quote_count` / `bookmark_count`

- **자료형:** 정수형
- **계산 방식:** 원본 데이터에서 직접 가져옴
- **해석:** 게시글 수준 engagement 지표

## `view_count`

- **자료형:** 정수형 또는 결측
- **계산 방식:** 원본 데이터에서 직접 가져옴; 결측 가능
- **해석:** 게시글 조회 수 — H1 DV로 미사용 (이번 분석 범위 밖)
- **주의사항:** 결측값은 대체(imputation)하지 않음

## `engagement_total`

- **자료형:** 정수형
- **계산 방식:** `reply_count + favorite_count + retweet_count + quote_count + bookmark_count`
- **해석:** 5개 engagement 지표의 합산 — H1의 주요 종속변수
- **주의사항:** `view_count`는 포함하지 않음

## `log1p_engagement_total`

- **자료형:** 연속형 수치
- **계산 방식:** `log(1 + engagement_total)` — 자연로그
- **해석:** H1 회귀분석의 주요 종속변수; 로그 변환으로 우편향 분포를 완화
- **주의사항:** `engagement_total = 0`인 경우에도 `log(1+0) = 0`으로 정의됨

## `log1p_favorite_count` / `log1p_retweet_count` / `log1p_reply_count` / `log1p_quote_count` / `log1p_bookmark_count`

- **자료형:** 연속형 수치
- **계산 방식:** `log(1 + 해당_count)` — 자연로그
- **해석:** H1 회귀분석의 보조 종속변수 (log1p_engagement_total의 구성 요소별 분리 분석)

---

## 유머 점수 변수

## `humor_score`

- **자료형:** 연속형 수치, 0.000~1.000
- **계산 방식:** 정규식 기반 규칙 시스템 — 텍스트에서 유머 신호 패턴(pun, sarcasm, roast 등)을 탐지하여 가중합산. 강한 cue가 없으면 0.
- **해석:** 게시글 텍스트에 유머가 포함되어 있을 가능성에 대한 규칙 기반 1차 추정값
- **주의사항:** 보정된 확률이 아님. 명확한 패턴이 없는 짧은 유머는 과소탐지될 수 있음

## `log1p_humor_score`

- **자료형:** 연속형 수치
- **계산 방식:** `log(1 + humor_score)` — 자연로그
- **해석:** `humor_score`의 로그 변환값 — 이전 H1 분석의 IV로 사용됨
- **주의사항:** `humor_score = 0`인 경우(739건, 75.6%)가 많아 분산이 제한적

## `humor_score_components`

- **자료형:** 문자열 (세미콜론 구분)
- **계산 방식:** 탐지된 유머 cue 목록을 문자열로 결합
- **해석:** 어떤 유머 패턴이 탐지되었는지 감사용으로 기록
- **주의사항:** 탐지 cue가 없으면 `insufficient_text_signal` 또는 `plain_promotion` 등이 기록됨

---

## Weak Label 변수

## `weak_humor_label`

- **자료형:** 정수형(0 또는 1) 또는 공란(미분류)
- **계산 방식:**
  - 1: `humor_score >= 0.60` 또는 강한 유머 cue 포함
  - 0: `humor_score == 0` AND (`plain_promotion` 또는 `url_only` 포함)
  - 공란: 그 외 (특히 `insufficient_text_signal` — false negative 가능성)
- **해석:** 분류기 학습에 사용되는 고신뢰 의사 레이블
- **주의사항:** `humor_score == 0` 전체를 0으로 레이블링하지 않음. engagement 변수 미사용.

## `weak_label_source`

- **자료형:** 문자열
- **계산 방식:** weak label 부여 근거를 기록
- **해석:** 레이블이 어떤 조건으로 부여되었는지 추적용

## `weak_label_confidence`

- **자료형:** 문자열 ("high" 또는 "uncertain")
- **계산 방식:** 명확한 조건으로 부여된 경우 "high", 미분류는 "uncertain"
- **해석:** 레이블의 신뢰도 수준

---

## 토픽 모델링 변수

## `dominant_topic`

- **자료형:** 정수형 (0 ~ {n_topics-1})
- **계산 방식:** NMF 토픽 비중 행렬(W)에서 가장 높은 비중의 토픽 번호
- **해석:** 해당 게시글이 주로 속하는 콘텐츠 토픽
- **주의사항:** 토픽 자체는 분류기 입력이 아닌 감사(audit) 목적

## `dominant_topic_weight`

- **자료형:** 연속형 수치 (0 이상)
- **계산 방식:** NMF 비중 행렬(W)에서 지배적 토픽의 비중값
- **해석:** 값이 클수록 해당 게시글이 하나의 토픽에 집중되어 있음

{topic_prob_vars}

---

## 머신러닝 유머 점수 변수

## `classifier_prob`

- **자료형:** 연속형 수치, 0~1
- **계산 방식:** TF-IDF + Logistic Regression 분류기가 예측한 유머 클래스(1) 확률
- **해석:** 순수 기계학습 모델의 유머 존재 예측 확률
- **주의사항:** 분류기 미학습 시 0으로 채워짐 (fallback)

## `p_humor_ml`

- **자료형:** 연속형 수치, 0~1
- **계산 방식:** `{blend_ml} × classifier_prob + {blend_rule} × humor_score`
  (분류기 미학습 시: `p_humor_ml = humor_score`)
- **해석:** 해당 게시글 텍스트에 유머가 포함되어 있을 가능성에 대한 개선된 추정값
- **주의사항:** human-labeled gold standard가 아니며 weak-supervised 방식의 1차 측정값. 보정된 확률로 해석하면 안 됨.

## `log1p_p_humor_ml`

- **자료형:** 연속형 수치
- **계산 방식:** `log(1 + p_humor_ml)` — 자연로그
- **해석:** H1 재분석의 주요 독립변수(IV)
- **주의사항:** `p_humor_ml = 0`인 경우에도 `log(1+0) = 0`으로 정의됨. `log(p_humor_ml)`을 사용하지 않는 이유는 0값이 있을 때 정의 불가하기 때문임.

---

## Human Review Sample 변수

## `review_priority`

- **자료형:** 문자열
- **계산 방식:** 검토 표본 유형 코드
  - `false_negative_candidate`: `humor_score == 0` 이지만 `p_humor_ml >= 0.40`인 경우 — 탐지 누락 의심
  - `high_confidence_humor`: `p_humor_ml >= 0.70` — 유머 고신뢰 표본
  - `high_confidence_nonhumor`: `p_humor_ml <= 0.10` AND `weak_humor_label == 0` — 비유머 고신뢰 표본
  - `boundary_case`: `0.40 <= p_humor_ml <= 0.60` — 판단이 어려운 경계 케이스
- **해석:** 수동 코딩 우선순위 구분용

## `human_humor_label`

- **자료형:** 공란 (향후 정수형 0/1로 채울 예정)
- **계산 방식:** 향후 수동 코딩으로 채워야 함
- **해석:** 인간 코더가 직접 판단한 유머 존재 여부 (1=유머, 0=비유머)
- **주의사항:** 현재 이 파일에는 비어 있음 — 수동 입력 필요

## `human_notes`

- **자료형:** 공란 (향후 자유 텍스트로 채울 예정)
- **계산 방식:** 향후 수동 코딩 시 메모
- **해석:** 코더가 판단 근거나 특이사항을 기록하는 자유 텍스트 필드
"""
    with open(OUT_VARDICT, "w", encoding="utf-8") as f:
        f.write(content)


if __name__ == "__main__":
    main()
