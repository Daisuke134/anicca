import { describe, it, expect, vi, beforeEach } from 'vitest';
import { prismaMock } from '../../../test/setup.js';
import { checkCapGate } from '../capGates.js';
import { clearPolicyCache } from '../policyService.js';

beforeEach(() => {
  clearPolicyCache();
});

// T5: postXGate quota reached
describe('T5: postXGate_quotaReached', () => {
  it('should reject when X daily quota is reached', async () => {
    // Policy mocks
    prismaMock.opsPolicy.findUnique
      .mockResolvedValueOnce({ key: 'x_autopost', value: { enabled: true } })
      .mockResolvedValueOnce({ key: 'x_daily_quota', value: { limit: 3 } });

    prismaMock.opsEvent.count.mockResolvedValue(3);

    const result = await checkCapGate('post_x');
    expect(result.ok).toBe(false);
    expect(result.reason).toContain('X daily quota reached');
  });
});

// T6: postXGate disabled
describe('T6: postXGate_disabled', () => {
  it('should reject when x_autopost is disabled', async () => {
    prismaMock.opsPolicy.findUnique.mockResolvedValue({
      key: 'x_autopost', value: { enabled: false }
    });

    const result = await checkCapGate('post_x');
    expect(result.ok).toBe(false);
    expect(result.reason).toBe('x_autopost disabled');
  });
});

// T7: sendNudgeGate quota reached
describe('T7: sendNudgeGate_quotaReached', () => {
  it('should reject when nudge daily quota is reached', async () => {
    prismaMock.opsPolicy.findUnique.mockResolvedValue({
      key: 'nudge_daily_quota', value: { limit: 10 }
    });
    prismaMock.opsEvent.count.mockResolvedValue(10);

    const result = await checkCapGate('send_nudge');
    expect(result.ok).toBe(false);
    expect(result.reason).toContain('Nudge daily quota reached');
  });
});

// Passthrough for unknown step kinds
describe('checkCapGate passthrough', () => {
  it('should pass for unknown step kinds', async () => {
    const result = await checkCapGate('draft_content');
    expect(result.ok).toBe(true);
  });
});
