(function () {
  const EXACT = new Map(Object.entries({
    'X Brand Intelligence Dashboard': 'X 브랜드 인텔리전스 대시보드',
    'Loading React dashboard...': 'React 대시보드를 불러오는 중입니다...',
    'Dashboard boot error': '대시보드 실행 오류',
    'Open browser console for details.': '자세한 내용은 브라우저 콘솔을 확인하십시오.',
    'React or ReactDOM failed to load.': 'React 또는 ReactDOM을 불러오지 못했습니다.',
    'Advanced React analytics for all-brand and brand-specific X posts, sentiment, topics, and HSQ humor.': '전체 브랜드 및 브랜드별 X 게시물, 감성, 토픽, HSQ 유머 분석을 제공하는 고도화 React 대시보드입니다.',
    'React analytics for all-brand and brand-specific X posts, sentiment, topics, and HSQ humor.': '전체 브랜드 및 브랜드별 X 게시물, 감성, 토픽, HSQ 유머 분석을 제공하는 React 대시보드입니다.',
    'All Brands': '전체 브랜드',
    'ready': '준비 완료',
    'loading': '로딩 중',
    'error': '오류',
    'overview': '개요',
    'advanced': '고급 분석',
    'status': '데이터 상태',
    'descriptives': '기술통계',
    'comparison': '브랜드 비교',
    'evidence': '모델 프리 근거',
    'posting': '게시 및 참여',
    'sentiment': '감성 분석',
    'humor': '유머 분석',
    'topics': '토픽 분석',
    'posts': '게시물 탐색',
    'Executive summary': '핵심 요약',
    'All Brands Overview': '전체 브랜드 개요',
    "Wendy's Overview": 'Wendy\'s 개요',
    'Coca-Cola Overview': 'Coca-Cola 개요',
    'MoonPie Overview': 'MoonPie 개요',
    'Total Posts': '총 게시물 수',
    'Date Range': '수집 기간',
    'Total Engagement': '총 참여도',
    'Median Engagement': '중앙값 참여도',
    'Viral Share': '바이럴 비중',
    'Dominant Humor': '주요 유머 유형',
    'parsed post timestamps': '게시물 작성일 기준',
    'top 5% by engagement': '참여도 상위 5% 기준',
    'Data readiness': '데이터 준비 상태',
    'Dataset Status': '데이터셋 상태',
    'Brand': '브랜드',
    'Posts': '게시물',
    'LDA': 'LDA',
    'Sentiment': '감성',
    'HSQ Humor': 'HSQ 유머',
    'available': '사용 가능',
    'missing': '누락',
    'Descriptive statistics': '기술통계',
    'Dataset and Engagement Profile': '데이터셋 및 참여도 프로파일',
    'Summary': '요약',
    'Metric': '지표',
    'Value': '값',
    'Post Count by Brand': '브랜드별 게시물 수',
    'Total Engagement by Brand': '브랜드별 총 참여도',
    'Brand Summary': '브랜드 요약',
    'Cross-brand analysis': '브랜드 간 분석',
    'Brand Comparison': '브랜드 비교',
    'Brand comparison is shown in the All Brands view.': '브랜드 비교는 전체 브랜드 보기에서 표시됩니다.',
    'Advanced analytics': '고급 분석',
    'Insights, Quality Audit, and Export': '인사이트, 데이터 품질 점검 및 내보내기',
    'Auto Insights': '자동 인사이트',
    'Data Quality Audit': '데이터 품질 점검',
    'Confidence Diagnostics': '분류 신뢰도 진단',
    'Export Current View': '현재 보기 내보내기',
    'Download the currently filtered post-level dataset with sentiment, humor, topic, and engagement fields.': '현재 필터가 적용된 게시물 단위 데이터셋을 감성, 유머, 토픽, 참여도 필드와 함께 다운로드합니다.',
    'Download filtered CSV': '필터링 결과 CSV 다운로드',
    'Top Engagement Posts': '참여도 상위 게시물',
    'Check': '점검 항목',
    'Count': '개수',
    'Share': '비중',
    'Missing text': '본문 누락',
    'Unknown sentiment': '감성 미분류',
    'Unknown humor': '유머 미분류',
    'Missing topic assignment': '토픽 배정 누락',
    'Zero engagement': '참여도 0',
    'Average sentiment score': '평균 감성 점수',
    'Average humor score': '평균 유머 점수',
    'Posts with sentiment score ≥ .70': '감성 점수 .70 이상 게시물',
    'Posts with humor score ≥ .70': '유머 점수 .70 이상 게시물',
    'Model-free evidence': '모델 프리 근거',
    'Observed Patterns Before Modeling': '모형화 이전 관찰 패턴',
    'Humor Type → Median Engagement': '유머 유형 → 중앙값 참여도',
    'Sentiment → Median Engagement': '감성 → 중앙값 참여도',
    'Viral Humor Composition': '바이럴 게시물의 유머 구성',
    'Humor × Sentiment Cells': '유머 × 감성 조합',
    'Cell': '조합',
    'Posting and engagement': '게시 및 참여도',
    'Posting Volume and Interaction Mix': '게시량 및 상호작용 구성',
    'Recent Monthly Posting Volume': '최근 월별 게시량',
    'Engagement Mix': '참여도 구성',
    'Likes': '좋아요',
    'Replies': '답글',
    'Retweets': '리트윗',
    'Quotes': '인용',
    'Zero-shot sentiment': '제로샷 감성 분석',
    'Sentiment Analysis': '감성 분석',
    'Sentiment Distribution': '감성 분포',
    'Sentiment by Brand': '브랜드별 감성',
    'Representative Negative Posts': '대표 부정 게시물',
    'HSQ humor classification': 'HSQ 유머 분류',
    'Humor Analysis': '유머 분석',
    'Humor Type Distribution': '유머 유형 분포',
    'Aggressive Humor Focus': '공격적 유머 집중 분석',
    'Aggressive Posts': '공격적 유머 게시물',
    'Negative Share': '부정 감성 비중',
    'within aggressive humor': '공격적 유머 내 비중',
    'aggressive posts': '공격적 유머 게시물 기준',
    'Humor Type by Brand': '브랜드별 유머 유형',
    'Representative Humor Posts': '대표 유머 게시물',
    'LDA topics': 'LDA 토픽',
    'Topic Analysis': '토픽 분석',
    'Topic Share': '토픽 비중',
    'Topic × Engagement × Humor': '토픽 × 참여도 × 유머',
    'Topic': '토픽',
    'Top Terms': '주요 단어',
    'Dominant Humor': '주요 유머 유형',
    'Post-level evidence': '게시물 단위 근거',
    'Post Explorer': '게시물 탐색기',
    'Date': '날짜',
    'Text': '본문',
    'Engagement': '참여도',
    'Humor': '유머',
    'Link': '링크',
    'Open': '열기',
    'Open post': '게시물 열기',
    'No data available': '사용 가능한 데이터가 없습니다.',
    'Filters': '필터',
    'Search': '검색',
    'text, humor, sentiment, topic': '본문, 유머, 감성, 토픽',
    'From': '시작일',
    'To': '종료일',
    'All brands': '전체 브랜드',
    'All sentiment': '전체 감성',
    'All humor': '전체 유머',
    'All topics': '전체 토픽',
    'All posts': '전체 게시물',
    'Viral': '바이럴',
    'Viral only': '바이럴만',
    'Non-viral only': '비바이럴만',
    'Min Humor Score': '최소 유머 점수',
    'Min Sentiment Score': '최소 감성 점수',
    'Sort': '정렬',
    'Newest': '최신순',
    'Humor score': '유머 점수',
    'Sentiment score': '감성 점수',
    'Reset': '초기화',
    'Prev': '이전',
    'Next': '다음',
    'positive': '긍정',
    'neutral': '중립',
    'negative': '부정',
    'unknown': '미분류',
    'Affiliative humor': '친화적 유머',
    'Self-enhancing humor': '자기고양적 유머',
    'Aggressive humor': '공격적 유머',
    'Self-defeating humor': '자기패배적 유머'
  }));

  function replacePatterns(text) {
    let out = text;
    out = out.replace(/^Last updated: (.+)$/u, '최종 업데이트: $1');
    out = out.replace(/^(\d[\d,.]*) posts$/u, '$1개 게시물');
    out = out.replace(/^(\d[\d,.]*) loaded$/u, '$1개 로드됨');
    out = out.replace(/^(\d[\d,.]*) brand\(s\), (\d[\d,.]*) active day\(s\)$/u, '$1개 브랜드, $2일 활동');
    out = out.replace(/^Avg (.+) per post$/u, '게시물당 평균 $1');
    out = out.replace(/^P95 (.+)$/u, '95백분위수 $1');
    out = out.replace(/^Positive (.+) \/ Negative (.+)$/u, '긍정 $1 / 부정 $2');
    out = out.replace(/^(.+) posts after filters\. Page (\d+) of (\d+)\.$/u, '필터 적용 후 $1개 게시물. $2 / $3 페이지.');
    out = out.replace(/^Topic (\d+)$/u, '토픽 $1');
    out = out.replace(/^(.+) engagement$/u, '참여도 $1');
    out = out.replace(/^(.+) has the highest median engagement in the current view \((.+) across (.+) posts\)\.$/u, '현재 보기에서 $1의 중앙값 참여도가 가장 높습니다($2, $3개 게시물 기준).');
    out = out.replace(/^(.+) has the highest median engagement among visible HSQ humor types \((.+)\)\.$/u, '현재 보기의 HSQ 유머 유형 중 $1의 중앙값 참여도가 가장 높습니다($2).');
    out = out.replace(/^Negative sentiment accounts for (.+) of visible posts\.$/u, '현재 표시된 게시물 중 부정 감성 비중은 $1입니다.');
    out = out.replace(/^Aggressive humor accounts for (.+) of visible posts, with (.+) median engagement\.$/u, '현재 표시된 게시물 중 공격적 유머 비중은 $1이며, 중앙값 참여도는 $2입니다.');
    out = out.replace(/^Humor coverage needs attention: (.+) of visible posts have unknown humor labels\.$/u, '유머 분류 커버리지 점검이 필요합니다. 현재 표시된 게시물 중 $1가 유머 미분류 상태입니다.');
    out = out.replace(/positive \(([^)]+)\)/gu, '긍정 ($1)');
    out = out.replace(/neutral \(([^)]+)\)/gu, '중립 ($1)');
    out = out.replace(/negative \(([^)]+)\)/gu, '부정 ($1)');
    out = out.replace(/unknown \(([^)]+)\)/gu, '미분류 ($1)');
    out = out.replace(/Affiliative humor/gu, '친화적 유머');
    out = out.replace(/Self-enhancing humor/gu, '자기고양적 유머');
    out = out.replace(/Aggressive humor/gu, '공격적 유머');
    out = out.replace(/Self-defeating humor/gu, '자기패배적 유머');
    out = out.replace(/positive/gu, '긍정');
    out = out.replace(/neutral/gu, '중립');
    out = out.replace(/negative/gu, '부정');
    out = out.replace(/unknown/gu, '미분류');
    return out;
  }

  function translateText(text) {
    const trimmed = text.trim();
    if (!trimmed) return text;
    const translated = EXACT.get(trimmed) || replacePatterns(trimmed);
    if (translated === trimmed) return text;
    return text.replace(trimmed, translated);
  }

  function translateNode(node) {
    if (!node) return;
    if (node.nodeType === Node.TEXT_NODE) {
      node.nodeValue = translateText(node.nodeValue || '');
      return;
    }
    if (node.nodeType !== Node.ELEMENT_NODE) return;
    const tag = node.tagName;
    if (tag === 'SCRIPT' || tag === 'STYLE' || tag === 'NOSCRIPT') return;
    if (node.placeholder) node.placeholder = translateText(node.placeholder);
    node.childNodes.forEach(translateNode);
  }

  function run() {
    document.documentElement.lang = 'ko';
    translateNode(document.body);
  }

  const observer = new MutationObserver(() => {
    window.requestAnimationFrame(run);
  });

  window.addEventListener('DOMContentLoaded', run);
  window.addEventListener('load', run);
  observer.observe(document.documentElement, { childList: true, subtree: true, characterData: true });
  setTimeout(run, 250);
  setTimeout(run, 1000);
})();
