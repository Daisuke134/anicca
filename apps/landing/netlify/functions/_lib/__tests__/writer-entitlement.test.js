const test = require('node:test');
const assert = require('node:assert/strict');

const {
  grantFromStripe,
  issueEntitlement,
  verifyEntitlement,
} = require('../writer-entitlement.js');

const SECRET = 'writer-access-secret-at-least-thirty-two-bytes';
const NOW = 1785639600;
const EXPECTED = Object.freeze({
  slug: 'reader-useful-proof',
  run_id: '20260802-010000',
  artifact_id: '20260802-010000__self-owned__en',
  lang: 'en',
  client_reference_id: 'c0f67b0a-f694-48c8-b676-1e0ae15649df',
});

function metadata(product, overrides = {}) {
  return { product, ...EXPECTED, ...overrides };
}

function paidSession(overrides = {}) {
  return {
    id: 'cs_live_writer_1',
    livemode: true,
    status: 'complete',
    mode: 'payment',
    payment_status: 'paid',
    client_reference_id: EXPECTED.client_reference_id,
    metadata: metadata('writer_article'),
    ...overrides,
  };
}

function archiveSession(overrides = {}) {
  return {
    id: 'cs_live_writer_archive_1',
    livemode: true,
    status: 'complete',
    mode: 'subscription',
    payment_status: 'paid',
    subscription: 'sub_writer_1',
    client_reference_id: EXPECTED.client_reference_id,
    metadata: metadata('writer_archive'),
    ...overrides,
  };
}

function subscription(overrides = {}) {
  return {
    id: 'sub_writer_1',
    livemode: true,
    status: 'active',
    metadata: metadata('writer_archive'),
    ...overrides,
  };
}

test('paid live one-time Checkout grants only its exact article', () => {
  const grant = grantFromStripe({ session: paidSession(), expected: EXPECTED, liveMode: true });
  const token = issueEntitlement({ secret: SECRET, grant, nowSeconds: NOW });
  const claims = verifyEntitlement({ token, secret: SECRET, slug: EXPECTED.slug, nowSeconds: NOW + 3599 });

  assert.equal(grant.scope, 'article');
  assert.equal(claims.artifact_id, EXPECTED.artifact_id);
  assert.equal(claims.checkout_session_id, 'cs_live_writer_1');
  assert.throws(
    () => verifyEntitlement({ token, secret: SECRET, slug: 'another-article', nowSeconds: NOW + 1 }),
    /wrong article/,
  );
});

test('active or trialing live archive Subscription grants archive scope', () => {
  for (const status of ['active', 'trialing']) {
    const grant = grantFromStripe({
      session: archiveSession(),
      subscription: subscription({ status }),
      expected: EXPECTED,
      liveMode: true,
    });
    const token = issueEntitlement({ secret: SECRET, grant, nowSeconds: NOW });
    const claims = verifyEntitlement({ token, secret: SECRET, slug: 'another-paid-article', nowSeconds: NOW + 10 });
    assert.equal(claims.scope, 'archive');
    assert.equal(claims.subscription_id, 'sub_writer_1');
  }
});

test('tampered, expired, and wrong-secret bearer tokens fail closed', () => {
  const grant = grantFromStripe({ session: paidSession(), expected: EXPECTED, liveMode: true });
  const token = issueEntitlement({ secret: SECRET, grant, nowSeconds: NOW });
  const tampered = `${token.slice(0, -1)}${token.endsWith('a') ? 'b' : 'a'}`;
  assert.throws(() => verifyEntitlement({ token: tampered, secret: SECRET, slug: EXPECTED.slug, nowSeconds: NOW }), /signature/);
  assert.throws(() => verifyEntitlement({ token, secret: SECRET, slug: EXPECTED.slug, nowSeconds: NOW + 3600 }), /expired/);
  assert.throws(() => verifyEntitlement({ token, secret: `${SECRET}x`, slug: EXPECTED.slug, nowSeconds: NOW }), /signature/);
});

test('unpaid/incomplete Checkout, bad lineage, and test/live mismatch never grant', () => {
  const invalid = [
    paidSession({ payment_status: 'unpaid' }),
    paidSession({ status: 'open' }),
    paidSession({ metadata: metadata('writer_article', { artifact_id: 'wrong' }) }),
    paidSession({ client_reference_id: 'another-client-reference' }),
    paidSession({ livemode: false, id: 'cs_test_writer_1' }),
  ];
  for (const session of invalid) {
    assert.throws(
      () => grantFromStripe({ session, expected: EXPECTED, liveMode: true }),
    );
  }
});

test('canceled, past-due, mismatched, and test-mode archive Subscriptions never grant live access', () => {
  const invalid = [
    subscription({ status: 'canceled' }),
    subscription({ status: 'past_due' }),
    subscription({ id: 'sub_wrong' }),
    subscription({ metadata: metadata('writer_archive', { run_id: 'wrong' }) }),
    subscription({ livemode: false }),
  ];
  for (const sub of invalid) {
    assert.throws(() => grantFromStripe({
      session: archiveSession(), subscription: sub, expected: EXPECTED, liveMode: true,
    }));
  }
});
