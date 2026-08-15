"""A loop that runs and fails must not be reported as a loop that is dead.

On 2026-07-30 23:51 the heartbeat was eleven hours stale while three passes were
running and fifteen had failed that day, nine of them at the same step. The alarm
that fired said the work "was stopped", that the cause "was not yet known", and
asked Dais to go and look -- three statements that were each false or forbidden.

These tests pin the three states apart from the evidence already on disk, pin the
escalation ladder that acts before anyone is told, and pin the words a
non-technical reader actually receives.
"""

from __future__ import annotations

import importlib.util
import json
import sqlite3
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"


def _module(name: str):
    spec = importlib.util.spec_from_file_location(f"a15_{name}", SCRIPTS / f"{name}.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


pass_health = _module("pass_health")
pass_outage = _module("pass_outage")
repair_queue = _module("repair_queue")

# 2026-07-30 23:51 JST -- the moment the wrong message was sent.
NOW = 1785423060
# 2026-07-30 12:55 JST -- the last real success, eleven hours earlier.
LAST_SUCCESS = 1785383700
HOUR = 3600


def _write_failures(path: Path, rows: list[dict]) -> None:
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )


def _failure(ts: int, step: str, reason: str, *, pass_id: str = "p") -> dict:
    return {
        "ts": ts,
        "driver": "gig_pass.sh",
        "pass_id": pass_id,
        "status": "failed",
        "failed_step": step,
        "reason": reason,
        # The real rows carry a multi-kilobyte queue_top; the reader must ignore it.
        "queue_top": {"title": "x" * 512},
        "evidence_dir": f"/workspace/gig/evidence/gig-pass-{pass_id}",
    }


def _heartbeat(path: Path, at: int, *, steps: list[str] | None = None) -> None:
    path.write_text(
        json.dumps({"ts": at, "status": "success", "steps_executed": steps or []}),
        encoding="utf-8",
    )
    import os

    os.utime(path, (at, at))


# --------------------------------------------------------------------------
# 1. Three states, not two.
# --------------------------------------------------------------------------


def test_running_and_failing_is_not_dead(tmp_path: Path) -> None:
    """The measured 2026-07-30 shape: stale heartbeat, live failures at one step."""
    heartbeat = tmp_path / ".last-pass"
    failures = tmp_path / "pass-failures.jsonl"
    _heartbeat(heartbeat, LAST_SUCCESS)
    _write_failures(
        failures,
        [
            _failure(LAST_SUCCESS + n * HOUR, "B2", "b2_applied_page_readback_failed")
            for n in range(1, 10)
        ],
    )
    verdict = pass_health.classify(
        heartbeat_path=heartbeat,
        failures_path=failures,
        now=NOW,
        running_passes=3,
    )
    assert verdict["state"] == pass_health.STATE_FAILING
    assert verdict["step"] == "B2"
    assert verdict["reason"] == "b2_applied_page_readback_failed"
    assert verdict["consecutive"] == 9


def test_nothing_running_and_nothing_ran_is_dead(tmp_path: Path) -> None:
    heartbeat = tmp_path / ".last-pass"
    failures = tmp_path / "pass-failures.jsonl"
    _heartbeat(heartbeat, LAST_SUCCESS)
    failures.write_text("", encoding="utf-8")
    verdict = pass_health.classify(
        heartbeat_path=heartbeat,
        failures_path=failures,
        now=NOW,
        running_passes=0,
    )
    assert verdict["state"] == pass_health.STATE_DEAD
    assert verdict["step"] is None
    assert verdict["consecutive"] == 0


def test_a_fresh_heartbeat_is_healthy_even_with_old_failures(tmp_path: Path) -> None:
    heartbeat = tmp_path / ".last-pass"
    failures = tmp_path / "pass-failures.jsonl"
    _heartbeat(heartbeat, NOW - 600)
    _write_failures(
        failures,
        [_failure(NOW - n * HOUR, "B2", "b2_applied_page_readback_failed") for n in (5, 4, 3)],
    )
    verdict = pass_health.classify(
        heartbeat_path=heartbeat, failures_path=failures, now=NOW, running_passes=0
    )
    assert verdict["state"] == pass_health.STATE_HEALTHY
    # A success is the reset point: failures older than it are not this run's.
    assert verdict["consecutive"] == 0


