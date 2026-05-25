/* global React, ReactDOM */
(function () {
  const mount = document.getElementById('humor-sentiment-root');
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

  const SENTIMENT_KO = {
    positive: '긍정',
    neutral: '중립',
    negative: '부정',
    unknown: '미분류'
  };

  const HUMOR_ORDER = ['Affiliative humor', 'Self-enhancing humor', 'Aggressive humor', 'Self-defeating humor', 'unknown'];
  const SENTIMENT_ORDER = ['positive', 'neutral', 'negative', 'unknown'];

  const fmt = new Intl.NumberFormat('ko-KR');
  const compact = new Intl.NumberFormat('ko-KR', { notation: 'compact', maximumFractionDigits: 1 });
  const pct = new Intl.NumberFormat('ko-KR', { style: 'percent', maximumFractionDigits: 1 });
  const scoreFmt = new Intl.NumberFormat('ko-KR', { maximumFractionDigits: 3 });
  const n = (value) => Number.isFinite(Number(value)) ? Number(value) : 0;
  const compactValue = (value) => Math.abs(n(value)) >= 1000 ? compact.format(n(value)) : fmt.format(Math.round(n(value)));
  const textOf = (post) => String((post && (post.text || post.content || post.tweet_text || post.post_text)) || '');
  const dateOf = (post) => (post && (post.date || post.created_at || post.timestamp)) || '';
  const parseDate = (value) => { const d = new Date(value); return Number.isNaN(d.getTime()) ? null : d; };
  const isoDate = (value) => { const d = parseDate(value); return d ? d.toISOString().slice(0, 10) : ''; };
  const engagement = (post) => n(post && (post.likes || post.like_count || post.favorite_count)) + n(post && (post.replies || post.reply_count)) + n(post && (post.retweets || post.retweet_count || post.reposts)) + n(post && (post.quotes || post.quote_count));

  function median(values) {
    const arr = values.map(n).filter(Number.isFinite).sort((a, b) => a - b);
    if (!arr.length) return 0;
    const mid = Math.floor(arr.length / 2);
    return arr.length % 2 ? arr[mid] : (arr[mid - 1] + arr[mid]) / 2;
  }

  function average(values) {
    const arr = values.map(n).filter(Number.isFinite);
    return arr.length ? arr.reduce((sum, value) => sum + value, 0) / arr.length : 0;
  }

  async function readJson(path) {
    const response = await fetch(path, { cache: 'no-store' });
    if (!response.ok) return null;
    return response.json();
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
      const sentimentRow = sentimentById.get(id) || {};
      const humorRow = humorById.get(id) || {};
      return {
        id,
        account: key,
        brand: account.label,
        date: isoDate(dateOf(post)),
        text: textOf(post),
        url: post.tweet_url || post.url || '',
        engagement: engagement(post),
        sentiment: sentimentRow.top_label || 'unknown',
        sentimentScore: n(sentimentRow.top_score),
        humor: humorRow.top_label || 'unknown',
        humorScore: n(humorRow.top_score)
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
    const map = new Map();
    rows.forEach((row) => {
      const key = getter(row) || 'unknown';
      if (!map.has(key)) map.set(key, []);
      map.get(key).push(row);
    });
    return Array.from(map.entries()).map(([key, grouped]) => ({ key, rows: grouped, value: grouped.length })).sort((a, b) => b.value - a.value);
  }

  function makeCellRows(rows) {
    const cells = [];
    HUMOR_ORDER.forEach((humor) => {
      SENTIMENT_ORDER.forEach((sentiment) => {
        const scoped = rows.filter((row) => row.humor === humor && row.sentiment === sentiment);
        if (!scoped.length) return;
        cells.push({
          humor,
          sentiment,
          rows: scoped,
          count: scoped.length,
          share: rows.length ? scoped.length / rows.length : 0,
          avgEngagement: average(scoped.map((row) => row.engagement)),
          medEngagement: median(scoped.map((row) => row.engagement)),
          avgHumorScore: average(scoped.map((row) => row.humorScore)),
          avgSentimentScore: average(scoped.map((row) => row.sentimentScore))
        });
      });
    });
    return cells.sort((a, b) => b.medEngagement - a.medEngagement || b.count - a.count);
  }

  function Metric({ label, value, help, tone }) {
    return e('article', { className: `metric ${tone || ''}` }, e('span', null, label), e('strong', null, value), help ? e('small', null, help) : null);
  }

  function Table({ heads, rows }) {
    if (!rows.length) return e('div', { className: 'empty' }, '사용 가능한 유머 × 감성 조합 데이터가 없습니다.');
    return e('div', { className: 'table-wrap' }, e('table', null,
      e('thead', null, e('tr', null, heads.map((head) => e('th', { key: head }, head)))),
      e('tbody', null, rows.map((row, index) => e('tr', { key: index }, row.map((cell, cellIndex) => e('td', { key: cellIndex }, cell)))))
    ));
  }

  function Bars({ rows, asPercent }) {
    if (!rows.length) return e('div', { className: 'empty' }, '사용 가능한 데이터가 없습니다.');
    const max = Math.max(...rows.map((row) => row.value), 1);
    return e('div', { className: 'bars' }, rows.map((row, index) => e('div', { className: 'bar', key: `${row.key}-${index}` },
      e('div', { className: 'bar-meta' }, e('span', { title: row.key }, row.key), e('b', null, asPercent ? pct.format(row.value) : compactValue(row.value))),
      e('div', { className: 'track' }, e('i', { style: { width: `${Math.max(2, row.value / max * 100)}%`, background: row.color || undefined } }))
    )));
  }

  function PostList({ rows }) {
    if (!rows.length) return e('div', { className: 'empty' }, '대표 게시물이 없습니다.');
    return e('div', { className: 'post-mini' }, rows.slice(0, 5).map((post) => e('a', { key: post.id, href: post.url, target: '_blank', rel: 'noreferrer' },
      e('b', null, `${post.brand} · ${post.date || '날짜 미상'} · 참여도 ${compactValue(post.engagement)}`),
      e('span', null, post.text || '(본문 없음)'),
      e('small', null, `${HUMOR_KO[post.humor] || post.humor} / ${SENTIMENT_KO[post.sentiment] || post.sentiment} · 유머 ${scoreFmt.format(post.humorScore)} · 감성 ${scoreFmt.format(post.sentimentScore)}`)
    )));
  }

  function HumorSentimentEngagement({ rows, scope }) {
    const cells = makeCellRows(rows);
    const bestByEngagement = cells[0];
    const largestCell = cells.slice().sort((a, b) => b.count - a.count)[0];
    const negativeAggressive = rows.filter((row) => row.humor === 'Aggressive humor' && row.sentiment === 'negative');
    const positiveAffiliative = rows.filter((row) => row.humor === 'Affiliative humor' && row.sentiment === 'positive');
    const humorEngagementRows = group(rows, (row) => row.humor).map((item) => ({ key: HUMOR_KO[item.key] || item.key, value: median(item.rows.map((row) => row.engagement)) }));
    const sentimentShareRows = group(rows, (row) => row.sentiment).map((item) => ({ key: SENTIMENT_KO[item.key] || item.key, value: rows.length ? item.value / rows.length : 0, color: item.key === 'negative' ? '#DC2626' : item.key === 'positive' ? '#16A34A' : undefined }));

    return e('section', { id: 'humor-sentiment-engagement', className: 'confidence-review-shell' },
      e('div', { className: 'section-title' }, e('span', null, '유머 × 감성 × 참여도'), e('h2', null, '유머-감성 결합 효과 요약')),
      e('p', { className: 'panel-copy' }, `${scope} 기준으로 HSQ 유머 유형과 감성 라벨의 조합별 게시물 비중 및 참여도 차이를 요약합니다.`),
      e('div', { className: 'metrics' },
        e(Metric, { label: '관찰 조합 수', value: fmt.format(cells.length), help: '유머 × 감성 cell 기준', tone: 'blue' }),
        e(Metric, { label: '최고 중앙값 참여 조합', value: bestByEngagement ? `${HUMOR_KO[bestByEngagement.humor]} / ${SENTIMENT_KO[bestByEngagement.sentiment]}` : '-', help: bestByEngagement ? `중앙값 ${compactValue(bestByEngagement.medEngagement)}` : '-' }),
        e(Metric, { label: '최대 빈도 조합', value: largestCell ? `${HUMOR_KO[largestCell.humor]} / ${SENTIMENT_KO[largestCell.sentiment]}` : '-', help: largestCell ? `${fmt.format(largestCell.count)}개 · ${pct.format(largestCell.share)}` : '-' }),
        e(Metric, { label: '공격적 유머 × 부정', value: fmt.format(negativeAggressive.length), help: `${pct.format(rows.length ? negativeAggressive.length / rows.length : 0)} of scope`, tone: 'danger' }),
        e(Metric, { label: '친화적 유머 × 긍정', value: fmt.format(positiveAffiliative.length), help: `${pct.format(rows.length ? positiveAffiliative.length / rows.length : 0)} of scope` }),
        e(Metric, { label: '전체 게시물 수', value: fmt.format(rows.length), help: scope })
      ),
      e('div', { className: 'grid' },
        e('article', { className: 'panel' }, e('h3', null, '유머 유형별 중앙값 참여도'), e(Bars, { rows: humorEngagementRows })),
        e('article', { className: 'panel' }, e('h3', null, '감성 라벨 비중'), e(Bars, { rows: sentimentShareRows, asPercent: true })),
        e('article', { className: 'panel wide' }, e('h3', null, '유머 × 감성 × 참여도 요약표'), e(Table, { heads: ['유머 유형', '감성', '게시물', '비중', '평균 참여도', '중앙값 참여도', '유머 점수', '감성 점수'], rows: cells.map((cell) => [
          HUMOR_KO[cell.humor] || cell.humor,
          SENTIMENT_KO[cell.sentiment] || cell.sentiment,
          fmt.format(cell.count),
          pct.format(cell.share),
          compactValue(cell.avgEngagement),
          compactValue(cell.medEngagement),
          scoreFmt.format(cell.avgHumorScore),
          scoreFmt.format(cell.avgSentimentScore)
        ]) })),
        e('article', { className: 'panel wide' }, e('h3', null, '해당 조합 기준 참여도 상위 게시물'), e(PostList, { rows: rows.slice().sort((a, b) => b.engagement - a.engagement) }))
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
        .catch((error) => console.error('humor-sentiment-engagement load failed', error));
      const onClick = () => setTimeout(() => setScope(selectedKey()), 50);
      document.addEventListener('click', onClick);
      return () => { cancelled = true; document.removeEventListener('click', onClick); };
    }, []);
    const rows = useMemo(() => scope === 'all' ? Object.values(data).flat() : (data[scope] || []), [data, scope]);
    const label = scope === 'all' ? '전체 브랜드' : ACCOUNTS[scope].label;
    return e(HumorSentimentEngagement, { rows, scope: label });
  }

  ReactDOM.createRoot(mount).render(e(App));
})();
