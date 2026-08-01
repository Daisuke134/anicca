const test = require('node:test');
const assert = require('node:assert/strict');

const { writerContentHandler } = require('../../writer-content.js');
const { grantFromStripe, issueEntitlement } = require('../writer-entitlement.js');

const SECRET = 'writer-access-secret-at-least-thirty-two-bytes';
const NOW = 1785639600;
const CLIENT = 'c0f67b0a-f694-48c8-b676-1e0ae15649df';
const ARTICLE = Object.freeze({
  slug: 'reader-useful-proof',
  run_id: '20260802-010000',
  artifact_id: '20260802-010000__self-owned__en',
  lang: 'en',
  access_model: 'both',
  paid_markdown: '## Paid proof\n\nExact private evidence.',
  paid_sha256: '2add5909197bf894427e2410cfd0f6df91547b62c36c8334c88ddca16850c696',
});
const expected = { ...ARTICLE, client_reference_id: CLIENT };
const meta = (product) => ({
  product,
  slug: ARTICLE.slug,
  run_id: ARTICLE.run_id,
  artifact_id: ARTICLE.artifact_id,
  lang: ARTICLE.lang,
  client_reference_id: CLIENT,
});
const session = (overrides = {}) => ({
  id: 'cs_live_writer_1', livemode: true, status: 'complete', mode: 'payment',
  payment_status: 'paid', client_reference_id: CLIENT,
  metadata: meta('writer_article'), ...overrides,
});
const archiveSession = () => ({
  id: 'cs_live_archive_1', livemode: true, status: 'complete', mode: 'subscription',
  payment_status: 'paid', subscription: 'sub_writer_1', client_reference_id: CLIENT,
  metadata: meta('writer_archive'),
});
const activeSubscription = (overrides = {}) => ({
  id: 'sub_writer_1', livemode: true, status: 'active', metadata: meta('writer_archive'), ...overrides,
});

const dependencies = (overrides = {}) => ({
  secret: SECRET,
  liveMode: true,
  nowSeconds: NOW,
  loadArticle: (slug) => slug === ARTICLE.slug ? ARTICLE : null,
  retrieveSession: async () => session(),
  retrieveSubscription: async () => activeSubscription(),
  ...overrides,
});

test('no entitlement returns a generic denial and no paid bytes', async () => {
  const response = await writerContentHandler({
    httpMethod: 'GET', queryStringParameters: { slug: ARTICLE.slug }, headers: {},
  }, dependencies());
  assert.equal(response.statusCode, 401);
  assert.equal(response.body.includes('Exact private evidence'), false);
  assert.equal(response.body.includes('cs_live'), false);
});

test('paid Checkout exchange sets a hardened cookie and returns only the bound paid article', async () => {
  const response = await writerContentHandler({
    httpMethod: 'POST',
    body: JSON.stringify({ session_id: 'cs_live_writer_1', slug: ARTICLE.slug, client_reference_id: CLIENT }),
    headers: {},
  }, dependencies());
  assert.equal(response.statusCode, 200);
  const body = JSON.parse(response.body);
  assert.equal(body.paid_markdown, ARTICLE.paid_markdown);
  assert.equal(body.paid_sha256, ARTICLE.paid_sha256);
  const cookies = response.multiValueHeaders['Set-Cookie'];
  assert.equal(cookies.length, 2);
  assert.equal(cookies.every((cookie) => cookie.includes('HttpOnly')), true);
  assert.equal(cookies.every((cookie) => cookie.includes('Secure')), true);
  assert.equal(cookies.every((cookie) => cookie.includes('SameSite=Lax')), true);
  assert.equal(cookies.some((cookie) => cookie.includes('writer_access=') && cookie.includes('Max-Age=3600')), true);
  assert.equal(cookies.some((cookie) => cookie.includes('writer_receipt_') && cookie.includes('Max-Age=315360000')), true);
  assert.equal(response.body.includes('cs_live_writer_1'), false);
});