def test_evidence_directories_alone_prove_a_pass_ran(tmp_path: Path) -> None:
    """No failure rows and no live process, but a pass left a working directory."""
    import os

    heartbeat = tmp_path / ".last-pass"
    failures = tmp_path / "pass-failures.jsonl"
    evidence_root = tmp_path / "evidence"
    (evidence_root / "gig-pass-1785420000-1").mkdir(parents=True)
    os.utime(evidence_root / "gig-pass-1785420000-1", (NOW - 600, NOW - 600))
    _heartbeat(heartbeat, LAST_SUCCESS)
    failures.write_text("", encoding="utf-8")
    verdict = pass_health.classify(
        heartbeat_path=heartbeat,
        failures_path=failures,
        evidence_root=evidence_root,
        now=NOW,
        running_passes=0,
    )
    assert verdict["state"] == pass_health.STATE_FAILING


def test_a_heartbeat_that_never_existed_is_dead(tmp_path: Path) -> None:
    verdict = pass_health.classify(
        heartbeat_path=tmp_path / "absent",
        failures_path=tmp_path / "absent.jsonl",
        now=NOW,
        running_passes=0,
    )
    assert verdict["state"] == pass_health.STATE_DEAD


# --------------------------------------------------------------------------
# 2. The consecutive count, and what resets it.
# --------------------------------------------------------------------------


def test_a_different_step_resets_the_count(tmp_path: Path) -> None:
    failures = tmp_path / "pass-failures.jsonl"
    _write_failures(
        failures,
        [
            _failure(LAST_SUCCESS + 1 * HOUR, "B2", "b2_applied_page_readback_failed"),
            _failure(LAST_SUCCESS + 2 * HOUR, "B2", "b2_applied_page_readback_failed"),
            _failure(LAST_SUCCESS + 3 * HOUR, "B2", "b2_applied_page_readback_failed"),
            _failure(LAST_SUCCESS + 4 * HOUR, "PAID_WORK", "paid_work_builder_failed"),
        ],
    )
    run = pass_health.consecutive_step_failures(
        pass_health.read_failure_rows(failures, since=LAST_SUCCESS)
    )
    assert run["step"] == "PAID_WORK"
    assert run["count"] == 1


def test_the_run_is_the_trailing_streak_not_the_total(tmp_path: Path) -> None:
    failures = tmp_path / "pass-failures.jsonl"
    _write_failures(
        failures,
        [
            _failure(LAST_SUCCESS + 1 * HOUR, "B2", "r1"),
            _failure(LAST_SUCCESS + 2 * HOUR, "PAID_WORK", "r2"),
            _failure(LAST_SUCCESS + 3 * HOUR, "B2", "r1"),
            _failure(LAST_SUCCESS + 4 * HOUR, "B2", "r1"),
        ],
    )
    run = pass_health.consecutive_step_failures(
        pass_health.read_failure_rows(failures, since=LAST_SUCCESS)
    )
    assert (run["step"], run["count"]) == ("B2", 2)


def test_rows_at_or_before_the_last_success_are_not_this_run(tmp_path: Path) -> None:
    failures = tmp_path / "pass-failures.jsonl"
    _write_failures(
        failures,
        [
            _failure(LAST_SUCCESS - HOUR, "B2", "r1"),
            _failure(LAST_SUCCESS, "B2", "r1"),
            _failure(LAST_SUCCESS + HOUR, "B2", "r1"),
        ],
    )
    rows = pass_health.read_failure_rows(failures, since=LAST_SUCCESS)
    assert [row["ts"] for row in rows] == [LAST_SUCCESS + HOUR]


def test_the_reader_drops_the_multi_kilobyte_payload(tmp_path: Path) -> None:
    """pass-failures.jsonl rows are ~4KB each; only four fields may be carried."""
    failures = tmp_path / "pass-failures.jsonl"
    _write_failures(failures, [_failure(LAST_SUCCESS + HOUR, "B2", "r1")])
    row = pass_health.read_failure_rows(failures, since=LAST_SUCCESS)[0]
    assert set(row) == {"ts", "failed_step", "reason", "evidence_dir"}


