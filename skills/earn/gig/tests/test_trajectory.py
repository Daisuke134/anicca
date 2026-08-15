"""EV1: the trajectory writer, its schema, and the proof that something calls it.

★ The last third of this file is the important part. ★ This repository has twice built a
component that ran and that nothing read (``project_context_compiler`` wrote
``context/current.json`` every pass with no reader; ``project_effect_fence`` existed
unwired). A writer nothing calls is worth nothing, so ``TestWiring`` asserts the call sites
by reading the production sources -- those tests fail the moment someone deletes a
``record_trajectory`` call or the ``export`` in gig_pass.sh, which is the only failure mode
a unit test of the writer itself cannot see.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

SKILL_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = SKILL_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import trajectory  # noqa: E402


# ── the schema ────────────────────────────────────────────────────────────────────────


def test_a_line_carries_the_whole_documented_schema(tmp_path):
    target = tmp_path / "trajectory.jsonl"
    event = trajectory.record(
        stage="PAID_QUEUE_DELIVERY", lane="delivery",
        resource_key="talkroom:90000002", action="deliver",
        result="refused", reason="artifact_is_about_the_deal_not_the_deliverable",
        artifact_sha256="a" * 64, path=target,
    )
    assert event is not None
    written = json.loads(target.read_text(encoding="utf-8").strip())
    assert written == event
    assert set(written) == {
        "ts", "stage", "lane", "resource_key", "action", "result", "ok",
        "artifact_sha256", "reason",
    }
    assert isinstance(written["ts"], float)


def test_ok_is_derived_from_result_so_the_two_can_never_disagree(tmp_path):
    """spec §4.2 reads e.get("ok"); spec §4.1's example line carries result."""
    for result, expected in (("ok", True), ("refused", False), ("error", False), ("skipped", False)):
        event = trajectory.build_event(
            stage="S", lane="delivery", resource_key="talkroom:1", action="judge", result=result,
        )
        assert event["ok"] is expected, result


def test_optional_fields_are_omitted_not_nulled(tmp_path):
    event = trajectory.build_event(
        stage="S", lane="delivery", resource_key="talkroom:1", action="read",
    )
    assert "artifact_sha256" not in event
    assert "reason" not in event


@pytest.mark.parametrize("action", list(trajectory.ACTIONS))
def test_every_documented_action_is_accepted(action):
    assert trajectory.build_event(
        stage="S", lane="l", resource_key="talkroom:1", action=action,
    )["action"] == action


@pytest.mark.parametrize("kind", list(trajectory.RESOURCE_KINDS))
def test_every_documented_resource_kind_is_accepted(kind):
    key = f"{kind}:12345"
    assert trajectory.build_event(
        stage="S", lane="l", resource_key=key, action="read",
    )["resource_key"] == key


# ── a bad value is rejected, never silently written ───────────────────────────────────


@pytest.mark.parametrize("bad", [
    {"action": "post"},                       # not in the fixed vocabulary
    {"action": "DELIVER"},                    # case is part of the vocabulary
    {"action": ""},
    {"resource_key": "mailbox:1"},            # not one of the four kinds
    {"resource_key": "talkroom"},             # no id
    {"resource_key": "talkroom:"},
    {"resource_key": "talkroom:has spaces"},
    {"result": "great"},
    {"artifact_sha256": "not-a-digest"},
    {"artifact_sha256": "a" * 63},
    {"stage": "has spaces"},
    {"lane": ""},
])
def test_a_value_outside_the_vocabulary_raises_in_build_event(bad):
    kwargs = {
        "stage": "PAID_QUEUE_DELIVERY", "lane": "delivery",
        "resource_key": "talkroom:1", "action": "deliver",
    }
    kwargs.update(bad)
    with pytest.raises(trajectory.InvalidTrajectoryEvent):
        trajectory.build_event(**kwargs)


