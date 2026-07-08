# Verification Architecture — franklin-funding-loop

## Purity Boundary Map

- **Pure Core** (deterministic, no side effects, unit/property testable):
  - `viability_gate(balance_usd, floor_usd) -> {allowed, reason}` (REQ-004) — new pure predicate
    this feature introduces. No I/O.
  - `cooldown_gate(last_sent_ts, now_ts, cooldown_hours) -> {allowed, reason}` (REQ-005) — new
    pure predicate. No I/O.
  - `should_fund(decide_recommendation, viability_result, cooldown_result, killed) -> bool` (REQ-007)
    — pure boolean AND over already-computed inputs. No I/O.
  - `clip_amount(recommended_usd, per_transfer_cap_usd) -> float` (REQ-003 edge case) — pure
    numeric clamp, mirrors the clamping style already used in
    `skills/earn/funding/lib/caps.py::reserve_protected_amount`.
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
  - DECIDE (REQ-003): a real `claude --model claude-sonnet-5 --dangerously-skip-permissions -p
    "$(cat prompt.txt)"` subprocess — genuine LLM judgment, not a pure function; its OUTPUT (a
    parsed recommendation) is what the pure `should_fund`/`clip_amount` functions consume.
  - FUND (REQ-007): `python3 skills/earn/funding/run.py --amount-usd <clipped>` — a real subprocess
    that performs real on-chain transfers via the UNCHANGED, already-adversary-reviewed mechanism.
  - LOG (REQ-008): append-only write to `funding-ledger.jsonl` (reuses
    `skills/earn/funding/lib/ledger.py`'s append convention, or an equivalent append-only writer
    with the same one-JSON-line-per-decision shape).
  - `ai.anicca.franklin-funding-loop.plist` (REQ-009): launchd scheduling configuration.

## Proof Obligations

| ID | Description | Tier | Required | Tool |
|----|-------------|------|----------|------|
| PROP-001 | `viability_gate(balance_usd, floor_usd)`: returns `allowed:false` iff `balance_usd >= floor_usd` (inclusive boundary blocks funding — safety-conservative direction); returns `allowed:false` (fail-closed, never permissive) for non-finite, negative, or non-numeric `floor_usd`/`balance_usd` inputs | 1 | true | pytest boundary table (mirrors `skills/earn/funding/tests/test_caps.py`'s own convention: `balance < floor`, `== floor`, `> floor`, plus bad-input rows) |
| PROP-002 | `cooldown_gate(last_sent_ts, now_ts, cooldown_hours)`: returns `allowed:false` iff `(now_ts - last_sent_ts) < cooldown_hours*3600`; `last_sent_ts is None`/absent (no prior send) always returns `allowed:true`; exactly-at-window boundary returns `allowed:true` (cooldown has elapsed, not still active) | 1 | true | pytest boundary table (no-prior-row, just-under-window, exactly-at-window, well-past-window) |
| PROP-003 | `should_fund(decide_recommendation, viability_result, cooldown_result, killed)` is a strict logical AND: `fund_recommended AND viability_result.allowed AND cooldown_result.allowed AND NOT killed` — exhaustive truth table over all 2^4=16 input combinations matches the AND semantics exactly (REQ-007) | 1 | true | pytest exhaustive truth-table test |
| PROP-004 | `clip_amount(recommended_usd, per_transfer_cap_usd)` never returns a value greater than `per_transfer_cap_usd`, is a no-op when `recommended_usd <= per_transfer_cap_usd`, and returns `0`/fails closed for negative or non-numeric `recommended_usd` (REQ-003 edge case) | 1 | true | pytest boundary table |
| PROP-005 | A synthetic ledger row `{"step": "loop-decide", "status": "sent", "amount_usd": 1000000, "ts": <now>}` fed through the REAL, unmodified `skills/earn/funding/lib/caps.py::_outflow_rows` (imported directly, not reimplemented) is NEVER selected — i.e. it contributes `$0` to `check_caps`'s daily/cumulative totals, proving REQ-008's structural (not conventional) isolation from cap accounting | 1 | true | pytest, imports the real `caps.py` module from `skills/earn/funding/lib` (regression-style cross-feature test — this feature's test suite depends on that module's `step` filter never changing without this test also failing) |
| PROP-006 | Loop-level kill-switch (REQ-001): with `~/.anicca/franklin-funding-loop.pause` (or an injectable test-path equivalent) present, the entry script exits 0 before any OBSERVE read, DECIDE subprocess spawn, or ledger write occurs; with it absent and a live pidfile held by another process, a second concurrent invocation also exits 0 without a second DECIDE/FUND invocation; a stale pidfile (dead PID) is reclaimed, not treated as "already running" | 1 | true | bash test harness in the style of `skills/self/founder-loop/test-founder-loop.sh` (static grep-based structural assertions: kill-switch check precedes any OBSERVE/DECIDE code path; `kill -0` liveness check present) plus behavioral fixture runs with injectable `FRANKLIN_FUNDING_LOOP_TEST` env-scoped paths (mirrors `founder-loop.sh`'s `FOUNDER_TEST=1` convention) |
| PROP-007 | End-to-end gate composition (money-safety invariant): the ONLY code path that can result in a non-dry `run.py` invocation requires, in this exact conjunction, kill-switch absent AND DECIDE `fund_recommended:true` AND `viability_gate.allowed:true` AND `cooldown_gate.allowed:true` — verified as a control-flow invariant over the entry script's actual source (no branch bypasses any one of the four), not merely inferred from the pure unit tests of the individual predicates in isolation | 2 | true | exhaustive state-table test over the REAL entry script (mirrors `franklin-loop-revival`'s PROP-007/PROP-016 treatment of money-safety/identity invariants as Tier 2 — every combination of `{kill-switch present/absent} x {fund_recommended true/false} x {viability allowed/blocked} x {cooldown allowed/blocked}` asserted against whether a (mocked, non-network) `run.py` invocation occurs) |
| PROP-008 | No source file added by this feature contains a numeric threshold, regex, or keyword-based classifier that decides "Franklin is starving/undergrown" — that judgment is produced exclusively by the DECIDE step's LLM subprocess invocation (REQ-003); the wrapper script/gate predicates only consume the LLM's OUTPUT (`fund_recommended`/`amount_usd`), they never independently re-derive it from OBSERVE data | 1 | true | manual/adversary code review (Phase 3) of the implementation diff, checking for any conditional that inspects OBSERVE snapshot fields (balance, ledger rows) to directly set `fund_recommended` without going through the DECIDE subprocess — this is a structural/architectural property, not something a runtime unit test alone can prove, so it is additionally gated by Phase 3 adversary review as a required finding-check |
| PROP-009 | Live smoke check: with the kill-switch absent and a real Franklin balance below `viability_floor_usd`, one full real wake (OBSERVE -> DECIDE -> gates -> at most one `run.py` invocation -> LOG) produces exactly one new `loop-decide` row in `funding-ledger.jsonl`, and if `fund_recommended` was true and both gates passed, a corresponding real `withdraw`/`bridge`/`send_to_franklin` row trio with a matching amount appears in the same ledger within the same wake's time window | 0 | true | live end-to-end smoke run (one supervised, manually-watched invocation before the launchd job is left unattended — mirrors the funding skill's own D1/D2 supervised-first-run precedent) |
| PROP-010 | Autonomy indicator (informational, long-horizon, not a Phase-gating requirement): sampled across `loop-decide` rows in `funding-ledger.jsonl` over multiple real wakes spanning days/weeks, the proportion of wakes where `fund_recommended:true` AND both gates passed trends downward as Franklin's own balance/growth trend rises | 0 | false | periodic manual/dashboard inspection of `funding-ledger.jsonl` history (observational fact about real-world Franklin performance, not independently provable by any test at spec time) |
| PROP-011 | `ai.anicca.franklin-funding-loop.plist` (REQ-009), the deployed file at `~/Library/LaunchAgents/`, has `RunAtLoad=false`, a `StartInterval` present (default 21600), `ProgramArguments` pointing at a script distinct from `claude-p-mainloop.sh` and Franklin's own daemon entry point, and distinct `StandardOutPath`/`StandardErrorPath` values from both of those other jobs | 0 | true | live artifact check: parse the actual deployed plist (`plutil -convert json` or XML parse) and assert the above, plus `launchctl print gui/$(id -u)/ai.anicca.franklin-funding-loop` shows the job loaded |

