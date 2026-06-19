#!/usr/bin/env python3
"""Run v2 Wendy's-expanded classifier and fixed simple OLS baseline.

This is a separate v2 pipeline. It does not modify f945aca
`simple_ols_baseline_main/` outputs.

Fixed analysis formulas:
  H1/H2 post-level:
    log(1+Engagement_i) = b0 + b1*Aggressive_i + b2*Affiliative_i
                          + b3*SelfEnhancing_i + b4*SelfDefeating_i + e_i
  H3 firm-quarter:
    Mean log(1+Engagement)_{fq} = a + b1*AggIntensity_{fq}
                                  + b2*AggIntensity^2_{fq} + e_{fq}

No controls. No fixed effects. No OOF. No firm-month H3.
"""
from __future__ import annotations

import csv
import math
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

PYPACKAGES = Path('/home/user/.local/pypackages')
if str(PYPACKAGES) not in sys.path:
    sys.path.insert(0, str(PYPACKAGES))

import numpy as np
from scipy import stats
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.multiclass import OneVsRestClassifier
from sklearn.pipeline import FeatureUnion, Pipeline

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
DATA = OUT / 'data'

TRAINING_V2 = ROOT / '20260618expand/classifier_improvement/wendys_label_integration_audit/training_labels_v2_with_wendys.csv'
CORPUS = ROOT / '20260618expand/classifier_improvement/h1_presence_only/integrated_collected_corpus/data/integrated_collected_post_corpus.csv'
BASELINE = ROOT / '20260618expand/ols_hypothesis_results/simple_ols_baseline_main'

TWITTER_FMT = '%a %b %d %H:%M:%S +0000 %Y'
TYPE_LABELS = ['aggressive', 'affiliative', 'self_enhancing', 'self_defeating']
LABEL_TO_TYPE = {'1': 'aggressive', '2': 'affiliative', '3': 'self_enhancing', '4': 'self_defeating'}
CLASSIFIER_MODEL = 'v2_wendys_word_char_tfidf_logreg_fixed'
CLASSIFIER_SCOPE = 'training_labels_v2_with_wendys_3046'


def read_csv(path: Path, encoding='utf-8-sig') -> list[dict[str, str]]:
    with path.open(newline='', encoding=encoding) as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore', lineterminator='\n')
        w.writeheader()
        w.writerows(rows)


def preprocess(text: str) -> str:
    text = text or ''
    text = re.sub(r'https?://\S+', '<URL>', text)
    text = re.sub(r'@\w+', '<MENTION>', text)
    text = re.sub(r'#(\w+)', r'\1', text)
    return re.sub(r'\s+', ' ', text.lower()).strip()


def build_fixed_pipeline(multiclass_ovr: bool = False) -> Pipeline:
    features = FeatureUnion([
        ('word', TfidfVectorizer(
            lowercase=True, ngram_range=(1, 2), min_df=2,
            max_df=0.95, sublinear_tf=True,
        )),
        ('char_wb', TfidfVectorizer(
            lowercase=True, analyzer='char_wb', ngram_range=(3, 5),
            min_df=2, max_df=0.95, sublinear_tf=True,
        )),
    ])
    base_clf = LogisticRegression(
        solver='liblinear', C=0.1, class_weight='balanced',
        max_iter=2000, random_state=42,
    )
    clf = OneVsRestClassifier(base_clf) if multiclass_ovr else base_clf
    return Pipeline([
        ('features', features),
        ('clf', clf),
    ])


def to_f(v, default=0.0) -> float:
    try:
        if v in (None, ''):
            return default
        return float(v)
    except Exception:
        return default


def stars(p: float) -> str:
    if p < 0.01:
        return '***'
    if p < 0.05:
        return '**'
    if p < 0.10:
        return '*'
    return ''


