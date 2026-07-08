"""Unit + integration tests — IMPURE orchestration layer
(skills/earn/hl-trade/lib/reconcile.py, NOT YET IMPLEMENTED).

RED phase (VCSDD Phase 2a). Every I/O-touching function is tested with an INJECTED fake: a
fake `info` object with a stubbed `user_fills_by_time`, a stubbed `record_line` callable, and
temp-dir checkpoint/ledger/lock paths (mirrors sol-trade/lib/record-swap.mjs's injectable-
fetchImpl technique, ported to Python via parameter injection instead of a mocking framework —
per verification-architecture.md's "Purity test rule"). No live Hyperliquid call anywhere in
this file (REQ-E5 / anti-fake gate; the ONLY live call this feature makes is PROP-021's Phase 5
E2E, out of scope here).

Public API this file defines by import (reconcile.py does not exist yet — every test in this
file is expected to fail at collection with ModuleNotFoundError until Phase 2b implements it):

  plan_batch(candidates: list[dict], already_recorded_tids: set[int]) -> dict
      {"steps": [{"fill": <dict>, "action": "skip_duplicate" | "record"}, ...],
       "stop_index": <int index into `candidates` where an UNPROCESSABLE fill halted
                      planning, or None if none was hit>}
      PURE. Walks `candidates` in order. A tid already in `already_recorded_tids` is
      "skip_duplicate" (REQ-B4.1) and never halts the walk. The first fill for which
      is_unprocessable() is True sets `stop_index` to its position and ends the walk right
      there (REQ-B4.2) — no `steps` entry is produced for it or for anything after it, and
      nothing later in `candidates` is ever inspected.

  acquire_lock(lock_path: str):
      Returns an open file handle holding an exclusive, non-blocking flock
      (fcntl.flock(fd, LOCK_EX | LOCK_NB)) on `lock_path`, or None if the lock is already
      held elsewhere (REQ-B10). Caller releases by closing the handle.

  read_checkpoint(path: str) -> int
      Missing/empty/corrupt file -> 0 (REQ-B7). Never raises.

  write_checkpoint(path: str, value: int) -> None
      Atomic (tempfile + os.replace) (REQ-B6).

  already_recorded_tids(ledger_path: str) -> set[int]
      Reads ledger_path's JSONL lines, returns the set of every `fill_tid` present.

  record_line(payload: dict, ledger_path: str) -> dict
      subprocess.run(["node", <record.mjs path>, json.dumps(payload), ledger_path]) — the ONLY
      ledger-mutating call in this feature's Python code (REQ-D1). Not exercised directly in
      this test file (always injected as `record_line_fn` below) — its real subprocess wiring
      is proven by PROP-021's live E2E, not a unit test.

  reconcile(info, address: str, ledger_path: str, checkpoint_path: str, lock_path: str,
            wallet: str, wake: str, now_ms: int, record_line_fn=None) -> dict
      Composition root. `record_line_fn` defaults to the real `record_line` when None; tests
      ALWAYS pass an injected fake so no subprocess/record.mjs call ever happens here.
      Acquires the lock FIRST — if not acquired, returns {"status": "locked", "recorded": 0}
      immediately, touching nothing else (REQ-B10). Otherwise: read_checkpoint -> fetch fills
      via info.user_fills_by_time(address, since, now_ms, aggregate_by_time=False) (REQ-B8) ->
      select_close_fills -> plan_batch against already_recorded_tids(ledger_path) -> walk
      `steps`, calling record_line_fn(payload, ledger_path) for each "record" step; if
      record_line_fn raises, STOP immediately (REQ-B4.3) without attempting anything later in
      `steps`. The checkpoint advances (REQ-B5) to the "time" of the last step that was
      actually handled (skip_duplicate, or record that did not raise) in strict order; it is
      written LAST, after every append attempt has resolved (REQ-B6), and is left UNCHANGED if
      zero steps were handled (REQ-B5/E2). A `fetch` that raises is caught: returns
      {"status": "api-error", "recorded": 0}, checkpoint untouched (REQ-B9). Releases the lock
      after the checkpoint write or on STOP/error.
"""
import fcntl
import json
import os