@pytest.mark.parametrize("bad", [
    {"action": "post"}, {"resource_key": "mailbox:1"}, {"result": "great"},
    {"artifact_sha256": "nope"},
])
def test_a_rejected_value_writes_nothing_and_does_not_raise(tmp_path, bad):
    """★ Rejected, but not at the caller's expense. ★"""
    target = tmp_path / "trajectory.jsonl"
    kwargs = {
        "stage": "S", "lane": "delivery", "resource_key": "talkroom:1",
        "action": "deliver", "path": target,
    }
    kwargs.update(bad)
    assert trajectory.record(**kwargs) is None
    assert not target.exists()


def test_the_cli_exits_non_zero_on_a_bad_action_and_writes_nothing(tmp_path):
    target = tmp_path / "trajectory.jsonl"
    done = subprocess.run(
        [sys.executable, str(SCRIPTS / "trajectory.py"), "--lane", "delivery",
         "--resource-key", "talkroom:1", "--action", "deliver", "--result", "ok",
         "--file", str(target)],
        capture_output=True, text=True,
    )
    assert done.returncode == 0 and target.exists()
    bad = subprocess.run(
        [sys.executable, str(SCRIPTS / "trajectory.py"), "--lane", "delivery",
         "--resource-key", "mailbox:1", "--action", "deliver", "--file", str(target)],
        capture_output=True, text=True,
    )
    assert bad.returncode != 0
    assert len(target.read_text(encoding="utf-8").strip().splitlines()) == 1


# ── no buyer text, no secrets ─────────────────────────────────────────────────────────


@pytest.mark.parametrize("leak", [
    "画像を10枚差し替えてください",                       # a buyer's own words
    "password=hunter2",
    "https://coconala.com/talkrooms/1?token=abcdef",
    "judge said the artifact is about the deal, not the deliverable",
    "user@example.com",
])
def test_prose_and_structured_secrets_cannot_reach_the_line(leak):
    event = trajectory.build_event(
        stage="S", lane="delivery", resource_key="talkroom:1", action="judge",
        result="refused", reason=leak,
    )
    assert event["reason"] == trajectory.REASON_UNPRINTABLE
    assert leak not in json.dumps(event, ensure_ascii=False)


def test_a_real_error_id_survives():
    event = trajectory.build_event(
        stage="S", lane="delivery", resource_key="talkroom:1", action="judge",
        result="refused", reason="artifact_is_about_the_deal_not_the_deliverable",
    )
    assert event["reason"] == "artifact_is_about_the_deal_not_the_deliverable"


def test_the_judge_gate_records_the_error_id_and_not_the_judges_prose(tmp_path, monkeypatch):
    """★ The judge explains itself in the buyer's language. That prose stays off disk. ★"""
    import artifact_judge

    target = tmp_path / "trajectory.jsonl"
    monkeypatch.setenv(trajectory.ENV_FILE, str(target))
    prose = "この成果物は取引についての説明であって納品物ではありません"
    with pytest.raises(ValueError):
        artifact_judge.refuse_unless_deliverable(
            tmp_path, tmp_path / "artifact.md",
            judge=lambda *_a, **_k: (artifact_judge.ABOUT_THE_DEAL, prose),
            trajectory_context={"stage": "PAID_QUEUE_DELIVERY", "lane": "delivery",
                                "resource_key": "talkroom:90000002"},
        )
    body = target.read_text(encoding="utf-8")
    assert prose not in body
    row = json.loads(body.strip())
    assert row["action"] == "judge" and row["ok"] is False
    assert row["reason"] == artifact_judge.ERROR_ABOUT_THE_DEAL


# ── ★ a trajectory write may never fail its caller ★ ──────────────────────────────────


def test_an_unwritable_directory_returns_none_instead_of_raising(tmp_path):
    blocked = tmp_path / "blocked"
    blocked.mkdir()
    blocked.chmod(0o000)
    try:
        assert trajectory.record(
            stage="S", lane="delivery", resource_key="talkroom:1", action="deliver",
            path=blocked / "trajectory.jsonl",
        ) is None
    finally:
        blocked.chmod(0o755)


