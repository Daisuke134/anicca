// economy/gig/lib/ensure-agent-id.mjs — resolve-or-register THIS instance's own ERC-8004 identity,
// cached to disk so run.sh mints the identity NFT AT MOST ONCE per instance. register() is real gas
// and is NOT idempotent (calling it twice mints two token ids for the same wallet, wasting funds) —
// this is deterministic bookkeeping (same category as resolve-identity.mjs's file-gated key lookup),
// never a judgment call. Cache path mirrors resolve-identity.mjs's own ANICCA_HOME gating exactly, so
// a foreign spawn (different ANICCA_HOME) can never read/reuse another instance's cached agentId.
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { privateKeyToAccount } from "viem/accounts";
import { registerIdentity, verifyIdentity } from "./identity.mjs";

function cachePath(env = process.env) {
  const home = env.ANICCA_HOME || (env.HOME ? path.join(env.HOME, ".anicca") : null);
  if (!home) return null;
  return path.join(home, ".automaton", "gig-agent-id.json");
}

function readCache(file) {
  try {
    return JSON.parse(fs.readFileSync(file, "utf8"));
  } catch {
    return null;
  }
}

function writeCache(file, data) {
  try {
    fs.mkdirSync(path.dirname(file), { recursive: true });
    fs.writeFileSync(file, JSON.stringify(data));
  } catch {
    // best-effort cache -- a failed write just means we re-register (or re-verify) next wake
  }
}

/**
 * Resolve this instance's own ERC-8004 agentId, registering on-chain ONLY the first time. Re-verifies
 * a cached agentId is STILL owned by the current address before trusting it (a stale/foreign cache
 * must never be reused blindly). Fail-closed: any error returns {ok:false}, never throws, never
 * silently mints a duplicate identity for an address that already has one cached.
 *
 * @param {{privateKey: string, env?: object, cacheFile?: string,
 *          registerFn?: Function, verifyFn?: Function}} opts
 *   registerFn/verifyFn: injected for tests (default to the real on-chain calls in lib/identity.mjs).
 * @returns {Promise<{ok:true, agentId:string, address:string, cached:boolean}|{ok:false, reason:string}>}
 */
export async function ensureAgentId({
  privateKey,
  env = process.env,
  cacheFile,
  registerFn = registerIdentity,
  verifyFn = verifyIdentity,
} = {}) {
  if (!privateKey) return { ok: false, reason: "no signing key" };
  let address;
  try {
    address = privateKeyToAccount(privateKey).address;
  } catch (e) {
    return { ok: false, reason: `invalid signing key: ${e.message || e}` };
  }

  const file = cacheFile || cachePath(env);
  if (file) {
    const cached = readCache(file);
    if (cached && cached.address && cached.agentId && cached.address.toLowerCase() === address.toLowerCase()) {
      const check = await verifyFn({ agentId: cached.agentId, expectedAddress: address });
      if (check.ok && check.valid) {
        return { ok: true, agentId: cached.agentId, address, cached: true };
      }
      // cached agentId no longer verifies (unexpected) -- fall through and register fresh rather than
      // trusting stale data; never silently swallow the mismatch.
    }
  }

  const reg = await registerFn({ privateKey });
  if (!reg.ok) return { ok: false, reason: reg.reason };
  if (file) writeCache(file, { address, agentId: reg.agentId });
  return { ok: true, agentId: reg.agentId, address, cached: false };
}

// CLI: `SIGNKEY=0x... node ensure-agent-id.mjs` prints {"ok":true,"agentId":"..","address":".."} (or
// {"ok":false,"reason":".."}) to stdout — never the key itself — so run.sh can capture the result via
// command substitution.
if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const privateKey = process.env.SIGNKEY;
  ensureAgentId({ privateKey })
    .then((r) => console.log(JSON.stringify(r)))
    .catch((e) => console.log(JSON.stringify({ ok: false, reason: e.message || String(e) })));
}
