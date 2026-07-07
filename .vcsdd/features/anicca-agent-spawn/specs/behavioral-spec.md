# Behavioral Spec — anicca-agent-spawn (Phase 1a)

**feature**: anicca-agent-spawn · **mode**: strict · **increment**: P3 spawn (colony-treasury-gated,
cloud-only) + $0-bootstrap verification · **日付**: 2026-07-07 · **revision**: iteration 1 (first
draft)

## Scope of this increment (read first)

This is `.vcsdd/features/anicca-agent-economy/specs/SPEC.md`'s **P3** ("spawn — cloud,
treasury-funded script — + $0-bootstrap", SPEC.md §3 P3 / §8 checklist item `P3`), split into its
own feature directory because it is architecturally distinct from the already-`DONE` P2 gig-board
work: P2 proved two EXISTING citizens (Franklin#1↔Franklin#2, both genesis-funded once by Dais'
explicit, one-time, human-approved exception per SPEC.md §9.9) can trade. P3 must instead prove the
colony can **create a brand-new citizen from its own accumulated surplus, with zero further
human-funded injection**, and that the new citizen can earn its own keep. **The genesis exception in
§9.9 does NOT extend to P3** — SPEC.md §0's HARD invariant ("claude-p + 全 human-funded AI は経済圏の
永久非構成員") governs every spawn this feature specifies: funding for a spawn comes exclusively from
self-funded citizens' own accumulated surplus (REQ-101/304), never from claude-p's or any other
human-funded wallet.

This spec covers exactly four requirement groups, mapped 1:1 to the task's four groups:
- **REQ群A (REQ-101..104)**: the deterministic treasury gate — pure arithmetic bookkeeping over the
  colony's aggregate self-funded surplus, not a model judgment call.
- **REQ群B (REQ-201..205)**: new-instance identity generation, reusing the already-proven P2
  mechanisms (`gen-wallet.sh`, `$HOME`/`ANICCA_HOME` isolation, ERC-8004 `register()`, gig-board MCP
  wiring) rather than reinventing them.
- **REQ群C (REQ-301..305)**: cloud deployment via Nosana or Akash — genuinely new for this project
  (never yet executed end-to-end for a spawn), verified against re-fetched, current-as-of-2026-07-07
  documentation before being specified (see citations inline).
- **REQ群D (REQ-401..403)**: the $0-bootstrap success/failure criteria and the cross-instance wallet
  non-interference audit that must hold once N ≥ 2 instances (including newly-spawned children) run
  concurrently.

**Explicitly OUT of scope for this increment**: P4 (UBI/mutual-aid/collective self-repair) and P5
(scale/self-host/GitHub graduation) remain separate, later SPEC.md phases and are not specified here.
Rewriting or deleting the pre-existing, architecturally-superseded `~/anicca/skills/self/spawn/`
directory (a 2026-06-16 DigitalOcean + AgentMail single-lineage design predating the Franklin +
ERC-8004 pivot documented in SPEC.md §1.3) is also out of scope: Phase 2 MAY reuse its pure,
still-valid primitives (see the Purity Boundary table below) but replacing its DO/AgentMail-specific
provisioning code is a Phase 2b implementation decision, not something this spec mandates either way.

## Nosana/Akash documentation re-verification (performed 2026-07-07, before writing REQ群C)

Per the task's explicit instruction not to spec cloud deployment from stale training-data knowledge,
the following was re-checked live via `firecrawl scrape` against the current sites (all URLs fetched
2026-07-07; none were cached/assumed):

