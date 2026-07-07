# Resolution Notes — Phase 1c iteration-7 spec review (FIND-601..604)

**Feature**: anicca-agent-spawn · **mode**: strict · **date**: 2026-07-07
**Reviewed findings**: `reviews/spec/iteration-7/output/findings/FIND-601.json` (critical),
`FIND-602.json` (major), `FIND-603.json` (critical), `FIND-604.json` (major)
**Files edited**: `specs/behavioral-spec.md`, `specs/verification-architecture.md` (both bumped to
"iteration 7, revised"). No `state.json`, review manifest, or verdict file was touched, per
instructions. Nothing was committed/pushed.

---

## FIND-601 (critical) — wallet address mismatch / stale citation

**Important honesty note**: the underlying FACT question here — "which address is automaton's real,
current wallet, `0xB9dd3B67921B354c656523d6851537988F31DD56` or `0xa3CDd4Ec6b94F01826Aaf90a6d5538A2Aa8C4C21`?"
— was investigated and RESOLVED **by the architect** (the calling agent), not by this spec-builder pass.
The architect cryptographically re-derived the real address from `~/.automaton/wallet.json`'s actual
`privateKey` via `viem`'s `privateKeyToAccount`, confirmed the file's own `rotatedAt`/`rotationReason`
metadata (key exposed in `~/.anicca-founder/agents/polymarket-agent/.env` + `~/.openclaw/.env`,
2026-07-07 incident), and separately fixed the two stale canonical docs (`CLAUDE.md`, `docs/WALLETS.md`)
in commit `18e6ae96a` (verified present on disk and in `git log` during this pass — see the "Verification
performed" section below). **This spec-builder pass did NOT re-investigate that fact — it only updated
the spec's own citation of its verification method**, per the architect's explicit instruction.

**What changed and where**:
- `specs/behavioral-spec.md:568` (`### REQ-105`) — the seed JSON array itself is **UNCHANGED** (it was
  already correct: `walletAddress.evm: "0xB9dd3B67921B354c656523d6851537988F31DD56"`).
- `specs/behavioral-spec.md:639-654` (new "**Corrected, resolves FIND-601 (critical):**" paragraph,
  inserted immediately before the seed JSON block) — replaces the prior citation ("per...
  `colony-status.sh`'s own live output and this project's own `CLAUDE.md` colony table") with: (a) an
  honest account of why that citation was wrong (CLAUDE.md/WALLETS.md had themselves drifted stale
  post-rotation, independently fixed by the architect in `18e6ae96a`), and (b) the citation of the
  method that was always actually authoritative — cryptographic re-derivation via `privateKeyToAccount`
  against the real `privateKey`, cross-checked against `colony-status.sh`'s own live balance query.
- `specs/behavioral-spec.md:737-742` (new REQ-105 Acceptance Criteria bullet, `**(resolves FIND-601)**`)
  — adds the binding forward-looking rule: every future seed/append of a `walletAddress` must be
  verified against real signing key material or a live balance query, never solely a markdown doc.
- `specs/behavioral-spec.md:100-112` (new "Changelog (iteration 6 spec review → iteration 7)" section,
  FIND-601 row) — summarizes the above for the historical audit trail this spec always keeps.
- `specs/verification-architecture.md:178` — new proof obligation **PROP-105g** (REQ-105): every
  seeded/appended `walletAddress` must be verified against real signing key material or a live balance
  query, never solely a markdown citation. Tier 0 (structural/process check, verified the same way
  REQ-104's design-constraint is verified — by Phase 3 structural/commit review, not a runtime
  assertion, since there is no code artifact to unit-test "was this citation method correct" against).
- `specs/verification-architecture.md:86-89` (Tier 0 list) and `:362` (Gate item 1a) — added references
  to PROP-105g so the new obligation is wired into the verification strategy and the adversary gate.
- `specs/verification-architecture.md:9` and `specs/behavioral-spec.md:9` — header revision lines
  bumped to "iteration 7" mentioning FIND-601 among the resolved findings.

**Verification performed during this pass** (confirming the architect's account, not re-deriving the
underlying fact): `grep -n "0xB9dd3B\|0xa3CDd4" CLAUDE.md docs/WALLETS.md` shows `CLAUDE.md:42` and
`docs/WALLETS.md:13` NOW both read `0xB9dd3B67921B354c656523d6851537988F31DD56`; `git log --oneline -3`
shows commit `18e6ae96a` — "docs: fix stale automaton wallet address in CLAUDE.md/WALLETS.md (rotated
2026-07-07, never propagated to these docs)" — with a commit body matching the architect's account
verbatim. The spec's own seed data required zero change.

---

## FIND-602 (major) — stale purity-boundary summary tables

**What changed and where**:
- `specs/behavioral-spec.md:225` — the "Shelter-cost funding transfer" row of the "Purity boundary
  analysis (overview)" table is corrected from a Solana/Jupiter-only description to: multi-hop Skip API
  `smart_relay` bridge into `akashnet-2`, enterable from EITHER citizen's own native chain (Franklin via
  Solana/Jupiter, automaton via Base/CCTP), citing PROP-304e's live-confirmed Base-native entry.
