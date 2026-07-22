import { acceptThe402Webhook } from './the402-inbox.mjs';

const JSON_HEADERS = {
  'content-type': 'application/json; charset=utf-8',
  'cache-control': 'no-store',
};

function jsonResponse(body, status, extraHeaders = {}) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { ...JSON_HEADERS, ...extraHeaders },
  });
}

class BodyTooLargeError extends Error {}

async function readBoundedBody(request, maxBodyBytes) {
  if (!Number.isSafeInteger(maxBodyBytes) || maxBodyBytes < 1 || maxBodyBytes > 10_485_760) {
    throw new Error('invalid body limit');
  }
  const declared = request.headers.get('content-length');
  if (declared && /^\d+$/.test(declared) && Number(declared) > maxBodyBytes) {
    throw new BodyTooLargeError();
  }
  if (!request.body) return '';

  const reader = request.body.getReader();
  const chunks = [];
  let total = 0;
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    total += value.byteLength;
    if (total > maxBodyBytes) {
      await reader.cancel().catch(() => {});
      throw new BodyTooLargeError();
    }
    chunks.push(Buffer.from(value));
  }
  return Buffer.concat(chunks, total).toString('utf8');
}

export async function handleThe402WebhookRequest(request, {
  inbox,
  apiKey,
  webhookSecret,
  allowApiKeyOnly = false,
  allowMissingPlatformSecret = false,
  allowUnsignedTestProbe = false,
  expectedTestServiceId = null,
  onRejected = () => {},
  nowMs = Date.now(),
  maxBodyBytes = 1_048_576,
}) {
  if (request?.method !== 'POST') {
    return jsonResponse({ ok: false, error: 'method_not_allowed' }, 405, { allow: 'POST' });
  }
  const mediaType = String(request.headers.get('content-type') || '')
    .split(';', 1)[0]
    .trim()
    .toLowerCase();
  if (mediaType !== 'application/json') {
    return jsonResponse({ ok: false, error: 'unsupported_media_type' }, 415);
  }
  if (typeof apiKey !== 'string' || !apiKey.length
      || typeof webhookSecret !== 'string' || !webhookSecret.length) {
    return jsonResponse({ ok: false, error: 'temporarily_unavailable' }, 503);
  }
  try {
    const rawBody = await readBoundedBody(request, maxBodyBytes);
    if (allowUnsignedTestProbe) {
      let testPayload = null;
      try { testPayload = JSON.parse(rawBody); } catch {}
      if (testPayload?.test === true
          && testPayload?.type === 'job_dispatch'
          && /^test_job_[A-Za-z0-9]+$/.test(testPayload?.job_id || '')
          && testPayload?.service_id === expectedTestServiceId) {
        return jsonResponse({ ok: true, test: true }, 200);
      }
    }
    const accepted = acceptThe402Webhook({
      inbox,
      rawBody,
      headers: request.headers,
      apiKey,
      webhookSecret,
      allowApiKeyOnly,
      allowMissingPlatformSecret,
      nowMs,
    });
    return jsonResponse(accepted, 200);
  } catch (error) {
    if (error instanceof BodyTooLargeError) {
      return jsonResponse({ ok: false, error: 'payload_too_large' }, 413);
    }
    if (String(error?.message).startsWith('the402 webhook rejected:')) {
      onRejected(error.message);
      const malformed = /invalid JSON|unknown event type|invalid event id/.test(error.message);
      return jsonResponse({ ok: false, error: malformed ? 'invalid_event' : 'unauthorized' }, malformed ? 400 : 401);
    }
    return jsonResponse({ ok: false, error: 'temporarily_unavailable' }, 503);
  }
}
