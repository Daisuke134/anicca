function normalizeAddress(value) {
  const normalized = String(value || '').toLowerCase();
  return /^0x[0-9a-f]{40}$/.test(normalized) ? normalized : null;
}

function normalizeTx(value) {
  const normalized = String(value || '').toLowerCase();
  return /^0x[0-9a-f]{64}$/.test(normalized) ? normalized : null;
}

export function usdcAtomic(value) {
  const normalized = String(value ?? '').trim().replace(/^\$/, '');
  if (!/^\d+(?:\.\d{1,6})?$/.test(normalized)) return null;
  const [whole, fraction = ''] = normalized.split('.');
  return (BigInt(whole) * 1_000_000n + BigInt(fraction.padEnd(6, '0'))).toString();
}

function observedAt(value) {
  if (typeof value !== 'string' || !value) return null;
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? null : parsed.toISOString();
}

function normalizeIdentifier(value) {
  const normalized = String(value || '');
  return /^[a-zA-Z0-9][a-zA-Z0-9._:-]{0,127}$/.test(normalized) ? normalized : null;
}

export function normalizeImageSales(rows, {
  payTo,
  route = '/image',
  priceUsd = '0.03',
} = {}) {
  const receiver = normalizeAddress(payTo);
  const expectedAtomic = usdcAtomic(priceUsd);
  if (!receiver) throw new TypeError('payTo must be a valid EVM address');
  if (!expectedAtomic) throw new TypeError('priceUsd must be an exact USDC decimal');

  return (Array.isArray(rows) ? rows : []).flatMap((row) => {
    const tx = normalizeTx(row?.tx);
    const timestamp = observedAt(row?.ts);
    const status = Number(row?.status);
    if (row?.settled !== true || !tx || !timestamp) return [];
    if (row?.route !== route || usdcAtomic(row?.price) !== expectedAtomic) return [];
    if (!Number.isInteger(status) || status < 200 || status >= 300) return [];
    return [{
      source: 'x402-image',
      source_sale_id: `x402-image:${tx}`,
      offer_id: route,
      tx,
      expected_pay_to: receiver,
      expected_usdc_atomic: expectedAtomic,
      observed_at: timestamp,
    }];
  });
}

export function normalizeRailwaySettlements(rows, {
  payTo,
  allowedOffers,
} = {}) {
  const receiver = normalizeAddress(payTo);
  if (!receiver) throw new TypeError('payTo must be a valid EVM address');
  if (!allowedOffers || typeof allowedOffers !== 'object' || Array.isArray(allowedOffers)) {
    throw new TypeError('allowedOffers must be an object');
  }
  const offers = new Map(Object.entries(allowedOffers).map(([route, atomic]) => {
    const safeRoute = typeof route === 'string' && /^\/[a-z0-9][a-z0-9/_-]{0,126}$/.test(route)
      ? route
      : null;
    const safeAtomic = typeof atomic === 'string' && /^[1-9]\d*$/.test(atomic) ? atomic : null;
    if (!safeRoute || !safeAtomic) throw new TypeError('allowedOffers contains an invalid route or amount');
    return [safeRoute, safeAtomic];
  }));

  return (Array.isArray(rows) ? rows : []).flatMap((row) => {
    const saleId = normalizeIdentifier(row?.id);
    const tx = normalizeTx(row?.transaction);
    const timestamp = observedAt(row?.observed_at);
    const rowPayTo = normalizeAddress(row?.pay_to);
    const route = typeof row?.route === 'string' && offers.has(row.route) ? row.route : null;
    const amount = typeof row?.amount_atomic === 'string' && /^\d+$/.test(row.amount_atomic)
      ? row.amount_atomic.replace(/^0+(?=\d)/, '')
      : null;
    if (!saleId || !tx || !timestamp || !route || !amount) return [];
    if (row?.success !== true
      || !['GET', 'POST'].includes(row?.method)
      || row?.scheme !== 'exact'
      || row?.network !== 'eip155:8453'
      || normalizeAddress(row?.asset) !== '0x833589fcd6edb6e08f4c7c32d4f71b54bda02913'
      || rowPayTo !== receiver
      || amount !== offers.get(route)) {
      return [];
    }
    return [{
      source: 'x402-railway',
      source_sale_id: `x402-railway:${saleId}`,
      offer_id: route,
      tx,
      expected_pay_to: receiver,
      expected_usdc_atomic: amount,
      observed_at: timestamp,
    }];
  });
}

