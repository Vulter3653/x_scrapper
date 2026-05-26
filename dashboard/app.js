/* global React, ReactDOM */
(function () {
  const root = document.getElementById('root');
  if (!window.React || !window.ReactDOM) {
    root.innerHTML = '<div class="boot-error"><strong>대시보드 실행 오류</strong><span>React 또는 ReactDOM을 불러오지 못했습니다.</span></div>';
    return;
  }

  const e = React.createElement;
  const { useEffect, useMemo, useState } = React;

  const ACCOUNTS = {
    wendys: { label: "Wendy's", base: 'data/wendys', color: '#E2231A' },
    cocacola: { label: 'Coca-Cola', base: 'data/cocacola', color: '#111827' },
    moonpie: { label: 'MoonPie', base: 'data/moonpie', color: '#F97316' }
  };

  Object.values(ACCOUNTS).forEach((account) => {
    account.posts = `${account.base}/posts.json`;
    account.lda = `${account.base}/lda_topics.json`;
    account.sentiment = `${account.base}/zero_shot_sentiment.json`;
    account.humor = `${account.base}/hsq_humor_classification.json`;
    account.scrapeState = `${account.base}/scrape_state.json`;
  });

  const HUMOR_LABELS = ['Affiliative humor', 'Self-enhancing humor', 'Aggressive humor', 'Self-defeating humor', 'Non-humorous brand message'];
  const SENTIMENT_LABELS = ['positive', 'neutral', 'negative', 'unknown'];
  const HUMOR_KO = {
    'Affiliative humor': '친화적 유머',
    'Self-enhancing humor': '자기고양적 유머',
    'Aggressive humor': '공격적 유머',
    'Self-defeating humor': '자기패배적 유머',
    'Non-humorous brand message': '비유머 브랜드 메시지',
    unknown: '미분류'
  };
  const SENTIMENT_KO = { positive: '긍정', neutral: '중립', negative: '부정', unknown: '미분류' };
  const QUADRANTS = [
    { key: 'Self-enhancing humor', title: '자기고양적 유머', axis: '자기 지향 × 적응적/긍정적' },
    { key: 'Affiliative humor', title: '친화적 유머', axis: '타인 지향 × 적응적/긍정적' },
    { key: 'Self-defeating humor', title: '자기패배적 유머', axis: '자기 지향 × 부적응적/부정적' },
    { key: 'Aggressive humor', title: '공격적 유머', axis: '타인 지향 × 부적응적/부정적' }
  ];

  const fmt = new Intl.NumberFormat('ko-KR');
  const compact = new Intl.NumberFormat('ko-KR', { notation: 'compact', maximumFractionDigits: 1 });
  const pct = new Intl.NumberFormat('ko-KR', { style: 'percent', maximumFractionDigits: 1 });
  const scoreFmt = new Intl.NumberFormat('ko-KR', { maximumFractionDigits: 3 });

  const n = (value) => Number.isFinite(Number(value)) ? Number(value) : 0;
  const cv = (value) => Math.abs(n(value)) >= 1000 ? compact.format(n(value)) : fmt.format(Math.round(n(value)));
  const textOf = (post) => String((post && (post.text || post.content || post.tweet_text || post.post_text)) || '');
  const dateOf = (post) => (post && (post.date || post.created_at || post.timestamp)) || '';
  const parseDate = (value) => {
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? null : date;
  };
  const isoDate = (value) => {
    const date = parseDate(value);
    return date ? date.toISOString().slice(0, 10) : '';
  };
  const monthKey = (value) => {
    const date = parseDate(value);
    return date ? date.toISOString().slice(0, 7) : '미상';
  };
  const likes = (post) => n(post && (post.likes || post.like_count || post.favorite_count));
  const replies = (post) => n(post && (post.replies || post.reply_count));
  const retweets = (post) => n(post && (post.retweets || post.retweet_count || post.reposts));
  const quotes = (post) => n(post && (post.quotes || post.quote_count));
  const engagement = (post) => likes(post) + replies(post) + retweets(post) + quotes(post);

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

  function percentile(values, ratio) {
    const arr = values.map(n).filter(Number.isFinite).sort((a, b) => a - b);
    if (!arr.length) return 0;
    return arr[Math.min(arr.length - 1, Math.max(0, Math.ceil(arr.length * ratio) - 1))];
  }

  function groupRows(rows, getter) {
    const map = new Map();
    rows.forEach((row) => {
      const key = getter(row) || 'unknown';
      if (!map.has(key)) map.set(key, []);
      map.get(key).push(row);
    });
    return map;
  }

  function counts(rows, getter) {
    return Array.from(groupRows(rows, getter).entries())
      .map(([key, grouped]) => ({ key, rows: grouped, value: grouped.length }))
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

  function enrich(accountKey, dataset) {
    const config = ACCOUNTS[accountKey];
    const sentimentById = new Map(((dataset.sentiment && dataset.sentiment.posts) || []).map((row) => [String(row.id), row]));
    const humorById = new Map(((dataset.humor && dataset.humor.posts) || []).map((row) => [String(row.id), row]));
    const topicById = new Map();
    ((dataset.lda && dataset.lda.topics) || []).forEach((topic) => {
      (topic.representative_posts || []).forEach((post) => {
        topicById.set(String(post.id), { id: topic.topic_id, terms: topic.top_terms || [], score: n(post.score) });
      });
    });
    const viralThreshold = percentile((dataset.posts || []).map(engagement), 0.95);
    return (dataset.posts || []).map((post) => {
      const id = String(post.id);
      const sentiment = sentimentById.get(id) || {};
      const humor = humorById.get(id) || {};
      const topic = topicById.get(id) || null;
      const text = textOf(post);
      const total = engagement(post);
      return Object.assign({}, post, {
        id,
        account: accountKey,
        brand: config.label,
        brand_color: config.color,
        date_iso: isoDate(dateOf(post)),
        month_key: monthKey(dateOf(post)),
        text_normalized: text,
        likes_count: likes(post),
        replies_count: replies(post),
        retweets_count: retweets(post),
        quotes_count: quotes(post),
        total_engagement: total,
        text_length: text.length,
        word_count: text.trim().split(/\s+/).filter(Boolean).length,
        has_url: /(https?:\/\/|www\.)/i.test(text),
        hashtag_count: (text.match(/(^|\s)#[\p{L}\p{N}_]+/gu) || []).length,
        mention_count: (text.match(/(^|\s)@[A-Za-z0-9_]+/g) || []).length,
        sentiment_label: sentiment.top_label || 'unknown',
        sentiment_score: n(sentiment.top_score),
        humor_label: humor.top_label || 'unknown',
        humor_score: n(humor.top_score),
        topic_id: topic ? topic.id : null,
        topic_terms: topic ? topic.terms : [],
        topic_score: topic ? topic.score : 0,
        is_viral: total >= viralThreshold && total > 0
      });
    });
  }

  function computeStats(rows) {
    const total = rows.length;
    const dates = rows.map((row) => parseDate(row.date_iso)).filter(Boolean).sort((a, b) => a - b);
    const topHumor = counts(rows, (row) => row.humor_label).filter((row) => row.key !== 'unknown')[0];
    const topSentiment = counts(rows, (row) => row.sentiment_label).filter((row) => row.key !== 'unknown')[0];
    return {
      total,
      range: dates.length ? `${dates[0].toISOString().slice(0, 10)} - ${dates[dates.length - 1].toISOString().slice(0, 10)}` : '-',
      brands: new Set(rows.map((row) => row.account)).size,
      days: new Set(rows.map((row) => row.date_iso).filter(Boolean)).size,
      engagement: rows.reduce((sum, row) => sum + row.total_engagement, 0),
      avg: average(rows.map((row) => row.total_engagement)),
      med: median(rows.map((row) => row.total_engagement)),
      p95: percentile(rows.map((row) => row.total_engagement), 0.95),
      viral: total ? rows.filter((row) => row.is_viral).length / total : 0,
      pos: total ? rows.filter((row) => row.sentiment_label === 'positive').length / total : 0,
      neg: total ? rows.filter((row) => row.sentiment_label === 'negative').length / total : 0,
      humor: topHumor ? topHumor.key : '-',
      sent: topSentiment ? topSentiment.key : '-'
    };
  }

  function defaultFilters() {
    return { brand: 'all', search: '', from: '', to: '', sentiment: 'all', humor: 'all', topic: 'all', viral: 'all', minHumorScore: '0', minSentimentScore: '0', sort: 'date' };
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
      if (post.humor_score < n(filters.minHumorScore)) return false;
      if (post.sentiment_score < n(filters.minSentimentScore)) return false;
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
      return (parseDate(b.date_iso)?.getTime() || 0) - (parseDate(a.date_iso)?.getTime() || 0);
    });
    return filtered;
  }

  function csvEscape(value) {
    return `"${String(value == null ? '' : value).replace(/"/g, '""')}"`;
  }

  function downloadCsv(rows) {
    const columns = ['date_iso', 'brand', 'id', 'tweet_url', 'text_normalized', 'total_engagement', 'likes_count', 'replies_count', 'retweets_count', 'quotes_count', 'sentiment_label', 'sentiment_score', 'humor_label', 'humor_score', 'topic_id', 'topic_terms', 'is_viral'];
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
    if (!rows.length) return ['현재 필터 조건에 해당하는 게시물이 없습니다.'];
    const bestBrand = counts(rows, (row) => row.brand).map((row) => ({ key: row.key, value: median(row.rows.map((post) => post.total_engagement)), count: row.value })).sort((a, b) => b.value - a.value)[0];
    const bestHumor = counts(rows, (row) => row.humor_label).filter((row) => row.key !== 'unknown').map((row) => ({ key: row.key, value: median(row.rows.map((post) => post.total_engagement)), count: row.value })).sort((a, b) => b.value - a.value)[0];
    const aggressive = rows.filter((row) => row.humor_label === 'Aggressive humor');
    const unknownHumor = rows.filter((row) => row.humor_label === 'unknown').length / rows.length;
    const out = [];
    if (bestBrand) out.push(`현재 보기에서 ${bestBrand.key}의 중앙값 참여도가 가장 높습니다(${cv(bestBrand.value)}, ${fmt.format(bestBrand.count)}개 게시물 기준).`);
    if (bestHumor) out.push(`현재 보기의 HSQ 유머 유형 중 ${HUMOR_KO[bestHumor.key] || bestHumor.key}의 중앙값 참여도가 가장 높습니다(${cv(bestHumor.value)}).`);
    out.push(`현재 표시된 게시물 중 부정 감성 비중은 ${pct.format(rows.filter((row) => row.sentiment_label === 'negative').length / rows.length)}입니다.`);
    out.push(`현재 표시된 게시물 중 공격적 유머 비중은 ${pct.format(aggressive.length / rows.length)}이며, 중앙값 참여도는 ${cv(median(aggressive.map((post) => post.total_engagement)))}입니다.`);
    if (unknownHumor > 0.1) out.push(`유머 분류 커버리지 점검이 필요합니다. 현재 표시된 게시물 중 ${pct.format(unknownHumor)}가 유머 미분류 상태입니다.`);
    return out;
  }

  function qualityRows(rows) {
    const total = rows.length || 1;
    return [
      ['본문 누락', fmt.format(rows.filter((row) => !row.text_normalized.trim()).length), pct.format(rows.filter((row) => !row.text_normalized.trim()).length / total)],
      ['감성 미분류', fmt.format(rows.filter((row) => row.sentiment_label === 'unknown').length), pct.format(rows.filter((row) => row.sentiment_label === 'unknown').length / total)],
      ['유머 미분류', fmt.format(rows.filter((row) => row.humor_label === 'unknown').length), pct.format(rows.filter((row) => row.humor_label === 'unknown').length / total)],
      ['토픽 배정 누락', fmt.format(rows.filter((row) => row.topic_id === null).length), pct.format(rows.filter((row) => row.topic_id === null).length / total)],
      ['참여도 0', fmt.format(rows.filter((row) => row.total_engagement === 0).length), pct.format(rows.filter((row) => row.total_engagement === 0).length / total)]
    ];
  }

  function Metric({ label, value, help, tone }) {
    return e('article', { className: `metric ${tone || ''}` }, e('span', null, label), e('strong', null, value), help ? e('small', null, help) : null);
  }

  function Section({ id, kicker, title, children }) {
    return e('section', { id, className: 'section' }, e('div', { className: 'section-title' }, e('span', null, kicker), e('h2', null, title)), children);
  }

  function Bars({ rows, asPercent }) {
    if (!rows.length) return e('div', { className: 'empty' }, '사용 가능한 데이터가 없습니다.');
    const max = Math.max(...rows.map((row) => row.value), 1);
    return e('div', { className: 'bars' }, rows.map((row, index) => e('div', { className: 'bar', key: `${row.key}-${index}` },
      e('div', { className: 'bar-meta' }, e('span', { title: row.key }, row.key), e('b', null, asPercent ? pct.format(row.value) : cv(row.value))),
      e('div', { className: 'track' }, e('i', { style: { width: `${Math.max(2, row.value / max * 100)}%`, background: row.color || undefined } }))
    )));
  }

  function DataTable({ heads, rows }) {
    if (!rows.length) return e('div', { className: 'empty' }, '사용 가능한 데이터가 없습니다.');
    return e('div', { className: 'table-wrap' }, e('table', null,
      e('thead', null, e('tr', null, heads.map((head) => e('th', { key: head }, head)))),
      e('tbody', null, rows.map((row, index) => e('tr', { key: index }, row.map((cell, cellIndex) => e('td', { key: cellIndex }, cell)))))
    ));
  }

  function Header({ selected, setSelected, status, lastUpdated }) {
    const statusText = status === 'ready' ? '준비 완료' : status === 'loading' ? '로딩 중' : '오류';
    return e('header', { className: 'top' },
      e('div', null,
        e('div', { className: 'title' }, e('h1', null, 'X 브랜드 인텔리전스 대시보드'), e('em', { className: status }, statusText)),
        e('p', null, '전체 브랜드 및 브랜드별 X 게시물, 감성, 토픽, HSQ 유머 분석을 제공합니다.'),
        e('small', null, `최종 업데이트: ${lastUpdated}`),
        e('a', { className: 'review-link', href: 'review.html', 'aria-label': '수동 검토 대시보드 열기' }, '수동 검토 대시보드')
      ),
      e('nav', { className: 'tabs' },
        e('button', { className: selected === 'all' ? 'on' : '', onClick: () => setSelected('all') }, '전체 브랜드'),
        Object.entries(ACCOUNTS).map(([key, account]) => e('button', { key, className: selected === key ? 'on' : '', onClick: () => setSelected(key) }, account.label))
      )
    );
  }

  function Filters({ filters, setFilters, topics, count }) {
    const update = (key, value) => setFilters(Object.assign({}, filters, { [key]: value }));
    return e('aside', { className: 'filters' },
      e('div', { className: 'filter-head' }, e('b', null, '필터'), e('span', null, `${fmt.format(count)}개 게시물`)),
      e('label', null, '브랜드', e('select', { value: filters.brand, onChange: (event) => update('brand', event.target.value) }, e('option', { value: 'all' }, '전체 브랜드'), Object.entries(ACCOUNTS).map(([key, account]) => e('option', { key, value: key }, account.label)))),
      e('label', null, '검색', e('input', { type: 'search', value: filters.search, onChange: (event) => update('search', event.target.value), placeholder: '본문, 유머, 감성, 토픽' })),
      e('div', { className: 'two' }, e('label', null, '시작일', e('input', { type: 'date', value: filters.from, onChange: (event) => update('from', event.target.value) })), e('label', null, '종료일', e('input', { type: 'date', value: filters.to, onChange: (event) => update('to', event.target.value) }))),
      e('label', null, '감성', e('select', { value: filters.sentiment, onChange: (event) => update('sentiment', event.target.value) }, e('option', { value: 'all' }, '전체 감성'), SENTIMENT_LABELS.map((label) => e('option', { key: label, value: label }, SENTIMENT_KO[label] || label)))),
      e('label', null, 'HSQ 유머', e('select', { value: filters.humor, onChange: (event) => update('humor', event.target.value) }, e('option', { value: 'all' }, '전체 유머'), HUMOR_LABELS.map((label) => e('option', { key: label, value: label }, HUMOR_KO[label] || label)), e('option', { value: 'unknown' }, '미분류'))),
      e('label', null, '토픽', e('select', { value: filters.topic, onChange: (event) => update('topic', event.target.value) }, e('option', { value: 'all' }, '전체 토픽'), topics.map((topic) => e('option', { key: topic, value: topic }, `토픽 ${topic}`)))),
      e('label', null, '바이럴', e('select', { value: filters.viral, onChange: (event) => update('viral', event.target.value) }, e('option', { value: 'all' }, '전체 게시물'), e('option', { value: 'viral' }, '바이럴만'), e('option', { value: 'nonviral' }, '비바이럴만'))),
      e('div', { className: 'two' }, e('label', null, '최소 유머 점수', e('input', { type: 'number', min: '0', max: '1', step: '0.05', value: filters.minHumorScore, onChange: (event) => update('minHumorScore', event.target.value) })), e('label', null, '최소 감성 점수', e('input', { type: 'number', min: '0', max: '1', step: '0.05', value: filters.minSentimentScore, onChange: (event) => update('minSentimentScore', event.target.value) }))),
      e('label', null, '정렬', e('select', { value: filters.sort, onChange: (event) => update('sort', event.target.value) }, e('option', { value: 'date' }, '최신순'), e('option', { value: 'engagement' }, '참여도'), e('option', { value: 'humor' }, '유머 점수'), e('option', { value: 'sentiment' }, '감성 점수'))),
      e('button', { onClick: () => setFilters(defaultFilters()) }, '초기화')
    );
  }

  function Overview({ summary, selected }) {
    return e(Section, { id: 'overview', kicker: '핵심 요약', title: selected === 'all' ? '전체 브랜드 개요' : `${ACCOUNTS[selected].label} 개요` },
      e('div', { className: 'metrics' },
        e(Metric, { label: '총 게시물 수', value: fmt.format(summary.total), help: `${summary.brands}개 브랜드, ${summary.days}일 활동`, tone: 'red' }),
        e(Metric, { label: '수집 기간', value: summary.range, help: '게시물 작성일 기준' }),
        e(Metric, { label: '총 참여도', value: cv(summary.engagement), help: `게시물당 평균 ${cv(summary.avg)}` }),
        e(Metric, { label: '중앙값 참여도', value: cv(summary.med), help: `95백분위수 ${cv(summary.p95)}` }),
        e(Metric, { label: '바이럴 비중', value: pct.format(summary.viral), help: '참여도 상위 5% 기준' }),
        e(Metric, { label: '주요 유머 유형', value: HUMOR_KO[summary.humor] || summary.humor, help: `긍정 ${pct.format(summary.pos)} / 부정 ${pct.format(summary.neg)}`, tone: 'blue' })
      )
    );
  }

  function BrandScopeVisual({ selected, rows, allPosts }) {
    if (selected === 'all') {
      const brandRows = Object.entries(ACCOUNTS).map(([key, account]) => {
        const scoped = allPosts.filter((row) => row.account === key);
        const s = computeStats(scoped);
        return { key, account, scoped, s };
      });
      return e(Section, { id: 'brand-visual', kicker: '전체 브랜드 비교', title: '브랜드별 분석 요약' },
        e('div', { className: 'grid' },
          e('article', { className: 'panel' }, e('h3', null, '브랜드별 게시물 수'), e(Bars, { rows: brandRows.map((item) => ({ key: item.account.label, value: item.scoped.length, color: item.account.color })) })),
          e('article', { className: 'panel' }, e('h3', null, '브랜드별 총 참여도'), e(Bars, { rows: brandRows.map((item) => ({ key: item.account.label, value: item.s.engagement, color: item.account.color })) })),
          e('article', { className: 'panel' }, e('h3', null, '브랜드별 중앙값 참여도'), e(Bars, { rows: brandRows.map((item) => ({ key: item.account.label, value: item.s.med, color: item.account.color })) })),
          e('article', { className: 'panel' }, e('h3', null, '브랜드별 주요 유머 유형'), e(DataTable, { heads: ['브랜드', '주요 유머', '긍정 감성', '부정 감성'], rows: brandRows.map((item) => [item.account.label, HUMOR_KO[item.s.humor] || item.s.humor, pct.format(item.s.pos), pct.format(item.s.neg)]) }))
        )
      );
    }

    const account = ACCOUNTS[selected];
    const s = computeStats(rows);
    const monthlyPosts = counts(rows, (row) => row.month_key).filter((row) => row.key !== '미상').slice(0, 12).reverse().map((row) => ({ key: row.key, value: row.value }));
    const monthlyEngagement = counts(rows, (row) => row.month_key).filter((row) => row.key !== '미상').slice(0, 12).reverse().map((row) => ({ key: row.key, value: row.rows.reduce((sum, post) => sum + post.total_engagement, 0) }));
    const sentimentRows = counts(rows, (row) => row.sentiment_label).map((row) => ({ key: SENTIMENT_KO[row.key] || row.key, value: rows.length ? row.value / rows.length : 0 }));
    const topicRows = counts(rows.filter((row) => row.topic_id !== null), (row) => `토픽 ${row.topic_id}`).slice(0, 8).map((row) => ({ key: row.key, value: row.value }));

    return e(Section, { id: 'brand-visual', kicker: '브랜드 단위 시각화', title: `${account.label} 분석 결과` },
      e('p', { className: 'panel-copy' }, '선택한 브랜드 탭에서는 모든 분석이 해당 브랜드 게시물만을 기준으로 계산됩니다.'),
      e('div', { className: 'metrics' },
        e(Metric, { label: '브랜드 게시물 수', value: fmt.format(s.total), help: `${account.label} 기준`, tone: 'red' }),
        e(Metric, { label: '브랜드 총 참여도', value: cv(s.engagement), help: '좋아요·답글·리트윗·인용 합계' }),
        e(Metric, { label: '중앙값 참여도', value: cv(s.med), help: '극단값 영향을 줄인 대표 반응' }),
        e(Metric, { label: '주요 감성', value: SENTIMENT_KO[s.sent] || s.sent, help: '최빈 감성 라벨' }),
        e(Metric, { label: '주요 유머', value: HUMOR_KO[s.humor] || s.humor, help: '최빈 HSQ 유머 유형', tone: 'blue' }),
        e(Metric, { label: '평균 유머 점수', value: scoreFmt.format(average(rows.map((row) => row.humor_score))), help: 'zero-shot confidence 평균' })
      ),
      e('div', { className: 'grid' },
        e('article', { className: 'panel' }, e('h3', null, '월별 게시량'), e(Bars, { rows: monthlyPosts })),
        e('article', { className: 'panel' }, e('h3', null, '월별 참여도'), e(Bars, { rows: monthlyEngagement })),
        e('article', { className: 'panel' }, e('h3', null, '감성 분포'), e(Bars, { rows: sentimentRows, asPercent: true })),
        e('article', { className: 'panel' }, e('h3', null, '토픽 분포'), e(Bars, { rows: topicRows })),
        e(HumorQuadrantMatrix, { rows }),
        e('article', { className: 'panel wide' }, e('h3', null, '브랜드 내 참여도 상위 게시물'), e(PostList, { rows: rows.slice().sort((a, b) => b.total_engagement - a.total_engagement).slice(0, 5) }))
      )
    );
  }

  function HumorQuadrantMatrix({ rows }) {
    return e('article', { className: 'panel wide' },
      e('h3', null, '유머 유형 2×2 분포도'),
      e('p', { className: 'panel-copy' }, '가로축은 자기 지향-타인 지향, 세로축은 적응적/긍정적-부적응적/부정적 기준입니다.'),
      e('div', { className: 'humor-matrix' }, QUADRANTS.map((quadrant) => {
        const scoped = rows.filter((row) => row.humor_label === quadrant.key);
        return e('div', { key: quadrant.key, className: `humor-cell ${quadrant.key === 'Aggressive humor' ? 'danger' : ''}` },
          e('span', { className: 'humor-axis' }, quadrant.axis),
          e('strong', null, quadrant.title),
          e('b', null, `${fmt.format(scoped.length)}개 · ${pct.format(rows.length ? scoped.length / rows.length : 0)}`),
          e('small', null, `중앙값 참여도 ${cv(median(scoped.map((row) => row.total_engagement)))} · 평균 점수 ${scoreFmt.format(average(scoped.map((row) => row.humor_score)))}`)
        );
      }))
    );
  }

  function Status({ datasets }) {
    return e(Section, { id: 'status', kicker: '데이터 준비 상태', title: '데이터셋 상태' },
      e(DataTable, { heads: ['브랜드', '게시물', 'LDA', '감성', 'HSQ 유머'], rows: Object.entries(ACCOUNTS).map(([key, account]) => {
        const dataset = datasets[key] || {};
        return [account.label, dataset.posts && dataset.posts.length ? `${fmt.format(dataset.posts.length)}개 로드됨` : '누락', dataset.lda ? '사용 가능' : '누락', dataset.sentiment ? '사용 가능' : '누락', dataset.humor ? '사용 가능' : '누락'];
      }) })
    );
  }

  function Advanced({ rows }) {
    return e(Section, { id: 'advanced', kicker: '고급 분석', title: '인사이트, 데이터 품질 점검 및 내보내기' },
      e('div', { className: 'grid' },
        e('article', { className: 'panel' }, e('h3', null, '자동 인사이트'), e('ul', { className: 'insight-list' }, insights(rows).map((item, index) => e('li', { key: index }, item)))),
        e('article', { className: 'panel' }, e('h3', null, '데이터 품질 점검'), e(DataTable, { heads: ['점검 항목', '개수', '비중'], rows: qualityRows(rows) })),
        e('article', { className: 'panel' }, e('h3', null, '분류 신뢰도 진단'), e(DataTable, { heads: ['지표', '값'], rows: [['평균 감성 점수', scoreFmt.format(average(rows.map((row) => row.sentiment_score)))], ['평균 유머 점수', scoreFmt.format(average(rows.map((row) => row.humor_score)))], ['감성 점수 .70 이상 게시물', fmt.format(rows.filter((row) => row.sentiment_score >= 0.7).length)], ['유머 점수 .70 이상 게시물', fmt.format(rows.filter((row) => row.humor_score >= 0.7).length)]] })),
        e('article', { className: 'panel' }, e('h3', null, '현재 보기 내보내기'), e('p', { className: 'panel-copy' }, '현재 필터가 적용된 게시물 단위 데이터셋을 CSV로 다운로드합니다.'), e('button', { className: 'primary-action', disabled: !rows.length, onClick: () => downloadCsv(rows) }, '필터링 결과 CSV 다운로드')),
        e('article', { className: 'panel wide' }, e('h3', null, '참여도 상위 게시물'), e(PostList, { rows: rows.slice().sort((a, b) => b.total_engagement - a.total_engagement).slice(0, 5) }))
      )
    );
  }

  function Descriptives({ rows }) {
    const s = computeStats(rows);
    const brandRows = counts(rows, (row) => row.brand).map((row) => ({ key: row.key, value: median(row.rows.map((post) => post.total_engagement)), color: row.rows[0] && row.rows[0].brand_color }));
    return e(Section, { id: 'descriptives', kicker: '기술통계', title: '데이터셋 및 참여도 프로파일' },
      e('div', { className: 'grid' },
        e('article', { className: 'panel' }, e('h3', null, '요약'), e(DataTable, { heads: ['지표', '값'], rows: [['게시물', fmt.format(s.total)], ['수집 기간', s.range], ['총 참여도', cv(s.engagement)], ['평균 참여도', cv(s.avg)], ['중앙값 참여도', cv(s.med)], ['주요 감성', SENTIMENT_KO[s.sent] || s.sent], ['주요 유머', HUMOR_KO[s.humor] || s.humor]] })),
        e('article', { className: 'panel' }, e('h3', null, '브랜드별 중앙값 참여도'), e(Bars, { rows: brandRows }))
      )
    );
  }

  function Comparison({ rows, selected }) {
    if (selected !== 'all') return e(Section, { id: 'comparison', kicker: '브랜드 간 분석', title: '브랜드 비교' }, e('div', { className: 'empty' }, '브랜드 비교는 전체 브랜드 보기에서 표시됩니다.'));
    const items = Object.entries(ACCOUNTS).map(([key, account]) => {
      const scoped = rows.filter((row) => row.account === key);
      return { account, rows: scoped, s: computeStats(scoped) };
    });
    return e(Section, { id: 'comparison', kicker: '브랜드 간 분석', title: '브랜드 비교' },
      e('div', { className: 'grid' },
        e('article', { className: 'panel' }, e('h3', null, '브랜드별 게시물 수'), e(Bars, { rows: items.map((item) => ({ key: item.account.label, value: item.rows.length, color: item.account.color })) })),
        e('article', { className: 'panel' }, e('h3', null, '브랜드별 총 참여도'), e(Bars, { rows: items.map((item) => ({ key: item.account.label, value: item.s.engagement, color: item.account.color })) })),
        e('article', { className: 'panel wide' }, e('h3', null, '브랜드 요약'), e(DataTable, { heads: ['브랜드', '게시물', '중앙값 참여도', '긍정', '부정', '바이럴', '주요 유머'], rows: items.map((item) => [item.account.label, fmt.format(item.rows.length), cv(item.s.med), pct.format(item.s.pos), pct.format(item.s.neg), pct.format(item.s.viral), HUMOR_KO[item.s.humor] || item.s.humor]) }))
      )
    );
  }

  function Evidence({ rows }) {
    const viral = rows.filter((row) => row.is_viral);
    return e(Section, { id: 'evidence', kicker: '모델 프리 근거', title: '모형화 이전 관찰 패턴' },
      e('div', { className: 'grid' },
        e('article', { className: 'panel' }, e('h3', null, '유머 유형 → 중앙값 참여도'), e(Bars, { rows: counts(rows, (row) => row.humor_label).map((row) => ({ key: HUMOR_KO[row.key] || row.key, value: median(row.rows.map((post) => post.total_engagement)) })) })),
        e('article', { className: 'panel' }, e('h3', null, '감성 → 중앙값 참여도'), e(Bars, { rows: counts(rows, (row) => row.sentiment_label).map((row) => ({ key: SENTIMENT_KO[row.key] || row.key, value: median(row.rows.map((post) => post.total_engagement)) })) })),
        e('article', { className: 'panel' }, e('h3', null, '바이럴 게시물의 유머 구성'), e(Bars, { asPercent: true, rows: counts(viral, (row) => row.humor_label).map((row) => ({ key: HUMOR_KO[row.key] || row.key, value: viral.length ? row.value / viral.length : 0, color: row.key === 'Aggressive humor' ? '#DC2626' : undefined })) })),
        e('article', { className: 'panel' }, e('h3', null, '유머 × 감성 조합'), e(DataTable, { heads: ['조합', '게시물', '중앙값 참여도'], rows: counts(rows, (row) => `${HUMOR_KO[row.humor_label] || row.humor_label} / ${SENTIMENT_KO[row.sentiment_label] || row.sentiment_label}`).slice(0, 8).map((row) => [row.key, fmt.format(row.value), cv(median(row.rows.map((post) => post.total_engagement)))]) }))
      )
    );
  }

  function Posting({ rows }) {
    const months = counts(rows, (row) => row.month_key).filter((row) => row.key !== '미상').slice(0, 18).reverse();
    const mix = [
      { key: '좋아요', value: rows.reduce((sum, row) => sum + row.likes_count, 0) },
      { key: '답글', value: rows.reduce((sum, row) => sum + row.replies_count, 0) },
      { key: '리트윗', value: rows.reduce((sum, row) => sum + row.retweets_count, 0) },
      { key: '인용', value: rows.reduce((sum, row) => sum + row.quotes_count, 0) }
    ];
    return e(Section, { id: 'posting', kicker: '게시 및 참여도', title: '게시량 및 상호작용 구성' }, e('div', { className: 'grid' }, e('article', { className: 'panel' }, e('h3', null, '최근 월별 게시량'), e(Bars, { rows: months })), e('article', { className: 'panel' }, e('h3', null, '참여도 구성'), e(Bars, { rows: mix }))));
  }

  function Sentiment({ rows, selected }) {
    const distribution = counts(rows, (row) => row.sentiment_label).map((row) => ({ key: SENTIMENT_KO[row.key] || row.key, value: rows.length ? row.value / rows.length : 0, color: row.key === 'positive' ? '#16A34A' : row.key === 'negative' ? '#DC2626' : '#94A3B8' }));
    return e(Section, { id: 'sentiment', kicker: '제로샷 감성 분석', title: '감성 분석' },
      e('div', { className: 'grid' },
        e('article', { className: 'panel' }, e('h3', null, '감성 분포'), e(Bars, { rows: distribution, asPercent: true })),
        e('article', { className: 'panel' }, e('h3', null, selected === 'all' ? '브랜드별 감성' : '대표 부정 게시물'), selected === 'all' ? e(DataTable, { heads: ['브랜드', '긍정', '중립', '부정'], rows: Object.entries(ACCOUNTS).map(([key, account]) => { const scoped = rows.filter((row) => row.account === key); return [account.label, pct.format(scoped.length ? scoped.filter((row) => row.sentiment_label === 'positive').length / scoped.length : 0), pct.format(scoped.length ? scoped.filter((row) => row.sentiment_label === 'neutral').length / scoped.length : 0), pct.format(scoped.length ? scoped.filter((row) => row.sentiment_label === 'negative').length / scoped.length : 0)]; }) }) : e(PostList, { rows: rows.filter((row) => row.sentiment_label === 'negative').slice(0, 5) }))
      )
    );
  }

  function Humor({ rows, selected }) {
    const aggressive = rows.filter((row) => row.humor_label === 'Aggressive humor');
    const ag = computeStats(aggressive);
    const distribution = counts(rows, (row) => row.humor_label).map((row) => ({ key: HUMOR_KO[row.key] || row.key, value: rows.length ? row.value / rows.length : 0, color: row.key === 'Aggressive humor' ? '#DC2626' : row.key === 'Self-enhancing humor' ? '#2563EB' : undefined }));
    return e(Section, { id: 'humor', kicker: 'HSQ 유머 분류', title: '유머 분석' },
      e('div', { className: 'grid' },
        e('article', { className: 'panel' }, e('h3', null, '유머 유형 분포'), e(Bars, { rows: distribution, asPercent: true })),
        e('article', { className: 'panel' }, e('h3', null, '공격적 유머 집중 분석'), e('div', { className: 'focus' }, e(Metric, { label: '공격적 유머 게시물', value: fmt.format(aggressive.length), help: pct.format(rows.length ? aggressive.length / rows.length : 0), tone: 'danger' }), e(Metric, { label: '중앙값 참여도', value: cv(ag.med), help: '공격적 유머 게시물 기준' }), e(Metric, { label: '부정 감성 비중', value: pct.format(ag.neg), help: '공격적 유머 내 비중' }))),
        e('article', { className: 'panel wide' }, e('h3', null, selected === 'all' ? '브랜드별 유머 유형' : '대표 유머 게시물'), selected === 'all' ? e(DataTable, { heads: ['브랜드', '친화적', '자기고양적', '공격적', '자기패배적'], rows: Object.entries(ACCOUNTS).map(([key, account]) => { const scoped = rows.filter((row) => row.account === key); return [account.label].concat(HUMOR_LABELS.map((label) => pct.format(scoped.length ? scoped.filter((row) => row.humor_label === label).length / scoped.length : 0))); }) }) : e(PostList, { rows: rows.slice(0, 6) }))
      )
    );
  }

  function Topics({ rows }) {
    const topicRows = counts(rows.filter((row) => row.topic_id !== null), (row) => String(row.topic_id)).slice(0, 12);
    return e(Section, { id: 'topics', kicker: 'LDA 토픽', title: '토픽 분석' },
      e('div', { className: 'grid' },
        e('article', { className: 'panel' }, e('h3', null, '토픽 비중'), e(Bars, { rows: topicRows.map((row) => ({ key: `토픽 ${row.key}`, value: row.value })) })),
        e('article', { className: 'panel wide' }, e('h3', null, '토픽 × 참여도 × 유머'), e(DataTable, { heads: ['토픽', '주요 단어', '게시물', '중앙값 참여도', '주요 유머'], rows: topicRows.map((row) => [`토픽 ${row.key}`, row.rows[0] && row.rows[0].topic_terms ? row.rows[0].topic_terms.slice(0, 6).join(', ') : '-', fmt.format(row.value), cv(median(row.rows.map((post) => post.total_engagement))), counts(row.rows, (post) => post.humor_label)[0] ? HUMOR_KO[counts(row.rows, (post) => post.humor_label)[0].key] || counts(row.rows, (post) => post.humor_label)[0].key : '-']) }))
      )
    );
  }

  function PostList({ rows }) {
    if (!rows.length) return e('div', { className: 'empty' }, '사용 가능한 데이터가 없습니다.');
    return e('div', { className: 'post-mini' }, rows.map((post) => e('a', { key: post.id, href: post.tweet_url, target: '_blank', rel: 'noreferrer' }, e('b', null, `${post.brand} · ${post.date_iso}`), e('span', null, post.text_normalized || '(본문 없음)'), e('small', null, `${HUMOR_KO[post.humor_label] || post.humor_label} · ${SENTIMENT_KO[post.sentiment_label] || post.sentiment_label} · 참여도 ${cv(post.total_engagement)}`))));
  }

  function Explorer({ rows }) {
    const [page, setPage] = useState(1);
    useEffect(() => setPage(1), [rows.length]);
    const pageSize = 30;
    const pages = Math.max(1, Math.ceil(rows.length / pageSize));
    const current = Math.min(page, pages);
    const visible = rows.slice((current - 1) * pageSize, current * pageSize);
    return e(Section, { id: 'posts', kicker: '게시물 단위 근거', title: '게시물 탐색기' },
      e('div', { className: 'post-head' }, e('p', null, `필터 적용 후 ${fmt.format(rows.length)}개 게시물. ${current} / ${pages} 페이지.`), e('div', null, e('button', { disabled: current <= 1, onClick: () => setPage(current - 1) }, '이전'), e('button', { disabled: current >= pages, onClick: () => setPage(current + 1) }, '다음'))),
      e(DataTable, { heads: ['날짜', '브랜드', '본문', '참여도', '감성', '유머', '토픽', '링크'], rows: visible.map((post) => [post.date_iso, post.brand, e('span', { className: 'post-text' }, post.text_normalized || '(본문 없음)'), cv(post.total_engagement), `${SENTIMENT_KO[post.sentiment_label] || post.sentiment_label} (${scoreFmt.format(post.sentiment_score)})`, `${HUMOR_KO[post.humor_label] || post.humor_label} (${scoreFmt.format(post.humor_score)})`, post.topic_id === null ? '-' : `토픽 ${post.topic_id}`, post.tweet_url ? e('a', { href: post.tweet_url, target: '_blank', rel: 'noreferrer' }, '열기') : '-']) }),
      e('div', { className: 'cards' }, visible.map((post) => e('article', { key: post.id }, e('b', null, `${post.brand} · ${post.date_iso}`), e('p', null, post.text_normalized || '(본문 없음)'), e('small', null, `${cv(post.total_engagement)} 참여도 · ${SENTIMENT_KO[post.sentiment_label] || post.sentiment_label} · ${HUMOR_KO[post.humor_label] || post.humor_label}`), post.tweet_url ? e('a', { href: post.tweet_url, target: '_blank', rel: 'noreferrer' }, '게시물 열기') : null)))
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
    const topics = Array.from(new Set(scoped.filter((post) => post.topic_id !== null).map((post) => String(post.topic_id)))).sort((a, b) => Number(a) - Number(b));
    const effectiveFilters = selected === 'all' ? filters : Object.assign({}, filters, { brand: 'all' });
    const visible = useMemo(() => applyFilters(scoped, effectiveFilters), [scoped, effectiveFilters]);
    const summary = computeStats(visible);
    const latestValues = Object.values(datasets).flatMap((dataset) => [dataset.scrapeState && dataset.scrapeState.updated_at, dataset.scrapeState && dataset.scrapeState.scraped_at, dataset.lda && dataset.lda.generated_at, dataset.sentiment && dataset.sentiment.generated_at, dataset.humor && dataset.humor.generated_at]).filter(Boolean).map((value) => new Date(value)).filter((date) => !Number.isNaN(date.getTime()));
    const lastUpdated = latestValues.length ? latestValues.sort((a, b) => b - a)[0].toISOString().slice(0, 19).replace('T', ' ') : 'unknown';

    return e(React.Fragment, null,
      e(Header, { selected, setSelected, status: loading ? 'loading' : error ? 'error' : 'ready', lastUpdated }),
      e('nav', { className: 'section-nav' }, [
        ['overview', '개요'], ['brand-visual', '브랜드 시각화'], ['advanced', '고급 분석'], ['status', '데이터 상태'], ['descriptives', '기술통계'], ['comparison', '브랜드 비교'], ['evidence', '모델 프리 근거'], ['posting', '게시 및 참여'], ['sentiment', '감성 분석'], ['humor', '유머 분석'], ['topics', '토픽 분석'], ['posts', '게시물 탐색']
      ].map(([id, label]) => e('a', { href: `#${id}`, key: id }, label))),
      e('main', { className: 'layout' },
        e(Filters, { filters, setFilters, topics, count: visible.length }),
        e('div', { className: 'content' },
          loading ? e('div', { className: 'notice' }, '대시보드 데이터를 불러오는 중입니다...') : null,
          error ? e('div', { className: 'notice error' }, error) : null,
          e(Overview, { summary, selected }),
          e(BrandScopeVisual, { selected, rows: visible, allPosts }),
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
