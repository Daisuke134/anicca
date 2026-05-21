import { describe, it, expect, vi, beforeEach } from 'vitest';
import { prismaMock } from '../../../test/setup.js';
import { getPolicy, setPolicy, clearPolicyCache } from '../policyService.js';

beforeEach(() => {
  clearPolicyCache();
});

// T8: getPolicy cached
describe('T8: getPolicy_cached', () => {
  it('should query DB only once for repeated calls', async () => {
    prismaMock.opsPolicy.findUnique.mockResolvedValue({
      key: 'auto_approve',
      value: { enabled: true, allowed_step_kinds: ['draft_content'] }
    });

    const first = await getPolicy('auto_approve');
    const second = await getPolicy('auto_approve');

    expect(first).toEqual({ enabled: true, allowed_step_kinds: ['draft_content'] });
    expect(second).toEqual(first);
    expect(prismaMock.opsPolicy.findUnique).toHaveBeenCalledTimes(1);
  });
});

// T9: setPolicy invalidates cache
describe('T9: setPolicy_invalidatesCache', () => {
  it('should return new value after setPolicy', async () => {
    prismaMock.opsPolicy.findUnique
      .mockResolvedValueOnce({ key: 'x_daily_quota', value: { limit: 3 } })
      .mockResolvedValueOnce({ key: 'x_daily_quota', value: { limit: 5 } });
    prismaMock.opsPolicy.upsert.mockResolvedValue({});

    const first = await getPolicy('x_daily_quota');
    expect(first).toEqual({ limit: 3 });

    await setPolicy('x_daily_quota', { limit: 5 });

    const third = await getPolicy('x_daily_quota');
    expect(third).toEqual({ limit: 5 });
    expect(prismaMock.opsPolicy.findUnique).toHaveBeenCalledTimes(2);
  });
});
