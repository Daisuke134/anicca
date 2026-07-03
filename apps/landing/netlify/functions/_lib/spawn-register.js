// Sprint-2 S9: spawn-boot signed upsert helper.
// Builds the canonical heartbeat, signs it with the agent's private key, verifies the
// signer==id invariant locally (so a mis-owned row never touches Supabase), stamps
// last_heartbeat, and upserts via the existing telemetry-store contract.
const { Wallet, verifyMessage } = require("ethers");
const { canonicalMessage, verifyTelemetry } = require("./telemetry-verify");
const { upsertInstance } = require("./telemetry-store");

async function registerSpawn({ privateKey, payload, storeDeps, now = () => new Date().toISOString() }) {
  if (!privateKey || !payload || !storeDeps) throw new Error("registerSpawn: privateKey, payload, storeDeps required");
  const wallet = new Wallet(privateKey);
  const message = canonicalMessage(payload);
  const signature = await wallet.signMessage(message);

  // Client-side invariant: signer MUST equal payload.id. Sprint-1 R10 + INV-OWN-STATE.
  const signer = verifyMessage(message, signature);
  if (signer.toLowerCase() !== String(payload.id).toLowerCase()) {
    throw new Error(`registerSpawn: signer/id mismatch (signer=${signer}, id=${payload.id})`);
  }
  // Full-format check with the same verifier the server uses (schema + replay window).
  const v = verifyTelemetry(message, signature, { now: payload.ts, lastTs: 0 });
  if (!v.ok) throw new Error(`registerSpawn: verifyTelemetry ${v.reason}`);

  const last_heartbeat = now();
  await upsertInstance({ ...payload, id: String(payload.id).toLowerCase(), last_heartbeat }, storeDeps);
  return { message, signature, last_heartbeat };
}

module.exports = { registerSpawn };
