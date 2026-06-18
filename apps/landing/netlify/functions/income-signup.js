// POST /.netlify/functions/income-signup
// Body: { email, method ('email'|'wallet'|'bank'|'card'), wallet? }
// Records a basic-income signup into Supabase `recipients` (status='queued').
// Reuses existing columns (no migration): wallet + method go into `notes`.
// The actual payout runs LOCALLY from anicca's wallet (execute-ubi.py, anicca's key) —
// NOT from this lambda (the key never lives here). This only records the queue entry.

const SUPABASE_URL = process.env.SUPABASE_URL;
const SUPABASE_SERVICE = process.env.SUPABASE_SERVICE_ROLE_KEY;

const WALLET_RE = /^0x[0-9a-fA-F]{40}$/;

async function supabaseInsert(table, row) {
  const res = await fetch(`${SUPABASE_URL}/rest/v1/${table}`, {
    method: 'POST',
    headers: {
      apikey: SUPABASE_SERVICE,
      Authorization: `Bearer ${SUPABASE_SERVICE}`,
      'Content-Type': 'application/json',
      Prefer: 'return=representation',
    },
    body: JSON.stringify(row),
  });
  return { ok: res.ok, status: res.status, body: await res.json().catch(() => null) };
}

exports.handler = async (event) => {
  if (event.httpMethod !== 'POST') return { statusCode: 405, body: 'method not allowed' };
  if (!SUPABASE_URL || !SUPABASE_SERVICE) {
    return { statusCode: 500, body: JSON.stringify({ error: 'missing config' }) };
  }
  let body;
  try {
    body = JSON.parse(event.body || '{}');
  } catch {
    return { statusCode: 400, body: JSON.stringify({ error: 'invalid json' }) };
  }
  const email = (body.email || '').trim().toLowerCase();
  const method = ['email', 'wallet', 'bank', 'card'].includes(body.method) ? body.method : 'email';
  const wallet = (body.wallet || '').trim();

  if (!email || !email.includes('@')) {
    return { statusCode: 400, body: JSON.stringify({ error: 'email required' }) };
  }
  if (method === 'wallet' && !WALLET_RE.test(wallet)) {
    return { statusCode: 400, body: JSON.stringify({ error: 'valid Base wallet (0x…40 hex) required' }) };
  }

  const ins = await supabaseInsert('recipients', {
    email,
    reason: 'basic income signup',
    notes: `method=${method};wallet=${method === 'wallet' ? wallet : ''}`,
    status: 'queued',
  });
  // Tolerate duplicate / constraint errors — never block the user's UX. We log status.
  return {
    statusCode: 200,
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ok: true, recorded: ins.ok, method }),
  };
};
