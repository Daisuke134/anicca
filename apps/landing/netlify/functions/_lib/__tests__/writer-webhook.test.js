const test = require('node:test');
const assert = require('node:assert/strict');
const crypto = require('node:crypto');

const { webhookHandler } = require('../../webhook.js');

const SECRET = 'whsec_writer_test';
const NOW = 1785642000;

function signedEvent(payload, overrides = {}) {
  const body = JSON.stringify(payload);
  const timestamp = overrides.timestamp || NOW;
  const signature = crypto.createHmac('sha256', SECRET).update(`${timestamp}.${body}`).digest('hex');
  return {
    httpMethod: 'POST',
    body,
    headers: { 'stripe-signature': `t=${timestamp},v1=${overrides.signature || signature}` },
  };
}

const writerCheckout = (id = 'evt_writer_1') => ({
  id,
  type: 'checkout.session.completed',
  data: { object: {
    id: 'cs_live_writer_1', mode: 'payment',
    metadata: { product: 'writer_article', lang: 'en' },
    customer_details: { email: 'reader@example.com' },
  } },
});

const deps = (overrides = {}) => ({
  env: { STRIPE_WEBHOOK_SECRET: SECRET },
  nowSeconds: NOW,
  sendEmail: async () => { throw new Error('Writer must not send legacy fulfillment'); },
  fetchImpl: async () => { throw new Error('Writer must not write legacy stores'); },
  ...overrides,
});

test('bad and stale Stripe signatures fail before Writer acknowledgement', async () => {
  const bad = await webhookHandler(signedEvent(writerCheckout(), { signature: '0'.repeat(64) }), deps());
  const stale = await webhookHandler(signedEvent(writerCheckout(), { timestamp: NOW - 301 }), deps());
  assert.equal(bad.statusCode, 400);
  assert.equal(stale.statusCode, 400);
});

test('Writer Checkout is acknowledged without ebook or Letter fulfillment', async () => {
  let sends = 0;
  let writes = 0;
  const response = await webhookHandler(signedEvent(writerCheckout()), deps({
    sendEmail: async () => { sends += 1; },
    fetchImpl: async () => { writes += 1; },
  }));
  assert.deepEqual(response, { statusCode: 200, body: 'ok writer' });
  assert.equal(sends, 0);
  assert.equal(writes, 0);
});

test('duplicate Writer event IDs have the same idempotent no-side-effect outcome', async () => {
  let sideEffects = 0;
  const dependencies = deps({
    sendEmail: async () => { sideEffects += 1; },
    fetchImpl: async () => { sideEffects += 1; },
  });
  const event = signedEvent(writerCheckout('evt_duplicate'));
  const first = await webhookHandler(event, dependencies);
  const second = await webhookHandler(event, dependencies);
  assert.equal(first.body, 'ok writer');
  assert.equal(second.body, 'ok writer');
  assert.equal(sideEffects, 0);
});

test('Writer subscription, invoice, refund, and payout events are safely acknowledged', async () => {
  const payloads = [
    { id: 'evt_sub', type: 'customer.subscription.updated', data: { object: { metadata: { product: 'writer_archive' } } } },
    { id: 'evt_invoice', type: 'invoice.paid', data: { object: { subscription_details: { metadata: { product: 'writer_archive' } } } } },
    { id: 'evt_refund', type: 'charge.refunded', data: { object: { metadata: { product: 'writer_article' } } } },
    { id: 'evt_payout', type: 'payout.paid', data: { object: {} } },
  ];
  for (const payload of payloads) {
    const response = await webhookHandler(signedEvent(payload), deps());
    assert.equal(response.body, 'ok writer');
  }
});

test('legacy ebook checkout retains its email fulfillment behavior', async () => {
  let delivered = 0;
  const payload = {
    id: 'evt_ebook', type: 'checkout.session.completed',
    data: { object: {
      id: 'cs_ebook', mode: 'payment', metadata: { product: 'ebook', lang: 'en' },
      customer_details: { email: 'buyer@example.com' }, amount_total: 1099, currency: 'usd',
    } },
  };
  const response = await webhookHandler(signedEvent(payload), deps({
    env: {
      STRIPE_WEBHOOK_SECRET: SECRET,
      STRIPE_SECRET_KEY: 'sk_live_redacted',
      RESEND_API_KEY: 're_redacted',
    },
    sendEmail: async () => { delivered += 1; },
  }));
  assert.equal(response.body, 'ok ebook');
  assert.equal(delivered, 1);
});
