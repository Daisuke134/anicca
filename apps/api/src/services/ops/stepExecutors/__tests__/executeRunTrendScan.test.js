import { describe, it, expect } from 'vitest';

describe('executeRunTrendScan', () => {
  // T61: test_executeRunTrendScan_interfaceShape
  it('T61: returns correct interface shape with savedCount and sources', async () => {
    const { executeRunTrendScan } = await import('../executeRunTrendScan.js');
    const result = await executeRunTrendScan({
      input: {},
      proposalPayload: {}
    });

    expect(typeof result.output.savedCount).toBe('number');
    expect(Array.isArray(result.output.sources)).toBe(true);
    expect(Array.isArray(result.output.errors)).toBe(true);
  });
});
