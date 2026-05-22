const accounts = {
  wendys: {
    label: "Wendy's",
    posts: 'data/wendys_posts.json',
    lda: 'data/wendys_lda_topics.json',
    sentiment: 'data/wendys_zero_shot_sentiment.json',
    color: '#d6223a'
  },
  cocacola: {
    label: 'Coca-Cola',
    posts: 'data/cocacola_posts.json',
    lda: 'data/cocacola_lda_topics.json',
    sentiment: 'data/cocacola_zero_shot_sentiment.json',
    color: '#b57912'
  }
};

const pageSize = 40;
const state = {
  account: 'wendys',
  datasets: {},
  enriched: {},
  cache: new Map(),
  search: '',
  year: 'all',
  dateFrom: '',
  dateTo: '',
  sentiment: 'all',
  topic: 'all',
  viral: 'all',
  sort: 'date_desc',
  topicSearch: '',
  selectedTopicId: null,
  page: 1,
  expandedPosts: new Set(),
  chartSeries: {
    volume: { Posts: true },
    engagement: { Likes: true, Replies: true, Retweets: true, Quotes: true },
    sentiment: {}
  },
  charts: {}
};

const el = (id) => document.getElementById(id);
const fmt = new Intl.NumberFormat('en-US');
const percentFmt = new Intl.NumberFormat('en-US', { style: 'percent', maximumFractionDigits: 1 });

function parseDate(value) {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? null : date;
}

function isoDate(value) {
  const date = parseDate(value);
  return date ? date.toISOString().slice(0, 10) : '';
}

function numberValue(value) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : 0;
}

function engagement(post) {
  return numberValue(post.favorite_count) + numberValue(post.reply_count) + numberValue(post.retweet_count) + numberValue(post.quote_count);
}

function median(values) {
  if (!values.length) return 0;
  const sorted = [...values].sort((a, b) => a - b);
  const mid = Math.floor(sorted.length / 2);
  return sorted.length % 2 ? sorted[mid] : Math.round((sorted[mid - 1] + sorted[mid]) / 2);
}

function percentile(values, ratio) {
  if (!values.length) return 0;
  const sorted = [...values].sort((a, b) => a - b);
  const index = Math.min(sorted.length - 1, Math.max(0, Math.ceil(sorted.length * ratio) - 1));
  return sorted[index];
}

async function loadJson(path) {
  const response = await fetch(path, { cache: 'no-store' });
  if (!response.ok) throw new Error(`${path}: ${response.status}`);
  return response.json();
}

async function loadAccount(accountKey) {
  if (state.datasets[accountKey]) return state.datasets[accountKey];
  const config = accounts[accountKey];
  const dataset = { posts: [], lda: null, sentiment: null, errors: {} };

  try { dataset.posts = await loadJson(config.posts); } catch (error) { dataset.errors.posts = error.message; }
  try { dataset.lda = await loadJson(config.lda); } catch (error) { dataset.errors.lda = error.message; }
  try { dataset.sentiment = await loadJson(config.sentiment); } catch (error) { dataset.errors.sentiment = error.message; }

  state.datasets[accountKey] = dataset;
  return dataset;
}

function buildEnrichedDataset(accountKey, dataset) {
  const cacheKey = `${accountKey}:${dataset.posts.length}:${dataset.sentiment?.post_count || 0}:${dataset.lda?.num_topics || 0}`;
  if (state.enriched[cacheKey]) return state.enriched[cacheKey];

  const sentimentById = new Map((dataset.sentiment?.posts || []).map((row) => [String(row.id), row]));
  const topicById = new Map();
  (dataset.lda?.topics || []).forEach((topic) => {
    (topic.representative_posts || []).forEach((post) => {
      const id = String(post.id);
      const existing = topicById.get(id);
      if (!existing || numberValue(post.score) > numberValue(existing.score)) {
        topicById.set(id, { topic_id: topic.topic_id, score: post.score, top_terms: topic.top_terms || [] });
      }
    });
  });

  const engagements = dataset.posts.map(engagement);
  const viralThreshold = percentile(engagements, 0.9);
  const posts = dataset.posts.map((post) => {
    const id = String(post.id);
    const sentiment = sentimentById.get(id);
    const topic = topicById.get(id);
    const totalEngagement = engagement(post);
    return {
      ...post,
      id,
      account: accountKey,
      brand: accounts[accountKey].label,
      date_iso: isoDate(post.created_at),
      total_engagement: totalEngagement,
      sentiment_label: sentiment?.top_label || 'unknown',
      sentiment_score: numberValue(sentiment?.top_score),
      topic_id: topic?.topic_id ?? null,
      topic_terms: topic?.top_terms || [],
      topic_score: numberValue(topic?.score),
      viral: totalEngagement >= viralThreshold && totalEngagement > 0
    };
  });

  const result = { posts, viralThreshold };
  state.enriched[cacheKey] = result;
  return result;
}

