import test from 'node:test';
import assert from 'node:assert/strict';
import { createHmac } from 'node:crypto';
import { mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

import { openThe402Inbox } from '../lib/the402-inbox.mjs';
import { handleThe402WebhookRequest } from '../lib/the402-webhook-handler.mjs';

const NOW_MS = 1_784_756_503_000;
const API_KEY = 'sk_test_agent_only';
const WEBHOOK_SECRET = 'whsec_test_agent_only';

function withTempInbox(run) {
  const dir = mkdtempSync(join(tmpdir(), 'anicca-the402-handler-'));
  const inbox = openThe402Inbox(join(dir, 'inbox.sqlite'));
  return Promise.resolve(run(inbox)).finally(() => {
    inbox.close();
    rmSync(dir, { recursive: true, force: true });
  });
}

function signedRequest(rawBody, overrides = {}) {
  const timestamp = String(NOW_MS / 1_000);
  const signature = createHmac('sha256', WEBHOOK_SECRET)
    .update(`${timestamp}.${rawBody}`)
    .digest('hex');
  return new Request('https://seller.example/webhooks/the402', {
    method: 'POST',
    headers: {
      'content-type': 'application/json',
      'x-platform-secret': API_KEY,
      'x-webhook-timestamp': timestamp,
      'x-webhook-signature': `sha256=${signature}`,
      ...overrides,
    },
    body: rawBody,
  });
}

test('returns a prompt 200 only after the signed event is durably queued', () => withTempInbox(async (inbox) => {
  const rawBody = JSON.stringify({
    type: 'request.created',
    posting_id: 'post_signed',
    title: 'Private buyer request',
  });
  const response = await handleThe402WebhookRequest(signedRequest(rawBody), {
    inbox,
    apiKey: API_KEY,
    webhookSecret: WEBHOOK_SECRET,
    nowMs: NOW_MS,
  });

  assert.equal(response.status, 200);
  assert.equal(response.headers.get('cache-control'), 'no-store');
  assert.deepEqual(await response.json(), {
    ok: true,
    accepted: true,
    duplicate: false,
    type: 'request.created',
    eventId: 'request.created:post_signed',
    status: 'pending',
  });
  assert.deepEqual(inbox.stats(), {
    total: 1,
    pending: 1,
    processing: 0,
    completed: 0,
    dead: 0,
  });
}));

test('rejects forged and oversized bodies without enqueueing either event', () => withTempInbox(async (inbox) => {
  const rawBody = JSON.stringify({
    type: 'job_dispatch',
    job_id: 'job_forged',
    brief: { objective: 'must never be queued' },
  });
  const forged = await handleThe402WebhookRequest(signedRequest(rawBody, {
    'x-webhook-signature': `sha256=${'0'.repeat(64)}`,
  }), {
    inbox,
    apiKey: API_KEY,
    webhookSecret: WEBHOOK_SECRET,
    nowMs: NOW_MS,
  });
  assert.equal(forged.status, 401);
  assert.deepEqual(await forged.json(), { ok: false, error: 'unauthorized' });
  assert.equal(inbox.stats().total, 0);

  const oversized = await handleThe402WebhookRequest(signedRequest('x'.repeat(129)), {
    inbox,
    apiKey: API_KEY,
    webhookSecret: WEBHOOK_SECRET,
    nowMs: NOW_MS,
    maxBodyBytes: 128,
  });
  assert.equal(oversized.status, 413);
  assert.deepEqual(await oversized.json(), { ok: false, error: 'payload_too_large' });
  assert.equal(inbox.stats().total, 0);
}));

test('fails closed on method, media type, malformed events, and missing server secrets', () => withTempInbox(async (inbox) => {
  const get = await handleThe402WebhookRequest(new Request('https://seller.example/webhooks/the402'), {
    inbox,
    apiKey: API_KEY,
    webhookSecret: WEBHOOK_SECRET,
    nowMs: NOW_MS,
  });
  assert.equal(get.status, 405);
  assert.equal(get.headers.get('allow'), 'POST');

  const rawBody = JSON.stringify({ type: 'job_dispatch', job_id: 'job_media' });
  const media = await handleThe402WebhookRequest(signedRequest(rawBody, {
    'content-type': 'text/plain',
  }), {
    inbox,
    apiKey: API_KEY,
    webhookSecret: WEBHOOK_SECRET,
    nowMs: NOW_MS,
  });
  assert.equal(media.status, 415);

  const malformed = await handleThe402WebhookRequest(signedRequest('{'), {
    inbox,
    apiKey: API_KEY,
    webhookSecret: WEBHOOK_SECRET,
    nowMs: NOW_MS,
  });
  assert.equal(malformed.status, 400);
  assert.deepEqual(await malformed.json(), { ok: false, error: 'invalid_event' });

  const unconfigured = await handleThe402WebhookRequest(signedRequest(rawBody), {
    inbox,
    apiKey: API_KEY,
    webhookSecret: '',
    nowMs: NOW_MS,
  });
  assert.equal(unconfigured.status, 503);
  assert.deepEqual(await unconfigured.json(), { ok: false, error: 'temporarily_unavailable' });
  assert.equal(inbox.stats().total, 0);
}));
