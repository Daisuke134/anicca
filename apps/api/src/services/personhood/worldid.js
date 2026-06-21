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

// Live: verify a proof, then dedup the nullifier via a REQUIRED async store {has(hash), add(hash)}.
// Returns { allowed, nullifier_hash?, reason? }. Never throws on a normal deny — only on misconfig.
//
// `signal` is REQUIRED and MUST be the SERVER-KNOWN per-claim binding (the payout recipient address),
// passed by the route — NEVER taken from the client proof bundle. This binds the proof to a specific
// recipient so a valid proof cannot be relayed/front-run to a different payout (security review #3).
// Production: signal_hash MUST be derived with @worldcoin/idkit-core `hashToField(signal)` to match
// the frontend IDKit; a mismatch fails the Worldcoin verify (fail-closed). See buildVerifyBody.
export async function verifyPersonhood({ proofBundle, signal, appId = APP_ID, action = ACTION, store, fetchImpl = fetch }) {
  if (!appId) throw new Error('worldid: WORLDCOIN_APP_ID required (set env)');
  if (!store) throw new Error('worldid: dedup store required (sybil gate must NOT fail open)'); // security #2
  if (signal == null || signal === '') throw new Error('worldid: signal required (server-bound recipient)'); // security #3
  if (!isAcceptedLevel(proofBundle?.verification_level)) {
    return { allowed: false, reason: 'level_too_low' };
  }
  // signal is the server-supplied binding; any client-supplied proofBundle.signal is overridden.
  const body = buildVerifyBody({ ...proofBundle, action, signal });
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
  // The DB-level UNIQUE constraint on nullifier_hash is the ATOMIC guard: the has() pre-check is
  // only a fast path; the real race-closer is add() throwing a unique-violation under concurrency
  // (TOCTOU) — which we treat as already_claimed. A non-durable / failed add must NEVER fall through
  // to allowed:true (VCSDD FIND-001/FIND-002). REQUIRED of the production store: a unique index on
  // nullifier_hash so a duplicate insert rejects.
  const hash = body.nullifier_hash;
  if (await store.has(hash)) return { allowed: false, reason: 'already_claimed', nullifier_hash: hash };
  try {
    await store.add(hash);
  } catch (e) {
    // unique-constraint violation = a concurrent claim won the race, OR the write failed:
    // either way this claim is NOT durably the unique recipient -> deny, never allow.
    return { allowed: false, reason: 'already_claimed', nullifier_hash: hash };
  }
  return { allowed: true, nullifier_hash: hash };
}
