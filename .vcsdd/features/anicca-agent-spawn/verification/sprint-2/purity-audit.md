# Purity Boundary Audit — Sprint 2 (Formal Hardening addendum)

**Feature**: anicca-agent-spawn · **Sprint**: 2 · **Phase**: 5 · **Date**: 2026-07-10

Scope: the 4 sprint-2 files this Phase 5 pass hardens, plus their real production call site
(`run.sh` → `wake-gate.mjs`).

## Declared Boundaries

Per `specs/verification-architecture.md`'s "Purity Boundary Map (file/function level)" (§232):

| Module/function | Declared classification | Declared basis |
|---|---|---|
| `spawn-orchestrator.mjs::executeSpawnAttempt` | **Effectful Shell (new, sprint-2 — resolves FIND-2001)** | "The single, previously-unnamed binding function that calls REQ-201 through REQ-305's already-specified steps in the canonical order REQ-307 states, entirely inside REQ-103's `colony-spawn` lock. Itself contains zero decision/judgment logic (REQ-104's discipline, extended) — pure sequencing + error propagation over the already-classified rows above; every value it passes between steps is one of those rows' own already-specified outputs, never re-derived." |
| `gen-solana-wallet.sh` | **Effectful Shell (new)** | "Ed25519/Solana-shaped analog of `gen-wallet.sh`; real entropy, same 600-perm/never-logged discipline. REQ-202." |
| `run.sh`'s gate-then-provision body | **Effectful Shell (rewritten, sprint-2 contract-review round 2 — resolves FIND-004)** | "`run.sh`'s own gate-then-provision body, calling `decideColonySpawn()` (REQ-102) then, if eligible, `executeSpawnAttempt()` (REQ-307)." |
| `pending-registry-append.js` | **Not given its own dedicated Map row** — named only in prose, at the traceability matrix's (8b) entry ("...a transient citizen-registry-append failure correctly leaves the ledger row `active` and is retried via `pending-registry-append.js`, per REQ-305's own pre-existing Edge Case text") and inside PROP-307c's own row text. | The Purity Boundary Map's own last edit predates this module (it was added later, during contract-review round 8/9's FIND-003 fix cycle) — a genuine documentation gap this audit flags below, not a code-drift finding. |
| `wake-gate.mjs` | **Not given its own dedicated Map row either** — folded into the `run.sh` row above ("`run.sh`'s own gate-then-provision body"), since `wake-gate.mjs` is the file `run.sh` now `exec`s into (per REQ-307's "wake-cycle scheduler's real identity" correction and `contracts/sprint-2.md`'s "Round 2 additions" paragraph). | Same source. |

## Observed Boundaries

Confirmed by direct, full-file source read this session (fresh context):

- **`spawn-orchestrator.mjs::executeSpawnAttempt`**: confirmed **Effectful Shell, matches declared
  exactly**. Zero decision/judgment logic (see `verification-report.md`'s PROP-116/PROP-307b analysis —
  no threshold/surplus/cooldown comparison anywhere in the function). Every value passed between steps
  (`evmWallet`, `cloudTarget`, `solanaWallet`, `leaseId`/`shelterCostUsd`, `identityResult.agentId`,
  `spec`) is the direct, unmodified return value of the prior step's own already-classified function —
  confirmed by reading each assignment site; none is re-derived, hardcoded, or independently recomputed.
  The module's OWN internal helper functions (`defaultCheckHomeDistinct`, `defaultGenerateEvmWallet`,
  `defaultPersistChildWallet`, `defaultSelectCloudTarget`, `defaultQueryAktBalance`,
  `defaultAttemptAktBridge`, `defaultDeploy`, `defaultRunSeedChild`, `defaultSeedChild`,
  `defaultReclaimSeed`, `defaultRegisterIdentity`, `defaultWriteMcpConfig`, `appendCitizenRecord`) are
  each individually effectful (real `execFileSync`/`fs`/`fsp` calls) — this is EXPECTED and matches the
  declared row's own description ("pure sequencing... over the already-classified rows above"): the
  SEQUENCING function (`executeSpawnAttempt`) is the thing classified Effectful Shell as a WHOLE (it
  orchestrates real effects), not a claim that its constituent steps are individually pure. Two newly
  exported pure helper functions this sprint adds, `assertRealEvmAddress` and
  `shelterCostUsdFromSettledPrice`, ARE individually pure (zero I/O, deterministic given their arguments)
  — confirmed by direct read; neither is claimed otherwise anywhere.
- **`gen-solana-wallet.sh`**: confirmed **Effectful Shell, matches declared exactly**. Real entropy via
  `solana-keygen new` (no `--no-*` flag disables the underlying CSPRNG), stdout-only output (caller MUST
  redirect, per its own header comment), same 600-perm-caller-redirect/never-logged discipline
  `gen-wallet.sh` already establishes — confirmed by direct read of both scripts side-by-side. No
  hardcoded/cached keypair (`--force` overwrites any existing temp file, `mktemp` generates a fresh one
  per invocation, `trap 'rm -f "$KEYPAIR_FILE"' EXIT` cleans it up).
