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

const state = {
  account: 'wendys',
  datasets: {},
  search: '',
  year: 'all',
  sort: 'date_desc'
};

const el = (id) => document.getElementById(id);
const fmt = new Intl.NumberFormat('en-US');

function parseDate(value) {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? null : date;
}

function numberValue(value) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : 0;
}

function engagement(post) {
  return numberValue(post.favorite_count) + numberValue(post.reply_count) + numberValue(post.retweet_count) + numberValue(post.quote_count);
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

function filteredPosts(posts) {
  const query = state.search.trim().toLowerCase();
  const rows = posts.filter((post) => {
    const date = parseDate(post.created_at);
    const year = date ? String(date.getUTCFullYear()) : 'unknown';
    if (state.year !== 'all' && year !== state.year) return false;
    if (!query) return true;
    return [post.text, post.tweet_url, post.lang].some((value) => String(value || '').toLowerCase().includes(query));
  });

  rows.sort((a, b) => {
    if (state.sort === 'engagement_desc') return engagement(b) - engagement(a);
    if (state.sort === 'likes_desc') return numberValue(b.favorite_count) - numberValue(a.favorite_count);
    if (state.sort === 'replies_desc') return numberValue(b.reply_count) - numberValue(a.reply_count);
    if (state.sort === 'retweets_desc') return numberValue(b.retweet_count) - numberValue(a.retweet_count);
    return numberValue(b.id) - numberValue(a.id);
  });
  return rows;
}

function dateRange(posts) {
  const dates = posts.map((post) => parseDate(post.created_at)).filter(Boolean).sort((a, b) => a - b);
  if (!dates.length) return '-';
  const start = dates[0].toISOString().slice(0, 10);
  const end = dates[dates.length - 1].toISOString().slice(0, 10);
  return `${start} – ${end}`;
}

function populateYears(posts) {
  const select = el('yearSelect');
  const years = [...new Set(posts.map((post) => parseDate(post.created_at)).filter(Boolean).map((date) => date.getUTCFullYear()))].sort((a, b) => b - a);
  const current = state.year;
  select.innerHTML = '<option value="all">All years</option>' + years.map((year) => `<option value="${year}">${year}</option>`).join('');
  state.year = years.map(String).includes(current) ? current : 'all';
  select.value = state.year;
}

function drawBarChart(canvas, labels, values, color, formatter = (v) => fmt.format(v)) {
  const ctx = canvas.getContext('2d');
  const width = canvas.clientWidth || 600;
  const height = Number(canvas.getAttribute('height')) || 220;
  const dpr = window.devicePixelRatio || 1;
  canvas.width = width * dpr;
  canvas.height = height * dpr;
  ctx.scale(dpr, dpr);
  ctx.clearRect(0, 0, width, height);

  const pad = { top: 16, right: 16, bottom: 34, left: 44 };
  const chartW = width - pad.left - pad.right;
  const chartH = height - pad.top - pad.bottom;
  const max = Math.max(...values, 1);

  ctx.strokeStyle = '#d9e1e4';
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.moveTo(pad.left, pad.top);
  ctx.lineTo(pad.left, pad.top + chartH);
  ctx.lineTo(pad.left + chartW, pad.top + chartH);
  ctx.stroke();

  const gap = 4;
  const barW = Math.max(3, chartW / values.length - gap);
  values.forEach((value, index) => {
    const x = pad.left + index * (barW + gap);
    const barH = (value / max) * chartH;
    const y = pad.top + chartH - barH;
    ctx.fillStyle = color;
    ctx.fillRect(x, y, barW, barH);
  });

  ctx.fillStyle = '#607076';
  ctx.font = '11px system-ui, sans-serif';
  ctx.textAlign = 'left';
  ctx.fillText(formatter(max), 6, pad.top + 10);
  ctx.textAlign = 'center';
  const step = Math.max(1, Math.floor(labels.length / 6));
  labels.forEach((label, index) => {
    if (index % step !== 0 && index !== labels.length - 1) return;
    const x = pad.left + index * (barW + gap) + barW / 2;
    ctx.fillText(label, x, height - 12);
  });
}

function drawDonut(canvas, rows) {
  const ctx = canvas.getContext('2d');
  const width = canvas.clientWidth || 420;
  const height = Number(canvas.getAttribute('height')) || 220;
  const dpr = window.devicePixelRatio || 1;
  canvas.width = width * dpr;
  canvas.height = height * dpr;
  ctx.scale(dpr, dpr);
  ctx.clearRect(0, 0, width, height);

  const total = rows.reduce((sum, row) => sum + row.value, 0) || 1;
  const radius = Math.min(width, height) * 0.32;
  const cx = width * 0.35;
  const cy = height * 0.5;
  let start = -Math.PI / 2;

  rows.forEach((row) => {
    const angle = (row.value / total) * Math.PI * 2;
    ctx.beginPath();
    ctx.moveTo(cx, cy);
    ctx.arc(cx, cy, radius, start, start + angle);
    ctx.closePath();
    ctx.fillStyle = row.color;
    ctx.fill();
    start += angle;
  });

  ctx.beginPath();
  ctx.arc(cx, cy, radius * 0.58, 0, Math.PI * 2);
  ctx.fillStyle = '#ffffff';
  ctx.fill();

  ctx.fillStyle = '#1c2427';
  ctx.font = '600 18px system-ui, sans-serif';
  ctx.textAlign = 'center';
  ctx.fillText(fmt.format(total), cx, cy + 6);

  ctx.font = '12px system-ui, sans-serif';
  ctx.textAlign = 'left';
  rows.forEach((row, index) => {
    const y = 40 + index * 26;
    ctx.fillStyle = row.color;
    ctx.fillRect(width * 0.63, y - 10, 10, 10);
    ctx.fillStyle = '#607076';
    ctx.fillText(`${row.label}: ${fmt.format(row.value)}`, width * 0.63 + 16, y);
  });
}

function renderMetrics(posts) {
  const totalEngagement = posts.reduce((sum, post) => sum + engagement(post), 0);
  el('metricPosts').textContent = fmt.format(posts.length);
  el('metricRange').textContent = dateRange(posts);
  el('metricEngagement').textContent = fmt.format(totalEngagement);
  el('metricAverage').textContent = posts.length ? fmt.format(Math.round(totalEngagement / posts.length)) : '-';
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
  const values = recentLabels.map((label) => byMonth.get(label));
  el('volumeCaption').textContent = recentLabels.length ? `last ${recentLabels.length} active months` : '';
  drawBarChart(el('volumeChart'), recentLabels, values, accounts[account].color);

  const mix = [
    { label: 'Likes', value: posts.reduce((s, p) => s + numberValue(p.favorite_count), 0), color: '#d6223a' },
    { label: 'Replies', value: posts.reduce((s, p) => s + numberValue(p.reply_count), 0), color: '#227c91' },
    { label: 'Retweets', value: posts.reduce((s, p) => s + numberValue(p.retweet_count), 0), color: '#2d7d5f' },
    { label: 'Quotes', value: posts.reduce((s, p) => s + numberValue(p.quote_count), 0), color: '#b57912' }
  ];
  drawDonut(el('engagementChart'), mix);
}

function renderStatus(dataset) {
  const rows = [
    ['Posts', dataset.posts.length ? `${fmt.format(dataset.posts.length)} loaded` : 'missing', dataset.posts.length ? 'ok' : 'warn'],
    ['LDA', dataset.lda ? 'available' : 'not generated', dataset.lda ? 'ok' : 'warn'],
    ['Zero-shot', dataset.sentiment ? 'available' : 'not generated', dataset.sentiment ? 'ok' : 'warn']
  ];
  el('analysisStatus').innerHTML = rows.map(([name, value, cls]) => `<div class="status-item ${cls}"><span>${name}</span><strong>${value}</strong></div>`).join('');
}

function renderTopics(lda) {
  const container = el('topicList');
  if (!lda || !Array.isArray(lda.topics) || !lda.topics.length) {
    el('topicMeta').textContent = 'not generated';
    container.innerHTML = '<div class="empty">Run the LDA workflow to populate topic clusters and representative posts.</div>';
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
        return `<div class="coherence-row ${row.num_topics === selection.selected_num_topics ? 'selected' : ''}" style="--bar-width:${width}%">
          <span>${row.num_topics} topics</span>
          <strong>${coherence.toFixed(4)}</strong>
        </div>`;
      }).join('')}
    </div>
  </section>` : '';

  const topicsHtml = lda.topics.map((topic) => {
    const terms = (topic.top_terms || []).slice(0, 12).map((term) => `<span class="term">${escapeHtml(term)}</span>`).join('');
    const example = topic.representative_posts?.[0];
    const exampleHtml = example ? `<div class="example">${escapeHtml(example.text || '')}</div>` : '';
    return `<section class="topic-item"><h3>Topic ${topic.topic_id}</h3><div class="topic-terms">${terms}</div>${exampleHtml}</section>`;
  }).join('');

  container.innerHTML = selectionHtml + topicsHtml;
}

function renderSentiment(sentiment) {
  const summary = el('sentimentSummary');
  if (!sentiment || !sentiment.label_counts) {
    el('sentimentMeta').textContent = 'not generated';
    summary.innerHTML = '<div class="empty">Run the zero-shot sentiment workflow to populate label counts and post-level scores.</div>';
    drawDonut(el('sentimentChart'), [{ label: 'No data', value: 1, color: '#d9e1e4' }]);
    return;
  }
  el('sentimentMeta').textContent = `${fmt.format(sentiment.post_count || 0)} posts`;
  const rows = Object.entries(sentiment.label_counts).sort((a, b) => b[1] - a[1]);
  summary.innerHTML = rows.slice(0, 3).map(([label, count]) => `<div class="sentiment-card"><span>${escapeHtml(label)}</span><strong>${fmt.format(count)}</strong></div>`).join('');
  const colors = ['#2d7d5f', '#b57912', '#d6223a', '#227c91', '#607076'];
  drawDonut(el('sentimentChart'), rows.map(([label, value], index) => ({ label, value, color: colors[index % colors.length] })));
}

function renderPosts(posts) {
  const list = el('postList');
  el('postCountLabel').textContent = `${fmt.format(posts.length)} shown`;
  const rows = posts.slice(0, 120);
  if (!rows.length) {
    list.innerHTML = '<div class="empty">No posts match the current filters.</div>';
    return;
  }
  list.innerHTML = rows.map((post) => {
    const date = parseDate(post.created_at);
    const dateText = date ? date.toISOString().slice(0, 10) : 'unknown date';
    return `<article class="post-item">
      <div class="post-meta"><span>${dateText}</span><span>ID ${escapeHtml(post.id)}</span><span>${escapeHtml(post.lang || '')}</span></div>
      <div class="post-text">${escapeHtml(post.text || '')}</div>
      <div class="post-actions">
        <span>likes ${fmt.format(numberValue(post.favorite_count))}</span>
        <span>replies ${fmt.format(numberValue(post.reply_count))}</span>
        <span>retweets ${fmt.format(numberValue(post.retweet_count))}</span>
        <span>quotes ${fmt.format(numberValue(post.quote_count))}</span>
        <a href="${post.tweet_url}" target="_blank" rel="noreferrer">Open X post</a>
      </div>
    </article>`;
  }).join('');
}

function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>'"]/g, (char) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[char]));
}

async function render() {
  const dataset = await loadAccount(state.account);
  const posts = dataset.posts || [];
  populateYears(posts);
  const visible = filteredPosts(posts);
  renderStatus(dataset);
  renderMetrics(visible);
  renderCharts(visible, state.account);
  renderTopics(dataset.lda);
  renderSentiment(dataset.sentiment);
  renderPosts(visible);
  el('dataStatus').textContent = `${accounts[state.account].label}: ${fmt.format(posts.length)} posts loaded`;
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

  const payload = { kind, account, maxScrolls, analysisMaxPosts: maxPosts };
  result.textContent = `Submitting ${kind} for ${accounts[account].label}...`;
  setActionButtons(true);

  try {
    const response = await fetch('/api/dispatch', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify(payload)
    });
    const body = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(body.error || `HTTP ${response.status}`);
    }
    result.textContent = `${kind} workflow dispatched for ${accounts[account].label}. Check GitHub Actions for progress.`;
  } catch (error) {
    result.textContent = `Dispatch failed: ${error.message}`;
  } finally {
    setActionButtons(false);
  }
}

function setActionButtons(disabled) {
  ['runScrapeButton', 'runLdaButton', 'runSentimentButton'].forEach((id) => {
    const button = el(id);
    if (button) button.disabled = disabled;
  });
}

function bindEvents() {
  document.querySelectorAll('.tab').forEach((button) => {
    button.addEventListener('click', async () => {
      document.querySelectorAll('.tab').forEach((tab) => tab.classList.remove('active'));
      button.classList.add('active');
      state.account = button.dataset.account;
      state.year = 'all';
      await render();
    });
  });

  el('searchInput').addEventListener('input', async (event) => {
    state.search = event.target.value;
    await render();
  });
  el('yearSelect').addEventListener('change', async (event) => {
    state.year = event.target.value;
    await render();
  });
  el('sortSelect').addEventListener('change', async (event) => {
    state.sort = event.target.value;
    await render();
  });
  el('runScrapeButton').addEventListener('click', () => dispatchWorkflow('scrape'));
  el('runLdaButton').addEventListener('click', () => dispatchWorkflow('lda'));
  el('runSentimentButton').addEventListener('click', () => dispatchWorkflow('sentiment'));
  window.addEventListener('resize', () => render());
}

bindEvents();
render().catch((error) => {
  console.error(error);
  el('dataStatus').textContent = `Dashboard load failed: ${error.message}`;
});
