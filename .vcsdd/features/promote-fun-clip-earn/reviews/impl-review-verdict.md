# VCSDD Phase-3 Implementation Review — promote-fun-clip-earn (lean)

**Reviewer:** fresh-context VCSDD adversary (disk-only, ZERO builder context)
**Spec:** REV 4 (Phase 1c PASS 5/5) — `specs/spec.md`
**Date:** 2026-06-29

## OVERALL VERDICT: **FAIL**

FAIL is driven by verification gaps, NOT by a money bug. After an exhaustive adversarial trace I found
**NO path by which the DONE gate records a false earn** — the money-correctness core is sound. The FAIL is
because the single most safety-critical shell wiring (the RECORD→DONE executor in `run.sh`) and the
spec-mandated `blocked:human:*` watchdog proof are **untested**, and because I **could not execute any
suite in this review environment** (no shell/execution tool present), so the GREEN claims are unverified.

| Dimension | Verdict |
|---|---|
| Spec Fidelity | PASS (delivered spine; one minor deviation) |
| Edge Case Coverage | **FAIL** |
| Implementation Correctness | PASS |
| Structural Integrity | PASS |
| Verification Readiness | **FAIL** |

---

## Test execution — HONEST STATUS

**I did NOT execute the tests.** This review environment exposes only Read/Write/Edit/Grep/Glob — there is
no Bash/`node`/`python3` runner available to me. I will not invent pass/fail counts (HARD 0.24 / HONESTY
Rule 4). Instead I performed a **line-by-line static trace** of each test's assertions against the
implementation; that trace is reported per-finding below.

- SKILL.md claims `45/45` (`_shared/lib`), `42/42` (`earn/lib`), `4/4` (record-payout), `8/8` (decide),
  `4/4` (run.sh). **These counts are UNVERIFIED by me.**
- Static `test()` count of the THREE new `_shared/lib` files I read = **30** (solana-verify 12 + ledger 9
  + identity-guard 9). The `__tests__/*.test.js` glob ALSO pulls in pre-existing `transfer/usdc/verify-tx`
  suites (not re-read), so `45` is only plausible as the *full* shared suite — I cannot confirm it.
- The orchestrator MUST re-run all five commands and confirm GREEN before treating this as Phase-2 done;
  my static trace indicates the assertions WOULD pass on a PII-clean process env (see FIND-006).

---

## Real vs Stubbed inventory

