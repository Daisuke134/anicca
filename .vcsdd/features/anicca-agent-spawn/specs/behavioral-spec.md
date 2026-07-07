# Behavioral Spec — anicca-agent-spawn (Phase 1a)

**feature**: anicca-agent-spawn · **mode**: strict · **increment**: P3 spawn (colony-treasury-gated,
cloud-only) + $0-bootstrap verification · **日付**: 2026-07-07 · **revision**: iteration 2, revised
(spec review iteration-1 findings FIND-001..006 resolved AND spec review iteration-2 findings
FIND-101..104 resolved — see changelogs below)

## Changelog (iteration 1 → iteration 2)

Spec review iteration 1 FAILed with 6 findings. Each is resolved by a specific, cited design decision
(not a vague "will fix later"):

| Finding | Severity | Resolution |
|---|---|---|
| FIND-001 | critical | `child-spec.js::buildChildSpec` is corrected from a false "reused unmodified" claim to a small, backward-compatible validation extension (new REQ-206): its identity-anchor requirement now accepts EITHER the old `childInbox` (AgentMail) OR the new `agentEvmAddress`+`agentId` (ERC-8004) pair — never both required. |
| FIND-002 | critical | The dynamic citizen registry is specified explicitly (new REQ-105): a brand-new, dedicated registry file (`~/anicca/skills/self/spawn/registry/citizens.json`) holds an array of `{id, wallet, walletAddress, fuel, humanDependencies, telemetryPath}` records that `isSelfFunded()` can consume directly; REQ-305 appends a new record to it on every successful spawn. |
| FIND-003 | major | This increment's scope is explicitly narrowed (new REQ-106): all REQ-101/102/103 evaluation happens on ONE designated coordinator host (the Mac Mini already running automaton); cloud-deployed children never evaluate the colony-spawn gate themselves in this increment (spawn chaining is out of scope, deferred). This is what makes `lock.mjs`/`ledger.js` (local-filesystem primitives) correct as specified. |
| FIND-004 | medium | REQ-204's "already-registered" defensive edge case is rewritten to reuse the existing, already-tested `~/anicca/skills/economy/gig/lib/ensure-agent-id.mjs::ensureAgentId` wrapper instead of re-deriving the same cache/verify/register-once logic from scratch. |
| FIND-005 | low | REQ-204's citation of "SPEC.md §9.9" for the gas-seed tx hashes is corrected to the actual section, "SPEC.md §9.6". |
| FIND-006 | medium | The Nosana-vs-Akash cloud-target selection that REQ-302/303 presupposed is now itself specified (new REQ-306): a deterministic, price/availability-based comparison — bookkeeping, never a model judgment call. |

## Changelog (iteration 2 spec review, round 1 → round 2)

Iteration 2's spec review FAILed with 4 findings (all 6 iteration-1 findings above were reconfirmed
genuinely resolved). Each is resolved by a specific, cited design decision:

