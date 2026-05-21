import { describe, it, expect, vi, beforeEach } from 'vitest';

// Mock callLLM
const mockCallLLM = vi.fn();
vi.mock('../../../../lib/llm.js', () => ({
  callLLM: mockCallLLM
}));

beforeEach(() => {
  mockCallLLM.mockReset();
});

describe('executeDraftNudge', () => {
  // T51: test_executeDraftNudge_topSeveritySelection
  it('T51: selects detection with highest severity and generates nudge', async () => {
    mockCallLLM.mockResolvedValue('大丈夫。まず深呼吸から。');

    const { executeDraftNudge } = await import('../executeDraftNudge.js');
    const result = await executeDraftNudge({
      input: {
        detections: [
          { text: 'mild issue', severity: 0.6, problemType: 'anxiety' },
          { text: 'severe issue', severity: 0.8, problemType: 'self_loathing' }
        ]
      }
    });

    expect(result.output.nudgeContent).not.toBeNull();
    expect(result.output.severity).toBe(0.8);
    expect(result.output.targetProblemType).toBe('self_loathing');
  });

  it('skips when no detections provided', async () => {
    const { executeDraftNudge } = await import('../executeDraftNudge.js');
    const result = await executeDraftNudge({
      input: { detections: [] }
    });

    expect(result.output.skipped).toBe(true);
    expect(result.output.nudgeContent).toBeNull();
  });
});
