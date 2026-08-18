#!/usr/bin/env python3
"""One durable, human-readable answer to "why has the gig work stopped?".

Silent success is the bug class this loop already guards against; silent death is
its mirror. On 2026-07-30 the disk sentinel raised its stop flag, the launcher
refused every hourly pass for ten hours, and the only trace was one line per hour
in a launchd error log. Nothing reached Dais.

Two detectors write into the single outage record kept here:

  launcher  the pass was REFUSED before it started, and the reason is known
            (stop flag raised, measured free space below the minimum, or the
            measurement itself unavailable).
  silence   no pass produced a terminal record for longer than the threshold.
            Two shapes hide under that one observation, and pass_health tells
            them apart: pass_silence (nothing ran -- crash, hang, unloaded
            scheduler) and pass_failing (passes ran and died at a nameable
            step). On 2026-07-30 23:51 the second was reported as the first,
            with "the cause is not yet known" and "please go and look" attached
            to nine identical, perfectly named failures.

A failing loop is not announced on sight. pass_health climbs its ladder first --
retry, isolate, file a repair task -- and only a defect that survives all of it
is worth a person's attention. When that message finally goes out it names the
step and the count, and says what was already tried.

Exactly one outage is open at a time and the first cause wins: a known cause is
never overwritten by the symptom it produces. Each detector may only recover the
outage it opened, so "the pass can start again" is never mistaken for "a pass
finished again".

Message text is anchored to the outage's START, never to the current time, for a
mechanical reason: the durable outbox rejects a re-enqueue of the same event key
with a different payload, and this module is called once per hourly wake for as
long as the outage lasts.
"""

from __future__ import annotations

import importlib.util
import json
import os
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Mapping

JST = timezone(timedelta(hours=9))

STATE_VERSION = 1
DEFAULT_STATE_FILENAME = "pass-outage.json"
DEFAULT_HEARTBEAT_FILENAME = ".last-pass"
DEFAULT_FAILURES_FILENAME = "pass-failures.jsonl"
DEFAULT_EVIDENCE_DIRNAME = "evidence"

LAUNCHER_SCOPE = "launcher"
SILENCE_SCOPE = "silence"

# Which detector owns each reason, and therefore which one is allowed to declare
# it recovered. pass_silence and pass_failing are two readings of one silence, so
# they share a scope: whichever was opened, the same observation recovers it.
REASON_SCOPES = {
    "stop_flag": LAUNCHER_SCOPE,
    "low_space": LAUNCHER_SCOPE,
    "measurement_unavailable": LAUNCHER_SCOPE,
    "pass_silence": SILENCE_SCOPE,
    "pass_failing": SILENCE_SCOPE,
}

SILENCE_SECONDS_ENV = "GIG_PASS_SILENCE_SECONDS"


def _pass_health():
    path = Path(__file__).with_name("pass_health.py")
    spec = importlib.util.spec_from_file_location("gig_pass_health", path)
    if spec is None or spec.loader is None:  # pragma: no cover - packaging accident
        raise RuntimeError("cannot load pass_health")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _default_silence_seconds() -> int:
    """Borrow the SLO's own threshold so the alarm and the repair queue agree."""
    path = Path(__file__).with_name("gig_slo.py")
    spec = importlib.util.spec_from_file_location("gig_slo_thresholds", path)
    if spec is None or spec.loader is None:  # pragma: no cover - packaging accident
        return 2 * 60 * 60
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return int(module.PASS_SILENCE_SECONDS)


def pass_silence_seconds(environ: Mapping[str, str] | None = None) -> int:
    """Silence threshold in seconds; the SLO default unless overridden.

    A malformed or non-positive override falls back to the default rather than
    disabling the alarm -- a typo in an environment variable must never be able
    to reproduce the silence this module exists to break.
    """
    default = _default_silence_seconds()
    raw = (os.environ if environ is None else environ).get(SILENCE_SECONDS_ENV)
    if raw is None:
        return default
    try:
        seconds = int(str(raw).strip())
    except (TypeError, ValueError):
        return default
    return seconds if seconds > 0 else default