import pytest

from reconcile import (
    acquire_lock,
    already_recorded_tids,
    plan_batch,
    read_checkpoint,
    reconcile,
    write_checkpoint,
)


# ---------------------------------------------------------------------------------------------
# fixtures / fakes
# ---------------------------------------------------------------------------------------------

class FakeInfo:
    """Stands in for hyperliquid.info.Info — records every call, returns a fixed fill list
    filtered the way the real server would (time >= since), so select_close_fills's OWN
    inclusive re-filter is exercised on top rather than masked by the fake."""

    def __init__(self, fills):
        self._fills = fills
        self.calls = []

    def user_fills_by_time(self, address, since_time_ms, now_ms, aggregate_by_time=False):
        self.calls.append(
            {"address": address, "since_time_ms": since_time_ms, "now_ms": now_ms,
             "aggregate_by_time": aggregate_by_time}
        )
        return [f for f in self._fills if f["time"] >= since_time_ms]


class RaisingFakeInfo:
    def user_fills_by_time(self, *a, **kw):
        raise Exception("timeout")


def make_recording_stub():
    calls = []

    def _stub(payload, ledger_path):
        calls.append(dict(payload))
        return {"ok": True}

    _stub.calls = calls
    return _stub


def make_never_call_stub():
    def _stub(payload, ledger_path):
        raise AssertionError(
            f"record_line_fn must NEVER be invoked for an already-recorded duplicate "
            f"(REQ-B4.1), but was called with payload={payload!r}"
        )

    return _stub


def make_raising_on_nth_call_stub(raise_at_call_number):
    """1-indexed: raises on the Nth successful invocation (after recording it in .calls)."""
    calls = []

    def _stub(payload, ledger_path):
        calls.append(dict(payload))
        if len(calls) == raise_at_call_number:
            raise RuntimeError("simulated record.mjs failure")
        return {"ok": True}

    _stub.calls = calls
    return _stub


def seed_ledger_line(ledger_path, fill_tid):
    """Pre-populate a scratch ledger with one prior HL line carrying `fill_tid`, simulating a
    fill already recorded by a previous reconcile pass (REQ-B4.1 dedup precondition)."""
    line = {
        "ts": 1, "wallet": "0xseed", "source": "hl-trade", "task": "hl-close prior",
        "earn_usdc": 1.0, "cost_usdc": 0.1, "net_usdc": 0.9, "wake": "seed",
        "chain": "hyperliquid", "fill_tid": fill_tid, "confirmed": True, "external": True,
    }
    os.makedirs(os.path.dirname(ledger_path), exist_ok=True)
    with open(ledger_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(line) + "\n")


def paths(tmp_path):
    return (
        str(tmp_path / "earn-ledger.jsonl"),
        str(tmp_path / ".last-fill-ts"),
        str(tmp_path / ".last-fill-ts.lock"),
    )


# ---------------------------------------------------------------------------------------------
# PROP-004 (REQ-B4.1) — idempotency: a duplicate tid is NEVER (re-)recorded
# ---------------------------------------------------------------------------------------------

def test_plan_batch_marks_already_recorded_tid_as_skip_duplicate_and_never_stops():
    candidates = [{"time": 100, "tid": 555, "closedPnl": "1.0", "fee": "0.1"}]
    plan = plan_batch(candidates, already_recorded_tids={555})
    assert plan["stop_index"] is None
    assert len(plan["steps"]) == 1
    assert plan["steps"][0]["action"] == "skip_duplicate"
    assert plan["steps"][0]["fill"]["tid"] == 555


def test_reconcile_never_calls_record_line_fn_for_an_already_recorded_tid(tmp_path):
    ledger_path, checkpoint_path, lock_path = paths(tmp_path)
    seed_ledger_line(ledger_path, fill_tid=555)
    info = FakeInfo([{"time": 100, "tid": 555, "closedPnl": "1.0", "fee": "0.1"}])
    result = reconcile(
        info, "0xaddr", ledger_path, checkpoint_path, lock_path, "0xaddr", "wake1", 999999,
        record_line_fn=make_never_call_stub(),
    )
    assert result["recorded"] == 0


