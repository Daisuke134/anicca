import { describe, expect, it, vi } from 'vitest';

import {
  listSettlementRecords,
  recordSettlement,
  settlementAuditData,
} from './settlement-records.js';

const validContext = {
  paymentPayload: { x402Version: 2 },
  requirements: {
    scheme: 'exact',
    network: 'eip155:8453',
    asset: '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913',
    amount: '8000',
    payTo: '0x6592EB8EF820aBC092e8C3474fb2042dffCCEDc7',
  },
  result: {
    success: true,
    network: 'eip155:8453',
    payer: '0xe7747Fd899D8987821Bb4CB3D6aDf22565F87ce9',
    transaction: '0xcf095a8703837e2a07026c97f009ed874a0e8e7759a282b4d24c4884151092f0',
  },
  transportContext: {
    request: {
      path: '/context-compressor',
      method: 'POST',
      paymentHeader: 'must-never-be-persisted',
    },
  },
};

describe('settlement records', () => {
  it('maps a successful x402 settlement to a public audit record without payment credentials', () => {
    const data = settlementAuditData(validContext);

    expect(data).toEqual({
      eventType: 'x402_settlement',
      executedBy: 'x402_facilitator',
      requestPayload: {
        route: '/context-compressor',
        method: 'POST',
        scheme: 'exact',
        network: 'eip155:8453',
        asset: '0x833589fcd6edb6e08f4c7c32d4f71b54bda02913',
        amount_atomic: '8000',
        pay_to: '0x6592eb8ef820abc092e8c3474fb2042dffccedc7',
      },
      responsePayload: {
        success: true,
        transaction: '0xcf095a8703837e2a07026c97f009ed874a0e8e7759a282b4d24c4884151092f0',
        payer: '0xe7747fd899d8987821bb4cb3d6adf22565f87ce9',
      },
    });
    expect(JSON.stringify(data)).not.toContain('must-never-be-persisted');
  });

  it('rejects malformed or unsuccessful settlement contexts', () => {
    expect(settlementAuditData({ ...validContext, result: { ...validContext.result, success: false } })).toBeNull();
    expect(settlementAuditData({
      ...validContext,
      result: { ...validContext.result, transaction: 'not-a-tx' },
    })).toBeNull();
  });

  it('does not turn a completed payment into an HTTP failure when audit persistence is unavailable', async () => {
    const prismaClient = {
      agentAuditLog: { create: vi.fn().mockRejectedValue(new Error('db unavailable')) },
    };
    const logger = { error: vi.fn() };

    await expect(recordSettlement(validContext, { prismaClient, logger })).resolves.toBe(false);
    expect(logger.error).toHaveBeenCalledWith('x402 settlement audit persistence failed');
  });

  it('returns bounded public settlement rows for the observer', async () => {
    const prismaClient = {
      agentAuditLog: {
        findMany: vi.fn().mockResolvedValue([{
          id: '11111111-1111-1111-1111-111111111111',
          createdAt: new Date('2026-07-27T22:31:00.000Z'),
          requestPayload: settlementAuditData(validContext).requestPayload,
          responsePayload: settlementAuditData(validContext).responsePayload,
        }]),
      },
    };

    const rows = await listSettlementRecords({ prismaClient, limit: 500 });

    expect(prismaClient.agentAuditLog.findMany).toHaveBeenCalledWith(expect.objectContaining({
      where: { eventType: 'x402_settlement' },
      take: 100,
    }));
    expect(rows).toEqual([{
      id: '11111111-1111-1111-1111-111111111111',
      observed_at: '2026-07-27T22:31:00.000Z',
      route: '/context-compressor',
      method: 'POST',
      scheme: 'exact',
      network: 'eip155:8453',
      asset: '0x833589fcd6edb6e08f4c7c32d4f71b54bda02913',
      amount_atomic: '8000',
      pay_to: '0x6592eb8ef820abc092e8c3474fb2042dffccedc7',
      transaction: '0xcf095a8703837e2a07026c97f009ed874a0e8e7759a282b4d24c4884151092f0',
      payer: '0xe7747fd899d8987821bb4cb3d6adf22565f87ce9',
      success: true,
    }]);
  });
});