function cacheKeyForFilters() {
  return JSON.stringify({
    account: state.account,
    search: state.search,
    year: state.year,
    dateFrom: state.dateFrom,
    dateTo: state.dateTo,
    sentiment: state.sentiment,
    topic: state.topic,
    viral: state.viral,
    sort: state.sort
  });
}

function filteredPosts(posts) {
  const key = `filtered:${cacheKeyForFilters()}:${posts.length}`;
  if (state.cache.has(key)) return state.cache.get(key);
  const query = state.search.trim().toLowerCase();
  const from = state.dateFrom ? new Date(`${state.dateFrom}T00:00:00Z`) : null;
  const to = state.dateTo ? new Date(`${state.dateTo}T23:59:59Z`) : null;

  const rows = posts.filter((post) => {
    const date = parseDate(post.created_at);
    const year = date ? String(date.getUTCFullYear()) : 'unknown';
    if (state.year !== 'all' && year !== state.year) return false;
    if (from && (!date || date < from)) return false;
    if (to && (!date || date > to)) return false;
    if (state.sentiment !== 'all' && post.sentiment_label !== state.sentiment) return false;
    if (state.topic !== 'all' && String(post.topic_id) !== state.topic) return false;
    if (state.viral === 'viral' && !post.viral) return false;
    if (state.viral === 'nonviral' && post.viral) return false;
    if (!query) return true;
    return [post.text, post.tweet_url, post.lang, post.sentiment_label, post.topic_terms.join(' ')].some((value) => String(value || '').toLowerCase().includes(query));
  });

  rows.sort((a, b) => {
    if (state.sort === 'engagement_desc') return b.total_engagement - a.total_engagement;
    if (state.sort === 'likes_desc') return numberValue(b.favorite_count) - numberValue(a.favorite_count);
    if (state.sort === 'replies_desc') return numberValue(b.reply_count) - numberValue(a.reply_count);
    if (state.sort === 'retweets_desc') return numberValue(b.retweet_count) - numberValue(a.retweet_count);
    return numberValue(b.id) - numberValue(a.id);
  });
  state.cache.set(key, rows);
  return rows;
}

function dateRange(posts) {
  const dates = posts.map((post) => parseDate(post.created_at)).filter(Boolean).sort((a, b) => a - b);
  if (!dates.length) return '-';
  return `${dates[0].toISOString().slice(0, 10)} to ${dates[dates.length - 1].toISOString().slice(0, 10)}`;
}

function countActiveFilters() {
  return [state.search, state.dateFrom, state.dateTo].filter(Boolean).length +
    ['year', 'sentiment', 'topic', 'viral'].filter((key) => state[key] !== 'all').length;
}

function populateFilterOptions(posts, dataset) {
  const years = [...new Set(posts.map((post) => parseDate(post.created_at)).filter(Boolean).map((date) => date.getUTCFullYear()))].sort((a, b) => b - a);
  const yearSelect = el('yearSelect');
  const currentYear = state.year;
  yearSelect.innerHTML = '<option value="all">All years</option>' + years.map((year) => `<option value="${year}">${year}</option>`).join('');
  state.year = years.map(String).includes(currentYear) ? currentYear : 'all';
  yearSelect.value = state.year;

  const sentimentSelect = el('sentimentSelect');
  const labels = Object.keys(dataset.sentiment?.label_counts || {}).sort();
  sentimentSelect.innerHTML = '<option value="all">All sentiment labels</option>' + labels.map((label) => `<option value="${escapeHtml(label)}">${escapeHtml(label)}</option>`).join('');
  state.sentiment = labels.includes(state.sentiment) ? state.sentiment : 'all';
  sentimentSelect.value = state.sentiment;

  const topicSelect = el('topicFilterSelect');
  const topics = dataset.lda?.topics || [];
  topicSelect.innerHTML = '<option value="all">All topics</option>' + topics.map((topic) => {
    const label = `Topic ${topic.topic_id}: ${(topic.top_terms || []).slice(0, 3).join(', ')}`;
    return `<option value="${topic.topic_id}">${escapeHtml(label)}</option>`;
  }).join('');
  state.topic = topics.some((topic) => String(topic.topic_id) === state.topic) ? state.topic : 'all';
  topicSelect.value = state.topic;

  el('brandFilterLabel').textContent = accounts[state.account].label;
  el('activeFilterCount').textContent = `${countActiveFilters()} active`;
}

