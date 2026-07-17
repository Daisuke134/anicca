// Sprint-2 S9: spawn-boot signed upsert helper.
// Builds the canonical heartbeat, signs it with the agent's private key, verifies the
// signer==id invariant locally (so a mis-owned row never touches Supabase), stamps
// last_heartbeat, and upserts via the existing telemetry-store contract.
const { Wallet, verifyMessage } = require("ethers");
const nacl = require("tweetnacl");
const bs58 = require("bs58");
const { canonicalMessage, verifyTelemetry } = require("./telemetry-verify");
const { upsertInstance } = require("./telemetry-store");

async function registerSpawn({ chain = "base", privateKey, payload, storeDeps, now = () => new Date().toISOString() }) {
  if (!privateKey || !payload || !storeDeps) throw new Error("registerSpawn: privateKey, payload, storeDeps required");
  const message = canonicalMessage(payload);
  let signature;

  if (chain === "solana") {
    // ed25519: no independent signer-recovery step — the claimed payload.id IS the verification
    // key. base58 is case-sensitive: NEVER lowercase a solana id anywhere in this path.
    const secretKey = bs58.decode(privateKey);
    const sig = nacl.sign.detached(Buffer.from(message, "utf8"), secretKey);
    signature = bs58.encode(Buffer.from(sig));
    const claimedPub = bs58.decode(payload.id);
    const verifiedAgainstClaim = nacl.sign.detached.verify(Buffer.from(message, "utf8"), sig, claimedPub);
    if (!verifiedAgainstClaim) {
      throw new Error(`registerSpawn: signer/id mismatch (solana) — payload.id=${payload.id} does not match the signing key`);
    }
    const v = verifyTelemetry(message, signature, { now: payload.ts, lastTs: 0 });
    if (!v.ok) throw new Error(`registerSpawn: verifyTelemetry ${v.reason}`);
    const last_heartbeat = now();
    await upsertInstance({ ...payload, id: payload.id, last_heartbeat }, storeDeps);
    return { message, signature, last_heartbeat };
  }

  const wallet = new Wallet(privateKey);
  signature = await wallet.signMessage(message);

  // Client-side invariant: signer MUST equal payload.id. Sprint-1 R10 + INV-OWN-STATE.
  // Error message MUST contain the literal "signer" AND both addresses so RED tests can bind
  // to the invariant, not to a coincidental thrown error (S9.2).
  //
  // S2-IMPL-FIND: verifyTelemetry ALSO checks signer==id internally, so we would be duplicating
  // the invariant. We keep this pre-check as the ONLY place we throw the semantic
  // "signer/id mismatch" error (the RED test binds to that specific message), and call
  // verifyTelemetry AFTER for the remaining checks (schema + replay window) — never as a
  // second signer check.
  const signer = verifyMessage(message, signature);
  const signerLc = signer.toLowerCase();
  const idLc = String(payload.id).toLowerCase();
  if (signerLc !== idLc) {
    throw new Error(`registerSpawn: signer/id mismatch — signer=${signer} payload.id=${payload.id}`);
  }
  // Full-format check: schema (rejects malformed additive fields BEFORE touching the store)
  // + replay window. verifyTelemetry re-verifies signer==id too, but that path is unreachable
  // here because the pre-check above already threw on any mismatch.
  const v = verifyTelemetry(message, signature, { now: payload.ts, lastTs: 0 });
  if (!v.ok) throw new Error(`registerSpawn: verifyTelemetry ${v.reason}`);

  const last_heartbeat = now();
  await upsertInstance({ ...payload, id: String(payload.id).toLowerCase(), last_heartbeat }, storeDeps);
  return { message, signature, last_heartbeat };
}

module.exports = { registerSpawn };
