---
sprintNumber: 1
feature: self-improve-real-ledger
scope: Per-instance ledger path resolution (lib/ledger_reader.py), Hyperliquid mirror-sync (is_confirmed/is_profitable split), realized-ledger promotion gate (lib/gate_math.py new pure functions, lib/promotion_history.py, lib/promote_gate.py's realized_gate param), end-to-end wiring (promote_gate_run.py, scope_guard.py DENYLIST_MODULES), and honest data_source tagging (evaluator.py).
negotiationRound: 1
status: approved
criteria:
  - id: CRIT-001
    dimension: spec_fidelity
    description: Group RL-ID's per-instance path resolution (resolve_ledger_path's ANICCA_HOME/file-relative/unresolved priority, REQ-RL1-4) matches behavioral-spec.md exactly, and the cross-instance-leak-is-impossible property (INV-RL1) is proven by construction against two distinct temp instance bodies.
    weight: 0.2
    passThreshold: test_ledger_resolution.py's PROP-RL-ID1/ID2/ID3/ID4/ID5/ID7 all pass (ANICCA_HOME-priority resolution, file-relative default shape, zero cross-contamination between two distinct ANICCA_HOME-scoped ledgers, explicit path= argument ALWAYS overriding resolve_ledger_path's own computation per REQ-RL2 — PROP-RL-ID4, no import-time path caching across two env-mutated calls, resolved/resolution_source present and correct in both the ANICCA_HOME-set and unset cases), AND the pre-existing test_realized_summary_default_path_points_at_the_real_earn_ledger_location (PROP-RL-ID6) remains byte-identical and green when re-run with ANICCA_HOME unset.
  - id: CRIT-002
    dimension: edge_case_coverage
    description: Every REQ-RL8-11 pure gate_math function (realized_window_split's midpoint arithmetic, is_worsening_trend's strict inequality, realized_trend_blocks' and data_realism_gap's full truth tables including the EDGE-RL1/RL4 "insufficient data never fires" case) and REQ-RL5/RL6's is_confirmed/is_profitable Hyperliquid-losing-row split are covered end to end.
    weight: 0.2
    passThreshold: test_realized_gate.py's PROP-RL-GATE2/GATE3/GATE4 (window split even+odd+out-of-window rows, 8-combination worsening-trend truth table, both data_realism_gap contradiction cases plus the sufficient=False vacuous-pass case) and test_ledger_resolution.py's PROP-RL-MIR1 and PROP-RL-MIR2 (Hyperliquid win recognized, Hyperliquid/EVM/Solana confirmed-loss rows split correctly between is_confirmed=True and is_profitable=False) all pass.
  - id: CRIT-003
    dimension: implementation_correctness
    description: decide_promotion's new realized_gate parameter enforces REQ-RL7's unconditional resolved=False block and REQ-RL18's None-vacuous-pass default side by side (removing any ambiguity between the two None-ish states, per spec-review F-4), REQ-RL13a's canonical 13-key realized_gate schema is produced, REQ-RL12's last_promotion_ts picks the latest matching commit, and REQ-RL13's escalation record is written with the documented keys before decide_promotion returns its blocking verdict.
    weight: 0.2
    passThreshold: test_realized_gate.py's PROP-RL-GATE1, PROP-RL-GATE-NONE, PROP-RL-GATE5, PROP-RL-GATE6, and test_wiring.py's realized_gate-schema test (asserting compute_realized_gate's returned key set equals REQ-RL13a's exact 13 keys, no more, no fewer) all pass.
  - id: CRIT-004
    dimension: structural_integrity
    description: promote_gate_run.py's three decide_promotion call sites (REQ-RL17) are ALL wired with an explicit realized_gate= keyword argument (no orphan 2-arg/3-arg bare form survives), and scope_guard.py's DENYLIST_MODULES (REQ-RL19) is extended to close the exact F-5 bypass this feature's own new module names create, without dropping any pre-existing entry.
    weight: 0.2
    passThreshold: test_wiring.py's PROP-RL-WIRE1 (ast-scan of promote_gate_run.py's own source: every Call to decide_promotion carries a realized_gate keyword) and test_denylist_rl.py's PROP-RL-SAFE1 (DENYLIST_MODULES is a strict superset of the pre-feature snapshot AND now contains ledger_reader/is_profitable/resolve_ledger_path/is_confirmed/realized_summary/promotion_history/last_promotion_ts/realized_gate, plus the F-5 executable-bypass-reproduction asserting scan_denylisted_imports returns non-empty for both `from lib.ledger_reader import is_profitable` and the `import lib.ledger_reader as lr; lr.is_profitable(row)` alias form), test_denylist_rl.py's PROP-RL-SAFE2 (static scan: no function added by this feature opens earn-ledger for "w"/"a" — REQ-RL20), and PROP-RL-SAFE3 (static scan: zero wallet-key/env-secret references in any touched file — REQ-RL21) ALL pass and remain pass conditions for this sprint (SAFE2/SAFE3 legitimately pre-pass at RED as non-regression invariants, disclosed in the RED log; they gate the sprint regardless), AND PROP-RL-WIRE2 (the FULL pre-existing 44-test suite — whose tests call decide_promotion WITHOUT realized_gate — re-runs green with assertions unmodified, proving realized_gate=None behaves as "no constraint" per REQ-RL18; named here as its own sprint pass condition, not merely bundled into CRIT-006's post-merge regression run), AND (REQ-RL17 second half — a judgment check the Phase-3 fresh adversary MUST perform, carried as explicit prose because it is not an automatable pytest assertion) the Phase-3 implementation review verifies by reading promote_gate_run.py that the value bound to realized_gate= at EACH of the three call sites is genuinely sourced from the compute_realized_gate(...) helper over the resolved ledger — NEVER a hardcoded literal, stub dict, or constant that would satisfy PROP-RL-WIRE1's keyword-presence scan while bypassing real data; a stubbed binding at ANY call site is a BLOCKING Phase-3 finding and fails this criterion.
  - id: CRIT-005
    dimension: verification_readiness
    description: evaluator.py's data_source tagging (REQ-RL14) never overclaims a real-data replay that does not exist (REQ-RL15's honesty requirement) — combined_score's own numeric computation is byte-identical regardless of which data_source value is reported, and no file under skills/earn/self-improve/** ever asserts data_source == "real".
    weight: 0.1
    passThreshold: test_realized_gate.py's PROP-RL-EVAL1 (mocking lib.ledger_reader.confirmed_net_series's row count below vs at/above MIN_REALIZED_ROWS_FOR_TREND flips data_source between "fixture" and "fixture+realized-crosscheck" while combined_score's numeric value is identical in both calls) and PROP-RL-EVAL2 (repo-wide grep for the bare string pattern data_source.*==.*"real" under skills/earn/self-improve/** returns zero matches) both pass — PROP-RL-EVAL2 is a static invariant expected to already hold in the RED baseline (nothing in the repo asserts the forbidden literal yet, mirroring hl-realized-pnl CRIT-005's own precedent for non-regression checks that legitimately pass before implementation) and is NOT counted against the "new tests must fail" rule for that reason, disclosed explicitly in the RED-phase evidence log.
  - id: CRIT-006
    dimension: verification_readiness
    description: The Tier-2 live E2E proof (PROP-RL-LIVE1/2/3) that this feature's resolved-path + gate wiring actually functions against claude-p's OWN real, non-fixture ledger (30 rows, confirmed live 2026-07-09) — not merely against synthetic fixtures — is executed from the correct locus and evidenced with real artifacts, per EDGE-RL5a's structural constraint that the feature's own dev worktree has no skills/earn/state/ directory at all.
    weight: 0.1
    passThreshold: PROP-RL-LIVE1 (resolve_ledger_path() with ANICCA_HOME unset resolves to claude-p's real earn-ledger.jsonl and realized_summary's realized_net_usd matches an independently hand-computed sum), PROP-RL-LIVE2 (a hand-crafted candidate run through promote_gate_run.py's real, non-mocked main() against claude-p's real ledger plus a disposable tmp_path git clone produces the hand-predicted gate outcome, including an unconditional block when resolved is forced False via an isolated empty HOME), and PROP-RL-LIVE3 (one real run_evolve.sh execution with ANICCA_HOME unset logs a resolved:true/resolution_source:"file_relative_default" OBSERVE line) are ALL executed from the merged ~/anicca MAIN checkout AFTER this feature merges — NEVER from .worktrees/self-improve-real-ledger/ — with raw response/log/verdict/escalation JSON files saved under evidence/ as the fresh artifact (not a prose claim), AND the full regression table (44 self-improve + 42 hl-trade + ledger.test.mjs + ledger.test.js) is re-run green in that same post-merge run.
