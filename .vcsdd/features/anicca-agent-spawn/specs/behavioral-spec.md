# Behavioral Spec — anicca-agent-spawn (Phase 1a)

**feature**: anicca-agent-spawn · **mode**: strict · **increment**: P3 spawn (colony-treasury-gated,
cloud-only) + $0-bootstrap verification · **日付**: 2026-07-07 · **revision**: iteration 5, revised
(spec review iteration-1 findings FIND-001..006 resolved AND spec review iteration-2 findings
FIND-101..104 resolved AND spec review iteration-3 findings FIND-201..206 resolved AND spec review
iteration-4 findings FIND-301..305 resolved AND spec review iteration-5 findings FIND-401..405
resolved — see changelogs below)

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

## Changelog (iteration 2 spec review, round 2 → iteration 3)

Iteration 2's round-2 spec review FAILed with 6 NEW findings (all 4 prior findings, FIND-101..104,
were reconfirmed genuinely resolved against the real, current source). Each is resolved by a specific,
cited design decision:

| Finding | Severity | Resolution |
|---|---|---|
| FIND-201 | critical | REQ-402's lifecycle facts (`status`, `active_since`) are pinned to their ONE canonical owner, `ledger.js`'s own rows — never `citizens.json`, which stays deliberately minimal. REQ-101 gains an explicit JOIN step, a new pure function `filterProductiveCitizens({citizens, ledgerRows, nowMs, bootstrapWindowDays})`, that cross-references REQ-105's registry against `ledger.js`'s rows before `computeColonySurplusUsd` ever runs. REQ-305 now explicitly sets `active_since` on the ledger row the moment a child is marked `"active"`. |
| FIND-202 + FIND-205 | major + medium | REQ-105's record shape gains a new `homeDir` field (an already-resolved absolute HOME path, for REQ-403's audit), and `telemetryPath` is redefined to be an ALREADY-RESOLVED absolute path at seed/append time — never an unresolved `$HOME` template string requiring a runtime substitution step nobody specified. Both today's citizens legitimately share the same `homeDir` (documented as expected, not a bug, per REQ-106's single-coordinator-host scoping). |
| FIND-203 | major | REQ-402's promise to feed `children_bootstrap_failed` into REQ-102's gate evaluation is REMOVED — descoped to an observability-only bookkeeping count with an explicit, structurally-checkable non-effect on REQ-102's pinned signature/behavior. |
| FIND-204 | critical | REQ-206 is extended (not just its identity-anchor clause) to specify concrete values/derivation for `buildChildSpec`'s other four already-mandatory fields: `parentWallet` (REQ-106's coordinator-host citizen's own wallet), `generation` (fixed `1`, reusing `run.sh`'s own existing default convention), `seedUsdc` (aliased exactly to REQ-204's gas-seed amount, explicitly distinct from REQ-303/304's shelter cost), and `constitutionHash` (a fixed SHA-256 of the already-shipped `identity/genesis.md` canonical genesis file). |
| FIND-206 | low | REQ-101's vestigial "claude-p appears in the same telemetry-file directory listing" edge case is removed entirely — unreachable under the registry-only design REQ-105/101 specify. |

## Changelog (iteration 3 spec review → iteration 4)

Iteration 3's spec review (an Opus-model adversary pass, deeper scrutiny than prior Sonnet passes)
FAILed with 5 NEW findings (all 6 iteration-1 findings, all 4 iteration-2-round-1 findings, and all
6 iteration-2-round-2 findings were reconfirmed genuinely resolved against the real, current source).
Each is resolved by a specific, cited design decision:

| Finding | Severity | Resolution |
|---|---|---|
| FIND-301 | critical | REQ-101's `filterProductiveCitizens` join now explicitly specifies "last write wins": `ledger.js`'s real, append-only rows may legitimately contain MULTIPLE rows sharing one `child_id` (proven by `run.sh`'s own existing provisioning-row-then-status-row pattern), and the join MUST reduce these to exactly one effective row per `child_id` — the LAST-appended one — before applying its exclusion rule. `ledger.js` itself is untouched (no update/upsert primitive added). PROP-101d's own fixture is extended to cover the duplicate-`child_id` case. |
| FIND-302 + FIND-303 | critical | REQ-101's balance lookup is redefined from a coordinator-local `fs.readFile` of a per-citizen `telemetryPath` (which structurally cannot reach a REQ-301-mandated remote child's own disk) to a NEW, registry-driven, coordinator-run PUBLIC-RPC balance query keyed on each citizen's `walletAddress` — generalizing `~/anicca/skills/self/telemetry-collect.sh`'s own already-proven, host-location-agnostic RPC-by-address pattern from 3 hardcoded instances to a registry-driven loop. `telemetryPath` is REMOVED from REQ-105's schema. Separately, REQ-403's LIVE wallet-comparison check (which depends on `resolve-identity.mjs`'s pure-local-filesystem resolvers and therefore has the same structural limitation) is explicitly SCOPED to co-located instances only for this increment (today: automaton + Franklin) — a cloud-hosted spawned child is exempt from the live check until a future increment adds a genuine remote-audit mechanism; REQ-403's STATIC grep-sweep half is unaffected and continues to cover a remote child's deployed source (which boots from the SAME git-cloned repo the grep already runs against). |
| FIND-304 | major | A cross-file disambiguation note is added wherever REQ-206/REQ-305 describe `buildChildSpec`'s returned row: that row's pre-existing, unmodified `wallet` field (a bare address STRING, `child-spec.js:37`) is a completely separate field, in a completely separate file/schema, from `citizens.json`'s `wallet` field (a boolean presence-flag object, REQ-105) — the two share a name only by coincidence; neither file is renamed (same discipline FIND-104 already established for `wallet`/`walletAddress` within `citizens.json` itself). |
| FIND-305 | major | REQ-306's false claim that USD-price normalization reuses "already-available" infrastructure is corrected: `akt-treasury.sh` has no live USD price query (its `P_mint≈0.66` is a one-time historical comment, not a callable rate), and no NOS/SOL/USD or AKT/USD utility exists anywhere in this codebase. REQ-306 now honestly specifies a MINIMAL, genuinely NEW price-fetch step (one public spot-price API call per native token), reusing the exact, already-proven, already-used PATTERN this codebase already applies three times for ETH-USD/SOL-USD (`telemetry-poster.mjs::ethPrice()`, `telemetry-post-franklin.mjs::solPrice()`, `execute-invest.mjs`'s own `ethPrice()`) rather than inventing a bespoke oracle design. |

## Changelog (iteration 4 spec review → iteration 5)