def test_a_write_error_returns_none_instead_of_raising(tmp_path, monkeypatch):
    def explode(_path, _line):
        raise OSError(28, "No space left on device")

    monkeypatch.setattr(trajectory, "_append", explode)
    assert trajectory.record(
        stage="S", lane="delivery", resource_key="talkroom:1", action="deliver",
        path=tmp_path / "trajectory.jsonl",
    ) is None


def test_a_path_that_is_a_directory_returns_none_instead_of_raising(tmp_path):
    collision = tmp_path / "trajectory.jsonl"
    collision.mkdir()
    assert trajectory.record(
        stage="S", lane="delivery", resource_key="talkroom:1", action="deliver",
        path=collision,
    ) is None


def test_with_no_destination_configured_the_writer_is_a_silent_no_op(monkeypatch):
    """This is what the whole test suite sees, and why tests leave no trajectory behind."""
    monkeypatch.delenv(trajectory.ENV_FILE, raising=False)
    assert trajectory.trajectory_path() is None
    assert trajectory.record(
        stage="S", lane="delivery", resource_key="talkroom:1", action="deliver",
    ) is None


def test_the_environment_variable_is_the_destination_when_no_path_is_given(tmp_path, monkeypatch):
    target = tmp_path / "nested" / "trajectory.jsonl"
    monkeypatch.setenv(trajectory.ENV_FILE, str(target))
    assert trajectory.record(
        stage="S", lane="delivery", resource_key="talkroom:1", action="deliver",
    ) is not None
    assert target.is_file()


def test_nothing_is_written_to_stdout(tmp_path, capsys, monkeypatch):
    """Several call sites parse their own stdout as JSON."""
    monkeypatch.setattr(trajectory, "_append", lambda *_a: (_ for _ in ()).throw(OSError("x")))
    trajectory.record(stage="S", lane="delivery", resource_key="talkroom:1",
                      action="deliver", path=tmp_path / "t.jsonl")
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "trajectory_write_skipped" in captured.err


# ── append-only under concurrency ─────────────────────────────────────────────────────


def test_parallel_lanes_never_interleave_a_partial_line(tmp_path):
    """★ The lanes really do run concurrently. ★ Real processes, not threads."""
    target = tmp_path / "trajectory.jsonl"
    worker = tmp_path / "worker.py"
    worker.write_text(
        "import sys\n"
        f"sys.path.insert(0, {str(SCRIPTS)!r})\n"
        "import trajectory\n"
        "wid, n, target = sys.argv[1], int(sys.argv[2]), sys.argv[3]\n"
        "for i in range(n):\n"
        "    trajectory.record(stage='PAID_QUEUE_DELIVERY', lane='lane'+wid,\n"
        "                      resource_key='talkroom:%s%04d' % (wid, i), action='write',\n"
        "                      reason='x'*110, artifact_sha256='%064x' % i, path=target)\n",
        encoding="utf-8",
    )
    workers, per_worker = 8, 60
    procs = [
        subprocess.Popen([sys.executable, str(worker), str(w), str(per_worker), str(target)],
                         stderr=subprocess.DEVNULL)
        for w in range(workers)
    ]
    assert {p.wait() for p in procs} == {0}

    raw = target.read_bytes()
    assert raw.endswith(b"\n")
    lines = raw.decode("utf-8").splitlines()
    assert len(lines) == workers * per_worker
    for line in lines:                      # every one whole, none spliced
        row = json.loads(line)
        assert {"ts", "stage", "lane", "resource_key", "action", "result", "ok"} <= set(row)
    assert len({json.loads(line)["lane"] for line in lines}) == workers


