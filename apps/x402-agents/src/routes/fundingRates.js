import { Router } from 'express';
import { z } from 'zod';

import { buildFundingRatesResponse, getFundingRatesCached } from '../lib/funding-rates.js';
import { prisma } from '../lib/prisma.js';

const router = Router();
const QuerySchema = z.object({
  symbol: z.string().regex(/^[A-Za-z0-9]{1,20}$/).optional(),
});

router.get('/', async (req, res) => {
  const parsed = QuerySchema.safeParse(req.query);
  if (!parsed.success) {
    return res.status(400).json({ error: 'Invalid symbol' });
  }
  try {
    const { rows, errors } = await getFundingRatesCached();
    const result = buildFundingRatesResponse(rows, {
      symbol: parsed.data.symbol,
      errors,
    });
    try {
      await prisma.agentAuditLog.create({
        data: {
          eventType: 'x402_funding_rates',
          executedBy: 'x402_external',
          requestPayload: {
            symbol: parsed.data.symbol?.toUpperCase() ?? null,
          },
          responsePayload: {
            rates_count: result.rates.length,
            divergence_count: result.divergenceTop20.length,
            exchanges: result.exchanges,
            degraded: result.degraded,
          },
        },
      });
    } catch {
      console.error('funding-rates audit persistence failed');
    }
    return res.json(result);
  } catch {
    return res.status(502).json({ error: 'Funding-rate upstreams unavailable' });
  }
});

export default router;