function resetFilters() {
  state.search = '';
  state.year = 'all';
  state.dateFrom = '';
  state.dateTo = '';
  state.sentiment = 'all';
  state.topic = 'all';
  state.viral = 'all';
  state.sort = 'date_desc';
  state.page = 1;
  el('searchInput').value = '';
  el('dateFromInput').value = '';
  el('dateToInput').value = '';
  el('viralSelect').value = 'all';
  el('sortSelect').value = 'date_desc';
}

function showLoading() {
  el('dataStatus').textContent = 'Loading datasets...';
  ['metricPosts', 'metricRange', 'metricMedian', 'metricEngagement', 'metricViralShare', 'metricPositiveShare'].forEach((id) => {
    el(id).textContent = '-';
  });
  el('postTableWrap').innerHTML = '<div class="skeleton"></div>';
  el('postCards').innerHTML = '';
}

function renderStatus(dataset) {
  const rows = [
    ['Posts', dataset.posts.length ? `${fmt.format(dataset.posts.length)} loaded` : `missing${dataset.errors.posts ? `: ${dataset.errors.posts}` : ''}`, dataset.posts.length ? 'ok' : 'warn'],
    ['LDA', dataset.lda ? 'available' : `not generated${dataset.errors.lda ? `: ${dataset.errors.lda}` : ''}`, dataset.lda ? 'ok' : 'warn'],
    ['Zero-shot', dataset.sentiment ? 'available' : `not generated${dataset.errors.sentiment ? `: ${dataset.errors.sentiment}` : ''}`, dataset.sentiment ? 'ok' : 'warn']
  ];
  el('analysisStatus').innerHTML = rows.map(([name, value, cls]) => `<div class="status-item ${cls}"><span>${name}</span><strong>${escapeHtml(value)}</strong></div>`).join('');
}

function renderMetrics(posts) {
  const totalEngagement = posts.reduce((sum, post) => sum + post.total_engagement, 0);
  const viralCount = posts.filter((post) => post.viral).length;
  const positiveCount = posts.filter((post) => post.sentiment_label === 'positive').length;
  el('metricPosts').textContent = fmt.format(posts.length);
  el('metricRange').textContent = dateRange(posts);
  el('metricMedian').textContent = fmt.format(median(posts.map((post) => post.total_engagement)));
  el('metricEngagement').textContent = fmt.format(totalEngagement);
  el('metricViralShare').textContent = posts.length ? percentFmt.format(viralCount / posts.length) : '-';
  el('metricPositiveShare').textContent = posts.length ? percentFmt.format(positiveCount / posts.length) : '-';
}

function renderEvidence(posts) {
  const bySentiment = new Map();
  posts.forEach((post) => bySentiment.set(post.sentiment_label, (bySentiment.get(post.sentiment_label) || 0) + 1));
  const mostCommonSentiment = [...bySentiment.entries()].sort((a, b) => b[1] - a[1])[0];
  const viralPosts = posts.filter((post) => post.viral);
  const topPost = [...posts].sort((a, b) => b.total_engagement - a.total_engagement)[0];
  const avgReplies = posts.length ? Math.round(posts.reduce((sum, post) => sum + numberValue(post.reply_count), 0) / posts.length) : 0;
  el('evidenceGrid').innerHTML = [
    ['Dominant Sentiment', mostCommonSentiment ? `${mostCommonSentiment[0]} (${fmt.format(mostCommonSentiment[1])})` : 'No data available for this section'],
    ['Viral Posts', posts.length ? `${fmt.format(viralPosts.length)} posts` : 'No data available for this section'],
    ['Average Replies', posts.length ? fmt.format(avgReplies) : 'No data available for this section'],
    ['Top Post Engagement', topPost ? fmt.format(topPost.total_engagement) : 'No data available for this section']
  ].map(([label, value]) => `<article class="evidence-card"><span>${label}</span><strong>${escapeHtml(value)}</strong></article>`).join('');
}

function setupCanvas(canvas, height) {
  const ctx = canvas.getContext('2d');
  const width = Math.max(280, Math.floor(canvas.clientWidth || 600));
  const dpr = window.devicePixelRatio || 1;
  canvas.width = width * dpr;
  canvas.height = height * dpr;
  canvas.style.height = `${height}px`;
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, width, height);
  return { ctx, width, height };
}