# ---------------------------------------------------------------------------------------------
# PROP-005 (REQ-B4.2/B5) — stop-at-first-unprocessable, no gap-jumping past it
# ---------------------------------------------------------------------------------------------

def test_plan_batch_stops_at_first_unprocessable_fill_and_never_plans_past_it():
    t1 = {"time": 100, "tid": 1, "closedPnl": "1.0", "fee": "0.1"}
    t2_unprocessable = {"time": 200, "tid": 2, "closedPnl": "abc", "fee": "0.1"}  # non-numeric
    t3 = {"time": 300, "tid": 3, "closedPnl": "2.0", "fee": "0.1"}
    plan = plan_batch([t1, t2_unprocessable, t3], already_recorded_tids=set())
    assert plan["stop_index"] == 1
    assert [s["fill"]["tid"] for s in plan["steps"]] == [1]
    assert plan["steps"][0]["action"] == "record"


def test_reconcile_checkpoint_stops_before_unprocessable_fill_t3_never_attempted(tmp_path):
    ledger_path, checkpoint_path, lock_path = paths(tmp_path)
    t1 = {"time": 100, "tid": 1, "closedPnl": "1.0", "fee": "0.1"}
    t2_unprocessable = {"time": 200, "tid": 2, "closedPnl": "abc", "fee": "0.1"}
    t3 = {"time": 300, "tid": 3, "closedPnl": "2.0", "fee": "0.1"}
    info = FakeInfo([t1, t2_unprocessable, t3])
    stub = make_recording_stub()
    result = reconcile(info, "0xaddr", ledger_path, checkpoint_path, lock_path, "0xaddr",
                        "wake1", 999999, record_line_fn=stub)
    assert [p["fill_tid"] for p in stub.calls] == [1]
    assert result["recorded"] == 1
    assert read_checkpoint(checkpoint_path) == 100


# ---------------------------------------------------------------------------------------------
# PROP-006 (REQ-B4.3) — a record.mjs call failure stops the batch (runtime STOP, unknowable to
# the pure plan_batch — this is why reconcile() itself, not plan_batch, must be tested here)
# ---------------------------------------------------------------------------------------------

def test_reconcile_stops_batch_when_record_line_fn_raises_on_second_fill(tmp_path):
    ledger_path, checkpoint_path, lock_path = paths(tmp_path)
    t1 = {"time": 100, "tid": 1, "closedPnl": "1.0", "fee": "0.1"}
    t2 = {"time": 200, "tid": 2, "closedPnl": "2.0", "fee": "0.1"}
    t3 = {"time": 300, "tid": 3, "closedPnl": "3.0", "fee": "0.1"}
    info = FakeInfo([t1, t2, t3])
    stub = make_raising_on_nth_call_stub(raise_at_call_number=2)
    result = reconcile(info, "0xaddr", ledger_path, checkpoint_path, lock_path, "0xaddr",
                        "wake1", 999999, record_line_fn=stub)
    assert [p["fill_tid"] for p in stub.calls] == [1, 2], (
        "t1 recorded, t2 attempted-and-raised, t3 NEVER attempted this pass"
    )
    assert result["recorded"] == 1
    assert read_checkpoint(checkpoint_path) == 100, "checkpoint must not advance past t1"


# ---------------------------------------------------------------------------------------------
# PROP-007 (REQ-B5/B6) — checkpoint advances to the LAST recorded fill's time; atomic write
# ---------------------------------------------------------------------------------------------

def test_reconcile_full_successful_batch_checkpoint_is_last_fills_time_not_first(tmp_path):
    ledger_path, checkpoint_path, lock_path = paths(tmp_path)
    t1 = {"time": 100, "tid": 1, "closedPnl": "1.0", "fee": "0.1"}
    t2 = {"time": 200, "tid": 2, "closedPnl": "2.0", "fee": "0.1"}
    t3 = {"time": 300, "tid": 3, "closedPnl": "3.0", "fee": "0.1"}
    info = FakeInfo([t1, t2, t3])
    stub = make_recording_stub()
    result = reconcile(info, "0xaddr", ledger_path, checkpoint_path, lock_path, "0xaddr",
                        "wake1", 999999, record_line_fn=stub)
    assert result["recorded"] == 3
    assert read_checkpoint(checkpoint_path) == 300


