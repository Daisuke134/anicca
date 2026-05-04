// POST /api/income/apply
// Body: { email, reason }
// 1. Stripe Connect Express account create
// 2. Account link create (onboarding URL)
// 3. Insert recipient row (status=pending)
// 4. Return { onboarding_url }

const STRIPE_KEY = process.env.STRIPE_SECRET_KEY;
const SUPABASE_URL = process.env.SUPABASE_URL;
const SUPABASE_SERVICE = process.env.SUPABASE_SERVICE_ROLE_KEY;
const ORIGIN = process.env.URL || 'https://aniccaai.com';

async function stripeForm(path, params) {
  const body = new URLSearchParams();
  function flat(obj, prefix = '') {
    for (const [k, v] of Object.entries(obj)) {
      const key = prefix ? `${prefix}[${k}]` : k;
      if (v && typeof v === 'object' && !Array.isArray(v)) flat(v, key);
      else body.append(key, String(v));
    }
  }
  flat(params);
  const res = await fetch(`https://api.stripe.com/v1${path}`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${STRIPE_KEY}`,
      'Content-Type': 'application/x-www-form-urlencoded',
    },
    body,
  });
  return res.json();
}

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
  return { ok: res.ok, status: res.status, body: await res.json() };
}

exports.handler = async (event) => {
  if (event.httpMethod !== 'POST') {
    return { statusCode: 405, body: 'method not allowed' };
  }
  if (!STRIPE_KEY || !SUPABASE_URL || !SUPABASE_SERVICE) {
    return { statusCode: 500, body: JSON.stringify({ error: 'missing config' }) };
  }

  let body;
  try {
    body = JSON.parse(event.body || '{}');
  } catch {
    return { statusCode: 400, body: JSON.stringify({ error: 'invalid json' }) };
  }
  const email = (body.email || '').trim().toLowerCase();
  const reason = (body.reason || '').trim().slice(0, 280);

  if (!email || !email.includes('@')) {
    return { statusCode: 400, body: JSON.stringify({ error: 'email required' }) };
  }
  if (!reason) {
    return { statusCode: 400, body: JSON.stringify({ error: 'reason required' }) };
  }

  // 1. Create Stripe Connect Express account
  const account = await stripeForm('/accounts', {
    type: 'express',
    country: 'US',
    email,
    capabilities: { transfers: { requested: 'true' } },
    metadata: { source: 'aniccaai_basic_income' },
  });
  if (account.error) {
    return {
      statusCode: 502,
      body: JSON.stringify({ error: 'stripe account create failed', detail: account.error.message }),
    };
  }

  // 2. Create onboarding link
  const link = await stripeForm('/account_links', {
    account: account.id,
    refresh_url: `${ORIGIN}/income`,
    return_url: `${ORIGIN}/income/onboarded`,
    type: 'account_onboarding',
  });
  if (link.error) {
    return {
      statusCode: 502,
      body: JSON.stringify({ error: 'stripe account link failed', detail: link.error.message }),
    };
  }

  // 3. Insert recipient row
  const insert = await supabaseInsert('recipients', {
    email,
    reason,
    stripe_account_id: account.id,
    status: 'pending',
  });
  if (!insert.ok) {
    // If duplicate email, return existing onboarding by retrying with existing account
    return {
      statusCode: 409,
      body: JSON.stringify({ error: 'already applied', detail: insert.body }),
    };
  }

  return {
    statusCode: 200,
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ onboarding_url: link.url, account_id: account.id }),
  };
};
