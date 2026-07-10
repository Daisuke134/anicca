# Verification Report

## Feature: franklin-sol-evolvable-edge | Sprint: 1 | Date: 2026-07-10

Code under verification: `~/anicca/.worktrees/franklin-sol-edge/skills/earn/sol-trade/` (worktree
commit `42b35c6`, branch `feature/franklin-sol-edge`). Modules hardened: `lib/sol-genome.mjs`,
`lib/sol-gate.mjs`, `lib/sol-trace.mjs`, `lib/sol-evolve.mjs`, `lib/sol-gate-cli.mjs`,
`lib/resolve-max-spend.sh`, `run.sh` (pre-gate wiring), `baseline-genome.json`.

## Tooling detection

| Tool | Status |
|---|---|
| `node --test` (Tier 0/1) | available, used |
| `fast-check` (Tier 2 property tests) | available (`node_modules/fast-check@4.8.0`), used — already wired into the Phase 2 test suite |
| `kani` (Tier 3, Rust BMC) | not applicable — this is a JS/bash feature, no Tier 3 obligation exists per verification-architecture.md |
| `hypothesis` (Python) | not applicable — no Python production code in this feature |
| `semgrep` | available (`1.168.0`), used (`--config auto` + `--config p/security-audit`) |

No Tier 3 tool was required (verification-architecture.md explicitly scopes this feature to Tiers
0-2 only — no concurrency-critical shared-mutable-state proof obligation exists). No degradation
occurred.

## Full suite (fresh run, this session)

| Suite | Command | Result | Raw log |
|---|---|---|---|
| SOL rail new/extended tests | `node --test skills/earn/sol-trade/lib/__tests__/sol-*.test.mjs` | **89/89 pass, 0 fail** | `verification/fuzz-results/node-test-sol-suite.log` |
| Bash integration | `bash skills/earn/sol-trade/tests/test_run.sh` | **9/9 pass** | `verification/fuzz-results/bash-test-run.log` |
| Regression baseline (pre-existing sol-trade `parse-pass`/`record-swap` + shared `earn/lib`) | `node --test skills/earn/sol-trade/lib/__tests__/{parse-pass,record-swap}.test.mjs skills/earn/lib/__tests__/*.test.mjs` | **73/73 pass, 0 fail** | `verification/fuzz-results/node-test-regression-baseline.log` |

No regression. Combined SOL-rail total (new + pre-existing sol-trade-local): 102/102.

## Proof Obligations

| ID | Tier | Required | Status | Tool | Test evidence |
|----|------|----------|--------|------|---------|
| PROP-001 | 0 | true | **proved** | node:test | `sol-genome.test.mjs` — SAFE_DEFAULT_GENOME exactly 5 keys/defaults, disjoint from FORBIDDEN_CAP_KEYS |
| PROP-002 | 2 | true | **proved** | node:test + fast-check | `sol-genome.test.mjs` — mutate() output always within [min,max], randomized seeds; re-anchor-before-step edge case |
| PROP-003 | 1 | true | **proved** | node:test | `sol-genome.test.mjs` — mutate() never touches SOL_GATE_WATCHLIST or FORBIDDEN_CAP_KEYS |
| PROP-004 | 2 | true | **proved** | node:test + fast-check | `sol-genome.test.mjs` — stripForbidden() removes SOL_TRADE_MAX_SPEND from adversarially crafted objects, never mutates input |
| PROP-005 | 1 | true | **proved** | node:test | `sol-genome.test.mjs` — genomeId() order-independent, cap-presence-independent, differing values -> differing ids |
| PROP-006 | 1 | true | **proved** | node:test | `sol-genome.test.mjs` — loadGenome() never throws on missing/malformed files, override wins per-key, fails closed to SAFE_DEFAULT |
| PROP-007 | 1 | true | **proved** | node:test (injected fetchImpl, no real network) | `sol-gate.test.mjs` — cold-start/fail/malformed/NaN all -> no-signal; fresh-always-preferred; multi-mint isolation; 8s timeout NFR |
| PROP-008 | 2 | true | **proved** | node:test + fast-check | `sol-gate.test.mjs` — wouldEngage iff all 3 thresholds hold; NaN/Infinity -> false; direction-agnostic |
| PROP-009 | 2 | true | **proved** | node:test + fast-check | `sol-gate.test.mjs` — `liveEnabled=false -> engage always false` (fast-check over randomized momentum/liquidity); only exactly `"1"` is live |
| PROP-010 | 1 | true | **proved** | node:test | `sol-gate.test.mjs` — describeSignal payload contains no action/side/size directive token (schema + fast-check) |
| PROP-011 | 1 | true | **proved** | node:test | `sol-trace.test.mjs` — every pass appends exactly one sol-gate.trace.jsonl line with required fields; fail-soft on write error |
| PROP-012 | 1 | true | **proved** | node:test | `sol-trace.test.mjs`/`sol-evolve.test.mjs` — engage===true pass's genome-link line ts <= live-pass line's ts |
| PROP-012b | 2 | true | **proved** | node:test + fast-check | `sol-evolve.test.mjs` — multi-pass nearest-preceding timestamp-only attribution (2 distinct genome_ids, interleaved WAIT pass); structural no-market/task-field-comparison test; fast-check randomized multi-pass sequences |
| PROP-013 | 2 | true | **proved** | node:test + fast-check | `sol-evolve.test.mjs` — row-gate (source/sig/confirmed); **WIN(+0.5)+LOSS(-0.3) -> realized_usdc===0.2 EXACTLY** (explicit net_usdc-vs-earn_usdc guard); fast-check randomized mixed ledger |
| PROP-014 | 0 | true | **proved** | node:test (import-identity) | `sol-evolve.test.mjs` — `assert.equal(evaluatePromotion, evaluatePromotionDirect)` (reference equality) + fixture-parity replay |
| PROP-015 | 1 | true | **proved** | node:test (temp git repo, `git show --stat`) | `sol-evolve.test.mjs` — promote() commits ONLY the SOL canonical baseline-genome.json path |
| PROP-015b | 0 | true | **proved** | node:test (import-identity) | `sol-evolve.test.mjs` — `assert.equal(promote, promoteDirect)` (reference equality) |
| PROP-016 | 2 | true | **proved** | node:test + fast-check | `sol-genome.test.mjs` — instanceOverridePath differs per ANICCA_HOME (fast-check randomized homes); cross-instance write isolation |
| PROP-017 | 2 | true | **proved** | node:test (real `execFileSync` subprocess of `resolve-max-spend.sh`) | `sol-max-spend.test.mjs` — attacker-preset SOL_TRADE_MAX_SPEND=999999 -> resolved value still exactly `"0.25"` (3/3 cases incl. genome-shaped env attack) |
| PROP-018 | 0 | true | **proved** | node:test (static source-text contract) | `sol-source-contract.test.mjs` — no `eval(`/`new Function(`/variable-derived `import(` in sol-genome/sol-gate/sol-trace/sol-evolve/sol-gate-cli.mjs; malformed genome value never reaches a code-execution sink |

