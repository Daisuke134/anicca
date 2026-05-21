import { describe, it, expect, vi, beforeEach } from 'vitest';

const prismaMock = vi.hoisted(() => ({
  agentAuditLog: {
    count: vi.fn(),
  },
  xPost: {
    count: vi.fn(),
  },
  tiktokPost: {
    count: vi.fn(),
  },
  $queryRaw: vi.fn(),
}));

vi.mock('../../lib/prisma.js', () => ({ prisma: prismaMock }));

const slackMock = vi.hoisted(() => ({
  sendSlackMessage: vi.fn(),
}));

vi.mock('../../services/slackNotifier.js', () => ({
  sendSlackMessage: slackMock.sendSlackMessage,
}));

import { runRoundtableStandup } from '../roundtableStandup.js';
import { runRoundtableWatercooler } from '../roundtableWatercooler.js';
import { resolveDebate } from '../roundtableDebate.js';

describe('roundtable', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('standup posts to #ops', async () => {
    prismaMock.agentAuditLog.count
      .mockResolvedValueOnce(1)
      .mockResolvedValueOnce(0)
      .mockResolvedValueOnce(0)
      .mockResolvedValueOnce(0);
    prismaMock.xPost.count.mockResolvedValueOnce(2);
    prismaMock.tiktokPost.count.mockResolvedValueOnce(1);
    prismaMock.$queryRaw.mockResolvedValueOnce([{ outcome_count: 10, tap_count: 3 }]);

    await runRoundtableStandup({ nowMs: Date.now() });
    expect(slackMock.sendSlackMessage).toHaveBeenCalledTimes(1);
  });

  it('watercooler skips when incidents exist', async () => {
    prismaMock.agentAuditLog.count.mockResolvedValueOnce(1);
    const res = await runRoundtableWatercooler({ nowMs: Date.now() });
    expect(res.skipped).toBe(true);
    expect(slackMock.sendSlackMessage).toHaveBeenCalledTimes(0);
  });

  it('debate resolves with safety priority', () => {
    const res = resolveDebate({
      anicca: { id: 'a', priority: 'safety' },
      growth: { id: 'g', violatesSafety: true },
    });
    expect(res.decision).toBe('reject_growth');
  });
});