def test_reconcile_py_writes_checkpoint_atomically_static_grep():
    reconcile_py = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                 "lib", "reconcile.py")
    assert os.path.exists(reconcile_py), (
        "lib/reconcile.py does not exist yet (RED phase) — this static check will pass once "
        "Phase 2b implements it with an atomic checkpoint write"
    )
    src = open(reconcile_py, encoding="utf-8").read()
    assert ("os.replace(" in src) or (".replace(" in src and "tempfile" in src), (
        "expected an atomic write (tempfile + os.replace/Path.replace) for the checkpoint file"
    )
    for line in src.splitlines():
        assert not (
            "checkpoint" in line and "open(" in line and ("'w'" in line or '"w"' in line)
        ), f"non-atomic direct overwrite of the checkpoint path found: {line!r}"


# ---------------------------------------------------------------------------------------------
# PROP-008 (REQ-B5 zero-fills case) — checkpoint file bytes IDENTICAL before/after
# ---------------------------------------------------------------------------------------------

def test_reconcile_zero_eligible_fills_leaves_checkpoint_byte_identical(tmp_path):
    ledger_path, checkpoint_path, lock_path = paths(tmp_path)
    write_checkpoint(checkpoint_path, 42)
    before = open(checkpoint_path, "rb").read()
    info = FakeInfo([])  # no fills at all
    result = reconcile(info, "0xaddr", ledger_path, checkpoint_path, lock_path, "0xaddr",
                        "wake1", 999999, record_line_fn=make_never_call_stub())
    after = open(checkpoint_path, "rb").read()
    assert result["recorded"] == 0
    assert before == after


# ---------------------------------------------------------------------------------------------
# PROP-009 (REQ-B7) — missing/corrupt checkpoint -> since_time_ms = 0, never raises
# ---------------------------------------------------------------------------------------------

def test_read_checkpoint_missing_file_returns_zero(tmp_path):
    assert read_checkpoint(str(tmp_path / "does-not-exist")) == 0


def test_read_checkpoint_corrupt_file_returns_zero(tmp_path):
    p = tmp_path / ".last-fill-ts"
    p.write_text("not-a-number", encoding="utf-8")
    assert read_checkpoint(str(p)) == 0


def test_read_checkpoint_empty_file_returns_zero(tmp_path):
    p = tmp_path / ".last-fill-ts"
    p.write_text("", encoding="utf-8")
    assert read_checkpoint(str(p)) == 0


# ---------------------------------------------------------------------------------------------
# PROP-010 (REQ-B8) — bounded query args, INCLUSIVE boundary, never the unbounded `user_fills`
# ---------------------------------------------------------------------------------------------

def test_reconcile_queries_user_fills_by_time_inclusive_not_plus_one(tmp_path):
    ledger_path, checkpoint_path, lock_path = paths(tmp_path)
    write_checkpoint(checkpoint_path, 500)
    info = FakeInfo([])
    reconcile(info, "0xaddr", ledger_path, checkpoint_path, lock_path, "0xaddr", "wake1",
              999999, record_line_fn=make_never_call_stub())
    assert len(info.calls) == 1
    call = info.calls[0]
    assert call["address"] == "0xaddr"
    assert call["since_time_ms"] == 500, "must be the raw checkpoint value, NEVER checkpoint+1"
    assert call["now_ms"] == 999999
    assert call["aggregate_by_time"] is False


def test_reconcile_py_never_calls_unbounded_user_fills_static_grep():
    reconcile_py = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                 "lib", "reconcile.py")
    assert os.path.exists(reconcile_py), "lib/reconcile.py does not exist yet (RED phase)"
    src = open(reconcile_py, encoding="utf-8").read()
    assert "user_fills_by_time" in src
    assert ".user_fills(" not in src, "must never call the unbounded all-time user_fills variant"
    assert "since_time_ms + 1" not in src and "since_time_ms+1" not in src, (
        "the +1 boundary must never reappear anywhere in the implementation (REQ-B8 invariant)"
    )


