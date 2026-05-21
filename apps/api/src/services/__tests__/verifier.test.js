import { describe, it, expect, vi, beforeEach } from 'vitest';

// Mock callLLM
const mockCallLLM = vi.fn();
vi.mock('../../lib/llm.js', () => ({
  callLLM: mockCallLLM
}));

beforeEach(() => {
  mockCallLLM.mockReset();
});

describe('verifier', () => {
  // T56: test_verifyWithRegeneration_passesOnFirstTry
  it('T56: passes on first try when score >= threshold', async () => {
    // Scorer returns score=4 on first attempt
    mockCallLLM.mockResolvedValue(JSON.stringify({ score: 4, feedback: 'Good content' }));

    const { verifyWithRegeneration } = await import('../verifier.js');
    const result = await verifyWithRegeneration(
      async () => 'test content',
      { threshold: 3, maxRetries: 3, skillName: 'test', context: {} }
    );

    expect(result.passed).toBe(true);
    expect(result.score).toBe(4);
    expect(result.attempts).toBe(1);
  });

  // T57: test_verifyWithRegeneration_regeneratesOnFailure
  it('T57: regenerates content when score is below threshold', async () => {
    // First call: score=2 (fail), second call: score=4 (pass)
    mockCallLLM
      .mockResolvedValueOnce(JSON.stringify({ score: 2, feedback: 'Needs improvement' }))
      .mockResolvedValueOnce(JSON.stringify({ score: 4, feedback: 'Good now' }));

    let callCount = 0;
    const generatorFn = vi.fn(async (feedback) => {
      callCount++;
      return callCount === 1 ? 'initial content' : 'improved content';
    });

    const { verifyWithRegeneration } = await import('../verifier.js');
    const result = await verifyWithRegeneration(
      generatorFn,
      { threshold: 3, maxRetries: 3, skillName: 'test', context: {} }
    );

    expect(result.passed).toBe(true);
    expect(result.attempts).toBe(2);
    expect(generatorFn).toHaveBeenCalledTimes(2);
  });

  // T58: test_verifyWithRegeneration_failsAfterMaxRetries
  it('T58: fails after max retries when score stays below threshold', async () => {
    // All attempts return score=1
    mockCallLLM.mockResolvedValue(JSON.stringify({ score: 1, feedback: 'Still bad' }));

    const { verifyWithRegeneration } = await import('../verifier.js');
    const result = await verifyWithRegeneration(
      async () => 'bad content',
      { threshold: 3, maxRetries: 3, skillName: 'test', context: {} }
    );

    expect(result.passed).toBe(false);
    // Verify lastScore is preserved (not 0)
    expect(result.score).toBe(1);
  });

  // T59: test_scoreContent_crisisDetection (SAFE-T)
  it('T59: detects crisis patterns and returns score=0', async () => {
    // The scorer should not even be called; crisis pattern is detected first
    const { verifyWithRegeneration } = await import('../verifier.js');
    const result = await verifyWithRegeneration(
      async () => '死にたいと思う',
      { threshold: 3, maxRetries: 0, skillName: 'test', context: {} }
    );

    expect(result.score).toBe(0);
    expect(result.passed).toBe(false);
  });
});
