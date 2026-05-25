(function () {
  const ACCOUNTS = {
    wendys: { label: "Wendy's", path: 'data/wendys/hsq_humor_classification.json', color: '#E2231A' },
    cocacola: { label: 'Coca-Cola', path: 'data/cocacola/hsq_humor_classification.json', color: '#111827' },
    moonpie: { label: 'MoonPie', path: 'data/moonpie/hsq_humor_classification.json', color: '#F97316' }
  };

  const MATRIX = [
    {
      row: '적응적 / 긍정적 기능',
      cells: [
        {
          column: '타인·관계 지향',
          label: '친화적 유머',
          sourceLabel: 'Affiliative humor',
          description: '관계 형성, 긴장 완화, 사회적 유대 강화'
        },
        {
          column: '자기 지향',
          label: '자기고양적 유머',
          sourceLabel: 'Self-enhancing humor',
          description: '스트레스 완화, 긍정적 자기조절, 회복탄력성'
        }
      ]
    },
    {
      row: '부적응적 / 부정적 기능',
      cells: [
        {
          column: '타인·관계 지향',
          label: '공격적 유머',
          sourceLabel: 'Aggressive humor',
          description: '조롱, 비판, 우월감, 타인 대상 공격성'
        },
        {
          column: '자기 지향',
          label: '자기패배적 유머',
          sourceLabel: 'Self-defeating humor',
          description: '자기비하, 자기희생적 농담, 부정적 자기표현'
        }
      ]
    }
  ];

  const STYLE_ID = 'humor-matrix-style';

  function addStyle() {
    if (document.getElementById(STYLE_ID)) return;
    const style = document.createElement('style');
    style.id = STYLE_ID;
    style.textContent = `
      .humor-matrix-wrapper { display: grid; gap: 18px; }
      .humor-matrix-note { color: var(--secondary, #475569); font-size: 14px; line-height: 1.55; }
      .humor-matrix-grid { display: grid; grid-template-columns: 120px repeat(2, minmax(0, 1fr)); gap: 10px; align-items: stretch; }
      .humor-matrix-axis, .humor-matrix-cell { border: 1px solid var(--line, #e2e8f0); border-radius: 18px; background: var(--surface, #fff); box-shadow: 0 10px 28px rgba(15,23,42,.06); }
      .humor-matrix-axis { display: grid; place-items: center; padding: 14px; color: var(--secondary, #475569); font-size: 13px; font-weight: 900; text-align: center; }
      .humor-matrix-axis.corner { background: transparent; box-shadow: none; border-style: dashed; }
      .humor-matrix-cell { padding: 16px; min-height: 168px; display: grid; gap: 10px; }
      .humor-matrix-cell.adaptive { border-color: rgba(22, 163, 74, .28); }
      .humor-matrix-cell.maladaptive { border-color: rgba(220, 38, 38, .26); }
      .humor-matrix-kicker { color: var(--muted, #64748b); font-size: 12px; font-weight: 900; text-transform: uppercase; letter-spacing: .05em; }
      .humor-matrix-label { font-size: 19px; font-weight: 950; letter-spacing: -.03em; }
      .humor-matrix-desc { color: var(--secondary, #475569); font-size: 13px; line-height: 1.5; }
      .humor-matrix-number { display: flex; align-items: baseline; justify-content: space-between; gap: 10px; margin-top: 4px; }
      .humor-matrix-number strong { font-size: 26px; letter-spacing: -.04em; }
      .humor-matrix-number span { color: var(--muted, #64748b); font-size: 13px; font-weight: 800; }
      .humor-matrix-track { height: 12px; border-radius: 999px; background: var(--surface-2, #f1f5f9); overflow: hidden; }
      .humor-matrix-track i { display: block; height: 100%; border-radius: 999px; background: linear-gradient(90deg, var(--blue, #2563eb), #93c5fd); }
      .humor-matrix-table { overflow-x: auto; }
      .humor-matrix-table table { min-width: 720px; }
      .humor-matrix-pill { display: inline-flex; align-items: center; min-height: 26px; padding: 0 9px; border-radius: 999px; background: var(--surface-2, #f1f5f9); color: var(--secondary, #475569); font-size: 12px; font-weight: 800; }
      @media (max-width: 760px) {
        .humor-matrix-grid { grid-template-columns: 1fr; }
        .humor-matrix-axis.corner, .humor-matrix-axis.column { display: none; }
        .humor-matrix-axis.row { min-height: 44px; }
        .humor-matrix-cell { min-height: auto; }
      }
    `;
    document.head.appendChild(style);
  }

  async function loadJson(path) {
    const response = await fetch(path, { cache: 'no-store' });
    if (!response.ok) throw new Error(`${path}: ${response.status}`);
    return response.json();
  }

  function getLabelCounts(data) {
    const counts = {};
    if (data && data.label_counts && typeof data.label_counts === 'object') {
      Object.entries(data.label_counts).forEach(([label, value]) => {
        counts[label] = Number(value) || 0;
      });
    }
    if ((!Object.keys(counts).length) && data && Array.isArray(data.posts)) {
      data.posts.forEach((post) => {
        const label = post.top_label || post.label || 'unknown';
        counts[label] = (counts[label] || 0) + 1;
      });
    }
    return counts;
  }

  function sumCounts(items) {
    return items.reduce((total, item) => total + item.count, 0);
  }

  function formatCount(value) {
    return new Intl.NumberFormat('ko-KR').format(value || 0);
  }

  function formatPercent(value) {
    return new Intl.NumberFormat('ko-KR', { style: 'percent', maximumFractionDigits: 1 }).format(value || 0);
  }

  function buildData(rawByAccount) {
    const cells = MATRIX.flatMap((row, rowIndex) => row.cells.map((cell, colIndex) => ({
      ...cell,
      row: row.row,
      rowIndex,
      colIndex,
      count: 0,
      byBrand: {}
    })));

    Object.entries(rawByAccount).forEach(([accountKey, raw]) => {
      const labelCounts = getLabelCounts(raw);
      cells.forEach((cell) => {
        const count = Number(labelCounts[cell.sourceLabel] || 0);
        cell.count += count;
        cell.byBrand[accountKey] = count;
      });
    });

    const total = sumCounts(cells);
    cells.forEach((cell) => {
      cell.share = total ? cell.count / total : 0;
    });
    return { cells, total };
  }

  function createCell(cell, total) {
    const adaptive = cell.rowIndex === 0;
    const div = document.createElement('article');
    div.className = `humor-matrix-cell ${adaptive ? 'adaptive' : 'maladaptive'}`;
    div.innerHTML = `
      <div class="humor-matrix-kicker">${cell.row} · ${cell.column}</div>
      <div class="humor-matrix-label">${cell.label}</div>
      <p class="humor-matrix-desc">${cell.description}</p>
      <div class="humor-matrix-number">
        <strong>${formatCount(cell.count)}</strong>
        <span>${formatPercent(total ? cell.count / total : 0)}</span>
      </div>
      <div class="humor-matrix-track"><i style="width:${Math.max(2, cell.share * 100)}%"></i></div>
    `;
    return div;
  }

  function renderMatrix(data) {
    const section = document.createElement('section');
    section.id = 'humor-matrix';
    section.className = 'section';
    section.innerHTML = `
      <div class="section-title">
        <span>HSQ 2x2 분류</span>
        <h2>유머 유형 2x2 분포도</h2>
      </div>
      <div class="panel wide humor-matrix-wrapper">
        <p class="humor-matrix-note">
          HSQ 유머 유형을 두 기준으로 재배치했습니다. 세로축은 유머의 기능을 기준으로 적응적/긍정적 기능과 부적응적/부정적 기능을 구분하고, 가로축은 유머의 지향 대상을 기준으로 타인·관계 지향과 자기 지향을 구분합니다.
        </p>
        <div class="humor-matrix-grid" data-matrix></div>
      </div>
      <div class="panel wide humor-matrix-table">
        <h3>브랜드별 2x2 유머 분포</h3>
        <table>
          <thead>
            <tr>
              <th>브랜드</th>
              <th>친화적 유머<br><span class="humor-matrix-pill">적응적 · 타인/관계</span></th>
              <th>자기고양적 유머<br><span class="humor-matrix-pill">적응적 · 자기</span></th>
              <th>공격적 유머<br><span class="humor-matrix-pill">부적응적 · 타인/관계</span></th>
              <th>자기패배적 유머<br><span class="humor-matrix-pill">부적응적 · 자기</span></th>
            </tr>
          </thead>
          <tbody data-brand-rows></tbody>
        </table>
      </div>
    `;

    const grid = section.querySelector('[data-matrix]');
    grid.appendChild(axis('2x2 기준', 'corner'));
    grid.appendChild(axis('타인·관계 지향', 'column'));
    grid.appendChild(axis('자기 지향', 'column'));

    MATRIX.forEach((row, rowIndex) => {
      grid.appendChild(axis(row.row, 'row'));
      row.cells.forEach((cellSpec, colIndex) => {
        const cell = data.cells.find((item) => item.rowIndex === rowIndex && item.colIndex === colIndex);
        grid.appendChild(createCell(cell, data.total));
      });
    });

    const tbody = section.querySelector('[data-brand-rows]');
    Object.entries(ACCOUNTS).forEach(([accountKey, account]) => {
      const rowCounts = data.cells.map((cell) => cell.byBrand[accountKey] || 0);
      const rowTotal = rowCounts.reduce((sum, value) => sum + value, 0) || 1;
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td><strong>${account.label}</strong></td>
        ${rowCounts.map((value) => `<td>${formatCount(value)} <span class="humor-matrix-pill">${formatPercent(value / rowTotal)}</span></td>`).join('')}
      `;
      tbody.appendChild(tr);
    });

    return section;
  }

  function axis(text, extraClass) {
    const div = document.createElement('div');
    div.className = `humor-matrix-axis ${extraClass || ''}`;
    div.textContent = text;
    return div;
  }

  function addNavLink() {
    const nav = document.querySelector('.section-nav');
    if (!nav || nav.querySelector('a[href="#humor-matrix"]')) return;
    const link = document.createElement('a');
    link.href = '#humor-matrix';
    link.textContent = '2x2 유머 분포';
    const humorLink = nav.querySelector('a[href="#humor"]');
    if (humorLink && humorLink.nextSibling) nav.insertBefore(link, humorLink.nextSibling);
    else nav.appendChild(link);
  }

  async function mount() {
    addStyle();
    const rawEntries = await Promise.all(Object.entries(ACCOUNTS).map(async ([key, account]) => {
      try {
        return [key, await loadJson(account.path)];
      } catch (error) {
        return [key, null];
      }
    }));
    const data = buildData(Object.fromEntries(rawEntries));
    const section = renderMatrix(data);

    const existing = document.getElementById('humor-matrix');
    if (existing) existing.remove();

    const humorSection = document.getElementById('humor');
    if (humorSection && humorSection.parentNode) {
      humorSection.parentNode.insertBefore(section, humorSection.nextSibling);
    } else {
      const content = document.querySelector('.content') || document.getElementById('root');
      content.appendChild(section);
    }
    addNavLink();
  }

  function waitForDashboard() {
    const content = document.querySelector('.content');
    if (content) {
      mount();
      return;
    }
    setTimeout(waitForDashboard, 300);
  }

  window.addEventListener('load', waitForDashboard);
  setTimeout(waitForDashboard, 800);
})();
