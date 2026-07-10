# Verification Report — Sprint 2 (Formal Hardening addendum)

**Feature**: anicca-agent-spawn · **Sprint**: 2 · **Phase**: 5 (Formal Hardening) · **Date**: 2026-07-10
**Verifier**: fresh-context Phase 5 session, invoked directly because `reviews/converge/iteration-1/output/verdict.json`
FAILED — the effectful spawn orchestrator (`spawn-orchestrator.mjs`, `wake-gate.mjs`,
`pending-registry-append.js`, `gen-solana-wallet.sh`) shipped in sprint-2 but never went through Phase 5.
The only pre-existing hardening artifacts (`verification/verification-report.md` etc.) are sprint-1-only
(dated 2026-07-08) and explicitly assert "the effectful spawn ORCHESTRATOR does not exist in this
sprint's diff" — now false. This addendum is scoped exclusively to the 7 required proof obligations
`state.json` still listed `status:"pending"` (PROP-115..121), plus a security/purity/money-safety sweep
of the sprint-2 files. It does **not** re-litigate sprint-1's own 76 already-proved obligations or the
38 already-`skipped` ones — those are untouched.

**Toolchain**: identical to sprint-1 — plain ESM/CJS Node, `node:test` runner, `node --test
'skills/self/spawn/lib/__tests__/**/*.test.mjs' 'skills/self/spawn/lib/__tests__/**/*.test.js'`.

## Summary

| Metric | Count |
|---|---|
| Required proof obligations targeted this pass (were `status:"pending"`) | 7 (PROP-115..121) |
| Proved this pass | **7 / 7** |
| Full sprint-2 target-feature test suite | **206/206 passing** (fresh run this session — `verification/fuzz-results/sprint-2-full-suite-206-run.log`) |
| Security static analysis (sprint-2 files) | Semgrep `--config=auto --config=p/security-audit --config=p/secrets`: **0 findings**, 206 rules, 5 files — `verification/security-results/semgrep-sprint2-raw.json` |
| Purity boundary audit (sprint-2 files) | No drift against `specs/verification-architecture.md`'s declared classifications — see `sprint-2/purity-audit.md` |
| **New finding this pass (not one of the 7 targeted PROPs, not blocking)** | Money-safety-adjacent crash-window gap in `retryPendingRegistryAppends` — see "New finding" section below |

## PROP → verification-architecture.md anchor mapping (exact, per this feature's own naming convention)

`state.json`'s `PROP-11x` IDs are this feature's own sequential proof-obligation numbering; each one's
`artifact` field already points at its true anchor inside `specs/verification-architecture.md`. Restated
explicitly here (a sibling feature failed convergence for mislabeling this exact mapping):

| `state.json` ID | Anchor (verification-architecture.md) | Tier | beadId | REQ |
|---|---|---|---|---|
| PROP-115 | PROP-307a | 0 | BEAD-139 | REQ-307 |
| PROP-116 | PROP-307b | 0 | BEAD-140 | REQ-307 |
| PROP-117 | PROP-307c | 1 (spec row states 1/2, dual-tier) | BEAD-141 | REQ-307 |
| PROP-118 | PROP-307d | 2 | BEAD-142 | REQ-307 |
| PROP-119 | PROP-204d | 1 (spec row states 1/2, dual-tier) | BEAD-152 | REQ-204/REQ-307 |
| PROP-120 | PROP-307f | 0 (spec row states 0/1, dual-tier) | BEAD-153 | REQ-307 |
| PROP-121 | PROP-307e | 1 | BEAD-154 | REQ-307 |

## Results

### PROP-115 → PROP-307a — PROVED

**Claim** (verification-architecture.md line 516): exactly ONE function, `executeSpawnAttempt`, in
exactly ONE new module (`spawn-orchestrator.mjs`), calls REQ-201 through REQ-305's own already-exported
functions/scripts in the canonical order REQ-307 states — no second, competing orchestration entry point
exists anywhere in the diff.

