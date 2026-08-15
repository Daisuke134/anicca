"""Run directly: python3 skills/earn/gig/tests/test_site_ledger_reconcile.py
(NEVER pytest -- the rtk shim blocks it, see repo convention in sibling tests)."""
from __future__ import annotations

import importlib.util
import json
import shutil
import sys
import tempfile
from pathlib import Path


SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
SCRIPT = SCRIPTS_DIR / "site_ledger_reconcile.py"
sys.path.insert(0, str(SCRIPTS_DIR))  # site_ledger_reconcile imports delivery_identity
SPEC = importlib.util.spec_from_file_location("site_ledger_reconcile", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def _order(request_id="111", talkroom_id="9001", **overrides):
    base = {
        "request_id": request_id,
        "talkroom_id": talkroom_id,
        "talkroom_state": "取引中",
        "formal_delivery_control_disabled": False,
        "seller_sent_messages": [],
        "room_contract_kind": "one_shot",
    }
    base.update(overrides)
    return base


def _write(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def test_agreeing_project_produces_all_true_rows():
    tmp = Path(tempfile.mkdtemp())
    try:
        snapshot = {"orders": [_order(talkroom_state="取引中")]}
        _write(tmp / "snapshot.json", snapshot)
        _write(
            tmp / "projects" / "111" / "state.json",
            {"talkroom_state": "取引中", "buyer_visible_artifact_observed": False},
        )

        report = MODULE.scan(tmp / "snapshot.json", tmp / "projects")

        assert report["projects_checked"] == 1, report
        assert report["discrepancies"] == 0, report
        row = report["rows"][0]
        assert row["status"] == "ok"
        assert all(c["agree"] for c in row["checks"]), row
        print("PASS test_agreeing_project_produces_all_true_rows")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_91000001_shaped_blindness_is_recorded_as_a_discrepancy():
    """The real bug this feature exists to catch: site shows a Google-Docs delivery
    message (a link, redacted by the collector to "[redacted-url]") while state.json
    still says buyer_visible_artifact_observed=false and points at a stale artifact."""
    tmp = Path(tempfile.mkdtemp())
    try:
        snapshot = {
            "orders": [
                _order(
                    request_id="91000001",
                    talkroom_id="90000001",
                    talkroom_state="取引中",
                    seller_sent_messages=[
                        {
                            "text": "納品ドキュメント（Googleドキュメント） [redacted-url]",
                            "attachments": [],
                        }
                    ],
                )
            ]
        }
        _write(tmp / "snapshot.json", snapshot)
        _write(
            tmp / "projects" / "91000001" / "state.json",
            {
                "talkroom_state": "取引中",
                "buyer_visible_artifact_observed": False,
                "current_artifact_path": "sample-game-guide-v1.docx",
            },
        )

        report = MODULE.scan(tmp / "snapshot.json", tmp / "projects")

        row = report["rows"][0]
        checks_by_name = {c["name"]: c for c in row["checks"]}
        assert checks_by_name["artifact_visible"]["site_value"] is True
        assert checks_by_name["artifact_visible"]["ledger_value"] is False
        assert checks_by_name["artifact_visible"]["agree"] is False
        assert report["discrepancies"] >= 1, report
        print("PASS test_91000001_shaped_blindness_is_recorded_as_a_discrepancy")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_missing_state_json_is_skipped_not_crashed():
    tmp = Path(tempfile.mkdtemp())
    try:
        snapshot = {"orders": [_order(request_id="222", talkroom_id="9002")]}
        _write(tmp / "snapshot.json", snapshot)
        # no projects/222/state.json written at all

        report = MODULE.scan(tmp / "snapshot.json", tmp / "projects")

        assert report["projects_checked"] == 0, report
        assert report["skipped_no_state"] == 1, report
        assert report["rows"][0]["status"] == "skipped_no_state"
        assert "checks" not in report["rows"][0]
        print("PASS test_missing_state_json_is_skipped_not_crashed")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_malformed_state_json_is_recorded_as_unreadable():
    tmp = Path(tempfile.mkdtemp())
    try:
        snapshot = {"orders": [_order(request_id="333", talkroom_id="9003")]}
        _write(tmp / "snapshot.json", snapshot)
        state_path = tmp / "projects" / "333" / "state.json"
        state_path.parent.mkdir(parents=True)
        state_path.write_text("{not valid json", encoding="utf-8")

        report = MODULE.scan(tmp / "snapshot.json", tmp / "projects")

        assert report["projects_checked"] == 0, report
        assert report["unreadable_state"] == 1, report
        assert report["rows"][0]["status"] == "unreadable_state"
        print("PASS test_malformed_state_json_is_recorded_as_unreadable")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_malformed_snapshot_does_not_crash():
    tmp = Path(tempfile.mkdtemp())
    try:
        (tmp / "snapshot.json").write_text("{not valid json", encoding="utf-8")

        report = MODULE.scan(tmp / "snapshot.json", tmp / "projects")

        assert report["rows"] == []
        assert "error" in report, report
        print("PASS test_malformed_snapshot_does_not_crash")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_subscription_room_with_one_shot_delivery_action_is_a_discrepancy():
    tmp = Path(tempfile.mkdtemp())
    try:
        snapshot = {
            "orders": [
                _order(request_id="444", talkroom_id="9004", room_contract_kind="subscription")
            ]
        }
        _write(tmp / "snapshot.json", snapshot)
        _write(tmp / "projects" / "444" / "state.json", {"talkroom_state": "取引中"})
        _write(
            tmp / "queue.json",
            {"items": [{"talkroom_id": "9004", "delivery_action": "formal"}]},
        )

        report = MODULE.scan(tmp / "snapshot.json", tmp / "projects", tmp / "queue.json")

        row = report["rows"][0]
        contract_check = next(c for c in row["checks"] if c["name"] == "contract_kind")
        assert contract_check["site_value"] == "subscription"
        assert contract_check["ledger_value"] == "formal"
        assert contract_check["agree"] is False
        print("PASS test_subscription_room_with_one_shot_delivery_action_is_a_discrepancy")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_subscription_room_with_no_delivery_action_agrees():
    tmp = Path(tempfile.mkdtemp())
    try:
        snapshot = {
            "orders": [
                _order(request_id="555", talkroom_id="9005", room_contract_kind="subscription")
            ]
        }
        _write(tmp / "snapshot.json", snapshot)
        _write(tmp / "projects" / "555" / "state.json", {"talkroom_state": "取引中"})
        _write(
            tmp / "queue.json",
            {"items": [{"talkroom_id": "9005", "delivery_action": "none"}]},
        )

        report = MODULE.scan(tmp / "snapshot.json", tmp / "projects", tmp / "queue.json")

        row = report["rows"][0]
        contract_check = next(c for c in row["checks"] if c["name"] == "contract_kind")
        assert contract_check["agree"] is True
        print("PASS test_subscription_room_with_no_delivery_action_agrees")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_missing_queue_omits_contract_kind_check_but_keeps_the_others():
    tmp = Path(tempfile.mkdtemp())
    try:
        snapshot = {"orders": [_order(request_id="666", talkroom_id="9006")]}
        _write(tmp / "snapshot.json", snapshot)
        _write(tmp / "projects" / "666" / "state.json", {"talkroom_state": "取引中"})
        # no --queue passed at all

        report = MODULE.scan(tmp / "snapshot.json", tmp / "projects")

        row = report["rows"][0]
        names = {c["name"] for c in row["checks"]}
        assert "contract_kind" not in names
        assert {"transaction_state", "artifact_visible", "control_disabled"} <= names
        print("PASS test_missing_queue_omits_contract_kind_check_but_keeps_the_others")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_control_disabled_coherence_check():
    tmp = Path(tempfile.mkdtemp())
    try:
        snapshot = {
            "orders": [
                _order(request_id="777", talkroom_id="9007", formal_delivery_control_disabled=True)
            ]
        }
        _write(tmp / "snapshot.json", snapshot)
        _write(
            tmp / "projects" / "777" / "state.json",
            {
                "talkroom_state": "取引中",
                "last_delivery_attempt_reason": "formal_delivery_awaiting_buyer_confirmation",
            },
        )

        report = MODULE.scan(tmp / "snapshot.json", tmp / "projects")

        row = report["rows"][0]
        check = next(c for c in row["checks"] if c["name"] == "control_disabled")
        assert check["agree"] is True, check
        print("PASS test_control_disabled_coherence_check")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    test_agreeing_project_produces_all_true_rows()
    test_91000001_shaped_blindness_is_recorded_as_a_discrepancy()
    test_missing_state_json_is_skipped_not_crashed()
    test_malformed_state_json_is_recorded_as_unreadable()
    test_malformed_snapshot_does_not_crash()
    test_subscription_room_with_one_shot_delivery_action_is_a_discrepancy()
    test_subscription_room_with_no_delivery_action_agrees()
    test_missing_queue_omits_contract_kind_check_but_keeps_the_others()
    test_control_disabled_coherence_check()
    print("ALL PASS")
