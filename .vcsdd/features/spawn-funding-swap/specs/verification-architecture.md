# Verification Architecture — spawn-funding-swap

## Purity Boundary Map

- **Pure Core** (deterministic, no I/O, formally/property-verifiable in isolation; language: TypeScript,
  no `fetch`/`fs`/`child_process` imports permitted in these modules):
  - `computeSwapNeed(currentAkt, thresholdAkt): number` — REQ-001
  - `usdEquivalentOf(needAkt: number, aktUsdPrice: number): number` — REQ-011; sole producer of
    `capUsd`'s input across this feature, throws for `aktUsdPrice <= 0`/`NaN`/`Infinity`
  - `capUsd(requestedUsd): number` — REQ-006, cap value is a `const` literal in this module only
  - `validateRoute(routeResponse: unknown): RouteValidationResult` — REQ-002
  - `planNextLeg(route: ValidatedRoute, ledger: LegLedgerState): NextAction` — REQ-004, REQ-005
  - `checkSourceFunded(baseUsdcBalance: bigint, baseGasBalance: bigint, requiredBaseUnits: bigint, minGasWei: bigint): boolean`
    — REQ-003; `requiredBaseUnits` is the SAME `toBaseUnits(capUsd(usdEquivalentOf(need, aktUsdPrice)),
    USDC_DECIMALS_BASE)` `bigint` value REQ-012 routes to `SkipApiClient.getRoute()`'s `amount_in` (REQ-002)
    and `BaseSigner.signAndBroadcast()`'s tx amount (REQ-006) — never an independently-named or
    independently-derived dollar float; the comparison against `baseUsdcBalance` is exact bigint-vs-bigint
  - `verifySettlement(preBalanceUakt, postBalanceUakt, quotedAmountOutUakt, toleranceBps): boolean` —
    REQ-007
  - `reconcileLedgerOnResume(ledgerFile: unknown): ReconciledLedger | 'CORRUPT'` — REQ-005 (pure parse +
    validation; the actual file read is effectful, but interpreting its contents is pure)
  - `toBaseUnits(amountFloat: number, decimals: number): bigint` — REQ-012; THE single named choke point
    converting `capUsd(usdEquivalentOf(need, aktUsdPrice))`'s dollar float into the integer amount used as
    BOTH `SkipApiClient.getRoute()`'s `amount_in` (REQ-002) and `BaseSigner.signAndBroadcast()`'s tx amount
    (REQ-006); `decimals` always explicit (`USDC_DECIMALS_BASE = 6`), floors (never rounds up), throws on
    `NaN`/negative/non-finite input or `Number.MAX_SAFE_INTEGER` overflow
  - `fromBaseUnits(amount: bigint, decimals: number): number` — REQ-012; inverse conversion, used to turn
    `ChainReader.getAkashBalance()`'s raw `uakt` `bigint` into the decimal-AKT `current` input consumed by
    `computeSwapNeed` (REQ-001, `AKT_DECIMALS = 6`); throws on negative `bigint` input

- **Effectful Shell** (I/O; MUST be injected as parameters/interfaces, never module-level singletons, so
  Phase 2a tests substitute mocks with zero real network/chain access):
  - `SkipApiClient.getRoute(params): Promise<unknown>` — HTTP POST to `api.skip.build`
  - `ChainReader.getBaseUsdc(address): Promise<bigint>`, `ChainReader.getBaseGas(address): Promise<bigint>`
  - `ChainReader.getAkashBalance(address): Promise<bigint>` — `akash query bank balances` (CLI or REST)
  - `BaseSigner.signAndBroadcast(tx): Promise<{txHash}>`
  - `AkashSigner` usage is delegated to `akash tx ... --from anicca-akash` (existing CLI pattern from
    `akt-treasury.sh`) — effectful subprocess call
  - `RelayPoller.waitForConfirmation(chainId, txHashOrPacket, timeoutMs): Promise<'confirmed'|'pending'|'failed'>`
  - `LedgerStore.read()/write(state)` — local JSON ledger file (effectful disk I/O, but its *contents*
    are interpreted by the pure `reconcileLedgerOnResume`)
  - CLI entrypoint (`bin/spawn-funding-swap.ts` or `.mjs`) — the only place these effectful clients are
    concretely instantiated and wired to the pure core; this is what `TREASURY_SWAP_CMD` invokes.
  - `PriceOracle.getAktUsdPrice(): Promise<number>` — external AKT/USD price source, queried once per
    invocation, AFTER `LedgerStore`'s canonical lock (REQ-010) is held and BEFORE `SkipApiClient.getRoute()`
    (REQ-002); MUST be injectable/mockable, never queried live in Phase 2a/2b tests (REQ-011).
  - `LedgerStore` canonical lock primitive — atomic acquire/release keyed by the destination Akash
    address (NOT by Skip route/quote id), backed by the same ledger file as REQ-005's resumability state
    (REQ-010); acquired BEFORE any `PriceOracle`/`SkipApiClient` call.

