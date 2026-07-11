# Verification Report — franklin-alwaysact-skill-router (VCSDD Phase 5, formal hardening)

Feature: Franklin's "never waits, always picks exactly one positive-EV earning action" always-act
router (REQ-501..REQ-513, `specs/behavioral-spec.md`). Worktree
`/Users/operator/anicca/.worktrees/alwaysact-impl`, branch `feature/franklin-alwaysact-skill-router`,
HEAD `39a9c217`. Phase 3 impl-review PASSed at iteration 4 (0 blocking,
`reviews/impl/iteration-4/output/verdict.json`).

**Language profile**: JavaScript/ESM, `node --test` (Node's built-in test runner) + `fast-check`
(the JS-ecosystem property-testing tool the project's own `specs/verification-architecture.md`
names as its Tier 1 equivalent of `hypothesis`/`kani`). No `kani`/kani-style bounded model checker
applies (not Rust); no Tier 3 obligation is declared for this feature (see
`verification-architecture.md`'s own "Tier 3: none required" note — no cryptographic, consensus, or
concurrency-critical logic is introduced; the underlying money-safety proofs this feature reuses
unchanged, `MAX_SPEND`/`earn-guard.mjs`/`catalog-gate.mjs`, are out of this feature's re-verification
scope by design).

`state.json`'s `proofObligations` array is empty — this feature's obligation tracking lives in
`specs/verification-architecture.md`'s "Proof Obligations" table (33 `PROP-5xx` rows) + this report,
the same pattern the prior `self-improve-real-ledger` Phase 5 pass used.

## Tool availability

| tool | status |
|---|---|
| `node --test` | available (v25.6.1, this session) |
| `fast-check` | available (`^4.8.0`, `~/anicca/package.json`), used by `always-act-router.test.mjs` only among this feature's suites |
| `kani` (Rust BMC) | N/A — not applicable, this codebase is JS/ESM, not Rust |
| `hypothesis` (Python) | N/A — not applicable to this feature's `runtime/loop/**` diff |
| `semgrep` | available (`/opt/homebrew/bin/semgrep` v1.168.0) — see `security-report.md` |

No degradation was needed: every obligation this table declares Tier 0/1/2 for was discharged at
its declared tier with the declared tool (`node --test` exhaustive-case harnesses for Tier 0/2,
`fast-check` properties for Tier 1). Tier 3 is correctly declared "none required" by Phase 1b and
this session found no reason to revise that.

## Fresh test evidence (this session, from the worktree, HEAD `39a9c217`)

```
$ cd runtime/loop && npm test
ℹ tests 183
ℹ pass 183
ℹ fail 0
ℹ cancelled 0
ℹ skipped 0
ℹ todo 0
```
Raw: `proof-harnesses/full-suite-run.txt`. **First run this session hit the pre-existing, documented
`integration.test.mjs` `ENOTEMPTY` teardown-race flake** (2 of 183 failing — `PROP-021(a)`/`PROP-021(b)`,
`errno: 66`/`ENOTEMPTY` on `/tmp/anicca-loop-test-*` rmSync during test teardown; raw:
`proof-harnesses/full-suite-run-attempt1-flake.txt` was not separately retained but the failure
signature is quoted verbatim above and matches `contracts/sprint-1.md` CRIT-010's own pre-disclosed
description character-for-character). Per that contract's own stated allowance ("adversary re-runs
the SAME command up to 2 more times and confirms at least one clean 183/183 run"), a second run this
session produced the clean 183/183 above — captured in `proof-harnesses/full-suite-run.txt`. This
flake is orthogonal to this feature: it is in `integration.test.mjs` (a pre-existing, unmodified test
file, `PROP-021`, not `PROP-5xx`), a child-process-teardown timing race unrelated to the always-act
router's own logic. No `always-act-*.test.mjs`/`go-live.test.mjs` test has ever failed in this
session, across all runs.

```
$ node --test __tests__/always-act-router.test.mjs __tests__/always-act-wire-seam.test.mjs \
    __tests__/always-act-nojudgment.test.mjs __tests__/always-act-reroute.test.mjs __tests__/go-live.test.mjs
ℹ tests 63   ℹ pass 63   ℹ fail 0
```
(30 + 3 + 1 + 25 + 4 = 63, individually re-confirmed per file.) Raw: `proof-harnesses/target-feature-run.txt`.

```
$ node --test __tests__/address-classify.test.mjs __tests__/balance-solana.test.mjs __tests__/brain.test.mjs \
    __tests__/daemon-script-franklin-routing.test.mjs __tests__/earn-slot.test.mjs \
    __tests__/franklin-plist-config.test.mjs __tests__/integration-solana-tier.test.mjs \
    __tests__/liquidity.test.mjs __tests__/prompt.test.mjs __tests__/resolve-identity.test.mjs \
    __tests__/self-eval.test.mjs __tests__/wallet-address-solana.test.mjs
ℹ tests 94   ℹ pass 94   ℹ fail 0
```
Raw: `proof-harnesses/sweep-regression-run.txt` — the "additional sweep" CRIT-010 requires, confirming
zero regression outside the target-feature suites.

## fast-check reproducibility

`always-act-router.test.mjs` is the only file in this feature's suite (and the only file in
`runtime/loop/__tests__/` at all — confirmed by `grep -l fast-check __tests__/*.mjs`) that imports
`fast-check` (`import fc from 'fast-check'`). None of its ~14 `fc.assert(fc.property(...))` call
sites pass an explicit `{ seed, path }` option — this is **not itself a defect**: fast-check's own
design generates a fresh random seed per run but always prints `Deterministically reproduce with
fc.assert(..., {seed: X, path: "Y", endOnFailure: true})` in its failure output the moment a property
fails, which is fast-check's standard reproducibility convention (reproduce-on-demand from the
printed seed, not a pre-pinned seed on every green run). No other file in this repo uses fast-check,
so there is no established repo-wide "pin an explicit seed" convention to compare against — this
feature's usage is consistent with fast-check's own out-of-the-box default and with the only
precedent this repo has (none). All fast-check properties in this suite passed clean in every run
this session (see `always-act-router` counts above), so no counterexample/seed was ever produced to
verify the reproduction mechanism end-to-end; this is a documented, honest gap, not a fabricated
confirmation.

