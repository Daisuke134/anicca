#!/usr/bin/env python3
"""proactive-loop-dispatch.py — Python orchestrator for proactive-loop.sh.

REQ-P0..P10 8-step body. NO human-touch surfaces.
"""
import fcntl
import json
import os
import sys
import time
from pathlib import Path

shared_dir = os.environ.get("ANICCA_SHARED_DIR", "")
if shared_dir:
    sys.path.insert(0, shared_dir)

from lib.quota_tracker import (  # noqa: E402
    compute_budget,
    quantize_budget,
    Budget,
    compute_dormant_state,
    resolve_time_horizon_days,
    write_dormant_sentinel,
)
from lib.menu import pick_next, load_menu  # noqa: E402
from lib.build_log import append_pass  # noqa: E402
from lib.proactive_loop import should_skip_step6, write_unfixable_cascade_sink  # noqa: E402
from lib.step6_act import task_descriptor, enqueue_task_descriptor  # noqa: E402
from lib.step3_recipe import execute_recipe, default_restart_cmd_map  # noqa: E402
from lib.roi_track import roi_row, compute_expected_jpy, append_roi_row  # noqa: E402
from lib.reconciler import reconcile as _reconcile_slot  # noqa: E402
from lib.settle_mirror import mirror_earnings_to_settle as _mirror_slot  # noqa: E402


def _acquire_or_exit():
    """REQ-NFR-3 re-entrancy guard: fcntl.flock (cross-platform; macOS has no flock(1))."""
    lock_path = os.environ.get("ANICCA_LOCK_PATH", "")
    if not lock_path:
        return None
    Path(lock_path).parent.mkdir(parents=True, exist_ok=True)
    fh = open(lock_path, "w")
    try:
        fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        sys.stdout.write(f"{time.strftime('%F %T')} proactive-loop: another tick in progress, exit\n")
        sys.stdout.flush()
        fh.close()
        sys.exit(0)
    return fh


def _write_status(slot_dir, **fields):
    p = Path(slot_dir) / "state" / "core-status.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    base = {"ts": int(time.time()), **fields}
    p.write_text(json.dumps(base, indent=2))


def _emit_roi_row(slot_dir, *, slot, pass_id, budget_value, picked, outcome):
    """REQ-W1 canonical exit hook: EVERY tick appends exactly one roi.jsonl
    row. Called from all four exit paths (skip / picked=None / STEP 6 done /
    STEP 6 enqueue-failed). EDGE-E5: picked=None → picked=null in row,
    expected=0."""
    row = roi_row(
        ts=int(time.time()),
        pass_id=pass_id, slot=slot, budget=budget_value,
        picked=picked, outcome=outcome,
        realized=0,  # LAYER C settle wire is sprint-4
        expected=compute_expected_jpy(picked) if isinstance(picked, dict) else 0,
    )
    ar = append_roi_row(Path(slot_dir) / "roi.jsonl", row)
    if not ar.get("ok"):
        _write_status(slot_dir, slot=slot, status="running",
                     step=f"7-{ar.get('status', 'roi-write-failed-unknown')}")