# ---------------------------------------------------------------------------------------------
# PROP-010b (REQ-B8/B5/B4.1) — tied-timestamp recovery, the F-1 money-safety capstone (EDGE-11)
# ---------------------------------------------------------------------------------------------

def test_tied_timestamp_partial_stop_recovers_the_sibling_fill_on_the_next_pass(tmp_path):
    ledger_path, checkpoint_path, lock_path = paths(tmp_path)
    x = {"time": 500, "tid": 1, "closedPnl": "1.0", "fee": "0.1"}
    y = {"time": 500, "tid": 2, "closedPnl": "2.0", "fee": "0.1"}
    z = {"time": 600, "tid": 3, "closedPnl": "3.0", "fee": "0.1"}
    info = FakeInfo([x, y, z])

    # pass 1: X records; Y raises -> batch STOPS; Z never attempted this pass.
    pass1_stub = make_raising_on_nth_call_stub(raise_at_call_number=2)
    result1 = reconcile(info, "0xaddr", ledger_path, checkpoint_path, lock_path, "0xaddr",
                         "wake1", 999999, record_line_fn=pass1_stub)
    assert [p["fill_tid"] for p in pass1_stub.calls] == [1, 2]
    assert result1["recorded"] == 1
    assert read_checkpoint(checkpoint_path) == 500

    # pass 2: fresh reconcile() call, SAME fake info/ledger/checkpoint state; record_line_fn now
    # succeeds for everything.
    pass2_stub = make_recording_stub()
    result2 = reconcile(info, "0xaddr", ledger_path, checkpoint_path, lock_path, "0xaddr",
                         "wake2", 999999, record_line_fn=pass2_stub)

    assert info.calls[1]["since_time_ms"] == 500, "re-query must be inclusive of 500, not 501"
    assert [p["fill_tid"] for p in pass2_stub.calls] == [2, 3], (
        "X (tid=1) must be skipped as an already-recorded duplicate (REQ-B4.1); "
        "Y (tid=2) must be recorded exactly once this pass; Z (tid=3) recorded normally"
    )
    assert result2["recorded"] == 2
    assert read_checkpoint(checkpoint_path) == 600


# ---------------------------------------------------------------------------------------------
# PROP-011 (REQ-B9) — a live API failure fails the pass closed: nothing recorded, no raise
# ---------------------------------------------------------------------------------------------

def test_reconcile_api_error_returns_status_and_leaves_checkpoint_untouched(tmp_path):
    ledger_path, checkpoint_path, lock_path = paths(tmp_path)
    write_checkpoint(checkpoint_path, 77)
    before = open(checkpoint_path, "rb").read()
    result = reconcile(RaisingFakeInfo(), "0xaddr", ledger_path, checkpoint_path, lock_path,
                        "0xaddr", "wake1", 999999, record_line_fn=make_never_call_stub())
    assert result["status"] == "api-error"
    assert result["recorded"] == 0
    after = open(checkpoint_path, "rb").read()
    assert before == after


# ---------------------------------------------------------------------------------------------
# PROP-012 (REQ-C1) — the exact ledger-line payload shape built for a well-formed fill
# ---------------------------------------------------------------------------------------------

def test_reconcile_builds_payload_with_exactly_the_req_c1_keys(tmp_path):
    ledger_path, checkpoint_path, lock_path = paths(tmp_path)
    fill = {"time": 100, "tid": 42, "closedPnl": "1.23", "fee": "0.01", "coin": "ETH"}
    info = FakeInfo([fill])
    stub = make_recording_stub()
    reconcile(info, "0xaddr", ledger_path, checkpoint_path, lock_path, "0xMyWallet", "wake9",
              999999, record_line_fn=stub)
    assert len(stub.calls) == 1
    payload = stub.calls[0]
    expected_keys = {
        "source", "chain", "fill_tid", "confirmed", "external",
        "earn_usdc", "cost_usdc", "wallet", "task", "wake",
    }
    assert set(payload.keys()) == expected_keys
    assert payload["chain"] == "hyperliquid"
    assert payload["confirmed"] is True
    assert payload["external"] is True
    assert payload["source"] == "hl-trade"
    assert payload["fill_tid"] == 42
    assert payload["wallet"] == "0xMyWallet"
    assert payload["wake"] == "wake9"
    assert abs(payload["earn_usdc"] - 1.23) < 1e-9
    assert abs(payload["cost_usdc"] - 0.01) < 1e-9


