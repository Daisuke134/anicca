// identity-guard.mjs — the constitutional malice-guard, enforced in code (spec 28 §3).
//
// THE WALL: Anicca earns using ONLY its OWN identity (own Base wallet + own AgentMail).
// It MUST NEVER use a USER's email / name / phone / contacts / calendar / messaging identity
// to earn, cold-outreach, or build trust. The user's connected info (gcal / Gmail / phone /
// location) is for managing the USER'S OWN life ONLY — never to earn.
//
// Polsia distinction: a founder using their OWN inbox for their OWN company = consented
// self-use (fine). Multi-tenant use of EACH user's identity to earn = the malice this forbids.
//
// This module is imported by the earn write-path (lib/record.mjs). Every earn-ledger line
// passes assertOwnIdentityOnly(); if the earn context references a user-PII source or env,
// it THROWS — the earn never records, the wake fails closed.

// Env-var name fragments that belong to a USER's connected identity (NOT Anicca's own).
// If any of these is present in the env handed to the earn path, the earn is tainted.
export const USER_PII_ENV_PATTERNS = [
  /^USER_/i,                 // any explicit USER_* var (USER_EMAIL, USER_PHONE, USER_NAME…)
  /GOOGLE_LOGIN/i,           // the user's Google login (life-skill / Composio onboarding)
  /COMPOSIO/i,               // Composio = the user's connected gcal/Gmail grant
  /GCAL|GOOGLE_CALENDAR/i,   // user calendar
  /USER.?GMAIL|GMAIL_REFRESH|GMAIL_TOKEN/i, // user mailbox tokens
  /TELEGRAM/i,               // user live-location / messaging
  /USER.?PHONE|USER.?CONTACT/i,
];

// "source" values the earn ledger is ALLOWED to record. These are Anicca's OWN identity
// channels: its own wallet (x402 / crypto / 0xwork escrow) and its own AgentMail-based
// content. A user-identity source can never appear here.
export const ALLOWED_EARN_SOURCES = new Set([
  "x402", "0xwork", "litcoin", "nookplot", "crypto",
  "swap-eth-usdc", "swap", "swap-usdc-eth", // own-asset rotation (non-gate, still own identity)
  // own-wallet DeFi yield + investing (deploy own idle USDC into own positions — own identity).
  // execute-yield.mjs emits source "yield-<protocol>" (e.g. yield-beefy-morpho, yield-aave-v3) and
  // execute-invest.mjs "invest-eth-dca"; without these the guard rejected real yield earns (the
  // deposit happened on-chain but couldn't be recorded). Added 2026-06-21.
  "yield", "yield-aave-v3", "yield-beefy-morpho", "yield-beefy", "yield-fluid", "yield-morpho",
  "yield-moonwell", "yield-defi", "invest-eth-dca",
  "hl-trade", "hl", // own-wallet Hyperliquid perp (own identity, own funds)
  // own-wallet Polymarket CTF/neg-risk redeem: collecting an ALREADY-WON resolved
  // position back into the SAME deposit wallet (own identity, own funds, no
  // external transfer). Added 2026-07-05 (earn-redeem-winnings, EARN-1).
  "polymarket-redeem",
  // own-wallet Polymarket CTF mergePositions: converting an OPEN (unresolved) balanced
  // YES+NO leg pair back into collateral in the SAME deposit wallet -- own identity, own
  // funds, no external transfer, no counterparty needed (permissionless CTF primitive,
  // distinct from redeem which requires market resolution). Added 2026-07-17 (RECOVER-1).
  "polymarket-merge",
  "token-launch", "token", // own token launch (own identity)
  "content", "x402-serve",
  // own-identity store introspection (SELF-STORE-1, 2026-07-18): reading our own sales/attempts
  // logs and re-listing our own catalog moves no funds and touches no foreign identity.
  "x402-review", "x402-update",
  // promote.fun per-view clipping: Anicca's OWN IG account + OWN Solana wallet payout (own identity).
  // Added 2026-06-29 (promote-fun-clip-earn). Matches no FORBIDDEN_EARN_SOURCES pattern.
  "promote.fun", "clip-promote", "ig-clip",
  "cook", // own-identity web exploration (no funds moved)
  "discover", // narrate-only discovery wake
  // economy/gig internal gig-market (P2.2): Anicca posting/taking/delivering/collecting payouts on the
  // gig board using its OWN wallet + OWN ERC-8004 on-chain identity (posterAgentId/takerAgentId are
  // always derived from THIS instance's own key, never a user's) -- own identity, added 2026-07-07.
  "gig",
  // earn/sol-trade: Franklin's OWN Solana wallet (8Fpqd, resolved per-instance via
  // wallet-address-solana.mjs; the identity-match guard in sol-trade/run.sh HALTs any non-owner
  // instance) doing REAL Jupiter DEX swaps -- own identity, added 2026-07-08 (franklin-earn-foundation).
  "sol-trade",
]);

// Sources that smell of using a USER's identity to earn. Explicit denylist so a typo'd or
// hostile source can't slip a user-identity earn past the allowlist by being "unknown".
export const FORBIDDEN_EARN_SOURCES = [
  /gmail/i, /gcal|calendar/i, /contact/i, /cold.?mail|cold.?outreach|outreach/i,
  /user.?email|user.?name|user.?phone/i, /telegram/i, /composio/i,
];

// Scan an env object for any user-PII variable. Returns the offending key, or null.
export function findUserPIIEnv(env = process.env) {
  for (const key of Object.keys(env || {})) {
    if (USER_PII_ENV_PATTERNS.some((re) => re.test(key))) return key;
  }
  return null;
}

// Assert the earn `source` is one of Anicca's OWN identity channels.
// Throws if the source is forbidden (user-identity) or simply not on the allowlist.
export function assertOwnEarnSource(source) {
  const s = String(source ?? "");
  for (const re of FORBIDDEN_EARN_SOURCES) {
    if (re.test(s)) {
      throw new Error(
        `MALICE-GUARD: earn source "${s}" references a USER identity. ` +
        `Anicca earns with its OWN wallet/AgentMail only (spec 28 §3).`
      );
    }
  }
  if (!ALLOWED_EARN_SOURCES.has(s)) {
    throw new Error(
      `MALICE-GUARD: earn source "${s}" is not an own-identity channel ` +
      `(allowed: ${[...ALLOWED_EARN_SOURCES].join(", ")}).`
    );
  }
  return true;
}

// The single guard the earn write-path calls before recording a line. It fails CLOSED:
//   1. no user-PII env var may be present in the earn process env, AND
//   2. the earn source must be an own-identity channel.
// `opts.env` defaults to process.env so the live run.sh path is covered; tests pass a fixture.
export function assertOwnIdentityOnly(line, opts = {}) {
  const env = opts.env || process.env;
  const offending = findUserPIIEnv(env);
  if (offending) {
    throw new Error(
      `MALICE-GUARD: earn process exposes user-PII env "${offending}". ` +
      `The earn skill must have NO access to user PII (spec 28 §3). Refusing to record.`
    );
  }
  assertOwnEarnSource(line && line.source);
  return true;
}
