// dashboard-wallet-legs.js — the SSOT mapping a telemetry row's signing `id` to every OTHER
// (chain, address) leg where that same instance actually holds money, plus its Polymarket trading
// account (for realized-PnL revenue — see polymarket-revenue-reader.js).
//
// Why this file exists (2026-07-12): enrichOnChain reads a single wallet on a single chain per row,
// keyed on the telemetry `id`. For most instances the signing id IS the funded wallet, so that is
// enough. Two instances are NOT like that:
//   - claude-p signs telemetry with a DEDICATED, UNFUNDED signing-only identity
//     (0x02bb6b2af70dbf2c367c1b69aca9858bf3525502 — see fixed-identities.js and docs/WALLETS.md
//     §"Telemetry SIGNING identity ≠ funding wallet") because its real funds sit behind a Polymarket
//     ERC-1167 deposit PROXY that cannot itself produce an EIP-191 signature. Reading balance AT the
//     signing id therefore always returns $0 — the dashboard was silently blind to claude-p's real
//     money on Base, Polygon, its Polymarket deposit, and its Hyperliquid margin.
//   - Franklin signs with its own funded Solana wallet (fine for the Solana leg), but ALSO holds
//     money on Base + Hyperliquid + its own Polymarket deposit wallet, none of which the Solana-only
//     reader could see.
//
// All addresses here are PUBLIC (no private keys). This is DATA (which wallets belong to which known
// instance), not judgment — same category as fixed-identities.js / leaderboard-constants.js.
//
// NOTE on the Polymarket deposit wallet: it is deliberately NOT in `legs` (which only reads plain
// ERC-20 balances). A Polymarket account's real value is mostly OPEN POSITIONS (ERC-1155 conditional
// tokens), invisible to balanceOf() — verified live 2026-07-12: claude-p's deposit wallet held ~$0.18
// of idle pUSD while its actual mark-to-market portfolio value was ~$20.59. `polymarketAccount` is
// read separately via polymarket-value-reader.js's /value endpoint (idle cash + every open position,
// Polymarket's own mark-to-market — the same number the trader sees in its own UI), added on top of
// the plain chain legs. `polymarketRevenue: true` additionally enables the realized-P&L revenue
// override (polymarket-revenue-reader.js) for that id.
const WALLET_LEGS = {
  // claude-p — telemetry signing id (0x02bb…) holds no funds itself; real money lives at the
  // founder-loop treasury wallet (0x810f…, base+polygon+hyperliquid) and the Polymarket deposit
  // proxy (0x904B50…, polygon). docs/WALLETS.md §"Telemetry SIGNING identity ≠ funding wallet".
  '0x02bb6b2af70dbf2c367c1b69aca9858bf3525502': {
    legs: [
      { chain: 'base', address: '0x810f6d61f7606deee2657d3083e150a222bc29c5', label: 'claude-p treasury (base)' },
      { chain: 'polygon', address: '0x810f6d61f7606deee2657d3083e150a222bc29c5', label: 'claude-p treasury (polygon)' },
      { chain: 'hyperliquid', address: '0x810f6d61f7606deee2657d3083e150a222bc29c5', label: 'claude-p HL margin' },
    ],
    polymarketAccount: '0x904B50d2e214Da947d83D6a2D32c4E3Ffc17Eb74',
    // realized Polymarket PnL (REDEEM − BUY) is claude-p's revenue signal — see polymarket-revenue-reader.js.
    polymarketRevenue: true,
  },
  // Franklin — telemetry signing id IS its own funded Solana wallet, but it also holds Base +
  // Hyperliquid + its own Polymarket deposit wallet that the Solana-only reader never saw.
  '8FpqdcCHqjqkVXR58eVJa53neXbJf9emXhvHhgeUPCV9': {
    legs: [
      { chain: 'solana', address: '8FpqdcCHqjqkVXR58eVJa53neXbJf9emXhvHhgeUPCV9', label: 'Franklin (solana)' },
      { chain: 'base', address: '0x3EcCAD24794ca298D25378E9902A251322ea8749', label: 'Franklin (base)' },
      { chain: 'hyperliquid', address: '0x3EcCAD24794ca298D25378E9902A251322ea8749', label: 'Franklin HL margin' },
    ],
    polymarketAccount: '0xda4b6E34A25fa70A901f30161f1Fd6a3Ec68219b',
    // Franklin's earn rail is SOL trading, not Polymarket (colony architecture doc §19) — count its PM
    // deposit toward net worth, but do not report Polymarket P&L as Franklin's "revenue" signal.
    polymarketRevenue: false,
  },
};

// EVM ids are 0x-prefixed hex, case-INsensitive (canonicalized lowercase). Solana ids are base58,
// case-SENSITIVE — lowercasing would corrupt the address. Same rule as leaderboard-constants.js.
function normalizeId(id) {
  const s = String(id);
  return s.startsWith('0x') ? s.toLowerCase() : s;
}

function legsFor(id) {
  const entry = WALLET_LEGS[normalizeId(id)];
  return entry ? entry.legs : [];
}

function polymarketAccountFor(id) {
  const entry = WALLET_LEGS[normalizeId(id)];
  return (entry && entry.polymarketAccount) || null;
}

function polymarketRevenueEnabledFor(id) {
  const entry = WALLET_LEGS[normalizeId(id)];
  return !!(entry && entry.polymarketRevenue);
}

module.exports = { WALLET_LEGS, normalizeId, legsFor, polymarketAccountFor, polymarketRevenueEnabledFor };