Iteration 4's spec review FAILed with 5 NEW findings (3 critical, 2 major — FIND-401/402/403/404/405;
all 15 prior findings across iterations 1-4 were reconfirmed genuinely resolved against the real,
current source). Each is resolved by a specific, cited design decision, grounded in a full read of
every real artifact these findings cite (`~/anicca/skills/self/spawn-child/`'s `SKILL.md`,
`config.json`, `lib/akt-cost-gate.js`, `sdl/child.yaml`; `~/anicca/skills/self/spawn/`'s `run.sh`,
`scripts/cloud-init.sh`, `scripts/deploy-akash.sh`, `lib/ledger.js`; and a live check of the installed
`provider-services`/`nosana` CLIs' own `--help` output, performed 2026-07-07):

| Finding | Severity | Resolution |
|---|---|---|
| FIND-401 + FIND-402 | critical + critical | The previously-undiscovered sibling skill `~/anicca/skills/self/spawn-child/` is now cited as reused prior art (Scope section, REQ-303 below): it is a narrow, read-only Akash funding-READINESS gate (`lib/akt-cost-gate.js::computeSpawnGate`, already unit-tested) plus a corrected, image-independent SDL template — it does not itself deploy or inject secrets. Separately, and more substantially: REQ-201/301/302/303/304 are corrected to specify a REAL two-phase provisioning sequence for BOTH of this feature's cloud targets — boot the host/lease with ZERO secret material in its public boot config (Akash SDL `env:`, Nosana job command — this was ALREADY correct in the existing artifacts, never a gap), THEN, only after the host/lease is confirmed running, inject the child's own pre-generated wallet material via a NEW, per-provider, authenticated post-boot channel this feature's own orchestration adds: Akash via `provider-services lease-shell <service> "cat > /opt/anicca.env" --stdin` (a real, confirmed-present CLI primitive, `provider-services lease-shell --help`, 2026-07-07); Nosana via `nosana job ssh <job> [port]` (a real, confirmed-present CLI primitive — an actual SSH shell into the running job, `nosana job ssh --help`, 2026-07-07). `deploy-akash.sh`/`akt-treasury.sh` themselves remain byte-identical/unmodified (PROP-303a's claim is preserved, now explicitly SCOPED to those two scripts only); the secrets-injection step is NEW orchestration code this feature adds on top of them, tested as new (not claimed as already-proven reuse). REQ-304 is corrected to drop its false "single-signer, single-transaction" characterization of AKT funding specifically (that claim remains accurate for the same-chain gas-seed transfer and for a same-chain shelter-cost transfer where the funding citizen's native chain already matches the target cloud's native currency) and instead cites the REAL, already-documented multi-hop route `spawn-child/config.json`'s own `funding_route` field specifies for Akash (Jupiter SOL→USDC, then Skip API 4-hop `smart_relay` USDC(solana)→AKT(akashnet-2) via `noble-1`/`osmosis-1`) — reusing that already-vetted route rather than re-deriving a same-chain assumption that does not hold for either of the colony's two actual citizen wallets (neither natively holds AKT). Honesty note (see RESOLUTION-NOTES.md): the pre-existing `~/anicca/skills/self/spawn/scripts/cloud-init.sh`'s own header comment ("Secrets are SCP'd to /opt/anicca.env after boot") is cited here ONLY as the established SECURITY PATTERN precedent (boot-with-zero-secrets, inject-post-boot) — a direct read of `run.sh` confirms NO actual `scp` call exists anywhere in its DO path yet either; that gap is honestly out of scope for THIS feature (DO is not one of REQ-302/303's two cloud targets) and is not claimed as "already proven" anywhere in this revision. |
| FIND-403 | major | REQ-303 now honestly acknowledges that neither `deploy-akash.sh`'s inline default SDL nor `spawn-child/sdl/child.yaml` sets `HOME`/`ANICCA_HOME` in their `env:` block (confirmed by direct read) — this is corrected by specifying that this feature's own child-specific SDL variant (reusing the external template's structure, per REQ-303) adds ONE new, explicit `env:` line, `HOME=/root` (matching `node:22-bookworm`'s own default root-user home, made EXPLICIT rather than relied-upon-implicitly, per PROP-203c's own "never a base-image default" requirement), acknowledged here as a genuinely new, small, necessary SDL modification — the same honesty pattern FIND-305 already established for the price-oracle fix. |
| FIND-404 | critical | REQ-101 now explicitly specifies that a citizen record carrying BOTH `walletAddress.evm` AND `walletAddress.solana` (the expected shape for every Nosana-path child, per REQ-202) has its balance computed as the SUM of both chains' USD-normalized balances — a deliberate design decision, not an unstated ambiguity — with a new edge case, acceptance criterion, and PROP-101f covering exactly this fixture. |
| FIND-405 | major | REQ-402's "bootstrap_failed" relabeling text now explicitly cross-references REQ-101's already-established last-write-wins reduction by name: the relabeling is implemented as `appendChild`-ing a NEW row with the same `child_id` (never mutating the prior row in place — `ledger.js` remains exactly `{readChildren, appendChild}`), and this new row becomes "the" effective row for that citizen precisely because `filterProductiveCitizens`'s last-write-wins reduction (REQ-101) picks it up on the next read — identical to the clarification FIND-301 already gave REQ-101/REQ-305's own analogous writes. |

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
  documentation before being specified (see citations inline). The Akash leg additionally REUSES a
  previously-undiscovered sibling skill, `~/anicca/skills/self/spawn-child/` (its own `SKILL.md`: "Akash
  self-spawn READINESS gate... narrow, read-only... never moves money"), for its funding-readiness
  arithmetic (`lib/akt-cost-gate.js::computeSpawnGate`) and its corrected, image-independent SDL
  template (`sdl/child.yaml`) — see REQ-303 (added iteration 5, resolves FIND-402).
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
backward-compatible exception (`child-spec.js`'s identity-anchor validation). This feature never
extends the DO-specific path (`run.sh --host=do`, `scripts/cloud-init.sh`) to a real spawn — REQ-302/303
are the only two deploy targets this increment specifies — but `cloud-init.sh`'s own header comment
("SECURITY: NO secret VALUES in user_data... Secrets are SCP'd... after boot") IS cited (REQ-303/402
resolution, iteration 5) as the established SECURITY-PATTERN PRECEDENT this feature's own Akash/Nosana
secrets-injection mechanism follows; it is cited for that pattern only, never as a claim that DO's own
SCP step is itself already wired (a direct read of `run.sh` confirms it is not — see RESOLUTION-NOTES.md
for iteration 5).

**Also reconciled, iteration 5 (resolves FIND-402)**: the separate, already-complete, narrower
`~/anicca/skills/self/spawn-child/` skill (a 2026-07-05 Akash-specific funding-READINESS gate + a
corrected SDL template, per its own `SKILL.md`) is REUSED — not rebuilt, not duplicated — by REQ-303's
Akash-specific funding-readiness check (`lib/akt-cost-gate.js::computeSpawnGate`) and by REQ-304's
AKT-funding-route citation (`config.json`'s own `funding_route` field). `spawn-child` itself remains
unmodified; this spec adds no new requirement group for it, since its own SKILL.md already documents it
as complete ("does not need re-building").

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
| Akash `provider-services` exposes an authenticated exec-into-running-lease primitive | **New finding, iteration 5 (resolves FIND-401)** | `provider-services lease-shell --help` (installed CLI, checked live 2026-07-07): "do lease shell... Usage: provider-services lease-shell <service-name> <command> [flags]... --stdin connect stdin" — a real, present primitive, the Akash analog of an authenticated SSH exec channel into a running container. Never previously cited anywhere in this spec. |
| Nosana CLI exposes an authenticated exec-into-running-job primitive | **New finding, iteration 5 (resolves FIND-401)** | `nosana job ssh --help` (installed CLI, checked live 2026-07-07): "Open an SSH shell into a running job... Usage: nosana job ssh [options] <job> [port]" — a real, present primitive (an actual SSH shell, proxied through Nosana's own relay). Never previously cited anywhere in this spec; the exact non-interactive (single-command) invocation shape is not independently re-verified beyond this `--help` output in this revision (see REQ-302). |

No other drift was found: both CLIs, both wallet models (Solana-keypair-auto-gen for Nosana,
`provider-services`+SDL for Akash), and this repo's existing `deploy-akash.sh`/`akt-treasury.sh`
scripts remain aligned with current upstream documentation.

## Purity boundary analysis (overview — file/function detail lives in verification-architecture.md)

| Concern | Classification | Why |
|---|---|---|
| Colony self-funded citizen filter | **Pure core (existing, reused unmodified)** | `~/anicca/skills/_shared/lib/is-self-funded.mjs::isSelfFunded(agent)` — already implements exactly the "own wallet + own-funded fuel + zero human deps" test this feature's REQ-101 needs to decide which balances even count toward the colony surplus. No new judgment logic is written; REQ-101 calls this existing, already-tested function on each RECORD supplied by REQ-105's registry (below) — `isSelfFunded()` itself is untouched; only its INPUT source is now specified. |
| Colony citizen registry (data source for REQ-101) | **Effectful shell (BRAND NEW, dedicated file — REQ-105, revised to resolve FIND-101/202/302/304)** | `~/anicca/skills/self/spawn/registry/citizens.json` — a brand-new file created fresh by this feature, holding an array of `{id, wallet: {evm?: boolean, solana?: boolean}, walletAddress: {evm?: string, solana?: string}, fuel, humanDependencies, homeDir}` records (`telemetryPath` REMOVED from this schema, resolves FIND-302) — the BOOLEAN-shaped `wallet` field is the exact shape `isSelfFunded()` already requires (resolves FIND-104's type mismatch; UNRELATED to `child-spec.js`'s own returned-row `wallet` STRING field, resolves FIND-304), `walletAddress` separately carries the real address string(s) and is what REQ-101's `readCitizenBalances` keys its RPC query on, and `homeDir` is an ALREADY-RESOLVED absolute path (never an unresolved `$HOME` template, resolves FIND-202) feeding REQ-403's now co-located-only-scoped audit (resolves FIND-303). This registry deliberately carries NEITHER `status` NOR `active_since` — those lifecycle facts live exclusively in `ledger.js` (see below, resolves FIND-201). Seeded with a FIXED LITERAL 2-entry array (the colony's only currently-verified self-funded citizens) — NOT a migration, and sharing ZERO state with the pre-existing `~/anicca/skills/economy/ubi/colony-wallets.json` (see next row). |
| Pre-existing mutual-aid recipient list (untouched, out of scope) | **Effectful shell (existing, NOT read/written by this feature)** | `~/anicca/skills/economy/ubi/colony-wallets.json` — `ubi.js::distributeAI`'s own recipient-eligibility list ("addresses proven to be real colony members," its own JSDoc), a DIFFERENT purpose than REQ-101's surplus aggregation. Its current 2nd entry is claude-p's own human-funded wallet (`docs/WALLETS.md` lines 49-62). This feature never reads, writes, or repurposes this file — resolves FIND-101's critical finding that an earlier draft wrongly proposed migrating/extending it, which would have risked a human-funded wallet silently entering the colony-surplus aggregate. |
| Colony surplus aggregation | **Pure core (new)** | A sum of `max(0, balance_i - perCitizenReserveUsd)` over self-funded, currently-productive citizens only — deterministic arithmetic over already-fetched balances, no I/O once inputs are supplied (REQ-101). Fed exclusively by `filterProductiveCitizens({citizens, ledgerRows, nowMs, bootstrapWindowDays})`, a new pure join function that cross-references REQ-105's registry against `ledger.js`'s rows to exclude `"bootstrap_failed"`/window-overdue children before this sum ever runs (resolves FIND-201). |
| Spawn eligibility gate | **Pure core (new, extends an existing pattern)** | `~/anicca/skills/self/spawn/lib/spawn-decision.js::decideSpawn` already establishes the exact target shape (`{eligible, reason}`, pure, no I/O) this feature's colony-scoped gate follows — REQ-102 is a colony-aggregate generalization of that same pattern, not a new design. |
| Per-child identity record assembly | **Pure core (existing, extended — small, backward-compatible modification, REQ-206)** | `~/anicca/skills/self/spawn/lib/child-spec.js::nextChildId`/`buildChildSpec` — monotonic ID (unchanged) + an identity-anchor validation that now accepts EITHER the old `childInbox` (AgentMail) OR the new `agentEvmAddress`+`agentId` (ERC-8004) pair, never requiring both (REQ-206). This corrects iteration 1's false "reused unmodified" claim (FIND-001): the distinct-wallet assertion and every other existing field/behavior are untouched, and a regression test locks in that today's `childInbox`-only callers still succeed identically. `buildChildSpec`'s OTHER four already-mandatory fields (`parentWallet`, `generation`, `seedUsdc`, `constitutionHash`) are unchanged CODE but now have an explicit spec-level derivation rule each (REQ-206, resolves FIND-204) — the function's own source is not modified for these four; only the caller-supplied values are now specified. |
| Cross-instance spawn mutual exclusion (lock predicate) | **Pure core (existing, reused unmodified)** | `~/anicca/skills/economy/gig/lib/lock.mjs::isLockStale(nowMs, mtimeMs, staleMs)` — the already-adversary-hardened staleness predicate from the P2 concurrency-hardening sprint (`anicca-agent-economy` REQ-101). REQ-103 reuses the SAME generic file-lock module under a new lock key (`"colony-spawn"`), not a new lock implementation. This module's local-POSIX-filesystem guarantee is sufficient ONLY because REQ-106 scopes every evaluator to a single coordinator host this increment (FIND-003) — it is not claimed to solve cross-host mutual exclusion. |
| Cloud target selection (Nosana vs Akash) | **Pure core (new) + Effectful shell (new)** | A pure comparison function `selectCloudTarget({nosanaAvailable, nosanaPriceUsd, akashAvailable, akashPriceUsd}) → "nosana"\|"akash"\|"none"` (deterministic, price-based, never a model judgment — REQ-306) fed by an effectful price/availability query step against each provider's own CLI/API, INCLUDING a genuinely NEW USD-normalization price-fetch step (one public spot-price API call per native token, reusing the exact fail-closed pattern already established by `ethPrice()`/`solPrice()` elsewhere in this codebase — resolves FIND-305's false "already-available oracle" claim; `akt-treasury.sh` has no live USD price query). Resolves FIND-006 (REQ-302/303 presupposed this selection without ever specifying it). |
| Balance/telemetry reads across colony instances | **Effectful shell (revised, resolves FIND-302)** | A NEW, coordinator-run, registry-driven public-RPC balance query, `readCitizenBalances({citizens})`, keyed on each citizen's own `walletAddress` (REQ-105) — generalizing `~/anicca/skills/self/telemetry-collect.sh`'s own existing hardcoded-3-instance RPC-by-address pattern (`erc20()`/`sol()`/`solusdc()` against public RPC endpoints) into a registry-driven loop, so it reaches a REQ-301-mandated cloud-hosted child's balance exactly as readily as a co-located citizen's (a public RPC call does not care where the querying process runs, unlike the coordinator-local `fs.readFile` this mechanism REPLACES — REQ-105's `telemetryPath` field is REMOVED as a result, its sole purpose now served by this walletAddress-keyed RPC read). Real I/O, not inferred. |
| Child EVM wallet generation | **Effectful shell** | `~/anicca/skills/self/spawn/scripts/gen-wallet.sh` — `openssl`+`python3` subprocess, real entropy source, reused unmodified. |
| Child Solana keypair generation | **Effectful shell (new)** | New script analogous to `gen-wallet.sh` but ed25519/Solana-shaped (REQ-202); real entropy source. |
| `$HOME`/`ANICCA_HOME` isolation at process launch | **Effectful shell** | Setting an env var at process spawn time is an OS-level side effect; the isolation PROPERTY it produces (a distinct resolved path) is what REQ-203 specifies and what `~/anicca/skills/earn/lib/resolve-identity.mjs` already relies on for existing instances. |
| ERC-8004 `register()` | **Effectful shell (existing, reused unmodified)** | `~/anicca/skills/economy/gig/lib/identity.mjs::registerIdentity`/`verifyIdentity`, called THROUGH the existing, already-tested `~/anicca/skills/economy/gig/lib/ensure-agent-id.mjs::ensureAgentId` cache-then-verify-then-register-once wrapper (not re-derived from scratch — resolves FIND-004) — a real on-chain transaction (mainnet registry `0x8004A169FB4a3325136EB29fA0ceB6D2e539a432` on Base, chain 8453; testnet `0xdc527768082c489e0ee228d24d3cfa290214f387` on Base-Sepolia; both independently re-verified live 2026-07-07 per that file's own header). |
| gig-board `mcp.json` generation | **Effectful shell (new, template reused)** | File write following the exact shape of the already-live, verified `~/.blockrun/mcp.json`. |
| Nosana job deploy | **Effectful shell (new)** | Real `nosana job post` subprocess against a real Solana-settled market; genuinely new for this project (REQ-302). |
| Akash job deploy | **Effectful shell (existing, reused unmodified) + new secrets-injection step (revised iteration 5, resolves FIND-401/402/403)** | `~/anicca/skills/self/spawn/scripts/deploy-akash.sh` + `akt-treasury.sh` — already implemented, already tested against a real sandbox-2 chain per those scripts' own inline evidence references; reused unmodified with a new CHILD-SPECIFIC SDL (NOT byte-identical to `spawn-child/sdl/child.yaml` — that template lacks an explicit `HOME`/`ANICCA_HOME` `env:` line, confirmed by direct read; this feature's own variant adds ONE new line, `HOME=/root`, resolves FIND-403) and `CHILD_ID` (REQ-303). PROP-303a's "zero source modification" claim is scoped to `deploy-akash.sh`/`akt-treasury.sh`'s own script files only, never to this new SDL variant. A genuinely NEW post-lease-active secrets-injection step (this feature's own orchestration code, never a `deploy-akash.sh` modification) delivers the child's pre-generated wallet material (REQ-201/202) via `provider-services lease-shell <service> "cat > /opt/anicca.env" --stdin` (confirmed-present CLI primitive, `lease-shell --help`, 2026-07-07) — resolves FIND-401's core gap: neither the SDL nor `install.sh` ever provided ANY channel for this. |
| Akash-specific AKT funding-readiness gate (reused, new to this feature — resolves FIND-402) | **Pure core (existing, reused unmodified) + effectful config read** | `~/anicca/skills/self/spawn-child/lib/akt-cost-gate.js::computeSpawnGate({balanceAkt, costAkt, bufferAkt}) → {ready, reason, thresholdAkt, shortfallAkt}` — already implemented, already unit-tested (`lib/__tests__/akt-cost-gate.test.js`); REQ-303 calls it with `costAkt`/`bufferAkt` read from `spawn-child/config.json`'s own real values (`spawn_cost_akt: 25`, `buffer_akt: 1`) BEFORE invoking `akt-treasury.sh`/`deploy-akash.sh` — a DIFFERENT, narrower concern than REQ-102's colony-wide `MIN_SHELTER_USD`/`SPAWN_THRESHOLD_USD` (cross-cloud aggregate USD surplus), never a competing reimplementation of it. |
| Nosana job deploy — post-boot secrets-injection (new, resolves FIND-401's Nosana-side analog) | **Effectful shell (new)** | A NEW orchestration step delivering the child's pre-generated Solana/EVM wallet material onto a `RUNNING` Nosana job via `nosana job ssh <job> [port]` (confirmed-present CLI primitive, `job ssh --help`, 2026-07-07) — genuinely new, never previously specified; the exact non-interactive invocation shape is confirmed against the actually-installed CLI at Phase 2, not asserted here as already-proven (REQ-302). |
| Shelter-cost funding transfer | **Effectful shell (new)** | A real on-chain transfer from a citizen's own wallet to cover a deploy's escrow/deposit, gated on REQ-102's already-certified amount (REQ-304). For Akash's `uact` requirement specifically, this is a MULTI-HOP transfer (Jupiter SOL→USDC, then Skip API 4-hop `smart_relay` USDC(solana)→AKT(akashnet-2) via `noble-1`/`osmosis-1`) reusing `spawn-child/config.json`'s own already-documented `funding_route` — NOT a single-signer single-transaction transfer for this specific target, since neither current citizen's wallet natively holds AKT (revised iteration 5, resolves FIND-402(c)). |
| Spawn ledger append | **Effectful shell (existing, reused unmodified) + a new registry-append side effect (REQ-105/305)** | `~/anicca/skills/self/spawn/lib/ledger.js::appendChild`/`readChildren` — append-only JSONL, already implemented, unmodified. This feature's own rows are the SOLE canonical owner of each child's lifecycle state (`status`, and a new `active_since` field REQ-305 sets the moment a child is first marked `"active"`) — REQ-402's window check and REQ-101's `filterProductiveCitizens` join both read `active_since`/`status` from THESE rows, never from `citizens.json` (resolves FIND-201). On a successful spawn (child marked `"active"`), REQ-305 ALSO appends a new record to REQ-105's colony citizen registry (`~/anicca/skills/self/spawn/registry/citizens.json` — NOT `economy/ubi/colony-wallets.json`, which this feature never touches) — a new, explicit write path this spec did not previously specify (resolves FIND-002's "how does the registry grow" gap), GATED on an `isSelfFunded()` pre-append check that REFUSES the append if the new record would itself fail that gate (resolves FIND-101's permanent-hazard-closure requirement). |
| $0-bootstrap independent on-chain re-verification | **Effectful shell (new)** | A fresh RPC `eth_call`/balance read performed independently of either trading party's self-report, mirroring the exact method SPEC.md §9.9 already used to confirm Franklin#1's final USDC balance (REQ-401). |
| Wallet mutual non-interference audit | **Effectful shell + static analysis (new)** | A grep-based static source audit (Tier 0) PLUS a live runtime comparison of resolved signing keys across N ≥ 2 concurrently-running instances (Tier 2/3) — reusing the exact "grep all path forms across skill scripts and cron config" method this project's own wallet-rotation work already established (REQ-403). |
| REQ-104 (bookkeeping-only design constraint) | **Not code — a design constraint, verified structurally** | Directly analogous to `anicca-agent-economy`'s REQ-203 ("Design-constraint requirement — bookkeeping only, never judgment"): not independently unit-testable in the normal sense; verified by a Phase 3 structural code read (no scoring/ranking/preference logic anywhere in REQ-101-103's diff), not a runtime assertion. |

---

## Requirements

### REQ群A: 決定論 treasury ゲート

### REQ-101: Colony self-funded surplus aggregation
**EARS**: WHEN any component needs to know how much surplus the colony has available to fund a new
spawn, THE SYSTEM SHALL compute it as the sum, over every **self-funded, currently-productive** citizen
only, of `max(0, balance_i − perCitizenReserveUsd)`, where the candidate citizen list is assembled in
two explicit, separately-owned steps, never a single blended lookup (resolves FIND-201's location
contradiction between REQ-105's registry and REQ-402's ledger-based lifecycle state):
1. READ the candidate citizen array from REQ-105's colony citizen registry (`citizens.json`) — never
   hardcoded inline in this aggregation — and call `isSelfFunded()`
   (`~/anicca/skills/_shared/lib/is-self-funded.mjs`, reused unmodified) on each record's `{wallet,
   fuel, humanDependencies}` sub-object to decide which citizens count as self-funded at all.
2. JOIN that self-funded subset against REQ-402's lifecycle state — which lives EXCLUSIVELY in
   `~/anicca/skills/self/spawn/lib/ledger.js`'s own JSONL rows (`status`, `active_since`), NEVER in
   `citizens.json` (REQ-105's registry is deliberately minimal and carries neither field) — via a new,
   pure join function `filterProductiveCitizens({citizens, ledgerRows, nowMs, bootstrapWindowDays}) →
   citizens[]`, zero I/O, matched by `citizens[].id` against `ledgerRows[].child_id`.

   **`ledgerRows` may legitimately contain MULTIPLE rows sharing one `child_id` (resolves FIND-301):**
   `ledger.js` is real, existing, append-only JSONL, reused unmodified — it exports exactly
   `readChildren`/`appendChild`, no update/upsert primitive, and this spec does NOT add one — so every
   lifecycle transition (`"provisioning"` → `"active"`, or → `"bootstrap_failed"`, or a later
   retroactive correction, REQ-402) is recorded by APPENDING A NEW LINE with the SAME `child_id`, never
   by mutating an existing line. This is not hypothetical: the superseded `run.sh`'s own real, existing
   behavior already does exactly this on every spawn attempt (`run.sh:124-140` appends a
   `"provisioning"` row, then a LATER, SEPARATE `appendChild` call at `run.sh:200-205` or
   `run.sh:213-220` appends a SECOND row with the SAME `child_id` and an updated `status`
   (`"seed_failed"` or `"active"`) — proving `readChildren`'s raw output routinely contains duplicate
   `child_id` rows in real production usage). Because JSONL append order is strictly chronological,
   "that row" (the row a citizen with a matching `child_id` is evaluated against, below) MEANS the LAST
   (highest array index / most-recently-appended) row for that `child_id` — last-write-wins is the
   correct, and only specified, reading of "current status." `filterProductiveCitizens` MUST reduce
   `ledgerRows` to exactly one effective row per `child_id` (its last-appended row) BEFORE applying the
   exclusion rule below; it MUST NOT match against the FIRST row for a `child_id` (which would
   incorrectly mean a child is NEVER observed past `"provisioning"`) nor pick nondeterministically among
   duplicates.

   A citizen with NO matching ledger row (e.g. today's two seed citizens, automaton/Franklin, which were
   never spawned via this feature) passes through unfiltered; a citizen WITH a matching ledger row is
   EXCLUDED if that (last-appended) row's `status` is already `"bootstrap_failed"`, OR if that row's
   `status` is `"active"` with no recorded REQ-401 success and `nowMs − active_since >=
   bootstrapWindowDays * 86400000` (the same window REQ-402 itself applies, checked here too as a
   real-time safeguard so REQ-101 never has to wait for REQ-402's own separately-scheduled relabeling
   job to have already run this wake).

`computeColonySurplusUsd({citizens, perCitizenReserveUsd})` then runs ONLY on
`filterProductiveCitizens`'s OUTPUT — never on the raw registry array — where `balance_i` is that
citizen's own most-recently-read liquid balance, obtained via a NEW, coordinator-run, registry-driven
effectful step, `readCitizenBalances({citizens})` (`~/anicca/skills/self/spawn/lib/colony-balances.mjs`),
that queries EACH citizen's balance directly from PUBLIC CHAIN RPC, keyed on that citizen's own
`walletAddress` (REQ-105's registry field, already present) — generalizing, rather than reinventing, the
EXACT mechanism `~/anicca/skills/self/telemetry-collect.sh` already proves works today (that script's
own `erc20()`/`sol()`/`solusdc()` helpers query `base-rpc.publicnode.com`/`api.mainnet-beta.solana.com`
by a hardcoded wallet-address CONSTANT per instance, writing a local `telemetry.json` as a SEPARATE,
unrelated side effect this feature does not depend on) into a REGISTRY-DRIVEN loop over
`citizens[].walletAddress` instead of 3 hardcoded constants (resolves FIND-302: a public RPC balance
read does not care where the querying PROCESS runs, unlike a local `fs.readFile`, so this mechanism
reaches a REQ-301-mandated cloud-hosted child's balance exactly as readily as it reaches a co-located
citizen's — no coordinator-local filesystem access to the child's own disk is ever required).
`telemetryPath` is REMOVED from REQ-105's registry schema (below) — its sole prior purpose (locating
this balance) is now served by this walletAddress-keyed RPC mechanism instead; `telemetry-collect.sh`'s
own separate `telemetry.json` output remains, unmodified, an independent, out-of-scope mechanism for the
public dashboard (not read by this feature). `perCitizenReserveUsd` defaults to `5.00` (reusing, for
consistency, the exact `RESERVE = 5.0` constant `economy/ubi/run.sh` already uses for the same "don't
count money a citizen needs for its own survival" purpose — not a new number invented for this feature).

**Dual-chain balance handling (resolves FIND-404):** A citizen record legitimately carries BOTH
`walletAddress.evm` AND `walletAddress.solana` simultaneously — this is the EXPECTED shape for every
Nosana-path child this feature ever produces (REQ-201 unconditionally generates an EVM wallet for every
child; REQ-202 additionally generates a Solana wallet whenever the child is Nosana-deployed; REQ-305's
own append template records both address strings when both exist). THE SYSTEM SHALL, for such a citizen,
SUM both chains' USD-normalized balances into that citizen's single `balance_i` for this aggregation —
never pick one chain and ignore the other, and never treat the dual-wallet shape itself as a malformed
record. This is a deliberate design decision (the citizen's TOTAL liquid surplus, not one chain's share
of it, is what REQ-102's colony-wide threshold gate needs to reason about), not an unstated ambiguity:
`readCitizenBalances` queries EACH populated `walletAddress` field independently (EVM via the existing
`erc20()`-style public-RPC pattern, Solana via the existing `sol()`/`solusdc()`-style pattern, both
already established by `telemetry-collect.sh`), normalizes each to USD via the same already-proven
spot-price mechanism (`ethPrice()`/`solPrice()`), and returns their SUM as that citizen's one balance
figure — a citizen with only ONE populated `walletAddress` field degenerates to that single chain's own
balance, with no special-casing required.

**Edge Cases**:
- A citizen's public-RPC balance query fails, times out, or returns a non-finite/negative value:
  that citizen contributes **0** to the sum (fail-closed — never treated as infinite/unknown-but-fine),
  matching the existing `tier.mjs`/`catalog-gate.mjs` convention of "unparseable numeric input collapses
  to the safe default," here the safe default being "counts for nothing until it can be read cleanly"
  (resolves FIND-302: this replaces the prior "telemetry.json missing/unreadable" framing, which assumed
  a coordinator-local file read that cannot reach a remote child).
- A citizen's `child_id` has TWO OR MORE matching `ledger.js` rows with different `status` values (e.g.
  a `"provisioning"` row followed later by an `"active"` row for the SAME child): `filterProductiveCitizens`
  uses ONLY the LAST (most-recently-appended) row's `status`/`active_since` — never the first, never an
  arbitrary pick (resolves FIND-301; `ledger.js` is real, append-only, and legitimately produces exactly
  this shape per real spawn attempts, per `run.sh`'s own existing provisioning-row-then-status-row
  pattern).
- A citizen's matching ledger.js row has `status:"active"` but a missing/non-finite `active_since`
  (a malformed row): `filterProductiveCitizens` applies the SAME fail-closed convention as above —
  the citizen is excluded from the productive set until the row is corrected, never assumed fresh.
- Exactly one self-funded citizen exists (current colony state, per §9.9/§9.5): the sum degenerates to
  that single citizen's own surplus-above-reserve; the formula requires no special case for N=1.
- A citizen's on-chain balance is native-token-denominated only (e.g. a Solana citizen's SOL/native-USDC
  holdings, exactly the shape `telemetry-collect.sh`'s own existing `sol()`/`solusdc()` helpers already
  produce for Franklin — `balance_native: {sol, usdc}`, no single `balance_usd` field): THE SYSTEM SHALL
  normalize to USD using the SAME already-proven, already-used spot-price pattern this codebase already
  applies for exactly this purpose (`runtime/dashboard/telemetry-post-franklin.mjs::solPrice()`'s single
  Coinbase SOL-USD spot-price call) rather than inventing a second conversion path — the identical
  discipline `economy/ubi/run.sh`'s own `bal()` helper already applies for its own, differently-scoped
  purpose.
- A citizen's registry record carries BOTH `walletAddress.evm` AND `walletAddress.solana` populated
  simultaneously (the expected Nosana-path shape, REQ-202): `readCitizenBalances` queries and
  USD-normalizes BOTH chains independently and returns their SUM as that citizen's single balance figure
  — never one chain alone, and never treated as a malformed/ambiguous record (resolves FIND-404). A
  citizen with a nonzero balance on one chain and zero on the other still correctly contributes the sum
  (i.e., the nonzero chain's own normalized value) — no special case is needed for the "one chain is
  empty" sub-case.

**Acceptance Criteria**:
- Pure function, e.g. `computeColonySurplusUsd({ citizens, perCitizenReserveUsd }) → number`, takes
  already-fetched balance data as input and performs zero I/O itself.
- Given a fixture citizen with a nonzero, independently-verifiable balance on BOTH its `walletAddress.evm`
  AND `walletAddress.solana` fields, `readCitizenBalances` returns a total equal to the SUM of both
  chains' own USD-normalized values (each normalized via the existing `ethPrice()`/`solPrice()`
  mechanism) — never either chain's value alone (resolves FIND-404).
- Given two self-funded citizens with balances `$8` and `$3` and `perCitizenReserveUsd=5`, returns
  `max(0,8-5) + max(0,3-5) = 3 + 0 = 3`.
- Given a citizen whose `isSelfFunded()` check returns `false`, its balance (however large) contributes
  `0` regardless of magnitude.
- `filterProductiveCitizens({ citizens, ledgerRows, nowMs, bootstrapWindowDays }) → citizens[]` is a
  pure function, zero I/O, that FIRST reduces `ledgerRows` to at most one effective row per `child_id`
  (the LAST-appended row for that id — last-write-wins, resolves FIND-301), THEN excludes exactly the
  citizens whose (reduced) matching row is `"bootstrap_failed"` or window-overdue-while-`"active"`, and
  passes through unfiltered any citizen with no matching ledger row (resolves FIND-201).

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
plus ONE additional field this feature needs and `isSelfFunded()` itself does not read (revised, resolves
FIND-302: the prior second additional field, `telemetryPath`, is REMOVED from this schema — REQ-101's
balance lookup no longer depends on a coordinator-local file path per citizen; see REQ-101's revised
`readCitizenBalances`, which reads each citizen's balance via public RPC keyed on `walletAddress` above,
a mechanism that works identically whether that citizen is co-located with the coordinator or, per
REQ-301, exclusively cloud-hosted):
- `homeDir: string` — the citizen's own resolved absolute `HOME`/`ANICCA_HOME` directory (e.g.
  `/Users/anicca`, or a dedicated per-instance HOME if the colony ever runs non-co-located instances),
  used exclusively by REQ-403's wallet mutual non-interference audit's LIVE comparison half — itself now
  scoped to co-located instances only for this increment (resolves FIND-303; see REQ-403) — to learn
  each CO-LOCATED running instance's own HOME without a second, parallel instance-enumeration mechanism
  (resolves FIND-202). Both of today's seeded citizens (automaton, Franklin) legitimately share the
  identical `homeDir` value (`/Users/anicca`, per REQ-106's single-coordinator-host scoping) THIS
  increment — that is expected, not a bug. A future cloud-hosted child's `homeDir`, if ever recorded,
  is NOT consulted by REQ-403's live check this increment (that check is co-located-only) — the field
  is present on every record only so a future increment's remote-audit mechanism has somewhere to read
  it from.

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
    "homeDir": "/Users/anicca"
  },
  {
    "id": "Franklin",
    "wallet": { "solana": true },
    "walletAddress": { "solana": "8FpqdcCHqjqkVXR58eVJa53neXbJf9emXhvHhgeUPCV9" },
    "fuel": { "provider": "x402" },
    "humanDependencies": [],
    "homeDir": "/Users/anicca"
  }
]
```

Both entries' `homeDir` values are ALREADY-RESOLVED absolute paths — never a `$HOME`-template string —
because this spec's author already knows the real, concrete path each citizen uses at seed time
(resolves FIND-202). Both entries legitimately share the identical `homeDir` (`/Users/anicca`) because
both citizens currently run co-located on the same coordinator host per REQ-106 — expected for this
increment, not an error. Neither entry carries a `telemetryPath` field (removed, resolves FIND-302 —
see above).

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
  humanDependencies, homeDir}` (no `telemetryPath` field — removed, resolves FIND-302), and calling the
  existing, unmodified `isSelfFunded()` on any one record's `{wallet, fuel, humanDependencies}`
  sub-object (never `walletAddress`) returns a boolean without throwing.
- Every seeded (and later appended, REQ-305) entry's `homeDir` is an ALREADY-RESOLVED absolute path — a
  structural check confirms its value never contains the literal substring `$HOME` or `$ANICCA_HOME`
  anywhere in `citizens.json` (resolves FIND-202).
- A direct test confirms that EACH of the two seeded entries above, when its `{wallet, fuel,
  humanDependencies}` sub-object is passed through the existing, unmodified `isSelfFunded()`, returns
  `true` — a straightforward assertion against literal fixture data (resolves FIND-101's critique of
  the prior "compare against today's known-good identities" proof method, which presupposed an
  out-of-band ground truth no longer needed once there is no migration).
- `citizens.json`'s seed content contains ZERO entries whose `isSelfFunded()` verdict is `false` — and
  REQ-305's append-on-spawn path (below) enforces the SAME property on every future append, closing
  this hazard PERMANENTLY rather than only at t=0.
- REQ-403 (the wallet non-interference audit's "current set of co-located running instances," this
  increment — resolves FIND-303) reads its citizen list AND each instance's `homeDir` directly from
  THIS SAME registry — no second, parallel instance-enumeration mechanism exists anywhere in this spec.
  REQ-402/REQ-101's productivity exclusion (`"bootstrap_failed"`, `active_since`) is a SEPARATE concern
  that lives EXCLUSIVELY in `ledger.js` — see REQ-101's `filterProductiveCitizens` join and REQ-402 —
  this registry intentionally carries neither field (resolves FIND-201's location contradiction).

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
- The generated private key material must be delivered to the child's own remote lease/job via REQ-303's
  (`provider-services lease-shell`) or REQ-302's (`nosana job ssh`) post-boot injection channel ONLY —
  THE SYSTEM SHALL NEVER write this key material into any boot-time artifact (an SDL `env:` line, a
  Nosana job command string, a cloud-init `user_data` field, or any other artifact
  `provider-services sdl-to-manifest`/a job-definition dump would expose publicly) at any point between
  generation and injection (resolves FIND-401: this is the structural property that makes the two-phase
  "boot secretless, inject after" sequence in REQ-302/303 actually correct, rather than merely asserted).

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

**Cross-file field-name disambiguation (resolves FIND-304):** `buildChildSpec`'s own, pre-existing,
UNMODIFIED returned row carries a field literally named `wallet` (`child-spec.js:37`: `wallet:
childWallet` — a bare address STRING; confirmed by its own existing test, `child-spec.test.js:36`:
`assert.strictEqual(spec.wallet, "0xCHILD...")`). This is a COMPLETELY SEPARATE field, in a COMPLETELY
SEPARATE file/schema, from REQ-105's `citizens.json` registry record's `wallet` field, which is a
BOOLEAN presence-flag object (`{evm?: boolean, solana?: boolean}`, REQ-105). The two `wallet` fields
share a name only by coincidence across two unrelated schemas this feature touches — this spec does NOT
rename `child-spec.js`'s existing field (that would violate its "unmodified" contract, the same
discipline already established above for this file) — implementers and reviewers MUST read each
`wallet` field per its OWN file's schema and MUST NOT cross-reference the two (same class of
disambiguation FIND-104 already performed for `wallet`/`walletAddress` WITHIN `citizens.json` itself;
here it is a cross-file clarifying note, not a schema change).

**The other four fields `buildChildSpec` already unconditionally requires** (`parentWallet`,
`generation`, `seedUsdc`, `constitutionHash` — confirmed still mandatory at
`~/anicca/skills/self/spawn/lib/child-spec.js:16-34`, unrelated to and untouched by the identity-anchor
extension above) **are reconciled with this feature's actual architecture as follows** (resolves
FIND-204 — REQ-206 is extended to cover these four, not merely the identity-anchor clause):
- **`parentWallet`**: set to REQ-106's single coordinator-host citizen's OWN wallet address — the
  citizen that evaluated REQ-101/102/103 and is driving this spawn attempt (never a synthesized or
  absent value). This value is always distinct from the freshly generated `childWallet` (REQ-201), so
  `buildChildSpec`'s own existing `childWallet === parentWallet` throw is never triggered by a
  colony-treasury-funded spawn. REQ-304's multi-citizen co-funding (no single "parent" for FUNDING
  purposes) is a SEPARATE concept from `parentWallet` here, which only identifies the
  coordinator-driving citizen for `buildChildSpec`'s own distinct-wallet bookkeeping — it does not imply
  that citizen alone funded the deploy.
- **`generation`**: fixed at `1` for every child this feature produces — reusing, not inventing, the
  SAME default `run.sh` already hardcodes (`"${ANICCA_GENERATION:-1}"`, `run.sh:136`) — because this
  feature's colony-treasury-funded spawns are, by design, top-level, non-lineage children (REQ-304's own
  edge case already establishes there is no single funding "parent" to derive a lineage depth from);
  spawn CHAINING (which would need a real generation-incrementing rule) is explicitly out of scope this
  increment (REQ-106).
- **`seedUsdc`**: IS REQ-204's gas-seed USDC amount — the SAME value, passed straight through (never a
  second, independently-derived quantity). REQ-303/304's "shelter cost" (cloud hosting/lease cost) is a
  GENUINELY DISTINCT amount — never conflated with `seedUsdc` — funded and ledgered separately per
  REQ-303/304's own mechanism.
- **`constitutionHash`**: a fixed SHA-256 hex digest of `~/anicca/identity/genesis.md`'s content — the
  SAME canonical identity-seed file `install.sh` already ships verbatim into every new instance's own
  `ANICCA_HOME` (`install.sh:78-93`, "Canonical hustle genesis lives at identity/genesis.md in the repo;
  ship it verbatim") — computed ONCE and treated as a fixed spec-level constant for this feature (not
  recomputed per spawn, since every child this increment produces inherits the identical, unmodified
  genesis file). A future increment that needs per-child constitution variation would need a dedicated
  new requirement; this increment's children are all identical-genesis siblings.

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
- `parentWallet` is supplied as the coordinator-host citizen's own wallet and happens to equal the
  freshly-generated `childWallet` (an astronomically unlikely secp256k1 collision, REQ-201's own
  defensive check): `buildChildSpec`'s existing, untouched `childWallet === parentWallet` throw fires
  exactly as it already does today — this feature relies on that EXISTING check, never a new one.
- `generation` is passed as anything other than `1` for a colony-treasury-funded spawn (a future coding
  error): THE SYSTEM treats this as a spec violation to be caught at Phase 3 review — this increment's
  children are never lineage-chained, so `1` is the only value this requirement authorizes.
- `seedUsdc` and REQ-204's actual gas-seed transfer amount ever diverge (a future bug passing two
  different numbers into `buildChildSpec` vs the real on-chain gas-seed transfer): THE SYSTEM treats
  this as a spec violation — the two MUST be the identical value by construction, never merely close.

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
- A fixture/integration test calls `buildChildSpec` with all SEVEN required fields populated per the
  derivation rules above (`parentWallet`=a fixture coordinator wallet, `generation`=1, `seedUsdc`=the
  same fixture gas-seed amount used elsewhere in the test, `constitutionHash`=the real SHA-256 of
  `identity/genesis.md`, plus the ERC-8004 anchor pair) and asserts success with every field correctly
  present in the returned row — not just the two identity-anchor-focused fixtures (PROP-206a/b) already
  specified (resolves FIND-204).
- `generation` is asserted to be exactly `1` for every REQ-305 spawn-flow call in this increment; a
  structural/Tier-0 check confirms no code path in this feature's diff passes any other value.
- `seedUsdc`'s value, in every real REQ-305 call, is asserted identical to the amount REQ-204 actually
  transferred as the gas seed for that same spawn attempt — never an independently-computed number.

---

## REQ群C: cloud deployment（新規、local 禁止）

### REQ-301: Local spawn is structurally forbidden
**EARS**: THE SYSTEM SHALL NOT provision any child instance's runtime, wallet material (beyond the
ephemeral REQ-201/202 generation step, which MAY run on whichever host initiates the spawn attempt,
provided the generated key is held ONLY in a transient, 600-perm file on the initiating host and is
relocated into the child's own isolated remote `$HOME` EXCLUSIVELY via REQ-302's/REQ-303's post-boot
secrets-injection channel — resolves FIND-401's timing gap: "relocated" means relocated the moment the
child's own lease/job is confirmed running and reachable via that injection channel, never synchronously
at generation time, since no authenticated channel to an as-yet-unbooted lease/job can exist — and is
never itself persisted under the initiating host's own home beyond that transient file, which the
trap/cleanup discipline REQ-201 already specifies removes), or persistent state on the same
physical/virtual host as any existing colony citizen's own runtime. Every child SHALL be deployed
exclusively via REQ-302 (Nosana) or REQ-303 (Akash) — reusing SPEC.md §3 P3's own stated rationale
("spawn は local 禁止（disk を埋めて崩壊）") — never onto the machine currently running the spawning
process itself.

**Edge Cases**:
- A spawn attempt is initiated from a laptop/Mac Mini host that ALSO happens to run an existing
  citizen (the current colony's actual topology): the child's own long-running process/state MUST
  still end up exclusively on the cloud lease, never left running on that initiating host after the
  spawn attempt completes (success or failure).
- The generated wallet material's transient temp file on the initiating host is never cleaned up
  (e.g. the process crashes before REQ-302/303's post-boot injection step and its own trap/cleanup
  runs): THE SYSTEM treats this as a REQ-305 failed-attempt condition requiring the SAME shred/rm
  cleanup discipline REQ-201 already specifies, checked at the NEXT wake if it was missed — never left
  indefinitely as a stray secret on the initiating host.

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

**Post-boot secrets-injection channel (new, resolves FIND-401's Nosana-side analog):** Exactly like
REQ-303's Akash path, a Nosana job posted via `nosana job post` boots the child's compute with no
channel, by itself, for delivering the child's own already-generated EVM (REQ-201) private key material
onto the running job (the `-w/--wallet` flag documented above supplies the JOB-POSTING wallet — the
transaction signer for the Nosana market itself — not a channel for injecting a DIFFERENT, separate
secret payload into the job's own running container). THE SYSTEM SHALL therefore deliver that payload,
after the job reaches `RUNNING` status (this leg's own existing success check, above), via
`nosana job ssh <job> [port]` — a real, confirmed-present CLI primitive (`nosana job ssh --help`, checked
live 2026-07-07: "Open an SSH shell into a running job"), the direct Nosana analog of Akash's
`lease-shell` and the authenticated-post-boot-channel security pattern `cloud-init.sh`'s own header
comment already establishes as this codebase's precedent (see the Scope section's honesty note on that
precedent). The EXACT non-interactive invocation shape for a single `cat > /opt/anicca.env`-style
payload delivery (as opposed to an interactive shell) is NOT independently re-verified beyond this CLI's
own `--help` output in this revision — THE SYSTEM SHALL confirm the exact working invocation against the
actually-installed `@nosana/cli` version at Phase 2 implementation time before relying on it, rather than
this spec asserting an unverified exact command line as already-proven.

**Edge Cases**:
- The `nosana job ssh` secrets-delivery step fails after the job itself is already `RUNNING` (billing):
  treated as a deploy failure under REQ-305, mirroring REQ-303's identical Akash-side edge case — the
  already-paid job cost is logged for colony accounting, and the child is never marked `"active"` on a
  booted-but-secretless job alone.
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
- After a Nosana job reaches `RUNNING`, a `nosana job ssh`-based delivery step lands the child's own
  pre-generated wallet material inside the running job's container — an integration/E2E check confirms
  this (never inferred from the job posting's own stdout alone), mirroring REQ-303's Akash-side check
  (resolves FIND-401's Nosana-side analog).

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

**Funding-readiness gate reuse (resolves FIND-402):** BEFORE invoking `akt-treasury.sh`/
`deploy-akash.sh`, THE SYSTEM SHALL determine whether the signing wallet's current AKT balance is
sufficient by calling the existing, already-unit-tested
`~/anicca/skills/self/spawn-child/lib/akt-cost-gate.js::computeSpawnGate({balanceAkt, costAkt,
bufferAkt})` — reusing `spawn-child/config.json`'s own real, already-documented `spawn_cost_akt`
(default `25`) and `buffer_akt` (default `1`) values as `costAkt`/`bufferAkt` — rather than defining a
competing, Akash-specific numeric threshold from scratch. This is a DIFFERENT, narrower concern than
REQ-102's `MIN_SHELTER_USD`/`SPAWN_THRESHOLD_USD` (which answers "does the colony have enough aggregate
USD-equivalent surplus to attempt a spawn at all, across either cloud target"): `computeSpawnGate`
answers the Akash-specific mechanical question "given Akash is the already-SELECTED target (REQ-306)
and REQ-102 already certified sufficient aggregate surplus, does the signing wallet's OWN AKT balance
right now cover this deploy's real cost" — REQ-303 reuses it exactly as
`~/anicca/skills/self/spawn-child/SKILL.md` itself already documents (its own "READY" branch: steps 1-4,
ending in `deploy-akash.sh`), never re-deriving `spawn-child`'s already-tested arithmetic. If
`computeSpawnGate` returns `ready:false`, THE SYSTEM SHALL treat this identically to the "ACT mint
cancels" edge case below (a deploy failure, REQ-305, never a fabricated `dseq`) — funding the AKT
shortfall itself (the Jupiter→Skip-API bridge, REQ-304) is what THIS feature adds; the gate merely
decides whether that bridge needs to run at all.

**Child-specific SDL variant — explicit `HOME` (resolves FIND-403):** Direct reads confirm neither
`deploy-akash.sh`'s inline default SDL nor the reused external template
(`~/anicca/skills/self/spawn-child/sdl/child.yaml`) sets `HOME`/`ANICCA_HOME` anywhere in its `env:`
block — both currently rely on `node:22-bookworm`'s own default root-user home (`/root`), which is
exactly the "base-image default" REQ-203's own PROP-203c prohibits relying on implicitly. THE SYSTEM
SHALL therefore use a child-specific SDL variant (structurally identical to
`spawn-child/sdl/child.yaml` in every other respect — same image, same `command`/`args` boot shape, same
`expose`/`profiles`/`placement` blocks) that adds exactly ONE new `env:` line, `HOME=/root` (the same
value the base image already resolves to implicitly today — made EXPLICIT, not a behavior change),
acknowledged here as a genuinely new, small, necessary SDL modification — NOT a claim that the existing
template is reused byte-for-byte for THIS feature's actual deploys (PROP-303a's "zero source
modification" claim is correspondingly scoped to `deploy-akash.sh`/`akt-treasury.sh`'s own script files
only, never to this new, small SDL variant).

**Post-lease secrets-injection step (resolves FIND-401, new — not a modification to `deploy-akash.sh`):**
`deploy-akash.sh` (unmodified) already boots the lease with ZERO secret material in the SDL/manifest —
this was ALREADY correct, existing behavior, not a gap needing a fix. What the existing artifacts never
provided is a channel for delivering the child's own already-generated EVM (and, if applicable, Solana)
private key material (REQ-201/202) onto that booted lease so the running process can actually sign as
the identity REQ-204 registers and REQ-305 ledgers. THE SYSTEM SHALL therefore add a NEW orchestration
step, run by THIS feature's own code (never by `deploy-akash.sh`'s own source, which stays byte-identical
per PROP-303a) immediately after `deploy-akash.sh`'s existing manifest-send succeeds (i.e., after the
lease is confirmed `active` and the manifest is confirmed sent — reusing `deploy-akash.sh`'s own existing
`ACTIVE`/`SENT` polling result as the trigger, never a new polling mechanism): render the child's wallet
material (the REQ-201/202 private key(s), `ANICCA_CHILD_ID`, and any other `.env` value the child's own
`install.sh`/`runtime/loop/index.mjs` require at first wake) into a `.env`-shaped payload, then deliver
it via `provider-services lease-shell <service-name> "cat > /opt/anicca.env" --dseq <dseq> --gseq <gseq>
--oseq <oseq> --provider <provider> --from "$AKASH_KEY_NAME" --stdin` — a real, confirmed-present
`provider-services` CLI primitive (`provider-services lease-shell --help`, checked live 2026-07-07: "do
lease shell... connect stdin"), the direct Akash analog of an authenticated SSH exec-into-running-
container channel. `<service-name>` is `automaton` (the SDL's own service name, `sdl/child.yaml` line 7);
`<dseq>`/`<provider>` are already known from `deploy-akash.sh`'s own successful run (its own
stdout/internal variables); `<gseq>`/`<oseq>` default to `1` per `provider-services`' own documented
defaults (unchanged from `deploy-akash.sh`'s own lease-create call, which never overrides them). Once
delivered, the file lands at `/opt/anicca.env` — the path the child's own booted process is configured to
read its runtime configuration from (a Phase 2 implementation detail this feature's diff, not
`install.sh` itself, is responsible for wiring). THE SYSTEM SHALL NEVER place this secret payload in the
SDL's own `env:` block, in any `user_data`-equivalent boot config, or in any location
`provider-services query`/`sdl-to-manifest` exposes publicly — this mirrors the EXACT security discipline
`~/anicca/skills/self/spawn/scripts/cloud-init.sh`'s own header comment already documents for the
(separate, DO-specific, out-of-scope) `run.sh` path ("SECURITY: NO secret VALUES in user_data...
Secrets are SCP'd... after boot") — cited here ONLY as the established SECURITY PATTERN precedent this
feature's Akash-specific mechanism follows, NOT as a claim that DO's own SCP step is itself already
implemented (a direct read of `run.sh` confirms no `scp` invocation exists anywhere in its current DO
path either — an honest, out-of-scope gap in a DIFFERENT, non-REQ-302/303 cloud target this feature does
not touch; see RESOLUTION-NOTES.md).

**Edge Cases**:
- The signing wallet's `uact` (ACT) balance is below `AKASH_DEPOSIT` at spawn time: `akt-treasury.sh`
  MUST be run and its EXECUTED (not CANCELED — the script's own documented balance-delta check)
  outcome confirmed BEFORE `deploy-akash.sh` is invoked; if the mint cancels (output below
  `bme.params.min_mint`), THE SYSTEM SHALL treat this as a deploy failure (REQ-305) and never fabricate
  a `dseq`.
- The `computeSpawnGate` readiness check reports `ready:false` (insufficient AKT even after accounting
  for `buffer_akt`): THE SYSTEM SHALL treat this identically to the "mint cancels" edge case above — a
  deploy failure under REQ-305, `akt-treasury.sh`/`deploy-akash.sh` are never invoked, and no `dseq` is
  fabricated.
- No open bid appears within `deploy-akash.sh`'s existing poll window (30 attempts, existing default
  sleep): the script's own existing fail-closed behavior (non-zero exit, no dseq printed) is reused
  as-is; REQ-303 adds no new retry logic beyond what already exists.
- `send-manifest` fails after its existing retry budget (5 attempts): treated as a deploy failure even
  though the lease itself is technically active — a leased-but-unmanifested deployment is not a running
  child and MUST NOT be marked `"active"`.
- The post-lease secrets-injection step (`lease-shell`) fails (network error, expired lease-shell
  authorization, or a non-zero exit) AFTER `deploy-akash.sh` already reports an active lease + sent
  manifest: THE SYSTEM SHALL treat this as a deploy failure under REQ-305 (the lease itself is real and
  billing, but the child cannot yet sign as its own registered identity) — the already-paid,
  non-refundable lease deposit is logged for colony accounting (mirroring REQ-305's own "already-spent,
  non-refundable resource" handling), and the child is NEVER marked `"active"` on the strength of a
  booted-but-secretless lease alone.
- The child-specific SDL variant's new `HOME=/root` line is accidentally omitted at implementation time
  (a regression): THE SYSTEM treats this as a spec violation to be caught at Phase 3 review — PROP-203c's
  "explicit env line" acceptance criterion is re-checked against the ACTUAL rendered SDL used for a real
  deploy, not merely asserted from this spec's own text.

**Acceptance Criteria**:
- `deploy-akash.sh CHILD_ID` and `akt-treasury.sh` are invoked with no source modification; their
  existing exit-code/stdout contract (dseq on stdout, non-zero exit + stderr message on any failure) is
  the sole success/failure signal this feature reads.
- The real `AKASH_DEPOSIT` amount and (once queryable) the real settled lease cost are appended to a
  shelter-cost ledger file that REQ-102 reads on its NEXT evaluation — the very first spawn therefore
  uses the provisional `$5.00`/`$10.00` defaults, and every subsequent evaluation uses real measured
  data once at least one successful deploy exists.
- `computeSpawnGate({balanceAkt, costAkt: config.spawn_cost_akt, bufferAkt: config.buffer_akt})` (from
  `~/anicca/skills/self/spawn-child/lib/akt-cost-gate.js`, reused unmodified) is called before every
  Akash deploy attempt, with `costAkt`/`bufferAkt` read from `spawn-child/config.json`'s own real values
  — never a competing, independently-invented Akash-specific threshold.
- The rendered SDL actually submitted on-chain for a real deploy contains an explicit `HOME=/root` line
  in its `env:` block — a structural check of the ACTUAL post-`envsubst` artifact (not the template
  file alone), resolving FIND-403 and satisfying PROP-203c's "never a base-image default" requirement.
- After `deploy-akash.sh`'s manifest-send succeeds, a `provider-services lease-shell ... --stdin` call
  delivers the child's own pre-generated wallet material to `/opt/anicca.env` on the leased container —
  an integration/E2E check confirms the file exists post-delivery with the expected content (never
  checked via the SDL/manifest artifact, which never carries it) — and that `deploy-akash.sh`/
  `akt-treasury.sh`'s own source remains byte-identical throughout (PROP-303a's scope, corrected to
  exclude the new secrets-injection step and the new child-specific SDL variant, both of which are
  tested as NEW code, never claimed as pre-proven reuse).

---

### REQ-304: Shelter cost is funded only from treasury-gate-approved surplus
**EARS**: THE SYSTEM SHALL NOT fund any REQ-302/303 deploy (nor REQ-204's gas seed) from any single
citizen's own `perCitizenReserveUsd` (the amount REQ-101 excludes from the aggregate precisely because
it is that citizen's own survival reserve) or from any human-funded wallet (claude-p's or any other);
funding SHALL draw only from the aggregate surplus REQ-102 already certified as available for THAT
spawn attempt, and by an amount not exceeding what REQ-102 approved.

**AKT funding route correction (resolves FIND-402):** The "single-signer, single-transaction transfer"
characterization in the first Edge Case below is accurate for REQ-204's gas-seed transfer and for any
shelter-cost transfer where the funding citizen's OWN native chain already matches the deploy target's
native currency (e.g., Franklin's Solana SOL/USDC directly funding a Nosana deploy — REQ-302 — both
Solana-native, genuinely one signer, one transaction). It is NOT accurate for funding an AKASH deploy's
`uact`-denominated escrow specifically: NEITHER of the colony's two currently-verified self-funded
citizens (`anicca-a3cdd4`'s Base USDC, `Franklin`'s Solana SOL/USDC, per REQ-105's seed data) natively
holds AKT. THE SYSTEM SHALL fund an Akash deploy's AKT requirement via the REAL, already-documented,
already-vetted route `~/anicca/skills/self/spawn-child/config.json`'s own `funding_route` field
specifies (confirmed by direct read, 2026-07-07): Jupiter SOL→USDC (Solana, same-chain swap), THEN Skip
API 4-hop `smart_relay` USDC(solana)→AKT(akashnet-2) routed through `noble-1`/`osmosis-1`, THEN
`akt-treasury.sh`'s own existing `mint-act` step (unmodified) to convert the received AKT into the
`uact` `deploy-akash.sh` actually escrows. THE SYSTEM SHALL reuse this documented route rather than
re-deriving a same-chain assumption that does not hold for either citizen's actual wallet composition —
this is a genuinely multi-hop, multi-transaction funding path for the Akash target specifically, never a
single-signer single-transaction transfer.

**Edge Cases**:
- The approved aggregate surplus is spread across multiple citizens' wallets and no single citizen
  individually holds the full deploy cost: THE SYSTEM SHALL fund from whichever citizen(s)
  INDIVIDUALLY hold sufficient surplus-above-reserve to cover the cost alone (a single-signer,
  single-transaction transfer for a SAME-CHAIN funding path, matching the existing gojo/rescue transfer
  pattern already used in `economy/ubi/run.sh` — see the AKT funding route correction above for the
  Akash-specific, genuinely multi-hop exception), rather than attempting a new multi-wallet pooled
  transaction mechanism — this feature deliberately does not build multi-signer pooling.
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
`child-spec.js::buildChildSpec`'s own `status:"provisioning"` initial value, assembled via
`buildChildSpec` called with all seven required fields populated per REQ-206's rules — the identity
anchor being the child's own `agentEvmAddress`+`agentId` once REQ-204 completes (this feature's children
never carry a `childInbox`), and `parentWallet`/`generation`/`seedUsdc`/`constitutionHash` set exactly
as REQ-206 now specifies (resolves FIND-204)) together with the specific failing step and error
message, any already-spent, non-refundable resource (e.g. an Akash deployment deposit not yet
converted into an active lease) SHALL be logged for colony accounting, and REQ-102's
`SPAWN_COOLDOWN_DAYS` timer SHALL NOT be considered "consumed" by a failed attempt — mirroring this
project's existing HARD RULE 0.24 ("NO FAKE RUN... any failed step exits non-zero and leaves an honest
provisioning/failed ledger row, never a fabricated success").

WHEN, and only when, a spawn attempt completes and the child is marked `"active"` (REQ-204+REQ-205 both
complete), THE SYSTEM SHALL, in that SAME ledger.js row, ALSO set a new field `active_since` to the
current timestamp (never omitted, never set earlier at the `"provisioning"` stage) — this is the SOLE
field REQ-402's window check and REQ-101's `filterProductiveCitizens` join read (resolves FIND-201's
location contradiction: this lifecycle fact lives exclusively in `ledger.js`, never in
`citizens.json`). THE SYSTEM SHALL ALSO append a new record for that child to REQ-105's colony citizen
registry (`~/anicca/skills/self/spawn/registry/citizens.json` — NOT `economy/ubi/colony-wallets.json`,
which this feature never touches, per REQ-105's FIND-101 revision) — `{id: child_id, wallet: {evm:
true, solana: true-if-generated} (BOOLEAN presence flags, matching `is-self-funded.mjs::hasOwnWallet()`'s
own documented contract exactly — resolves FIND-104), walletAddress: {evm: childWallet, solana:
childSolanaAddress-if-generated} (the actual address STRING(s) — a SEPARATE field from `wallet`, never
passed to `isSelfFunded()`), fuel: {provider: "free-model"} (per REQ-401's exclusive free-model fuel
requirement), humanDependencies: [], homeDir: <the child's own resolved absolute `HOME`/`ANICCA_HOME`
directory, REQ-203 — resolves FIND-202>}` — NO `telemetryPath` field (removed from this schema,
resolves FIND-302; REQ-101's balance lookup for this child, like every other citizen, goes through the
registry-driven public-RPC `readCitizenBalances` step keyed on `walletAddress` above) — so REQ-101's
NEXT evaluation includes the new citizen automatically, without any separate manual or out-of-band
registry-edit step (resolves FIND-002's "how does the registry grow" gap). This registry record
deliberately carries NEITHER `status` NOR `active_since` — those remain exclusively in the ledger.js
row set above.

**Cross-file field-name disambiguation (resolves FIND-304):** the `ledger.js` row this feature writes
for each child (first paragraph above, assembled via `buildChildSpec`) already carries a field named
`wallet` — this is `buildChildSpec`'s own, pre-existing, UNMODIFIED returned-row field (`child-spec.js:
37`: `wallet: childWallet`, a bare address STRING; see REQ-206's own disambiguation note), NOT the
boolean-shaped `wallet` object this same paragraph just appended to `citizens.json`. The two `wallet`
fields — one in `ledger.js`'s JSONL rows (a string, untouched code) and one in `citizens.json`'s
registry records (a boolean pair, REQ-105) — share a name only by coincidence across two unrelated
files/schemas this feature touches; implementers and reviewers reading these two files side by side
MUST read each `wallet` field per its OWN file's schema, never cross-reference the two.

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
- Marking a child `"active"` ALSO sets that SAME ledger.js row's `active_since` field to the current
  timestamp (never omitted, never set at the earlier `"provisioning"` stage) — the field REQ-402's
  window check and REQ-101's `filterProductiveCitizens` join both read (resolves FIND-201).
- The appended `citizens.json` record's `homeDir` field is an ALREADY-RESOLVED absolute path — a
  structural check confirms it never contains a `$HOME`/`ANICCA_HOME` template string (resolves
  FIND-202), and the appended record carries NO `telemetryPath` field at all (removed, resolves
  FIND-302).
- The real `buildChildSpec` call underlying this append supplies concrete values for all seven required
  fields per REQ-206's derivation rules (`parentWallet`, `generation`, `seedUsdc`, `constitutionHash`
  included, not just the identity-anchor pair) — resolves FIND-204.

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
  USD-equivalent estimate. **Corrected (resolves FIND-305): this normalization is NOT already-available,
  reused infrastructure.** `akt-treasury.sh` (read in full) contains no live USD price query anywhere —
  it only compares NATIVE-denominated balances (`uact`/`uakt`, via `akash query bank balances`) against
  fixed native-unit thresholds, and the `P_mint≈0.66` figure its own comment documents is a ONE-TIME
  HISTORICAL OBSERVATION recorded at write time, not a callable, live rate function. A repo-wide grep
  (`nosana|market.*price|SOL.*price`, case-insensitive, across `~/anicca/skills`) confirms no NOS/USD or
  AKT/USD price-conversion utility exists anywhere in this codebase either. THE SYSTEM therefore requires
  a MINIMAL, genuinely NEW price-fetch step — one public spot-price API call per native token — rather
  than reusing a nonexistent oracle. This new step SHALL follow the exact, already-established,
  already-used PATTERN this codebase already applies three times for ETH-USD/SOL-USD
  (`runtime/dashboard/telemetry-poster.mjs::ethPrice()`, `runtime/dashboard/
  telemetry-post-franklin.mjs::solPrice()`, `skills/earn/execute-invest.mjs`'s own `ethPrice()`: a single
  `fetch()` to a public spot-price API, parsed to a number, fail-closed to `0` on any error) — a single
  new call for AKT-USD (no existing utility covers Akash's native token) and, if Nosana's configured
  market denominates in NOS rather than SOL, a single new analogous call for NOS-USD (the existing
  `solPrice()` mechanism is reused AS-IS, unmodified, if the market is SOL-denominated) — never a
  bespoke, multi-source, or judgment-based oracle design.
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
`"bootstrap_failed"` in the ledger — `~/anicca/skills/self/spawn/lib/ledger.js`'s own JSONL rows, the
SOLE canonical owner of this lifecycle fact (REQ-105's `citizens.json` is deliberately minimal per its
own exact-field-list design and carries neither `status` nor `active_since` — this feature never stores
a second, competing copy of either fact there, resolving FIND-201's location contradiction) — never
silently delete or destroy the child, its wallet, or its cloud lease. This relabeling is implemented as
`ledger.js::appendChild`-ing a NEW row carrying the SAME `child_id` and `status:"bootstrap_failed"` —
`ledger.js` itself gains NO update/upsert primitive and remains exactly `{readChildren, appendChild}`
(the identical discipline REQ-101/REQ-305 already establish for every other lifecycle transition); this
new row becomes "the" effective row for that citizen precisely because REQ-101's own
`filterProductiveCitizens` join already reduces multiple rows sharing one `child_id` to the
LAST-appended row before applying its exclusion rule (last-write-wins, REQ-101's own naming) — REQ-402
does not introduce a second, competing reduction rule; it relies on that SAME one, by cross-reference,
resolving FIND-405's recurrence of FIND-301's class of ambiguity. `active_since` is itself a ledger.js
row field, set once by REQ-305 at the exact moment a child is first marked `"active"` (REQ-204+REQ-205
complete); REQ-402's window check is `now − active_since >= BOOTSTRAP_WINDOW_DAYS * 86400000`, read
directly from that same (last-appended, "active") row.

THE SYSTEM SHALL EXCLUDE a `"bootstrap_failed"` child from REQ-101's colony-surplus aggregation until it
produces its own first realized settlement (it does not count as a "productive" self-funded citizen
while `"bootstrap_failed"`, though its wallet may still technically satisfy `isSelfFunded()`'s
structural test — REQ-402 adds a SEPARATE productivity flag, not a change to that existing gate). This
exclusion is realized EXCLUSIVELY through REQ-101's own `filterProductiveCitizens` join step (see
REQ-101), which reads this exact ledger.js row per citizen — REQ-402 does not maintain, and this
requirement does not specify, any second, parallel exclusion mechanism.

THE SYSTEM SHALL record this outcome (a running `children_bootstrap_failed` count) for observability
ONLY — e.g. in the ledger row itself or in telemetry — and this count SHALL NOT be passed as a
parameter to, or otherwise change the behavior of, REQ-102's `decideColonySpawn`: REQ-102's gate
signature is pinned (see REQ-102's own Acceptance Criteria) and remains governed solely by its own
seven named parameters, unaffected by how many prior attempts failed (resolves FIND-203 — this is a
descope of the prior false promise, not a signature extension). This feature does not implement a
bootstrap-failure-aware spawn throttle this increment; a bootstrap failure never automatically triggers
or blocks a replacement spawn (that remains gated purely by REQ-102's own arithmetic).

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
- A scheduled/wake-triggered check reads `active_since` and `status` directly from
  `~/anicca/skills/self/spawn/lib/ledger.js`'s own rows (never from REQ-105's registry, which carries
  neither field) for every `"active"` child lacking a recorded REQ-401 success, compares
  `now - active_since` against `BOOTSTRAP_WINDOW_DAYS`, and, for exactly those past the window,
  `appendChild`s a NEW row for the SAME `child_id` with `status:"bootstrap_failed"` — never a mutation
  of the prior row, and never applied to any child not past the window (resolves FIND-405: this new row
  becomes "the" effective row for REQ-101's `filterProductiveCitizens` join precisely because that join's
  own last-write-wins reduction, REQ-101, picks up the LAST-appended row for each `child_id`). Every
  child this check considers is one already present in BOTH REQ-105's colony citizen registry (as a
  citizen record, appended by REQ-305 on activation) AND ledger.js (as one or more rows, appended at
  spawn time and again at activation) — REQ-402 does not maintain a third, separate list of children,
  nor does it add any update/upsert primitive to `ledger.js`, which stays exactly `{readChildren,
  appendChild}`.
- `filterProductiveCitizens({citizens, ledgerRows, nowMs, bootstrapWindowDays})` (REQ-101's new join
  function), given a citizen whose matching ledger.js row is flagged `"bootstrap_failed"`, excludes it
  from the productive-surplus sum even if its own registry-recorded balance is nonzero (e.g. residual
  gas-seed dust) — this is the ONLY mechanism REQ-402's exclusion is realized through; there is no
  second, parallel exclusion path anywhere in this spec.
- The `children_bootstrap_failed` count is recorded for observability only; a structural/Tier-0 check
  confirms REQ-102's `decideColonySpawn` signature and behavior are byte-identical whether or not any
  bootstrap failures have occurred (resolves FIND-203: no dangling REQ-402→REQ-102 data flow).

---

### REQ-403: Wallet mutual non-interference audit (live-comparison half scoped to co-located instances this increment — resolves FIND-303)
**EARS**: WHEN N ≥ 2 instances (any mix of pre-existing citizens and newly-spawned children) run
concurrently, THE SYSTEM SHALL provide a deterministic audit combining two independently-scoped halves:
(a) a static, grep-based source audit across every skill script and cron/job config, checking all three
path-reference forms (`$HOME/...`, `~/...`, and the fully-resolved absolute form), reusing the exact
method this project's own wallet-rotation work already established (memory
`feedback_move_refcheck_must_cover_skill_scripts_and_home_forms`: "grep ~/.openclaw/skills +
~/anicca/skills + cron in ALL 3 path forms") — this static half covers EVERY instance this increment
produces, INCLUDING a cloud-hosted child, because REQ-303's SDL boots that child by `git clone`-ing the
SAME OSS repo this static grep already runs against (no separate remote-source-audit mechanism is
needed for this half); with (b) a live runtime comparison — reusing `resolve-identity.mjs`'s existing
exported resolvers, invoked once per CO-LOCATED running instance with that instance's OWN `HOME`/
`ANICCA_HOME` (read from REQ-105's registry's `homeDir` field, an already-resolved absolute path — see
Acceptance Criteria) — that PROVES no two CO-LOCATED instances' resolved EVM or Solana signing keys are
ever equal, and no CO-LOCATED instance's resolved key-file PATH ever points inside another CO-LOCATED
instance's own home directory, before any newly-spawned CO-LOCATED child is permitted to participate in
REQ-401's bootstrap.

**Scoping correction (resolves FIND-303):** `resolve-identity.mjs`'s exported resolvers
(`resolveEvmPrivateKey`/`resolveSolanaSecret`) are a PURE LOCAL-FILESYSTEM primitive
(`fs.readFileSync` against `path.join(effectiveHome, '.automaton', 'wallet.json')`, confirmed by direct
read of that module's real source) — the coordinator process invoking them can only ever resolve a key
that lives on the coordinator's OWN local disk. Per REQ-301, a spawned child's wallet material lives
EXCLUSIVELY on its own remote Nosana/Akash lease, a physically separate filesystem the coordinator
cannot `fs.readFileSync` into, and this feature never transmits a child's own private key material back
to the coordinator over the network for comparison (that would itself violate REQ-201's private-key-
handling discipline — "must never appear in any log file, stdout capture that reaches persistent logs,
or process list," reasonably extended here to "or any network transmission"). THE SYSTEM SHALL therefore
SCOPE the live-comparison half of this audit, for THIS INCREMENT ONLY, to co-located instances — today,
automaton + Franklin, both on the Mac Mini per REQ-106 — mirroring REQ-106's own already-established
"this increment only, future work for multi-host" precedent. A cloud-hosted spawned child is EXEMPT from
the live-comparison check until a future increment adds a genuine remote-audit mechanism (e.g. a
self-check script deployed to the child that reports only a boolean PASS/FAIL result — never key
material — back to the coordinator). The STATIC grep-sweep half (a) is UNAFFECTED by this scoping and
continues to cover a cloud-hosted child's deployed source, per the EARS clause above.

**Edge Cases**:
- The static grep audit finds a hardcoded/templated path in a cloud-init script or SDL that could
  resolve to a shared location across children (e.g. a copy-paste bug reusing the SAME literal
  `GIG_STATE_PATH` or wallet-file path across two SDL templates): THE SYSTEM SHALL treat this as a
  BLOCKING finding — the affected child(ren) SHALL NOT be marked `"active"` until fixed, even if no
  actual runtime collision has yet been observed (structural risk is enough to block, not requiring a
  live incident first).
- The live runtime comparison finds an ACTUAL key collision among CO-LOCATED instances (two co-located
  instances resolve the identical signing key): THE SYSTEM SHALL halt BOTH implicated instances from any
  further signing immediately (fail-closed security-incident response), not merely log a warning and
  continue.
- A cloud-hosted spawned child exists and is about to participate in REQ-401's bootstrap: THE SYSTEM
  SHALL NOT block it on the live-comparison half (that check does not run for it this increment,
  resolves FIND-303) — it IS still covered by the static grep-sweep half (a), which remains a blocking
  gate for it exactly as for any co-located instance.
- A new cloud-host template is added later (e.g. a third provider beyond Nosana/Akash) with a
  different environment-injection mechanism than either already-audited path: THE SYSTEM SHALL require
  the audit to be explicitly extended to that new mechanism before any child deployed via it is trusted
  — silent "probably fine by analogy" reasoning is not permitted for a money-safety check.

**Acceptance Criteria**:
- A repeatable audit script exists that, given the current set of CO-LOCATED running instances' own
  `HOME` values — read directly from REQ-105's colony citizen registry's `homeDir` field (an
  ALREADY-RESOLVED absolute path per REQ-105's schema — resolves FIND-202; the same registry REQ-101
  aggregates over, no second, parallel instance-enumeration mechanism is introduced for this audit),
  (1) runs the static grep sweep across the WHOLE fleet (co-located AND cloud-hosted, since the
  latter's deployed source is the same repo, per the EARS clause above) and reports zero cross-instance
  path references, and (2) invokes `resolveEvmPrivateKey`/`resolveSolanaSecret` once per CO-LOCATED
  instance's own `homeDir` and asserts pairwise inequality across all resolved keys — this increment's
  live-comparison scope is co-located instances only (resolves FIND-303); a cloud-hosted child is
  exempted from step (2) and is covered only by step (1) this increment.
- Given a deliberately-injected test fixture where two fake CO-LOCATED instances share a `HOME`
  (negative test), the audit correctly reports a collision — proving the check is not vacuously passing.
