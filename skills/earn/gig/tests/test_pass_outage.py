"""A pass that refuses to start must be as loud as one that finishes.

These tests pin the two properties the 2026-07-30 ten-hour outage lacked: the
blocked pass produces exactly one durable human-readable event, and the silence
that no flag explains produces one of its own.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"


def _module(name: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


pass_outage = _module("pass_outage")

# 2026-07-30 08:37:00 JST -- the real outage's start, used as a stable anchor.
OUTAGE_START = 1785368220


@pytest.fixture()
def state_path(tmp_path: Path) -> Path:
    return tmp_path / "pass-outage.json"


def test_first_block_opens_an_outage_and_the_second_stays_quiet(state_path: Path) -> None:
    first = pass_outage.open_outage(
        state_path=state_path,
        reason="stop_flag",
        started_at=OUTAGE_START,
        now=OUTAGE_START,
    )
    assert first is not None
    assert first["reason"] == "stop_flag"
    assert first["started_at"] == OUTAGE_START

    # An hourly wake that observes the same still-raised flag must not re-alert.
    for hour in range(1, 11):
        assert (
            pass_outage.open_outage(
                state_path=state_path,
                reason="stop_flag",
                started_at=OUTAGE_START,
                now=OUTAGE_START + hour * 3600,
            )
            is None
        )


def test_a_second_cause_never_opens_a_competing_outage(state_path: Path) -> None:
    assert pass_outage.open_outage(
        state_path=state_path, reason="stop_flag", started_at=OUTAGE_START, now=OUTAGE_START
    )
    assert (
        pass_outage.open_outage(
            state_path=state_path,
            reason="low_space",
            started_at=OUTAGE_START + 3600,
            now=OUTAGE_START + 3600,
            detail="4",
        )
        is None
    )
    state = json.loads(state_path.read_text(encoding="utf-8"))
    assert state["reason"] == "stop_flag"


def test_recovery_is_pinned_so_a_retry_repeats_the_same_bytes(state_path: Path) -> None:
    pass_outage.open_outage(
        state_path=state_path, reason="stop_flag", started_at=OUTAGE_START, now=OUTAGE_START
    )
    recovered_at = OUTAGE_START + 3 * 3600
    first = pass_outage.close_outage(
        state_path=state_path, scope=pass_outage.LAUNCHER_SCOPE, now=recovered_at
    )
    assert first is not None
    # The publisher crashed between pinning and clearing; the next wake must
    # rebuild a byte-identical message or the outbox rejects the re-enqueue.
    retry = pass_outage.close_outage(
        state_path=state_path, scope=pass_outage.LAUNCHER_SCOPE, now=recovered_at + 7200
    )
    assert retry is not None
    assert pass_outage.recovery_report(first) == pass_outage.recovery_report(retry)

    pass_outage.clear_state(state_path)
    assert (
        pass_outage.close_outage(
            state_path=state_path, scope=pass_outage.LAUNCHER_SCOPE, now=recovered_at + 7200
        )
        is None
    )


def test_a_scope_only_recovers_the_outage_it_owns(state_path: Path) -> None:
    pass_outage.open_outage(
        state_path=state_path, reason="pass_silence", started_at=OUTAGE_START, now=OUTAGE_START
    )
    assert (
        pass_outage.close_outage(
            state_path=state_path, scope=pass_outage.LAUNCHER_SCOPE, now=OUTAGE_START + 3600
        )
        is None
    )
    assert pass_outage.close_outage(
        state_path=state_path, scope=pass_outage.SILENCE_SCOPE, now=OUTAGE_START + 3600
    )


def test_outage_event_key_is_anchored_to_the_outage_start(state_path: Path) -> None:
    record = pass_outage.open_outage(
        state_path=state_path, reason="stop_flag", started_at=OUTAGE_START, now=OUTAGE_START
    )
    key, kind, _ = pass_outage.outage_report(record)
    assert key == f"gig:telegram:pass-outage:v1:stop_flag:{OUTAGE_START}"
    assert kind == "pass_outage"
    recovery_key, recovery_kind, _ = pass_outage.recovery_report(
        pass_outage.close_outage(
            state_path=state_path, scope=pass_outage.LAUNCHER_SCOPE, now=OUTAGE_START + 3600
        )
    )
    assert recovery_key == f"gig:telegram:pass-recovered:v1:stop_flag:{OUTAGE_START}"
    assert recovery_kind == "pass_recovered"


@pytest.mark.parametrize(
    "reason,detail",
    [
        ("stop_flag", ""),
        ("low_space", "4"),
        ("measurement_unavailable", ""),
        ("pass_silence", "36000"),
    ],
)
def test_every_message_reads_as_plain_japanese(reason: str, detail: str, state_path: Path) -> None:
    record = pass_outage.open_outage(
        state_path=state_path,
        reason=reason,
        started_at=OUTAGE_START,
        now=OUTAGE_START,
        detail=detail,
    )
    _, _, message = pass_outage.outage_report(record)
    assert message.startswith("⚠️ ギグの仕事が止まっています")
    # 08:37 JST on 2026-07-30 -- "since when", in the reader's own clock.
    assert "7月30日 08:37" in message
    for jargon in ("78", "exit", "lane", "pass_id", "preflight", "flag", "SLO", "rc="):
        assert jargon not in message, f"{jargon!r} leaked into a human message"
    # "whether it needs a human" is answered explicitly, never left implied.
    assert ("人の対応はいりません" in message) or ("確認してください" in message)


def test_recovery_message_states_how_long_it_was_down(state_path: Path) -> None:
    pass_outage.open_outage(
        state_path=state_path, reason="stop_flag", started_at=OUTAGE_START, now=OUTAGE_START
    )
    record = pass_outage.close_outage(
        state_path=state_path, scope=pass_outage.LAUNCHER_SCOPE, now=OUTAGE_START + 3 * 3600
    )
    _, _, message = pass_outage.recovery_report(record)
    assert message.startswith("✅ ギグの仕事が再開しました")
    assert "3時間" in message


def test_two_short_recoveries_do_not_render_the_same_text(state_path: Path, tmp_path: Path) -> None:
    """Identical bodies are how a real alert gets swallowed.

    The outbox suppresses a body it has already sent for 24 hours (added
    2026-08-04 after one sentence went out 104 times). That protection turns
    into a mute button the moment two different events render the same bytes.
    A recovery under a minute used to render "すぐに元どおりになりました。" and
    nothing else, so today's outage and tomorrow's unrelated one were
    byte-identical and only the first was ever delivered.
    """
    second_path = tmp_path / "second.json"
    pass_outage.open_outage(
        state_path=state_path, reason="stop_flag", started_at=OUTAGE_START, now=OUTAGE_START
    )
    first = pass_outage.close_outage(
        state_path=state_path, scope=pass_outage.LAUNCHER_SCOPE, now=OUTAGE_START + 30
    )
    later = OUTAGE_START + 86400
    pass_outage.open_outage(
        state_path=second_path, reason="stop_flag", started_at=later, now=later
    )
    second = pass_outage.close_outage(
        state_path=second_path, scope=pass_outage.LAUNCHER_SCOPE, now=later + 30
    )

    assert pass_outage.recovery_report(first)[2] != pass_outage.recovery_report(second)[2]


def test_recovery_message_names_what_had_broken(state_path: Path) -> None:
    """"再開しました" alone does not tell Dais which failure just ended."""
    pass_outage.open_outage(
        state_path=state_path, reason="stop_flag", started_at=OUTAGE_START, now=OUTAGE_START
    )
    record = pass_outage.close_outage(
        state_path=state_path, scope=pass_outage.LAUNCHER_SCOPE, now=OUTAGE_START + 30
    )
    message = pass_outage.recovery_report(record)[2]

    assert "7月30日 08:37" in message
    assert "止まっていた原因:" in message


@pytest.mark.parametrize(
    "seconds,expected",
    [
        # A1 rendered anything under a minute as "0分", which reached Dais as
        # "0分ぶりです" -- a duration that cannot exist. A15, 2026-07-30.
        (0, "1分たらず"),
        (31, "1分たらず"),
        (60, "1分"),
        (3540, "59分"),
        (3600, "1時間"),
        (36000, "10時間"),
        (183600, "2日3時間"),
    ],
)
def test_duration_reads_the_way_a_person_would_say_it(seconds: int, expected: str) -> None:
    assert pass_outage.duration_ja(seconds) == expected


def test_silence_threshold_defaults_to_two_hours_and_is_configurable() -> None:
    assert pass_outage.pass_silence_seconds({}) == 2 * 60 * 60
    assert pass_outage.pass_silence_seconds({"GIG_PASS_SILENCE_SECONDS": "900"}) == 900
    # A malformed override must never silence the alarm it configures.
    assert pass_outage.pass_silence_seconds({"GIG_PASS_SILENCE_SECONDS": "soon"}) == 2 * 60 * 60
    assert pass_outage.pass_silence_seconds({"GIG_PASS_SILENCE_SECONDS": "0"}) == 2 * 60 * 60


def test_a_backdated_heartbeat_fires_and_a_fresh_one_does_not(tmp_path: Path) -> None:
    heartbeat = tmp_path / ".last-pass"
    state_path = tmp_path / "pass-outage.json"
    heartbeat.write_text("", encoding="utf-8")
    import os

    now = OUTAGE_START + 10 * 3600
    os.utime(heartbeat, (OUTAGE_START, OUTAGE_START))
    opened = pass_outage.evaluate_pass_silence(
        heartbeat_path=heartbeat, state_path=state_path, now=now, environ={}
    )
    assert opened["action"] == "opened"
    assert opened["record"]["reason"] == "pass_silence"
    assert opened["record"]["started_at"] == OUTAGE_START

    # Same still-silent heartbeat on the next audit: no second alert.
    assert (
        pass_outage.evaluate_pass_silence(
            heartbeat_path=heartbeat, state_path=state_path, now=now + 3600, environ={}
        )["action"]
        == "none"
    )

    # A pass finished: the heartbeat is fresh again and recovery is announced once.
    os.utime(heartbeat, (now + 3600, now + 3600))
    recovered = pass_outage.evaluate_pass_silence(
        heartbeat_path=heartbeat, state_path=state_path, now=now + 3700, environ={}
    )
    assert recovered["action"] == "recovered"
    # The publisher clears only after the event is durably enqueued; until then a
    # retry must keep replaying the same recovery rather than losing it.
    assert (
        pass_outage.evaluate_pass_silence(
            heartbeat_path=heartbeat, state_path=state_path, now=now + 3800, environ={}
        )["action"]
        == "recovered"
    )
    pass_outage.clear_state(state_path)
    assert (
        pass_outage.evaluate_pass_silence(
            heartbeat_path=heartbeat, state_path=state_path, now=now + 7200, environ={}
        )["action"]
        == "none"
    )


def test_a_missing_heartbeat_is_treated_as_silence(tmp_path: Path) -> None:
    result = pass_outage.evaluate_pass_silence(
        heartbeat_path=tmp_path / "never-written",
        state_path=tmp_path / "pass-outage.json",
        now=OUTAGE_START,
        environ={},
    )
    assert result["action"] == "opened"


def test_a_corrupt_state_file_never_suppresses_the_alarm(state_path: Path) -> None:
    state_path.write_text("{not json", encoding="utf-8")
    assert pass_outage.open_outage(
        state_path=state_path, reason="stop_flag", started_at=OUTAGE_START, now=OUTAGE_START
    )
