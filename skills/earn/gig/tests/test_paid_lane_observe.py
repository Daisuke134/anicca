from __future__ import annotations

import importlib.util
import json
from pathlib import Path


# P1a-5 wiring. One command the pass can call right after reply_queue drops the paid rooms:
# read the snapshot, enumerate the paid talkrooms, and record who is waiting.
#
# It is placed at that exact line on purpose. `reply_queue.py build` collects the paid
# talkroom ids and skips every one of them; this runs immediately afterwards and picks up
# what was just put down, so the two halves of the decision sit next to each other in the
# pass and cannot drift apart unnoticed.

MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "paid_lane_observe.py"


def load_module():
    spec = importlib.util.spec_from_file_location("paid_lane_observe", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


KITTY = {
    "talkroom_id": "90000004",
    "title": "ウェブ画像の更新と軽微な調整",
    "price_jpy": 2500,
    "status": "paid",
    "buyer_feedback_pending_artifact": True,
    "buyer_feedback_sha256": "9292841a",
    "buyer_visible_artifact_observed": False,
    "formal_delivery_observed": False,
}

DELIVERED = {
    "talkroom_id": "90000005",
    "title": "スクリーンショットのイタリア語化",
    "price_jpy": 4200,
    "buyer_feedback_pending_artifact": False,
    "buyer_visible_artifact_observed": True,
    "formal_delivery_observed": True,
}


def write_snapshot(tmp_path, *orders) -> Path:
    path = tmp_path / "snapshot.json"
    path.write_text(json.dumps({"captured_at": "2026-08-05T00:00:00+00:00", "orders": list(orders)}))
    return path


def test_it_records_the_waiting_buyer_and_not_the_delivered_one(tmp_path, capsys) -> None:
    m = load_module()
    snapshot = write_snapshot(tmp_path, KITTY, DELIVERED)
    store = tmp_path / "sl.jsonl"
    rc = m.main(["--snapshot", str(snapshot), "--store", str(store), "--pass-id", "pass-1"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["open_liabilities"] == 1
    assert payload["rooms_enumerated"] == 2


def test_a_missing_snapshot_is_reported_rather_than_treated_as_no_customers(tmp_path, capsys) -> None:
    m = load_module()
    rc = m.main([
        "--snapshot", str(tmp_path / "absent.json"),
        "--store", str(tmp_path / "sl.jsonl"),
        "--pass-id", "pass-1",
    ])
    assert rc != 0
    assert json.loads(capsys.readouterr().out)["snapshot_missing"] is True


def test_enumeration_errors_survive_into_the_output(tmp_path, capsys) -> None:
    m = load_module()
    snapshot = write_snapshot(tmp_path, KITTY, {"price_jpy": 9000})
    rc = m.main([
        "--snapshot", str(snapshot),
        "--store", str(tmp_path / "sl.jsonl"),
        "--pass-id", "pass-1",
    ])
    payload = json.loads(capsys.readouterr().out)
    assert payload["dropped"] == 1
    assert payload["errors"]
    # A dropped order is a blind spot, not a clean pass.
    assert rc != 0


def test_running_it_twice_in_one_pass_does_not_double_count(tmp_path, capsys) -> None:
    m = load_module()
    snapshot = write_snapshot(tmp_path, KITTY)
    store = tmp_path / "sl.jsonl"
    m.main(["--snapshot", str(snapshot), "--store", str(store), "--pass-id", "pass-1"])
    capsys.readouterr()
    m.main(["--snapshot", str(snapshot), "--store", str(store), "--pass-id", "pass-1"])
    payload = json.loads(capsys.readouterr().out)
    assert payload["oldest_age_passes"] == 1
