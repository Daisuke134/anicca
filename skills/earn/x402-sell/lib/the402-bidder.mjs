function reject(reason) {
  throw new Error(`the402 bidder rejected: ${reason}`);
}

function errorCode(error) {
  return String(error?.message || 'bidder_error')
    .replace(/[^A-Za-z0-9_.:-]/g, '_')
    .slice(0, 64);
}

function candidateFor(posting, { researchServiceId, explainerServiceId }) {
  if (posting?.status !== 'open') return null;
  const min = Number(posting.budget_min_usd);
  const max = Number(posting.budget_max_usd);
  if (!Number.isFinite(min) || !Number.isFinite(max) || min < 0 || max < min || max > 25) return null;
  const category = String(posting.category || '').toLowerCase();
  const searchable = JSON.stringify({ title: posting.title, brief: posting.brief }).toLowerCase();
  let basePrice;
  let serviceId;
  let pitch;
  if (category === 'research'
      && /\b(?:x402|machine[- ]payments?|agent payments?|http 402|usdc on base)\b/i.test(searchable)) {
    basePrice = 3;
    serviceId = researchServiceId;
    pitch = 'Automated evidence-backed x402 adoption brief with primary-source links and the requested structure.';
  } else if (category === 'writing'
      && /(?:http\s*402|payment required)/i.test(searchable)) {
    basePrice = 2;
    serviceId = explainerServiceId;
    pitch = 'Beginner-friendly evergreen HTTP 402 explainer with four required sections and no product references.';
  } else {
    return null;
  }
  if (typeof serviceId !== 'string' || !serviceId.length) return null;
  const priceUsd = Math.max(basePrice, min);
  if (priceUsd > max) return null;
  return { priceUsd, serviceId, pitch };
}

export async function runThe402BidderOnce({
  inbox,
  apiKey,
  researchServiceId,
  explainerServiceId,
  fetchImpl = fetch,
  nowMs = Date.now(),
  maxAttempts = 5,
  retryDelayMs = 30_000,
}) {
  if (!inbox || typeof inbox.claimNext !== 'function') reject('missing inbox');
  if (typeof apiKey !== 'string' || !apiKey.length) reject('missing API key');
  const event = inbox.claimNext({ nowMs, type: 'request.created', leaseMs: 300_000 });
  if (!event) return { worked: false };

  try {
    const postingId = event.payload?.posting_id;
    if (typeof postingId !== 'string' || !/^[A-Za-z0-9_.:-]{1,128}$/.test(postingId)
        || event.eventId !== `request.created:${postingId}`) {
      reject('event identity mismatch');
    }
    const detailUrl = `https://api.the402.ai/v1/postings/${encodeURIComponent(postingId)}`;
    const detailResponse = await fetchImpl(detailUrl, {
      headers: { 'X-API-Key': apiKey },
    });
    if (detailResponse.status === 404) {
      inbox.complete({ eventId: event.eventId, leaseToken: event.leaseToken, nowMs });
      return { worked: true, eventId: event.eventId, status: 'skipped', postingId };
    }
    if (!detailResponse.ok) throw new Error(`posting_http_${detailResponse.status}`);
    const detailBody = await detailResponse.json();
    const posting = detailBody?.data || detailBody;
    const candidate = candidateFor(posting, { researchServiceId, explainerServiceId });
    if (!candidate) {
      inbox.complete({ eventId: event.eventId, leaseToken: event.leaseToken, nowMs });
      return { worked: true, eventId: event.eventId, status: 'skipped', postingId };
    }

    const bidResponse = await fetchImpl(`${detailUrl}/bids`, {
      method: 'POST',
      headers: {
        'X-API-Key': apiKey,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        price_usd: candidate.priceUsd,
        eta_hours: 1,
        service_id: candidate.serviceId,
        pitch: candidate.pitch,
      }),
    });
    const bidBody = await bidResponse.json().catch(() => null);
    if (!bidResponse.ok) throw new Error(`bid_http_${bidResponse.status}`);
    const root = bidBody?.data || bidBody;
    const bidId = root?.bid_id || root?.id;
    if (typeof bidId !== 'string') throw new Error('bid_response_invalid');
    inbox.complete({ eventId: event.eventId, leaseToken: event.leaseToken, nowMs });
    return { worked: true, eventId: event.eventId, status: 'bid', postingId, bidId };
  } catch (error) {
    const code = errorCode(error);
    const failure = inbox.fail({
      eventId: event.eventId,
      leaseToken: event.leaseToken,
      nowMs,
      retryDelayMs,
      maxAttempts,
      errorCode: code,
    });
    return {
      worked: true,
      eventId: event.eventId,
      status: failure.status,
      attempt: event.attempt,
      errorCode: code,
    };
  }
}
