#!/usr/bin/env node
import { chmodSync, existsSync, mkdirSync, readFileSync, renameSync, writeFileSync } from 'node:fs';
import { homedir } from 'node:os';
import { dirname, join } from 'node:path';

const API_ROOT = 'https://api.the402.ai/v1';
const TARGET_POSTING_ID = 'post_4031e5a29523480d';
const EXPLAINER_POSTING_ID = 'post_32714ee36ddb4e6b';
const stateDir = join(homedir(), '.anicca');
const credentials = JSON.parse(readFileSync(join(stateDir, 'the402-credentials.json'), 'utf8'));
const command = process.argv[2];

function writeSecureJson(path, value) {
  mkdirSync(dirname(path), { recursive: true, mode: 0o700 });
  const temporary = `${path}.tmp-${process.pid}`;
  writeFileSync(temporary, `${JSON.stringify(value)}\n`, { mode: 0o600, flag: 'wx' });
  chmodSync(temporary, 0o600);
  renameSync(temporary, path);
}

async function api(path, init = {}) {
  const response = await fetch(`${API_ROOT}${path}`, {
    ...init,
    headers: {
      'content-type': 'application/json',
      'X-API-Key': credentials.api_key,
      ...init.headers,
    },
  });
  const body = await response.json().catch(() => null);
  if (!response.ok) {
    const error = body?.error || body?.code || body?.message || 'unknown_error';
    throw new Error(`the402 HTTP ${response.status}: ${error}`);
  }
  return { status: response.status, body: body?.data || body };
}

async function createService() {
  const statePath = join(stateDir, 'the402-service.json');
  if (existsSync(statePath)) {
    const saved = JSON.parse(readFileSync(statePath, 'utf8'));
    const serviceId = saved.service_id || saved.id;
    if (typeof serviceId !== 'string') throw new Error('saved service state omitted service_id');
    const current = await api(`/services/${serviceId}`);
    process.stdout.write(`${JSON.stringify({ created: false, reused: true, serviceId, status: current.body?.status })}\n`);
    return;
  }
  const result = await api('/services', {
    method: 'POST',
    body: JSON.stringify({
      name: 'x402 Adoption Research Brief',
      description: 'An evidence-backed 800–1200 word markdown brief on machine-payment adoption across AI agent frameworks, with concrete examples, obstacles, and a 12-month outlook.',
      price: { fixed: '$3.00' },
      service_type: 'automated_service',
      pricing_model: 'fixed',
      fulfillment_type: 'automated',
      estimated_delivery: '10m',
      category: 'research',
      tags: ['x402', 'usdc', 'base', 'ai-agents', 'research'],
      input_schema: {
        type: 'object',
        required: ['objective'],
        properties: {
          objective: { type: 'string', description: 'Research objective and scope.' },
          deliverable: { type: 'string', description: 'Requested output and length.' },
          acceptance_criteria: { type: 'string', description: 'Conditions the report must satisfy.' },
          format: { type: 'string', description: 'Requested delivery format.' },
        },
      },
      deliverable_schema: {
        report: { type: 'string', description: 'Complete evidence-backed markdown research brief.' },
        sources: { type: 'array', items: { type: 'string' }, description: 'Primary source URLs used.' },
      },
    }),
  });
  const serviceId = result.body?.service_id || result.body?.id;
  if (typeof serviceId !== 'string') throw new Error('service response omitted service_id');
  writeSecureJson(statePath, result.body);
  process.stdout.write(`${JSON.stringify({ created: true, serviceId, status: result.body.status || 'active' })}\n`);
}

async function createExplainerService() {
  const statePath = join(stateDir, 'the402-service-http402.json');
  if (existsSync(statePath)) {
    const saved = JSON.parse(readFileSync(statePath, 'utf8'));
    const serviceId = saved.service_id || saved.id;
    if (typeof serviceId !== 'string') throw new Error('saved explainer service omitted service_id');
    const current = await api(`/services/${serviceId}`);
    process.stdout.write(`${JSON.stringify({ created: false, reused: true, serviceId, name: current.body?.name })}\n`);
    return;
  }
  const result = await api('/services', {
    method: 'POST',
    body: JSON.stringify({
      name: 'HTTP 402 Beginner Explainer',
      description: 'A clear 600–900 word evergreen markdown explainer of HTTP status codes, the reserved 402 Payment Required status, the request-pay-retry pattern, and a simple analogy.',
      price: { fixed: '$2.00' },
      service_type: 'automated_service',
      pricing_model: 'fixed',
      fulfillment_type: 'automated',
      estimated_delivery: '10m',
      category: 'writing',
      tags: ['http', '402', 'technical-writing', 'beginner', 'explainer'],
      input_schema: {
        type: 'object',
        required: ['objective'],
        properties: {
          objective: { type: 'string', description: 'Explanation objective and audience.' },
          deliverable: { type: 'string', description: 'Requested output and length.' },
          acceptance_criteria: { type: 'string', description: 'Conditions the explainer must satisfy.' },
          format: { type: 'string', description: 'Requested delivery format.' },
        },
      },
      deliverable_schema: {
        report: { type: 'string', description: 'Complete beginner-friendly markdown explainer.' },
        sources: { type: 'array', items: { type: 'string' }, description: 'Standards sources used.' },
      },
    }),
  });
  const serviceId = result.body?.service_id || result.body?.id;
  if (typeof serviceId !== 'string') throw new Error('explainer service response omitted service_id');
  writeSecureJson(statePath, result.body);
  process.stdout.write(`${JSON.stringify({ created: true, serviceId, status: result.body.status || 'active' })}\n`);
}