- `specs/verification-architecture.md:64` — the corresponding "Purity Boundary Map" row is corrected
  identically (same multi-hop-either-citizen framing, same PROP-304e citation).
- `specs/behavioral-spec.md:1234-1241` (REQ-303's Akash-readiness-gate prose) — a third, incidental
  stale phrase found during the full grep sweep the finding requested ("funding the AKT shortfall itself
  (the Jupiter→Skip-API bridge, REQ-304)") is corrected to "the multi-hop Skip API bridge...
  Jupiter-first-hop if Solana-funded, CCTP-first-hop if Base-funded, per PROP-304e." This was NOT one of
  the two tables FIND-602 explicitly named, but the finding's own instruction to "do a full grep for
  every place these two summary tables are referenced/relied upon" surfaced this third stale copy of the
  same misconception, so it was fixed for the same reason.
- `specs/behavioral-spec.md:100-113` (new changelog section, FIND-602 row) documents all three fixes.

**Full-grep verification performed**: `grep -n "Jupiter\|smart_relay\|funding_route\|multi-hop\|solana/8453\|Base-native\|CCTP"` across both spec files. Confirmed: REQ-304's own body (behavioral-spec.md
~1290-1370) and PROP-304d/PROP-304e (verification-architecture.md ~208-209, 447-459) were already
correct (iteration 6's own fix) and needed no further change; the only stale copies were the two named
summary tables plus the one incidental REQ-303 phrase, all now fixed. No other stale copy was found.

---

## FIND-603 (critical) — second unmodeled resolver input (`env.HOME`)

Fresh full re-read performed: `~/anicca/skills/earn/lib/resolve-identity.mjs` (lines 63-87,
`resolveEvmPrivateKey`) and `~/anicca/runtime/loop/__tests__/resolve-identity.test.mjs` (all 242 lines).
Confirmed the finding's claim exactly: `const e = env || process.env;` then `const legacyHome = e.HOME;`
— the legacy-fallback branch that resolves both citizens' real keys only fires when `legacyHome` equals
`/Users/anicca`, and this value comes from `env.HOME` if an `env` object is passed, or bare ambient
`process.env.HOME` otherwise. Every one of the test suite's 20 cases passes an explicit `env` object with
both `HOME` and (where applicable) `ANICCA_HOME` — none exercises the bare `{home: X}`-only shape the
spec's prior worked examples used.

**What changed and where**:
- `specs/behavioral-spec.md:1717-1785` (`### REQ-403`, EARS clause and "Seed-data correction" paragraph)
  — the EARS clause (~1725-1735) now notes the live comparison is invoked with "an EXPLICITLY-CONSTRUCTED
  `env` object — never ambient `process.env`"; every worked-example invocation of
  `resolveEvmPrivateKey`/`resolveSolanaSecret` in the "Seed-data correction" paragraph is rewritten from
  the bare `{home: X}` shape to the explicit `{home: X, env: {HOME, ANICCA_HOME}}` shape.
- `specs/behavioral-spec.md:1785-1801` — new "**Explicit-env correction (resolves FIND-603 —
  critical):**" paragraph inserted immediately after the "Seed-data correction" paragraph, explaining
  the second unmodeled input, quoting the real source (`const legacyHome = e.HOME`), citing the test
  suite's own 20-case convention, and specifying the binding fix (audit always passes an explicit `env`
  object).
- `specs/behavioral-spec.md:1838-1855` (REQ-403 Acceptance Criteria) — both the "(1)/(2)" bullet and the
  "(resolves FIND-501)" bullet are rewritten to require/demonstrate the explicit-`env` invocation shape;
  the latter bullet is re-tagged `**(resolves FIND-501, corrected resolves FIND-603)**`.