- **`run.sh` + `wake-gate.mjs` (the "run.sh's own gate-then-provision body" declared row)**: confirmed
  **Effectful Shell, matches declared exactly**. `run.sh`'s only remaining logic is env-loading + a single
  `exec node wake-gate.mjs "$@"` handoff — no decision logic of its own. `wake-gate.mjs::runWakeGate`
  itself contains real I/O (`fs.readFileSync`/`ensureCitizensRegistry`/`readChildren`/`readShelterCostEntries`/
  `fetch` calls to Solana RPC and Coinbase) feeding PURE decision functions (`filterProductiveCitizens`,
  `computeColonySurplusUsd`, `deriveRecentSpawnAttempts`, `countChildrenProvisioning`,
  `deriveMeasuredShelterCostUsd`, `decideColonySpawn` — all reused unmodified from sprint-1, all still
  Pure Core per the unchanged declared row for `treasury-gate.mjs`) — confirmed by direct read that
  `runWakeGate` itself performs no threshold/eligibility arithmetic of its own; it only calls
  `decideColonySpawn` and branches on its `eligible` boolean return value. This matches REQ-307/REQ-104's
  own "bookkeeping-only" discipline, extended to this caller as the doc's own PROP-307e/traceability-
  matrix (8b) entry requires.

## Documentation gap (not a purity-boundary drift)

`pending-registry-append.js` and `wake-gate.mjs` are each named in prose (the traceability matrix's (8b)
entry, `contracts/sprint-2.md`'s "Round 2 additions"/FIND-003 correction paragraphs) but neither has its
OWN dedicated row in the `## Purity Boundary Map (file/function level)` table — `wake-gate.mjs`'s
classification is reasonably inferable by folding it into the pre-existing `run.sh` row (both files are
one production call chain, and the audit above confirms the fold is accurate), but `pending-registry-
append.js` has no equivalent fold-in anywhere in the table. Independently classified by this audit's own
direct source read: **Effectful Shell** — `readPendingRegistryAppends`/`queuePendingRegistryAppend`/
`resolvePendingRegistryAppend` are thin delegations to `ledger.js`'s own `readChildren`/`appendChild`
primitives (confirmed: `const { readChildren, appendChild } = require("./ledger.js")`, no re-implemented
`fs` logic of its own — matches `shelter-cost-ledger.js`'s own established "reuse, never reimplement"
convention, cited approvingly elsewhere in this same Map). `deriveOutstandingRegistryAppends` is **Pure
Core** — zero I/O, a deterministic last-row-wins reduction over an already-given `rows` array (confirmed
by direct read and by `pending-registry-append.test.js`'s own 5 passing unit tests, which exercise this
exact function with no I/O mocking required). This is a Map-table completeness gap, not a code drift —
the actual code's real classification is unambiguous and matches the "reuse ledger.js primitives, never
reimplement" pattern the doc already establishes for its sibling module. **Recommended follow-up (non-
blocking)**: add explicit `pending-registry-append.js` and `wake-gate.mjs` rows to the Purity Boundary Map
the next time `specs/verification-architecture.md` is touched.

## Summary

**No purity-boundary drift detected** in any of the 4 sprint-2 files this pass hardens, nor in their real
production call site (`run.sh`/`wake-gate.mjs`) — every module's observed core/shell classification
matches (or, for the two undocumented-but-inferable modules, is consistent with) `specs/verification-
architecture.md`'s declared Purity Boundary Map. No hidden side effects were found in any function
classified/expected as pure (`assertRealEvmAddress`, `shelterCostUsdFromSettledPrice`,
`deriveOutstandingRegistryAppends`, `needsSolanaWallet`/`selectCloudTarget` reused unmodified from
sprint-1) — each was independently re-read this session and contains zero `fs`/`fetch`/subprocess calls.
No verifier-hostile coupling was found (every effectful call site in `executeSpawnAttempt` goes through
the established `deps`-or-default injection seam, matching sprint-1's own already-certified testing
discipline).

**One documentation gap, not a code defect**: `pending-registry-append.js`/`wake-gate.mjs` lack their own
dedicated Purity Boundary Map rows (see above) — flagged as a follow-up for whoever next edits
`specs/verification-architecture.md`, not a blocker for this Phase 5 pass or for Phase 6.

**No required follow-up before Phase 6 on purity grounds.** The one genuine open item from this pass (the
registry-append-retry non-atomicity — see `verification-report.md`'s "New finding" and `security-report.md`)
is a money-safety/atomicity concern in already-correctly-classified Effectful Shell code, not a
core/shell misclassification.
