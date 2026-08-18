#!/usr/bin/env python3
"""Tell a loop that is dead apart from a loop that runs and fails, then climb.

A1 gave the loop a voice for the case where nothing ran. On 2026-07-30 23:51 that
voice said the wrong thing: the heartbeat was eleven hours stale, so it reported
"the work has stopped, the cause is not yet known, please go and look" -- while
three passes were running and fifteen had failed that day, nine of them at the
same named step.

The ambiguity is structural, not accidental. ``.last-pass`` is written only by
``finalize_success``; a pass that runs and dies leaves a row in
``pass-failures.jsonl`` and a nonzero exit but no heartbeat. From the heartbeat
alone, "nothing succeeded for two hours" and "nothing ran for two hours" are the
same observation.

So this module reads the evidence the heartbeat cannot carry:

  running passes      a live process is the strongest proof the loop is not dead
  failure rows        a terminal failure since the last success proves one ran
  evidence directories a pass that crashed before it could file a row still
                      left its working directory behind

and separates three states -- dead, failing, healthy -- where there were two.

When the state is *failing* the step is nameable, and a named repeating defect
can be climbed rather than announced. The ladder escalates on the count of
consecutive failures at the SAME step:

    1  retry through that step's existing alternate path, when one exists
    3  isolate the step so the other lanes keep running instead of the whole
       pass dying with it
    5  generate a durable repair task in the repair queue that already exists,
       naming the step, the reason code, the last evidence paths, and the source
       file that emits the reason
   6+  only now tell Dais -- and the message says what broke and what was tried

Every rung already earned stays latched, so a wake that never observed rung 3
cannot lose the isolation on its way to rung 5.

There is no model call in this module and there must never be one. Counting a
streak and comparing it to a threshold is bookkeeping; ``evidence_gc.py``,
``pass_outage.py`` and ``interview_scheduler.py`` are model-free for the same
reason -- a repair path that needs inference cannot run while inference is what
is broken.
"""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

STATE_HEALTHY = "healthy"
STATE_FAILING = "failing"
STATE_DEAD = "dead"

ACTION_NONE = "none"
ACTION_RETRY_ALTERNATE = "retry_alternate"
ACTION_NO_ALTERNATE_PATH = "no_alternate_path"
ACTION_ISOLATE_STEP = "isolate_step"
ACTION_OPEN_REPAIR_TASK = "open_repair_task"
ACTION_NOTIFY_HUMAN = "notify_human"

RUNG_RETRY = 1
RUNG_ISOLATE = 3
RUNG_REPAIR_TASK = 5
RUNG_NOTIFY = 6

# The repair queue's own vocabulary. The healing controller blocks a class it
# does not know, which would file this straight into the unread pile the whole
# rung exists to avoid -- so this string is also registered there.
REPAIR_CLASS = "pass_step_repair"

DEFAULT_ISOLATION_SECONDS = 3600
ISOLATION_VERSION = 1
DEFAULT_ISOLATION_FILENAME = "step-isolation.json"
EVIDENCE_PATHS_KEPT = 3

# Only steps with a genuine second route belong here. B0's is verified in
# gig_pass.sh: b0_result_gate.py retry-context re-enters the step in the same
# wake after a capacity failure. B2 has none -- which is exactly why the
# 2026-07-30 readback failure repeated nine times untouched, and why rung 1 must
# be able to answer "there is nothing to retry" instead of pretending.
STEP_ALTERNATE_PATHS: dict[str, str] = {
    "B0": "b0_result_gate.py retry-context",
}

# What each step is, to somebody who did not write it.
STEP_LABELS_JA: dict[str, str] = {
    "B0": "出品の見直し",
    "B1": "お客さまとのやりとり",
    "B2": "お仕事への応募",
    "PROFILE": "プロフィールの手入れ",
    "QUEUE": "お仕事一覧の取り込み",
    "REPLY_QUEUE": "問い合わせの整理",
    "INQUIRY_REPLY": "問い合わせへの返信",
    "PAID_WORK": "ご依頼ぶんの制作",
    "PAID_QUEUE_DELIVERY": "ご依頼ぶんのお渡し",
    "DELIVERY": "納品",
    "QUOTE": "お見積り",
    "POLL": "新着の確認",
    "PASSPREP": "作業の準備",
    "LEDGER": "記録の書き込み",
    "LEARN": "振り返り",
    "REFLECT": "振り返りのまとめ",
    "SELFIMPROVE": "自分の手直し",
    "UNIT_ECONOMICS": "売上の記録",
    "SHELL": "作業全体",
}
UNKNOWN_STEP_LABEL_JA = "作業のとちゅう"