- `specs/behavioral-spec.md:568-696` (REQ-105 body, the paragraph right after the seed JSON array) — one
  more bare-shape occurrence (`resolveEvmPrivateKey({home: '/Users/anicca/.anicca'})`) found during
  consistency-checking was also corrected to the explicit-env shape, with a forward reference to REQ-403's
  Explicit-env correction.
- `specs/verification-architecture.md:236` — **PROP-403b** is corrected: both its Description and
  Tool/Method columns now specify the explicit-`env` invocation shape and cross-reference the new
  PROP-403e; its worked examples are rewritten from bare `{home: X}` to explicit-env form.
- `specs/verification-architecture.md:239` — new proof obligation **PROP-403e** (REQ-403): the live-audit
  invocation must always pass an explicit `env` object, never a bare `{home: X}` call. Tier 0 (structural
  read: every call site passes an explicit `env` object literal) + Tier 2 (integration test simulating a
  stripped/launchd-style minimal `process.env` that omits `HOME`, proving the audit still resolves both
  citizens' real key material because the explicit `env` argument makes it launcher-independent).
- `specs/verification-architecture.md:86-89` (Tier 0 list), `:317` (Tier 2 list), `:527-533` (Gate item
  11) — all updated to wire PROP-403e into the verification strategy and gate.

**A deliberate exception, noted for transparency**: `specs/behavioral-spec.md:95` (the iteration-6
changelog's own historical FIND-501 row) still quotes the OLD bare `{home: X}` shape verbatim, and
`specs/behavioral-spec.md:1792` (inside the new Explicit-env correction paragraph) also quotes the bare
shape verbatim. Both are intentional: line 95 is a preserved historical record of what iteration 6
actually said at the time (this spec's own established convention — every past iteration's changelog
table is kept verbatim as an audit trail, never retroactively rewritten), and line 1792 deliberately
quotes the bad shape as the explicit "this is what NOT to do" example the correction paragraph is
explaining. Neither is a live worked-example instructing an implementer to use the bare shape.

---

## FIND-604 (major) — missing dual-wallet-both-fail fixture

**What changed and where**:
- `specs/behavioral-spec.md:237-393` (`### REQ-101`) — new Edge Case bullet at line 370
  (`**(resolves FIND-604)**`) specifying: both chains failing simultaneously for a dual-wallet citizen
  contributes exactly `0` (composing the existing per-chain-independent fail-closed rule to its
  both-fail limit), never throws, never `NaN`, never double-subtracts `perCitizenReserveUsd`. New
  Acceptance Criteria bullet at line 393 (`**(resolves FIND-604)**`) making this a concrete, testable
  fixture requirement.
- `specs/verification-architecture.md:161` — new proof obligation **PROP-101h** (REQ-101): the
  dual-wallet-both-chains-fail-simultaneously fixture, explicitly distinct from PROP-101f (both succeed)
  and PROP-101g (exactly one fails). Tier 1/2 (unit/integration test).
- `specs/verification-architecture.md:271` (Tier 1 list), `:298` (Tier 2 list), `:393` (Gate item 1d) —
  all updated to reference PROP-101h alongside PROP-101f/g.

---

## Summary of line-range citations (post-edit, both files bumped to iteration 7)

| Finding | behavioral-spec.md | verification-architecture.md |
|---|---|---|
| FIND-601 | 100-112 (changelog), 568 (REQ-105, unchanged seed), 639-654 (citation fix), 737-742 (new AC bullet) | 9 (header), 86-89 (Tier 0), 178 (new PROP-105g), 362 (Gate 1a) |
| FIND-602 | 100-113 (changelog), 225 (purity table row), 1234-1241 (REQ-303 incidental fix) | 64 (Purity Boundary Map row) |
| FIND-603 | 100-114 (changelog), 568-696 (REQ-105 worked example), 1717-1801 (REQ-403 EARS + new Explicit-env correction), 1838-1855 (Acceptance Criteria) | 9 (header), 86-89 (Tier 0), 236 (PROP-403b fix), 239 (new PROP-403e), 317 (Tier 2), 527-533 (Gate 11) |
| FIND-604 | 100-115 (changelog), 370 (new edge case), 393 (new AC bullet) | 161 (new PROP-101h), 271 (Tier 1), 298 (Tier 2), 393 (Gate 1d) |

## Not touched (per instructions)

`state.json`, the iteration-7 review manifest/verdict files, and any git commit/push were left
untouched. No new files were created other than this note.