function loadServiceId() {
  const service = JSON.parse(readFileSync(join(stateDir, 'the402-service.json'), 'utf8'));
  const serviceId = service.service_id || service.id;
  if (typeof serviceId !== 'string') throw new Error('saved service state omitted service_id');
  return serviceId;
}

async function testWebhook() {
  const serviceId = loadServiceId();
  const result = await api(`/services/${serviceId}/test`, { method: 'POST' });
  writeSecureJson(join(stateDir, 'the402-webhook-test.json'), result.body);
  process.stdout.write(`${JSON.stringify({ tested: true, serviceId, httpStatus: result.status, responseKeys: Object.keys(result.body || {}) })}\n`);
}

async function testExplainerWebhook() {
  const service = JSON.parse(readFileSync(join(stateDir, 'the402-service-http402.json'), 'utf8'));
  const serviceId = service.service_id || service.id;
  if (typeof serviceId !== 'string') throw new Error('saved explainer service omitted service_id');
  const result = await api(`/services/${serviceId}/test`, { method: 'POST' });
  writeSecureJson(join(stateDir, 'the402-webhook-test-http402.json'), result.body);
  process.stdout.write(`${JSON.stringify({ tested: true, serviceId, httpStatus: result.status, responseKeys: Object.keys(result.body || {}) })}\n`);
}

async function bid() {
  const serviceId = loadServiceId();
  const posting = await api(`/postings/${TARGET_POSTING_ID}`);
  if (posting.body?.status !== 'open') throw new Error(`target posting is ${posting.body?.status || 'unavailable'}`);
  const result = await api(`/postings/${TARGET_POSTING_ID}/bids`, {
    method: 'POST',
    body: JSON.stringify({
      price_usd: 3,
      eta_hours: 1,
      service_id: serviceId,
      pitch: 'I will deliver the requested 800–1200 word factual markdown brief with 3–5 concrete framework/platform examples, adoption obstacles, a three-bullet outlook, and primary-source links.',
    }),
  });
  const bidId = result.body?.bid_id || result.body?.id;
  if (typeof bidId !== 'string') throw new Error('bid response omitted bid_id');
  writeSecureJson(join(stateDir, 'the402-bid.json'), result.body);
  process.stdout.write(`${JSON.stringify({ bidPlaced: true, postingId: TARGET_POSTING_ID, serviceId, bidId, status: result.body.status || 'submitted' })}\n`);
}

async function bidExplainer() {
  const service = JSON.parse(readFileSync(join(stateDir, 'the402-service-http402.json'), 'utf8'));
  const serviceId = service.service_id || service.id;
  if (typeof serviceId !== 'string') throw new Error('saved explainer service omitted service_id');
  const posting = await api(`/postings/${EXPLAINER_POSTING_ID}`);
  if (posting.body?.status !== 'open') throw new Error(`explainer posting is ${posting.body?.status || 'unavailable'}`);
  const result = await api(`/postings/${EXPLAINER_POSTING_ID}/bids`, {
    method: 'POST',
    body: JSON.stringify({
      price_usd: 2,
      eta_hours: 1,
      service_id: serviceId,
      pitch: 'I will deliver the requested self-contained 600–900 word beginner markdown explainer with all four required sections, an everyday analogy, and no company, product, or current-event references.',
    }),
  });
  const bidId = result.body?.bid_id || result.body?.id;
  if (typeof bidId !== 'string') throw new Error('explainer bid response omitted bid_id');
  writeSecureJson(join(stateDir, 'the402-bid-http402.json'), result.body);
  process.stdout.write(`${JSON.stringify({ bidPlaced: true, postingId: EXPLAINER_POSTING_ID, serviceId, bidId, status: result.body.status || 'submitted' })}\n`);
}

async function subscribe() {
  const result = await api('/postings/notifications', {
    method: 'PUT',
    body: JSON.stringify({
      categories: ['research', 'writing'],
      min_budget_usd: 1,
      max_budget_usd: 25,
    }),
  });
  writeSecureJson(join(stateDir, 'the402-notifications.json'), result.body);
  process.stdout.write(`${JSON.stringify({
    subscribed: true,
    categories: result.body?.categories || ['research', 'writing'],
    minBudgetUsd: result.body?.min_budget_usd ?? 1,
    maxBudgetUsd: result.body?.max_budget_usd ?? 25,
  })}\n`);
}

if (command === 'create-service') await createService();
else if (command === 'create-explainer-service') await createExplainerService();
else if (command === 'test-webhook') await testWebhook();
else if (command === 'test-explainer-webhook') await testExplainerWebhook();
else if (command === 'bid') await bid();
else if (command === 'bid-explainer') await bidExplainer();
else if (command === 'subscribe') await subscribe();
else throw new Error('usage: the402-market.mjs <create-service|create-explainer-service|test-webhook|test-explainer-webhook|bid|bid-explainer|subscribe>');
