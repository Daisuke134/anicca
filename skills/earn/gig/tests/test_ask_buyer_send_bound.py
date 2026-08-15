#!/usr/bin/env python3
"""A question that cannot leave must stop being written.

Order 91000001's send failed once, at 2026-08-08 00:56:32. The guard that then froze the
order is fixed elsewhere (tests/test_gig_ask_buyer_unsent_answer.sh); unfreezing it without
this file would replace one silent failure with an hourly one -- compose, fail, forget,
repeat -- because ~/gig/ask-buyer.jsonl is written only after a verified send and is
therefore structurally unable to remember that a send failed.

Shape and reasoning are cbc29d23's: consecutive, per (target, error class), reset by
success, durable, escalated once.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]

TALKROOM = "90000001"
# The real blocker_key for 91000001: sha256 of its buyer feedback.
KEY = "8643236ef2c2b66bde6325dc10e22c006fc6355ba85766971fc1016fad72e7a8"
OTHER_KEY = "b" * 64


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, SKILL / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


attempts = _load("ask_buyer_send_attempts")


def fail(path, key=KEY, reason="paid_answer_send_failed"):
    return attempts.record(path, talkroom_id=TALKROOM, blocker_key=key,
                           outcome="failed", reason=reason, pass_id="test")


def sent(path, key=KEY):
    return attempts.record(path, talkroom_id=TALKROOM, blocker_key=key,
                           outcome="sent", pass_id="test")


# ---------------------------------------------------------------------------
# The counter
# ---------------------------------------------------------------------------

def test_three_identical_failures_in_a_row_reach_the_bound(tmp_path):
    ledger = tmp_path / "ask-buyer-send-attempts.jsonl"
    assert fail(ledger)["exhausted"] is False
    assert fail(ledger)["exhausted"] is False
    third = fail(ledger)
    assert third["consecutive_failures"] == 3
    assert third["exhausted"] is True


def test_the_escalation_happens_once_and_not_again(tmp_path):
    """Otherwise the bound becomes the new hourly noise -- the loop cbc29d23 ended."""
    ledger = tmp_path / "attempts.jsonl"
    assert [fail(ledger)["escalate"] for _ in range(1)] == [False]
    assert fail(ledger)["escalate"] is False
    assert fail(ledger)["escalate"] is True
    assert fail(ledger)["escalate"] is False
    assert fail(ledger)["escalate"] is False


def test_one_verified_send_clears_the_history(tmp_path):
    ledger = tmp_path / "attempts.jsonl"
    fail(ledger)
    fail(ledger)
    sent(ledger)
    after = attempts.verdict(ledger, TALKROOM, KEY)
    assert after["consecutive_failures"] == 0
    assert after["exhausted"] is False


def test_a_different_error_starts_its_own_count(tmp_path):
    """Three flavours of one-off breakage is not the pathology this is looking for."""
    ledger = tmp_path / "attempts.jsonl"
    fail(ledger, reason="paid_answer_send_failed")
    fail(ledger, reason="paid_answer_send_failed")
    third = fail(ledger, reason="paid_answer_copy_failed")
    assert third["consecutive_failures"] == 1
    assert third["exhausted"] is False


def test_another_blocked_state_is_another_conversation(tmp_path):
    """The buyer answered and we are stuck on something new: that earns its own attempts."""
    ledger = tmp_path / "attempts.jsonl"
    for _ in range(3):
        fail(ledger)
    assert attempts.verdict(ledger, TALKROOM, KEY)["exhausted"] is True
    assert attempts.verdict(ledger, TALKROOM, OTHER_KEY)["exhausted"] is False


def test_a_zero_says_how_it_was_counted(tmp_path):
    """"No ledger" and "a ledger with nothing about this target" are the same integer."""
    missing = attempts.verdict(tmp_path / "absent.jsonl", TALKROOM, KEY)
    assert missing["consecutive_failures"] == 0
    assert missing["ledger_present"] is False
    ledger = tmp_path / "attempts.jsonl"
    fail(ledger, key=OTHER_KEY)
    present = attempts.verdict(ledger, TALKROOM, KEY)
    assert present["consecutive_failures"] == 0
    assert present["ledger_present"] is True
    assert present["rows_scanned"] == 1


def test_remote_text_never_lands_in_the_ledger(tmp_path):
    ledger = tmp_path / "attempts.jsonl"
    fail(ledger, reason="送信できませんでした https://coconala.com/talkrooms/90000001")
    row = json.loads(ledger.read_text(encoding="utf-8").splitlines()[0])
    assert row["reason"] == attempts.UNKNOWN_REASON


def test_a_corrupt_line_is_skipped_not_fatal(tmp_path):
    ledger = tmp_path / "attempts.jsonl"
    fail(ledger)
    with ledger.open("a", encoding="utf-8") as handle:
        handle.write("{not json\n")
    fail(ledger)
    assert attempts.verdict(ledger, TALKROOM, KEY)["consecutive_failures"] == 2


def test_an_unusable_target_is_refused_rather_than_counted(tmp_path):
    ledger = tmp_path / "attempts.jsonl"
    assert attempts.record(ledger, talkroom_id="", blocker_key=KEY, outcome="failed")["ok"] is False
    assert not ledger.exists()


# ---------------------------------------------------------------------------
# The wiring: the bound is consulted before the model call, not after it
# ---------------------------------------------------------------------------

ask_buyer_pass = _load("ask_buyer_pass")
paid_work_evidence = _load("paid_work_evidence")


def blocked_project(tmp_path: Path) -> Path:
    """91000001 as it stands: a fresh BLOCKED record about the feedback that is open now."""
    root = tmp_path / "gig" / "projects" / "91000001"
    (root / "requirements").mkdir(parents=True, exist_ok=True)
    (root / "evidence").mkdir(parents=True, exist_ok=True)
    requirements = root / "requirements" / "live-buyer-reply.json"
    requirements.write_text(json.dumps({
        "version": 1, "feedback_sha256": KEY,
        "feedback_text": "よろしくお願いします。\n題材\n『パズルクエストX』",
    }, ensure_ascii=False), encoding="utf-8")
    (root / "evidence" / "acceptance-blocked.json").write_text(json.dumps({
        "version": 1, "status": "BLOCKED",
        "requirements_path": str(requirements), "feedback_sha256": KEY,
        "checks": [{"command": "find source artifacts -type f", "result": "制作の指定がありません。"}],
        "blocker": "何を作る注文かが書かれていないため着手できません。",
    }, ensure_ascii=False), encoding="utf-8")
    return root


def plan(root: Path, tmp_path: Path, send_attempts) -> dict:
    output = tmp_path / "ask-buyer-queue.json"
    args = argparse.Namespace(
        project_root=str(root), talkroom_id=TALKROOM,
        ledger=str(tmp_path / "ask-buyer.jsonl"), output=str(output),
        send_attempts=None if send_attempts is None else str(send_attempts),
    )
    assert ask_buyer_pass.build(args) == 0
    return json.loads(output.read_text(encoding="utf-8"))


def test_the_blocked_order_is_planned_while_the_bound_has_room(tmp_path):
    root = blocked_project(tmp_path)
    ledger = tmp_path / "attempts.jsonl"
    # Verify the fixture is the situation we mean before asserting on the bound.
    assert paid_work_evidence.blocked_evidence_verdict(str(root))[0] == paid_work_evidence.BLOCK_FRESH
    fail(ledger)
    fail(ledger)
    planned = plan(root, tmp_path, ledger)
    assert planned["status"] == "ready"
    assert planned["items"][0]["blocker_key"] == KEY


def test_the_bound_empties_the_queue_the_send_path_reads(tmp_path):
    root = blocked_project(tmp_path)
    ledger = tmp_path / "attempts.jsonl"
    for _ in range(3):
        fail(ledger)
    planned = plan(root, tmp_path, ledger)
    assert planned["items"] == []
    assert planned["send_attempts_exhausted"] == KEY
    assert planned["consecutive_send_failures"] == 3
    assert planned["send_failure_class"] == "paid_answer_send_failed"


def test_without_the_flag_nothing_changes_for_existing_callers(tmp_path):
    root = blocked_project(tmp_path)
    ledger = tmp_path / "attempts.jsonl"
    for _ in range(9):
        fail(ledger)
    planned = plan(root, tmp_path, send_attempts=None)
    assert planned["status"] == "ready"
    assert "send_attempts_exhausted" not in planned


def test_a_verified_send_reopens_the_lane_the_bound_closed(tmp_path):
    """A bound that also silences the future is worse than the loop it replaces."""
    root = blocked_project(tmp_path)
    ledger = tmp_path / "attempts.jsonl"
    for _ in range(3):
        fail(ledger)
    assert plan(root, tmp_path, ledger)["items"] == []
    sent(ledger)
    fail(ledger)
    assert plan(root, tmp_path, ledger)["status"] == "ready"
