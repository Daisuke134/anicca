---
feature: self-improve-real-ledger
phase: 1b
mode: strict
sources:
  - behavioral-spec.md (this feature, same directory) — REQ-RL/INV-RL/EDGE-RL IDs referenced below
  - .vcsdd/features/anicca-self-improve-harness/specs/verification-architecture.md (prior phase) — Purity Boundary Map / Proof Obligations / Test List conventions, PROP-SI-* IDs this feature's own PROP-RL-* IDs sit alongside without duplicating
---

# Verification Architecture — self-improve-real-ledger (Phase 1b)

## Purity Boundary Map

### Pure Core (extends `skills/earn/self-improve/lib/gate_math.py` — no new pure module created, per INV-RL6)

Same invariants as the prior phase's Pure Core: deterministic, referentially transparent, zero
side effects, no `os`/`subprocess`/`pathlib`/`requests`/`urllib`/`socket` imports — verified by the
SAME AST/text import-scan test the prior phase already wrote for `gate_math.py`, re-run (not
re-written) against the file's new, larger contents.

| function | signature | why it is pure | REQ traced |
|---|---|---|---|
| `realized_window_split(rows, window_start_ts, window_end_ts)` | `(Iterable[tuple[float,float]], float, float) → dict` | pure aggregation over an already-injected list of `(ts, net_usdc)` pairs — no file/env access | REQ-RL8 |
| `is_worsening_trend(first_half_net_usd, second_half_net_usd)` | `(float, float) → bool` | trivial strict-less-than comparison | REQ-RL9 |
| `realized_trend_blocks(window_net_usd, worsening, sufficient)` | `(float, bool, bool) → bool` | boolean AND over three injected inputs | REQ-RL10 |
| `data_realism_gap(mean_backtest_net_usd, mean_realized_net_per_row, sufficient, multiple=3.0)` | `(float, float, bool, float) → bool` | pure numeric comparison, delegates to the ALREADY-pure `is_implausible_jump` (REQ-RH2) for its case (b); case (a) is a trivial comparison | REQ-RL11 |

Also pure (mislabeled as "part of an I/O module" only because they live in `lib/ledger_reader.py`
alongside impure functions — same classification anomaly the prior phase's `evaluator.py` already
has for its own arithmetic; noted here for completeness, not moved):

| function | signature | why it is pure | REQ traced |
|---|---|---|---|
| `is_confirmed(line)` | `(Optional[dict]) → bool` | pure predicate over an already-provided dict, zero I/O | REQ-RL6 |
| `is_profitable(line)` | `(Optional[dict]) → bool` | `is_confirmed(line) and net_usdc > 0`, pure | REQ-RL5, REQ-RL6 |

### Effectful Shell

