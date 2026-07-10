# Verification Report

## Feature: spawn-funding-swap | Sprint: 1 | Date: 2026-07-10

**Phase**: 5 (Formal Hardening) · **Verifier**: fresh-context Phase 5 session (not the same context as the
Phase 2/3 Builder/adversary passes) · **Prior gate**: Phase 3 impl review iteration-2 PASS, 0 blocking
findings, live-executed 104/104 target + 310/310 regression (`reviews/impl/iteration-2/output/verdict.json`).

**Toolchain note**: this feature (plain ESM JavaScript under `~/anicca`, tested via Node's built-in
`node:test` runner) has no Kani/Dafny/Coq/TLA+ formal prover available or applicable. All 23 proof
obligations (PROP-001..023, all Tier 0-2, all `required: true`) are discharged via `node:test` unit/fixture
tests and `fast-check` (already a devDependency, `~/anicca/package.json` `^4.8.0`) property tests, plus
Tier-0 static-source-scan tests — the same discipline already established by this codebase's
`skills/self/anicca-agent-spawn`/`skills/earn/sol-trade` money-safety precedents. Tier 3 (strong formal
proof) is not claimed anywhere in `specs/verification-architecture.md`'s Verification Strategy section for
this feature — it explicitly states Tier 2 `fast-check` over the small, pure, bounded state machine is
sufficient and a Kani/TLA+-grade proof would be disproportionate. No degradation occurred: nothing was
downgraded from a higher tier this feature's own spec called for.

**state.json note**: `proofObligations` was `[]` in state.json at the start of this Phase 5 session (Phase
1b defined the 23 PROP-001..023 obligations only in `specs/verification-architecture.md`'s table — it was
never mirrored into `state.json.proofObligations`, so the Phase 5→6 gate's `requiredProofs` check would
have trivially passed against an empty array). This session populated `state.json.proofObligations` with
all 23 obligations (id/tier/required/status/artifact) from the Phase 1b table via
`scripts/lib/vcsdd-state.js`'s `readState`/`writeState` (atomic, schema-validated) — not a hand-edit — and
set each to `status: "proved"` only after independently re-running the cited tests live in this session
(see command output below). This is a genuine Phase-1b→state.json wiring gap this session found and closed,
not a new proof-coverage gap.

## Live test evidence (this session, fresh execution)

```
$ cd ~/anicca && node --test skills/self/spawn-funding-swap/lib/__tests__/*.test.mjs
...
ℹ tests 104
ℹ suites 0
ℹ pass 104
ℹ fail 0
ℹ cancelled 0
ℹ skipped 0
ℹ todo 0
ℹ duration_ms 1185.222542
(exit code 0)
```

```
$ cd ~/anicca && node --test skills/self/spawn/lib/__tests__/*.test.mjs skills/self/spawn/lib/__tests__/*.test.js skills/earn/sol-trade/lib/__tests__/*.test.mjs
...
ℹ tests 310
ℹ suites 0
ℹ pass 310
ℹ fail 0
ℹ cancelled 0
ℹ skipped 0
ℹ todo 0
ℹ duration_ms 2863.174
(exit code 0)
```

Full logs captured at `verification/fuzz-results/target-suite-104.log` and
`verification/fuzz-results/regression-suite-310.log`. Zero regression from this feature's changes against
the sibling `spawn`/`sol-trade` money-safety suites.

## Proof Obligations

| ID | Tier | Required | Status | Tool | Artifact |
|----|------|----------|--------|------|---------|
| PROP-001 | 2 | true | proved | fast-check + node:test | `swap-need.test.mjs` |
| PROP-002 | 1 | true | proved | node:test spy | `driver-preconditions.test.mjs:48,60` |
| PROP-003 | 1 | true | proved | node:test fixtures | `route-validation.test.mjs` |
| PROP-004 | 1 | true | proved | node:test spy | `driver-preconditions.test.mjs:69` |
| PROP-005 | 2 | true | proved | fast-check + node:test spy | `funding-check.test.mjs:21,29,36,42,53,64` + `driver-choke-point.test.mjs:198,231` |
| PROP-006 | 0 | true | proved | node:test fixed fixture | `funding-check.test.mjs:13` |
| PROP-007 | 2 | true | proved | fast-check | `ledger-plan.test.mjs` |
| PROP-008 | 1 | true | proved | node:test + fake timers | `driver-multileg.test.mjs` |
| PROP-009 | 2 | true | proved | fast-check + node:test | `driver-crash-recovery.test.mjs:145,164,186,206,225` |
| PROP-010 | 2 | true | proved | fast-check / lock contention | `driver-lock-and-concurrency.test.mjs:66,101` |
| PROP-011 | 2 | true | proved | fast-check | `swap-need.test.mjs` |
| PROP-012 | 1 | true | proved | node:test hostile-env fixture | `swap-need.test.mjs` |
| PROP-013 | 1 | true | proved | node:test spy + fixed boundary fixtures | `settlement.test.mjs:15,22,29,34,40,46` + `driver-choke-point.test.mjs:253,275` |
| PROP-014 | 1 | true | proved | node:test subprocess | `cli.test.mjs` |
| PROP-015 | 1 | true | proved | node:test spy | `driver-preconditions.test.mjs:81` |
| PROP-016 | 1 | true | proved | node:test env fixture | `driver-preconditions.test.mjs:89,96` |
| PROP-017 | 0 | true | proved | node:test static-source-scan | `purity-boundary.test.mjs` |
| PROP-018 | 2 | true | proved | fast-check | `swap-need.test.mjs` |
| PROP-019 | 1 | true | proved | node:test spy, exact call-arg equality | `driver-choke-point.test.mjs:90,122,152` |
| PROP-020 | 2 | true | proved | fast-check + call-order spy | `driver-crash-recovery.test.mjs:107,129` |
| PROP-021 | 0 | true | proved | node:test static-source-scan | `test-money-safety-scan.test.mjs:47,60` |
| PROP-022 | 2 | true | proved | fast-check + node:test fixed fixtures | `base-units.test.mjs:11,16,21,28,34,40,46,53` |
| PROP-023 | 1 | true | proved | node:test fixed fixtures + spy | `base-units.test.mjs:75,79,83,90` + `driver-choke-point.test.mjs:174` |