ATTEMPT_RETRY_JA = "別のやり方での再試行"
ATTEMPT_NO_ALTERNATE_JA = "別のやり方がなく再試行できず"
ATTEMPT_ISOLATE_JA = "その手順だけ切り離して他は続行"
ATTEMPT_REPAIR_TASK_JA = "修理の予約"


def step_label_ja(step: str | None) -> str:
    if not step:
        return UNKNOWN_STEP_LABEL_JA
    return STEP_LABELS_JA.get(str(step), UNKNOWN_STEP_LABEL_JA)


# ---------------------------------------------------------------------------
# Reading the evidence
# ---------------------------------------------------------------------------


def read_failure_rows(
    path: Path | str,
    *,
    since: int = 0,
    limit: int = 200,
) -> list[dict[str, Any]]:
    """Failure rows newer than ``since``, reduced to the four fields that matter.

    A real row carries the whole queue head -- several kilobytes of buyer text,
    hashes and payloads. Carrying that into a health check would make the cheap
    bookkeeping expensive, so everything but the identity of the failure is
    dropped at the door.
    """
    try:
        lines = Path(path).read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    rows: list[dict[str, Any]] = []
    for line in lines[-limit:]:
        try:
            row = json.loads(line)
        except (json.JSONDecodeError, ValueError):
            continue
        if not isinstance(row, dict):
            continue
        timestamp = row.get("ts")
        if not isinstance(timestamp, (int, float)) or int(timestamp) <= int(since):
            continue
        rows.append(
            {
                "ts": int(timestamp),
                "failed_step": str(row.get("failed_step") or "") or None,
                "reason": str(row.get("reason") or "") or None,
                "evidence_dir": str(row.get("evidence_dir") or "") or None,
            }
        )
    rows.sort(key=lambda row: row["ts"])
    return rows


