// Agents at Arms leaderboard constants (VCSDD).
// excludeSet(row) is PER-ROW: it contains the row's OWN id so self-transfers never count as earnings,
// plus our own instances and the parent-treasury/seed wallets. Inflows FROM any of these are NOT
// earnings (they're self-funding / internal transfers), so they cannot buy leaderboard rank.
// All values are PUBLIC wallet addresses (no private keys), lowercased at use.

// Our canonical instance wallet ids. Add each new instance's wallet as it comes online.
const OUR_INSTANCE_IDS = [
  "0xa3cdd4ec6b94f01826aaf90a6d5538a2aa8c4c21", // ANICCA_WALLET_ADDRESS (primary Anicca instance)
];

// Parent-treasury / seed / founder wallets. Money sent FROM these to an agent = seed funding.
// Solana (base58) addresses go in this SAME list — normalize() below tells them apart by prefix.
const SEED_ADDRESSES = [
  "0x810f6d61f7606deee2657d3083e150a222bc29c5", // founder / treasury (Base) — seeds children
  "BF9vzj7YdA6nowwZdW65fQSM1vhRN4sntkKTPnnsfRCX", // founder / treasury (Solana mainnet) — seeds children
];

// Base/EVM ids are 0x-prefixed hex (case-INsensitive, canonicalized lowercase). Solana ids are
// base58 (case-SENSITIVE — lowercasing corrupts the address). Same rule as telemetry-store.js's
// normalizeId — the two formats are distinguishable by the "0x" prefix.
function normalize(id) {
  const s = String(id);
  return s.startsWith("0x") ? s.toLowerCase() : s;
}

function excludeSet(row) {
  const s = new Set();
  if (row && row.id) s.add(normalize(row.id));
  for (const a of OUR_INSTANCE_IDS) s.add(normalize(a));
  for (const a of SEED_ADDRESSES) s.add(normalize(a));
  return s;
}

module.exports = { OUR_INSTANCE_IDS, SEED_ADDRESSES, excludeSet };
