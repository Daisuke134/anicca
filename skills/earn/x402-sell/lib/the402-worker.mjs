function reject(reason) {
  throw new Error(`the402 worker rejected: ${reason}`);
}

function callbackFor(payload) {
  const { callback_url: callbackUrl, thread_id: threadId, job_id: jobId } = payload || {};
  if (typeof callbackUrl !== 'string' || typeof threadId !== 'string' || typeof jobId !== 'string') {
    reject('invalid dispatch identity');
  }
  let url;
  try { url = new URL(callbackUrl); } catch { reject('invalid callback URL'); }
  const expected = `/v1/threads/${encodeURIComponent(threadId)}/update`;
  if (url.protocol !== 'https:' || url.hostname !== 'api.the402.ai'
      || url.port || url.username || url.password || url.search || url.hash
      || url.pathname !== expected) {
    reject('unpinned callback URL');
  }
  return url.href;
}

async function postUpdate(fetchImpl, url, apiKey, body) {
  const response = await fetchImpl(url, {
    method: 'POST',
    headers: {
      'X-API-Key': apiKey,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(body),
  });
  if (!response?.ok) throw new Error(`callback_http_${response?.status || 0}`);
}

export async function runThe402WorkerOnce({
  inbox,
  apiKey,
  processJob,
  fetchImpl = fetch,
  nowMs = Date.now(),
  maxAttempts = 5,
  retryDelayMs = 30_000,
}) {
  if (!inbox || typeof inbox.claimNext !== 'function') reject('missing inbox');
  if (typeof apiKey !== 'string' || !apiKey.length) reject('missing API key');
  if (typeof processJob !== 'function') reject('missing job processor');

  const event = inbox.claimNext({ nowMs, type: 'job_dispatch', leaseMs: 300_000 });
  if (!event) return { worked: false };
  try {
    const payload = event.payload;
    if (event.eventId !== `job_dispatch:${payload?.job_id || ''}`) reject('event identity mismatch');
    const callbackUrl = callbackFor(payload);
    await postUpdate(fetchImpl, callbackUrl, apiKey, { status: 'in_progress' });
    const output = await processJob({
      jobId: payload.job_id,
      threadId: payload.thread_id,
      serviceId: payload.service_id,
      brief: payload.brief,
      deadline: payload.deadline,
    });
    if (!output || typeof output.deliverables !== 'object' || output.deliverables === null) {
      reject('invalid deliverables');
    }
    const completed = { status: 'completed', deliverables: output.deliverables };
    if (typeof output.notes === 'string' && output.notes.length) completed.notes = output.notes;
    await postUpdate(fetchImpl, callbackUrl, apiKey, completed);
    inbox.complete({ eventId: event.eventId, leaseToken: event.leaseToken, nowMs });
    return { worked: true, eventId: event.eventId, status: 'completed', attempt: event.attempt };
  } catch (error) {
    const failure = inbox.fail({
      eventId: event.eventId,
      leaseToken: event.leaseToken,
      nowMs,
      retryDelayMs,
      maxAttempts,
      errorCode: String(error?.message || 'worker_error').replace(/[^A-Za-z0-9_.:-]/g, '_').slice(0, 64),
    });
    return {
      worked: true,
      eventId: event.eventId,
      status: failure.status,
      attempt: event.attempt,
      errorCode: String(error?.message || 'worker_error').replace(/[^A-Za-z0-9_.:-]/g, '_').slice(0, 64),
    };
  }
}