export function normalizeClawMerchantSales(rows, {
  assetId,
  payTo,
  priceUsd = '0.03',
} = {}) {
  const pinnedAsset = normalizeIdentifier(assetId);
  const receiver = normalizeAddress(payTo);
  const expectedAtomic = usdcAtomic(priceUsd);
  if (!pinnedAsset) throw new TypeError('assetId must be a safe identifier');
  if (!receiver) throw new TypeError('payTo must be a valid EVM address');
  if (!expectedAtomic) throw new TypeError('priceUsd must be an exact USDC decimal');

  return (Array.isArray(rows) ? rows : []).flatMap((row) => {
    const saleId = normalizeIdentifier(row?.id);
    const tx = normalizeTx(row?.txHash ?? row?.tx_hash);
    const timestamp = observedAt(row?.createdAt ?? row?.created_at);
    if (!saleId || !tx || !timestamp) return [];
    if ((row?.assetId ?? row?.asset_id) !== pinnedAsset) return [];
    if (row?.status !== 'delivered') return [];
    if (usdcAtomic(row?.amountUsdc ?? row?.amount_usdc) !== expectedAtomic) return [];
    return [{
      source: 'clawmerchants',
      source_sale_id: `clawmerchants:${saleId}`,
      offer_id: pinnedAsset,
      tx,
      expected_pay_to: receiver,
      expected_usdc_atomic: expectedAtomic,
      observed_at: timestamp,
    }];
  });
}

function oneConsistent(values, normalize) {
  const provided = values.filter((value) => value !== undefined && value !== null);
  const normalized = provided.map(normalize);
  if (normalized.some((value) => !value)) return null;
  const unique = [...new Set(normalized)];
  return unique.length === 1 ? unique[0] : null;
}

export function normalizeThe402Sales(body, {
  payTo,
  allowedOffers,
} = {}) {
  const receiver = normalizeAddress(payTo);
  if (!receiver) throw new TypeError('payTo must be a valid EVM address');
  if (!allowedOffers || typeof allowedOffers !== 'object' || Array.isArray(allowedOffers)) {
    throw new TypeError('allowedOffers must be an object');
  }
  const offers = new Map(Object.entries(allowedOffers).map(([id, range]) => {
    const offerId = normalizeIdentifier(id);
    const min = usdcAtomic(range?.minUsd);
    const max = usdcAtomic(range?.maxUsd);
    if (!offerId || !min || !max || BigInt(min) <= 0n || BigInt(min) > BigInt(max)) {
      throw new TypeError('allowedOffers contains an invalid range');
    }
    return [offerId, { min: BigInt(min), max: BigInt(max) }];
  }));
  const rows = Array.isArray(body?.recent_settlements) ? body.recent_settlements : [];

  return rows.flatMap((row) => {
    const saleId = oneConsistent([row?.settlement_id, row?.settlementId, row?.id], normalizeIdentifier);
    const tx = oneConsistent([row?.tx_hash, row?.txHash, row?.transaction_hash, row?.transactionHash, row?.transaction], normalizeTx);
    const timestamp = oneConsistent([row?.settled_at, row?.settledAt, row?.created_at, row?.createdAt], observedAt);
    const amountAtomic = oneConsistent([
      row?.provider_amount_usd,
      row?.providerAmountUsd,
      row?.amount_usd,
      row?.amountUsd,
      row?.amount,
    ], usdcAtomic);
    const offerMatches = [...new Set([
      row?.offer_id,
      row?.offerId,
      row?.service_id,
      row?.serviceId,
      row?.product_id,
      row?.productId,
      row?.posting_id,
      row?.postingId,
      row?.job_id,
      row?.jobId,
    ].map(normalizeIdentifier).filter((id) => id && offers.has(id)))];
    const status = String(row?.status || '').toLowerCase();
    if (!saleId || !tx || !timestamp || !amountAtomic || offerMatches.length !== 1) return [];
    if (!['settled', 'released', 'completed'].includes(status)) return [];
    const offerId = offerMatches[0];
    const range = offers.get(offerId);
    const amount = BigInt(amountAtomic);
    if (amount < range.min || amount > range.max) return [];
    return [{
      source: 'the402',
      source_sale_id: `the402:${saleId}`,
      offer_id: offerId,
      tx,
      expected_pay_to: receiver,
      expected_usdc_atomic: amountAtomic,
      observed_at: timestamp,
    }];
  });
}

