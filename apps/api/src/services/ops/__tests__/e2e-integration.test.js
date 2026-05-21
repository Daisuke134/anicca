/**
 * E2E Integration Tests — Full Closed-Loop Chain Verification
 *
 * These tests verify the COMPLETE chain across multiple services:
 * Proposal → Mission → Steps → Events → Triggers → Reactions → new Proposal
 *
 * Spec reference: 12-e2e-integration-tests.md (I1-I22)
 * Boundary: B2 (DB chain) + B3 (Event chain) level using mocked Prisma
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { prismaMock } from '../../../test/setup.js';
import { createProposalAndMaybeAutoApprove } from '../proposalService.js';
import { maybeFinalizeMission } from '../staleRecovery.js';
import { evaluateTriggers } from '../triggerEvaluator.js';
import { processReactionQueue } from '../reactionProcessor.js';
import { clearPolicyCache } from '../policyService.js';

// Mock approvalNotifier
vi.mock('../approvalNotifier.js', () => ({
  sendApprovalNotification: vi.fn()
}));

beforeEach(() => {
  clearPolicyCache();
});

// ============================================================
// I1: Proposal → Mission chain (auto-approve)
// ============================================================
describe('I1: e2e_proposal_to_mission_chain', () => {
  it('auto-approved proposal creates mission with correctly ordered steps', async () => {
    // -- Arrange --
    prismaMock.opsProposal.count.mockResolvedValue(0);
    prismaMock.opsProposal.create.mockResolvedValue({ id: 'prop-e2e-1' });
    prismaMock.opsEvent.create.mockResolvedValue({ id: 'evt-1', tags: [] });

    // Policy: auto_approve enabled for safe steps
    prismaMock.opsPolicy.findUnique.mockResolvedValue({
      key: 'auto_approve',
      value: { enabled: true, allowed_step_kinds: ['draft_content', 'verify_content', 'fetch_metrics'] }
    });

    // Mission creation captures the steps
    prismaMock.opsMission.create.mockResolvedValue({
      id: 'miss-e2e-1',
      steps: [
        { id: 's1', stepKind: 'draft_content', stepOrder: 0, status: 'queued' },
        { id: 's2', stepKind: 'verify_content', stepOrder: 1, status: 'queued' },
        { id: 's3', stepKind: 'fetch_metrics', stepOrder: 2, status: 'queued' }
      ]
    });
    prismaMock.opsProposal.update.mockResolvedValue({});

    // -- Act --
    const result = await createProposalAndMaybeAutoApprove({
      skillName: 'x-poster',
      source: 'cron',
      title: 'E2E: Full content pipeline',
      payload: { topic: 'mindfulness' },
      steps: [
        { kind: 'draft_content', order: 0, input: { topic: 'mindfulness' } },
        { kind: 'verify_content', order: 1 },
        { kind: 'fetch_metrics', order: 2 }
      ]
    });

    // -- Assert --
    expect(result.status).toBe('accepted');
    expect(result.missionId).toBe('miss-e2e-1');
    expect(result.proposalId).toBe('prop-e2e-1');

    // Verify mission was created with correct step structure
    expect(prismaMock.opsMission.create).toHaveBeenCalledWith(
      expect.objectContaining({
        data: expect.objectContaining({
          proposalId: 'prop-e2e-1',
          status: 'running',
          steps: {
            create: expect.arrayContaining([
              expect.objectContaining({ stepKind: 'draft_content', stepOrder: 0 }),
              expect.objectContaining({ stepKind: 'verify_content', stepOrder: 1 }),
              expect.objectContaining({ stepKind: 'fetch_metrics', stepOrder: 2 })
            ])
          }
        })
      })
    );

    // Verify proposal was accepted
    expect(prismaMock.opsProposal.update).toHaveBeenCalledWith(
      expect.objectContaining({
        data: expect.objectContaining({ status: 'accepted' })
      })
    );

    // Verify events were emitted (proposal:created + proposal:auto_approved)
    expect(prismaMock.opsEvent.create).toHaveBeenCalledTimes(2);
  });
});

// ============================================================
// I3: Full mission success — all steps succeeded → mission finalized
// ============================================================
describe('I3: e2e_mission_finalization_success', () => {
  it('mission finalizes as succeeded when all steps complete successfully', async () => {
    prismaMock.$transaction.mockImplementation(async (fn) => fn(prismaMock));

    prismaMock.opsMissionStep.findMany.mockResolvedValue([
      { status: 'succeeded' },
      { status: 'succeeded' },
      { status: 'succeeded' }
    ]);
    prismaMock.opsMission.update.mockResolvedValue({});
    prismaMock.opsMission.findUnique.mockResolvedValue({
      id: 'miss-e2e-3',
      proposalId: 'prop-e2e-3',
      proposal: { skillName: 'x-poster' }
    });

    const result = await maybeFinalizeMission('miss-e2e-3');

    expect(result).toBe('succeeded');
    expect(prismaMock.opsMission.update).toHaveBeenCalledWith(
      expect.objectContaining({
        data: expect.objectContaining({ status: 'succeeded' })
      })
    );
  });
});

// ============================================================
// I4: Step failure cascade — failed step → cancel queued → mission failed
// ============================================================
describe('I4: e2e_step_failure_cascade', () => {
  it('step failure cancels remaining queued steps and fails mission', async () => {
    prismaMock.$transaction.mockImplementation(async (fn) => fn(prismaMock));

    // Step 0: succeeded, Step 1: failed, Step 2: queued, Step 3: queued
    prismaMock.opsMissionStep.findMany.mockResolvedValue([
      { status: 'succeeded' },
      { status: 'failed' },
      { status: 'queued' },
      { status: 'queued' }
    ]);
    prismaMock.opsMissionStep.updateMany.mockResolvedValue({ count: 2 });
    prismaMock.opsMission.update.mockResolvedValue({});
    prismaMock.opsMission.findUnique.mockResolvedValue({
      id: 'miss-e2e-4',
      proposalId: 'prop-e2e-4',
      proposal: { skillName: 'x-poster' }
    });

    const result = await maybeFinalizeMission('miss-e2e-4');

    // Queued steps must be cancelled
    expect(prismaMock.opsMissionStep.updateMany).toHaveBeenCalledWith({
      where: { missionId: 'miss-e2e-4', status: 'queued' },
      data: expect.objectContaining({ status: 'cancelled' })
    });

    // Mission must be failed
    expect(result).toBe('failed');
    expect(prismaMock.opsMission.update).toHaveBeenCalledWith(
      expect.objectContaining({
        data: expect.objectContaining({ status: 'failed' })
      })
    );
  });
});

// ============================================================
// I5: Cap gate prevents mission creation
// ============================================================
describe('I5: e2e_cap_gate_prevents_mission', () => {
  it('X daily quota reached → proposal rejected, no mission created', async () => {
    prismaMock.opsProposal.count.mockResolvedValue(0);

    // Cap gate: x_autopost enabled + quota reached
    prismaMock.opsPolicy.findUnique
      .mockResolvedValueOnce({ key: 'x_autopost', value: { enabled: true } })
      .mockResolvedValueOnce({ key: 'x_daily_quota', value: { limit: 3 } });
    prismaMock.opsEvent.count.mockResolvedValue(3); // quota reached

    prismaMock.opsProposal.create.mockResolvedValue({ id: 'prop-e2e-5' });
    prismaMock.opsEvent.create.mockResolvedValue({ id: 'evt-1', tags: [] });

    const result = await createProposalAndMaybeAutoApprove({
      skillName: 'x-poster',
      source: 'cron',
      title: 'E2E: Cap gate test',
      payload: {},
      steps: [{ kind: 'post_x', order: 0 }]
    });

    expect(result.status).toBe('rejected');
    expect(result.rejectReason).toContain('X daily quota');
    // Mission should NOT have been created
    expect(prismaMock.opsMission.create).not.toHaveBeenCalled();
  });
});

// ============================================================
// I17 (simplified): X-poster full loop — Kill Switch blocks auto-approve
// ============================================================
describe('I17: e2e_x_poster_kill_switch', () => {
  it('x-poster proposal with post_x step stays pending (Kill Switch)', async () => {
    prismaMock.opsProposal.count.mockResolvedValue(0);

    // Cap gate: x_autopost enabled + quota NOT reached
    prismaMock.opsPolicy.findUnique
      .mockResolvedValueOnce({ key: 'x_autopost', value: { enabled: true } })
      .mockResolvedValueOnce({ key: 'x_daily_quota', value: { limit: 10 } });
    prismaMock.opsEvent.count.mockResolvedValue(1); // below quota

    prismaMock.opsProposal.create.mockResolvedValue({ id: 'prop-e2e-17' });
    prismaMock.opsEvent.create.mockResolvedValue({ id: 'evt-1', tags: [] });

    // Policy allows post_x (but Kill Switch overrides)
    prismaMock.opsPolicy.findUnique.mockResolvedValue({
      key: 'auto_approve',
      value: { enabled: true, allowed_step_kinds: ['draft_content', 'verify_content', 'post_x'] }
    });

    const result = await createProposalAndMaybeAutoApprove({
      skillName: 'x-poster',
      source: 'cron',
      title: 'E2E: X poster full loop',
      payload: { topic: 'procrastination' },
      steps: [
        { kind: 'draft_content', order: 0, input: { topic: 'procrastination' } },
        { kind: 'verify_content', order: 1 },
        { kind: 'post_x', order: 2 }
      ]
    });

    // Kill Switch: post_x → NEVER auto-approve
    expect(result.status).toBe('pending');
    expect(result.missionId).toBeUndefined();
    // Mission should NOT have been created (awaiting human approval)
    expect(prismaMock.opsMission.create).not.toHaveBeenCalled();
  });
});

// ============================================================
// I11: Trigger fires on event match → new Proposal
// ============================================================
describe('I11: e2e_trigger_fires_on_event', () => {
  it('tweet_posted event fires engagement analysis trigger', async () => {
    const twentyFourHoursAgo = new Date(Date.now() - 24 * 60 * 60 * 1000);

    // Find active trigger rules (model: opsTriggerRule)
    prismaMock.opsTriggerRule.findMany.mockResolvedValue([{
      id: 'trig-1',
      name: 'engagement_analysis_24h',
      eventKind: 'tweet_posted',
      enabled: true,
      condition: { delay_min: 1440 },
      cooldownMin: 60,
      lastFiredAt: null,
      proposalTemplate: {
        skill_name: 'x-poster',
        title: 'Analyze tweet engagement',
        steps: [
          { kind: 'fetch_metrics', order: 0 },
          { kind: 'analyze_engagement', order: 1 }
        ]
      }
    }]);

    // Find matching events (24h old event matches delay_min=1440)
    prismaMock.opsEvent.findMany.mockResolvedValue([{
      id: 'evt-tweet-1',
      kind: 'tweet_posted',
      source: 'x-poster',
      createdAt: twentyFourHoursAgo,
      payload: { tweetId: '123456' },
      missionId: 'miss-original'
    }]);

    // CAS update: lastFiredAt guard
    prismaMock.opsTriggerRule.updateMany.mockResolvedValue({ count: 1 });

    // Proposal creation (auto-approve path for fetch_metrics + analyze_engagement)
    prismaMock.opsProposal.count.mockResolvedValue(0);
    prismaMock.opsProposal.create.mockResolvedValue({ id: 'prop-trigger-1' });
    prismaMock.opsEvent.create.mockResolvedValue({ id: 'evt-2', tags: [] });
    prismaMock.opsPolicy.findUnique.mockResolvedValue({
      key: 'auto_approve',
      value: { enabled: true, allowed_step_kinds: ['fetch_metrics', 'analyze_engagement'] }
    });
    prismaMock.opsMission.create.mockResolvedValue({
      id: 'miss-trigger-1',
      steps: [
        { id: 's1', stepKind: 'fetch_metrics', stepOrder: 0 },
        { id: 's2', stepKind: 'analyze_engagement', stepOrder: 1 }
      ]
    });
    prismaMock.opsProposal.update.mockResolvedValue({});

    const result = await evaluateTriggers(4000);

    // Trigger should have fired
    expect(result.fired).toBeGreaterThanOrEqual(1);

    // Trigger lastFiredAt should be updated (CAS guard)
    expect(prismaMock.opsTriggerRule.updateMany).toHaveBeenCalledWith(
      expect.objectContaining({
        where: { id: 'trig-1', lastFiredAt: null },
        data: expect.objectContaining({ lastFiredAt: expect.any(Date) })
      })
    );
  });
});

// ============================================================
// I15: Suffering detected → nudge Proposal via Reaction
// ============================================================
describe('I15: e2e_suffering_triggers_nudge', () => {
  it('suffering_detected event creates nudge proposal via reaction queue', async () => {
    // Pending reactions for suffering_detected
    prismaMock.opsReaction.findMany.mockResolvedValue([{
      id: 'react-1',
      eventId: 'evt-suffering-1',
      targetSkill: 'nudge-engine',
      reactionType: 'draft_nudge',
      status: 'pending',
      cooldownUntil: null,
      event: {
        id: 'evt-suffering-1',
        kind: 'suffering_detected',
        source: 'nudge-engine',
        payload: { severity: 0.8, userId: 'user-123', problemType: 'procrastination' }
      }
    }]);

    // Proposal creation for nudge
    prismaMock.opsProposal.count.mockResolvedValue(0);
    prismaMock.opsProposal.create.mockResolvedValue({ id: 'prop-nudge-1' });
    prismaMock.opsEvent.create.mockResolvedValue({ id: 'evt-2', tags: [] });

    // send_nudge is Kill Switch → pending (no auto-approve)
    prismaMock.opsPolicy.findUnique.mockResolvedValue({
      key: 'auto_approve',
      value: { enabled: true, allowed_step_kinds: ['draft_nudge'] }
    });

    // Atomic claim mock
    prismaMock.opsReaction.updateMany.mockResolvedValue({ count: 1 });
    prismaMock.opsReaction.update.mockResolvedValue({});

    const result = await processReactionQueue(4000);

    expect(result.processed).toBeGreaterThanOrEqual(1);

    // Reaction should be marked processed
    expect(prismaMock.opsReaction.update).toHaveBeenCalledWith(
      expect.objectContaining({
        where: { id: 'react-1' },
        data: expect.objectContaining({ status: 'processed' })
      })
    );
  });
});

// ============================================================
// I22 (simplified): Trend-hunter loop — TikTok post detection
// ============================================================
describe('I22: e2e_trend_hunter_tiktok', () => {
  it('trend-hunter proposal with post_tiktok stays pending (Kill Switch)', async () => {
    prismaMock.opsProposal.count.mockResolvedValue(0);

    // No cap gate for trend-hunter (no tiktok_autopost policy)
    prismaMock.opsPolicy.findUnique.mockResolvedValue(null);

    prismaMock.opsProposal.create.mockResolvedValue({ id: 'prop-e2e-22' });
    prismaMock.opsEvent.create.mockResolvedValue({ id: 'evt-1', tags: [] });

    // auto_approve policy — even if allowed, Kill Switch blocks post_tiktok
    prismaMock.opsPolicy.findUnique.mockResolvedValue({
      key: 'auto_approve',
      value: { enabled: true, allowed_step_kinds: ['run_trend_scan', 'evaluate_hook', 'post_tiktok'] }
    });

    const result = await createProposalAndMaybeAutoApprove({
      skillName: 'trend-hunter',
      source: 'cron',
      title: 'E2E: TikTok trend scan + post',
      payload: { platform: 'tiktok' },
      steps: [
        { kind: 'run_trend_scan', order: 0 },
        { kind: 'evaluate_hook', order: 1 },
        { kind: 'post_tiktok', order: 2 }
      ]
    });

    // Kill Switch: post_tiktok → NEVER auto-approve
    expect(result.status).toBe('pending');
    expect(prismaMock.opsMission.create).not.toHaveBeenCalled();
  });
});

// ============================================================
// I20: Stale recovery — running step → failed after threshold
// ============================================================
describe('I20: e2e_stale_recovery', () => {
  it('stale step is recovered to failed, mission finalizes as failed', async () => {
    const thirtyFiveMinutesAgo = new Date(Date.now() - 35 * 60 * 1000);

    // Policy: stale threshold = 30 min
    prismaMock.opsPolicy.findUnique.mockResolvedValue({ value: 30 });

    // Stale step found
    prismaMock.opsMissionStep.findMany.mockResolvedValueOnce([{
      id: 'step-stale-1',
      missionId: 'miss-stale-1',
      status: 'running',
      reservedAt: thirtyFiveMinutesAgo
    }]);
    // Status-guarded updateMany for stale step recovery
    prismaMock.opsMissionStep.updateMany.mockResolvedValueOnce({ count: 1 });

    // maybeFinalizeMission will be called
    prismaMock.$transaction.mockImplementation(async (fn) => fn(prismaMock));

    // After stale recovery: step is failed, other steps queued
    prismaMock.opsMissionStep.findMany.mockResolvedValueOnce([
      { status: 'failed' },
      { status: 'queued' }
    ]);
    prismaMock.opsMissionStep.updateMany.mockResolvedValueOnce({ count: 1 });
    prismaMock.opsMission.update.mockResolvedValue({});
    prismaMock.opsMission.findUnique.mockResolvedValue({
      id: 'miss-stale-1',
      proposalId: 'prop-stale-1',
      proposal: { skillName: 'x-poster' }
    });

    const { recoverStaleSteps } = await import('../staleRecovery.js');
    const result = await recoverStaleSteps();

    expect(result.recovered).toBe(1);

    // Step should be marked failed (status-guarded updateMany)
    expect(prismaMock.opsMissionStep.updateMany).toHaveBeenCalledWith(
      expect.objectContaining({
        where: { id: 'step-stale-1', status: 'running' },
        data: expect.objectContaining({
          status: 'failed',
          lastError: expect.stringContaining('Stale')
        })
      })
    );
  });
});
