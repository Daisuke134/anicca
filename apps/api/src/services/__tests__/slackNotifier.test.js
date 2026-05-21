import { beforeEach, describe, expect, it, vi } from 'vitest';

const fetchMock = vi.fn();

vi.mock('undici', () => ({
  fetch: (...args) => fetchMock(...args),
}));

import { notifyPostSuccess, notifyDLQEntry, sendSlackMessage } from '../slackNotifier.js';

describe('slackNotifier', () => {
  const originalEnv = { ...process.env };

  beforeEach(() => {
    vi.clearAllMocks();
    process.env = { ...originalEnv };
  });

  it('skips sending when webhook is missing', async () => {
    delete process.env.SLACK_WEBHOOK_AGENTS;
    delete process.env.SLACK_WEBHOOK_URL;

    const result = await sendSlackMessage('#metrics', { text: 'hello' });
    expect(result).toEqual({
      sent: false,
      skipped: true,
      reason: 'webhook_not_configured',
    });
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it('sends post success message', async () => {
    process.env.SLACK_WEBHOOK_AGENTS = 'https://example.com/webhook';
    fetchMock.mockResolvedValueOnce({
      ok: true,
      status: 200,
      text: async () => 'ok',
    });

    const result = await notifyPostSuccess('x', 'post-1', 4);
    expect(result.sent).toBe(true);
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it('throws when webhook returns non-2xx', async () => {
    process.env.SLACK_WEBHOOK_URL = 'https://example.com/webhook';
    fetchMock.mockResolvedValueOnce({
      ok: false,
      status: 500,
      text: async () => 'boom',
    });

    await expect(notifyDLQEntry('hook-poster', 'failed', { id: 1 })).rejects.toThrow(
      'Slack webhook failed'
    );
  });
});