# --------------------------------------------------------------------------
# 3. The self-repair ladder.
# --------------------------------------------------------------------------


def test_rung_one_retries_through_an_existing_alternate_path() -> None:
    decision = pass_health.ladder_decision(step="B0", consecutive=1)
    assert decision["rung"] == 1
    assert decision["action"] == pass_health.ACTION_RETRY_ALTERNATE
    # Verified in gig_pass.sh: b0_result_gate.py retry-context, same wake.
    assert decision["alternate_path"] == pass_health.STEP_ALTERNATE_PATHS["B0"]
    assert decision["notify"] is False


def test_rung_one_says_so_when_no_alternate_path_exists() -> None:
    decision = pass_health.ladder_decision(step="B2", consecutive=1)
    assert decision["rung"] == 1
    assert decision["action"] == pass_health.ACTION_NO_ALTERNATE_PATH
    assert decision["alternate_path"] is None
    assert decision["notify"] is False


def test_rung_three_isolates_the_step() -> None:
    decision = pass_health.ladder_decision(step="B2", consecutive=3)
    assert decision["rung"] == 3
    assert decision["action"] == pass_health.ACTION_ISOLATE_STEP
    assert decision["isolate"] is True
    assert decision["repair_task"] is False
    assert decision["notify"] is False


def test_rung_five_generates_a_repair_task() -> None:
    decision = pass_health.ladder_decision(step="B2", consecutive=5)
    assert decision["rung"] == 5
    assert decision["action"] == pass_health.ACTION_OPEN_REPAIR_TASK
    assert decision["repair_task"] is True
    assert decision["notify"] is False


def test_beyond_five_notifies_and_the_lower_rungs_stay_latched() -> None:
    decision = pass_health.ladder_decision(step="B2", consecutive=9)
    assert decision["rung"] == 6
    assert decision["action"] == pass_health.ACTION_NOTIFY_HUMAN
    assert decision["notify"] is True
    # A skipped observation must never lose a rung already earned.
    assert decision["isolate"] is True
    assert decision["repair_task"] is True


def test_zero_failures_climbs_nothing() -> None:
    decision = pass_health.ladder_decision(step=None, consecutive=0)
    assert decision["rung"] == 0
    assert decision["action"] == pass_health.ACTION_NONE
    assert decision["notify"] is False


@pytest.mark.parametrize(
    ("consecutive", "action"),
    [
        (2, pass_health.ACTION_NO_ALTERNATE_PATH),
        (4, pass_health.ACTION_ISOLATE_STEP),
        (6, pass_health.ACTION_NOTIFY_HUMAN),
    ],
)
def test_the_ladder_is_monotone_between_rungs(consecutive: int, action: str) -> None:
    assert pass_health.ladder_decision(step="B2", consecutive=consecutive)["action"] == action


# --------------------------------------------------------------------------
# 4. Rung 3: the isolation store, and how a step gets back in.
# --------------------------------------------------------------------------


def test_isolation_is_written_read_back_and_expires(tmp_path: Path) -> None:
    store = tmp_path / "step-isolation.json"
    pass_health.isolate_step(
        store_path=store, step="B2", reason="b2_applied_page_readback_failed",
        consecutive=3, now=NOW, seconds=HOUR,
    )
    assert pass_health.isolated_steps(store, now=NOW) == {"B2"}
    assert pass_health.isolated_steps(store, now=NOW + HOUR) == set()


def test_a_step_that_succeeded_is_released_immediately(tmp_path: Path) -> None:
    store = tmp_path / "step-isolation.json"
    pass_health.isolate_step(
        store_path=store, step="B2", reason="r", consecutive=3, now=NOW, seconds=HOUR
    )
    pass_health.release_steps(store_path=store, steps=["B2"], now=NOW + 60)
    assert pass_health.isolated_steps(store, now=NOW + 60) == set()


def test_a_corrupt_isolation_store_isolates_nothing(tmp_path: Path) -> None:
    """Fail open: a broken file must never be able to silence a lane."""
    store = tmp_path / "step-isolation.json"
    store.write_text("{not json", encoding="utf-8")
    assert pass_health.isolated_steps(store, now=NOW) == set()