function drawEmptyChart(canvas, message) {
  const { ctx, width, height } = setupCanvas(canvas, Number(canvas.getAttribute('height')) || 220);
  ctx.fillStyle = '#607076';
  ctx.font = '13px system-ui, sans-serif';
  ctx.textAlign = 'center';
  ctx.fillText(message, width / 2, height / 2);
  state.charts[canvas.id] = { points: [] };
}

function drawBarChart(canvas, labels, values, color) {
  if (!values.length) {
    drawEmptyChart(canvas, 'No data available for this section');
    return;
  }
  const { ctx, width, height } = setupCanvas(canvas, Number(canvas.getAttribute('height')) || 230);
  const compact = width < 420;
  const pad = { top: 18, right: 14, bottom: compact ? 42 : 36, left: compact ? 34 : 48 };
  const chartW = Math.max(1, width - pad.left - pad.right);
  const chartH = Math.max(1, height - pad.top - pad.bottom);
  const max = Math.max(...values, 1);
  const gap = compact ? 2 : 4;
  const barW = Math.max(2, chartW / values.length - gap);
  const points = [];

  ctx.strokeStyle = '#d9e1e4';
  ctx.beginPath();
  ctx.moveTo(pad.left, pad.top);
  ctx.lineTo(pad.left, pad.top + chartH);
  ctx.lineTo(pad.left + chartW, pad.top + chartH);
  ctx.stroke();

  values.forEach((value, index) => {
    const x = pad.left + index * (barW + gap);
    const barH = (value / max) * chartH;
    const y = pad.top + chartH - barH;
    ctx.fillStyle = color;
    ctx.fillRect(x, y, barW, barH);
    points.push({ x, y, w: barW, h: barH, label: labels[index], value, text: `${labels[index]}: ${fmt.format(value)} posts` });
  });

  ctx.fillStyle = '#607076';
  ctx.font = '11px system-ui, sans-serif';
  ctx.textAlign = 'left';
  ctx.fillText(fmt.format(max), 4, pad.top + 10);
  ctx.textAlign = 'center';
  const step = compact ? Math.max(1, Math.floor(labels.length / 3)) : Math.max(1, Math.floor(labels.length / 6));
  labels.forEach((label, index) => {
    if (index % step !== 0 && index !== labels.length - 1) return;
    const x = pad.left + index * (barW + gap) + barW / 2;
    ctx.fillText(label, x, height - 14);
  });
  state.charts[canvas.id] = { type: 'bar', points };
}

function drawDonut(canvas, rows) {
  const activeRows = rows.filter((row) => row.active !== false && row.value > 0);
  if (!activeRows.length) {
    drawEmptyChart(canvas, 'No data available for this section');
    return;
  }
  const { ctx, width, height } = setupCanvas(canvas, Number(canvas.getAttribute('height')) || 220);
  const total = activeRows.reduce((sum, row) => sum + row.value, 0) || 1;
  const radius = Math.min(width, height) * (width < 420 ? 0.28 : 0.32);
  const cx = width < 420 ? width * 0.5 : width * 0.36;
  const cy = height * 0.48;
  let start = -Math.PI / 2;
  const points = [];

  activeRows.forEach((row) => {
    const angle = (row.value / total) * Math.PI * 2;
    ctx.beginPath();
    ctx.moveTo(cx, cy);
    ctx.arc(cx, cy, radius, start, start + angle);
    ctx.closePath();
    ctx.fillStyle = row.color;
    ctx.fill();
    points.push({ cx, cy, r: radius, start, end: start + angle, text: `${row.label}: ${fmt.format(row.value)} (${percentFmt.format(row.value / total)})` });
    start += angle;
  });

  ctx.beginPath();
  ctx.arc(cx, cy, radius * 0.58, 0, Math.PI * 2);
  ctx.fillStyle = '#ffffff';
  ctx.fill();
  ctx.fillStyle = '#1c2427';
  ctx.font = '600 17px system-ui, sans-serif';
  ctx.textAlign = 'center';
  ctx.fillText(fmt.format(total), cx, cy + 6);
  state.charts[canvas.id] = { type: 'donut', points };
}

function renderLegend(containerId, rows, groupName) {
  const container = el(containerId);
  container.innerHTML = rows.map((row) => {
    const active = row.active !== false;
    return `<button type="button" class="legend-item ${active ? 'active' : ''}" data-chart-group="${groupName}" data-series="${escapeHtml(row.label)}" aria-pressed="${active}">
      <span style="--legend-color:${row.color}"></span>${escapeHtml(row.label)}<strong>${fmt.format(row.value)}</strong>
    </button>`;
  }).join('');
  container.querySelectorAll('[data-series]').forEach((button) => {
    button.addEventListener('click', async () => {
      const group = state.chartSeries[button.dataset.chartGroup];
      group[button.dataset.series] = !group[button.dataset.series];
      await render();
    });
  });
}