| module / function | primary I/O surface | REQ traced |
|---|---|---|
| `lib/ledger_reader.py::resolve_ledger_path` | reads `env`/`os.environ` and this module's own `__file__`; NO ledger file access itself | REQ-RL1, REQ-RL2 |
| `lib/ledger_reader.py::read_ledger` / `realized_summary` | reads `earn-ledger.jsonl` (read-only, unchanged from prior phase); now calls `resolve_ledger_path()` fresh per call instead of a frozen constant | REQ-RL3, REQ-RL4 |
| `lib/promotion_history.py::last_promotion_ts` (NEW file) | subprocess `git log --grep -- <path>` (mirrors `lib/promote.py`'s own "subprocess confined to a small effectful module" convention) | REQ-RL12 |
| `lib/promote_gate.py::compute_realized_gate` (NEW function, this feature) | calls `ledger_reader.resolve_ledger_path`/`is_confirmed`-filtered read + `promotion_history.last_promotion_ts`; assembles the pure `gate_math` calls' inputs; itself does the file/git I/O, never the gating math | REQ-RL7-13 |
| `lib/promote_gate.py::decide_promotion` (EXTENDED, existing function) | still pure decision logic — the NEW `realized_gate` param is an already-computed dict passed in by the impure caller, exactly like `adversary_verdict` already is | REQ-RL7, REQ-RL18 |
| `promote_gate_run.py::main` (EXTENDED, existing script) | calls `compute_realized_gate`, writes `realized_gate_escalation.json` when blocked, passes `realized_gate=` to EVERY `decide_promotion` call site | REQ-RL13, REQ-RL17 |
| `evaluator.py::evaluate`/`evaluate_stage2` (EXTENDED, existing functions) | reads the realized ledger (via `ledger_reader`, read-only) ADDITIONALLY to the fixture, to compute `data_source` — the actual `combined_score` computation path is UNCHANGED (still 100% fixture-derived) | REQ-RL14, REQ-RL15 |
| `lib/scope_guard.py::DENYLIST_MODULES` (EXTENDED, existing constant) | no I/O itself; the constant this feature adds new string entries to | REQ-RL19 |
| `run_evolve.sh` | UNCHANGED shell code (REQ-RL16) — its existing subprocess call to `ledger_reader.py`'s `__main__` now benefits from the fixed default transitively | REQ-RL16 |

The pure layer (`gate_math.py`'s new functions + `is_confirmed`/`is_profitable`) forms a fully
deterministic, directly-unit-testable core, exactly mirroring the prior phase's own split. The
effectful shell (`ledger_reader.py`'s I/O half, `promotion_history.py`, `compute_realized_gate`,
`promote_gate_run.py`) snapshots real filesystem/git state into plain data (floats, bools, row
lists) and hands it to the pure layer; it never re-implements the pure layer's gating logic inline.

---

## Proof Obligations

Tier legend (extends the prior phase's three tiers with one new tier this feature specifically
needs): **deterministic** = pure-function pytest/property test, no I/O. **backtest** = integration
test over the synthetic fixture (unchanged meaning from the prior phase). **live** = integration
test against a REAL per-instance ledger file (claude-p's own, or a hand-constructed
temp-`HOME`/temp-`ANICCA_HOME` directory shaped exactly like a real one) — NEW this phase, because
this feature's entire point is behavior that can only be proven against real, not synthetic, ledger
data. **adversary** = fresh-context `vcsdd-adversary` review (unchanged meaning).

| ID | Property (traces to REQ) | Tier | Method |
|---|---|---|---|
| PROP-RL-ID1 | `resolve_ledger_path(env={"ANICCA_HOME": "/tmp/x"})` returns `("/tmp/x/skills/earn/state/earn-ledger.jsonl", True, "anicca_home_env")` (REQ-RL1.1) | deterministic | pytest parametrize over several `ANICCA_HOME` values |
| PROP-RL-ID2 | `resolve_ledger_path(env={})` (no `ANICCA_HOME`) returns a path ending in `.../earn/state/earn-ledger.jsonl` computed relative to `ledger_reader.py`'s own `__file__`, `resolution_source == "file_relative_default"` (REQ-RL1.2) | deterministic | pytest: assert the returned path's directory structure matches `os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(ledger_reader.__file__))))/state/earn-ledger.jsonl` |
| PROP-RL-ID3 | Two DIFFERENT `ANICCA_HOME` values never resolve to the same path (no accidental collision), and NEITHER ever equals the OTHER instance's hardcoded legacy default (the exact cross-instance leak this feature fixes) (REQ-RL1, INV-RL1) | deterministic | pytest: construct two temp dirs shaped like real instance bodies (`<tmp>/instA/skills/earn/state/earn-ledger.jsonl` with content X, `<tmp>/instB/...` with content Y), resolve with `env={"ANICCA_HOME": "<tmp>/instA"}` vs `env={"ANICCA_HOME": "<tmp>/instB"}`, assert `realized_summary` reads back X vs Y respectively — NEVER cross-contaminated |
| PROP-RL-ID4 | An explicit `path=` argument always overrides `resolve_ledger_path()`'s own computation, unchanged from prior behavior (REQ-RL2) | deterministic | pytest: re-run existing `test_ledger_reader.py` calls unmodified (regression, see Regression table) |
| PROP-RL-ID5 | `realized_summary()` called twice with different injected `env` (no module reload) returns summaries for the TWO DIFFERENT resolved paths, proving no import-time caching (REQ-RL3) | deterministic | pytest: monkeypatch `os.environ`/pass `env=` between two calls in the same test |
| PROP-RL-ID6 | `ledger_reader.DEFAULT_LEDGER_PATH` (legacy attribute) still ends with `anicca/skills/earn/state/earn-ledger.jsonl` when this test suite is run from the `~/anicca` checkout with `ANICCA_HOME` unset (REQ-RL3, exact pre-existing assertion, UNMODIFIED) | deterministic | re-run of the EXISTING `test_realized_summary_default_path_points_at_the_real_earn_ledger_location` test, byte-identical, in the Regression table |
| PROP-RL-ID7 | `realized_summary(...)`'s dict has `resolved` and `resolution_source` keys with the expected values for both the `ANICCA_HOME`-set and unset cases (REQ-RL4) | deterministic | pytest parametrize |
| PROP-RL-MIR1 | `is_profitable` returns `True` for a well-formed Hyperliquid-confirmed row (`chain: "hyperliquid", fill_tid: <int>, confirmed: true, net_usdc > 0, external: true`) and `False` when any one of `fill_tid`/`confirmed`/`chain` is missing/wrong (REQ-RL5) | deterministic | pytest, mirrors `ledger.mjs`'s own `isProfitable` HL fixture rows (cross-checked against a `node -e` invocation of the real `ledger.mjs::isProfitable` on the SAME fixture row, proving byte-for-byte behavioral parity, not just a same-shaped Python guess) |
| PROP-RL-MIR2 | `is_confirmed` returns `True` for a confirmed LOSING row (`net_usdc < 0`, otherwise well-formed EVM/Solana/HL confirmation) that `is_profitable` correctly returns `False` for (REQ-RL6) | deterministic | pytest: one fixture row per chain type, asserting the `is_confirmed`/`is_profitable` split |
| PROP-RL-GATE1 | `decide_promotion(assessment, "PASS", realized_gate={"resolved": False, ...})` returns `promote: False` regardless of `assessment`'s own eligibility (REQ-RL7) | deterministic | pytest: reuse `_good_candidate`'s already-eligible assessment fixture from `test_adversary_disapprove.py`, add `resolved: False` |
| PROP-RL-GATE2 | `realized_window_split` splits a 6-row synthetic `(ts, net)` list at the exact temporal midpoint and sums each half correctly, for both an even and an odd row count (REQ-RL8) | deterministic | pytest parametrize |
| PROP-RL-GATE3 | `is_worsening_trend`/`realized_trend_blocks` truth table (8 combinations: `window_net_usd` sign × `worsening` × `sufficient`) matches REQ-RL10's stated AND exactly (REQ-RL9, REQ-RL10) | deterministic | pytest full truth-table, mirrors `PROP-SI-RH4`'s 16-combo style |
| PROP-RL-GATE4 | `data_realism_gap` fires for BOTH case (a) (`mean_realized <= 0 < mean_backtest`) and case (b) (`mean_realized > 0`, backtest `> 3x` it), and does NOT fire when `sufficient=False` regardless of the other inputs (REQ-RL11) | deterministic | pytest parametrize + reuse of `is_implausible_jump`'s own existing boundary tests (strict `>`, not `>=`) |
| PROP-RL-GATE5 | `last_promotion_ts` returns the LATEST matching commit's timestamp when ≥2 promotion commits exist in a throwaway git repo fixture, and `None` when zero exist (REQ-RL12, EDGE-RL3) | deterministic | pytest against a `tmp_path`-initialized real git repo (real `git init`/`git commit`, not mocked — cheap and fully hermetic) |
| PROP-RL-GATE6 | A blocked-by-REQ-RL10-or-RL11 run writes `realized_gate_escalation.json` with the documented keys BEFORE `decide_promotion` returns (REQ-RL13) | deterministic | pytest: call `promote_gate_run.py`'s escalation-writing helper directly with a synthetic blocking `realized_gate`, assert file contents |
| PROP-RL-EVAL1 | `evaluate()`'s `data_source` key is `"fixture"` when the (mocked) realized-row count is below `MIN_REALIZED_ROWS_FOR_TREND`, and `"fixture+realized-crosscheck"` when at/above it — and `combined_score`'s NUMERIC VALUE is IDENTICAL in both cases (proving the score computation itself is untouched, REQ-RL14) | deterministic | pytest: mock `ledger_reader.confirmed_net_series`'s row count, assert `combined_score` unchanged, `data_source` flips |
| PROP-RL-EVAL2 | Repo-wide grep for `data_source.*==.*"real"` (bare, not `"fixture+realized-crosscheck"`) inside `skills/earn/self-improve/**` returns zero matches (REQ-RL15's honesty requirement, no overclaim) | deterministic | CI grep check |
| PROP-RL-WIRE1 | Repo-scan of `promote_gate_run.py`'s own source text: EVERY call to `promote_gate.decide_promotion(` includes a `realized_gate=` keyword argument (no 2-arg or 3-arg bare form) (REQ-RL7, REQ-RL17) | deterministic | pytest: `ast.parse` `promote_gate_run.py`, walk all `Call` nodes targeting `decide_promotion`, assert every one has a `realized_gate` keyword |
| PROP-RL-WIRE2 | The 44 pre-existing tests calling `decide_promotion` WITHOUT `realized_gate` (unit tests targeting pure gate logic in isolation) still pass, `realized_gate=None` behaving as "no constraint" (REQ-RL18) | deterministic | full regression run, see Regression table |
| PROP-RL-SAFE1 | `DENYLIST_MODULES` (after this feature's edit) is a STRICT SUPERSET of the pre-existing tuple (no entry removed or renamed) AND now also contains every REQ-RL19-listed new string (REQ-RL19) | deterministic | pytest: set-difference assertion against a snapshot of the pre-feature tuple (committed as a test fixture literal) |
| PROP-RL-SAFE2 | Static source-text scan of `ledger_reader.py`/`promotion_history.py`/`gate_math.py`'s new functions finds zero `open(..., "w")`/`open(..., "a")` calls whose path argument contains `"earn-ledger"` (REQ-RL20, mirrors PROP-SI-EV7) | deterministic | pytest source-text scan |
| PROP-RL-SAFE3 | Static source-text scan of every file this feature touches finds zero references to `ANICCA_EVM_PRIVATE_KEY`/`ANICCA_SOLANA_PRIVATE_KEY`/`.automaton/wallet.json`/`.automaton/solana.json`/`.blockrun/.solana-session` (REQ-RL21) | deterministic | pytest source-text scan |
| PROP-RL-LIVE1 | Against claude-p's OWN real ledger (`~/anicca/skills/earn/state/earn-ledger.jsonl`, 30 rows, confirmed live 2026-07-09), `ANICCA_HOME` unset, `resolve_ledger_path()` resolves to that EXACT file, and `realized_summary()`'s `realized_net_usd` matches an independently hand-computed sum over its `polymarket-redeem`/`0xwork`/`x402`/`cook` rows (REQ-RL1, RL4) | live | integration test, real file, read-only (never writes) |
| PROP-RL-LIVE2 | A hand-crafted candidate run through `promote_gate_run.py`'s REAL (non-mocked) `main()` against claude-p's real ledger + a temporarily checked-out git history (a disposable `tmp_path` clone, never the live repo) produces the gate outcome REQ-RL7-13 predict by hand-computation, and (when `resolved=False` is forced via an isolated empty `HOME`) blocks unconditionally end-to-end (REQ-RL7, RL17) | live | integration test, disposable git clone, no writes to the real repo |
| PROP-RL-LIVE3 | `run_evolve.sh` executed once for real (small `--iterations`, same as the prior phase's own acceptance run) with `ANICCA_HOME` unset logs a `resolved: true` / `resolution_source: "file_relative_default"` OBSERVE line pointing at claude-p's real ledger path (REQ-RL16) | live | one real, human-zero shell execution; evidence = the run's own log file |
| PROP-RL-GATE-NONE | Side-by-side property (added at spec-review iteration 1, finding F-4): the SAME assessment+adversary-PASS inputs produce `promote: True` with `realized_gate=None` (vacuous pass, REQ-RL18) and `promote: False` with `realized_gate={"resolved": False, ...}` (unconditional block, REQ-RL7) — one test, two assertions, removing any ambiguity between the two None-ish states | deterministic | pytest: single test calling `decide_promotion` twice with identical other args |

**Execution locus for the live tier (added at spec-review iteration 1, finding F-1 — BLOCKING fix):**
PROP-RL-LIVE1/2/3 and the Done table's `verification` row MUST be executed from the merged
`~/anicca` MAIN checkout after this feature merges — NEVER from the feature's own dev worktree.
`skills/*/state/` is gitignored, so any worktree checkout has NO `skills/earn/state/` directory:
`__file__`-relative resolution there computes a nonexistent path and silently degrades to
`resolved: true, row_count: 0`, which can never satisfy PROP-RL-LIVE1/3's nonzero real-data
assertions. Worktree-run tests requiring a "real-shaped" instance body MUST build it as a
`tmp_path`/temp-`HOME` fixture (PROP-RL-ID3's pattern). It is FORBIDDEN to symlink or copy any
real `skills/*/state/` directory into any worktree (cross-checkout financial-state leak — the
class of defect this feature exists to close; see behavioral-spec.md EDGE-RL5a).

---

## Regression Table (INV-RL5 — the 44 pre-existing tests, plus adjacent suites, MUST stay green)

| suite | count | why it could break | how this feature avoids it |
|---|---|---|---|
| `skills/earn/self-improve/tests/*.py` (existing) | 44 | `DEFAULT_LEDGER_PATH` attribute removal/rename; `decide_promotion`'s signature change; `evaluate()`'s dict shape change | `DEFAULT_LEDGER_PATH` kept (REQ-RL3); `decide_promotion`'s new param is keyword-only with a safe default (REQ-RL18); `evaluate()` only ADDS a `data_source` key, no existing key removed/renamed (REQ-RL14) — verified by re-running this exact suite, asserting the SAME 44 test IDs collect and pass, not just "some tests pass" |
| `skills/earn/hl-trade/tests/*.py` (existing, unrelated feature) | 42 | none expected — this feature does not touch `hl-trade/`; re-run purely as a blast-radius sanity check per the delegating task's own regression ask | re-run unchanged, zero edits to `hl-trade/**` |
| `skills/_shared/lib/__tests__/ledger.test.mjs` + `.test.js` | (existing) | none expected — `ledger.mjs` itself is never edited (INV-5/INV-RL2); `is_profitable`'s HL disjunct is a PYTHON-side sync TO match `ledger.mjs`, never a change to `ledger.mjs` itself | re-run unchanged, zero edits to `skills/_shared/lib/ledger.mjs` |

## Test List (the five required end-to-end behaviors, mirrors the prior phase's own "Test List" section)

1. **Cross-instance leak is structurally impossible** (REQ-RL1, INV-RL1, PROP-RL-ID3) — two
   temp-dir "instance bodies" with distinct ledger content, resolved via distinct `ANICCA_HOME`
   values, NEVER cross-read each other's data.
2. **`resolved: false` blocks promotion unconditionally** (REQ-RL7, PROP-RL-GATE1, PROP-RL-LIVE2)
   — even a candidate that clears every pre-existing deterministic gate AND gets a real adversary
   `PASS` is NOT promoted when the realized-ledger identity could not be determined.
3. **Worsening realized trend blocks promotion even on a fixture-passing candidate**
   (REQ-RL8-10, PROP-RL-GATE2/3) — hand-crafted `(ts, net)` rows showing a negative, worsening
   window override an otherwise-eligible candidate.
4. **Data-realism gap blocks an implausible fixture-vs-reality gap** (REQ-RL11, PROP-RL-GATE4) —
   a candidate whose fixture backtest claims a per-trade edge wildly (>3x) larger than the real,
   sufficiently-sampled per-trade realized edge is blocked, with an escalation record written
   (REQ-RL13, PROP-RL-GATE6).
5. **Live, real-ledger end-to-end proof, not fixture-only** (PROP-RL-LIVE1/2/3, the Done-dimension
   acceptance evidence) — claude-p's OWN real 30-row ledger flows through `resolve_ledger_path` →
   `realized_summary`/`is_confirmed` → `compute_realized_gate` → `decide_promotion` with the
   documented outcome, AND one real `run_evolve.sh` execution shows the fix live in its own log,
   AND the full regression table (44 + 42 + ledger.test.mjs/js) is re-run green. Evidence artifact:
   the live run's own log/escalation/verdict JSON files — not a prose claim.

## Convergence Gate (strict mode)

No phase advances while any PROP-RL-* obligation above is unproven for a REQ marked required for
convergence (all are — every REQ-RL* in behavioral-spec.md maps to ≥1 PROP-RL-* row above,
satisfying `vcsdd-converge`'s criteria-coverage dimension). Test 5 (PROP-RL-LIVE1/2/3 +
Regression table) is the single piece of evidence satisfying behavioral-spec.md's "Done" table
`verification` row; tests 1-4 satisfy `test` (RED→GREEN) together with the PROP-RL-* unit/property
tests above.
