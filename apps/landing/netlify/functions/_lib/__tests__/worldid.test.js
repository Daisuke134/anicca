const { test } = require('node:test');
const assert = require('node:assert/strict');
const { verifyProof, verifyAndClaim } = require('../worldid.js');

const PROOF = { proof: 'p', merkle_root: 'm', nullifier_hash: '0xN', verification_level: 'device' };
const okVerify = async () => ({ success: true });
const args = (over = {}) => ({ proof: PROOF, signal: 'a@x.com', appId: 'app_1', action: 'claim-ubi', verify: okVerify, ...over });

test('verifyProof: missing proof/signal/appId/nullifier -> fail-closed', async () => {
  assert.equal((await verifyProof({ ...args(), proof: null })).reason, 'proof_required');
  assert.equal((await verifyProof({ ...args(), signal: '' })).reason, 'signal_required');
  assert.equal((await verifyProof({ ...args(), appId: '' })).reason, 'missing_worldcoin_app_id');
  assert.equal((await verifyProof({ ...args(), proof: { ...PROOF, nullifier_hash: undefined } })).reason, 'no_nullifier');
});

test('verifyProof: verify throws -> verify_error (never ok)', async () => {
  const r = await verifyProof({ ...args(), verify: async () => { throw new Error('net'); } });
  assert.equal(r.ok, false); assert.equal(r.reason, 'verify_error');
});

test('verifyProof: success!==true -> verification_failed, surfaces code', async () => {
  assert.equal((await verifyProof({ ...args(), verify: async () => ({ success: false, code: 'invalid_proof' }) })).reason, 'invalid_proof');
  assert.equal((await verifyProof({ ...args(), verify: async () => null })).reason, 'verification_failed');
});

test('verifyProof: valid -> ok + nullifier_hash', async () => {
  const r = await verifyProof(args());
  assert.deepEqual(r, { ok: true, nullifier_hash: '0xN' });
});

test('verifyAndClaim: fresh nullifier insert (2xx) -> ok', async () => {
  const r = await verifyAndClaim({ ...args(), insert: async () => 201 });
  assert.deepEqual(r, { ok: true, nullifier_hash: '0xN' });
});

test('verifyAndClaim: 409 unique-violation -> already_claimed (atomic sybil block)', async () => {
  const r = await verifyAndClaim({ ...args(), insert: async () => 409 });
  assert.equal(r.ok, false); assert.equal(r.reason, 'already_claimed'); assert.equal(r.status, 409);
});

test('verifyAndClaim: insert write failure (500) -> deny, never allow (fail-closed)', async () => {
  assert.equal((await verifyAndClaim({ ...args(), insert: async () => 500 })).reason, 'dedup_store_error');
  assert.equal((await verifyAndClaim({ ...args(), insert: async () => { throw new Error('db'); } })).reason, 'dedup_store_error');
});

test('verifyAndClaim: does NOT claim if verify fails (no insert call)', async () => {
  let inserted = false;
  const r = await verifyAndClaim({ ...args(), verify: async () => ({ success: false, code: 'bad' }), insert: async () => { inserted = true; return 201; } });
  assert.equal(r.ok, false);
  assert.equal(inserted, false); // verify gate precedes the claim
});

test('verifyAndClaim: missing insert fn -> no_store (never silently allow)', async () => {
  assert.equal((await verifyAndClaim({ ...args(), insert: undefined })).reason, 'no_store');
});