function renderCharts(posts, account) {
  const byMonth = new Map();
  posts.forEach((post) => {
    const date = parseDate(post.created_at);
    if (!date) return;
    const key = `${date.getUTCFullYear()}-${String(date.getUTCMonth() + 1).padStart(2, '0')}`;
    byMonth.set(key, (byMonth.get(key) || 0) + 1);
  });
  const labels = [...byMonth.keys()].sort();
  const recentLabels = labels.slice(-36);
  const values = state.chartSeries.volume.Posts ? recentLabels.map((label) => byMonth.get(label)) : [];
  el('volumeCaption').textContent = recentLabels.length ? `last ${recentLabels.length} active months` : 'No data available for this section';
  drawBarChart(el('volumeChart'), recentLabels, values, accounts[account].color);
  renderLegend('volumeLegend', [{ label: 'Posts', value: posts.length, color: accounts[account].color, active: state.chartSeries.volume.Posts }], 'volume');

  const mix = [
    { label: 'Likes', value: posts.reduce((s, p) => s + numberValue(p.favorite_count), 0), color: '#d6223a' },
    { label: 'Replies', value: posts.reduce((s, p) => s + numberValue(p.reply_count), 0), color: '#227c91' },
    { label: 'Retweets', value: posts.reduce((s, p) => s + numberValue(p.retweet_count), 0), color: '#2d7d5f' },
    { label: 'Quotes', value: posts.reduce((s, p) => s + numberValue(p.quote_count), 0), color: '#b57912' }
  ].map((row) => ({ ...row, active: state.chartSeries.engagement[row.label] !== false }));
  drawDonut(el('engagementChart'), mix);
  renderLegend('engagementLegend', mix, 'engagement');
}

function topicMatches(topic, query) {
  if (!query) return true;
  const haystack = [
    ...(topic.top_terms || []),
    ...(topic.representative_posts || []).map((post) => post.text || '')
  ].join(' ').toLowerCase();
  return haystack.includes(query);
}

function renderTopicDetail(topic) {
  const detail = el('topicDetail');
  if (!topic) {
    detail.innerHTML = '<div class="empty">No data available for this section</div>';
    return;
  }
  const terms = (topic.top_terms || []).map((term) => `<span class="term">${escapeHtml(term)}</span>`).join('');
  const posts = (topic.representative_posts || []).map((post) => `<article class="topic-post">
    <div><a href="${post.tweet_url}" target="_blank" rel="noreferrer">${escapeHtml(post.id)}</a><span>score ${Number(post.score || 0).toFixed(3)}</span></div>
    <p>${escapeHtml(post.text || '')}</p>
  </article>`).join('');
  detail.innerHTML = `<section class="topic-detail-inner">
    <div class="panel-head compact-head"><h4>Topic ${topic.topic_id} Detail</h4><span>${(topic.representative_posts || []).length} representative posts</span></div>
    <div class="topic-terms detail-terms">${terms}</div>
    <div class="topic-posts">${posts || '<div class="empty">No data available for this section</div>'}</div>
  </section>`;
}