## Verification Strategy

- **Tier 0** (no formal proof needed — live/operational facts about the real deployed plist, real
  wallet balances, and real ledger content over time): PROP-009, PROP-010, PROP-011. These depend
  on the actual deployed launchd job, Franklin's real on-chain balance, and real accumulated
  ledger history — no unit test substitutes for observing them directly (mirrors
  `franklin-loop-revival`'s own Tier-0 treatment of its equivalent live-artifact/live-log
  proof obligations, PROP-003/009/010/011/013-016).
- **Tier 1** (property tests / boundary tables over pure or thinly-mocked functions): PROP-001,
  PROP-002, PROP-003, PROP-004, PROP-005, PROP-006, PROP-008. These follow the existing repo
  convention (`skills/earn/funding/tests/test_caps.py`'s exhaustive boundary-table style,
  `skills/self/founder-loop/test-founder-loop.sh`'s static-grep + fixture-run bash-test style) —
  consistent with `mode: lean` and with how this feature's OWN direct dependency
  (`skills/earn/funding/`) is already verified in this codebase. PROP-008 is additionally
  discharged by Phase 3 adversary review (a structural/architectural property that a runtime test
  alone cannot fully close).
- **Tier 2** (lightweight formal/invariant methods): PROP-007 — the four-gate AND composition that
  gates any real (non-dry) money movement is treated as a money-safety invariant (same treatment
  `franklin-loop-revival` gave its per-instance identity gate, PROP-007 there) and gets an
  exhaustive state-table test over the REAL entry script's control flow, not just the isolated
  pure predicates.
- **Tier 3** (strong formal proof — Kani/similar): none required. This feature is glue/orchestration
  logic (bash + a handful of pure Python/JS predicates) over an already-pure, already-verified
  mechanism (`skills/earn/funding/`'s own money-safety rails, verified in
  `MONEY-SAFETY-VERDICT.md`) and an already-existing LLM-invocation pattern
  (`claude-p-mainloop.sh`); no new safety-critical arithmetic or protocol logic is introduced that
  would warrant a heavyweight prover, consistent with the rest of this repo's `node:test`/`pytest`
  boundary-table convention (no Kani/similar used anywhere in `~/anicca`).

## Non-Goals Carried Into Verification

- No proof obligation is written for `skills/earn/funding/lib/caps.py::check_caps`'s own
  per-transfer/daily/cumulative cap correctness, `lib/identity.py`'s recipient-identity
  verification, or `lib/erc20.py`/`lib/solana_rpc.py`'s on-chain-confirm-before-record logic —
  these are already independently specified, implemented, tested (`skills/earn/funding/tests/`,
  33+28 passing per `MONEY-SAFETY-VERDICT.md`), and adversary-PASS'd under that skill's own
  (already-complete) VCSDD history. This feature only proves it calls into them correctly and
  never bypasses/duplicates them (PROP-005/PROP-007).
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
  cannot override) are proof obligations.
