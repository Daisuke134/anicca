// POST /api/income/apply
// Body: { email, reason, country? ('us'|'jp'|...) }
//
// 1. Stripe Connect V2 account create (recipient capability for stripe_transfers)
// 2. V2 Account Link create (account_onboarding)
// 3. Insert recipient row (status=pending)
// 4. Return { onboarding_url }
//
// Uses V2 API directly via fetch (no SDK to keep functions lean).

const STRIPE_KEY = process.env.STRIPE_SECRET_KEY;
const STRIPE_API_VERSION = '2025-08-27.preview';
const SUPABASE_URL = process.env.SUPABASE_URL;
const SUPABASE_SERVICE = process.env.SUPABASE_SERVICE_ROLE_KEY;
const ORIGIN = process.env.URL || 'https://aniccaai.com';

async function stripeV2(path, body) {
  const res = await fetch(`https://api.stripe.com/v2${path}`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${STRIPE_KEY}`,
      'Content-Type': 'application/json',
      'Stripe-Version': STRIPE_API_VERSION,
    },
    body: JSON.stringify(body),
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
  const country = (body.country || 'jp').toLowerCase();

  if (!email || !email.includes('@')) {
    return { statusCode: 400, body: JSON.stringify({ error: 'email required' }) };
  }
  if (!reason) {
    return { statusCode: 400, body: JSON.stringify({ error: 'reason required' }) };
  }

  // 1. Stripe Connect V2 account
  const account = await stripeV2('/core/accounts', {
    contact_email: email,
    display_name: email.split('@')[0].slice(0, 60),
    identity: { country },
    dashboard: 'express',
    defaults: {
      responsibilities: {
        fees_collector: 'application',
        losses_collector: 'application',
      },
    },
    configuration: {
      recipient: {
        capabilities: {
          stripe_balance: { stripe_transfers: { requested: true } },
        },
      },
    },
    metadata: { source: 'aniccaai_basic_income' },
  });
  if (account.error || !account.id) {
    return {
      statusCode: 502,
      body: JSON.stringify({
        error: 'stripe v2 account create failed',
        detail: account.error?.message || account.error || 'unknown',
      }),
    };
  }

  // 2. V2 Account Link
  const link = await stripeV2('/core/account_links', {
    account: account.id,
    use_case: {
      type: 'account_onboarding',
      account_onboarding: {
        configurations: ['recipient'],
        refresh_url: `${ORIGIN}/income`,
        return_url: `${ORIGIN}/income/onboarded?account=${account.id}`,
      },
    },
  });
  if (link.error || !link.url) {
    return {
      statusCode: 502,
      body: JSON.stringify({
        error: 'stripe v2 account link failed',
        detail: link.error?.message || link.error || 'unknown',
      }),
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
    return {
      statusCode: 409,
      body: JSON.stringify({ error: 'already applied or db error', detail: insert.body }),
    };
  }

  return {
    statusCode: 200,
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ onboarding_url: link.url, account_id: account.id }),
  };
};
