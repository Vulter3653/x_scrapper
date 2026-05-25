/* global React, ReactDOM */
(function () {
  const mount = document.getElementById('engagement-robustness-root');
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
  const HUMOR_ORDER = ['Affiliative humor', 'Self-enhancing humor', 'Aggressive humor', 'Self-defeating humor', 'unknown'];
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

  function quantile(values, ratio) {
    const arr = values.map(n).filter(Number.isFinite).sort((a, b) => a - b);
    if (!arr.length) return 0;
    const index = Math.min(arr.length - 1, Math.max(0, Math.ceil(arr.length * ratio) - 1));
    return arr[index];
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
    const humor = await readJson(`${account.base}/hsq_humor_classification.json`) || {};
    const humorById = new Map((humor.posts || []).map((row) => [String(row.id), row]));
    return posts.map((post) => {
      const id = String(post.id);
      const h = humorById.get(id) || {};
      return {
        id,
        account: key,
        brand: account.label,
        date: isoDate(dateOf(post)),
        text: textOf(post),
        url: post.tweet_url || post.url || '',
        engagement: engagement(post),
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
    const map = new Map();
    rows.forEach((row) => {
      const key = getter(row) || 'unknown';
      if (!map.has(key)) map.set(key, []);
      map.get(key).push(row);
    });
    return Array.from(map.entries()).map(([key, grouped]) => ({ key, rows: grouped, value: grouped.length }));
  }
  function Metric({ label, value, help, tone }) {
    return e('article', { className: `metric ${tone || ''}` }, e('span', null, label), e('strong', null, value), help ? e('small', null, help) : null);
  }
  function Table({ heads, rows }) {
    if (!rows.length) return e('div', { className: 'empty' }, '참여도 강건성 분석에 사용할 데이터가 없습니다.');
    return e('div', { className: 'table-wrap' }, e('table', null,
      e('thead', null, e('tr', null, heads.map((head) => e('th', { key: head }, head)))),
      e('tbody', null, rows.map((row, index) => e('tr', { key: index }, row.map((cell, cellIndex) => e('td', { key: cellIndex }, cell)))))
    ));
  }
  function Bars({ rows }) {
    if (!rows.length) return e('div', { className: 'empty' }, '사용 가능한 데이터가 없습니다.');
    const max = Math.max(...rows.map((row) => row.value), 1);
    return e('div', { className: 'bars' }, rows.map((row, index) => e('div', { className: 'bar', key: `${row.key}-${index}` },
      e('div', { className: 'bar-meta' }, e('span', { title: row.key }, row.key), e('b', null, compactValue(row.value))),
      e('div', { className: 'track' }, e('i', { style: { width: `${Math.max(2, row.value / max * 100)}%`, background: row.color || undefined } }))
    )));
  }
  function makeRows(rows) {
    const grouped = group(rows, (row) => row.humor);
    return HUMOR_ORDER.map((label) => grouped.find((item) => item.key === label) || { key: label, rows: [], value: 0 })
      .filter((item) => item.value > 0)
      .map((item) => {
        const engagements = item.rows.map((row) => row.engagement);
        return {
          humor: item.key,
          count: item.value,
          share: rows.length ? item.value / rows.length : 0,
          average: average(engagements),
          median: quantile(engagements, 0.5),
          p75: quantile(engagements, 0.75),
          p90: quantile(engagements, 0.9),
          max: Math.max(...engagements.map(n), 0),
          confidence: average(item.rows.map((row) => row.humorScore))
        };
      });
  }
  function Robustness({ rows, scope }) {
    const stats = makeRows(rows).sort((a, b) => b.median - a.median || b.p90 - a.p90);
    const highestMedian = stats[0];
    const highestP90 = stats.slice().sort((a, b) => b.p90 - a.p90)[0];
    const maxSpread = stats.slice().sort((a, b) => (b.p90 - b.median) - (a.p90 - a.median))[0];
    return e('section', { id: 'engagement-robustness', className: 'confidence-review-shell' },
      e('div', { className: 'section-title' }, e('span', null, '참여도 강건성'), e('h2', null, '유머 유형별 Engagement Robustness')),
      e('p', { className: 'panel-copy' }, `${scope} 기준으로 유머 유형별 평균, 중앙값, 상위 분위수, 최대값을 함께 비교하여 일부 바이럴 게시물에 따른 왜곡 가능성을 확인합니다.`),
      e('div', { className: 'metrics' },
        e(Metric, { label: '최고 중앙값 유머', value: highestMedian ? HUMOR_KO[highestMedian.humor] : '-', help: highestMedian ? `중앙값 ${compactValue(highestMedian.median)}` : '-' }),
        e(Metric, { label: '최고 P90 유머', value: highestP90 ? HUMOR_KO[highestP90.humor] : '-', help: highestP90 ? `90분위 ${compactValue(highestP90.p90)}` : '-' }),
        e(Metric, { label: '바이럴 편차 큰 유형', value: maxSpread ? HUMOR_KO[maxSpread.humor] : '-', help: maxSpread ? `P90-중앙값 ${compactValue(maxSpread.p90 - maxSpread.median)}` : '-' }),
        e(Metric, { label: '분석 게시물 수', value: fmt.format(rows.length), help: scope, tone: 'blue' })
      ),
      e('div', { className: 'grid' },
        e('article', { className: 'panel' }, e('h3', null, '유머 유형별 중앙값 참여도'), e(Bars, { rows: stats.map((item) => ({ key: HUMOR_KO[item.humor] || item.humor, value: item.median })) })),
        e('article', { className: 'panel' }, e('h3', null, '유머 유형별 90분위 참여도'), e(Bars, { rows: stats.map((item) => ({ key: HUMOR_KO[item.humor] || item.humor, value: item.p90 })) })),
        e('article', { className: 'panel wide' }, e('h3', null, '유머 유형별 참여도 강건성 표'), e(Table, { heads: ['유머 유형', '게시물', '비중', '평균', '중앙값', '75분위', '90분위', '최대값', '평균 유머 점수'], rows: stats.map((item) => [
          HUMOR_KO[item.humor] || item.humor,
          fmt.format(item.count),
          pct.format(item.share),
          compactValue(item.average),
          compactValue(item.median),
          compactValue(item.p75),
          compactValue(item.p90),
          compactValue(item.max),
          scoreFmt.format(item.confidence)
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
        .catch((error) => console.error('engagement robustness load failed', error));
      const onClick = () => setTimeout(() => setScope(selectedKey()), 50);
      document.addEventListener('click', onClick);
      return () => { cancelled = true; document.removeEventListener('click', onClick); };
    }, []);
    const rows = useMemo(() => scope === 'all' ? Object.values(data).flat() : (data[scope] || []), [data, scope]);
    const label = scope === 'all' ? '전체 브랜드' : ACCOUNTS[scope].label;
    return e(Robustness, { rows, scope: label });
  }
  ReactDOM.createRoot(mount).render(e(App));
})();
