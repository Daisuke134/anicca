# Verification Report

**SPRINT-2 ADDENDUM (2026-07-10)**: this file's own content below is **sprint-1-scoped only** (dated
2026-07-08) and explicitly asserts "the effectful spawn ORCHESTRATOR does not exist in this sprint's
diff" — that is now FALSE. Sprint-2 delivered the money-moving orchestrator
(`spawn-orchestrator.mjs`/`wake-gate.mjs`/`pending-registry-append.js`/`gen-solana-wallet.sh`) and its own
dedicated Phase 5 hardening pass, covering the 7 required proof obligations (PROP-115..121) this sprint's
own contract targeted, lives at **`verification/sprint-2/verification-report.md`** (+ sibling
`sprint-2/security-report.md`, `sprint-2/purity-audit.md`). Read that addendum for sprint-2's own
disposition; everything below this notice is preserved, unmodified, as the as-run sprint-1 record.

**Feature**: anicca-agent-spawn · **Sprint**: 1 · **Phase**: 5 (Formal Hardening) · **Date**: 2026-07-08
**Verifier**: fresh-context Phase 5 session (not the same context as Phase 2/3's Builder/adversary passes)

**Toolchain note**: this feature (and the whole `~/anicca` sibling codebase) is plain ESM/CJS JavaScript
tested via Node's built-in `node:test` runner — every command below was run as
`cd ~/anicca && node --test skills/self/spawn/lib/__tests__/*.test.mjs skills/self/spawn/lib/__tests__/*.test.js`,
never vitest/Stryker. `fast-check` (already a devDependency, `~/anicca/package.json`, added during
`anicca-agent-lending`'s own Phase 5 this session) is reused for Tier-1 property-based tests.

## Summary

**Third update (2026-07-08, same session, orchestrator's own independent re-verification)**: the
"Second update" below undercounted the provable set. The orchestrator independently re-verified all 25
Tier-0 obligations surfaced by the Phase 5→6 gate attempt directly (grep/source-read for structural
checks, plus a dedicated live cryptographic re-derivation harness for PROP-105g —
`verification/proof-harnesses/prop-105g-live-address-rederivation.mjs`, re-deriving automaton's real EVM
address and Franklin's real Solana address from their real, resolved private key material and confirming
both match `citizens.seed.json`'s seeded values). Net result: **16** of the 25 are genuinely provable now
(PROP-104a/106a/106b/103d/105e/105g/105j/202e/206d/206h/303a/304a/304e/402d/403a/306d), including 4 the
prior pass had incorrectly deferred (106a, 403a, 105g, 202e — restored to `required:true`/`status:proved`
after independent verification); **9** genuinely require the orchestrator (PROP-203c/205a/301a/303f/
305a/305h/401b, plus 2 more — see `contracts/sprint-1.md`'s "Second completeness correction" for the
authoritative, final enumeration). **Truly final, orchestrator-confirmed state**: 76/76 required
obligations `status:"proved"`, 0 pending; 38 total `required:false`/`status:"skipped"` (31 Tier>0 + 7
Tier-0), all deferred to sprint-2 (task #57). Full suite: 123/123 passing.

**Second update (2026-07-08, same session, Phase 6 gate attempt — numbers superseded by Third update
above)**: attempting the Phase 5→6 transition surfaced 25 further required Tier-0 obligations (the gate
checks ALL `required:true` regardless of tier — see `contracts/sprint-1.md`'s "Second completeness
correction"). This update's own count (14 proved / 11 deferred) undercounted 4 genuinely-provable
obligations, corrected in the Third update above.

**First update (2026-07-08, same session, post citizens.seed.json fix)**: the numbers below were captured
BEFORE `~/anicca/skills/self/spawn/registry/citizens.seed.json` was created (see
`contracts/sprint-1.md`'s "Missing-deliverable finding, found AND closed same session" note). After
creating that file and proving PROP-013/PROP-015/PROP-062/PROP-067/PROP-087 against it
(`citizens-seed.test.mjs`, 5/5 passing), and after the architect's recorded Scope decision downgrading
the 31 still-unresolved obligations to `required:false`/`status:"skipped"` (`contracts/sprint-1.md`'s
"Scope decision (2026-07-08, architect)"), the FINAL state is: **58/58 required Tier>0 obligations now
`status:"proved"`, 0 pending** (89 original required − 31 downgraded = 58 remaining, all proved).
Full suite: **121/121 passing** (116 below + 5 new `citizens-seed.test.mjs` tests). The per-obligation
detail below (53 proved / 36 not-provable at the time of writing) is preserved as the as-run record of
this phase's own investigative work; treat the Update paragraph above as authoritative for current state.

| Metric | Count |
|---|---|
| Required proof obligations, Tier > 0 | 89 (49 Tier-1, 34 Tier-2, 6 Tier-3) |
| **Proved this session** | **53** (then **+5** after the seed-file fix → **58 final**) |
| Not provable this sprint (orchestrator/deliverable does not exist yet) | 36 (then **-5** after the seed-file fix → **31 final**, all downgraded `required:false` by architect decision) |
| Full target-feature test suite | **116/116 passing** at time of writing → **121/121 final** (100 pre-existing + 16 new + 5 `citizens-seed.test.mjs`) |
| New test files added | `treasury-gate.property.test.mjs` (7 fast-check tests), `akash-funding-gate.property.test.mjs` (2 fast-check tests), `spawn-gap-coverage.test.mjs` (7 unit/integration tests), `citizens-seed.test.mjs` (5 unit tests, added after the seed-file fix) — all under `~/anicca/skills/self/spawn/lib/__tests__/` |
| Live E2E artifacts (Tier 3) | PROP-204a: real Base-mainnet ERC-8004 `ownerOf` cross-provider re-verification. PROP-403b/PROP-403e: real automaton+Franklin key-distinctness live audit, via unmodified `resolve-identity.mjs` |
| Security static analysis | Semgrep `--config=auto --config=p/security-audit --config=p/secrets`: **0 findings** across 203 rules, 12 files |
| Purity boundary audit | Confirmed intact — see `purity-audit.md` |

**The headline finding of this phase**: of the 89 required Tier>0 obligations, **36 cannot be proved this
sprint**, falling into three distinct root causes — all are pre-existing scope gaps, not defects
introduced or discovered this phase:

1. **Orchestrator-blocked (30 obligations)**: the effectful spawn ORCHESTRATOR — the code that would
   actually call `gen-wallet.sh`/`ensureAgentId`/write `mcp.json`/invoke `nosana job post`/`deploy-akash.sh`/
   append a real REQ-305 ledger row/transfer real funding — does not exist anywhere in this sprint's diff.
   `contracts/sprint-1.md`'s own "Known residual scope boundary" section already names this gap for
   REQ-201/204/205/302/304(partial)/305/401/402(partial). This session independently confirms the
   underlying fact: `~/anicca/skills/self/spawn/lib/` contains exactly the 9 delivered modules (plus
   `ledger.js`/`state-path.js`/`spawn-decision.js`, reused unmodified) and no orchestrator file.
2. **Missing seed deliverable (5 obligations)**: `specs/verification-architecture.md`'s own Purity
   Boundary Map declares `~/anicca/skills/self/spawn/registry/citizens.seed.json` as a "Static config
   asset (git-tracked)" this sprint should have delivered — **it does not exist** (`skills/self/spawn/`
   has no `registry/` directory at all). PROP-013/PROP-015/PROP-062/PROP-067/PROP-087 (anchors
   105a/105c/105d/105f/105h) all reference this file's content and cannot be evaluated without it. This
   is **not named** in `contracts/sprint-1.md`'s residual-scope section — flagged below as a
   contract-listing gap, mirroring `anicca-agent-lending`'s own Phase 5 precedent for un-listed gaps.
3. **Tier-3, would require spending real money on a throwaway artifact (2 obligations, PROP-038/PROP-040
   — the other 4 Tier-3 obligations fall into case 1 or were provable, see below)**: PROP-038 (real
   `nosana job post`) and PROP-040 (real Akash deploy) would each require CREATING a brand-new real
   deployment purely to produce a proof artifact, with no already-existing lease/job to independently
   re-query instead (confirmed live: `provider-services query market lease list --owner
   akash1ms7gr5sxkv33ra353hg5lu8dm7akljdaamj523` on Akash mainnet returned zero leases). Unlike
   `anicca-agent-lending`'s own Phase 5 precedent (which found a real HISTORICAL Base-mainnet tx to query
   read-only), no equivalent already-existing Akash/Nosana artifact exists for this feature — spending
   real AKT/SOL on a job with no real child behind it was judged out of scope for a proof session.

**Because `vcsdd-state.js`'s own Phase-6 gate prerequisite requires literally every `required:true`
obligation to reach `status:"proved"` before Phase 6 (convergence) can be entered, these 36 obligations
structurally block Phase 6 today.** This is a decision for the orchestrator (team-lead): either open a
sprint-2 that builds the missing orchestrator/seed file and closes these for real, or make an explicit,
recorded decision to downgrade some/all of them to `required:false` citing this session's findings — a
scope decision, not something this session unilaterally applied. `state.json` has NOT been modified for
any of these 36; they remain `status:"pending"`, `required:true`, exactly as Phase 3 left them.

## Tier-3 obligations — case (a) vs case (b), per this session's assigning instructions

| ID | Anchor | Case | Resolution |
|---|---|---|---|
| PROP-027 | 204a | **(a) live evidence, PROVED** | `ensure-agent-id.mjs` (unmodified, from a PRIOR already-shipped sprint) already minted a REAL registration for this instance: agentId `58381`, address `0xB9dd3B67921B354c656523d6851537988F31DD56`, on Base mainnet's real `IdentityRegistry` (`0x8004A169FB4a3325136EB29fA0ceB6D2e539a432`). This session independently re-verified `ownerOf(58381)` via TWO separate RPC providers (`mainnet.base.org`, `base-rpc.publicnode.com`) — both agree, both match the expected address. See `proof-harnesses/prop-204a-live-agentid-reverify.mjs` + `.output.log`. |
| PROP-059 | 403b | **(a) live evidence, PROVED** | `resolve-identity.mjs` (unmodified) invoked live against automaton (`$HOME/.anicca`) and Franklin (`$HOME/.blockrun`), both `coLocatedWithCoordinator:true` today — pairwise same-chain comparison (`automaton.evm` vs `franklin.evm`) confirms distinct, non-null real key material. See `proof-harnesses/prop-403b-live-key-distinctness.mjs` + `.output.log`. Raw key material never printed — only booleans. |
| PROP-038 | 302b | **(b) orchestrator-blocked** | Needs a real `nosana job post --wait` for a genuinely new child — no orchestrator exists to create one, and no already-existing Nosana job for this project was found to re-query instead. Spending real SOL on a throwaway job was judged out of scope. |
| PROP-040 | 303b | **(b) orchestrator-blocked** | Needs a real Akash deploy/lease for a genuinely new child. Confirmed live (read-only): `provider-services query market lease list --owner akash1ms7gr5sxkv33ra353hg5lu8dm7akljdaamj523` on Akash mainnet → zero leases. No already-existing lease to independently re-query; spending real AKT on a throwaway deploy was judged out of scope. |
| PROP-053 | 401a | **(b) orchestrator-blocked** | Unlike `anicca-agent-lending`'s Phase 5 (which found a real, already-shipped `verifyRepayment` function to run against live chain data), this sprint's diff contains NO delivered function implementing "$0-bootstrap RPC corroboration" at all — the mechanism itself does not exist as code yet, only as spec prose. A real, independently-verified citizen-to-citizen settlement DOES exist (`memory/project_p2_witness_achieved_franklin_to_franklin.md`, Base mainnet tx `0x87e0d4dd.../0x436143c1...`), but that is REQ-106's gig-marketplace transaction, not REQ-401's spawn-bootstrap proof — using it here would be citing the wrong requirement's evidence. |
| PROP-079 | 303e | **(b) orchestrator-blocked** | Per the doc's own wording: "a genuinely NEW step, never claimed as pre-proven reuse" — the `provider-services lease-shell ... --stdin` wallet-injection code does not exist anywhere in this sprint's diff or any prior sprint. |

## Proof Obligations — Proved (53)

| ID | Anchor | Tier | Evidence |
|---|---|---|---|
| PROP-001 | 101a | 1 | `treasury-gate.test.mjs` |
| PROP-002 | 101b | 1 | `treasury-gate.test.mjs` |
| PROP-003 | 101c | 1 | `colony-balances.test.mjs` |
| PROP-004 | 102a | 1 | `treasury-gate.test.mjs` |
| PROP-005 | 102b | 1 | `treasury-gate.test.mjs` |
| PROP-006 | 102c | 1 | `treasury-gate.test.mjs` |
| PROP-007 | 102d | 1 | `treasury-gate.test.mjs` |
| PROP-008 | 102e | 1 | `treasury-gate.test.mjs` + NEW `treasury-gate.property.test.mjs` "PROP-102e (property)" (300 runs, arbitrary insufficient surplus/cooldown/cap combinations) |
| PROP-009 | 103a | 2 | `colony-spawn-lock.test.mjs` "PROP-103a/PROP-103d" |
| PROP-010 | 103b | 2 | NEW `spawn-gap-coverage.test.mjs` "PROP-103b" — a REAL backdated stale lock file, `isLockStale` confirmed true on the fixture, exactly one of two concurrent `withGigLock` reclaim attempts succeeds |
| PROP-011 | 103c | 1 | Cites upstream `isLockStale` Tier-1 proof (`~/anicca/skills/economy/gig/__tests__/lock.test.mjs`, `anicca-agent-economy` REQ-101, re-run green this session, 11/11) — `lock.mjs` reused unmodified (confirmed: zero diff since prior sprint) |
| PROP-014 | 105b | 1 | NEW `spawn-gap-coverage.test.mjs` "PROP-105b" — a malformed registry record (missing wallet/fuel/humanDependencies) mixed with 2 valid citizens never throws, aggregation sums only the 2 valid citizens |
| PROP-021 | 202a | 1 | `needs-solana-wallet.test.mjs` |
| PROP-025 | 203b | 2 | `~/anicca/runtime/loop/__tests__/resolve-identity.test.mjs` "fresh ANICCA_HOME: EVM + Solana keys generated under it resolve back via resolve-identity" — a genuinely THIRD, freshly-generated home fixture, from the `equalize-multichain-identity` sprint, `resolve-identity.mjs` reused unmodified |
| PROP-027 | 204a | 3 | **Live E2E** — see Tier-3 table above |
| PROP-029 | 204c | 2 | `~/anicca/skills/economy/gig/__tests__/ensure-agent-id.test.mjs` "valid cache for the SAME address -> reuses it, never re-registers" — `ensure-agent-id.mjs` reused unmodified from a prior sprint |
| PROP-032 | 206a | 1 | `child-spec.test.js` + `child-spec-erc8004.test.js` |
| PROP-033 | 206b | 1 | `child-spec-erc8004.test.js` |
| PROP-034 | 206c | 1 | `child-spec-erc8004.test.js` |
| PROP-041 | 303c | 2 | NEW `spawn-gap-coverage.test.mjs` "PROP-303c" — real `appendShelterCostEntry` write observed by `deriveMeasuredShelterCostUsd({shelterCostLedgerRows: readShelterCostEntries(...)})` on the next evaluation, last-appended entry wins |
| PROP-047 | 305c | 1 | `treasury-gate.test.mjs` |
| PROP-049 | 306a | 1 | `cloud-target.test.mjs` |
| PROP-050 | 306b | 1 | `cloud-target.test.mjs` |
| PROP-051 | 306c | 1 | `cloud-target.test.mjs` |
| PROP-057 | 402c | 1 | Cites `treasury-gate.test.mjs`'s existing "PROP-101d" fixture — `filterProductiveCitizens` reads the `bootstrap_failed` flag from the SAME `ledger.js` row this obligation describes; same underlying function, no new proof needed |
| PROP-059 | 403b | 2 | **Live E2E** — see Tier-3 table above |
| PROP-060 | 403c | 2 | NEW `spawn-gap-coverage.test.mjs` "PROP-403c" — two fixture instances forced to share the same HOME are correctly flagged as a key-material collision, proving the check is not vacuous |
| PROP-063 | 206e | 1 | `child-spec-erc8004.test.js` |
| PROP-065 | 101d | 1 | `treasury-gate.test.mjs` |
| PROP-068 | 206f | 2 | NEW `spawn-gap-coverage.test.mjs` "PROP-206f" — all required fields (base six + ERC-8004 anchor pair) populated, every field present in the returned row |
| PROP-069 | 206g | 2 | NEW `spawn-gap-coverage.test.mjs` "PROP-206g" — `seedUsdc` fixture-bound identity, `generation === 1` |
| PROP-071 | 101e | 2 | `colony-balances.test.mjs` "PROP-101e" + NEW `spawn-gap-coverage.test.mjs` "PROP-101e" (co-located vs simulated-remote citizen resolve identically via RPC alone) |
| PROP-073 | 306e | 2 | `cloud-target.test.mjs` |
| PROP-075 | 101f | 1 | `colony-balances.test.mjs` |
| PROP-078 | 303d | 2 | `akash-funding-gate.test.mjs` "PROP-303d" |
| PROP-082 | 101g | 2 | `colony-balances.test.mjs` |
| PROP-084 | 101h | 2 | `colony-balances.test.mjs` |
| PROP-086 | 403e | 2 | **Live E2E** — same harness as PROP-403b; every call site in `prop-403b-live-key-distinctness.mjs` passes an explicit `{HOME, ANICCA_HOME}` object, never a bare `{home:X}` call |
| PROP-092 | 105k | 2 | `registry-path.test.mjs` |
| PROP-093 | 105l | 2 | `citizens-registry.test.mjs` |
| PROP-094 | 105m | 2 | `registry-path.test.mjs` |
| PROP-096 | 305g | 1 | `treasury-gate.test.mjs` |
| PROP-097 | 103e | 2 | `colony-spawn-lock.test.mjs` "PROP-103e" |
| PROP-098 | 101i | 1 | `treasury-gate.test.mjs` + NEW property test (500 runs) |
| PROP-099 | 402e | 1 | `treasury-gate.test.mjs` |
| PROP-100 | 102f | 1 | `treasury-gate.test.mjs` + NEW property test (300 runs, realistic status-sequence generator) |
| PROP-103 | 102h | 1 | `treasury-gate.test.mjs` + NEW property test |
| PROP-105 | 102j | 1 | `treasury-gate.test.mjs` |
| PROP-110 | 101k | 1 | `treasury-gate.test.mjs` |
| PROP-111 | 303g | 1 | `akash-funding-gate.test.mjs` + NEW `akash-funding-gate.property.test.mjs` (300 runs) |
| PROP-112 | 303h | 1 | `akash-funding-gate.test.mjs` + NEW `akash-funding-gate.property.test.mjs` (300 runs) |
| PROP-113 | 102l | 1 | `treasury-gate.test.mjs` + NEW property tests (FIND-1901/1902 coercions, 700 runs total) |
| PROP-114 | 101l | 1 | `treasury-gate.test.mjs` + NEW property test (300 runs) |

## Not provable this sprint (36)

### Orchestrator-blocked (30) — code that would call the delivered modules does not exist

PROP-018(201a), PROP-019(201b), PROP-020(201c), PROP-076(201d), PROP-022(202b), PROP-023(202c),
PROP-024(203a), PROP-028(204b), PROP-031(205b), PROP-037(302a), PROP-077(302c), PROP-079(303e),
PROP-043(304b), PROP-044(304c), PROP-081(304d), PROP-095(304f), PROP-046(305b), PROP-048(305d),
PROP-064(305e), PROP-088(305f), PROP-055(402a), PROP-056(402b), PROP-101(102g), PROP-104(102i),
PROP-106(202d), PROP-108(101j), PROP-109(102k) — 27 anchors, plus PROP-038(302b)/PROP-040(303b)
(Tier-3, would also need real money spent — see Tier-3 table) = 29, plus PROP-090(105i) (needs a
re-derivation audit script this session did not have time to build against a real dual-chain citizen —
not attempted, distinct from the other orchestrator-blocked items but grouped here since it is
similarly a not-yet-built mechanism) = **30**.

`PROP-101`/`PROP-104`/`PROP-106`/`PROP-108`/`PROP-109` (anchors 102g/102i/202d/101j/102k) are the
"X's real orchestration derives Y by calling Z directly" family — `contracts/sprint-1.md`'s own text
explicitly admits this for PROP-102k ("it requires that same not-yet-built orchestrator;
treasury-gate.test.mjs has no PROP-102k-named test this sprint, confirming the gap is not silently
overclaimed"); this session confirms the identical root cause applies to its four siblings, which the
contract's own residual-scope section does not individually name — a **contract-listing gap**, not a new
scope decision (same pattern `anicca-agent-lending`'s Phase 5 found for its own PROP-037/PROP-055/PROP-038).

### Missing seed deliverable (5) — contract-listing gap

PROP-013(105a), PROP-015(105c), PROP-062(105d), PROP-067(105f), PROP-087(105h). All five require
`~/anicca/skills/self/spawn/registry/citizens.seed.json` to exist and hold the documented 2-entry literal
array — `specs/verification-architecture.md`'s own Purity Boundary Map declares this file as part of
this feature, but `skills/self/spawn/` has **no `registry/` directory at all**. Not named in
`contracts/sprint-1.md`'s residual-scope section.

### Tier-3, real-money orchestrator gap (2)

PROP-038(302b), PROP-040(303b) — see Tier-3 table above.

## Test evidence

```
cd ~/anicca && node --test skills/self/spawn/lib/__tests__/*.test.mjs skills/self/spawn/lib/__tests__/*.test.js
# tests 116, pass 116, fail 0, cancelled 0, skipped 0, todo 0
```

New files this session (all `~/anicca/skills/self/spawn/lib/__tests__/`):
- `treasury-gate.property.test.mjs` — 7 `fast-check` property tests (~2,400 generated-input runs total)
- `akash-funding-gate.property.test.mjs` — 2 `fast-check` property tests (~500 generated-input runs)
- `spawn-gap-coverage.test.mjs` — 7 unit/integration tests (PROP-103b/303c/206f/206g/403c/101e/105b)

Live proof harnesses (`.vcsdd/features/anicca-agent-spawn/verification/proof-harnesses/`):
- `prop-204a-live-agentid-reverify.mjs` + `.output.log`
- `prop-403b-live-key-distinctness.mjs` + `.output.log`
