import { describe, it, expect } from 'vitest';
import { makeNullifierStore } from '../nullifierStore.js';
import { verifyPersonhood } from '../worldid.js';

function mockPrisma() {
  const rows = [];
  return {
    personhood_nullifier: {
      findUnique: async ({ where }) => {
        const k = where.nullifierHash_action;
        return rows.find((r) => r.nullifierHash === k.nullifierHash && r.action === k.action) || null;
      },
      create: async ({ data }) => {
        if (rows.find((r) => r.nullifierHash === data.nullifierHash && r.action === data.action)) {
          const e = new Error('Unique constraint failed'); e.code = 'P2002'; throw e;
        }
        rows.push(data); return data;
      },
    },
  };
}
const PROOF = { nullifier_hash: '0xN', merkle_root: '0xr', proof: '0xp', verification_level: 'device' };
const okFetch = async () => ({ ok: true, json: async () => ({ success: true }) });

describe('nullifierStore (Prisma unique-constraint dedup)', () => {
  it('requires an action', () => {
    expect(() => makeNullifierStore({})).toThrow(/action required/);
  });
  it('has(): false, then true after add()', async () => {
    const st = makeNullifierStore({ action: 'a', prisma: mockPrisma() });
    expect(await st.has('0xN')).toBe(false);
    await st.add('0xN');
    expect(await st.has('0xN')).toBe(true);
  });
  it('add() twice throws P2002 (the atomic guard — not swallowed here)', async () => {
    const st = makeNullifierStore({ action: 'a', prisma: mockPrisma() });
    await st.add('0xN');
    await expect(st.add('0xN')).rejects.toThrow(/Unique constraint/);
  });
  it('INTEGRATION: verifyPersonhood + store -> 1st allowed, 2nd already_claimed (sybil closed)', async () => {
    const prisma = mockPrisma();
    const mk = () => makeNullifierStore({ action: 'claim-ubi', signal: '0xRecip', prisma });
    const r1 = await verifyPersonhood({ proofBundle: PROOF, signal: '0xRecip', appId: 'app_1', store: mk(), fetchImpl: okFetch });
    expect(r1.allowed).toBe(true);
    const r2 = await verifyPersonhood({ proofBundle: PROOF, signal: '0xRecip', appId: 'app_1', store: mk(), fetchImpl: okFetch });
    expect(r2.allowed).toBe(false);
    expect(r2.reason).toBe('already_claimed');
  });
});
