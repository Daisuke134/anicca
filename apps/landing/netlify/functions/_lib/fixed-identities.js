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
  "F5SYUC4f5QULbEgSYb1DFCBfi74AnWE3ZaXAhqXwhZ5T": "Franklin", // Solana: base58, case-sensitive, verbatim (rotated 2026-07-17, old 8Fpqd... key leaked)
  // FIX-1 (2026-07-17): franklin2's own Solana wallet (~/.franklin2-home/.blockrun/.solana-session),
  // derived the same way telemetry-post-franklin.mjs derives it (last 32 bytes of the 64-byte secret
  // key, base58-encoded). Without this entry expectedHost() fell through to the EVM-only auto-derive
  // fallback ("anicca-" + id.slice(2,8)), which mangles a base58 id and never equals the poster's
  // host:"Franklin2" — every post 400'd as host_wallet_mismatch (poster.log: 4193/4194 non-202).
  "HyJHSfTkLjpmqeY4FEbnSjM4DfUh9ELGchHqgFDBkrcX": "Franklin2", // Solana: base58, case-sensitive, verbatim
};

// The canonical host an id is allowed to claim: a pinned fixed name, else the auto-derived
// "anicca-<first 6 hex>" (EVM only — no auto-derived Solana instance exists yet; the fallback is
// still wrong for any *unregistered* Solana id — out of scope for FIX-1, tracked here only).
function expectedHost(id) {
  return FIXED_IDENTITIES[id] || FIXED_IDENTITIES[String(id).toLowerCase()] || ("anicca-" + String(id).slice(2, 8).toLowerCase());
}

module.exports = { FIXED_IDENTITIES, expectedHost };
