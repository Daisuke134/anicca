import { describe, it, expect, vi, beforeEach } from 'vitest';

const prismaMocks = vi.hoisted(() => ({
  agentAuditLog: {
    count: vi.fn(),
  },
}));

vi.mock('../../lib/prisma.js', () => ({ prisma: prismaMocks }));

vi.mock('node:fs/promises', async () => {
  return {
    readdir: vi.fn().mockResolvedValue(['tiktok-poster.jsonl']),
    readFile: vi.fn().mockResolvedValue('{"timestamp":"2026-02-08T00:00:00.000Z"}\n'),
  };
});

import { runAutonomyCheck } from '../autonomyCheck.js';

describe('autonomyCheck', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('fails when stale dlq exists', async () => {
    prismaMocks.agentAuditLog.count.mockResolvedValueOnce(0).mockResolvedValueOnce(0);

    const now = new Date('2026-02-09T12:00:00.000Z');
    const res = await runAutonomyCheck({ now, dlqDir: '/tmp/anicca/dlq' });
    expect(res.pass).toBe(false);
    expect(res.metrics.dlqStale).toBeGreaterThan(0);
  });

  it('passes when no incidents and dlq empty', async () => {
    const fs = await import('node:fs/promises');
    fs.readdir.mockResolvedValueOnce([]);
    prismaMocks.agentAuditLog.count.mockResolvedValueOnce(0).mockResolvedValueOnce(0);

    const now = new Date('2026-02-09T12:00:00.000Z');
    const res = await runAutonomyCheck({ now, dlqDir: '/tmp/anicca/dlq' });
    expect(res.pass).toBe(true);
  });
});
