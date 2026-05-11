// Anicca Retreats — Build the Center Stripe Checkout
// POST { amount_jpy, tier_label } → returns { url } to Stripe Checkout
exports.handler = async (event) => {
  if (event.httpMethod !== 'POST') return { statusCode: 405, body: 'method not allowed' };
  let body;
  try { body = JSON.parse(event.body || '{}'); }
  catch { return { statusCode: 400, body: 'bad json' }; }

  const amountJpy = parseInt(body.amount_jpy, 10);
  const tierLabel = String(body.tier_label || 'donation').slice(0, 80);
  if (!amountJpy || amountJpy < 100 || amountJpy > 100_000_000) {
    return { statusCode: 400, body: 'invalid amount' };
  }

  const STRIPE_KEY = process.env.STRIPE_SECRET_KEY;
  const SLACK_BOT_TOKEN = process.env.SLACK_BOT_TOKEN;
  const SLACK_CHANNEL = process.env.SLACK_CHANNEL_METRICS || 'C091G3PKHL2';

  if (!STRIPE_KEY) {
    return { statusCode: 500, body: 'stripe not configured' };
  }

  // Build success/cancel URLs
  const proto = event.headers['x-forwarded-proto'] || 'https';
  const host = event.headers.host || 'aniccaai.com';
  const successUrl = `${proto}://${host}/retreat/build?status=success&session_id={CHECKOUT_SESSION_ID}`;
  const cancelUrl = `${proto}://${host}/retreat/build?status=cancel`;

  // Stripe Checkout Session — donation mode (one-off, customer-supplied amount)
  const params = new URLSearchParams();
  params.append('mode', 'payment');
  params.append('success_url', successUrl);
  params.append('cancel_url', cancelUrl);
  params.append('payment_method_types[0]', 'card');
  params.append('line_items[0][price_data][currency]', 'jpy');
  params.append('line_items[0][price_data][product_data][name]', `Anicca Retreats — Build the Center`);
  params.append('line_items[0][price_data][product_data][description]', `Tier: ${tierLabel}`);
  params.append('line_items[0][price_data][unit_amount]', String(amountJpy));
  params.append('line_items[0][quantity]', '1');
  params.append('metadata[product]', 'retreat-build-fund');
  params.append('metadata[tier_label]', tierLabel);
  params.append('metadata[amount_jpy]', String(amountJpy));
  params.append('submit_type', 'donate');

  let session;
  try {
    const r = await fetch('https://api.stripe.com/v1/checkout/sessions', {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${STRIPE_KEY}`,
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: params.toString(),
    });
    session = await r.json();
    if (!r.ok || !session?.url) {
      console.error('Stripe Checkout error', session);
      return { statusCode: 502, body: JSON.stringify({ error: 'stripe failure', detail: session }) };
    }
  } catch (e) {
    return { statusCode: 502, body: JSON.stringify({ error: 'stripe network', detail: String(e) }) };
  }

  // Slack notify (intent — not yet paid)
  if (SLACK_BOT_TOKEN) {
    fetch('https://slack.com/api/chat.postMessage', {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${SLACK_BOT_TOKEN}`,
        'Content-Type': 'application/json; charset=utf-8',
      },
      body: JSON.stringify({
        channel: SLACK_CHANNEL,
        text: `🏗 *Anicca Retreats — Build* — Checkout intent\n*tier:* ${tierLabel}\n*amount:* ¥${amountJpy.toLocaleString()}\n*session:* \`${session.id}\`\n\nWaiting for completion (webhook will fire on success).`,
        mrkdwn: true,
      }),
    }).catch(() => {});
  }

  return {
    statusCode: 200,
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ url: session.url, session_id: session.id }),
  };
};
