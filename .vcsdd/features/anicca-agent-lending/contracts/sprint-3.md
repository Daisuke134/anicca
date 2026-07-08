---
status: approved
feature: anicca-agent-lending
sprintNumber: 3
negotiationRound: 0
scope: The autonomous daemon-wake entry point that closes this feature's own reachability gap — REQ-117's new `run.sh` + `scripts/wake-gate.mjs` pair under `~/anicca/skills/economy/lending/` plus a new `economy/lending` entry in `~/anicca/skills/registry.json`'s own `slots` object (`status:"live"`). Sprint-1/sprint-2 already delivered every eligibility/sizing/servicing/orchestration function this sprint calls (`lending-gate.mjs`, `lending-verify.mjs`, `gojo-read.mjs`, `lending-path.mjs`, `lending-orchestrator.mjs::executeLoanIssuanceAttempt`/`executeDefaultDetectionSweep`) — this sprint adds NO new eligibility/sizing/servicing behavior of its own, it only makes those already-correct, already-tested functions genuinely REACHABLE from a real daemon wake for the first time (before this sprint, `~/anicca/skills/registry.json` had no `economy/lending` slot at all, so nothing in the running system could ever originate a real loan, confirmed by direct reading of `runtime/loop/index.mjs`/`prompt.mjs::liveSlotNames`). Files touched (all in `~/anicca`, repo `github.com/Daisuke134/anicca`, branch `main`, commit `ccef6ee480add1f7e3d670fab53a12fbfb07339e`) — see the body's Scope section for the full file list.
criteria:
  - id: CRIT-301
    dimension: structural_integrity
    description: The three new/modified artifacts REQ-117 specifies all exist and are correctly wired per PROP-117a/b — `~/anicca/skills/economy/lending/run.sh` is executable, loads env under `set -a`/`set +a`, and its own final line unconditionally execs `node "$SKILL_DIR/scripts/wake-gate.mjs" "$@"` with no eligibility/sizing/servicing logic of its own; `~/anicca/skills/economy/lending/scripts/wake-gate.mjs` exports `runWakeGate({argv, env, deps})` and is the ONLY production call site anywhere in the repository invoking `executeLoanIssuanceAttempt`/`executeDefaultDetectionSweep`, with `executeRepaymentClaim` invoked from zero production call sites; `~/anicca/skills/registry.json`'s own `slots["economy/lending"]` entry carries `status:"live"`, `dir:"skills/economy/lending"`, `entrypoint:"run.sh"`, and genuinely resolves via the REAL `prompt.mjs::liveSlotNames`/`earn-slot.mjs::earnSkillRelPath`/`index.mjs`'s own path-join chain to that SAME real `run.sh` file.
    weight: 0.2
    passThreshold: A read of `run.sh` confirms its final line is exactly `exec "$NODE" "$SKILL_DIR/scripts/wake-gate.mjs" "$@"` with no relational/threshold comparison anywhere in the file; a repository-wide grep for `executeLoanIssuanceAttempt` and `executeDefaultDetectionSweep` confirms both are imported and called from exactly one production (non-test) file, `scripts/wake-gate.mjs`, and a repository-wide grep for `executeRepaymentClaim` confirms zero production call sites; a read of `registry.json`'s `slots["economy/lending"]` entry confirms `status:"live"`/`dir`/`entrypoint` are exactly as stated, and re-running the PROP-117b structural test (`wake-gate.test.mjs`, "PROP-117b: registry.json's economy/lending slot has status:live...") confirms it passes, matching this sprint's own delivered `git show ccef6ee480add1f7e3d670fab53a12fbfb07339e -- skills/registry.json` diff (11 insertions, exactly the `economy/lending` block, no other slot touched). FAIL if `run.sh` contains any eligibility/sizing/servicing branch, if a second production caller of either orchestrator function exists, if `executeRepaymentClaim` has any production call site, or if the registry entry's `status`/`dir`/`entrypoint` fields diverge.
  - id: CRIT-302
    dimension: spec_fidelity
    description: The production `getCitizen(id)` closure `wake-gate.mjs`'s own `buildDefaultGetCitizen` builds spreads the FULL real citizen registry record and merges a fresh `balanceUsd` on top — `{...citizen, balanceUsd}` — never a hand-enumerated literal field list, per PROP-117c's own final wording and REQ-117 step 6's FIND-1006 root-cause fix (resolving the FIND-1003 → FIND-1004/1005 → FIND-1006 chain: FIND-1003 found `executeLoanIssuanceAttempt`'s real 2-argument `(params, deps={})` signature was never wired with `deps.getCitizen`, crashing with `TypeError: getCitizen is not a function`; FIND-1004/1005's own partial fix merely added `balanceUsd` to a hand-typed field subset and left it incomplete; FIND-1006 found that partial fix still silently omitted `fuel`/`humanDependencies`, reproducing the identical silent `{status:"refused"}` failure mode via whichever field it happened to omit — the delivered fix closes the entire defect CLASS at once via full-record-spread, not a fifth enumerated field).
    weight: 0.25
    passThreshold: A read of `buildDefaultGetCitizen` in `scripts/wake-gate.mjs` confirms its returned closure's final line is exactly `return { ...citizen, balanceUsd };` — a full object-spread of the citizen record read fresh from `readCitizensRegistry(citizensRegistryFile)` on every call, never a literal `{id, wallet, walletAddress, coLocatedWithCoordinator, balanceUsd}` subset or any other hand-enumerated shape; re-running `node --test skills/economy/lending/lib/__tests__/wake-gate.test.mjs` confirms the named test "PROP-117c fixture 3 (resolves FIND-1003/1004/1006): a real two-citizen wake selects the correct pair and executeLoanIssuanceAttempt genuinely returns {status:"active"}, never "refused"" passes, and that this genuinely exercises the REAL, unmodified `executeLoanIssuanceAttempt` (never a mocked stand-in). FAIL if the closure enumerates any field subset instead of spreading the full record, or if the named fixture-3 test fails or is missing.
  - id: CRIT-303
    dimension: structural_integrity
    description: The exit-code divergence from `self/spawn/scripts/wake-gate.mjs`'s own convention (FIND-1001) is deliberate and correctly implemented — `scripts/wake-gate.mjs`'s CLI entrypoint sets `process.exitCode = 1` ONLY from its own top-level `.catch` (a genuine, unexpected in-process error), and deliberately does NOT set it for a `{status:"refused", reason}` return value from `executeLoanIssuanceAttempt`, unlike `self/spawn/scripts/wake-gate.mjs`'s own second `if (result.status !== "active") process.exitCode = 1` site, which this feature's own `scripts/wake-gate.mjs` MUST NOT copy verbatim.
    weight: 0.15
    passThreshold: A read of `scripts/wake-gate.mjs`'s CLI entrypoint (the `if (process.argv[1] && ...)` block) confirms `process.exitCode = 1` is assigned in exactly one place, the `.catch((e) => {...})` handler, and that the `.then((result) => {...})` success handler contains no `result.status !== "active"` (or equivalent) check of any kind; re-running `node --test skills/economy/lending/lib/__tests__/wake-gate-structural.test.mjs` confirms the named test "Corrected (Phase 1c iteration-1, FIND-1001) structural: scripts/wake-gate.mjs's own CLI entrypoint deliberately diverges from self/spawn/scripts/wake-gate.mjs's own exit-code convention -- a refused issuance attempt stays exit 0, never mirrors self/spawn's own `result.status !== "active"` -> exit 1 check" passes. FAIL if a second `process.exitCode` assignment site exists in the success path, or if the named test fails or is missing.
  - id: CRIT-304
    dimension: spec_fidelity
    description: PROP-117d's structural discipline holds — `scripts/wake-gate.mjs`'s own candidate-selection code (`isCandidateCitizen`/`findSelectedPair`) contains no re-implemented eligibility/sizing/kill-switch arithmetic of its own beyond the single, plain `lenderAvailableUsd > 0 && borrowerEligibility.eligible === true` combining `computeLenderAvailableUsd`'s/`isBorrowerEligible`'s own two already-computed, independent outputs, and the file never reads `process.env.ANICCA_ARGS` (or a parsed `$ANICCA_ARGS` value) anywhere in its own candidate-selection or issuance/sweep-invocation code path.
    weight: 0.15
    passThreshold: A structural grep of `scripts/wake-gate.mjs` for `ANICCA_ARGS` finds zero hits; a control-flow read of `findSelectedPair` confirms the ONLY relational comparison against a balance/surplus value is `lenderAvailableUsd > 0`, computed by calling `computeLenderAvailableUsd` unmodified, and the ONLY boolean eligibility check is `borrowerEligibility.eligible === true`, computed by calling `isBorrowerEligible` unmodified — no independent threshold/arithmetic re-derivation of either function's own internal logic exists anywhere in the file; re-running `wake-gate.test.mjs`'s named test "PROP-117d structural: scripts/wake-gate.mjs contains no re-implemented eligibility/sizing/kill-switch arithmetic of its own, and never reads process.env.ANICCA_ARGS" confirms it passes. FAIL if any relational/threshold comparison against a balance/surplus/rate/count value exists outside a call into an already-exported REQ-101/102/107/111/112 function, or if any `ANICCA_ARGS` reference is found.
  - id: CRIT-305
    dimension: verification_readiness
    description: The full target-feature test suite (`skills/economy/lending/lib/__tests__/*.test.mjs`) is genuinely green, independently re-run by the Phase 3 adversary itself — not accepted from the builder's own log — with zero regression against sprint-1's/sprint-2's own already-passing 120 tests.
    weight: 0.25
    passThreshold: Adversary runs `cd ~/anicca && node --test skills/economy/lending/lib/__tests__/*.test.mjs` itself and confirms the process exits 0 with exactly 131/131 passing (0 fail, 0 cancelled, 0 skipped) — 120 pre-existing (sprint-1/sprint-2) plus 11 new this sprint (5 in `wake-gate.test.mjs`, 6 in `wake-gate-structural.test.mjs`). FAIL if the count differs from 131/131, if any test is skipped/todo, or if the adversary does not actually execute the command itself.