# ---------------------------------------------------------------------------------------------
# PROP-015 (REQ-D1) — routes through record.mjs ONLY; never reimplements append/guard/halt
# ---------------------------------------------------------------------------------------------

def test_reconcile_py_never_reimplements_ledger_guards_static_grep():
    reconcile_py = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                 "lib", "reconcile.py")
    assert os.path.exists(reconcile_py), "lib/reconcile.py does not exist yet (RED phase)"
    src = open(reconcile_py, encoding="utf-8").read()
    assert "appendLedger" not in src
    assert "assertOwnIdentityOnly" not in src
    assert "checkHalt" not in src
    assert "record.mjs" in src


# ---------------------------------------------------------------------------------------------
# PROP-016 (REQ-D2) — identity reuse: no second key-loading path added in reconcile.py
# ---------------------------------------------------------------------------------------------

def test_reconcile_py_never_loads_a_second_signing_key_static_grep():
    reconcile_py = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                 "lib", "reconcile.py")
    assert os.path.exists(reconcile_py), "lib/reconcile.py does not exist yet (RED phase)"
    src = open(reconcile_py, encoding="utf-8").read()
    assert "_key(" not in src
    assert "resolve-identity" not in src


def test_hl_py_cmd_reconcile_reuses_clients_static_grep():
    hl_py = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "hl.py")
    src = open(hl_py, encoding="utf-8").read()
    assert "def cmd_reconcile" in src, (
        "hl.py has no cmd_reconcile subcommand yet (RED phase) — Phase 2b wires it through "
        "the existing _clients()"
    )
    # cmd_reconcile's own body must call _clients(), the SAME helper cmd_account/cmd_open/
    # cmd_close already use — never a second key-loading function.
    body = src.split("def cmd_reconcile", 1)[1].split("\ndef ", 1)[0]
    assert "_clients()" in body


# ---------------------------------------------------------------------------------------------
# PROP-017 (REQ-D3) — read-only against the exchange: no order placement anywhere
# ---------------------------------------------------------------------------------------------

def test_reconcile_py_never_places_modifies_or_cancels_orders_static_grep():
    reconcile_py = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                 "lib", "reconcile.py")
    assert os.path.exists(reconcile_py), "lib/reconcile.py does not exist yet (RED phase)"
    src = open(reconcile_py, encoding="utf-8").read()
    assert "market_close" not in src
    assert ".order(" not in src
    assert "update_leverage" not in src


# ---------------------------------------------------------------------------------------------
# PROP-018 (REQ-A1) — the false pre-close closed_pnl_usd field is gone from hl.py entirely
# ---------------------------------------------------------------------------------------------

def test_hl_py_has_no_closed_pnl_usd_field_static_grep():
    hl_py = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "hl.py")
    src = open(hl_py, encoding="utf-8").read()
    assert "closed_pnl_usd" not in src, (
        "hl.py:cmd_close still reports the pre-close unrealizedPnl-derived closed_pnl_usd "
        "field — REQ-A1 requires this field be removed entirely, not relabeled"
    )


def test_hl_py_cmd_close_json_output_has_no_closed_pnl_usd_key():
    pytest.importorskip("hyperliquid", reason=(
        "hyperliquid-python-sdk is not installed in this environment (hl.py imports it at "
        "module scope and calls sys.exit(1) on failure); hl-trade runs this in its own .venv "
        "in production (skills/earn/run.sh:171). This unit test needs that venv to import "
        "hl.py at all — the static grep test above covers the same REQ-A1 assertion without "
        "needing the SDK, and PROP-021's live E2E (Phase 5) exercises the real dependency."
    ))
    import importlib
    import io
    import json as _json
    import contextlib
    import types

    hl = importlib.import_module("hl")

    class FakeExchange:
        def market_close(self, coin):
            return {"status": "ok"}

    class FakeInfoClient:
        def user_state(self, address):
            return {"marginSummary": {"accountValue": "100.0"}, "assetPositions": []}

    fake_w = types.SimpleNamespace(address="0xFAKE")
    hl._clients = lambda: (fake_w, FakeInfoClient(), FakeExchange())  # noqa: SLF001

    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        hl.cmd_close(types.SimpleNamespace(coin="ETH"))
    out = _json.loads(buf.getvalue())
    assert "closed_pnl_usd" not in out


