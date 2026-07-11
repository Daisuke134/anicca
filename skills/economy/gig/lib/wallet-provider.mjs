// economy/gig/lib/wallet-provider.mjs — franklin-reputation-gasless G4: a differentiable seam between
// "how a signer is constructed" and "what identity.mjs/reputation.mjs/ensure-gas.mjs do with it", so a
// future true-gasless signer can be swapped in at ONE place instead of three. See
// docs/superpowers/specs/2026-07-12-franklin-reputation-gasless-design.md §1 G4 and
// docs/loop-engineering/23-anicca-loop-architecture-redesign.md §11 部品2 (source of the evaluation
// below).
//
// ★NOT WIRED (spec §1 G4 MUST: "本 spec では実配線しない、seam のみ")★ — identity.mjs, reputation.mjs,
// and ensure-gas.mjs each still build their own viem WalletClient directly (walletClientFactory /
// sendDripFn defaults), UNCHANGED by this file. This module is not imported by any of them. It exists
// so the swap described below has a landing spot when/if it's ever needed -- adopting it today would be
// wiring a seam nothing uses yet, i.e. the exact "abstraction not required by tests" anti-pattern this
// codebase's own coding-style rules forbid.
//
// ============================================================================================
// EVALUATION MEMO (23 §11 部品2, real code read this session -- @coinbase/agentkit source, not docs)
// ============================================================================================
// Read directly: agentkit's `viemWalletProvider.ts` (thinly wraps an ALREADY-CONSTRUCTED viem
// WalletClient -- construction, key management, and RPC selection all stay exactly as this repo already
// does them) and `cdpSmartWalletProvider.ts` (constructs an ERC-4337 smart account via
// `CdpSmartWalletProvider.configureWithWallet({ paymasterUrl, ... })` -- THIS is the piece that gives
// true gasless writes: user operations are bundled and a paymaster contract pays the gas, not this
// wallet's own native ETH balance).
//
// AS-IS (this repo, all three files independently, per identity.mjs's own documented rationale for
// staying self-contained rather than cross-importing): construct `createWalletClient({ account, chain,
// transport: http(rpcUrl) })` directly from a raw private key via `privateKeyToAccount`. Every write
// (register(), giveFeedback(), the G1 testnet gas drip itself) spends THIS wallet's own native ETH.
//
// COST of adopting CdpSmartWalletProvider now: a new npm dependency (@coinbase/agentkit, NOT currently
// in this repo's package.json -- confirmed via repo-wide grep, zero hits outside this comment) whose own
// erc8004 action-provider internally depends on an unverified-by-us `agent0-ts` package (23 §11 部品2's
// own UNVERIFIED flag), PLUS a real Coinbase Developer Platform paymaster account/API key this feature's
// money-safety boundary (§4) explicitly forbids touching (no new external funded-service credentials in
// this spec). The current direct-viem approach is objectively THINNER (fewer deps, fewer external
// accounts) for what G1/G2/G3 actually need today (testnet-only, hard-capped, own-key writes).
//
// DECISION (per 23 §11's own "実装優先順" -- 部品2 explicitly ranked "保留"): do NOT adopt
// CdpSmartWalletProvider now. Revisit only if gasless onboarding becomes an ACTUAL measured bottleneck
// (e.g. G1's own testnet drip-cap/no-funder-configured refusal starts happening in production at a rate
// that matters) -- at that point, `createSignerFn` below is the one place every one of identity.mjs's,
// reputation.mjs's, and ensure-gas.mjs's own `walletClientFactory`/`sendDripFn` production defaults would
// each need to start calling instead of constructing their own `createWalletClient` inline.
import { createWalletClient, http } from "viem";
import { privateKeyToAccount } from "viem/accounts";

/**
 * createSignerFn — the seam itself: today, a thin, literal wrap of the SAME
 * `privateKeyToAccount` + `createWalletClient` pair identity.mjs/reputation.mjs/ensure-gas.mjs already
 * each construct inline. Swapping this module's internals to route through
 * `CdpSmartWalletProvider.configureWithWallet({ paymasterUrl })` in the future (see memo above) would
 * change NOTHING about this function's signature or return shape -- callers stay identical.
 */
export function createSignerFn({ privateKey, chain, rpcUrl }) {
  const account = privateKeyToAccount(privateKey);
  return createWalletClient({ account, chain, transport: http(rpcUrl) });
}
