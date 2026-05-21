import { describe, it, expect, vi, beforeEach } from 'vitest';
import { prismaMock } from '../../../test/setup.js';

vi.mock('../stepExecutors/registry.js', () => ({
  getExecutor: vi.fn()
}));

vi.mock('../eventEmitter.js', () => ({
  emitEvent: vi.fn().mockResolvedValue(undefined)
}));

vi.mock('../staleRecovery.js', () => ({
  maybeFinalizeMission: vi.fn().mockResolvedValue(null)
}));

describe('processQueuedSteps', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('returns 0 executed when no queued steps', async () => {
    prismaMock.$transaction.mockImplementation(async (fn) => {
      return fn({
        opsMissionStep: {
          findMany: vi.fn().mockResolvedValue([]),
          updateMany: vi.fn()
        }
      });
    });

    const { processQueuedSteps } = await import('../stepWorker.js');
    const result = await processQueuedSteps(3);

    expect(result.executed).toBe(0);
    expect(result.failed).toBe(0);
  });

  it('claims and executes a queued step', async () => {
    const mockStep = {
      id: 'step-1',
      missionId: 'mission-1',
      stepKind: 'draft_content',
      stepOrder: 0,
      input: { slot: 'morning' },
      mission: {
        proposal: {
          skillName: 'x-poster',
          payload: { slot: 'morning' }
        }
      }
    };

    const mockExecutor = vi.fn().mockResolvedValue({
      output: { content: 'test', hookId: 'h1' },
      events: []
    });

    const { getExecutor } = await import('../stepExecutors/registry.js');
    getExecutor.mockReturnValue(mockExecutor);

    let callCount = 0;
    prismaMock.$transaction.mockImplementation(async (fn) => {
      callCount++;
      if (callCount > 1) return null;
      return fn({
        opsMissionStep: {
          findMany: vi.fn().mockResolvedValue([mockStep]),
          updateMany: vi.fn().mockResolvedValue({ count: 1 })
        }
      });
    });

    prismaMock.opsMissionStep.updateMany.mockResolvedValue({ count: 1 });

    const { processQueuedSteps } = await import('../stepWorker.js');
    const result = await processQueuedSteps(3);

    expect(result.executed).toBe(1);
    expect(mockExecutor).toHaveBeenCalledWith(
      expect.objectContaining({
        input: { slot: 'morning' },
        missionId: 'mission-1',
        skillName: 'x-poster'
      })
    );
  });
});
