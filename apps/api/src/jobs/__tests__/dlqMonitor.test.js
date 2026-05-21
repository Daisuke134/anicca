import { beforeEach, describe, expect, it, vi } from 'vitest';

const mocks = vi.hoisted(() => ({
  monitorDLQ: vi.fn(),
  notifyDLQEntry: vi.fn(),
}));

vi.mock('../../services/dlqMonitor.js', () => ({
  monitorDLQ: mocks.monitorDLQ,
}));

vi.mock('../../services/slackNotifier.js', () => ({
  notifyDLQEntry: mocks.notifyDLQEntry,
}));

import { runDlqMonitor } from '../dlqMonitor.js';

describe('runDlqMonitor', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('does not notify when nothing archived', async () => {
    mocks.monitorDLQ.mockResolvedValueOnce({ active: 10, archived: 0 });

    const result = await runDlqMonitor();

    expect(result).toEqual({ active: 10, archived: 0 });
    expect(mocks.notifyDLQEntry).not.toHaveBeenCalled();
  });

  it('notifies when entries are archived', async () => {
    mocks.monitorDLQ.mockResolvedValueOnce({ active: 3, archived: 7 });

    const result = await runDlqMonitor();

    expect(result.archived).toBe(7);
    expect(mocks.notifyDLQEntry).toHaveBeenCalledTimes(1);
  });
});
