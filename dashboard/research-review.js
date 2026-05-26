/* global React, ReactDOM */
(function () {
  const mount = document.getElementById('research-review-root');
  if (!mount || !window.React || !window.ReactDOM) return;

  const e = React.createElement;
  const { useEffect, useMemo, useState } = React;
  const HUMOR_OPTIONS = ['Affiliative humor', 'Self-enhancing humor', 'Aggressive humor', 'Self-defeating humor', 'Non-humorous brand message'];
  const SENTIMENT_OPTIONS = ['positive', 'neutral', 'negative'];
  const HUMOR_KO = {
    'Affiliative humor': '친화적 유머',
    'Self-enhancing humor': '자기고양적 유머',
    'Aggressive humor': '공격적 유머',
    'Self-defeating humor': '자기패배적 유머',
    'Non-humorous brand message': '비유머 브랜드 메시지'
  };
  const SENTIMENT_KO = { positive: '긍정', neutral: '중립', negative: '부정' };
  const fmt = new Intl.NumberFormat('ko-KR');
  const scoreFmt = new Intl.NumberFormat('ko-KR', { maximumFractionDigits: 3 });

  async function readJson(path) {
    const response = await fetch(path, { cache: 'no-store' });
    if (!response.ok) throw new Error(`${path}: ${response.status}`);
    return response.json();
  }

  function csvEscape(value) {
    return `"${String(value == null ? '' : value).replace(/"/g, '""')}"`;
  }

  function downloadText(filename, text, type) {
    const blob = new Blob([text], { type: type || 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
  }

  function downloadCsv(filename, rows, columns) {
    const lines = [columns.join(',')].concat(rows.map((row) => columns.map((column) => csvEscape(row[column])).join(',')));
    downloadText(filename, lines.join('\n') + '\n', 'text/csv;charset=utf-8');
  }

  function SectionTitle({ kicker, title, children }) {
    return e('div', { className: 'section-title' }, e('span', null, kicker), e('h2', null, title), children || null);
  }

  function ReviewDashboard() {
    const [auditRows, setAuditRows] = useState([]);
    const [joinedRows, setJoinedRows] = useState([]);
    const [topics, setTopics] = useState({});
    const [stopwords, setStopwords] = useState('');
    const [status, setStatus] = useState('loading');
    const [error, setError] = useState('');
    const [brand, setBrand] = useState('all');
    const [reason, setReason] = useState('all');
    const [query, setQuery] = useState('');
    const [limit, setLimit] = useState(80);

    useEffect(() => {
      let cancelled = false;
      Promise.all([
        readJson('data/analysis/sampling_audit_candidates.json'),
        readJson('data/analysis/joined_posts.json'),
        Promise.all(['wendys', 'cocacola', 'moonpie'].map((slug) => readJson(`data/${slug}/lda_topics.json`).then((data) => [slug, data]).catch(() => [slug, null])))
      ]).then(([audit, joined, topicEntries]) => {
        if (cancelled) return;
        setAuditRows((audit || []).map((row, index) => Object.assign({ _index: index }, row)));
        setJoinedRows(joined || []);
        setTopics(Object.fromEntries(topicEntries));
        setStopwords('wendys\ncocacola\nmoonpie\nhttps\nhttp\namp\nrt\ncom\npic\ntwitter\njust\nlike\nget\ngot\nnew\none\nnow\ntoday\nmake\nknow\nreally\nus\n');
        setStatus('ready');
      }).catch((err) => {
        if (!cancelled) { setError(err.message); setStatus('error'); }
      });
      return () => { cancelled = true; };
    }, []);

    const brands = useMemo(() => Array.from(new Set(auditRows.map((row) => row.brand))).sort(), [auditRows]);
    const reasons = useMemo(() => Array.from(new Set(auditRows.map((row) => row.audit_reason))).sort(), [auditRows]);
    const filteredAudit = useMemo(() => {
      const q = query.trim().toLowerCase();
      return auditRows.filter((row) => {
        if (brand !== 'all' && row.brand !== brand) return false;
        if (reason !== 'all' && row.audit_reason !== reason) return false;
        if (!q) return true;
        return [row.text, row.brand, row.sentiment_label, row.humor_type, row.audit_reason, row.post_id].some((value) => String(value || '').toLowerCase().includes(q));
      }).slice(0, limit);
    }, [auditRows, brand, reason, query, limit]);

    const topicReviewRows = useMemo(() => {
      const rows = [];
      Object.entries(topics).forEach(([slug, data]) => {
        ((data && data.topics) || []).forEach((topic) => {
          rows.push({
            brand_slug: slug,
            topic_id: topic.topic_id,
            top_terms: (topic.top_terms || []).join(', '),
            representative_posts: (topic.representative_posts || []).slice(0, 3).map((post) => post.text).join(' | '),
            human_topic_label: '',
            remove_terms: '',
            merge_with_topic: '',
            split_needed: '',
            notes: ''
          });
        });
      });
      return rows;
    }, [topics]);

    function updateAudit(index, key, value) {
      setAuditRows((rows) => rows.map((row) => row._index === index ? Object.assign({}, row, { [key]: value }) : row));
    }

    function exportAudit() {
      downloadCsv('sampling_audit_review_completed.csv', auditRows, ['audit_reason', 'brand', 'post_id', 'created_at', 'tweet_url', 'text', 'sentiment_label', 'sentiment_score', 'humor_type', 'humor_score', 'total_engagement', 'is_viral', 'human_sentiment_label', 'human_humor_type', 'human_notes']);
    }

    function exportStopwords() {
      downloadText('lda_stopwords_reviewed.txt', stopwords.trim() + '\n', 'text/plain;charset=utf-8');
    }

    function exportTopicReview() {
      downloadCsv('lda_topic_review.csv', topicReviewRows, ['brand_slug', 'topic_id', 'top_terms', 'representative_posts', 'human_topic_label', 'remove_terms', 'merge_with_topic', 'split_needed', 'notes']);
    }

    function exportConfig() {
      const humorConfig = {
        labels: HUMOR_OPTIONS,
        hypothesis_template: 'This brand post uses {}.',
        label_notes: {
          'Affiliative humor': 'Relationship-building humor, shared amusement, warmth, or bonding with audiences.',
          'Self-enhancing humor': 'Positive self-presentation, optimistic framing, or playful brand confidence.',
          'Aggressive humor': 'Teasing, ridicule, sarcasm targeted at others, competitive attacks, or superiority claims.',
          'Self-defeating humor': 'Self-deprecation, self-mockery, or intentionally lowering the brand own status for comic effect.',
          'Non-humorous brand message': 'Plain promotional, informational, support, announcement, or conversational content without a clear humor strategy.'
        }
      };
      downloadText('humor_labels_reviewed.json', JSON.stringify(humorConfig, null, 2) + '\n', 'application/json;charset=utf-8');
    }

    const completed = auditRows.filter((row) => row.human_sentiment_label || row.human_humor_type || row.human_notes).length;
    const lowConfidence = auditRows.filter((row) => row.audit_reason === 'low_confidence').length;
    const nonDominant = auditRows.filter((row) => row.audit_reason === 'non_dominant_humor').length;
    const viral = auditRows.filter((row) => row.audit_reason === 'viral').length;

    return e('section', { id: 'research-review', className: 'section research-review-shell' },
      e(SectionTitle, { kicker: 'Human-in-the-loop Review', title: 'Research Review Workspace' },
        e('p', { className: 'panel-copy' }, 'Zero-shot Classification과 LDA Topic 품질을 사람이 검토하고, 수정 파일을 다운로드해 repo config에 반영하는 작업 공간입니다.')
      ),
      status === 'loading' ? e('div', { className: 'notice' }, '수동 검토 데이터를 불러오는 중입니다...') : null,
      status === 'error' ? e('div', { className: 'notice error' }, error) : null,
      e('div', { className: 'metrics' },
        e('article', { className: 'metric' }, e('span', null, 'Audit Candidates'), e('strong', null, fmt.format(auditRows.length)), e('small', null, '수동 검토 후보')),
        e('article', { className: 'metric danger' }, e('span', null, 'Low-confidence'), e('strong', null, fmt.format(lowConfidence)), e('small', null, '분류 점수 낮음')),
        e('article', { className: 'metric blue' }, e('span', null, 'Non-dominant Humor'), e('strong', null, fmt.format(nonDominant)), e('small', null, '희소 유머 유형 보강')),
        e('article', { className: 'metric red' }, e('span', null, 'Viral Cases'), e('strong', null, fmt.format(viral)), e('small', null, '상위 참여도 검토')),
        e('article', { className: 'metric' }, e('span', null, 'Completed Locally'), e('strong', null, fmt.format(completed)), e('small', null, '브라우저 편집 기준')),
        e('article', { className: 'metric' }, e('span', null, 'Joined Posts'), e('strong', null, fmt.format(joinedRows.length)), e('small', null, '분석 대상 전체'))
      ),
      e('article', { className: 'panel wide review-actions' },
        e('h3', null, 'Export Actions'),
        e('div', { className: 'action-row' },
          e('button', { onClick: exportAudit, 'aria-label': 'Download completed sampling audit CSV' }, 'Audit CSV 다운로드'),
          e('button', { onClick: exportTopicReview, 'aria-label': 'Download LDA topic review CSV' }, 'LDA Topic Review 다운로드'),
          e('button', { onClick: exportStopwords, 'aria-label': 'Download reviewed LDA stopwords' }, 'Stopwords TXT 다운로드'),
          e('button', { onClick: exportConfig, 'aria-label': 'Download reviewed humor label config' }, 'Humor Config 다운로드')
        ),
        e('p', { className: 'panel-copy' }, '다운로드한 파일은 `data/analysis/`, `config/lda_stopwords.txt`, `config/humor_labels.json`에 반영한 뒤 재분석하면 됩니다.')
      ),
      e('article', { className: 'panel wide' },
        e('h3', null, 'Sampling Audit Editor'),
        e('div', { className: 'review-filters' },
          e('label', null, 'Brand', e('select', { value: brand, onChange: (event) => setBrand(event.target.value) }, e('option', { value: 'all' }, 'All'), brands.map((item) => e('option', { key: item, value: item }, item)))),
          e('label', null, 'Reason', e('select', { value: reason, onChange: (event) => setReason(event.target.value) }, e('option', { value: 'all' }, 'All'), reasons.map((item) => e('option', { key: item, value: item }, item)))),
          e('label', null, 'Search', e('input', { value: query, onChange: (event) => setQuery(event.target.value), placeholder: '본문, 브랜드, 라벨 검색' })),
          e('label', null, 'Rows', e('select', { value: limit, onChange: (event) => setLimit(Number(event.target.value)) }, [40, 80, 150, 300].map((value) => e('option', { key: value, value }, value))))
        ),
        e('div', { className: 'review-list' }, filteredAudit.map((row) => e('article', { key: row._index, className: 'review-card' },
          e('div', { className: 'review-card-head' },
            e('b', null, `${row.brand} · ${row.audit_reason}`),
            e('a', { href: row.tweet_url, target: '_blank', rel: 'noreferrer' }, 'X에서 열기')
          ),
          e('p', null, row.text || '(본문 없음)'),
          e('div', { className: 'review-badges' },
            e('span', null, `Model Sentiment: ${SENTIMENT_KO[row.sentiment_label] || row.sentiment_label} (${scoreFmt.format(Number(row.sentiment_score) || 0)})`),
            e('span', null, `Model Humor: ${HUMOR_KO[row.humor_type] || row.humor_type} (${scoreFmt.format(Number(row.humor_score) || 0)})`),
            e('span', null, `Engagement: ${fmt.format(Number(row.total_engagement) || 0)}`)
          ),
          e('div', { className: 'review-inputs' },
            e('label', null, 'Human Sentiment', e('select', { value: row.human_sentiment_label || '', onChange: (event) => updateAudit(row._index, 'human_sentiment_label', event.target.value) }, e('option', { value: '' }, '선택 안 함'), SENTIMENT_OPTIONS.map((item) => e('option', { key: item, value: item }, SENTIMENT_KO[item] || item)))),
            e('label', null, 'Human Humor', e('select', { value: row.human_humor_type || '', onChange: (event) => updateAudit(row._index, 'human_humor_type', event.target.value) }, e('option', { value: '' }, '선택 안 함'), HUMOR_OPTIONS.map((item) => e('option', { key: item, value: item }, HUMOR_KO[item] || item)))),
            e('label', null, 'Notes', e('textarea', { value: row.human_notes || '', onChange: (event) => updateAudit(row._index, 'human_notes', event.target.value), placeholder: '오분류 이유, 문맥, 라벨 수정 제안' }))
          )
        )))
      ),
      e('div', { className: 'grid' },
        e('article', { className: 'panel' },
          e('h3', null, 'LDA Stopword Review'),
          e('p', { className: 'panel-copy' }, 'Topic 구분력이 낮거나 반복적으로 노이즈를 만드는 단어를 한 줄에 하나씩 추가합니다.'),
          e('textarea', { className: 'stopword-box', value: stopwords, onChange: (event) => setStopwords(event.target.value), 'aria-label': 'LDA stopwords editor' })
        ),
        e('article', { className: 'panel' },
          e('h3', null, 'LDA Topic Review Guide'),
          e('div', { className: 'topic-review-list' }, topicReviewRows.slice(0, 12).map((row) => e('div', { key: `${row.brand_slug}-${row.topic_id}`, className: 'topic-review-item' },
            e('b', null, `${row.brand_slug} · Topic ${row.topic_id}`),
            e('span', null, row.top_terms),
            e('small', null, row.representative_posts || '대표 게시물 없음')
          )))
        )
      )
    );
  }

  ReactDOM.createRoot(mount).render(e(ReviewDashboard));
})();
