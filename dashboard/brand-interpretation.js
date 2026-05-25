/* global React, ReactDOM */
(function () {
  const mount = document.getElementById('brand-interpretation-root');
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
  const compact = new Intl.NumberFormat('ko-KR', { notation: 'compact', maximumFractionDigits: 1 });
  const pct = new Intl.NumberFormat('ko-KR', { style: 'percent', maximumFractionDigits: 1 });
  const n = (value) => Number.isFinite(Number(value)) ? Number(value) : 0;
  const cv = (value) => Math.abs(n(value)) >= 1000 ? compact.format(n(value)) : fmt.format(Math.round(n(value)));
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
    const map = new Map();
    rows.forEach((row) => {
      const key = getter(row) || 'unknown';
      if (!map.has(key)) map.set(key, []);
      map.get(key).push(row);
    });
    return Array.from(map.entries()).map(([key, grouped]) => ({ key, rows: grouped, value: grouped.length })).sort((a, b) => b.value - a.value);
  }
  function describeStrategy(rows, scope) {
    if (!rows.length) return ['현재 범위에서 해석 가능한 게시물이 없습니다.'];
    const humorTop = group(rows, (row) => row.humor).filter((item) => item.key !== 'unknown')[0];
    const sentimentTop = group(rows, (row) => row.sentiment).filter((item) => item.key !== 'unknown')[0];
    const aggressive = rows.filter((row) => row.humor === 'Aggressive humor');
    const affiliative = rows.filter((row) => row.humor === 'Affiliative humor');
    const negativeAggressive = rows.filter((row) => row.humor === 'Aggressive humor' && row.sentiment === 'negative');
    const positiveAffiliative = rows.filter((row) => row.humor === 'Affiliative humor' && row.sentiment === 'positive');
    const overallMedian = median(rows.map((row) => row.engagement));
    const agMedian = median(aggressive.map((row) => row.engagement));
    const affMedian = median(affiliative.map((row) => row.engagement));
    const lowConfidence = rows.filter((row) => (row.humorScore > 0 && row.humorScore < 0.5) || (row.sentimentScore > 0 && row.sentimentScore < 0.5));
    const lines = [];

    if (humorTop) {
      lines.push(`${scope}의 가장 빈번한 HSQ 유머 유형은 ${HUMOR_KO[humorTop.key] || humorTop.key}이며, 전체의 ${pct.format(humorTop.value / rows.length)}를 차지합니다.`);
    }
    if (sentimentTop) {
      lines.push(`감성 측면에서는 ${SENTIMENT_KO[sentimentTop.key] || sentimentTop.key} 라벨이 가장 많이 나타나며, 이는 현재 브랜드 커뮤니케이션의 정서적 방향성을 보여줍니다.`);
    }
    if (aggressive.length) {
      const direction = agMedian > overallMedian ? '전체 중앙값보다 높아, 도발적 표현이 참여를 끌어내는 경향이 관찰됩니다' : '전체 중앙값보다 높지 않아, 도발적 표현이 항상 높은 참여로 이어진다고 보기는 어렵습니다';
      lines.push(`공격적 유머는 ${pct.format(aggressive.length / rows.length)}를 차지하며, 중앙값 참여도는 ${cv(agMedian)}입니다. 이는 ${direction}.`);
    }
    if (affiliative.length) {
      const direction = affMedian > overallMedian ? '관계 형성형 유머가 비교적 안정적인 반응을 유도할 가능성을 시사합니다' : '관계 형성형 유머의 반응이 다른 유형보다 두드러진다고 단정하기는 어렵습니다';
      lines.push(`친화적 유머는 ${pct.format(affiliative.length / rows.length)}를 차지하며, 중앙값 참여도는 ${cv(affMedian)}입니다. 이는 ${direction}.`);
    }
    if (negativeAggressive.length) {
      lines.push(`공격적 유머와 부정 감성이 결합된 게시물은 ${fmt.format(negativeAggressive.length)}개이며, 전체의 ${pct.format(negativeAggressive.length / rows.length)}입니다. 이 조합은 논쟁적 반응 가능성을 별도로 검토할 필요가 있습니다.`);
    }
    if (positiveAffiliative.length) {
      lines.push(`친화적 유머와 긍정 감성이 결합된 게시물은 ${fmt.format(positiveAffiliative.length)}개입니다. 이는 관계 형성 중심의 긍정적 커뮤니케이션 사례로 해석할 수 있습니다.`);
    }
    if (lowConfidence.length / rows.length > 0.1) {
      lines.push(`다만 저신뢰 분류 게시물이 ${pct.format(lowConfidence.length / rows.length)}로 나타나므로, 주요 결론을 내리기 전 수동 검토 샘플링이 필요합니다.`);
    }
    return lines;
  }
  function Metric({ label, value, help, tone }) {
    return e('article', { className: `metric ${tone || ''}` }, e('span', null, label), e('strong', null, value), help ? e('small', null, help) : null);
  }
  function PostList({ rows }) {
    if (!rows.length) return e('div', { className: 'empty' }, '대표 게시물이 없습니다.');
    return e('div', { className: 'post-mini' }, rows.slice(0, 5).map((post) => e('a', { key: post.id, href: post.url, target: '_blank', rel: 'noreferrer' },
      e('b', null, `${post.brand} · ${post.date || '날짜 미상'} · 참여도 ${cv(post.engagement)}`),
      e('span', null, post.text || '(본문 없음)'),
      e('small', null, `${HUMOR_KO[post.humor] || post.humor} / ${SENTIMENT_KO[post.sentiment] || post.sentiment}`)
    )));
  }
  function Interpretation({ rows, scope }) {
    const lines = describeStrategy(rows, scope);
    const topPost = rows.slice().sort((a, b) => b.engagement - a.engagement)[0];
    const topHumor = group(rows, (row) => row.humor).filter((item) => item.key !== 'unknown')[0];
    const topSentiment = group(rows, (row) => row.sentiment).filter((item) => item.key !== 'unknown')[0];
    const lowConfidence = rows.filter((row) => (row.humorScore > 0 && row.humorScore < 0.5) || (row.sentimentScore > 0 && row.sentimentScore < 0.5));
    return e('section', { id: 'brand-interpretation', className: 'confidence-review-shell' },
      e('div', { className: 'section-title' }, e('span', null, '브랜드별 자동 해석'), e('h2', null, '브랜드 커뮤니케이션 해석')),
      e('p', { className: 'panel-copy' }, `${scope} 기준으로 유머 유형, 감성, 참여도, 분류 신뢰도를 결합하여 해석 문장을 자동 생성합니다.`),
      e('div', { className: 'metrics' },
        e(Metric, { label: '게시물 수', value: fmt.format(rows.length), help: scope, tone: 'blue' }),
        e(Metric, { label: '주요 유머', value: topHumor ? HUMOR_KO[topHumor.key] || topHumor.key : '-', help: topHumor ? pct.format(topHumor.value / Math.max(rows.length, 1)) : '-' }),
        e(Metric, { label: '주요 감성', value: topSentiment ? SENTIMENT_KO[topSentiment.key] || topSentiment.key : '-', help: topSentiment ? pct.format(topSentiment.value / Math.max(rows.length, 1)) : '-' }),
        e(Metric, { label: '대표 최고 참여도', value: topPost ? cv(topPost.engagement) : '-', help: topPost ? topPost.date : '-' }),
        e(Metric, { label: '저신뢰 검토 대상', value: fmt.format(lowConfidence.length), help: 'score < .50' })
      ),
      e('div', { className: 'grid' },
        e('article', { className: 'panel wide' }, e('h3', null, '자동 해석 문장'), e('ul', { className: 'insight-list' }, lines.map((line, index) => e('li', { key: index }, line)))),
        e('article', { className: 'panel wide' }, e('h3', null, '해석 참고용 상위 참여 게시물'), e(PostList, { rows: rows.slice().sort((a, b) => b.engagement - a.engagement).slice(0, 5) }))
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
        .catch((error) => console.error('brand interpretation load failed', error));
      const onClick = () => setTimeout(() => setScope(selectedKey()), 50);
      document.addEventListener('click', onClick);
      return () => { cancelled = true; document.removeEventListener('click', onClick); };
    }, []);
    const rows = useMemo(() => scope === 'all' ? Object.values(data).flat() : (data[scope] || []), [data, scope]);
    const label = scope === 'all' ? '전체 브랜드' : ACCOUNTS[scope].label;
    return e(Interpretation, { rows, scope: label });
  }
  ReactDOM.createRoot(mount).render(e(App));
})();