def test_appends_never_truncate_an_existing_file(tmp_path):
    target = tmp_path / "trajectory.jsonl"
    for index in range(3):
        trajectory.record(stage="S", lane="delivery", resource_key=f"talkroom:{index}",
                          action="read", path=target)
    assert len(target.read_text(encoding="utf-8").splitlines()) == 3


def test_read_trajectory_keeps_file_order_and_skips_corrupt_lines(tmp_path):
    """★ File order is the authoritative order ★ -- ts alone is not fine-grained enough."""
    target = tmp_path / "trajectory.jsonl"
    target.write_text(
        '{"action":"read","resource_key":"posting:1"}\n'
        "{ this is not json\n"
        "\n"
        '{"action":"deliver","resource_key":"talkroom:1"}\n',
        encoding="utf-8",
    )
    rows = trajectory.read_trajectory(target)
    assert [row["action"] for row in rows] == ["read", "deliver"]


def test_read_trajectory_of_a_missing_file_is_empty(tmp_path):
    assert trajectory.read_trajectory(tmp_path / "absent.jsonl") == []


# ── ★ wiring: the failure mode a unit test cannot see ★ ───────────────────────────────


class TestWiring:
    def test_gig_pass_exports_the_destination(self):
        body = (SKILL_ROOT / "gig_pass.sh").read_text(encoding="utf-8")
        assert 'export GIG_TRAJECTORY_FILE="$EVIDENCE_DIR/trajectory.jsonl"' in body, (
            "gig_pass.sh no longer exports GIG_TRAJECTORY_FILE; every Python call site "
            "silently becomes a no-op and the pass writes no trajectory at all"
        )

    def test_the_export_happens_after_the_evidence_directory_exists(self):
        body = (SKILL_ROOT / "gig_pass.sh").read_text(encoding="utf-8")
        assert body.index('mkdir -p "$EVIDENCE_DIR"') < body.index("export GIG_TRAJECTORY_FILE")

    @pytest.mark.parametrize("source, needle", [
        ("scripts/artifact_judge.py", "action=\"judge\""),
        ("scripts/coconala_formal_delivery_browser.py", "action=\"deliver\""),
        ("scripts/coconala_paid_progress_browser.py", "action=\"deliver\""),
        ("scripts/coconala_paid_progress_browser.py", "action=\"ask\""),
        ("scripts/reply_lane.py", "action=\"write\""),
        ("scripts/project_context_compiler.py", "action=\"read\""),
    ])
    def test_the_call_site_still_records_its_action(self, source, needle):
        body = (SKILL_ROOT / source).read_text(encoding="utf-8")
        assert "record_trajectory" in body and needle in body, (
            f"{source} no longer records {needle}; the corresponding spec 4.2 check "
            "becomes unsatisfiable without any test failing on its own"
        )

    @pytest.mark.parametrize("source", [
        "scripts/artifact_judge.py",
        "scripts/coconala_formal_delivery_browser.py",
        "scripts/coconala_paid_progress_browser.py",
        "scripts/reply_lane.py",
        "scripts/project_context_compiler.py",
    ])
    def test_the_import_shim_cannot_break_its_host(self, source):
        """A missing trajectory.py must degrade to silence, not to an ImportError."""
        body = (SKILL_ROOT / source).read_text(encoding="utf-8")
        head = body[: body.index("record_trajectory")]
        assert "try:" in head
        assert "except Exception" in body[body.index("from trajectory import"):][:400]

    def test_both_delivery_browsers_hand_the_gate_a_resource_key(self):
        for source in ("scripts/coconala_formal_delivery_browser.py",
                       "scripts/coconala_paid_progress_browser.py"):
            body = (SKILL_ROOT / source).read_text(encoding="utf-8")
            assert "trajectory_context=trajectory_context" in body
            assert '"resource_key": f"talkroom:{' in body


# ── the classifier that makes sources_read_before_work possible ───────────────────────


