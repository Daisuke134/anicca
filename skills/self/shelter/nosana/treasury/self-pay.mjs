// self-pay.mjs — reuses the EXACT classification pattern verify-inflow.mjs/self-wallets.mjs already
// use (an inflow's `from` address is self-pay, never revenue, iff it is in a known set of
// colony-controlled addresses — INV-7) and generalizes it to accept ANY wallet set, so it works for
// both the EVM/Base x402 revenue rail (self-wallets-evm.mjs, a verbatim copy of the sibling
// worktree's list) and Franklin's own Solana treasury wallet, which the EVM-only source file does
// not (and structurally cannot) cover.
//
// This is NOT a second, competing self-pay engine: the actual exclusion rule — "address in a known
// self-wallet set => not revenue" — is copied unchanged. What differs is that verify-inflow.mjs
// hardcodes ONE EVM set inline; this module takes the set as a parameter so shelter/treasury can
// plug in whichever set is relevant to the chain a given revenue row's `from` address is on,
// without forking the classification logic itself.
//
// No colony-wide Solana self-wallet registry exists in THIS worktree yet (skills/economy/ubi/
// colony-wallets.json, which does list Franklin's own Solana address alongside two EVM addresses,
// lives only on canonical/main as of 2026-07-25 — added by a commit this feature's branch was cut
// before, not present here). Until that lands here, callers pass known Solana self-wallets
// explicitly (e.g. the shelter's own treasury address, so an accidental self-transfer is never
// double-counted as external revenue); DEFAULT_SOLANA_SELF_WALLETS stays an empty array — an empty
// default is honest (there is nothing to exclude yet), never a fabricated placeholder list.

import { SELF_WALLET_SET_EVM } from "./self-wallets-evm.mjs";

export { SELF_WALLET_SET_EVM };

export const DEFAULT_SOLANA_SELF_WALLETS = [];

/**
 * Pure: build the combined self-wallet set this treasury check should exclude from external
 * revenue — the EVM set (always included, verbatim from the shared source) union any Solana
 * addresses the caller knows are colony-controlled (e.g. the shelter's own treasury address, so an
 * inflow FROM Franklin's own wallet TO Franklin's own wallet — nonsensical on its face, but cheap
 * to guard — is never miscounted; and any sibling Solana wallet the caller supplies).
 * Case-insensitive for EVM (0x… addresses are case-insensitive checksummed hex) and exact-match for
 * Solana (base58 addresses ARE case-sensitive — lowercasing a base58 address changes which account
 * it names, unlike hex).
 */
export function buildSelfWalletSet({ solanaSelfWallets = DEFAULT_SOLANA_SELF_WALLETS } = {}) {
  const evm = new Set(SELF_WALLET_SET_EVM);
  const solana = new Set((solanaSelfWallets || []).filter((a) => typeof a === "string" && a.length > 0));
  return { evm, solana };
}

/**
 * Pure: is `address` a wallet the colony controls itself? EVM addresses (0x-prefixed) are matched
 * case-insensitively against `selfWalletSet.evm`; everything else (Solana base58) is matched
 * exact-case against `selfWalletSet.solana`. Returns false (never throws) for a missing/malformed
 * address — an unclassifiable address is NOT self-pay by default; the caller's revenue math must
 * treat "we could not tell" honestly rather than this function silently deciding either way for it.
 */
export function isSelfWalletAddress(address, selfWalletSet) {
  if (typeof address !== "string" || address.length === 0) return false;
  if (!selfWalletSet) return false;
  if (address.startsWith("0x") || address.startsWith("0X")) {
    return selfWalletSet.evm instanceof Set && selfWalletSet.evm.has(address.toLowerCase());
  }
  return selfWalletSet.solana instanceof Set && selfWalletSet.solana.has(address);
}

/**
 * Pure: classify one already-fetched revenue row. Never mutates `row`. A row with no `from` field
 * is classified `external: false` with `reason: "no from address — cannot prove external, fail
 * closed against counting it as revenue"` — the same fail-closed direction as spend-gate.mjs
 * (unknown data must never be read as the OPTIMISTIC outcome; here the optimistic outcome for a
 * revenue number is "this is real external income", so an unclassifiable row is excluded, not
 * included).
 *
 * @param {{from?: string, amountUsd?: number, ts?: number}} row
 * @param {{evm: Set<string>, solana: Set<string>}} selfWalletSet
 * @returns {object} row with `external` (boolean) and `classification` (string reason) added
 */
export function classifyRevenueRow(row, selfWalletSet) {
  if (!row || typeof row !== "object") {
    throw new Error("classifyRevenueRow: row must be an object");
  }
  if (typeof row.from !== "string" || row.from.length === 0) {
    return { ...row, external: false, classification: "no from address on this row — fail-closed, not counted as external revenue" };
  }
  const selfPay = isSelfWalletAddress(row.from, selfWalletSet);
  return {
    ...row,
    external: !selfPay,
    classification: selfPay
      ? `self-pay: ${row.from} is a colony-controlled wallet (INV-7 — never revenue)`
      : `external: ${row.from} is not in the known self-wallet set`,
  };
}

/** Pure: classify every row in `rows` (see classifyRevenueRow). */
export function classifyRevenueRows(rows, selfWalletSet) {
  return (rows || []).map((row) => classifyRevenueRow(row, selfWalletSet));
}
