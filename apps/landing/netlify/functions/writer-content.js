const {
  grantFromStripe,
  issueEntitlement,
  issueReceipt,
  verifyArchiveSubscription,
  verifyEntitlement,
  verifyReceipt,
} = require('./_lib/writer-entitlement.js');
const { loadWriterArticle } = require('./_lib/writer-checkout.js');

const STRIPE_API_VERSION = '2026-04-22.dahlia';
const COOKIE_NAME = 'writer_access';
const SESSION_ID = /^cs_(?:live|test)_[A-Za-z0-9_]{4,200}$/;
const CLIENT_REFERENCE = /^[A-Za-z0-9_-]{16,64}$/;

function generic(statusCode) {
  return {
    statusCode,
    headers: { 'Content-Type': 'application/json', 'Cache-Control': 'no-store' },
    body: JSON.stringify({ error: 'access unavailable' }),
  };
}

function parseCookies(header) {
  const values = new Map();
  for (const part of String(header || '').split(';')) {
    const index = part.indexOf('=');
    if (index < 0) continue;
    const name = part.slice(0, index).trim();
    if (name) values.set(name, decodeURIComponent(part.slice(index + 1).trim()));
  }
  return values;
}

function receiptCookieName(slug) {
  const digest = require('node:crypto').createHash('sha256').update(slug, 'utf8').digest('hex');
  return `writer_receipt_${digest.slice(0, 16)}`;
}

function expectedLineage(article, clientReference) {
  return {
    slug: article.slug,
    artifact_id: article.artifact_id,
    run_id: article.run_id,
    lang: article.lang,
    client_reference_id: clientReference,
  };
}

function contentResponse(article, { accessToken = null, receiptToken = null } = {}) {
  const headers = { 'Content-Type': 'application/json', 'Cache-Control': 'no-store' };
  const cookies = [];
  if (accessToken) {
    cookies.push(`${COOKIE_NAME}=${encodeURIComponent(accessToken)}; Path=/; Max-Age=3600; HttpOnly; Secure; SameSite=Lax`);
  }
  if (receiptToken) {
    cookies.push(`${receiptCookieName(article.slug)}=${encodeURIComponent(receiptToken)}; Path=/; Max-Age=315360000; HttpOnly; Secure; SameSite=Lax`);
  }
  const response = {
    statusCode: 200,
    headers,
    body: JSON.stringify({
      access: true,
      paid_markdown: article.paid_markdown,
      paid_sha256: article.paid_sha256,
    }),
  };
  if (cookies.length === 1) headers['Set-Cookie'] = cookies[0];
  if (cookies.length > 1) response.multiValueHeaders = { 'Set-Cookie': cookies };
  return response;
}

async function stripeRetrieve(kind, id, key, fetchImpl) {
  const response = await fetchImpl(`https://api.stripe.com/v1/${kind}/${encodeURIComponent(id)}`, {
    headers: {
      Authorization: 'Basic ' + Buffer.from(`${key}:`).toString('base64'),
      'Stripe-Version': STRIPE_API_VERSION,
    },
  });
  if (!response.ok) throw new TypeError('Stripe object unavailable');
  return response.json();
}

async function writerContentHandler(event, dependencies = {}) {
  const env = dependencies.env || process.env;
  const secret = dependencies.secret || env.WRITER_ACCESS_SECRET;
  const stripeKey = env.STRIPE_SECRET_KEY;
  const liveMode = typeof dependencies.liveMode === 'boolean'
    ? dependencies.liveMode
    : Boolean(stripeKey && stripeKey.startsWith('sk_live_'));
  const nowSeconds = dependencies.nowSeconds || Math.floor(Date.now() / 1000);
  const fetchImpl = dependencies.fetchImpl || fetch;
  const loadArticle = dependencies.loadArticle || loadWriterArticle;
  const retrieveSession = dependencies.retrieveSession
    || ((id) => stripeRetrieve('checkout/sessions', id, stripeKey, fetchImpl));
  const retrieveSubscription = dependencies.retrieveSubscription
    || ((id) => stripeRetrieve('subscriptions', id, stripeKey, fetchImpl));

  if (!secret || (!stripeKey && (!dependencies.retrieveSession || !dependencies.retrieveSubscription))) {
    return generic(500);
  }

  if (event.httpMethod === 'POST') {
    let body;
    try {
      body = JSON.parse(event.body || '{}');
    } catch {
      return generic(400);
    }
    if (
      !body || Object.keys(body).some((key) => !['session_id', 'slug', 'client_reference_id'].includes(key))
      || !SESSION_ID.test(body.session_id || '')
      || !CLIENT_REFERENCE.test(body.client_reference_id || '')
    ) {
      return generic(400);
    }
    const article = loadArticle(body.slug);
    if (!article) return generic(404);
    try {
      const session = await retrieveSession(body.session_id);
      let subscription = null;
      if (session && session.metadata && session.metadata.product === 'writer_archive') {
        const subscriptionId = typeof session.subscription === 'string'
          ? session.subscription : session.subscription && session.subscription.id;
        if (!subscriptionId) return generic(403);
        subscription = await retrieveSubscription(subscriptionId);
      }
      const grant = grantFromStripe({
        session,
        subscription,
        expected: expectedLineage(article, body.client_reference_id),
        liveMode,
      });
      const accessToken = issueEntitlement({ secret, grant, nowSeconds });
      const receiptToken = issueReceipt({ secret, grant, nowSeconds });
      return contentResponse(article, { accessToken, receiptToken });
    } catch {
      return generic(403);
    }
  }

  if (event.httpMethod === 'GET') {
    const slug = event.queryStringParameters && event.queryStringParameters.slug;
    const article = loadArticle(slug);
    if (!article) return generic(404);
    const cookies = parseCookies(event.headers && (event.headers.cookie || event.headers.Cookie));
    const token = cookies.get(COOKIE_NAME);
    let claims = null;
    let refreshAccess = false;
    try {
      if (token) claims = verifyEntitlement({ token, secret, slug, nowSeconds });
    } catch {
      claims = null;
    }
    if (!claims) {
      for (const [name, value] of cookies.entries()) {
        if (!name.startsWith('writer_receipt_')) continue;
        try {
          claims = verifyReceipt({ token: value, secret, slug, nowSeconds });
          refreshAccess = true;
          break;
        } catch {
          // Another article's receipt is expected and does not grant this slug.
        }
      }
    }
    if (!claims) return generic(token ? 403 : 401);
    try {
      if (claims.scope === 'article') {
        if (
          claims.artifact_id !== article.artifact_id
          || claims.run_id !== article.run_id
          || claims.lang !== article.lang
        ) throw new TypeError('article changed');
      } else {
        const subscription = await retrieveSubscription(claims.subscription_id);
        verifyArchiveSubscription({ subscription, claims, liveMode });
      }
      const accessToken = refreshAccess
        ? issueEntitlement({ secret, grant: claims, nowSeconds })
        : null;
      return contentResponse(article, { accessToken });
    } catch {
      return generic(403);
    }
  }

  return generic(405);
}

exports.writerContentHandler = writerContentHandler;
exports.handler = (event) => writerContentHandler(event);
