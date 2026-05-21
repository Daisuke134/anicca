import { describe, it, expect, vi, beforeEach } from 'vitest';
import { prismaMock } from '../../../test/setup.js';

// Mock proposalService
const mockCreateProposal = vi.fn();
vi.mock('../proposalService.js', () => ({
  createProposalAndMaybeAutoApprove: mockCreateProposal
}));

beforeEach(() => {
  mockCreateProposal.mockReset();
});

describe('triggerEvaluator', () => {
  // T10: test_evaluateTriggers_fireOnMatch
  it('T10: fires trigger and creates proposal when event matches', async () => {
    const now = new Date();
    prismaMock.opsTriggerRule.findMany.mockResolvedValue([{
      id: 'rule-1',
      name: 'on_tweet_posted',
      eventKind: 'tweet_posted',
      condition: {},
      cooldownMin: 60,
      lastFiredAt: null,
      enabled: true,
      proposalTemplate: {
        skill_name: 'x-poster',
        title: 'Fetch metrics for posted tweet',
        steps: [{ kind: 'fetch_metrics', order: 0 }]
      }
    }]);

    prismaMock.opsEvent.findMany.mockResolvedValue([{
      id: 'evt-1',
      kind: 'tweet_posted',
      createdAt: now,
      payload: {}
    }]);

    // Mock CAS update (updateMany with lastFiredAt guard)
    prismaMock.opsTriggerRule.updateMany.mockResolvedValue({ count: 1 });

    mockCreateProposal.mockResolvedValue({
      proposalId: 'prop-1',
      status: 'accepted',
      missionId: 'mission-1'
    });

    const { evaluateTriggers } = await import('../triggerEvaluator.js');
    const result = await evaluateTriggers(10000);

    expect(result.fired).toBe(1);
    expect(mockCreateProposal).toHaveBeenCalled();
  });

  // T11: test_evaluateTriggers_cooldown
  it('T11: skips trigger during cooldown period', async () => {
    const oneMinuteAgo = new Date(Date.now() - 60 * 1000);
    prismaMock.opsTriggerRule.findMany.mockResolvedValue([{
      id: 'rule-1',
      name: 'on_tweet_posted',
      eventKind: 'tweet_posted',
      condition: {},
      cooldownMin: 60,
      lastFiredAt: oneMinuteAgo,
      enabled: true,
      proposalTemplate: {}
    }]);

    const { evaluateTriggers } = await import('../triggerEvaluator.js');
    const result = await evaluateTriggers(10000);

    expect(result.fired).toBe(0);
    expect(mockCreateProposal).not.toHaveBeenCalled();
  });

  // T12: test_evaluateTriggers_delayCondition
  it('T12: skips trigger when delay_min not reached', async () => {
    prismaMock.opsTriggerRule.findMany.mockResolvedValue([{
      id: 'rule-2',
      name: 'delayed_metrics',
      eventKind: 'tweet_posted',
      condition: { delay_min: 1440 },
      cooldownMin: 60,
      lastFiredAt: null,
      enabled: true,
      proposalTemplate: {
        skill_name: 'x-poster',
        title: 'Delayed metrics',
        steps: [{ kind: 'fetch_metrics', order: 0 }]
      }
    }]);

    // Event was posted 10 minutes ago (delay_min=1440, needs 24h)
    const tenMinutesAgo = new Date(Date.now() - 10 * 60 * 1000);
    prismaMock.opsEvent.findMany.mockResolvedValue([{
      id: 'evt-1',
      kind: 'tweet_posted',
      createdAt: tenMinutesAgo,
      payload: {}
    }]);

    const { evaluateTriggers } = await import('../triggerEvaluator.js');
    const result = await evaluateTriggers(10000);

    expect(result.fired).toBe(0);
  });

  // T39: test_delayMin_tooEarly
  it('T39: does not fire when event is too recent for delay_min', async () => {
    prismaMock.opsTriggerRule.findMany.mockResolvedValue([{
      id: 'rule-3',
      name: 'delayed_trigger',
      eventKind: 'test_event',
      condition: { delay_min: 1440 },
      cooldownMin: 60,
      lastFiredAt: null,
      enabled: true,
      proposalTemplate: {
        skill_name: 'test',
        title: 'Delayed',
        steps: [{ kind: 'fetch_metrics', order: 0 }]
      }
    }]);

    const tenMinutesAgo = new Date(Date.now() - 10 * 60 * 1000);
    prismaMock.opsEvent.findMany.mockResolvedValue([{
      id: 'evt-1',
      kind: 'test_event',
      createdAt: tenMinutesAgo,
      payload: {}
    }]);

    const { evaluateTriggers } = await import('../triggerEvaluator.js');
    const result = await evaluateTriggers(10000);

    expect(result.fired).toBe(0);
  });

  // T40: test_delayMin_tooOld
  it('T40: does not fire when event is too old (past delay_min * 2 window)', async () => {
    prismaMock.opsTriggerRule.findMany.mockResolvedValue([{
      id: 'rule-4',
      name: 'delayed_trigger',
      eventKind: 'test_event',
      condition: { delay_min: 1440 },
      cooldownMin: 60,
      lastFiredAt: null,
      enabled: true,
      proposalTemplate: {
        skill_name: 'test',
        title: 'Delayed',
        steps: [{ kind: 'fetch_metrics', order: 0 }]
      }
    }]);

    // Event is 3000 minutes old (delay_min=1440, max=2880 → too old)
    const threeThousandMinutesAgo = new Date(Date.now() - 3000 * 60 * 1000);
    prismaMock.opsEvent.findMany.mockResolvedValue([{
      id: 'evt-1',
      kind: 'test_event',
      createdAt: threeThousandMinutesAgo,
      payload: {}
    }]);

    const { evaluateTriggers } = await import('../triggerEvaluator.js');
    const result = await evaluateTriggers(10000);

    expect(result.fired).toBe(0);
  });
});
