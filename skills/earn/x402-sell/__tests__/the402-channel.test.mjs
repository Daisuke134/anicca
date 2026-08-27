import test from 'node:test';
import assert from 'node:assert/strict';
import { createHmac } from 'node:crypto';

import {
  THE402_BASE_USDC,
  THE402_REGISTER_PAY_TO,
  THE402_REGISTER_URL,
  privacySafeThe402Audit,
  validateThe402RegistrationChallenge,
  verifyThe402Webhook,
} from '../lib/the402-channel.mjs';

const SELF = '0x1111111111111111111111111111111111111111';
const API_KEY = 'sk_test_agent_only';
const WEBHOOK_SECRET = 'whsec_test_agent_only';
const NOW_MS = 1_784_755_727_000;

function registrationChallenge(overrides = {}) {
  return {
    x402Version: 1,
    accepts: [{
      scheme: 'exact',
      network: 'base',
      maxAmountRequired: '10000',
      resource: THE402_REGISTER_URL,
      payTo: THE402_REGISTER_PAY_TO,
      asset: THE402_BASE_USDC,
      ...overrides,
    }],
  };
}

function signedHeaders(rawBody, {
  timestamp = String(NOW_MS / 1000),
  secret = WEBHOOK_SECRET,
  platformSecret = API_KEY,
} = {}) {
  const digest = createHmac('sha256', secret)
    .update(`${timestamp}.${rawBody}`)
    .digest('hex');
  return {
    'x-platform-secret': platformSecret,
    'x-webhook-timestamp': timestamp,
    'x-webhook-signature': `sha256=${digest}`,
  };
}

test('accepts only the measured external the402 registration requirement', () => {
  const requirement = validateThe402RegistrationChallenge(registrationChallenge(), {
    selfWallets: [SELF],
  });

  assert.deepEqual(requirement, {
    x402Version: 1,
    scheme: 'exact',
    network: 'base',
    amountAtomic: 10_000n,
    asset: THE402_BASE_USDC.toLowerCase(),
    payTo: THE402_REGISTER_PAY_TO.toLowerCase(),
    resource: THE402_REGISTER_URL,
  });
});

test('registration guard fails closed on price, chain, asset, recipient, resource, scheme, or ambiguity drift', () => {
  const cases = [
    registrationChallenge({ maxAmountRequired: '10001' }),
    registrationChallenge({ network: 'eip155:8453' }),
    registrationChallenge({ asset: SELF }),
    registrationChallenge({ payTo: SELF }),
    registrationChallenge({ payTo: '0x2222222222222222222222222222222222222222' }),
    registrationChallenge({ resource: `${THE402_REGISTER_URL}?changed=1` }),
    registrationChallenge({ scheme: 'upto' }),
    { ...registrationChallenge(), x402Version: 2 },
    { ...registrationChallenge(), accepts: [registrationChallenge().accepts[0], registrationChallenge().accepts[0]] },
  ];

  for (const challenge of cases) {
    assert.throws(
      () => validateThe402RegistrationChallenge(challenge, { selfWallets: [SELF] }),
      /the402 registration requirement rejected/,
    );
  }
});

test('verifies the402 raw-body HMAC, API-key header, timestamp window, and stable job id', () => {
  const rawBody = JSON.stringify({
    type: 'job_dispatch',
    job_id: 'job_abc123',
    service_id: 'svc_research',
    brief: { objective: 'private buyer brief' },
  });

  const verified = verifyThe402Webhook({
    rawBody,
    headers: signedHeaders(rawBody),
    apiKey: API_KEY,
    webhookSecret: WEBHOOK_SECRET,
    nowMs: NOW_MS,
  });

  assert.equal(verified.eventId, 'job_dispatch:job_abc123');
  assert.equal(verified.type, 'job_dispatch');
  assert.deepEqual(verified.payload.brief, { objective: 'private buyer brief' });
});

test('webhook verifier rejects forged, mutated, stale, future, wrong-key, and unknown events', () => {
  const rawBody = JSON.stringify({ type: 'job_dispatch', job_id: 'job_abc123' });
  const valid = signedHeaders(rawBody);
  const cases = [
    { rawBody: `${rawBody} `, headers: valid },
    { rawBody, headers: { ...valid, 'x-webhook-signature': `sha256=${'0'.repeat(64)}` } },
    { rawBody, headers: signedHeaders(rawBody, { timestamp: String(NOW_MS / 1000 - 301) }) },
    { rawBody, headers: signedHeaders(rawBody, { timestamp: String(NOW_MS / 1000 + 301) }) },
    { rawBody, headers: signedHeaders(rawBody, { platformSecret: 'wrong-api-key' }) },
    { rawBody: JSON.stringify({ type: 'unknown', job_id: 'job_abc123' }), headers: null },
    { rawBody: JSON.stringify({ type: 'job_dispatch' }), headers: null },
  ];
  cases[5].headers = signedHeaders(cases[5].rawBody);
  cases[6].headers = signedHeaders(cases[6].rawBody);

  for (const item of cases) {
    assert.throws(() => verifyThe402Webhook({
      rawBody: item.rawBody,
      headers: item.headers,
      apiKey: API_KEY,
      webhookSecret: WEBHOOK_SECRET,
      nowMs: NOW_MS,
    }), /the402 webhook rejected/);
  }
});

test('accepts the documented API-key-only dispatch only when compatibility is explicit', () => {
  const rawBody = JSON.stringify({ type: 'job_dispatch', job_id: 'job_api_key_only' });
  const headers = { 'x-platform-secret': API_KEY };

  assert.throws(() => verifyThe402Webhook({
    rawBody,
    headers,
    apiKey: API_KEY,
    webhookSecret: WEBHOOK_SECRET,
    nowMs: NOW_MS,
  }), /the402 webhook rejected/);

  assert.equal(verifyThe402Webhook({
    rawBody,
    headers,
    apiKey: API_KEY,
    webhookSecret: WEBHOOK_SECRET,
    allowApiKeyOnly: true,
    nowMs: NOW_MS,
  }).eventId, 'job_dispatch:job_api_key_only');
});

test('privacy-safe webhook audit never includes buyer brief, raw body, headers, or secrets', () => {
  const row = privacySafeThe402Audit({
    ts: '2026-07-22T21:48:47.000Z',
    type: 'job_dispatch',
    eventId: 'job_dispatch:job_abc123',
    status: 'verified',
    brief: { objective: 'private buyer brief' },
    rawBody: 'private raw body',
    headers: { authorization: 'secret' },
    apiKey: API_KEY,
    webhookSecret: WEBHOOK_SECRET,
  });

  assert.deepEqual(row, {
    ts: '2026-07-22T21:48:47.000Z',
    type: 'job_dispatch',
    eventId: 'job_dispatch:job_abc123',
    status: 'verified',
  });
  assert.doesNotMatch(JSON.stringify(row), /private|secret|sk_test|whsec/);
});
