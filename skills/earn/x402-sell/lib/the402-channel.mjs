import { createHash, createHmac, timingSafeEqual } from 'node:crypto';

export const THE402_REGISTER_URL = 'https://api.the402.ai/v1/register';
export const THE402_BASE_USDC = '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913';
// Measured from the unpaid registration challenge. Pin changes fail closed and require re-verification.
export const THE402_REGISTER_PAY_TO = '0x21bCE104282d6a089539C34aDddE152D42A02D0e';

const ADDRESS_RE = /^0x[0-9a-f]{40}$/i;
const EVENT_ID_RE = /^[A-Za-z0-9_.:-]{1,128}$/;
const WEBHOOK_TYPES = new Map([
  ['job_dispatch', 'job_id'],
  ['request.created', 'posting_id'],
  ['thread_inquiry', 'thread_id'],
]);

function registrationRejected(reason) {
  throw new Error(`the402 registration requirement rejected: ${reason}`);
}

function webhookRejected(reason) {
  throw new Error(`the402 webhook rejected: ${reason}`);
}

function normalizedAddress(value, reject) {
  if (typeof value !== 'string' || !ADDRESS_RE.test(value)) reject('invalid address');
  return value.toLowerCase();
}

export function validateThe402RegistrationChallenge(challenge, {
  selfWallets = [],
} = {}) {
  if (!challenge || challenge.x402Version !== 1) registrationRejected('x402 version drift');
  if (!Array.isArray(challenge.accepts) || challenge.accepts.length !== 1) {
    registrationRejected('ambiguous accepts');
  }
  const requirement = challenge.accepts[0];
  if (!requirement || requirement.scheme !== 'exact') registrationRejected('scheme drift');
  if (requirement.network !== 'base') registrationRejected('network drift');
  if (requirement.resource !== THE402_REGISTER_URL) registrationRejected('resource drift');

  let amountAtomic;
  try {
    if (!/^\d+$/.test(String(requirement.maxAmountRequired))) throw new Error('not atomic');
    amountAtomic = BigInt(requirement.maxAmountRequired);
  } catch {
    registrationRejected('invalid amount');
  }
  if (amountAtomic !== 10_000n) registrationRejected('price drift');

  const asset = normalizedAddress(requirement.asset, registrationRejected);
  if (asset !== THE402_BASE_USDC.toLowerCase()) registrationRejected('asset drift');
  const payTo = normalizedAddress(requirement.payTo, registrationRejected);
  if (payTo !== THE402_REGISTER_PAY_TO.toLowerCase()) registrationRejected('recipient drift');
  const internal = new Set(selfWallets.map((wallet) => String(wallet).toLowerCase()));
  if (internal.has(payTo)) registrationRejected('self payment');

  return {
    x402Version: 1,
    scheme: 'exact',
    network: 'base',
    amountAtomic,
    asset,
    payTo,
    resource: THE402_REGISTER_URL,
  };
}

function headerValue(headers, name) {
  if (headers?.get) return headers.get(name);
  if (!headers || typeof headers !== 'object') return null;
  const wanted = name.toLowerCase();
  const entry = Object.entries(headers).find(([key]) => key.toLowerCase() === wanted);
  return entry ? String(entry[1]) : null;
}

function constantTimeStringEqual(left, right) {
  const a = createHash('sha256').update(String(left)).digest();
  const b = createHash('sha256').update(String(right)).digest();
  return timingSafeEqual(a, b);
}

export function verifyThe402Webhook({
  rawBody,
  headers,
  apiKey,
  webhookSecret,
  nowMs = Date.now(),
  toleranceSeconds = 300,
}) {
  if (typeof rawBody !== 'string' || !rawBody.length) webhookRejected('missing raw body');
  if (typeof apiKey !== 'string' || !apiKey.length) webhookRejected('missing API key');
  if (typeof webhookSecret !== 'string' || !webhookSecret.length) webhookRejected('missing webhook secret');
  if (!Number.isFinite(nowMs) || !Number.isFinite(toleranceSeconds) || toleranceSeconds < 0) {
    webhookRejected('invalid clock configuration');
  }

  const platformSecret = headerValue(headers, 'x-platform-secret');
  if (!platformSecret || !constantTimeStringEqual(platformSecret, apiKey)) {
    webhookRejected('platform secret mismatch');
  }
  const timestamp = headerValue(headers, 'x-webhook-timestamp');
  if (!timestamp || !/^\d+$/.test(timestamp)) webhookRejected('invalid timestamp');
  if (Math.abs(nowMs / 1000 - Number(timestamp)) > toleranceSeconds) {
    webhookRejected('timestamp outside replay window');
  }

  const signature = headerValue(headers, 'x-webhook-signature');
  const match = /^sha256=([0-9a-f]{64})$/i.exec(signature || '');
  if (!match) webhookRejected('invalid signature format');
  const expected = createHmac('sha256', webhookSecret)
    .update(`${timestamp}.${rawBody}`)
    .digest();
  const supplied = Buffer.from(match[1], 'hex');
  if (!timingSafeEqual(expected, supplied)) webhookRejected('signature mismatch');

  let payload;
  try { payload = JSON.parse(rawBody); }
  catch { webhookRejected('invalid JSON'); }
  const type = payload?.type;
  const idField = WEBHOOK_TYPES.get(type);
  if (!idField) webhookRejected('unknown event type');
  const id = payload?.[idField];
  if (typeof id !== 'string' || !EVENT_ID_RE.test(id)) webhookRejected('invalid event id');

  return { type, eventId: `${type}:${id}`, payload };
}

export function privacySafeThe402Audit({ ts, type, eventId, status }) {
  return {
    ts: String(ts),
    type: String(type),
    eventId: String(eventId),
    status: String(status),
  };
}
