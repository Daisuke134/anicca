# Spec Review Verdict — anicca-agent-spawn — Iteration 3

**Overall verdict: FAIL**

## Prior iteration's 4 findings: all genuinely resolved (verified against real source, not spec claims)

| Finding | Status | How verified fresh |
|---|---|---|
| FIND-101 (colony-wallets.json repurposing) | RESOLVED | Re-read `/Users/anicca/anicca/skills/economy/ubi/colony-wallets.json` directly: still the original 3-entry bare-address array, 2nd entry still `0x904B50d2e214Da947d83D6a2D32c4E3Ffc17Eb74` (claude-p, confirmed human-funded per `docs/WALLETS.md` lines 53-54/61-62, still accurate). `citizens.json` is a genuinely new, separate path; zero shared state anywhere in either spec file. |
| FIND-102 (REQ-206 EARS/edge-case contradiction) | RESOLVED | REQ-206's "at least one, not XOR" rewrite is internally consistent with its own edge cases and new PROP-206e. |
| FIND-103 (mismatched statePath) | RESOLVED | Re-read `/Users/anicca/anicca/skills/economy/gig/lib/lock.mjs` (`lockPaths`, `withGigLock`): real signature and lock-file derivation exactly match REQ-103's canonical-`CITIZENS_REGISTRY_PATH` claim, and REQ-103's own text explicitly extends the requirement to REQ-101/105/305's own reads/writes. |
| FIND-104 (wallet type mismatch) | RESOLVED | Re-read `/Users/anicca/anicca/skills/_shared/lib/is-self-funded.mjs` (`hasOwnWallet`): `Boolean(wallet.evm)\|\|Boolean(wallet.solana)` exactly matches REQ-105's boolean `wallet`/string `walletAddress` split. Both seeded citizens.json entries independently re-verified to pass `isSelfFunded()` against the real gate logic. |

## New defects found on this iteration's full fresh pass (6, two critical)

1. **FIND-201 (critical, spec_fidelity)** — REQ-105's now-exact citizen registry schema has no field for `active_since` or a bootstrap-failure/productivity status, yet REQ-402's Acceptance Criteria and PROP-402c require reading exactly these facts "from REQ-105's registry, no second citizen list" — while REQ-402's own EARS clause places the same fact "in the ledger" instead. No join/enrichment step between ledger.js and citizens.json is specified anywhere.
2. **FIND-202 (major, spec_fidelity)** — REQ-403's audit script is required to obtain each instance's `HOME` value "read from REQ-105's colony citizen registry," but the registry schema has no `HOME`/`ANICCA_HOME` field — only a `telemetryPath` template string containing a literal, unresolved `$HOME` placeholder.
3. **FIND-203 (major, spec_fidelity)** — REQ-402 promises to feed a `children_bootstrap_failed` count into REQ-102's "next gate evaluation," but REQ-102's fully-pinned pure-function signature/return-type/edge-cases never accept or define any effect for such a value.
4. **FIND-204 (critical, spec_fidelity)** — Fresh read of the real `child-spec.js::buildChildSpec` (and its existing test suite) confirms it still unconditionally requires `parentWallet`, `generation`, `seedUsdc`, and `constitutionHash` — none of which REQ-201-306 ever specify a value or derivation rule for, directly contradicting REQ-206/PROP-206d's claim that the modification is "limited to" identity-anchor validation. REQ-304's own multi-citizen co-funding design (no single "parent") makes `parentWallet` doubly unspecified.
5. **FIND-205 (medium, verification_readiness)** — `telemetryPath`'s literal, unresolved `$HOME` placeholder has no specified resolution mechanism/owner.
6. **FIND-206 (low, spec_fidelity)** — REQ-101 retains a vestigial "claude-p appears in the telemetry directory listing" edge case that describes a code path the registry-only design (REQ-105) makes unreachable, risking a Phase 3 implementer reintroducing directory-scan enumeration.

## Dimension verdicts

| Dimension | Verdict | Findings |
|---|---|---|
| spec_fidelity | FAIL | FIND-201, FIND-202, FIND-203, FIND-204, FIND-206 |
| verification_readiness | FAIL | FIND-201, FIND-202, FIND-203, FIND-205 |

This spec does not pass. FIND-201 and FIND-204 are both critical and both block Phase 2 (TDD): FIND-201 leaves REQ-101/402's core treasury-gate aggregation unimplementable as literally specified, and FIND-204 leaves REQ-305's ledger-append (the completion criterion for every successful spawn) unimplementable without inventing four unspecified values.