function renderTopics(lda) {
  const container = el('topicList');
  if (!lda || !Array.isArray(lda.topics) || !lda.topics.length) {
    el('topicMeta').textContent = 'not generated';
    container.innerHTML = '<div class="empty">No data available for this section</div>';
    el('topicDetail').innerHTML = '';
    return;
  }
  const selection = lda.topic_selection;
  el('topicMeta').textContent = selection ? `${selection.selected_num_topics} selected topics` : `${lda.num_topics} topics`;

  const evaluations = selection?.evaluations || [];
  const minCoherence = evaluations.length ? Math.min(...evaluations.map((row) => Number(row.coherence_npmi || 0))) : 0;
  const maxCoherence = evaluations.length ? Math.max(...evaluations.map((row) => Number(row.coherence_npmi || 0))) : 1;
  const selectionHtml = selection ? `<section class="lda-selection">
    <div class="lda-score-card"><span>Selected Topics</span><strong>${selection.selected_num_topics}</strong></div>
    <div class="lda-score-card"><span>Coherence NPMI</span><strong>${Number(selection.selected_coherence_npmi || 0).toFixed(4)}</strong></div>
    <div class="lda-score-card"><span>Perplexity</span><strong>${Number(selection.selected_perplexity || 0).toFixed(1)}</strong></div>
    <div class="coherence-list">
      ${evaluations.map((row) => {
        const coherence = Number(row.coherence_npmi || 0);
        const width = maxCoherence === minCoherence ? 100 : Math.max(8, ((coherence - minCoherence) / (maxCoherence - minCoherence)) * 100);
        return `<div class="coherence-row ${row.num_topics === selection.selected_num_topics ? 'selected' : ''}" style="--bar-width:${width}%"><span>${row.num_topics} topics</span><strong>${coherence.toFixed(4)}</strong></div>`;
      }).join('')}
    </div>
  </section>` : '';

  const query = state.topicSearch.trim().toLowerCase();
  const matchingTopics = lda.topics.filter((topic) => topicMatches(topic, query));
  if (!matchingTopics.some((topic) => topic.topic_id === state.selectedTopicId)) {
    state.selectedTopicId = matchingTopics[0]?.topic_id ?? lda.topics[0].topic_id;
  }

  const topicsHtml = matchingTopics.map((topic) => {
    const terms = (topic.top_terms || []).slice(0, 8).map((term) => `<span class="term">${escapeHtml(term)}</span>`).join('');
    const example = topic.representative_posts?.[0];
    const active = topic.topic_id === state.selectedTopicId ? 'active' : '';
    return `<button class="topic-item topic-button ${active}" type="button" data-topic-id="${topic.topic_id}" aria-label="Inspect topic ${topic.topic_id}">
      <span class="topic-title">Topic ${topic.topic_id}</span>
      <span class="topic-terms">${terms}</span>
      ${example ? `<span class="example">${escapeHtml(example.text || '')}</span>` : ''}
    </button>`;
  }).join('');

  container.innerHTML = selectionHtml + (topicsHtml || '<div class="empty">No topics match the current topic search.</div>');
  container.querySelectorAll('[data-topic-id]').forEach((button) => {
    button.addEventListener('click', () => {
      state.selectedTopicId = Number(button.dataset.topicId);
      renderTopics(lda);
    });
  });
  renderTopicDetail(lda.topics.find((topic) => topic.topic_id === state.selectedTopicId));
}

function renderSentiment(sentiment) {
  const summary = el('sentimentSummary');
  if (!sentiment || !sentiment.label_counts) {
    el('sentimentMeta').textContent = 'not generated';
    summary.innerHTML = '<div class="empty">No data available for this section</div>';
    drawEmptyChart(el('sentimentChart'), 'No data available for this section');
    el('sentimentLegend').innerHTML = '';
    return;
  }
  el('sentimentMeta').textContent = `${fmt.format(sentiment.post_count || 0)} posts`;
  const rows = Object.entries(sentiment.label_counts).sort((a, b) => b[1] - a[1]);
  rows.forEach(([label]) => {
    if (!(label in state.chartSeries.sentiment)) state.chartSeries.sentiment[label] = true;
  });
  summary.innerHTML = rows.slice(0, 3).map(([label, count]) => `<div class="sentiment-card"><span>${escapeHtml(label)}</span><strong>${fmt.format(count)}</strong></div>`).join('');
  const colors = ['#2d7d5f', '#b57912', '#d6223a', '#227c91', '#607076'];
  const chartRows = rows.map(([label, value], index) => ({ label, value, color: colors[index % colors.length], active: state.chartSeries.sentiment[label] !== false }));
  drawDonut(el('sentimentChart'), chartRows);
  renderLegend('sentimentLegend', chartRows, 'sentiment');
}

function badge(text, cls = '') {
  return `<span class="badge ${cls}">${escapeHtml(text)}</span>`;
}

function postBadges(post) {
  return [
    badge(post.brand, 'brand'),
    badge(post.date_iso || 'unknown date'),
    badge(post.sentiment_label, `sentiment-${post.sentiment_label}`),
    badge(post.topic_id === null ? 'Topic unknown' : `Topic ${post.topic_id}`),
    badge(fmt.format(post.total_engagement), 'engagement'),
    badge(post.viral ? 'Viral' : 'Standard', post.viral ? 'viral' : '')
  ].join('');
}

