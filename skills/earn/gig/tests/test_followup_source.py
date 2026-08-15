#!/usr/bin/env python3
"""Where follow-up candidates come from."""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))

import followup_source  # noqa: E402


def inquiry(talkroom_id="93000004", side="seller", **extra):
    row = {
        "talkroom_id": talkroom_id,
        "last_message_side": side,
        "buyer_sent_at": "2026-07-28T02:00:00Z",
        "talkroom_url": f"https://coconala.com/talkrooms/{talkroom_id}",
        "title": "ロゴ制作のご相談",
    }
    row.update(extra)
    return row


def test_only_threads_where_we_spoke_last():
    snapshot = {"inquiries": [inquiry("1"), inquiry("2", side="buyer")]}
    rows = followup_source.candidate_rows(snapshot)
    assert [row["thread_id"] for row in rows] == ["1"]


def test_a_paying_buyer_is_not_chased_for_a_sale():
    snapshot = {"inquiries": [inquiry("1")], "orders": [{"talkroom_id": "1"}]}
    assert followup_source.candidate_rows(snapshot) == []


def test_the_measured_send_time_beats_the_snapshot_estimate():
    snapshot = {"inquiries": [inquiry("1")]}
    rows = followup_source.candidate_rows(snapshot, send_times={"1": 1_785_000_000})
    assert rows[0]["last_seller_sent_at"] == 1_785_000_000
    assert rows[0]["sent_at_source"] == "transcript"


def test_the_collectors_thread_time_beats_the_buyer_estimate():
    # seller_sent_at is read off the thread itself, so it is exact for every thread --
    # not only the ones answered since transcripts were wired.
    rows = followup_source.candidate_rows(
        {"inquiries": [inquiry("1", seller_sent_at="2026-08-01T09:00:00Z")]})
    assert rows[0]["sent_at_source"] == "seller_sent_at"
    assert rows[0]["last_seller_sent_at"] == 1_785_574_800


def test_the_estimate_is_used_but_labelled():
    # Silence measured from the buyer's message is always longer than the truth, which
    # sends follow-ups early. The row has to admit that.
    rows = followup_source.candidate_rows({"inquiries": [inquiry("1")]})
    assert rows[0]["sent_at_source"] == "buyer_sent_at"
    assert rows[0]["last_seller_sent_at"] == 1_785_204_000


def test_a_thread_with_no_clock_is_kept_but_uncontactable():
    # Dropping it would make a pass report "considered 0" while real threads went
    # unexamined -- indistinguishable from an empty inbox. It is emitted with no clock,
    # so exclusion_reason refuses it by name.
    import followup_candidates

    rows = followup_source.candidate_rows({"inquiries": [inquiry("1", buyer_sent_at=None)]})
    assert rows[0]["last_seller_sent_at"] is None
    assert rows[0]["sent_at_source"] == "unknown"
    assert followup_candidates.exclusion_reason(rows[0], now=1_786_000_000) == "no_send_time"


def test_conversation_is_absent_so_the_send_path_must_check_again():
    rows = followup_source.candidate_rows({"inquiries": [inquiry("1")]})
    assert rows[0]["conversation"] is None


def test_followup_counts_are_carried_through():
    rows = followup_source.candidate_rows(
        {"inquiries": [inquiry("1")]}, followups_sent={"1": 2})
    assert rows[0]["followups_sent"] == 2


def test_transcript_times_take_the_newest_per_thread(tmp_path):
    path = tmp_path / "reply-transcripts.jsonl"
    path.write_text(
        json.dumps({"talkroom_id": "1", "sent_at": 100}) + "\n"
        + json.dumps({"talkroom_id": "1", "sent_at": 900}) + "\n"
        + json.dumps({"talkroom_id": "2", "sent_at": 500}) + "\n",
        encoding="utf-8",
    )
    assert followup_source.transcript_send_times(path) == {"1": 900, "2": 500}


def test_a_broken_log_line_does_not_kill_the_lane(tmp_path):
    path = tmp_path / "reply-transcripts.jsonl"
    path.write_text('{"talkroom_id": "1", "sent_at": 100}\nnot json\n\n', encoding="utf-8")
    assert followup_source.transcript_send_times(path) == {"1": 100}


def test_a_missing_log_reads_as_nothing_known():
    assert followup_source.transcript_send_times("/nonexistent/path.jsonl") == {}


def test_a_non_snapshot_reads_as_nothing():
    assert followup_source.candidate_rows(None) == []
    assert followup_source.candidate_rows({"inquiries": [None, 42]}) == []


def test_silence_is_carried_on_the_row_not_recomputed_later():
    """The first real run drafted three follow-ups that each said 「0 日」.

    Selection reads last_seller_sent_at; the queue item and therefore the prompt read
    silent_days. When only the first existed, every draft told the buyer they had been
    quiet for no time at all.
    """
    now = 1_786_000_000
    rows = followup_source.candidate_rows(
        {"inquiries": [inquiry("1", seller_sent_at=now - 9 * 86400)]}, now=now)
    assert round(rows[0]["silent_days"]) == 9


def test_silence_is_none_when_the_clock_is_unknown():
    rows = followup_source.candidate_rows(
        {"inquiries": [inquiry("1", buyer_sent_at=None)]}, now=1_786_000_000)
    assert rows[0]["silent_days"] is None
