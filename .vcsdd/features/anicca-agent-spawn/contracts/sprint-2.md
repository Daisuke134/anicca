---
status: draft
feature: anicca-agent-spawn
sprintNumber: 2
negotiationRound: 1
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
    description: Exactly one function, `executeSpawnAttempt`, in exactly one new module
      (`~/anicca/skills/self/spawn/lib/spawn-orchestrator.mjs`), calls REQ-201 through REQ-305's own
      already-exported functions/scripts in the canonical order REQ-307 states — no second, competing
      orchestration entry point exists anywhere in the diff, and `~/anicca/skills/self/spawn/run.sh`
      (the pre-existing AgentMail+DigitalOcean/Akash design, already classified "reused-but-superseded
      prior art" in verification-architecture.md's own Purity Boundary Map) is neither modified nor
      called by this sprint's new code.
    weight: 0.15
    passThreshold: A control-flow read of `spawn-orchestrator.mjs` confirms a single call-graph root
      reaching every one of REQ-201/202/203/204/205/206/301/302/303/304/305/306's own exported
      functions/scripts, in the order REQ-307's own "Canonical call order" states, and that
      `~/anicca/skills/self/spawn/run.sh` appears in neither this sprint's commits nor its diff. FAIL
      if a second orchestration path exists, if the canonical order is violated, or if `run.sh` is
      touched.
  - id: CRIT-202
    dimension: structural_integrity
    description: `executeSpawnAttempt` itself contains no decision/judgment logic — no
      arithmetic/boolean eligibility comparison and no LLM/prompt reference — mirroring REQ-104's
      bookkeeping-only discipline, extended by REQ-307 to this new function (PROP-307b).
    weight: 0.1
    passThreshold: Structural grep of `spawn-orchestrator.mjs` finds no relational/threshold comparison
      and no prompt/LLM-client reference. FAIL if either is found.
  - id: CRIT-203
    dimension: edge_case_coverage
    description: A failure injected at each of REQ-307's 9 canonical steps in turn is recorded
      correctly — steps 1-5 (before an identity anchor exists) append a minimal
      `{child_id, status:"failed", attempted_ms, error}` row directly via `ledger.js::appendChild`,
      never via `buildChildSpec`; steps 6-9 use the existing `buildChildSpec`-based REQ-305 path; no row
      anywhere ever claims `status:"active"` for a failed attempt (PROP-307c, resolves FIND-2002).
    weight: 0.15
    passThreshold: An integration test triggering a failure at each of the 9 steps against a real
      `ledger.js` file confirms the above, AND confirms `filterProductiveCitizens`/
      `deriveRecentSpawnAttempts` (REQ-101/102, sprint-1, unmodified) correctly treat every resulting
      row as non-productive/failure regardless of which recording path produced it. FAIL if any step's
      failure produces no row, a wrongly-shaped row, or a row misread by the sprint-1 aggregation
      functions.
  - id: CRIT-204
    dimension: structural_integrity
    description: The `"colony-spawn"` lock (REQ-103, sprint-1, unmodified) is held from before
      `executeSpawnAttempt`'s step 1 begins until after step 9 completes or a failure is ledgered —
      never released any earlier (PROP-307d).
    weight: 0.1
    passThreshold: Integration test reusing PROP-103e's own staggered-race method against the REAL
      `executeSpawnAttempt` (steps 2-9 stubbed to fast, real-shaped fixture I/O) confirms the lock's
      real scope over this actual function matches REQ-103's already-specified critical section. FAIL
      if any staggered attempt during the delay window succeeds.
  - id: CRIT-205
    dimension: verification_readiness
    description: Every one of the 35 non-Tier-3 obligations this sprint targets (see "Deferred-obligation
      disposition" below) is either proved (structural/unit/integration) or explicitly re-deferred with
      a stated reason — none is silently left `pending`.
    weight: 0.2
    passThreshold: `state.json`'s proofObligations array, after this sprint's Phase 3/5, shows every
      PROP ID in the "35 targeted" list as `status:"proved"` or, for any exception, a Phase-5 contract
      note stating the specific reason it could not be closed this sprint (mirroring sprint-1's own
      disposition style). FAIL if any targeted PROP is left `pending`.
  - id: CRIT-206
    dimension: spec_fidelity
    description: The 3 Tier-3 real-money obligations (PROP-302b, PROP-303b, PROP-401a) are NOT claimed
      proved via a fixture/simulated deploy or a borrowed/historical artifact from a DIFFERENT feature
      (e.g. `anicca-agent-lending`'s own prior Akash lease) — each requires either a genuinely NEW real
      spend this sprint, or an explicit, honest re-deferral to a dedicated future checkpoint (this
      project's own task #28, "P3実deploy検証チェックポイント(Phase5)").
    weight: 0.1
    passThreshold: A read of whichever artifact/evidence file claims these 3 PROPs proved confirms a
      genuinely fresh on-chain transaction/job ID minted THIS sprint (not a citation of `2026-07-08`'s
      read-only "zero existing leases" query from sprint-1's own contract, and not
      `anicca-agent-lending`'s own historical artifact) — OR the contract explicitly re-defers them,
      citing this section. FAIL if either is claimed proved via a stale/borrowed/simulated artifact.
  - id: CRIT-207
    dimension: implementation_correctness
    description: `~/anicca/skills/self/spawn/scripts/gen-solana-wallet.sh` (genuinely new — confirmed
      absent from the codebase as of this sprint's own Phase 1a research; no such file, and no
      `@nosana/cli`-adjacent auto-keygen wrapper, exists anywhere under `~/anicca` today) follows the
      SAME generation-discipline `gen-wallet.sh` already established (fresh entropy, `{address,
      private_key, public_key}`-shaped JSON to stdout, 600-perm caller-redirected file, never logged).
    weight: 0.1
    passThreshold: A structural read confirms the new script's output shape and permission discipline
      match `gen-wallet.sh`'s own documented contract; a live invocation's generated Solana address
      independently re-derives under a second keypair-derivation path (mirrors REQ-201's own
      cross-check acceptance criterion, applied to REQ-202's new script). FAIL if the shape/discipline
      diverges or no cross-check is performed.
  - id: CRIT-208
    dimension: verification_readiness
    description: This sprint's own Phase 1a/1b artifact (REQ-307 in behavioral-spec.md, PROP-307a-d in
      verification-architecture.md, this contract) is reviewed by a fresh-context adversary
      (Phase 1c) BEFORE Phase 2 (TDD) begins, exactly as sprint-1's own REQ-101-306/401-403 spec was
      reviewed before ITS Phase 2 began — this sprint is not exempted from Phase 1c merely because most
      of its underlying spec content pre-dates it.
    weight: 0.1
    passThreshold: `state.json` shows a `"1b"->"1c"` transition with a recorded PASS verdict for this
      sprint's own contract + REQ-307/PROP-307a-d, produced by a fresh `vcsdd-adversary` instance with
      zero Builder context. FAIL if Phase 2 begins without this gate.
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

Files touched (all in `~/anicca`, repo `github.com/Daisuke134/anicca`, branch `main`) — exact list
finalized at Phase 2a (RED), expected to include: `skills/self/spawn/lib/spawn-orchestrator.mjs` (new),
`skills/self/spawn/scripts/gen-solana-wallet.sh` (new), `skills/self/spawn/scripts/sdl/child.yaml` or
equivalent child-specific SDL variant (new, small — REQ-303's own FIND-403 correction), a new
lease-shell/job-ssh secrets-injection helper (new — REQ-303's own FIND-401 correction), plus test files
under `skills/self/spawn/lib/__tests__/`. `run.sh`, `child-spec.js`, `ledger.js`, `treasury-gate.mjs`,
`colony-balances.mjs`, `registry-path.mjs`, `citizens-registry.mjs`, `akash-funding-gate.mjs`,
`cloud-target.mjs`, `needs-solana-wallet.mjs`, `shelter-cost-ledger.js` are all reused UNMODIFIED
(sprint-1 delivered and hardened them; this sprint calls them, never edits them, matching CRIT-201's own
"no second orchestration path" requirement extended to "no incidental edits to sprint-1's own files").

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
expected to promote 35 of the remaining 38 back to `status:"proved"`:

**35 targeted for closure this sprint** (28 orchestrator-blocked Tier>0 + 7 Tier-0, all closeable via
structural/unit/integration-test proof against sprint-1's own already-injectable I/O boundaries —
`fetchEvmBalanceUsd`/`fetchSolanaBalanceUsd`/`fetchImpl`/`queryBalanceAkt`/`attemptBridge` — none of
these 35 require a real, live token spend to prove):
PROP-201a, PROP-201b, PROP-201c, PROP-201d, PROP-202b, PROP-202c, PROP-203a, PROP-204b, PROP-205b,
PROP-302a, PROP-302c, PROP-303e, PROP-304b, PROP-304c, PROP-304d, PROP-304f, PROP-305b, PROP-305d,
PROP-305e, PROP-305f, PROP-402a, PROP-402b, PROP-102g, PROP-102i, PROP-202d, PROP-101j, PROP-105i,
PROP-102k (28 Tier>0) + PROP-203c, PROP-205a, PROP-301a, PROP-305a, PROP-401b, PROP-303f, PROP-305h
(7 Tier-0).

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
