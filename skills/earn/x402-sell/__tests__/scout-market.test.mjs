import test from 'node:test';
import assert from 'node:assert/strict';

import { aggregateMarket, fetchResources, inferCategory } from '../scout-market.mjs';

const categoryCases = [
  ['search', 'https://example.com/research/query'],
  ['data', 'https://example.com/funding-rate'],
  ['llm', 'https://example.com/v1/chat/completions'],
  ['image', 'https://example.com/generate-image'],
  ['audio', 'https://example.com/text-to-speech'],
  ['defi', 'https://example.com/dex/swap'],
  ['calc', 'https://example.com/mortgage/calc'],
  ['other', 'https://example.com/weather'],
];

for (const [category, url] of categoryCases) {
  test(`inferCategory: ${category}`, () => {
    assert.equal(inferCategory(url), category);
  });
}

test('aggregateMarket computes interpolated percentiles and category medians', () => {
  const fixture = [
    { resource: 'https://example.com/search/one', accepts: [{ maxAmountRequired: '1000000' }], quality: { l30DaysTotalCalls: 10, l30DaysUniquePayers: 4 } },
    { resource: 'https://example.com/funding/one', accepts: [{ maxAmountRequired: '2000000' }] },
    { resource: 'https://example.com/research/two', accepts: [{ maxAmountRequired: '3000000' }], quality: { l30DaysTotalCalls: 5, l30DaysUniquePayers: 3 } },
    { resource: 'https://example.com/market/two', accepts: [{ maxAmountRequired: '4000000' }] },
    { resource: 'https://example.com/gpt', accepts: [{ maxAmountRequired: '5000000' }] },
    { resource: 'https://example.com/image', accepts: [{ maxAmountRequired: '6000000' }] },
    { resource: 'https://example.com/speech', accepts: [{ maxAmountRequired: '7000000' }] },
    { resource: 'https://example.com/dex', accepts: [{ maxAmountRequired: '8000000' }] },
    { resource: 'https://example.com/mortgage', accepts: [{ maxAmountRequired: '9000000' }] },
    { resource: 'https://example.com/weather', accepts: [{ amount: '10000000' }] },
    { resource: 'https://example.com/invalid', accepts: [{ maxAmountRequired: 'not-a-number' }] },
    { resource: '', accepts: [{ maxAmountRequired: '11000000' }] },
  ];

  const report = aggregateMarket(fixture, 1_700_000_000.9);

  assert.equal(report.ts, 1_700_000_000);
  assert.equal(report.source, 'cdp-bazaar');
  assert.equal(report.sampled, 10);
  assert.deepEqual(report.priceDistribution, {
    p25: 3.25,
    median: 5.5,
    p75: 7.75,
    p90: 9.1,
  });
  assert.deepEqual(report.byCategory.slice(0, 2), [
    { category: 'data', count: 2, medianPriceUsd: 3, calls30d: 0, payerSignals30d: 0 },
    { category: 'search', count: 2, medianPriceUsd: 2, calls30d: 15, payerSignals30d: 7 },
  ]);
  assert.deepEqual(report.topPricedSamples.slice(0, 2), [
    { resource: 'https://example.com/weather', priceUsd: 10 },
    { resource: 'https://example.com/mortgage', priceUsd: 9 },
  ]);
  assert.deepEqual(report.topDemandSamples, [
    {
      resource: 'https://example.com/research/two',
      category: 'search',
      priceUsd: 3,
      calls30d: 5,
      payerSignals30d: 3,
      estimatedGrossUsd30d: 15,
    },
    {
      resource: 'https://example.com/search/one',
      category: 'search',
      priceUsd: 1,
      calls30d: 10,
      payerSignals30d: 4,
      estimatedGrossUsd30d: 10,
    },
  ]);
  assert.deepEqual(report.demandGate, {
    passed: true,
    paidCalls30d: 15,
    payerSignals30d: 7,
    categoriesWithPaidDemand: 1,
    reason: 'observed paid calls and payer signals in the last 30 days',
  });
});

test('aggregateMarket does not pass the demand gate for listings without payer signals', () => {
  const report = aggregateMarket([
    {
      resource: 'https://example.com/search',
      accepts: [{ maxAmountRequired: '10000' }],
      quality: { l30DaysTotalCalls: 50, l30DaysUniquePayers: 0 },
    },
  ], 1_700_000_000);

  assert.deepEqual(report.demandGate, {
    passed: false,
    paidCalls30d: 50,
    payerSignals30d: 0,
    categoriesWithPaidDemand: 0,
    reason: 'no category has both paid calls and payer signals in the last 30 days',
  });
});

test('inferCategory uses service metadata for DeFi routes whose URL is generic', () => {
  assert.equal(inferCategory({
    resource: 'https://example.com/pools',
    serviceName: 'Yield Optimizer',
    tags: ['defi', 'apy'],
  }), 'defi');
});

test('fetchResources follows the entire catalog instead of stopping at 500 resources', async () => {
  const total = 2_500;
  const offsets = [];
  const fetchImpl = async (url) => {
    const offset = Number(new URL(url).searchParams.get('offset') ?? 0);
    offsets.push(offset);
    const count = Math.min(1_000, total - offset);
    return {
      ok: true,
      async json() {
        return {
          items: Array.from({ length: count }, (_, index) => ({ resource: `https://example.com/${offset + index}` })),
          pagination: { offset, total },
        };
      },
    };
  };

  const resources = await fetchResources({
    fetchImpl,
    discoveryUrl: 'https://example.com/resources?limit=1000',
    maxResources: 30_000,
  });

  assert.equal(resources.length, total);
  assert.deepEqual(offsets, [0, 1_000, 2_000]);
});
