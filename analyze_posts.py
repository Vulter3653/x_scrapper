import json
import os
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from sklearn.decomposition import LatentDirichletAllocation
from sklearn.feature_extraction.text import CountVectorizer, ENGLISH_STOP_WORDS
from transformers import pipeline

TARGET_USER = os.getenv('TARGET_USER', 'Wendys').lstrip('@')
PREFIX = TARGET_USER.lower()
INPUT_FILE = Path(os.getenv('INPUT_FILE', f'{PREFIX}_posts.json'))
LDA_TOPICS_FILE = Path(os.getenv('LDA_TOPICS_FILE', f'{PREFIX}_lda_topics.json'))
LDA_REPORT_FILE = Path(os.getenv('LDA_REPORT_FILE', f'{PREFIX}_lda_topics.md'))
SENTIMENT_FILE = Path(os.getenv('SENTIMENT_FILE', f'{PREFIX}_zero_shot_sentiment.json'))
SENTIMENT_REPORT_FILE = Path(os.getenv('SENTIMENT_REPORT_FILE', f'{PREFIX}_zero_shot_sentiment.md'))

LDA_NUM_TOPICS = int(os.getenv('LDA_NUM_TOPICS', '8'))
LDA_WORDS_PER_TOPIC = int(os.getenv('LDA_WORDS_PER_TOPIC', '12'))
LDA_MAX_FEATURES = int(os.getenv('LDA_MAX_FEATURES', '3000'))
ANALYSIS_MAX_POSTS = int(os.getenv('ANALYSIS_MAX_POSTS', '0'))
ZERO_SHOT_MODEL = os.getenv('ZERO_SHOT_MODEL', 'typeform/distilbert-base-uncased-mnli')
SENTIMENT_LABELS = [
    label.strip()
    for label in os.getenv('SENTIMENT_LABELS', 'positive,neutral,negative').split(',')
    if label.strip()
]
HYPOTHESIS_TEMPLATE = os.getenv('HYPOTHESIS_TEMPLATE', 'This post expresses a {} sentiment.')

CUSTOM_STOP_WORDS = {
    PREFIX,
    'wendys',
    'cocacola',
    'coca',
    'cola',
    'https',
    'http',
    'amp',
    'rt',
    'co',
    't',
    'x',
    'com',
}
STOP_WORDS = sorted(set(ENGLISH_STOP_WORDS) | CUSTOM_STOP_WORDS)


def load_posts() -> list[dict[str, Any]]:
    if not INPUT_FILE.exists():
        raise FileNotFoundError(f'Input file not found: {INPUT_FILE}')
    posts = json.loads(INPUT_FILE.read_text(encoding='utf-8'))
    if not isinstance(posts, list):
        raise ValueError(f'Expected list in {INPUT_FILE}')
    if ANALYSIS_MAX_POSTS > 0:
        return posts[:ANALYSIS_MAX_POSTS]
    return posts