---

## Scope

This sprint delivers exactly REQ-117 — the autonomous daemon-wake entry point that closes this
feature's own reachability gap discovered this sprint: sprint-1/sprint-2 already delivered every
eligibility (REQ-101/102/107/111/112), sizing (REQ-104/105/114), servicing (REQ-108/109), and
orchestration (REQ-115/REQ-116's `executeLoanIssuanceAttempt`/`executeRepaymentClaim`/
`executeDefaultDetectionSweep`) function as real, correct, well-tested library code — but, confirmed
this sprint by direct reading of `~/anicca/runtime/loop/index.mjs`/`prompt.mjs::liveSlotNames`,
`~/anicca/skills/registry.json`'s own `slots` object never had an `economy/lending` entry, so the live
autonomous daemon could never pick this slot and nothing in the running system could ever originate a
real loan, independent of every one of those underlying functions already being correct. REQ-117 adds no
new eligibility/sizing/servicing behavior of its own — it wires three new artifacts (`run.sh`,
`scripts/wake-gate.mjs`, a `registry.json` slot entry) that make REQ-115/REQ-116's own already-hardened
functions genuinely reachable and, when a real eligible candidate exists, genuinely invoked.

Files touched (all in `~/anicca`, repo `github.com/Daisuke134/anicca`, branch `main`, delivered in a
single commit `ccef6ee480add1f7e3d670fab53a12fbfb07339e`):
- `skills/economy/lending/run.sh` (new, 32 lines)
- `skills/economy/lending/scripts/wake-gate.mjs` (new, 172 lines)
- `skills/registry.json` (modified, +11 lines — new `slots["economy/lending"]` entry only, no other
  slot touched)