- **Tier 0 structural**: direct read of `~/anicca/skills/self/spawn/lib/spawn-orchestrator.mjs` (776
  lines, read in full this session) confirms exactly one `export async function executeSpawnAttempt`,
  which is the single call-graph root reaching `defaultCheckHomeDistinct` (REQ-203) →
  `defaultGenerateEvmWallet`/`assertRealEvmAddress` (REQ-201) → `defaultPersistChildWallet` (REQ-201c) →
  `defaultSelectCloudTarget`/`selectCloudTargetPure` (REQ-306) → `needsSolanaWallet`/
  `defaultGenerateSolanaWallet` (REQ-202) → `defaultDeploy`/`evaluateAkashFundingGate` (REQ-302/303/304) →
  `defaultSeedChild` (REQ-204 edge case) → `defaultRegisterIdentity`/`ensureAgentId` (REQ-204) →
  `buildChildSpec` (REQ-206) → `defaultWriteMcpConfig` (REQ-205) → `appendChild`/`appendCitizenRecord`
  (REQ-305), entirely inside `withGigLock(lockStatePath, "colony-spawn", runAttempt)` (REQ-103). `grep -rln
  "spawn-decision" skills/self/spawn/` confirms the only remaining references are `run.sh`'s own
  retirement-note comment, `scripts/wake-gate.mjs`'s own retirement-note comment, and `SKILL.md`'s stale
  header (flagged separately below, non-blocking) — `lib/spawn-decision.js` is imported by NO live
  production code path anymore (its only remaining importer is its own pre-existing unit test,
  `spawn-decision.test.js`).
- **Test**: `spawn-orchestrator.test.mjs` — `"PROP-307a structural: spawn-orchestrator.mjs exports exactly
  one executeSpawnAttempt entry point and never references run.sh"` and `"PROP-307a: a real invocation
  calls every one of steps 1-9 (plus round-3's own persistChildWallet/seedChild) exactly once, in the
  canonical order, for a happy-path attempt"` — both re-run fresh this session, both PASS (see
  `verification/fuzz-results/sprint-2-full-suite-206-run.log`).

**Status: proved.** Evidence: `spawn-orchestrator.test.mjs` (existing tests, re-run) + this session's own
structural source read (above), captured in `sprint-2-full-suite-206-run.log`.

### PROP-116 → PROP-307b — PROVED

**Claim** (line 517): `executeSpawnAttempt`'s own function body contains no arithmetic/boolean
eligibility logic and no LLM/prompt reference.

- **Tier 0 structural**: direct read of `executeSpawnAttempt`'s full body (lines 478-747) confirms zero
  relational/arithmetic comparisons against a threshold/surplus/cooldown value — the only conditional
  branches are `if (cloudTarget === "none")`, `if (typeof shelterCostUsd === "number" && ...)` (a
  well-formedness gate on an already-computed value, not an eligibility threshold), `if
  (needsSolanaWallet(...))` (delegates to the already-classified Pure Core function, REQ-202), and
  `if (isSelfFunded(citizenRecord))` (delegates to the already-classified Pure Core gate, REQ-105/P0) —
  none of these compare against `colonySurplusUsd`/`spawnThresholdUsd`/a cooldown window, which remain
  exclusively `decideColonySpawn`'s own concern (called by `executeSpawnAttempt`'s caller,
  `wake-gate.mjs`, BEFORE `executeSpawnAttempt` is ever invoked). No `fetch`/prompt/LLM-client reference
  anywhere in the file.
- **Test**: `"PROP-307b structural: executeSpawnAttempt contains no arithmetic/boolean eligibility
  comparison and no LLM/prompt reference"` — re-run fresh, PASS.

**Status: proved.**

### PROP-117 → PROP-307c — PROVED