| Finding | Severity | Resolution |
|---|---|---|
| FIND-101 | critical | REQ-105/REQ-305 STOP repurposing the pre-existing, live `~/anicca/skills/economy/ubi/colony-wallets.json` (whose 2nd entry is claude-p's own human-funded wallet, and which `ubi.js::distributeAI` already uses for a different, unrelated purpose). A brand-new, dedicated file — `~/anicca/skills/self/spawn/registry/citizens.json` — is introduced instead, seeded with a fixed literal 2-entry array (no migration, no ambiguous classification step), and REQ-305's append path now calls `isSelfFunded()` on any new entry before appending, refusing the append if it returns `false`. |
| FIND-102 | major | REQ-206's EARS clause is corrected to remove its self-contradiction with its own edge case: "at least one of these two anchors" is now stated explicitly as a non-exclusive minimum (both anchors present simultaneously is accepted, not an error), with a new acceptance criterion and PROP-206e covering exactly that path. |
| FIND-103 | major | REQ-103 now names the canonical `statePath` every colony-spawn lock caller MUST use — REQ-105's `citizens.json` path, exported as a single constant `CITIZENS_REGISTRY_PATH` from a new shared module `~/anicca/skills/self/spawn/lib/registry-path.mjs` — closing the "mismatched statePath silently defeats mutual exclusion" gap. |
| FIND-104 | medium | The citizen-registry record's `wallet` field is split into two separate fields: `wallet: {evm?: boolean, solana?: boolean}` (matching `is-self-funded.mjs::hasOwnWallet()`'s real, documented boolean contract exactly) and `walletAddress: {evm?: string, solana?: string}` (the actual address string(s), never passed to `isSelfFunded()`). |

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
Reusing those primitives is NOT always "unmodified" — see REQ-206 for the one, small,
backward-compatible exception (`child-spec.js`'s identity-anchor validation).

**Single-coordinator-host scope constraint (added iteration 2, resolves FIND-003)**: this increment
does NOT build a multi-host colony-spawn architecture. REQ-106 makes this explicit: every REQ-101/
102/103 evaluation (and the resulting REQ-201-305 execution) runs exclusively on ONE, designated
coordinator host — currently the Mac Mini already running automaton's own loop (this project's own
`CLAUDE.md`: "Mac Mini（`anicca-mac-mini-1`...）で直接実行する"). A cloud-deployed child does NOT
itself evaluate the colony-spawn gate in this increment — spawn CHAINING (a child spawning its own
child) is explicitly deferred to a future increment. This is the scope boundary that makes REQ-103's
`lock.mjs` (a local-POSIX-filesystem primitive) and REQ-305's `ledger.js` (a local append-only file)
correct AS SPECIFIED: neither mechanism needs to serialize/record callers on different physical hosts,
because this increment guarantees there is only ever one evaluator host.

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
| Colony self-funded citizen filter | **Pure core (existing, reused unmodified)** | `~/anicca/skills/_shared/lib/is-self-funded.mjs::isSelfFunded(agent)` — already implements exactly the "own wallet + own-funded fuel + zero human deps" test this feature's REQ-101 needs to decide which balances even count toward the colony surplus. No new judgment logic is written; REQ-101 calls this existing, already-tested function on each RECORD supplied by REQ-105's registry (below) — `isSelfFunded()` itself is untouched; only its INPUT source is now specified. |
| Colony citizen registry (data source for REQ-101) | **Effectful shell (BRAND NEW, dedicated file — REQ-105, revised to resolve FIND-101)** | `~/anicca/skills/self/spawn/registry/citizens.json` — a brand-new file created fresh by this feature, holding an array of `{id, wallet: {evm?: boolean, solana?: boolean}, walletAddress: {evm?: string, solana?: string}, fuel, humanDependencies, telemetryPath}` records — the BOOLEAN-shaped `wallet` field is the exact shape `isSelfFunded()` already requires (resolves FIND-104's type mismatch), `walletAddress` separately carries the real address string(s), and `telemetryPath` feeds REQ-101's balance lookup. Seeded with a FIXED LITERAL 2-entry array (the colony's only currently-verified self-funded citizens) — NOT a migration, and sharing ZERO state with the pre-existing `~/anicca/skills/economy/ubi/colony-wallets.json` (see next row). |
| Pre-existing mutual-aid recipient list (untouched, out of scope) | **Effectful shell (existing, NOT read/written by this feature)** | `~/anicca/skills/economy/ubi/colony-wallets.json` — `ubi.js::distributeAI`'s own recipient-eligibility list ("addresses proven to be real colony members," its own JSDoc), a DIFFERENT purpose than REQ-101's surplus aggregation. Its current 2nd entry is claude-p's own human-funded wallet (`docs/WALLETS.md` lines 49-62). This feature never reads, writes, or repurposes this file — resolves FIND-101's critical finding that an earlier draft wrongly proposed migrating/extending it, which would have risked a human-funded wallet silently entering the colony-surplus aggregate. |
| Colony surplus aggregation | **Pure core (new)** | A sum of `max(0, balance_i - perCitizenReserveUsd)` over self-funded citizens only — deterministic arithmetic over already-fetched balances, no I/O once inputs are supplied (REQ-101). |
| Spawn eligibility gate | **Pure core (new, extends an existing pattern)** | `~/anicca/skills/self/spawn/lib/spawn-decision.js::decideSpawn` already establishes the exact target shape (`{eligible, reason}`, pure, no I/O) this feature's colony-scoped gate follows — REQ-102 is a colony-aggregate generalization of that same pattern, not a new design. |
| Per-child identity record assembly | **Pure core (existing, extended — small, backward-compatible modification, REQ-206)** | `~/anicca/skills/self/spawn/lib/child-spec.js::nextChildId`/`buildChildSpec` — monotonic ID (unchanged) + an identity-anchor validation that now accepts EITHER the old `childInbox` (AgentMail) OR the new `agentEvmAddress`+`agentId` (ERC-8004) pair, never requiring both (REQ-206). This corrects iteration 1's false "reused unmodified" claim (FIND-001): the distinct-wallet assertion and every other existing field/behavior are untouched, and a regression test locks in that today's `childInbox`-only callers still succeed identically. |
| Cross-instance spawn mutual exclusion (lock predicate) | **Pure core (existing, reused unmodified)** | `~/anicca/skills/economy/gig/lib/lock.mjs::isLockStale(nowMs, mtimeMs, staleMs)` — the already-adversary-hardened staleness predicate from the P2 concurrency-hardening sprint (`anicca-agent-economy` REQ-101). REQ-103 reuses the SAME generic file-lock module under a new lock key (`"colony-spawn"`), not a new lock implementation. This module's local-POSIX-filesystem guarantee is sufficient ONLY because REQ-106 scopes every evaluator to a single coordinator host this increment (FIND-003) — it is not claimed to solve cross-host mutual exclusion. |
| Cloud target selection (Nosana vs Akash) | **Pure core (new) + Effectful shell (new)** | A pure comparison function `selectCloudTarget({nosanaAvailable, nosanaPriceUsd, akashAvailable, akashPriceUsd}) → "nosana"\|"akash"\|"none"` (deterministic, price-based, never a model judgment — REQ-306) fed by an effectful price/availability query step against each provider's own CLI/API. Resolves FIND-006 (REQ-302/303 presupposed this selection without ever specifying it). |
| Balance/telemetry reads across colony instances | **Effectful shell** | `fs.readFile` of each citizen's `state/telemetry.json`, located via REQ-105's registry `telemetryPath` field (the exact pattern `~/anicca/skills/economy/ubi/run.sh` already uses to read `$HOME/.automaton/state/telemetry.json` / `$HOME/.blockrun/state/telemetry.json`) — real I/O, not inferred. |
| Child EVM wallet generation | **Effectful shell** | `~/anicca/skills/self/spawn/scripts/gen-wallet.sh` — `openssl`+`python3` subprocess, real entropy source, reused unmodified. |
| Child Solana keypair generation | **Effectful shell (new)** | New script analogous to `gen-wallet.sh` but ed25519/Solana-shaped (REQ-202); real entropy source. |
| `$HOME`/`ANICCA_HOME` isolation at process launch | **Effectful shell** | Setting an env var at process spawn time is an OS-level side effect; the isolation PROPERTY it produces (a distinct resolved path) is what REQ-203 specifies and what `~/anicca/skills/earn/lib/resolve-identity.mjs` already relies on for existing instances. |
| ERC-8004 `register()` | **Effectful shell (existing, reused unmodified)** | `~/anicca/skills/economy/gig/lib/identity.mjs::registerIdentity`/`verifyIdentity`, called THROUGH the existing, already-tested `~/anicca/skills/economy/gig/lib/ensure-agent-id.mjs::ensureAgentId` cache-then-verify-then-register-once wrapper (not re-derived from scratch — resolves FIND-004) — a real on-chain transaction (mainnet registry `0x8004A169FB4a3325136EB29fA0ceB6D2e539a432` on Base, chain 8453; testnet `0xdc527768082c489e0ee228d24d3cfa290214f387` on Base-Sepolia; both independently re-verified live 2026-07-07 per that file's own header). |
| gig-board `mcp.json` generation | **Effectful shell (new, template reused)** | File write following the exact shape of the already-live, verified `~/.blockrun/mcp.json`. |
| Nosana job deploy | **Effectful shell (new)** | Real `nosana job post` subprocess against a real Solana-settled market; genuinely new for this project (REQ-302). |
| Akash job deploy | **Effectful shell (existing, reused unmodified)** | `~/anicca/skills/self/spawn/scripts/deploy-akash.sh` + `akt-treasury.sh` — already implemented, already tested against a real sandbox-2 chain per those scripts' own inline evidence references; reused unmodified with a new child SDL/`CHILD_ID` (REQ-303). |
| Shelter-cost funding transfer | **Effectful shell (new)** | A real on-chain transfer from a citizen's own wallet to cover a deploy's escrow/deposit, gated on REQ-102's already-certified amount (REQ-304). |
| Spawn ledger append | **Effectful shell (existing, reused unmodified) + a new registry-append side effect (REQ-105/305)** | `~/anicca/skills/self/spawn/lib/ledger.js::appendChild`/`readChildren` — append-only JSONL, already implemented, unmodified. On a successful spawn (child marked `"active"`), REQ-305 ALSO appends a new record to REQ-105's colony citizen registry (`~/anicca/skills/self/spawn/registry/citizens.json` — NOT `economy/ubi/colony-wallets.json`, which this feature never touches) — a new, explicit write path this spec did not previously specify (resolves FIND-002's "how does the registry grow" gap), GATED on an `isSelfFunded()` pre-append check that REFUSES the append if the new record would itself fail that gate (resolves FIND-101's permanent-hazard-closure requirement). |
| $0-bootstrap independent on-chain re-verification | **Effectful shell (new)** | A fresh RPC `eth_call`/balance read performed independently of either trading party's self-report, mirroring the exact method SPEC.md §9.9 already used to confirm Franklin#1's final USDC balance (REQ-401). |
| Wallet mutual non-interference audit | **Effectful shell + static analysis (new)** | A grep-based static source audit (Tier 0) PLUS a live runtime comparison of resolved signing keys across N ≥ 2 concurrently-running instances (Tier 2/3) — reusing the exact "grep all path forms across skill scripts and cron config" method this project's own wallet-rotation work already established (REQ-403). |
| REQ-104 (bookkeeping-only design constraint) | **Not code — a design constraint, verified structurally** | Directly analogous to `anicca-agent-economy`'s REQ-203 ("Design-constraint requirement — bookkeeping only, never judgment"): not independently unit-testable in the normal sense; verified by a Phase 3 structural code read (no scoring/ranking/preference logic anywhere in REQ-101-103's diff), not a runtime assertion. |

---

## Requirements

### REQ群A: 決定論 treasury ゲート

### REQ-101: Colony self-funded surplus aggregation
**EARS**: WHEN any component needs to know how much surplus the colony has available to fund a new
spawn, THE SYSTEM SHALL compute it as the sum, over every **self-funded** citizen only (per
`isSelfFunded()`, `~/anicca/skills/_shared/lib/is-self-funded.mjs`, reused unmodified, called on each
record supplied by REQ-105's colony citizen registry — the candidate citizen list itself is READ from
that registry, never hardcoded inline in this aggregation), of `max(0, balance_i −
perCitizenReserveUsd)`, where `balance_i` is that citizen's own most-recently-read liquid balance
(read from its own `state/telemetry.json`, located via REQ-105's registry `telemetryPath` field —
the same file the existing `economy/ubi/run.sh` already reads) and `perCitizenReserveUsd` defaults to
`5.00` (reusing, for consistency, the exact `RESERVE = 5.0` constant `economy/ubi/run.sh` already uses
for the same "don't count money a citizen needs for its own survival" purpose — not a new number
invented for this feature).

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
- Two or more spawn evaluations run in the same wake cycle (e.g. because two independently-scheduled
  loops on the SAME coordinator host, per REQ-106, both evaluate the colony-wide gate — this increment
  never has evaluations racing across DIFFERENT physical hosts, see REQ-106): the gate function ITSELF
  is pure and may return `eligible:true` from both evaluations — REQ-103 is what prevents both from
  acting on that `true` result simultaneously; REQ-102 does not need to know about concurrency.
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
**EARS**: WHEN two or more evaluation LOOPS — always running on the SAME single coordinator host per
REQ-106, this increment — independently evaluate REQ-102's gate in the same or an overlapping wake
window and BOTH observe `eligible:true`, THE SYSTEM SHALL ensure that at most ONE of them actually
proceeds to REQ-201's identity generation and beyond — the other(s) SHALL detect the lock is held,
decline to proceed, and log a no-op (never silently duplicate a spawn, and never queue indefinitely
waiting for the lock).

This reuses, unmodified, the same generic per-resource file lock already adversary-hardened for the P2
gig board (`~/anicca/skills/economy/gig/lib/lock.mjs`, including its `isLockStale` pure predicate and
its atomic `fs.rename`-based reclaim fix from that lock's own REQ-101), acquired under a new, distinct
lock key (e.g. `"colony-spawn"`) rather than any gig-specific key — this is a new lock KEY on an
EXISTING lock MECHANISM, not new lock-implementation code. Per REQ-106, this local-POSIX-filesystem
lock is sufficient because every caller in this increment shares the SAME mounted filesystem on the
SAME coordinator host — this requirement does NOT claim to solve mutual exclusion across physically
separate hosts (see REQ-106's own known-limitation edge case for that future scenario).

**Canonical `statePath` (resolves FIND-103)**: `withGigLock`'s real, existing signature is
`withGigLock(statePath, lockKey, fn, opts)` — `statePath` is a MANDATORY positional argument, and
`lockPaths()` derives the actual lock FILE from BOTH `statePath`'s directory AND `lockKey`
(`path.join(path.dirname(statePath), 'locks', lockKey + '.lock')`), never from `lockKey` alone. If two
call sites passed two DIFFERENT `statePath` values under the same `"colony-spawn"` lock key, they would
resolve to two DIFFERENT physical lock files under two different `locks/` directories and BOTH could
"hold the lock" simultaneously — silently defeating this requirement's entire purpose. THE SYSTEM SHALL
therefore designate REQ-105's citizen registry path (`~/anicca/skills/self/spawn/registry/citizens.json`)
as the colony-spawn lock's ONE canonical `statePath` — a natural fit, since the critical section this
lock protects IS "read `citizens.json` + decide + possibly append to `citizens.json`" (REQ-101 through
REQ-305) — and SHALL export this single path as ONE named constant, `CITIZENS_REGISTRY_PATH`, from a
new shared module `~/anicca/skills/self/spawn/lib/registry-path.mjs`. EVERY call site that acquires the
`"colony-spawn"` lock (and every REQ-101/105/305 read/write of the registry itself) SHALL import and use
this SAME exported constant — never an independently hardcoded path string — so lock identity and
registry identity can never silently drift apart across call sites.

**Edge Cases**:
- Two evaluation loops on the coordinator host race to acquire the `"colony-spawn"` lock within the
  same millisecond: POSIX exclusive file creation (`fs.open(..., "wx")`, the existing mechanism's own
  atomicity guarantee) ensures exactly one succeeds; the other's `acquire()` call fails immediately
  (fail-closed, no retry-queue).
- The instance holding the lock crashes mid-spawn (dies before releasing): the existing heartbeat +
  `isLockStale` mechanism reclaims the lock after `staleMs` of no heartbeat, exactly as it already does
  for gig-board operations — REQ-103 does not need a second staleness mechanism.
- A held lock's holder is still genuinely working (heartbeating) well past any naive fixed timeout: per
  the existing `isLockStale` semantics, it is NEVER stolen from while it heartbeats, regardless of
  elapsed wall-clock time — this property is inherited, not re-derived, from the existing lock.
- A future call site hardcodes its own literal `citizens.json` path string instead of importing
  `CITIZENS_REGISTRY_PATH`: even if the literal string happens to match TODAY, THE SYSTEM treats this as
  a spec violation to be caught at Phase 3 review (a structural/import-identity check, not a runtime
  assertion) — the binding contract is "imports the constant," not "the string happens to be correct."

**Acceptance Criteria**:
- The colony-spawn critical section (REQ-201 through REQ-205, and the decision to proceed into REQ-3xx)
  is wrapped by the existing `withGigLock`-equivalent helper (or a directly analogous
  `withColonyLock("colony-spawn", fn)`) using the SAME `lock.mjs` module, not a reimplementation, with
  `statePath` set to the single exported `CITIZENS_REGISTRY_PATH` constant from `registry-path.mjs` —
  never an independently hardcoded string.
- Given two concurrent callers both observing `eligible:true`, an integration test proves exactly one
  reaches REQ-201's wallet-generation step during the run; the other's attempt is recorded as
  `reason:"lock_held"` and makes zero wallet-generation calls.
- A structural/Tier-0 check (source-grep or import-identity check) confirms EVERY call site that
  invokes the `"colony-spawn"` lock imports and passes the SAME `CITIZENS_REGISTRY_PATH` constant — this
  is required IN ADDITION TO (not instead of) the concurrent-race integration test above, because a
  single test process sharing one implicit `statePath` choice cannot, by itself, prove every real call
  site in the eventual implementation converges on one canonical path.

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

### REQ-105: Colony citizen registry — brand-new, dedicated, spawn-appended (resolves FIND-002; revised to resolve FIND-101/FIND-104)
**EARS**: WHEN REQ-101 needs the list of citizens to evaluate, THE SYSTEM SHALL read that list from a
single, versioned JSON registry file dedicated EXCLUSIVELY to this feature's colony-surplus/spawn
concern — `~/anicca/skills/self/spawn/registry/citizens.json` — created FRESH by this feature. THE
SYSTEM SHALL NOT read from, write to, migrate, or otherwise repurpose the pre-existing
`~/anicca/skills/economy/ubi/colony-wallets.json`: that file remains exclusively `ubi.js::
distributeAI`'s own recipient-eligibility list ("addresses proven to be real colony members," a
DIFFERENT purpose than this requirement's surplus-aggregation registry), and its current 2nd entry is
claude-p's own human-funded wallet — the two files share ZERO state (resolves FIND-101's critical
finding that an earlier draft wrongly proposed migrating/extending that live, differently-scoped,
already-in-use file).

Each record in `citizens.json` carries EXACTLY the fields `isSelfFunded()`/`selfFundedReasons()`
(`~/anicca/skills/_shared/lib/is-self-funded.mjs`, reused unmodified) already require, SPLIT into the
two separate shapes that module's own documented contract and this feature's own consumers each need
(resolves FIND-104's wallet-field type mismatch: `is-self-funded.mjs::hasOwnWallet()` documents and
implements `wallet.evm`/`wallet.solana` as BOOLEAN presence flags — `Boolean(wallet.evm) ||
Boolean(wallet.solana)` — never address strings):
- `wallet: {evm?: boolean, solana?: boolean}` — a presence-flag pair, matching `hasOwnWallet()`'s real,
  documented boolean contract EXACTLY (true compatibility, never accidental truthiness coercion of a
  non-empty address string).
- `walletAddress: {evm?: string, solana?: string}` — the actual address string(s), for REQ-305's
  registry-append use and any future consumer that needs the real address — this field is NEVER passed
  to `isSelfFunded()`.

The full record shape is therefore `{id: string, wallet: {evm?: boolean, solana?: boolean},
walletAddress: {evm?: string, solana?: string}, fuel: {provider: string}, humanDependencies: string[]}`
plus ONE additional field this feature needs and `isSelfFunded()` itself does not read,
`telemetryPath: string` (the citizen's own `state/telemetry.json` absolute or `$HOME`-relative path,
used by REQ-101's balance lookup).

THE SYSTEM SHALL seed `citizens.json`, at implementation time, with the following FIXED, LITERAL JSON
array — NOT a migration of `colony-wallets.json`'s entries, and NOT derived from any out-of-band
classification step, because there is no migration to begin with — containing ONLY the entities this
spec's author has verified, as of 2026-07-07, are genuinely self-funded colony citizens (per
`~/anicca/skills/self/colony-status.sh`'s own live output and this project's own `CLAUDE.md` colony
table: "SELF-funded on Earth = 2"):

```json
[
  {
    "id": "anicca-a3cdd4",
    "wallet": { "evm": true },
    "walletAddress": { "evm": "0xB9dd3B67921B354c656523d6851537988F31DD56" },
    "fuel": { "provider": "clawrouter-own-wallet" },
    "humanDependencies": [],
    "telemetryPath": "$HOME/.automaton/state/telemetry.json"
  },
  {
    "id": "Franklin",
    "wallet": { "solana": true },
    "walletAddress": { "solana": "8FpqdcCHqjqkVXR58eVJa53neXbJf9emXhvHhgeUPCV9" },
    "fuel": { "provider": "x402" },
    "humanDependencies": [],
    "telemetryPath": "$HOME/.blockrun/state/telemetry.json"
  }
]
```

claude-p (real funds at `0x904B50d2e214Da947d83D6a2D32c4E3Ffc17Eb74`, human-funded, per
`docs/WALLETS.md` lines 49-62) and every other human-funded wallet SHALL NEVER be seeded into this
file — there is no ambiguous classification step here precisely BECAUSE there is no migration; the
seed set above is a fixed literal this spec's author already verified against live, on-disk evidence.

**Edge Cases**:
- The registry file is missing, unparseable, or one record is missing a required field: THE SYSTEM
  SHALL exclude only that INDIVIDUAL malformed record from REQ-101's aggregation (fail-closed
  per-record, matching REQ-101's own missing-telemetry fail-closed convention) — one bad record never
  aborts aggregation for every OTHER valid citizen.
- A record's `wallet`/`fuel`/`humanDependencies` fields are well-formed but `isSelfFunded()` itself
  returns `false` for that record (e.g. `fuel.provider` not in `OWN_FUNDED_FUEL_PROVIDERS`): excluded
  from the surplus sum exactly as REQ-101 already specifies — REQ-105 supplies DATA, REQ-101 still
  owns the JUDGMENT of who counts; REQ-105 does not duplicate or override that gate.
- Two records share the same `id`: THE SYSTEM SHALL treat this as a malformed registry and exclude
  BOTH duplicate-id records from aggregation until corrected, rather than arbitrarily picking one.
- A future write path (anywhere in this feature) attempts to append or edit an entry in `citizens.json`
  whose `{wallet, fuel, humanDependencies}` sub-object would make `isSelfFunded()` return `false`: see
  REQ-305's binding pre-append `isSelfFunded()` check below — this registry SHALL NEVER contain an
  entry that fails its own gate, at seed time OR at any later append.

**Acceptance Criteria**:
- The seed file parses as an array of objects each satisfying `{id, wallet, walletAddress, fuel,
  humanDependencies, telemetryPath}`, and calling the existing, unmodified `isSelfFunded()` on any one
  record's `{wallet, fuel, humanDependencies}` sub-object (never `walletAddress`) returns a boolean
  without throwing.
- A direct test confirms that EACH of the two seeded entries above, when its `{wallet, fuel,
  humanDependencies}` sub-object is passed through the existing, unmodified `isSelfFunded()`, returns
  `true` — a straightforward assertion against literal fixture data (resolves FIND-101's critique of
  the prior "compare against today's known-good identities" proof method, which presupposed an
  out-of-band ground truth no longer needed once there is no migration).
- `citizens.json`'s seed content contains ZERO entries whose `isSelfFunded()` verdict is `false` — and
  REQ-305's append-on-spawn path (below) enforces the SAME property on every future append, closing
  this hazard PERMANENTLY rather than only at t=0.
- REQ-402c (a `"bootstrap_failed"` child's exclusion) and REQ-403 (the wallet non-interference audit's
  "current set of running instances") both read their citizen list from THIS SAME registry — no second,
  parallel citizen-enumeration mechanism exists anywhere in this spec.

---

### REQ-106: Colony-spawn evaluation is scoped to a single coordinator host, this increment only (resolves FIND-003)
**EARS**: THE SYSTEM SHALL perform every REQ-101/102/103 evaluation (colony surplus aggregation,
threshold gate, and `"colony-spawn"` lock acquisition) EXCLUSIVELY on one, explicitly-designated
coordinator host for the full duration of this increment — currently the Mac Mini
(`anicca-mac-mini-1`) on which automaton's own loop already runs (this project's own `CLAUDE.md`:
"Mac Mini（`anicca-mac-mini-1`...）で直接実行する"). A cloud-deployed child instance (REQ-301-303)
SHALL NOT itself evaluate REQ-101/102/103 or attempt to acquire the `"colony-spawn"` lock during this
increment — spawn CHAINING (a child later spawning its own child) is explicitly OUT OF SCOPE,
deferred to a future increment. This constraint is what makes REQ-103's `lock.mjs` (a local-POSIX-
filesystem primitive) and REQ-305's `ledger.js` (a local append-only file) CORRECT as specified: both
mechanisms only need to serialize/record callers that share the SAME mounted filesystem, which holds
precisely because every evaluator in this increment IS that one coordinator host.

**Edge Cases**:
- Multiple LOOPS on the SAME coordinator host (e.g. automaton's own cron-driven wake and a separately-
  scheduled evaluation) race to evaluate REQ-102/103 in the same window: this is the scenario REQ-103's
  lock already handles (both are local callers sharing one filesystem) — this is the ONLY concurrency
  scenario this increment's lock/ledger design needs to survive, and it replaces iteration 1's
  now-corrected edge case that conflated this with a cross-host scenario.
- A future increment extends the colony to genuinely multiple physical coordinator hosts (e.g. once a
  spawned child is itself permitted to evaluate REQ-102/103): THE SYSTEM as specified in THIS increment
  does NOT support that topology — `lock.mjs`/`ledger.js` would need to be replaced or backed by
  networked/shared storage (a shared network filesystem, a database-backed lock, or a distributed
  consensus mechanism) before multi-host colony-spawn evaluation is safe. This is an explicit,
  documented, KNOWN LIMITATION of this increment, not an oversight.
- The coordinator host itself becomes unavailable (hardware failure, network partition from the cloud
  providers): no OTHER host picks up colony-spawn evaluation in this increment (single coordinator, by
  design) — an accepted single-point-of-failure for this increment's scope, matching the colony's
  actual current topology (every existing citizen's own loop already runs on this same Mac Mini today).

**Acceptance Criteria**:
- A structural/Tier-0 check confirms `lock.mjs`'s acquire/release path and `ledger.js`'s read/write
  path are invoked from exactly one designated coordinator-host code entry point in this feature's
  implementation, with no code path that invokes them from a cloud-deployed child's own runtime.
- This spec's own scope section states spawn chaining is out of scope, so a fresh adversary reviewing
  REQ-103/REQ-305 does not need to (and must not be asked to) prove multi-host correctness for this
  increment.

---

## REQ群B: 新規 instance identity 生成（P2 実証済み手順の再利用、車輪の再発明禁止）

### REQ-201: Child EVM (Base) wallet generation
**EARS**: WHEN REQ-102/103 jointly permit a spawn attempt to proceed, THE SYSTEM SHALL generate the
child's own secp256k1/Base-EVM keypair via `~/anicca/skills/self/spawn/scripts/gen-wallet.sh`
(existing, unmodified — the exact script this feature's task description names as already-proven),
BEFORE any cloud provisioning or on-chain action for that child occurs, and SHALL verify the resulting
address is a real keccak256-derived Ethereum address (not the script's own documented sha256 fallback,
which is not a valid Ethereum address — see Edge Cases) and is distinct from every existing colony
citizen's own EVM address (reusing `child-spec.js::buildChildSpec`'s existing, UNTOUCHED distinct-
wallet assertion, which already throws if `childWallet === parentWallet`; REQ-201 generalizes that same
check to "distinct from ALL existing citizens," not merely the one parent that happened to initiate the
attempt). This generated address ALSO becomes `buildChildSpec`'s `agentEvmAddress` identity-anchor
field once REQ-204 registers it (see REQ-206) — REQ-201 itself only generates and validates the
keypair; it does not call `buildChildSpec`.

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
reachable, THE SYSTEM SHALL register the child's ERC-8004 identity by calling the existing
`~/anicca/skills/economy/gig/lib/ensure-agent-id.mjs::ensureAgentId({privateKey: childPrivateKey,
cacheFile: <child's own isolated cache path>})` — NOT `identity.mjs::registerIdentity()` directly —
reusing `ensureAgentId`'s already-implemented, already-tested cache-then-verify-then-register-once
wrapper UNMODIFIED (resolves FIND-004: this is the SAME defensive "don't double-register" logic REQ-204
needs, already built and covered by that module's own test suite; REQ-204 does not re-derive it).
`ensureAgentId` itself calls `registerIdentity()`/`verifyIdentity()` against the already-live registry
contract — mainnet `0x8004A169FB4a3325136EB29fA0ceB6D2e539a432` (Base, chain 8453) or testnet
`0xdc527768082c489e0ee228d24d3cfa290214f387` (Base-Sepolia, chain 84532), selected by the same
`GIG_CHAIN` env toggle it already uses — signed with the child's OWN private key (`msg.sender` = the
child's own address, matching the existing "each agent registers itself" discipline). Because
`ensureAgentId`'s own cache path is gated on `ANICCA_HOME`/`HOME` exactly as `resolve-identity.mjs`
already is (that module's own header: "so a foreign spawn ... can never read/reuse another instance's
cached agentId"), passing the child's own isolated `$HOME` (REQ-203) as `cacheFile`'s basis is
sufficient — no new per-child cache-scoping logic is needed. THE SYSTEM SHALL record the returned
`agentId` and transaction hash in the spawn ledger (REQ-305) before the child may be marked `"active"`.

**Edge Cases**:
- `register()` reverts for insufficient gas (the child's fresh wallet starts at exactly `0 ETH`): THE
  SYSTEM SHALL fund it with a ONE-TIME, minimal gas seed transferred from a self-funded citizen's own
  wallet — sized to cover exactly one `register()` call plus the child's first gig-board interaction,
  the SAME class of transfer SPEC.md §9.6 already performed and evidenced on-chain (tx `0x48d49e…`
  /`0x1478758…`), never an open-ended top-up, and never sourced from a human-funded wallet (REQ-304
  governs the funding SOURCE constraint).
- The registration transaction succeeds but its `Registered` event cannot be decoded (a malformed/odd
  log): treated as a REQ-305 failure (no `agentId` recorded), never a fabricated/guessed agentId.
- The SAME child wallet somehow already holds an agentId (should be impossible for a genuinely fresh
  key): THE SYSTEM SHALL rely EXCLUSIVELY on `ensureAgentId`'s own existing cache-hit/`verifyIdentity`
  re-check path (already reads a cached `{address, agentId}` pair, re-verifies via `verifyIdentity`
  before trusting it, and falls through to a fresh `register()` only if that re-check fails) — REQ-204
  does not implement a second, parallel "already-registered" check; the anomaly (a fresh key already
  owning an agentId) is logged by `ensureAgentId`'s own `cached:true` return value, which REQ-305's
  ledger write surfaces for audit.

**Acceptance Criteria**:
- `ensureAgentId({ privateKey: childPrivateKey, cacheFile: <child's own isolated path> })` is called
  with no modification to `ensure-agent-id.mjs`'s or `identity.mjs`'s existing logic, signature, ABI,
  or registry-address constants.
- A successful registration produces a real, independently-re-verifiable transaction hash and a
  numeric `agentId`; both are appended to the spawn ledger (REQ-305) in the same row that eventually
  marks the child `"active"`.
- A fixture where `ensureAgentId`'s injected `verifyFn` reports an existing, matching cached agentId
  results in ZERO calls to `registerFn` (i.e. `register()` is never invoked a second time) — reusing
  that module's own existing test double pattern (`registerFn`/`verifyFn` injection), not a new mock
  harness built from scratch for this feature.

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

### REQ-206: `buildChildSpec`'s identity-anchor validation — backward-compatible extension (resolves FIND-001; EARS clarified to resolve FIND-102)
**EARS**: WHEN a new child record is assembled via `~/anicca/skills/self/spawn/lib/child-spec.js::
buildChildSpec` (called from REQ-305's ledger-append step), THE SYSTEM SHALL accept as a valid
"identity anchor" for the child EITHER (a) a non-empty `childInbox` string (the pre-existing
AgentMail-based anchor, unchanged in shape and validation from today's already-shipped design) OR (b)
the pair `agentEvmAddress` (identical to `childWallet`, REQ-201) AND `agentId` (the numeric ERC-8004
identifier `ensureAgentId`/REQ-204 returns), both present and non-empty. THE SYSTEM SHALL require that
AT LEAST ONE of these two anchors is present; it is NOT an error for BOTH to be present simultaneously
(a future hybrid child with both an AgentMail inbox and an on-chain identity succeeds identically to
either anchor alone — see Edge Cases and Acceptance Criteria); it IS an error for NEITHER to be present.
"At least one" is stated here as a genuine minimum, not an exclusive-or, so this EARS clause and the
Edge Cases below never disagree (resolves FIND-102's self-contradiction between an earlier XOR-reading
EARS sentence and this requirement's own "both present" acceptance rule). This corrects iteration 1's
false claim that
`buildChildSpec` is reused "unmodified" (FIND-001: today's code throws `missing required field
"childInbox"` for `undefined`/`null`/`""`, and this feature's own design never produces an AgentMail
inbox at all): `buildChildSpec` requires a SMALL, backward-compatible validation/signature extension
— adding the optional `agentEvmAddress`/`agentId` pair and relaxing `childInbox` from unconditionally-
required to "required only if the ERC-8004 pair is absent" — never a rewrite of its existing
distinct-wallet assertion, monotonic-ID logic (`nextChildId`), or returned row shape (which gains two
new optional fields, `agent_evm_address`/`agent_id`, alongside its existing, unchanged fields).

**Edge Cases**:
- An existing (hypothetical future) caller that still passes a non-empty `childInbox` and omits
  `agentEvmAddress`/`agentId` entirely (the old AgentMail-only design, e.g. today's
  `~/anicca/skills/self/spawn/run.sh`'s own happy path where `AGENTMAIL_API_KEY` is set and a real
  inbox is minted) MUST continue to succeed with an identical returned row shape to today's — this is
  the binding backward-compatibility contract; a regression test locks this in.
- A caller (this feature's own REQ-305 integration) passes `agentEvmAddress`+`agentId` and omits
  `childInbox` (or passes it as `""`/`null`, which is exactly what this feature's spawn flow does,
  since it never mints an AgentMail inbox): THE SYSTEM SHALL accept this as a valid identity anchor and
  NOT throw the pre-existing "missing childInbox" error — this is the specific behavior iteration 1
  incorrectly assumed already existed.
- Neither `childInbox` nor the `agentEvmAddress`+`agentId` pair is present, or only ONE half of the
  ERC-8004 pair is present (e.g. `agentEvmAddress` set but `agentId` missing): THE SYSTEM SHALL throw
  a `missing identity anchor` error — exactly as strict as today's all-required validation, never
  silently defaulting to a placeholder identity.
- Both `childInbox` AND the ERC-8004 pair are present simultaneously (a future hybrid child with both
  an inbox and an on-chain identity): THE SYSTEM SHALL accept this without error — "at least one" is a
  minimum, not an exclusive-or.

**Acceptance Criteria**:
- A regression test fixture identical to the existing `child-spec.test.js`'s "assembles a complete,
  distinct-wallet spec" case (non-empty `childInbox`, no `agentEvmAddress`/`agentId`) passes UNCHANGED
  after this modification.
- A new test fixture supplying `agentEvmAddress`+`agentId` and omitting `childInbox` succeeds, and the
  returned row carries `agent_evm_address`/`agent_id`.
- A new test fixture supplying NEITHER anchor throws; a fixture supplying only HALF of the ERC-8004
  pair also throws.
- A new test fixture supplying BOTH a non-empty `childInbox` AND a complete `agentEvmAddress`+`agentId`
  pair simultaneously SUCCEEDS without throwing, and the returned row carries `childInbox`,
  `agent_evm_address`, AND `agent_id` all together — proving the "at least one, not an XOR" reading of
  the EARS clause above (resolves FIND-102).
- A structural diff of `child-spec.js` confirms the change is limited to the required-field validation
  and the returned row's field list — `nextChildId`, the distinct-wallet assertion, and every other
  existing field/behavior are byte-identical to today's.

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
attempt (the selection ITSELF — Nosana vs Akash — is specified by REQ-306, not by this requirement;
REQ-302 governs only the Nosana-specific execution once selected), THE SYSTEM SHALL provision the
child's compute using the Nosana CLI (`@nosana/cli`, confirmed
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
**EARS**: WHEN a spawn attempt proceeds and Akash is the selected cloud target for that attempt (per
REQ-306's selection mechanism — see REQ-302's own note), THE SYSTEM SHALL provision the child's compute
using the existing, already-implemented
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
`child-spec.js::buildChildSpec`'s own `status:"provisioning"` initial value, assembled via REQ-206's
identity-anchor rules using the child's own `agentEvmAddress`+`agentId` once REQ-204 completes — this
feature's children never carry a `childInbox`) together with the specific failing step and error
message, any already-spent, non-refundable resource (e.g. an Akash deployment deposit not yet
converted into an active lease) SHALL be logged for colony accounting, and REQ-102's
`SPAWN_COOLDOWN_DAYS` timer SHALL NOT be considered "consumed" by a failed attempt — mirroring this
project's existing HARD RULE 0.24 ("NO FAKE RUN... any failed step exits non-zero and leaves an honest
provisioning/failed ledger row, never a fabricated success"). WHEN, and only when, a spawn attempt
completes and the child is marked `"active"` (REQ-204+REQ-205 both complete), THE SYSTEM SHALL ALSO
append a new record for that child to REQ-105's colony citizen registry
(`~/anicca/skills/self/spawn/registry/citizens.json` — NOT `economy/ubi/colony-wallets.json`, which
this feature never touches, per REQ-105's FIND-101 revision) — `{id: child_id, wallet: {evm: true,
solana: true-if-generated} (BOOLEAN presence flags, matching `is-self-funded.mjs::hasOwnWallet()`'s own
documented contract exactly — resolves FIND-104), walletAddress: {evm: childWallet, solana:
childSolanaAddress-if-generated} (the actual address STRING(s) — a SEPARATE field from `wallet`, never
passed to `isSelfFunded()`), fuel: {provider: "free-model"} (per REQ-401's exclusive free-model fuel
requirement), humanDependencies: [], telemetryPath: <child's own isolated telemetry.json path>}` — so
REQ-101's NEXT evaluation includes the new citizen automatically, without any separate manual or
out-of-band registry-edit step (resolves FIND-002's "how does the registry grow" gap).

**Before this append is performed** (resolves FIND-101's permanent-hazard-closure requirement), THE
SYSTEM SHALL call the existing, unmodified `isSelfFunded()` on the new record's `{wallet, fuel,
humanDependencies}` sub-object — exactly the same gate REQ-101 itself would apply — and SHALL REFUSE
the append (logged as a distinct, non-silent REQ-305 append-failure; the child's ledger row remains
`"active"` since REQ-204+REQ-205 genuinely completed, but the registry-append reconciliation below
applies) if `isSelfFunded()` returns `false` for that exact record. This ensures `citizens.json` can
NEVER come to contain a non-self-funded entry, whether at its initial REQ-105 seed or at ANY later
spawn-triggered append — a permanent closure of the hazard, not merely a t=0 check.

**Edge Cases**:
- The cloud deploy (REQ-302/303) succeeds but ERC-8004 registration (REQ-204) subsequently fails: the
  child remains `"provisioning"`, is EXCLUDED from REQ-101's colony-surplus aggregation (it is not yet
  a citizen, and NO registry record is appended for it yet), and registration is retried up to a
  bounded retry window (to avoid wasting an already-paid, non-refundable lease) before the lease itself
  is torn down and the attempt marked `"failed"`.
- A failed attempt's cooldown-exemption (above) could in principle be exploited to attempt unlimited
  spawns by engineering repeated "failures": THE SYSTEM SHALL cap the number of failed attempts counted
  within any single `SPAWN_COOLDOWN_DAYS` window (default cap `3`) — beyond that cap, further attempts
  within the window ARE rate-limited exactly as a successful spawn would be, closing this gap.
- The ledger write (`"active"`) succeeds but the SUBSEQUENT registry-append write fails FOR A TRANSIENT
  REASON (e.g. a filesystem error): THE SYSTEM SHALL retry the registry-append on the NEXT wake before
  any further spawn evaluation runs — a child marked `"active"` in the ledger but absent from the
  registry is a detectable inconsistency (the next REQ-101 aggregation run reconciles it), never a
  silent, permanent gap.
- The registry-append is REFUSED because the new record fails its own `isSelfFunded()` pre-append check
  (e.g. an upstream bug produced a `wallet` object with no `true` flags): THE SYSTEM SHALL treat this as
  a DISTINCT failure mode from the transient-filesystem-error case above — it is NOT blindly retried on
  the next wake (retrying an isSelfFunded-refusal without fixing the underlying defect would either loop
  forever or eventually succeed for the wrong reason) — instead it SHALL be surfaced as a BLOCKING
  colony-accounting anomaly requiring explicit remediation; the child remains `"active"` in the spawn
  ledger (REQ-204+REQ-205 genuinely completed) but is PERMANENTLY excluded from REQ-101's aggregation
  until the anomaly is fixed and the append is manually/explicitly retried.

**Acceptance Criteria**:
- A structural/Tier-0 check of the ledger-writing code path confirms every write path that can leave a
  row behind sets `status` to one of `{"provisioning","active","failed"}` — never omits `status`, and
  never writes `"active"` from any branch that has not completed REQ-204+REQ-205.
- An integration test that injects a failure at each of REQ-201/202/203/204/205/302/303 in turn
  confirms the resulting ledger row's `status` and `error` fields correctly identify the failing step,
  and that REQ-101's next aggregation run excludes that child.
- An integration test confirms that marking a child `"active"` appends a new, correctly-shaped record
  (with `wallet` boolean flags and `walletAddress` strings correctly split — resolves FIND-104) to
  REQ-105's registry, and that a FAILED attempt appends NO registry record at all.
- A fixture where the new record's `{wallet, fuel, humanDependencies}` sub-object would fail
  `isSelfFunded()` (e.g. `fuel.provider` missing/unrecognized) results in ZERO append to `citizens.json`
  and a logged, distinct refusal — never a silent append of a non-self-funded entry (resolves FIND-101).

---

### REQ-306: Deterministic cloud-target selection — Nosana vs Akash (resolves FIND-006)
**EARS**: WHEN a spawn attempt (REQ-102/103) proceeds and REQ-301's local-spawn-prohibition applies,
THE SYSTEM SHALL select which of Nosana (REQ-302) or Akash (REQ-303) is "the selected cloud target for
that attempt" via a single, deterministic, bookkeeping decision function `selectCloudTarget({
nosanaAvailable, nosanaPriceUsd, akashAvailable, akashPriceUsd }) → "nosana"|"akash"|"none"` — NEVER a
model/LLM judgment call (consistent with REQ-104's bookkeeping-only discipline, extended here to
cloud-target selection). THE SYSTEM SHALL query BOTH providers' current price/availability for the
SAME minimal workload spec immediately before each spawn attempt (Nosana: the CLI's own market-price
query for the configured market address; Akash: the `provider-services query market bid list`-
equivalent for the configured SDL) and SELECT the provider whose quoted price, normalized to a common
USD-equivalent estimate, is LOWER, given both are currently available (at least one biddable
node/market at query time). IF exactly one provider is currently available, THAT provider is selected
regardless of price. IF NEITHER provider is currently available, THE SYSTEM SHALL treat this as a
deploy failure under REQ-305 (no cloud target selected, no child record ever reaches beyond
`"provisioning"`) — this mirrors REQ-302/303's own existing "no open market/bid" failure paths,
generalized to the selection step itself.

**Edge Cases**:
- Both providers quote the exact same normalized USD price (a tie): THE SYSTEM SHALL default
  deterministically to `"nosana"` (a fixed, documented tie-breaker — arbitrary but CONSISTENT, never
  randomized, so identical inputs always produce the identical selection — bookkeeping determinism,
  matching REQ-104's own discipline).
- A price quote cannot be directly compared because the two providers price in different native tokens
  (Nosana: NOS/SOL-denominated; Akash: AKT/`uact`-denominated): THE SYSTEM SHALL normalize both to a
  USD-equivalent estimate using the SAME already-available price-conversion mechanism this project's
  own `akt-treasury.sh` already documents (an observed AKT/ACT/USD rate) and an equivalent,
  already-available NOS/SOL/USD rate — never comparing raw native-token quantities across different
  currencies, and never inventing a new pricing oracle for this feature.
- The selection function's own PRICE QUERIES are I/O (effectful), but the COMPARISON/decision logic is
  pure given the two already-fetched quotes — mirroring this spec's existing effectful-shell-feeds-
  pure-core pattern (REQ-101's `readCitizenBalances`/`computeColonySurplusUsd` split); `selectCloudTarget`
  itself performs zero I/O.

**Acceptance Criteria**:
- Pure function `selectCloudTarget({ nosanaAvailable, nosanaPriceUsd, akashAvailable, akashPriceUsd })
  → "nosana"|"akash"|"none"`, zero I/O, given already-fetched quotes as input.
- `nosanaPriceUsd < akashPriceUsd`, both available → `"nosana"`. The reverse → `"akash"`. Equal prices,
  both available → `"nosana"` (documented tie-breaker). `nosanaAvailable=false`, `akashAvailable=true`
  → `"akash"` regardless of price (and vice versa). Both unavailable → `"none"`.
- REQ-302's and REQ-303's own EARS clauses ("Nosana/Akash is the selected cloud target for that
  attempt") are satisfied exactly when this function returns the matching string — no other selection
  path exists anywhere in this spec.

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
  `"bootstrap_failed"` — no others. Every child this check considers is one already present in REQ-105's
  colony citizen registry (REQ-305 appends it there on activation) — REQ-402 does not maintain a second,
  separate list of children.
- REQ-101's aggregation function, given a child flagged `"bootstrap_failed"` in REQ-105's registry,
  excludes its balance from the productive-surplus sum even if that balance is nonzero (e.g. residual
  gas-seed dust).

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
- A repeatable audit script exists that, given the current set of running instances' own `HOME` values
  — read from REQ-105's colony citizen registry (the same registry REQ-101 aggregates over; no second,
  parallel instance-enumeration mechanism is introduced for this audit), (1) runs the static grep sweep
  and reports zero cross-instance path references, and (2) invokes
  `resolveEvmPrivateKey`/`resolveSolanaSecret` once per instance's own `HOME` and asserts pairwise
  inequality across all resolved keys.
- Given a deliberately-injected test fixture where two fake instances share a `HOME` (negative test),
  the audit correctly reports a collision — proving the check is not vacuously passing.
