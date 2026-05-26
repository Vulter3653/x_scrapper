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

  function SectionTitle({ kicker, title, description }) {
    return e('div', { className: 'section-title' },
      e('span', null, kicker),
      e('h2', null, title),
      description ? e('p', { className: 'panel-copy' }, description) : null
    );
  }

  function Metric({ label, value, help, tone }) {
    return e('article', { className: `metric ${tone || ''}` }, e('span', null, label), e('strong', null, value), e('small', null, help));
  }

  function TaskCard({ step, title, body, output }) {
    return e('article', { className: 'task-card' },
      e('b', null, step),
      e('h3', null, title),
      e('p', null, body),
      output ? e('small', null, output) : null
    );
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
    const [sentimentTemplate, setSentimentTemplate] = useState('This brand post expresses a {} sentiment.');
    const [humorTemplate, setHumorTemplate] = useState('This brand post uses {}.');
    const [topicDrafts, setTopicDrafts] = useState({});

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
          const key = `${slug}-${topic.topic_id}`;
          const draft = topicDrafts[key] || {};
          rows.push({
            key,
            brand_slug: slug,
            topic_id: topic.topic_id,
            top_terms: (topic.top_terms || []).join(', '),
            representative_posts: (topic.representative_posts || []).slice(0, 3).map((post) => post.text).join(' | '),
            human_topic_label: draft.human_topic_label || '',
            remove_terms: draft.remove_terms || '',
            merge_with_topic: draft.merge_with_topic || '',
            split_needed: draft.split_needed || '',
            notes: draft.notes || ''
          });
        });
      });
      return rows;
    }, [topics, topicDrafts]);

    function updateAudit(index, key, value) {
      setAuditRows((rows) => rows.map((row) => row._index === index ? Object.assign({}, row, { [key]: value }) : row));
    }

    function updateTopic(key, field, value) {
      setTopicDrafts((drafts) => Object.assign({}, drafts, { [key]: Object.assign({}, drafts[key] || {}, { [field]: value }) }));
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

    function exportSentimentConfig() {
      downloadText('sentiment_labels_reviewed.json', JSON.stringify({ labels: SENTIMENT_OPTIONS, hypothesis_template: sentimentTemplate }, null, 2) + '\n', 'application/json;charset=utf-8');
    }

    function exportHumorConfig() {
      const humorConfig = {
        labels: HUMOR_OPTIONS,
        hypothesis_template: humorTemplate,
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

    return e(React.Fragment, null,
      e('header', { className: 'top review-top' },
        e('div', null,
          e('div', { className: 'title' }, e('h1', null, 'X 브랜드 인텔리전스 수동 검토 대시보드'), e('em', { className: status === 'ready' ? 'ready' : status === 'error' ? 'error' : 'loading' }, status === 'ready' ? '준비 완료' : status === 'error' ? '오류' : '로딩 중')),
          e('p', null, 'Zero-shot Classification과 LDA Topic 품질을 사람이 검토하고 개선 파일을 만드는 별도 작업 공간입니다.'),
          e('small', null, '편집 내용은 브라우저에 임시 보관되며 다운로드 후 repo에 반영해야 합니다.')
        ),
        e('nav', { className: 'tabs review-tabs' },
          e('a', { href: 'index.html' }, '분석 대시보드'),
          e('a', { href: '#audit' }, 'Audit'),
          e('a', { href: '#labels' }, 'Labels'),
          e('a', { href: '#stopwords' }, 'Stopwords'),
          e('a', { href: '#topics' }, 'Topics')
        )
      ),
      e('nav', { className: 'section-nav review-section-nav' }, [
        ['workflow', '작업 순서'], ['audit', '1. Sampling Audit'], ['labels', '2. Zero-shot Labels'], ['stopwords', '3. LDA Stopwords'], ['topics', '4. Topic Review'], ['exports', '5. Export & Apply']
      ].map(([id, label]) => e('a', { key: id, href: `#${id}` }, label))),
      e('main', { className: 'review-layout' },
        status === 'loading' ? e('div', { className: 'notice' }, '수동 검토 데이터를 불러오는 중입니다...') : null,
        status === 'error' ? e('div', { className: 'notice error' }, error) : null,
        e('section', { id: 'workflow', className: 'section' },
          e(SectionTitle, { kicker: 'Workflow', title: '사람이 수행할 작업 순서', description: '각 작업은 독립적으로 수행할 수 있지만, 권장 순서는 Audit → Label 보정 → LDA 보정 → Export → 재분석입니다.' }),
          e('div', { className: 'task-grid' },
            e(TaskCard, { step: 'Step 1', title: 'Sampling Audit', body: '저신뢰/바이럴/희소 유머 후보를 읽고 human sentiment, human humor, notes를 입력합니다.', output: 'Output: sampling_audit_review_completed.csv' }),
            e(TaskCard, { step: 'Step 2', title: 'Zero-shot Label Review', body: '반복 오분류 패턴을 보고 sentiment/humor label과 hypothesis template을 조정합니다.', output: 'Output: sentiment_labels_reviewed.json, humor_labels_reviewed.json' }),
            e(TaskCard, { step: 'Step 3', title: 'LDA Stopword Review', body: 'Topic 해석을 방해하는 반복어를 한 줄에 하나씩 추가합니다.', output: 'Output: lda_stopwords_reviewed.txt' }),
            e(TaskCard, { step: 'Step 4', title: 'LDA Topic Review', body: 'Topic별 이름, 제거어, merge/split 필요성, 해석 메모를 기록합니다.', output: 'Output: lda_topic_review.csv' }),
            e(TaskCard, { step: 'Step 5', title: 'Apply & Reanalyze', body: '다운로드한 파일을 repo에 반영하고 analyze/export/sync를 다시 실행합니다.', output: 'Output: updated analysis JSON/CSV and dashboard data' })
          )
        ),
        e('section', { id: 'audit', className: 'section' },
          e(SectionTitle, { kicker: 'Task 1', title: 'Sampling Audit Editor', description: '개별 tweet을 읽고 model label과 human label이 일치하는지 검토합니다.' }),
          e('div', { className: 'metrics' },
            e(Metric, { label: 'Audit Candidates', value: fmt.format(auditRows.length), help: '수동 검토 후보' }),
            e(Metric, { label: 'Low-confidence', value: fmt.format(lowConfidence), help: '분류 점수 낮음', tone: 'danger' }),
            e(Metric, { label: 'Non-dominant Humor', value: fmt.format(nonDominant), help: '희소 유머 유형 보강', tone: 'blue' }),
            e(Metric, { label: 'Viral Cases', value: fmt.format(viral), help: '상위 참여도 검토', tone: 'red' }),
            e(Metric, { label: 'Completed Locally', value: fmt.format(completed), help: '브라우저 편집 기준' }),
            e(Metric, { label: 'Joined Posts', value: fmt.format(joinedRows.length), help: '분석 대상 전체' })
          ),
          e('article', { className: 'panel wide' },
            e('div', { className: 'review-filters' },
              e('label', null, 'Brand', e('select', { value: brand, onChange: (event) => setBrand(event.target.value) }, e('option', { value: 'all' }, 'All'), brands.map((item) => e('option', { key: item, value: item }, item)))),
              e('label', null, 'Reason', e('select', { value: reason, onChange: (event) => setReason(event.target.value) }, e('option', { value: 'all' }, 'All'), reasons.map((item) => e('option', { key: item, value: item }, item)))),
              e('label', null, 'Search', e('input', { value: query, onChange: (event) => setQuery(event.target.value), placeholder: '본문, 브랜드, 라벨 검색' })),
              e('label', null, 'Rows', e('select', { value: limit, onChange: (event) => setLimit(Number(event.target.value)) }, [40, 80, 150, 300].map((value) => e('option', { key: value, value }, value))))
            ),
            e('div', { className: 'review-list' }, filteredAudit.map((row) => e('article', { key: row._index, className: 'review-card' },
              e('div', { className: 'review-card-head' }, e('b', null, `${row.brand} · ${row.audit_reason}`), e('a', { href: row.tweet_url, target: '_blank', rel: 'noreferrer' }, 'X에서 열기')),
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
          )
        ),
        e('section', { id: 'labels', className: 'section' },
          e(SectionTitle, { kicker: 'Task 2', title: 'Zero-shot Label & Template Review', description: '분류 라벨과 hypothesis template을 작업 단위로 분리해 검토합니다.' }),
          e('div', { className: 'grid' },
            e('article', { className: 'panel' }, e('h3', null, 'Sentiment Config'), e('p', { className: 'panel-copy' }, '감성 라벨은 기본적으로 positive, neutral, negative를 유지합니다.'), e('textarea', { className: 'stopword-box compact', value: sentimentTemplate, onChange: (event) => setSentimentTemplate(event.target.value), 'aria-label': 'Sentiment hypothesis template' }), e('button', { onClick: exportSentimentConfig, className: 'inline-action' }, 'Sentiment Config 다운로드')),
            e('article', { className: 'panel' }, e('h3', null, 'Humor Config'), e('p', { className: 'panel-copy' }, '비유머 브랜드 메시지 라벨을 포함해 일반 홍보성 문장이 강제로 HSQ 유머에 배정되는 문제를 줄입니다.'), e('textarea', { className: 'stopword-box compact', value: humorTemplate, onChange: (event) => setHumorTemplate(event.target.value), 'aria-label': 'Humor hypothesis template' }), e('button', { onClick: exportHumorConfig, className: 'inline-action' }, 'Humor Config 다운로드'))
          )
        ),
        e('section', { id: 'stopwords', className: 'section' },
          e(SectionTitle, { kicker: 'Task 3', title: 'LDA Stopword Review', description: 'Topic 해석을 방해하는 단어를 보수적으로 추가합니다. 캠페인/제품 의미가 있는 단어는 제거하지 않습니다.' }),
          e('article', { className: 'panel wide' }, e('textarea', { className: 'stopword-box', value: stopwords, onChange: (event) => setStopwords(event.target.value), 'aria-label': 'LDA stopwords editor' }), e('button', { onClick: exportStopwords, className: 'inline-action' }, 'Stopwords TXT 다운로드'))
        ),
        e('section', { id: 'topics', className: 'section' },
          e(SectionTitle, { kicker: 'Task 4', title: 'LDA Topic Review', description: 'Topic별 해석 가능한 이름, 제거어, merge/split 판단을 기록합니다.' }),
          e('div', { className: 'topic-review-list detailed' }, topicReviewRows.map((row) => e('article', { key: row.key, className: 'topic-review-item detailed' },
            e('b', null, `${row.brand_slug} · Topic ${row.topic_id}`),
            e('span', null, row.top_terms),
            e('small', null, row.representative_posts || '대표 게시물 없음'),
            e('div', { className: 'topic-inputs' },
              e('label', null, 'Human Topic Label', e('input', { value: row.human_topic_label, onChange: (event) => updateTopic(row.key, 'human_topic_label', event.target.value) })),
              e('label', null, 'Remove Terms', e('input', { value: row.remove_terms, onChange: (event) => updateTopic(row.key, 'remove_terms', event.target.value), placeholder: 'comma-separated' })),
              e('label', null, 'Merge With', e('input', { value: row.merge_with_topic, onChange: (event) => updateTopic(row.key, 'merge_with_topic', event.target.value) })),
              e('label', null, 'Split Needed', e('select', { value: row.split_needed, onChange: (event) => updateTopic(row.key, 'split_needed', event.target.value) }, e('option', { value: '' }, '선택 안 함'), e('option', { value: 'yes' }, 'yes'), e('option', { value: 'no' }, 'no'))),
              e('label', null, 'Notes', e('textarea', { value: row.notes, onChange: (event) => updateTopic(row.key, 'notes', event.target.value) }))
            )
          )))
        ),
        e('section', { id: 'exports', className: 'section' },
          e(SectionTitle, { kicker: 'Task 5', title: 'Export & Apply', description: '각 작업 결과를 다운로드한 뒤 repo에 반영하고 재분석합니다.' }),
          e('article', { className: 'panel wide review-actions' },
            e('div', { className: 'action-row' },
              e('button', { onClick: exportAudit, 'aria-label': 'Download completed sampling audit CSV' }, 'Audit CSV 다운로드'),
              e('button', { onClick: exportSentimentConfig, 'aria-label': 'Download reviewed sentiment config' }, 'Sentiment Config 다운로드'),
              e('button', { onClick: exportHumorConfig, 'aria-label': 'Download reviewed humor label config' }, 'Humor Config 다운로드'),
              e('button', { onClick: exportStopwords, 'aria-label': 'Download reviewed LDA stopwords' }, 'Stopwords TXT 다운로드'),
              e('button', { onClick: exportTopicReview, 'aria-label': 'Download LDA topic review CSV' }, 'LDA Topic Review 다운로드')
            ),
            e('pre', { className: 'apply-steps' }, '1. 다운로드 파일을 repo에 반영\n2. config/lda_stopwords.txt, config/*_labels.json 업데이트\n3. python analyze_posts.py --task all\n4. python export_research_outputs.py\n5. python sync_dashboard_data.py\n6. 결과를 commit/push')
          )
        )
      )
    );
  }

  ReactDOM.createRoot(mount).render(e(ReviewDashboard));
})();
