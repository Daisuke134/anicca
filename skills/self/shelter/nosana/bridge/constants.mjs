// constants.mjs — verified real-world constants for the Base(EVM)<->Solana CCTP V2 Standard
// Transfer bridge (S10: agent financial independence — move idle Base USDC to the Solana wallet
// that actually pays for shelter). Every address/domain below was verified LIVE 2026-07-25 against
// Circle's own docs (developers.circle.com) — see this feature's report for the exact quoted
// lines. Circle explicitly warns fees can change (never hardcode fees — see quote.mjs's
// bridgeFeeBps parameter, always passed in, never assumed here); domains/addresses are stable but
// should be re-verified if this module is ever revived after a long gap.

// Base mainnet.
export const BASE_CHAIN_ID = 8453; // verified live via eth_chainId -> 0x2105
export const BASE_DOMAIN = 6; // developers.circle.com/cctp/concepts/supported-chains-and-domains
export const SOLANA_DOMAIN = 5; // same page

// Native (Circle-issued) USDC on Base — the SAME literal already used by
// ../../../earn/lib/usdc.mjs. Kept as an independent constant here (not imported from usdc.mjs's
// internals) because usdc.mjs does not export it; bridge/ only imports usdc.mjs's public
// `usdcBalance` function. If this ever drifts, usdc.mjs is the other place to check.
export const BASE_USDC = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913";
export const BASE_USDC_DECIMALS = 6;

// TokenMessengerV2 on Base — verified live 2026-07-25 against
// developers.circle.com/cctp/references/contract-addresses:
// "Base | 6 | 0x28b5a0e9C621a5BadaA536219b3a228C8168cf5d"
// This is both the ERC-20 `approve` spender AND the `depositForBurn` call target.
export const TOKEN_MESSENGER_V2_BASE = "0x28b5a0e9C621a5BadaA536219b3a228C8168cf5d";

// Canonical (Circle-issued) USDC mint on Solana mainnet-beta. Well-known constant, cross-checked
// live 2026-07-25 against a real li.quest (LI.FI) quote response's `toToken.address` field.
export const SOLANA_USDC_MINT = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v";
export const SOLANA_USDC_DECIMALS = 6;

// CCTP V2 finality thresholds (developers.circle.com/cctp/references/technical-guide
// #defined-finality-thresholds): a message with minFinalityThreshold <= 1000 is a Fast Transfer
// (fee-bearing, 1.3 bps on Base per developers.circle.com/cctp/concepts/fees); 2000 is a Standard
// Transfer (0 bps everywhere per the same page, verified live 2026-07-25). This bridge only ever
// uses Standard Transfer — see the feature's report for why Fast Transfer's fee is not worth
// paying at this transfer size.
export const STANDARD_TRANSFER_MIN_FINALITY_THRESHOLD = 2000;

export const ZERO_BYTES32 = `0x${"00".repeat(32)}`;
