/* global React, ReactDOM */
(function () {
  const mount = document.getElementById('confidence-root');
  if (!mount || !window.React || !window.ReactDOM) return;

  const e = React.createElement;
  const { useEffect, useMemo, useState } = React;
  const ACCOUNTS = {
    wendys: { label: "Wendy's", base: 'data/wendys', color: '#E2231A' },
    cocacola: { label: 'Coca-Cola', base: 'data/cocacola', color: '#111827' },
    moonpie: { label: 'MoonPie', base: 'data/moonpie', color: '#F97316' }
  };
  const HUMOR_KO = {
    'Affiliative humor': '친화적 유머',
    'Self-enhancing humor': '자기고양적 유머',
    'Aggressive humor': '공격적 유머',
    'Self-defeating humor': '자기패배적 유머',
    unknown: '미분류'
  };
  const SENTIMENT_KO = { positive: '긍정', neutral: '중립', negative: '부정', unknown: '미분류' };
  const fmt = new Intl.NumberFormat('ko-KR');
  const scoreFmt = new Intl.NumberFormat('ko-KR', { maximumFractionDigits: 3 });
  const pct = new Intl.NumberFormat('ko-KR', { style: 'percent', maximumFractionDigits: 1 });
  const n = (value) => Number.isFinite(Number(value)) ? Number(value) : 0;
  const textOf = (post) => String((post && (post.text || post.content || post.tweet_text || post.post_text)) || '');
  const dateOf = (post) => (post && (post.date || post.created_at || post.timestamp)) || '';
  const parseDate = (value) => { const d = new Date(value); return Number.isNaN(d.getTime()) ? null : d; };
  const isoDate = (value) => { const d = parseDate(value); return d ? d.toISOString().slice(0, 10) : ''; };
  const engagement = (post) => n(post && (post.likes || post.like_count || post.favorite_count)) + n(post && (post.replies || post.reply_count)) + n(post && (post.retweets || post.retweet_count || post.reposts)) + n(post && (post.quotes || post.quote_count));
  const avg = (values) => { const arr = values.map(n).filter(Number.isFinite); return arr.length ? arr.reduce((s, v) => s + v, 0) / arr.length : 0; };

  async function readJson(path) {
    const res = await fetch(path, { cache: 'no-store' });
    if (!res.ok) return null;
    return res.json();
  }

  async function loadAccount(key) {
    const account = ACCOUNTS[key];
    const posts = await readJson(`${account.base}/posts.json`) || [];
    const sentiment = await readJson(`${account.base}/zero_shot_sentiment.json`) || {};
    const humor = await readJson(`${account.base}/hsq_humor_classification.json`) || {};
    const sentimentById = new Map((sentiment.posts || []).map((row) => [String(row.id), row]));
    const humorById = new Map((humor.posts || []).map((row) => [String(row.id), row]));

    return posts.map((post) => {
      const id = String(post.id);
      const s = sentimentById.get(id) || {};
      const h = humorById.get(id) || {};
      return {
        id,
        account: key,
        brand: account.label,
        date: isoDate(dateOf(post)),
        text: textOf(post),
        url: post.tweet_url || post.url || '',
        engagement: engagement(post),
        sentiment: s.top_label || 'unknown',
        sentimentScore: n(s.top_score),
        humor: h.top_label || 'unknown',
        humorScore: n(h.top_score)
      };
    });
  }

  function selectedKey() {
    const active = document.querySelector('.tabs button.on');
    const label = active ? active.textContent.trim() : '전체 브랜드';
    if (label.includes('Wendy')) return 'wendys';
    if (label.includes('Coca')) return 'cocacola';
    if (label.includes('Moon')) return 'moonpie';
    return 'all';
  }

  function group(rows, getter) {
    const m = new Map();
    rows.forEach((row) => {
      const key = getter(row) || 'unknown';
      if (!m.has(key)) m.set(key, []);
      m.get(key).push(row);
    });
    return Array.from(m.entries()).map(([key, grouped]) => ({ key, rows: grouped, value: grouped.length })).sort((a, b) => b.value - a.value);
  }

  function Metric({ label, value, help, tone }) {
    return e('article', { className: `metric ${tone || ''}` }, e('span', null, label), e('strong', null, value), help ? e('small', null, help) : null);
  }

  function Table({ heads, rows }) {
    if (!rows.length) return e('div', { className: 'empty' }, '수동 검토가 필요한 저신뢰 게시물이 없습니다.');
    return e('div', { className: 'table-wrap' }, e('table', null,
      e('thead', null, e('tr', null, heads.map((head) => e('th', { key: head }, head)))),
      e('tbody', null, rows.map((row, index) => e('tr', { key: index }, row.map((cell, cellIndex) => e('td', { key: cellIndex }, cell)))))
    ));
  }

  function ConfidenceReview({ rows, scope }) {
    const threshold = 0.5;
    const lowHumor = rows.filter((row) => row.humorScore > 0 && row.humorScore < threshold);
    const lowSentiment = rows.filter((row) => row.sentimentScore > 0 && row.sentimentScore < threshold);
    const bothLow = rows.filter((row) => row.humorScore > 0 && row.humorScore < threshold && row.sentimentScore > 0 && row.sentimentScore < threshold);
    const reviewRows = rows
      .filter((row) => (row.humorScore > 0 && row.humorScore < threshold) || (row.sentimentScore > 0 && row.sentimentScore < threshold))
      .sort((a, b) => Math.min(a.humorScore || 1, a.sentimentScore || 1) - Math.min(b.humorScore || 1, b.sentimentScore || 1))
      .slice(0, 12);
    const humorRows = group(rows, (row) => row.humor).map((row) => [HUMOR_KO[row.key] || row.key, fmt.format(row.value), scoreFmt.format(avg(row.rows.map((post) => post.humorScore))), fmt.format(row.rows.filter((post) => post.humorScore > 0 && post.humorScore < threshold).length)]);
    const sentimentRows = group(rows, (row) => row.sentiment).map((row) => [SENTIMENT_KO[row.key] || row.key, fmt.format(row.value), scoreFmt.format(avg(row.rows.map((post) => post.sentimentScore))), fmt.format(row.rows.filter((post) => post.sentimentScore > 0 && post.sentimentScore < threshold).length)]);

    return e('section', { id: 'confidence-review', className: 'confidence-review-shell' },
      e('div', { className: 'section-title' }, e('span', null, '분류 신뢰도 검토'), e('h2', null, 'Low-confidence Review')),
      e('p', { className: 'panel-copy' }, `${scope} 기준으로 zero-shot 감성/유머 분류의 낮은 confidence 후보를 수동 검토 대상으로 분리합니다.`),
      e('div', { className: 'metrics' },
        e(Metric, { label: '유머 저신뢰 게시물', value: fmt.format(lowHumor.length), help: `humor score < ${threshold}`, tone: 'danger' }),
        e(Metric, { label: '감성 저신뢰 게시물', value: fmt.format(lowSentiment.length), help: `sentiment score < ${threshold}` }),
        e(Metric, { label: '동시 저신뢰 게시물', value: fmt.format(bothLow.length), help: '유머와 감성 모두 수동 검토 권장' }),
        e(Metric, { label: '평균 유머 점수', value: scoreFmt.format(avg(rows.map((row) => row.humorScore))), help: '현재 범위 기준' }),
        e(Metric, { label: '평균 감성 점수', value: scoreFmt.format(avg(rows.map((row) => row.sentimentScore))), help: '현재 범위 기준' }),
        e(Metric, { label: '검토 필요 비중', value: pct.format(rows.length ? reviewRows.length / rows.length : 0), help: '상위 12개 우선 표시' })
      ),
      e('div', { className: 'grid' },
        e('article', { className: 'panel' }, e('h3', null, '유머 라벨별 신뢰도'), e(Table, { heads: ['유머 유형', '게시물', '평균 점수', '저신뢰'], rows: humorRows })),
        e('article', { className: 'panel' }, e('h3', null, '감성 라벨별 신뢰도'), e(Table, { heads: ['감성', '게시물', '평균 점수', '저신뢰'], rows: sentimentRows })),
        e('article', { className: 'panel wide' }, e('h3', null, '수동 검토 우선 게시물'), e(Table, { heads: ['날짜', '브랜드', '본문', '감성 점수', '유머 점수', '라벨', '링크'], rows: reviewRows.map((post) => [
          post.date,
          post.brand,
          e('span', { className: 'post-text' }, post.text || '(본문 없음)'),
          scoreFmt.format(post.sentimentScore),
          scoreFmt.format(post.humorScore),
          `${SENTIMENT_KO[post.sentiment] || post.sentiment} / ${HUMOR_KO[post.humor] || post.humor}`,
          post.url ? e('a', { href: post.url, target: '_blank', rel: 'noreferrer' }, '열기') : '-'
        ]) }))
      )
    );
  }

  function App() {
    const [data, setData] = useState({});
    const [scope, setScope] = useState(selectedKey());
    useEffect(() => {
      let cancelled = false;
      Promise.all(Object.keys(ACCOUNTS).map((key) => loadAccount(key).then((rows) => [key, rows])))
        .then((entries) => { if (!cancelled) setData(Object.fromEntries(entries)); })
        .catch((error) => console.error('low-confidence review load failed', error));
      const onClick = () => setTimeout(() => setScope(selectedKey()), 50);
      document.addEventListener('click', onClick);
      return () => { cancelled = true; document.removeEventListener('click', onClick); };
    }, []);
    const rows = useMemo(() => scope === 'all' ? Object.values(data).flat() : (data[scope] || []), [data, scope]);
    const label = scope === 'all' ? '전체 브랜드' : ACCOUNTS[scope].label;
    return e(ConfidenceReview, { rows, scope: label });
  }

  ReactDOM.createRoot(mount).render(e(App));
})();
