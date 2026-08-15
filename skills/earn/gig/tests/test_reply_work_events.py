from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))


# Measured 2026-08-06: the outbox holds 74 replied actions and work-events.jsonl holds a
# single talkroom_reply, left by an implementation that no longer exists. The projector
# emits contract, payment, incident, recovery, application and delivery -- and nothing for
# a reply. The one act that actually reaches a buyer was the one act never recorded as
# work, so the funnel could count it while the event stream could not see it.


def load():
    spec = importlib.util.spec_from_file_location(
        "work_event_projector_reply", SCRIPTS / "work_event_projector.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def verified_event(talkroom_id="93000003", sent="2026-08-06T09:55:24+00:00"):
    # The shape _verified_event() produces in reply_lane; only these reach the result file.
    return {
        "action_id": 70,
        "revision": 2,
        "talkroom_id": talkroom_id,
        "origin_at": "2026-08-04T17:16:36+00:00",
        "seller_sent_at": sent,
        "status": "replied",
    }


def test_a_verified_reply_becomes_a_work_event() -> None:
    m = load()
    events = list(m._reply_events([verified_event()], "pass-1"))
    assert len(events) == 1
    event = events[0]
    assert event["kind"] == "reply"
    assert event["entity_id"] == "93000003"
    assert event["state"] == "verified"
    assert event["event_key"] == "gig:reply:pass-1:93000003"


def test_the_kind_is_reply_not_the_retired_name() -> None:
    # One talkroom_reply row survives from a retired implementation. Reusing that name
    # would make the old row and the new stream indistinguishable.
    m = load()
    events = list(m._reply_events([verified_event()], "pass-1"))
    assert events[0]["kind"] != "talkroom_reply"


def test_an_unverified_reply_is_not_projected() -> None:
    # pending_verify means we could not prove the buyer can see it. Recording that as work
    # would be the fabrication the whole evidence chain exists to prevent.
    m = load()
    unverified = {**verified_event(), "status": "pending_verify"}
    assert list(m._reply_events([unverified], "pass-1")) == []


def test_a_reply_without_a_send_time_is_not_projected() -> None:
    m = load()
    broken = {**verified_event(), "seller_sent_at": ""}
    assert list(m._reply_events([broken], "pass-1")) == []


def test_no_pass_id_projects_nothing() -> None:
    m = load()
    assert list(m._reply_events([verified_event()], None)) == []
    assert list(m._reply_events([verified_event()], "")) == []


def test_two_threads_in_one_pass_get_distinct_keys() -> None:
    m = load()
    events = list(m._reply_events(
        [verified_event("93000003"), verified_event("90000007")], "pass-1"
    ))
    assert len({event["event_key"] for event in events}) == 2


def test_project_writes_the_reply_event(tmp_path) -> None:
    # A pure projector nobody calls emits nothing. _application_events and
    # _delivery_events are both wired into project(); this one must be too, or the 74
    # replies stay invisible exactly as before.
    import json as json_module

    m = load()
    lane_result = tmp_path / "reply-lane-result.json"
    lane_result.write_text(
        json_module.dumps({"replied": 1, "events": [verified_event()]}),
        encoding="utf-8",
    )
    out = tmp_path / "work-events.jsonl"
    empty = tmp_path / "empty.jsonl"
    empty.write_text("", encoding="utf-8")

    result = m.project(
        snapshot_path=None,
        earnings_path=empty,
        failures_path=empty,
        audit_path=empty,
        applications_path=empty,
        paid_progress_path=empty,
        reply_lane_path=lane_result,
        pass_id="pass-1",
        output_path=out,
    )

    assert result["appended"] == 1
    written = [json_module.loads(line) for line in out.read_text(encoding="utf-8").splitlines()]
    assert written[0]["kind"] == "reply"
    assert written[0]["entity_id"] == "93000003"


def test_a_missing_reply_result_is_not_an_error(tmp_path) -> None:
    # Most passes reply to nobody. The projector must stay quiet, not fail.
    m = load()
    out = tmp_path / "work-events.jsonl"
    empty = tmp_path / "empty.jsonl"
    empty.write_text("", encoding="utf-8")

    result = m.project(
        snapshot_path=None,
        earnings_path=empty,
        failures_path=empty,
        audit_path=empty,
        applications_path=empty,
        paid_progress_path=empty,
        reply_lane_path=tmp_path / "absent.json",
        pass_id="pass-1",
        output_path=out,
    )
    assert result["appended"] == 0


def test_the_cli_passes_the_reply_result_through() -> None:
    # project() accepting reply_lane_path is not enough: the production caller is this CLI,
    # invoked from gig_pass.sh. Four separate defects today were "implemented but not
    # wired", so the wiring gets its own test.
    source = (SCRIPTS / "work_event_projector.py").read_text(encoding="utf-8")
    # The whole CLI function: the argument is declared before parse_args and consumed
    # after it, so any window narrower than the function misses one of the two halves.
    start = source.index("def main(")
    cli = source[start:]
    assert "--reply-lane" in cli
    assert "reply_lane_path=args.reply_lane" in cli


def test_the_cli_defaults_to_no_reply_result() -> None:
    # Passes that replied to nobody must not fail for a file that was never written.
    source = (SCRIPTS / "work_event_projector.py").read_text(encoding="utf-8")
    marker = source.index('"--reply-lane"')
    window = source[marker:marker + 200]
    assert "default=None" in window