test('one-time purchase restores after access expiry from an HttpOnly receipt without another Checkout', async () => {
  const exchange = await writerContentHandler({
    httpMethod: 'POST',
    body: JSON.stringify({ session_id: 'cs_live_writer_1', slug: ARTICLE.slug, client_reference_id: CLIENT }),
    headers: {},
  }, dependencies());
  const receipt = exchange.multiValueHeaders['Set-Cookie']
    .find((cookie) => cookie.startsWith('writer_receipt_'))
    .split(';')[0];
  let sessionFetches = 0;
  const restored = await writerContentHandler({
    httpMethod: 'GET', queryStringParameters: { slug: ARTICLE.slug }, headers: { cookie: receipt },
  }, dependencies({
    nowSeconds: NOW + 3601,
    retrieveSession: async () => { sessionFetches += 1; return session(); },
  }));
  assert.equal(restored.statusCode, 200);
  assert.equal(JSON.parse(restored.body).paid_markdown, ARTICLE.paid_markdown);
  assert.equal(restored.headers['Set-Cookie'].includes('Max-Age=3600'), true);
  assert.equal(sessionFetches, 0);
});

test('unpaid Checkout, wrong client, and wrong slug fail without private bytes or Stripe IDs', async () => {
  const cases = [
    dependencies({ retrieveSession: async () => session({ payment_status: 'unpaid' }) }),
    dependencies(),
    dependencies({ loadArticle: () => null }),
  ];
  const bodies = [
    { session_id: 'cs_live_writer_1', slug: ARTICLE.slug, client_reference_id: CLIENT },
    { session_id: 'cs_live_writer_1', slug: ARTICLE.slug, client_reference_id: 'different-client-reference' },
    { session_id: 'cs_live_writer_1', slug: 'unknown-article', client_reference_id: CLIENT },
  ];
  for (let index = 0; index < cases.length; index += 1) {
    const response = await writerContentHandler({
      httpMethod: 'POST', body: JSON.stringify(bodies[index]), headers: {},
    }, cases[index]);
    assert.equal(response.statusCode >= 400, true);
    assert.equal(response.body.includes('Exact private evidence'), false);
    assert.equal(response.body.includes('cs_live'), false);
  }
});

test('valid article cookie cannot be replayed on another slug', async () => {
  const grant = grantFromStripe({ session: session(), expected, liveMode: true });
  const token = issueEntitlement({ secret: SECRET, grant, nowSeconds: NOW });
  const response = await writerContentHandler({
    httpMethod: 'GET',
    queryStringParameters: { slug: 'another-article' },
    headers: { cookie: `writer_access=${token}` },
  }, dependencies({ loadArticle: () => ({ ...ARTICLE, slug: 'another-article' }) }));
  assert.equal(response.statusCode, 403);
  assert.equal(response.body.includes('Exact private evidence'), false);
});

test('archive cookie is rechecked against Stripe and canceled/past-due access stops', async () => {
  const grant = grantFromStripe({
    session: archiveSession(), subscription: activeSubscription(), expected, liveMode: true,
  });
  const token = issueEntitlement({ secret: SECRET, grant, nowSeconds: NOW });
  for (const status of ['canceled', 'past_due']) {
    const response = await writerContentHandler({
      httpMethod: 'GET',
      queryStringParameters: { slug: ARTICLE.slug },
      headers: { cookie: `writer_access=${token}` },
    }, dependencies({ retrieveSubscription: async () => activeSubscription({ status }) }));
    assert.equal(response.statusCode, 403);
    assert.equal(response.body.includes('Exact private evidence'), false);
  }
});

test('live function rejects test-mode Checkout objects', async () => {
  const response = await writerContentHandler({
    httpMethod: 'POST',
    body: JSON.stringify({ session_id: 'cs_test_writer_1', slug: ARTICLE.slug, client_reference_id: CLIENT }),
    headers: {},
  }, dependencies({ retrieveSession: async () => session({ id: 'cs_test_writer_1', livemode: false }) }));
  assert.equal(response.statusCode, 403);
  assert.equal(response.body.includes('Exact private evidence'), false);
});
