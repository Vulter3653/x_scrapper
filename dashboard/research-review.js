/* global React, ReactDOM */
(function () {
  const mount = document.getElementById('research-review-root');
  if (!mount || !window.React || !window.ReactDOM) return;

  const e = React.createElement;
  const { useEffect, useMemo, useState } = React;
  const fmt = new Intl.NumberFormat('ko-KR');

  async function readJson(path) {
    const response = await fetch(path, { cache: 'no-store' });
    if (!response.ok) throw new Error(`${path}: ${response.status}`);
    return response.json();
  }

  function SectionTitle({ kicker, title, description }) {
    return e('div', { className: 'section-title' },
      e('span', null, kicker),
      e('h2', null, title),
      description ? e('p', { className: 'panel-copy' }, description) : null
    );
  }

  function Metric({ label, value, help, tone }) {
    return e('article', { className: `metric ${tone || ''}` }, e('span', null, label), e('strong', null, value), e('small', null, help));
  }

  function GuideCard({ step, title, goal, children }) {
    return e('article', { className: 'task-card guide-card' },
      e('b', null, step),
      e('h3', null, title),
      e('p', null, goal),
      children ? e('div', { className: 'guide-card-body' }, children) : null
    );
  }

  function GuidelineList({ items }) {
    return e('ul', { className: 'guide-list' }, items.map((item) => e('li', { key: item }, item)));
  }

  function DecisionTable({ rows }) {
    return e('div', { className: 'table-wrap guide-table-wrap' },
      e('table', { className: 'guide-table' },
        e('thead', null, e('tr', null, e('th', null, '판단 항목'), e('th', null, '선택 기준'), e('th', null, '예시'))),
        e('tbody', null, rows.map((row) => e('tr', { key: row.item },
          e('td', null, e('b', null, row.item)),
          e('td', null, row.rule),
          e('td', null, row.example)
        )))
      )
    );
  }

  function ExampleBox({ title, label, text, note }) {
    return e('article', { className: 'example-box' },
      e('span', null, label),
      e('h4', null, title),
      e('p', null, text),
      note ? e('small', null, note) : null
    );
  }

  function ReviewGuideDashboard() {
    const [auditRows, setAuditRows] = useState([]);
    const [joinedRows, setJoinedRows] = useState([]);
    const [topics, setTopics] = useState({});
    const [status, setStatus] = useState('loading');
    const [error, setError] = useState('');

    useEffect(() => {
      let cancelled = false;
      Promise.all([
        readJson('data/analysis/sampling_audit_candidates.json'),
        readJson('data/analysis/joined_posts.json'),
        Promise.all(['wendys', 'cocacola', 'moonpie'].map((slug) => readJson(`data/${slug}/lda_topics.json`).then((data) => [slug, data]).catch(() => [slug, null])))
      ]).then(([audit, joined, topicEntries]) => {
        if (cancelled) return;
        setAuditRows(audit || []);
        setJoinedRows(joined || []);
        setTopics(Object.fromEntries(topicEntries));
        setStatus('ready');
      }).catch((err) => {
        if (!cancelled) { setError(err.message); setStatus('error'); }
      });
      return () => { cancelled = true; };
    }, []);

    const stats = useMemo(() => {
      const lowConfidence = auditRows.filter((row) => row.audit_reason === 'low_confidence').length;
      const nonDominant = auditRows.filter((row) => row.audit_reason === 'non_dominant_humor').length;
      const viral = auditRows.filter((row) => row.audit_reason === 'viral').length;
      const topicCount = Object.values(topics).reduce((sum, data) => sum + (((data && data.topics) || []).length), 0);
      return { lowConfidence, nonDominant, viral, topicCount };
    }, [auditRows, topics]);

    const sampleAudit = useMemo(() => auditRows.slice(0, 3), [auditRows]);
    const sampleTopics = useMemo(() => {
      const rows = [];
      Object.entries(topics).forEach(([slug, data]) => {
        ((data && data.topics) || []).slice(0, 2).forEach((topic) => rows.push({ slug, topic }));
      });
      return rows.slice(0, 4);
    }, [topics]);

    return e(React.Fragment, null,
      e('header', { className: 'top review-top' },
        e('div', null,
          e('div', { className: 'title' }, e('h1', null, 'X 브랜드 인텔리전스 수동 검토 가이드'), e('em', { className: status === 'ready' ? 'ready' : status === 'error' ? 'error' : 'loading' }, status === 'ready' ? '가이드 준비' : status === 'error' ? '데이터 일부 오류' : '로딩 중')),
          e('p', null, '이 화면은 직접 편집하는 작업장이 아니라, 사람이 판단해야 할 기준과 예시만 제공하는 읽기 전용 가이드입니다.'),
          e('small', null, '실제 수정은 repo의 config 파일과 분석 산출 파일에서 수행합니다. 이 페이지에서는 입력값을 저장하지 않습니다.')
        ),
        e('nav', { className: 'tabs review-tabs' },
          e('a', { href: 'index.html' }, '분석 대시보드'),
          e('a', { href: '#audit' }, 'Audit 기준'),
          e('a', { href: '#labels' }, 'Zero-shot 기준'),
          e('a', { href: '#topics' }, 'LDA 기준')
        )
      ),
      e('nav', { className: 'section-nav review-section-nav' }, [
        ['purpose', '목적'], ['audit', '1. Sampling Audit'], ['labels', '2. Zero-shot 분류'], ['stopwords', '3. Stopwords'], ['topics', '4. Topic 해석'], ['apply', '5. 반영 절차']
      ].map(([id, label]) => e('a', { key: id, href: `#${id}` }, label))),
      e('main', { className: 'review-layout' },
        status === 'loading' ? e('div', { className: 'notice' }, '가이드에 표시할 현재 분석 데이터를 불러오는 중입니다...') : null,
        status === 'error' ? e('div', { className: 'notice error' }, `일부 데이터 로딩 실패: ${error}. 그래도 판단 기준은 계속 확인할 수 있습니다.`) : null,

        e('section', { id: 'purpose', className: 'section' },
          e(SectionTitle, { kicker: 'Read-only Guide', title: '이 페이지에서 하는 일과 하지 않는 일', description: '혼동을 줄이기 위해 편집 UI와 다운로드 버튼을 제거했습니다. 이 화면은 판단 기준, 예시, 반영 순서만 제시합니다.' }),
          e('div', { className: 'metrics' },
            e(Metric, { label: 'Audit Candidates', value: fmt.format(auditRows.length), help: '현재 생성된 수동 검토 후보' }),
            e(Metric, { label: 'Low-confidence', value: fmt.format(stats.lowConfidence), help: '우선 확인 대상', tone: 'danger' }),
            e(Metric, { label: 'Viral Cases', value: fmt.format(stats.viral), help: '성과 해석 영향 큼', tone: 'red' }),
            e(Metric, { label: 'Non-dominant Humor', value: fmt.format(stats.nonDominant), help: '희소 유머 유형 점검', tone: 'blue' }),
            e(Metric, { label: 'LDA Topics', value: fmt.format(stats.topicCount), help: '현재 토픽 수' }),
            e(Metric, { label: 'Joined Posts', value: fmt.format(joinedRows.length), help: '분석 대상 전체' })
          ),
          e('div', { className: 'guide-grid two-col' },
            e('article', { className: 'panel' }, e('h3', null, '이 화면에서 하지 않는 일'), e(GuidelineList, { items: ['tweet 라벨을 직접 저장하지 않습니다.', 'config 파일을 브라우저에서 수정하지 않습니다.', 'CSV/JSON 다운로드를 생성하지 않습니다.', '분석 파이프라인을 실행하지 않습니다.'] })),
            e('article', { className: 'panel' }, e('h3', null, '실제 작업 위치'), e(GuidelineList, { items: ['감성/유머 라벨 기준: config/sentiment_labels.json, config/humor_labels.json', 'LDA 불용어: config/lda_stopwords.txt', '수동 검토 기록: data/analysis/ 산출물 또는 별도 review 파일', '반영 후 재분석: analyze_posts.py, export_research_outputs.py, sync_dashboard_data.py'] }))
          )
        ),

        e('section', { id: 'audit', className: 'section' },
          e(SectionTitle, { kicker: 'Task 1', title: 'Sampling Audit 판단 기준', description: '모델이 불확실하거나 연구 결론에 영향이 큰 게시물을 사람이 먼저 확인합니다.' }),
          e(DecisionTable, { rows: [
            { item: 'low_confidence', rule: 'sentiment 또는 humor score가 낮아 모델 확신이 약한 경우 우선 검토', example: '짧은 답글, 맥락 의존 농담, 반어적 표현' },
            { item: 'viral', rule: '참여도가 높아 평균/토픽/감성 결과에 큰 영향을 주는 경우 우선 검토', example: '브랜드 간 teasing, 캠페인성 대형 반응 게시물' },
            { item: 'non_dominant_humor', rule: '자주 등장하지 않는 HSQ 유머 유형은 표본을 직접 확인', example: 'self-defeating 또는 aggressive로 분류된 희소 케이스' }
          ] }),
          e('div', { className: 'example-list' },
            sampleAudit.length ? sampleAudit.map((row, index) => e(ExampleBox, {
              key: `${row.post_id || index}`,
              label: row.audit_reason || 'audit candidate',
              title: `${row.brand || 'brand'} · 모델 라벨 확인 예시`,
              text: row.text || '(본문 없음)',
              note: `현재 모델: sentiment=${row.sentiment_label || 'n/a'}, humor=${row.humor_type || 'n/a'}, engagement=${fmt.format(Number(row.total_engagement) || 0)}`
            })) : e('div', { className: 'empty' }, 'No data available for this section.')
          )
        ),

        e('section', { id: 'labels', className: 'section' },
          e(SectionTitle, { kicker: 'Task 2', title: 'Zero-shot 감성/유머 분류 가이드라인', description: '사람은 개별 라벨을 무작정 바꾸는 것이 아니라, 반복되는 오분류 패턴을 찾아 라벨 설명과 hypothesis template을 개선합니다.' }),
          e('div', { className: 'guide-grid' },
            e(GuideCard, { step: 'Sentiment', title: '감성 라벨 기준', goal: '브랜드 게시물의 태도가 수용자에게 전달되는 정서를 판단합니다.' }, e(GuidelineList, { items: ['positive: 호의, 축하, 기대, 긍정적 캠페인 톤', 'neutral: 정보 전달, 단순 안내, 감정 표현이 약한 답변', 'negative: 불만, 공격, 조롱, 위기 대응, 부정적 정서'] })),
            e(GuideCard, { step: 'Humor', title: 'HSQ 유머 라벨 기준', goal: '유머가 있다면 기능을, 없다면 비유머 브랜드 메시지로 분리합니다.' }, e(GuidelineList, { items: ['Affiliative: 관계 형성, 친근한 농담, 공감 유도', 'Self-enhancing: 브랜드 자신감, 낙관적 자기표현', 'Aggressive: 경쟁자/타인 조롱, 비꼼, 공격적 teasing', 'Self-defeating: 자기비하, 자조적 표현', 'Non-humorous: 단순 홍보, 안내, 고객응대, 유머 없음'] })),
            e(GuideCard, { step: 'Template', title: 'Template 수정 기준', goal: '라벨이 반복적으로 한쪽으로 쏠릴 때만 문장을 수정합니다.' }, e(GuidelineList, { items: ['라벨 이름을 바꾸기 전 examples를 먼저 확인합니다.', '한두 사례가 아니라 반복 패턴이 있을 때 수정합니다.', '템플릿은 짧고 중립적으로 유지합니다.'] }))
          )
        ),

        e('section', { id: 'stopwords', className: 'section' },
          e(SectionTitle, { kicker: 'Task 3', title: 'LDA Stopword 추가 가이드라인', description: '불용어는 토픽 해석력을 높이기 위한 보수적 개입입니다. 브랜드/제품/캠페인 의미가 있는 단어를 과도하게 제거하면 분석력이 떨어집니다.' }),
          e('div', { className: 'guide-grid two-col' },
            e('article', { className: 'panel' }, e('h3', null, '추가해도 되는 경우'), e(GuidelineList, { items: ['모든 브랜드에서 반복되지만 의미 구분에 기여하지 않는 단어', 'URL, 플랫폼 잔여어, 자동 생성 토큰', '토픽 대부분에 반복되어 차이를 흐리는 일반어'] })),
            e('article', { className: 'panel' }, e('h3', null, '추가하지 말아야 하는 경우'), e(GuidelineList, { items: ['제품명, 캠페인명, 경쟁 브랜드명', '특정 브랜드 톤을 드러내는 핵심 단어', '토픽 간 차이를 설명하는 감성/유머 관련 단어'] }))
          ),
          e('article', { className: 'panel wide' },
            e('h3', null, '판단 예시'),
            e('p', { className: 'panel-copy' }, '예: “https”, “amp”, “twitter”는 제거 후보입니다. 반면 “frosty”, “coke”, “moonpie”, “spicy”처럼 제품 또는 캠페인 의미가 있는 단어는 먼저 토픽 맥락을 확인해야 합니다.')
          )
        ),

        e('section', { id: 'topics', className: 'section' },
          e(SectionTitle, { kicker: 'Task 4', title: 'LDA Topic 해석 가이드라인', description: '토픽은 단어 목록만 보고 이름 붙이지 말고, 대표 게시물과 engagement 특성을 함께 확인합니다.' }),
          e(DecisionTable, { rows: [
            { item: 'human_topic_label', rule: '상위 단어와 대표 게시물이 같은 의미 범주를 가리킬 때 짧은 이름 부여', example: 'Brand humor / teasing, Seasonal campaign, Customer support' },
            { item: 'remove_terms', rule: '여러 토픽에 반복되는 노이즈 단어만 기록', example: 'http, amp, generic filler words' },
            { item: 'merge_with_topic', rule: '두 토픽의 대표 게시물과 상위 단어가 실질적으로 같은 경우만 병합 제안', example: 'promotion topic과 product announcement topic이 거의 동일한 경우' },
            { item: 'split_needed', rule: '한 토픽 안에 명확히 다른 캠페인/담론이 섞인 경우 분할 제안', example: '고객응대와 경쟁자 teasing이 한 토픽에 섞인 경우' }
          ] }),
          e('div', { className: 'example-list' },
            sampleTopics.length ? sampleTopics.map(({ slug, topic }) => e(ExampleBox, {
              key: `${slug}-${topic.topic_id}`,
              label: `${slug} · Topic ${topic.topic_id}`,
              title: '토픽 이름 부여 예시',
              text: `상위 단어: ${(topic.top_terms || []).join(', ')}`,
              note: `대표 게시물은 실제 review 시 최소 3개 이상 확인한 뒤 이름을 붙입니다.`
            })) : e('div', { className: 'empty' }, 'No data available for this section.')
          )
        ),

        e('section', { id: 'apply', className: 'section' },
          e(SectionTitle, { kicker: 'Task 5', title: '수정 반영 절차', description: '이 페이지는 가이드만 제공합니다. 실제 변경은 아래 파일을 직접 수정한 뒤 분석을 다시 실행합니다.' }),
          e('article', { className: 'panel wide' },
            e('pre', { className: 'apply-steps' }, '1. Sampling Audit 결과를 별도 CSV 또는 data/analysis/에 기록\n2. 반복 오분류가 확인되면 config/sentiment_labels.json 또는 config/humor_labels.json 수정\n3. Topic 노이즈가 확인되면 config/lda_stopwords.txt 수정\n4. python analyze_posts.py --task all\n5. python export_research_outputs.py\n6. python sync_dashboard_data.py\n7. 변경 결과를 dashboard에서 재확인 후 commit/push'),
            e('p', { className: 'panel-copy' }, '권장 원칙: 사람이 판단한 변경은 반드시 이유를 남기고, 성능 향상 여부는 coherence, topic interpretability, low-confidence sample 재검토로 확인합니다.')
          )
        )
      )
    );
  }

  ReactDOM.createRoot(mount).render(e(ReviewGuideDashboard));
})();