- `skills/economy/lending/lib/__tests__/wake-gate.test.mjs` (new, 271 lines, 5 tests)
- `skills/economy/lending/lib/__tests__/wake-gate-structural.test.mjs` (new, 179 lines, 6 tests)

Phase 2b/2c evidence: `node --test skills/economy/lending/lib/__tests__/*.test.mjs` run this sprint
confirms 131/131 passing (120 pre-existing sprint-1/sprint-2 tests + 11 new this sprint — 5 in
`wake-gate.test.mjs`, 6 in `wake-gate-structural.test.mjs`), zero regressions.

## Known residual scope boundary

`executeRepaymentClaim` (REQ-116) remains permanently unwired from this entry point — this is
deliberate, per REQ-117's own step 8 text, not an oversight: `executeRepaymentClaim` structurally
requires an externally-supplied `{loanId, txHash}` pair, and no borrower-facing repayment-claim
UI/API/skill exists anywhere in this colony as of this sprint (confirmed by this sprint's own research).
Wiring a fabricated `txHash` into this wake-cycle coordinator slot would be structurally forbidden
(REQ-108 never trusts a self-report), and treating this daemon-wake slot as if it were that
not-yet-built external channel would be a real design error. A future increment's own dedicated
borrower-facing entry point — not this wake-cycle coordinator slot — is the correct, not-yet-designed
place to wire a genuine repayment claim.

Separately, and independently of the above: today's real registry (confirmed this sprint by direct
reading) contains exactly ONE self-funded citizen, Franklin, whose own wallet is Solana-only (no
`wallet.evm` entry). This means step 5's own `lenderId !== borrowerId` enumeration can never be
satisfied (only one citizen to choose from) AND, separately and independently, even a hypothetical
second citizen would still need to pass step 4's own `wallet.evm===true` filter, which Franklin itself
cannot. Consequently this slot, though now genuinely `status:"live"` and structurally reachable from a
real daemon wake, is a currently-dormant, honest no-op in production — every real wake enumerates zero
candidate pairs, never invokes `executeLoanIssuanceAttempt`, and only `executeDefaultDetectionSweep`
runs (correctly, unconditionally, once per wake, against a `loans.jsonl` that itself has zero rows to
default). This is NOT a defect: it is the same kind of documented, deliberate, currently-real structural
limitation REQ-107/REQ-112 already establish for their own scope boundaries, now simply observable for
the first time as an actual zero-candidate wake (rather than an unreachable code path). It resolves
itself automatically, with no further code change to this sprint's own delivered files, the moment a
second, EVM-walleted, co-located citizen exists in the registry — e.g. via a future `anicca-agent-spawn`
REQ-301 spawn event giving Franklin's own first child an EVM wallet.
