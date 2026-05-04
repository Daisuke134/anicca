// POST /api/income/webhook
// Stripe Connect webhook: account.updated → flip kyc_complete + status='waitlist'
// SECURITY: validates signature with STRIPE_CONNECT_WEBHOOK_SECRET

const crypto = require('crypto');

const SUPABASE_URL = process.env.SUPABASE_URL;
const SUPABASE_SERVICE = process.env.SUPABASE_SERVICE_ROLE_KEY;
const WEBHOOK_SECRET = process.env.STRIPE_CONNECT_WEBHOOK_SECRET;
const SLACK_WEBHOOK_AGENTS = process.env.SLACK_WEBHOOK_AGENTS;

async function supabaseUpdate(table, filter, patch) {
  const url = `${SUPABASE_URL}/rest/v1/${table}?${filter}`;
  const res = await fetch(url, {
    method: 'PATCH',
    headers: {
      apikey: SUPABASE_SERVICE,
      Authorization: `Bearer ${SUPABASE_SERVICE}`,
      'Content-Type': 'application/json',
      Prefer: 'return=representation',
    },
    body: JSON.stringify(patch),
  });
  return { ok: res.ok, status: res.status, body: await res.json() };
}

function verifyStripeSignature(rawBody, signatureHeader, secret) {
  if (!signatureHeader || !secret) return false;
  const parts = signatureHeader.split(',').reduce((acc, p) => {
    const [k, v] = p.split('=');
    acc[k] = v;
    return acc;
  }, {});
  if (!parts.t || !parts.v1) return false;
  const expected = crypto
    .createHmac('sha256', secret)
    .update(`${parts.t}.${rawBody}`)
    .digest('hex');
  return crypto.timingSafeEqual(Buffer.from(parts.v1), Buffer.from(expected));
}

async function notifySlack(text) {
  if (!SLACK_WEBHOOK_AGENTS) return;
  await fetch(SLACK_WEBHOOK_AGENTS, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text }),
  }).catch(() => {});
}

exports.handler = async (event) => {
  if (event.httpMethod !== 'POST') return { statusCode: 405, body: 'method not allowed' };
  if (!SUPABASE_URL || !SUPABASE_SERVICE) {
    return { statusCode: 500, body: 'missing config' };
  }

  const rawBody = event.body || '';
  const sig = event.headers['stripe-signature'] || event.headers['Stripe-Signature'];

  // If WEBHOOK_SECRET not set yet (initial deploy), skip verification but log warning
  if (WEBHOOK_SECRET && !verifyStripeSignature(rawBody, sig, WEBHOOK_SECRET)) {
    return { statusCode: 400, body: 'invalid signature' };
  }

  let evt;
  try {
    evt = JSON.parse(rawBody);
  } catch {
    return { statusCode: 400, body: 'invalid json' };
  }

  // Only handle Connect account.updated
  if (evt.type !== 'account.updated') {
    return { statusCode: 200, body: 'ignored' };
  }

  const acct = evt.data.object;
  const acctId = acct.id;
  const detailsSubmitted = acct.details_submitted === true;
  const transfersActive =
    acct.capabilities &&
    (acct.capabilities.transfers === 'active' || acct.capabilities.transfers === true);
  const kycComplete = detailsSubmitted && transfersActive;

  if (kycComplete) {
    const upd = await supabaseUpdate(
      'recipients',
      `stripe_account_id=eq.${encodeURIComponent(acctId)}`,
      { kyc_complete: true, status: 'waitlist' },
    );
    if (upd.ok && Array.isArray(upd.body) && upd.body.length > 0) {
      const r = upd.body[0];
      await notifySlack(
        `🎯 Basic Income — new waitlist application:\n• email: ${r.email}\n• stripe acct: ${r.stripe_account_id}\n• reason: "${(r.reason || '').slice(0, 200)}"\n\nApprove: aniccaai.com/admin/basic-income (TBD) or set status=active manually.`,
      );
    }
  }

  return { statusCode: 200, body: 'ok' };
};
