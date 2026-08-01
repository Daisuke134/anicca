const crypto = require('node:crypto');

const ACCESS_MODELS = new Set(['one_time', 'archive', 'both']);
const LANGUAGES = new Set(['ja', 'en']);
const SHA256 = /^[a-f0-9]{64}$/;
const SLUG = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;

function sha256(value) {
  return crypto.createHash('sha256').update(value, 'utf8').digest('hex');
}

function requiredString(value, field) {
  if (typeof value !== 'string' || !value.trim()) {
    throw new TypeError(`${field} is required`);
  }
  return value;
}

function validateWriterArticle(input) {
  if (!input || typeof input !== 'object' || Array.isArray(input)) {
    throw new TypeError('writer article must be an object');
  }
  const value = { ...input };
  for (const field of [
    'slug', 'run_id', 'artifact_id', 'lang', 'title', 'source_sha256',
    'preview_markdown', 'preview_sha256', 'paid_markdown', 'paid_sha256',
    'access_model',
  ]) {
    requiredString(value[field], field);
  }
  if (!SLUG.test(value.slug)) throw new TypeError('slug is invalid');
  if (!LANGUAGES.has(value.lang)) throw new TypeError('lang is unsupported');
  if (!ACCESS_MODELS.has(value.access_model)) throw new TypeError('access_model is unsupported');
  if (value.artifact_id !== `${value.run_id}__self-owned__${value.lang}`) {
    throw new TypeError('artifact_id does not match run/lang lineage');
  }
  for (const field of ['source_sha256', 'preview_sha256', 'paid_sha256']) {
    if (!SHA256.test(value[field])) throw new TypeError(`${field} is invalid`);
  }
  if (value.preview_sha256 !== sha256(value.preview_markdown)) {
    throw new TypeError('preview hash mismatch');
  }
  if (value.paid_sha256 !== sha256(value.paid_markdown)) {
    throw new TypeError('paid hash mismatch');
  }
  if (value.source_sha256 !== sha256(`${value.preview_markdown}\n\n${value.paid_markdown}`)) {
    throw new TypeError('source hash mismatch');
  }
  if (value.paid_markdown.includes(value.preview_markdown)) {
    throw new TypeError('paid body duplicates preview');
  }
  return Object.freeze(value);
}

function publicPreview(input) {
  const value = validateWriterArticle(input);
  return Object.freeze({
    slug: value.slug,
    run_id: value.run_id,
    artifact_id: value.artifact_id,
    lang: value.lang,
    title: value.title,
    source_sha256: value.source_sha256,
    preview_markdown: value.preview_markdown,
    preview_sha256: value.preview_sha256,
    paid_sha256: value.paid_sha256,
    access_model: value.access_model,
  });
}

function publicManifestJson(input) {
  return JSON.stringify(publicPreview(input)).replace(/</g, '\\u003c');
}

module.exports = { validateWriterArticle, publicPreview, publicManifestJson, sha256 };
