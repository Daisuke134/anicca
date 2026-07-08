---
status: approved
feature: anicca-agent-spawn
sprintNumber: 2
negotiationRound: 2
scope: The effectful spawn ORCHESTRATOR — the code that actually wires sprint-1's pure/narrow modules
  (treasury-gate.mjs, colony-balances.mjs, registry-path.mjs, citizens-registry.mjs, child-spec.js's
  REQ-206 extension, shelter-cost-ledger.js, cloud-target.mjs, needs-solana-wallet.mjs,
  akash-funding-gate.mjs) into a single, real, runnable spawn flow. This sprint delivers REQ-307 (new,
  the previously-unnamed orchestrator entry-point function this sprint's own Phase 1a/1b work added to
  behavioral-spec.md) plus real call-site implementations for REQ-201/202/204/205/302/303/305 — the
  wallet-generation, ERC-8004-registration, mcp.json-write, cloud-deploy, and ledger/registry-append
  call sites contracts/sprint-1.md's own "Known residual scope boundary" section named as not yet
  built. REQ-201/202/203/204/205/206/301/302/303/304/305/306/401/402/403 do NOT get new behavioral
  content in this sprint beyond REQ-307 and two small, additive edge-case corrections (FIND-2001,
  FIND-2002) — they were already fully specified, EARS-clause-through-acceptance-criteria, before this
  sprint began (see the "Pre-existing spec confirmation" section below for the citation-by-citation
  proof of this claim). This sprint's own Phase 1a/1b work is this contract plus REQ-307/PROP-307a-d —
  not a rewrite of any REQ-2xx/3xx/4xx.
