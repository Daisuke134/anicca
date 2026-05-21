import { describe, it, expect, vi, beforeEach } from 'vitest';

const prismaMock = vi.hoisted(() => ({
  agentPost: {
    findUnique: vi.fn(async () => null),
    create: vi.fn(async ({ data }) => ({ id: 'p1', ...data })),
  },
  agentAuditLog: {
    create: vi.fn(async ({ data }) => ({ id: 'a1', ...data })),
  },
}));

const clientMock = vi.hoisted(() => ({
  postMoltbookStatus: vi.fn(async () => ({ dryRun: true, statusId: null, url: null })),
}));

vi.mock('../../lib/prisma.js', () => ({ prisma: prismaMock }));
vi.mock('../../services/moltbookClient.js', () => ({
  postMoltbookStatus: clientMock.postMoltbookStatus,
}));

import { runMoltbookPosterJob } from '../moltbookPosterJob.js';

describe('moltbookPosterJob', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('creates a daily agent post and calls poster client', async () => {
    const res = await runMoltbookPosterJob({ dateJst: '2026-02-10', status: 'test status' });
    expect(res.ok).toBe(true);
    expect(res.externalPostId).toBe('moltbook-daily-2026-02-10');
    expect(prismaMock.agentPost.create).toHaveBeenCalledTimes(1);
    expect(clientMock.postMoltbookStatus).toHaveBeenCalledTimes(1);
    expect(prismaMock.agentAuditLog.create).toHaveBeenCalled();
  });

  it('dedupes by externalPostId', async () => {
    prismaMock.agentPost.findUnique.mockResolvedValueOnce({ id: 'existing' });
    const res = await runMoltbookPosterJob({ dateJst: '2026-02-10' });
    expect(res.ok).toBe(true);
    expect(res.deduped).toBe(true);
    expect(prismaMock.agentPost.create).toHaveBeenCalledTimes(0);
    expect(clientMock.postMoltbookStatus).toHaveBeenCalledTimes(0);
  });
});

