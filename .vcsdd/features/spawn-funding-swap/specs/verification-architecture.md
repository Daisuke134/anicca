# Verification Architecture — spawn-funding-swap

## Purity Boundary Map

- **Pure Core** (deterministic, no I/O, formally/property-verifiable in isolation; language: TypeScript,
  no `fetch`/`fs`/`child_process` imports permitted in these modules):
  - `computeSwapNeed(currentAkt, thresholdAkt): number` — REQ-001
  - `capUsd(requestedUsd): number` — REQ-006, cap value is a `const` literal in this module only
  - `validateRoute(routeResponse: unknown): RouteValidationResult` — REQ-002
  - `planNextLeg(route: ValidatedRoute, ledger: LegLedgerState): NextAction` — REQ-004, REQ-005
  - `checkSourceFunded(baseUsdcBalance, baseGasBalance, neededUsd, minGasWei): boolean` — REQ-003
  - `verifySettlement(preBalanceUakt, postBalanceUakt, quotedAmountOutUakt, toleranceBps): boolean` —
    REQ-007
  - `reconcileLedgerOnResume(ledgerFile: unknown): ReconciledLedger | 'CORRUPT'` — REQ-005 (pure parse +
    validation; the actual file read is effectful, but interpreting its contents is pure)

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

The pure/effectful split is enforced structurally: pure modules live under `lib/pure/` and MUST have no
import of `node:fs`, `node:child_process`, `node:http(s)`, or `fetch`; a lint/test rule may assert this
(Tier 0, cheap, high-value guard against boundary erosion).

## Proof Obligations

| ID | Description | REQ | Tier | Required | Tool |
|----|---|---|---|---|---|
| PROP-001 | `computeSwapNeed(current, threshold)` returns 0 for all `current >= threshold`; never negative | REQ-001 | 2 | true | fast-check (property) |
| PROP-002 | When `need == 0`, driver calls zero Skip/sign/broadcast functions | REQ-001 | 1 | true | node:test + spy mocks |
| PROP-003 | `validateRoute` rejects every malformed/wrong-denom/wrong-chain/zero-amount fixture; accepts only the confirmed-live shape | REQ-002 | 1 | true | node:test fixtures |
| PROP-004 | No signing code path reachable unless `validateRoute` returned true for the in-hand route object | REQ-002 | 1 | true | node:test + spy mocks |
| PROP-005 | `checkSourceFunded` returns false for all `baseUsdcBalance < neededUsd` or `baseGasBalance < minGasWei`; driver never proceeds past a `false` result | REQ-003 | 2 | true | fast-check (property) + node:test spy |
| PROP-006 | Regression fixture: today's real balances (Base USDC≈0, Base gas≈0) fail closed with an explicit deficit message | REQ-003 | 0 | true | node:test fixture (fixed values, not generated) |
| PROP-007 | `planNextLeg` never returns a leg index already `confirmed` in the ledger | REQ-004, REQ-005 | 2 | true | fast-check (property over ledger states) |
| PROP-008 | Simulated Leg-2 stall past timeout → ledger shows Leg-1 `confirmed`, Leg-2 `pending` (not `failed`/absent); exit non-zero | REQ-004 | 1 | true | node:test + fake timers + mock poller |
| PROP-009 | For any crash-injection point (pre-broadcast, post-broadcast-pre-ledger-write, post-ledger-write) at each leg boundary, replay-to-completion never issues more than one `confirmed`-producing broadcast call per leg index | REQ-005 | 2 | true | fast-check (property, sequence of crash points) |
| PROP-010 | Two concurrent driver invocations sharing one ledger file/lock produce exactly one successful submission per leg across both | REQ-005 | 2 | true | fast-check (property, interleaving schedules) or node:test with simulated lock contention |
| PROP-011 | `capUsd(x) === Math.min(x, SWAP_MAX_USD)` for all finite non-negative `x`; `NaN`/negative/`Infinity` inputs resolve to a fail-closed value (0 or throw), never to an unbounded pass-through | REQ-006 | 2 | true | fast-check (property, adversarial inputs incl. NaN/Infinity/negative) |
| PROP-012 | `capUsd` output is bit-identical regardless of `process.env.SWAP_MAX_USD` / any hostile env or genome-provided override value being set | REQ-006 | 1 | true | node:test (hostile-env fixture) |
| PROP-013 | Success path unreachable unless `verifySettlement` returns true for the specific pre/post balance pair observed; a mock showing unchanged post-balance after all legs "succeed" yields non-zero exit | REQ-007 | 1 | true | node:test + spy mocks |
| PROP-014 | CLI entrypoint invoked as `bash -c "<cmd>"` (matching `akt-treasury.sh` call site) exits 0 only on a full success fixture, non-zero on every failure fixture (no-route, no-source, leg-timeout, cap-exceeded, settlement-unverified, bad-signer) | REQ-008 | 1 | true | node:test (subprocess invocation, injected mock transport via config) |
| PROP-015 | Base signer resolving to an unexpected/unpinned address → non-zero exit, zero broadcast calls | REQ-009 | 1 | true | node:test + spy mocks |
| PROP-016 | `AKASH_KEY_NAME` unset or not equal to `anicca-akash` → non-zero exit, zero broadcast calls | REQ-009 | 1 | true | node:test (env fixture) |
| PROP-017 | Pure-module import boundary: no file under `lib/pure/**` imports `node:fs`, `node:child_process`, `node:http(s)`, or references `fetch` | (structural, all REQs) | 0 | true | node:test static-source-scan (grep-equivalent assertion, no formal tool needed) |

