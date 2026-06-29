import { describe, it, expect } from 'vitest';
import { buildVerifyBody, isAcceptedLevel, mapVerifyResult, isDuplicateNullifier, verifyPersonhood } from '../worldid.js';

const PROOF = { nullifier_hash: '0xnull1', merkle_root: '0xroot', proof: '0xproof', verification_level: 'device' };
const okFetch = async () => ({ ok: true, json: async () => ({ success: true }) });
function memStore() { const s = new Set(); return { has: async (h) => s.has(h), add: async (h) => s.add(h) }; }

describe('worldid pure helpers', () => {
  it('buildVerifyBody defaults to device level + maps signal->signal_hash', () => {
    const b = buildVerifyBody({ ...PROOF, action: 'claim-ubi' });
    expect(b.verification_level).toBe('device');
    expect(b.nullifier_hash).toBe('0xnull1');
    expect(b.signal_hash).toBe('');
  });
  it('buildVerifyBody throws when any proof field is missing', () => {
    expect(() => buildVerifyBody({ nullifier_hash: '0x', merkle_root: '0x' })).toThrow(/required/);
  });
  it('isAcceptedLevel: device + orb yes, anything else no', () => {
    expect(isAcceptedLevel('device')).toBe(true);
    expect(isAcceptedLevel('orb')).toBe(true);
    expect(isAcceptedLevel('lite')).toBe(false);
    expect(isAcceptedLevel(undefined)).toBe(false);
  });
  it('mapVerifyResult: only explicit success===true is ok', () => {
    expect(mapVerifyResult({ success: true }).ok).toBe(true);
    expect(mapVerifyResult({ success: false, code: 'invalid_proof' })).toEqual({ ok: false, reason: 'invalid_proof' });
    expect(mapVerifyResult(undefined).ok).toBe(false);
  });
  it('isDuplicateNullifier: true only when the set already has the hash', () => {
    const s = new Set(['0xa']);
    expect(isDuplicateNullifier(s, '0xa')).toBe(true);
    expect(isDuplicateNullifier(s, '0xb')).toBe(false);
  });
});

const SIG = '0xRecipientAddress';
describe('verifyPersonhood (live path, injected fetch + store)', () => {
  it('valid proof, fresh nullifier -> allowed + records the nullifier', async () => {
    const store = memStore();
    const r = await verifyPersonhood({ proofBundle: PROOF, signal: SIG, appId: 'app_1', store, fetchImpl: okFetch });
    expect(r).toEqual({ allowed: true, nullifier_hash: '0xnull1' });
    expect(await store.has('0xnull1')).toBe(true);
  });
  it('SYBIL: same nullifier a second time -> already_claimed, NOT allowed', async () => {
    const store = memStore();
    await verifyPersonhood({ proofBundle: PROOF, signal: SIG, appId: 'app_1', store, fetchImpl: okFetch });
    const r2 = await verifyPersonhood({ proofBundle: PROOF, signal: SIG, appId: 'app_1', store, fetchImpl: okFetch });
    expect(r2.allowed).toBe(false);
    expect(r2.reason).toBe('already_claimed');
  });
  it('level below device -> rejected before any network call', async () => {
    let called = false;
    const r = await verifyPersonhood({ proofBundle: { ...PROOF, verification_level: 'lite' }, signal: SIG, appId: 'app_1', store: memStore(), fetchImpl: async () => { called = true; return okFetch(); } });
    expect(r).toEqual({ allowed: false, reason: 'level_too_low' });
    expect(called).toBe(false);
  });
  it('Worldcoin rejects the proof -> not allowed, reason surfaced', async () => {
    const badFetch = async () => ({ ok: true, json: async () => ({ success: false, code: 'invalid_merkle_root' }) });
    const r = await verifyPersonhood({ proofBundle: PROOF, signal: SIG, appId: 'app_1', store: memStore(), fetchImpl: badFetch });
    expect(r.allowed).toBe(false);
    expect(r.reason).toBe('invalid_merkle_root');
  });
  it('non-2xx from Worldcoin -> not allowed (no false-allow)', async () => {
    const errFetch = async () => ({ ok: false, status: 400, json: async () => ({ code: 'bad_request' }) });
    const r = await verifyPersonhood({ proofBundle: PROOF, signal: SIG, appId: 'app_1', store: memStore(), fetchImpl: errFetch });
    expect(r.allowed).toBe(false);
  });
  it('missing appId -> throws (misconfig, not a silent allow)', async () => {
    await expect(verifyPersonhood({ proofBundle: PROOF, signal: SIG, appId: undefined, store: memStore(), fetchImpl: okFetch })).rejects.toThrow(/WORLDCOIN_APP_ID/);
  });
  it('missing store -> throws (NO fail-open) (security #2)', async () => {
    await expect(verifyPersonhood({ proofBundle: PROOF, signal: SIG, appId: 'app_1', store: undefined, fetchImpl: okFetch })).rejects.toThrow(/dedup store required/);
  });
  it('missing signal -> throws (proof must bind to recipient) (security #3)', async () => {
    await expect(verifyPersonhood({ proofBundle: PROOF, signal: '', appId: 'app_1', store: memStore(), fetchImpl: okFetch })).rejects.toThrow(/signal required/);
  });
  it('store.add throws (unique-violation / concurrent race) -> already_claimed, NOT allowed (FIND-001/002)', async () => {
    const racingStore = { has: async () => false, add: async () => { throw new Error('duplicate key value violates unique constraint'); } };
    const r = await verifyPersonhood({ proofBundle: PROOF, signal: SIG, appId: 'app_1', store: racingStore, fetchImpl: okFetch });
    expect(r.allowed).toBe(false);
    expect(r.reason).toBe('already_claimed');
  });
  it('malformed JSON from Worldcoin -> deny (no false-allow) (FIND-004)', async () => {
    const badJson = async () => ({ ok: true, json: async () => { throw new Error('not json'); } });
    const r = await verifyPersonhood({ proofBundle: PROOF, signal: SIG, appId: 'app_1', store: memStore(), fetchImpl: badJson });
    expect(r.allowed).toBe(false);
  });
});
