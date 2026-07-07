# Spec Review Verdict — anicca-agent-spawn — iteration 9

**Overall verdict: FAIL**

This is a fresh-context, zero-prior-history adversary pass. Both spec files
(`behavioral-spec.md`, `verification-architecture.md`) were read in full, end to end, and every
real source file cited by the requirements this review focused on was independently re-read from
disk (`resolve-identity.mjs`, `is-self-funded.mjs`, `child-spec.js` + its test, `ledger.js`, plus
`~/.automaton/wallet.json`, `~/.anicca/.automaton/wallet.json` (absent), `~/.blockrun/.automaton/*`,
`~/.blockrun/.solana-session`) to confirm every factual claim rather than trust the prose.

## Verification of the 3 prior (iteration-8) findings

| Finding | Status |
|---|---|
| FIND-701 (critical — un-pinned `COORDINATOR_HOME`) | **Partially resolved.** The code-layer fix (a named `COORDINATOR_HOME` constant exported from the still-not-yet-created `registry-path.mjs`, plus PROP-403f's structural import-identity check) is sound and would genuinely close the hazard *in the Phase-2 implementation*. But the identical hardcoded literal (`HOME: '/Users/anicca'`) the constant exists to eliminate still appears, unexplained, in the spec's own prose in two places PROP-403f's check cannot reach (REQ-105's worked example, and part of REQ-403's own "Seed-data correction" subsection, which textually precedes the `COORDINATOR_HOME` definition). See new **FIND-802**. |
| FIND-702 (major — citation vs. actual computation) | **Partially resolved.** PROP-105g is genuinely rewritten into a real, mechanically-performable re-derivation for the EVM case (`viem::privateKeyToAccount` against `~/.automaton/wallet.json`, independently confirmed to exist on disk with the claimed fields). But this is the *only* tool named anywhere in either spec file, and it is EVM-only — Franklin's own seed record is Solana-only, and REQ-202 makes a Solana wallet the norm for every future Nosana-path spawn. No Solana-equivalent re-derivation method is specified anywhere. See new **FIND-801 (critical)**. |
| FIND-703 (critical — undefined "co-located" notion) | **Genuinely resolved.** `coLocatedWithCoordinator` is threaded consistently through REQ-105/305/403 and the Gate section, with no stale implicit assumption left in REQ-101 or REQ-402. Also independently confirmed (per the manifest's own question) that this field does *not* need a `COORDINATOR_HOME`-style canonical-constant discipline: unlike `HOME`, it is never dynamically sourced from multiple possible ambient inputs — it is always a fixed literal at seed time or a fixed structural constant (`false`) at append time. |

## New findings this iteration

- **FIND-801 (critical, verification_readiness)** — PROP-105g's rewritten mechanical
  re-derivation check names only `viem::privateKeyToAccount` (EVM-only). It is not executable, as
  literally specified, for Franklin's Solana-only registry entry, nor for any future Nosana-path
  spawned child (which REQ-202 mandates get a Solana wallet). No Solana-equivalent cryptographic
  re-derivation method is named anywhere in either spec file.
- **FIND-802 (major, spec_fidelity)** — The exact class of hazard FIND-701 was fixed to eliminate
  (an un-pinned, potentially-hardcoded `HOME` value) recurs in the spec's own worked-example prose:
  REQ-105's own resolution example, and part of REQ-403's "Seed-data correction" subsection (which
  appears *before* `COORDINATOR_HOME` is even defined in reading order), still hardcode the literal
  `/Users/anicca` value with no reference to the new canonical constant.

## Why this is still FAIL

This is the fifth consecutive spec-review iteration (FIND-501 → FIND-601 → FIND-603 → FIND-701/703
→ FIND-801/802) to surface a genuine, critical-or-major defect in the same REQ-101/105/403
wallet-identity area. The defect keeps changing shape rather than closing: this iteration it
shifted from "un-pinned HOME input in code" to "the same un-pinned literal recreated in the spec's
own prose" (FIND-802), and separately from "citation vs. computation" to "a computation method that
does not generalize across the two chains this feature's own citizens actually use" (FIND-801). The
recurring failure class named in this iteration's manifest is not closed.

## Full fresh pass over the rest of the spec

REQ-102/103/104/106/201-206/301-306/401/402 were re-read in full and cross-checked directly against
real, current source (`is-self-funded.mjs`, `child-spec.js`/`child-spec.test.js`, `ledger.js`). No
additional drift was found beyond the two findings above — every other citation (booleans consumed
by `isSelfFunded`, `buildChildSpec`'s real required-field list and `wallet:childWallet` string
field, `ledger.js`'s exact `{readChildren, appendChild}` export surface) matches the real,
on-disk source exactly.
