import { describe, expect, it } from 'vitest';

import {
  annualizedBps,
  baseSymbol,
  buildFundingRatesResponse,
  computeDivergence,
  normalizeBinance,
  normalizeBybit,
  normalizeHyperliquid,
  toFundingRate8h,
} from './funding-rates.js';

describe('funding rates', () => {
  it('normalizes symbols and native intervals to an 8-hour rate', () => {
    expect(baseSymbol('btcusdt')).toBe('BTC');
    expect(toFundingRate8h(0.0000125, 1)).toBe(0.0001);
    expect(annualizedBps(0.0001)).toBeCloseTo(1095);
  });

  it('normalizes Binance, Bybit, and Hyperliquid public responses', () => {
    expect(normalizeBinance([
      { symbol: 'LPTUSDT', markPrice: '10', lastFundingRate: '0.00005', nextFundingTime: 10 },
    ], [{ symbol: 'LPTUSDT', fundingIntervalHours: 4 }])[0]).toMatchObject({
      exchange: 'binance', baseSymbol: 'LPT', fundingRate8h: 0.0001,
    });
    expect(normalizeBybit([
      { symbol: 'BTCUSDT', markPrice: '100', fundingRate: '0.0001', nextFundingTime: '10', fundingIntervalHour: '8' },
    ])[0]).toMatchObject({ exchange: 'bybit', baseSymbol: 'BTC', fundingRate8h: 0.0001 });
    expect(normalizeHyperliquid(
      [{ name: 'BTC' }, { name: 'OLD', isDelisted: true }],
      [{ funding: '0.0000125', markPx: '100' }, { funding: '0', markPx: '1' }],
      Date.UTC(2026, 0, 1, 10, 15),
    )).toHaveLength(1);
  });

  it('ranks the cross-exchange funding divergence', () => {
    const result = computeDivergence([
      { baseSymbol: 'BTC', exchange: 'binance', fundingRate8h: 0.0001 },
      { baseSymbol: 'BTC', exchange: 'hyperliquid', fundingRate8h: -0.0001 },
      { baseSymbol: 'ETH', exchange: 'binance', fundingRate8h: 0.0002 },
    ]);
    expect(result).toHaveLength(1);
    expect(result[0]).toMatchObject({
      symbol: 'BTC',
      divergenceBps: 2190,
      short: { exchange: 'binance' },
      long: { exchange: 'hyperliquid' },
    });
  });

  it('builds a bounded buyer response and supports a symbol filter', () => {
    const rows = [
      { exchange: 'binance', symbol: 'BTCUSDT', baseSymbol: 'BTC', fundingRateNative: 0.0001, fundingIntervalHoursNative: 8, fundingRate8h: 0.0001, nextFundingTime: 1, markPrice: 100 },
      { exchange: 'bybit', symbol: 'ETHUSDT', baseSymbol: 'ETH', fundingRateNative: 0.0002, fundingIntervalHoursNative: 8, fundingRate8h: 0.0002, nextFundingTime: 1, markPrice: 50 },
    ];
    const response = buildFundingRatesResponse(rows, { symbol: 'btc' });
    expect(response.rates).toHaveLength(1);
    expect(response.rates[0].baseSymbol).toBe('BTC');
    expect(response.generatedAt).toMatch(/Z$/);
  });
});