## Proof Obligations (33 rows, `specs/verification-architecture.md`)

| ID | Tier | Required | Status | Mechanism |
|---|---|---|---|---|
| PROP-501a | 2 | true | **discharged** | `always-act-reroute.test.mjs::"PROP-501a: identity MISMATCH..."` — exhaustive case |
| PROP-501b | 2 | true | **discharged** | same file, 2 named tests (`flag unset` / `flag malformed`) |
| PROP-501c | 2 | true | **discharged** | same file, `"PROP-501c: identity MATCH + flag \"1\"..."` |
| PROP-502a | 1 | true | **discharged** | `always-act-router.test.mjs` — literal fixture + `fc.property(fc.string(), ...)` |
| PROP-502b | 1 | true | **discharged** | same file, `fc.property(fc.dictionary(...))` over generated registries |
| PROP-502c | 1 | true | **discharged** | same file, literal fixture against the CURRENT `skills/registry.json` |
| PROP-502d | 2 | true | **discharged** | `always-act-reroute.test.mjs::"PROP-502d (REAL wake)..."` — real spawned wake via `ALWAYS_ACT_REGISTRY_PATH_OVERRIDE` fixture |
| PROP-503a | 1 | true | **discharged** | `always-act-router.test.mjs` — `fc.property(fc.double(...), fc.double(...))` boundary sweep |
| PROP-503b | 2 | true | **discharged** | same file, exhaustive-case |
| PROP-504a | 1 | true | **discharged** | same file — pure-helper `fc.property` |
| PROP-504b | 2 | true | **discharged** | `always-act-wire-seam.test.mjs` — 3 tests, REAL `thinkProxy` with only `httpPost` mocked |
| PROP-505a | 1 | true | **discharged** | `always-act-reroute.test.mjs` Row 2 / Row 4 + `always-act-router.test.mjs`'s `PROP-511a` bounded-exhaustive property |
| PROP-506a | 1 | true | **discharged** | `always-act-reroute.test.mjs` Row 5 — real constructed tool schema `enum` assertion |
| PROP-506b | 1 | true | **discharged** | same file, Row 1 |
| PROP-506c | 2 | true | **discharged** | same file, 2 named tests (`economy/gig` / `economy/lending`) |
| PROP-506d | 2 | true | **discharged (same code branch as PROP-506f, no dedicated menu-size-1 fixture)** | `index.mjs:824-831`'s `rerouteTargets.length === 0` branch does not distinguish "no other slot exists" from "every other slot is risk:capital" — both hit the identical escalation code path PROP-506f's test exercises and asserts (`requests.length===1`, zero additional `think()`, immediate escalation). No test uses a literal 1-element menu fixture; behaviorally equivalent coverage, honestly flagged as not a dedicated case |
| PROP-506e | 2 | true | **discharged** | `always-act-router.test.mjs` — literal + property + current-registry fixture (`earn/sol-trade`/`hl_trade`/`token_launch`/`earn/polymarket-trade`/`yield` never reroute targets) |
| PROP-506f | 2 | true | **discharged** | `always-act-reroute.test.mjs::"PROP-506f (empty-safe-set-escalates)"` |
| PROP-506g | 2 | true | **discharged** | same file, Row 9 |
| PROP-507a | 1 | true | **discharged** | `always-act-nojudgment.test.mjs::"PROP-507a"` |
| PROP-507b | 0 | true | **discharged** | same file — grep-based static check + independently re-confirmed by hand this session (`grep -n "RegExp\|\.match(\|\.test(" always-act-router.mjs` → 0 matches; only 2 imports, `earn-slot.mjs`/`prompt.mjs`, both pure) |
| PROP-508a | 2 | true | **discharged (via overlapping escalation-path assertions, no single dedicated test)** | Every ESCALATE-terminal test in `always-act-reroute.test.mjs` (Rows 3/4/6/6b/7/9-12, `PROP-502d`, `PROP-506f`) asserts `kind` is one of `router_no_realized_action`/`router_menu_empty` (never `wake`/`narrate`); `PROP-506f`/Row-4-adjacent tests explicitly assert `notEqual(escalated.profitable, true)`. Structurally guaranteed by `writeAlwaysActEscalation` (`index.mjs:899-910`)'s hardcoded `profitable: false, slot: ledgerFields.slot` (never a fabricated success) — verified by direct read |
| PROP-509a | 0 | true | **discharged** | `always-act-reroute.test.mjs::"PROP-509a"` + independently re-run this session: `git diff --name-only 826c7f6 HEAD -- skills/earn skills/_shared/lib/earn-guard.mjs runtime/loop/catalog-gate.mjs` → zero output |
| PROP-509b | 2 | true | **discharged** | same file — real (unmodified) guard fixture, ledger.jsonl preserved-record assertion + harness-failures.jsonl negative control |
| PROP-510a | 1 | true | **discharged** | `always-act-router.test.mjs` — literal + property (`{0,1}` domain echoed verbatim) |
| PROP-511a | 1 | true | **discharged** | same file — `fc.property(fc.array(fc.constantFrom(...)))` bounded-exhaustive over all 3 failure-mode orderings |
| PROP-512a | 1 | true | **discharged** | same file (pure `buildGoLiveRecord`/`shouldRecordGoLive`) + `always-act-reroute.test.mjs` (live `always_act_not_engaged` reason ledgering) + `go-live.test.mjs` (4 tests, real `recordGoLive` end-to-end) |
| PROP-512b | 1 | true | **discharged** | `always-act-router.test.mjs` — 4 literal cases (a/b/c) + 1 property |
| PROP-513a | 2 | true | **discharged** | `always-act-reroute.test.mjs` Row 8 |
| PROP-513b | 2 | true | **discharged** | same file, Row 6 |
| PROP-513c | 2 | true | **discharged** | same file, Row 6b |
| PROP-513d | 1 | true | **discharged (via Row 1/PROP-506b, no separately-named test)** | Row 1 (`PROP-506b`) IS the baseline-attempt-accepts-a-valid-member scenario PROP-513d describes (`currentOfferedSlots === ctx.alwaysActMenu`, valid pick, immediate EXECUTE, no rejection/escalation) — same assertion, not duplicated under a second name |
| PROP-513e | 2 | true | **discharged** | same file, Row 3 (the direct FIND-301 regression test) |