**Claim** (line 518): a failure injected at each of the 9 canonical steps is recorded correctly — steps
1-6 via a minimal direct `ledger.js::appendChild` row (never `buildChildSpec`), steps 7-8 via the
`buildChildSpec`-based path, and step 9's own two sub-failure modes (raw ledger-append failure propagates
uncaught with no row; transient citizen-registry-append failure leaves the ledger row `"active"` and
queues a durable retry via `pending-registry-append.js`) — corrected boundary per FIND-S2-001/FIND-019.

- **Tests** (all re-run fresh this session, all PASS): `spawn-orchestrator.test.mjs`'s `"PROP-307c step 1"`
  through `"PROP-307c step 9"` (9 tests, one per canonical step, each asserting the specific recording
  path — steps 1-6 minimal, steps 7-8 `buildChildSpec`-shaped, step 9 the raw-append-uncaught subcase),
  plus `"FIND-003: a transient citizens.json append failure (ENOTDIR) resolves status:\"active\" (never
  rejects), the ledger's active row is still honestly present, and a durable pending-registry-append
  marker is queued"` and `"FIND-003 retry mechanism: retryPendingRegistryAppends detects a queued pending
  append on a subsequent call/wake and completes it once the underlying transient condition has cleared"`
  (step 9's second subcase).
- **Cross-check** (the passThreshold's own "and that `filterProductiveCitizens`/`deriveRecentSpawnAttempts`
  ... correctly treat every resulting row as non-productive/failure" clause): `treasury-gate.test.mjs`'s
  pre-existing `PROP-101d`/`PROP-102f` family (reused unmodified, still passing in the same 206/206 run)
  already proves these two functions correctly classify any `status:"failed"`/`status:"active"` row by
  its own `status`/`active_since` fields regardless of which of the two recording paths produced it — the
  functions have no branch on "which code path wrote this row", only on the row's own content.

**Status: proved.** Evidence: 11 tests total (9 step tests + 2 FIND-003 tests) in
`spawn-orchestrator.test.mjs`, all in `sprint-2-full-suite-206-run.log`.

### PROP-118 → PROP-307d — PROVED

**Claim** (line 519): the `"colony-spawn"` lock is held from before `executeSpawnAttempt`'s step 1 begins
until after step 9 completes (or a failure is ledgered) — never released early.

- **Test**: `"PROP-307d: the colony-spawn lock is held from before step 1 until after step 9 completes --
  a staggered concurrent attempt fails throughout, succeeds only after release"` — an integration test
  against the REAL `executeSpawnAttempt` (steps 2-9 stubbed to fast, real-shaped fixture I/O, per the
  spec's own passThreshold method, reusing PROP-103e's staggered-race technique) — re-run fresh, PASS.
- **Structural corroboration**: `executeSpawnAttempt`'s own body wraps `runAttempt` (which performs all 9
  steps) in a single `await withGigLock(lockStatePath, "colony-spawn", runAttempt)` call — `lock.mjs`'s
  own `withGigLock` (read in full, `~/anicca/skills/economy/gig/lib/lock.mjs`) only releases the lock in
  its own `finally` block, after `fn()` (here, the entire `runAttempt`) resolves or rejects — there is no
  code path inside `runAttempt` that releases or bypasses the lock early.

**Status: proved.**

### PROP-119 → PROP-204d — PROVED

**Claim** (line 474): a real, one-time best-effort RECLAIM of the REQ-204 gas seed fires ONLY at the 3
failure sites reachable after `seedStep` has already succeeded (REQ-204 registration failure, REQ-206
`buildChildSpec` distinct-wallet-assertion throw, REQ-205 mcp.json write failure) — signed by the CHILD's
own in-memory wallet, destined to the driving citizen's wallet, reusing `seed-child.py` UNMODIFIED with
sender/recipient reversed from REQ-204's own forward-direction transfer; the outcome is recorded
ALONGSIDE — never in place of — the triggering failure's own `error` field; NEVER attempted for a failure
before `seedStep` or within `seedStep` itself.

- **Tier 1** (reversed sender/recipient vs. `defaultSeedChild`'s own established fixture pattern): read
  together, two existing unit tests establish this directly —
  `spawn-orchestrator-gas-seed-and-key-persistence.test.mjs`'s `"defaultSeedChild: happy path"` (line 110)
  confirms `defaultSeedChild`'s own pattern: SIGNER = the driving citizen's (parent's) resolved private
  key, DESTINATION = the child's address (`seenArgs.childAddr`); `spawn-orchestrator-reclaim-and-
  shelter-cost.test.mjs`'s `"defaultReclaimSeed: happy path"` (line 73) confirms the reversed pattern:
  SIGNER = the child's own in-memory `evmWallet.privateKey` (`seenFileDuringCall.private_key ===
  CHILD_EVM_WALLET.privateKey`, "the SIGNER must be the child's own key, never the parent's"), DESTINATION
  = `parentWalletAddress` (`seenArgs.destAddr === DRIVING_CITIZEN_WALLET`, "the reclaim's destination must
  be the driving citizen's own wallet, never the child itself") — a genuine, test-asserted reversal, not
  merely a naming coincidence.
- **Tier 2** (the binding integration check): `spawn-orchestrator-reclaim-and-shelter-cost.test.mjs`'s
  `"FIND-001(a)"` (identityStep/step 6 failure after a successful seedStep), `"FIND-001: buildChildSpec's
  own real distinct-wallet assertion (step 8)"`, and `"FIND-001: mcp.json write failure (step 7)"` each
  confirm `deps.reclaimSeed` is invoked exactly once with `{childEvmWallet: <the child's own in-memory
  wallet>, parentWalletAddress: <the driving citizen>, amountUsdc: <the SAME seedUsdc already used>}`, and
  that the resulting ledger row carries `reclaimed`/`reclaimTxHash`/`lease_id` alongside an `error` field
  that is byte-identical to the original triggering error (`FIND-001(a)`'s own assertion: `assert.match(
  rows[0].error, /Registered event could not be decoded/, "the ORIGINAL failure's error must never be
  masked/replaced by the reclaim")`). `"FIND-001(c)"` and `"FIND-001(c) variant"` confirm a reclaim that
  itself fails (`ok:false`) or throws is swallowed into `reclaimed:false`/`reclaimError`, never masking
  the original `error`. `"FIND-001(b): seedStep itself fails"` confirms the negative case: `deps.reclaimSeed`
  is called ZERO times, and the resulting row's own keys are EXACTLY `["attempted_ms","child_id","error",
  "status"]` — no `reclaimed`/`reclaimTxHash`/`reclaimError`/`lease_id` fields at all. Steps 1-5 (before
  `seedStep`) never reach a `runStep` call with an `onFailure` reclaim wrapper at all — confirmed by
  direct source read: only the `identityStep` (step 6), the `buildChildSpec` try/catch (step 8), and the
  `mcpStep` (step 7) construct an `onFailure: async (error) => { ... attemptSeedReclaim ... }` callback;
  every earlier step's `runStep` call omits `onFailure` entirely, defaulting to the plain
  `appendMinimalFailure` path with no reclaim fields.

**Status: proved.** Evidence: `spawn-orchestrator-gas-seed-and-key-persistence.test.mjs` +
`spawn-orchestrator-reclaim-and-shelter-cost.test.mjs`, all re-run fresh, all PASS.

### PROP-120 → PROP-307f — PROVED

**Claim** (line 521): `executeSpawnAttempt`'s own `runStep` helper genuinely `await`s its
`onFailure`/`recordFailure` callback — required so `PROP-204d`'s own reclaim attempt genuinely completes
before the ledger row is written; a structural no-op for every PRE-EXISTING synchronous `onFailure`
caller.

- **Tier 0 structural**: direct read of `runStep` (`spawn-orchestrator.mjs` lines 102-118) confirms both
  call sites — `await recordFailure(error)` (the `catch` branch, line 109) and `await recordFailure(error)`
  (the `requireOk`-failure branch, line 114) — are genuinely `await`ed, not fire-and-forget.
- **Tier 1 regression** (no behavioral drift for a synchronous caller): the SAME `PROP-307c` step 1-5
  tests cited under PROP-117 above exercise `runStep`'s DEFAULT, synchronous `onFailure` path (`const
  recordFailure = onFailure || ((error) => appendMinimalFailure(...))` — a plain, non-`async` function,
  the exact "pre-existing synchronous `onFailure` caller" shape this obligation's own passThreshold
  describes) and confirm the resulting ledger row content/shape is exactly as expected (a minimal
  `{child_id, status:"failed", attempted_ms, error}` row) — `await`ing an already-resolved/synchronous
  return value is, by JS semantics, a microtask-scheduling no-op that changes no OBSERVABLE ledger-row
  content, which these 5 already-passing tests directly confirm holds in practice, not merely in theory.

**Status: proved.** Evidence: direct source read (this session) + `PROP-307c` step 1-5 tests
(`spawn-orchestrator.test.mjs`), re-run fresh, PASS.

### PROP-121 → PROP-307e — PROVED

**Claim** (line 520): `run.sh`'s own PRODUCTION body genuinely calls `decideColonySpawn()` (fed real,
freshly-read values) and, only if `eligible:true`, calls `executeSpawnAttempt()` — the OLD
`lib/spawn-decision.js`-based gate and DO/AgentMail path no longer appear anywhere in `run.sh`'s own
reachable code; `skills/registry.json`'s `self/spawn` entry's `riskNote` cites `decideColonySpawn`, not
`lib/spawn-decision.js`.

- **Structural read of `run.sh`** (read in full this session, 49 lines): confirms the production body is
  now `exec "$NODE" "$SKILL_DIR/scripts/wake-gate.mjs" "$@"` after loading shared instance env — no
  `lib/spawn-decision.js` require/source, no DigitalOcean/AgentMail provisioning code anywhere in the
  file's reachable path (the OLD path is referenced only in a retirement-note comment, lines 23-27,
  explicitly documenting it as RETIRED).
- **Structural read of `scripts/wake-gate.mjs`** (read in full, 208 lines): confirms `runWakeGate` imports
  `decideColonySpawn as decideColonySpawnPure` from `../lib/treasury-gate.mjs` and `executeSpawnAttempt as
  executeSpawnAttemptReal` from `../lib/spawn-orchestrator.mjs`, computes `decisionCore =
  decideColonySpawn({colonySurplusUsd, spawnThresholdUsd, recentSpawnAttempts, nowMs,
  childrenProvisioning})` from freshly-read `filterProductiveCitizens`/`computeColonySurplusUsd`/
  `deriveRecentSpawnAttempts`/`countChildrenProvisioning`/`deriveMeasuredShelterCostUsd` values (never
  hand-assembled), and only calls `executeSpawnAttempt(...)` when `!dryRun && decisionCore.eligible`.
- **Structural read of `skills/registry.json`**'s `self/spawn` entry: `riskNote` field reads "...its own
  decision core (`lib/treasury-gate.mjs::decideColonySpawn`) already gates any real spawn attempt
  (`lib/spawn-orchestrator.mjs::executeSpawnAttempt`)..." — zero occurrences of `spawn-decision` anywhere
  in the entry.
- **Tests**: `"PROP-307e structural: run.sh no longer CALLS the OLD lib/spawn-decision.js gate or
  provisions DigitalOcean/AgentMail directly (outside its own retirement-note comments)"` and `"PROP-307e
  structural: wake-gate.mjs (run.sh's real production body) genuinely calls decideColonySpawn then, if
  eligible, executeSpawnAttempt"` — re-run fresh, PASS.

**Status: proved.**

**Non-blocking doc-drift note**: `skills/self/spawn/SKILL.md` line 22's section header still reads "##
Gate (deterministic — `lib/spawn-decision.js`, node:test-covered)" — stale documentation predating this
sprint's `run.sh` rewrite. This does not affect PROP-307e's own pass condition (which is scoped to
`run.sh`'s code and `skills/registry.json`'s `riskNote`, both correct), but is a genuine documentation gap
worth a follow-up edit; not required to block this obligation or Phase 6.

## New finding this pass (NOT one of the 7 targeted PROPs — reported for honesty, not blocking)

While re-confirming the task's explicit money-safety hard gate "durable registry-append retry does not
double-append", this session found a genuine narrow-window gap: `retryPendingRegistryAppends`
(`spawn-orchestrator.mjs`) performs `await append(entry.citizens_registry_file, entry.citizen_record)`
THEN `resolvePendingRegistryAppend(file, entry.child_id)` as two separate, non-atomic writes. If the
process dies (SIGKILL/OOM/host reboot) between the first write landing and the second, the pending-queue
entry is still `status:"pending"` — the NEXT wake's retry re-appends the SAME citizen record a second
time, since `appendCitizenRecord` has no existing-`id` idempotency guard. Traced to a real consequence:
`treasury-gate.mjs`'s `computePerCitizenSurplusUsd`/`computeColonySurplusUsd` iterate the raw `citizens`
array with no id-dedup (unlike `ledger.js` rows, which ARE deduped last-write-wins before use) — a
duplicated citizen record doubles that citizen's own surplus contribution, inflating the exact value
`decideColonySpawn`'s real-money eligibility check consumes.

Live-reproduced, evidence captured: `verification/proof-harnesses/finding-money-safety-registry-retry-
crash-window.mjs` + `.output.log` — confirms a duplicate `citizens.json` record after simulating the
crash window, and confirms `computeColonySurplusUsd` reports exactly 2x the correct surplus ($70 vs. the
correct $35) for the fixture used.

This is NOT one of PROP-115..121 (none of the 7 targeted obligations name registry-append idempotency
across a crash) and NOT part of sprint-2's own contract obligations (FIND-003's own scope, per
`contracts/sprint-2.md`, was the transient-failure-THEN-successful-retry happy path, never a
crash-mid-retry scenario) — it is reported here as a genuinely new Phase 5 finding, not folded into any
PROP's discharge. **Recommendation**: a future fix should either (a) make `appendCitizenRecord` reject/
skip a record whose `id` already exists in `citizens.json` (idempotent-by-construction), or (b) reorder
`retryPendingRegistryAppends` to write the "resolved" marker via an atomic rename-based primitive BEFORE
the citizens.json append is considered durable-committed (mirroring `lock.mjs`'s own atomic-rename
reclaim discipline). This does not block PROP-115..121 or this Phase 5 pass; it is an open item for
whoever next touches `pending-registry-append.js`/`spawn-orchestrator.mjs`.

## Test evidence

```
cd ~/anicca && node --test 'skills/self/spawn/lib/__tests__/**/*.test.mjs' 'skills/self/spawn/lib/__tests__/**/*.test.js'
# tests 206, pass 206, fail 0, cancelled 0, skipped 0, todo 0
```
Full raw output: `verification/fuzz-results/sprint-2-full-suite-206-run.log`.

New evidence artifacts this pass:
- `verification/security-results/semgrep-sprint2-raw.json` (0 findings, 206 rules, 5 files)
- `verification/proof-harnesses/finding-money-safety-registry-retry-crash-window.mjs` + `.output.log`

## Sprint-2 obligation disposition (unchanged from `contracts/sprint-2.md`, restated for clarity)

This pass targeted exactly the 7 obligations `state.json` still listed `status:"pending"`
(PROP-115..121). It did not re-evaluate sprint-1's 76 already-`proved` obligations or the 38 already-
`skipped` ones (30 sprint-1-deferred + PROP-307e's own siblings + the Tier-3/infra-blocked re-deferrals
`contracts/sprint-2.md` already documents) — those dispositions stand as `contracts/sprint-2.md` and
sprint-1's own `verification-report.md` left them.