def consecutive_step_failures(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """The trailing streak of failures at one step -- the ladder's only input.

    A different step ends the streak because it is a different defect; the count
    that governs escalation must not be the total number of ways the loop is
    unwell.
    """
    empty = {
        "step": None,
        "reason": None,
        "count": 0,
        "first_ts": None,
        "last_ts": None,
        "evidence_dirs": [],
    }
    if not rows:
        return empty
    step = rows[-1].get("failed_step")
    if not step:
        return empty
    streak: list[Mapping[str, Any]] = []
    for row in reversed(rows):
        if row.get("failed_step") != step:
            break
        streak.append(row)
    streak.reverse()
    return {
        "step": str(step),
        # The most recent reason: the same step can break two ways, and the one
        # to name is the one happening now.
        "reason": streak[-1].get("reason"),
        "count": len(streak),
        "first_ts": streak[0]["ts"],
        "last_ts": streak[-1]["ts"],
        "evidence_dirs": [
            row["evidence_dir"]
            for row in streak[-EVIDENCE_PATHS_KEPT:]
            if row.get("evidence_dir")
        ],
    }


def probe_running_passes(pattern: str = "gig_pass.sh") -> int:
    """How many passes are alive right now. Unknown counts as none.

    A false "nothing is running" only costs a state downgrade to dead, which is
    still louder than silence; a false "something is running" would suppress a
    real death, so the uncertain answer is the quiet one.
    """
    try:
        completed = subprocess.run(
            ["/usr/bin/pgrep", "-f", pattern],
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return 0
    if completed.returncode != 0:
        return 0
    mine = str(os.getpid())
    return len(
        [line for line in completed.stdout.split() if line.strip() and line.strip() != mine]
    )


def _any_evidence_since(evidence_root: Path | str | None, *, floor: int) -> int:
    if evidence_root is None:
        return 0
    try:
        entries = os.scandir(Path(evidence_root))
    except OSError:
        return 0
    seen = 0
    with entries:
        for entry in entries:
            if not entry.name.startswith("gig-pass-"):
                continue
            try:
                if int(entry.stat().st_mtime) > floor:
                    seen += 1
                    if seen >= 2:  # Presence is the signal; stop counting.
                        break
            except OSError:
                continue
    return seen


def _last_success(heartbeat_path: Path | str) -> tuple[int | None, list[str]]:
    path = Path(heartbeat_path)
    try:
        at: int | None = int(path.stat().st_mtime)
    except OSError:
        return None, []
    steps: list[str] = []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            steps = [
                str(step)
                for step in (payload.get("steps_executed") or [])
                if isinstance(step, str)
            ]
    except (OSError, ValueError):
        steps = []
    return at, steps


def classify(
    *,
    heartbeat_path: Path | str,
    failures_path: Path | str | None = None,
    evidence_root: Path | str | None = None,
    now: int,
    running_passes: int = 0,
    silence_seconds: int = 2 * 60 * 60,
) -> dict[str, Any]:
    """dead / failing / healthy, from what is already on disk.

    healthy  a pass completed inside the silence window
    failing  nothing completed, but something ran: a live process, a terminal
             failure since the last success, or a fresh evidence directory
    dead     nothing completed and nothing ran

    The streak is measured since the last SUCCESS, not since the window opened:
    nine failures spread over eleven hours are one defect, and a two-hour view of
    them would have counted two.
    """
    last_success_at, last_success_steps = _last_success(heartbeat_path)
    silent_for = None if last_success_at is None else int(now) - last_success_at
    healthy = last_success_at is not None and silent_for is not None and silent_for <= silence_seconds

    rows = (
        read_failure_rows(failures_path, since=last_success_at or 0)
        if failures_path is not None
        else []
    )
    run = consecutive_step_failures(rows)

    verdict: dict[str, Any] = {
        "state": STATE_HEALTHY,
        "last_success_at": last_success_at,
        "last_success_steps": last_success_steps,
        "silent_for": silent_for,
        "silence_seconds": int(silence_seconds),
        "step": None,
        "reason": None,
        "consecutive": 0,
        "first_failure_at": None,
        "last_failure_at": None,
        "evidence_dirs": [],
        "activity": {
            "running_passes": int(running_passes),
            "failures_since_success": 0,
            "evidence_dirs_since_window": 0,
        },
    }
    if healthy:
        return verdict

    activity_floor = int(now) - int(silence_seconds)
    recent_failures = len([row for row in rows if row["ts"] > activity_floor])
    fresh_evidence = _any_evidence_since(evidence_root, floor=activity_floor)
    verdict["activity"] = {
        "running_passes": int(running_passes),
        "failures_since_success": recent_failures,
        "evidence_dirs_since_window": fresh_evidence,
    }
    ran = int(running_passes) > 0 or recent_failures > 0 or fresh_evidence > 0
    verdict["state"] = STATE_FAILING if ran else STATE_DEAD
    if ran:
        verdict.update(
            {
                "step": run["step"],
                "reason": run["reason"],
                "consecutive": run["count"],
                "first_failure_at": run["first_ts"],
                "last_failure_at": run["last_ts"],
                "evidence_dirs": run["evidence_dirs"],
            }
        )
    return verdict


# ---------------------------------------------------------------------------
# The ladder
# ---------------------------------------------------------------------------


def ladder_decision(
    *,
    step: str | None,
    consecutive: int,
    alternate_paths: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Which rung a streak has reached, and everything it has earned below it.

    ``action`` is the rung reached; ``isolate`` and ``repair_task`` stay true for
    every higher rung so a wake that was never observed cannot un-isolate a step
    on its way up.
    """
    paths = STEP_ALTERNATE_PATHS if alternate_paths is None else alternate_paths
    count = max(0, int(consecutive))
    alternate = paths.get(str(step)) if step else None

    if count >= RUNG_NOTIFY:
        rung, action = RUNG_NOTIFY, ACTION_NOTIFY_HUMAN
    elif count >= RUNG_REPAIR_TASK:
        rung, action = RUNG_REPAIR_TASK, ACTION_OPEN_REPAIR_TASK
    elif count >= RUNG_ISOLATE:
        rung, action = RUNG_ISOLATE, ACTION_ISOLATE_STEP
    elif count >= RUNG_RETRY:
        rung = RUNG_RETRY
        action = ACTION_RETRY_ALTERNATE if alternate else ACTION_NO_ALTERNATE_PATH
    else:
        rung, action = 0, ACTION_NONE

    return {
        "rung": rung,
        "action": action,
        "alternate_path": alternate,
        "retry_alternate": bool(alternate) and count >= RUNG_RETRY,
        "isolate": count >= RUNG_ISOLATE,
        "repair_task": count >= RUNG_REPAIR_TASK,
        "notify": count >= RUNG_NOTIFY,
        "consecutive": count,
        "step": str(step) if step else None,
    }


def attempted_ja(decision: Mapping[str, Any]) -> list[str]:
    """What was actually tried, in the order it was tried, for the message."""
    attempted: list[str] = []
    if int(decision.get("consecutive", 0)) >= RUNG_RETRY:
        attempted.append(
            ATTEMPT_RETRY_JA if decision.get("retry_alternate") else ATTEMPT_NO_ALTERNATE_JA
        )
    if decision.get("isolate"):
        attempted.append(ATTEMPT_ISOLATE_JA)
    if decision.get("repair_task"):
        attempted.append(ATTEMPT_REPAIR_TASK_JA)
    return attempted


# ---------------------------------------------------------------------------
# Rung 3 -- isolation
# ---------------------------------------------------------------------------


def _read_isolation(store_path: Path | str) -> dict[str, Any]:
    try:
        payload = json.loads(Path(store_path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    if not isinstance(payload, dict) or payload.get("version") != ISOLATION_VERSION:
        return {}
    steps = payload.get("steps")
    return steps if isinstance(steps, dict) else {}


def _write_isolation(store_path: Path | str, steps: Mapping[str, Any]) -> None:
    path = Path(store_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            json.dump(
                {"version": ISOLATION_VERSION, "steps": dict(steps)},
                stream,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
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


def isolated_steps(store_path: Path | str, *, now: int) -> set[str]:
    """Steps the pass should skip right now. A broken store isolates nothing.

    Failing open matters more here than anywhere else in this module: a corrupt
    file that silenced a lane would be indistinguishable from the outage it was
    meant to survive.
    """
    live: set[str] = set()
    for step, entry in _read_isolation(store_path).items():
        if not isinstance(entry, dict):
            continue
        until = entry.get("until")
        if isinstance(until, (int, float)) and int(until) > int(now):
            live.add(str(step))
    return live


def isolate_step(
    *,
    store_path: Path | str,
    step: str,
    reason: str | None,
    consecutive: int,
    now: int,
    seconds: int = DEFAULT_ISOLATION_SECONDS,
) -> dict[str, Any]:
    """Take one step out of the pass, leaving every other lane running.

    The window is one wake long. It is re-decided on the next observation and
    lapses on its own, so an isolation can never outlive the defect that earned
    it even if nothing ever comes back to lift it.
    """
    steps = {
        name: entry
        for name, entry in _read_isolation(store_path).items()
        if isinstance(entry, dict)
        and isinstance(entry.get("until"), (int, float))
        and int(entry["until"]) > int(now)
    }
    entry = {
        "since": int(steps.get(step, {}).get("since", now)),
        "until": int(now) + max(1, int(seconds)),
        "reason": str(reason or ""),
        "consecutive": int(consecutive),
    }
    steps[str(step)] = entry
    _write_isolation(store_path, steps)
    return entry


def release_steps(*, store_path: Path | str, steps: Iterable[str], now: int) -> set[str]:
    """Let named steps back in, and drop anything that has already lapsed."""
    releasing = {str(step) for step in steps}
    remaining = {
        name: entry
        for name, entry in _read_isolation(store_path).items()
        if name not in releasing
        and isinstance(entry, dict)
        and isinstance(entry.get("until"), (int, float))
        and int(entry["until"]) > int(now)
    }
    if remaining:
        _write_isolation(store_path, remaining)
    else:
        try:
            Path(store_path).unlink()
        except FileNotFoundError:
            pass
    return set(remaining)


# ---------------------------------------------------------------------------
# Rung 5 -- the durable repair task
# ---------------------------------------------------------------------------


def locate_reason_source(reason: str, root: Path | str) -> str | None:
    """The file that emits this reason code, found rather than tabulated.

    A hand-written step-to-file map would be wrong the first time a reason moved.
    Searching for the literal string is deterministic, needs no maintenance, and
    is only ever paid once, at rung 5.
    """
    if not reason:
        return None
    base = Path(root)
    needle = f'"{reason}"'
    for path in sorted(base.rglob("*")):
        if path.suffix not in {".sh", ".py"} or not path.is_file():
            continue
        if "/tests/" in str(path) or "__pycache__" in str(path):
            continue
        try:
            body = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if needle in body or f"'{reason}'" in body:
            return str(path.relative_to(base))
    return None


def _repair_queue_module():
    import importlib.util

    path = Path(__file__).with_name("repair_queue.py")
    spec = importlib.util.spec_from_file_location("pass_health_repair_queue", path)
    if spec is None or spec.loader is None:  # pragma: no cover - packaging accident
        raise RuntimeError("cannot load repair_queue")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def open_repair_task(
    *,
    repair_database: Path | str,
    step: str,
    reason: str | None,
    consecutive: int,
    evidence_dirs: Sequence[str],
    source_file: str | None,
    first_failure_at: int | None,
    last_failure_at: int | None,
    now: int,
) -> dict[str, Any]:
    """File the defect where repairs are already claimed, leased and audited.

    A second queue would be a second thing nobody reads. This one has a fencing
    token, an occurrence count and a controller that dispatches it -- so the row
    written here names the step, the reason code, the last evidence paths and the
    source file, and the existing machinery can act on it.
    """
    queue = _repair_queue_module().RepairQueue(repair_database)
    return queue.enqueue(
        fingerprint=f"pass_step:{step}:{reason or 'unknown'}",
        repair_class=REPAIR_CLASS,
        evidence={
            "failed_step": str(step),
            "reason": str(reason or ""),
            "consecutive": int(consecutive),
            "evidence_dirs": list(evidence_dirs)[-EVIDENCE_PATHS_KEPT:],
            "source_file": source_file,
            "first_failure_at": first_failure_at,
            "last_failure_at": last_failure_at,
            "detected_by": "pass_health.classify",
        },
        detected_at=int(now),
    )
