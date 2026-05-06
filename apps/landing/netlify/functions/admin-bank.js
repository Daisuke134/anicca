// /admin/bank — token-gated bank preview UI.
//
// Reads bank_entries from Supabase (public.bank_entries), groups by bank_type+lang,
// renders an HTML page with a card per entry. Approval/rejection is read-only here;
// the canonical bank lives in ~/anicca-monk-factory/scripts/bank_*.jsonl. Use the
// `anicca-bank` CLI (rebuild/preview/promote) for content edits — this UI is for
// quick review on mobile/desktop.
//
// Auth: ?token=<ADMIN_TOKEN> (set ADMIN_TOKEN in Netlify env).
// Filter: ?type=letter&lang=en  (optional)

const SUPABASE_URL = process.env.SUPABASE_URL || 'https://cycgdwndgfgdbnndithc.supabase.co';

exports.handler = async (event) => {
  const params = event.queryStringParameters || {};
  const token = params.token || '';
  const expected = process.env.ADMIN_TOKEN || '';

  if (!expected) {
    return resp(500, 'ADMIN_TOKEN not configured in Netlify env');
  }
  if (token !== expected) {
    return resp(401, 'auth required: append ?token=...');
  }

  const KEY = process.env.SUPABASE_SERVICE_ROLE_KEY;
  if (!KEY) return resp(500, 'SUPABASE_SERVICE_ROLE_KEY missing');

  const filter = [];
  if (params.type) filter.push(`bank_type=eq.${encodeURIComponent(params.type)}`);
  if (params.lang) filter.push(`lang=eq.${encodeURIComponent(params.lang)}`);
  const filterQ = filter.length ? '&' + filter.join('&') : '';

  let rows;
  try {
    const r = await fetch(
      `${SUPABASE_URL}/rest/v1/bank_entries?select=*&order=bank_type.asc,lang.asc,entry_id.asc${filterQ}`,
      { headers: { apikey: KEY, Authorization: `Bearer ${KEY}` } }
    );
    if (!r.ok) return resp(500, `supabase ${r.status}: ${await r.text()}`);
    rows = await r.json();
  } catch (e) {
    return resp(500, `fetch error: ${e.message || e}`);
  }

  // Group rows
  const groups = {};
  for (const row of rows) {
    const key = `${row.bank_type}/${row.lang}`;
    if (!groups[key]) groups[key] = [];
    groups[key].push(row);
  }

  const totalsHtml = Object.entries(groups)
    .map(([k, arr]) => `<a href="?token=${encodeURIComponent(token)}&type=${arr[0].bank_type}&lang=${arr[0].lang}" class="pill">${k} · ${arr.length}</a>`)
    .join(' ');

  const cards = Object.entries(groups).map(([groupKey, arr]) => {
    const cardItems = arr.map((row) => renderCard(row, token)).join('\n');
    return `<section class="group"><h2>${esc(groupKey)} <small>(${arr.length})</small></h2><div class="grid">${cardItems}</div></section>`;
  }).join('\n');

  const html = `<!DOCTYPE html>
<html lang="en"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex,nofollow">
<title>Anicca Bank Preview</title>
<style>
  * { box-sizing: border-box; }
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif; margin: 0; padding: 24px; background: #FBF7EF; color: #2A2520; max-width: 1100px; margin: 0 auto; }
  h1 { font-weight: 300; font-size: 26px; margin-bottom: 6px; }
  .meta { font-size: 14px; color: #6F6058; margin-bottom: 24px; }
  .pill { display: inline-block; padding: 6px 12px; border-radius: 999px; background: #ECE5D5; color: #2A2520; text-decoration: none; font-size: 13px; margin-right: 6px; margin-bottom: 6px; }
  .pill:hover { background: #DCD0B4; }
  .group { margin: 28px 0; }
  .group h2 { font-weight: 400; font-size: 18px; margin-bottom: 14px; padding-bottom: 8px; border-bottom: 1px solid #DCD0B4; }
  .group h2 small { color: #998976; font-weight: 300; }
  .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 16px; }
  .card { background: white; border: 1px solid #DCD0B4; border-radius: 12px; padding: 18px; overflow: hidden; }
  .card h3 { margin: 0 0 6px; font-size: 15px; font-weight: 500; }
  .card .id { font-family: 'SF Mono', Menlo, monospace; font-size: 11px; color: #998976; margin-bottom: 10px; }
  .card .preview { font-size: 14px; line-height: 1.5; color: #2A2520; max-height: 260px; overflow: hidden; position: relative; }
  .card .preview::after { content: ''; position: absolute; bottom: 0; left: 0; right: 0; height: 24px; background: linear-gradient(to bottom, transparent, white); pointer-events: none; }
  .card .preview iframe { width: 100%; min-height: 260px; border: 0; }
  .status { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; }
  .status-approved { background: #E0F0DC; color: #2C6E33; }
  .status-pending { background: #FFF3D6; color: #8A6014; }
  .status-rejected { background: #F4D6D6; color: #8B2D2D; }
  details summary { cursor: pointer; color: #6F6058; font-size: 12px; margin-top: 10px; }
  details pre { background: #F4EEDF; padding: 10px; border-radius: 6px; overflow: auto; font-size: 11px; max-height: 300px; }
</style>
</head><body>
<h1>Anicca Bank Preview</h1>
<div class="meta">${rows.length} total entries · filter: ${esc((params.type||'all') + ' / ' + (params.lang||'all'))} · <a href="?token=${encodeURIComponent(token)}">reset</a></div>
<div>${totalsHtml}</div>
${cards}
</body></html>`;

  return {
    statusCode: 200,
    headers: { 'Content-Type': 'text/html; charset=utf-8', 'Cache-Control': 'private, no-store' },
    body: html,
  };
};

function renderCard(row, token) {
  const c = row.content || {};
  const title = c.title || c.subject || c.full_text?.slice(0, 80) || '(untitled)';
  const status = row.status || 'pending';
  const statusClass = `status-${status}`;

  let previewBody = '';
  if (c.html) {
    // letter — render the HTML in an iframe to isolate styles
    const safeHtml = c.html.replace(/<\/script>/gi, '<\\/script>');
    previewBody = `<iframe srcdoc='${esc(safeHtml).replace(/'/g, '&apos;')}' sandbox></iframe>`;
  } else if (c.full_text) {
    previewBody = `<div>${esc(c.full_text)}</div>`;
  } else {
    previewBody = `<div>(no preview body)</div>`;
  }

  const captionsHtml = (c.captions && c.captions.length)
    ? `<details><summary>captions (${c.captions.length})</summary><pre>${esc(c.captions.join('\n\n'))}</pre></details>`
    : '';

  return `<div class="card">
    <span class="status ${statusClass}">${status}</span>
    <h3>${esc(title)}</h3>
    <div class="id">${esc(row.bank_type)}/${esc(row.lang)}/${esc(row.entry_id)}</div>
    <div class="preview">${previewBody}</div>
    ${captionsHtml}
    <details><summary>raw json</summary><pre>${esc(JSON.stringify(row.content, null, 2))}</pre></details>
  </div>`;
}

function esc(s) {
  if (s == null) return '';
  return String(s).replace(/[&<>"]/g, (m) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[m]));
}

function resp(code, msg) {
  return { statusCode: code, headers: { 'Content-Type': 'text/plain; charset=utf-8' }, body: String(msg) };
}
