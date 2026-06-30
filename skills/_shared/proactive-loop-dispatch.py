#!/usr/bin/env python3
"""proactive-loop-dispatch.py — Python orchestrator for proactive-loop.sh.

REQ-P0..P10 8-step body. NO human-touch surfaces.
"""
import json
import os
import sys
import time
from pathlib import Path

shared_dir = os.environ.get("ANICCA_SHARED_DIR", "")
if shared_dir:
    sys.path.insert(0, shared_dir)

from lib.quota_tracker import compute_budget, quantize_budget, Budget  # noqa: E402
from lib.menu import pick_next, load_menu  # noqa: E402
from lib.build_log import append_pass  # noqa: E402
from lib.proactive_loop import should_skip_step6, write_unfixable_cascade_sink  # noqa: E402


def _write_status(slot_dir, **fields):
    p = Path(slot_dir) / "state" / "core-status.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    base = {"ts": int(time.time()), **fields}
    p.write_text(json.dumps(base, indent=2))


def main() -> int:
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

    # STEP 3: health-check (placeholder: real --fix in sprint-2 cycle 2)
    _write_status(slot_dir, slot=slot, status="running", step="3-health-check")
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
        return 0

    # STEP 4: read build_log
    _write_status(slot_dir, slot=slot, status="running", step="4-read-buildlog")

    # STEP 5: pick next from menu
    menu = load_menu(slot_dir / "menu.json")
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
        return 0

    # STEP 6: ACT (cycle 2 wires real action; here we just log the pick)
    _write_status(slot_dir, slot=slot, status="running",
                 step=f"6-act-{picked.get('name')}")

    # STEP 7: update build_log
    append_pass(
        slot_dir / "build_log.md",
        pass_id=pass_id, ts=int(time.time()), budget=budget.value,
        picked=str(picked.get("name", "?")),
        outcome="scaffold-pick-recorded",
        next_candidate="(cycle-2-wires-action)",
    )

    # STEP exit
    _write_status(slot_dir, slot=slot, status="idle", step="done")
    return 0


if __name__ == "__main__":
    sys.exit(main())
