import { describe, it, expect, vi, beforeEach } from 'vitest';
import { prismaMock } from '../../../../test/setup.js';

// Mock callLLM
const mockCallLLM = vi.fn();
vi.mock('../../../../lib/llm.js', () => ({
  callLLM: mockCallLLM
}));

beforeEach(() => {
  mockCallLLM.mockReset();
});

describe('executeDiagnose', () => {
  // T49: test_executeDiagnose_extractsFailedSteps
  it('T49: extracts failed steps and generates diagnosis', async () => {
    prismaMock.opsEvent.findUnique.mockResolvedValue({
      id: 'evt-1',
      source: 'x-poster',
      payload: { missionId: 'mission-1' }
    });

    prismaMock.opsMission.findUnique.mockResolvedValue({
      id: 'mission-1',
      proposal: { title: 'X投稿 morning' },
      steps: [
        { stepKind: 'draft_content', status: 'succeeded', lastError: null },
        { stepKind: 'verify_content', status: 'failed', lastError: 'Score too low' }
      ]
    });

    mockCallLLM.mockResolvedValue('Root cause: verification threshold too strict. Recommendation: adjust scoring.');

    const { executeDiagnose } = await import('../executeDiagnose.js');
    const result = await executeDiagnose({
      input: { eventId: 'evt-1' },
      proposalPayload: {}
    });

    expect(result.output.diagnosis).not.toBeNull();
    expect(result.output.failedStepKinds).toContain('verify_content');
    expect(result.output.failedStepKinds).toHaveLength(1);
    expect(result.events[0].kind).toBe('diagnosis:completed');
  });
});
