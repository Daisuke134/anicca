const { test } = require('node:test');
const assert = require('node:assert/strict');
const { verifyV4, verifyAndClaimV4, extractNullifier, responseSignalHash } = require('../worldid4.js');

const resp = (over = {}) => ({ protocol_version: '4.0', action: 'claim-ubi', responses: [{ identifier: 'orb', signal_hash: '0xABC', nullifier: '0xDEAD', ...over }] });
const okFetch = async () => ({ ok: true, json: async () => ({ success: true, nullifier: '0xdead' }) });
const okVerify = async () => ({ ok: true });

test('extractNullifier: valid hex lowercased; malformed -> null', () => {
  assert.equal(extractNullifier(resp()), '0xdead');
  assert.equal(extractNullifier(resp({ nullifier: 'nothex' })), null);
  assert.equal(extractNullifier({ responses: [] }), null);
  assert.equal(extractNullifier({}), null);
});

test('responseSignalHash: lowercased; missing -> null', () => {
  assert.equal(responseSignalHash(resp()), '0xabc');
  assert.equal(responseSignalHash(resp({ signal_hash: undefined })), null);
});

test('verifyV4: ok -> {ok:true}', async () => {
  assert.deepEqual(await verifyV4(resp(), 'rp_1', { fetchImpl: okFetch }), { ok: true });
});

test('verifyV4: missing rpId / invalid response -> fail (never ok)', async () => {
  assert.equal((await verifyV4(resp(), '', { fetchImpl: okFetch })).reason, 'missing_rp_id');
  assert.equal((await verifyV4({}, 'rp_1', { fetchImpl: okFetch })).reason, 'invalid_idkit_response');
});

test('verifyV4: non-ok 400 -> 403 verification_failed; network throw -> fail-closed', async () => {
  assert.equal((await verifyV4(resp(), 'rp_1', { fetchImpl: async () => ({ ok: false, status: 400 }) })).status, 403);
  assert.equal((await verifyV4(resp(), 'rp_1', { fetchImpl: async () => { throw new Error('net'); } })).reason, 'verify_network_error');
});

test('verifyV4: HTTP 200 but body success!==true -> NOT ok (FIND-003 no false-allow)', async () => {
  assert.equal((await verifyV4(resp(), 'rp_1', { fetchImpl: async () => ({ ok: true, json: async () => ({ success: false }) }) })).ok, false);
  assert.equal((await verifyV4(resp(), 'rp_1', { fetchImpl: async () => ({ ok: true, json: async () => { throw new Error('bad'); } }) })).ok, false);
});

test('verifyAndClaimV4: ok + insert 2xx -> ok + nullifier', async () => {
  const r = await verifyAndClaimV4({ idkitResponse: resp(), rpId: 'rp_1', action: 'claim-ubi', verify: okVerify, insert: async () => 201 });
  assert.deepEqual(r, { ok: true, nullifier_hash: '0xdead' });
});

test('verifyAndClaimV4: verify fails -> propagate, NO insert', async () => {
  let inserted = false;
  const r = await verifyAndClaimV4({ idkitResponse: resp(), rpId: 'rp_1', verify: async () => ({ ok: false, status: 403, reason: 'verification_failed' }), insert: async () => { inserted = true; return 201; } });
  assert.equal(r.ok, false); assert.equal(inserted, false);
});

test('verifyAndClaimV4: signal mismatch -> 403, NO insert (anti-relay)', async () => {
  let inserted = false;
  const r = await verifyAndClaimV4({ idkitResponse: resp(), rpId: 'rp_1', expectedSignalHash: '0xWRONG', verify: okVerify, insert: async () => { inserted = true; return 201; } });
  assert.equal(r.reason, 'signal_mismatch'); assert.equal(inserted, false);
});

test('verifyAndClaimV4: matching signal -> ok', async () => {
  const r = await verifyAndClaimV4({ idkitResponse: resp(), rpId: 'rp_1', expectedSignalHash: '0xabc', verify: okVerify, insert: async () => 201 });
  assert.equal(r.ok, true);
});

test('verifyAndClaimV4: 409 -> already_claimed; write fail -> dedup_store_error', async () => {
  assert.equal((await verifyAndClaimV4({ idkitResponse: resp(), rpId: 'rp_1', verify: okVerify, insert: async () => 409 })).reason, 'already_claimed');
  assert.equal((await verifyAndClaimV4({ idkitResponse: resp(), rpId: 'rp_1', verify: okVerify, insert: async () => 500 })).reason, 'dedup_store_error');
  assert.equal((await verifyAndClaimV4({ idkitResponse: resp(), rpId: 'rp_1', verify: okVerify, insert: async () => { throw new Error('x'); } })).reason, 'dedup_store_error');
});

test('verifyAndClaimV4: missing nullifier -> 403; no insert fn -> no_store', async () => {
  assert.equal((await verifyAndClaimV4({ idkitResponse: resp({ nullifier: 'bad' }), rpId: 'rp_1', verify: okVerify, insert: async () => 201 })).reason, 'no_nullifier');
  assert.equal((await verifyAndClaimV4({ idkitResponse: resp(), rpId: 'rp_1', verify: okVerify, insert: undefined })).reason, 'no_store');
});