## Verification Strategy

- **Tier 0** (no formal proof needed — cheap structural/regression guards): PROP-006 (today's real
  balances fixture — a fixed regression case, not a property), PROP-017 (import-boundary static scan).
- **Tier 1** (unit tests / mocked-transport tests, deterministic fixtures): PROP-002, PROP-003, PROP-004,
  PROP-008, PROP-012, PROP-013, PROP-014, PROP-015, PROP-016 — every effectful client is injected as a
  mock/spy; assertions cover exit codes, call counts, and ledger contents. None of these tests perform
  real network calls or real signing (enforced by PROP-017's boundary + Phase 2a test-harness convention
  of never importing the real `SkipApiClient`/`ChainReader`/`Signer` implementations, only fakes).
- **Tier 2** (property-based / fuzz testing on the money-safety-critical surface — `fast-check`, since
  this feature is TypeScript): PROP-001, PROP-005, PROP-007, PROP-009, PROP-010, PROP-011. These six
  cover exactly the four money-safety MUSTs called out in the task: (a) threshold no-over-buy = PROP-001,
  (b) fail-closed on no funded source = PROP-005 (paired with PROP-006's fixed regression case and
  PROP-003/PROP-004 for the no-route sibling), (c) idempotency/no-double-spend = PROP-007 + PROP-009 +
  PROP-010, (d) cap hard-override immunity = PROP-011 + PROP-012. Tier 2 tests generate hundreds of
  randomized inputs/schedules per run and MUST all operate purely in-memory against the pure-core
  functions or in-memory fakes — never against real chains.
- **Tier 3** (strong formal proof): not required for this feature. The money-safety properties are fully
  covered by exhaustive-enough property testing (Tier 2) over a small, pure, easily-modeled state
  machine (leg ledger + cap function); a Kani/TLA+-grade proof would be disproportionate to the
  complexity here (a handful of pure functions with small, bounded state), and Tier 2 fast-check gives a
  falsifiable, fast-running, CI-friendly guarantee consistent with `sol-trade`'s existing
  `lib/__tests__/sol-max-spend.test.mjs` precedent for money-safety-critical caps in this codebase.

## Test-Money Safety Rule (binding on Phase 2a/2b)

No test file in this feature may hold a real private key, call a real Skip API endpoint, call a real
Base/Akash RPC, or broadcast a real transaction. Every Tier 0–2 test operates against injected
fakes/mocks of `SkipApiClient`, `ChainReader`, `BaseSigner`, `RelayPoller`, and `LedgerStore`. The one
regression fixture that encodes today's real balances (PROP-006) uses those balances as **literal input
constants** to the pure `checkSourceFunded` function — it does not query anything live. A real swap is
only ever triggered by the production CLI entrypoint wired to real clients, which is explicitly out of
scope for any automated test run.
