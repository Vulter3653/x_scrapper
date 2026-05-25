/* global React, ReactDOM */
(function () {
  const root = document.getElementById('root');
  if (!window.React || !window.ReactDOM) {
    root.innerHTML = '<div class="boot-error"><strong>Dashboard boot error</strong><span>React or ReactDOM failed to load.</span></div>';
    return;
  }

  const e = React.createElement;
  const { useEffect, useMemo, useState } = React;

  const ACCOUNTS = {
    wendys: { label: "Wendy's", color: '#E2231A', base: 'data/wendys' },
    cocacola: { label: 'Coca-Cola', color: '#111827', base: 'data/cocacola' },
    moonpie: { label: 'MoonPie', color: '#F97316', base: 'data/moonpie' }
  };
  Object.values(ACCOUNTS).forEach((a) => {
    a.posts = `${a.base}/posts.json`;
    a.lda = `${a.base}/lda_topics.json`;
    a.sentiment = `${a.base}/zero_shot_sentiment.json`;
    a.humor = `${a.base}/hsq_humor_classification.json`;
    a.scrapeState = `${a.base}/scrape_state.json`;
  });

  const HUMOR_LABELS = ['Affiliative humor', 'Self-enhancing humor', 'Aggressive humor', 'Self-defeating humor'];
  const SENTIMENT_LABELS = ['positive', 'neutral', 'negative', 'unknown'];
  const fmt = new Intl.NumberFormat('en-US');
  const compact = new Intl.NumberFormat('en-US', { notation: 'compact', maximumFractionDigits: 1 });
  const percent = new Intl.NumberFormat('en-US', { style: 'percent', maximumFractionDigits: 1 });
  const scoreFmt = new Intl.NumberFormat('en-US', { maximumFractionDigits: 3 });

  const num = (v) => Number.isFinite(Number(v)) ? Number(v) : 0;
  const cv = (v) => Math.abs(num(v)) >= 1000 ? compact.format(num(v)) : fmt.format(Math.round(num(v)));
  const txt = (p) => String((p && (p.text || p.content || p.tweet_text || p.post_text)) || '');
  const rawDate = (p) => (p && (p.date || p.created_at || p.timestamp)) || '';
  const parsed = (v) => { const d = new Date(v); return Number.isNaN(d.getTime()) ? null : d; };
  const iso = (v) => { const d = parsed(v); return d ? d.toISOString().slice(0, 10) : ''; };
  const month = (v) => { const d = parsed(v); return d ? d.toISOString().slice(0, 7) : 'unknown'; };
  const likes = (p) => num(p && (p.likes || p.like_count || p.favorite_count));
  const replies = (p) => num(p && (p.replies || p.reply_count));
  const retweets = (p) => num(p && (p.retweets || p.retweet_count || p.reposts));
  const quotes = (p) => num(p && (p.quotes || p.quote_count));
  const engagement = (p) => likes(p) + replies(p) + retweets(p) + quotes(p);

  function median(vals) {
    const a = vals.map(num).filter(Number.isFinite).sort((x, y) => x - y);
    if (!a.length) return 0;
    const m = Math.floor(a.length / 2);
    return a.length % 2 ? a[m] : (a[m - 1] + a[m]) / 2;
  }
  function avg(vals) {
    const a = vals.map(num).filter(Number.isFinite);
    return a.length ? a.reduce((s, v) => s + v, 0) / a.length : 0;
  }
  function perc(vals, r) {
    const a = vals.map(num).filter(Number.isFinite).sort((x, y) => x - y);
    if (!a.length) return 0;
    return a[Math.min(a.length - 1, Math.max(0, Math.ceil(a.length * r) - 1))];
  }
  function group(rows, getter) {
    const m = new Map();
    rows.forEach((row) => {
      const k = getter(row) || 'unknown';
      if (!m.has(k)) m.set(k, []);
      m.get(k).push(row);
    });
    return m;
  }
  function counts(rows, getter) {
    return Array.from(group(rows, getter).entries()).map(([key, rows]) => ({ key, rows, value: rows.length })).sort((a, b) => b.value - a.value);
  }

  async function loadJson(path) {
    const r = await fetch(path, { cache: 'no-store' });
    if (!r.ok) throw new Error(`${path}: ${r.status}`);
    return r.json();
  }
  async function loadAccount(key) {
    const c = ACCOUNTS[key];
    const ds = { key, posts: [], lda: null, sentiment: null, humor: null, scrapeState: null, errors: {} };
    for (const [name, path] of Object.entries({ posts: c.posts, lda: c.lda, sentiment: c.sentiment, humor: c.humor, scrapeState: c.scrapeState })) {
      try { ds[name] = await loadJson(path); } catch (err) { ds.errors[name] = err.message; }
    }
    return ds;
  }

  function enrich(key, ds) {
    const c = ACCOUNTS[key];
    const sentiment = new Map(((ds.sentiment && ds.sentiment.posts) || []).map((r) => [String(r.id), r]));
    const humor = new Map(((ds.humor && ds.humor.posts) || []).map((r) => [String(r.id), r]));
    const topics = new Map();
    ((ds.lda && ds.lda.topics) || []).forEach((topic) => {
      (topic.representative_posts || []).forEach((post) => {
        topics.set(String(post.id), { id: topic.topic_id, terms: topic.top_terms || [], score: num(post.score) });
      });
    });
    const threshold = perc((ds.posts || []).map(engagement), 0.95);
    return (ds.posts || []).map((post) => {
      const id = String(post.id);
      const s = sentiment.get(id) || {};
      const h = humor.get(id) || {};
      const topic = topics.get(id) || null;
      const text = txt(post);
      const total = engagement(post);
      return Object.assign({}, post, {
        id, account: key, brand: c.label, brand_color: c.color,
        date_iso: iso(rawDate(post)), month_key: month(rawDate(post)),
        text_normalized: text,
        likes_count: likes(post), replies_count: replies(post), retweets_count: retweets(post), quotes_count: quotes(post),
        total_engagement: total,
        text_length: text.length,
        word_count: text.trim().split(/\s+/).filter(Boolean).length,
        has_url: /(https?:\/\/|www\.)/i.test(text),
        hashtag_count: (text.match(/(^|\s)#[\p{L}\p{N}_]+/gu) || []).length,
        mention_count: (text.match(/(^|\s)@[A-Za-z0-9_]+/g) || []).length,
        sentiment_label: s.top_label || 'unknown', sentiment_score: num(s.top_score),
        humor_label: h.top_label || 'unknown', humor_score: num(h.top_score),
        topic_id: topic ? topic.id : null, topic_terms: topic ? topic.terms : [], topic_score: topic ? topic.score : 0,
        is_viral: total >= threshold && total > 0
      });
    });
  }

  function stats(rows) {
    const total = rows.length;
    const dates = rows.map((r) => parsed(r.date_iso)).filter(Boolean).sort((a, b) => a - b);
    const hTop = counts(rows, (r) => r.humor_label).filter((r) => r.key !== 'unknown')[0];
    const sTop = counts(rows, (r) => r.sentiment_label).filter((r) => r.key !== 'unknown')[0];
    return {
      total,
      range: dates.length ? `${dates[0].toISOString().slice(0, 10)} - ${dates[dates.length - 1].toISOString().slice(0, 10)}` : '-',
      brands: new Set(rows.map((r) => r.account)).size,
      days: new Set(rows.map((r) => r.date_iso).filter(Boolean)).size,
      engagement: rows.reduce((s, r) => s + r.total_engagement, 0),
      avg: avg(rows.map((r) => r.total_engagement)),
      med: median(rows.map((r) => r.total_engagement)),
      p95: perc(rows.map((r) => r.total_engagement), 0.95),
      viral: total ? rows.filter((r) => r.is_viral).length / total : 0,
      pos: total ? rows.filter((r) => r.sentiment_label === 'positive').length / total : 0,
      neg: total ? rows.filter((r) => r.sentiment_label === 'negative').length / total : 0,
      humor: hTop ? hTop.key : '-',
      sent: sTop ? sTop.key : '-'
    };
  }

  function defaultFilters() {
    return { brand: 'all', search: '', from: '', to: '', sentiment: 'all', humor: 'all', topic: 'all', viral: 'all', minHumorScore: '0', minSentimentScore: '0', sort: 'date' };
  }
  function applyFilters(rows, filters) {
    const q = filters.search.trim().toLowerCase();
    const from = filters.from ? new Date(`${filters.from}T00:00:00Z`) : null;
    const to = filters.to ? new Date(`${filters.to}T23:59:59Z`) : null;
    const filtered = rows.filter((p) => {
      const d = parsed(p.date_iso);
      if (filters.brand !== 'all' && p.account !== filters.brand) return false;
      if (filters.sentiment !== 'all' && p.sentiment_label !== filters.sentiment) return false;
      if (filters.humor !== 'all' && p.humor_label !== filters.humor) return false;
      if (filters.topic !== 'all' && String(p.topic_id) !== filters.topic) return false;
      if (filters.viral === 'viral' && !p.is_viral) return false;
      if (filters.viral === 'nonviral' && p.is_viral) return false;
      if (p.humor_score < num(filters.minHumorScore)) return false;
      if (p.sentiment_score < num(filters.minSentimentScore)) return false;
      if (from && (!d || d < from)) return false;
      if (to && (!d || d > to)) return false;
      if (!q) return true;
      return [p.text_normalized, p.brand, p.sentiment_label, p.humor_label, p.topic_terms.join(' '), p.tweet_url].some((v) => String(v || '').toLowerCase().includes(q));
    });
    filtered.sort((a, b) => {
      if (filters.sort === 'engagement') return b.total_engagement - a.total_engagement;
      if (filters.sort === 'humor') return b.humor_score - a.humor_score;
      if (filters.sort === 'sentiment') return b.sentiment_score - a.sentiment_score;
      return (parsed(b.date_iso)?.getTime() || 0) - (parsed(a.date_iso)?.getTime() || 0);
    });
    return filtered;
  }

  function csvEscape(value) { return `"${String(value == null ? '' : value).replace(/"/g, '""')}"`; }
  function downloadCsv(rows) {
    const columns = ['date_iso','brand','id','tweet_url','text_normalized','total_engagement','likes_count','replies_count','retweets_count','quotes_count','sentiment_label','sentiment_score','humor_label','humor_score','topic_id','topic_terms','is_viral'];
    const body = rows.map((row) => columns.map((column) => csvEscape(column === 'topic_terms' ? row.topic_terms.join('|') : row[column])).join(','));
    const blob = new Blob([[columns.join(','), ...body].join('\n')], { type: 'text/csv;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `x-brand-dashboard-${new Date().toISOString().slice(0, 10)}.csv`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  }

  function insights(rows) {
    if (!rows.length) return ['No posts match the current filters.'];
    const brand = counts(rows, (r) => r.brand).map((r) => ({ key: r.key, value: median(r.rows.map((p) => p.total_engagement)), count: r.value })).sort((a, b) => b.value - a.value)[0];
    const humor = counts(rows, (r) => r.humor_label).filter((r) => r.key !== 'unknown').map((r) => ({ key: r.key, value: median(r.rows.map((p) => p.total_engagement)), count: r.value })).sort((a, b) => b.value - a.value)[0];
    const aggressive = rows.filter((r) => r.humor_label === 'Aggressive humor');
    const unknownHumor = rows.filter((r) => r.humor_label === 'unknown').length / rows.length;
    const out = [];
    if (brand) out.push(`${brand.key} has the highest median engagement in the current view (${cv(brand.value)} across ${fmt.format(brand.count)} posts).`);
    if (humor) out.push(`${humor.key} has the highest median engagement among visible HSQ humor types (${cv(humor.value)}).`);
    out.push(`Negative sentiment accounts for ${percent.format(rows.filter((r) => r.sentiment_label === 'negative').length / rows.length)} of visible posts.`);
    out.push(`Aggressive humor accounts for ${percent.format(aggressive.length / rows.length)} of visible posts, with ${cv(median(aggressive.map((p) => p.total_engagement)))} median engagement.`);
    if (unknownHumor > 0.1) out.push(`Humor coverage needs attention: ${percent.format(unknownHumor)} of visible posts have unknown humor labels.`);
    return out;
  }

  function qualityRows(rows) {
    const total = rows.length || 1;
    return [
      ['Missing text', fmt.format(rows.filter((r) => !r.text_normalized.trim()).length), percent.format(rows.filter((r) => !r.text_normalized.trim()).length / total)],
      ['Unknown sentiment', fmt.format(rows.filter((r) => r.sentiment_label === 'unknown').length), percent.format(rows.filter((r) => r.sentiment_label === 'unknown').length / total)],
      ['Unknown humor', fmt.format(rows.filter((r) => r.humor_label === 'unknown').length), percent.format(rows.filter((r) => r.humor_label === 'unknown').length / total)],
      ['Missing topic assignment', fmt.format(rows.filter((r) => r.topic_id === null).length), percent.format(rows.filter((r) => r.topic_id === null).length / total)],
      ['Zero engagement', fmt.format(rows.filter((r) => r.total_engagement === 0).length), percent.format(rows.filter((r) => r.total_engagement === 0).length / total)]
    ];
  }

  function Metric({ label, value, help, tone }) {
    return e('article', { className: `metric ${tone || ''}` }, e('span', null, label), e('strong', null, value), help ? e('small', null, help) : null);
  }
  function Section({ id, kicker, title, children }) {
    return e('section', { id, className: 'section' }, e('div', { className: 'section-title' }, e('span', null, kicker), e('h2', null, title)), children);
  }
  function Bars({ rows, asPercent }) {
    if (!rows.length) return e('div', { className: 'empty' }, 'No data available');
    const max = Math.max(...rows.map((r) => r.value), 1);
    return e('div', { className: 'bars' }, rows.map((r, i) => e('div', { className: 'bar', key: `${r.key}-${i}` },
      e('div', { className: 'bar-meta' }, e('span', { title: r.key }, r.key), e('b', null, asPercent ? percent.format(r.value) : cv(r.value))),
      e('div', { className: 'track' }, e('i', { style: { width: `${Math.max(2, r.value / max * 100)}%`, background: r.color || undefined } }))
    )));
  }
  function DataTable({ heads, rows }) {
    if (!rows.length) return e('div', { className: 'empty' }, 'No data available');
    return e('div', { className: 'table-wrap' }, e('table', null,
      e('thead', null, e('tr', null, heads.map((head) => e('th', { key: head }, head)))),
      e('tbody', null, rows.map((row, index) => e('tr', { key: index }, row.map((cell, cellIndex) => e('td', { key: cellIndex }, cell)))))
    ));
  }

  function Header({ selected, setSelected, status, lastUpdated }) {
    return e('header', { className: 'top' },
      e('div', null,
        e('div', { className: 'title' }, e('h1', null, 'X Brand Intelligence Dashboard'), e('em', { className: status }, status)),
        e('p', null, 'Advanced React analytics for all-brand and brand-specific X posts, sentiment, topics, and HSQ humor.'),
        e('small', null, `Last updated: ${lastUpdated}`)
      ),
      e('nav', { className: 'tabs' },
        e('button', { className: selected === 'all' ? 'on' : '', onClick: () => setSelected('all') }, 'All Brands'),
        Object.entries(ACCOUNTS).map(([key, account]) => e('button', { key, className: selected === key ? 'on' : '', onClick: () => setSelected(key) }, account.label))
      )
    );
  }

  function Filters({ filters, setFilters, topics, count }) {
    const update = (key, value) => setFilters(Object.assign({}, filters, { [key]: value }));
    return e('aside', { className: 'filters' },
      e('div', { className: 'filter-head' }, e('b', null, 'Filters'), e('span', null, `${fmt.format(count)} posts`)),
      e('label', null, 'Brand', e('select', { value: filters.brand, onChange: (ev) => update('brand', ev.target.value) }, e('option', { value: 'all' }, 'All brands'), Object.entries(ACCOUNTS).map(([key, account]) => e('option', { key, value: key }, account.label)))),
      e('label', null, 'Search', e('input', { type: 'search', value: filters.search, onChange: (ev) => update('search', ev.target.value), placeholder: 'text, humor, sentiment, topic' })),
      e('div', { className: 'two' },
        e('label', null, 'From', e('input', { type: 'date', value: filters.from, onChange: (ev) => update('from', ev.target.value) })),
        e('label', null, 'To', e('input', { type: 'date', value: filters.to, onChange: (ev) => update('to', ev.target.value) }))
      ),
      e('label', null, 'Sentiment', e('select', { value: filters.sentiment, onChange: (ev) => update('sentiment', ev.target.value) }, e('option', { value: 'all' }, 'All sentiment'), SENTIMENT_LABELS.map((label) => e('option', { key: label, value: label }, label)))),
      e('label', null, 'HSQ Humor', e('select', { value: filters.humor, onChange: (ev) => update('humor', ev.target.value) }, e('option', { value: 'all' }, 'All humor'), HUMOR_LABELS.map((label) => e('option', { key: label, value: label }, label)), e('option', { value: 'unknown' }, 'unknown'))),
      e('label', null, 'Topic', e('select', { value: filters.topic, onChange: (ev) => update('topic', ev.target.value) }, e('option', { value: 'all' }, 'All topics'), topics.map((topic) => e('option', { key: topic, value: topic }, `Topic ${topic}`)))),
      e('label', null, 'Viral', e('select', { value: filters.viral, onChange: (ev) => update('viral', ev.target.value) }, e('option', { value: 'all' }, 'All posts'), e('option', { value: 'viral' }, 'Viral only'), e('option', { value: 'nonviral' }, 'Non-viral only'))),
      e('div', { className: 'two' },
        e('label', null, 'Min Humor Score', e('input', { type: 'number', min: '0', max: '1', step: '0.05', value: filters.minHumorScore, onChange: (ev) => update('minHumorScore', ev.target.value) })),
        e('label', null, 'Min Sentiment Score', e('input', { type: 'number', min: '0', max: '1', step: '0.05', value: filters.minSentimentScore, onChange: (ev) => update('minSentimentScore', ev.target.value) }))
      ),
      e('label', null, 'Sort', e('select', { value: filters.sort, onChange: (ev) => update('sort', ev.target.value) }, e('option', { value: 'date' }, 'Newest'), e('option', { value: 'engagement' }, 'Engagement'), e('option', { value: 'humor' }, 'Humor score'), e('option', { value: 'sentiment' }, 'Sentiment score'))),
      e('button', { onClick: () => setFilters(defaultFilters()) }, 'Reset')
    );
  }

  function Status({ datasets }) {
    return e(Section, { id: 'status', kicker: 'Data readiness', title: 'Dataset Status' },
      e(DataTable, { heads: ['Brand', 'Posts', 'LDA', 'Sentiment', 'HSQ Humor'], rows: Object.entries(ACCOUNTS).map(([key, account]) => {
        const d = datasets[key] || {};
        return [account.label, d.posts && d.posts.length ? `${fmt.format(d.posts.length)} loaded` : 'missing', d.lda ? 'available' : 'missing', d.sentiment ? 'available' : 'missing', d.humor ? 'available' : 'missing'];
      }) })
    );
  }

  function Overview({ summary, selected }) {
    return e(Section, { id: 'overview', kicker: 'Executive summary', title: selected === 'all' ? 'All Brands Overview' : `${ACCOUNTS[selected].label} Overview` },
      e('div', { className: 'metrics' },
        e(Metric, { label: 'Total Posts', value: fmt.format(summary.total), help: `${summary.brands} brand(s), ${summary.days} active day(s)`, tone: 'red' }),
        e(Metric, { label: 'Date Range', value: summary.range, help: 'parsed post timestamps' }),
        e(Metric, { label: 'Total Engagement', value: cv(summary.engagement), help: `Avg ${cv(summary.avg)} per post` }),
        e(Metric, { label: 'Median Engagement', value: cv(summary.med), help: `P95 ${cv(summary.p95)}` }),
        e(Metric, { label: 'Viral Share', value: percent.format(summary.viral), help: 'top 5% by engagement' }),
        e(Metric, { label: 'Dominant Humor', value: summary.humor, help: `Positive ${percent.format(summary.pos)} / Negative ${percent.format(summary.neg)}`, tone: 'blue' })
      )
    );
  }

  function Advanced({ rows }) {
    const confidenceRows = [
      ['Average sentiment score', scoreFmt.format(avg(rows.map((r) => r.sentiment_score)))],
      ['Average humor score', scoreFmt.format(avg(rows.map((r) => r.humor_score)))],
      ['Posts with sentiment score ≥ .70', fmt.format(rows.filter((r) => r.sentiment_score >= 0.7).length)],
      ['Posts with humor score ≥ .70', fmt.format(rows.filter((r) => r.humor_score >= 0.7).length)]
    ];
    return e(Section, { id: 'advanced', kicker: 'Advanced analytics', title: 'Insights, Quality Audit, and Export' },
      e('div', { className: 'grid' },
        e('article', { className: 'panel' }, e('h3', null, 'Auto Insights'), e('ul', { className: 'insight-list' }, insights(rows).map((item, i) => e('li', { key: i }, item)))),
        e('article', { className: 'panel' }, e('h3', null, 'Data Quality Audit'), e(DataTable, { heads: ['Check', 'Count', 'Share'], rows: qualityRows(rows) })),
        e('article', { className: 'panel' }, e('h3', null, 'Confidence Diagnostics'), e(DataTable, { heads: ['Metric', 'Value'], rows: confidenceRows })),
        e('article', { className: 'panel' }, e('h3', null, 'Export Current View'), e('p', { className: 'panel-copy' }, 'Download the currently filtered post-level dataset with sentiment, humor, topic, and engagement fields.'), e('button', { className: 'primary-action', disabled: !rows.length, onClick: () => downloadCsv(rows) }, 'Download filtered CSV')),
        e('article', { className: 'panel wide' }, e('h3', null, 'Top Engagement Posts'), e(PostList, { rows: rows.slice().sort((a, b) => b.total_engagement - a.total_engagement).slice(0, 5) }))
      )
    );
  }

  function Descriptives({ rows }) {
    const s = stats(rows);
    const brandRows = counts(rows, (r) => r.brand).map((r) => ({ key: r.key, value: median(r.rows.map((p) => p.total_engagement)), color: r.rows[0] && r.rows[0].brand_color }));
    return e(Section, { id: 'descriptives', kicker: 'Descriptive statistics', title: 'Dataset and Engagement Profile' },
      e('div', { className: 'grid' },
        e('article', { className: 'panel' }, e('h3', null, 'Summary'), e(DataTable, { heads: ['Metric', 'Value'], rows: [['Posts', fmt.format(s.total)], ['Date range', s.range], ['Total engagement', cv(s.engagement)], ['Average engagement', cv(s.avg)], ['Median engagement', cv(s.med)], ['Dominant sentiment', s.sent], ['Dominant humor', s.humor]] })),
        e('article', { className: 'panel' }, e('h3', null, 'Median Engagement by Brand'), e(Bars, { rows: brandRows }))
      )
    );
  }

  function Comparison({ rows, selected }) {
    if (selected !== 'all') return e(Section, { id: 'comparison', kicker: 'Cross-brand analysis', title: 'Brand Comparison' }, e('div', { className: 'empty' }, 'Brand comparison is shown in the All Brands view.'));
    const items = Object.entries(ACCOUNTS).map(([key, account]) => {
      const scoped = rows.filter((r) => r.account === key);
      return { account, rows: scoped, s: stats(scoped) };
    });
    return e(Section, { id: 'comparison', kicker: 'Cross-brand analysis', title: 'Brand Comparison' },
      e('div', { className: 'grid' },
        e('article', { className: 'panel' }, e('h3', null, 'Post Count by Brand'), e(Bars, { rows: items.map((it) => ({ key: it.account.label, value: it.rows.length, color: it.account.color })) })),
        e('article', { className: 'panel' }, e('h3', null, 'Total Engagement by Brand'), e(Bars, { rows: items.map((it) => ({ key: it.account.label, value: it.s.engagement, color: it.account.color })) })),
        e('article', { className: 'panel wide' }, e('h3', null, 'Brand Summary'), e(DataTable, { heads: ['Brand', 'Posts', 'Median Engagement', 'Positive', 'Negative', 'Viral', 'Dominant Humor'], rows: items.map((it) => [it.account.label, fmt.format(it.rows.length), cv(it.s.med), percent.format(it.s.pos), percent.format(it.s.neg), percent.format(it.s.viral), it.s.humor]) }))
      )
    );
  }

  function Evidence({ rows }) {
    const viral = rows.filter((r) => r.is_viral);
    return e(Section, { id: 'evidence', kicker: 'Model-free evidence', title: 'Observed Patterns Before Modeling' },
      e('div', { className: 'grid' },
        e('article', { className: 'panel' }, e('h3', null, 'Humor Type → Median Engagement'), e(Bars, { rows: counts(rows, (r) => r.humor_label).map((r) => ({ key: r.key, value: median(r.rows.map((p) => p.total_engagement)) })) })),
        e('article', { className: 'panel' }, e('h3', null, 'Sentiment → Median Engagement'), e(Bars, { rows: counts(rows, (r) => r.sentiment_label).map((r) => ({ key: r.key, value: median(r.rows.map((p) => p.total_engagement)) })) })),
        e('article', { className: 'panel' }, e('h3', null, 'Viral Humor Composition'), e(Bars, { asPercent: true, rows: counts(viral, (r) => r.humor_label).map((r) => ({ key: r.key, value: viral.length ? r.value / viral.length : 0, color: r.key === 'Aggressive humor' ? '#DC2626' : undefined })) })),
        e('article', { className: 'panel' }, e('h3', null, 'Humor × Sentiment Cells'), e(DataTable, { heads: ['Cell', 'Posts', 'Median Engagement'], rows: counts(rows, (r) => `${r.humor_label} / ${r.sentiment_label}`).slice(0, 8).map((r) => [r.key, fmt.format(r.value), cv(median(r.rows.map((p) => p.total_engagement)))]) }))
      )
    );
  }

  function Posting({ rows }) {
    const months = counts(rows, (r) => r.month_key).filter((r) => r.key !== 'unknown').slice(0, 18).reverse();
    const mix = [
      { key: 'Likes', value: rows.reduce((s, r) => s + r.likes_count, 0) },
      { key: 'Replies', value: rows.reduce((s, r) => s + r.replies_count, 0) },
      { key: 'Retweets', value: rows.reduce((s, r) => s + r.retweets_count, 0) },
      { key: 'Quotes', value: rows.reduce((s, r) => s + r.quotes_count, 0) }
    ];
    return e(Section, { id: 'posting', kicker: 'Posting and engagement', title: 'Posting Volume and Interaction Mix' }, e('div', { className: 'grid' }, e('article', { className: 'panel' }, e('h3', null, 'Recent Monthly Posting Volume'), e(Bars, { rows: months })), e('article', { className: 'panel' }, e('h3', null, 'Engagement Mix'), e(Bars, { rows: mix }))));
  }

  function Sentiment({ rows, selected }) {
    const distribution = counts(rows, (r) => r.sentiment_label).map((r) => ({ key: r.key, value: rows.length ? r.value / rows.length : 0, color: r.key === 'positive' ? '#16A34A' : r.key === 'negative' ? '#DC2626' : '#94A3B8' }));
    return e(Section, { id: 'sentiment', kicker: 'Zero-shot sentiment', title: 'Sentiment Analysis' },
      e('div', { className: 'grid' },
        e('article', { className: 'panel' }, e('h3', null, 'Sentiment Distribution'), e(Bars, { rows: distribution, asPercent: true })),
        e('article', { className: 'panel' }, e('h3', null, selected === 'all' ? 'Sentiment by Brand' : 'Representative Negative Posts'), selected === 'all' ? e(DataTable, { heads: ['Brand', 'Positive', 'Neutral', 'Negative'], rows: Object.entries(ACCOUNTS).map(([key, account]) => { const scoped = rows.filter((r) => r.account === key); return [account.label, percent.format(scoped.length ? scoped.filter((r) => r.sentiment_label === 'positive').length / scoped.length : 0), percent.format(scoped.length ? scoped.filter((r) => r.sentiment_label === 'neutral').length / scoped.length : 0), percent.format(scoped.length ? scoped.filter((r) => r.sentiment_label === 'negative').length / scoped.length : 0)]; }) }) : e(PostList, { rows: rows.filter((r) => r.sentiment_label === 'negative').slice(0, 5) }))
      )
    );
  }

  function Humor({ rows, selected }) {
    const aggressive = rows.filter((r) => r.humor_label === 'Aggressive humor');
    const ag = stats(aggressive);
    const distribution = counts(rows, (r) => r.humor_label).map((r) => ({ key: r.key, value: rows.length ? r.value / rows.length : 0, color: r.key === 'Aggressive humor' ? '#DC2626' : r.key === 'Self-enhancing humor' ? '#2563EB' : undefined }));
    return e(Section, { id: 'humor', kicker: 'HSQ humor classification', title: 'Humor Analysis' },
      e('div', { className: 'grid' },
        e('article', { className: 'panel' }, e('h3', null, 'Humor Type Distribution'), e(Bars, { rows: distribution, asPercent: true })),
        e('article', { className: 'panel' }, e('h3', null, 'Aggressive Humor Focus'), e('div', { className: 'focus' }, e(Metric, { label: 'Aggressive Posts', value: fmt.format(aggressive.length), help: percent.format(rows.length ? aggressive.length / rows.length : 0), tone: 'danger' }), e(Metric, { label: 'Median Engagement', value: cv(ag.med), help: 'aggressive posts' }), e(Metric, { label: 'Negative Share', value: percent.format(ag.neg), help: 'within aggressive humor' }))),
        e('article', { className: 'panel wide' }, e('h3', null, selected === 'all' ? 'Humor Type by Brand' : 'Representative Humor Posts'), selected === 'all' ? e(DataTable, { heads: ['Brand', 'Affiliative', 'Self-enhancing', 'Aggressive', 'Self-defeating'], rows: Object.entries(ACCOUNTS).map(([key, account]) => { const scoped = rows.filter((r) => r.account === key); return [account.label].concat(HUMOR_LABELS.map((label) => percent.format(scoped.length ? scoped.filter((r) => r.humor_label === label).length / scoped.length : 0))); }) }) : e(PostList, { rows: rows.slice(0, 6) }))
      )
    );
  }

  function Topics({ rows }) {
    const topicRows = counts(rows.filter((r) => r.topic_id !== null), (r) => String(r.topic_id)).slice(0, 12);
    return e(Section, { id: 'topics', kicker: 'LDA topics', title: 'Topic Analysis' },
      e('div', { className: 'grid' },
        e('article', { className: 'panel' }, e('h3', null, 'Topic Share'), e(Bars, { rows: topicRows.map((r) => ({ key: `Topic ${r.key}`, value: r.value })) })),
        e('article', { className: 'panel wide' }, e('h3', null, 'Topic × Engagement × Humor'), e(DataTable, { heads: ['Topic', 'Top Terms', 'Posts', 'Median Engagement', 'Dominant Humor'], rows: topicRows.map((r) => [`Topic ${r.key}`, r.rows[0] && r.rows[0].topic_terms ? r.rows[0].topic_terms.slice(0, 6).join(', ') : '-', fmt.format(r.value), cv(median(r.rows.map((p) => p.total_engagement))), counts(r.rows, (p) => p.humor_label)[0] ? counts(r.rows, (p) => p.humor_label)[0].key : '-']) }))
      )
    );
  }

  function PostList({ rows }) {
    if (!rows.length) return e('div', { className: 'empty' }, 'No data available');
    return e('div', { className: 'post-mini' }, rows.map((post) => e('a', { key: post.id, href: post.tweet_url, target: '_blank', rel: 'noreferrer' }, e('b', null, `${post.brand} · ${post.date_iso}`), e('span', null, post.text_normalized || '(no text)'), e('small', null, `${post.humor_label} · ${post.sentiment_label} · ${cv(post.total_engagement)} engagement`))));
  }

  function Explorer({ rows }) {
    const [page, setPage] = useState(1);
    useEffect(() => setPage(1), [rows.length]);
    const pageSize = 30, pages = Math.max(1, Math.ceil(rows.length / pageSize)), current = Math.min(page, pages), visible = rows.slice((current - 1) * pageSize, current * pageSize);
    return e(Section, { id: 'posts', kicker: 'Post-level evidence', title: 'Post Explorer' },
      e('div', { className: 'post-head' }, e('p', null, `${fmt.format(rows.length)} posts after filters. Page ${current} of ${pages}.`), e('div', null, e('button', { disabled: current <= 1, onClick: () => setPage(current - 1) }, 'Prev'), e('button', { disabled: current >= pages, onClick: () => setPage(current + 1) }, 'Next'))),
      e(DataTable, { heads: ['Date', 'Brand', 'Text', 'Engagement', 'Sentiment', 'Humor', 'Topic', 'Link'], rows: visible.map((post) => [post.date_iso, post.brand, e('span', { className: 'post-text' }, post.text_normalized || '(no text)'), cv(post.total_engagement), `${post.sentiment_label} (${scoreFmt.format(post.sentiment_score)})`, `${post.humor_label} (${scoreFmt.format(post.humor_score)})`, post.topic_id === null ? '-' : `Topic ${post.topic_id}`, post.tweet_url ? e('a', { href: post.tweet_url, target: '_blank', rel: 'noreferrer' }, 'Open') : '-']) }),
      e('div', { className: 'cards' }, visible.map((post) => e('article', { key: post.id }, e('b', null, `${post.brand} · ${post.date_iso}`), e('p', null, post.text_normalized || '(no text)'), e('small', null, `${cv(post.total_engagement)} engagement · ${post.sentiment_label} · ${post.humor_label}`), post.tweet_url ? e('a', { href: post.tweet_url, target: '_blank', rel: 'noreferrer' }, 'Open post') : null)))
    );
  }

  function App() {
    const [datasets, setDatasets] = useState({});
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const [selected, setSelected] = useState('all');
    const [filters, setFilters] = useState(defaultFilters());

    useEffect(() => {
      let cancelled = false;
      Promise.all(Object.keys(ACCOUNTS).map((key) => loadAccount(key).then((dataset) => [key, dataset])))
        .then((entries) => { if (!cancelled) { setDatasets(Object.fromEntries(entries)); setLoading(false); } })
        .catch((err) => { if (!cancelled) { setError(err.message); setLoading(false); } });
      return () => { cancelled = true; };
    }, []);

    const enrichedByAccount = useMemo(() => {
      const result = {};
      Object.entries(datasets).forEach(([key, dataset]) => { result[key] = enrich(key, dataset); });
      return result;
    }, [datasets]);

    const allPosts = useMemo(() => Object.values(enrichedByAccount).flat(), [enrichedByAccount]);
    const scoped = selected === 'all' ? allPosts : (enrichedByAccount[selected] || []);
    const topics = Array.from(new Set(scoped.filter((p) => p.topic_id !== null).map((p) => String(p.topic_id)))).sort((a, b) => Number(a) - Number(b));
    const effective = selected === 'all' ? filters : Object.assign({}, filters, { brand: 'all' });
    const visible = useMemo(() => applyFilters(scoped, effective), [scoped, effective]);
    const summary = stats(visible);
    const latestValues = Object.values(datasets).flatMap((dataset) => [dataset.scrapeState && dataset.scrapeState.updated_at, dataset.scrapeState && dataset.scrapeState.scraped_at, dataset.lda && dataset.lda.generated_at, dataset.sentiment && dataset.sentiment.generated_at, dataset.humor && dataset.humor.generated_at]).filter(Boolean).map((value) => new Date(value)).filter((date) => !Number.isNaN(date.getTime()));
    const lastUpdated = latestValues.length ? latestValues.sort((a, b) => b - a)[0].toISOString().slice(0, 19).replace('T', ' ') : 'unknown';

    return e(React.Fragment, null,
      e(Header, { selected, setSelected, status: loading ? 'loading' : error ? 'error' : 'ready', lastUpdated }),
      e('nav', { className: 'section-nav' }, ['overview', 'advanced', 'status', 'descriptives', 'comparison', 'evidence', 'posting', 'sentiment', 'humor', 'topics', 'posts'].map((id) => e('a', { href: `#${id}`, key: id }, id))),
      e('main', { className: 'layout' },
        e(Filters, { filters, setFilters, topics, count: visible.length }),
        e('div', { className: 'content' },
          loading ? e('div', { className: 'notice' }, 'Loading dashboard datasets...') : null,
          error ? e('div', { className: 'notice error' }, error) : null,
          e(Overview, { summary, selected }),
          e(Advanced, { rows: visible }),
          e(Status, { datasets }),
          e(Descriptives, { rows: visible }),
          e(Comparison, { rows: visible, selected }),
          e(Evidence, { rows: visible }),
          e(Posting, { rows: visible }),
          e(Sentiment, { rows: visible, selected }),
          e(Humor, { rows: visible, selected }),
          e(Topics, { rows: visible }),
          e(Explorer, { rows: visible })
        )
      )
    );
  }

  ReactDOM.createRoot(root).render(e(App));
})();