20/20 required proof obligations discharged with real, substantive test evidence (verified by
reading each test body in this session, not just trusting the PASS count — see PROP-009, PROP-013,
PROP-017, PROP-012b, PROP-014/015b assertion excerpts reviewed directly). No proof harness needed
writing from scratch: every PROP already had dedicated coverage from Phase 2 (GREEN) plus the
FIND-fix commit `42b35c6`. No obligation is Tier 3; no Tier 3 tool was needed or degraded-from.

## Money-safety-critical PROPs — extra scrutiny (per task instruction)

- **PROP-009** (paper-only, HARD dev-safety): `isLiveEnabled(env)` returns `env.SOL_GATE_LIVE_ENABLE === "1"` literally (strict equality, no coercion). Grepped the entire worktree: `SOL_GATE_LIVE_ENABLE` is compared against `"1"` in exactly one production line (`sol-gate.mjs:32`) and never *assigned* `"1"` anywhere outside test fixtures. `decideEngagement`'s `engage` field is `liveEnabled === true && wouldEngage === true` — structurally two-gated.
- **PROP-004/PROP-017** (forbidden-cap / hard-spend-cap): `FORBIDDEN_CAP_KEYS = ["SOL_TRADE_MAX_SPEND"]` is stripped at every genome production site (`loadGenome`, `mutate`, `genomeId`'s hashing input). Independently, `resolve-max-spend.sh` is a single `echo "0.25"` with **zero env reads** — confirmed by reading the file (10 lines) and by the real subprocess test (PROP-017) proving an attacker-preset env var has zero effect.
- **PROP-013** (net_usdc summation, win-or-loss): `summarizeByGenomeSol` accumulates `Number(row.net_usdc || 0)`, never `row.earn_usdc`. Explicit win+loss numeric fixture (`+0.5` and `-0.3` -> `0.2`) is in the suite and passes.
- **PROP-014/015/015b** (evolve reuse): `sol-evolve.mjs` line 34 imports `evaluatePromotion, promote, readTrace, buildGenomeIndex` from `../../lib/evolve.mjs` and re-exports them unchanged (line 37) — no local reimplementation exists anywhere in the file. Reference-equality tests confirm this at runtime, not just at the source-text level.
- **PROP-012b** (attribution): `attributeGenomeIdSol` compares `traceLineTs <= ledgerRow.ts` only — no market/task/mint field is read from either argument. Confirmed by direct source read and by the dedicated "does NOT compare any market/task/mint field" test.

## Degradation notes

None required. All Tier 0/1/2 tools were available; no Tier 3 obligation exists for this feature.

## Summary

- Required obligations: 20
- Proved: 20
- Failed: 0
- Skipped: 0
- Deferred: 0
- Fresh test totals this session: 89/89 (SOL new) + 9/9 (bash) + 73/73 (regression baseline) = all green, 0 regressions.
