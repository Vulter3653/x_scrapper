const accounts = {
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

const pageSize = 40;
const state = {
  account: 'wendys',
  brand: 'all',
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
const compactFmt = new Intl.NumberFormat('en-US', { notation: 'compact', maximumFractionDigits: 1 });

function parseDate(value) {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? null : date;
}

function isoDate(value) {
  const date = parseDate(value);
  return date ? date.toISOString().slice(0, 10) : '';
}

function formatEngagement(value) {
  return Math.abs(Number(value) || 0) >= 1000 ? compactFmt.format(value) : fmt.format(value);
}

function numberValue(value) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : 0;
}

function firstValue(row, names, fallback = '') {
  for (const name of names) {
    if (row && row[name] !== undefined && row[name] !== null && row[name] !== '') return row[name];
  }
  return fallback;
}

function metricValue(row, names) {
  return numberValue(firstValue(row, names, 0));
}

function textValue(row) {
  return String(firstValue(row, ['text', 'content', 'tweet_text', 'post_text'], ''));
}

function dateValue(row) {
  return firstValue(row, ['date', 'created_at', 'timestamp'], '');
}

function brandValue(row, fallback) {
  return String(firstValue(row, ['brand', 'company', 'account'], fallback));
}

function likes(row) { return metricValue(row, ['likes', 'like_count', 'favorite_count']); }
function replies(row) { return metricValue(row, ['replies', 'reply_count']); }
function retweets(row) { return metricValue(row, ['retweets', 'retweet_count', 'reposts']); }
function quotes(row) { return metricValue(row, ['quotes', 'quote_count']); }

function engagement(post) {
  return likes(post) + replies(post) + retweets(post) + quotes(post);
}

function words(text) {
  return String(text || '').trim().split(/\s+/).filter(Boolean);
}

function countMatches(text, pattern) {
  return (String(text || '').match(pattern) || []).length;
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
  const dataset = { posts: [], lda: null, sentiment: null, scrapeState: null, errors: {} };

  try { dataset.posts = await loadJson(config.posts); } catch (error) { dataset.errors.posts = error.message; }
  try { dataset.lda = await loadJson(config.lda); } catch (error) { dataset.errors.lda = error.message; }
  try { dataset.sentiment = await loadJson(config.sentiment); } catch (error) { dataset.errors.sentiment = error.message; }
  try { dataset.humor = await loadJson(config.humor); } catch (error) { dataset.errors.humor = error.message; }
  try { dataset.scrapeState = await loadJson(config.scrapeState); } catch (error) { dataset.errors.scrapeState = error.message; }

  state.datasets[accountKey] = dataset;
  return dataset;
}


async function loadAllAccounts() {
  const entries = await Promise.all(Object.keys(accounts).map(async (key) => [key, await loadAccount(key)]));
  return Object.fromEntries(entries);
}

function buildAllEnrichedPosts(datasets) {
  return Object.entries(datasets).flatMap(([key, dataset]) => buildEnrichedDataset(key, dataset).posts);
}

function buildEnrichedDataset(accountKey, dataset) {
  const cacheKey = `${accountKey}:${dataset.posts.length}:${dataset.sentiment?.post_count || 0}:${dataset.humor?.post_count || 0}:${dataset.lda?.num_topics || 0}`;
  if (state.enriched[cacheKey]) return state.enriched[cacheKey];

  const sentimentById = new Map((dataset.sentiment?.posts || []).map((row) => [String(row.id), row]));
  const humorById = new Map((dataset.humor?.posts || []).map((row) => [String(row.id), row]));
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
  const viralThreshold = percentile(engagements, 0.95);
  const posts = dataset.posts.map((post) => {
    const id = String(post.id);
    const sentiment = sentimentById.get(id);
    const humor = humorById.get(id);
    const topic = topicById.get(id);
    const totalEngagement = engagement(post);
    return {
      ...post,
      id,
      account: accountKey,
      brand: brandValue(post, accounts[accountKey].label),
      date_iso: isoDate(dateValue(post)),
      text_normalized: textValue(post),
      likes_count: likes(post),
      replies_count: replies(post),
      retweets_count: retweets(post),
      quotes_count: quotes(post),
      total_engagement: totalEngagement,
      log_total_engagement: Math.log1p(totalEngagement),
      text_length: textValue(post).length,
      word_count: words(textValue(post)).length,
      has_url: /(https?:\/\/|www\.)/i.test(textValue(post)),
      hashtag_count: countMatches(textValue(post), /(^|\s)#[\p{L}\p{N}_]+/gu),
      mention_count: countMatches(textValue(post), /(^|\s)@[A-Za-z0-9_]+/g),
      sentiment_label: sentiment?.top_label || 'unknown',
      sentiment_score: numberValue(sentiment?.top_score),
      humor_label: humor?.top_label || 'unknown',
      humor_score: numberValue(humor?.top_score),
      topic_id: topic?.topic_id ?? null,
      topic_terms: topic?.top_terms || [],
      topic_score: numberValue(topic?.score),
      is_viral: totalEngagement >= viralThreshold && totalEngagement > 0,
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
    brand: state.brand,
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
    const date = parseDate(post.date_iso || dateValue(post));
    const year = date ? String(date.getUTCFullYear()) : 'unknown';
    if (state.brand !== 'all' && post.account !== state.brand) return false;
    if (state.year !== 'all' && year !== state.year) return false;
    if (from && (!date || date < from)) return false;
    if (to && (!date || date > to)) return false;
    if (state.sentiment !== 'all' && post.sentiment_label !== state.sentiment) return false;
    if (state.topic !== 'all' && String(post.topic_id) !== state.topic) return false;
    if (state.viral === 'viral' && !post.is_viral) return false;
    if (state.viral === 'nonviral' && post.is_viral) return false;
    if (!query) return true;
    return [post.text_normalized, post.tweet_url, post.lang, post.sentiment_label, post.topic_terms.join(' ')].some((value) => String(value || '').toLowerCase().includes(query));
  });

  rows.sort((a, b) => {
    if (state.sort === 'engagement_desc') return b.total_engagement - a.total_engagement;
    if (state.sort === 'likes_desc') return b.likes_count - a.likes_count;
    if (state.sort === 'replies_desc') return b.replies_count - a.replies_count;
    if (state.sort === 'retweets_desc') return b.retweets_count - a.retweets_count;
    if (state.sort === 'text_length_desc') return b.text_length - a.text_length;
    return numberValue(b.id) - numberValue(a.id);
  });
  state.cache.set(key, rows);
  return rows;
}

function dateRange(posts) {
  const dates = posts.map((post) => parseDate(post.date_iso || dateValue(post))).filter(Boolean).sort((a, b) => a - b);
  if (!dates.length) return '-';
  return `${dates[0].toISOString().slice(0, 10)} to ${dates[dates.length - 1].toISOString().slice(0, 10)}`;
}

function countActiveFilters() {
  return [state.search, state.dateFrom, state.dateTo].filter(Boolean).length +
    ['brand', 'year', 'sentiment', 'topic', 'viral'].filter((key) => state[key] !== 'all').length;
}

function populateFilterOptions(posts, dataset) {
  const years = [...new Set(posts.map((post) => parseDate(dateValue(post))).filter(Boolean).map((date) => date.getUTCFullYear()))].sort((a, b) => b - a);
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

  const brandSelect = el('brandSelect');
  const brands = Object.entries(accounts);
  brandSelect.innerHTML = '<option value="all">All brands</option>' + brands.map(([key, cfg]) => `<option value="${key}">${escapeHtml(cfg.label)}</option>`).join('');
  if (state.brand !== 'all' && !accounts[state.brand]) state.brand = 'all';
  brandSelect.value = state.brand;
  el('activeFilterCount').textContent = `${countActiveFilters()} active`;
}

function resetFilters() {
  state.search = '';
  state.brand = 'all';
  state.year = 'all';
  state.dateFrom = '';
  state.dateTo = '';
  state.sentiment = 'all';
  state.topic = 'all';
  state.viral = 'all';
  state.sort = 'date_desc';
  state.page = 1;
  el('searchInput').value = '';
  el('brandSelect').value = 'all';
  el('dateFromInput').value = '';
  el('dateToInput').value = '';
  el('viralSelect').value = 'all';
  el('sortSelect').value = 'date_desc';
}

function setDatasetState(stateName, message) {
  const badge = el('datasetStateBadge');
  badge.className = `state-badge ${stateName}`;
  badge.textContent = stateName.charAt(0).toUpperCase() + stateName.slice(1);
  el('dataStatus').textContent = message;
}

function latestTimestamp(datasets) {
  const values = Object.values(datasets).flatMap((dataset) => [
    dataset.scrapeState?.updated_at, dataset.scrapeState?.scraped_at, dataset.lda?.generated_at, dataset.sentiment?.generated_at, dataset.humor?.generated_at
  ]).filter(Boolean).map((value) => new Date(value)).filter((date) => !Number.isNaN(date.getTime()));
  if (!values.length) return 'unknown';
  return values.sort((a, b) => b - a)[0].toISOString().slice(0, 19).replace('T', ' ');
}

function showLoading() {
  setDatasetState('loading', 'Loading datasets...');
  ['metricPosts', 'metricRange', 'metricMedian', 'metricEngagement', 'metricViralShare', 'metricPositiveShare', 'metricPostsTrend', 'metricRangeTrend', 'metricMedianTrend', 'metricEngagementTrend', 'metricViralTrend', 'metricPositiveTrend'].forEach((id) => {
    const node = el(id);
    if (node) node.textContent = '-';
  });
  el('descriptiveCards').innerHTML = '<div class="skeleton"></div>';
  el('evidenceGrid').innerHTML = '<div class="skeleton"></div>';
  el('postTableWrap').innerHTML = '<div class="skeleton"></div>';
  el('postCards').innerHTML = '';
}

function renderStatus(dataset) {
  const rows = [
    ['Posts', dataset.posts.length ? `${fmt.format(dataset.posts.length)} loaded` : `missing${dataset.errors.posts ? `: ${dataset.errors.posts}` : ''}`, dataset.posts.length ? 'ok' : 'warn'],
    ['LDA', dataset.lda ? 'available' : `not generated${dataset.errors.lda ? `: ${dataset.errors.lda}` : ''}`, dataset.lda ? 'ok' : 'warn'],
    ['Zero-shot', dataset.sentiment ? 'available' : `not generated${dataset.errors.sentiment ? `: ${dataset.errors.sentiment}` : ''}`, dataset.sentiment ? 'ok' : 'warn'],
    ['HSQ Humor', dataset.humor ? 'available' : `not generated${dataset.errors.humor ? `: ${dataset.errors.humor}` : ''}`, dataset.humor ? 'ok' : 'warn']
  ];
  el('analysisStatus').innerHTML = rows.map(([name, value, cls]) => `<div class="status-item ${cls}"><span>${name}</span><strong>${escapeHtml(value)}</strong></div>`).join('');
}


function groupBy(rows, getter) {
  const map = new Map();
  rows.forEach((row) => {
    const key = getter(row) ?? 'unknown';
    if (!map.has(key)) map.set(key, []);
    map.get(key).push(row);
  });
  return map;
}

function average(values) {
  const valid = values.map(numberValue).filter((value) => Number.isFinite(value));
  return valid.length ? valid.reduce((sum, value) => sum + value, 0) / valid.length : 0;
}

function ratio(count, total) {
  return total ? count / total : 0;
}

function summarizeValues(values) {
  const nums = values.map(numberValue).filter((value) => Number.isFinite(value));
  return {
    total: nums.reduce((sum, value) => sum + value, 0),
    avg: average(nums),
    median: median(nums),
    p75: percentile(nums, 0.75),
    p90: percentile(nums, 0.90),
    p95: percentile(nums, 0.95),
    max: nums.length ? Math.max(...nums) : 0
  };
}

function metricRows(title, rows) {
  return `<article class="analytics-card"><h3>${escapeHtml(title)}</h3><dl>${rows.map(([label, value]) => `<div><dt>${escapeHtml(label)}</dt><dd>${escapeHtml(value)}</dd></div>`).join('')}</dl></article>`;
}

function sentimentBucket(label) {
  const value = String(label || '').toLowerCase();
  if (value === 'positive' || value === 'neutral' || value === 'negative') return value;
  return 'other';
}

function topEntry(entries, valueGetter) {
  return [...entries].sort((a, b) => valueGetter(b) - valueGetter(a))[0];
}

function computeDescriptiveStats(posts) {
  const total = posts.length;
  const engagementStats = summarizeValues(posts.map((post) => post.total_engagement));
  const textStats = summarizeValues(posts.map((post) => post.text_length));
  const wordStats = summarizeValues(posts.map((post) => post.word_count));
  const dates = posts.map((post) => parseDate(post.date_iso || dateValue(post))).filter(Boolean);
  const activeDays = new Set(dates.map((date) => date.toISOString().slice(0, 10))).size;
  const normalizedTexts = posts.map((post) => post.text_normalized.trim().toLowerCase()).filter(Boolean);
  const duplicateTexts = normalizedTexts.length - new Set(normalizedTexts).size;
  const sentimentCounts = groupBy(posts, (post) => sentimentBucket(post.sentiment_label));
  const topicGroups = groupBy(posts.filter((post) => post.topic_id !== null), (post) => `Topic ${post.topic_id}`);
  const largestTopic = topEntry(topicGroups.entries(), ([, rows]) => rows.length);
  const topMedianTopic = topEntry(topicGroups.entries(), ([, rows]) => median(rows.map((post) => post.total_engagement)));
  return {
    total,
    activeDays,
    brands: new Set(posts.map((post) => post.brand)).size,
    engagementStats,
    textStats,
    wordStats,
    missingTextRatio: ratio(posts.filter((post) => !post.text_normalized.trim()).length, total),
    duplicateTextRatio: ratio(duplicateTexts, total),
    averagePostsPerDay: activeDays ? total / activeDays : 0,
    urlRatio: ratio(posts.filter((post) => post.has_url).length, total),
    avgHashtags: average(posts.map((post) => post.hashtag_count)),
    avgMentions: average(posts.map((post) => post.mention_count)),
    sentimentShares: Object.fromEntries(['positive', 'neutral', 'negative', 'other'].map((key) => [key, ratio((sentimentCounts.get(key) || []).length, total)])),
    topicCount: topicGroups.size,
    largestTopicShare: largestTopic ? ratio(largestTopic[1].length, total) : 0,
    topTopicByCount: largestTopic ? largestTopic[0] : '-',
    topTopicByMedian: topMedianTopic ? `${topMedianTopic[0]} (${fmt.format(median(topMedianTopic[1].map((post) => post.total_engagement)))})` : '-'
  };
}

function renderDescriptiveCards(posts) {
  if (!posts.length) {
    el('descriptiveCards').innerHTML = '<div class="empty">No data available for this section</div>';
    return;
  }
  const stats = computeDescriptiveStats(posts);
  el('descriptiveCards').innerHTML = [
    metricRows('Dataset Overview', [
      ['Total Posts', fmt.format(stats.total)], ['Number of Brands', fmt.format(stats.brands)], ['Date Range', dateRange(posts)],
      ['Active Posting Days', fmt.format(stats.activeDays)], ['Average Posts per Day', stats.averagePostsPerDay.toFixed(2)],
      ['Missing Text Ratio', percentFmt.format(stats.missingTextRatio)], ['Duplicate Text Ratio', percentFmt.format(stats.duplicateTextRatio)]
    ]),
    metricRows('Engagement Summary', [
      ['Total Engagement', fmt.format(stats.engagementStats.total)], ['Average Engagement', fmt.format(Math.round(stats.engagementStats.avg))],
      ['Median Engagement', fmt.format(stats.engagementStats.median)], ['P75 Engagement', fmt.format(stats.engagementStats.p75)],
      ['P90 Engagement', fmt.format(stats.engagementStats.p90)], ['P95 Engagement', fmt.format(stats.engagementStats.p95)], ['Max Engagement', fmt.format(stats.engagementStats.max)]
    ]),
    metricRows('Text Summary', [
      ['Average Text Length', fmt.format(Math.round(stats.textStats.avg))], ['Median Text Length', fmt.format(stats.textStats.median)],
      ['Average Word Count', fmt.format(Math.round(stats.wordStats.avg))], ['URL Included Ratio', percentFmt.format(stats.urlRatio)],
      ['Average Hashtag Count', stats.avgHashtags.toFixed(2)], ['Average Mention Count', stats.avgMentions.toFixed(2)]
    ]),
    metricRows('Sentiment Summary', [
      ['Positive Share', percentFmt.format(stats.sentimentShares.positive)], ['Neutral Share', percentFmt.format(stats.sentimentShares.neutral)],
      ['Negative Share', percentFmt.format(stats.sentimentShares.negative)], ['Other Share', percentFmt.format(stats.sentimentShares.other)]
    ]),
    metricRows('Topic Summary', [
      ['Number of Topics', fmt.format(stats.topicCount)], ['Largest Topic Share', percentFmt.format(stats.largestTopicShare)],
      ['Top Topic by Post Count', stats.topTopicByCount], ['Top Topic by Median Engagement', stats.topTopicByMedian]
    ])
  ].join('');
}

function colorAt(index) {
  return ['#E2231A', '#111827', '#2563EB', '#16A34A', '#F97316', '#94A3B8', '#DC2626', '#475569'][index % 8];
}


function canvasFont(width, size = 12, weight = '') {
  const scale = Math.max(0, Math.min(1, (width - 320) / 560));
  const adjusted = Math.round((width < 420 ? size + 1 : size) + scale);
  return `${weight ? `${weight} ` : ''}${adjusted}px system-ui, sans-serif`;
}

function safeChart(canvasId, drawFn) {
  try {
    drawFn();
  } catch (error) {
    console.warn(`Chart render failed: ${canvasId}`, error);
    const canvas = el(canvasId);
    if (canvas) drawEmptyChart(canvas, 'No data available for this section');
  }
}

function drawHorizontalBars(canvas, rows, valueLabel = '') {
  const sortedRows = [...rows].filter((row) => Number.isFinite(row.value)).sort((a, b) => b.value - a.value).slice(0, 12);
  if (!sortedRows.length) return drawEmptyChart(canvas, 'No data available for this section');
  const { ctx, width, height } = setupCanvas(canvas, Number(canvas.getAttribute('height')) || 260);
  const compact = width < 420;
  const pad = { top: 18, right: compact ? 30 : 66, bottom: 22, left: compact ? 54 : 118 };
  const chartW = Math.max(1, width - pad.left - pad.right);
  const rowH = Math.max(20, (height - pad.top - pad.bottom) / sortedRows.length);
  const max = Math.max(...sortedRows.map((row) => row.value), 1);
  const points = [];
  ctx.strokeStyle = '#E2E8F0';
  ctx.fillStyle = '#64748B';
  ctx.font = canvasFont(width, 12);
  sortedRows.forEach((row, index) => {
    const y = pad.top + index * rowH;
    const barW = Math.max(2, (row.value / max) * chartW);
    ctx.fillStyle = colorAt(index);
    ctx.fillRect(pad.left, y + 4, barW, Math.max(10, rowH - 9));
    ctx.fillStyle = '#64748B';
    ctx.textAlign = 'right';
    ctx.fillText(shortLabel(row.label, compact ? 7 : 16), pad.left - 6, y + rowH * 0.65);
    ctx.textAlign = 'left';
    ctx.fillText(formatEngagement(Math.round(row.value)), pad.left + barW + 6, y + rowH * 0.65);
    points.push({ x: pad.left, y, w: Math.max(barW, 8), h: rowH, text: `${row.label}: ${formatEngagement(Math.round(row.value))}${valueLabel}` });
  });
  state.charts[canvas.id] = { type: 'bar', points };
}

function drawHistogram(canvas, values, bins = 12) {
  const nums = values.filter((value) => Number.isFinite(value));
  if (!nums.length) return drawEmptyChart(canvas, 'No data available for this section');
  const max = Math.max(...nums);
  const min = Math.min(...nums);
  const step = Math.max(1, (max - min) / bins);
  const counts = Array.from({ length: bins }, () => 0);
  nums.forEach((value) => { counts[Math.min(bins - 1, Math.floor((value - min) / step))] += 1; });
  drawBarChart(canvas, counts.map((_, i) => `${Math.round(min + i * step)}`), counts, '#227c91');
}

function drawStackedShare(canvas, groups, categories) {
  const groupEntries = [...groups.entries()];
  if (!groupEntries.length || !categories.length) return drawEmptyChart(canvas, 'No data available for this section');
  const { ctx, width, height } = setupCanvas(canvas, Number(canvas.getAttribute('height')) || 260);
  const compact = width < 420;
  const pad = { top: 18, right: 14, bottom: compact ? 56 : 46, left: compact ? 50 : 92 };
  const chartW = width - pad.left - pad.right;
  const rowH = Math.max(26, (height - pad.top - pad.bottom) / groupEntries.length);
  const points = [];
  groupEntries.forEach(([group, rows], gi) => {
    let x = pad.left;
    const y = pad.top + gi * rowH + 5;
    categories.forEach((cat, ci) => {
      const count = rows.filter((row) => row.category === cat).length;
      const w = rows.length ? (count / rows.length) * chartW : 0;
      ctx.fillStyle = colorAt(ci);
      ctx.fillRect(x, y, w, Math.max(12, rowH - 11));
      if (w > 38) {
        ctx.fillStyle = '#ffffff';
        ctx.font = canvasFont(width, 11);
        ctx.textAlign = 'center';
        ctx.fillText(`${Math.round(ratio(count, rows.length) * 100)}%`, x + w / 2, y + rowH * 0.48);
      }
      points.push({ x, y, w: Math.max(w, 1), h: rowH, text: `${group} ${cat}: ${percentFmt.format(ratio(count, rows.length))}` });
      x += w;
    });
    ctx.fillStyle = '#64748B';
    ctx.font = canvasFont(width, 12);
    ctx.textAlign = 'right';
    ctx.fillText(shortLabel(group, compact ? 6 : 13), pad.left - 6, y + rowH * 0.55);
  });
  ctx.textAlign = 'left';
  categories.slice(0, compact ? 4 : 8).forEach((cat, i) => {
    const x = pad.left + (i % 4) * (compact ? 72 : 92);
    const y = height - (compact && i >= 4 ? 12 : 22) + Math.floor(i / 4) * 12;
    ctx.fillStyle = colorAt(i);
    ctx.fillRect(x, y - 8, 9, 9);
    ctx.fillStyle = '#64748B';
    ctx.font = canvasFont(width, 11);
    ctx.fillText(shortLabel(cat, width < 420 ? 8 : 12), x + 13, y);
  });
  state.charts[canvas.id] = { type: 'bar', points };
}

function drawBoxplot(canvas, groups) {
  const rows = [...groups.entries()].map(([label, posts]) => ({ label, values: posts.map((post) => post.total_engagement).sort((a, b) => a - b) })).filter((row) => row.values.length);
  if (!rows.length) return drawEmptyChart(canvas, 'No data available for this section');
  const { ctx, width, height } = setupCanvas(canvas, Number(canvas.getAttribute('height')) || 220);
  const max = Math.max(...rows.flatMap((row) => row.values), 1);
  const pad = { top: 20, right: 18, bottom: 34, left: 52 };
  const band = (width - pad.left - pad.right) / rows.length;
  const points = [];
  rows.forEach((row, i) => {
    const q1 = percentile(row.values, 0.25), med = median(row.values), q3 = percentile(row.values, 0.75), hi = Math.max(...row.values), lo = Math.min(...row.values);
    const x = pad.left + i * band + band / 2;
    const y = (v) => pad.top + (height - pad.top - pad.bottom) * (1 - v / max);
    ctx.strokeStyle = colorAt(i); ctx.fillStyle = 'rgba(34,124,145,0.18)';
    ctx.beginPath(); ctx.moveTo(x, y(lo)); ctx.lineTo(x, y(hi)); ctx.stroke();
    ctx.fillRect(x - band * 0.25, y(q3), band * 0.5, Math.max(4, y(q1) - y(q3)));
    ctx.strokeRect(x - band * 0.25, y(q3), band * 0.5, Math.max(4, y(q1) - y(q3)));
    ctx.beginPath(); ctx.moveTo(x - band * 0.28, y(med)); ctx.lineTo(x + band * 0.28, y(med)); ctx.stroke();
    ctx.fillStyle = '#64748B'; ctx.font = canvasFont(width, 12); ctx.textAlign = 'center'; ctx.fillText(shortLabel(row.label, width < 420 ? 7 : 10), x, height - 12);
    points.push({ x: x - band * 0.3, y: y(q3), w: band * 0.6, h: Math.max(12, y(q1) - y(q3)), text: `${row.label}: median ${fmt.format(med)}, P95 ${fmt.format(percentile(row.values, 0.95))}` });
  });
  state.charts[canvas.id] = { type: 'bar', points };
}

function drawHeatmap(canvas, groups, metrics) {
  const entries = [...groups.entries()];
  if (!entries.length) return drawEmptyChart(canvas, 'No data available for this section');
  const { ctx, width, height } = setupCanvas(canvas, Number(canvas.getAttribute('height')) || 260);
  const compact = width < 420;
  const pad = { top: 20, right: 12, bottom: 42, left: compact ? 50 : 88 };
  const cellW = (width - pad.left - pad.right) / metrics.length;
  const cellH = Math.max(30, (height - pad.top - pad.bottom) / entries.length);
  const matrix = entries.map(([label, rows]) => metrics.map(([name, getter]) => average(rows.map(getter))));
  const max = Math.max(...matrix.flat(), 1);
  const points = [];
  entries.forEach(([label], r) => {
    ctx.fillStyle = '#64748B';
    ctx.font = canvasFont(width, 12);
    ctx.textAlign = 'right';
    ctx.fillText(shortLabel(label, compact ? 6 : 12), pad.left - 5, pad.top + r * cellH + cellH * 0.6);
    metrics.forEach(([name], c) => {
      const value = matrix[r][c];
      const alpha = Math.max(0.15, value / max);
      ctx.fillStyle = `rgba(34,124,145,${alpha})`;
      const x = pad.left + c * cellW;
      const y = pad.top + r * cellH;
      ctx.fillRect(x, y, cellW - 4, cellH - 4);
      ctx.fillStyle = alpha > 0.55 ? '#ffffff' : '#1c2427';
      ctx.font = canvasFont(width, 11);
      ctx.textAlign = 'center';
      ctx.fillText(formatEngagement(Math.round(value)), x + cellW / 2, y + cellH * 0.58);
      points.push({ x, y, w: cellW, h: cellH, text: `${label} ${name}: ${formatEngagement(Math.round(value))}` });
    });
  });
  metrics.forEach(([name], c) => {
    ctx.fillStyle = '#64748B';
    ctx.textAlign = 'center';
    ctx.font = canvasFont(width, 12);
    ctx.fillText(shortLabel(name, 9), pad.left + c * cellW + cellW / 2, height - 14);
  });
  state.charts[canvas.id] = { type: 'bar', points };
}


function setInsight(id, text) {
  const node = el(id);
  if (node) node.textContent = text;
}

function renderChartInsights(posts) {
  if (!posts.length) {
    ['engagementHistogramInsight','brandBoxplotInsight','postsByBrandInsight','textLengthInsight','sentimentBrandInsight','topicBrandInsight','brandEngagementInsight','sentimentEngagementInsight','sentimentHeatmapInsight','dailyVolumeInsight','topicRankingInsight'].forEach((id) => setInsight(id, 'No data available for this section.'));
    return;
  }
  const brandGroups = groupBy(posts, (post) => post.brand);
  const topBrand = topEntry(brandGroups.entries(), ([, rows]) => rows.length);
  const topEngBrand = topEntry(brandGroups.entries(), ([, rows]) => average(rows.map((post) => post.total_engagement)));
  const sentGroups = groupBy(posts, (post) => sentimentBucket(post.sentiment_label));
  const topSent = topEntry(sentGroups.entries(), ([, rows]) => median(rows.map((post) => post.total_engagement)));
  const topicGroups = groupBy(posts.filter((post) => post.topic_id !== null), (post) => `Topic ${post.topic_id}`);
  const topTopic = topEntry(topicGroups.entries(), ([, rows]) => median(rows.map((post) => post.total_engagement)));
  setInsight('engagementHistogramInsight', `Median engagement is ${formatEngagement(median(posts.map((post) => post.total_engagement)))}; the distribution is interpreted at raw post level.`);
  setInsight('brandBoxplotInsight', topEngBrand ? `${topEngBrand[0]} has the highest average engagement among visible brands.` : 'No brand spread is available.');
  setInsight('postsByBrandInsight', topBrand ? `${topBrand[0]} contributes the largest visible post volume (${fmt.format(topBrand[1].length)} posts).` : 'No brand volume is available.');
  setInsight('textLengthInsight', `Median text length is ${fmt.format(median(posts.map((post) => post.text_length)))} characters.`);
  setInsight('sentimentBrandInsight', 'Sentiment shares are normalized within each visible brand.');
  setInsight('topicBrandInsight', topTopic ? `${topTopic[0]} is the highest-median topic among representative-topic posts.` : 'Topic labels are unavailable for the visible sample.');
  setInsight('brandEngagementInsight', topEngBrand ? `${topEngBrand[0]} leads raw mean engagement before any regression adjustment.` : 'No brand comparison is available.');
  setInsight('sentimentEngagementInsight', topSent ? `${topSent[0]} sentiment has the highest median engagement in the visible sample.` : 'No sentiment comparison is available.');
  setInsight('sentimentHeatmapInsight', 'Cell values are average engagement components; darker cells indicate larger raw averages.');
  setInsight('dailyVolumeInsight', 'Trend values show daily posting volume by brand for recent visible dates.');
  setInsight('topicRankingInsight', topTopic ? `${topTopic[0]} ranks highest by median engagement.` : 'No topic ranking is available.');
}

function renderDescriptives(posts) {
  renderDescriptiveCards(posts);
  renderChartInsights(posts);
  safeChart('engagementHistogram', () => drawHistogram(el('engagementHistogram'), posts.map((post) => post.total_engagement), 12));
  safeChart('brandBoxplotChart', () => drawBoxplot(el('brandBoxplotChart'), groupBy(posts, (post) => post.brand)));
  safeChart('postsByBrandChart', () => drawHorizontalBars(el('postsByBrandChart'), [...groupBy(posts, (post) => post.brand).entries()].map(([label, rows]) => ({ label, value: rows.length }))));
  safeChart('textLengthChart', () => drawHistogram(el('textLengthChart'), posts.map((post) => post.text_length), 12));
  safeChart('sentimentBrandChart', () => drawStackedShare(el('sentimentBrandChart'), new Map([...groupBy(posts, (post) => post.brand).entries()].map(([brand, rows]) => [brand, rows.map((post) => ({ category: sentimentBucket(post.sentiment_label) }))])), ['positive', 'neutral', 'negative', 'other']));
  const topicCats = [...new Set(posts.filter((post) => post.topic_id !== null).map((post) => `Topic ${post.topic_id}`))].slice(0, 8);
  safeChart('topicBrandChart', () => drawStackedShare(el('topicBrandChart'), new Map([...groupBy(posts, (post) => post.brand).entries()].map(([brand, rows]) => [brand, rows.map((post) => ({ category: post.topic_id === null ? 'Unknown' : `Topic ${post.topic_id}` }))])), topicCats));
  renderTopicShareLegend(posts, topicCats);
}

function renderTopicShareLegend(posts, topicCats) {
  const container = el('topicShareLegend');
  if (!container) return;
  if (!posts.length || !topicCats.length) {
    container.innerHTML = '<div class="empty">No data available for this section</div>';
    return;
  }
  const total = posts.filter((post) => post.topic_id !== null).length || 1;
  container.innerHTML = topicCats.map((topicLabel, index) => {
    const id = Number(String(topicLabel).replace('Topic ', ''));
    const rows = posts.filter((post) => post.topic_id === id);
    const terms = rows.find((post) => post.topic_terms?.length)?.topic_terms?.slice(0, 4) || [];
    return `<span class="topic-share-chip" style="--topic-color:${colorAt(index)}">
      <strong>${escapeHtml(topicLabel)}</strong>
      <em>${percentFmt.format(rows.length / total)} / ${fmt.format(rows.length)} posts</em>
      <small>${escapeHtml(terms.join(', ') || 'no terms')}</small>
    </span>`;
  }).join('');
}

function drawGroupedBars(canvas, labels, series) {
  if (!labels.length || !series.length) return drawEmptyChart(canvas, 'No data available for this section');
  const { ctx, width, height } = setupCanvas(canvas, Number(canvas.getAttribute('height')) || 260);
  const compact = width < 420;
  const pad = { top: 18, right: 14, bottom: compact ? 54 : 42, left: compact ? 42 : 64 };
  const chartW = width - pad.left - pad.right;
  const chartH = height - pad.top - pad.bottom;
  const max = Math.max(...series.flatMap((row) => row.values), 1);
  const groupW = chartW / labels.length;
  const barW = Math.max(3, (groupW - 8) / series.length);
  const points = [];
  drawGrid(ctx, pad, width, height, max, compact ? 2 : 4);
  labels.forEach((label, i) => {
    series.forEach((row, j) => {
      const value = row.values[i] || 0;
      const x = pad.left + i * groupW + 4 + j * barW;
      const barH = (value / max) * chartH;
      const y = pad.top + chartH - barH;
      ctx.fillStyle = row.color;
      ctx.fillRect(x, y, Math.max(2, barW - 2), barH);
      points.push({ x, y, w: barW, h: Math.max(8, barH), text: `${row.label} ${label}: ${formatEngagement(Math.round(value))}` });
    });
    ctx.fillStyle = '#64748B';
    ctx.font = canvasFont(width, 12);
    ctx.textAlign = 'center';
    ctx.fillText(shortLabel(label, compact ? 7 : 10), pad.left + i * groupW + groupW / 2, height - 14);
  });
  state.charts[canvas.id] = { type: 'bar', points };
}

function drawLineChart(canvas, rows, series) {
  if (!rows.length || !series.length) return drawEmptyChart(canvas, 'No data available for this section');
  const { ctx, width, height } = setupCanvas(canvas, Number(canvas.getAttribute('height')) || 260);
  const compact = width < 420;
  const pad = { top: 18, right: 18, bottom: compact ? 48 : 42, left: compact ? 42 : 64 };
  const chartW = width - pad.left - pad.right;
  const chartH = height - pad.top - pad.bottom;
  const max = Math.max(...rows.flatMap((row) => series.map((s) => row[s.key] || 0)), 1);
  const points = [];
  drawGrid(ctx, pad, width, height, max, compact ? 2 : 4);
  series.forEach((s) => {
    ctx.strokeStyle = s.color;
    ctx.lineWidth = 2;
    ctx.beginPath();
    rows.forEach((row, index) => {
      const x = pad.left + (rows.length === 1 ? chartW / 2 : (chartW / (rows.length - 1)) * index);
      const y = pad.top + chartH - ((row[s.key] || 0) / max) * chartH;
      if (index === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
      points.push({ x: x - 8, y: y - 8, w: 16, h: 16, text: `${s.label} ${row.label}: ${formatEngagement(row[s.key] || 0)}` });
    });
    ctx.stroke();
  });
  ctx.fillStyle = '#64748B';
  ctx.font = canvasFont(width, 12);
  ctx.textAlign = 'center';
  const step = Math.max(1, Math.ceil(rows.length / (compact ? 4 : 7)));
  rows.forEach((row, index) => {
    if (index % step !== 0 && index !== rows.length - 1) return;
    const x = pad.left + (rows.length === 1 ? chartW / 2 : (chartW / (rows.length - 1)) * index);
    ctx.fillText(shortLabel(row.label, compact ? 7 : 10), x, height - 14);
  });
  state.charts[canvas.id] = { type: 'bar', points };
}

function renderModelFreeEvidence(posts) {
  renderEvidence(posts);
  renderChartInsights(posts);
  const brandRows = [...groupBy(posts, (post) => post.brand).entries()].map(([label, rows]) => {
    const values = rows.map((post) => post.total_engagement).sort((a, b) => a - b);
    return { label, value: average(values), median: median(values), iqr: percentile(values, 0.75) - percentile(values, 0.25) };
  });
  safeChart('brandEngagementChart', () => drawHorizontalBars(el('brandEngagementChart'), brandRows));
  const brandRawStats = el('brandRawStats');
  if (brandRawStats) {
    brandRawStats.innerHTML = brandRows.length
      ? brandRows.map((row) => `<span>${escapeHtml(row.label)} mean ${formatEngagement(Math.round(row.value))} / median ${formatEngagement(row.median)} / IQR ${formatEngagement(Math.round(row.iqr))}</span>`).join('')
      : '<span>No data available for this section</span>';
  }
  const sentiments = ['positive', 'neutral', 'negative', 'other'].filter((sentiment) => posts.some((post) => sentimentBucket(post.sentiment_label) === sentiment));
  const brandEntries = [...groupBy(posts, (post) => post.brand).entries()];
  const sentimentSeries = brandEntries.map(([brand, rows], index) => ({
    label: brand,
    color: index === 0 ? '#E2231A' : '#111827',
    values: sentiments.map((sentiment) => average(rows.filter((post) => sentimentBucket(post.sentiment_label) === sentiment).map((post) => post.total_engagement)))
  }));
  safeChart('sentimentEngagementChart', () => drawGroupedBars(el('sentimentEngagementChart'), sentiments, sentimentSeries));
  safeChart('sentimentHeatmapChart', () => drawHeatmap(el('sentimentHeatmapChart'), groupBy(posts, (post) => sentimentBucket(post.sentiment_label)), [['likes', (p) => p.likes_count], ['replies', (p) => p.replies_count], ['retweets', (p) => p.retweets_count], ['quotes', (p) => p.quotes_count]]));
  const byDate = [...groupBy(posts, (post) => post.date_iso).entries()].filter(([date]) => date).sort((a, b) => a[0].localeCompare(b[0])).slice(-24);
  const dailyRows = byDate.map(([date, rows]) => {
    const item = { label: date.slice(5) };
    brandEntries.forEach(([brand]) => { item[brand] = rows.filter((post) => post.brand === brand).length; });
    return item;
  });
  safeChart('dailyVolumeChart', () => drawLineChart(el('dailyVolumeChart'), dailyRows, brandEntries.map(([brand], index) => ({ key: brand, label: brand, color: index === 0 ? '#E2231A' : '#111827' }))));
  renderTopicRanking(posts);
  renderViralEvidence(posts);
}

function renderTopicRanking(posts) {
  const rows = [...groupBy(posts.filter((post) => post.topic_id !== null), (post) => `Topic ${post.topic_id}`).entries()].map(([topic, items]) => ({ topic, count: items.length, avg: average(items.map((p) => p.total_engagement)), med: median(items.map((p) => p.total_engagement)), sentiment: topEntry(groupBy(items, (p) => sentimentBucket(p.sentiment_label)).entries(), ([, r]) => r.length)?.[0] || '-', reps: [...items].sort((a,b)=>b.total_engagement-a.total_engagement).slice(0,3) })).sort((a,b)=>b.med-a.med).slice(0,12);
  safeChart('topicRankingChart', () => drawHorizontalBars(el('topicRankingChart'), rows.slice(0, 8).map((row) => ({ label: row.topic, value: row.med }))));
  el('topicRankingTable').innerHTML = rows.length ? `<table><thead><tr><th>Topic</th><th>Posts</th><th>Avg</th><th>Median</th><th>Sentiment</th><th>Top posts</th></tr></thead><tbody>${rows.slice(0, 6).map((r)=>`<tr><td>${r.topic}</td><td>${fmt.format(r.count)}</td><td>${fmt.format(Math.round(r.avg))}</td><td>${fmt.format(r.med)}</td><td>${escapeHtml(r.sentiment)}</td><td>${r.reps.map((p)=>`<a href="${p.tweet_url}" target="_blank" rel="noreferrer">${fmt.format(p.total_engagement)}</a>`).join(' ')}</td></tr>`).join('')}</tbody></table>` : '<div class="empty">No data available for this section</div>';
}

function renderViralEvidence(posts) {
  const viral = posts.filter((post) => post.is_viral).sort((a,b)=>b.total_engagement-a.total_engagement).slice(0,15);
  const viralAvg = average(posts.filter((p)=>p.is_viral).map((p)=>p.total_engagement));
  const nonAvg = average(posts.filter((p)=>!p.is_viral).map((p)=>p.total_engagement));
  const summary = `<div class="mini-summary"><span>Viral avg ${fmt.format(Math.round(viralAvg))}</span><span>Non-viral avg ${fmt.format(Math.round(nonAvg))}</span></div>`;
  el('viralEvidenceTable').innerHTML = viral.length ? summary + `<table><thead><tr><th>Brand</th><th>Date</th><th>Sentiment</th><th>Topic</th><th>Total</th><th>Post</th></tr></thead><tbody>${viral.map((p)=>`<tr><td>${escapeHtml(p.brand)}</td><td>${escapeHtml(p.date_iso)}</td><td>${escapeHtml(p.sentiment_label)}</td><td>${p.topic_id === null ? 'unknown' : `Topic ${p.topic_id}`}</td><td>${fmt.format(p.total_engagement)}</td><td><a href="${p.tweet_url}" target="_blank" rel="noreferrer">Open</a></td></tr>`).join('')}</tbody></table>` : '<div class="empty">No data available for this section</div>';
}

function renderMetrics(posts) {
  const totalEngagement = posts.reduce((sum, post) => sum + post.total_engagement, 0);
  const viralCount = posts.filter((post) => post.is_viral).length;
  const positiveCount = posts.filter((post) => sentimentBucket(post.sentiment_label) === 'positive').length;
  el('metricPosts').textContent = fmt.format(posts.length);
  el('metricRange').textContent = dateRange(posts);
  el('metricMedian').textContent = formatEngagement(median(posts.map((post) => post.total_engagement)));
  el('metricEngagement').textContent = formatEngagement(totalEngagement);
  el('metricViralShare').textContent = posts.length ? percentFmt.format(viralCount / posts.length) : '-';
  el('metricPositiveShare').textContent = posts.length ? percentFmt.format(positiveCount / posts.length) : '-';
  el('metricPostsTrend').textContent = `${fmt.format(new Set(posts.map((post) => post.brand)).size)} brand sample`;
  el('metricRangeTrend').textContent = `${fmt.format(new Set(posts.map((post) => post.date_iso).filter(Boolean)).size)} active days`;
  el('metricMedianTrend').textContent = 'less sensitive to outliers';
  el('metricEngagementTrend').textContent = `${formatEngagement(posts.length ? Math.round(totalEngagement / posts.length) : 0)} per post`;
  el('metricViralTrend').textContent = `${fmt.format(viralCount)} viral posts`;
  el('metricPositiveTrend').textContent = `${fmt.format(positiveCount)} positive posts`;
}

function renderEvidence(posts) {
  const bySentiment = new Map();
  posts.forEach((post) => bySentiment.set(post.sentiment_label, (bySentiment.get(post.sentiment_label) || 0) + 1));
  const mostCommonSentiment = [...bySentiment.entries()].sort((a, b) => b[1] - a[1])[0];
  const viralPosts = posts.filter((post) => post.is_viral);
  const topPost = [...posts].sort((a, b) => b.total_engagement - a.total_engagement)[0];
  const avgReplies = posts.length ? Math.round(posts.reduce((sum, post) => sum + numberValue(post.replies_count), 0) / posts.length) : 0;
  el('evidenceGrid').innerHTML = [
    ['Dominant Sentiment', mostCommonSentiment ? `${mostCommonSentiment[0]} (${fmt.format(mostCommonSentiment[1])})` : 'No data available for this section'],
    ['Viral Posts', posts.length ? `${fmt.format(viralPosts.length)} posts` : 'No data available for this section'],
    ['Average Replies', posts.length ? fmt.format(avgReplies) : 'No data available for this section'],
    ['Top Post Engagement', topPost ? fmt.format(topPost.total_engagement) : 'No data available for this section']
  ].map(([label, value]) => `<article class="evidence-card"><span>${label}</span><strong>${escapeHtml(value)}</strong></article>`).join('');
}

function shortLabel(value, limit = 12) {
  const text = String(value || '');
  return text.length > limit ? `${text.slice(0, limit - 1)}…` : text;
}

function drawGrid(ctx, pad, width, height, max, ticks = 4) {
  const compact = width < 420;
  const chartW = width - pad.left - pad.right;
  const chartH = height - pad.top - pad.bottom;
  ctx.strokeStyle = '#E2E8F0';
  ctx.fillStyle = '#64748B';
  ctx.font = canvasFont(width, 12);
  ctx.textAlign = 'right';
  for (let i = 0; i <= ticks; i += 1) {
    const value = (max / ticks) * i;
    const y = pad.top + chartH - (chartH / ticks) * i;
    ctx.beginPath();
    ctx.moveTo(pad.left, y);
    ctx.lineTo(pad.left + chartW, y);
    ctx.stroke();
    ctx.fillText(compact ? formatEngagement(Math.round(value)).replace('.0', '') : formatEngagement(Math.round(value)), pad.left - 5, y + 4);
  }
}

function chartHeightFor(width, requestedHeight) {
  const fluid = Math.round(width * 0.56);
  if (width < 420) return Math.max(240, Math.min(260, Math.round(width * 0.66)));
  if (width < 768) return Math.max(250, Math.min(280, fluid));
  if (width < 1200) return Math.max(280, Math.min(requestedHeight, 300));
  return Math.max(300, Math.min(requestedHeight, 320));
}

function setupCanvas(canvas, height) {
  const ctx = canvas.getContext('2d');
  const box = canvas.parentElement?.getBoundingClientRect?.();
  const measuredWidth = box?.width || canvas.clientWidth || canvas.parentElement?.clientWidth || 320;
  const width = Math.max(220, Math.floor(measuredWidth));
  const renderHeight = chartHeightFor(width, height);
  const dpr = window.devicePixelRatio || 1;
  canvas.width = width * dpr;
  canvas.height = renderHeight * dpr;
  canvas.style.height = `${renderHeight}px`;
  height = renderHeight;
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, width, height);
  return { ctx, width, height };
}

function drawEmptyChart(canvas, message) {
  const { ctx, width, height } = setupCanvas(canvas, Number(canvas.getAttribute('height')) || 220);
  ctx.fillStyle = '#64748B';
  ctx.font = canvasFont(width, 13);
  ctx.textAlign = 'center';
  ctx.fillText(message, width / 2, height / 2);
  state.charts[canvas.id] = { points: [] };
}

function drawBarChart(canvas, labels, values, color) {
  if (!values.length) {
    drawEmptyChart(canvas, 'No data available for this section');
    return;
  }
  const { ctx, width, height } = setupCanvas(canvas, Number(canvas.getAttribute('height')) || 260);
  const compact = width < 420;
  const pad = { top: 18, right: 12, bottom: compact ? 54 : 42, left: compact ? 36 : 64 };
  const chartW = Math.max(1, width - pad.left - pad.right);
  const chartH = Math.max(1, height - pad.top - pad.bottom);
  const max = Math.max(...values, 1);
  const gap = compact ? 2 : 5;
  const barW = Math.max(3, chartW / values.length - gap);
  const points = [];

  drawGrid(ctx, pad, width, height, max, compact ? 2 : 4);
  ctx.strokeStyle = '#E2E8F0';
  ctx.beginPath();
  ctx.moveTo(pad.left, pad.top + chartH);
  ctx.lineTo(pad.left + chartW, pad.top + chartH);
  ctx.stroke();

  values.forEach((value, index) => {
    const x = pad.left + index * (barW + gap);
    const barH = Math.max(value ? 2 : 0, (value / max) * chartH);
    const y = pad.top + chartH - barH;
    ctx.fillStyle = color;
    ctx.fillRect(x, y, barW, barH);
    points.push({ x, y, w: barW, h: Math.max(barH, 8), label: labels[index], value, text: `${labels[index]}: ${formatEngagement(value)}` });
  });

  ctx.fillStyle = '#64748B';
  ctx.font = canvasFont(width, 12);
  ctx.textAlign = 'center';
  const step = compact ? Math.max(1, Math.ceil(labels.length / 4)) : Math.max(1, Math.ceil(labels.length / 7));
  labels.forEach((label, index) => {
    if (index % step !== 0 && index !== labels.length - 1) return;
    const x = pad.left + index * (barW + gap) + barW / 2;
    ctx.save();
    if (compact) {
      ctx.translate(x, height - 12);
      ctx.rotate(-Math.PI / 6);
      ctx.fillText(shortLabel(label, 8), 0, 0);
    } else {
      ctx.fillText(shortLabel(label, 11), x, height - 14);
    }
    ctx.restore();
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
    points.push({ cx, cy, r: radius, start, end: start + angle, text: `${row.label}: ${formatEngagement(row.value)} (${percentFmt.format(row.value / total)})` });
    start += angle;
  });

  ctx.beginPath();
  ctx.arc(cx, cy, radius * 0.58, 0, Math.PI * 2);
  ctx.fillStyle = '#ffffff';
  ctx.fill();
  ctx.fillStyle = '#1c2427';
  ctx.font = canvasFont(width, 18, '600');
  ctx.textAlign = 'center';
  ctx.fillText(formatEngagement(total), cx, cy + 6);
  state.charts[canvas.id] = { type: 'donut', points };
}

function renderLegend(containerId, rows, groupName) {
  const container = el(containerId);
  container.innerHTML = rows.map((row) => {
    const active = row.active !== false;
    return `<button type="button" class="legend-item ${active ? 'active' : ''}" data-chart-group="${groupName}" data-series="${escapeHtml(row.label)}" aria-pressed="${active}">
      <span style="--legend-color:${row.color}"></span>${escapeHtml(row.label)}<strong>${formatEngagement(row.value)}</strong>
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
    const date = parseDate(post.date_iso || dateValue(post));
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
    { label: 'Likes', value: posts.reduce((s, p) => s + p.likes_count, 0), color: '#E2231A' },
    { label: 'Replies', value: posts.reduce((s, p) => s + p.replies_count, 0), color: '#2563EB' },
    { label: 'Retweets', value: posts.reduce((s, p) => s + p.retweets_count, 0), color: '#16A34A' },
    { label: 'Quotes', value: posts.reduce((s, p) => s + p.quotes_count, 0), color: '#F97316' }
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
    <p>${escapeHtml(post.text_normalized || '')}</p>
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

  const topicsHtml = matchingTopics.map((topic, index) => {
    const terms = (topic.top_terms || []).slice(0, 8).map((term) => `<span class="term">${escapeHtml(term)}</span>`).join('');
    const example = topic.representative_posts?.[0];
    const active = topic.topic_id === state.selectedTopicId ? 'active' : '';
    const scores = (topic.representative_posts || []).map((post) => numberValue(post.score));
    const strength = Math.max(0, Math.min(100, average(scores) * 100));
    const leadTerms = (topic.top_terms || []).slice(0, 3).join(' / ') || `Topic ${topic.topic_id}`;
    return `<button class="topic-item topic-button ${active}" type="button" data-topic-id="${topic.topic_id}" aria-label="Inspect topic ${topic.topic_id}" style="--topic-color:${colorAt(index)};--topic-strength:${strength}%">
      <span class="topic-title-row"><strong>Topic ${topic.topic_id}</strong><em>${strength.toFixed(1)}% representative fit</em></span>
      <span class="topic-lead">${escapeHtml(leadTerms)}</span>
      <span class="topic-strength" aria-hidden="true"><i></i></span>
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
    badge(post.humor_label === 'unknown' ? 'Humor unknown' : post.humor_label),
    badge(post.topic_id === null ? 'Topic unknown' : `Topic ${post.topic_id}`),
    badge(fmt.format(post.total_engagement), 'engagement'),
    badge(post.is_viral ? 'Viral' : 'Standard', post.is_viral ? 'viral' : '')
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

  el('postTableWrap').innerHTML = `<table class="post-table wide">
    <thead><tr><th>Brand</th><th>Date</th><th>Text</th><th>Topic</th><th>Sentiment</th><th>HSQ Humor</th><th>Likes</th><th>Replies</th><th>Retweets</th><th>Quotes</th><th>Total</th><th>Log</th><th>Viral</th><th>Length</th><th>Hashtags</th><th>Mentions</th><th>URL</th><th>Link</th></tr></thead>
    <tbody>${rows.map((post) => `<tr>
      <td>${escapeHtml(post.brand)}</td>
      <td>${escapeHtml(post.date_iso || 'unknown')}</td>
      <td>${escapeHtml(post.text_normalized || '')}</td>
      <td>${post.topic_id === null ? 'unknown' : `Topic ${post.topic_id}`}</td>
      <td>${escapeHtml(post.sentiment_label)}</td>
      <td>${escapeHtml(post.humor_label)}</td>
      <td>${fmt.format(post.likes_count)}</td>
      <td>${fmt.format(post.replies_count)}</td>
      <td>${fmt.format(post.retweets_count)}</td>
      <td>${fmt.format(post.quotes_count)}</td>
      <td>${fmt.format(post.total_engagement)}</td>
      <td>${post.log_total_engagement.toFixed(2)}</td>
      <td>${post.is_viral ? 'Viral' : 'Standard'}</td>
      <td>${fmt.format(post.text_length)}</td>
      <td>${fmt.format(post.hashtag_count)}</td>
      <td>${fmt.format(post.mention_count)}</td>
      <td>${post.has_url ? 'Yes' : 'No'}</td>
      <td><a href="${post.tweet_url}" target="_blank" rel="noreferrer">Open</a></td>
    </tr>`).join('')}</tbody>
  </table>`;

  el('postCards').innerHTML = rows.map((post) => {
    const expanded = state.expandedPosts.has(post.id);
    const textClass = expanded ? 'post-text expanded' : 'post-text';
    return `<article class="post-card">
      <div class="post-badges">${postBadges(post)}</div>
      <p class="${textClass}" id="post-text-${post.id}">${escapeHtml(post.text_normalized || '')}</p>
      <button class="text-toggle" type="button" data-post-id="${post.id}" aria-expanded="${expanded}" aria-controls="post-text-${post.id}">${expanded ? 'Show less' : 'Show more'}</button>
      <div class="metric-badges">
        ${badge(`likes ${fmt.format(numberValue(post.likes_count))}`)}
        ${badge(`replies ${fmt.format(numberValue(post.replies_count))}`)}
        ${badge(`retweets ${fmt.format(numberValue(post.retweets_count))}`)}
        ${badge(`quotes ${fmt.format(numberValue(post.quotes_count))}`)}
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
  el('brandSelect').value = state.brand;
  el('searchInput').value = state.search;
  el('dateFromInput').value = state.dateFrom;
  el('dateToInput').value = state.dateTo;
  el('viralSelect').value = state.viral;
  el('sortSelect').value = state.sort;
  el('activeFilterCount').textContent = `${countActiveFilters()} active`;
}

async function render() {
  const datasets = await loadAllAccounts();
  const dataset = datasets[state.account];
  const allPosts = buildAllEnrichedPosts(datasets);
  populateFilterOptions(allPosts, dataset);
  syncInputs();
  const visible = filteredPosts(allPosts);
  const hasErrors = Object.values(datasets).some((dataset) => dataset.errors.posts);
  if (!allPosts.length) setDatasetState(hasErrors ? 'error' : 'empty', hasErrors ? 'Failed to load dataset. Please check the data source or API response.' : 'No dataset loaded yet. Run scraper or check dataset source.');
  else setDatasetState('ready', `${fmt.format(allPosts.length)} posts loaded across ${fmt.format(Object.keys(datasets).length)} brands`);
  el('lastUpdatedLabel').textContent = `Last updated: ${latestTimestamp(datasets)}`;
  renderStatus(dataset);
  renderMetrics(visible);
  renderDescriptives(visible);
  renderModelFreeEvidence(visible);
  renderCharts(visible, state.account);
  renderTopics(dataset.lda);
  renderSentiment(dataset.sentiment);
  renderPosts(visible);

}



function setActiveNav() {
  const sections = [...document.querySelectorAll('.section-block')];
  const links = [...document.querySelectorAll('.section-nav a')];
  let current = sections[0]?.id;
  sections.forEach((section) => {
    if (section.getBoundingClientRect().top < 180) current = section.id;
  });
  links.forEach((link) => link.classList.toggle('active', link.getAttribute('href') === `#${current}`));
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


let resizeTimer = null;
function scheduleRender() {
  clearTimeout(resizeTimer);
  resizeTimer = setTimeout(() => render(), 120);
}

function observeDashboardResize() {
  const ResizeObserverCtor = window.ResizeObserver || globalThis.ResizeObserver;
  if (!ResizeObserverCtor) return;
  const observer = new ResizeObserverCtor(scheduleRender);
  document.querySelectorAll('.chart-panel').forEach((panel) => observer.observe(panel));
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
  el('brandSelect').addEventListener('change', async (event) => { state.brand = event.target.value; state.page = 1; await render(); });
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
  ['volumeChart', 'engagementChart', 'sentimentChart', 'engagementHistogram', 'brandBoxplotChart', 'postsByBrandChart', 'textLengthChart', 'sentimentBrandChart', 'topicBrandChart', 'brandEngagementChart', 'sentimentEngagementChart', 'sentimentHeatmapChart', 'dailyVolumeChart', 'topicRankingChart'].forEach((id) => bindChartTooltip(el(id)));
  window.addEventListener('resize', scheduleRender);
  window.addEventListener('scroll', setActiveNav, { passive: true });
  setActiveNav();
  if (window.innerWidth < 640) el('filterDetails').open = false;
  observeDashboardResize();
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