**33/33 required proof obligations discharged.** 30 by a literally-named, dedicated test; 3
(PROP-506d, PROP-508a, PROP-513d) by direct-read + overlapping-test coverage from the SAME code
branch a differently-named sibling obligation already exercises — honestly distinguished above rather
than claimed as separately authored tests. Zero required obligations skipped or failed.

## §2.5 Transition-matrix coverage (behavioral-spec.md, the authoritative exhaustive 12-row table)

Confirmed by direct grep of `always-act-reroute.test.mjs` test titles: Rows 1, 2, 3, 4, 5, 6, 6b, 7,
8, 9, 10, 11, 12 are all present as named tests and all pass (25/25 in that file). This is the full
12-cell attempt-1×attempt-2 product the spec declares exhaustive, plus Row 6b (a PROP-513c variant).

## Summary

All 33 required `PROP-5xx` proof obligations are proved (30 dedicated, 3 via honestly-disclosed
overlapping coverage — see table). Full target-feature suite: 63/63 (`always-act-router` 30,
`always-act-wire-seam` 3, `always-act-nojudgment` 1, `always-act-reroute` 25, `go-live` 4). Additional
regression sweep: 94/94. Combined `npm test`: 183/183 clean on retry (first attempt hit the
pre-existing, pre-disclosed `integration.test.mjs` ENOTEMPTY teardown flake, unrelated to this
feature — documented above, not hidden). No Tier 3 obligation exists (Tier 3 correctly declared "none
required" by Phase 1b). fast-check usage is consistent with the tool's own default
reproduce-on-failure convention; no counterexample was produced this session to exercise that
mechanism (all properties passed). Security hardening (`security-report.md`) and purity-boundary
audit (`purity-audit.md`) are documented separately in this same directory. Ready for Phase 6
convergence.