criteria:
  - id: CRIT-201
    dimension: structural_integrity
    description: Exactly one function, `executeSpawnAttempt`, in exactly one new module (`~/anicca/skills/self/spawn/lib/spawn-orchestrator.mjs`), calls REQ-201 through REQ-305's own already-exported functions/scripts in the canonical order REQ-307 states — no second, competing orchestration entry point exists anywhere in the diff. Per REQ-307's own step 7/8 construction-order clarification (resolves contract-review round-1 FIND-001), step 8's `buildChildSpec` call — a PURE, zero-side-effect construction — MAY run ahead of step 7's own effectful `mcp.json` write, since only step 7's own effectful call, never step 8's in-memory construction, is subject to "canonical order" for this criterion's purposes. Per REQ-307's own "wake-cycle scheduler's real identity" correction (resolves contract-review round-2 FIND-004), `~/anicca/skills/self/spawn/run.sh` — the LIVE `self/spawn` slot entry point, previously wrongly assumed superseded/untouched — MUST be rewritten this sprint to call `decideColonySpawn()` then, if eligible, `executeSpawnAttempt()`, retiring the OLD `lib/spawn-decision.js`-based gate and DO/AgentMail path.
    weight: 0.15
    passThreshold: A control-flow read of `spawn-orchestrator.mjs` confirms a single call-graph root reaching every one of REQ-201/202/203/204/205/206/301/302/303/304/305/306's own exported functions/scripts, and that every EFFECTFUL call (REQ-201/202/203/204/205/302/303/306/305) fires in the order REQ-307's own "Canonical call order" states. A SEPARATE control-flow read of `run.sh`'s current production body confirms it calls `decideColonySpawn()` then, if eligible, `executeSpawnAttempt()`, and that the OLD `lib/spawn-decision.js`/DO/AgentMail path no longer appears anywhere in its reachable code (PROP-307e). FAIL if a second orchestration path exists, if any EFFECTFUL step fires out of order or is skipped/duplicated, or if `run.sh` still calls the OLD gate — NOT if step 8's own zero-side-effect `buildChildSpec` construction happens ahead of step 7's effectful call (this is required by REQ-307's own Edge Cases, see the step 7/8 clarification).
  - id: CRIT-202
    dimension: structural_integrity
    description: `executeSpawnAttempt` itself contains no decision/judgment logic — no arithmetic/boolean eligibility comparison and no LLM/prompt reference — mirroring REQ-104's bookkeeping-only discipline, extended by REQ-307 to this new function (PROP-307b).
    weight: 0.1
    passThreshold: Structural grep of `spawn-orchestrator.mjs` finds no relational/threshold comparison and no prompt/LLM-client reference. FAIL if either is found.
  - id: CRIT-203
    dimension: edge_case_coverage
    description: A failure injected at each of REQ-307's 9 canonical steps in turn is recorded correctly — steps 1-6 (before a complete identity anchor exists, since step 6/REQ-204 is itself the step that produces the anchor's agentId half) append a minimal `{child_id, status:"failed", attempted_ms, error}` row directly via `ledger.js::appendChild`, never via `buildChildSpec`; steps 7-9 use the existing `buildChildSpec`-based REQ-305 path, requiring step 6 to have genuinely succeeded first; no row anywhere ever claims `status:"active"` for a failed attempt (PROP-307c, resolves FIND-2002; boundary corrected per FIND-S2-001/FIND-S2-101 — NOT the disproven "steps 1-5/6-9" split).
    weight: 0.15
    passThreshold: An integration test triggering a failure at each of the 9 steps against a real `ledger.js` file confirms the above, AND confirms `filterProductiveCitizens`/`deriveRecentSpawnAttempts` (REQ-101/102, sprint-1, unmodified) correctly treat every resulting row as non-productive/failure regardless of which recording path produced it. FAIL if any step's failure produces no row, a wrongly-shaped row, or a row misread by the sprint-1 aggregation functions.
  - id: CRIT-204
    dimension: structural_integrity
    description: The `"colony-spawn"` lock (REQ-103, sprint-1, unmodified) is held from before `executeSpawnAttempt`'s step 1 begins until after step 9 completes or a failure is ledgered — never released any earlier (PROP-307d).
    weight: 0.1
    passThreshold: Integration test reusing PROP-103e's own staggered-race method against the REAL `executeSpawnAttempt` (steps 2-9 stubbed to fast, real-shaped fixture I/O) confirms the lock's real scope over this actual function matches REQ-103's already-specified critical section. FAIL if any staggered attempt during the delay window succeeds.
  - id: CRIT-205
    dimension: verification_readiness
    description: (Revised, contract-review round 1, resolves FIND-002; count revised round 2, resolves FIND-003/FIND-005; count revised again round 4, resolves FIND-009 — re-scoped to be genuinely evaluable AT THIS gate, before Phase 3/5 run; final closure of the 30 obligations remains independently enforced by vcsdd-harden's own standard "all required obligations proved" gate before Phase 6, this criterion does not weaken that.) Every one of the 30 non-Tier-3 obligations this sprint targets (see "Deferred-obligation disposition" below) has a genuinely exercisable proof path in the CURRENT implementation — the real function/call site each obligation's own verification method names (a control-flow read location, an integration-test injection point) actually exists in `spawn-orchestrator.mjs`/`gen-solana-wallet.sh`/`run.sh` as written, so nothing in the current code makes any of the 30 structurally unprovable.
    weight: 0.2
    passThreshold: For each of the 30 targeted PROP IDs (including PROP-307e), a read of its own verification method (in verification-architecture.md) against the current `spawn-orchestrator.mjs`/`gen-solana-wallet.sh`/`run.sh` source confirms the named call site/function genuinely exists and is reachable — e.g. PROP-202d's `deployTarget`-fed Solana keygen call site, PROP-307c's per-step failure-recording branches, PROP-105i's real citizen-registry append, PROP-307e's `run.sh` wiring. FAIL if any of the 30 names a call site that does not exist in the current implementation, is unreachable, or is a stub/placeholder — NOT if a PROP is simply not yet promoted to `status:"proved"` in state.json (that promotion is Phase 3/5's own job, independently gated by vcsdd-harden before Phase 6).
  - id: CRIT-206
    dimension: spec_fidelity
    description: The 3 Tier-3 real-money obligations (PROP-302b, PROP-303b, PROP-401a) are NOT claimed proved via a fixture/simulated deploy or a borrowed/historical artifact from a DIFFERENT feature (e.g. `anicca-agent-lending`'s own prior Akash lease) — each requires either a genuinely NEW real spend this sprint, or an explicit, honest re-deferral to a dedicated future checkpoint (this project's own task #28, "P3実deploy検証チェックポイント(Phase5)").
    weight: 0.1
    passThreshold: A read of whichever artifact/evidence file claims these 3 PROPs proved confirms a genuinely fresh on-chain transaction/job ID minted THIS sprint (not a citation of 2026-07-08's read-only "zero existing leases" query from sprint-1's own contract, and not `anicca-agent-lending`'s own historical artifact) — OR the contract explicitly re-defers them, citing this section. FAIL if either is claimed proved via a stale/borrowed/simulated artifact.
  - id: CRIT-207
    dimension: implementation_correctness
    description: `~/anicca/skills/self/spawn/scripts/gen-solana-wallet.sh` (genuinely new — confirmed absent from the codebase as of this sprint's own Phase 1a research; no such file, and no `@nosana/cli`-adjacent auto-keygen wrapper, exists anywhere under `~/anicca` today) follows the SAME generation-discipline `gen-wallet.sh` already established (fresh entropy, `{address, private_key, public_key}`-shaped JSON to stdout, 600-perm caller-redirected file, never logged).
    weight: 0.1
    passThreshold: A structural read confirms the new script's output shape and permission discipline match `gen-wallet.sh`'s own documented contract; a live invocation's generated Solana address independently re-derives under a second keypair-derivation path (mirrors REQ-201's own cross-check acceptance criterion, applied to REQ-202's new script). FAIL if the shape/discipline diverges or no cross-check is performed.
  - id: CRIT-208
    dimension: verification_readiness
    description: This sprint's own Phase 1a/1b artifact (REQ-307 in behavioral-spec.md, PROP-307a-d in verification-architecture.md, this contract) is reviewed by a fresh-context adversary (Phase 1c) BEFORE Phase 2 (TDD) begins, exactly as sprint-1's own REQ-101-306/401-403 spec was reviewed before ITS Phase 2 began — this sprint is not exempted from Phase 1c merely because most of its underlying spec content pre-dates it.
    weight: 0.1
    passThreshold: state.json shows a "1b"->"1c" transition with a recorded PASS verdict for this sprint's own contract + REQ-307/PROP-307a-d, produced by a fresh `vcsdd-adversary` instance with zero Builder context. FAIL if Phase 2 begins without this gate.
---

## Pre-existing spec confirmation (this sprint's own Phase 1a/1b finding)

Before any new requirement text was written, this sprint's spec-crystallization phase re-read
`specs/behavioral-spec.md` and `specs/verification-architecture.md` in full and confirmed: REQ-201
(line 1693), REQ-202 (1738), REQ-203 (1795), REQ-204 (1834), REQ-205 (1884), REQ-206 (1915), REQ-301
(2040), REQ-302 (2074), REQ-303 (2138), REQ-304 (2340), REQ-305 (2443), REQ-306 (2604), REQ-401 (2664),
REQ-402 (2702), REQ-403 (2788) already carry full EARS clauses, edge cases, and acceptance criteria —
each already adversary-hardened across sprint-1's own 21 Phase-1c iterations (FIND-001 through
FIND-1901+). None of these fifteen requirements needed new or rewritten behavioral content this sprint.
The ONE genuine gap this sweep found: no function anywhere was named as the thing that calls all of
these steps, in order, inside REQ-103's `"colony-spawn"` lock — every individual step had its own
pinned signature, but the binding orchestration function itself had no row in the Purity Boundary Map
and no REQ number. This sprint's own Phase 1a/1b work is exactly that one addition (REQ-307,
PROP-307a-d) plus two small, additive edge-case corrections to REQ-305/REQ-307 (FIND-2001: the missing
entry-point name; FIND-2002: REQ-305's own "partially-completed attempt SHALL be recorded" promise had
no described mechanism for a failure occurring BEFORE an identity anchor exists, since `buildChildSpec`
cannot be called without one) — never a rewrite or duplication of REQ-201-403's own already-hardened
text. `~/anicca/skills/self/spawn/run.sh` (the pre-existing AgentMail+DigitalOcean/Akash design) was
independently confirmed, by direct read, to be architecturally superseded prior art — already so
classified in verification-architecture.md's own Purity Boundary Map (last row) — and is neither
extended nor called by REQ-307's new orchestrator; sprint-2 builds a NEW module reusing sprint-1's
pure/narrow lib/ building blocks plus `gen-wallet.sh`/`deploy-akash.sh`/`akt-treasury.sh`, never `run.sh`
itself.

## Scope

This sprint delivers:
1. REQ-307's `executeSpawnAttempt` (new `~/anicca/skills/self/spawn/lib/spawn-orchestrator.mjs`),
   wiring sprint-1's pure/narrow modules together per its own canonical call order.
2. `~/anicca/skills/self/spawn/scripts/gen-solana-wallet.sh` (new — REQ-202; confirmed genuinely absent
   from the codebase this sprint's own research phase, no existing Solana-keygen script or
   `@nosana/cli`-wrapping script exists under `~/anicca` today).
3. The REQ-204 ERC-8004 registration call site (reusing `economy/gig/lib/ensure-agent-id.mjs::
   ensureAgentId` unmodified, per REQ-204's own already-specified binding).
4. The REQ-205 `mcp.json`-write call site (matching the real, live `~/.blockrun/mcp.json` shape,
   confirmed by direct read this sprint: `{mcpServers:{"anicca-gig":{transport:"stdio", command, args,
   env:{GIG_FACILITATOR_URL, GIG_STATE_PATH, GIG_CHAIN}}}}`).
5. The REQ-302/303 deploy call sites — reusing `deploy-akash.sh`/`akt-treasury.sh`/`gen-wallet.sh`
   unmodified (confirmed by direct read this sprint, all three still present, unmodified, at
   `~/anicca/skills/self/spawn/scripts/`) — plus the two genuinely NEW pieces REQ-303 itself already
   specifies: the child-specific SDL variant (`HOME=/root` explicit) and the post-lease/post-job
   secrets-injection step (`provider-services lease-shell`/`nosana job ssh`).
6. The REQ-305 ledger-append and citizen-registry-append call site (including FIND-2002's minimal
   early-failure row).

Files touched (all in `~/anicca`, repo `github.com/Daisuke134/anicca`, branch `main`) — final list as
delivered through Phase 2c (refactor): `skills/self/spawn/lib/spawn-orchestrator.mjs` (new, REQ-307's
`executeSpawnAttempt` plus the internal `runStep` helper Phase 2c's refactor introduced to collapse the
7 deps-or-default effectful call sites' identical try/catch/requireOk shape into one place — no exported
surface change, no second orchestration path, CRIT-201 unaffected), `skills/self/spawn/scripts/
gen-solana-wallet.sh` (new), plus test files under `skills/self/spawn/lib/__tests__/`
(`spawn-orchestrator.test.mjs`, `gen-solana-wallet.test.mjs`). The `skills/self/spawn/scripts/sdl/
child.yaml`-equivalent child-specific SDL variant and the lease-shell/job-ssh secrets-injection helper
(REQ-303's own FIND-403/FIND-401 corrections) were NOT created this sprint — both belong exclusively to
PROP-303b's real Akash deploy path, which the "Deferred-obligation disposition" section below explicitly
re-defers as Tier-3 (not silently dropped; `defaultDeploy` continues to call the existing, unmodified
`deploy-akash.sh` exactly as sprint-1 left it). `run.sh`, `child-spec.js`, `ledger.js`, `treasury-gate.mjs`,
`colony-balances.mjs`, `registry-path.mjs`, `citizens-registry.mjs`, `akash-funding-gate.mjs`,
`cloud-target.mjs`, `needs-solana-wallet.mjs`, `shelter-cost-ledger.js` are all reused UNMODIFIED
(sprint-1 delivered and hardened them; this sprint calls them, never edits them, matching CRIT-201's own
"no second orchestration path" requirement extended to "no incidental edits to sprint-1's own files").

**Round 2 additions (contract-review round 2, resolves FIND-001/002/003a/004)**:
`spawn-orchestrator.mjs`'s `defaultDeploy` MUST be updated to call `akash-funding-gate.mjs`'s
`evaluateAkashFundingGate` (REQ-304's own already-tested pure/narrow module) before invoking
`deploy-akash.sh`, enforcing the per-citizen funding ceiling `computePerCitizenSurplusUsd` already
computes — closing FIND-001/002 (PROP-304b/c/d/f). `spawn-orchestrator.mjs`'s
`defaultGenerateEvmWallet` MUST validate the generated address is not the documented sha256-fallback
shape and abort if it is, per REQ-201's own hard SHALL — closing FIND-003a (PROP-201a).
`~/anicca/skills/self/spawn/run.sh` MUST be rewritten (no longer reused-unmodified — see REQ-307's own
"wake-cycle scheduler's real identity" correction) to call `decideColonySpawn()` then, if eligible,
`executeSpawnAttempt()`, retiring the OLD `lib/spawn-decision.js`-based gate and DO/AgentMail
provisioning path entirely from its reachable code — closing FIND-004 (PROP-307e, PROP-102g/102i/101j/
102k). `skills/registry.json`'s `self/spawn` entry's `riskNote` field MUST be updated to cite
`decideColonySpawn` instead of `lib/spawn-decision.js`.

## Deferred-obligation disposition (contracts/sprint-1.md's 38, reconciled against this sprint's own scope)

**Correction (2026-07-08, post-Phase-6 reconciliation)**: `contracts/sprint-1.md`'s FINAL tally (after
the orchestrator's own independent re-verification of the 25 Tier-0 obligations surfaced by the Phase
5→6 gate check) is **38** total deferred obligations (31 Tier>0 + 7 Tier-0), not 42 — 4 of the
originally-deferred Tier-0 obligations (`PROP-106a`, `PROP-403a`, `PROP-105g`, `PROP-202e`) turned out to
be genuinely provable NOW against sprint-1's own already-delivered code (structural grep/read checks, and
for `PROP-105g`, a live cryptographic re-derivation of automaton's real EVM address and Franklin's real
Solana address from their real, resolved key material — see
`verification/proof-harnesses/prop-105g-live-address-rederivation.mjs`) and were restored to
`required:true`/`status:"proved"` — they are NOT part of this sprint's scope, they are ALREADY closed.
Now that REQ-307 names the orchestrator, this sprint's own implementation phase (Phase 2a-2c/3/5) is
expected to promote 30 of the remaining 38 back to `status:"proved"` (revised from 35, contract-review
round 2, resolves FIND-003/FIND-005; revised again round 4, resolves FIND-009 — see the "5 additionally
re-deferred" bucket below):

**30 targeted for closure this sprint** (25 orchestrator-blocked Tier>0 + 5 Tier-0, all closeable via
structural/unit/integration-test proof against sprint-1's own already-injectable I/O boundaries —
`fetchEvmBalanceUsd`/`fetchSolanaBalanceUsd`/`fetchImpl`/`queryBalanceAkt`/`attemptBridge` — none of
these 30 require a real, live token spend to prove):
PROP-201a, PROP-201b, PROP-201c, PROP-201d, PROP-202b, PROP-202c, PROP-203a, PROP-204b, PROP-205b,
PROP-304b, PROP-304c, PROP-304d, PROP-304f, PROP-305b, PROP-305d,
PROP-305e, PROP-305f, PROP-402a, PROP-402b, PROP-102g, PROP-102i, PROP-202d, PROP-101j, PROP-105i,
PROP-102k (25 Tier>0) + PROP-205a, PROP-301a, PROP-305a, PROP-401b, PROP-305h
(5 Tier-0), PLUS the new PROP-307e (run.sh's real wake-cycle wiring, resolves FIND-004).

**3 explicitly NOT targeted this sprint (Tier-3, genuinely require a real, live token spend on a
throwaway artifact)**: PROP-302b (a real `nosana job post`), PROP-303b (a real Akash deploy — sprint-1's
own contract already confirmed, 2026-07-08, zero existing leases under this coordinator's own Akash key,
so no historical artifact can be cited instead of minting a new one), PROP-401a (the $0-bootstrap RPC
corroboration mechanism, which additionally requires a real, first-ever autonomous child to exist and
independently earn — not merely a deploy). These 3 are NOT re-scoped into a hypothetical "sprint 3" by
this contract's own decision — whether they close during THIS sprint's own Phase 5 (mirroring sprint-1's
own precedent of performing real live E2E checks during Phase 5: PROP-204a's real Base-mainnet
`ownerOf` re-verify, PROP-403b/e/f/d's real automaton+Franklin key-distinctness audit) or are pushed to
a dedicated later checkpoint is a decision for whoever executes Phase 5, made against the colony's ACTUAL
real-money readiness at that time (this project's own task #28, "P3実deploy検証チェックポイント(Phase5)",
already tracks this decision point) — this contract only commits to NOT silently claiming them proved via
a fixture, a simulated deploy, or a borrowed artifact from a different feature (CRIT-206).

**5 additionally re-deferred this round (contract-review round 2, resolves FIND-003/FIND-005; round 4
adds a 5th, resolves FIND-009 — genuinely require infrastructure this sprint does not build, distinct
from the Tier-3 real-money-spend reason above)**: PROP-302a and PROP-302c both name REQ-302's own Nosana
deploy path as their verification target — confirmed absent in full this round (`defaultSelectCloudTarget`
hardcodes `nosanaAvailable: false`; no Nosana deploy/secrets-injection call exists anywhere in
`spawn-orchestrator.mjs`; per the module's own code comment, "no live NOS/AKT spot-price feed and no
Nosana deploy path exist anywhere in this codebase yet"). Building Nosana support solely to satisfy these
2 PROPs, when the ACTUAL Nosana deploy (PROP-302b) is ALREADY Tier-3-deferred above, would be wasted,
premature work — they join PROP-302b's own deferral. PROP-203c and PROP-303f both name the
child-specific Akash SDL variant's `HOME=/root` line as their verification artifact — this sprint's own
"Files touched" section already admits this artifact was NOT created this sprint (it belongs exclusively
to PROP-303b's own real Akash deploy path). The original 35-item list wrongly included PROP-203c/PROP-303f
among the "targeted for closure" set despite this same admission — a genuine internal contradiction
(FIND-005) — corrected here: both join PROP-303b's own Tier-3 deferral, since building a custom SDL
variant for a deploy that itself will not run this sprint is equally premature. PROP-303e names a NEW
`provider-services lease-shell ... --stdin` secrets-injection step delivering the child's wallet material
onto a leased Akash container — this is the IDENTICAL "belongs exclusively to PROP-303b's own real Akash
deploy path, not built this sprint" pattern, missed in round 2's own sweep (`grep -rn "lease-shell"
~/anicca/skills/self/spawn/` confirms zero matches anywhere in source or tests) — corrected here: it joins
PROP-303b's own Tier-3 deferral for the identical reason as PROP-203c/PROP-303f. None of these 5 are
claimed proved by this sprint; each carries this same stated reason.

## Known residual scope boundary

REQ-304's full multi-citizen sequential co-funding orchestration (two citizens' sequential transfers to
the same child wallet, PROP-304b/c/d/f above) is included in the 35 targeted for closure, but ONLY as
much as sprint-1's own REQ-304 spec already scopes it: sequential, single-signer transfers, never a
pooled/joint transaction. If, at Phase 2a (RED), the two-citizen case is found to need no dedicated
integration test beyond a single-citizen-sufficient fixture (i.e., no real spawn attempt this sprint
ever actually needs BOTH citizens to co-fund it), that narrower scope is recorded as a Phase 2c note,
not silently dropped. REQ-401/402/403's own remaining Tier-0/Tier-1 obligations not already proved by
sprint-1 (see the 35-item list above) are targeted for real closure this sprint via REQ-307's own
orchestrator existing to call into; none of REQ-401/402/403's own EARS/edge-case/acceptance-criteria text
requires further revision.
