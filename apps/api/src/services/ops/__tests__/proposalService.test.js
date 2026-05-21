import { describe, it, expect, vi, beforeEach } from 'vitest';
import { prismaMock } from '../../../test/setup.js';
import { createProposalAndMaybeAutoApprove } from '../proposalService.js';
import { clearPolicyCache } from '../policyService.js';

// Mock approvalNotifier
vi.mock('../approvalNotifier.js', () => ({
  sendApprovalNotification: vi.fn()
}));

beforeEach(() => {
  clearPolicyCache();
});

const PROPOSAL_ID = 'prop-001';
const MISSION_ID = 'miss-001';

// T1: createProposal accepted (auto-approve)
describe('T1: createProposal_accepted', () => {
  it('should auto-approve when all steps are auto-approvable', async () => {
    // Daily count OK
    prismaMock.opsProposal.count.mockResolvedValue(0);

    // Cap gate: draft_content and verify_content pass through (no gate fn)

    // Create proposal
    prismaMock.opsProposal.create.mockResolvedValue({ id: PROPOSAL_ID });

    // emitEvent mocks (proposal:created, proposal:auto_approved)
    prismaMock.opsEvent.create.mockResolvedValue({ id: 'evt-1', tags: [] });

    // getPolicy: auto_approve
    prismaMock.opsPolicy.findUnique.mockResolvedValue({
      key: 'auto_approve',
      value: { enabled: true, allowed_step_kinds: ['draft_content', 'verify_content'] }
    });

    // Create mission
    prismaMock.opsMission.create.mockResolvedValue({
      id: MISSION_ID,
      steps: [
        { id: 's1', stepKind: 'draft_content', stepOrder: 0 },
        { id: 's2', stepKind: 'verify_content', stepOrder: 1 }
      ]
    });

    // Update proposal status
    prismaMock.opsProposal.update.mockResolvedValue({});

    const result = await createProposalAndMaybeAutoApprove({
      skillName: 'x-poster',
      source: 'manual',
      title: 'Test proposal',
      payload: {},
      steps: [
        { kind: 'draft_content', order: 0 },
        { kind: 'verify_content', order: 1 }
      ]
    });

    expect(result.status).toBe('accepted');
    expect(result.proposalId).toBe(PROPOSAL_ID);
    expect(result.missionId).toBe(MISSION_ID);
  });
});

// T2: createProposal rejected by cap gate
describe('T2: createProposal_rejected_capGate', () => {
  it('should reject when cap gate fails', async () => {
    prismaMock.opsProposal.count.mockResolvedValue(0);

    // Cap gate: x_autopost enabled + quota reached
    prismaMock.opsPolicy.findUnique
      .mockResolvedValueOnce({ key: 'x_autopost', value: { enabled: true } })
      .mockResolvedValueOnce({ key: 'x_daily_quota', value: { limit: 3 } });
    prismaMock.opsEvent.count.mockResolvedValue(3);

    // Create rejected proposal
    prismaMock.opsProposal.create.mockResolvedValue({ id: PROPOSAL_ID });
    prismaMock.opsEvent.create.mockResolvedValue({ id: 'evt-1', tags: [] });

    const result = await createProposalAndMaybeAutoApprove({
      skillName: 'x-poster',
      source: 'manual',
      title: 'Post tweet',
      payload: {},
      steps: [{ kind: 'post_x', order: 0 }]
    });

    expect(result.status).toBe('rejected');
    expect(result.rejectReason).toContain('X daily quota');
  });
});

// T3: createProposal pending (no auto-approve for post_x)
describe('T3: createProposal_pending_noAutoApprove', () => {
  it('should stay pending when steps contain Kill Switch items', async () => {
    prismaMock.opsProposal.count.mockResolvedValue(0);

    // Cap gate: x_autopost enabled + quota NOT reached
    prismaMock.opsPolicy.findUnique
      .mockResolvedValueOnce({ key: 'x_autopost', value: { enabled: true } })
      .mockResolvedValueOnce({ key: 'x_daily_quota', value: { limit: 3 } });
    prismaMock.opsEvent.count.mockResolvedValue(0);

    // Create proposal
    prismaMock.opsProposal.create.mockResolvedValue({ id: PROPOSAL_ID });
    prismaMock.opsEvent.create.mockResolvedValue({ id: 'evt-1', tags: [] });

    // auto_approve policy: post_x is NOT in allowed_step_kinds
    prismaMock.opsPolicy.findUnique.mockResolvedValue({
      key: 'auto_approve',
      value: { enabled: true, allowed_step_kinds: ['draft_content', 'verify_content'] }
    });

    const result = await createProposalAndMaybeAutoApprove({
      skillName: 'x-poster',
      source: 'manual',
      title: 'Post tweet',
      payload: {},
      steps: [
        { kind: 'draft_content', order: 0 },
        { kind: 'verify_content', order: 1 },
        { kind: 'post_x', order: 2 }
      ]
    });

    expect(result.status).toBe('pending');
    expect(result.missionId).toBeUndefined();
  });
});

// T3b: Kill Switch regression — policy explicitly allows post_x but still pending
describe('T3b: killSwitch_overridesPolicy', () => {
  it('should stay pending even when policy allows Kill Switch step kinds', async () => {
    prismaMock.opsProposal.count.mockResolvedValue(0);

    // Cap gate passes (no gate for draft_content)

    // Create proposal
    prismaMock.opsProposal.create.mockResolvedValue({ id: PROPOSAL_ID });
    prismaMock.opsEvent.create.mockResolvedValue({ id: 'evt-1', tags: [] });

    // auto_approve policy: explicitly includes post_x in allowed_step_kinds
    prismaMock.opsPolicy.findUnique.mockResolvedValue({
      key: 'auto_approve',
      value: { enabled: true, allowed_step_kinds: ['draft_content', 'verify_content', 'post_x', 'post_tiktok', 'send_nudge'] }
    });

    const result = await createProposalAndMaybeAutoApprove({
      skillName: 'x-poster',
      source: 'manual',
      title: 'Post tweet (kill switch test)',
      payload: {},
      steps: [
        { kind: 'draft_content', order: 0 },
        { kind: 'post_x', order: 1 }
      ]
    });

    // Kill Switch MUST override policy — post_x never auto-approves
    expect(result.status).toBe('pending');
    expect(result.missionId).toBeUndefined();
  });
});

// T4: createProposal daily limit
describe('T4: createProposal_dailyLimit', () => {
  it('should reject when daily proposal limit is reached', async () => {
    prismaMock.opsProposal.count.mockResolvedValue(100);

    const result = await createProposalAndMaybeAutoApprove({
      skillName: 'x-poster',
      source: 'cron',
      title: 'Daily post',
      payload: {},
      steps: [{ kind: 'draft_content', order: 0 }]
    });

    expect(result.status).toBe('rejected');
    expect(result.rejectReason).toBe('daily_proposal_limit');
    expect(result.proposalId).toBeNull();
  });
});
