// worldid.js — World ID personhood gate for UBI claims (sybil resistance).
//
// A UBI recipient must prove they are a UNIQUE human before a claim is enqueued. World ID returns a
// per-app, per-action anonymous `nullifier_hash`; we verify the proof with Worldcoin and refuse any
// second claim carrying a nullifier we've already seen (one human -> at most one active recipient).
// No Orb required: `device` level (World App on a phone) is accepted; `orb` is a stronger optional tier.
// Privacy: we persist only the opaque nullifier_hash + payout destination, never identity.
// Spec: docs/superpowers/specs/anicca/2026-06-21-personhood-gate-worldid-superfluid-gda.md (#36).

const APP_ID = process.env.WORLDCOIN_APP_ID;            // app_xxxxxxxx (from developer.worldcoin.org)
const ACTION = process.env.WORLDCOIN_ACTION || 'claim-ubi';
const VERIFY_BASE = 'https://developer.worldcoin.org/api/v2/verify';

// Pure: shape the body for Worldcoin's /verify endpoint. Defaults to 'device' level.
export function buildVerifyBody({ nullifier_hash, merkle_root, proof, verification_level, action, signal }) {
  if (!nullifier_hash || !merkle_root || !proof) {
    throw new Error('worldid: nullifier_hash, merkle_root, proof are all required');
  }
  return {
    nullifier_hash,
    merkle_root,
    proof,
    verification_level: verification_level || 'device',
    action,
    signal_hash: signal ?? '',
  };
}

// Pure: accept device OR orb (we never require Orb); reject anything weaker/unknown.
export function isAcceptedLevel(level) {
  return level === 'device' || level === 'orb';
}

// Pure: map Worldcoin v2 verify response -> {ok} | {ok:false, reason}. Only an explicit success counts.
export function mapVerifyResult(res) {
  if (res && res.success === true) return { ok: true };
  const reason = (res && (res.code || res.detail || res.error)) || 'verification_failed';
  return { ok: false, reason };
}

// Pure: sybil check — a nullifier already recorded for this action is a duplicate (refuse).
export function isDuplicateNullifier(seen, hash) {
  return !!(seen && hash && (typeof seen.has === 'function' ? seen.has(hash) : false));
}

// Live: verify a proof, then dedup the nullifier via an injected async store {has(hash), add(hash)}.
// Returns { allowed, nullifier_hash?, reason? }. Never throws on a normal deny — only on misconfig.
export async function verifyPersonhood({ proofBundle, appId = APP_ID, action = ACTION, store, fetchImpl = fetch }) {
  if (!appId) throw new Error('worldid: WORLDCOIN_APP_ID required (set env)');
  if (!isAcceptedLevel(proofBundle?.verification_level)) {
    return { allowed: false, reason: 'level_too_low' };
  }
  const body = buildVerifyBody({ ...proofBundle, action });
  const res = await fetchImpl(`${VERIFY_BASE}/${appId}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) return { allowed: false, reason: mapVerifyResult(data).reason || `verify_${res.status}` };
  const mapped = mapVerifyResult(data);
  if (!mapped.ok) return { allowed: false, reason: mapped.reason };

  // proof is valid — enforce one-human-one-recipient on the nullifier (sybil gate).
  const hash = body.nullifier_hash;
  if (store) {
    if (await store.has(hash)) return { allowed: false, reason: 'already_claimed', nullifier_hash: hash };
    await store.add(hash);
  }
  return { allowed: true, nullifier_hash: hash };
}