class TestSourceClassification:
    @staticmethod
    def _key(path):
        from project_context_compiler import source_resource_key
        return source_resource_key(path, "91000002", "90000002")

    @pytest.mark.parametrize("path, expected", [
        # relative, as project_context_compiler._refs records them
        ("source/posting/request-91000002.json", "posting:91000002"),
        ("source/dm/thread-90000007-full.json", "dm:91000002"),
        ("source/dm/attachments/0da46b1e2f94-x.png", "dm:91000002"),
        ("source/talkroom/messages.jsonl", "talkroom:90000002"),
        ("requirements/live-buyer-reply.json", "project:91000002"),
        ("state.json", "project:91000002"),
        # absolute, as append_context_read_receipt appends the live DOM capture
        ("/workspace/gig/evidence/gig-pass-1/live-dom/talkroom-90000002.json", "talkroom:90000002"),
        ("/workspace/gig/projects/91000002/source/posting/request-91000002.json", "posting:91000002"),
    ])
    def test_relative_and_absolute_paths_classify_the_same(self, path, expected):
        assert self._key(path) == expected

    def test_every_classification_is_a_legal_resource_key(self):
        from project_context_compiler import source_resource_key
        for path in ("source/posting/a.json", "source/dm/b.json",
                     "source/talkroom/messages.jsonl", "state.json"):
            key = source_resource_key(path, "91000002", "90000002")
            assert trajectory.build_event(
                stage="PAID_WORK", lane="delivery", resource_key=key, action="read",
            )["resource_key"] == key


# ── the schema against a pass that really happened ────────────────────────────────────


class TestReplayOfRealEvidence:
    """spec §6 done-condition 1: it has to work on today's evidence, not on a fixture."""

    INCIDENT = Path.home() / "gig" / "evidence" / "gig-pass-1786075205-12532"

    @pytest.fixture
    def replayed(self, tmp_path):
        if not (self.INCIDENT / "context-read-receipt.json").is_file():
            pytest.skip("the 2026-08-07 incident evidence has been garbage-collected")
        sys.path.insert(0, str(SKILL_ROOT / "evals"))
        import replay_evidence

        sandbox = tmp_path / self.INCIDENT.name
        sandbox.mkdir()
        for name in ("context-read-receipt.json", "project-context-queue-item.json",
                     "paid-work-transaction.json", "reply-lane-result.json"):
            source = self.INCIDENT / name
            if source.is_file():
                (sandbox / name).write_bytes(source.read_bytes())
        return list(replay_evidence.replay(sandbox))

    def test_every_replayed_line_is_a_legal_event(self, replayed):
        assert replayed
        for event in replayed:
            assert event["action"] in trajectory.ACTIONS
            assert event["resource_key"].split(":")[0] in trajectory.RESOURCE_KINDS

    def test_accident_three_is_visible_two_lanes_touched_one_paid_room(self, replayed):
        """2026-08-07: the reply lane touched the room the delivery lane owned."""
        lanes = {
            event["lane"]
            for event in replayed
            if event["resource_key"] == "talkroom:90000002"
            and event["action"] in {"write", "deliver", "ask", "judge"}
        }
        assert lanes == {"delivery", "reply"}, lanes

    def test_accident_five_is_visible_neither_posting_nor_dm_was_read(self, replayed):
        """2026-08-07: two buyers were asked for material they had already sent."""
        kinds = {event["resource_key"].split(":")[0]
                 for event in replayed if event["action"] == "read"}
        assert "posting" not in kinds and "dm" not in kinds

    def test_the_replay_refuses_to_write_into_live_evidence(self, tmp_path):
        sys.path.insert(0, str(SKILL_ROOT / "evals"))
        import replay_evidence

        if not self.INCIDENT.is_dir():
            pytest.skip("no live evidence directory to point at")
        assert replay_evidence.main(["--evidence-dir", str(self.INCIDENT)]) == 2
