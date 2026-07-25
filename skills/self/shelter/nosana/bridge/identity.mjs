// identity.mjs — resolves the two identities this bridge moves money between: the Base(EVM)
// wallet holding the idle USDC (source, signs the burn) and the Solana wallet that receives it
// (destination — address only; this build never signs anything on the Solana side, see
// bridge.mjs's file header for why the destination-side finalize call is out of scope). Reuses
// skills/earn/lib/resolve-identity.mjs's resolution chain UNCHANGED for both chains — never a
// new/second wallet, never a bespoke resolution path — and ../keypair.mjs's
// `deriveAddressFromSecret` (the SAME function funding/acquire-nos.mjs already uses to derive
// Franklin's own address from its secret), exactly the "tenant/-style derivation" this feature's
// spec calls for.

import { resolveEvmPrivateKey, resolveSolanaSecret } from "../../../../earn/lib/resolve-identity.mjs";
import { deriveAddressFromSecret } from "../keypair.mjs";
import { privateKeyToAccount } from "viem/accounts";

/**
 * @param {{env?: Record<string,string>, evmHome?: string, solanaHome?: string}} [opts]
 *   evmHome: explicit home for the Base (source) identity, e.g. `$HOME/.anicca-founder`. Defaults
 *   to resolveEvmPrivateKey's own default (env.ANICCA_HOME, then $HOME/.anicca).
 *   solanaHome: explicit home for the Solana (destination) identity, e.g. `$HOME/.blockrun`
 *   (Franklin's home — the wallet that actually pays for shelter and needs the runway). REQUIRED:
 *   bridging is inherently cross-instance (founder's idle Base USDC -> Franklin's Solana wallet),
 *   so this is never silently defaulted to the caller's own ANICCA_HOME — see bridge.mjs.
 * @returns {{evmAddress: string, evmPrivateKey: `0x${string}`, solanaAddress: string}}
 */
export function resolveBridgeIdentity({ env = process.env, evmHome, solanaHome } = {}) {
  if (typeof solanaHome !== "string" || solanaHome.length === 0) {
    throw new Error(
      "resolveBridgeIdentity: solanaHome is required — bridging is cross-instance by design, never inferred from the caller's own ANICCA_HOME (fail-closed)",
    );
  }

  const evmPrivateKey = resolveEvmPrivateKey({ home: evmHome, env });
  if (!evmPrivateKey) {
    throw new Error(
      `resolveBridgeIdentity: no EVM private key resolved for home ${evmHome ?? env.ANICCA_HOME ?? "(default)"} — refusing (fail-closed)`,
    );
  }
  const evmAddress = privateKeyToAccount(evmPrivateKey).address;

  const solanaSecret = resolveSolanaSecret({ home: solanaHome, env });
  if (!solanaSecret) {
    throw new Error(`resolveBridgeIdentity: no Solana secret resolved for home ${solanaHome} — refusing (fail-closed)`);
  }
  // Only `.address` is ever propagated out of this module — `secretBytes` (the decoded private
  // key material) goes out of scope immediately below and is never returned, logged, or written.
  // Nothing downstream of resolveBridgeIdentity needs to sign on Solana in this build.
  const { address: solanaAddress } = deriveAddressFromSecret(solanaSecret);

  return { evmAddress, evmPrivateKey, solanaAddress };
}
