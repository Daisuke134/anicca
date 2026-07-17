// Agents at Arms leaderboard constants (VCSDD).
// excludeSet(row) is PER-ROW: it contains the row's OWN id so self-transfers never count as earnings,
// plus our own instances and the parent-treasury/seed wallets. Inflows FROM any of these are NOT
// earnings (they're self-funding / internal transfers), so they cannot buy leaderboard rank.
// All values are PUBLIC wallet addresses (no private keys), lowercased at use.

// Our canonical instance wallet ids. Add each new instance's wallet as it comes online.
// NOTE: this Set is compared lowercased on both sides internally (self-consistent for exact-match
// purposes) — that's fine for Solana ids HERE (unlike telemetry-verify.js's signature-identity path,
// where lowercasing a base58 id would corrupt it and must never happen there).
const OUR_INSTANCE_IDS = [
  "0xa3cdd4ec6b94f01826aaf90a6d5538a2aa8c4c21", // ANICCA_WALLET_ADDRESS (primary Anicca instance)
  "F5SYUC4f5QULbEgSYb1DFCBfi74AnWE3ZaXAhqXwhZ5T", // Franklin (Solana, SELF-funded, rotated 2026-07-17)
  "0x02bb6b2af70dbf2c367c1b69aca9858bf3525502", // claude-p telemetry-signing identity (human-funded)
];

// Parent-treasury / seed / founder wallets. Money sent FROM these to an agent = seed funding.
const SEED_ADDRESSES = [
  "0x810f6d61f7606deee2657d3083e150a222bc29c5", // founder / treasury (Base) — seeds children
];

function excludeSet(row) {
  const s = new Set();
  if (row && row.id) s.add(String(row.id).toLowerCase());
  for (const a of OUR_INSTANCE_IDS) s.add(String(a).toLowerCase());
  for (const a of SEED_ADDRESSES) s.add(String(a).toLowerCase());
  return s;
}

module.exports = { OUR_INSTANCE_IDS, SEED_ADDRESSES, excludeSet };
