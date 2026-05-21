import { describe, it, expect } from 'vitest';
import { evaluateTask } from '../evaluationService.js';

describe('evaluationService', () => {
  it('calculates normalized score for successful tasks', async () => {
    const result = await evaluateTask('task-1', {
      success: true,
      verificationScore: 4,
      latencyMs: 123,
    });

    expect(result.taskId).toBe('task-1');
    expect(result.score).toBe(0.8);
    expect(result.metrics.success).toBe(true);
    expect(result.metrics.verificationScore).toBe(4);
    expect(result.metrics.latencyMs).toBe(123);
  });

  it('returns score 0 for failed tasks', async () => {
    const result = await evaluateTask('task-2', {
      success: false,
      verificationScore: 5,
    });

    expect(result.score).toBe(0);
    expect(result.metrics.success).toBe(false);
  });
});
