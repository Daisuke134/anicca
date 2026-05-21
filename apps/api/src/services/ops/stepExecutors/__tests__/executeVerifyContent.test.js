import { describe, it, expect, vi, beforeEach } from 'vitest';

// Mock verifier
const mockVerifyWithRegeneration = vi.fn();
vi.mock('../../../verifier.js', () => ({
  verifyWithRegeneration: mockVerifyWithRegeneration
}));

// Mock callLLM
vi.mock('../../../../lib/llm.js', () => ({
  callLLM: vi.fn()
}));

beforeEach(() => {
  mockVerifyWithRegeneration.mockReset();
});

describe('executeVerifyContent', () => {
  // T35: test_executeVerifyContent_passes
  it('T35: returns passed=true when verification score meets threshold', async () => {
    mockVerifyWithRegeneration.mockResolvedValue({
      content: 'verified content',
      score: 4,
      passed: true,
      attempts: 1,
      feedback: ['Good content']
    });

    const { executeVerifyContent } = await import('../executeVerifyContent.js');
    const result = await executeVerifyContent({
      input: { content: 'test content', hookId: 'hook-1', platform: 'x' }
    });

    expect(result.output.passed).toBe(true);
    expect(result.output.verificationScore).toBe(4);
    expect(result.output.content).toBe('verified content');
  });

  // T36: test_executeVerifyContent_failsAfterRetries
  it('T36: throws when verification fails after max retries', async () => {
    mockVerifyWithRegeneration.mockResolvedValue({
      content: 'bad content',
      score: 1,
      passed: false,
      attempts: 4,
      feedback: ['Bad', 'Still bad', 'Really bad', 'Terrible']
    });

    const { executeVerifyContent } = await import('../executeVerifyContent.js');

    await expect(executeVerifyContent({
      input: { content: 'bad content', hookId: 'hook-1', platform: 'x' }
    })).rejects.toThrow(/Content verification failed/);
  });

  it('throws when input.content is missing', async () => {
    const { executeVerifyContent } = await import('../executeVerifyContent.js');

    await expect(executeVerifyContent({
      input: {}
    })).rejects.toThrow('verify_content requires input.content');
  });
});
