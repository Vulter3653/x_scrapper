(function () {
  const KEY_TERM_REPLACEMENTS = [
    [/X 브랜드 인텔리전스 대시보드/g, 'X Brand Intelligence Dashboard'],
    [/React 대시보드/g, 'React Dashboard'],
    [/대시보드/g, 'Dashboard'],

    [/자기고양적 유머/g, 'Self-enhancing Humor'],
    [/친화적 유머/g, 'Affiliative Humor'],
    [/자기패배적 유머/g, 'Self-defeating Humor'],
    [/공격적 유머/g, 'Aggressive Humor'],
    [/HSQ 유머/g, 'HSQ Humor'],
    [/유머 유형/g, 'Humor Type'],
    [/유머/g, 'Humor'],

    [/제로샷 감성/g, 'Zero-shot Sentiment'],
    [/감성 라벨/g, 'Sentiment Label'],
    [/감성 점수/g, 'Sentiment Score'],
    [/감성/g, 'Sentiment'],

    [/토픽/g, 'Topic'],
    [/참여도/g, 'Engagement'],
    [/신뢰도/g, 'Confidence'],
    [/분류/g, 'Classification'],
    [/라벨/g, 'Label'],
    [/모델 프리/g, 'Model-free'],
    [/인사이트/g, 'Insight'],
    [/기술통계/g, 'Descriptives'],
    [/강건성/g, 'Robustness'],
    [/수동 검토/g, 'Manual Review'],
    [/저신뢰/g, 'Low-confidence'],
    [/바이럴/g, 'Viral'],
    [/샘플링/g, 'Sampling'],
    [/내보내기/g, 'Export'],

    [/브랜드/g, 'Brand'],
    [/게시물/g, 'Post'],
    [/데이터셋/g, 'Dataset'],
    [/데이터/g, 'Data'],
    [/필터/g, 'Filter'],
    [/시각화/g, 'Visualization'],
    [/분석/g, 'Analysis'],
    [/요약/g, 'Summary'],
    [/탐색기/g, 'Explorer'],
    [/탐색/g, 'Explorer'],

    [/중앙값/g, 'Median'],
    [/평균/g, 'Average'],
    [/비중/g, 'Share'],
    [/개수/g, 'Count'],
    [/최대값/g, 'Maximum'],
    [/최고/g, 'Top'],
    [/상위/g, 'Top'],
    [/분포/g, 'Distribution'],
    [/조합/g, 'Combination'],
    [/효과/g, 'Effect'],
    [/결과/g, 'Result'],
    [/현재 보기/g, 'Current View'],

    [/긍정/g, 'Positive'],
    [/중립/g, 'Neutral'],
    [/부정/g, 'Negative'],
    [/미분류/g, 'Unknown'],
    [/준비 완료/g, 'Ready'],
    [/로딩 중/g, 'Loading'],
    [/오류/g, 'Error'],

    [/좋아요/g, 'Likes'],
    [/답글/g, 'Replies'],
    [/리트윗/g, 'Retweets'],
    [/인용/g, 'Quotes'],
    [/열기/g, 'Open'],
    [/이전/g, 'Prev'],
    [/다음/g, 'Next'],
    [/초기화/g, 'Reset'],
    [/최신순/g, 'Newest'],
    [/정렬/g, 'Sort'],
    [/검색/g, 'Search']
  ];

  const EXACT_PHRASES = new Map(Object.entries({
    '사용 가능한 Data가 없습니다.': '사용 가능한 Data가 없습니다.',
    '사용 가능한 데이터가 없습니다.': '사용 가능한 Data가 없습니다.',
    '자세한 내용은 브라우저 콘솔을 확인하십시오.': '자세한 내용은 Browser Console을 확인하십시오.',
    '알 수 없는 JavaScript 오류': '알 수 없는 JavaScript Error',
    '본문 없음': '본문 없음',
    '날짜 미상': '날짜 미상'
  }));

  function normalizeRepeatedTerms(text) {
    return text
      .replace(/Engagement Engagement/g, 'Engagement')
      .replace(/Humor Humor/g, 'Humor')
      .replace(/Sentiment Sentiment/g, 'Sentiment')
      .replace(/Topic Topic/g, 'Topic')
      .replace(/Confidence Confidence/g, 'Confidence')
      .replace(/Brand Brand/g, 'Brand')
      .replace(/Post Post/g, 'Post')
      .replace(/Data Data/g, 'Data')
      .replace(/Analysis Analysis/g, 'Analysis')
      .replace(/Summary Summary/g, 'Summary')
      .replace(/Robustness Robustness/g, 'Robustness')
      .replace(/Low-confidence Low-confidence/g, 'Low-confidence')
      .replace(/Viral Viral/g, 'Viral')
      .replace(/Filter Filter/g, 'Filter')
      .replace(/Explorer Explorer/g, 'Explorer')
      .replace(/Classification Classification/g, 'Classification')
      .replace(/Median Engagement/g, 'Median Engagement')
      .replace(/Average Engagement/g, 'Average Engagement')
      .replace(/Top Engagement/g, 'Top Engagement');
  }

  function convertKeyTerms(text) {
    let out = text;
    KEY_TERM_REPLACEMENTS.forEach(([pattern, replacement]) => {
      out = out.replace(pattern, replacement);
    });
    out = normalizeRepeatedTerms(out);
    return EXACT_PHRASES.get(out.trim()) || out;
  }

  function translateNode(node) {
    if (!node) return;
    if (node.nodeType === Node.TEXT_NODE) {
      const value = node.nodeValue || '';
      const converted = convertKeyTerms(value);
      if (converted !== value) node.nodeValue = converted;
      return;
    }
    if (node.nodeType !== Node.ELEMENT_NODE) return;
    const tag = node.tagName;
    if (tag === 'SCRIPT' || tag === 'STYLE' || tag === 'NOSCRIPT') return;
    if (node.classList && (node.classList.contains('post-text') || node.classList.contains('post-mini'))) return;
    if (node.placeholder) node.placeholder = convertKeyTerms(node.placeholder);
    node.childNodes.forEach(translateNode);
  }

  function run() {
    document.documentElement.lang = 'ko';
    translateNode(document.body);
  }

  let scheduled = false;
  const observer = new MutationObserver(() => {
    if (scheduled) return;
    scheduled = true;
    window.requestAnimationFrame(() => {
      scheduled = false;
      run();
    });
  });

  window.addEventListener('DOMContentLoaded', run);
  window.addEventListener('load', run);
  observer.observe(document.documentElement, { childList: true, subtree: true, characterData: true });
  setTimeout(run, 250);
  setTimeout(run, 1000);
})();
