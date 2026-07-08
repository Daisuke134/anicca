# Verification Architecture — franklin-funding-loop

## Purity Boundary Map

- **Pure Core** (deterministic, no side effects, unit/property testable):
  - `viability_gate(balance_usd, floor_usd) -> {allowed, reason, headroom_usd}` (REQ-004) — new
    pure predicate this feature introduces. **Corrected 2026-07-08 iteration 2 (closes FIND-003)**:
    now also returns `headroom_usd = max(0, floor_usd - balance_usd)` when `allowed: true` (`0`
    when blocked or on fail-closed bad input) — the additional sizing bound `clip_amount` composes
    with the flat per-transfer cap. No I/O.
  - `cooldown_gate(last_attempt_ts, now_ts, cooldown_hours) -> {allowed, reason}` (REQ-005) — new
    pure predicate. No I/O. **Corrected 2026-07-08 iteration 2 (closes FIND-002)**: parameter
    renamed from `last_sent_ts` to `last_attempt_ts` to reflect that it is fed by
    `most_recent_funding_attempt` (below), not merely the most recent
    `send_to_franklin`/`sent` row.
  - `most_recent_funding_attempt(history) -> ts | None` (REQ-005 correction, NEW, closes FIND-002)
    — pure row-selection helper: filters `history` (parsed `funding-ledger.jsonl` rows) to `step
    in {"withdraw", "bridge", "send_to_franklin"}` AND `status != "dry"`, returns the maximum `ts`
    among them (or `None` if empty). No I/O — takes the already-parsed row list; OBSERVE (REQ-002)
    is what actually reads the file.
  - `should_fund(decide_recommendation, viability_result, cooldown_result, killed) -> bool` (REQ-007)
    — pure boolean AND over already-computed inputs. No I/O.
  - `clip_amount(recommended_usd, per_transfer_cap_usd, headroom_usd) -> float` (REQ-003 edge case)
    — pure numeric clamp, mirrors the clamping style already used in
    `skills/earn/funding/lib/caps.py::reserve_protected_amount`. **Corrected 2026-07-08 iteration 2
    (closes FIND-003)**: signature now takes `headroom_usd` (from `viability_gate`'s own output,
    REQ-004) as a third bound, alongside the existing flat `per_transfer_cap_usd` — returns
    `max(0, min(recommended_usd, per_transfer_cap_usd, headroom_usd))` for valid positive input,
    `0` (fail-closed) otherwise.
  - `skills/earn/funding/lib/caps.py::_outflow_rows` / `check_caps` — UNCHANGED by this feature
    (REQ-006/REQ-008 depend on its existing, already-tested `step == "withdraw"` filter behavior;
    this feature's own tests call the REAL, unmodified function to prove non-interference, never a
    reimplementation of it).

