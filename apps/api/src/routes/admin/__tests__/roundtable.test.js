import { describe, it, expect, vi, beforeEach } from 'vitest';
import request from 'supertest';
import express from 'express';

vi.mock('../../../middleware/requireInternalAuth.js', () => ({
  default: (req, res, next) => next(),
}));

const jobMocks = vi.hoisted(() => ({
  runRoundtableStandup: vi.fn(),
  runRoundtableWatercooler: vi.fn(),
  runMemoryExtraction: vi.fn(),
  runInitiativeGenerator: vi.fn(),
}));

vi.mock('../../../jobs/roundtableStandup.js', () => ({
  runRoundtableStandup: jobMocks.runRoundtableStandup,
}));
vi.mock('../../../jobs/roundtableWatercooler.js', () => ({
  runRoundtableWatercooler: jobMocks.runRoundtableWatercooler,
}));
vi.mock('../../../jobs/memoryExtractor.js', () => ({
  runMemoryExtraction: jobMocks.runMemoryExtraction,
}));
vi.mock('../../../jobs/initiativeGenerator.js', () => ({
  runInitiativeGenerator: jobMocks.runInitiativeGenerator,
}));

import roundtableRouter from '../roundtable.js';

const app = express();
app.use(express.json());
app.use('/api/admin/roundtable', roundtableRouter);

describe('admin roundtable routes', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('POST /standup returns job result', async () => {
    jobMocks.runRoundtableStandup.mockResolvedValueOnce({ ok: 1 });
    const res = await request(app).post('/api/admin/roundtable/standup').send({});
    expect(res.status).toBe(200);
    expect(res.body.result.ok).toBe(1);
  });

  it('POST /initiative-generate returns job result', async () => {
    jobMocks.runInitiativeGenerator.mockResolvedValueOnce({ createdCount: 2 });
    const res = await request(app).post('/api/admin/roundtable/initiative-generate').send({});
    expect(res.status).toBe(200);
    expect(res.body.result.createdCount).toBe(2);
  });
});