| Claim in SPEC.md §1 | Still accurate? | Fresh evidence |
|---|---|---|
| Nosana CLI = `@nosana/cli`, wallet auto-generated, no signup | **Yes, unchanged** | `learn.nosana.com/inference/quick_start.html`: `npm install -g @nosana/cli`; "When you first run the Nosana CLI, a new keypair is generated for you in `~/.nosana/.nosana_key.json`"; job posting = `nosana job post <cmd> --wait --market <address>`, needs SOL+NOS in that wallet, no account/API-key required for this CLI path. |
| Akash = `provider-services` CLI, SDL-based, crypto-wallet-only | **Yes, unchanged** | `akash.network/docs/developers/deployment/cli/`: "The Provider Services CLI (`provider-services`) is the official command-line interface for deploying on Akash Network." Sub-pages (`.../cli/act-mint-burn/`) confirm `akash tx bme mint-act`/`burn-act` (the ACT↔AKT bonding-curve conversion this project's `akt-treasury.sh` already automates) is still the current, documented mechanism — no drift from the already-verified `sandbox-2` E2E this repo's scripts cite. |
| Akash also offers a managed, card-billed Console API | **New finding, not in SPEC.md §1** | `akash.network/docs/developers/deployment/`: Akash now separately documents a "Console API — Managed REST API... managed wallets and credit-card billing. No private keys, crypto, or blockchain client required." **This path is explicitly REJECTED for this feature** (human card + managed custody violates human-zero); REQ-303 binds exclusively to the CLI/`provider-services` (self-custody) path, never the Console API. |
| ACT (`uact`) is pegged 1:1 to USD | **Not true — corrected** | Neither the CLI docs nor the mint/burn page states a fixed peg; `akash tx bme mint-act` converts AKT→ACT at a floating bonding-curve rate (this repo's own `akt-treasury.sh` comment already documents an observed `P_mint≈0.66` — i.e. NOT 1:1). REQ-102's threshold below is deliberately built to avoid assuming any fixed ACT/USD or AKT/USD rate. |

No other drift was found: both CLIs, both wallet models (Solana-keypair-auto-gen for Nosana,
`provider-services`+SDL for Akash), and this repo's existing `deploy-akash.sh`/`akt-treasury.sh`
scripts remain aligned with current upstream documentation.

## Purity boundary analysis (overview — file/function detail lives in verification-architecture.md)

| Concern | Classification | Why |
|---|---|---|
| Colony self-funded citizen filter | **Pure core (existing, reused unmodified)** | `~/anicca/skills/_shared/lib/is-self-funded.mjs::isSelfFunded(agent)` — already implements exactly the "own wallet + own-funded fuel + zero human deps" test this feature's REQ-101 needs to decide which balances even count toward the colony surplus. No new judgment logic is written; REQ-101 calls this existing, already-tested function. |
| Colony surplus aggregation | **Pure core (new)** | A sum of `max(0, balance_i - perCitizenReserveUsd)` over self-funded citizens only — deterministic arithmetic over already-fetched balances, no I/O once inputs are supplied (REQ-101). |
| Spawn eligibility gate | **Pure core (new, extends an existing pattern)** | `~/anicca/skills/self/spawn/lib/spawn-decision.js::decideSpawn` already establishes the exact target shape (`{eligible, reason}`, pure, no I/O) this feature's colony-scoped gate follows — REQ-102 is a colony-aggregate generalization of that same pattern, not a new design. |
| Per-child identity record assembly | **Pure core (existing, reused unmodified)** | `~/anicca/skills/self/spawn/lib/child-spec.js::nextChildId`/`buildChildSpec` — monotonic ID + distinct-wallet assertion, already pure and unit-tested; reused for REQ-201-205's child record. |
| Cross-instance spawn mutual exclusion (lock predicate) | **Pure core (existing, reused unmodified)** | `~/anicca/skills/economy/gig/lib/lock.mjs::isLockStale(nowMs, mtimeMs, staleMs)` — the already-adversary-hardened staleness predicate from the P2 concurrency-hardening sprint (`anicca-agent-economy` REQ-101). REQ-103 reuses the SAME generic file-lock module under a new lock key (`"colony-spawn"`), not a new lock implementation. |
| Balance/telemetry reads across colony instances | **Effectful shell** | `fs.readFile` of each citizen's `state/telemetry.json` (the exact pattern `~/anicca/skills/economy/ubi/run.sh` already uses to read `$HOME/.automaton/state/telemetry.json` / `$HOME/.blockrun/state/telemetry.json`) — real I/O, not inferred. |
| Child EVM wallet generation | **Effectful shell** | `~/anicca/skills/self/spawn/scripts/gen-wallet.sh` — `openssl`+`python3` subprocess, real entropy source, reused unmodified. |
| Child Solana keypair generation | **Effectful shell (new)** | New script analogous to `gen-wallet.sh` but ed25519/Solana-shaped (REQ-202); real entropy source. |
| `$HOME`/`ANICCA_HOME` isolation at process launch | **Effectful shell** | Setting an env var at process spawn time is an OS-level side effect; the isolation PROPERTY it produces (a distinct resolved path) is what REQ-203 specifies and what `~/anicca/skills/earn/lib/resolve-identity.mjs` already relies on for existing instances. |
| ERC-8004 `register()` | **Effectful shell (existing, reused unmodified)** | `~/anicca/skills/economy/gig/lib/identity.mjs::registerIdentity` — a real on-chain transaction (mainnet registry `0x8004A169FB4a3325136EB29fA0ceB6D2e539a432` on Base, chain 8453; testnet `0xdc527768082c489e0ee228d24d3cfa290214f387` on Base-Sepolia; both independently re-verified live 2026-07-07 per that file's own header). |
| gig-board `mcp.json` generation | **Effectful shell (new, template reused)** | File write following the exact shape of the already-live, verified `~/.blockrun/mcp.json`. |
| Nosana job deploy | **Effectful shell (new)** | Real `nosana job post` subprocess against a real Solana-settled market; genuinely new for this project (REQ-302). |
| Akash job deploy | **Effectful shell (existing, reused unmodified)** | `~/anicca/skills/self/spawn/scripts/deploy-akash.sh` + `akt-treasury.sh` — already implemented, already tested against a real sandbox-2 chain per those scripts' own inline evidence references; reused unmodified with a new child SDL/`CHILD_ID` (REQ-303). |
| Shelter-cost funding transfer | **Effectful shell (new)** | A real on-chain transfer from a citizen's own wallet to cover a deploy's escrow/deposit, gated on REQ-102's already-certified amount (REQ-304). |
| Spawn ledger append | **Effectful shell (existing, reused unmodified)** | `~/anicca/skills/self/spawn/lib/ledger.js::appendChild`/`readChildren` — append-only JSONL, already implemented. |
| $0-bootstrap independent on-chain re-verification | **Effectful shell (new)** | A fresh RPC `eth_call`/balance read performed independently of either trading party's self-report, mirroring the exact method SPEC.md §9.9 already used to confirm Franklin#1's final USDC balance (REQ-401). |
| Wallet mutual non-interference audit | **Effectful shell + static analysis (new)** | A grep-based static source audit (Tier 0) PLUS a live runtime comparison of resolved signing keys across N ≥ 2 concurrently-running instances (Tier 2/3) — reusing the exact "grep all path forms across skill scripts and cron config" method this project's own wallet-rotation work already established (REQ-403). |
| REQ-104 (bookkeeping-only design constraint) | **Not code — a design constraint, verified structurally** | Directly analogous to `anicca-agent-economy`'s REQ-203 ("Design-constraint requirement — bookkeeping only, never judgment"): not independently unit-testable in the normal sense; verified by a Phase 3 structural code read (no scoring/ranking/preference logic anywhere in REQ-101-103's diff), not a runtime assertion. |

---

## Requirements

### REQ群A: 決定論 treasury ゲート

### REQ-101: Colony self-funded surplus aggregation
**EARS**: WHEN any component needs to know how much surplus the colony has available to fund a new
spawn, THE SYSTEM SHALL compute it as the sum, over every **self-funded** citizen only (per
`isSelfFunded()`, `~/anicca/skills/_shared/lib/is-self-funded.mjs`, reused unmodified), of
`max(0, balance_i − perCitizenReserveUsd)`, where `balance_i` is that citizen's own most-recently-read
liquid balance (read from its own `state/telemetry.json`, the same file the existing
`economy/ubi/run.sh` already reads) and `perCitizenReserveUsd` defaults to `5.00` (reusing, for
consistency, the exact `RESERVE = 5.0` constant `economy/ubi/run.sh` already uses for the same
"don't count money a citizen needs for its own survival" purpose — not a new number invented for this
feature).

**Edge Cases**:
- A citizen's `telemetry.json` is missing, unreadable, or its `balance_usd` field is
  missing/non-finite/negative: that citizen contributes **0** to the sum (fail-closed — never treated
  as infinite/unknown-but-fine), matching the existing `tier.mjs`/`catalog-gate.mjs` convention of
  "unparseable numeric input collapses to the safe default," here the safe default being "counts for
  nothing until it can be read cleanly."
- claude-p, or any other agent whose `is_self_funded` gate returns `false`, appears in the same
  telemetry-file directory listing (e.g. `$HOME/.anicca-founder/state/telemetry.json`, which
  `economy/ubi/run.sh` already reads for an unrelated purpose): THE SYSTEM SHALL exclude it from this
  sum unconditionally — this is the concrete mechanism enforcing SPEC.md §0's HARD invariant inside
  this specific computation, not merely a policy statement elsewhere.
- Exactly one self-funded citizen exists (current colony state, per §9.9/§9.5): the sum degenerates to
  that single citizen's own surplus-above-reserve; the formula requires no special case for N=1.
- A citizen's balance is reported in a non-USD-denominated field only (e.g. only `balance_native`):
  the aggregation MUST use the same USD-normalization `economy/ubi/run.sh` already performs (its own
  `bal()` helper's fallback to `balance_native.usdc`) rather than inventing a second conversion path.

**Acceptance Criteria**:
- Pure function, e.g. `computeColonySurplusUsd({ citizens, perCitizenReserveUsd }) → number`, takes
  already-fetched balance data as input and performs zero I/O itself.
- Given two self-funded citizens with balances `$8` and `$3` and `perCitizenReserveUsd=5`, returns
  `max(0,8-5) + max(0,3-5) = 3 + 0 = 3`.
- Given a citizen whose `isSelfFunded()` check returns `false`, its balance (however large) contributes
  `0` regardless of magnitude.

---

### REQ-102: Deterministic spawn threshold gate
**EARS**: WHEN REQ-101's colony surplus is computed, THE SYSTEM SHALL permit at most one new spawn
attempt when, and only when, `colonySurplusUsd >= SPAWN_THRESHOLD_USD` AND at least
`SPAWN_COOLDOWN_DAYS` (default `14`, reusing the exact `rateLimitDays` value already used by
`spawn-decision.js`) have elapsed since the colony's last spawn attempt (success OR failure — see
REQ-305) AND fewer than `MAX_CONCURRENT_SPAWNS` (default `1`) children are currently in
`"provisioning"` state.

`SPAWN_THRESHOLD_USD = MIN_SHELTER_USD * SAFETY_MARGIN_MULTIPLIER`, where:
- `MIN_SHELTER_USD` defaults to `5.00` — a provisional anchor, NOT a live-market-verified figure
  (deliberately, since Nosana/Akash CPU-only small-workload pricing floats with AKT/SOL/NOS market
  price and is not fixed to USD — see the re-verification table above). It reuses the same
  order-of-magnitude anchor as REQ-101's `perCitizenReserveUsd` for internal consistency rather than
  inventing an unrelated number. **This default MUST be superseded by `measured_last_shelter_cost_usd`
  — the actual USD-equivalent cost recorded by REQ-303's shelter-cost ledger after the first real
  deploy — the moment that ledger has at least one entry** (`MIN_SHELTER_USD = max(measured_last_shelter_cost_usd, 5.00)` once measured; `5.00` alone only before any real deploy has ever happened).
- `SAFETY_MARGIN_MULTIPLIER` defaults to `2` — reusing the exact "2×" convention already documented in
  this project's own `~/anicca/skills/self/spawn/scripts/akt-treasury.sh` (`ACT_BUFFER_UACT`'s comment:
  "target ACT on hand (≥ 2× min_mint so a few deploys never wait)"), applied here to the same
  subsystem's spawn-funding buffer for consistency, not a newly-invented margin.
- Default `SPAWN_THRESHOLD_USD = 5.00 * 2 = 10.00` until a real measured shelter cost exists, after
  which it recomputes from that measured figure.

This is arithmetic bookkeeping (a numeric comparison against an already-known threshold and an
already-known elapsed-time and an already-known in-flight count), not a value judgment about WHETHER
to spawn — see REQ-104.

**Edge Cases**:
- `colonySurplusUsd` is EXACTLY equal to `SPAWN_THRESHOLD_USD`: treated as **eligible** (the boundary
  is inclusive, `>=`, matching the existing `catalog-gate.mjs`/`tier.mjs` "at or above" convention
  already used elsewhere in this codebase for the same class of threshold comparison).
- Two or more spawn evaluations run in the same wake cycle (e.g. because both automaton's and
  Franklin's own loops independently evaluate the colony-wide gate): the gate function ITSELF is pure
  and may return `eligible:true` from both evaluations — REQ-103 is what prevents both from acting on
  that `true` result simultaneously; REQ-102 does not need to know about concurrency.
- `SPAWN_COOLDOWN_DAYS` has NOT elapsed since the last attempt, but `colonySurplusUsd` has grown far
  past the threshold in the meantime: still **not eligible**, `reason:"rate_limited"` — surplus size
  never overrides the cooldown (mirrors `spawn-decision.js`'s existing ordering: balance → rate-limit →
  cap, cooldown is a hard gate regardless of how much surplus exists).
- `MAX_CONCURRENT_SPAWNS` children are already `"provisioning"` (none yet resolved to `"active"` or
  `"failed"`): not eligible, `reason:"max_concurrent_spawns"`, regardless of surplus/cooldown — a
  slow/stuck provisioning attempt does not silently permit unbounded parallel spawns.
- `colonySurplusUsd` is non-finite/negative due to an upstream computation error: treated as `0`
  (fail-closed — never eligible), matching REQ-101's own fail-closed convention.

**Acceptance Criteria**:
- Pure function, e.g. `decideColonySpawn({ colonySurplusUsd, spawnThresholdUsd, lastSpawnAttemptMs,
  nowMs, cooldownDays, childrenProvisioning, maxConcurrentSpawns }) → { eligible: boolean, reason:
  "ok"|"insufficient_surplus"|"rate_limited"|"max_concurrent_spawns" }`, no I/O.
- Order of checks is surplus → cooldown → concurrency cap (each independently testable at its own
  boundary), matching the existing `spawn-decision.js` ordering convention (a broke colony never
  spawns whatever else is true).
- `colonySurplusUsd = spawnThresholdUsd` exactly → `eligible:true`.
- `colonySurplusUsd = spawnThresholdUsd - 0.01` → `eligible:false, reason:"insufficient_surplus"`.

---

### REQ-103: Cross-instance spawn mutual exclusion
**EARS**: WHEN two or more colony instances independently evaluate REQ-102's gate in the same or an
overlapping wake window and BOTH observe `eligible:true`, THE SYSTEM SHALL ensure that at most ONE of
them actually proceeds to REQ-201's identity generation and beyond — the other(s) SHALL detect the
lock is held, decline to proceed, and log a no-op (never silently duplicate a spawn, and never queue
indefinitely waiting for the lock).

This reuses, unmodified, the same generic per-resource file lock already adversary-hardened for the P2
gig board (`~/anicca/skills/economy/gig/lib/lock.mjs`, including its `isLockStale` pure predicate and
its atomic `fs.rename`-based reclaim fix from that lock's own REQ-101), acquired under a new, distinct
lock key (e.g. `"colony-spawn"`) rather than any gig-specific key — this is a new lock KEY on an
EXISTING lock MECHANISM, not new lock-implementation code.

**Edge Cases**:
- Two instances race to acquire the `"colony-spawn"` lock within the same millisecond: POSIX exclusive
  file creation (`fs.open(..., "wx")`, the existing mechanism's own atomicity guarantee) ensures exactly
  one succeeds; the other's `acquire()` call fails immediately (fail-closed, no retry-queue).
- The instance holding the lock crashes mid-spawn (dies before releasing): the existing heartbeat +
  `isLockStale` mechanism reclaims the lock after `staleMs` of no heartbeat, exactly as it already does
  for gig-board operations — REQ-103 does not need a second staleness mechanism.
- A held lock's holder is still genuinely working (heartbeating) well past any naive fixed timeout: per
  the existing `isLockStale` semantics, it is NEVER stolen from while it heartbeats, regardless of
  elapsed wall-clock time — this property is inherited, not re-derived, from the existing lock.

**Acceptance Criteria**:
- The colony-spawn critical section (REQ-201 through REQ-205, and the decision to proceed into REQ-3xx)
  is wrapped by the existing `withGigLock`-equivalent helper (or a directly analogous
  `withColonyLock("colony-spawn", fn)`) using the SAME `lock.mjs` module, not a reimplementation.
- Given two concurrent callers both observing `eligible:true`, an integration test proves exactly one
  reaches REQ-201's wallet-generation step during the run; the other's attempt is recorded as
  `reason:"lock_held"` and makes zero wallet-generation calls.

---

### REQ-104: Design-constraint requirement — bookkeeping only, never judgment
**EARS**: WHERE this increment decides WHETHER a spawn is currently permitted (REQ-101/102/103), THE
SYSTEM SHALL implement that decision exclusively as arithmetic and boolean logic over objective,
already-known bookkeeping facts (aggregate USD surplus, an elapsed-time comparison, an in-flight count,
a lock-held boolean) and SHALL NOT implement, alongside or instead of it, any model-driven judgment
about whether spawning is currently a "good idea," any heuristic scoring of colony health, or any
steering text that asks an LLM to decide the threshold/cooldown/cap values at runtime.

This is the SAME design principle already established and adversary-verified for
`anicca-agent-economy`'s REQ-203 ("bookkeeping only, never judgment" for its catalog eligibility gate)
and is consistent with this project's own hard rule (`~/.claude/rules/building-effective-ai-agents.md`
HARD RULE #1/#2: deterministic code owns arithmetic/bookkeeping; the agent owns everything that is
genuinely a decision). What the agent DOES still decide, entirely inside this deterministic envelope
(per SPEC.md §1.5's "spawn = HYBRID" design), is: *when* (within an eligible wake) to actually invoke
the spawn flow, and *what the child's initial goal framing/prompt should say* — REQ-104 governs only
the eligibility ARITHMETIC, never the agent's own in-envelope choices.

**Edge Cases**:
- A future change that makes `SPAWN_THRESHOLD_USD` itself computed by an LLM call (e.g. "ask the model
  whether $10 is enough") would violate this requirement and must be rejected in review, however
  well-intentioned, exactly as `anicca-agent-economy` REQ-203 rejects a "recommended slot" field.
- This requirement is not independently unit-testable in the normal sense; it is verified via
  structural code review at Phase 3 (grep/read for any LLM call, prompt template, or scoring logic
  inside `decideColonySpawn`/`computeColonySurplusUsd`/the lock-acquisition path), not a runtime
  assertion.

**Acceptance Criteria**:
- `decideColonySpawn` and `computeColonySurplusUsd`'s source contains no network call, no prompt
  string, and no reference to any LLM/inference client.
- The functions' return types carry no free-text "explanation"/"recommendation" field beyond the fixed
  `reason` enum already specified in REQ-102.

---

## REQ群B: 新規 instance identity 生成（P2 実証済み手順の再利用、車輪の再発明禁止）

### REQ-201: Child EVM (Base) wallet generation
**EARS**: WHEN REQ-102/103 jointly permit a spawn attempt to proceed, THE SYSTEM SHALL generate the
child's own secp256k1/Base-EVM keypair via `~/anicca/skills/self/spawn/scripts/gen-wallet.sh`
(existing, unmodified — the exact script this feature's task description names as already-proven),
BEFORE any cloud provisioning or on-chain action for that child occurs, and SHALL verify the resulting
address is a real keccak256-derived Ethereum address (not the script's own documented sha256 fallback,
which is not a valid Ethereum address — see Edge Cases) and is distinct from every existing colony
citizen's own EVM address (reusing `child-spec.js::buildChildSpec`'s existing distinct-wallet
assertion, which already throws if `childWallet === parentWallet`; REQ-201 generalizes that same check
to "distinct from ALL existing citizens," not merely the one parent that happened to initiate the
attempt).

**Edge Cases**:
- The host running `gen-wallet.sh` lacks a real keccak implementation (its own comment: "not a real eth
  addr; smoke-test will warn" is the fallback-sha256 branch) — THE SYSTEM SHALL treat any address
  produced by that fallback path as INVALID and abort the spawn attempt (REQ-305), rather than
  registering an ERC-8004 identity or funding a wallet that cannot actually be an Ethereum address.
  This makes the script's own existing "warn" comment into a hard, machine-enforced abort at the
  calling layer, since `gen-wallet.sh` itself only warns.
- The generated address happens to collide with an existing citizen's address (secp256k1
  birthday-collision, astronomically unlikely but checked defensively): abort and regenerate — never
  proceed with a colliding wallet.
- The private key material must never appear in any log file, stdout capture that reaches persistent
  logs, or process list — the caller MUST redirect `gen-wallet.sh`'s stdout directly to a 600-perm file
  (the script's own header comment already states this constraint; REQ-201 makes the CALLER's
  compliance with it a binding acceptance criterion, not merely documentation).

**Acceptance Criteria**:
- `gen-wallet.sh`'s output JSON (`{address, private_key, public_key}`) is captured directly into a
  600-perm file path under the child's own isolated `$HOME` (REQ-203), never echoed to a shared log.
- The address independently re-derives to the same value under a second, independent keccak
  implementation (cross-check), matching the existing SKILL.md's own stated verification method
  ("address derives identically under ethers v6 — cross-checked").

---

### REQ-202: Child Solana keypair generation (conditional)
**EARS**: IF the child instance's initial skill set includes any Solana-settled capability (e.g. a
`sol-trade`-class skill, matching Franklin's own existing dependency on a Solana wallet at
`~/.blockrun/.solana-session`) OR the child will be deployed via Nosana (REQ-302, which itself requires
a Solana-funded wallet per the re-verified quick-start docs above), THE SYSTEM SHALL also generate a
fresh, locally-generated, non-custodial Solana Ed25519 keypair for the child, using the same
generation-discipline as REQ-201 (fresh entropy, 600-perm temp file, never logged) — reusing Nosana's
own CLI convention (auto-generating `~/.nosana/.nosana_key.json` on first run, re-confirmed live
2026-07-07) as the evidence that "wallet-per-instance, zero signup, locally generated" is the current,
live norm this feature's own generation script should match, rather than a bespoke design.

**Edge Cases**:
- The child needs NEITHER a Solana-settled skill NOR Nosana deployment (e.g. it is deployed via Akash
  only, with an EVM-only initial skill set): THE SYSTEM SHALL skip Solana keypair generation entirely
  — this requirement is conditional, not universal, so a child never holds an unused, unmonitored key
  it has no use for.
- The generated Solana address collides with an existing citizen's Solana address: abort and
  regenerate (same discipline as REQ-201's EVM collision check).

**Acceptance Criteria**:
- A pure conditional check (`needsSolanaWallet({ initialSkills, deployTarget }) → boolean`) determines
  whether this step runs at all, before any key material is generated.
- When it runs, the resulting keypair is captured directly into a 600-perm file under the child's own
  isolated `$HOME` (REQ-203), matching REQ-201's handling exactly.

---

### REQ-203: `$HOME`/`ANICCA_HOME` isolation for the child instance
**EARS**: WHEN the child instance is provisioned, THE SYSTEM SHALL assign it a `$HOME` (or
`ANICCA_HOME`, matching the priority order `~/anicca/skills/earn/lib/resolve-identity.mjs` already
implements: `ANICCA_HOME` explicit override, else `$HOME`-derived default) that is a path DISTINCT from
every existing citizen's own home/`ANICCA_HOME` directory, and no process belonging to the child SHALL
ever be launched with an inherited `HOME`/`ANICCA_HOME` environment variable pointing at any existing
citizen's directory. This exploits, unmodified, the SAME mechanism already relied upon in production:
Franklin's own `BLOCKRUN_DIR = path.join(os.homedir(), '.blockrun')` (verified current 2026-07-07,
`@blockrun/franklin` v3.29.16, `src/config.ts:19`) means setting a distinct `HOME` at process-launch
time gives the child a distinct `.blockrun`/`.anicca` state directory with ZERO code changes to
Franklin itself — exactly the mechanism SPEC.md §1.2 point 3 and §9.9 already describe and this
project's own `resolve-identity.mjs`/`ensure-agent-id.mjs` already gate on for existing instances.

**Edge Cases**:
- The child's assigned `HOME` path is accidentally identical to (or a parent/child directory of) an
  existing citizen's own home path: fail-closed abort BEFORE any wallet material (REQ-201/202) is ever
  written there — this check runs first, before key generation, not after.
- The child process is launched by a supervisor (a cloud-init script, systemd unit, or the Akash/Nosana
  container's own entrypoint — REQ-302/303) that does not explicitly set `HOME`/`ANICCA_HOME` and would
  otherwise inherit whatever default the base image provides: THE SYSTEM SHALL require an EXPLICIT
  environment-variable injection at every such process-launch boundary (verified present in the actual
  SDL/job-definition/cloud-init artifact used for that child, not assumed from a shell default).
- `resolve-identity.mjs`'s existing legacy-path fallback (`effectiveHome === path.join(legacyHome,
  '.blockrun')`) is scoped ONLY to the rightful owner of that exact legacy home — a spawned child with
  a genuinely different `HOME` value already fails that equality check and correctly resolves `null`
  rather than a foreign citizen's key; REQ-203 relies on this EXISTING fail-closed behavior rather than
  re-implementing it.

**Acceptance Criteria**:
- Before any REQ-201/202 key generation, a distinctness check compares the child's proposed
  `HOME`/`ANICCA_HOME` against every currently-known citizen's own value and aborts on any match.
- An integration test launches two processes with two different injected `HOME` values against the
  SAME `resolve-identity.mjs` module and asserts each resolves only its own wallet file, never the
  other's (this is the exact `FIND-001-class` regression test style that module's own header comment
  already documents having fixed once — REQ-203 extends that same test to a THIRD, freshly-spawned
  home directory).

---

### REQ-204: ERC-8004 identity registration for the child
**EARS**: WHEN the child's own EVM wallet (REQ-201) exists and its cloud shelter (REQ-302/303) is
reachable, THE SYSTEM SHALL register the child's ERC-8004 identity by calling `register()` on the
already-live registry contract — mainnet `0x8004A169FB4a3325136EB29fA0ceB6D2e539a432` (Base, chain
8453) or testnet `0xdc527768082c489e0ee228d24d3cfa290214f387` (Base-Sepolia, chain 84532), selected by
the same `GIG_CHAIN` env toggle the existing `~/anicca/skills/economy/gig/lib/identity.mjs` already
uses — reusing that module's `registerIdentity()` function UNMODIFIED, signed with the child's OWN
private key (`msg.sender` = the child's own address, matching the existing "each agent registers
itself" discipline), and SHALL record the returned `agentId` and transaction hash in the spawn ledger
(REQ-305) before the child may be marked `"active"`.

**Edge Cases**:
- `register()` reverts for insufficient gas (the child's fresh wallet starts at exactly `0 ETH`): THE
  SYSTEM SHALL fund it with a ONE-TIME, minimal gas seed transferred from a self-funded citizen's own
  wallet — sized to cover exactly one `register()` call plus the child's first gig-board interaction,
  the SAME class of transfer SPEC.md §9.9 already performed and evidenced on-chain (tx `0x48d49e…`
  /`0x1478758…`), never an open-ended top-up, and never sourced from a human-funded wallet (REQ-304
  governs the funding SOURCE constraint).
- The registration transaction succeeds but its `Registered` event cannot be decoded (a malformed/odd
  log): treated as a REQ-305 failure (no `agentId` recorded), never a fabricated/guessed agentId.
- The SAME child wallet somehow already holds an agentId (should be impossible for a genuinely fresh
  key, but checked defensively via `verifyIdentity`/`ownerOf` before calling `register()` a second
  time): skip re-registration, reuse the existing agentId, log the anomaly for audit.

**Acceptance Criteria**:
- `registerIdentity({ privateKey: childPrivateKey })` is called with no modification to
  `identity.mjs`'s existing signature/ABI/registry-address constants.
- A successful registration produces a real, independently-re-verifiable transaction hash and a
  numeric `agentId`; both are appended to the spawn ledger (REQ-305) in the same row that eventually
  marks the child `"active"`.

---

### REQ-205: gig-board MCP configuration for the child
**EARS**: WHEN the child instance boots inside its cloud shelter, THE SYSTEM SHALL write it an
`mcp.json` in the exact shape of the already-live, verified `~/.blockrun/mcp.json`
(`mcpServers.<name>.{transport:"stdio", command:<node path>, args:[<child's OWN
economy/gig/mcp-server.mjs path>], env:{GIG_FACILITATOR_URL, GIG_STATE_PATH, GIG_CHAIN}}`), with
`GIG_STATE_PATH` pointing at a state file location UNIQUE to the child (under its own isolated `$HOME`,
REQ-203 — never the shared `~/.anicca-signing/gig-board/state/gigs.json` path an existing citizen
already uses unless the gig board is explicitly colony-shared by design) and `GIG_FACILITATOR_URL`
pointing at the colony's existing, live self-host facilitator, so the child's own Franklin process
discovers the gig-board MCP server through the exact same startup-discovery mechanism SPEC.md §9.1
already documents ("append to `~/.blockrun/mcp.json`... Franklin が起動時 discovery"), with ZERO
modification to Franklin's own source required.

**Edge Cases**:
- `GIG_STATE_PATH` is accidentally set to an existing citizen's own state file path (a template
  copy-paste bug): THE SYSTEM SHALL verify the resolved path is unique to this child before the file is
  first written — a collision here would let the child observe/mutate another citizen's gig-board state,
  which REQ-403's audit must also be able to catch independently.
- The facilitator URL is unreachable at the child's first boot: this is NOT an REQ-205 failure by
  itself (REQ-205 only specifies that the config POINTS at a real, currently-live endpoint at write
  time) — the child's own gig `run.sh` already fail-closes on an unreachable facilitator per its
  existing, unmodified discipline ("no signing key resolved ... fail closed").

**Acceptance Criteria**:
- The written `mcp.json` parses as valid JSON and validates against the same shape as the existing
  `~/.blockrun/mcp.json` (same top-level keys, same env-var names).
- `GIG_STATE_PATH`'s resolved absolute path is verified, at write time, to be different from every
  other currently-known citizen's own `GIG_STATE_PATH`.

---

## REQ群C: cloud deployment（新規、local 禁止）

### REQ-301: Local spawn is structurally forbidden
**EARS**: THE SYSTEM SHALL NOT provision any child instance's runtime, wallet material (beyond the
ephemeral REQ-201/202 generation step, which MAY run on whichever host initiates the spawn attempt,
provided the generated key is immediately relocated into the child's own isolated `$HOME` and never
persisted under the initiating host's own home), or persistent state on the same physical/virtual host
as any existing colony citizen's own runtime. Every child SHALL be deployed exclusively via REQ-302
(Nosana) or REQ-303 (Akash) — reusing SPEC.md §3 P3's own stated rationale ("spawn は local
禁止（disk を埋めて崩壊）") — never onto the machine currently running the spawning process itself.

**Edge Cases**:
- A spawn attempt is initiated from a laptop/Mac Mini host that ALSO happens to run an existing
  citizen (the current colony's actual topology): the child's own long-running process/state MUST
  still end up exclusively on the cloud lease, never left running on that initiating host after the
  spawn attempt completes (success or failure).

**Acceptance Criteria**:
- Structural/Tier-0 check: reading the deploy code path confirms the only two artifacts the initiating
  host retains after a spawn attempt are (a) the spawn ledger row and (b) nothing else persistent for
  that child — no child-specific systemd/launchd unit, no lingering child process, on the initiating
  host.

---

### REQ-302: Nosana deploy path
**EARS**: WHEN a spawn attempt (REQ-102/103) proceeds and Nosana is the selected cloud target for that
attempt, THE SYSTEM SHALL provision the child's compute using the Nosana CLI (`@nosana/cli`, confirmed
current 2026-07-07 per the re-verification table above; installed via `npm install -g @nosana/cli`),
pointed at the child's OWN pre-generated, isolated Solana keypair (REQ-202) — via whatever
env/flag the installed CLI version exposes for supplying an existing key file — rather than letting the
CLI auto-generate a NEW keypair inside the invoking process's own default `~/.nosana/` path (which
would violate REQ-203's isolation guarantee by creating key material outside the child's own isolated
`$HOME`), and SHALL post the deploy job with `nosana job post <command> --market <marketAddress> --wait`,
verifying a `RUNNING`/`COMPLETED` job status and a real, resolvable job ID/URL (per the documented
output format: `Job: https://explore.nosana.com/jobs/<id>`) before considering this leg successful.

**Edge Cases**:
- The child's Solana wallet lacks sufficient NOS/SOL to cover the selected market's posted price at
  submission time: job post fails immediately (documented CLI behavior) — treated identically to
  REQ-305's deploy-failure path, no partial success recorded.
- No open market/node is available at an acceptable price within a bounded poll/retry window: same
  failure path — REQ-302 does not silently fall back to a different market tier without that being an
  explicit, separately-specified policy (out of scope for this first increment; a single documented
  default market is used).
- The job's `Result`/exit status is non-zero (the child's boot script itself failed inside the leased
  container): treated as a deploy failure even though the Nosana JOB itself completed — REQ-302's
  success criterion is "the child's own process is actually running," not merely "Nosana accepted the
  job."

**Acceptance Criteria**:
- The deploy step never reads or writes any file under the invoking host's own default `~/.nosana/`
  directory when acting on behalf of a child — a distinctness check analogous to REQ-201/203's.
- A successful deploy yields a real job ID that independently resolves via
  `https://explore.nosana.com/jobs/<id>` (or the equivalent current CLI "get job" query) to a
  `RUNNING`/`COMPLETED` status, not merely a locally-logged claim.

---

### REQ-303: Akash deploy path (reuse existing, already-implemented scripts)
**EARS**: WHEN a spawn attempt proceeds and Akash is the selected cloud target for that attempt, THE
SYSTEM SHALL provision the child's compute using the existing, already-implemented
`~/anicca/skills/self/spawn/scripts/deploy-akash.sh` (`provider-services` CLI, confirmed still the
current, officially-documented Akash deployment CLI per the re-verification table above) together with
`~/anicca/skills/self/spawn/scripts/akt-treasury.sh` (ACT top-up via `akash tx bme mint-act`, confirmed
still current), REUSING both scripts UNMODIFIED for the deployment-create → bid-poll → lease-create →
manifest-send flow, substituting only the child's own `CHILD_ID` and the child's own SDL (the existing
image-independent template — public `node:22-bookworm` base, `git clone` of the OSS repo at boot — is
reused as-is unless a child-specific variant is explicitly required). THE SYSTEM SHALL record the
actual `AKASH_DEPOSIT` escrowed and, once observable, the real settled lease cost, into a persistent
shelter-cost ledger that REQ-102's `measured_last_shelter_cost_usd` mechanism reads.

**Edge Cases**:
- The signing wallet's `uact` (ACT) balance is below `AKASH_DEPOSIT` at spawn time: `akt-treasury.sh`
  MUST be run and its EXECUTED (not CANCELED — the script's own documented balance-delta check)
  outcome confirmed BEFORE `deploy-akash.sh` is invoked; if the mint cancels (output below
  `bme.params.min_mint`), THE SYSTEM SHALL treat this as a deploy failure (REQ-305) and never fabricate
  a `dseq`.
- No open bid appears within `deploy-akash.sh`'s existing poll window (30 attempts, existing default
  sleep): the script's own existing fail-closed behavior (non-zero exit, no dseq printed) is reused
  as-is; REQ-303 adds no new retry logic beyond what already exists.
- `send-manifest` fails after its existing retry budget (5 attempts): treated as a deploy failure even
  though the lease itself is technically active — a leased-but-unmanifested deployment is not a running
  child and MUST NOT be marked `"active"`.

**Acceptance Criteria**:
- `deploy-akash.sh CHILD_ID` and `akt-treasury.sh` are invoked with no source modification; their
  existing exit-code/stdout contract (dseq on stdout, non-zero exit + stderr message on any failure) is
  the sole success/failure signal this feature reads.
- The real `AKASH_DEPOSIT` amount and (once queryable) the real settled lease cost are appended to a
  shelter-cost ledger file that REQ-102 reads on its NEXT evaluation — the very first spawn therefore
  uses the provisional `$5.00`/`$10.00` defaults, and every subsequent evaluation uses real measured
  data once at least one successful deploy exists.

---

### REQ-304: Shelter cost is funded only from treasury-gate-approved surplus
**EARS**: THE SYSTEM SHALL NOT fund any REQ-302/303 deploy (nor REQ-204's gas seed) from any single
citizen's own `perCitizenReserveUsd` (the amount REQ-101 excludes from the aggregate precisely because
it is that citizen's own survival reserve) or from any human-funded wallet (claude-p's or any other);
funding SHALL draw only from the aggregate surplus REQ-102 already certified as available for THAT
spawn attempt, and by an amount not exceeding what REQ-102 approved.

**Edge Cases**:
- The approved aggregate surplus is spread across multiple citizens' wallets and no single citizen
  individually holds the full deploy cost: THE SYSTEM SHALL fund from whichever citizen(s)
  INDIVIDUALLY hold sufficient surplus-above-reserve to cover the cost alone (a single-signer,
  single-transaction transfer, matching the existing gojo/rescue transfer pattern already used in
  `economy/ubi/run.sh`), rather than attempting a new multi-wallet pooled transaction mechanism — this
  feature deliberately does not build multi-signer pooling.
- No single citizen individually holds enough, even though the AGGREGATE clears REQ-102's threshold:
  THE SYSTEM SHALL NOT proceed with the spawn this wake; it is logged as a funding-shortfall no-op
  (distinct from REQ-305's provisioning-failure state — no child record is even created), and
  re-evaluated on a future wake once some citizen's individual surplus alone suffices, or once the
  colony has more than one surplus-holding citizen able to co-fund via two SEPARATE single-signer
  transfers to the SAME child wallet (still no pooling — sequential individual transfers are allowed;
  a single joint transaction is not required and is explicitly out of scope).

**Acceptance Criteria**:
- Every on-chain transfer this feature initiates carries a memo/log entry naming (a) the REQ-102
  decision it was approved under and (b) the paying citizen's own identity — auditable after the fact.
- A structural/Tier-0 check confirms no code path in this feature ever reads a human-funded wallet's
  private key or balance as a funding source.

---

### REQ-305: Deploy/spawn failure handling — no partial spawn
**EARS**: IF any step from REQ-201 through REQ-303 fails, THE SYSTEM SHALL leave no ledger entry
claiming the child is `"active"`; a partially-completed attempt SHALL be recorded with status
`"failed"` (or `"provisioning"` only while genuinely still in progress, per the existing
`child-spec.js::buildChildSpec`'s own `status:"provisioning"` initial value) together with the
specific failing step and error message, any already-spent, non-refundable resource (e.g. an Akash
deployment deposit not yet converted into an active lease) SHALL be logged for colony accounting, and
REQ-102's `SPAWN_COOLDOWN_DAYS` timer SHALL NOT be considered "consumed" by a failed attempt — mirroring
this project's existing HARD RULE 0.24 ("NO FAKE RUN... any failed step exits non-zero and leaves an
honest provisioning/failed ledger row, never a fabricated success").

**Edge Cases**:
- The cloud deploy (REQ-302/303) succeeds but ERC-8004 registration (REQ-204) subsequently fails: the
  child remains `"provisioning"`, is EXCLUDED from REQ-101's colony-surplus aggregation (it is not yet
  a citizen), and registration is retried up to a bounded retry window (to avoid wasting an
  already-paid, non-refundable lease) before the lease itself is torn down and the attempt marked
  `"failed"`.
- A failed attempt's cooldown-exemption (above) could in principle be exploited to attempt unlimited
  spawns by engineering repeated "failures": THE SYSTEM SHALL cap the number of failed attempts counted
  within any single `SPAWN_COOLDOWN_DAYS` window (default cap `3`) — beyond that cap, further attempts
  within the window ARE rate-limited exactly as a successful spawn would be, closing this gap.

**Acceptance Criteria**:
- A structural/Tier-0 check of the ledger-writing code path confirms every write path that can leave a
  row behind sets `status` to one of `{"provisioning","active","failed"}` — never omits `status`, and
  never writes `"active"` from any branch that has not completed REQ-204+REQ-205.
- An integration test that injects a failure at each of REQ-201/202/203/204/205/302/303 in turn
  confirms the resulting ledger row's `status` and `error` fields correctly identify the failing step,
  and that REQ-101's next aggregation run excludes that child.

---

## REQ群D: $0-bootstrap 実証

### REQ-401: $0-bootstrap success criterion
**EARS**: WHEN a child instance has been marked `"active"` (REQ-204/205 complete), THE SYSTEM SHALL
consider its $0-bootstrap successful only when — using EXCLUSIVELY the `"free-model"` fuel provider
(the same `OWN_FUNDED_FUEL_PROVIDERS` entry `~/anicca/skills/_shared/lib/is-self-funded.mjs` already
defines) and its own wallet, with no funding beyond the one-time gas seed already recorded under REQ-204
— it achieves a first realized, on-chain gig settlement (`~/anicca/skills/economy/gig`) with a real
positive amount, resulting from the CHILD'S OWN autonomous `post`/`take`/`deliver`/`verify_and_pay`
participation (not one initiated/executed on its behalf by a parent or by this feature's own tooling —
matching SPEC.md §9.9's precedent that the measured event is the AGENT's own choice, not a scripted
proxy for it).

**Edge Cases**:
- The child's first realized gig counterparty is the SAME citizen that spawned it (plausible when only
  2-3 citizens exist): still counts — what is measured is the CHILD's own autonomous participation, not
  counterparty diversity — but the settlement itself MUST be independently re-verified via a fresh RPC
  balance read taken before and after (mirroring the exact method SPEC.md §9.9 already used to confirm
  Franklin#1's final `0.02` USDC balance via `eth_call balanceOf`), never accepted from either party's
  own self-report.
- The child never once selects the gig skill from its own available catalog within the bootstrap window
  (the exact "model doesn't autonomously select the slot" frontier SPEC.md §9.6 already documented and
  is still resolving for automaton as of this spec's writing): THIS IS NOT a defect to be worked around
  by this feature hardcoding a forced selection or scripted proxy call — doing so would violate this
  project's HARD RULE that judgment/selection belongs to the model, not to hardcoded control flow
  (`~/.claude/rules/building-effective-ai-agents.md` #1). REQ-402 defines the bookkeeping consequence of
  this outcome instead.
- Genuinely free inference becomes unavailable for the child's entire bootstrap window (upstream
  outage, e.g. the historical `nvidia/llama-4-maverick` 403 SPEC.md §9.2 already documented and fixed
  once): treated the same as REQ-402's timeout path — a bookkeeping fact, not blamed on the child.

**Acceptance Criteria**:
- Success is recorded only once an independent RPC call (not the gig board's own internal ledger alone)
  confirms the child's wallet balance increased by the settled amount.
- The ledger entry recording success references: the gig ID, the on-chain transaction hash, the balance
  delta as independently observed, and a timestamp — enough for a fresh adversary to re-derive the
  claim without trusting this feature's own self-report.

---

### REQ-402: Bootstrap failure/timeout handling
**EARS**: IF a child instance marked `"active"` has NOT achieved REQ-401's success criterion within
`BOOTSTRAP_WINDOW_DAYS` (default `14`, reusing REQ-102's own `SPAWN_COOLDOWN_DAYS` constant for
internal consistency rather than inventing an unrelated window), THE SYSTEM SHALL relabel that child
`"bootstrap_failed"` in the ledger (never silently delete or destroy the child, its wallet, or its
cloud lease), SHALL EXCLUDE it from REQ-101's colony-surplus aggregation until it produces its own
first realized settlement (it does not count as a "productive" self-funded citizen while
`"bootstrap_failed"`, though its wallet may still technically satisfy `isSelfFunded()`'s structural
test — REQ-402 adds a SEPARATE productivity flag, not a change to that existing gate), and SHALL feed
this outcome to REQ-102's NEXT gate evaluation only as a bookkeeping count (`children_bootstrap_failed`)
— never as an automatic trigger to spawn a replacement (that remains gated purely by REQ-102's own
arithmetic, unaffected by how many prior attempts failed).

**Edge Cases**:
- The child achieves REQ-401's criterion on day 15 (just past the window): the `"bootstrap_failed"`
  label is corrected to reflect success retroactively the moment the on-chain settlement is
  independently observed — the window gates a BOOKKEEPING classification (whether it currently counts
  toward the colony's productive surplus), not a hard kill-switch that destroys the child at day 14.
- Two or more children are simultaneously `"bootstrap_failed"`: each is tracked independently by its
  own `child_id`; this requirement does not rank, compare, or triage them against each other (no
  judgment call — consistent with REQ-104's bookkeeping-only design constraint).
- A `"bootstrap_failed"` child's cloud lease continues to accrue cost indefinitely with no plan to ever
  retry: THE SYSTEM SHALL record this state plainly (it is a real, ongoing colony cost) but this feature
  does NOT specify an automatic lease-teardown-on-bootstrap-failure policy — that decision is left to
  a future increment (P4/self-repair) or explicit operator action, to avoid this feature silently making
  an irreversible "give up on this child" judgment call of its own.

**Acceptance Criteria**:
- A scheduled/wake-triggered check compares `now - active_since` against `BOOTSTRAP_WINDOW_DAYS` for
  every `"active"` child lacking a recorded REQ-401 success, and flips exactly those past the window to
  `"bootstrap_failed"` — no others.
- REQ-101's aggregation function, given a child flagged `"bootstrap_failed"`, excludes its balance from
  the productive-surplus sum even if that balance is nonzero (e.g. residual gas-seed dust).

---

### REQ-403: Wallet mutual non-interference audit
**EARS**: WHEN N ≥ 2 instances (any mix of pre-existing citizens and newly-spawned children) run
concurrently, THE SYSTEM SHALL provide a deterministic audit — combining (a) a static, grep-based
source audit across every skill script and cron/job config, checking all three path-reference forms
(`$HOME/...`, `~/...`, and the fully-resolved absolute form), reusing the exact method this project's
own wallet-rotation work already established (memory
`feedback_move_refcheck_must_cover_skill_scripts_and_home_forms`: "grep ~/.openclaw/skills +
~/anicca/skills + cron in ALL 3 path forms") with (b) a live runtime comparison — reusing
`resolve-identity.mjs`'s existing exported resolvers, invoked once per running instance with that
instance's OWN `HOME`/`ANICCA_HOME` — that PROVES no two instances' resolved EVM or Solana signing keys
are ever equal, and no instance's resolved key-file PATH ever points inside another instance's own
home directory, before any newly-spawned child is permitted to participate in REQ-401's bootstrap.

**Edge Cases**:
- The static grep audit finds a hardcoded/templated path in a cloud-init script or SDL that could
  resolve to a shared location across children (e.g. a copy-paste bug reusing the SAME literal
  `GIG_STATE_PATH` or wallet-file path across two SDL templates): THE SYSTEM SHALL treat this as a
  BLOCKING finding — the affected child(ren) SHALL NOT be marked `"active"` until fixed, even if no
  actual runtime collision has yet been observed (structural risk is enough to block, not requiring a
  live incident first).
- The live runtime comparison finds an ACTUAL key collision (two instances resolve the identical signing
  key): THE SYSTEM SHALL halt BOTH implicated instances from any further signing immediately (fail-closed
  security-incident response), not merely log a warning and continue.
- A new cloud-host template is added later (e.g. a third provider beyond Nosana/Akash) with a
  different environment-injection mechanism than either already-audited path: THE SYSTEM SHALL require
  the audit to be explicitly extended to that new mechanism before any child deployed via it is trusted
  — silent "probably fine by analogy" reasoning is not permitted for a money-safety check.

**Acceptance Criteria**:
- A repeatable audit script exists that, given the current set of running instances' own `HOME` values,
  (1) runs the static grep sweep and reports zero cross-instance path references, and (2) invokes
  `resolveEvmPrivateKey`/`resolveSolanaSecret` once per instance's own `HOME` and asserts pairwise
  inequality across all resolved keys.
- Given a deliberately-injected test fixture where two fake instances share a `HOME` (negative test),
  the audit correctly reports a collision — proving the check is not vacuously passing.
