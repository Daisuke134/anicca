// economy/lending/lib/lending-signer.mjs — derives the on-chain signer address a raw EVM private key
// would sign as, for the money-safety guard this feature's impl-review iteration-1 (FIND-001,
// critical) requires: confirming "the resolved key actually belongs to the lender the ledger says it
// does" BEFORE any lock/provisioning/disbursement is attempted. Pure, deterministic (viem's own
// privateKeyToAccount) — no I/O, no mutation. Fail-closed: returns null instead of throwing on a
// malformed/missing key, the SAME convention resolve-identity.mjs already uses for an unresolvable
// key, so callers can treat "null" and "mismatch" identically (both refuse).
import { privateKeyToAccount } from "viem/accounts";

/**
 * deriveSignerAddress — the checksummed EVM address `privateKey` would sign transactions as.
 * @param {string|null|undefined} privateKey
 * @returns {string|null}
 */
export function deriveSignerAddress(privateKey) {
  if (typeof privateKey !== "string" || privateKey.length === 0) return null;
  try {
    return privateKeyToAccount(privateKey).address;
  } catch {
    return null;
  }
}

/**
 * addressesEqual — case-insensitive EVM address equality (checksummed vs. lowercased forms of the
 * SAME address must compare equal). Neither input being a non-empty string is treated as unequal
 * (fail-closed — a missing recorded wallet must never compare "equal" to anything).
 * @param {string|null|undefined} a
 * @param {string|null|undefined} b
 * @returns {boolean}
 */
export function addressesEqual(a, b) {
  return typeof a === "string" && a.length > 0 && typeof b === "string" && b.length > 0 && a.toLowerCase() === b.toLowerCase();
}