---

# Sprint 1 Contract — self-improve-real-ledger

## CRIT-001 — spec_fidelity

`resolve_ledger_path` is the single new entrypoint every downstream REQ-RL* depends on, and its
three-tier priority (explicit `ANICCA_HOME` env override → `__file__`-relative rsync-tree default
→ the one genuine "cannot determine identity" case) is the exact fix for Gap 1's cross-instance
leak. `test_ledger_resolution.py` proves:

- PROP-RL-ID1: `resolve_ledger_path(env={"ANICCA_HOME": "/tmp/x"})` returns EXACTLY
  `("/tmp/x/skills/earn/state/earn-ledger.jsonl", True, "anicca_home_env")` — the money-safety
  fix's most direct case.
- PROP-RL-ID2: with no `ANICCA_HOME` (`env={}`), the returned path is computed relative to
  `ledger_reader.py`'s OWN `__file__` and lands on `.../earn/state/earn-ledger.jsonl`,
  `resolution_source == "file_relative_default"`.
- PROP-RL-ID3 (INV-RL1's money-safety capstone): two temp directories shaped exactly like real
  instance bodies, each with distinct ledger content, resolved via two distinct `ANICCA_HOME`
  values, are read back through `realized_summary(path=resolved_path)` and NEVER cross-contaminate
  — instance A's content is never visible through instance B's resolved path or vice versa. This
  is the literal reproduction of the bug `ledger_reader.py`'s own pre-feature module docstring
  discloses (Gap 1: a single hardcoded `DEFAULT_LEDGER_PATH` reads claude-p's ledger from every
  rsynced instance).
- PROP-RL-ID5: `realized_summary()` called twice in the same test, with `ANICCA_HOME` monkeypatched
  to two different values between calls (no module reload), resolves and reads TWO DIFFERENT
  paths — proving REQ-RL3's "fresh resolution on every call, never a frozen constant" property.
- PROP-RL-ID7: `realized_summary()`'s returned dict carries `resolved`/`resolution_source` keys
  with the values REQ-RL4 documents, in both the `ANICCA_HOME`-set and unset cases (the unset case,
  run from this feature's own worktree, correctly degrades to EDGE-RL5a's shape: `resolved: True`,
  `resolution_source: "file_relative_default"`, `row_count`-equivalent zero, because
  `skills/earn/state/` does not exist in a worktree checkout — NOT a resolution failure).
- PROP-RL-ID6 (regression, byte-identical, UNMODIFIED): the pre-existing
  `test_realized_summary_default_path_points_at_the_real_earn_ledger_location` in
  `test_ledger_reader.py` must still pass with `ANICCA_HOME` unset — REQ-RL3's requirement that
  `DEFAULT_LEDGER_PATH` keeps working for any caller referencing the module attribute directly.

## CRIT-002 — edge_case_coverage

The realized-ledger promotion gate's entire money-safety argument is pure arithmetic over
already-filtered `(ts, net_usdc)` pairs (REQ-RL8-11) plus the confirmed/profitable line-level
split that feeds it (REQ-RL5/RL6). `test_realized_gate.py` and `test_ledger_resolution.py` prove:

- PROP-RL-GATE2: `realized_window_split` splits a hand-crafted row list at the temporal MIDPOINT
  of `[window_start_ts, window_end_ts)` for both an even (4-row) and odd (5-row) count, correctly
  summing each half plus the whole window, AND excludes rows whose `ts` falls outside the window
  entirely from `row_count`.
- PROP-RL-GATE3: `is_worsening_trend`'s strict-less-than (equal halves is NOT worsening) and
  `realized_trend_blocks`' full 8-combination truth table
  (`window_net_usd` sign × `worsening` × `sufficient`) match REQ-RL9/RL10's stated AND exactly —
  mirrors `test_reward_hacking_tripwire.py`'s own truth-table style for this codebase.
- PROP-RL-GATE4: `data_realism_gap` fires for case (a) (`mean_realized <= 0 < mean_backtest`,
  `sufficient=True`) and case (b) (`mean_realized > 0`, backtest `>3x` it, `sufficient=True`), does
  NOT fire at the exact 3x boundary (strict `>`, reusing `is_implausible_jump`'s own boundary
  contract), and — critically — does NOT fire under EITHER case when `sufficient=False`, proving
  EDGE-RL1/RL4's "a quiet or brand-new instance is never mistaken for a losing one" guarantee.
- PROP-RL-MIR1/MIR2: `is_profitable` recognizes a well-formed Hyperliquid win
  (`chain=="hyperliquid" AND fill_tid is not None AND confirmed is True`, mirrored verbatim from
  `ledger.mjs::isProfitable`'s CURRENT implementation) and rejects it when any one of
  `fill_tid`/`confirmed`/`chain` is missing or wrong; `is_confirmed` recognizes a confirmed LOSING
  row (`net_usdc < 0`, otherwise well-formed, one fixture per chain: EVM/Solana/Hyperliquid) that
  `is_profitable` correctly rejects for the sign alone — proving REQ-RL6's DRY re-expression
  (`is_profitable = is_confirmed and net_usdc > 0`) actually gives RL8-11's trend/loss detection
  visibility into confirmed losses `is_profitable` alone structurally cannot report.

## CRIT-003 — implementation_correctness

`decide_promotion`'s new `realized_gate` parameter is the single seam that lets REAL per-instance
data override an otherwise fixture-passing candidate, and REQ-RL13a's canonical schema is the one
written contract both `decide_promotion` and `promote_gate_run.py`'s escalation check consume by
exact key name.

- PROP-RL-GATE1: `decide_promotion(assessment, "PASS", realized_gate={"resolved": False, ...})`
  returns `promote: False` even when `assessment` is fully eligible and the adversary said PASS —
  REQ-RL7's unconditional block, independent of every pre-existing deterministic gate.
- PROP-RL-GATE-NONE (spec-review F-4's disambiguation): the SAME assessment+adversary-PASS inputs,
  run twice in one test, produce `promote: True` with `realized_gate=None` (REQ-RL18's vacuous
  pass — the 44 pre-existing tests' calling convention) and `promote: False` with
  `realized_gate={"resolved": False, ...}` (REQ-RL7's unconditional block) — removing any
  ambiguity between "no constraint given" and "constraint given and failed."
- PROP-RL-GATE5: `lib.promotion_history.last_promotion_ts` returns the LATEST matching commit's
  unix timestamp when ≥2 real commits (real `git init`/`git commit` in a throwaway `tmp_path` repo,
  not mocked) match `lib/promote.py`'s own `"feat(self-improve): promote candidate"` prefix scoped
  to a given path, and returns `None` when zero such commits exist (EDGE-RL3's "no current
  generation to measure a trend against yet").
- PROP-RL-GATE6: a synthetic blocking `realized_gate` (`trend_blocks=True`) passed directly to
  `promote_gate_run.py`'s escalation-writing helper produces
  `<run_dir>/realized_gate_escalation.json` containing `reason`/`window_net_usd`/`worsening`/
  `data_realism_gap`/`candidate_path` BEFORE any promotion verdict is returned (REQ-RL13).
- Schema test (`test_wiring.py`): `promote_gate.compute_realized_gate(...)`'s returned dict has
  EXACTLY REQ-RL13a's 13 keys — `resolved, resolution_source, ledger_path, row_count, sufficient,
  window_net_usd, first_half_net_usd, second_half_net_usd, worsening, trend_blocks,
  realism_gap_blocks, window_start_ts, window_end_ts` — no more, no fewer, over a constructed
  tmp-git-repo + tmp-ledger scenario (this function and the exact signature it is called with here
  do not exist yet at RED-phase time; Phase 2b implements `compute_realized_gate` to satisfy this
  interface, which composes REQ-RL1's env-injection convention with REQ-RL12's repo-cwd need).

## CRIT-004 — structural_integrity

No REQ-RL7-13 gate logic is worth anything if the ONE real call site
(`promote_gate_run.py::main`) can still silently omit it, or if `scope_guard.py`'s denylist doesn't
actually cover this feature's own new harness-file names — the exact F-5 finding this feature's
own spec-review already caught once.

- PROP-RL-WIRE1: `ast.parse`-based scan of `promote_gate_run.py`'s own source text walks every
  `Call` node targeting `decide_promotion` and asserts EVERY ONE carries a `realized_gate` keyword
  argument — today all three of `main()`'s call sites (the `not eligible_for_adversary_review`
  short-circuit, the adversary-unavailable/errored branch, and the adversary-succeeded branch) omit
  it entirely, so this test currently finds 3 violations and correctly FAILS.
- PROP-RL-SAFE1: `scope_guard.DENYLIST_MODULES` (after this feature's edit) is asserted to be a
  STRICT SUPERSET of a committed pre-feature snapshot (no entry dropped/renamed) AND to contain
  every REQ-RL19-listed new string (`ledger_reader`, `is_profitable` Python form,
  `resolve_ledger_path`, `is_confirmed`, `realized_summary`, `promotion_history`,
  `last_promotion_ts`, `realized_gate`) — plus the F-5 EXECUTABLE bypass reproduction:
  `scan_denylisted_imports("from lib.ledger_reader import is_profitable", DENYLIST_MODULES)` and
  `scan_denylisted_imports("import lib.ledger_reader as lr\nlr.is_profitable(row)",
  DENYLIST_MODULES)` both currently return `[]` (the entries don't exist yet) and MUST return a
  non-empty match list once REQ-RL19 lands.

## CRIT-005 — verification_readiness (honest data_source tagging)

`evaluate()`/`evaluate_stage2()`'s `data_source` key is a purely cosmetic/reporting addition —
`combined_score`'s own computation is 100% unchanged fixture-derived arithmetic regardless of which
value is reported (REQ-RL14/RL15's honesty requirement: this feature never claims a row-level real-
data replay it does not build).

- PROP-RL-EVAL1: mocking `lib.ledger_reader.confirmed_net_series`'s row count below
  `MIN_REALIZED_ROWS_FOR_TREND` (6) versus at/above it flips `data_source` between `"fixture"` and
  `"fixture+realized-crosscheck"` while `combined_score`'s NUMERIC VALUE is identical across both
  calls (proving the score computation path itself is untouched).
- PROP-RL-EVAL2: a repo-wide grep for the bare pattern `data_source.*==.*"real"` under
  `skills/earn/self-improve/**` returns zero matches. **Disclosure** (mirrors hl-realized-pnl
  CRIT-005's own precedent for a non-regression check that legitimately holds before
  implementation exists): this specific assertion is expected to ALREADY PASS in the RED baseline
  — there is nothing in the repo asserting the forbidden literal yet, precisely because REQ-RL14
  is not implemented. It is written now as a permanent CI-style safety net (so it starts failing
  the moment any future change violates REQ-RL15's honesty constraint), not as a proof that a gap
  currently exists — and is excluded from the "every new test must fail red" rule for that
  documented reason.

## CRIT-006 — verification_readiness (live E2E capstone)

Fixture-only proof cannot show this feature's resolved-path + gate wiring actually functions
against a REAL, non-fixture ledger — the entire point of this feature per its own Purpose section.
EDGE-RL5a is a structural fact, not a preference: `.worktrees/self-improve-real-ledger/` (like
every worktree) has no `skills/earn/state/` directory at all (`skills/*/state/` is gitignored), so
`__file__`-relative resolution computed from a worktree copy of `ledger_reader.py` degrades to
`resolved: true, row_count: 0` — structurally incapable of exercising PROP-RL-LIVE1/2's nonzero
real-data assertions. Executing the live tier from a worktree would therefore not merely be
inconvenient, it would silently produce a false-green (a `resolved: true` result that never
actually touched real data) for the single proof obligation this feature exists to satisfy. Pass
condition: PROP-RL-LIVE1 (real path resolution + hand-verified `realized_net_usd` against claude-p's
own 30-row ledger), PROP-RL-LIVE2 (a real, non-mocked `promote_gate_run.py::main()` run against a
disposable tmp_path git clone, including the forced-`resolved=False` unconditional-block case), and
PROP-RL-LIVE3 (one real `run_evolve.sh` execution logging a correct OBSERVE line) are ALL executed
from the merged `~/anicca` main checkout post-merge, with raw response/log/verdict/escalation JSON
artifacts saved under `evidence/` — and the full regression table (44 self-improve + 42 hl-trade +
`ledger.test.mjs` + `ledger.test.js`) is re-run green in that same post-merge session, not merely
claimed.

## Cross-criterion note

CRIT-003's PROP-RL-GATE1/GATE-NONE and CRIT-004's PROP-RL-WIRE1 are both grounded in
`decide_promotion`'s `realized_gate` parameter, but test non-overlapping properties: CRIT-003 is
"does the parameter's VALUE correctly gate a single decision," CRIT-004 is "is the parameter
ALWAYS SUPPLIED at the one real production call site" — the same deliberate non-overlap the
`hl-realized-pnl` sprint contract already established for its own PROP-007 citation (checkpoint
correctness vs. composition-root ordering).