# --------------------------------------------------------------------------
# 5. Rung 5: the durable repair record, in the queue that already exists.
# --------------------------------------------------------------------------


def test_the_repair_task_lands_in_the_existing_repair_queue(tmp_path: Path) -> None:
    database = tmp_path / "gig-control.sqlite3"
    row = pass_health.open_repair_task(
        repair_database=database,
        step="B2",
        reason="b2_applied_page_readback_failed",
        consecutive=9,
        evidence_dirs=["/e/gig-pass-a", "/e/gig-pass-b", "/e/gig-pass-c"],
        source_file="skills/earn/gig/gig_pass.sh",
        first_failure_at=LAST_SUCCESS + HOUR,
        last_failure_at=NOW,
        now=NOW,
    )
    assert row["repair_class"] == pass_health.REPAIR_CLASS
    assert row["fingerprint"] == "pass_step:B2:b2_applied_page_readback_failed"
    assert row["evidence"]["failed_step"] == "B2"
    assert row["evidence"]["reason"] == "b2_applied_page_readback_failed"
    assert row["evidence"]["consecutive"] == 9
    assert row["evidence"]["evidence_dirs"] == ["/e/gig-pass-a", "/e/gig-pass-b", "/e/gig-pass-c"]
    assert row["evidence"]["source_file"] == "skills/earn/gig/gig_pass.sh"

    # Readable back through the queue's own reader, in its own database file.
    listed = repair_queue.RepairQueue(database).list_incidents()
    assert [item["fingerprint"] for item in listed] == [
        "pass_step:B2:b2_applied_page_readback_failed"
    ]
    with sqlite3.connect(database) as connection:
        stored = connection.execute(
            "SELECT repair_class,state FROM repair_queue"
        ).fetchone()
    assert stored == (pass_health.REPAIR_CLASS, "queued")


def test_repeating_the_same_defect_does_not_pile_up_rows(tmp_path: Path) -> None:
    database = tmp_path / "gig-control.sqlite3"
    for consecutive in (5, 6, 7):
        pass_health.open_repair_task(
            repair_database=database, step="B2", reason="r", consecutive=consecutive,
            evidence_dirs=[], source_file="x", first_failure_at=1, last_failure_at=2, now=NOW,
        )
    rows = repair_queue.RepairQueue(database).list_incidents()
    assert len(rows) == 1
    assert rows[0]["occurrence_count"] == 3
    assert rows[0]["evidence"]["consecutive"] == 7


def test_the_repair_class_is_one_the_healer_already_consumes() -> None:
    """A second unread queue is worse than none; this class must be dispatched."""
    controller = (SCRIPTS.parents[2] / "src/gig/healing/controller.py").read_text(
        encoding="utf-8"
    )
    healer = (SCRIPTS / "gig_healer.py").read_text(encoding="utf-8")
    assert pass_health.REPAIR_CLASS in controller
    assert pass_health.REPAIR_CLASS in healer


def test_the_named_source_file_is_the_one_that_emits_the_reason() -> None:
    """No invented mapping table: the source is wherever the literal reason lives."""
    root = SCRIPTS.parents[1]
    assert (
        pass_health.locate_reason_source("b2_applied_page_readback_failed", root)
        == "gig-work/gig_pass.sh"
    )
    assert pass_health.locate_reason_source("no_such_reason_anywhere", root) is None


# --------------------------------------------------------------------------
# 6. The words. No exit codes, no pass ids, no reason codes, no 確認してください.
# --------------------------------------------------------------------------

FORBIDDEN = ("確認してください", "exit ", "b2_applied_page_readback_failed", "B2")


def _outage_message(record) -> str:
    return pass_outage.outage_report(record)[2]


def test_the_failing_message_names_the_step_and_the_count(tmp_path: Path) -> None:
    record = pass_outage.open_outage(
        state_path=tmp_path / "s.json",
        reason="pass_failing",
        started_at=LAST_SUCCESS,
        now=NOW,
        context={
            "step": "B2",
            "consecutive": 9,
            "attempted": ["別のやり方での再試行", "その手順だけ切り離して他は続行", "修理の予約"],
        },
    )
    message = _outage_message(record)
    assert "空回り" in message
    assert "止まっています" not in message
    assert "お仕事への応募" in message
    assert "9回" in message
    for banned in FORBIDDEN:
        assert banned not in message