def parse_quarter_from_row(row: dict[str, str]) -> str:
    ym = row.get('year_month') or row.get('period') or ''
    if re.fullmatch(r'\d{4}-\d{2}', ym):
        y, m = ym.split('-')
        q = (int(m) - 1) // 3 + 1
        return f'{y}-Q{q}'
    raw = row.get('created_at') or row.get('created_at_raw') or ''
    try:
        dt = datetime.strptime(raw.strip(), TWITTER_FMT)
        q = (dt.month - 1) // 3 + 1
        return f'{dt.year}-Q{q}'
    except Exception:
        return 'missing'


def ols_fit(X: np.ndarray, y: np.ndarray):
    n, k = X.shape
    b, _, _, _ = np.linalg.lstsq(X, y, rcond=None)
    yhat = X @ b
    resid = y - yhat
    ssr = float(resid @ resid)
    s2 = ssr / (n - k)
    XtXi = np.linalg.inv(X.T @ X)
    V = s2 * XtXi
    se = np.sqrt(np.diag(V))
    t_stats = b / se
    p_vals = 2 * stats.t.sf(np.abs(t_stats), df=n-k)
    ss_tot = float(np.sum((y - float(np.mean(y))) ** 2))
    r2 = 1 - ssr / ss_tot if ss_tot > 0 else 0.0
    adj = 1 - (1 - r2) * (n - 1) / (n - k) if n > k else 0.0
    return b, V, se, t_stats, p_vals, n, k, r2, adj, n-k


def contrast(c: list[float], b_sub: np.ndarray, V_sub: np.ndarray, df: int):
    c_arr = np.array(c, dtype=float)
    est = float(c_arr @ b_sub)
    var = float(c_arr @ V_sub @ c_arr)
    se = math.sqrt(max(var, 0.0))
    if se == 0:
        return est, se, float('nan'), float('nan')
    t = est / se
    p = 2 * stats.t.sf(abs(t), df)
    return est, se, t, float(p)


def h1h2_ols(rows: list[dict[str, str]], model: str):
    y = np.array([to_f(r['log_total_engagement']) for r in rows])
    agg = np.array([to_f(r['aggressive_humor']) for r in rows])
    aff = np.array([to_f(r['affiliative_humor']) for r in rows])
    se = np.array([to_f(r['self_enhancing_humor']) for r in rows])
    sd = np.array([to_f(r['self_defeating_humor']) for r in rows])
    X = np.column_stack([np.ones(len(rows)), agg, aff, se, sd])
    b, V, ses, t, p, n, k, r2, adj, df = ols_fit(X, y)
    names = ['intercept', 'aggressive', 'affiliative', 'self_enhancing', 'self_defeating']
    coef_rows = []
    for i, name in enumerate(names):
        coef_rows.append({
            'model': model, 'term': name,
            'coefficient': round(float(b[i]), 6),
            'std_error': round(float(ses[i]), 6),
            't_statistic': round(float(t[i]), 4),
            'p_value': round(float(p[i]), 6),
            'stars': stars(float(p[i])),
            'n': n, 'r_squared': round(r2, 6),
            'adj_r_squared': round(adj, 6), 'df_residual': df,
            'controls_included': 'false', 'fixed_effects_included': 'false',
        })
    counts = {
        'aggressive': int(agg.sum()), 'affiliative': int(aff.sum()),
        'self_enhancing': int(se.sum()), 'self_defeating': int(sd.sum()),
    }
    counts['non_humorous'] = n - sum(counts.values())
    return b, V, p, df, coef_rows, counts, n, r2, adj


