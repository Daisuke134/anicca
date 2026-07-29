import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';

describe('Railway runtime contract', () => {
  it('requires the minimum Node version supported by x402 dependencies', () => {
    const packageJson = JSON.parse(
      readFileSync(new URL('../../package.json', import.meta.url), 'utf8'),
    );

    expect(packageJson.engines?.node).toBe('>=20.18.0');
  });
});
