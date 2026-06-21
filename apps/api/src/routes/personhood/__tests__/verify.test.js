import { describe, it, expect } from 'vitest';
import { makeVerifyHandler } from '../index.js';

function mkRes() {
  return { code: 200, body: null, status(c) { this.code = c; return this; }, json(o) { this.body = o; return this; } };
}
const BODY = { proof: 'p', merkle_root: 'm', nullifier_hash: '0xN', verification_level: 'device', recipient: '0xR' };
const makeStore = () => ({});

describe('POST /personhood/verify handler (VCSDD FIND-002)', () => {
  it('400 when recipient missing', async () => {
    const res = mkRes();
    await makeVerifyHandler({ verify: async () => ({ allowed: true }), makeStore })({ body: { ...BODY, recipient: undefined } }, res);
    expect(res.code).toBe(400);
    expect(res.body.reason).toBe('recipient_required');
  });
  it('200 ok when allowed', async () => {
    const res = mkRes();
    await makeVerifyHandler({ verify: async () => ({ allowed: true, nullifier_hash: '0xN' }), makeStore })({ body: BODY }, res);
    expect(res.code).toBe(200);
    expect(res.body).toEqual({ ok: true, nullifier_hash: '0xN' });
  });
  it('409 already_claimed (sybil refusal)', async () => {
    const res = mkRes();
    await makeVerifyHandler({ verify: async () => ({ allowed: false, reason: 'already_claimed' }), makeStore })({ body: BODY }, res);
    expect(res.code).toBe(409);
  });
  it('403 level_too_low', async () => {
    const res = mkRes();
    await makeVerifyHandler({ verify: async () => ({ allowed: false, reason: 'level_too_low' }), makeStore })({ body: BODY }, res);
    expect(res.code).toBe(403);
  });
  it('422 on other deny reasons', async () => {
    const res = mkRes();
    await makeVerifyHandler({ verify: async () => ({ allowed: false, reason: 'invalid_merkle_root' }), makeStore })({ body: BODY }, res);
    expect(res.code).toBe(422);
  });
  it('500 fail-closed on throw — never allows', async () => {
    const res = mkRes();
    await makeVerifyHandler({ verify: async () => { throw new Error('WORLDCOIN_APP_ID required'); }, makeStore })({ body: BODY }, res);
    expect(res.code).toBe(500);
    expect(res.body.ok).toBe(false);
  });
  it('binds signal to recipient + builds store with action+signal', async () => {
    let captured = null;
    const res = mkRes();
    await makeVerifyHandler({
      verify: async (a) => { captured = a; return { allowed: true, nullifier_hash: '0xN' }; },
      makeStore: ({ action, signal }) => ({ action, signal }),
    })({ body: BODY }, res);
    expect(captured.signal).toBe('0xR');
    expect(captured.store.signal).toBe('0xR');
  });
});
