#!/usr/bin/env python3
"""Planning a pass of follow-ups, and recording the ones that landed."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time

SCRIPTS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts")
sys.path.insert(0, SCRIPTS)

import followup_ledger  # noqa: E402

PASS = os.path.join(SCRIPTS, "followup_pass.py")


def run(*args):
    return subprocess.run(
        [sys.executable, PASS, *args], capture_output=True, text=True, check=False
    )


def write(path, value):
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False)
    return str(path)


def test_build_selects_silent_threads_and_explains_the_rest(tmp_path):
    old = int(time.time()) - 9 * 86400
    snapshot = write(tmp_path / "snapshot.json", {"inquiries": [
        {"talkroom_id": "1", "last_message_side": "seller", "seller_sent_at": old},
        # Answered an hour ago: too soon to chase.
        {"talkroom_id": "2", "last_message_side": "seller",
         "seller_sent_at": int(time.time()) - 3600},
        # Their turn, not ours.
        {"talkroom_id": "3", "last_message_side": "buyer",
         "buyer_sent_at": "2026-07-01T00:00:00Z"},
    ]})
    output = str(tmp_path / "queue.json")
    result = run("build", "--snapshot", snapshot, "--transcripts",
                 str(tmp_path / "none.jsonl"), "--ledger", str(tmp_path / "none.jsonl"),
                 "--output", output)
    assert result.returncode == 0, result.stderr
    queue = json.load(open(output, encoding="utf-8"))
    assert [item["talkroom_id"] for item in queue["items"]] == ["1"]
    # A lane that reports "0 items" for a fortnight must say why.
    assert queue["excluded"] == {"too_soon": 1}
    assert queue["considered"] == 2


def test_build_respects_the_per_pass_limit(tmp_path):
    old = int(time.time()) - 9 * 86400
    snapshot = write(tmp_path / "snapshot.json", {"inquiries": [
        {"talkroom_id": str(index), "last_message_side": "seller", "seller_sent_at": old}
        for index in range(1, 8)
    ]})
    output = str(tmp_path / "queue.json")
    run("build", "--snapshot", snapshot, "--transcripts", str(tmp_path / "n.jsonl"),
        "--ledger", str(tmp_path / "n.jsonl"), "--output", output, "--limit", "2")
    assert len(json.load(open(output, encoding="utf-8"))["items"]) == 2


def test_a_missing_snapshot_is_an_empty_queue_not_a_crash(tmp_path):
    output = str(tmp_path / "queue.json")
    result = run("build", "--snapshot", str(tmp_path / "absent.json"),
                 "--transcripts", str(tmp_path / "n.jsonl"),
                 "--ledger", str(tmp_path / "n.jsonl"), "--output", output)
    assert result.returncode == 0
    assert json.load(open(output, encoding="utf-8"))["status"] == "queue_empty"


def test_record_counts_only_a_verified_send(tmp_path):
    # Shape taken from a real reply-lane-result.json: events carry status, not "verified".
    result_path = write(tmp_path / "result.json", {"events": [
        {"talkroom_id": "1", "status": "replied"},
        {"talkroom_id": "2", "status": "failed"},
    ]})
    ledger = str(tmp_path / "followups.jsonl")
    assert run("record", "--result", result_path, "--ledger", ledger).returncode == 0
    assert followup_ledger.followups_sent(ledger) == {"1": 1}


def test_record_accumulates_across_passes(tmp_path):
    result_path = write(tmp_path / "result.json",
                        {"events": [{"talkroom_id": "1", "status": "replied"}]})
    ledger = str(tmp_path / "followups.jsonl")
    run("record", "--result", result_path, "--ledger", ledger)
    run("record", "--result", result_path, "--ledger", ledger)
    assert followup_ledger.followups_sent(ledger) == {"1": 2}


def test_already_contacted_threads_drop_out_of_the_next_build(tmp_path):
    """The cap is counted from the ledger, so build and record have to agree."""
    old = int(time.time()) - 9 * 86400
    snapshot = write(tmp_path / "snapshot.json", {"inquiries": [
        {"talkroom_id": "1", "last_message_side": "seller", "seller_sent_at": old},
    ]})
    ledger = str(tmp_path / "followups.jsonl")
    for _ in range(3):
        followup_ledger.record_followup(ledger, thread_id="1", sent_at=int(time.time()))
    output = str(tmp_path / "queue.json")
    run("build", "--snapshot", snapshot, "--transcripts", str(tmp_path / "n.jsonl"),
        "--ledger", ledger, "--output", output)
    queue = json.load(open(output, encoding="utf-8"))
    assert queue["items"] == []
    assert queue["excluded"] == {"followup_limit": 1}
