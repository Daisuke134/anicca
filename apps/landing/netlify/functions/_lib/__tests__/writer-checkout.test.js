const test = require('node:test');
const assert = require('node:assert/strict');
const path = require('node:path');
const { spawnSync } = require('node:child_process');

const {
  buildWriterCheckout,
} = require('../writer-checkout.js');
const { checkoutHandler } = require('../../checkout.js');

const ARTICLE = Object.freeze({
  slug: 'reader-useful-proof',
  run_id: '20260802-010000',
  artifact_id: '20260802-010000__self-owned__en',
  lang: 'en',
  access_model: 'both',
});

const ENV = Object.freeze({
  STRIPE_WRITER_JP_PRICE: 'price_writer_ja_500',
  STRIPE_WRITER_EN_PRICE: 'price_writer_en_5',
  STRIPE_LETTER_JP_PRICE: 'price_archive_ja',
  STRIPE_LETTER_EN_PRICE: 'price_archive_en',
});

const request = (overrides = {}) => ({
  product: 'writer_article',
  slug: ARTICLE.slug,
  artifact_id: ARTICLE.artifact_id,
  run_id: ARTICLE.run_id,
  lang: ARTICLE.lang,
  client_reference_id: 'c0f67b0a-f694-48c8-b676-1e0ae15649df',
  ...overrides,
});

const lookupArticle = (slug) => slug === ARTICLE.slug ? ARTICLE : null;

test('one-time Writer checkout uses the server price and exact article lineage', () => {
  const params = buildWriterCheckout({
    request: request(), env: ENV, lookupArticle, origin: 'https://aniccaai.com',
  });

  assert.equal(params.get('mode'), 'payment');
  assert.equal(params.get('line_items[0][price]'), ENV.STRIPE_WRITER_EN_PRICE);
  assert.equal(params.get('client_reference_id'), request().client_reference_id);
  assert.equal(params.get('success_url'), `https://aniccaai.com/blog/${ARTICLE.slug}?writer_checkout=success&session_id={CHECKOUT_SESSION_ID}`);
  assert.equal(params.get('cancel_url'), `https://aniccaai.com/blog/${ARTICLE.slug}?writer_checkout=canceled`);
  for (const field of ['slug', 'artifact_id', 'run_id', 'lang', 'client_reference_id']) {
    assert.equal(params.get(`metadata[${field}]`), request()[field]);
    assert.equal(params.get(`payment_intent_data[metadata][${field}]`), request()[field]);
  }
  assert.equal(params.get('metadata[product]'), 'writer_article');
  assert.equal(params.get('payment_intent_data[metadata][product]'), 'writer_article');
  assert.equal(params.has('subscription_data[metadata][product]'), false);
});

test('archive checkout uses Letter recurring price and copies lineage into Subscription metadata', () => {
  const input = request({ product: 'writer_archive' });
  const params = buildWriterCheckout({
    request: input, env: ENV, lookupArticle, origin: 'https://aniccaai.com',
  });

  assert.equal(params.get('mode'), 'subscription');
  assert.equal(params.get('line_items[0][price]'), ENV.STRIPE_LETTER_EN_PRICE);
  assert.equal(params.has('customer_creation'), false);
  for (const field of ['slug', 'artifact_id', 'run_id', 'lang', 'client_reference_id']) {
    assert.equal(params.get(`metadata[${field}]`), input[field]);
    assert.equal(params.get(`subscription_data[metadata][${field}]`), input[field]);
  }
  assert.equal(params.get('subscription_data[metadata][product]'), 'writer_archive');
});

test('Japanese Writer article uses the fixed Japanese Writer Price', () => {
  const ja = {
    ...ARTICLE,
    lang: 'ja',
    artifact_id: '20260802-010000__self-owned__ja',
  };
  const params = buildWriterCheckout({
    request: request({ lang: 'ja', artifact_id: ja.artifact_id }),
    env: ENV,
    lookupArticle: () => ja,
    origin: 'https://aniccaai.com',
  });
  assert.equal(params.get('line_items[0][price]'), ENV.STRIPE_WRITER_JP_PRICE);
});

test('unknown slug, mismatched lineage, missing client reference, and caller price are rejected', () => {
  const invalid = [
    { value: request({ slug: 'missing' }), lookup: lookupArticle, match: /unknown article/ },
    { value: request({ artifact_id: 'another__self-owned__en' }), lookup: lookupArticle, match: /lineage mismatch/ },
    { value: request({ run_id: '20260802-999999' }), lookup: lookupArticle, match: /lineage mismatch/ },
    { value: request({ lang: 'ja' }), lookup: lookupArticle, match: /lineage mismatch/ },
    { value: request({ client_reference_id: '' }), lookup: lookupArticle, match: /client_reference_id/ },
    { value: request({ price_id: 'price_attacker' }), lookup: lookupArticle, match: /unexpected field/ },
  ];
  for (const item of invalid) {
    assert.throws(
      () => buildWriterCheckout({
        request: item.value, env: ENV, lookupArticle: item.lookup, origin: 'https://aniccaai.com',
      }),
      item.match,
    );
  }
});