function renderPosts(posts) {
  const totalPages = Math.max(1, Math.ceil(posts.length / pageSize));
  state.page = Math.min(Math.max(1, state.page), totalPages);
  const start = (state.page - 1) * pageSize;
  const rows = posts.slice(start, start + pageSize);
  el('postCountLabel').textContent = `${fmt.format(posts.length)} shown, ${fmt.format(rows.length)} on this page`;
  el('pageLabel').textContent = `${state.page} / ${totalPages}`;
  el('prevPageButton').disabled = state.page <= 1;
  el('nextPageButton').disabled = state.page >= totalPages;

  if (!rows.length) {
    el('postTableWrap').innerHTML = '<div class="empty">No data available for this section</div>';
    el('postCards').innerHTML = '';
    return;
  }

  el('postTableWrap').innerHTML = `<table class="post-table">
    <thead><tr><th>Date</th><th>Post</th><th>Sentiment</th><th>Topic</th><th>Engagement</th><th>Link</th></tr></thead>
    <tbody>${rows.map((post) => `<tr>
      <td>${escapeHtml(post.date_iso || 'unknown')}</td>
      <td>${escapeHtml(post.text || '')}</td>
      <td>${escapeHtml(post.sentiment_label)}</td>
      <td>${post.topic_id === null ? 'unknown' : `Topic ${post.topic_id}`}</td>
      <td>${fmt.format(post.total_engagement)}</td>
      <td><a href="${post.tweet_url}" target="_blank" rel="noreferrer">Open</a></td>
    </tr>`).join('')}</tbody>
  </table>`;

  el('postCards').innerHTML = rows.map((post) => {
    const expanded = state.expandedPosts.has(post.id);
    const textClass = expanded ? 'post-text expanded' : 'post-text';
    return `<article class="post-card">
      <div class="post-badges">${postBadges(post)}</div>
      <p class="${textClass}" id="post-text-${post.id}">${escapeHtml(post.text || '')}</p>
      <button class="text-toggle" type="button" data-post-id="${post.id}" aria-expanded="${expanded}" aria-controls="post-text-${post.id}">${expanded ? 'Show less' : 'Show more'}</button>
      <div class="metric-badges">
        ${badge(`likes ${fmt.format(numberValue(post.favorite_count))}`)}
        ${badge(`replies ${fmt.format(numberValue(post.reply_count))}`)}
        ${badge(`retweets ${fmt.format(numberValue(post.retweet_count))}`)}
        ${badge(`quotes ${fmt.format(numberValue(post.quote_count))}`)}
      </div>
      <a class="post-link" href="${post.tweet_url}" target="_blank" rel="noreferrer">Open X post</a>
    </article>`;
  }).join('');

  el('postCards').querySelectorAll('[data-post-id]').forEach((button) => {
    button.addEventListener('click', async () => {
      const id = button.dataset.postId;
      if (state.expandedPosts.has(id)) state.expandedPosts.delete(id);
      else state.expandedPosts.add(id);
      await render();
    });
  });
}

function syncInputs() {
  el('searchInput').value = state.search;
  el('dateFromInput').value = state.dateFrom;
  el('dateToInput').value = state.dateTo;
  el('viralSelect').value = state.viral;
  el('sortSelect').value = state.sort;
  el('activeFilterCount').textContent = `${countActiveFilters()} active`;
}

async function render() {
  const dataset = await loadAccount(state.account);
  const enriched = buildEnrichedDataset(state.account, dataset);
  populateFilterOptions(enriched.posts, dataset);
  syncInputs();
  const visible = filteredPosts(enriched.posts);
  renderStatus(dataset);
  renderMetrics(visible);
  renderEvidence(visible);
  renderCharts(visible, state.account);
  renderTopics(dataset.lda);
  renderSentiment(dataset.sentiment);
  renderPosts(visible);
  el('dataStatus').textContent = `${accounts[state.account].label}: ${fmt.format(dataset.posts.length)} posts loaded`;
}

async function dispatchWorkflow(kind) {
  const token = el('adminTokenInput').value.trim();
  const account = state.account;
  const maxScrolls = el('actionMaxScrolls').value || '2500';
  const maxPosts = el('actionMaxPosts').value || '0';
  const result = el('actionResult');
  if (!token) {
    result.textContent = 'Admin token is required.';
    return;
  }
  result.textContent = `Submitting ${kind} for ${accounts[account].label}...`;
  setActionButtons(true);
  try {
    const response = await fetch('/api/dispatch', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
      body: JSON.stringify({ kind, account, maxScrolls, analysisMaxPosts: maxPosts })
    });
    const body = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(body.error || `HTTP ${response.status}`);
    result.textContent = `${kind} workflow dispatched for ${accounts[account].label}. Check GitHub Actions for progress.`;
  } catch (error) {
    result.textContent = `Dispatch failed: ${error.message}`;
  } finally {
    setActionButtons(false);
  }
}

