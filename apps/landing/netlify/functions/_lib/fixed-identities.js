// Fixed-identity colony instances whose host name is a stable, pre-registered handle rather than the
// auto-derived "anicca-<first 6 hex>" scheme (e.g. Franklin's Solana wallet, claude-p's Polygon wallet —
// docs/superpowers/specs/2026-07-03-anicca-colony-architecture-design.md §19). Each entry pins exactly
// one wallet id to one host, so the SAME anti-squatting invariant from 830dc93b4 still holds: only the
// pinned wallet may ever claim that host name. Extracted into its own module (no private keys here — only
// PUBLIC addresses) so the lookup logic is unit-testable without needing any real signing key.
//
// claude-p (2026-07-05 finding, skills/earn/polymarket-trade/SKILL.md): its real funded Polymarket wallet
// (0x904B50d2e214Da947d83D6a2D32c4E3Ffc17Eb74) is an ERC-1167 smart-contract PROXY (POLY_1271 sig type)
// with NO private key of its own — it structurally cannot produce a plain EIP-191 signature, which is
// all this endpoint currently verifies. Its owner EOA is ALSO the shared founder/treasury identity used
// elsewhere (SEED_ADDRESSES), so signing as that address would misreport claude-p's identity as the
// treasury's. Pinned here instead is a DEDICATED signing-only identity generated for this purpose (holds
// no funds, never used for trading) — exactly the same pattern anicca-a3cdd4 already uses (one signing
// wallet.json, net worth read from many separate on-chain addresses).
const FIXED_IDENTITIES = {
  "0x02bb6b2af70dbf2c367c1b69aca9858bf3525502": "claude-p", // EVM: looked up lowercased (signing-only identity, not the funded proxy)
  "8FpqdcCHqjqkVXR58eVJa53neXbJf9emXhvHhgeUPCV9": "Franklin", // Solana: base58, case-sensitive, verbatim
};

// The canonical host an id is allowed to claim: a pinned fixed name, else the auto-derived
// "anicca-<first 6 hex>" (EVM only — no auto-derived Solana instance exists yet).
function expectedHost(id) {
  return FIXED_IDENTITIES[id] || FIXED_IDENTITIES[String(id).toLowerCase()] || ("anicca-" + String(id).slice(2, 8).toLowerCase());
}

module.exports = { FIXED_IDENTITIES, expectedHost };
