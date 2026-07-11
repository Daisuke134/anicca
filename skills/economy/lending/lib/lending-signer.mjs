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

/**
 * normalizeTxHash — lowercases a tx hash before it is ever written to loans.jsonl (impl-review
 * iteration-4, FIND-301, critical). tx_hash values reach the ledger from TWO uncoordinated sources with
 * no shared, code-enforced casing contract: the happy-path disbursement route stores the external
 * facilitator's own `settle.json.transaction` string (`escrow.mjs`, a third-party Rust codebase this
 * feature does not control), while the reconciliation route stores THIS codebase's own
 * `eth_getLogs`-derived `log.transactionHash` (`lending-verify.mjs::extractTxHash`). Neither side of a
 * later replay-guard comparison (REQ-108e/REQ-124) can be trusted to already share casing — normalizing
 * at every storage site is the durable fix, the SAME "checksummed vs. lowercased forms of the SAME
 * value must compare equal" problem `addressesEqual` above already solves for wallet addresses.
 * Non-string input passes through unchanged (never fabricates a value; callers already reject a
 * falsy/missing tx_hash elsewhere).
 * @param {string|null|undefined} txHash
 * @returns {string|null|undefined}
 */
export function normalizeTxHash(txHash) {
  return typeof txHash === "string" ? txHash.toLowerCase() : txHash;
}

/**
 * txHashesEqual — case-insensitive tx-hash equality (impl-review iteration-4, FIND-301, critical),
 * mirroring `addressesEqual` exactly for the SAME class of hex-string identity problem. Used at every
 * tx_hash COMPARISON site (`lending-verify.mjs`'s `alreadyCredited`/`alreadyRecorded` guards) as
 * defense-in-depth alongside `normalizeTxHash`'s storage-side fix — so a row written before this fix
 * landed (already-lowercase or not) still compares correctly against a freshly-extracted candidate of
 * different casing. Fail-closed: neither side being a non-empty string is treated as unequal.
 * @param {string|null|undefined} a
 * @param {string|null|undefined} b
 * @returns {boolean}
 */
export function txHashesEqual(a, b) {
  return typeof a === "string" && a.length > 0 && typeof b === "string" && b.length > 0 && a.toLowerCase() === b.toLowerCase();
}
