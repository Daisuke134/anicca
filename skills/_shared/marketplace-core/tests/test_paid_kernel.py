from __future__ import annotations

import importlib.util
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import sys
import threading
import time


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "paid_kernel.py"
SPEC = importlib.util.spec_from_file_location("marketplace_paid_kernel", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
paid = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = paid
SPEC.loader.exec_module(paid)


def observation(work_id: str, event_id: str = "message-1") -> dict:
    return {
        "provider": "fixture",
        "account_id": "seller-1",
        "work_id": work_id,
        "latest_event_id": event_id,
        "provider_state": "active",
        "observed_at": "2026-09-07T00:00:00Z",
    }


class Adapter:
    def __init__(self, rows: list[dict]):
        self.rows = rows
        self.current = {row["work_id"]: dict(row) for row in rows}
        self.effects: list[dict] = []
        self.readbacks: dict[str, dict] = {}

    def observe_active(self) -> list[dict]:
        return [dict(row) for row in self.rows]

    def observe_one(self, work_id: str) -> dict:
        return dict(self.current[work_id])

    def mutate(self, intent: dict) -> None:
        with getattr(self, "lock", _NullLock()):
            self.effects.append(dict(intent))
            time.sleep(getattr(self, "mutation_delay", 0))
            self.readbacks[intent["effect_key"]] = {
                "verified": True,
                "provider_receipt_id": "receipt-" + intent["work_id"],
                "observed_at": "2026-09-07T00:01:00Z",
            }

    def readback(self, intent: dict) -> dict:
        return dict(self.readbacks.get(intent["effect_key"], {"verified": False}))


class _NullLock:
    def __enter__(self): return self
    def __exit__(self, *_args): return None


def submit(row: dict) -> dict:
    return {"action": "submit", "payload": {"message": "done " + row["work_id"]}}


def test_verified_effect_replays_with_zero_mutations(tmp_path: Path) -> None:
    adapter = Adapter([observation("work-1")])
    first = paid.run_wake(adapter=adapter, decide=submit, state_root=tmp_path)
    second = paid.run_wake(adapter=adapter, decide=submit, state_root=tmp_path)
    assert first["effect"] == 1 and first["readback"] == 1
    assert second["effect"] == 0 and second["readback"] == 1
    assert len(adapter.effects) == 1


def test_new_buyer_event_invalidates_intent_before_mutation(tmp_path: Path) -> None:
    adapter = Adapter([observation("work-1")])

    def decide(row: dict) -> dict:
        adapter.current[row["work_id"]]["latest_event_id"] = "message-2"
        return submit(row)

    result = paid.run_wake(adapter=adapter, decide=decide, state_root=tmp_path)
    assert result["effect"] == 0
    assert result["pending"] == 1
    assert result["items"][0]["reason"] == "newer_provider_event"


def test_blocked_item_does_not_prevent_sibling_effect(tmp_path: Path) -> None:
    adapter = Adapter([observation("blocked"), observation("ready")])

    def decide(row: dict) -> dict:
        if row["work_id"] == "blocked":
            return {"action": "wait", "reason": "external_access", "remaining_work": ["obtain access"]}
        return submit(row)

    result = paid.run_wake(adapter=adapter, decide=decide, state_root=tmp_path)
    assert result["observed"] == 2
    assert result["effect"] == 1
    assert result["pending"] == 1
    assert result["failed"] == 0
    assert [row["work_id"] for row in adapter.effects] == ["ready"]


def test_state_survives_a_new_adapter_process_boundary(tmp_path: Path) -> None:
    first_adapter = Adapter([observation("work-1")])
    assert paid.run_wake(adapter=first_adapter, decide=submit, state_root=tmp_path)["effect"] == 1
    second_adapter = Adapter([observation("work-1")])
    second_adapter.readbacks = dict(first_adapter.readbacks)
    result = paid.run_wake(adapter=second_adapter, decide=submit, state_root=tmp_path)
    assert result["effect"] == 0
    assert result["readback"] == 1
    assert second_adapter.effects == []


def test_two_overlapping_wakes_mutate_same_effect_once(tmp_path: Path) -> None:
    adapter = Adapter([observation("work-1")])
    adapter.lock = threading.Lock()
    adapter.mutation_delay = 0.05
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: paid.run_wake(
            adapter=adapter, decide=submit, state_root=tmp_path
        ), range(2)))
    assert len(adapter.effects) == 1
    assert sorted(result["effect"] for result in results) == [0, 1]


def test_one_failed_decision_does_not_stop_ready_sibling(tmp_path: Path) -> None:
    adapter = Adapter([observation("bad"), observation("ready")])

    def decide(row: dict) -> dict:
        if row["work_id"] == "bad":
            raise RuntimeError("private detail must not enter aggregate")
        return submit(row)

    result = paid.run_wake(adapter=adapter, decide=decide, state_root=tmp_path)
    assert result["observed"] == 2
    assert result["effect"] == 1
    assert result["readback"] == 1
    assert result["failed"] == 1
    assert result["items"][0] == {
        "work_id": "bad", "status": "failed", "reason": "RuntimeError",
        "effect": 0, "readback": 0, "failed": 1,
    }
