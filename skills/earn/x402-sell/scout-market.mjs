#!/usr/bin/env node
import { mkdir, writeFile } from 'node:fs/promises';
import { dirname, join } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const DISCOVERY_URL = 'https://api.cdp.coinbase.com/platform/v2/x402/discovery/resources?limit=100';
const MAX_RESOURCES = 500;
const USDC_DECIMALS = 1_000_000n;

export function inferCategory(url) {
  const value = String(url ?? '').toLowerCase();
  if (value.includes('search')) return 'search';
  if (/(funding|price|market)/.test(value)) return 'data';
  if (/(gpt|llm|chat)/.test(value)) return 'llm';
  if (value.includes('image')) return 'image';
  if (/(audio|speech|tts)/.test(value)) return 'audio';
  if (/(swap|defi|dex)/.test(value)) return 'defi';
  if (/(calc|compound|mortgage|hash)/.test(value)) return 'calc';
  return 'other';
}

function atomicUsdcToUsd(value) {
  let atomic;
  try {
    if (typeof value === 'bigint') {
      atomic = value;
    } else if (typeof value === 'number' && Number.isSafeInteger(value)) {
      atomic = BigInt(value);
    } else if (typeof value === 'string' && /^\d+$/.test(value.trim())) {
      atomic = BigInt(value.trim());
    } else {
      return null;
    }
  } catch {
    return null;
  }

  if (atomic < 0n) return null;
  const usd = Number(atomic / USDC_DECIMALS) + Number(atomic % USDC_DECIMALS) / 1_000_000;
  return Number.isFinite(usd) ? usd : null;
}

function listingFromResource(item) {
  if (!item || typeof item !== 'object') return null;
  const resource = typeof item.resource === 'string'
    ? item.resource
    : typeof item.resource?.url === 'string'
      ? item.resource.url
      : typeof item.url === 'string'
        ? item.url
        : '';
  if (!resource) return null;

  const prices = [];
  for (const accept of Array.isArray(item.accepts) ? item.accepts : []) {
    if (!accept || typeof accept !== 'object') continue;
    for (const candidate of [accept.maxAmountRequired, accept.amount]) {
      const priceUsd = atomicUsdcToUsd(candidate);
      if (priceUsd !== null) {
        prices.push(priceUsd);
        break;
      }
    }
  }
  if (prices.length === 0) return null;

  return {
    resource,
    priceUsd: Math.min(...prices),
    category: inferCategory(resource),
  };
}

function compareText(a, b) {
  return a < b ? -1 : a > b ? 1 : 0;
}

function roundUsd(value) {
  return value === null ? null : Math.round((value + Number.EPSILON) * 1_000_000) / 1_000_000;
}

function percentile(sorted, quantile) {
  if (sorted.length === 0) return null;
  const index = (sorted.length - 1) * quantile;
  const lower = Math.floor(index);
  const upper = Math.ceil(index);
  if (lower === upper) return sorted[lower];
  return sorted[lower] + (sorted[upper] - sorted[lower]) * (index - lower);
}

export function aggregateMarket(resources, now) {
  if (!Array.isArray(resources)) throw new TypeError('resources must be an array');
  const timestamp = Number(now);
  if (!Number.isFinite(timestamp)) throw new TypeError('now must be a finite Unix timestamp');

  const listings = resources.map(listingFromResource).filter(Boolean);
  const prices = listings.map((item) => item.priceUsd).sort((a, b) => a - b);
  const categoryPrices = new Map();
  for (const listing of listings) {
    const values = categoryPrices.get(listing.category) ?? [];
    values.push(listing.priceUsd);
    categoryPrices.set(listing.category, values);
  }

  const byCategory = [...categoryPrices.entries()]
    .map(([category, values]) => {
      values.sort((a, b) => a - b);
      return {
        category,
        count: values.length,
        medianPriceUsd: roundUsd(percentile(values, 0.5)),
      };
    })
    .sort((a, b) => b.count - a.count || compareText(a.category, b.category));

  const topPricedSamples = [...listings]
    .sort((a, b) => b.priceUsd - a.priceUsd || compareText(a.resource, b.resource))
    .slice(0, 15)
    .map(({ resource, priceUsd }) => ({ resource, priceUsd: roundUsd(priceUsd) }));

  return {
    ts: Math.floor(timestamp),
    source: 'cdp-bazaar',
    sampled: listings.length,
    priceDistribution: {
      p25: roundUsd(percentile(prices, 0.25)),
      median: roundUsd(percentile(prices, 0.5)),
      p75: roundUsd(percentile(prices, 0.75)),
      p90: roundUsd(percentile(prices, 0.9)),
    },
    byCategory,
    topPricedSamples,
  };
}

