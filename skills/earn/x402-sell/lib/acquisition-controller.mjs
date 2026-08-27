import { the402BidCandidate } from './the402-bidder.mjs';

function postingsFrom(body) {
  const root = body?.data ?? body;
  if (Array.isArray(root)) return root;
  if (Array.isArray(root?.postings)) return root.postings;
  if (Array.isArray(root?.items)) return root.items;
  return [];
}

function postingId(value) {
  const normalized = String(value || '');
  return /^[A-Za-z0-9_.:-]{1,128}$/.test(normalized) ? normalized : null;
}

export async function runAcquisitionCycle({
  inbox,
  apiKey,
  researchServiceId,
  explainerServiceId,
  fetchImpl = fetch,
  appendAction = () => {},
  nowMs = Date.now(),
} = {}) {
  if (!inbox || typeof inbox.audit !== 'function' || typeof inbox.enqueue !== 'function') {
    throw new TypeError('inbox is required');
  }
  if (typeof apiKey !== 'string' || !apiKey.length) throw new TypeError('apiKey is required');
  if (typeof fetchImpl !== 'function') throw new TypeError('fetchImpl must be a function');
  if (typeof appendAction !== 'function') throw new TypeError('appendAction must be a function');
  if (!Number.isSafeInteger(nowMs) || nowMs < 0) throw new TypeError('nowMs must be a safe timestamp');

  const response = await fetchImpl('https://api.the402.ai/v1/postings', {
    headers: { 'X-API-Key': apiKey },
    signal: AbortSignal.timeout(30_000),
  });
  const body = await response.json().catch(() => null);
  if (!response.ok || body === null) throw new Error(`postings_http_${response.status}`);
  const postings = postingsFrom(body);
  const openPostings = postings.filter((posting) => posting?.status === 'open').length;

  for (const posting of postings) {
    const id = postingId(posting?.posting_id ?? posting?.id);
    if (!id || posting?.status !== 'open') continue;
    const eventId = `request.created:${id}`;
    if (inbox.audit(eventId)) continue;
    const candidate = the402BidCandidate(posting, { researchServiceId, explainerServiceId });
    if (!candidate) continue;
    const event = {
      eventId,
      type: 'request.created',
      payload: { type: 'request.created', posting_id: id },
      receivedAtMs: nowMs,
    };
    const accepted = inbox.enqueue(event);
    if (!accepted?.accepted || accepted.duplicate) continue;
    appendAction({
      ts: new Date(nowMs).toISOString(),
      action: 'enqueue_bid',
      posting_id: id,
      event_id: eventId,
    });
    return { action: 'enqueued_bid', postingId: id, eventId, openPostings };
  }
  return { action: 'none', openPostings };
}
