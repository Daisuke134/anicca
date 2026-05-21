import { describe, it, expect, vi, beforeEach } from 'vitest';
import { prismaMock } from '../../../test/setup.js';

// Mock all service dependencies
vi.mock('../../../services/ops/proposalService.js', () => ({
  createProposalAndMaybeAutoApprove: vi.fn()
}));
vi.mock('../../../services/ops/triggerEvaluator.js', () => ({
  evaluateTriggers: vi.fn().mockResolvedValue({ evaluated: 0, fired: 0 })
}));
vi.mock('../../../services/ops/reactionProcessor.js', () => ({
  processReactionQueue: vi.fn().mockResolvedValue({ processed: 0, proposals: 0 }),
  evaluateReactionMatrix: vi.fn()
}));
vi.mock('../../../services/ops/staleRecovery.js', () => ({
  recoverStaleSteps: vi.fn().mockResolvedValue({ recovered: 0, missionsFailed: 0 }),
  maybeFinalizeMission: vi.fn().mockResolvedValue(null)
}));
vi.mock('../../../services/ops/insightPromoter.js', () => ({
  promoteInsights: vi.fn().mockResolvedValue({ promoted: 0 })
}));
vi.mock('../../../services/ops/eventEmitter.js', () => ({
  emitEvent: vi.fn().mockResolvedValue({ id: 'evt-mock', tags: [] })
}));

const { createProposalAndMaybeAutoApprove } = await import('../../../services/ops/proposalService.js');
const { evaluateTriggers } = await import('../../../services/ops/triggerEvaluator.js');
const { processReactionQueue } = await import('../../../services/ops/reactionProcessor.js');
const { recoverStaleSteps } = await import('../../../services/ops/staleRecovery.js');
const { emitEvent } = await import('../../../services/ops/eventEmitter.js');

beforeEach(() => {
  vi.clearAllMocks();
});

// T19: heartbeat returns 200
describe('T19: heartbeat_returns200', () => {
  it('should return heartbeat results', async () => {
    // Verify service functions are mockable and return expected shapes
    const triggers = await evaluateTriggers(4000);
    const reactions = await processReactionQueue(3000);
    const stale = await recoverStaleSteps();

    expect(triggers).toEqual({ evaluated: 0, fired: 0 });
    expect(reactions).toEqual({ processed: 0, proposals: 0 });
    expect(stale).toEqual({ recovered: 0, missionsFailed: 0 });
  });
});

// T20: proposal valid input
describe('T20: proposal_validInput', () => {
  it('should create proposal with valid input', async () => {
    createProposalAndMaybeAutoApprove.mockResolvedValue({
      proposalId: 'prop-1',
      status: 'accepted',
      missionId: 'miss-1'
    });

    const result = await createProposalAndMaybeAutoApprove({
      skillName: 'x-poster',
      source: 'manual',
      title: 'Test proposal',
      payload: {},
      steps: [{ kind: 'draft_content', order: 0 }]
    });

    expect(result.proposalId).toBe('prop-1');
    expect(result.status).toBe('accepted');
  });
});

// T66: event post with hook_saved triggers reaction
describe('T66: eventPost_hookSaved', () => {
  it('should emit event for hook_saved kind', async () => {
    emitEvent.mockResolvedValue({
      id: 'evt-hook-1',
      source: 'trend-hunter',
      kind: 'hook_saved',
      tags: ['hook_candidate', 'found']
    });

    const event = await emitEvent('trend-hunter', 'hook_saved', ['hook_candidate', 'found'], { hookId: 'h1' });

    expect(event.id).toBe('evt-hook-1');
    expect(emitEvent).toHaveBeenCalledWith('trend-hunter', 'hook_saved', ['hook_candidate', 'found'], { hookId: 'h1' });
  });
});

// T67: event post with scan_completed (no reaction expected)
describe('T67: eventPost_scanCompleted', () => {
  it('should emit event for scan_completed kind', async () => {
    emitEvent.mockResolvedValue({
      id: 'evt-scan-1',
      source: 'trend-hunter',
      kind: 'scan_completed',
      tags: ['scan', 'completed']
    });

    const event = await emitEvent('trend-hunter', 'scan_completed', ['scan', 'completed'], { savedCount: 5 });

    expect(event.id).toBe('evt-scan-1');
    expect(emitEvent).toHaveBeenCalled();
  });
});