def read_state(state_path: Path | str) -> dict[str, Any] | None:
    """Return the open outage, or None. A corrupt file reads as "no outage".

    Failing open is deliberate: an unreadable state file must let the next
    observation raise a fresh alarm, never suppress one.
    """
    try:
        state = json.loads(Path(state_path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(state, dict) or state.get("version") != STATE_VERSION:
        return None
    if state.get("reason") not in REASON_SCOPES:
        return None
    return state


def _write_state(state_path: Path | str, state: dict[str, Any]) -> None:
    path = Path(state_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            json.dump(state, stream, ensure_ascii=False, separators=(",", ":"))
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temporary, 0o600)
        os.replace(temporary, path)
    finally:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass


def clear_state(state_path: Path | str) -> None:
    try:
        Path(state_path).unlink()
    except FileNotFoundError:
        pass


def open_outage(
    *,
    state_path: Path | str,
    reason: str,
    started_at: int,
    now: int,
    detail: str = "",
    context: Mapping[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Open an outage. Returns the record only when this call opened it.

    Returning None on every later observation is the whole anti-spam contract:
    the caller alerts exactly when it is handed a record.
    """
    if reason not in REASON_SCOPES:
        raise ValueError(f"unknown outage reason: {reason}")
    if read_state(state_path) is not None:
        return None
    record = {
        "version": STATE_VERSION,
        "reason": reason,
        "scope": REASON_SCOPES[reason],
        "started_at": int(started_at),
        "detail": str(detail or ""),
        # What the message needs and `detail` cannot carry: the step, the streak,
        # and the rungs already climbed. Frozen at open time with the rest of the
        # record, so the text stays byte-identical on every replay.
        "context": dict(context or {}),
        "observed_at": int(now),
        "recovered_at": None,
    }
    _write_state(state_path, record)
    return record


def close_outage(
    *, state_path: Path | str, scope: str, now: int
) -> dict[str, Any] | None:
    """Pin recovery for an outage this scope owns. Returns the record, or None.

    The recovery instant is written back BEFORE the caller publishes, so a crash
    between pinning and clearing replays byte-identical text on the next wake
    instead of tripping the outbox's payload-mismatch guard.
    """
    record = read_state(state_path)
    if record is None or record.get("scope") != scope:
        return None
    if record.get("recovered_at") is None:
        record["recovered_at"] = int(now)
        _write_state(state_path, record)
    return record


def _jst_moment(epoch: int) -> str:
    moment = datetime.fromtimestamp(int(epoch), JST)
    return f"{moment.month}月{moment.day}日 {moment.hour:02d}:{moment.minute:02d}"


SUB_MINUTE_JA = "1分たらず"


def duration_ja(seconds: float) -> str:
    """How a person says a length of time, not how a clock stores one.

    Under a minute reads as "1分たらず", never "0分": a real outage that lasted
    forty seconds is not an outage of no length, and "0分ぶりです" was the one
    sentence in A1's output that could not possibly be true.
    """
    if max(0, int(seconds)) < 60:
        return SUB_MINUTE_JA
    minutes = max(0, int(seconds)) // 60
    if minutes < 60:
        return f"{minutes}分"
    hours = minutes // 60
    if hours < 24:
        return f"{hours}時間"
    days, remaining_hours = divmod(hours, 24)
    return f"{days}日{remaining_hours}時間" if remaining_hours else f"{days}日"


_NO_ACTION_NEEDED = "いまのところ人の対応はいりません。直りしだい、ひとりでに再開します。"


def _cause_and_advice(record: Mapping[str, Any]) -> tuple[str, str]:
    reason = record["reason"]
    detail = str(record.get("detail") or "")
    if reason == "stop_flag":
        return (
            "パソコンの空き容量が足りず、安全のため作業を止めました",
            "空き容量はいま自動で回収中です。" + _NO_ACTION_NEEDED,
        )
    if reason == "low_space":
        room = f"（残り{detail}GB）" if detail.isdigit() else ""
        return (
            f"パソコンの空き容量が足りません{room}",
            "空き容量はいま自動で回収中です。" + _NO_ACTION_NEEDED,
        )
    if reason == "measurement_unavailable":
        return (
            "パソコンの空き容量を確認できませんでした",
            "確認できないまま動かすと危ないので止めています。" + _NO_ACTION_NEEDED,
        )
    if reason == "pass_failing":
        context = record.get("context") or {}
        label = _pass_health().step_label_ja(context.get("step"))
        count = int(context.get("consecutive") or 0)
        attempted = [str(item) for item in (context.get("attempted") or [])]
        if count > 0:
            cause = f"「{label}」でつまずいて、{count}回続けて最後まで終わっていません"
        else:
            # Something is running, but nothing has finished and nothing has
            # filed a failure -- a hang. Naming no step is honest; blaming the
            # wrong one is not.
            cause = "仕事は動いていますが、ひとつも最後まで終わっていません"
        if not attempted:
            # Nothing was climbed, so nothing may be claimed. Reporting a repair
            # that was never booked is the same class of lie as the message this
            # replaces.
            return (
                cause,
                "つまずいた手順をまだ特定できていません。自動で立て直しを続けています。",
            )
        trail = " → ".join(attempted)
        return (
            cause,
            f"試したこと: {trail}。それでも直らないため、この手順そのものを直す作業を予約しました。",
        )
    # Floored to a minute: an aggressive threshold must still read as a duration.
    threshold = f"{duration_ja(max(60, int(detail)))}以上" if detail.isdigit() else "しばらく"
    return (
        f"1時間ごとに動くはずの仕事が、{threshold}ひとつも始まっていません",
        "自動で立て直しを試しています。" + _NO_ACTION_NEEDED,
    )


# 「止まっています」 is a claim about the world, so it is only allowed when the
# world is actually stopped. A loop that runs and dies is spinning, not stopped.
_HEADLINE_STOPPED = "⚠️ ギグの仕事が止まっています"
_HEADLINE_SPINNING = "⚠️ ギグの仕事が空回りしています"
_SINCE_STOPPED = "から止まっています"
_SINCE_SPINNING = "から最後まで終わっていません"


def outage_report(record: Mapping[str, Any]) -> tuple[str, str, str]:
    """(event_key, kind, message) for the start of an outage."""
    cause, advice = _cause_and_advice(record)
    started_at = int(record["started_at"])
    spinning = record["reason"] == "pass_failing"
    message = (
        f"{_HEADLINE_SPINNING if spinning else _HEADLINE_STOPPED}\n"
        f"原因: {cause}\n"
        f"{_jst_moment(started_at)} {_SINCE_SPINNING if spinning else _SINCE_STOPPED}\n"
        f"{advice}"
    )
    return (
        f"gig:telegram:pass-outage:v1:{record['reason']}:{started_at}",
        "pass_outage",
        message,
    )


def recovery_report(record: Mapping[str, Any]) -> tuple[str, str, str]:
    """(event_key, kind, message) for the end of an outage.

    The body carries the moment the outage began and what caused it, and not
    only because it reads better. The outbox suppresses a body it has already
    sent for 24 hours, so two events that render the same bytes collapse into
    one delivery. A sub-minute recovery used to render a single fixed sentence,
    which made every short recovery in a day indistinguishable -- and the
    protection against noise became a mute button on the real signal.
    """
    started_at = int(record["started_at"])
    recovered_at = int(record["recovered_at"])
    elapsed = recovered_at - started_at
    cause, _ = _cause_and_advice(record)
    # "1分たらずぶりです" is not a sentence anyone says.
    second_line = (
        "すぐに元どおりになりました。"
        if elapsed < 60
        else f"{duration_ja(elapsed)}ぶりです。"
    )
    message = (
        "✅ ギグの仕事が再開しました\n"
        f"{_jst_moment(started_at)} からの不調が解消しました。{second_line}\n"
        f"止まっていた原因: {cause}"
    )
    return (
        f"gig:telegram:pass-recovered:v1:{record['reason']}:{started_at}",
        "pass_recovered",
        message,
    )


def evaluate_pass_silence(
    *,
    heartbeat_path: Path | str,
    state_path: Path | str,
    now: int,
    environ: Mapping[str, str] | None = None,
    failures_path: Path | str | None = None,
    evidence_root: Path | str | None = None,
    isolation_path: Path | str | None = None,
    repair_database: Path | str | None = None,
    source_root: Path | str | None = None,
    running_passes: int | None = None,
) -> dict[str, Any]:
    """Catch the deaths no flag explains -- and separate them from the failures.

    The heartbeat is written only by finalize_success, so a pass that starts and
    then dies is indistinguishable from one that never woke *from that file
    alone*. Every additional argument here exists to break that tie; each is
    optional, so A1's original call site keeps its exact behaviour and reads as
    "dead" the way it always did.

    When the loop is failing rather than dead, the ladder runs BEFORE anyone is
    told: retry at 1, isolate at 3, file a repair task at 5. Only past 5 does a
    record come back, which is what makes a message mean something.

    Returns {"action": "opened"|"recovered"|"none", "record": ..., "health":
    ..., "ladder": ...}.
    """
    threshold = pass_silence_seconds(environ)
    health = _pass_health()
    if running_passes is None:
        running_passes = health.probe_running_passes()

    verdict = health.classify(
        heartbeat_path=heartbeat_path,
        failures_path=failures_path,
        evidence_root=evidence_root,
        now=now,
        running_passes=running_passes,
        silence_seconds=threshold,
    )
    state = verdict["state"]
    decision = health.ladder_decision(
        step=verdict["step"], consecutive=verdict["consecutive"]
    )

    if state == health.STATE_HEALTHY:
        # A step that ran in the successful pass has proved itself; anything
        # still isolated keeps its window and lapses on its own.
        if isolation_path is not None:
            health.release_steps(
                store_path=isolation_path,
                steps=verdict["last_success_steps"],
                now=now,
            )
        record = close_outage(state_path=state_path, scope=SILENCE_SCOPE, now=now)
        if record is None:
            return {"action": "none", "record": None, "health": verdict, "ladder": decision}
        return {"action": "recovered", "record": record, "health": verdict, "ladder": decision}

    if state == health.STATE_DEAD:
        record = open_outage(
            state_path=state_path,
            reason="pass_silence",
            # Anchor on the last real completion when there is one; a heartbeat
            # that never existed anchors on this observation.
            started_at=verdict["last_success_at"] if verdict["last_success_at"] is not None else now,
            now=now,
            detail=str(threshold),
        )
        if record is None:
            return {
                "action": "none",
                "record": read_state(state_path),
                "health": verdict,
                "ladder": decision,
            }
        return {"action": "opened", "record": record, "health": verdict, "ladder": decision}

    # Failing. Climb every rung this streak has earned, lowest first.
    if decision["isolate"] and verdict["step"] and isolation_path is not None:
        health.isolate_step(
            store_path=isolation_path,
            step=verdict["step"],
            reason=verdict["reason"],
            consecutive=verdict["consecutive"],
            now=now,
        )
    if decision["repair_task"] and verdict["step"] and repair_database is not None:
        health.open_repair_task(
            repair_database=repair_database,
            step=verdict["step"],
            reason=verdict["reason"],
            consecutive=verdict["consecutive"],
            evidence_dirs=verdict["evidence_dirs"],
            source_file=(
                health.locate_reason_source(verdict["reason"] or "", source_root)
                if source_root is not None
                else None
            ),
            first_failure_at=verdict["first_failure_at"],
            last_failure_at=verdict["last_failure_at"],
            now=now,
        )

    if not decision["notify"]:
        # The system is repairing itself. Saying so hourly would train Dais to
        # ignore the one message that will matter.
        return {"action": "none", "record": None, "health": verdict, "ladder": decision}

    record = open_outage(
        state_path=state_path,
        reason="pass_failing",
        # The streak's own first failure, not this wake: the event key is pinned
        # to the outage start so a growing count cannot re-notify.
        started_at=verdict["first_failure_at"] or verdict["last_success_at"] or now,
        now=now,
        detail=str(threshold),
        context={
            "step": verdict["step"],
            "consecutive": verdict["consecutive"],
            "attempted": health.attempted_ja(decision),
        },
    )
    if record is None:
        return {
            "action": "none",
            "record": read_state(state_path),
            "health": verdict,
            "ladder": decision,
        }
    return {"action": "opened", "record": record, "health": verdict, "ladder": decision}