function setActionButtons(disabled) {
  ['runScrapeButton', 'runLdaButton', 'runSentimentButton'].forEach((id) => { el(id).disabled = disabled; });
}

function chartPointFromEvent(canvas, event) {
  const rect = canvas.getBoundingClientRect();
  const x = event.clientX - rect.left;
  const y = event.clientY - rect.top;
  const meta = state.charts[canvas.id];
  if (!meta) return null;
  if (meta.type === 'bar') {
    return meta.points.find((point) => x >= point.x && x <= point.x + point.w && y >= point.y && y <= point.y + Math.max(point.h, 8));
  }
  if (meta.type === 'donut') {
    return meta.points.find((point) => {
      const dx = x - point.cx;
      const dy = y - point.cy;
      const distance = Math.sqrt(dx * dx + dy * dy);
      let angle = Math.atan2(dy, dx);
      if (angle < -Math.PI / 2) angle += Math.PI * 2;
      return distance <= point.r && distance >= point.r * 0.45 && angle >= point.start && angle <= point.end;
    });
  }
  return null;
}

function showTooltip(text, event) {
  const tooltip = el('chartTooltip');
  tooltip.textContent = text;
  tooltip.style.left = `${Math.min(window.innerWidth - 180, event.clientX + 12)}px`;
  tooltip.style.top = `${Math.max(12, event.clientY - 36)}px`;
  tooltip.classList.add('visible');
}

function bindChartTooltip(canvas) {
  const update = (event) => {
    const point = chartPointFromEvent(canvas, event);
    if (point) showTooltip(point.text, event);
    else el('chartTooltip').classList.remove('visible');
  };
  canvas.addEventListener('mousemove', update);
  canvas.addEventListener('click', update);
  canvas.addEventListener('touchstart', (event) => update(event.touches[0]), { passive: true });
  canvas.addEventListener('mouseleave', () => el('chartTooltip').classList.remove('visible'));
}

function bindEvents() {
  document.querySelectorAll('.tab').forEach((button) => {
    button.addEventListener('click', async () => {
      document.querySelectorAll('.tab').forEach((tab) => tab.classList.remove('active'));
      button.classList.add('active');
      state.account = button.dataset.account;
      state.selectedTopicId = null;
      state.page = 1;
      await render();
    });
  });

  document.querySelectorAll('.section-nav a').forEach((link) => {
    link.addEventListener('click', (event) => {
      event.preventDefault();
      document.querySelector(link.getAttribute('href'))?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    });
  });

  el('topicSearchInput').addEventListener('input', async (event) => { state.topicSearch = event.target.value; await render(); });
  el('searchInput').addEventListener('input', async (event) => { state.search = event.target.value; state.page = 1; await render(); });
  el('yearSelect').addEventListener('change', async (event) => { state.year = event.target.value; state.page = 1; await render(); });
  el('dateFromInput').addEventListener('change', async (event) => { state.dateFrom = event.target.value; state.page = 1; await render(); });
  el('dateToInput').addEventListener('change', async (event) => { state.dateTo = event.target.value; state.page = 1; await render(); });
  el('sentimentSelect').addEventListener('change', async (event) => { state.sentiment = event.target.value; state.page = 1; await render(); });
  el('topicFilterSelect').addEventListener('change', async (event) => { state.topic = event.target.value; state.page = 1; await render(); });
  el('viralSelect').addEventListener('change', async (event) => { state.viral = event.target.value; state.page = 1; await render(); });
  el('sortSelect').addEventListener('change', async (event) => { state.sort = event.target.value; state.page = 1; await render(); });
  el('resetFiltersButton').addEventListener('click', async () => { resetFilters(); await render(); });
  el('prevPageButton').addEventListener('click', async () => { state.page -= 1; await render(); });
  el('nextPageButton').addEventListener('click', async () => { state.page += 1; await render(); });
  el('runScrapeButton').addEventListener('click', () => dispatchWorkflow('scrape'));
  el('runLdaButton').addEventListener('click', () => dispatchWorkflow('lda'));
  el('runSentimentButton').addEventListener('click', () => dispatchWorkflow('sentiment'));
  ['volumeChart', 'engagementChart', 'sentimentChart'].forEach((id) => bindChartTooltip(el(id)));
  window.addEventListener('resize', () => render());
}

function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>'"]/g, (char) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[char]));
}

showLoading();
bindEvents();
render().catch((error) => {
  console.error(error);
  el('dataStatus').textContent = `Dashboard load failed: ${error.message}`;
  el('postTableWrap').innerHTML = `<div class="empty">Dashboard load failed: ${escapeHtml(error.message)}</div>`;
});
