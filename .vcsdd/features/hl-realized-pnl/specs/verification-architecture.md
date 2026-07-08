---
feature: hl-realized-pnl
phase: 1b
mode: strict
language: python
generated_at: 2026-07-09
---

# Verification Architecture — hl-realized-pnl

Pairs with `behavioral-spec.md` (same date). New/changed files this feature introduces:

| File | Status | Role |
|---|---|---|
| `skills/earn/hl-trade/lib/fills.py` | NEW | PURE fill-selection + P&L-split functions |
| `skills/earn/hl-trade/lib/reconcile.py` | NEW | EFFECTFUL orchestration (fetch fills, dedup, record, checkpoint) |
| `skills/earn/hl-trade/hl.py` | MODIFIED | `cmd_close` loses `closed_pnl_usd`; new `reconcile` subcommand wires `lib/reconcile.py` through the existing `_clients()` |
| `skills/earn/run.sh` | MODIFIED | `STRATEGY=hl` branch calls `hl.py reconcile` unconditionally, before cooldown/action branching |
| `skills/_shared/lib/ledger.mjs` | MODIFIED | `deriveLine` passthrough + `isProfitable` new disjunct |
| `skills/earn/hl-trade/tests/test_fills.py` | NEW | unit tests, PURE layer |
| `skills/earn/hl-trade/tests/test_reconcile.py` | NEW | unit/integration tests, injected fake `Info` + fake record-call |
| `skills/_shared/lib/__tests__/ledger.test.mjs` | NEW | unit tests for `deriveLine`/`isProfitable` (no existing test file for this module today) |

## Purity boundary map

| Component | Side | Reason |
|---|---|---|
| `fills.select_close_fills(fills, since_time_ms) -> list[dict]` | **PURE** | list-in, list-out; no I/O, no clock read (caller supplies `since_time_ms`) |
| `fills.is_unprocessable(fill: dict) -> bool` | **PURE** | dict-in, bool-out |
| `fills.compute_realized_pnl(closed_pnl: float, fee: float) -> dict` | **PURE** | numbers-in, dict-out |
| `reconcile.plan_batch(candidates, already_recorded_tids) -> {to_record, stop_index}` | **PURE** | pre-computes the REQ-B4 stop-at-first-failure decision as data, so the effectful loop below just executes a plan instead of re-deriving control flow — testable without any I/O |
| `reconcile.acquire_lock(lock_path) -> lock_handle \| None` | **IMPURE** | `fcntl.flock(fd, LOCK_EX \| LOCK_NB)` on a dedicated lock file; returns `None` (never blocks, never raises) if another invocation already holds it (REQ-B10) |
| `reconcile.read_checkpoint(path) -> int` | **IMPURE** | file read; never throws (REQ-B7 — missing/corrupt → `0`) |
| `reconcile.write_checkpoint(path, value)` | **IMPURE** | atomic file write (tempfile + `os.replace`), called LAST (REQ-B6) |
| `reconcile.fetch_fills(info, address, since_time_ms, now_ms)` | **IMPURE** | live HTTP call to Hyperliquid (`Info.user_fills_by_time`) |
| `reconcile.already_recorded_tids(ledger_path) -> set[int]` | **IMPURE** | reads `earn-ledger.jsonl`, extracts `fill_tid` values — read-only |
| `reconcile.record_line(payload: dict, ledger_path: str) -> dict` | **IMPURE** | `subprocess.run(["node", record_mjs_path, json.dumps(payload), ledger_path])` — the ONLY ledger-mutating call in this feature's Python code; delegates identity-guard/HALT/append entirely to `record.mjs` (REQ-D1) |
| `reconcile.reconcile(info, address, ledger_path, checkpoint_path, lock_path, wallet, wake, now_ms) -> dict` | **IMPURE** (composition root) | acquires the lock FIRST (REQ-B10) — returns `{"status":"locked"}` immediately and touches nothing else if not acquired — then wires the pieces above in REQ-B4/B5/B6 order, releasing the lock after the checkpoint write or on STOP/error; the ONLY function `hl.py`'s `cmd_reconcile` calls |
| `hl.py::cmd_reconcile` | **IMPURE** | CLI glue: calls `_clients()` (existing), then `reconcile.reconcile(...)`, prints JSON |
| `hl.py::cmd_close` (post-fix) | **IMPURE**, unchanged shape minus one field | still calls `Exchange.market_close`; no longer reads/reports `unrealizedPnl` as a P&L number |
| `ledger.mjs::deriveLine` | **PURE** | object-in, object-out (unchanged purity; one new conditional field) |
| `ledger.mjs::isProfitable` | **PURE** | object-in, bool-out (unchanged purity; one new disjunct) |

