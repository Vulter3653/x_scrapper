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
    wendys: {
      label: "Wendy's",
      posts: 'data/wendys/posts.json',
      lda: 'data/wendys/lda_topics.json',
      sentiment: 'data/wendys/zero_shot_sentiment.json',
      humor: 'data/wendys/hsq_humor_classification.json',
      scrapeState: 'data/wendys/scrape_state.json',
      color: '#E2231A'
    },
    cocacola: {
      label: 'Coca-Cola',
      posts: 'data/cocacola/posts.json',
      lda: 'data/cocacola/lda_topics.json',
      sentiment: 'data/cocacola/zero_shot_sentiment.json',
      humor: 'data/cocacola/hsq_humor_classification.json',
      scrapeState: 'data/cocacola/scrape_state.json',
      color: '#111827'
    },
    moonpie: {
      label: 'MoonPie',
      posts: 'data/moonpie/posts.json',
      lda: 'data/moonpie/lda_topics.json',
      sentiment: 'data/moonpie/zero_shot_sentiment.json',
      humor: 'data/moonpie/hsq_humor_classification.json',
      scrapeState: 'data/moonpie/scrape_state.json',
      color: '#F97316'
    }
  };

  const HUMOR_LABELS = ['Affiliative humor', 'Self-enhancing humor', 'Aggressive humor', 'Self-defeating humor'];
  const SENTIMENT_LABELS = ['positive', 'neutral', 'negative', 'unknown'];
  const fmt = new Intl.NumberFormat('en-US');
  const compact = new Intl.NumberFormat('en-US', { notation: 'compact', maximumFractionDigits: 1 });
  const percent = new Intl.NumberFormat('en-US', { style: 'percent', maximumFractionDigits: 1 });
  const scoreFmt = new Intl.NumberFormat('en-US', { maximumFractionDigits: 3 });

  function numberValue(value) {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : 0;
  }

  function compactValue(value) {
    return Math.abs(numberValue(value)) >= 1000 ? compact.format(numberValue(value)) : fmt.format(Math.round(numberValue(value)));
  }

  function textValue(post) {
    return String(post && (post.text || post.content || post.tweet_text || post.post_text) || '');
  }

  function dateValue(post) {
    return post && (post.date || post.created_at || post.timestamp) || '';
  }

  function parseDate(value) {
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? null : date;
  }

  function isoDate(value) {
    const date = parseDate(value);
    return date ? date.toISOString().slice(0, 10) : '';
  }

  function monthKey(value) {
    const date = parseDate(value);
    return date ? date.toISOString().slice(0, 7) : 'unknown';
  }

  function likes(post) { return numberValue(post && (post.likes || post.like_count || post.favorite_count)); }
  function replies(post) { return numberValue(post && (post.replies || post.reply_count)); }
  function retweets(post) { return numberValue(post && (post.retweets || post.retweet_count || post.reposts)); }
  function quotes(post) { return numberValue(post && (post.quotes || post.quote_count)); }
  function engagement(post) { return likes(post) + replies(post) + retweets(post) + quotes(post); }

  function median(values) {
    const sorted = values.map(numberValue).filter(Number.isFinite).sort((a, b) => a - b);
    if (!sorted.length) return 0;
    const mid = Math.floor(sorted.length / 2);
    return sorted.length % 2 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2;
  }

  function average(values) {
    const valid = values.map(numberValue).filter(Number.isFinite);
    return valid.length ? valid.reduce((sum, value) => sum + value, 0) / valid.length : 0;
  }

  function percentile(values, ratio) {
    const sorted = values.map(numberValue).filter(Number.isFinite).sort((a, b) => a - b);
    if (!sorted.length) return 0;
    const index = Math.min(sorted.length - 1, Math.max(0, Math.ceil(sorted.length * ratio) - 1));
    return sorted[index];
  }

  function groupBy(rows, getter) {
    const map = new Map();
    rows.forEach((row) => {
      const key = getter(row) || 'unknown';
      if (!map.has(key)) map.set(key, []);
      map.get(key).push(row);
    });
    return map;
  }

  function countRows(rows, getter) {
    return Array.from(groupBy(rows, getter).entries())
      .map(([key, grouped]) => ({ key, value: grouped.length, rows: grouped }))
      .sort((a, b) => b.value - a.value);
  }

  async function loadJson(path) {
    const response = await fetch(path, { cache: 'no-store' });
    if (!response.ok) throw new Error(`${path}: ${response.status}`);
    return response.json();
  }

  async function loadAccount(accountKey) {
    const config = ACCOUNTS[accountKey];
    const dataset = { key: accountKey, posts: [], lda: null, sentiment: null, humor: null, scrapeState: null, errors: {} };
    const targets = {
      posts: config.posts,
      lda: config.lda,
      sentiment: config.sentiment,
      humor: config.humor,
      scrapeState: config.scrapeState
    };

    for (const [name, path] of Object.entries(targets)) {
      try {
        dataset[name] = await loadJson(path);
      } catch (error) {
        dataset.errors[name] = error.message;
      }
    }
    return dataset;
  }

  function enrichPosts(accountKey, dataset) {
    const config = ACCOUNTS[accountKey];
    const sentimentById = new Map((dataset.sentiment && dataset.sentiment.posts || []).map((row) => [String(row.id), row]));
    const humorById = new Map((dataset.humor && dataset.humor.posts || []).map((row) => [String(row.id), row]));
    const topicById = new Map();

    (dataset.lda && dataset.lda.topics || []).forEach((topic) => {
      (topic.representative_posts || []).forEach((post) => {
        topicById.set(String(post.id), {
          id: topic.topic_id,
          terms: topic.top_terms || [],
          score: numberValue(post.score)
        });
      });
    });

    const viralThreshold = percentile((dataset.posts || []).map(engagement), 0.95);

    return (dataset.posts || []).map((post) => {
      const id = String(post.id);
      const sentiment = sentimentById.get(id) || {};
      const humor = humorById.get(id) || {};
      const topic = topicById.get(id) || null;
      const text = textValue(post);
      const totalEngagement = engagement(post);

      return Object.assign({}, post, {
        id,
        account: accountKey,
        brand: config.label,
        brand_color: config.color,
        date_iso: isoDate(dateValue(post)),
        month_key: monthKey(dateValue(post)),
        text_normalized: text,
        likes_count: likes(post),
        replies_count: replies(post),
        retweets_count: retweets(post),
        quotes_count: quotes(post),
        total_engagement: totalEngagement,
        text_length: text.length,
        word_count: text.trim().split(/\s+/).filter(Boolean).length,
        has_url: /(https?:\/\/|www\.)/i.test(text),
        hashtag_count: (text.match(/(^|\s)#[\p{L}\p{N}_]+/gu) || []).length,
        mention_count: (text.match(/(^|\s)@[A-Za-z0-9_]+/g) || []).length,
        sentiment_label: sentiment.top_label || 'unknown',
        sentiment_score: numberValue(sentiment.top_score),
        humor_label: humor.top_label || 'unknown',
        humor_score: numberValue(humor.top_score),
        topic_id: topic ? topic.id : null,
        topic_terms: topic ? topic.terms : [],
        topic_score: topic ? topic.score : 0,
        is_viral: totalEngagement >= viralThreshold && totalEngagement > 0
      });
    });
  }

  function computeStats(rows) {
    const total = rows.length;
    const positive = rows.filter((row) => row.sentiment_label === 'positive').length;
    const negative = rows.filter((row) => row.sentiment_label === 'negative').length;
    const viral = rows.filter((row) => row.is_viral).length;
    const dates = rows.map((row) => parseDate(row.date_iso)).filter(Boolean).sort((a, b) => a - b);
    const humorTop = countRows(rows, (row) => row.humor_label).filter((row) => row.key !== 'unknown')[0];
    const sentimentTop = countRows(rows, (row) => row.sentiment_label).filter((row) => row.key !== 'unknown')[0];

    return {
      total,
      range: dates.length ? `${dates[0].toISOString().slice(0, 10)} - ${dates[dates.length - 1].toISOString().slice(0, 10)}` : '-',
      brands: new Set(rows.map((row) => row.account)).size,
      days: new Set(rows.map((row) => row.date_iso).filter(Boolean)).size,
      engagement: rows.reduce((sum, row) => sum + row.total_engagement, 0),
      averageEngagement: average(rows.map((row) => row.total_engagement)),
      medianEngagement: median(rows.map((row) => row.total_engagement)),
      p95Engagement: percentile(rows.map((row) => row.total_engagement), 0.95),
      viralShare: total ? viral / total : 0,
      positiveShare: total ? positive / total : 0,
      negativeShare: total ? negative / total : 0,
      dominantHumor: humorTop ? humorTop.key : '-',
      dominantSentiment: sentimentTop ? sentimentTop.key : '-'
    };
  }

  function applyFilters(rows, filters) {
    const query = filters.search.trim().toLowerCase();
    const from = filters.from ? new Date(`${filters.from}T00:00:00Z`) : null;
    const to = filters.to ? new Date(`${filters.to}T23:59:59Z`) : null;

    const filtered = rows.filter((post) => {
      const date = parseDate(post.date_iso);
      if (filters.brand !== 'all' && post.account !== filters.brand) return false;
      if (filters.sentiment !== 'all' && post.sentiment_label !== filters.sentiment) return false;
      if (filters.humor !== 'all' && post.humor_label !== filters.humor) return false;
      if (filters.topic !== 'all' && String(post.topic_id) !== filters.topic) return false;
      if (filters.viral === 'viral' && !post.is_viral) return false;
      if (filters.viral === 'nonviral' && post.is_viral) return false;
      if (from && (!date || date < from)) return false;
      if (to && (!date || date > to)) return false;
      if (!query) return true;

      return [post.text_normalized, post.brand, post.sentiment_label, post.humor_label, post.topic_terms.join(' '), post.tweet_url]
        .some((value) => String(value || '').toLowerCase().includes(query));
    });

    filtered.sort((a, b) => {
      if (filters.sort === 'engagement') return b.total_engagement - a.total_engagement;
      if (filters.sort === 'humor') return b.humor_score - a.humor_score;
      if (filters.sort === 'sentiment') return b.sentiment_score - a.sentiment_score;
      const aDate = parseDate(a.date_iso);
      const bDate = parseDate(b.date_iso);
      return (bDate ? bDate.getTime() : 0) - (aDate ? aDate.getTime() : 0);
    });

    return filtered;
  }

  function Metric({ label, value, help, tone }) {
    return e('article', { className: `metric ${tone || ''}` },
      e('span', null, label),
      e('strong', null, value),
      help ? e('small', null, help) : null
    );
  }

  function Section({ id, kicker, title, children }) {
    return e('section', { id, className: 'section' },
      e('div', { className: 'section-title' },
        e('span', null, kicker),
        e('h2', null, title)
      ),
      children
    );
  }

  function Bars({ rows, asPercent }) {
    if (!rows.length) return e('div', { className: 'empty' }, 'No data available');
    const max = Math.max(...rows.map((row) => row.value), 1);
    return e('div', { className: 'bars' }, rows.map((row, index) => {
      const width = Math.max(2, row.value / max * 100);
      return e('div', { className: 'bar', key: `${row.key}-${index}` },
        e('div', { className: 'bar-meta' },
          e('span', { title: row.key }, row.key),
          e('b', null, asPercent ? percent.format(row.value) : compactValue(row.value))
        ),
        e('div', { className: 'track' }, e('i', { style: { width: `${width}%`, background: row.color || undefined } }))
      );
    }));
  }

  function DataTable({ heads, rows }) {
    if (!rows.length) return e('div', { className: 'empty' }, 'No data available');
    return e('div', { className: 'table-wrap' },
      e('table', null,
        e('thead', null, e('tr', null, heads.map((head) => e('th', { key: head }, head)))),
        e('tbody', null, rows.map((row, index) => e('tr', { key: index }, row.map((cell, cellIndex) => e('td', { key: cellIndex }, cell)))))
      )
    );
  }

  function Header({ selected, setSelected, status, lastUpdated }) {
    return e('header', { className: 'top' },
      e('div', null,
        e('div', { className: 'title' },
          e('h1', null, 'X Brand Intelligence Dashboard'),
          e('em', { className: status }, status)
        ),
        e('p', null, 'React analytics for all-brand and brand-specific X posts, sentiment, topics, and HSQ humor.'),
        e('small', null, `Last updated: ${lastUpdated}`)
      ),
      e('nav', { className: 'tabs' },
        e('button', { className: selected === 'all' ? 'on' : '', onClick: () => setSelected('all') }, 'All Brands'),
        Object.entries(ACCOUNTS).map(([key, account]) => e('button', { key, className: selected === key ? 'on' : '', onClick: () => setSelected(key) }, account.label))
      )
    );
  }

  function Filters({ filters, setFilters, topics, count }) {
    function update(key, value) {
      setFilters(Object.assign({}, filters, { [key]: value }));
    }

    return e('aside', { className: 'filters' },
      e('div', { className: 'filter-head' }, e('b', null, 'Filters'), e('span', null, `${fmt.format(count)} posts`)),
      e('label', null, 'Brand', e('select', { value: filters.brand, onChange: (event) => update('brand', event.target.value) },
        e('option', { value: 'all' }, 'All brands'),
        Object.entries(ACCOUNTS).map(([key, account]) => e('option', { key, value: key }, account.label))
      )),
      e('label', null, 'Search', e('input', { type: 'search', value: filters.search, onChange: (event) => update('search', event.target.value), placeholder: 'text, humor, sentiment, topic' })),
      e('div', { className: 'two' },
        e('label', null, 'From', e('input', { type: 'date', value: filters.from, onChange: (event) => update('from', event.target.value) })),
        e('label', null, 'To', e('input', { type: 'date', value: filters.to, onChange: (event) => update('to', event.target.value) }))
      ),
      e('label', null, 'Sentiment', e('select', { value: filters.sentiment, onChange: (event) => update('sentiment', event.target.value) },
        e('option', { value: 'all' }, 'All sentiment'),
        SENTIMENT_LABELS.map((label) => e('option', { key: label, value: label }, label))
      )),
      e('label', null, 'HSQ Humor', e('select', { value: filters.humor, onChange: (event) => update('humor', event.target.value) },
        e('option', { value: 'all' }, 'All humor'),
        HUMOR_LABELS.map((label) => e('option', { key: label, value: label }, label)),
        e('option', { value: 'unknown' }, 'unknown')
      )),
      e('label', null, 'Topic', e('select', { value: filters.topic, onChange: (event) => update('topic', event.target.value) },
        e('option', { value: 'all' }, 'All topics'),
        topics.map((topic) => e('option', { key: topic, value: topic }, `Topic ${topic}`))
      )),
      e('label', null, 'Viral', e('select', { value: filters.viral, onChange: (event) => update('viral', event.target.value) },
        e('option', { value: 'all' }, 'All posts'),
        e('option', { value: 'viral' }, 'Viral only'),
        e('option', { value: 'nonviral' }, 'Non-viral only')
      )),
      e('label', null, 'Sort', e('select', { value: filters.sort, onChange: (event) => update('sort', event.target.value) },
        e('option', { value: 'date' }, 'Newest'),
        e('option', { value: 'engagement' }, 'Engagement'),
        e('option', { value: 'humor' }, 'Humor score'),
        e('option', { value: 'sentiment' }, 'Sentiment score')
      )),
      e('button', { onClick: () => setFilters(defaultFilters()) }, 'Reset')
    );
  }

  function defaultFilters() {
    return { brand: 'all', search: '', from: '', to: '', sentiment: 'all', humor: 'all', topic: 'all', viral: 'all', sort: 'date' };
  }

  function Status({ datasets }) {
    const rows = Object.entries(ACCOUNTS).map(([key, account]) => {
      const dataset = datasets[key] || {};
      return [
        account.label,
        dataset.posts && dataset.posts.length ? `${fmt.format(dataset.posts.length)} loaded` : 'missing',
        dataset.lda ? 'available' : 'missing',
        dataset.sentiment ? 'available' : 'missing',
        dataset.humor ? 'available' : 'missing'
      ];
    });

    return e(Section, { id: 'status', kicker: 'Data readiness', title: 'Dataset Status' },
      e(DataTable, { heads: ['Brand', 'Posts', 'LDA', 'Sentiment', 'HSQ Humor'], rows })
    );
  }

  function Overview({ summary, selected }) {
    const title = selected === 'all' ? 'All Brands Overview' : `${ACCOUNTS[selected].label} Overview`;
    return e(Section, { id: 'overview', kicker: 'Executive summary', title },
      e('div', { className: 'metrics' },
        e(Metric, { label: 'Total Posts', value: fmt.format(summary.total), help: `${summary.brands} brand(s), ${summary.days} active day(s)`, tone: 'red' }),
        e(Metric, { label: 'Date Range', value: summary.range, help: 'parsed post timestamps' }),
        e(Metric, { label: 'Total Engagement', value: compactValue(summary.engagement), help: `Avg ${compactValue(summary.averageEngagement)} per post` }),
        e(Metric, { label: 'Median Engagement', value: compactValue(summary.medianEngagement), help: `P95 ${compactValue(summary.p95Engagement)}` }),
        e(Metric, { label: 'Viral Share', value: percent.format(summary.viralShare), help: 'top 5% by engagement' }),
        e(Metric, { label: 'Dominant Humor', value: summary.dominantHumor, help: `Positive ${percent.format(summary.positiveShare)} / Negative ${percent.format(summary.negativeShare)}`, tone: 'blue' })
      )
    );
  }

  function Descriptives({ rows }) {
    const summary = computeStats(rows);
    const brandRows = countRows(rows, (row) => row.brand).map((row) => ({ key: row.key, value: median(row.rows.map((post) => post.total_engagement)), color: row.rows[0] && row.rows[0].brand_color }));

    return e(Section, { id: 'descriptives', kicker: 'Descriptive statistics', title: 'Dataset and Engagement Profile' },
      e('div', { className: 'grid' },
        e('article', { className: 'panel' },
          e('h3', null, 'Summary'),
          e(DataTable, { heads: ['Metric', 'Value'], rows: [
            ['Posts', fmt.format(summary.total)],
            ['Date range', summary.range],
            ['Total engagement', compactValue(summary.engagement)],
            ['Average engagement', compactValue(summary.averageEngagement)],
            ['Median engagement', compactValue(summary.medianEngagement)],
            ['Dominant sentiment', summary.dominantSentiment],
            ['Dominant humor', summary.dominantHumor]
          ] })
        ),
        e('article', { className: 'panel' },
          e('h3', null, 'Median Engagement by Brand'),
          e(Bars, { rows: brandRows })
        )
      )
    );
  }

  function BrandComparison({ rows, selected }) {
    if (selected !== 'all') {
      return e(Section, { id: 'comparison', kicker: 'Cross-brand analysis', title: 'Brand Comparison' },
        e('div', { className: 'empty' }, 'Brand comparison is shown in the All Brands view.')
      );
    }

    const brandStats = Object.entries(ACCOUNTS).map(([key, account]) => {
      const scoped = rows.filter((row) => row.account === key);
      return { key, account, rows: scoped, summary: computeStats(scoped) };
    });

    return e(Section, { id: 'comparison', kicker: 'Cross-brand analysis', title: 'Brand Comparison' },
      e('div', { className: 'grid' },
        e('article', { className: 'panel' }, e('h3', null, 'Post Count by Brand'), e(Bars, { rows: brandStats.map((item) => ({ key: item.account.label, value: item.rows.length, color: item.account.color })) })),
        e('article', { className: 'panel' }, e('h3', null, 'Total Engagement by Brand'), e(Bars, { rows: brandStats.map((item) => ({ key: item.account.label, value: item.summary.engagement, color: item.account.color })) })),
        e('article', { className: 'panel wide' },
          e('h3', null, 'Brand Summary'),
          e(DataTable, { heads: ['Brand', 'Posts', 'Median Engagement', 'Positive', 'Negative', 'Viral', 'Dominant Humor'], rows: brandStats.map((item) => [
            item.account.label,
            fmt.format(item.rows.length),
            compactValue(item.summary.medianEngagement),
            percent.format(item.summary.positiveShare),
            percent.format(item.summary.negativeShare),
            percent.format(item.summary.viralShare),
            item.summary.dominantHumor
          ]) })
        )
      )
    );
  }

  function Evidence({ rows }) {
    const viral = rows.filter((row) => row.is_viral);
    const humorMedian = countRows(rows, (row) => row.humor_label).map((row) => ({ key: row.key, value: median(row.rows.map((post) => post.total_engagement)) }));
    const sentimentMedian = countRows(rows, (row) => row.sentiment_label).map((row) => ({ key: row.key, value: median(row.rows.map((post) => post.total_engagement)) }));
    const viralHumor = countRows(viral, (row) => row.humor_label).map((row) => ({ key: row.key, value: viral.length ? row.value / viral.length : 0, color: row.key === 'Aggressive humor' ? '#DC2626' : undefined }));
    const cells = countRows(rows, (row) => `${row.humor_label} / ${row.sentiment_label}`).slice(0, 8).map((row) => [row.key, fmt.format(row.value), compactValue(median(row.rows.map((post) => post.total_engagement)))]);

    return e(Section, { id: 'evidence', kicker: 'Model-free evidence', title: 'Observed Patterns Before Modeling' },
      e('div', { className: 'grid' },
        e('article', { className: 'panel' }, e('h3', null, 'Humor Type → Median Engagement'), e(Bars, { rows: humorMedian })),
        e('article', { className: 'panel' }, e('h3', null, 'Sentiment → Median Engagement'), e(Bars, { rows: sentimentMedian })),
        e('article', { className: 'panel' }, e('h3', null, 'Viral Humor Composition'), e(Bars, { rows: viralHumor, asPercent: true })),
        e('article', { className: 'panel' }, e('h3', null, 'Humor × Sentiment Cells'), e(DataTable, { heads: ['Cell', 'Posts', 'Median Engagement'], rows: cells }))
      )
    );
  }

  function Posting({ rows }) {
    const months = countRows(rows, (row) => row.month_key).filter((row) => row.key !== 'unknown').slice(0, 18).reverse();
    const mix = [
      { key: 'Likes', value: rows.reduce((sum, row) => sum + row.likes_count, 0) },
      { key: 'Replies', value: rows.reduce((sum, row) => sum + row.replies_count, 0) },
      { key: 'Retweets', value: rows.reduce((sum, row) => sum + row.retweets_count, 0) },
      { key: 'Quotes', value: rows.reduce((sum, row) => sum + row.quotes_count, 0) }
    ];

    return e(Section, { id: 'posting', kicker: 'Posting and engagement', title: 'Posting Volume and Interaction Mix' },
      e('div', { className: 'grid' },
        e('article', { className: 'panel' }, e('h3', null, 'Recent Monthly Posting Volume'), e(Bars, { rows: months })),
        e('article', { className: 'panel' }, e('h3', null, 'Engagement Mix'), e(Bars, { rows: mix }))
      )
    );
  }

  function Sentiment({ rows, selected }) {
    const distribution = countRows(rows, (row) => row.sentiment_label).map((row) => ({
      key: row.key,
      value: rows.length ? row.value / rows.length : 0,
      color: row.key === 'positive' ? '#16A34A' : row.key === 'negative' ? '#DC2626' : '#94A3B8'
    }));

    const secondPanel = selected === 'all'
      ? e(DataTable, { heads: ['Brand', 'Positive', 'Neutral', 'Negative'], rows: Object.entries(ACCOUNTS).map(([key, account]) => {
          const scoped = rows.filter((row) => row.account === key);
          return [
            account.label,
            percent.format(scoped.length ? scoped.filter((row) => row.sentiment_label === 'positive').length / scoped.length : 0),
            percent.format(scoped.length ? scoped.filter((row) => row.sentiment_label === 'neutral').length / scoped.length : 0),
            percent.format(scoped.length ? scoped.filter((row) => row.sentiment_label === 'negative').length / scoped.length : 0)
          ];
        }) })
      : e(PostList, { rows: rows.filter((row) => row.sentiment_label === 'negative').slice(0, 5) });

    return e(Section, { id: 'sentiment', kicker: 'Zero-shot sentiment', title: 'Sentiment Analysis' },
      e('div', { className: 'grid' },
        e('article', { className: 'panel' }, e('h3', null, 'Sentiment Distribution'), e(Bars, { rows: distribution, asPercent: true })),
        e('article', { className: 'panel' }, e('h3', null, selected === 'all' ? 'Sentiment by Brand' : 'Representative Negative Posts'), secondPanel)
      )
    );
  }

  function Humor({ rows, selected }) {
    const aggressive = rows.filter((row) => row.humor_label === 'Aggressive humor');
    const aggressiveStats = computeStats(aggressive);
    const distribution = countRows(rows, (row) => row.humor_label).map((row) => ({
      key: row.key,
      value: rows.length ? row.value / rows.length : 0,
      color: row.key === 'Aggressive humor' ? '#DC2626' : row.key === 'Self-enhancing humor' ? '#2563EB' : undefined
    }));

    const comparison = selected === 'all'
      ? e(DataTable, { heads: ['Brand', 'Affiliative', 'Self-enhancing', 'Aggressive', 'Self-defeating'], rows: Object.entries(ACCOUNTS).map(([key, account]) => {
          const scoped = rows.filter((row) => row.account === key);
          return [account.label].concat(HUMOR_LABELS.map((label) => percent.format(scoped.length ? scoped.filter((row) => row.humor_label === label).length / scoped.length : 0)));
        }) })
      : e(PostList, { rows: rows.slice(0, 6) });

    return e(Section, { id: 'humor', kicker: 'HSQ humor classification', title: 'Humor Analysis' },
      e('div', { className: 'grid' },
        e('article', { className: 'panel' }, e('h3', null, 'Humor Type Distribution'), e(Bars, { rows: distribution, asPercent: true })),
        e('article', { className: 'panel' },
          e('h3', null, 'Aggressive Humor Focus'),
          e('div', { className: 'focus' },
            e(Metric, { label: 'Aggressive Posts', value: fmt.format(aggressive.length), help: percent.format(rows.length ? aggressive.length / rows.length : 0), tone: 'danger' }),
            e(Metric, { label: 'Median Engagement', value: compactValue(aggressiveStats.medianEngagement), help: 'aggressive posts' }),
            e(Metric, { label: 'Negative Share', value: percent.format(aggressiveStats.negativeShare), help: 'within aggressive humor' })
          )
        ),
        e('article', { className: 'panel wide' }, e('h3', null, selected === 'all' ? 'Humor Type by Brand' : 'Representative Humor Posts'), comparison)
      )
    );
  }

  function Topics({ rows }) {
    const topicRows = countRows(rows.filter((row) => row.topic_id !== null), (row) => String(row.topic_id)).slice(0, 12);
    const tableRows = topicRows.map((row) => [
      `Topic ${row.key}`,
      row.rows[0] && row.rows[0].topic_terms ? row.rows[0].topic_terms.slice(0, 6).join(', ') : '-',
      fmt.format(row.value),
      compactValue(median(row.rows.map((post) => post.total_engagement))),
      countRows(row.rows, (post) => post.humor_label)[0] ? countRows(row.rows, (post) => post.humor_label)[0].key : '-'
    ]);

    return e(Section, { id: 'topics', kicker: 'LDA topics', title: 'Topic Analysis' },
      e('div', { className: 'grid' },
        e('article', { className: 'panel' }, e('h3', null, 'Topic Share'), e(Bars, { rows: topicRows.map((row) => ({ key: `Topic ${row.key}`, value: row.value })) })),
        e('article', { className: 'panel wide' }, e('h3', null, 'Topic × Engagement × Humor'), e(DataTable, { heads: ['Topic', 'Top Terms', 'Posts', 'Median Engagement', 'Dominant Humor'], rows: tableRows }))
      )
    );
  }

  function PostList({ rows }) {
    if (!rows.length) return e('div', { className: 'empty' }, 'No data available');
    return e('div', { className: 'post-mini' }, rows.map((post) => e('a', { key: post.id, href: post.tweet_url, target: '_blank', rel: 'noreferrer' },
      e('b', null, `${post.brand} · ${post.date_iso}`),
      e('span', null, post.text_normalized || '(no text)'),
      e('small', null, `${post.humor_label} · ${post.sentiment_label} · ${compactValue(post.total_engagement)} engagement`)
    )));
  }

  function Explorer({ rows }) {
    const [page, setPage] = useState(1);
    useEffect(() => setPage(1), [rows.length]);
    const pageSize = 30;
    const totalPages = Math.max(1, Math.ceil(rows.length / pageSize));
    const currentPage = Math.min(page, totalPages);
    const visible = rows.slice((currentPage - 1) * pageSize, currentPage * pageSize);

    return e(Section, { id: 'posts', kicker: 'Post-level evidence', title: 'Post Explorer' },
      e('div', { className: 'post-head' },
        e('p', null, `${fmt.format(rows.length)} posts after filters. Page ${currentPage} of ${totalPages}.`),
        e('div', null,
          e('button', { disabled: currentPage <= 1, onClick: () => setPage(currentPage - 1) }, 'Prev'),
          e('button', { disabled: currentPage >= totalPages, onClick: () => setPage(currentPage + 1) }, 'Next')
        )
      ),
      e(DataTable, { heads: ['Date', 'Brand', 'Text', 'Engagement', 'Sentiment', 'Humor', 'Topic', 'Link'], rows: visible.map((post) => [
        post.date_iso,
        post.brand,
        e('span', { className: 'post-text' }, post.text_normalized || '(no text)'),
        compactValue(post.total_engagement),
        `${post.sentiment_label} (${scoreFmt.format(post.sentiment_score)})`,
        `${post.humor_label} (${scoreFmt.format(post.humor_score)})`,
        post.topic_id === null ? '-' : `Topic ${post.topic_id}`,
        post.tweet_url ? e('a', { href: post.tweet_url, target: '_blank', rel: 'noreferrer' }, 'Open') : '-'
      ]) }),
      e('div', { className: 'cards' }, visible.map((post) => e('article', { key: post.id },
        e('b', null, `${post.brand} · ${post.date_iso}`),
        e('p', null, post.text_normalized || '(no text)'),
        e('small', null, `${compactValue(post.total_engagement)} engagement · ${post.sentiment_label} · ${post.humor_label}`),
        post.tweet_url ? e('a', { href: post.tweet_url, target: '_blank', rel: 'noreferrer' }, 'Open post') : null
      )))
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
        .then((entries) => {
          if (!cancelled) {
            setDatasets(Object.fromEntries(entries));
            setLoading(false);
          }
        })
        .catch((loadError) => {
          if (!cancelled) {
            setError(loadError.message);
            setLoading(false);
          }
        });
      return () => { cancelled = true; };
    }, []);

    const enrichedByAccount = useMemo(() => {
      const result = {};
      Object.entries(datasets).forEach(([key, dataset]) => {
        result[key] = enrichPosts(key, dataset);
      });
      return result;
    }, [datasets]);

    const allPosts = useMemo(() => Object.values(enrichedByAccount).flat(), [enrichedByAccount]);
    const scopedPosts = selected === 'all' ? allPosts : (enrichedByAccount[selected] || []);
    const topicOptions = Array.from(new Set(scopedPosts.filter((post) => post.topic_id !== null).map((post) => String(post.topic_id)))).sort((a, b) => Number(a) - Number(b));
    const effectiveFilters = selected === 'all' ? filters : Object.assign({}, filters, { brand: 'all' });
    const visiblePosts = useMemo(() => applyFilters(scopedPosts, effectiveFilters), [scopedPosts, effectiveFilters]);
    const summary = computeStats(visiblePosts);

    const latestValues = Object.values(datasets).flatMap((dataset) => [
      dataset.scrapeState && dataset.scrapeState.updated_at,
      dataset.scrapeState && dataset.scrapeState.scraped_at,
      dataset.lda && dataset.lda.generated_at,
      dataset.sentiment && dataset.sentiment.generated_at,
      dataset.humor && dataset.humor.generated_at
    ]).filter(Boolean).map((value) => new Date(value)).filter((date) => !Number.isNaN(date.getTime()));
    const lastUpdated = latestValues.length ? latestValues.sort((a, b) => b - a)[0].toISOString().slice(0, 19).replace('T', ' ') : 'unknown';

    return e(React.Fragment, null,
      e(Header, { selected, setSelected, status: loading ? 'loading' : error ? 'error' : 'ready', lastUpdated }),
      e('nav', { className: 'section-nav' }, ['overview', 'status', 'descriptives', 'comparison', 'evidence', 'posting', 'sentiment', 'humor', 'topics', 'posts'].map((id) => e('a', { href: `#${id}`, key: id }, id))),
      e('main', { className: 'layout' },
        e(Filters, { filters, setFilters, topics: topicOptions, count: visiblePosts.length }),
        e('div', { className: 'content' },
          loading ? e('div', { className: 'notice' }, 'Loading dashboard datasets...') : null,
          error ? e('div', { className: 'notice error' }, error) : null,
          e(Overview, { summary, selected }),
          e(Status, { datasets }),
          e(Descriptives, { rows: visiblePosts }),
          e(BrandComparison, { rows: visiblePosts, selected }),
          e(Evidence, { rows: visiblePosts }),
          e(Posting, { rows: visiblePosts }),
          e(Sentiment, { rows: visiblePosts, selected }),
          e(Humor, { rows: visiblePosts, selected }),
          e(Topics, { rows: visiblePosts }),
          e(Explorer, { rows: visiblePosts })
        )
      )
    );
  }

  ReactDOM.createRoot(root).render(e(App));
})();
