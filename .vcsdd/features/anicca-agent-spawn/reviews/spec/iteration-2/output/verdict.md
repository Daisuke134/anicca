# Spec Review — anicca-agent-spawn — iteration 2 — FAIL

Fresh-context adversary pass. Iteration 1's 6 findings (FIND-001..006) were independently re-verified
against the real, current source files each cites (not accepted from the revision's own claims) and are
confirmed genuinely resolved:

| Finding | Status |
|---|---|
| FIND-001 (child-spec.js unmodified-reuse contradiction) | Resolved by REQ-206 -- a real, substantive validation-extension spec, correctly scoped as not-yet-implemented (Phase 1c). |
| FIND-002 (no dynamic citizen registry) | Resolved by REQ-105/REQ-305 -- a real schema + append-on-spawn design, BUT see FIND-101 below: the design does not address a live hazard in the exact file it repurposes. |
| FIND-003 (multi-host lock/ledger) | Resolved by REQ-106 -- correctly scopes this increment to one coordinator host, BUT see FIND-103 below: the lock-reuse plan itself has a new, unaddressed gap. |
| FIND-004 (reinvented ensure-agent-id logic) | Resolved -- REQ-204's citation of `ensureAgentId`'s cache/verify/register-once wrapper matches the real module (`ensure-agent-id.mjs`) and its test suite exactly. |
| FIND-005 (wrong citation) | Resolved -- citation corrected. |
| FIND-006 (unspecified cloud-target selection) | Resolved by REQ-306 -- a real, deterministic, bookkeeping-only comparison function, consistent with REQ-104's discipline. |

## New findings this iteration

### FIND-101 (critical, spec_fidelity + verification_readiness, category: security_surface)
`colony-wallets.json`'s current 2nd entry (`0x904B50d2e214Da947d83D6a2D32c4E3Ffc17Eb74`) is **claude-p's
own human-funded wallet** -- confirmed via this project's own canonical wallet ledger
(`docs/WALLETS.md`, lines 49-62: "claude-p is the exception: its real funds sit in the Polymarket
deposit wallet 0x904B50d2e214Da947d83D6a2D32c4E3Ffc17Eb74"). REQ-105/REQ-305 repurpose this exact file
from its current role (a recipient-eligibility list for mutual aid, per `ubi.js`'s own JSDoc) into THE
registry REQ-101 aggregates surplus from to gate autonomous spawn funding -- without ever noticing or
addressing that one of the 3 entries being migrated is the very human-funded wallet the feature's own
stated HARD invariant exists to keep out. PROP-105c's proof method ("compare against today's known-good
identities") is incoherent as written: the current bare-address file carries no fuel/humanDependencies
data, so there is no derivable "known-good verdict" for entry #2 without out-of-band knowledge this spec
never states or tests.

### FIND-102 (major, spec_fidelity, category: requirement_mismatch)
REQ-206's own EARS clause ("requiring at least ONE of these two anchors, never both, and never
neither") directly contradicts its own edge case two paragraphs later ("Both `childInbox` AND the
ERC-8004 pair are present simultaneously ... SHALL accept this without error -- 'at least one' is a
minimum, not an exclusive-or"). No acceptance criterion or PROP (PROP-206a/b/c/d) tests the both-present
path at all, so a fully-PROP-compliant Phase 3 implementation could still implement the literal (wrong)
XOR reading.

### FIND-103 (major, verification_readiness, category: requirement_mismatch)
REQ-103 claims reuse of `lock.mjs`'s `withGigLock` "under a new lock key" only, but the real function
signature is `withGigLock(statePath, lockKey, fn, opts)` -- the lock file's actual identity depends on
BOTH `statePath` and `lockKey`. REQ-103 never specifies what `statePath` anchors the colony-spawn lock;
two call sites picking different `statePath` values would silently acquire two different lock files,
defeating REQ-103's entire mutual-exclusion purpose despite every other part of the reused mechanism
being correctly inherited.

### FIND-104 (medium, spec_fidelity, category: spec_gap)
REQ-105 claims the new registry shape carries "EXACTLY" the fields `isSelfFunded()` "already require,"
specifying `wallet: {evm?: string, solana?: string}` -- but `is-self-funded.mjs`'s own JSDoc and
implementation type/treat this field as boolean presence-flags, not addresses. Functionally compatible
only via JS truthiness coercion; the mismatch between this and REQ-305's need for the same field to
carry a real address value is never reconciled.

## Verdict

`spec_fidelity`: FAIL. `verification_readiness`: FAIL. **overallVerdict: FAIL.**