The pure/effectful split is enforced structurally: pure modules live under `lib/pure/` and MUST have no
import of `node:fs`, `node:child_process`, `node:http(s)`, or `fetch`; a lint/test rule may assert this
(Tier 0, cheap, high-value guard against boundary erosion). Test files under this feature's test
directories are held to a symmetric structural rule (PROP-021): no import of the concrete
`SkipApiClient`/`ChainReader`/`BaseSigner`/`AkashSigner`-subprocess/`PriceOracle` implementation modules,
and no real endpoint literal strings outside a documented fixture-comment.

## Proof Obligations

| ID | Description | REQ | Tier | Required | Tool |
|----|---|---|---|---|---|
| PROP-001 | `computeSwapNeed(current, threshold)` returns 0 for all `current >= threshold`; never negative | REQ-001 | 2 | true | fast-check (property) |
| PROP-002 | When `need == 0`, driver calls zero Skip/sign/broadcast functions | REQ-001 | 1 | true | node:test + spy mocks |
| PROP-003 | `validateRoute` rejects every malformed/wrong-denom/wrong-chain/zero-amount fixture; accepts only the confirmed-live shape | REQ-002 | 1 | true | node:test fixtures |
| PROP-004 | No signing code path reachable unless `validateRoute` returned true for the in-hand route object | REQ-002 | 1 | true | node:test + spy mocks |
| PROP-005 | `checkSourceFunded` returns false for all `baseUsdcBalance < requiredBaseUnits` (exact `bigint`-vs-`bigint` comparison, `requiredBaseUnits` per REQ-012) or `baseGasBalance < minGasWei`; driver never proceeds past a `false` result. Includes a nonzero-balance DISCRIMINATING fixture (`baseUsdcBalance = 5000000n`, `requiredBaseUnits = toBaseUnits(15.32, 6) = 15320000n`) which MUST return `false`; a wrong-unit implementation comparing `baseUsdcBalance` against the raw dollar float `15.32` instead (`5000000n >= 15.32` evaluates `true`) would wrongly return `true` (funded) and MUST fail this assertion — proving the test is falsifiable against the FIND-001/FIND-002 10^6x-class wrong-unit false-funded defect, which the zero-balance-only PROP-006 fixture cannot catch | REQ-003 | 2 | true | fast-check (property) + node:test spy |
| PROP-006 | Regression fixture: today's real balances (Base USDC≈0, Base gas≈0) fail closed with an explicit deficit message. This zero-balance fixture alone is non-discriminating (`0n` is `<` any positive comparand regardless of unit) — PROP-005's nonzero fixture is the mechanism that catches a wrong-unit comparison | REQ-003 | 0 | true | node:test fixture (fixed values, not generated) |
| PROP-007 | `planNextLeg` never returns a leg index already `confirmed` in the ledger | REQ-004, REQ-005 | 2 | true | fast-check (property over ledger states) |
| PROP-008 | Simulated Leg-2 stall past timeout → ledger shows Leg-1 `confirmed`, Leg-2 `pending` (not `failed`/absent); exit non-zero | REQ-004 | 1 | true | node:test + fake timers + mock poller |
| PROP-009 | For any crash-injection point across the three windows named in REQ-005 — Window 1 (pre-broadcast-RPC-call), Window 2 (post-broadcast-RPC-call but pre-tx-hash-write, AND post-tx-hash-write-pre-`confirmed`-write), Window 3 (post-`confirmed`-write) — at each leg boundary, replay-to-completion never issues more than one `confirmed`-producing broadcast call per leg index. Window 2's two sub-cases MUST both resolve via an on-chain query keyed by the synchronous pre-broadcast `submitting` record (nonce+leg index) asserted separately by PROP-020, not by an unspecified mechanism | REQ-005 | 2 | true | fast-check (property, sequence of crash points across all three windows) |
| PROP-010 | Two concurrent driver invocations, each given a *distinct*, freshly-mocked Skip route/quote id but contending for ONE shared canonical lock/ledger keyed by the destination Akash address `akash1ms7...` (REQ-010 — not by route/quote id), produce exactly one successful submission per leg across both; the loser MUST be observed resuming/no-oping at the lock-acquisition step, BEFORE it calls `PriceOracle.getAktUsdPrice()` or `SkipApiClient.getRoute()` at all | REQ-005, REQ-010 | 2 | true | fast-check (property, interleaving schedules with distinct mocked quote ids per invocation) or node:test with simulated lock contention |
| PROP-011 | `capUsd(x) === Math.min(x, SWAP_MAX_USD)` for all finite non-negative `x`; `NaN`/negative/`Infinity` inputs resolve to a fail-closed value (0 or throw), never to an unbounded pass-through | REQ-006 | 2 | true | fast-check (property, adversarial inputs incl. NaN/Infinity/negative) |
| PROP-012 | `capUsd` output is bit-identical regardless of `process.env.SWAP_MAX_USD` / any hostile env or genome-provided override value being set | REQ-006 | 1 | true | node:test (hostile-env fixture) |
| PROP-013 | Success path unreachable unless `verifySettlement` returns true for the specific pre/post balance pair observed; a mock showing unchanged post-balance after all legs "succeed" yields non-zero exit | REQ-007 | 1 | true | node:test + spy mocks |
| PROP-014 | CLI entrypoint invoked as `bash -c "<cmd>"` (matching `akt-treasury.sh` call site) exits 0 only on a full success fixture, non-zero on every failure fixture (no-route, no-source, leg-timeout, cap-exceeded, settlement-unverified, bad-signer) | REQ-008 | 1 | true | node:test (subprocess invocation, injected mock transport via config) |
| PROP-015 | Base signer resolving to an unexpected/unpinned address → non-zero exit, zero broadcast calls | REQ-009 | 1 | true | node:test + spy mocks |
| PROP-016 | `AKASH_KEY_NAME` unset or not equal to `anicca-akash` → non-zero exit, zero broadcast calls | REQ-009 | 1 | true | node:test (env fixture) |
| PROP-017 | Pure-module import boundary: no file under `lib/pure/**` imports `node:fs`, `node:child_process`, `node:http(s)`, or references `fetch` | (structural, all REQs) | 0 | true | node:test static-source-scan (grep-equivalent assertion, no formal tool needed) |
| PROP-018 | `usdEquivalentOf(needAkt, aktUsdPrice) === needAkt * aktUsdPrice` for all finite non-negative `needAkt` and finite positive `aktUsdPrice`; resolves to an explicit fail-closed signal (throw) for `aktUsdPrice <= 0`, `NaN`, or `Infinity` — never an unbounded/NaN/negative pass-through | REQ-011 | 2 | true | fast-check (property, adversarial price inputs) |
| PROP-019 | Driver-level choke-point (rewritten, FIND-001/FIND-002): for any `need` whose USD-equivalent exceeds `SWAP_MAX_USD`, the mocked `SkipApiClient.getRoute()` call's `amount_in` argument AND the mocked `BaseSigner.signAndBroadcast()` call's transaction-amount argument are BOTH bit-identical to the exact INTEGER `bigint` value `toBaseUnits(SWAP_MAX_USD, USDC_DECIMALS_BASE)` — asserted by exact equality against a concrete expected integer (e.g. `SWAP_MAX_USD=20` and `need`-USD-equivalent `= 25.00` (exceeds cap) → both call arguments expected `toBaseUnits(20, 6) = 20000000n`), NEVER by a `<=`-"equivalent" float comparison — inspecting the spies' actual call arguments, not `capUsd()`'s/`toBaseUnits()`'s return values in isolation. A companion fixture below the SAME `SWAP_MAX_USD=20` (e.g. `need`-USD-equivalent `= 15.00`, uncapped) asserts both call arguments equal exactly `15000000n`. A fixture built with a WRONG `decimals` constant (`0` or `18` instead of `6`) at either call site MUST fail this assertion — proving the test is falsifiable against a 10^6x-class unit-conversion defect | REQ-002, REQ-006, REQ-011, REQ-012 | 1 | true | node:test + spy mocks with exact call-argument equality |
| PROP-020 | The pre-broadcast `submitting` record (source-account deterministic nonce + leg index) is durably written to the canonical ledger SYNCHRONOUSLY and BEFORE the `BaseSigner.signAndBroadcast()`/leg-broadcast RPC call is made — verified by call-order assertion (ledger-write call precedes broadcast-RPC call in every recorded invocation, including ones where the mocked broadcast call is made to hang/crash before returning) | REQ-005 | 2 | true | fast-check (property, crash-injection at exact pre/post-RPC-return points) + node:test call-order spy |
| PROP-021 | Test-file static-source-scan (structural, symmetric to PROP-017): no file under this feature's test directories imports the concrete `SkipApiClient`/`ChainReader`/`BaseSigner`/`AkashSigner`-subprocess/`PriceOracle` implementation modules (only the fake/mock modules), and no test file contains the literal string `api.skip.build` or a real RPC endpoint URL outside a documented fixture-comment | (structural, all REQs) | 0 | true | node:test static-source-scan (grep-equivalent assertion) |
| PROP-022 | `toBaseUnits(amountFloat, decimals)` conversion exactness (new, FIND-001/FIND-002): (a) fixed fixture `toBaseUnits(15.0, 6) === 15000000n`; (b) floor-rounding fixture `toBaseUnits(15.0000009, 6) === 15000000n` (a naive `Math.round` implementation yielding `15000001n` MUST fail); (c) `toBaseUnits(SWAP_MAX_USD, 6)` equals the exact upper-bound `bigint` used by PROP-019; (d) adversarial-input property: `NaN`/negative/`Infinity` `amountFloat`, or an intermediate value exceeding `Number.MAX_SAFE_INTEGER`, or a missing/non-integer/negative `decimals`, all throw (fail-closed), never coerce to `0n` or silently truncate; (e) wrong-decimals fixture: `toBaseUnits(15.0, 0)` and `toBaseUnits(15.0, 18)` both produce integers that FAIL an exact-equality assertion against the correctly-scaled `15000000n` expectation — the mechanism that makes a 10^6x-class conversion defect fail loudly | REQ-012 | 2 | true | fast-check (property, adversarial inputs) + node:test fixed fixtures |
| PROP-023 | `fromBaseUnits(amount, decimals)` correctness and round-trip: fixed fixture `fromBaseUnits(1850000n, 6) === 1.85`; round-trip property `fromBaseUnits(toBaseUnits(x, decimals), decimals) === x` for representative fixture floats with no more than `decimals` fractional digits; negative-`bigint` input throws (fail-closed); driver-level assertion that `computeSwapNeed`'s `current` argument is bit-identical to `fromBaseUnits(mockedBalanceUakt, AKT_DECIMALS)`, never the raw `bigint` or an un-scaled `Number(balanceUakt)` | REQ-001, REQ-012 | 1 | true | node:test fixed fixtures + node:test spy on driver call argument |