def h1h2_contrasts(b, V, df, counts, model):
    n_agg = counts['aggressive']; n_aff = counts['affiliative']
    n_se = counts['self_enhancing']; n_sd = counts['self_defeating']
    n_humor = n_agg + n_aff + n_se + n_sd
    n_other = n_aff + n_se + n_sd
    n_self = n_se + n_sd
    b_sub = b[1:5]
    V_sub = V[1:5, 1:5]
    rows = []
    specs = []
    if n_humor:
        specs.append(('H1', 'Weighted Humor Effect (vs non-humorous)', [n_agg/n_humor, n_aff/n_humor, n_se/n_humor, n_sd/n_humor]))
    if n_other:
        specs.append(('H2-1', 'Aggressive - Other humor (weighted avg)', [1, -n_aff/n_other, -n_se/n_other, -n_sd/n_other]))
    specs += [
        ('H2-2', 'Aggressive - Affiliative', [1, -1, 0, 0]),
        ('H2-2', 'Aggressive - Self-Enhancing', [1, 0, -1, 0]),
        ('H2-2', 'Aggressive - Self-Defeating', [1, 0, 0, -1]),
    ]
    if n_self:
        specs.append(('H2-3', 'Aggressive - SELF (se+sd weighted avg)', [1, 0, -n_se/n_self, -n_sd/n_self]))
    for hyp, label, c in specs:
        est, se, t, p = contrast(c, b_sub, V_sub, df)
        rows.append({
            'model': model, 'hypothesis': hyp, 'contrast': label,
            'estimate': round(est, 6), 'std_error': round(se, 6),
            't_statistic': round(t, 4) if not math.isnan(t) else 'NA',
            'p_value': round(p, 6) if not math.isnan(p) else 'NA',
            'stars': stars(p) if not math.isnan(p) else '',
            'direction': 'positive' if est > 0 else 'negative',
            'support': 'supported' if est > 0 and not math.isnan(p) and p < 0.10 else 'not_supported',
        })
    return rows


