import { beforeEach, describe, expect, it, vi } from 'vitest';
import express from 'express';
import request from 'supertest';

const { getFundingRatesCached } = vi.hoisted(() => ({
  getFundingRatesCached: vi.fn(),
}));

vi.mock('../../lib/funding-rates.js', () => ({
  getFundingRatesCached,
  buildFundingRatesResponse: vi.fn((rows, options) => ({
    rates: options.symbol ? rows.filter(row => row.baseSymbol === options.symbol.toUpperCase()) : rows,
    divergenceTop20: [],
    exchanges: ['binance'],
    degraded: options.errors.length > 0,
    errors: options.errors,
    generatedAt: '2026-07-27T22:55:00.000Z',
  })),
}));

vi.mock('../../lib/prisma.js', () => ({
  prisma: {
    agentAuditLog: { create: vi.fn().mockResolvedValue({ id: 'audit-id' }) },
  },
}));

import router from '../fundingRates.js';

describe('GET /funding-rates', () => {
  let app;
  beforeEach(() => {
    vi.clearAllMocks();
    app = express();
    app.use('/funding-rates', router);
  });

  it('returns normalized cached rates for a valid symbol', async () => {
    getFundingRatesCached.mockResolvedValue({
      rows: [{ baseSymbol: 'BTC', exchange: 'binance' }],
      errors: [],
    });
    const response = await request(app).get('/funding-rates?symbol=btc');
    expect(response.status).toBe(200);
    expect(response.body.rates).toHaveLength(1);
  });

  it('rejects an unsafe symbol without contacting upstreams', async () => {
    const response = await request(app).get('/funding-rates?symbol=BTC%20DROP');
    expect(response.status).toBe(400);
    expect(getFundingRatesCached).not.toHaveBeenCalled();
  });

  it('returns 502 when every upstream exchange fails', async () => {
    getFundingRatesCached.mockRejectedValue(new Error('all upstreams failed'));
    const response = await request(app).get('/funding-rates');
    expect(response.status).toBe(502);
    expect(response.body).toEqual({ error: 'Funding-rate upstreams unavailable' });
  });
});