# ---------------------------------------------------------------------------------------------
# PROP-019 (REQ-E3) — run.sh invokes `hl.py reconcile` before cooldown/action branching
# ---------------------------------------------------------------------------------------------

def test_run_sh_calls_hl_reconcile_before_cooldown_and_close_branch_static_grep():
    run_sh = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "run.sh"
    )
    assert os.path.exists(run_sh)
    lines = open(run_sh, encoding="utf-8").read().splitlines()
    reconcile_line = next(
        (i for i, l in enumerate(lines) if "hl.py" in l and "reconcile" in l), None
    )
    assert reconcile_line is not None, (
        "run.sh does not call `hl.py reconcile` yet (RED phase) — REQ-E3 requires it on "
        "EVERY wake that reaches STRATEGY=hl, before cooldown/action branching"
    )
    cooldown_line = next((i for i, l in enumerate(lines) if "_hl_since" in l), None)
    close_branch_line = next(
        (i for i, l in enumerate(lines) if 'ACTION" = "close"' in l or "ACTION='close'" in l), None
    )
    assert cooldown_line is not None
    assert close_branch_line is not None
    assert reconcile_line < cooldown_line
    assert reconcile_line < close_branch_line


# ---------------------------------------------------------------------------------------------
# PROP-022 (REQ-B10) — concurrency lock: a second in-flight reconcile is a same-process no-op
# ---------------------------------------------------------------------------------------------

def test_acquire_lock_second_caller_gets_none_while_first_holds_it(tmp_path):
    lock_path = str(tmp_path / ".last-fill-ts.lock")
    handle_a = acquire_lock(lock_path)
    assert handle_a is not None
    handle_b = acquire_lock(lock_path)
    assert handle_b is None, "a second acquire_lock() call must return None, never block"
    handle_a.close()


def test_reconcile_returns_locked_status_and_touches_nothing_when_lock_held(tmp_path):
    ledger_path, checkpoint_path, lock_path = paths(tmp_path)
    write_checkpoint(checkpoint_path, 10)
    before = open(checkpoint_path, "rb").read()
    holder = acquire_lock(lock_path)
    assert holder is not None
    try:
        info = FakeInfo([{"time": 100, "tid": 1, "closedPnl": "1.0", "fee": "0.1"}])
        result = reconcile(info, "0xaddr", ledger_path, checkpoint_path, lock_path, "0xaddr",
                            "wake1", 999999, record_line_fn=make_never_call_stub())
        assert result == {"status": "locked", "recorded": 0}
        assert info.calls == [], "a locked pass must never even reach the fetch step"
    finally:
        holder.close()
    after = open(checkpoint_path, "rb").read()
    assert before == after


def test_reconcile_py_uses_real_flock_static_grep():
    reconcile_py = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                 "lib", "reconcile.py")
    assert os.path.exists(reconcile_py), "lib/reconcile.py does not exist yet (RED phase)"
    src = open(reconcile_py, encoding="utf-8").read()
    assert "fcntl.flock" in src or "LOCK_EX" in src


# ---------------------------------------------------------------------------------------------
# already_recorded_tids — direct unit coverage (feeds REQ-B4.1's dedup set)
# ---------------------------------------------------------------------------------------------

def test_already_recorded_tids_reads_fill_tid_values_from_the_ledger(tmp_path):
    ledger_path = str(tmp_path / "earn-ledger.jsonl")
    seed_ledger_line(ledger_path, fill_tid=1)
    seed_ledger_line(ledger_path, fill_tid=2)
    assert already_recorded_tids(ledger_path) == {1, 2}


def test_already_recorded_tids_missing_ledger_is_empty_set(tmp_path):
    assert already_recorded_tids(str(tmp_path / "does-not-exist.jsonl")) == set()


