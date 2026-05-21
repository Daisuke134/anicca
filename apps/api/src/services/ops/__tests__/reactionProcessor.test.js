import { describe, it, expect, vi, beforeEach } from 'vitest';
import { prismaMock } from '../../../test/setup.js';

// Mock proposalService
const mockCreateProposal = vi.fn();
vi.mock('../proposalService.js', () => ({
  createProposalAndMaybeAutoApprove: mockCreateProposal
}));

// Mock policyService
const mockGetPolicy = vi.fn();
vi.mock('../policyService.js', () => ({
  getPolicy: mockGetPolicy
}));

beforeEach(() => {
  mockCreateProposal.mockReset();
  mockGetPolicy.mockReset();
});

describe('reactionProcessor', () => {
  // T13: test_processReactionQueue_createProposal
  it('T13: processes pending reaction and creates proposal', async () => {
    prismaMock.opsReaction.findMany.mockResolvedValue([{
      id: 'reaction-1',
      eventId: 'evt-1',
      targetSkill: 'x-poster',
      actionType: 'analyze_engagement',
      status: 'pending'
    }]);

    mockCreateProposal.mockResolvedValue({
      proposalId: 'prop-1',
      status: 'accepted',
      missionId: 'mission-1'
    });

    // Mock atomic claim (updateMany with status guard)
    prismaMock.opsReaction.updateMany.mockResolvedValue({ count: 1 });
    prismaMock.opsReaction.update.mockResolvedValue({});

    const { processReactionQueue } = await import('../reactionProcessor.js');
    const result = await processReactionQueue(10000);

    expect(result.processed).toBe(1);
    expect(result.proposals).toBe(1);
    expect(prismaMock.opsReaction.update).toHaveBeenCalledWith(
      expect.objectContaining({
        where: { id: 'reaction-1' },
        data: expect.objectContaining({ status: 'processed' })
      })
    );
  });

  // T14: test_evaluateReactionMatrix_probability
  it('T14: creates reaction when probability passes', async () => {
    // Force Math.random to return 0.2 (below probability 0.3)
    const originalRandom = Math.random;
    Math.random = () => 0.2;

    mockGetPolicy.mockResolvedValue({
      patterns: [{
        source: 'x-poster',
        tags: ['tweet', 'posted'],
        target: 'trend-hunter',
        type: 'analyze_engagement',
        probability: 0.3,
        cooldown: 60
      }]
    });

    prismaMock.opsReaction.findFirst.mockResolvedValue(null); // No recent reaction
    prismaMock.opsReaction.create.mockResolvedValue({ id: 'reaction-1' });

    const { evaluateReactionMatrix } = await import('../reactionProcessor.js');
    await evaluateReactionMatrix({
      id: 'evt-1',
      source: 'x-poster',
      tags: ['tweet', 'posted'],
      payload: {}
    });

    expect(prismaMock.opsReaction.create).toHaveBeenCalled();

    Math.random = originalRandom;
  });

  // T15: test_evaluateReactionMatrix_cooldown
  it('T15: does not create reaction during cooldown', async () => {
    mockGetPolicy.mockResolvedValue({
      patterns: [{
        source: 'x-poster',
        tags: ['tweet', 'posted'],
        target: 'trend-hunter',
        type: 'analyze_engagement',
        probability: 1.0, // Always match
        cooldown: 120
      }]
    });

    // Recent reaction exists within cooldown
    prismaMock.opsReaction.findFirst.mockResolvedValue({
      id: 'recent-reaction',
      createdAt: new Date()
    });

    const { evaluateReactionMatrix } = await import('../reactionProcessor.js');
    await evaluateReactionMatrix({
      id: 'evt-1',
      source: 'x-poster',
      tags: ['tweet', 'posted'],
      payload: {}
    });

    expect(prismaMock.opsReaction.create).not.toHaveBeenCalled();
  });
});
