// Fixed-identity colony instances whose host name is a stable, pre-registered handle rather than the
// auto-derived "anicca-<first 6 hex>" scheme (e.g. Franklin's Solana wallet, claude-p's Polygon wallet —
// docs/superpowers/specs/2026-07-03-anicca-colony-architecture-design.md §19). Each entry pins exactly
// one wallet id to one host, so the SAME anti-squatting invariant from 830dc93b4 still holds: only the
// pinned wallet may ever claim that host name. Extracted into its own module (no private keys here — only
// PUBLIC addresses) so the lookup logic is unit-testable without needing any real signing key.
const FIXED_IDENTITIES = {
  "0x904b50d2e214da947d83d6a2d32c4e3ffc17eb74": "claude-p", // EVM: looked up lowercased
  "8FpqdcCHqjqkVXR58eVJa53neXbJf9emXhvHhgeUPCV9": "Franklin", // Solana: base58, case-sensitive, verbatim
};

// The canonical host an id is allowed to claim: a pinned fixed name, else the auto-derived
// "anicca-<first 6 hex>" (EVM only — no auto-derived Solana instance exists yet).
function expectedHost(id) {
  return FIXED_IDENTITIES[id] || FIXED_IDENTITIES[String(id).toLowerCase()] || ("anicca-" + String(id).slice(2, 8).toLowerCase());
}

module.exports = { FIXED_IDENTITIES, expectedHost };
