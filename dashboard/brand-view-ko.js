(function () {
  const ACCOUNTS = {
    wendys: { label: "Wendy's", ko: "Wendy's", base: 'data/wendys', color: '#E2231A' },
    cocacola: { label: 'Coca-Cola', ko: 'Coca-Cola', base: 'data/cocacola', color: '#111827' },
    moonpie: { label: 'MoonPie', ko: 'MoonPie', base: 'data/moonpie', color: '#F97316' }
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

  const QUADRANTS = [
    { key: 'Self-enhancing humor', title: '자기고양적 유머', axis: '자기 지향 × 적응적/긍정적' },
    { key: 'Affiliative humor', title: '친화적 유머', axis: '타인 지향 × 적응적/긍정적' },
    { key: 'Self-defeating humor', title: '자기패배적 유머', axis: '자기 지향 × 부적응적/부정적' },
    { key: 'Aggressive humor', title: '공격적 유머', axis: '타인 지향 × 부적응적/부정적' }
  ];

  const fmt = new Intl.NumberFormat('ko-KR');
  const compact = new Intl.NumberFormat('ko-KR', { notation: 'compact', maximumFractionDigits: 1 });
  const pct = new Intl.NumberFormat('ko-KR', { style: 'percent', maximumFractionDigits: 1 });
  const score = new Intl.NumberFormat('ko-KR', { maximumFractionDigits: 3 });
  let cache = null;
  let latestKey = null;

  function n(value) {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : 0;
  }

  function compactValue(value) {
    return Math.abs(n(value)) >= 1000 ? compact.format(n(value)) : fmt.format(Math.round(n(value)));
  }

  function textOf(post) {
    return String((post && (post.text || post.content || post.tweet_text || post.post_text)) || '');
  }

  function dateOf(post) {
    return (post && (post.date || post.created_at || post.timestamp)) || '';
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
    return date ? date.toISOString().slice(0, 7) : '미상';
  }

  function engagement(post) {
    return n(post && (post.likes || post.like_count || post.favorite_count)) +
      n(post && (post.replies || post.reply_count)) +
      n(post && (post.retweets || post.retweet_count || post.reposts)) +
      n(post && (post.quotes || post.quote_count));
  }

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

  function groupCount(rows, getter) {
    const map = new Map();
    rows.forEach((row) => {
      const key = getter(row) || 'unknown';
      if (!map.has(key)) map.set(key, []);
      map.get(key).push(row);
    });
    return Array.from(map.entries()).map(([key, grouped]) => ({ key, rows: grouped, value: grouped.length })).sort((a, b) => b.value - a.value);
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
    const lda = await readJson(`${account.base}/lda_topics.json`) || {};

    const sentimentById = new Map((sentiment.posts || []).map((row) => [String(row.id), row]));
    const humorById = new Map((humor.posts || []).map((row) => [String(row.id), row]));
    const topicById = new Map();
    (lda.topics || []).forEach((topic) => {
      (topic.representative_posts || []).forEach((post) => {
        topicById.set(String(post.id), {
          id: topic.topic_id,
          terms: topic.top_terms || [],
          score: n(post.score)
        });
      });
    });

    return posts.map((post) => {
      const id = String(post.id);
      const sentimentRow = sentimentById.get(id) || {};
      const humorRow = humorById.get(id) || {};
      const topicRow = topicById.get(id) || null;
      return {
        id,
        account: key,
        brand: account.ko,
        color: account.color,
        text: textOf(post),
        date: isoDate(dateOf(post)),
        month: monthKey(dateOf(post)),
        url: post.tweet_url || post.url || '',
        engagement: engagement(post),
        sentiment: sentimentRow.top_label || 'unknown',
        sentimentScore: n(sentimentRow.top_score),
        humor: humorRow.top_label || 'unknown',
        humorScore: n(humorRow.top_score),
        topic: topicRow ? topicRow.id : null,
        topicTerms: topicRow ? topicRow.terms : []
      };
    });
  }

  async function loadAll() {
    if (cache) return cache;
    const entries = await Promise.all(Object.keys(ACCOUNTS).map(async (key) => [key, await loadAccount(key)]));
    cache = Object.fromEntries(entries);
    return cache;
  }

  function getSelectedKey() {
    const active = document.querySelector('.tabs button.on');
    const label = active ? active.textContent.trim() : '전체 브랜드';
    if (label.includes('Wendy')) return 'wendys';
    if (label.includes('Coca')) return 'cocacola';
    if (label.includes('Moon')) return 'moonpie';
    return 'all';
  }

  function summary(rows) {
    const topHumor = groupCount(rows, (row) => row.humor).filter((row) => row.key !== 'unknown')[0];
    const topSentiment = groupCount(rows, (row) => row.sentiment).filter((row) => row.key !== 'unknown')[0];
    return {
      posts: rows.length,
      totalEngagement: rows.reduce((sum, row) => sum + row.engagement, 0),
      medianEngagement: median(rows.map((row) => row.engagement)),
      avgHumorScore: average(rows.map((row) => row.humorScore)),
      dominantHumor: topHumor ? HUMOR_KO[topHumor.key] || topHumor.key : '미분류',
      dominantSentiment: topSentiment ? SENTIMENT_KO[topSentiment.key] || topSentiment.key : '미분류'
    };
  }

  function el(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text != null) node.textContent = text;
    return node;
  }

  function card(label, value, help) {
    const node = el('article', 'brand-unit-metric');
    node.appendChild(el('span', '', label));
    node.appendChild(el('strong', '', value));
    if (help) node.appendChild(el('small', '', help));
    return node;
  }

  function barBlock(title, rows, options) {
    const panel = el('article', 'brand-unit-panel');
    panel.appendChild(el('h3', '', title));
    if (!rows.length) {
      panel.appendChild(el('div', 'brand-unit-empty', '사용 가능한 데이터가 없습니다.'));
      return panel;
    }
    const max = Math.max(...rows.map((row) => row.value), 1);
    rows.forEach((row) => {
      const line = el('div', 'brand-unit-bar');
      const meta = el('div', 'brand-unit-bar-meta');
      meta.appendChild(el('span', '', row.label));
      meta.appendChild(el('b', '', options && options.percent ? pct.format(row.value) : compactValue(row.value)));
      const track = el('div', 'brand-unit-track');
      const fill = el('i');
      fill.style.width = `${Math.max(2, row.value / max * 100)}%`;
      if (row.color) fill.style.background = row.color;
      track.appendChild(fill);
      line.appendChild(meta);
      line.appendChild(track);
      panel.appendChild(line);
    });
    return panel;
  }

  function twoByTwo(rows) {
    const panel = el('article', 'brand-unit-panel brand-unit-wide');
    panel.appendChild(el('h3', '', '유머 유형 2×2 분포도'));
    const note = el('p', 'brand-unit-note', '가로축은 자기 지향-타인 지향, 세로축은 적응적/긍정적-부적응적/부정적 기준입니다.');
    panel.appendChild(note);
    const grid = el('div', 'humor-matrix');
    QUADRANTS.forEach((quad) => {
      const scoped = rows.filter((row) => row.humor === quad.key);
      const cell = el('div', `humor-cell ${quad.key === 'Aggressive humor' ? 'danger' : ''}`);
      cell.appendChild(el('span', 'humor-axis', quad.axis));
      cell.appendChild(el('strong', '', quad.title));
      cell.appendChild(el('b', '', `${fmt.format(scoped.length)}개 · ${pct.format(rows.length ? scoped.length / rows.length : 0)}`));
      cell.appendChild(el('small', '', `중앙값 참여도 ${compactValue(median(scoped.map((row) => row.engagement)))} · 평균 점수 ${score.format(average(scoped.map((row) => row.humorScore)))}`));
      grid.appendChild(cell);
    });
    panel.appendChild(grid);
    return panel;
  }

  function postList(title, rows) {
    const panel = el('article', 'brand-unit-panel brand-unit-wide');
    panel.appendChild(el('h3', '', title));
    const list = el('div', 'brand-unit-posts');
    rows.slice(0, 5).forEach((row) => {
      const link = document.createElement(row.url ? 'a' : 'div');
      link.className = 'brand-unit-post';
      if (row.url) {
        link.href = row.url;
        link.target = '_blank';
        link.rel = 'noreferrer';
      }
      link.appendChild(el('b', '', `${row.brand} · ${row.date || '날짜 미상'} · 참여도 ${compactValue(row.engagement)}`));
      link.appendChild(el('span', '', row.text || '(본문 없음)'));
      link.appendChild(el('small', '', `${SENTIMENT_KO[row.sentiment] || row.sentiment} · ${HUMOR_KO[row.humor] || row.humor} · ${row.topic === null ? '토픽 없음' : `토픽 ${row.topic}`}`));
      list.appendChild(link);
    });
    if (!rows.length) list.appendChild(el('div', 'brand-unit-empty', '사용 가능한 데이터가 없습니다.'));
    panel.appendChild(list);
    return panel;
  }

  function renderBrand(container, key, rows) {
    const s = summary(rows);
    const section = el('section', 'brand-unit-section');
    section.id = 'brand-unit-view';
    section.appendChild(el('span', 'brand-unit-kicker', '브랜드 단위 시각화'));
    section.appendChild(el('h2', '', `${ACCOUNTS[key].ko} 분석 결과`));
    section.appendChild(el('p', 'brand-unit-subtitle', '선택한 브랜드 탭에서는 모든 분석이 해당 브랜드 게시물만을 기준으로 계산됩니다.'));

    const metrics = el('div', 'brand-unit-metrics');
    metrics.appendChild(card('게시물 수', fmt.format(s.posts), '현재 브랜드 기준'));
    metrics.appendChild(card('총 참여도', compactValue(s.totalEngagement), '좋아요·답글·리트윗·인용 합계'));
    metrics.appendChild(card('중앙값 참여도', compactValue(s.medianEngagement), '극단값 영향을 줄인 대표 반응'));
    metrics.appendChild(card('주요 감성', s.dominantSentiment, '최빈 감성 라벨'));
    metrics.appendChild(card('주요 유머', s.dominantHumor, '최빈 HSQ 유머 유형'));
    metrics.appendChild(card('평균 유머 점수', score.format(s.avgHumorScore), 'zero-shot confidence 평균'));
    section.appendChild(metrics);

    const panels = el('div', 'brand-unit-grid');
    panels.appendChild(barBlock('월별 게시량', groupCount(rows, (row) => row.month).filter((row) => row.key !== '미상').slice(0, 12).reverse().map((row) => ({ label: row.key, value: row.value }))));
    panels.appendChild(barBlock('월별 참여도', groupCount(rows, (row) => row.month).filter((row) => row.key !== '미상').slice(0, 12).reverse().map((row) => ({ label: row.key, value: row.rows.reduce((sum, item) => sum + item.engagement, 0) }))));
    panels.appendChild(barBlock('감성 분포', groupCount(rows, (row) => row.sentiment).map((row) => ({ label: SENTIMENT_KO[row.key] || row.key, value: rows.length ? row.value / rows.length : 0 })), { percent: true }));
    panels.appendChild(barBlock('토픽 분포', groupCount(rows.filter((row) => row.topic !== null), (row) => `토픽 ${row.topic}`).slice(0, 8).map((row) => ({ label: row.key, value: row.value }))));
    panels.appendChild(twoByTwo(rows));
    panels.appendChild(postList('브랜드 내 참여도 상위 게시물', rows.slice().sort((a, b) => b.engagement - a.engagement)));
    section.appendChild(panels);
    container.appendChild(section);
  }

  function renderAll(container, data) {
    const rows = Object.entries(ACCOUNTS).map(([key, account]) => {
      const scoped = data[key] || [];
      const s = summary(scoped);
      return { label: account.ko, color: account.color, posts: scoped.length, engagement: s.totalEngagement, median: s.medianEngagement, humor: s.dominantHumor };
    });
    const section = el('section', 'brand-unit-section');
    section.id = 'brand-unit-view';
    section.appendChild(el('span', 'brand-unit-kicker', '전체 브랜드 비교'));
    section.appendChild(el('h2', '', '브랜드별 분석 요약'));
    section.appendChild(el('p', 'brand-unit-subtitle', '전체 브랜드 탭에서는 브랜드 간 게시량, 참여도, 유머 유형 차이를 비교합니다.'));
    const panels = el('div', 'brand-unit-grid');
    panels.appendChild(barBlock('브랜드별 게시물 수', rows.map((row) => ({ label: row.label, value: row.posts, color: row.color }))));
    panels.appendChild(barBlock('브랜드별 총 참여도', rows.map((row) => ({ label: row.label, value: row.engagement, color: row.color }))));
    panels.appendChild(barBlock('브랜드별 중앙값 참여도', rows.map((row) => ({ label: row.label, value: row.median, color: row.color }))));
    const table = el('article', 'brand-unit-panel');
    table.appendChild(el('h3', '', '브랜드별 주요 유머 유형'));
    rows.forEach((row) => table.appendChild(el('p', 'brand-unit-row-text', `${row.label}: ${row.humor}`)));
    panels.appendChild(table);
    section.appendChild(panels);
    container.appendChild(section);
  }

  async function render() {
    const content = document.querySelector('.content');
    if (!content) return;
    const old = document.getElementById('brand-unit-view');
    if (old) old.remove();
    const key = getSelectedKey();
    if (key === latestKey && old) return;
    latestKey = key;
    const data = await loadAll();
    const target = document.getElementById('advanced') || document.getElementById('status') || content.firstElementChild;
    const holder = document.createElement('div');
    if (key === 'all') renderAll(holder, data);
    else renderBrand(holder, key, data[key] || []);
    const section = holder.firstElementChild;
    if (target) content.insertBefore(section, target);
    else content.appendChild(section);
  }

  function scheduleRender() {
    window.requestAnimationFrame(() => render().catch((error) => console.error('brand-view-ko render failed', error)));
  }

  function injectStyle() {
    if (document.getElementById('brand-view-ko-style')) return;
    const style = document.createElement('style');
    style.id = 'brand-view-ko-style';
    style.textContent = `
      .brand-unit-section { scroll-margin-top: 150px; display: grid; gap: 12px; }
      .brand-unit-kicker { color: var(--blue); font-size: 12px; font-weight: 900; letter-spacing: .08em; text-transform: uppercase; }
      .brand-unit-section h2 { font-size: clamp(19px, 2.2vw, 26px); line-height: 1.2; letter-spacing: -.03em; }
      .brand-unit-subtitle, .brand-unit-note, .brand-unit-row-text { color: var(--secondary); font-size: 13px; line-height: 1.5; }
      .brand-unit-metrics { display: grid; grid-template-columns: repeat(6, minmax(0, 1fr)); gap: 14px; }
      .brand-unit-metric, .brand-unit-panel { border: 1px solid var(--line); border-radius: 22px; background: var(--surface); box-shadow: var(--shadow); }
      .brand-unit-metric { min-height: 108px; padding: 16px; }
      .brand-unit-metric span { display: block; margin-bottom: 8px; color: var(--muted); font-size: 12px; font-weight: 800; }
      .brand-unit-metric strong { display: block; font-size: clamp(18px, 2vw, 24px); line-height: 1.12; letter-spacing: -.03em; }
      .brand-unit-metric small { display: block; margin-top: 8px; color: var(--secondary); font-size: 12px; line-height: 1.35; }
      .brand-unit-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 18px; }
      .brand-unit-panel { padding: 18px; min-width: 0; }
      .brand-unit-wide { grid-column: 1 / -1; }
      .brand-unit-panel h3 { margin: 0 0 14px; font-size: 16px; letter-spacing: -.02em; }
      .brand-unit-bar { display: grid; gap: 6px; margin-bottom: 11px; }
      .brand-unit-bar-meta { display: flex; align-items: baseline; justify-content: space-between; gap: 10px; color: var(--secondary); font-size: 12px; font-weight: 800; }
      .brand-unit-track { height: 12px; overflow: hidden; border-radius: 999px; background: var(--surface-2); }
      .brand-unit-track i { display: block; height: 100%; border-radius: 999px; background: linear-gradient(90deg, var(--blue), #60a5fa); }
      .humor-matrix { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; margin-top: 12px; }
      .humor-cell { display: grid; gap: 7px; min-height: 132px; padding: 16px; border: 1px solid var(--line); border-radius: 18px; background: var(--surface-2); }
      .humor-cell.danger { border-color: rgba(220, 38, 38, .35); background: #fff7f7; }
      .humor-axis { color: var(--muted); font-size: 11px; font-weight: 900; }
      .humor-cell strong { font-size: 17px; }
      .humor-cell b { font-size: 14px; }
      .humor-cell small { color: var(--secondary); line-height: 1.4; }
      .brand-unit-posts { display: grid; gap: 10px; }
      .brand-unit-post { display: grid; gap: 5px; padding: 12px; border: 1px solid var(--line); border-radius: 16px; color: inherit; background: var(--surface-2); }
      .brand-unit-post:hover { text-decoration: none; border-color: #bfdbfe; }
      .brand-unit-post span { display: -webkit-box; overflow: hidden; -webkit-line-clamp: 2; -webkit-box-orient: vertical; line-height: 1.45; }
      .brand-unit-post small { color: var(--muted); }
      .brand-unit-empty { min-height: 100px; display: grid; place-items: center; border: 1px dashed var(--line); border-radius: 18px; color: var(--muted); background: var(--surface-2); font-weight: 800; }
      @media (max-width: 1180px) { .brand-unit-metrics { grid-template-columns: repeat(3, minmax(0, 1fr)); } }
      @media (max-width: 760px) { .brand-unit-metrics, .brand-unit-grid, .humor-matrix { grid-template-columns: 1fr; } .brand-unit-wide { grid-column: auto; } }
    `;
    document.head.appendChild(style);
  }

  injectStyle();
  document.addEventListener('click', (event) => {
    if (event.target && event.target.closest && event.target.closest('.tabs button')) {
      setTimeout(scheduleRender, 150);
    }
  });
  const observer = new MutationObserver(() => scheduleRender());
  window.addEventListener('load', scheduleRender);
  setTimeout(scheduleRender, 500);
  observer.observe(document.body, { childList: true, subtree: true });
})();