def test_the_dead_message_still_says_stopped(tmp_path: Path) -> None:
    record = pass_outage.open_outage(
        state_path=tmp_path / "s.json",
        reason="pass_silence",
        started_at=LAST_SUCCESS,
        now=NOW,
        detail="7200",
    )
    message = _outage_message(record)
    assert "止まっています" in message
    assert "確認してください" not in message
    assert "原因がまだ分かっていません" not in message


def test_a_sub_minute_outage_does_not_render_as_zero_minutes(tmp_path: Path) -> None:
    state = tmp_path / "s.json"
    pass_outage.open_outage(
        state_path=state, reason="pass_silence", started_at=NOW, now=NOW, detail="60"
    )
    record = pass_outage.close_outage(
        state_path=state, scope=pass_outage.SILENCE_SCOPE, now=NOW + 31
    )
    message = pass_outage.recovery_report(record)[2]
    assert "0分" not in message
    assert "すぐに" in message


def test_an_unnamed_failing_step_still_avoids_the_three_defects(tmp_path: Path) -> None:
    record = pass_outage.open_outage(
        state_path=tmp_path / "s.json",
        reason="pass_failing",
        started_at=LAST_SUCCESS,
        now=NOW,
        context={"step": None, "consecutive": 0, "attempted": []},
    )
    message = _outage_message(record)
    assert "確認してください" not in message
    assert "止まっています" not in message
    # Nothing was climbed, so no repair may be claimed.
    assert "予約しました" not in message
    assert "まだ特定できていません" in message


def test_the_failing_reason_is_owned_by_the_silence_detector(tmp_path: Path) -> None:
    """One outage at a time, and only its own detector may recover it."""
    state = tmp_path / "s.json"
    pass_outage.open_outage(
        state_path=state, reason="pass_failing", started_at=LAST_SUCCESS, now=NOW,
        context={"step": "B2", "consecutive": 9, "attempted": []},
    )
    assert pass_outage.open_outage(
        state_path=state, reason="pass_silence", started_at=NOW, now=NOW
    ) is None
    assert pass_outage.close_outage(
        state_path=state, scope=pass_outage.LAUNCHER_SCOPE, now=NOW + 60
    ) is None
    assert pass_outage.close_outage(
        state_path=state, scope=pass_outage.SILENCE_SCOPE, now=NOW + 60
    )


# --------------------------------------------------------------------------
# 7. End to end through the detector: the ladder runs, then the message.
# --------------------------------------------------------------------------


def test_the_detector_climbs_the_ladder_before_it_speaks(tmp_path: Path) -> None:
    heartbeat = tmp_path / ".last-pass"
    failures = tmp_path / "pass-failures.jsonl"
    _heartbeat(heartbeat, LAST_SUCCESS)
    _write_failures(
        failures,
        [
            _failure(LAST_SUCCESS + n * HOUR, "B2", "b2_applied_page_readback_failed")
            for n in range(1, 10)
        ],
    )
    result = pass_outage.evaluate_pass_silence(
        heartbeat_path=heartbeat,
        state_path=tmp_path / "outage.json",
        failures_path=failures,
        isolation_path=tmp_path / "step-isolation.json",
        repair_database=tmp_path / "gig-control.sqlite3",
        source_root=SCRIPTS.parents[1],
        running_passes=3,
        now=NOW,
    )
    assert result["action"] == "opened"
    assert result["record"]["reason"] == "pass_failing"
    assert result["ladder"]["action"] == pass_health.ACTION_NOTIFY_HUMAN
    # Rung 3 and rung 5 actually happened, not merely were decided.
    assert pass_health.isolated_steps(tmp_path / "step-isolation.json", now=NOW) == {"B2"}
    rows = repair_queue.RepairQueue(tmp_path / "gig-control.sqlite3").list_incidents()
    assert rows[0]["evidence"]["source_file"] == "gig-work/gig_pass.sh"


