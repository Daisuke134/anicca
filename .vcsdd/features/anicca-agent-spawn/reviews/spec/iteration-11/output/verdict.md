# vcsdd-adversary verdict — anicca-agent-spawn — spec review, iteration 11

**Overall: FAIL** (2 dimensions in scope per manifest: spec_fidelity, verification_readiness — both FAIL)

## FIND-901 (iteration 10) re-verification: GENUINELY RESOLVED

Fresh reads (this session, no prior context) of:
- `~/anicca/skills/self/spawn/lib/state-path.js` — `resolveStateDir({env, home})` really defaults to
  `${home}/.hermes/state` and really throws on any `/tmp`- or `/private/tmp`-rooted path.
- `~/anicca/skills/self/spawn/run.sh:39-45` — really the current, live caller of `resolveStateDir`
  for `children.jsonl`'s durable location (`STATE_DIR="$("$NODE" -e '...resolveStateDir({env: process.env, home: process.env.HOME})...')"`).

confirm `CITIZENS_REGISTRY_PATH = path.join(resolveStateDir({env, home}), 'citizens.json')` genuinely
reuses this exact, already-proven mechanism, and would resolve to `~/.hermes/state/citizens.json` today
— outside the git working tree, exactly as claimed.

A full grep of both spec files for every `citizens.json` / `citizens.seed.json` / `CITIZENS_REGISTRY_PATH`
occurrence confirms every prior citation that used to point at the single in-tree path (REQ-103's lock
`statePath`, REQ-105's own registry read, REQ-305's append target, REQ-403's audit enumeration) now
correctly cites the DURABLE `CITIZENS_REGISTRY_PATH` — none were left pointing at the git-tracked seed
template `citizens.seed.json` by mistake. `~/anicca/.gitignore`'s current patterns still do not match
`skills/self/spawn/registry/`, so the seed template will genuinely be git-tracked (as the design
requires) while the durable file lives entirely outside git.

I also independently re-verified the FIND-501/FIND-603 wallet-resolution claims that depend on the same
module family: `/Users/anicca/.anicca/.automaton/wallet.json` does **not** exist (confirmed by direct
Read — file-not-found), so `resolveEvmPrivateKey`'s primary `effectiveHome`-based branch genuinely falls
through to its legacy-fallback branch, which reads `/Users/anicca/.automaton/wallet.json` — confirmed
present, with a real `privateKey` field. Symmetrically, `/Users/anicca/.blockrun/.automaton/solana.json`
does not exist, and `/Users/anicca/.blockrun/.solana-session` does exist with real content. Both match
the spec's own claimed resolution mechanism exactly.

**However, the two-artifact split itself introduces a NEW, previously-unaddressed hazard — FIND-1001
below — that a genuinely thorough re-check of FIND-901's fix surfaced.**

## New findings, iteration 11

### FIND-1001 (critical, category: spec_gap) — concurrent "one-time bootstrap" race, unprotected by the colony-spawn lock

REQ-105's bootstrap step ("on first access, IF `CITIZENS_REGISTRY_PATH`'s file does NOT yet exist, THE
SYSTEM SHALL initialize it by copying `citizens.seed.json`'s content VERBATIM") is a classic
check-then-act operation. It is triggered by REQ-101's registry READ, which happens **before** REQ-102's
gate and **before** REQ-103's lock is ever attempted — REQ-103's own Acceptance Criteria explicitly scope
the lock's critical section to start at REQ-201 (identity generation), not at the registry read. This
spec elsewhere explicitly anticipates concurrent evaluators on the single coordinator host (REQ-103's own
edge case: "Two evaluation loops on the coordinator host race..."; REQ-106's own edge case: "Multiple
LOOPS on the SAME coordinator host... race to evaluate REQ-102/103 in the same window") — yet never
protects the ONE write operation (the bootstrap copy) that sits entirely outside the lock it otherwise
builds specifically for exactly this class of race. No atomic primitive (e.g. `fs.open(file, "wx")`, the
same primitive this codebase's own `lock.mjs` uses specifically because an earlier check-then-act gap
caused a real double-pay drain) is specified for the bootstrap write, and no proof obligation
(PROP-105j/PROP-105k) exercises a concurrent-bootstrap race. Worst case: a REQ-305 append that lands
between one slow racer's exists-check and that racer's own bootstrap write can be silently destroyed —
the exact "colony citizen registry silently lost" failure class FIND-901 exists to prevent, reached
through a different vector.

### FIND-1002 (major, category: purity_boundary) — `registry-path.mjs` mislabeled "Pure Core"

verification-architecture.md's Purity Boundary Map labels the new `registry-path.mjs` module
(`CITIZENS_REGISTRY_PATH`/`COORDINATOR_HOME`) "Pure Core" — but `CITIZENS_REGISTRY_PATH` is built by
calling `resolveStateDir`, which this SAME table classifies "Effectful Shell" two rows away, and
`COORDINATOR_HOME` is built from `os.homedir()`, a real OS/environment read. This is an internal
inconsistency in the spec's own pure/effectful convention, and risks Phase 3 under-testing this module's
real environment coupling (it needs Tier-2-style, environment-controlled tests, not Tier-0/1 zero-I/O
tests, to genuinely prove either constant's correctness).

## Extensive additional verification performed (no further findings)

Beyond the citizens.json area, I read the full behavioral-spec.md (2163 lines) and
verification-architecture.md (665 lines) end-to-end this session and cross-checked the following real
source artifacts against the spec's citations, all of which matched exactly: `child-spec.js` +
`__tests__/child-spec.test.js` (buildChildSpec's 7 required fields, `wallet:childWallet` at line 37,
distinct-wallet throw), `ledger.js` (exactly `{readChildren, appendChild}`, no update/upsert primitive),
`lock.mjs` (`withGigLock(statePath, lockKey, fn, opts)` signature, `lockPaths` deriving from
`path.dirname(statePath)`, `isLockStale`, `isSafeLockKey` allowing `"colony-spawn"`), `is-self-funded.mjs`
(`hasOwnWallet` boolean contract, `OWN_FUNDED_FUEL_PROVIDERS`), `ensure-agent-id.mjs` +  `identity.mjs`
(both ERC-8004 registry addresses, cache-then-verify-then-register-once flow), `akt-cost-gate.js` +
`spawn-child/config.json` (`computeSpawnGate`, `spawn_cost_akt:25`/`buffer_akt:1`, `funding_route`
literal string), `escrow.mjs` (`USDC_BASE_MAINNET`/`CHAIN_ID_BASE_MAINNET=8453`), `spawn-decision.js`
(`rateLimitDays:14` default), `telemetry-collect.sh` + `telemetry-post-franklin.mjs` (wallet addresses,
`bs58`/Solana-secret handling), `install.sh:26`/`:78` (`ANICCA_HOME` default, genesis.md citation),
`gen-wallet.sh` (the sha256-fallback comment REQ-201 cites), `spawn-child/sdl/child.yaml` (service name
`automaton` at line 7, confirmed no `HOME`/`ANICCA_HOME` env line), `akt-treasury.sh` (the `P_mint≈0.66`
and `ACT_BUFFER_UACT` "2× min_mint" comments), `package.json`/`runtime/package.json`
(`@solana/web3.js@^1.98.4`, `bs58@^5.0.0` both real dependencies). REQ-201 through REQ-306 and REQ-401
through REQ-403's prose was re-read in full; no other stale citation, internal contradiction, or
un-closed hazard was found in these sections this iteration.

I did not have code-execution access this session and could not independently re-run the
`privateKeyToAccount`/`Keypair.fromSecretKey` cryptographic re-derivations PROP-105g claims were
performed live; I verified the file-existence/content preconditions those re-derivations depend on
(the wallet/secret files genuinely exist and are read via the claimed resolution paths) but the address
match itself is trusted from the prior iterations' own live-performed record, not independently repeated
here.