def aggregate_firm_quarter(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    panel = {}
    for r in rows:
        q = parse_quarter_from_row(r)
        if q == 'missing':
            continue
        key = (r['company_name'], q)
        if key not in panel:
            panel[key] = {'post_count': 0, 'agg': 0, 'log_sum': 0.0}
        p = panel[key]
        p['post_count'] += 1
        p['agg'] += int(to_f(r.get('aggressive_humor', '0')))
        p['log_sum'] += to_f(r.get('log_total_engagement', '0'))
    out = []
    for (company, quarter), p in panel.items():
        n = p['post_count']
        intensity = p['agg'] / n if n else 0.0
        out.append({
            'company_name': company, 'quarter': quarter,
            'post_count': n, 'aggressive_count': p['agg'],
            'aggressive_intensity': round(intensity, 12),
            'aggressive_intensity_sq': round(intensity * intensity, 12),
            'mean_log1p_engagement': round(p['log_sum'] / n, 6),
        })
    return out


def h3_ols(panel_rows: list[dict[str, str]], model: str):
    y = np.array([to_f(r['mean_log1p_engagement']) for r in panel_rows])
    x1 = np.array([to_f(r['aggressive_intensity']) for r in panel_rows])
    x2 = np.array([to_f(r['aggressive_intensity_sq']) for r in panel_rows])
    X = np.column_stack([np.ones(len(panel_rows)), x1, x2])
    b, V, ses, t, p, n, k, r2, adj, df = ols_fit(X, y)
    names = ['intercept', 'aggressive_intensity', 'aggressive_intensity_sq']
    coef_rows = []
    for i, name in enumerate(names):
        coef_rows.append({
            'model': model, 'term': name,
            'coefficient': round(float(b[i]), 6),
            'std_error': round(float(ses[i]), 6),
            't_statistic': round(float(t[i]), 4),
            'p_value': round(float(p[i]), 6),
            'stars': stars(float(p[i])),
            'n': n, 'r_squared': round(r2, 6),
            'adj_r_squared': round(adj, 6), 'df_residual': df,
            'unit_of_analysis': 'firm-quarter',
            'controls_included': 'false', 'fixed_effects_included': 'false',
        })
    beta1 = float(b[1]); beta2 = float(b[2])
    tp = -beta1 / (2 * beta2) if beta2 != 0 else float('inf')
    obs_min = float(x1.min()) if len(x1) else float('nan')
    obs_max = float(x1.max()) if len(x1) else float('nan')
    in_range = obs_min <= tp <= obs_max if math.isfinite(tp) else False
    h3 = beta1 > 0 and beta2 < 0 and float(p[2]) < 0.10 and in_range
    pattern = 'inverted-U' if beta1 > 0 and beta2 < 0 else ('U-shaped' if beta1 < 0 and beta2 > 0 else 'no curvature support')
    diag = {
        'model': model, 'n_firm_quarters': n,
        'beta1_intensity': round(beta1, 6), 'beta1_p': round(float(p[1]), 6),
        'beta2_intensity_sq': round(beta2, 6), 'beta2_p': round(float(p[2]), 6),
        'turning_point': round(tp, 6) if math.isfinite(tp) else 'Inf',
        'observed_intensity_min': round(obs_min, 6),
        'observed_intensity_max': round(obs_max, 6),
        'turning_point_in_observed_range': str(in_range).lower(),
        'pattern': pattern, 'H3_supported': str(h3).lower(),
        'r_squared': round(r2, 6), 'adj_r_squared': round(adj, 6),
        'unit_of_analysis': 'firm-quarter',
        'controls_included': 'false', 'fixed_effects_included': 'false',
    }
    return coef_rows, diag



def status_id_from_url(url: str | None) -> str:
    m = re.search(r'/status/(\d+)', url or '')
    return m.group(1) if m else ''


def digits_or_blank(value: str | None) -> str:
    value = (value or '').strip()
    return value if re.fullmatch(r'\d{6,}', value) else ''


def text_hash_value(text: str | None) -> str:
    normalized = re.sub(r'\s+', ' ', (text or '').strip()).lower()
    return __import__('hashlib').sha1(normalized.encode('utf-8')).hexdigest()[:20] if normalized else ''


def build_corpus_lookup(corpus_rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    lookup: dict[str, dict[str, str]] = {}
    for r in corpus_rows:
        sid = digits_or_blank(r.get('tweet_id')) or status_id_from_url(r.get('tweet_url')) or digits_or_blank(r.get('stable_source_id'))
        if sid:
            lookup.setdefault(f'status_id:{sid}', r)
        th = text_hash_value(r.get('text'))
        if th:
            lookup.setdefault(f'text_hash:{th}', r)
    return lookup

def build_human_coded_rows(training_rows: list[dict[str, str]], corpus_lookup: dict[str, dict[str, str]]) -> list[dict[str, str]]:
    rows = []
    for r in training_rows:
        label = r['normalized_label']
        sid = digits_or_blank(r.get('status_id')) or digits_or_blank(r.get('tweet_id')) or status_id_from_url(r.get('tweet_url'))
        match = corpus_lookup.get(f'status_id:{sid}') if sid else None
        if match is None:
            th = r.get('text_hash') or text_hash_value(r.get('text'))
            match = corpus_lookup.get(f'text_hash:{th}') if th else None
        if match is None:
            continue
        log_eng = to_f(match.get('log_total_engagement'), default=None)
        if log_eng is None:
            log_eng = math.log1p(to_f(match.get('total_engagement')))
        rows.append({
            'company_name': match.get('company_name') or r.get('company_name', ''),
            'created_at': match.get('created_at_raw') or match.get('created_at') or r.get('created_at', ''),
            'year_month': match.get('year_month', ''),
            'log_total_engagement': str(log_eng),
            'aggressive_humor': '1' if label == '1' else '0',
            'affiliative_humor': '1' if label == '2' else '0',
            'self_enhancing_humor': '1' if label == '3' else '0',
            'self_defeating_humor': '1' if label == '4' else '0',
            'non_humorous': '1' if label == '0' else '0',
            'source': r.get('source', ''),
        })
    return rows


def train_and_classify(training_rows: list[dict[str, str]], corpus_rows: list[dict[str, str]]):
    presence_train = [r for r in training_rows if r['normalized_label'] in {'0', '1', '2', '3', '4'} and r.get('text')]
    type_train = [r for r in training_rows if r['normalized_label'] in {'1', '2', '3', '4'} and r.get('text')]

    presence_pipe = build_fixed_pipeline()
    Xp = [preprocess(r['text']) for r in presence_train]
    yp = [0 if r['normalized_label'] == '0' else 1 for r in presence_train]
    presence_pipe.fit(Xp, yp)

    type_pipe = build_fixed_pipeline(multiclass_ovr=True)
    Xt = [preprocess(r['text']) for r in type_train]
    yt = [LABEL_TO_TYPE[r['normalized_label']] for r in type_train]
    type_pipe.fit(Xt, yt)

    classified = []
    texts = [preprocess(r.get('text', '')) for r in corpus_rows]
    probs = presence_pipe.predict_proba(texts)[:, 1]
    for r, prob, text_pp in zip(corpus_rows, probs, texts):
        presence = '1' if prob >= 0.5 else '0'
        htype = 'non_humorous'
        htype_score = 0.0
        agg = aff = se = sd = '0'
        non = '1' if presence == '0' else '0'
        if presence == '1':
            type_probs = type_pipe.predict_proba([text_pp])[0]
            idx = int(np.argmax(type_probs))
            htype = str(type_pipe.classes_[idx])
            htype_score = float(type_probs[idx])
            agg = '1' if htype == 'aggressive' else '0'
            aff = '1' if htype == 'affiliative' else '0'
            se = '1' if htype == 'self_enhancing' else '0'
            sd = '1' if htype == 'self_defeating' else '0'
        classified.append({
            **r,
            'created_at': r.get('created_at_raw', '') or r.get('created_at', ''),
            'humor_presence': presence,
            'humor_presence_score': f'{prob:.6f}',
            'classification_status': 'ok',
            'humor_type': htype,
            'humor_type_score': f'{htype_score:.6f}',
            'aggressive_humor': agg,
            'affiliative_humor': aff,
            'self_enhancing_humor': se,
            'self_defeating_humor': sd,
            'non_humorous': non,
            'classifier_name': CLASSIFIER_MODEL,
            'classifier_version': 'v2_training_labels_with_wendys',
            'training_label_source': 'training_labels_v2_with_wendys.csv',
            'classification_confidence': f'{max(prob, 1-prob):.6f}',
        })
    diagnostics = {
        'presence_training_rows': len(presence_train),
        'type_training_rows': len(type_train),
        'presence_humor_rows': sum(yp),
        'presence_non_humor_rows': len(yp) - sum(yp),
        **{f'type_train_{k}': v for k, v in Counter(yt).items()},
    }
    return classified, diagnostics


def build_regression_rows(classified: list[dict[str, str]]) -> list[dict[str, str]]:
    out = []
    for r in classified:
        out.append({
            'integrated_post_id': r.get('integrated_post_id', ''),
            'source_dataset': r.get('source_dataset', ''),
            'company_name': r.get('company_name', ''),
            'source_x_handle': r.get('source_x_handle') or r.get('x_handle', ''),
            'tweet_id': r.get('tweet_id', ''),
            'tweet_url': r.get('tweet_url', ''),
            'created_at': r.get('created_at', ''),
            'year_month': r.get('year_month', ''),
            'log_total_engagement': f"{to_f(r.get('log_total_engagement')):.6f}",
            'total_engagement': r.get('total_engagement', ''),
            'text_length': r.get('text_length', ''),
            'hashtag_count': r.get('hashtag_count', ''),
            'mention_count': r.get('mention_count', ''),
            'humor_presence': r.get('humor_presence', ''),
            'humor_type': r.get('humor_type', ''),
            'aggressive_humor': r.get('aggressive_humor', '0'),
            'affiliative_humor': r.get('affiliative_humor', '0'),
            'self_enhancing_humor': r.get('self_enhancing_humor', '0'),
            'self_defeating_humor': r.get('self_defeating_humor', '0'),
            'non_humorous': r.get('non_humorous', '0'),
        })
    return out


def write_distribution(classified, training_rows, diagnostics):
    pres = Counter(r['humor_presence'] for r in classified)
    typ = Counter(r['humor_type'] for r in classified)
    training = Counter(r['normalized_label'] for r in training_rows)
    rows = []
    for label, n in pres.items():
        rows.append({'category': 'v2_full_sample_presence', 'label': label, 'n': n, 'pct': round(n/len(classified)*100, 4)})
    for label, n in typ.items():
        rows.append({'category': 'v2_full_sample_type', 'label': label, 'n': n, 'pct': round(n/len(classified)*100, 4)})
    for label in ['0', '1', '2', '3', '4']:
        n = training.get(label, 0)
        rows.append({'category': 'v2_training_labels', 'label': label, 'n': n, 'pct': round(n/len(training_rows)*100, 4)})
    write_csv(OUT / '00_v2_classified_data_distribution.csv', rows, ['category', 'label', 'n', 'pct'])
    md = [
        '# 00 V2 Classified Data Summary', '',
        '| Item | Value |', '|:--|--:|',
        f'| Integrated corpus posts | {len(classified):,} |',
        f'| Training labels v2 | {len(training_rows):,} |',
        f'| Presence training rows | {diagnostics["presence_training_rows"]:,} |',
        f'| Type training rows | {diagnostics["type_training_rows"]:,} |',
        f'| Full-sample humorous posts | {pres.get("1", 0):,} |',
        f'| Full-sample non-humorous posts | {pres.get("0", 0):,} |',
        f'| Full-sample aggressive posts | {typ.get("aggressive", 0):,} |',
        '',
        'Boundary: v2 changes classifier training labels only. The fixed simple OLS formulas remain unchanged.',
    ]
    (OUT / '00_v2_classified_data_summary.md').write_text('\n'.join(md) + '\n', encoding='utf-8')


def baseline_vs_v2(v2_full, v2_human, h3_diag):
    rows = []
    baseline_files = {
        'h1h2_full': BASELINE / '01_simple_ols_h1_h2_full_sample_results.csv',
        'h1h2_human': BASELINE / '01_simple_ols_h1_h2_human_coded_results.csv',
        'h3': BASELINE / '01_simple_ols_h3_quadratic_diagnostics.csv',
    }
    base_full = read_csv(baseline_files['h1h2_full']) if baseline_files['h1h2_full'].exists() else []
    base_human = read_csv(baseline_files['h1h2_human']) if baseline_files['h1h2_human'].exists() else []
    base_h3 = read_csv(baseline_files['h3']) if baseline_files['h3'].exists() else []

    def index(rows, key):
        return {r[key]: r for r in rows if key in r}
    bfi = index(base_full, 'term'); bhi = index(base_human, 'term')
    vfi = index(v2_full, 'term'); vhi = index(v2_human, 'term')
    for term in ['aggressive', 'affiliative', 'self_enhancing', 'self_defeating']:
        if term in bfi and term in vfi:
            rows.append({
                'comparison': 'full_sample_h1_h2', 'term': term,
                'baseline_coefficient': bfi[term].get('coefficient'),
                'v2_coefficient': vfi[term].get('coefficient'),
                'difference_v2_minus_baseline': round(to_f(vfi[term].get('coefficient')) - to_f(bfi[term].get('coefficient')), 6),
                'baseline_p_value': bfi[term].get('p_value'),
                'v2_p_value': vfi[term].get('p_value'),
            })
        if term in bhi and term in vhi:
            rows.append({
                'comparison': 'human_coded_h1_h2', 'term': term,
                'baseline_coefficient': bhi[term].get('coefficient'),
                'v2_coefficient': vhi[term].get('coefficient'),
                'difference_v2_minus_baseline': round(to_f(vhi[term].get('coefficient')) - to_f(bhi[term].get('coefficient')), 6),
                'baseline_p_value': bhi[term].get('p_value'),
                'v2_p_value': vhi[term].get('p_value'),
            })
    if base_h3:
        base_full_h3 = next((r for r in base_h3 if r.get('model') == 'Full_sample_H3'), base_h3[0])
        for term, bkey, vkey in [
            ('beta1_intensity', 'beta1_intensity', 'beta1_intensity'),
            ('beta2_intensity_sq', 'beta2_intensity_sq', 'beta2_intensity_sq'),
            ('turning_point', 'turning_point', 'turning_point'),
        ]:
            rows.append({
                'comparison': 'full_sample_h3', 'term': term,
                'baseline_coefficient': base_full_h3.get(bkey, ''),
                'v2_coefficient': h3_diag.get(vkey, ''),
                'difference_v2_minus_baseline': round(to_f(str(h3_diag.get(vkey, ''))) - to_f(base_full_h3.get(bkey, '')), 6),
                'baseline_p_value': base_full_h3.get('beta2_p' if 'beta2' in term else 'beta1_p', ''),
                'v2_p_value': h3_diag.get('beta2_p' if 'beta2' in term else 'beta1_p', ''),
            })
    write_csv(OUT / 'baseline_f945aca_vs_v2_comparison.csv', rows, ['comparison','term','baseline_coefficient','v2_coefficient','difference_v2_minus_baseline','baseline_p_value','v2_p_value'])
    md = ['# Baseline f945aca vs v2 Wendy\'s Comparison', '', 'This comparison is descriptive. V2 changes classifier training labels only; fixed OLS formulas are unchanged.', '', '| Comparison | Term | Baseline | V2 | Difference |', '|:--|:--|--:|--:|--:|']
    for r in rows:
        md.append(f"| {r['comparison']} | {r['term']} | {r['baseline_coefficient']} | {r['v2_coefficient']} | {r['difference_v2_minus_baseline']} |")
    (OUT / 'baseline_f945aca_vs_v2_comparison.md').write_text('\n'.join(md) + '\n', encoding='utf-8')


def write_interpretation(full_counts, human_counts, full_diag, human_diag):
    lines = [
        '# 01 V2 Simple OLS Interpretation', '',
        'This v2 run uses `training_labels_v2_with_wendys.csv` for classifier retraining and reclassifies the integrated collected corpus.', '',
        'Fixed formulas are unchanged from f945aca:', '',
        '- H1/H2 post-level OLS with aggressive, affiliative, self_enhancing, self_defeating dummies only; non-humorous is the reference category.',
        '- H3 firm-quarter quadratic OLS with aggressive usage intensity and squared intensity only.',
        '- No controls, no fixed effects, no OOF, no firm-month H3.', '',
        '## V2 label/classification counts', '',
        f"- Full-sample aggressive posts: {full_counts['aggressive']:,}",
        f"- Full-sample affiliative posts: {full_counts['affiliative']:,}",
        f"- Full-sample self-enhancing posts: {full_counts['self_enhancing']:,}",
        f"- Full-sample self-defeating posts: {full_counts['self_defeating']:,}",
        f"- Full-sample non-humorous posts: {full_counts['non_humorous']:,}",
        f"- Human-coded v2 aggressive labels: {human_counts['aggressive']:,}",
        '',
        '## H3 diagnostic', '',
        f"- beta1 intensity: {full_diag.get('beta1_intensity')} (p={full_diag.get('beta1_p')})",
        f"- beta2 intensity squared: {full_diag.get('beta2_intensity_sq')} (p={full_diag.get('beta2_p')})",
        f"- turning point: {full_diag.get('turning_point')}",
        f"- turning point in observed range: {full_diag.get('turning_point_in_observed_range')}",
        f"- H3 supported by this simple diagnostic: {full_diag.get('H3_supported')}",
        '',
        'Boundary: this is not causal evidence. It is a v2 classifier-based rerun of the already fixed simple OLS baseline.',
    ]
    (OUT / '01_simple_ols_interpretation.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')


def main():
    print('=== run_simple_ols_baseline_v2_wendys ===')
    DATA.mkdir(parents=True, exist_ok=True)
    training_rows = read_csv(TRAINING_V2)
    corpus_rows = read_csv(CORPUS, encoding='utf-8')
    print(f'training_v2_rows={len(training_rows)}')
    print(f'integrated_corpus_rows={len(corpus_rows)}')

    classified, train_diag = train_and_classify(training_rows, corpus_rows)
    classified_fields = list(classified[0].keys())
    write_csv(DATA / 'v2_domain_adapted_humor_classification.csv', classified, classified_fields)

    reg_rows = build_regression_rows(classified)
    reg_fields = list(reg_rows[0].keys())
    write_csv(DATA / 'v2_post_level_regression_ready.csv', reg_rows, reg_fields)
    write_distribution(classified, training_rows, train_diag)

    corpus_lookup = build_corpus_lookup(corpus_rows)
    human_rows = build_human_coded_rows(training_rows, corpus_lookup)
    b_full, V_full, p_full, df_full, full_coef, full_counts, n_full, r2_full, adj_full = h1h2_ols(reg_rows, 'V2_full_sample_simple_OLS')
    b_hc, V_hc, p_hc, df_hc, human_coef, human_counts, n_hc, r2_hc, adj_hc = h1h2_ols(human_rows, 'V2_human_coded_simple_OLS')
    write_csv(OUT / '01_simple_ols_h1_h2_full_sample_results.csv', full_coef, list(full_coef[0].keys()))
    write_csv(OUT / '01_simple_ols_h1_h2_human_coded_results.csv', human_coef, list(human_coef[0].keys()))
    contrast_rows = h1h2_contrasts(b_full, V_full, df_full, full_counts, 'V2_full_sample') + h1h2_contrasts(b_hc, V_hc, df_hc, human_counts, 'V2_human_coded')
    write_csv(OUT / '01_simple_ols_h1_h2_contrast_tests.csv', contrast_rows, list(contrast_rows[0].keys()))

    fq_full = aggregate_firm_quarter(reg_rows)
    write_csv(DATA / 'v2_h3_firm_quarter_panel.csv', fq_full, list(fq_full[0].keys()))
    h3_full_coef, h3_full_diag = h3_ols(fq_full, 'V2_full_sample_H3')
    fq_human = aggregate_firm_quarter(human_rows)
    write_csv(DATA / 'v2_human_coded_firm_quarter_panel.csv', fq_human, list(fq_human[0].keys()) if fq_human else ['company_name','quarter'])
    h3_human_coef, h3_human_diag = h3_ols(fq_human, 'V2_human_coded_H3') if len(fq_human) >= 3 else ([], {'model':'V2_human_coded_H3','H3_supported':'insufficient_data','n_firm_quarters':len(fq_human)})
    write_csv(OUT / '01_simple_ols_h3_full_sample_results.csv', h3_full_coef, list(h3_full_coef[0].keys()))
    write_csv(OUT / '01_simple_ols_h3_human_coded_results.csv', h3_human_coef if h3_human_coef else [{'model':'V2_human_coded_H3','term':'NOTE','coefficient':'insufficient_data','n':len(fq_human)}], list(h3_full_coef[0].keys()))
    diag_rows = [h3_full_diag, h3_human_diag]
    diag_fields = sorted({k for r in diag_rows for k in r.keys()})
    write_csv(OUT / '01_simple_ols_h3_quadratic_diagnostics.csv', diag_rows, diag_fields)

    train_diag['human_coded_rows_matched_to_corpus'] = len(human_rows)
    train_diag_rows = [{'metric': k, 'value': v} for k, v in sorted(train_diag.items())]
    write_csv(OUT / 'v2_training_and_classification_diagnostics.csv', train_diag_rows, ['metric','value'])
    baseline_vs_v2(full_coef, human_coef, h3_full_diag)
    write_interpretation(full_counts, human_counts, h3_full_diag, h3_human_diag)

    print(f'classified_rows={len(classified)}')
    print(f'full_counts={full_counts}')
    print(f'human_counts={human_counts}')
    print(f'h3_full={h3_full_diag}')
    print(f'outputs={OUT}')
    print('=== COMPLETE ===')


if __name__ == '__main__':
    main()