def main() -> int:
    _lock_fh = _acquire_or_exit()  # REQ-NFR-3 fcntl re-entrancy guard
    slot = os.environ.get("ANICCA_SLOT", "gig")
    slot_dir = Path.home() / "loops" / slot
    pass_id = f"p-{int(time.time())}"

    # STEP 0
    _write_status(slot_dir, slot=slot, status="running", step="0-start")

    # STEP 0.5: quota-tracker → budget
    # Sprint-2 cycle 2: real quota probe; here use defaults safely
    remaining_pct = float(os.environ.get("ANICCA_REMAINING_PCT", "50.0"))
    minutes_until_reset = int(os.environ.get("ANICCA_RESET_MIN", "120"))
    b = compute_budget(remaining_pct=remaining_pct, minutes_until_reset=minutes_until_reset)
    budget = quantize_budget(b)
    _write_status(slot_dir, slot=slot, status="running", step=f"0.5-budget={budget.value}")

    # STEP 1: process tasks/
    tasks_dir = slot_dir / "tasks"
    tasks_dir.mkdir(parents=True, exist_ok=True)
    tasks_pending = len(list(tasks_dir.glob("*.txt")) + list(tasks_dir.glob("*.json")))
    _write_status(slot_dir, slot=slot, status="running", step=f"1-tasks={tasks_pending}")

    # STEP 2: pending-questions (READ only; no surfacing to humans per REQ-J8)
    pq = slot_dir / "pending-questions.md"
    pq_count = 0
    if pq.exists():
        pq_count = sum(1 for l in pq.read_text().splitlines() if l.strip().startswith("- "))

    # STEP 3: health-check (FIND-3-003 fix: actually invoke dispatch_highest_priority)
    _write_status(slot_dir, slot=slot, status="running", step="3-health-check")
    try:
        from lib.health_check_v2 import HealthSnapshot, dispatch_highest_priority

        # Build snapshot from os.environ (set by proactive-loop.sh shell front-end).
        snap = HealthSnapshot(
            tmux_alive=os.environ.get("ANICCA_HAS_SESSION", "true").lower() == "true",
            last_pass_mtime=int(os.environ.get("ANICCA_LAST_PASS_MTIME", "0") or 0),
            last_start_mtime=int(os.environ.get("ANICCA_LAST_START_MTIME", "0") or 0),
            restart_log_entries=[int(t) for t in
                os.environ.get("ANICCA_RESTART_LOG", "").splitlines() if t.strip()],
            pane_text=os.environ.get("ANICCA_PANE_TEXT", ""),
            cron_has_slot_job=True,
            spawn_surface_valid=True,
            hook_modules_valid=True,
            now_ts=int(time.time()),
            tmux_server_state="ok",
        )
        # sprint-3 #33 wires REAL action for Issue.kind=='tmux_dead' only.
        # Replicate the highest-priority Issue extraction so we can route by
        # kind, not just action (= FIND-001 INV-P1 fix).
        from lib.health_check_v2 import classify_issue_from_snapshot, PRIORITY_ORDER, select_fix_recipe
        issues = classify_issue_from_snapshot(snap)
        issues.sort(key=lambda i: PRIORITY_ORDER.index(i.kind) if i.kind in PRIORITY_ORDER else 999)
        if issues:
            top = issues[0]
            recipe = select_fix_recipe(top)
            anicca_home = os.environ.get(
                "ANICCA_HOME",
                os.environ.get(
                    "LIFE_MANAGER_STATE_HOME",
                    str(Path.home() / ".local/state/life-manager"),
                ),
            )
            cmd_map = default_restart_cmd_map(anicca_home)
            r = execute_recipe(
                recipe=recipe, issue_kind=top.kind, slot=slot,
                cmd_map=cmd_map, timeout=30,
                anicca_home=anicca_home,
            )
            _write_status(slot_dir, slot=slot, status="running",
                         step=f"3-{r['status']}")
        else:
            _write_status(slot_dir, slot=slot, status="running", step="3-no-issues")
    except Exception as e:
        _write_status(slot_dir, slot=slot, status="running",
                     step=f"3-health-check-error-{type(e).__name__}")

    unfixable_count = 0
    unfixable_path = slot_dir / ".unfixable.jsonl"
    if unfixable_path.exists():
        unfixable_count = sum(1 for l in unfixable_path.read_text().splitlines() if l.strip())

    # SKIP guard
    dormant = (slot_dir / ".dormant.sentinel").exists()
    skip, reason = should_skip_step6(
        budget=budget.value, tasks_pending=tasks_pending,
        dormant=dormant, unfixable_count=unfixable_count,
    )
    if skip:
        _write_status(slot_dir, slot=slot, status="idle", step=f"skip-{reason}")
        append_pass(
            slot_dir / "build_log.md",
            pass_id=pass_id, ts=int(time.time()), budget=budget.value,
            picked="(skipped)", outcome=f"skip:{reason}", next_candidate="(none)",
        )
        # REQ-W1 FIND-001 fix: emit roi row even on skip
        _emit_roi_row(slot_dir, slot=slot, pass_id=pass_id,
                     budget_value=budget.value, picked=None,
                     outcome=f"skip:{reason}")
        return 0

    # STEP 4: read build_log
    _write_status(slot_dir, slot=slot, status="running", step="4-read-buildlog")

    # STEP 5: pick next from menu
    menu = load_menu(slot_dir / "menu.json")

    # sprint-4 (c): live-mode dormant wire — REQ-D1/D1a/D2/D3/D4.
    # Runs AFTER menu load (line ~169) and BEFORE STEP 6 ACT so time_horizon_days
    # is available. Sentinel written this tick takes effect on NEXT tick's SKIP
    # guard (line 147). Fail-closed per REQ-D4 — never aborts this tick.
    try:
        _roi_rows: list[dict] = []
        _roi_path = slot_dir / "roi.jsonl"
        if _roi_path.exists():
            for _ln in _roi_path.read_text().splitlines():
                _ln = _ln.strip()
                if not _ln:
                    continue
                try:
                    _roi_rows.append(json.loads(_ln))
                except (ValueError, TypeError):
                    continue  # EDGE-E6: skip malformed row
        # REQ-D1a: slot_age_days from a durable .slot_created marker (created on
        # first tick if absent). Using stat().st_ctime alone breaks in prod
        # because the dispatcher's own writes to slot_dir bump ctime; the
        # marker is stable across ticks, testable, and portable.
        _marker = slot_dir / ".slot_created"
        _now_ts_i = int(time.time())
        try:
            if _marker.exists():
                _created_ts = int((_marker.read_text().strip() or "0"))
            else:
                _created_ts = _now_ts_i
                try:
                    _marker.write_text(str(_created_ts))
                except OSError:
                    pass  # tolerate; recompute next tick
            _slot_age_days = max(0.0, float(_now_ts_i - _created_ts) / 86400.0)
        except (OSError, ValueError):
            _slot_age_days = 0.0
        _horizon = resolve_time_horizon_days(menu, default=14)
        _dormant_state = compute_dormant_state(
            roi_rows=_roi_rows,
            slot_age_days=_slot_age_days,
            time_horizon_days=_horizon,
            now_ts=int(time.time()),
        )
        # REQ-D2: only write if dormant AND sentinel does not yet exist (idempotent).
        _sentinel_path = slot_dir / ".dormant.sentinel"
        if _dormant_state.get("is_dormant") and not _sentinel_path.exists():
            try:
                write_dormant_sentinel(slot_dir, evidence={
                    "ts": int(time.time()),
                    "live_mode": bool(_dormant_state.get("live_mode")),
                    "consecutive_neg_windows": int(
                        _dormant_state.get("consecutive_neg_windows", 0)),
                    "slot_age_days": float(_slot_age_days),
                    "time_horizon_days": int(_horizon),
                    "window_days": 90,
                })
            except OSError as _sent_err:  # REQ-D4 (e)
                sys.stderr.write(
                    f"[dormant-check] step=3-dormant-check-error-"
                    f"{type(_sent_err).__name__} msg={_sent_err}\n")
    except Exception as _dc_err:  # REQ-D4 catch-all
        sys.stderr.write(
            f"[dormant-check] step=3-dormant-check-error-"
            f"{type(_dc_err).__name__} msg={_dc_err}\n")

    log_tail = []  # cycle 2: parse build_log.md tail
    history = []
    blockers = set()  # cycle 2: compute from slot_state
    picked = pick_next(
        menu=menu, log_tail=log_tail, history=history,
        blockers=blockers, now_ts=int(time.time()), budget=budget,
    )
    if picked is None:
        # EDGE-S4 sink: durable .unfixable.jsonl
        write_unfixable_cascade_sink(
            slot_dir=slot_dir,
            blockers=[c.get("name") for c in menu.get("categories", [])],
            bot2bot_error=None,
        )
        _write_status(slot_dir, slot=slot, status="idle", step="step5-no-unblocked")
        append_pass(
            slot_dir / "build_log.md",
            pass_id=pass_id, ts=int(time.time()), budget=budget.value,
            picked="(none)", outcome="edge-s4-sink", next_candidate="(blocked)",
        )
        # REQ-W1 FIND-001 fix / EDGE-E5: emit roi row with picked=null
        _emit_roi_row(slot_dir, slot=slot, pass_id=pass_id,
                     budget_value=budget.value, picked=None,
                     outcome="edge-s4-sink")
        return 0

    # STEP 6 ACT (sprint-3 #33 wire): enqueue tasks/<ts>-<pass_id>-<name>.json
    # SPRINT-4 (b) FIND-2-001 fix: if picked.category == "reconciler", invoke
    # reconcile in-process and DO NOT enqueue a tasks/ descriptor.
    _write_status(slot_dir, slot=slot, status="running",
                 step=f"6-act-{picked.get('name')}")
    if picked.get("category") == "reconciler":
        report = _reconcile_slot(slot_dir, now_ts=int(time.time()))
        outcome = (f"reconciled:matched={report.get('matched', 0)}/"
                   f"unmatched={report.get('unmatched', 0)}/"
                   f"updated={report.get('updated_rows', 0)}")
        # No task descriptor enqueued. The reconciler already did its work.
    elif picked.get("category") == "settle-mirror":
        # sprint-4 (a2) — earnings.jsonl → settle.jsonl mirror
        earnings_path = Path.home() / slot / "earnings.jsonl"
        r = _mirror_slot(slot_dir, earnings_path, int(time.time()))
        outcome = (f"settle-mirror:new={r.get('new', 0)}/"
                   f"dup={r.get('dup', 0)}/"
                   f"unmatched={r.get('unmatched', 0)}")
    else:
        descriptor = task_descriptor(
            pass_id=pass_id, ts=int(time.time()), picked=picked,
            budget=budget.value, slot=slot,
        )
        enq = enqueue_task_descriptor(slot_dir, descriptor)
        outcome = (
            f"enqueued:{enq['filename']}" if enq.get("ok")
            else f"enqueue-failed:{enq.get('status', 'unknown')}"
        )

    # STEP 7: update build_log
    if picked.get("category") == "reconciler":
        next_cand = "(reconciler-in-process)"
    elif picked.get("category") == "settle-mirror":
        next_cand = "(settle-mirror-in-process)"
    else:
        next_cand = f"(layer-c-dequeue: tasks/{enq.get('filename','?')})"
    append_pass(
        slot_dir / "build_log.md",
        pass_id=pass_id, ts=int(time.time()), budget=budget.value,
        picked=str(picked.get("name", "?")),
        outcome=outcome,
        next_candidate=next_cand,
    )

    # STEP 7.5 (sprint-3 #34): append roi.jsonl row (happy path).
    _emit_roi_row(slot_dir, slot=slot, pass_id=pass_id,
                 budget_value=budget.value, picked=picked, outcome=outcome)

    # STEP exit
    _write_status(slot_dir, slot=slot, status="idle", step="done")
    return 0


if __name__ == "__main__":
    sys.exit(main())