**Purity test rule**: `fills.py` and `reconcile.plan_batch` are unit-tested as plain functions
with fixture data, no network, no filesystem, no subprocess. Every I/O-touching function in
`reconcile.py` is tested with an INJECTED fake (`info` object with a stubbed
`user_fills_by_time`, a stubbed `record_line` callable, a temp-dir checkpoint/ledger path) —
mirrors `sol-trade/lib/record-swap.mjs`'s injectable-`fetchImpl` technique, ported to Python via
constructor/parameter injection instead of a mocking framework.

## Proof obligations (PROP-XXX ↔ REQ-XXX)

Tier 0 = required to land (adversary blocks PASS otherwise). Tier 1 = strong-pass, quality
reinforcement. Tier 2 = live/E2E proof against the real audited Hyperliquid wallet.

| ID | Covers | Tier | Required | Verification (concrete, falsifiable) |
|---|---|---|---|---|
| PROP-001 | REQ-B1 | 0 | yes | Unit: `compute_realized_pnl(2.0, 0.3) == {earn_usdc:2.0, cost_usdc:0.3, net_usdc:1.7}`; `compute_realized_pnl(-1.0, 0.2) == {earn_usdc:0, cost_usdc:1.2, net_usdc:-1.2}`; `compute_realized_pnl(0, 0.1) == {earn_usdc:0, cost_usdc:0.1, net_usdc:-0.1}`. For all three: `net_usdc == closed_pnl - fee` exactly (float tolerance 1e-9). |
| PROP-002 | REQ-B2 | 0 | yes | Unit: fills `[{time:90,closedPnl:"2.0"}, {time:100,closedPnl:"0.0"}, {time:150,closedPnl:"1.5"}]`, `since_time_ms=100` → `select_close_fills(...)` returns exactly `[fill@150]` (excludes `time<100` AND excludes `closedPnl==0`; note the boundary is INCLUSIVE per REQ-B2/B8 — `time==100` is a candidate but this fixture's `time==100` fill is excluded by the `closedPnl==0` rule, not the time rule), sorted ascending. |
| PROP-002b | REQ-B2 (inclusive boundary, tied timestamp) | 0 | yes | Unit: fills `[{time:100,tid:1,closedPnl:"2.0"}, {time:100,tid:2,closedPnl:"1.5"}, {time:150,tid:3,closedPnl:"1.0"}]`, `since_time_ms=100` → `select_close_fills(...)` returns ALL THREE fills including BOTH `tid=1` and `tid=2` at `time==100` (proves the boundary is `>=`, not `>` — a strictly-greater-than implementation fails this test by returning only `[fill@150]`). |
| PROP-003 | REQ-B3 | 0 | yes | Unit: `is_unprocessable({"closedPnl":"abc","fee":"0.1","tid":1}) is True`; `is_unprocessable({"closedPnl":"1.0","tid":1})` (missing `fee`) `is True`; `is_unprocessable({"closedPnl":"1.0","fee":"0.1"})` (missing `tid`) `is True`; `is_unprocessable({"closedPnl":"1.0","fee":"0.1","tid":"not-an-int"}) is True` (non-integer `tid`); `is_unprocessable({"closedPnl":"1.23","fee":"0.01","tid":568915744567876}) is False` (numeric-string P&L/fee fields plus a real integer `tid` from the live HL API shape must parse successfully, not be flagged — shape confirmed live in `evidence/audit-userfills-summary.md`). |
| PROP-004 | REQ-B4.1 (idempotency) | 0 | yes | Unit (`reconcile.py` with injected `already_recorded_tids={555}` and a fake `record_line` that raises `AssertionError` if ever called): candidate fill `tid=555` → `record_line` is NEVER invoked for it; batch result marks it `skipped_duplicate`; checkpoint MAY advance past it. |
| PROP-005 | REQ-B4.2/B5 (stop-at-first-failure, no gaps) | 0 | yes | Unit: 3 candidate fills in time order `[t1 ok, t2 unprocessable, t3 ok]` → only `t1` is recorded; returned checkpoint value `== t1.time` (NOT `t3.time`); `record_line` is called EXACTLY once (for `t1`) — `t3` is never attempted this pass. |
| PROP-006 | REQ-B4.3 (record-call failure stops batch) | 0 | yes | Unit: inject a `record_line` stub that raises on the 2nd of 3 well-formed fills `[t1, t2, t3]` → `record_line` called for `t1` only before the exception path is hit; batch result checkpoint `== t1.time`; `t3` never attempted. |
| PROP-007 | REQ-B5/B6 (checkpoint advance + atomic write) | 0 | yes | Unit: full successful batch recording fills at `[t1,t2,t3]` (`t3` newest) → persisted checkpoint file content `== t3` (not `t1`, not "now"). Static: `grep -n "os.replace\|Path(.*).replace(" skills/earn/hl-trade/lib/reconcile.py` ≥ 1 match; `grep -nE "open\([^)]*checkpoint[^)]*['\"]w['\"]" skills/earn/hl-trade/lib/reconcile.py` = 0 matches (no direct non-atomic overwrite of the checkpoint path). |
| PROP-008 | REQ-B5 (zero-fills case leaves checkpoint untouched) | 0 | yes | Unit: reconcile invoked with a fake `fetch_fills` returning `[]` → checkpoint file bytes are IDENTICAL before/after (hash comparison, not mtime — mirrors `earn-roi-reconciler`'s PROP-I2 style). |
| PROP-009 | REQ-B7 (missing/corrupt checkpoint → `since=0`) | 0 | yes | Unit: checkpoint file absent, and separately containing garbage bytes (`"not-a-number"`) → both cases produce `read_checkpoint(path) == 0`; never raises. |
| PROP-010 | REQ-B8 (bounded query, correct args, never unbounded, INCLUSIVE boundary) | 0 | yes | Unit: injected fake `info.user_fills_by_time` records its call args; assert called with `(address, since_time_ms, now_ms, aggregate_by_time=False)` — NOT `since_time_ms + 1` (a `+1` call fails this test). Static: `grep -n "user_fills_by_time" skills/earn/hl-trade/lib/reconcile.py` ≥ 1 match AND `grep -n "\.user_fills(" skills/earn/hl-trade/lib/reconcile.py` = 0 matches AND `grep -n "since_time_ms + 1\|since_time_ms+1" skills/earn/hl-trade/lib/reconcile.py` = 0 matches (the `+1` boundary must not reappear anywhere in the impl). |
| PROP-010b | REQ-B8/B5/B4.1 (tied-timestamp recovery — the F-1 money-safety capstone, EDGE-11) | 0 | yes | Integration (`test_reconcile.py`, injected fake `info` + fake `record_line`): candidates `[X(t=500,tid=1), Y(t=500,tid=2), Z(t=600,tid=3)]`; pass 1: `record_line` succeeds for `X`, raises for `Y` → batch STOPS, checkpoint persists as `500`. Pass 2 (fresh `reconcile()` call, same fake `info`/ledger/checkpoint state, `record_line` now succeeds for everything): assert (a) `info.user_fills_by_time` was called with `since_time_ms=500` (inclusive, not `501`), (b) `record_line` is invoked for `Y` exactly once and NOT for `X` (already-recorded via tid-dedup, REQ-B4.1), (c) the final checkpoint is `600`. This is the concrete regression test for F-1's failure trace — it MUST fail against a `since_time_ms + 1` implementation and MUST pass against the inclusive one. |
| PROP-022 | REQ-B10 (concurrency lock) | 0 | yes | Integration (`test_reconcile.py`, real `fcntl.flock` against a temp-dir lock file, not a fake): process/thread A acquires the lock and holds it (simulating an in-flight reconcile); process/thread B's `reconcile()` call, invoked concurrently against the SAME lock path, returns `{"status":"locked","recorded":0}` immediately (non-blocking) WITHOUT calling `record_line` or writing the checkpoint. Static: `grep -n "fcntl.flock\|LOCK_EX\|LOCK_NB" skills/earn/hl-trade/lib/reconcile.py` ≥ 1 match. |
| PROP-011 | REQ-B9 (API failure fail-closed) | 0 | yes | Unit: injected `fetch_fills` raises `Exception("timeout")` → `reconcile(...)` returns `{"status":"api-error", "recorded":0}`-shaped dict, does NOT raise to its caller; checkpoint file bytes identical before/after. |
| PROP-012 | REQ-C1 (ledger line shape) | 0 | yes | Unit: for a well-formed candidate fill, the payload dict built by `reconcile.py` immediately before calling `record_line` contains exactly the keys `{source, chain, fill_tid, confirmed, external, earn_usdc, cost_usdc, wallet, task, wake}` with `chain=="hyperliquid"`, `confirmed is True`, `external is True`, `source=="hl-trade"`. |
| PROP-013 | REQ-C2 (`deriveLine` passthrough) | 0 | yes | Unit (`ledger.test.mjs`): `deriveLine({wallet:"w",source:"s",task:"t",earn_usdc:1,cost_usdc:0,wake:"w1",fill_tid:999}).fill_tid === 999`; `deriveLine({...no fill_tid key...})` → resulting object has NO `fill_tid` key at all (`"fill_tid" in line === false`, not merely `undefined`). |
| PROP-014a | REQ-C3 (isProfitable: well-formed HL win) | 0 | yes | Unit: `isProfitable({source:"hl-trade", chain:"hyperliquid", fill_tid:1, confirmed:true, external:true, net_usdc:1.5}) === true`. |
| PROP-014b | REQ-C3 (isProfitable: HL loss still rejected) | 0 | yes | Unit: same line but `net_usdc:-0.5` → `isProfitable(...) === false` (gate 1 unchanged). |
| PROP-014c | REQ-C3 (isProfitable: missing `external` rejected) | 0 | yes | Unit: same well-formed HL line but `external` omitted (or `false`) → `isProfitable(...) === false` (gate 3 unchanged, not bypassed for HL). |
| PROP-014d | REQ-C3 (isProfitable: malformed HL shape rejected) | 0 | yes | Unit: `chain:"hyperliquid"` but `fill_tid` missing, and separately `confirmed:false` → both `isProfitable(...) === false` (neither the EVM nor Solana disjunct accidentally fires for an HL-shaped line lacking `tx`/`sig`). |
| PROP-014e | REQ-C3 (non-regression) | 0 | yes | Unit: re-run `ledger.mjs`'s OWN pre-existing example fixtures (a real EVM row, a real Solana row, a narrate-only row, a swap row — as already documented in `ledger_reader.py`'s module docstring, which mirrors them) through `isProfitable` — results UNCHANGED from before this feature (additive-only diff). |
| PROP-015 | REQ-D1 (routes through `record.mjs` only) | 0 | yes | Static: `grep -n "appendLedger\|assertOwnIdentityOnly\|checkHalt" skills/earn/hl-trade/lib/reconcile.py` = 0 matches AND `grep -n "record.mjs" skills/earn/hl-trade/lib/reconcile.py` ≥ 1 match. |
| PROP-016 | REQ-D2 (identity reuse, no second key path) | 0 | yes | Static: `grep -n "_clients()" skills/earn/hl-trade/hl.py` shows `cmd_reconcile` calling the SAME `_clients()` used by `cmd_account`/`cmd_open`/`cmd_close`; `grep -rn "_key(\|resolve-identity" skills/earn/hl-trade/lib/reconcile.py` = 0 matches (no second key-loading function added outside `hl.py`). |
| PROP-017 | REQ-D3 (read-only against the exchange) | 0 | yes | Static: `grep -n "market_close\|\.order(\|update_leverage" skills/earn/hl-trade/lib/reconcile.py` = 0 matches. |
| PROP-018 | REQ-A1 (false pnl field removed) | 0 | yes | Static: `grep -n "closed_pnl_usd" skills/earn/hl-trade/hl.py` = 0 matches. Unit: `cmd_close`'s JSON-building logic (with a stubbed `Exchange`/`Info`) produces an output dict with NO `closed_pnl_usd` key. |
| PROP-019 | REQ-E3 (reconcile runs before branching, every wake) | 0 | yes | Static: in `skills/earn/run.sh`'s `STRATEGY=hl` block, the line invoking `hl.py reconcile` has a LOWER line number than both the anti-churn cooldown check (`_hl_since`) and the `ACTION = "close"` branch (`grep -n` both patterns, compare line numbers). |
| PROP-020 | REQ-E1/E2 (non-regression, other hl-trade lines + append-only) | 1 | no | Diff review: the existing `open`/`hl-cooldown`/`hl-observe`/`hl-fund-skipped` JSON-construction snippets in `run.sh` are present verbatim in the post-diff file (unchanged); none of them gains an `external` key (`grep -n "'external'" skills/earn/run.sh` shows 0 occurrences outside the new reconcile-related code, since `run.sh` itself never sets `external` — that's exclusively `reconcile.py`'s job now for HL). |
| PROP-021 | Live E2E — the money-correctness capstone (REQ-A2, REQ-B*, REQ-C1) | 2 | yes (Done-gating) | See §Done below. |
| PROP-023 | REQ-D4 (per-instance path isolation) | 0 | yes | Static: `skills/earn/hl-trade/lib/reconcile.py` derives its checkpoint path and ledger-write target exclusively from its own file location / its own checkout's `record.mjs` (e.g. `Path(__file__)`-relative), with `grep -n "\.blockrun\|\.anicca\|\.openclaw\|/Users/" skills/earn/hl-trade/lib/reconcile.py` = 0 matches (no literal reference to any other instance's home or an absolute user path). Added at contract-review negotiation round 1 (finding F-2); test lands as a coverage-retrofit addition in `test_reconcile.py` before Phase 3. |
| PROP-024 | REQ-A3 (run.sh's own close branch never records a pnl-derived line — the F-1 impl-review capstone) | 0 | yes | Static: `grep -n "closed_pnl_usd" skills/earn/run.sh` = 0 matches (the field REQ-A1 removes SHALL NOT be read anywhere in `run.sh`, code or comments). Static/structural: within `run.sh`'s `ACTION="close"` execution branch (the block gated on `[ "$ACTION" = "close" ] && [ -n "$POS" ]`, NOT the earlier anti-churn cooldown's compound condition), `record_line` is NEVER invoked — the branch's only remaining actions are calling `hl.py close`, stamping the anti-churn timestamp, and echoing the raw result before `exit 0`. Added at impl-review iteration 1 (finding F-1): the pre-existing branch's own PNL-extraction + `record_line` call is deleted entirely, not patched — `reconcile()` (PROP-010b et al.) is the sole recorder of HL realized P&L for both explicit and auto-closes. |

30 proof obligations; 28 Tier-0 required; 1 Tier-1 quality check; 1 Tier-2 live capstone
required for Done (strict mode does not waive the Tier-2 obligation).

## Tiering rationale

- **Tier 0** (PROP-001 through PROP-019) = things that, if violated, mean either (a) a real
  loss or gain is mis-recorded or silently dropped, (b) an auto-close is never seen, (c) a
  crash duplicates or gaps the ledger, (d) money-safety gates (identity/HALT) get bypassed, or
  (e) the fix doesn't actually remove the bug it targets. ALL must pass for the adversary gate
  (Phase 1c) and for Phase 3 implementation review — strict mode, no waivers.
- **Tier 1** (PROP-020) = non-regression hygiene; failure means a smell in the diff, not a
  wrong new implementation.
- **Tier 2** (PROP-021) = the only way to actually prove the fill-based pipeline computes the
  CORRECT real-world number, using real settled fills instead of fixtures. Required for Done
  in strict mode (unlike a typical Tier-2 "nice to have" — this feature exists specifically
  because the OLD code's number was wrong, so a fixture-only proof would repeat the same class
  of undetected error).

## Anti-fake gate

- Every Tier-0/Tier-1 test in `test_fills.py` / `test_reconcile.py` / `ledger.test.mjs` uses
  fixture data or injected fakes and MUST be clearly a test file, never presented as the
  production reconcile path (REQ-E5).
- PROP-021 (§Done) is the ONLY place this feature touches a live Hyperliquid endpoint, and it
  is READ-ONLY (`user_fills_by_time` needs no signature) plus WRITE-ONLY to a scratch ledger —
  never the real `earn-ledger.jsonl` and never a real order.
- A "reconcile pipeline verified" claim with no live E2E output (§Done) and no `[MOCKED]` tag
  distinction between unit tests and the E2E run is an automatic Phase 3 adversary FAIL.

## Done (Phase 1b) = live E2E plan (PROP-021)

1. Instantiate `Info(constants.MAINNET_API_URL, skip_ws=True)` — no signing key required;
   `userFills` queries are public reads by address.
2. Call `info.user_fills_by_time(address="0xa3cdd4ec6b94f01826aaf90a6d5538a2aa8c4c21",
   start_time=0, end_time=<now_ms>, aggregate_by_time=False)` for the OLD audited wallet (146
   real historical fills, per the audit in behavioral-spec.md §2 and the pre-fetched raw
   evidence at `evidence/audit-userfills-0xa3cdd4-raw.json` / `evidence/audit-userfills-summary.md`
   — Phase 5 hardening SHALL re-run this live rather than reuse the pre-fetched snapshot, since
   the wallet's history may have grown since Phase 1b).
3. Run the real, non-mocked `select_close_fills` + `compute_realized_pnl` PURE functions over
   this LIVE response (no fixture substitution).
4. Feed the result through `reconcile(...)` end-to-end, pointed at a SCRATCH ledger file and a
   SCRATCH checkpoint file under the scratchpad directory — NEVER the real
   `skills/earn/state/earn-ledger.jsonl` and NEVER the real `.last-fill-ts`. `record_line`'s
   own ledger-path parameter is used to redirect the write (mirrors `record.mjs`'s existing
   `record(jsonStr, ledgerPath)` signature — no new redirection mechanism needed).
5. Assert, against the LIVE data:
   - (a) the number of scratch-ledger lines appended equals the number of live fills with
     `closedPnl != 0` in that address's history — zero silent drops, zero fabricated extras.
   - (b) the SUM of `net_usdc` across the appended scratch-ledger lines equals the SUM of
     `(closedPnl - fee)` computed directly from the raw live API response, within
     `ledger.mjs`'s own 6-decimal rounding tolerance.
   - (c) running the SAME reconcile call a SECOND time (checkpoint now advanced from step 4)
     appends ZERO additional lines — idempotency proven against LIVE data, not just fixtures.
   - (d) none of the appended lines, nor any log line this step produces, contains the words
     "dry", "fake", "mock", or "simulated" (REQ-E5) — this is a real, unmodified, live query
     result being recorded to a disposable scratch path.
   - (e) if the live response for this wallet appears truncated relative to the audited
     146-fill count (a real pagination limit surfaces), THIS is exactly where NFR-1 gets
     resolved: hardening adds chunked re-querying (loop `user_fills_by_time` by time window
     until no new fills return) before Done can be claimed. This spec does not pre-guess that
     outcome.
6. This step spends no money and never touches the real earn ledger or the real hl-trade
   checkpoint — it is read-only against Hyperliquid and write-only to a disposable path.

Done = spec ✓ + test (Tier 0/1, fixture-based) ✓ + impl ✓ + PROP-021 live E2E ✓ +
`vcsdd:vcsdd-adversary` PASS (fresh context, 5 dimensions, 0 blocking findings).
