#!/usr/bin/env python3
"""The second door into the reply queue."""
from __future__ import annotations

import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))

import followup_queue  # noqa: E402

NOW = datetime(2026, 8, 6, 15, 0, tzinfo=timezone.utc)


def candidate(thread_id="93000004", sent=0, **extra):
    row = {"thread_id": thread_id, "followups_sent": sent, "silent_days": 9.0}
    row.update(extra)
    return row


def test_each_attempt_gets_its_own_identity():
    """Without the count in the key, follow-up 2 folds into follow-up 1 and never sends."""
    first = followup_queue.build([candidate(sent=0)], now=NOW)["items"][0]
    second = followup_queue.build([candidate(sent=1)], now=NOW)["items"][0]
    assert first["event_key"] != second["event_key"]
    assert second["event_key"] == "coconala:message:v1:93000004:followup-1"


def test_the_key_does_not_move_with_the_clock():
    # Re-running a pass must not send the same follow-up twice.
    later = datetime(2026, 8, 7, 3, 0, tzinfo=timezone.utc)
    assert (followup_queue.build([candidate()], now=NOW)["items"][0]["event_key"]
            == followup_queue.build([candidate()], now=later)["items"][0]["event_key"])


def test_one_message_per_thread_per_pass():
    rows = [candidate(), candidate()]
    assert len(followup_queue.build(rows, now=NOW)["items"]) == 1


def test_a_row_without_a_thread_id_is_dropped():
    assert followup_queue.build([{"followups_sent": 0}], now=NOW)["items"] == []
    assert followup_queue.build([{"thread_id": ""}], now=NOW)["status"] == "queue_empty"


def test_talkroom_url_is_derived_when_absent_and_trusted_when_present():
    derived = followup_queue.build([candidate()], now=NOW)["items"][0]
    assert derived["talkroom_url"] == "https://coconala.com/talkrooms/93000004"
    given = followup_queue.build(
        [candidate(talkroom_url="https://coconala.com/talkrooms/999")], now=NOW)["items"][0]
    assert given["talkroom_url"] == "https://coconala.com/talkrooms/999"


def test_a_foreign_url_is_not_trusted():
    # A url from outside the platform would send the browser somewhere it must never go.
    item = followup_queue.build(
        [candidate(talkroom_url="https://evil.example/talkrooms/1")], now=NOW)["items"][0]
    assert item["talkroom_url"] == "https://coconala.com/talkrooms/93000004"


def test_items_carry_what_the_lane_needs():
    item = followup_queue.build([candidate()], now=NOW)["items"][0]
    assert item["next_action"] == "followup"
    assert item["event_type"] == "followup"
    assert item["covered_event_keys"] == [item["event_key"]]
    # Below a buyer who is waiting on an answer.
    assert item["priority"] == "P2"


def test_empty_input_is_a_state_not_an_error():
    result = followup_queue.build([], now=NOW)
    assert result["status"] == "queue_empty"
    assert result["errors"] == []


def test_the_key_is_a_shape_the_outbox_already_accepts():
    """Measured: the first shape tried was rejected with ValueError("invalid event_key").

    connector_outbox binds a key to its thread, and that binding is what stops a queue
    from writing into someone else's conversation. Fitting the lane to the grammar is
    safer than loosening the grammar for the lane.
    """
    import importlib.util
    import pathlib

    scripts = pathlib.Path(__file__).resolve().parent.parent / "scripts"
    spec = importlib.util.spec_from_file_location("connector_outbox", scripts / "connector_outbox.py")
    outbox = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(outbox)

    item = followup_queue.build([candidate()], now=NOW)["items"][0]
    assert outbox.validate_coconala_event_key(item["event_key"], item["talkroom_id"])
