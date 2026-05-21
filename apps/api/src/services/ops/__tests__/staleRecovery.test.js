import { describe, it, expect, vi, beforeEach } from 'vitest';
import { prismaMock } from '../../../test/setup.js';

// Mock policyService
const mockGetPolicy = vi.fn();
vi.mock('../policyService.js', () => ({
  getPolicy: mockGetPolicy
}));

// Mock eventEmitter
vi.mock('../eventEmitter.js', () => ({
  emitEvent: vi.fn().mockResolvedValue({ id: 'evt-mock' })
}));

beforeEach(() => {
  mockGetPolicy.mockReset();
});

describe('staleRecovery', () => {
  // T16: test_recoverStaleSteps_markFailed
  it('T16: marks stale steps as failed after threshold', async () => {
    mockGetPolicy.mockResolvedValue({ value: 30 });

    const thirtyFiveMinutesAgo = new Date(Date.now() - 35 * 60 * 1000);
    prismaMock.opsMissionStep.findMany.mockResolvedValue([{
      id: 'step-1',
      missionId: 'mission-1',
      status: 'running',
      reservedAt: thirtyFiveMinutesAgo
    }]);

    prismaMock.opsMissionStep.updateMany.mockResolvedValue({ count: 1 });

    // Mock maybeFinalizeMission transaction
    prismaMock.$transaction.mockImplementation(async (fn) => {
      const result = await fn(prismaMock);
      return result;
    });
    prismaMock.opsMissionStep.findMany.mockResolvedValueOnce([{
      id: 'step-1',
      missionId: 'mission-1',
      status: 'running',
      reservedAt: thirtyFiveMinutesAgo
    }]);
    // For maybeFinalizeMission internal call
    prismaMock.opsMissionStep.findMany.mockResolvedValueOnce([
      { status: 'failed' }
    ]);
    prismaMock.opsMission.update.mockResolvedValue({});
    prismaMock.opsMission.findUnique.mockResolvedValue({
      id: 'mission-1',
      proposalId: 'prop-1',
      proposal: { skillName: 'x-poster' }
    });

    const { recoverStaleSteps } = await import('../staleRecovery.js');
    const result = await recoverStaleSteps();

    expect(result.recovered).toBe(1);
    expect(prismaMock.opsMissionStep.updateMany).toHaveBeenCalledWith(
      expect.objectContaining({
        where: { id: 'step-1', status: 'running' },
        data: expect.objectContaining({
          status: 'failed',
          lastError: expect.stringContaining('Stale')
        })
      })
    );
  });

  // T17: test_maybeFinalizeMission_allSucceeded
  it('T17: finalizes mission as succeeded when all steps succeeded', async () => {
    prismaMock.$transaction.mockImplementation(async (fn) => fn(prismaMock));
    prismaMock.opsMissionStep.findMany.mockResolvedValue([
      { status: 'succeeded' },
      { status: 'succeeded' },
      { status: 'succeeded' }
    ]);
    prismaMock.opsMission.update.mockResolvedValue({});
    prismaMock.opsMission.findUnique.mockResolvedValue({
      id: 'mission-1',
      proposalId: 'prop-1',
      proposal: { skillName: 'x-poster' }
    });

    const { maybeFinalizeMission } = await import('../staleRecovery.js');
    const result = await maybeFinalizeMission('mission-1');

    expect(result).toBe('succeeded');
  });

  // T18: test_maybeFinalizeMission_anyFailed
  it('T18: finalizes mission as failed when any step failed', async () => {
    prismaMock.$transaction.mockImplementation(async (fn) => fn(prismaMock));
    prismaMock.opsMissionStep.findMany.mockResolvedValue([
      { status: 'succeeded' },
      { status: 'failed' },
      { status: 'succeeded' }
    ]);
    prismaMock.opsMissionStep.updateMany.mockResolvedValue({ count: 0 });
    prismaMock.opsMission.update.mockResolvedValue({});
    prismaMock.opsMission.findUnique.mockResolvedValue({
      id: 'mission-1',
      proposalId: 'prop-1',
      proposal: { skillName: 'x-poster' }
    });

    const { maybeFinalizeMission } = await import('../staleRecovery.js');
    const result = await maybeFinalizeMission('mission-1');

    expect(result).toBe('failed');
  });

  // T18b: test_maybeFinalizeMission_cancelsQueuedOnFailure
  it('T18b: cancels queued steps and fails mission when a step fails with queued remaining', async () => {
    prismaMock.$transaction.mockImplementation(async (fn) => fn(prismaMock));
    prismaMock.opsMissionStep.findMany.mockResolvedValue([
      { status: 'failed' },
      { status: 'queued' },
      { status: 'queued' }
    ]);
    prismaMock.opsMissionStep.updateMany.mockResolvedValue({ count: 2 });
    prismaMock.opsMission.update.mockResolvedValue({});
    prismaMock.opsMission.findUnique.mockResolvedValue({
      id: 'mission-1',
      proposalId: 'prop-1',
      proposal: { skillName: 'x-poster' }
    });

    const { maybeFinalizeMission } = await import('../staleRecovery.js');
    const result = await maybeFinalizeMission('mission-1');

    expect(result).toBe('failed');
    // Verify queued steps were cancelled
    expect(prismaMock.opsMissionStep.updateMany).toHaveBeenCalledWith({
      where: { missionId: 'mission-1', status: 'queued' },
      data: expect.objectContaining({ status: 'cancelled' })
    });
    // Verify mission was finalized
    expect(prismaMock.opsMission.update).toHaveBeenCalledWith(
      expect.objectContaining({
        data: expect.objectContaining({ status: 'failed' })
      })
    );
  });

  // T18c: returns null when failed step exists but other step still running
  it('T18c: returns null when step failed but another is still running', async () => {
    prismaMock.$transaction.mockImplementation(async (fn) => fn(prismaMock));
    prismaMock.opsMissionStep.findMany.mockResolvedValue([
      { status: 'failed' },
      { status: 'running' },
      { status: 'queued' }
    ]);
    prismaMock.opsMissionStep.updateMany.mockResolvedValue({ count: 1 });

    const { maybeFinalizeMission } = await import('../staleRecovery.js');
    const result = await maybeFinalizeMission('mission-1');

    // Should cancel queued but wait for running step
    expect(result).toBeNull();
    expect(prismaMock.opsMissionStep.updateMany).toHaveBeenCalledWith({
      where: { missionId: 'mission-1', status: 'queued' },
      data: expect.objectContaining({ status: 'cancelled' })
    });
  });
});
