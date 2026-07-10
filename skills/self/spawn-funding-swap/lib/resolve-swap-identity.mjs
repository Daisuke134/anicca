// resolve-swap-identity.mjs — spawn-funding-swap's own per-instance Base signer identity resolution
// (REQ-009 / FIND-002 fix, contract-review round: fresh-Opus adversary flagged the CLI reading
// identity-determining values from generic shared env vars WITHOUT the mandatory ANICCA_HOME
// per-instance gate — on the shared Mac this can load ANOTHER instance's Base signer key and sign a
// swap on the WRONG wallet, the exact leak class documented in
// feedback_earn_identity_resolve_per_instance_gate_on_anicca_home.md).
//
// This module is the CLI's SOLE source of `expectedBaseSignerAddress` / `sourceBaseAddress` (both
// money-path identity-determining values). It reuses skills/earn/lib/resolve-identity.mjs's own
// canonical resolveEvmPrivateKey (never a re-derived resolution path) and NEVER reads
// SPAWN_FUNDING_SWAP_EXPECTED_BASE_SIGNER_ADDRESS / SPAWN_FUNDING_SWAP_SOURCE_BASE_ADDRESS at all —
// there is no shared-env fallback path for identity. Resolution is gated on ANICCA_HOME being
// EXPLICITLY set, checked BEFORE resolveEvmPrivateKey is ever called: resolve-identity.mjs's own
// ANICCA_EVM_PRIVATE_KEY override (its priority-①  path) would otherwise apply regardless of
// ANICCA_HOME, so this module's own pre-check is what actually closes the "shared agent .env key
// present but ANICCA_HOME unset" leak (Test (c) below) — reusing resolve-identity.mjs's home-scoped
// legacy fallback alone would NOT have been sufficient.
//
// Fail-closed, never throws: returns { ok: false, reason } for ANY unresolvable case, { ok: true,
// baseAddress, akashKeyName } only once a real per-instance signing key is resolved. Callers MUST
// treat ok:false as "no lock/price/route/sign activity may happen" (mirrors driver.mjs's own REQ-009
// fail-closed-before-any-activity discipline).
import { resolveEvmPrivateKey } from "../../../earn/lib/resolve-identity.mjs";
import { privateKeyToAccount } from "viem/accounts";

/**
 * @param {{env?: Record<string, string>}} [opts]
 *   env: environment map to read from; defaults to process.env (mainly a test seam).
 * @returns {{ok: true, baseAddress: string, akashKeyName: string|undefined} | {ok: false, reason: string}}
 */
export function resolveOwnBaseIdentity({ env } = {}) {
  const e = env || process.env;

  // Gate FIRST, before resolveEvmPrivateKey is ever invoked — this instance has NO resolvable
  // identity here unless ANICCA_HOME is explicitly set. Never fall back to $HOME/.anicca's default
  // (which on the shared Mac IS another instance's real home) and never trust a shared agent .env key
  // that happens to be present in the ambient environment.
  if (typeof e.ANICCA_HOME !== "string" || e.ANICCA_HOME.length === 0) {
    return { ok: false, reason: "ANICCA_HOME is not set -- no per-instance identity to resolve (fail-closed, no shared-env fallback)" };
  }

  const privateKey = resolveEvmPrivateKey({ home: e.ANICCA_HOME, env: e });
  if (!privateKey) {
    return { ok: false, reason: `no Base signing key resolved under ANICCA_HOME=${e.ANICCA_HOME} (fail-closed)` };
  }

  const baseAddress = privateKeyToAccount(privateKey).address;
  const akashKeyName = typeof e.AKASH_KEY_NAME === "string" && e.AKASH_KEY_NAME.length > 0 ? e.AKASH_KEY_NAME : undefined;
  return { ok: true, baseAddress, akashKeyName };
}
