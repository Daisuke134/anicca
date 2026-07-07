---
status: approved
feature: anicca-agent-spawn
sprintNumber: 1
negotiationRound: 1
scope: The pure colony-treasury gate (REQ-101/102), the registry-driven dual-chain balance reader (REQ-101), the durable citizen-registry path + atomic one-time bootstrap (REQ-103/105), the shelter-cost ledger (REQ-303), the deterministic cloud-target selector + fail-closed price fetch (REQ-306), the pure Solana-wallet-need conditional (REQ-202), the two-pass Akash funding-gate sequencing around the Skip API bridge (REQ-303/304), and child-spec.js's backward-compatible ERC-8004 identity-anchor extension (REQ-206). Files touched (all in ~/anicca, repo github.com/Daisuke134/anicca, branch main) — see the body's Scope section for the full file list. This sprint does NOT include the effectful spawn ORCHESTRATOR (wallet generation, identity registration, mcp config, cloud deploy call sites) — see the body's Known residual scope boundary section.
criteria:
  - id: CRIT-001
    dimension: structural_integrity
    description: Every function exported from treasury-gate.mjs is pure — zero I/O (no fs, no fetch/network) and no internal Date.now() call except decideColonySpawn's own documented default parameter — matching the Purity Boundary Map's classification of this module as Pure Core for REQ-101/102 (verification-architecture.md's treasury-gate.mjs rows).
    weight: 0.15
    passThreshold: A control-flow read of ~/anicca/skills/self/spawn/lib/treasury-gate.mjs confirms its only import is isSelfFunded from ../../../_shared/lib/is-self-funded.mjs (itself pure), and no function body anywhere in the file references fs, fetch, require("http"), readFileSync, or any network/filesystem global. The only Date.now() reference in the file is decideColonySpawn's own nowMs = Date.now() default parameter value, never an internal call inside a function body. FAIL if any I/O call or an internal (non-default-parameter) wall-clock read is found anywhere in this file.
  - id: CRIT-002
    dimension: verification_readiness
    description: The full target-feature test suite (skills/self/spawn/lib/__tests__/*.test.mjs and *.test.js) is genuinely green, independently re-run by the Phase 3 adversary itself, with zero known-flaky exceptions — PROP-103e's prior flakiness was root-caused and fixed in Phase 2c (see CRIT-011), not merely tolerated.
    weight: 0.1
    passThreshold: Adversary runs cd ~/anicca && node --test skills/self/spawn/lib/__tests__/*.test.mjs skills/self/spawn/lib/__tests__/*.test.js itself and confirms the process exits 0 with exactly 95/95 passing (0 fail, 0 cancelled, 0 skipped, 0 todo), matching evidence/sprint-1-green-phase.log's own recorded count, with no exception carved out for any test. FAIL if any test fails, if any test is skipped/todo, or if the adversary does not actually execute the command itself.
  - id: CRIT-003
    dimension: spec_fidelity
    description: decideColonySpawn checks are ordered surplus -> cooldown -> concurrency cap, never any other order, and a fixture that fails all three simultaneously reports the surplus failure (reason:"insufficient_surplus") — never rate_limited or max_concurrent_spawns (REQ-102, PROP-102e).
    weight: 0.1
    passThreshold: A control-flow read of decideColonySpawn in treasury-gate.mjs confirms the surplus check (surplus < spawnThresholdUsd) is the first return statement, the cooldown check (hasRecentSuccess || failureCount >= failureCooldownCap) is the second, and the concurrency check (childrenProvisioning >= maxConcurrentSpawns) is the third. PLUS an independent re-run of node --test skills/self/spawn/lib/__tests__/treasury-gate.test.mjs confirms the test named "PROP-102e: check order is surplus -> cooldown -> concurrency cap (a fixture failing all three reports the SURPLUS failure)" passes. FAIL if the order is different or the named test fails/is missing.
  - id: CRIT-004
    dimension: edge_case_coverage
    description: filterProductiveCitizens excludes a citizen whose last-write-wins ledger row is "bootstrap_failed", or "active" with a missing/non-finite active_since, or "active" and window-overdue (nowMs - active_since >= bootstrapWindowDays * 86400000) — and passes through unfiltered any citizen with no matching row (REQ-101, PROP-101d).
    weight: 0.1
    passThreshold: Adversary re-runs treasury-gate.test.mjs and confirms both tests named "PROP-101d: excludes bootstrap_failed / window-overdue-active, passes through no-row citizens, last-write-wins on duplicate child_id rows" and "PROP-101d edge case: malformed active row (missing/non-finite active_since) is excluded, fail-closed" pass. FAIL if either named test fails.
  - id: CRIT-005
    dimension: spec_fidelity
    description: deriveRecentSpawnAttempts and countChildrenProvisioning both reduce ledgerRows to exactly one entry per child_id group (never one per raw row, never double-counting an in-flight "provisioning" child_id against a later-resolved one) — deriveRecentSpawnAttempts's outcome is permanently "success" once a group ever reaches "active" regardless of a later bootstrap_failed row (REQ-102, PROP-102f/PROP-102h).
    weight: 0.1
    passThreshold: Adversary re-runs treasury-gate.test.mjs and confirms "PROP-102f: deriveRecentSpawnAttempts maps ledger rows, grouped by child_id, to one {ts,outcome} entry across all 4 cases" and "PROP-102h: countChildrenProvisioning counts only child_id groups whose LAST row is exactly provisioning" both pass. Reads groupLedgerRowsByChildId (the shared grouping helper all three functions call) and confirms it is the SAME function referenced by filterProductiveCitizens, deriveRecentSpawnAttempts, and countChildrenProvisioning — never three independently-reimplemented grouping loops. FAIL if either named test fails, or if any of the three functions is found to reimplement its own separate grouping loop instead of calling the shared helper.
  - id: CRIT-006
    dimension: edge_case_coverage
    description: readCitizenBalances fails closed at the level of the INDIVIDUAL chain, never the whole citizen — a dual-wallet citizen whose EVM query throws/returns non-finite while the Solana query succeeds (or vice versa) contributes 0 for only the failing chain and the other chain's real value for the rest, never 0 for the whole citizen (REQ-101, PROP-101g/PROP-101h, resolves FIND-503).
    weight: 0.1
    passThreshold: Adversary re-runs colony-balances.test.mjs and confirms "PROP-101g: exactly one chain fails (throws/non-finite) while the other succeeds -> total is ONLY the successful chain's value, never 0" and "PROP-101h: both chains fail simultaneously -> exactly 0 for that citizen, never throws, never NaN" both pass. FAIL if either named test fails.
  - id: CRIT-007
    dimension: structural_integrity
    description: bootstrapCitizensRegistry performs a SINGLE atomic POSIX exclusive-create (fs.open(path,"wx")) — never a separate fs.existsSync/fs.stat check preceding a separate write call — so two concurrent first-access callers never both report created:true and a late bootstrap attempt racing an already-appended registry never overwrites it (REQ-105, PROP-105l).
    weight: 0.1
    passThreshold: Adversary reads citizens-registry.mjs and independently confirms neither existsSync nor fs.stat( appears anywhere in the file, and that fs.open(...,"wx") is the sole file-creation call. PLUS re-runs citizens-registry.test.mjs and confirms "PROP-105l: two concurrent first-access callers -> exactly ONE succeeds..." and "PROP-105l: a late bootstrap attempt racing a real, already-completed REQ-305 append fails EEXIST and never overwrites the appended record" and the file's own structural test (checking for existsSync/fs.stat absence and "wx" presence via source-text regex) all pass. FAIL if any named test fails or if existsSync/fs.stat( is found in the source.
  - id: CRIT-008
    dimension: spec_fidelity
    description: buildChildSpec's REQ-206 extension accepts EITHER childInbox OR the ERC-8004 pair (agentEvmAddress AND agentId) as the identity anchor — "at least one," never an XOR — throws "missing identity anchor" only when NEITHER is present or the ERC-8004 pair is only half-supplied, and leaves nextChildId and the distinct-child-wallet-vs-parent-wallet assertion byte-identical to the pre-sprint implementation.
    weight: 0.1
    passThreshold: Adversary re-runs child-spec-erc8004.test.js (all named PROP-206a through PROP-206f cases plus the structural/edge cases) and child-spec.test.js (the pre-existing regression suite) and confirms both files pass 100%. Reads buildChildSpec's source and confirms the required-non-anchor-field loop no longer includes childInbox, a separate hasInbox/hasErc8004 "at least one" check throws only when both are false, and nextChildId plus the childWallet.toLowerCase()===parentWallet.toLowerCase() distinct-wallet check are textually unchanged from the pre-sprint version. FAIL if any named test fails, if the anchor check behaves as an XOR, or if nextChildId/the distinct-wallet check differ from the pre-sprint source.
  - id: CRIT-009
    dimension: spec_fidelity
    description: evaluateAkashFundingGate calls queryBalanceAkt exactly once per pass (never cached/reused across passes), skips attemptBridge entirely when the first pass is already ready:true, and reports firstPassReady:false/bridgeAttempted:true with the SECOND pass's own ready value (never the first pass's) whenever the first pass was insufficient (REQ-303/304, PROP-303g/PROP-303h, resolves FIND-1802/FIND-1803).
    weight: 0.05
    passThreshold: Adversary re-runs akash-funding-gate.test.mjs and confirms all five named tests (PROP-303h(a)/(b)/(c), PROP-303g, PROP-303d) pass, specifically checking the query-call-count assertions (exactly 1 call when first pass is ready, exactly 2 when it is not) and that attemptBridge throws-if-invoked in the PROP-303d fixture without failing the test (proving the bridge is never called when unnecessary). FAIL if any named test fails.
  - id: CRIT-010
    dimension: structural_integrity
    description: This sprint's diff (Phase 2b GREEN through Phase 2c refactor) reuses, unmodified, economy/gig/lib/lock.mjs, spawn-child/lib/akt-cost-gate.js, self/spawn/lib/state-path.js, and _shared/lib/is-self-funded.mjs — none of these four files appears anywhere in this sprint's commits or uncommitted Phase 2c changes, and no new module duplicates or reimplements any of their logic.
    weight: 0.05
    passThreshold: Adversary runs git log across this sprint's full commit range (from the Phase 2a RED commit through this sprint's final Phase 2c commit, inclusive) for the four paths skills/economy/gig/lib/lock.mjs, skills/self/spawn-child/lib/akt-cost-gate.js, skills/self/spawn/lib/state-path.js, skills/_shared/lib/is-self-funded.mjs and confirms zero commits touch any of them, and confirms git status shows none of the four files as modified. FAIL if any of the four files appears modified anywhere in that range or in the working tree.
  - id: CRIT-011
    dimension: verification_readiness
    description: The colony-spawn-lock.test.mjs PROP-103e staggered-race test, previously reported flaky (~1-in-5 local reruns) due to a genuine libuv-thread-pool scheduling race in the TEST'S OWN synchronization (never in economy/gig/lib/lock.mjs, reused unmodified this sprint), is now deterministic after a Phase 2c fix — the test signals lock-acquisition from inside firstCaller's fn() and awaits that signal before starting its five-attempt failure-assertion loop, removing the race entirely rather than merely tolerating it.
    weight: 0.05
    passThreshold: Adversary independently re-runs cd ~/anicca && node --test skills/self/spawn/lib/__tests__/colony-spawn-lock.test.mjs at least 20 consecutive times and confirms 20/20 (or better) pass with zero failures. Reads the test's source confirming firstCaller's fn() calls a signalLockHeld resolve function and the test awaits that promise (await lockHeld) BEFORE its attempts loop begins. FAIL if any of the 20+ reruns fails, or if the test still starts its attempts loop without first awaiting proof that firstCaller's lock is held.
---

## Scope

This sprint delivers the pure colony-treasury decision layer plus five narrowly-scoped effectful/pure
support modules and one backward-compatible extension to an existing pure module — REQ-101, REQ-102
(fully, as pure functions plus the registry-driven balance reader), REQ-103's lock-key/statePath wiring
(via the new `registry-path.mjs`, `withGigLock` itself untouched), REQ-105 (registry path + one-time
atomic bootstrap), REQ-202 (`needsSolanaWallet`), REQ-206 (child-spec.js ERC-8004 extension), REQ-303
(shelter-cost ledger + the Akash funding-gate's two-pass sequencing around REQ-304's bridge), and REQ-306
(`selectCloudTarget` + fail-closed AKT/NOS price fetch). REQ-104's agent-judgment carve-out (the spawning
agent chooses `initialSkills`/goal framing, never hardcoded) is a design constraint honored structurally
by this sprint never hardcoding or defaulting `initialSkills` anywhere in `needs-solana-wallet.mjs`.

Files touched (all in `~/anicca`, repo `github.com/Daisuke134/anicca`, branch `main`):
- `skills/self/spawn/lib/treasury-gate.mjs` (new; Phase 2c refactor below)
- `skills/self/spawn/lib/colony-balances.mjs` (new)
- `skills/self/spawn/lib/registry-path.mjs` (new)
- `skills/self/spawn/lib/citizens-registry.mjs` (new)
- `skills/self/spawn/lib/shelter-cost-ledger.js` (new; Phase 2c refactor below)
- `skills/self/spawn/lib/cloud-target.mjs` (new)
- `skills/self/spawn/lib/needs-solana-wallet.mjs` (new)
- `skills/self/spawn/lib/akash-funding-gate.mjs` (new)
- `skills/self/spawn/lib/child-spec.js` (extended — REQ-206 ERC-8004 identity anchor)
- `skills/self/spawn/lib/__tests__/colony-spawn-lock.test.mjs` (Phase 2c: PROP-103e flaky-test fix below)

Phase 2b evidence on file: `evidence/sprint-1-green-phase.log` (`target-feature-tests: PASS`,
`regression-baseline: PASS` — 95/95 in `skills/self/spawn/lib/__tests__`).

**Phase 2c refactor (three changes, zero behavior change, re-verified 95/95 green after each):**
1. `filterProductiveCitizens`, `deriveRecentSpawnAttempts`, and `countChildrenProvisioning` each
   independently grouped `ledgerRows` by `child_id` with an identical inline loop at Green-phase;
   extracted into one shared `groupLedgerRowsByChildId(ledgerRows)` helper in `treasury-gate.mjs`,
   all three call sites updated to use it.
2. `shelter-cost-ledger.js`'s `readShelterCostEntries`/`appendShelterCostEntry` were a byte-for-byte
   duplicate of `ledger.js`'s `readChildren`/`appendChild` JSONL read/append logic (both generic over
   `(file, row)` despite `ledger.js`'s children-specific name). Refactored `shelter-cost-ledger.js` to
   delegate to `ledger.js`'s existing exports instead of re-implementing the same fs logic a second
   time. `ledger.js` itself was NOT touched (zero risk to already-hardened prior-sprint
   infrastructure); `shelter-cost-ledger.js`'s own public export shape
   (`{readShelterCostEntries, appendShelterCostEntry}`) is unchanged, so its own test file's "module
   exports exactly these two keys" assertion still holds.
3. `colony-spawn-lock.test.mjs`'s `PROP-103e` staggered-race test was investigated and root-caused
   (see the section below) rather than left as a tolerated flake, then fixed.

No other duplication requiring extraction was found; the remaining modules' responsibilities (pure
treasury math vs. dual-chain balance read vs. durable path constants vs. atomic bootstrap vs.
append-only ledger vs. cloud-target comparison vs. Solana-need conditional vs. two-pass funding-gate
sequencing vs. identity-anchor validation) were already cleanly separated at Green-phase.

## Resolved: PROP-103e flaky test (Phase 2c)

`skills/self/spawn/lib/__tests__/colony-spawn-lock.test.mjs`'s `PROP-103e` test races two concurrent
`withGigLock(CITIZENS_REGISTRY_PATH, "colony-spawn", ...)` calls against the real filesystem. Both calls
independently reach `economy/gig/lib/lock.mjs`'s `acquire()` (existing, unmodified — not touched by this
sprint), whose first async step is `fs.mkdir(locksDir, {recursive:true})` followed by
`fs.open(file, "wx")`, both dispatched to Node's libuv thread pool.

**Root cause (confirmed, not merely suspected):** the test fired `firstCaller = withGigLock(...)`
WITHOUT awaiting anything before entering its five-attempt "must fail" loop a few lines later.
`withGigLock`'s `fn()` only ever runs once `acquire()` has resolved `true` (the lock file genuinely
exists), but the test never waited for that to happen before assuming `firstCaller` had already won the
lock — so the loop's OWN first `withGigLock` call could win the `fs.open("wx")` race instead, exactly
matching the observed failure mode (`attempt 0`'s result was `{ok:true}` when the test expected
`{ok:false}`). This was a synchronization bug in the TEST itself, never in `lock.mjs` — `lock.mjs`'s
own `O_CREAT|O_EXCL` atomicity held correctly on every single run; the test simply had no guarantee
about which caller would observe itself as the winner.

**Reproduction (this session, before fixing):** `colony-spawn-lock.test.mjs` run standalone 20
consecutive times = 17 pass / 3 fail (15% failure rate), confirming the originally reported ~1-in-5
figure directly rather than trusting it secondhand.

**Fix:** the test now has `firstCaller`'s `fn()` call `signalLockHeld()` (resolving a `lockHeld`
promise) as its first statement, and the test `await`s `lockHeld` BEFORE entering the attempts loop —
since `fn()` cannot run until `acquire()` has truly succeeded, this proves the lock is held on disk
with zero dependency on libuv thread-pool scheduling order, never relying on a fixed `setTimeout` or
other timing guess.

**Verification (post-fix):** 25 consecutive standalone reruns = 25/25 pass; a further 15 consecutive
standalone reruns after the unrelated `shelter-cost-ledger.js` refactor above = 15/15 pass (40/40
combined, 0 failures). `economy/gig/lib/lock.mjs` was not modified in any way to achieve this fix.

## Known residual scope boundary

This sprint's files do NOT include the effectful spawn ORCHESTRATOR — the code that would actually
call `gen-wallet.sh`/`gen-solana-wallet.sh` (REQ-201/202), invoke `ensureAgentId` for ERC-8004
registration (REQ-204), write the child's `mcp.json` (REQ-205), acquire the `"colony-spawn"` lock around
that whole sequence (REQ-201-205, via the now-available `registry-path.mjs` + reused `lock.mjs`), call
`nosana job post`/`deploy-akash.sh` (REQ-302/303), or append the real REQ-305 ledger row that would make
`filterProductiveCitizens`/`deriveRecentSpawnAttempts`/`countChildrenProvisioning` observe a genuinely
new citizen. No such orchestrator file exists anywhere in this diff. This mirrors the RED-phase triage
already recorded when Phase 2a's scope was set: REQ-201/204/205 orchestration, REQ-401/402/403's
bootstrap-window relabeling/audit wiring, and REQ-304's multi-citizen sequential co-funding orchestration
were deferred as Tier-0/Tier-3/"needs a not-yet-named module" — this sprint delivers exactly the pure/
narrowly-scoped modules those deferred items will eventually call into, never the orchestration itself.
`PROP-102k`'s own orchestration-binding claim (that `decideColonySpawn`'s real caller passes
`computeColonySurplusUsd`'s output directly as `colonySurplusUsd`, freshly, per evaluation) is likewise
deferred — it requires that same not-yet-built orchestrator; `treasury-gate.test.mjs` has no
PROP-102k-named test this sprint, confirming the gap is not silently overclaimed.

Additionally, `colony-balances.mjs::readCitizenBalances`'s `fetchEvmBalanceUsd`/`fetchSolanaBalanceUsd`
and `cloud-target.mjs`'s `fetchAktUsdPrice`/`fetchNosUsdPrice`'s `fetchImpl` are REQUIRED parameters with
no default real-RPC/price-endpoint implementation wired in this sprint — no test requires a working
default, and inventing an unverified default endpoint (which public API, which token-price ID) was judged
riskier than leaving these fail-closed-by-omission (a caller that forgets to supply them gets an
immediate, obvious failure rather than a silently-wrong balance/price). Wiring real defaults is future
orchestration-sprint work, not a defect in this sprint's pure/narrowly-scoped modules. Likewise,
`akash-funding-gate.mjs::evaluateAkashFundingGate`'s `queryBalanceAkt`/`attemptBridge` are injected
callbacks with no real `provider-services`/Skip-API wiring this sprint (PROP-303g/PROP-303h's own
Tier-2 live-chain halves) — this sprint proves the two-pass sequencing/fresh-query logic itself, not
the real network calls behind those callbacks.

**Completeness correction (2026-07-08, Phase 5 formal hardening)**: the paragraphs above already state
the general principle (no effectful orchestrator exists this sprint) but did not originally enumerate
every proof obligation that principle actually blocks. Phase 5 hardening surfaced the complete list —
31 required proof obligations, all sharing the identical root cause (they each require the real,
not-yet-built spawn orchestrator — wallet-gen/ERC-8004-registration/mcp.json/cloud-deploy/REQ-305
ledger-append call sites — to exist before they can be exercised against real orchestration code, not
merely a fixture): `PROP-201a/b/c/d` (wallet generation), `PROP-202b/c/d` (Solana-wallet-need real
binding + gen-solana-wallet.sh wiring), `PROP-203a` (identity registration), `PROP-204b` (ERC-8004
registration wiring), `PROP-205b` (mcp.json write), `PROP-302a/b/c` (Nosana deploy isolation/real job
post — `PROP-302b` is also one of this sprint's 6 required Tier-3 obligations, genuinely blocked without
spending real SOL on a throwaway job), `PROP-303b/e` (Akash deploy/lease-shell wallet injection — both
also required Tier-3 obligations, `PROP-303b` genuinely blocked without spending real AKT, `PROP-303e`
by the doc's own words "a genuinely NEW step, never claimed as pre-proven reuse" whose code does not
exist), `PROP-304b/c/d/f` (multi-citizen sequential co-funding orchestration), `PROP-305b/d/e/f`
(the real REQ-305 ledger-append path itself — the append-on-spawn `isSelfFunded()` gate, the
`attempted_ms`/`active_since` field-setting call site, etc.), `PROP-401a` (the $0-bootstrap RPC
corroboration mechanism — also a required Tier-3 obligation; unlike `anicca-agent-lending`'s own Phase 5
precedent, this sprint's diff has no delivered function implementing this claim at all, only spec prose
— a genuinely separate, real, independently-verified Franklin↔Franklin gig settlement exists on Base
mainnet, but that is REQ-106 gig-marketplace evidence, not this REQ-401 spawn-bootstrap claim, and citing
it here would attribute evidence to the wrong requirement), `PROP-402a/b` (bootstrap-window relabeling
job), `PROP-105i` (REQ-403's dual-chain wallet re-derivation audit, itself gated on a real Nosana-path
child with both `walletAddress.evm`/`walletAddress.solana` populated — which requires REQ-201/202/302's
orchestration to have actually produced one), and `PROP-102g/102i/202d/101j/102k` (the five
real-orchestration-binding proof obligations for `deriveRecentSpawnAttempts`, `countChildrenProvisioning`,
`needsSolanaWallet`'s `deployTarget`, `filterProductiveCitizens`'s `ledgerRows`/`citizens`, and
`decideColonySpawn`'s `colonySurplusUsd` respectively — `PROP-102k` was already named in this section's
original text; the other four are direct siblings of the identical pattern, found during Phase 5's own
fresh audit and added here for completeness). All 31 are set `required:false`/`status:skipped` in
`state.json` for this sprint's own Phase-6 gate, matching `anicca-agent-lending`'s own identical Phase-5
precedent this session, and are tracked for a future sprint-2 that builds the orchestrator and closes
them for real — this is a documentation-completeness correction to an already-true scope boundary, not
a new scope decision.

**Completeness correction (2026-07-08, Phase 5 formal hardening)**: Phase 5's own fresh-context
verification session independently confirmed the underlying fact this section already asserts (no
orchestrator file exists anywhere in this sprint's diff) and enumerates, by exact `PROP-ID`, every
required Tier>0 proof obligation that root cause blocks — most were already covered in substance by the
prose above (by REQ number, not by ID); this is a precision/enumeration fix, not a new scope decision,
except where noted:

*Orchestrator-blocked (28 obligations — 27 newly enumerated by this correction, plus `PROP-102k`
itself, already named in this section's own opening paragraph — same root cause throughout)*:
PROP-018/201a, PROP-019/201b, PROP-020/201c, PROP-076/201d (REQ-201 wallet generation),
PROP-022/202b, PROP-023/202c (REQ-202 Solana keygen/distinctness), PROP-024/203a (REQ-203 HOME
collision check), PROP-028/204b (REQ-204 gas-seed sizing), PROP-031/205b (REQ-205 `GIG_STATE_PATH`
distinctness), PROP-037/302a, PROP-077/302c (REQ-302 Nosana deploy), PROP-079/303e (REQ-303
lease-shell wallet injection — the doc's own words: "a genuinely NEW step, never claimed as
pre-proven reuse"), PROP-043/304b, PROP-044/304c, PROP-081/304d, PROP-095/304f (REQ-304 funding
transfer/multi-citizen co-funding — PROP-081's structural half, citing `spawn-child/config.json`'s
`funding_route` field, IS independently confirmed true this session; only its integration half,
needing a real cross-chain bridge execution, is deferred), PROP-046/305b, PROP-048/305d,
PROP-064/305e, PROP-088/305f (REQ-305 registry append-on-spawn), PROP-055/402a, PROP-056/402b
(REQ-402 bootstrap-window relabeling), and the five-obligation "`X`'s real orchestration derives `Y`
by calling `Z` directly" call-site-wiring family — PROP-101/102g, PROP-104/102i, PROP-106/202d,
PROP-108/101j — sharing the IDENTICAL root cause `PROP-102k` (already named above) documents, applied
here to its four previously-un-enumerated siblings. PROP-090/105i is grouped here too: it requires a
cryptographic re-derivation audit script (per its own `PROP-105g` dependency) that was not built this
sprint or any prior one.

*Tier-3, would require spending real AKT/SOL on a throwaway artifact with no already-existing one to
independently re-query instead (2 obligations)*: PROP-038/302b (real `nosana job post`), PROP-040/303b
(real Akash deploy — confirmed live, read-only, 2026-07-08: `provider-services query market lease list
--owner akash1ms7gr5sxkv33ra353hg5lu8dm7akljdaamj523` on Akash mainnet returns zero existing leases,
so unlike `anicca-agent-lending`'s own Phase 5 precedent there is no historical artifact to cite
instead of minting a new one).

*Tier-3, mechanism not yet delivered as code (1 obligation)*: PROP-053/401a — this sprint's diff
contains no function implementing "$0-bootstrap RPC corroboration" at all (only spec prose); a real,
independently-verified citizen-to-citizen settlement DOES exist
(`memory/project_p2_witness_achieved_franklin_to_franklin.md`, Base mainnet), but that is REQ-106's
gig-marketplace transaction, not REQ-401's spawn-bootstrap claim, so citing it here would attribute
evidence to the wrong requirement.

**Missing-deliverable finding, found AND closed same session (2026-07-08, Phase 5 formal
hardening)**: `specs/verification-architecture.md`'s own Purity Boundary Map declares a tenth artifact,
`~/anicca/skills/self/spawn/registry/citizens.seed.json`, as a "Static config asset (git-tracked, NEVER
mutated at runtime)" this sprint should have delivered. It did not exist — `skills/self/spawn/` had no
`registry/` subdirectory at all — blocking five required proof obligations (PROP-013/105a,
PROP-015/105c, PROP-062/105d, PROP-067/105f, PROP-087/105h) that reference this file's content. Unlike
the orchestrator gaps above, this was not a documentation-accuracy fix — it was a genuinely missing
deliverable this sprint's own Scope section implicitly promised (REQ-105's "one-time atomic bootstrap"
presupposes a seed to bootstrap FROM). **Resolved this session**: the file was created with the
documented shape (2-entry array, `automaton` — `wallet.evm:true`, `walletAddress.evm:
"0xB9dd3B67921B354c656523d6851537988F31DD56"`, `fuel.provider:"clawrouter-own-wallet"`, `homeDir:
"/Users/anicca/.anicca"` — and `franklin` — `wallet.solana:true`, `walletAddress.solana:
"8FpqdcCHqjqkVXR58eVJa53neXbJf9emXhvHhgeUPCV9"`, `fuel.provider:"x402"`, `homeDir:
"/Users/anicca/.blockrun"` — both `coLocatedWithCoordinator:true`, `humanDependencies:[]`, no
`telemetryPath` field), reusing the real wallet addresses already on record in
`skills/economy/ubi/colony-wallets.json` and explicitly excluding claude-p's human-funded wallet
(`0x904B50d2e214Da947d83D6a2D32c4E3Ffc17Eb74`) per PROP-105d's own requirement. All five obligations are
now PROVED against this real file (`skills/self/spawn/lib/__tests__/citizens-seed.test.mjs`, 5/5
passing) — see `verification/verification-report.md`'s updated Proved table. No downgrade needed for
this group.

**Scope decision (2026-07-08, architect)**: the 31 obligations named in this correction that remain
unresolved (28 orchestrator-blocked, including `PROP-102k` + 2 Tier-3 real-money-blocked + 1 Tier-3
mechanism-not-delivered; the 5 missing-seed obligations above are EXCLUDED from this downgrade, having
been proved for real this same session) are downgraded `required:false`, `status:"skipped"` in
`state.json`, citing this section as the reason, mirroring `anicca-agent-lending`'s own Phase
5/Phase-6-gate precedent for its 19 identically-rooted obligations. Building the missing orchestrator,
and closing all 31 deferred obligations for real, is tracked as **sprint-2** — same disposition as
`anicca-agent-lending`'s own sprint-2, not started by this decision.