# ---------------------------------------------------------------------------------------------
# PROP-023 (REQ-D4, per-instance path isolation) — coverage-retrofit, added at contract-review
# negotiation round 1 (finding F-2). reconcile.py must derive every path it touches (the
# record.mjs it shells out to; any checkpoint/ledger default it computes itself) exclusively
# from its OWN file location (e.g. Path(__file__)-relative) — never a literal reference to
# another instance's home directory or an absolute user path, which would let this feature leak
# across per-instance checkouts (REQ-D4's "never influenced by / never writes to another
# instance's earn-ledger.jsonl or checkpoint file").
# ---------------------------------------------------------------------------------------------

def test_reconcile_py_never_hardcodes_another_instances_home_or_absolute_user_path_static_grep():
    reconcile_py = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                 "lib", "reconcile.py")
    assert os.path.exists(reconcile_py), "lib/reconcile.py does not exist yet (RED phase)"
    src = open(reconcile_py, encoding="utf-8").read()
    for needle in (".blockrun", ".anicca", ".openclaw", "/Users/"):
        assert needle not in src, (
            f"reconcile.py must never hardcode a literal reference to {needle!r} — every path it "
            "touches must derive from its own file location (Path(__file__)-relative), never "
            "another instance's home or an absolute user path (REQ-D4)"
        )


# ---------------------------------------------------------------------------------------------
# PROP-024 (REQ-A3, F-1 fix) — run.sh's own ACTION=close branch never reads closed_pnl_usd and
# never records its own earn_usdc/cost_usdc ledger line for a close: the reconciler (hl.py
# reconcile, invoked earlier this same wake per REQ-E3) is the SOLE recorder of HL realized P&L.
# Added at impl-review iteration 1 (finding F-1): the pre-existing close branch silently
# degraded every real close to a fabricated $0.00 ledger line once REQ-A1 removed
# `closed_pnl_usd` from hl.py's JSON output (`.get('closed_pnl_usd', 0)` unconditionally
# returned 0, no exception). The fix removes this branch's own PNL-recording logic entirely —
# it may still execute the close and echo the result, but it must never call record_line to
# append an earn_usdc/cost_usdc line of its own.
# ---------------------------------------------------------------------------------------------

def test_run_sh_never_references_closed_pnl_usd_anywhere():
    run_sh = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "run.sh"
    )
    src = open(run_sh, encoding="utf-8").read()
    assert "closed_pnl_usd" not in src, (
        "REQ-A3: run.sh must never reference closed_pnl_usd anywhere — the reconciler "
        "(hl.py reconcile) is the sole recorder of HL realized P&L, not run.sh's own "
        "ACTION=close branch"
    )


def test_run_sh_close_branch_never_calls_record_line_for_its_own_pnl_line():
    run_sh = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "run.sh"
    )
    lines = open(run_sh, encoding="utf-8").read().splitlines()
    # NOTE: 'ACTION" = "close"' also appears in the earlier anti-churn cooldown guard's compound
    # condition (`{ [ "$ACTION" = "close" ] || ... }`) — that is NOT this branch. The actual close
    # EXECUTION branch is the one that also gates on `-n "$POS"` (an open position to close).
    close_branch_start = next(
        (i for i, l in enumerate(lines)
         if ('ACTION" = "close"' in l or "ACTION='close'" in l) and '-n "$POS"' in l),
        None,
    )
    assert close_branch_start is not None, "ACTION=close execution branch not found in run.sh"
    # the branch ends at the next top-level "no new trade" narrate block that follows it.
    close_branch_end = next(
        (i for i, l in enumerate(lines)
         if i > close_branch_start and '-z "$SIDE"' in l),
        len(lines),
    )
    branch_src = "\n".join(lines[close_branch_start:close_branch_end])
    assert "record_line" not in branch_src, (
        "REQ-A3: run.sh's ACTION=close branch must not append any earn_usdc/cost_usdc ledger "
        "line of its own — reconcile() (hl.py reconcile, invoked earlier this wake per REQ-E3) "
        "is the SOLE recorder of HL realized P&L; this branch's job is only to execute the "
        "close and echo the result"
    )
