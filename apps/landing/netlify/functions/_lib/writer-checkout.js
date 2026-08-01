const fs = require('node:fs');
const path = require('node:path');
const { validateWriterArticle } = require('./writer-article-contract.js');
const { bundledWriterArticle } = require('./writer-article-registry.generated.js');

const PRODUCTS = new Set(['writer_article', 'writer_archive']);
const REQUEST_FIELDS = new Set([
  'product', 'slug', 'artifact_id', 'run_id', 'lang', 'client_reference_id',
]);
const CLIENT_REFERENCE = /^[A-Za-z0-9_-]{16,64}$/;

function loadWriterArticle(slug, root = path.resolve(__dirname, '../../..')) {
  if (typeof slug !== 'string' || !/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(slug)) {
    return null;
  }
  const bundled = bundledWriterArticle(slug);
  if (bundled) return validateWriterArticle(bundled);
  const file = path.join(root, 'private', 'writer-articles', `${slug}.json`);
  if (!fs.existsSync(file)) return null;
  return validateWriterArticle(JSON.parse(fs.readFileSync(file, 'utf8')));
}

function appendMetadata(params, prefix, values) {
  for (const field of ['slug', 'artifact_id', 'run_id', 'lang', 'client_reference_id']) {
    params.append(`${prefix}[${field}]`, values[field]);
  }
  params.append(`${prefix}[product]`, values.product);
}

function normalizedOrigin(origin) {
  let url;
  try {
    url = new URL(origin);
  } catch {
    throw new TypeError('public origin is invalid');
  }
  if (url.protocol !== 'https:' || url.username || url.password || url.search || url.hash) {
    throw new TypeError('public origin is invalid');
  }
  return url.origin;
}

function buildWriterCheckout({ request, env, lookupArticle = loadWriterArticle, origin }) {
  if (!request || typeof request !== 'object' || Array.isArray(request)) {
    throw new TypeError('Writer checkout request must be an object');
  }
  for (const field of Object.keys(request)) {
    if (!REQUEST_FIELDS.has(field)) throw new TypeError(`unexpected field: ${field}`);
  }
  if (!PRODUCTS.has(request.product)) throw new TypeError('unsupported Writer product');
  if (!CLIENT_REFERENCE.test(request.client_reference_id || '')) {
    throw new TypeError('client_reference_id is invalid');
  }

  const article = lookupArticle(request.slug);
  if (!article) throw new TypeError('unknown article');
  if (
    request.slug !== article.slug
    || request.artifact_id !== article.artifact_id
    || request.run_id !== article.run_id
    || request.lang !== article.lang
  ) {
    throw new TypeError('article lineage mismatch');
  }

  const isArchive = request.product === 'writer_archive';
  const allowed = isArchive
    ? article.access_model === 'archive' || article.access_model === 'both'
    : article.access_model === 'one_time' || article.access_model === 'both';
  if (!allowed) throw new TypeError('article access model does not permit product');

  const priceKey = isArchive
    ? (request.lang === 'ja' ? 'STRIPE_LETTER_JP_PRICE' : 'STRIPE_LETTER_EN_PRICE')
    : (request.lang === 'ja' ? 'STRIPE_WRITER_JP_PRICE' : 'STRIPE_WRITER_EN_PRICE');
  const price = env && env[priceKey];
  if (typeof price !== 'string' || !price.startsWith('price_')) {
    throw new TypeError('missing Writer Price');
  }

  const siteOrigin = normalizedOrigin(origin);
  const articleUrl = `${siteOrigin}/blog/${article.slug}`;
  const params = new URLSearchParams();
  params.append('mode', isArchive ? 'subscription' : 'payment');
  params.append('line_items[0][price]', price);
  params.append('line_items[0][quantity]', '1');
  params.append('client_reference_id', request.client_reference_id);
  params.append('success_url', `${articleUrl}?writer_checkout=success&session_id={CHECKOUT_SESSION_ID}`);
  params.append('cancel_url', `${articleUrl}?writer_checkout=canceled`);
  appendMetadata(params, 'metadata', request);

  if (isArchive) {
    appendMetadata(params, 'subscription_data[metadata]', request);
  } else {
    params.append('customer_creation', 'always');
    appendMetadata(params, 'payment_intent_data[metadata]', request);
  }
  return params;
}

module.exports = { buildWriterCheckout, loadWriterArticle };