All 23 proof obligations from `specs/verification-architecture.md`'s table are `required: true`; all 23 are
now `status: "proved"` in `state.json`. 0 pending, 0 failed, 0 skipped.

## Results (task's money-path PROPs, in detail)

### PROP-019/022/023 — cap + base-units choke point
- **Tool**: node:test spy call-argument inspection + fast-check property tests
- **Command**: `node --test skills/self/spawn-funding-swap/lib/__tests__/driver-choke-point.test.mjs skills/self/spawn-funding-swap/lib/__tests__/base-units.test.mjs`
- **Result**: VERIFIED — `driver-choke-point.test.mjs:90-172` asserts the mocked `SkipApiClient.getRoute()`
  `amount_in` AND `BaseSigner.signAndBroadcast()` tx-amount arguments are BOTH bit-identical to
  `toBaseUnits(SWAP_MAX_USD, 6) = 20000000n` (capped case) or the exact per-fixture uncapped value, never a
  `<=`-equivalent comparison; `driver-choke-point.test.mjs:152` proves a wrong-decimals override FAILS this
  assertion (falsifiability). `base-units.test.mjs:11-71` proves `toBaseUnits`/`fromBaseUnits` floor
  (never round up), fail closed on NaN/negative/Infinity/overflow, and that wrong-decimals fixtures FAIL
  exact equality (10^6x-class defect detector). Confirmed by direct source read of `lib/pure/base-units.mjs`
  and `lib/driver.mjs:161-163` (the sole `toBaseUnits` call site) and `:260` (the sole `fromBaseUnits` call
  site) — grep-confirmed no second dollar→base-unit conversion site exists anywhere in the feature (see
  `security-results/manual-review-scans.txt`).

