// Anicca Retreats — Build the Center Stripe Webhook
// Handles checkout.session.completed events for product=retreat-build-fund:
//   1. Slack #metrics notification (donor email + amount + tier)
//   2. Resend thank-you email to donor
//   3. (Future) Update dashboard.json or Supabase retreat_donations table
//
// Stripe sends POST with signature header. We verify with STRIPE_WEBHOOK_SECRET.
// Configure in Stripe Dashboard → Developers → Webhooks → Add endpoint:
//   https://aniccaai.com/.netlify/functions/retreat-build-webhook
//   events: checkout.session.completed

const crypto = require('crypto');

function verifySignature(payload, sigHeader, secret) {
  if (!sigHeader || !secret) return false;
  // Format: t=<ts>,v1=<sig>
  const parts = sigHeader.split(',').reduce((acc, p) => {
    const [k, v] = p.split('=');
    if (k === 't') acc.timestamp = v;
    if (k === 'v1') acc.signatures = (acc.signatures || []).concat(v);
    return acc;
  }, {});
  if (!parts.timestamp || !parts.signatures?.length) return false;
  const signedPayload = `${parts.timestamp}.${payload}`;
  const expected = crypto.createHmac('sha256', secret).update(signedPayload, 'utf8').digest('hex');
  return parts.signatures.some((s) =>
    crypto.timingSafeEqual(Buffer.from(s, 'hex'), Buffer.from(expected, 'hex'))
  );
}

exports.handler = async (event) => {
  if (event.httpMethod !== 'POST') return { statusCode: 405, body: 'method not allowed' };

  const STRIPE_WEBHOOK_SECRET = process.env.STRIPE_WEBHOOK_SECRET_RETREAT_BUILD;
  const SLACK_BOT_TOKEN = process.env.SLACK_BOT_TOKEN;
  const SLACK_CHANNEL = process.env.SLACK_CHANNEL_METRICS || 'C091G3PKHL2';
  const RESEND_API_KEY = process.env.RESEND_API_KEY;

  const payload = event.body || '';
  const sig = event.headers['stripe-signature'] || event.headers['Stripe-Signature'];

  if (STRIPE_WEBHOOK_SECRET) {
    if (!verifySignature(payload, sig, STRIPE_WEBHOOK_SECRET)) {
      return { statusCode: 400, body: 'invalid signature' };
    }
  }

  let evt;
  try { evt = JSON.parse(payload); }
  catch { return { statusCode: 400, body: 'bad json' }; }

  if (evt.type !== 'checkout.session.completed') {
    return { statusCode: 200, body: JSON.stringify({ ok: true, ignored: evt.type }) };
  }

  const session = evt.data?.object || {};
  const metadata = session.metadata || {};
  if (metadata.product !== 'retreat-build-fund') {
    return { statusCode: 200, body: JSON.stringify({ ok: true, ignored_product: metadata.product || 'unknown' }) };
  }

  const amount = session.amount_total || 0;
  const currency = (session.currency || 'jpy').toUpperCase();
  const customerEmail = session.customer_details?.email || 'anonymous';
  const customerName = session.customer_details?.name || 'a friend of the sangha';
  const tierLabel = metadata.tier_label || 'donation';
  const sessionId = session.id;

  // 1. Slack notify
  if (SLACK_BOT_TOKEN) {
    const text = `🏗 *Anicca Retreats — Build the Center: NEW DONATION* ❤️
*amount*: ${currency} ${amount.toLocaleString()}
*tier*: ${tierLabel}
*donor*: ${customerName} (\`${customerEmail}\`)
*session*: \`${sessionId}\`

Total updates appear on https://aniccaai.com/retreat/build (live progress bar via dashboard.json).`;
    await fetch('https://slack.com/api/chat.postMessage', {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${SLACK_BOT_TOKEN}`,
        'Content-Type': 'application/json; charset=utf-8',
      },
      body: JSON.stringify({ channel: SLACK_CHANNEL, text, mrkdwn: true }),
    }).catch(() => {});
  }

  // 2. Resend thank-you email to donor
  if (RESEND_API_KEY && customerEmail !== 'anonymous') {
    await fetch('https://api.resend.com/emails', {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${RESEND_API_KEY}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        from: 'Anicca Retreats <onboarding@resend.dev>',
        to: customerEmail,
        subject: 'Thank you — your gift toward the Anicca Retreat Center',
        html: `<p>Dear ${customerName},</p>
<p>Thank you for your gift of <strong>${currency} ${amount.toLocaleString()}</strong> toward building the first Anicca Retreat Center.</p>
<p>You picked the <strong>${tierLabel}</strong> tier. Every yen goes to the building — Anicca pays Stripe's processing fee out of cafe profit, so 100% of your gift becomes the land, the meditation hall, the kitchen, the silent rooms.</p>
<p>You can see live progress at <a href="https://aniccaai.com/retreat/build">aniccaai.com/retreat/build</a>.</p>
<p>We'll send one update per month — what we found, what we built, what came next. No spam. You can reply to this email with anything.</p>
<p>With gratitude,<br/>
Anicca<br/>
retreat@aniccaai.com</p>
<hr/>
<p><small>Receipt: Stripe session ${sessionId}</small></p>`,
      }),
    }).catch(() => {});
  }

  return {
    statusCode: 200,
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      ok: true,
      session_id: sessionId,
      amount,
      currency,
      tier: tierLabel,
    }),
  };
};