function safeCandidate(row) {
  const source = ['x402-image', 'x402-railway', 'the402', 'clawmerchants'].includes(row?.source) ? row.source : null;
  const sourceSaleId = typeof row?.source_sale_id === 'string'
    && /^[a-zA-Z0-9][a-zA-Z0-9._:-]{0,191}$/.test(row.source_sale_id)
    ? row.source_sale_id
    : null;
  const offerId = typeof row?.offer_id === 'string'
    && /^[a-zA-Z0-9/][a-zA-Z0-9._:/-]{0,191}$/.test(row.offer_id)
    ? row.offer_id
    : null;
  const tx = normalizeTx(row?.tx);
  const receiver = normalizeAddress(row?.expected_pay_to);
  const timestamp = observedAt(row?.observed_at);
  const atomic = typeof row?.expected_usdc_atomic === 'string' && /^\d+$/.test(row.expected_usdc_atomic)
    ? row.expected_usdc_atomic.replace(/^0+(?=\d)/, '')
    : null;
  if (!source || !sourceSaleId || !offerId || !tx || !receiver || !timestamp || !atomic || BigInt(atomic) <= 0n) {
    return null;
  }
  return {
    source,
    source_sale_id: sourceSaleId,
    offer_id: offerId,
    tx,
    expected_pay_to: receiver,
    expected_usdc_atomic: atomic,
    observed_at: timestamp,
  };
}

function existingCandidateKeys(path) {
  const saleIds = new Set();
  const txs = new Set();
  if (!existsSync(path)) return { saleIds, txs };
  for (const line of readFileSync(path, 'utf8').split('\n').filter(Boolean)) {
    try {
      const row = JSON.parse(line);
      if (typeof row?.source_sale_id === 'string') saleIds.add(row.source_sale_id);
      const tx = normalizeTx(row?.tx);
      if (tx) txs.add(tx);
    } catch { /* malformed historical rows do not become evidence */ }
  }
  return { saleIds, txs };
}

export function appendUniqueSaleCandidates(path, rows) {
  mkdirSync(dirname(path), { recursive: true, mode: 0o700 });
  const lockPath = `${path}.lock`;
  let lock;
  try {
    lock = openSync(lockPath, 'wx', 0o600);
    const { saleIds, txs } = existingCandidateKeys(path);
    const fresh = [];
    let duplicates = 0;
    let invalid = 0;
    for (const input of Array.isArray(rows) ? rows : []) {
      const row = safeCandidate(input);
      if (!row) {
        invalid += 1;
        continue;
      }
      if (saleIds.has(row.source_sale_id) || txs.has(row.tx)) {
        duplicates += 1;
        continue;
      }
      saleIds.add(row.source_sale_id);
      txs.add(row.tx);
      fresh.push(row);
    }
    if (fresh.length) {
      appendFileSync(path, `${fresh.map((row) => JSON.stringify(row)).join('\n')}\n`, { mode: 0o600 });
      chmodSync(path, 0o600);
    }
    return { recorded: fresh.length, duplicates, invalid };
  } finally {
    if (lock !== undefined) {
      closeSync(lock);
      try { unlinkSync(lockPath); } catch { /* already removed */ }
    }
  }
}
import {
  appendFileSync,
  chmodSync,
  closeSync,
  existsSync,
  mkdirSync,
  openSync,
  readFileSync,
  unlinkSync,
} from 'node:fs';
import { dirname } from 'node:path';