### PROP-005 — checkSourceFunded + driver-identity (exact bigint funding precondition)
- **Tool**: fast-check property + node:test spy
- **Command**: `node --test skills/self/spawn-funding-swap/lib/__tests__/funding-check.test.mjs skills/self/spawn-funding-swap/lib/__tests__/driver-choke-point.test.mjs`
- **Result**: VERIFIED — `funding-check.test.mjs:21` is the nonzero-balance DISCRIMINATING fixture
  (`baseUsdcBalance=5000000n < requiredBaseUnits=15320000n` must return `false`; a wrong-unit float
  comparison would wrongly return `true`); `:29` pins `MIN_GAS_WEI` as a literal, never a `0n`-default;
  three `fast-check` properties (`:42,53,64`) sweep randomized balances. `driver-choke-point.test.mjs:198`
  asserts `checkSourceFunded`'s `requiredBaseUnits`, Skip's `amount_in`, and the signer's tx amount are ALL
  THREE bit-identical bigints from ONE driver run (closes the "stale/independently-re-derived value at one
  call site" defect class); `:231` does the same for `minGasWei` against `MIN_GAS_WEI`.

### PROP-013 — slippage boundary (verifySettlement)
- **Tool**: node:test fixed boundary fixtures + spy
- **Command**: `node --test skills/self/spawn-funding-swap/lib/__tests__/settlement.test.mjs skills/self/spawn-funding-swap/lib/__tests__/driver-choke-point.test.mjs`
- **Result**: VERIFIED — `settlement.test.mjs:15` (`delta=995_000n` of a `1_000_000n` quote, exactly at the
  0.5% boundary) MUST pass; `:22` (`delta=994_999n`, one base unit below) MUST fail — proving the 50-bps
  tolerance is exact, not loose. `driver-choke-point.test.mjs:253` asserts the driver's actual `toleranceBps`
  argument at `verifySettlement`'s call site is bit-identical to `TOLERANCE_BPS`, closing the
  "hardcodes a looser value at its own call site" gap the isolated pure-function fixture alone cannot catch.

### PROP-009/020 — pre-broadcast nonce durability / crash-window idempotency
- **Tool**: fast-check property (crash-injection) + node:test call-order spy
- **Command**: `node --test skills/self/spawn-funding-swap/lib/__tests__/driver-crash-recovery.test.mjs`
- **Result**: VERIFIED — `:107` proves the `submitting` ledger write (nonce+legIndex) happens BEFORE
  `BaseSigner.signAndBroadcast()` is called (call-order, not eventual presence); `:129` proves the record
  survives even when the broadcast RPC call itself throws mid-flight. `:145/164/186/206` cover all three
  named crash windows (pre-broadcast, post-broadcast-pre-hash-write, post-hash-write-pre-confirmed,
  post-confirmed); `:225` is the `fast-check` property sweeping arbitrary single crash points, asserting
  replay-to-completion never issues more than one broadcast call that reaches `confirmed`.

### PROP-010 — canonical destination-address-keyed lock
- **Tool**: node:test simulated lock contention (distinct mocked quote ids per invocation)
- **Command**: `node --test skills/self/spawn-funding-swap/lib/__tests__/driver-lock-and-concurrency.test.mjs`
- **Result**: VERIFIED — `:66` proves two concurrent invocations with DISTINCT freshly-mocked Skip quote ids
  contending for ONE shared lock keyed by `destinationAkashAddress` produce exactly one proceeding
  invocation, the loser resuming/no-oping at lock acquisition BEFORE any `PriceOracle`/`SkipApiClient` call.
  `:101` is the falsifiability case: dedup is proven keyed by destination address, not by route/quote id.

### PROP-015/016 — identity pin (Base signer address, Akash key name)
- **Tool**: node:test spy + env fixture
- **Command**: `node --test skills/self/spawn-funding-swap/lib/__tests__/driver-preconditions.test.mjs skills/self/spawn-funding-swap/lib/__tests__/resolve-swap-identity.test.mjs skills/self/spawn-funding-swap/lib/__tests__/cli.test.mjs`
- **Result**: VERIFIED — `driver-preconditions.test.mjs:81` (unpinned Base signer address → non-zero exit,
  zero broadcast); `:89/96` (missing/wrong `AKASH_KEY_NAME` → non-zero exit, zero broadcast).
  `resolve-swap-identity.test.mjs` additionally proves (a) `ANICCA_HOME` unset/empty/no-wallet all fail
  closed, (b) a spoofed `SPAWN_FUNDING_SWAP_EXPECTED_BASE_SIGNER_ADDRESS`/`SOURCE_BASE_ADDRESS` env value is
  NEVER read (no such read exists anywhere in the module — confirmed by source read), (c) an ambient shared
  `ANICCA_EVM_PRIVATE_KEY` is NEVER used when `ANICCA_HOME` is unset (gate checked BEFORE
  `resolveEvmPrivateKey`'s own override path).

### PROP-021 — test-money isolation
- **Tool**: node:test static-source-scan (grep-equivalent)
- **Command**: `node --test skills/self/spawn-funding-swap/lib/__tests__/test-money-safety-scan.test.mjs`
- **Result**: VERIFIED — `:47` scans every file under this feature's test directories for an import of a
  concrete `SkipApiClient`/`ChainReader`/`BaseSigner`/`AkashSigner`-subprocess/`PriceOracle` implementation
  module (none found); `:60` scans for the literal `api.skip.build` or a real RPC endpoint URL outside a
  documented fixture-comment (none found). Independently re-confirmed this session by direct `grep -rln`
  (see `security-results/manual-review-scans.txt`) — same result.

## Known, pre-existing, documented scope boundary (not a proof-coverage gap)

`bin/spawn-funding-swap.mjs`'s production wiring path (`buildDeps()`, reached only when
`SPAWN_FUNDING_SWAP_FAKE_DEPS_MODULE` is unset) dynamically imports
`../lib/real-clients/{chain-reader,price-oracle,skip-api-client,base-signer,relay-poller}.mjs`. This
directory does not exist in the current tree. `contracts/sprint-1.md` (line 6) explicitly and
pre-emptively documents this as out of sprint-1 scope: "This sprint does NOT include the real effectful
client implementations ... every Phase 2a/2b test exercises the pure core and the driver exclusively
against injected fakes." No PROP-001..023 obligation references or depends on `real-clients/` existing —
every obligation is discharged against the pure core, the driver, and injected fakes per the Test-Money
Safety Rule. This means the CLI cannot be invoked for a real production swap yet (it would throw a module
resolution error at `buildDeps()`), which is itself a fail-closed-by-absence state, not a money-safety
defect — flagged here for full transparency, not as a blocking finding of this Phase 5 pass.

## Summary

- Required obligations: 23
- Proved: 23
- Failed: 0
- Skipped: 0
- Live evidence: target suite 104/104 pass, regression suite 310/310 pass, both exit 0, this session
- Degradation: none (no formal prover applicable/available for this JS feature; Tier 2 `fast-check` was
  always this feature's own declared ceiling per `specs/verification-architecture.md`'s Verification
  Strategy section, not a downgrade)
- Blocking hardening gap found: **none**. The `lib/real-clients/` absence is a pre-existing, already-
  documented sprint-1 scope boundary that does not affect any required proof obligation's coverage.
