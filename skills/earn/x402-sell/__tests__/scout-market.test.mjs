import test from 'node:test';
import assert from 'node:assert/strict';

import { aggregateMarket, inferCategory } from '../scout-market.mjs';

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
    { resource: 'https://example.com/search/one', accepts: [{ maxAmountRequired: '1000000' }] },
    { resource: 'https://example.com/funding/one', accepts: [{ maxAmountRequired: '2000000' }] },
    { resource: 'https://example.com/research/two', accepts: [{ maxAmountRequired: '3000000' }] },
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
    { category: 'data', count: 2, medianPriceUsd: 3 },
    { category: 'search', count: 2, medianPriceUsd: 2 },
  ]);
  assert.deepEqual(report.topPricedSamples.slice(0, 2), [
    { resource: 'https://example.com/weather', priceUsd: 10 },
    { resource: 'https://example.com/mortgage', priceUsd: 9 },
  ]);
});
