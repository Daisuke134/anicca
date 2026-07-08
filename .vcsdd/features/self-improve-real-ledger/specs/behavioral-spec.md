---
feature: self-improve-real-ledger
phase: 1a/1b
mode: strict
sources:
  - .vcsdd/features/anicca-self-improve-harness/specs/behavioral-spec.md (same repo, prior phase) — REQ-OE/EV/DL/RH/GR groups, INV-1..8, this feature extends them and MUST NOT contradict them
  - skills/earn/self-improve/lib/ledger_reader.py (read directly, this worktree) — its own module docstring already documents two disclosed gaps this feature closes: (a) `DEFAULT_LEDGER_PATH` is `os.path.expanduser("~")/anicca/skills/earn/state/earn-ledger.jsonl`, a single hardcoded path, not per-instance; (b) its `is_profitable` docstring's own "REQ-C4" comment names a Hyperliquid disjunct as "documented follow-up, NOT implemented here"
  - skills/earn/lib/resolve-identity.mjs (read directly) — the project's OWN prior-art fix for exactly this class of bug (cross-instance leak via a hardcoded default), and its test-injectable `{home, env}` parameter convention, copied here rather than re-invented
  - skills/earn/polymarket-trade/run.sh lines 35-63 (read directly) — states the EXACT failure mode this feature fixes, in the author's own words: "ANICCA_HOME unset, resolve-identity.mjs's OWN default derivation falls back to $HOME/.anicca, which — on THIS box — IS automaton's real home, so an unset-ANICCA_HOME [run] safely falls through to the agent['s own default]" — and confirms LIVE, in the real launchd plists, that automaton's `com.anicca.daemon.plist` exports `ANICCA_HOME=~/.anicca` and Franklin's `ai.anicca.franklin-loop.plist` exports `ANICCA_HOME=~/.blockrun`
  - skills/earn/lib/genome.mjs lines 20-24 (read directly) — "Canonical baseline lives IN the OSS repo itself... propagated to every instance body by the EXISTING daemon rsync (`~/anicca/skills` -> body)" — the rsync-tree-relative resolution model this feature's default path fix reuses (copy+tweak) instead of inventing a new per-instance addressing scheme
  - skills/_shared/lib/ledger.mjs (read directly, this worktree) — `isProfitable`'s CURRENT (post `hl-realized-pnl` feature, already `currentPhase: "complete"` per `.vcsdd/features/hl-realized-pnl/state.json`) implementation, including the Hyperliquid disjunct (`chain === "hyperliquid" && fill_tid != null && confirmed === true`) — the ground truth `ledger_reader.py`'s Python mirror has drifted from
  - live filesystem check (this worktree, 2026-07-09): real per-instance ledger row counts confirmed by direct read — claude-p (`~/anicca/skills/earn/state/earn-ledger.jsonl`) 30 rows / automaton (`~/.anicca/skills/earn/state/earn-ledger.jsonl`) 3819 rows / Franklin (`~/.blockrun/skills/earn/state/earn-ledger.jsonl`) 554 rows — proving all three are non-empty, real, and reachable via the rsync-tree-relative + ANICCA_HOME resolution this spec defines (each instance's own copy of `skills/earn/self-improve/lib/ledger_reader.py`, rsynced into its own body root, naturally sits `../../state/earn-ledger.jsonl` away from its OWN ledger — verified by walking the actual directory math for all three paths)
  - live schema check (this worktree, 2026-07-09): `grep -o '"source":"[^"]*"'` over all three real ledgers shows source values `0xwork, cook, polymarket-redeem, x402, x402-serve, hl-trade, token, yield, yield-defi, yield-aave-v3, yield-beefy-morpho, gig, invest-eth-dca` — NONE carry `edge`/`confidence`/`liquidity`/`price` fields (those exist only transiently inside `skills/earn/polymarket-trade/pick.py`'s own in-process decision dict, lines 226-267, never persisted to the ledger) — this grounds REQ-RL14/RL15's honest `data_source` design (a row-level fixture-shaped replay of real history is not buildable from the data that exists today)
  - Marcos Lopez de Prado, "The Three Types of Backtests" — https://www.hillsdaleinv.com/uploads/The_Three_Types_of_Backtests.pdf — already cited by the prior phase for walk-forward OOS scoring; re-cited here for the same "a backtest score means nothing until corroborated by real trading" principle this feature's realized-vs-fixture cross-check operationalizes
  - Freqtrade docs, Backtesting — https://www.freqtrade.io/en/stable/backtesting/ — "backtesting will never replace running a strategy in dry-run mode" (already cited by the prior phase); this feature is the concrete mechanism that makes that warning load-bearing instead of decorative
integration:
  extends:
    - anicca-self-improve-harness (all REQ-OE/EV/DL/RH/GR groups, INV-1..8 stay in force; this feature ADDS a new REQ-RL group and extends INV-3's denylist and INV-5's "sole shared interface" statement — see Global Invariants below — it does not delete or weaken any of them)
  does_not_replace_or_modify:
    - skills/_shared/lib/ledger.mjs (read-only dependency, never edited — same as the prior phase's INV-5)
    - skills/earn/polymarket-trade/pick.py, skills/earn/sol-trade/run.sh, skills/earn/hl-trade/** (live order-execution code; untouched, still frozen per INV-6)
    - .vcsdd/features/anicca-agent-economy/** (never touched, per INV-4)
    - skills/earn/self-improve/strategies/pm_backtest_strategy.py's EVOLVE-BLOCK content and its surrounding fixed region (this feature changes the HARNESS around the evolvable strategy, never the strategy file's own scope boundary)
  out_of_scope_this_phase:
    - Recording market-feature fields (`edge`/`confidence`/`liquidity`/`price`) into `earn-ledger.jsonl` at trade-decision time. This would let a FUTURE feature replay real history through `score_candidate` row-for-row exactly like the fixture does today. It requires editing `pick.py`/`run.sh` (live trading code, frozen by INV-6) and is NOT specified here. See REQ-RL15 and the UNVERIFIED section.
---

# Behavioral Specification — self-improve-real-ledger (Phase 1a/1b)

## Purpose

The prior feature (`anicca-self-improve-harness`) built a real openevolve-driven strategy-evolution
harness whose fitness and promotion gate are 100% derived from a synthetic historical fixture
(`strategies/fixtures/pm_history.csv`). Its own `lib/ledger_reader.py` module already contains an
OBSERVE step meant to read the real realized-P&L ledger before every run — but two audited defects
mean that step currently does nothing useful:

1. **Cross-instance data leak.** `DEFAULT_LEDGER_PATH` is a single hardcoded path
   (`os.path.expanduser("~")/anicca/skills/earn/state/earn-ledger.jsonl` — literally claude-p's own
   ledger). Every instance's rsynced copy of this exact file (`genome.mjs`'s own documented
   propagation model: `~/anicca/skills` → each instance body) would, if invoked with this
   hardcoded default, read claude-p's ledger instead of its own — the same class of bug this
   project's memory `feedback_earn_identity_resolve_per_instance_gate_on_anicca_home` already named
   and `resolve-identity.mjs` already fixed for wallet keys. `ledger_reader.py` was never given the
   equivalent fix.
2. **Decorative OBSERVE.** `run_evolve.sh`'s OBSERVE step (lines 54-64) only writes the ledger
   summary to a log file. Nothing in `evaluator.py`, `lib/promote_gate.py`, or
   `lib/promote_gate_run.py` ever reads it. `realized_summary`'s output has zero effect on
   `stage1_pass`/`stage2_pass`/`combined_score`/`decide_promotion`'s verdict — a candidate can be
   promoted purely on synthetic-fixture performance no matter how the real, per-instance ledger
   looks.

This feature closes both gaps: (a) makes ledger-path resolution per-instance and fail-closed, and
(b) wires the resulting REAL realized data into the promotion gate as a genuine, testable
constraint — so `self-improve`'s promote/reject decision can no longer be based on fixture
performance alone once real per-instance track-record data exists.

This is explicitly a **harness change**, not a strategy change: no line of
`strategies/pm_backtest_strategy.py`'s EVOLVE-BLOCK is touched, no live order-execution path is
touched, and every prior-phase invariant (INV-1..8) remains in force unless explicitly extended
below.

## Grounded Interface — the rsync-tree-relative resolution model (copy+tweak, not invented)

`genome.mjs`'s own module docstring establishes the propagation model already in production use:
"Canonical baseline lives IN the OSS repo itself (`~/anicca/skills/earn/baseline-genome.json`),
propagated to every instance body by the EXISTING daemon rsync (`~/anicca/skills -> body`)." This
means every instance body already carries its OWN physical copy of
`skills/earn/self-improve/lib/ledger_reader.py`, sitting inside that instance's OWN body root:

| instance | body root (`ANICCA_HOME`, or unset for claude-p) | rsynced `ledger_reader.py` physically sits at | that instance's real ledger (confirmed live, 2026-07-09) |
|---|---|---|---|
| claude-p (this checkout, no override) | unset | `~/anicca/skills/earn/self-improve/lib/ledger_reader.py` | `~/anicca/skills/earn/state/earn-ledger.jsonl` (30 rows) |
| automaton | `~/.anicca` (`com.anicca.daemon.plist` exports it) | `~/.anicca/skills/earn/self-improve/lib/ledger_reader.py` | `~/.anicca/skills/earn/state/earn-ledger.jsonl` (3819 rows) |
| Franklin | `~/.blockrun` (`ai.anicca.franklin-loop.plist` exports it) | `~/.blockrun/skills/earn/self-improve/lib/ledger_reader.py` | `~/.blockrun/skills/earn/state/earn-ledger.jsonl` (554 rows) |

A path computed **relative to this running copy's own `__file__`** (climb from
`self-improve/lib/ledger_reader.py` to `earn/state/earn-ledger.jsonl` within the SAME tree this
exact file physically resides in) therefore lands on the CORRECT, OWN ledger for every one of the
three real instances above, verified directly against the actual directory layout — with **zero
dependency on `ANICCA_HOME` at all**. This is the same reuse-not-reinvent principle `genome.mjs`
already applies to `baseline-genome.json`; this feature applies it to `earn-ledger.jsonl` reads.
`ANICCA_HOME`, when explicitly set, is still honored as an override (matching
`resolve-identity.mjs`'s own priority convention and the delegated task's requested order) for
cases where an instance's ledger is deliberately NOT collocated with its rsynced `skills/` tree.

## EARS-Format Functional Requirements

### Group RL-ID — per-instance ledger path resolution (fixes Gap 1)

- **REQ-RL1** `lib/ledger_reader.py` SHALL expose `resolve_ledger_path(env: Optional[dict] = None) ->
  tuple[str, bool, str]` (`path, resolved, resolution_source`) with this priority, mirroring
  `resolve-identity.mjs`'s own test-injectable `{env}` parameter convention (copied, not
  reinvented):
  1. `env["ANICCA_HOME"]` (or `os.environ["ANICCA_HOME"]` when `env` is `None`), if set and
     non-empty → `<ANICCA_HOME>/skills/earn/state/earn-ledger.jsonl`, `resolution_source =
     "anicca_home_env"`.
  2. Else → THIS running module's own `__file__`-relative path (climb from
     `self-improve/lib/ledger_reader.py` to `earn/state/earn-ledger.jsonl` in the same tree),
     `resolution_source = "file_relative_default"` (the Grounded Interface table above).
  3. `resolved` SHALL be `False` (path `""`, `resolution_source = "unresolved_no_file_context"`)
     ONLY when this process cannot determine its own module `__file__` at all (an exotic packaging
     context — e.g. `NameError` on `__file__`). This is the ONE genuine "cannot determine our own
     identity" case; it is NEVER used as an excuse to fall back to another hardcoded/guessed
     instance's path (mirrors `resolve-identity.mjs`'s R5: "any missing file/field or parse error
     returns null — this module NEVER throws" and "fail-closed... callers must treat null as skip,
     never fall back to another instance's key" — applied here to a ledger PATH, not a private key).

- **REQ-RL2** An explicit `path=` argument passed by a caller (existing test convention, unchanged)
  SHALL ALWAYS take priority over `resolve_ledger_path()`'s own computation — REQ-RL1 only governs
  the DEFAULT used when no explicit path is supplied.

- **REQ-RL3** `read_ledger`/`realized_summary`'s `path` parameter SHALL default to `None`, and
  internally call `resolve_ledger_path()` FRESH on every invocation when `path is None` (never a
  module-level constant frozen at import time) — so a process whose `ANICCA_HOME`/body location
  differs between calls (e.g. a test injecting a different `env`) is never served a stale resolved
  path from an earlier call. The pre-existing `DEFAULT_LEDGER_PATH` module attribute SHALL remain
  present (computed once at import time via the SAME REQ-RL1 logic, for any external caller that
  references it directly, and to keep the pre-existing test asserting its shape passing unmodified
  — see verification-architecture.md's regression table) but is NEVER the value `realized_summary`
  actually uses internally when called with no explicit path.

- **REQ-RL4** `realized_summary(...)`'s returned dict SHALL gain two new keys: `resolved: bool` and
  `resolution_source: str`, alongside its existing `ledger_path`/`total_rows`/
  `profitable_row_count`/`realized_net_usd` keys — so `run_evolve.sh`'s existing OBSERVE log line
  (unchanged shell code, REQ-RL16) now visibly proves, per run, WHICH resolution branch fired and
  WHETHER it succeeded, for any human/adversary auditing the log later.

### Group RL-MIR — mirror-sync with `ledger.mjs` (fixes the disclosed REQ-C4 drift)

- **REQ-RL5** `is_profitable(line)` SHALL recognize a THIRD chain-correct-confirmation disjunct —
  `line.get("chain") == "hyperliquid" AND line.get("fill_tid") is not None AND
  line.get("confirmed") is True` — mirrored VERBATIM from `ledger.mjs::isProfitable`'s CURRENT
  implementation (confirmed live: the `hl-realized-pnl` feature, `currentPhase: "complete"`, already
  added this disjunct upstream; `ledger_reader.py`'s own docstring for "REQ-C4" still says "NOT
  implemented here" — this closes that drift). `is_profitable`'s existing EVM/Solana disjuncts and
  its `net_usdc > 0` / non-swap / `external is True` preconditions are UNCHANGED.

- **REQ-RL6** `lib/ledger_reader.py` SHALL expose a NEW `is_confirmed(line) -> bool` predicate:
  IDENTICAL to `is_profitable`'s chain-correctness + non-swap + `external is True` checks, WITHOUT
  the `net_usdc > 0` requirement. `is_profitable(line)` SHALL be re-expressed as `is_confirmed(line)
  and net_usdc > 0` (DRY, single source of truth for the "real on-chain settlement" check).
  Rationale: `is_profitable`-filtered rows can, by construction, never be negative — REQ-RL8-11's
  realized-P&L TREND/loss detection needs to see confirmed LOSSES too (a redeemed losing
  Polymarket position, `net_usdc < 0`, `external: true`, `status: "0x1"`), which `is_profitable`
  alone structurally cannot report.

### Group RL-GATE — realized ledger data gates promotion (fixes Gap 2/decorative-OBSERVE)

- **REQ-RL7** `lib/promote_gate.py::decide_promotion(assessment, adversary_verdict,
  adversary_reason="", realized_gate: Optional[dict] = None)` SHALL treat
  `realized_gate["resolved"] is False` as an UNCONDITIONAL promotion block — `decision["promote"]`
  SHALL be `False` regardless of `assessment`/`adversary_verdict`, with `reason` naming the
  unresolved-identity condition. `promote_gate_run.py`'s PRODUCTION call site (the only real
  invocation path, `main()`) SHALL ALWAYS compute a real `realized_gate` dict (via REQ-RL8-13,
  reading THIS instance's own resolved ledger) and pass it explicitly — the bare
  `decide_promotion(assessment, adversary_verdict)` form (omitting `realized_gate`) SHALL NEVER
  appear at that call site (REQ-RL17's wiring test enforces this via repo-scan).

- **REQ-RL8** `lib/gate_math.py` SHALL expose a PURE function `realized_window_split(rows:
  Iterable[tuple[float, float]], window_start_ts: float, window_end_ts: float) -> dict` — `rows` are
  already-filtered `(ts, net_usdc)` pairs (the caller's job, via `is_confirmed`, is impure). Splits
  `[window_start_ts, window_end_ts)` at its temporal MIDPOINT into two halves; returns
  `{"window_net_usd": float, "first_half_net_usd": float, "second_half_net_usd": float,
  "row_count": int}` (sum of `net_usdc` in each half/whole window; `row_count` = rows falling inside
  the window at all).

- **REQ-RL9** `lib/gate_math.py` SHALL expose a PURE function `is_worsening_trend(first_half_net_usd:
  float, second_half_net_usd: float) -> bool` = strictly `second_half_net_usd < first_half_net_usd`.

- **REQ-RL10** `lib/gate_math.py` SHALL expose a PURE function `realized_trend_blocks(window_net_usd:
  float, worsening: bool, sufficient: bool) -> bool` = `sufficient AND window_net_usd < 0.0 AND
  worsening`. `sufficient` SHALL be computed by the (impure) caller as `row_count >=
  MIN_REALIZED_ROWS_FOR_TREND` where `MIN_REALIZED_ROWS_FOR_TREND = 6` (a documented, defensible
  minimum: at least 3 confirmed rows per half are needed for the first/second-half split to reflect
  more than single-row noise). When `sufficient` is `False` (too few confirmed rows in the current
  operating window — including a brand-new instance with an empty-but-resolvable ledger, EDGE-RL1),
  this SPECIFIC check does NOT fire (it is not evaluated as a block) — this is distinct from, and
  independent of, REQ-RL7's `resolved` gate, which is about identity/path resolution, not data
  volume.

- **REQ-RL11** `lib/gate_math.py` SHALL expose a PURE function `data_realism_gap(
  mean_backtest_net_usd: float, mean_realized_net_per_row: float, sufficient: bool, multiple: float
  = 3.0) -> bool`, returning `True` (contradiction — BLOCK) when `sufficient` is `True` AND either:
  (a) `mean_realized_net_per_row <= 0.0 AND mean_backtest_net_usd > 0.0` (the fixture backtest
  claims a real edge while the real, sufficiently-sampled track record shows none), OR (b)
  `mean_realized_net_per_row > 0.0 AND gate_math.is_implausible_jump(mean_backtest_net_usd,
  mean_realized_net_per_row, multiple)` (REUSE of the existing REQ-RH2 implausible-jump math,
  repurposed here to compare the fixture's claimed per-trade edge against the REAL observed
  per-trade edge, instead of candidate-vs-population — same pure function, new call site, no new
  gate-math primitive invented). `sufficient` uses the SAME `MIN_REALIZED_ROWS_FOR_TREND` threshold
  as REQ-RL10.

- **REQ-RL12** The "current promoted generation's operating window" (REQ-RL10/RL11's
  `window_start_ts`) SHALL be the UNIX timestamp of the most recent git commit whose subject line
  matches `lib/promote.py`'s own commit-message prefix (`"feat(self-improve): promote candidate"`),
  scoped to `strategies/pm_backtest_strategy.py`'s path (`git log -1 --format=%ct --grep=...  --
  <path>`); `window_end_ts` is "now" (the moment the gate runs). WHEN no such commit exists (the
  baseline is still the original seed program, never promoted) `sufficient` (REQ-RL10/RL11) SHALL
  be `False` for that reason alone — there is no "current generation" to measure a trend against
  yet. This is a NEW, small, effectful helper (`lib/promotion_history.py::last_promotion_ts`),
  isolated from the pure core exactly like `lib/promote.py` already isolates its own git
  subprocess calls.

- **REQ-RL13** WHEN REQ-RL10 or REQ-RL11 evaluates to `True` (blocks), `promote_gate_run.py` SHALL
  write an escalation record `<run_dir>/realized_gate_escalation.json` (containing the specific
  reason, the computed `window_net_usd`/`worsening`/`data_realism_gap` inputs, and
  `candidate_path`) BEFORE `decide_promotion` returns its `False` verdict for that reason — so a
  human/adversary reviewing the run later sees WHY real data overrode an otherwise-fixture-passing
  candidate, not just a bare `promote: false`.

### Group RL-EVAL — honest `data_source` tagging (no overclaim of a real-data replay that does not exist)

- **REQ-RL14** `evaluator.py::evaluate()` and `evaluate_stage2()`'s returned dict SHALL gain a
  `data_source` key, one of exactly two values: `"fixture"` (default — the ENTIRE existing
  fixture-based backtest computation is unchanged, this is the ONLY value used when insufficient
  real data exists) or `"fixture+realized-crosscheck"` (set exactly when the current instance's
  confirmed-row count over the current operating window, per REQ-RL12, meets
  `MIN_REALIZED_ROWS_FOR_TREND` — i.e. the SAME threshold and window REQ-RL10/RL11 use). THE
  SYSTEM SHALL NEVER report `data_source == "real"` or otherwise imply `combined_score` itself was
  computed from real historical rows replayed through `score_candidate` — it never is, in this
  phase (see REQ-RL15).

- **REQ-RL15** (grounding / honesty requirement) A row-level walk-forward replay of REAL ledger
  history through `score_candidate` (the literal thing "real data instead of fixture" would mean)
  is NOT built in this phase, because the real ledger's rows (confirmed live, all three instances,
  2026-07-09: sources `0xwork/cook/polymarket-redeem/x402/x402-serve/hl-trade/token/yield*/gig/
  invest-eth-dca`) carry NONE of the market-feature fields (`edge`/`confidence`/`liquidity`/
  `price`) `score_candidate`'s signature requires — those values exist only transiently inside
  `pick.py`'s own in-process decision dict (`polymarket-trade/pick.py` lines 226-267), never
  persisted to `earn-ledger.jsonl`. Building that replay would require a NEW feature that adds
  market-feature decision-logging to `pick.py`/`run.sh` (live trading code, out of scope here per
  INV-6). What THIS feature builds instead — REQ-RL7-13's realized-gate — makes real data GOVERN
  the promotion decision (by overriding/blocking an otherwise-fixture-passing candidate) without
  overclaiming that `combined_score`'s underlying computation itself became real-data-driven. This
  deferred item is recorded in this document's UNVERIFIED section for a follow-up feature, not
  silently dropped.

### Group RL-WIRE — end-to-end wiring (no orphan implementation)

- **REQ-RL16** `run_evolve.sh`'s existing OBSERVE step (lines 54-64, UNCHANGED shell code — it
  already calls `"$PY_BIN" "$SKILL_DIR/lib/ledger_reader.py"` with no explicit path override) SHALL,
  purely as a consequence of REQ-RL1-4's default-resolution fix, log a `resolved`/
  `resolution_source`-bearing JSON line that correctly reflects THIS instance's own ledger under
  whatever `ANICCA_HOME` this process was invoked with (or the file-relative default when unset).
  No `run_evolve.sh` code change is required or permitted to satisfy this REQ — it is proof that
  the fix lives in the resolution function itself, not sprinkled at every call site.

- **REQ-RL17** `promote_gate_run.py::main()` SHALL compute the `realized_gate` dict (REQ-RL7-13)
  ONCE and pass it to `decide_promotion` at EVERY ONE of `promote_gate_run.py`'s three current
  `decide_promotion` call sites (the `not eligible_for_adversary_review` short-circuit at ~line
  209, the adversary-unavailable/errored branch at ~line 225, and the adversary-succeeded branch
  at ~line 234 — today all three omit realized_gate entirely; each becomes
  `decide_promotion(..., realized_gate=<the computed dict>)`). No call site in
  `promote_gate_run.py` SHALL ever call `decide_promotion` without an explicit `realized_gate=`
  argument (verified by a repo-scan test over `promote_gate_run.py`'s own source text — this is
  the concrete "no orphan wiring" proof the delegating task required). Additionally, the
  Phase-3 implementation review SHALL verify that the value bound to `realized_gate=` at each
  call site is genuinely sourced from the REQ-RL7-13 computation helper over the resolved
  ledger — never a hardcoded literal, stub dict, or constant that would satisfy the repo-scan's
  keyword-presence check while bypassing real data.

- **REQ-RL18** `lib/promote_gate.py::decide_promotion`'s NEW `realized_gate` parameter SHALL default
  to `None`, and `None` SHALL be treated as "no realized-gate constraint" (REQ-RL7/RL10/RL11's
  checks all pass vacuously) — this default exists SOLELY so the 44 pre-existing tests (which
  construct `decide_promotion` calls without this parameter, asserting pure gate-logic behavior in
  isolation from any ledger) continue to pass UNMODIFIED. Production code (REQ-RL17) SHALL NEVER
  rely on this default — this constraint is documented in `decide_promotion`'s own docstring and
  enforced by REQ-RL17's wiring test, so "secure in production, permissive by default for isolated
  unit tests" is a verified property, not an assumption.

### Group RL-SAFE — money-safety restated and extended (no weakening of any prior invariant)

- **REQ-RL19** `lib/scope_guard.py::DENYLIST_MODULES` (REQ-DL1) SHALL be EXTENDED (never shrunk,
  never reordered in a way that drops an existing entry) to also include this feature's own new
  harness-file/symbol names: `"ledger_reader.py"`, `"resolve_ledger_path"`, `"is_confirmed"`,
  `"realized_summary"`, `"promotion_history.py"`, `"last_promotion_ts"`, `"realized_gate"` — the
  SAME "the harness/runner itself is never EVOLVE-BLOCK-editable" protection REQ-DL1 already gives
  `openevolve-run.py`/`config.yaml`, applied to this feature's own new files.

- **REQ-RL20** No function added by this feature, anywhere, SHALL write to `earn-ledger.jsonl` or
  any other live-system state file — verified by the SAME static source-text-scan technique
  `PROP-SI-EV7` already uses (scan `ledger_reader.py`, `promotion_history.py`, and any new
  `gate_math.py`/`promote_gate.py` additions for `open(...,"w")`/`open(...,"a")` against a path
  containing `"earn-ledger"`). This restates INV-5's read-only half for every new module this
  feature adds, closing the gap where the prior phase's INV-5 named only `ledger.mjs`
  (JS) and did not anticipate a second, Python-side reader being added.

- **REQ-RL21** No function added by this feature SHALL read, resolve, or reference a wallet private
  key or the `ANICCA_EVM_PRIVATE_KEY`/`ANICCA_SOLANA_PRIVATE_KEY` env vars, `.automaton/wallet.json`,
  `.automaton/solana.json`, or `.blockrun/.solana-session` — this feature's per-instance resolution
  is scoped EXCLUSIVELY to the financial ledger file (`earn-ledger.jsonl`), never to a signing key.
  (REQ-RL19's denylist additions are financial-data-adjacent, not key-adjacent, and REQ-DL1's
  existing wallet-key denylist entries are unchanged and still in force.)

## Global Invariants (extends the prior phase's INV-1..8 — none are weakened)

| # | Invariant |
|---|---|
| INV-RL1 | The per-instance ledger path resolution (REQ-RL1) MUST NEVER, under any input, return a path that resolves to a DIFFERENT instance's body root than the one this running process is physically part of (the rsync-tree-relative default is correct BY CONSTRUCTION, not by a runtime check — see Grounded Interface table; `ANICCA_HOME`, when set, is trusted the same way `resolve-identity.mjs` already trusts it for keys — this feature cannot detect operator misconfiguration of `ANICCA_HOME` any more than `resolve-identity.mjs` can) |
| INV-RL2 | `ledger_reader.py` (`read_ledger`/`realized_summary`/`is_confirmed`/`is_profitable`/`resolve_ledger_path`) remains READ-ONLY — no write/append function is added to it in this feature (REQ-RL20 restates and extends INV-5) |
| INV-RL3 | REQ-DL1's denylist (INV-3) is only ever EXTENDED (REQ-RL19), never shrunk or reordered to drop coverage |
| INV-RL4 | This feature never edits `strategies/pm_backtest_strategy.py`'s EVOLVE-BLOCK content or fixed region, nor any live order-execution file (`pick.py`, `sol-trade/run.sh`, `hl-trade/**`) — those stay exactly as frozen by the prior phase's INV-6 |
| INV-RL5 | The 44 pre-existing pytest tests under `skills/earn/self-improve/tests/` MUST remain green, UNMODIFIED in their assertions, after this feature's changes (verification-architecture.md's regression table is the proof obligation) |
| INV-RL6 | Every new pure function this feature adds lives in `lib/gate_math.py` (extending the existing AST-import-scan-verified pure core, REQ-OE/RH's own Pure Core table) — no new parallel "pure module" is created for this feature alone |

## Edge Cases

- **EDGE-RL1** A resolvable-but-empty ledger (a brand-new instance with zero rows ever, or an
  instance whose `ANICCA_HOME`-derived directory doesn't yet contain `state/earn-ledger.jsonl`):
  `resolved` is `True` (the PATH was determined correctly — this is "we know which file is ours and
  it happens to be empty," not "we don't know whose file to read"); REQ-RL10/RL11's checks simply
  don't fire (`sufficient = False`, `row_count = 0`) — the candidate is judged on fixture
  performance alone, same as before this feature, until real data accumulates.
- **EDGE-RL2** `ANICCA_HOME` is set but points at a directory with no `skills/earn/state/` subtree
  at all (operator typo): same as EDGE-RL1 — `read_ledger` already degrades a missing file to `[]`
  (existing, unchanged behavior) — `resolved` stays `True` (the path computation itself succeeded;
  it is the FILE that is absent, an orthogonal, already-handled case).
- **EDGE-RL3** Multiple self-improve promotion commits exist in git history: REQ-RL12 uses the
  MOST RECENT one (`git log -1`) as the current generation's start — older promotions' windows are
  irrelevant to "is the CURRENTLY live baseline losing money."
- **EDGE-RL4** The realized ledger has real rows but NONE fall inside `[window_start_ts,
  window_end_ts)` (e.g. the instance was dormant since the last promotion): `row_count = 0` inside
  the window → `sufficient = False` → REQ-RL10/RL11 do not fire, same treatment as EDGE-RL1 (a
  quiet instance is not evidence of a losing strategy).
- **EDGE-RL5a** (added at spec-review iteration 1, finding F-1) The feature's OWN dev worktree
  (`.worktrees/self-improve-real-ledger/`) has NO `skills/earn/state/` directory at all —
  `skills/*/state/` is gitignored, so `__file__`-relative resolution from the worktree computes a
  nonexistent path and degrades to `resolved: True, row_count: 0` (EDGE-RL2's shape). Therefore:
  (i) the Tier-2 live proof obligations (PROP-RL-LIVE1/2/3) and the Done table's verification row
  MUST be executed from the merged `~/anicca` main checkout AFTER merge — NEVER from the feature's
  own worktree; (ii) any worktree-run test that needs a "real-shaped" instance body MUST construct
  it as a `tmp_path`/temp-`HOME` fixture (as PROP-RL-ID3 does); (iii) it is FORBIDDEN to symlink
  or copy any real `skills/*/state/` directory (any instance's) into any worktree — that would
  grant a dev checkout read/write proximity to production financial ledger state, the exact
  cross-environment leak class this feature exists to close.
- **EDGE-RL5** A candidate is ineligible for adversary review (REQ-EV2/EV4 already block it before
  any LLM call) AND separately `resolved is False`: REQ-RL7's block and the pre-existing
  deterministic-gate block are BOTH true; `decide_promotion`'s `reason` string SHALL name whichever
  is checked first (REQ-RL7's `resolved` check runs before the pre-existing
  `eligible_for_adversary_review` check inside `decide_promotion` — an unresolved identity is
  strictly cheaper to check and strictly more fundamental than a fixture-performance verdict) —
  this ordering is a `decide_promotion` implementation detail, not a behavior change to what gets
  promoted (both paths already return `promote: False`).

## "Done" / 4-D Convergence

| dimension | condition |
|---|---|
| spec | this document + verification-architecture.md; fresh-context `vcsdd-adversary` `vcsdd-spec-review` verdict = PASS (strict mode: zero BLOCKING findings) |
| test | RED: cross-instance-leak-reproduction, resolved=false-blocks-promotion, worsening-trend-blocks, data-realism-gap-blocks, data_source-tagging, and the 44 pre-existing + 4 new regression suites all written/failing-for-the-right-reason first; GREEN: all passing, 44 pre-existing UNCHANGED in assertions |
| impl | `lib/ledger_reader.py` (resolve_ledger_path/is_confirmed/is_profitable/realized_summary), `lib/gate_math.py` (realized_window_split/is_worsening_trend/realized_trend_blocks/data_realism_gap), `lib/promotion_history.py` (last_promotion_ts), `lib/promote_gate.py` (decide_promotion's realized_gate param), `promote_gate_run.py` (production wiring, REQ-RL17), `lib/scope_guard.py` (extended DENYLIST_MODULES) all present and runnable |
| impl review | fresh-context `vcsdd-adversary` Phase-3 review of every file touched above returns PASS |
| verification | Phase 5 hardening: proof obligations in verification-architecture.md all discharged; a REAL run against claude-p's own live ledger (30 rows, realized net ≈ +$8.47 confirmed live 2026-07-09) demonstrates the resolved-path + gate wiring end-to-end (not mocked) — evidence = the run's own log/verdict/escalation JSON files, not a prose claim; `run_evolve.sh` executed once for real and its log shows `resolved: true`/correct `resolution_source`; the 44 pre-existing + 42 `hl-trade` tests + `ledger.test.mjs`/`ledger.test.js` regression suites all re-run green after this feature's changes |

Strict-mode gate: no phase advances with any BLOCKING adversary finding open.

## UNVERIFIED

- Row-level real-history walk-forward replay through `score_candidate` (the literal meaning of
  "evaluate on real data instead of fixture") is explicitly NOT built this phase — see REQ-RL15's
  grounding. A follow-up feature would need to: (1) add market-feature decision-logging to
  `pick.py`/`run.sh` (an edit to live trading code, requiring its own spec and adversary review,
  out of scope here per INV-6), (2) define a fixture-equivalent schema for the logged real rows,
  (3) re-derive `evaluate_stage2`'s walk-forward window-pair logic against real (non-synthetic)
  time boundaries instead of the fixture's fixed `window` column. None of this is designed here.
- `MIN_REALIZED_ROWS_FOR_TREND = 6`'s exact value is a documented, defensible-but-not-empirically-
  tuned minimum (≥3 rows per half-window split). Implementation/hardening MAY re-derive a
  statistically stronger threshold (e.g. a minimum-detectable-effect calculation against the real
  ledgers' actual per-row variance) if the fresh adversary review flags 6 as too low/high — this is
  a tunable constant, not a structural design decision, and changing it later does not require
  re-opening this spec's REQ-RL8-11 shapes.
- `last_promotion_ts`'s git-log-grep approach (REQ-RL12) assumes `lib/promote.py`'s commit-message
  prefix (`"feat(self-improve): promote candidate"`) is never changed by a future edit to
  `promote.py` without a corresponding update here — implementation MUST keep these two strings in
  sync (a `grep`-based regression test, mirrored on `PROP-SI-DL1`'s "denylist constant matches spec
  verbatim" pattern, is the intended guard — see verification-architecture.md).