| Component | Status |
|---|---|
| `_shared/lib/solana-verify.mjs` (sigStatus / usdcDeltaForSig / usdcBalance) | **REAL**, injectable fetch, RPC shapes match verified mainnet jsonParsed |
| `_shared/lib/ledger.mjs` deriveLine sig/confirmed/chain passthrough | **REAL** |
| `_shared/lib/ledger.mjs` isProfitable EVM∨Solana generalization | **REAL** |
| `_shared/lib/ledger.mjs` alreadyRecordedSig (sig dedup) | **REAL** |
| `identity-guard.mjs` promote.fun/clip-promote/ig-clip added to ALLOWED | **REAL** |
| `decide.py` PURE state machine | **REAL**, genuinely pure |
| `record-payout.mjs` DONE executor | **REAL**, the money gate |
| `run.sh` RECORD transition (read sig → env -i → record-payout → emit DONE) | **REAL** but **UNTESTED** wiring |
| `run.sh` watchdog (`run_step`/`blocked_or`) | binary path REAL; pure-fallback REAL but untested; `blocked:human:*` emission untested |
| `run.sh` SELECT/CLIP/POST/SUBMIT/WITHDRAW live handlers | **STUBBED → "execute:$TRANS:not-yet-wired (#14)"**, honest, NO fake success (NOT a defect) |
| MEASURE live read (views/liveness a+b) | **STUBBED** (#14), decide consumes state only |

The stubs narrate honestly and never claim a side effect or an earn → compliant with HARD 0.24. **No stub
falsely claims success.** Discover mode takes no side effect and claims no earn.

---

## Money-correctness trace (the priority) — NO false-earn path found

`recordPayout` gate sequence is correct and fail-closed:
1. missing sig/wallet/ledger → `bad-args` (no append).
2. `alreadyRecordedSig` true → `duplicate` (sig dedup, no append).
3. `sigStatus.confirmed===false` → `unconfirmed` (no append). `err` is gated (`err == null`), unknown sig
   (`value[0]=null`) → false. Only `confirmed`/`finalized` accepted (spec-sanctioned, REQ-8).
4. `usdcDeltaForSig` `!(delta>0)` → `zero-delta` (rejects zero AND negative; sub-micro float noise rounds
   to 0 via `round()` → rejected).
5. line built with `external:true` justified by the inbound semantics: `usdcDeltaForSig` SUMS
   `(post−pre)` over **only** entries whose `owner===wallet && mint===USDC`, so a SELF-shuffle nets ~0 and
   an internal move cannot fabricate inflow. A positive net = genuine external ownership inflow.
6. `isProfitable(persistedLine)` re-checked on the persisted shape: net>0 ∧ not-swap ∧ external ∧
   (evm 0x1 ∨ sol confirmed). Round-trip verified by `record-solana.test.mjs`.

`isProfitable` still rejects every old false-green (swap even w/ sig+confirmed, no-external, narrate-only,
reverted `0x0`) and every new Solana false-green (no sig, `confirmed:false`, no external). owner/mint live
on each token-balance entry (correct), accountIndex pre↔post match correct, `uiAmount===null` falls back to
`amount/10**decimals` (and `uiAmount===0` does not wrongly fall through). Idempotency is sound under the
single-writer slot model.

---

## FINDINGS

### FIND-001 — `blocked:human:*` emission path is UNTESTED (spec-mandated test not realized)
- **dimension:** edge_case_coverage / verification_readiness · **category:** test_coverage · **severity: medium**
- **evidence:** `skills/earn/clip-promote/run.sh:54-59` (`blocked_or`), `:82-86` (only wrapped step);
  `tests/test_run.sh:22-28`.
- **why it blocks:** REQ-9 gives an explicit constructible test — *"STEP_DEADLINE_S=1 + a sleep 5 step
  returns 124 → assert the printed line is `blocked:human:*` and exit 0."* The test instead exercises only
  the bare `timeout 1 sleep 5` BINARY. The actual `run_step → 124 → blocked_or → emit "blocked:human:…"
  → exit 0` integration (the no-human runtime invariant) is never asserted. The skill could emit the wrong
  `did`, or fail to exit 0, and the suite stays green.

### FIND-002 — the RECORD→DONE executor wiring in run.sh has ZERO test coverage
- **dimension:** edge_case_coverage / verification_readiness · **category:** test_coverage · **severity: medium**
- **evidence:** `skills/earn/clip-promote/run.sh:77-95` (read sig from STATE → `env -i` invocation →
  parse `RES` → set phase idle → `emit "record:DONE"`). No test drives `EARN_MODE=execute` with a state
  carrying `phase:"WITHDRAW",sig:…`.
- **why it blocks:** this is the money path's shell glue. `record-payout.mjs` is unit-tested in isolation,
  but the `run.sh` argv/env-plumbing, RES JSON parsing, `EARNED` extraction and the `record:DONE`
  emission are unverified end-to-end. The single most important branch in the feature is untested.

### FIND-003 — pure-fallback watchdog (`run_step` no-binary branch) untested
- **dimension:** edge_case_coverage · **category:** test_coverage · **severity: low**
- **evidence:** `run.sh:38-44`; `tests/test_run.sh:23-28` SKIPS the fallback whenever a `timeout`/
  `gtimeout` binary exists (which it does on this Mac), so the SIGTERM/SIGKILL→124 fallback that the
  cloud box may actually rely on is never exercised.

### FIND-004 — usdcDeltaForSig ignores closed (pre-only) own USDC accounts
- **dimension:** implementation_correctness · **category:** requirement_mismatch · **severity: low**
- **evidence:** `_shared/lib/solana-verify.mjs:75-79` — the delta sums over `post` entries only. An own
  `owner+USDC` account present in `preTokenBalances` but absent from `postTokenBalances` (account
  drained/closed in the same tx) contributes `0`, not `−pre`. A tx that closes one of our USDC accounts
  while creating another could compute a positive delta despite a net loss.
- **why it is NOT critical:** unreachable in the promote.fun threat model — only an authority over our
  account can close it, and the spec invariant (line 213) is *"we never sign our own Solana tx."* The
  external payer cannot close our accounts. Still, the net-delta algorithm is incomplete; correct form
  subtracts pre-only entries.

### FIND-005 — cost_usdc never wired; REQ-8 `cost_usdc:<run cost>` is always 0
- **dimension:** spec_fidelity · **category:** requirement_mismatch · **severity: low**
- **evidence:** `record-payout.mjs:11` (`cost_usdc = 0` default), `run.sh:82-85` (never passes
  `COST_USDC`). net always = full delta.
- **why it is NOT a false-earn:** under-reporting cost only INFLATES net, and the inbound USDC is real and
  external. It cannot manufacture an earn that did not arrive. But the recorded net is not the true net;
  wire run cost before claiming accurate profitability.

### FIND-006 — record-payout / record-solana unit tests assert against ambient process.env
- **dimension:** structural_integrity / verification_readiness · **category:** test_quality · **severity: low**
- **evidence:** `tests/test_record_payout.mjs:35-43`, `earn/lib/__tests__/record-solana.test.mjs:18-41`
  call `record()` → `assertOwnIdentityOnly(line)` with the DEFAULT `env=process.env` (no clean env
  injected). On a dev/CI shell that exports `USER_*`/`GOOGLE_LOGIN`/`COMPOSIO`/`TELEGRAM`/`*GMAIL*`, these
  tests THROW and fail. The production RECORD path is protected by `env -i`; the tests do not replicate it.
- **why it matters:** the "4/4 GREEN" claim is environment-dependent. (`identity-guard.test.js` correctly
  injects `{env}` fixtures — the record-path tests should do the same.)

### FIND-007 — GREEN counts unverified; I executed nothing
- **dimension:** verification_readiness · **category:** process · **severity: medium (process)**
- **evidence:** SKILL.md:45-52 asserts `45/45 + 42/42 + 4/4 + 8/8 + 4/4`. No execution tool in this review
  env. Static `test()` count of the 3 new `_shared` files = 30; `45` can only hold if the pre-existing
  `transfer/usdc/verify-tx` suites are included.
- **why it blocks:** VSDD requires the lib regression suite to be GREEN as a 4-D convergence condition.
  Until the orchestrator re-runs and confirms, GREEN is asserted, not proven.

---

## MUST-FIX (prioritized) before this spine is treated as Phase-2 done

1. **(FIND-001)** Add the spec's constructible REQ-9 test: inject a real blocking step under
   `STEP_DEADLINE_S=1` (or a stub step that sleeps) through `run.sh` execute mode and assert the printed
   `did` is `blocked:human:<step>` AND exit code 0.
2. **(FIND-002)** Add an integration test that drives `EARN_MODE=execute` with a state
   `{phase:"WITHDRAW", sig:…}` and a stubbed `record-payout` (or fixture RPC) to assert the `record:DONE`
   line, the `earned_usdc=delta` value, and the state→`idle` reset.
3. **(FIND-007)** Orchestrator: actually execute all five suites and paste real counts; reconcile the
   SKILL.md numbers.
4. **(FIND-006)** Make the record-path unit tests inject a clean `{env}` (or run under `env -i`) so GREEN
   is not ambient-env dependent.
5. **(FIND-003 / FIND-004 / FIND-005)** Low: test the pure watchdog fallback; subtract pre-only closed
   own-USDC accounts in `usdcDeltaForSig` for completeness; wire `COST_USDC` into the RECORD invocation.

No CRITICAL findings. The money gate is correct; the blockers are verification/coverage, not a false earn.