function responseItems(body) {
  if (Array.isArray(body)) return body;
  if (!body || typeof body !== 'object') return [];
  if (Array.isArray(body.items)) return body.items;
  if (Array.isArray(body.resources)) return body.resources;
  if (Array.isArray(body.data?.items)) return body.data.items;
  if (Array.isArray(body.data?.resources)) return body.data.resources;
  return [];
}

function nextPageUrl(body, currentUrl, pageSize) {
  if (!body || typeof body !== 'object') return null;
  const pagination = body.pagination && typeof body.pagination === 'object' ? body.pagination : {};
  const directNext = body.nextUrl ?? pagination.nextUrl ?? body.next ?? pagination.next;
  if (typeof directNext === 'string' && directNext) {
    if (/^https?:\/\//i.test(directNext) || directNext.startsWith('/')) {
      return new URL(directNext, currentUrl).href;
    }
    const next = new URL(currentUrl);
    next.searchParams.set('cursor', directNext);
    next.searchParams.set('limit', '100');
    return next.href;
  }

  const cursor = body.nextCursor ?? pagination.nextCursor ?? body.cursor?.next ?? pagination.cursor?.next;
  if (typeof cursor === 'string' && cursor) {
    const next = new URL(currentUrl);
    next.searchParams.set('cursor', cursor);
    next.searchParams.set('limit', '100');
    return next.href;
  }

  const offset = Number(pagination.offset);
  const total = Number(pagination.total);
  if (Number.isFinite(offset) && Number.isFinite(total) && pageSize > 0 && offset + pageSize < total) {
    const next = new URL(currentUrl);
    next.searchParams.set('offset', String(offset + pageSize));
    next.searchParams.set('limit', '100');
    return next.href;
  }
  return null;
}

async function fetchResources() {
  const resources = [];
  const visited = new Set();
  let nextUrl = DISCOVERY_URL;

  while (nextUrl && resources.length < MAX_RESOURCES && !visited.has(nextUrl)) {
    visited.add(nextUrl);
    const response = await fetch(nextUrl, { headers: { Accept: 'application/json' } });
    if (!response.ok) throw new Error(`CDP Bazaar request failed: ${response.status}`);
    const body = await response.json();
    const items = responseItems(body);
    resources.push(...items.slice(0, MAX_RESOURCES - resources.length));
    nextUrl = nextPageUrl(body, nextUrl, items.length);
  }

  return resources;
}

async function main() {
  const resources = await fetchResources();
  const report = aggregateMarket(resources, Math.floor(Date.now() / 1000));
  const stateDir = join(dirname(fileURLToPath(import.meta.url)), 'state');
  await mkdir(stateDir, { recursive: true });
  const output = JSON.stringify(report);
  await writeFile(join(stateDir, 'market-scout.json'), output + '\n', 'utf8');
  process.stdout.write(output + '\n');
}

const isEntry = process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href;
if (isEntry) {
  main().catch((error) => {
    console.error(error instanceof Error ? error.message : String(error));
    process.exitCode = 1;
  });
}