def test_below_the_top_rung_the_detector_acts_but_stays_silent(tmp_path: Path) -> None:
    heartbeat = tmp_path / ".last-pass"
    failures = tmp_path / "pass-failures.jsonl"
    _heartbeat(heartbeat, LAST_SUCCESS)
    _write_failures(
        failures,
        [_failure(LAST_SUCCESS + n * HOUR, "B2", "r") for n in range(1, 4)],
    )
    result = pass_outage.evaluate_pass_silence(
        heartbeat_path=heartbeat,
        state_path=tmp_path / "outage.json",
        failures_path=failures,
        isolation_path=tmp_path / "step-isolation.json",
        repair_database=tmp_path / "gig-control.sqlite3",
        running_passes=1,
        now=NOW,
    )
    assert result["action"] == "none"
    assert result["ladder"]["action"] == pass_health.ACTION_ISOLATE_STEP
    assert pass_health.isolated_steps(tmp_path / "step-isolation.json", now=NOW) == {"B2"}
    assert repair_queue.RepairQueue(tmp_path / "gig-control.sqlite3").list_incidents() == []


def test_recovery_releases_the_isolated_step(tmp_path: Path) -> None:
    heartbeat = tmp_path / ".last-pass"
    state = tmp_path / "outage.json"
    isolation = tmp_path / "step-isolation.json"
    pass_health.isolate_step(
        store_path=isolation, step="B2", reason="r", consecutive=3, now=NOW, seconds=HOUR
    )
    pass_outage.open_outage(
        state_path=state, reason="pass_failing", started_at=LAST_SUCCESS, now=NOW,
        context={"step": "B2", "consecutive": 9, "attempted": []},
    )
    _heartbeat(heartbeat, NOW + 60, steps=["B2"])
    result = pass_outage.evaluate_pass_silence(
        heartbeat_path=heartbeat,
        state_path=state,
        failures_path=tmp_path / "pass-failures.jsonl",
        isolation_path=isolation,
        now=NOW + 120,
    )
    assert result["action"] == "recovered"
    assert pass_health.isolated_steps(isolation, now=NOW + 120) == set()


def test_the_detector_keeps_working_with_no_new_arguments(tmp_path: Path) -> None:
    """A1's call site must keep compiling: every new input is optional."""
    heartbeat = tmp_path / ".last-pass"
    _heartbeat(heartbeat, LAST_SUCCESS)
    result = pass_outage.evaluate_pass_silence(
        heartbeat_path=heartbeat, state_path=tmp_path / "outage.json", now=NOW
    )
    assert result["action"] == "opened"
    assert result["record"]["reason"] == "pass_silence"


def test_no_model_is_called_anywhere_in_the_detector_or_the_ladder() -> None:
    """This is bookkeeping. evidence_gc, pass_outage and interview_scheduler are
    model-free and this one stays that way.

    Prose is not evidence, so this reads the imports: a model call needs either
    an SDK on the import list or a subprocess, and the only subprocess allowed
    here is the one that counts live passes.
    """
    import ast

    allowed_imports = {
        "argparse", "ast", "importlib", "importlib.util", "json", "os",
        "pathlib", "subprocess", "sqlite3", "tempfile", "time", "typing",
        "datetime", "__future__",
    }
    for name in ("pass_health.py", "pass_outage.py"):
        tree = ast.parse((SCRIPTS / name).read_text(encoding="utf-8"))
        imported: set[str] = set()
        argv_heads: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module)
            elif isinstance(node, ast.Call):
                target = getattr(node.func, "attr", getattr(node.func, "id", ""))
                if target in {"run", "Popen", "check_output", "call", "system", "exec"}:
                    first = node.args[0] if node.args else None
                    if isinstance(first, ast.List) and first.elts:
                        head = first.elts[0]
                        argv_heads.add(
                            head.value if isinstance(head, ast.Constant) else "<dynamic>"
                        )
                    elif first is not None:
                        argv_heads.add("<dynamic>")
        assert imported <= allowed_imports, f"{name} imports {imported - allowed_imports}"
        assert argv_heads <= {"/usr/bin/pgrep"}, f"{name} shells out to {argv_heads}"
