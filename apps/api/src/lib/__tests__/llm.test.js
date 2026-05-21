import { describe, it, expect, vi, beforeEach } from 'vitest';

// Mock OpenAI
const mockCreate = vi.fn();
vi.mock('openai', () => ({
  default: vi.fn().mockImplementation(() => ({
    chat: {
      completions: {
        create: mockCreate
      }
    }
  }))
}));

beforeEach(() => {
  mockCreate.mockReset();
});

describe('callLLM', () => {
  // T54: test_callLLM_returnsString
  it('T54: returns string from OpenAI response', async () => {
    mockCreate.mockResolvedValue({
      choices: [{ message: { content: 'hello' } }]
    });

    const { callLLM } = await import('../llm.js');
    const result = await callLLM('test prompt');

    expect(result).toBe('hello');
    expect(mockCreate).toHaveBeenCalledWith(
      expect.objectContaining({
        model: 'gpt-4o-mini',
        messages: [{ role: 'user', content: 'test prompt' }]
      })
    );
  });

  // T55: test_callLLM_throwsOnFailure
  it('T55: throws on API failure', async () => {
    mockCreate.mockRejectedValue(new Error('API rate limit'));

    const { callLLM } = await import('../llm.js');

    await expect(callLLM('test')).rejects.toThrow('LLM call failed: API rate limit');
  });
});
