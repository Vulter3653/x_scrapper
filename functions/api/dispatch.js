const WORKFLOWS = {
  scrape: 'scrape.yml',
  lda: 'lda.yml',
  sentiment: 'sentiment.yml'
};

function jsonResponse(body, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: {
      'content-type': 'application/json; charset=utf-8',
      'cache-control': 'no-store'
    }
  });
}

function readBearer(request) {
  const header = request.headers.get('authorization') || '';
  const match = header.match(/^Bearer\s+(.+)$/i);
  return match ? match[1].trim() : '';
}

export async function onRequestPost({ request, env }) {
  const adminToken = env.DASHBOARD_ADMIN_TOKEN;
  const githubToken = env.GH_ACTIONS_TOKEN;
  const owner = env.GITHUB_OWNER || 'Vulter3653';
  const repo = env.GITHUB_REPO || 'x_scrapper';
  const ref = env.GITHUB_REF || 'main';

  if (!adminToken || !githubToken) {
    return jsonResponse({ error: 'Cloudflare secrets DASHBOARD_ADMIN_TOKEN and GH_ACTIONS_TOKEN must be configured.' }, 500);
  }

  if (readBearer(request) !== adminToken) {
    return jsonResponse({ error: 'Unauthorized.' }, 401);
  }

  let payload;
  try {
    payload = await request.json();
  } catch (error) {
    return jsonResponse({ error: 'Invalid JSON payload.' }, 400);
  }

  const workflow = WORKFLOWS[payload.kind];
  if (!workflow) {
    return jsonResponse({ error: 'Invalid workflow kind.' }, 400);
  }

  const account = payload.account === 'cocacola' ? 'CocaCola' : 'Wendys';
  const maxScrolls = String(payload.maxScrolls || '2500');
  const analysisMaxPosts = String(payload.analysisMaxPosts || '0');

  const inputs = { target_user: account };
  if (payload.kind === 'scrape') {
    inputs.max_scrolls = maxScrolls;
    inputs.scroll_delay_seconds = '1.25';
    inputs.idle_scroll_limit = '60';
  }
  if (payload.kind === 'lda') {
    inputs.analysis_max_posts = analysisMaxPosts;
    inputs.lda_min_topics = '2';
    inputs.lda_max_topics = '12';
  }
  if (payload.kind === 'sentiment') {
    inputs.analysis_max_posts = analysisMaxPosts;
    inputs.sentiment_labels = 'positive,neutral,negative';
  }

  const url = `https://api.github.com/repos/${owner}/${repo}/actions/workflows/${workflow}/dispatches`;
  const response = await fetch(url, {
    method: 'POST',
    headers: {
      'accept': 'application/vnd.github+json',
      'authorization': `Bearer ${githubToken}`,
      'content-type': 'application/json',
      'user-agent': 'cloudflare-pages-dashboard',
      'x-github-api-version': '2022-11-28'
    },
    body: JSON.stringify({ ref, inputs })
  });

  if (!response.ok) {
    const detail = await response.text();
    return jsonResponse({ error: 'GitHub workflow dispatch failed.', detail }, response.status);
  }

  return jsonResponse({ ok: true, workflow, ref, inputs });
}

export function onRequestGet() {
  return jsonResponse({ ok: true, endpoint: 'POST /api/dispatch' });
}
