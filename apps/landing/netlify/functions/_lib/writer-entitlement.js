const crypto = require('node:crypto');

const LINEAGE_FIELDS = ['slug', 'artifact_id', 'run_id', 'lang', 'client_reference_id'];
const ACTIVE_SUBSCRIPTION = new Set(['active', 'trialing']);

function requireSecret(secret) {
  if (typeof secret !== 'string' || Buffer.byteLength(secret, 'utf8') < 32) {
    throw new TypeError('access secret is invalid');
  }
}

function objectId(value) {
  return typeof value === 'string' ? value : value && value.id;
}

function requireLineage(source, expected, label) {
  for (const field of LINEAGE_FIELDS) {
    if (typeof expected[field] !== 'string' || !expected[field]) {
      throw new TypeError(`expected ${field} is invalid`);
    }
    if (source[field] !== expected[field]) {
      throw new TypeError(`${label} lineage mismatch`);
    }
  }
}

function grantFromStripe({ session, subscription = null, expected, liveMode }) {
  if (!session || typeof session !== 'object' || !expected || typeof expected !== 'object') {
    throw new TypeError('Stripe entitlement input is invalid');
  }
  if (typeof liveMode !== 'boolean' || session.livemode !== liveMode) {
    throw new TypeError('Checkout livemode mismatch');
  }
  if (session.status !== 'complete') throw new TypeError('Checkout is incomplete');
  requireLineage(session.metadata || {}, expected, 'Checkout');
  if (session.client_reference_id !== expected.client_reference_id) {
    throw new TypeError('Checkout client reference mismatch');
  }

  const product = session.metadata && session.metadata.product;
  if (product === 'writer_article') {
    if (session.mode !== 'payment' || session.payment_status !== 'paid') {
      throw new TypeError('article payment is not paid');
    }
    return Object.freeze({
      scope: 'article',
      ...expected,
      checkout_session_id: session.id,
      subscription_id: null,
    });
  }

  if (product !== 'writer_archive') throw new TypeError('Writer product is invalid');
  if (session.mode !== 'subscription' || !['paid', 'no_payment_required'].includes(session.payment_status)) {
    throw new TypeError('archive Checkout is invalid');
  }
  if (!subscription || subscription.livemode !== liveMode) {
    throw new TypeError('Subscription livemode mismatch');
  }
  if (objectId(session.subscription) !== subscription.id) {
    throw new TypeError('Subscription does not match Checkout');
  }
  if (!ACTIVE_SUBSCRIPTION.has(subscription.status)) {
    throw new TypeError('Subscription is inactive');
  }
  if (!subscription.metadata || subscription.metadata.product !== 'writer_archive') {
    throw new TypeError('Subscription product is invalid');
  }
  requireLineage(subscription.metadata, expected, 'Subscription');
  return Object.freeze({
    scope: 'archive',
    ...expected,
    checkout_session_id: session.id,
    subscription_id: subscription.id,
  });
}

function verifyArchiveSubscription({ subscription, claims, liveMode }) {
  if (!subscription || !claims || claims.scope !== 'archive') {
    throw new TypeError('archive entitlement is invalid');
  }
  if (subscription.livemode !== liveMode || subscription.id !== claims.subscription_id) {
    throw new TypeError('Subscription identity is invalid');
  }
  if (!ACTIVE_SUBSCRIPTION.has(subscription.status)) {
    throw new TypeError('Subscription is inactive');
  }
  if (!subscription.metadata || subscription.metadata.product !== 'writer_archive') {
    throw new TypeError('Subscription product is invalid');
  }
  requireLineage(subscription.metadata, claims, 'Subscription');
  return true;
}

function encodeJson(value) {
  return Buffer.from(JSON.stringify(value), 'utf8').toString('base64url');
}

function sign(body, secret) {
  return crypto.createHmac('sha256', secret).update(body, 'utf8').digest('base64url');
}