def clean_text(text: str) -> str:
    text = re.sub(r'https?://\S+', ' ', text)
    text = re.sub(r'@\w+', ' ', text)
    text = re.sub(r'#', ' ', text)
    text = re.sub(r'[^A-Za-z\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip().lower()
    return text


def text_for_analysis(post: dict[str, Any]) -> str:
    return clean_text(str(post.get('text') or ''))


def run_lda(posts: list[dict[str, Any]]) -> dict[str, Any]:
    documents = [text_for_analysis(post) for post in posts]
    indexed_documents = [(idx, doc) for idx, doc in enumerate(documents) if len(doc.split()) >= 3]
    if len(indexed_documents) < 2:
        result = {
            'target_user': TARGET_USER,
            'input_file': str(INPUT_FILE),
            'document_count': len(indexed_documents),
            'topics': [],
            'message': 'Not enough text for LDA.',
        }
        LDA_TOPICS_FILE.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        LDA_REPORT_FILE.write_text('# LDA Topics\n\nNot enough text for LDA.\n', encoding='utf-8')
        return result

    source_indices = [idx for idx, _ in indexed_documents]
    source_documents = [doc for _, doc in indexed_documents]
    topic_count = min(LDA_NUM_TOPICS, max(1, len(source_documents) // 2))

    vectorizer = CountVectorizer(
        stop_words=STOP_WORDS,
        max_features=LDA_MAX_FEATURES,
        min_df=2,
        max_df=0.85,
        ngram_range=(1, 2),
    )
    matrix = vectorizer.fit_transform(source_documents)
    feature_names = vectorizer.get_feature_names_out()

    lda = LatentDirichletAllocation(
        n_components=topic_count,
        random_state=42,
        learning_method='batch',
        max_iter=25,
    )
    topic_matrix = lda.fit_transform(matrix)

    topics = []
    for topic_index, topic in enumerate(lda.components_):
        top_indices = topic.argsort()[-LDA_WORDS_PER_TOPIC:][::-1]
        words = [feature_names[i] for i in top_indices]
        representative_rows = topic_matrix[:, topic_index].argsort()[-5:][::-1]
        representatives = []
        for row in representative_rows:
            post = posts[source_indices[row]]
            representatives.append({
                'id': post.get('id'),
                'tweet_url': post.get('tweet_url'),
                'score': float(topic_matrix[row, topic_index]),
                'text': post.get('text'),
            })
        topics.append({
            'topic_id': topic_index,
            'top_terms': words,
            'representative_posts': representatives,
        })

    result = {
        'target_user': TARGET_USER,
        'input_file': str(INPUT_FILE),
        'document_count': len(source_documents),
        'num_topics': topic_count,
        'topics': topics,
    }
    LDA_TOPICS_FILE.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

    lines = [f'# LDA Topics for @{TARGET_USER}', '', f'- Documents analyzed: {len(source_documents)}', f'- Topics: {topic_count}', '']
    for topic in topics:
        lines.append(f"## Topic {topic['topic_id']}")
        lines.append(', '.join(topic['top_terms']))
        lines.append('')
        for post in topic['representative_posts'][:3]:
            lines.append(f"- [{post['id']}]({post['tweet_url']}): {post['text']}")
        lines.append('')
    LDA_REPORT_FILE.write_text('\n'.join(lines), encoding='utf-8')
    return result


def run_zero_shot_sentiment(posts: list[dict[str, Any]]) -> dict[str, Any]:
    cached: dict[str, Any] = {}
    if SENTIMENT_FILE.exists():
        try:
            previous = json.loads(SENTIMENT_FILE.read_text(encoding='utf-8'))
            for item in previous.get('posts', []):
                if item.get('id') and item.get('text'):
                    cached[str(item['id'])] = item
        except Exception:
            cached = {}

    classifier = pipeline('zero-shot-classification', model=ZERO_SHOT_MODEL)
    results = []
    counts: Counter[str] = Counter()
    score_sums: defaultdict[str, float] = defaultdict(float)

    for index, post in enumerate(posts, start=1):
        post_id = str(post.get('id') or '')
        text = str(post.get('text') or '').strip()
        if not post_id or not text:
            continue

        cached_item = cached.get(post_id)
        if cached_item and cached_item.get('text') == text and cached_item.get('model') == ZERO_SHOT_MODEL:
            item = cached_item
        else:
            output = classifier(
                text[:1000],
                candidate_labels=SENTIMENT_LABELS,
                hypothesis_template=HYPOTHESIS_TEMPLATE,
                multi_label=False,
            )
            labels = output['labels']
            scores = output['scores']
            item = {
                'id': post_id,
                'tweet_url': post.get('tweet_url'),
                'created_at': post.get('created_at'),
                'text': text,
                'model': ZERO_SHOT_MODEL,
                'top_label': labels[0],
                'top_score': float(scores[0]),
                'scores': {label: float(score) for label, score in zip(labels, scores)},
            }

        results.append(item)
        counts[item['top_label']] += 1
        for label, score in item.get('scores', {}).items():
            score_sums[label] += float(score)

        if index % 50 == 0:
            print(f'zero-shot analyzed {index}/{len(posts)} posts', flush=True)

    averages = {label: score_sums[label] / max(1, len(results)) for label in SENTIMENT_LABELS}
    summary = {
        'target_user': TARGET_USER,
        'input_file': str(INPUT_FILE),
        'model': ZERO_SHOT_MODEL,
        'labels': SENTIMENT_LABELS,
        'post_count': len(results),
        'label_counts': dict(counts),
        'average_scores': averages,
        'posts': results,
    }
    SENTIMENT_FILE.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

    lines = [f'# Zero-Shot Sentiment for @{TARGET_USER}', '', f'- Posts analyzed: {len(results)}', f'- Model: `{ZERO_SHOT_MODEL}`', '']
    lines.append('## Label Counts')
    for label, count in counts.most_common():
        lines.append(f'- {label}: {count}')
    lines.append('')
    lines.append('## Average Scores')
    for label, score in sorted(averages.items(), key=lambda item: item[1], reverse=True):
        lines.append(f'- {label}: {score:.4f}')
    lines.append('')
    lines.append('## Highest Confidence Examples')
    for item in sorted(results, key=lambda row: row.get('top_score', 0), reverse=True)[:10]:
        lines.append(f"- {item['top_label']} ({item['top_score']:.3f}) [{item['id']}]({item['tweet_url']}): {item['text']}")
    SENTIMENT_REPORT_FILE.write_text('\n'.join(lines), encoding='utf-8')
    return summary


def main() -> None:
    posts = load_posts()
    print(f'Analyzing {len(posts)} posts from {INPUT_FILE}', flush=True)
    lda_result = run_lda(posts)
    print(f"LDA complete: {len(lda_result.get('topics', []))} topics", flush=True)
    sentiment_result = run_zero_shot_sentiment(posts)
    print(f"Zero-shot sentiment complete: {sentiment_result['post_count']} posts", flush=True)


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print(f'Fatal analysis error: {type(exc).__name__}: {exc}', flush=True)
        raise