## Verification Strategy

- **Tier 0** (no formal proof needed — cheap structural/regression guards): PROP-006 (today's real
  balances fixture — a fixed regression case, not a property), PROP-017 (pure-module import-boundary
  static scan), PROP-021 (test-file import/endpoint-literal static scan — symmetric counterpart to
  PROP-017 on the test side, closing the prose-only Test-Money Safety Rule gap).
- **Tier 1** (unit tests / mocked-transport tests, deterministic fixtures): PROP-002, PROP-003, PROP-004,
  PROP-008, PROP-012, PROP-013, PROP-014, PROP-015, PROP-016, PROP-019, PROP-023 — every effectful client
  is injected as a mock/spy; assertions cover exit codes, call counts, call arguments, and ledger contents.
  PROP-019 (rewritten per FIND-001/FIND-002) and PROP-023 assert exact integer/`bigint` call-argument
  values, never a range or an "-equivalent" float comparison. None of these tests perform real network
  calls or real signing (enforced by PROP-017/PROP-021's boundaries + Phase 2a test-harness convention of
  never importing the real `SkipApiClient`/`ChainReader`/`Signer`/`PriceOracle` implementations, only
  fakes).
- **Tier 2** (property-based / fuzz testing on the money-safety-critical surface — `fast-check`, since
  this feature is TypeScript): PROP-001, PROP-005, PROP-007, PROP-009, PROP-010, PROP-011, PROP-018,
  PROP-020, PROP-022. These nine cover exactly the money-safety MUSTs called out in the task, now
  including the spec-review iteration-1 and iteration-2 findings: (a) threshold no-over-buy = PROP-001,
  (b) fail-closed on no funded source = PROP-005 (paired with PROP-006's fixed regression case and
  PROP-003/PROP-004 for the no-route sibling), (c) idempotency/no-double-spend across all three crash
  windows = PROP-007 + PROP-009 + PROP-020, (d) canonical destination-scoped lock precondition = PROP-010,
  (e) cap hard-override immunity at both the pure-function level AND the driver call-argument level =
  PROP-011 + PROP-012 + PROP-019, (f) AKT→USD conversion correctness/fail-closedness = PROP-018, (g)
  float-to-integer base-unit conversion exactness/fail-closedness (closing FIND-001/FIND-002's 10^6x gap)
  = PROP-022, paired with PROP-023's symmetric read-side conversion. Tier 2 tests generate hundreds of
  randomized inputs/schedules per run and MUST all operate purely in-memory against the pure-core
  functions or in-memory fakes — never against real chains.
- **Tier 3** (strong formal proof): not required for this feature. The money-safety properties are fully
  covered by exhaustive-enough property testing (Tier 2) over a small, pure, easily-modeled state
  machine (leg ledger + cap function + price conversion + base-unit conversion); a Kani/TLA+-grade proof
  would be disproportionate to the complexity here (a handful of pure functions with small, bounded
  state), and Tier 2 fast-check
  gives a falsifiable, fast-running, CI-friendly guarantee consistent with `sol-trade`'s existing
  `lib/__tests__/sol-max-spend.test.mjs` precedent for money-safety-critical caps in this codebase.

## Test-Money Safety Rule (binding on Phase 2a/2b)

This rule is structurally enforced, not merely prose: PROP-021 performs a static source-scan over every
file under this feature's test directories, asserting none imports the concrete
`SkipApiClient`/`ChainReader`/`BaseSigner`/`AkashSigner`-subprocess/`PriceOracle` implementation modules
(only the fake/mock modules are permitted) and none contains the literal string `api.skip.build` or a real
RPC endpoint URL outside a documented fixture-comment — giving PROP-017's pure-module import boundary a
symmetric, falsifiable counterpart on the test side.

No test file in this feature may hold a real private key, call a real Skip API endpoint, call a real
Base/Akash RPC, or broadcast a real transaction. Every Tier 0–2 test operates against injected
fakes/mocks of `SkipApiClient`, `ChainReader`, `BaseSigner`, `RelayPoller`, and `LedgerStore`. The one
regression fixture that encodes today's real balances (PROP-006) uses those balances as **literal input
constants** to the pure `checkSourceFunded` function — it does not query anything live. A real swap is
only ever triggered by the production CLI entrypoint wired to real clients, which is explicitly out of
scope for any automated test run.