- **Effectful Shell** (I/O, network, process spawn, LLM invocation — this feature's real surface):
  - Loop entry script (`skills/self/franklin-funding-loop/run.sh`, mirrors
    `skills/self/claude-p-mainloop.sh`'s structure): kill-switch file check
    (`~/.anicca/franklin-funding-loop.pause`), pidfile check/write/cleanup
    (`~/.openclaw/state/franklin-funding-loop.pid`), `cd` to a working directory, and the DECIDE
    subprocess invocation.
  - OBSERVE reads (REQ-002): `skills/_shared/lib/solana-verify.mjs::usdcBalance` (network RPC),
    file reads of `earn-ledger.jsonl` / `sol-trade.trace.jsonl` / `funding-ledger.jsonl` /
    `funding/config.json`.
  - DECIDE (REQ-003, corrected 2026-07-08 iteration 2, closes FIND-001): a real `claude -p
    "<prompt>" --output-format json --model <model>` subprocess — the `thinkClaudeP`-style
    restricted invocation (`runtime/loop/brain.mjs:83-134`): NO `--dangerously-skip-permissions`
    or other tool-grant flag, a scrubbed minimal env (no private keys/wallet credentials), and a
    neutral `os.tmpdir()`-equivalent cwd (never the project working directory or
    `skills/earn/funding/`) — genuine LLM judgment, not a pure function, but structurally
    incapable of taking a money-moving (or any filesystem/subprocess) action itself. Its OUTPUT (a
    parsed `fund_recommended`/`amount_usd`/`reasoning` JSON blob) is the only channel through which
    it can influence anything downstream — it is what the pure
    `should_fund`/`clip_amount`/`viability_gate` functions consume as plain data (see PROP-012 for
    the structural proof that this invocation cannot itself move money).
  - FUND (REQ-007): `python3 skills/earn/funding/run.py --amount-usd <clipped>` — a real subprocess
    that performs real on-chain transfers via the UNCHANGED, already-adversary-reviewed mechanism.
  - LOG (REQ-008): append-only write to `funding-ledger.jsonl` (reuses
    `skills/earn/funding/lib/ledger.py`'s append convention, or an equivalent append-only writer
    with the same one-JSON-line-per-decision shape).
  - `ai.anicca.franklin-funding-loop.plist` (REQ-009): launchd scheduling configuration.

## Proof Obligations

| ID | Description | Tier | Required | Tool |
|----|-------------|------|----------|------|
| PROP-001 | `viability_gate(balance_usd, floor_usd)`: returns `allowed:false` iff `balance_usd >= floor_usd` (inclusive boundary blocks funding — safety-conservative direction); returns `allowed:false` (fail-closed, never permissive) for non-finite, negative, or non-numeric `floor_usd`/`balance_usd` inputs. **Corrected 2026-07-08 iteration 2 (closes FIND-003)**: ALSO returns `headroom_usd = max(0, floor_usd - balance_usd)` when `allowed:true`, `headroom_usd = 0` when blocked or on fail-closed bad input | 1 | true | pytest boundary table (mirrors `skills/earn/funding/tests/test_caps.py`'s own convention: `balance < floor`, `== floor`, `> floor`, plus bad-input rows; assert `headroom_usd` on each row) |
| PROP-002 | `cooldown_gate(last_attempt_ts, now_ts, cooldown_hours)`: returns `allowed:false` iff `(now_ts - last_attempt_ts) < cooldown_hours*3600`; `last_attempt_ts is None`/absent (no prior attempt) always returns `allowed:true`; exactly-at-window boundary returns `allowed:true` (cooldown has elapsed, not still active). **Corrected 2026-07-08 iteration 2 (closes FIND-002)**: SEPARATELY, `most_recent_funding_attempt(history)` (which feeds `last_attempt_ts`) is tested to select the max `ts` across `step in {withdraw, bridge, send_to_franklin}` rows with `status != "dry"` — including a case with ONLY a `pending` `send_to_franklin` row (no terminal row) and a case where `withdraw`+`bridge` have terminal `sent` rows but NO `send_to_franklin` row exists at all; both cases must select a non-null `last_attempt_ts` (never treated as "no cooldown") | 1 | true | pytest boundary table for `cooldown_gate` (no-prior-row, just-under-window, exactly-at-window, well-past-window) PLUS a separate boundary table for `most_recent_funding_attempt` (pending-row-only, withdraw+bridge-sent-but-no-send_to_franklin-row, failed-row-only still counts, dry-row excluded, loop-decide-row excluded) |
| PROP-003 | `should_fund(decide_recommendation, viability_result, cooldown_result, killed)` is a strict logical AND: `fund_recommended AND viability_result.allowed AND cooldown_result.allowed AND NOT killed` — exhaustive truth table over all 2^4=16 input combinations matches the AND semantics exactly (REQ-007) | 1 | true | pytest exhaustive truth-table test |
| PROP-004 | `clip_amount(recommended_usd, per_transfer_cap_usd, headroom_usd)` never returns a value greater than `min(per_transfer_cap_usd, headroom_usd)`, is a no-op (returns `recommended_usd`) only when `recommended_usd <= per_transfer_cap_usd AND recommended_usd <= headroom_usd`, and returns `0`/fails closed for negative or non-numeric `recommended_usd` (REQ-003 edge case). **Corrected 2026-07-08 iteration 2 (closes FIND-003)**: signature gains the `headroom_usd` parameter (from `viability_gate`'s output); boundary table includes `balance=$19.99, floor=$20, cap=$12, recommended=$12 -> clipped<=$0.01` (headroom binds, not the flat cap) and `balance=$5, floor=$20, cap=$12, recommended=$12 -> clipped=$12` (cap binds, headroom does not tighten below the cap) | 1 | true | pytest boundary table |
| PROP-005 | A synthetic ledger row `{"step": "loop-decide", "status": "sent", "amount_usd": 1000000, "ts": <now>}` fed through the REAL, unmodified `skills/earn/funding/lib/caps.py::_outflow_rows` (imported directly, not reimplemented) is NEVER selected — i.e. it contributes `$0` to `check_caps`'s daily/cumulative totals, proving REQ-008's structural (not conventional) isolation from cap accounting | 1 | true | pytest, imports the real `caps.py` module from `skills/earn/funding/lib` (regression-style cross-feature test — this feature's test suite depends on that module's `step` filter never changing without this test also failing) |
| PROP-006 | Loop-level kill-switch (REQ-001): with `~/.anicca/franklin-funding-loop.pause` (or an injectable test-path equivalent) present, the entry script exits 0 before any OBSERVE read, DECIDE subprocess spawn, or ledger write occurs; with it absent and a live pidfile held by another process, a second concurrent invocation also exits 0 without a second DECIDE/FUND invocation; a stale pidfile (dead PID) is reclaimed, not treated as "already running" | 1 | true | bash test harness in the style of `skills/self/founder-loop/test-founder-loop.sh` (static grep-based structural assertions: kill-switch check precedes any OBSERVE/DECIDE code path; `kill -0` liveness check present) plus behavioral fixture runs with injectable `FRANKLIN_FUNDING_LOOP_TEST` env-scoped paths (mirrors `founder-loop.sh`'s `FOUNDER_TEST=1` convention) |
| PROP-007 | End-to-end gate composition (money-safety invariant): the ONLY code path that can result in a non-dry `run.py` invocation requires, in this exact conjunction, kill-switch absent AND DECIDE `fund_recommended:true` AND `viability_gate.allowed:true` AND `cooldown_gate.allowed:true` — verified as a control-flow invariant over the entry script's actual source (no branch bypasses any one of the four), not merely inferred from the pure unit tests of the individual predicates in isolation. NOTE: this proves the WRAPPER's own control-flow never bypasses a gate; it does NOT and cannot prove what the DECIDE subprocess itself is privileged to do independently of that control flow — that is PROP-012's job (added 2026-07-08 iteration 2, closes FIND-006) | 2 | true | exhaustive state-table test over the REAL entry script (mirrors `franklin-loop-revival`'s PROP-007/PROP-016 treatment of money-safety/identity invariants as Tier 2 — every combination of `{kill-switch present/absent} x {fund_recommended true/false} x {viability allowed/blocked} x {cooldown allowed/blocked}` asserted against whether a (mocked, non-network) `run.py` invocation occurs) |
| PROP-008 | No source file added by this feature contains a numeric threshold, regex, or keyword-based classifier that decides "Franklin is starving/undergrown" — that judgment is produced exclusively by the DECIDE step's LLM subprocess invocation (REQ-003); the wrapper script/gate predicates only consume the LLM's OUTPUT (`fund_recommended`/`amount_usd`), they never independently re-derive it from OBSERVE data. NOTE: this is a check for a hardcoded-classifier SUBSTITUTE for DECIDE, distinct from PROP-012's check of what DECIDE's OWN execution environment is privileged to do | 1 | true | manual/adversary code review (Phase 3) of the implementation diff, checking for any conditional that inspects OBSERVE snapshot fields (balance, ledger rows) to directly set `fund_recommended` without going through the DECIDE subprocess — this is a structural/architectural property, not something a runtime unit test alone can prove, so it is additionally gated by Phase 3 adversary review as a required finding-check |
| PROP-009 | Live smoke check: with the kill-switch absent and a real Franklin balance below `viability_floor_usd`, one full real wake (OBSERVE -> DECIDE -> gates -> at most one `run.py` invocation -> LOG) produces exactly one new `loop-decide` row in `funding-ledger.jsonl`, and if `fund_recommended` was true and both gates passed, a corresponding real `withdraw`/`bridge`/`send_to_franklin` row trio with a matching amount appears in the same ledger within the same wake's time window | 0 | true | live end-to-end smoke run (one supervised, manually-watched invocation before the launchd job is left unattended — mirrors the funding skill's own D1/D2 supervised-first-run precedent) |
| PROP-010 | Autonomy indicator (informational, long-horizon, not a Phase-gating requirement): sampled across `loop-decide` rows in `funding-ledger.jsonl` over multiple real wakes spanning days/weeks, the proportion of wakes where `fund_recommended:true` AND both gates passed trends downward as Franklin's own balance/growth trend rises | 0 | false | periodic manual/dashboard inspection of `funding-ledger.jsonl` history (observational fact about real-world Franklin performance, not independently provable by any test at spec time) |
| PROP-011 | `ai.anicca.franklin-funding-loop.plist` (REQ-009), the deployed file at `~/Library/LaunchAgents/`, has `RunAtLoad=false`, a `StartInterval` present (default 21600), `ProgramArguments` pointing at a script distinct from `claude-p-mainloop.sh` and Franklin's own daemon entry point, and distinct `StandardOutPath`/`StandardErrorPath` values from both of those other jobs | 0 | true | live artifact check: parse the actual deployed plist (`plutil -convert json` or XML parse) and assert the above, plus `launchctl print gui/$(id -u)/ai.anicca.franklin-funding-loop` shows the job loaded |
| PROP-012 | **NEW, 2026-07-08 iteration 2 — DECIDE subprocess privilege isolation (closes FIND-006, proves FIND-001's fix at the proof level, not just the wrapper's control flow)**: the actual argv/spawn-options passed to the child-process invocation for DECIDE (intercepted via a mocked `spawn`/`subprocess.run` call, never a live network call) contain NO `--dangerously-skip-permissions` flag and no other permissive tool-grant flag; the child env is exactly the scrubbed allow-list (no key matching a private-key/wallet-credential pattern is present); the child `cwd` is a neutral directory (e.g. `os.tmpdir()`), never the project working directory nor `skills/earn/funding/`. SEPARATELY, a Phase-3 adversary code review confirms the DECIDE module itself contains zero import of, hardcoded path to, or string-literal invocation of `run.py`, the kill-switch file path, or `funding-ledger.jsonl` — i.e. DECIDE's own code has no reachable code path to any money-moving action even in principle, independent of which CLI flags are used to invoke it | 2 | true | (a) a unit test that intercepts the real spawn call (mocked child-process boundary, asserting on the actual argv/options array, not a doc comment) and (b) Phase 3 adversary review of the DECIDE module's own source for any reference to `run.py`/kill-switch/ledger paths |
| PROP-013 | **NEW, 2026-07-08 iteration 2 — path indirection (closes FIND-005)**: every reference in this feature's own new source to `skills/earn/funding/` or `skills/earn/state/` resolves through exactly ONE configurable base-directory value (e.g. `FRANKLIN_FUNDING_HOME`, default `$HOME/anicca`) defined in exactly one place — a static grep across this feature's own new files finds zero independent second hardcoded literal of the base-directory string outside that one definition | 1 | true | static grep-based structural test (mirrors PROP-006's grep-based structural assertions), run against this feature's own new files only (not `skills/earn/funding/`'s existing, unmodified source, which this feature does not touch) |

## Verification Strategy

- **Tier 0** (no formal proof needed — live/operational facts about the real deployed plist, real
  wallet balances, and real ledger content over time): PROP-009, PROP-010, PROP-011. These depend
  on the actual deployed launchd job, Franklin's real on-chain balance, and real accumulated
  ledger history — no unit test substitutes for observing them directly (mirrors
  `franklin-loop-revival`'s own Tier-0 treatment of its equivalent live-artifact/live-log
  proof obligations, PROP-003/009/010/011/013-016).
- **Tier 1** (property tests / boundary tables over pure or thinly-mocked functions): PROP-001,
  PROP-002, PROP-003, PROP-004, PROP-005, PROP-006, PROP-008, PROP-013. These follow the existing
  repo convention (`skills/earn/funding/tests/test_caps.py`'s exhaustive boundary-table style,
  `skills/self/founder-loop/test-founder-loop.sh`'s static-grep + fixture-run bash-test style) —
  consistent with `mode: lean` and with how this feature's OWN direct dependency
  (`skills/earn/funding/`) is already verified in this codebase. PROP-008 is additionally
  discharged by Phase 3 adversary review (a structural/architectural property that a runtime test
  alone cannot fully close). PROP-013 (added 2026-07-08 iteration 2, closes FIND-005) is a
  static-grep structural test in the same style as PROP-006.
- **Tier 2** (lightweight formal/invariant methods): PROP-007 — the four-gate AND composition that
  gates any real (non-dry) money movement is treated as a money-safety invariant (same treatment
  `franklin-loop-revival` gave its per-instance identity gate, PROP-007 there) and gets an
  exhaustive state-table test over the REAL entry script's control flow, not just the isolated
  pure predicates. PROP-012 (added 2026-07-08 iteration 2, closes FIND-006) — the DECIDE
  subprocess's own tool-access privilege is treated as an EQUALLY load-bearing money-safety
  invariant: a structural test over the actual spawn argv/options (not the pure predicates, not
  the wrapper's branches) proves DECIDE cannot itself invoke `run.py`/touch the kill-switch/write
  the ledger, closing the exact gap FIND-006 identified (PROP-007 alone could not observe this
  because the DECIDE child process is not part of "the entry script's control flow").
- **Tier 3** (strong formal proof — Kani/similar): none required. This feature is glue/orchestration
  logic (bash + a handful of pure Python/JS predicates) over an already-pure mechanism
  (`skills/earn/funding/`'s own money-safety rails — this feature's confidence in that mechanism
  rests on direct code inspection matching commit `095a23d`, NOT on
  `MONEY-SAFETY-VERDICT.md`'s own stale prose; see behavioral-spec.md's Context correction, closes
  FIND-004) and a restricted, non-agentic LLM-invocation pattern for DECIDE
  (`runtime/loop/brain.mjs::thinkClaudeP`, closes FIND-001 — NOT `claude-p-mainloop.sh`'s
  full-tool-access pattern, which remains correct only for this feature's own loop-level wrapper);
  no new safety-critical arithmetic or protocol logic is introduced that would warrant a
  heavyweight prover, consistent with the rest of this repo's `node:test`/`pytest` boundary-table
  convention (no Kani/similar used anywhere in `~/anicca`).

## Non-Goals Carried Into Verification

- No proof obligation is written for `skills/earn/funding/lib/caps.py::check_caps`'s own
  per-transfer/daily/cumulative cap correctness, `lib/identity.py`'s recipient-identity
  verification, or `lib/erc20.py`/`lib/solana_rpc.py`'s on-chain-confirm-before-record logic —
  these are already independently specified, implemented, and tested (`skills/earn/funding/tests/`,
  33/33 passing in `tests/test_caps.py` per commit `095a23d`'s own test run, re-confirmed by direct
  code inspection on 2026-07-08 rather than by trusting `MONEY-SAFETY-VERDICT.md`'s own overall
  verdict line, which is stale — see behavioral-spec.md's Context correction, FIND-004). This
  feature only proves it calls into them correctly and never bypasses/duplicates them
  (PROP-005/PROP-007).
- No proof obligation is written for `runtime/loop/catalog-gate.mjs`'s
  `DEFAULT_BOOTSTRAP_RESERVE_USDC` threshold logic itself — this feature only copies its numeric
  DEFAULT value once as `viability_floor_usd`'s own independent default (REQ-004); the two
  thresholds are not wired together at runtime and can be tuned independently thereafter.
- No proof obligation is written for `skills/_shared/lib/solana-verify.mjs::usdcBalance`'s or
  `skills/_shared/lib/ledger.mjs::isProfitable`'s own internal correctness — both are already
  unit-tested in their own test suites (`skills/_shared/lib/__tests__/`); this feature only proves
  it calls them and fails closed on their errors (REQ-002 edge cases).
- No proof obligation is written for the DECIDE step's LLM output QUALITY (i.e., whether the
  agent's economic judgment is "good") — by design (REQ-003), that judgment is the agent's, not a
  formally specifiable property; only its BOUNDS (PROP-001/002/003/004/007, the hard gates it
  cannot override) and its structural PRIVILEGE isolation (PROP-012, the hard boundary it cannot
  bypass either, closes FIND-006) are proof obligations.