function issueSigned({ secret, grant, nowSeconds, ttlSeconds, kind }) {
  requireSecret(secret);
  if (!grant || !['article', 'archive'].includes(grant.scope)) {
    throw new TypeError('grant is invalid');
  }
  if (!Number.isSafeInteger(nowSeconds) || !Number.isSafeInteger(ttlSeconds) || ttlSeconds < 1) {
    throw new TypeError('entitlement lifetime is invalid');
  }
  const claims = {
    v: 1,
    kind,
    scope: grant.scope,
    slug: grant.slug,
    artifact_id: grant.artifact_id,
    run_id: grant.run_id,
    lang: grant.lang,
    client_reference_id: grant.client_reference_id,
    checkout_session_id: grant.checkout_session_id,
    subscription_id: grant.subscription_id,
    iat: nowSeconds,
    exp: nowSeconds + ttlSeconds,
    nonce: crypto.randomBytes(16).toString('base64url'),
  };
  const body = encodeJson(claims);
  return `${body}.${sign(body, secret)}`;
}

function issueEntitlement({ secret, grant, nowSeconds = Math.floor(Date.now() / 1000), ttlSeconds = 3600 }) {
  if (ttlSeconds !== 3600) throw new TypeError('entitlement lifetime is invalid');
  return issueSigned({ secret, grant, nowSeconds, ttlSeconds, kind: 'access' });
}

function issueReceipt({ secret, grant, nowSeconds = Math.floor(Date.now() / 1000) }) {
  return issueSigned({ secret, grant, nowSeconds, ttlSeconds: 315360000, kind: 'receipt' });
}

function verifySigned({ token, secret, slug, nowSeconds, kind, lifetime }) {
  requireSecret(secret);
  if (typeof token !== 'string' || typeof slug !== 'string') throw new TypeError('entitlement is invalid');
  const pieces = token.split('.');
  if (pieces.length !== 2) throw new TypeError('entitlement signature is invalid');
  const actual = Buffer.from(pieces[1], 'base64url');
  const expected = Buffer.from(sign(pieces[0], secret), 'base64url');
  if (actual.length !== expected.length || !crypto.timingSafeEqual(actual, expected)) {
    throw new TypeError('entitlement signature is invalid');
  }
  let claims;
  try {
    claims = JSON.parse(Buffer.from(pieces[0], 'base64url').toString('utf8'));
  } catch {
    throw new TypeError('entitlement payload is invalid');
  }
  if (
    claims.v !== 1
    || claims.kind !== kind
    || !['article', 'archive'].includes(claims.scope)
    || !Number.isSafeInteger(claims.iat)
    || !Number.isSafeInteger(claims.exp)
    || claims.exp - claims.iat !== lifetime
    || nowSeconds < claims.iat
    || nowSeconds >= claims.exp
  ) {
    throw new TypeError(nowSeconds >= claims.exp ? 'entitlement expired' : 'entitlement claims are invalid');
  }
  if (claims.scope === 'article' && claims.slug !== slug) {
    throw new TypeError('entitlement is for wrong article');
  }
  for (const field of ['artifact_id', 'run_id', 'lang', 'client_reference_id', 'checkout_session_id']) {
    if (typeof claims[field] !== 'string' || !claims[field]) {
      throw new TypeError('entitlement claims are invalid');
    }
  }
  if (claims.scope === 'archive' && (typeof claims.subscription_id !== 'string' || !claims.subscription_id)) {
    throw new TypeError('entitlement claims are invalid');
  }
  return Object.freeze(claims);
}

function verifyEntitlement({ token, secret, slug, nowSeconds = Math.floor(Date.now() / 1000) }) {
  return verifySigned({ token, secret, slug, nowSeconds, kind: 'access', lifetime: 3600 });
}

function verifyReceipt({ token, secret, slug, nowSeconds = Math.floor(Date.now() / 1000) }) {
  return verifySigned({ token, secret, slug, nowSeconds, kind: 'receipt', lifetime: 315360000 });
}

module.exports = {
  grantFromStripe,
  issueEntitlement,
  issueReceipt,
  verifyArchiveSubscription,
  verifyEntitlement,
  verifyReceipt,
};