test('missing server Price and incompatible article access model fail closed', () => {
  assert.throws(
    () => buildWriterCheckout({ request: request(), env: {}, lookupArticle, origin: 'https://aniccaai.com' }),
    /missing Writer Price/,
  );
  assert.throws(
    () => buildWriterCheckout({
      request: request({ product: 'writer_archive' }),
      env: ENV,
      lookupArticle: () => ({ ...ARTICLE, access_model: 'one_time' }),
      origin: 'https://aniccaai.com',
    }),
    /access model/,
  );
});

test('checkout handler sends the validated Writer params with an explicit Stripe API version', async () => {
  let stripeRequest;
  const response = await checkoutHandler({
    httpMethod: 'POST',
    body: JSON.stringify(request()),
    headers: { origin: 'https://attacker.example' },
  }, {
    env: { ...ENV, STRIPE_SECRET_KEY: 'sk_live_redacted' },
    lookupArticle,
    publicOrigin: 'https://aniccaai.com',
    fetchImpl: async (url, options) => {
      stripeRequest = { url, options };
      return { ok: true, status: 200, json: async () => ({ url: 'https://checkout.stripe.com/c/pay/cs_live' }) };
    },
  });

  assert.equal(response.statusCode, 200);
  assert.equal(JSON.parse(response.body).url, 'https://checkout.stripe.com/c/pay/cs_live');
  assert.equal(stripeRequest.url, 'https://api.stripe.com/v1/checkout/sessions');
  assert.equal(stripeRequest.options.headers['Stripe-Version'], '2026-04-22.dahlia');
  const sent = new URLSearchParams(stripeRequest.options.body);
  assert.equal(sent.get('metadata[artifact_id]'), ARTICLE.artifact_id);
  assert.equal(sent.get('success_url').startsWith('https://aniccaai.com/'), true);
  assert.equal(sent.get('success_url').includes('attacker.example'), false);
});

test('checkout handler rejects bad Writer lineage before touching Stripe', async () => {
  let fetches = 0;
  const response = await checkoutHandler({
    httpMethod: 'POST',
    body: JSON.stringify(request({ artifact_id: 'wrong' })),
  }, {
    env: { ...ENV, STRIPE_SECRET_KEY: 'sk_live_redacted' },
    lookupArticle,
    publicOrigin: 'https://aniccaai.com',
    fetchImpl: async () => { fetches += 1; },
  });
  assert.equal(response.statusCode, 400);
  assert.equal(response.body, 'invalid Writer checkout');
  assert.equal(fetches, 0);
});

test('legacy ebook checkout keeps its existing product and language mapping', async () => {
  let sent;
  const response = await checkoutHandler({
    httpMethod: 'POST',
    body: JSON.stringify({ product: 'ebook', lang: 'jp' }),
    headers: { origin: 'https://aniccaai.com' },
  }, {
    env: { STRIPE_SECRET_KEY: 'sk_live_redacted', STRIPE_JP_PRICE_ID: 'price_ebook_jp' },
    fetchImpl: async (_url, options) => {
      sent = new URLSearchParams(options.body);
      return { ok: true, status: 200, json: async () => ({ url: 'https://checkout.stripe.com/legacy' }) };
    },
  });
  assert.equal(response.statusCode, 200);
  assert.equal(sent.get('metadata[product]'), 'ebook');
  assert.equal(sent.get('metadata[lang]'), 'jp');
  assert.equal(sent.get('line_items[0][price]'), 'price_ebook_jp');
});

test('bundled Writer lookup is independent of the Lambda working directory', () => {
  const modulePath = path.resolve(__dirname, '../writer-checkout.js');
  const script = `
    const { loadWriterArticle } = require(${JSON.stringify(modulePath)});
    const article = loadWriterArticle('aipass5');
    if (!article) process.exit(2);
    process.stdout.write(JSON.stringify({ slug: article.slug, run_id: article.run_id }));
  `;
  const result = spawnSync(process.execPath, ['-e', script], {
    cwd: path.resolve(__dirname, '..'),
    encoding: 'utf8',
  });

  assert.equal(result.status, 0, result.stderr || 'Writer contract was not found');
  assert.deepEqual(JSON.parse(result.stdout), {
    slug: 'aipass5',
    run_id: '20260731-213927',
  });
});
