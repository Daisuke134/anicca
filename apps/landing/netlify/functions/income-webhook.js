// POST /api/income/webhook
// Stripe Connect V2 thin events: v2.core.account[configuration.recipient].capability_status_updated
//                                v2.core.account[requirements].updated
// SECURITY: validates signature with STRIPE_CONNECT_WEBHOOK_SECRET
// On capability active → flip kyc_complete=true + status='waitlist' + Slack notify

const crypto = require('crypto');

const SUPABASE_URL = process.env.SUPABASE_URL;
const SUPABASE_SERVICE = process.env.SUPABASE_SERVICE_ROLE_KEY;
const WEBHOOK_SECRET = process.env.STRIPE_CONNECT_WEBHOOK_SECRET;
const STRIPE_KEY = process.env.STRIPE_SECRET_KEY;
const STRIPE_API_VERSION = '2025-08-27.preview';
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

async function stripeV2Get(path) {
  const res = await fetch(`https://api.stripe.com/v2${path}`, {
    headers: {
      Authorization: `Bearer ${STRIPE_KEY}`,
      'Stripe-Version': STRIPE_API_VERSION,
    },
  });
  return res.json();
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
  try {
    return crypto.timingSafeEqual(Buffer.from(parts.v1), Buffer.from(expected));
  } catch {
    return false;
  }
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
  if (!SUPABASE_URL || !SUPABASE_SERVICE || !STRIPE_KEY) {
    return { statusCode: 500, body: 'missing config' };
  }

  const rawBody = event.body || '';
  const sig = event.headers['stripe-signature'] || event.headers['Stripe-Signature'];

  if (WEBHOOK_SECRET && !verifyStripeSignature(rawBody, sig, WEBHOOK_SECRET)) {
    return { statusCode: 400, body: 'invalid signature' };
  }

  let thinEvent;
  try {
    thinEvent = JSON.parse(rawBody);
  } catch {
    return { statusCode: 400, body: 'invalid json' };
  }

  const eventType = thinEvent.type || '';
  const acctId =
    (thinEvent.related_object && thinEvent.related_object.id) ||
    (thinEvent.data && thinEvent.data.object && thinEvent.data.object.id) ||
    thinEvent.account_id;

  if (!acctId) {
    return { statusCode: 200, body: 'no account in event' };
  }

  // For both event types we need to fetch the latest account status from V2
  if (
    eventType === 'v2.core.account[configuration.recipient].capability_status_updated' ||
    eventType === 'v2.core.account[requirements].updated' ||
    eventType.includes('capability_status_updated') ||
    eventType.includes('requirements')
  ) {
    const acct = await stripeV2Get(
      `/core/accounts/${acctId}?include=configuration.recipient&include=requirements`,
    );
    if (acct.error) {
      return { statusCode: 502, body: 'stripe fetch failed: ' + (acct.error.message || '') };
    }

    const transfersStatus =
      acct.configuration?.recipient?.capabilities?.stripe_balance?.stripe_transfers?.status;
    const reqStatus = acct.requirements?.summary?.minimum_deadline?.status;
    const onboardingComplete =
      reqStatus !== 'currently_due' && reqStatus !== 'past_due';
    const readyToReceive = transfersStatus === 'active';

    if (readyToReceive && onboardingComplete) {
      const upd = await supabaseUpdate(
        'recipients',
        `stripe_account_id=eq.${encodeURIComponent(acctId)}`,
        { kyc_complete: true, status: 'waitlist' },
      );
      if (upd.ok && Array.isArray(upd.body) && upd.body.length > 0) {
        const r = upd.body[0];
        await notifySlack(
          `🎯 Basic Income — new waitlist:\n• email: ${r.email}\n• stripe acct: ${r.stripe_account_id}\n• reason: "${(r.reason || '').slice(0, 200)}"\n\nApprove via Supabase: UPDATE recipients SET status='active', approved_at=NOW() WHERE id='${r.id}';`,
        );
      }
    }
  }

  return { statusCode: 200, body: 'ok' };
};
