from __future__ import annotations

import importlib.util
import json
from pathlib import Path


# P1a-7 (spec §0.1.6). Every open liability gets a disposition every pass: closed with a
# readback, or refused with a typed code and a concrete blocker.
#
# This is bookkeeping, not judgement. Which action to take — ask, extend, cancel, end — is
# the model's call. This module only records what was observably true at the end of the
# pass, so that "we did nothing" becomes "we did nothing because X, and here is X".
#
# The distinction matters because of what it enables later: `no_artifact_yet` recorded 47
# times against the same project root is not a legitimate wait, it is a defect, and only a
# typed refusal with a stable blocker id makes that countable. A free-text reason would be
# indistinguishable from a shrug.

MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "paid_lane_dispose.py"


def load(name: str):
    path = Path(__file__).resolve().parents[1] / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


KEY = "90000004:9292841a"
ROOM = {
    "talkroom_id": "90000004",
    "order_value_jpy": 2500,
    "liability_open": True,
    "liability_key": KEY,
    "title": "ウェブ画像の更新と軽微な調整",
}


def opened(tmp_path) -> Path:
    sl = load("silence_liability")
    store = tmp_path / "sl.jsonl"
    sl.observe(store, [ROOM], pass_id="pass-1")
    return store


# --- closing needs proof the buyer can see something --------------------------------------


def test_an_outbound_readback_closes_the_liability(tmp_path) -> None:
    m = load("paid_lane_dispose")
    sl = load("silence_liability")
    store = opened(tmp_path)
    m.dispose(
        store,
        pass_id="pass-1",
        readbacks={KEY: {"action": "ask_buyer", "posted_at": "2026-08-05T02:00:00+00:00"}},
        artifact_roots={},
    )
    assert sl.open_liabilities(store) == []


def test_a_readback_without_an_action_is_not_a_close(tmp_path) -> None:
    # A screenshot proves we looked. It does not prove we spoke.
    m = load("paid_lane_dispose")
    sl = load("silence_liability")
    store = opened(tmp_path)
    m.dispose(store, pass_id="pass-1", readbacks={KEY: {"posted_at": "x"}}, artifact_roots={})
    rows = sl.open_liabilities(store)
    assert len(rows) == 1
    assert rows[0]["last_refusal"]["code"] == "buyer_message_unparsed"


# --- refusals are derived from what was observable, and name the thing ---------------------


def test_no_artifact_refuses_and_names_the_project_root(tmp_path) -> None:
    m = load("paid_lane_dispose")
    sl = load("silence_liability")
    store = opened(tmp_path)
    m.dispose(
        store,
        pass_id="pass-1",
        readbacks={},
        artifact_roots={"90000004": str(tmp_path / "projects" / "90000004")},
    )
    refusal = sl.open_liabilities(store)[0]["last_refusal"]
    assert refusal["code"] == "no_artifact_yet"
    assert "90000004" in refusal["blocker_id"]


def test_an_existing_artifact_is_not_reported_as_missing(tmp_path) -> None:
    m = load("paid_lane_dispose")
    sl = load("silence_liability")
    store = opened(tmp_path)
    root = tmp_path / "projects" / "90000004" / "artifacts"
    root.mkdir(parents=True)
    (root / "v1.zip").write_text("x")
    m.dispose(
        store,
        pass_id="pass-1",
        readbacks={},
        artifact_roots={"90000004": str(tmp_path / "projects" / "90000004")},
    )
    # An artifact exists but was never sent — that is a different failure from having none,
    # and calling it no_artifact_yet would hide it.
    assert sl.open_liabilities(store)[0]["last_refusal"]["code"] == "awaiting_human_authority"


def test_an_exhausted_quota_is_named_as_such(tmp_path) -> None:
    m = load("paid_lane_dispose")
    sl = load("silence_liability")
    store = opened(tmp_path)
    m.dispose(
        store,
        pass_id="pass-1",
        readbacks={},
        artifact_roots={},
        quota_blocker="codex:keiodaisuke:transient_quota",
    )
    refusal = sl.open_liabilities(store)[0]["last_refusal"]
    assert refusal["code"] == "quota_exhausted"
    assert refusal["blocker_id"] == "codex:keiodaisuke:transient_quota"


# --- the pass can now end, which is the whole point ----------------------------------------


def test_after_disposing_the_gate_lets_the_pass_end(tmp_path) -> None:
    m = load("paid_lane_dispose")
    gate = load("paid_lane_pass_gate")
    store = opened(tmp_path)
    assert gate.check(store, pass_id="pass-1")["ok"] is False
    m.dispose(store, pass_id="pass-1", readbacks={}, artifact_roots={})
    assert gate.check(store, pass_id="pass-1")["ok"] is True


def test_every_open_liability_is_disposed_not_just_the_first(tmp_path) -> None:
    m = load("paid_lane_dispose")
    sl = load("silence_liability")
    gate = load("paid_lane_pass_gate")
    store = tmp_path / "sl.jsonl"
    second = {**ROOM, "liability_key": "90000000:aaaa", "talkroom_id": "90000000", "order_value_jpy": 40000}
    sl.observe(store, [ROOM, second], pass_id="pass-1")
    m.dispose(store, pass_id="pass-1", readbacks={}, artifact_roots={})
    assert gate.check(store, pass_id="pass-1")["ok"] is True


# --- a refusal that never resolves is a defect, not a state ---------------------------------


def test_a_refusal_repeated_without_ever_closing_is_reported_as_a_defect(tmp_path) -> None:
    m = load("paid_lane_dispose")
    sl = load("silence_liability")
    store = tmp_path / "sl.jsonl"
    for i in range(1, 13):
        sl.observe(store, [ROOM], pass_id=f"pass-{i}")
        m.dispose(store, pass_id=f"pass-{i}", readbacks={}, artifact_roots={})
    defects = m.dead_refusals(store, threshold=10)
    assert defects, "twelve identical refusals with no close is a structural deadlock"
    assert defects[0]["code"] == "no_artifact_yet"
    assert defects[0]["passes"] >= 12


def test_a_refusal_that_later_closes_is_not_a_defect(tmp_path) -> None:
    m = load("paid_lane_dispose")
    sl = load("silence_liability")
    store = tmp_path / "sl.jsonl"
    for i in range(1, 12):
        sl.observe(store, [ROOM], pass_id=f"pass-{i}")
        m.dispose(store, pass_id=f"pass-{i}", readbacks={}, artifact_roots={})
    sl.close(store, KEY, action="ask_buyer", outbound_readback={"posted_at": "x"}, pass_id="pass-12")
    assert m.dead_refusals(store, threshold=10) == []


def test_the_cli_disposes_and_reports(tmp_path, capsys) -> None:
    m = load("paid_lane_dispose")
    store = opened(tmp_path)
    rc = m.main(["--store", str(store), "--pass-id", "pass-1"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["disposed"] == 1
    assert payload["closed"] == 0
    assert payload["refused"] == 1


# --- deriving the project root, so the shell does not have to assemble JSON ----------------


def test_the_project_root_is_derived_from_the_talkroom_id(tmp_path) -> None:
    # gig_pass.sh would otherwise have to build a JSON map of every open talkroom, which is
    # a second place for the convention ~/gig/projects/<talkroom_id> to drift out of sync.
    m = load("paid_lane_dispose")
    sl = load("silence_liability")
    store = opened(tmp_path)
    projects = tmp_path / "projects"
    (projects / "90000004" / "artifacts").mkdir(parents=True)
    (projects / "90000004" / "artifacts" / "v23.zip").write_text("x")
    m.dispose(store, pass_id="pass-1", projects_root=str(projects))
    refusal = sl.open_liabilities(store)[0]["last_refusal"]
    assert refusal["code"] == "awaiting_human_authority"
    assert "90000004" in refusal["blocker_id"]


def test_an_explicit_root_still_wins_over_the_derived_one(tmp_path) -> None:
    m = load("paid_lane_dispose")
    sl = load("silence_liability")
    store = opened(tmp_path)
    projects = tmp_path / "projects"
    (projects / "90000004" / "artifacts").mkdir(parents=True)
    (projects / "90000004" / "artifacts" / "v1.zip").write_text("x")
    m.dispose(
        store,
        pass_id="pass-1",
        artifact_roots={"90000004": str(tmp_path / "elsewhere")},
        projects_root=str(projects),
    )
    assert sl.open_liabilities(store)[0]["last_refusal"]["code"] == "no_artifact_yet"


# --- the whole chain from one flag, so the shell stays simple -------------------------------


def test_evidence_alone_closes_the_liability(tmp_path) -> None:
    # gig_pass.sh should not have to assemble readbacks. Given the evidence directory the
    # pass already wrote, the disposer reads what was observed, what was intended, and closes
    # only where both agree.
    m = load("paid_lane_dispose")
    sl = load("silence_liability")
    store = opened(tmp_path)
    ev = tmp_path / "evidence" / "agent-90000004"
    ev.mkdir(parents=True)
    (ev / "paid-queue-live-dom.json").write_text(json.dumps({
        "url": "https://coconala.com/talkrooms/90000004",
        "messages": [
            {"side": "buyer", "text": "直りましたか", "attachments": []},
            {"side": "seller", "text": "修正しました", "attachments": []},
        ],
    }))
    (ev / "paid-queue-evidence.json").write_text(json.dumps({
        "sent": True, "mode": "answer", "talkroom_id": "90000004",
    }))
    result = m.dispose(store, pass_id="pass-1", evidence_dir=str(tmp_path / "evidence"))
    assert result["closed"] == 1
    assert sl.open_liabilities(store) == []


def test_evidence_showing_the_buyer_spoke_last_refuses_instead(tmp_path) -> None:
    m = load("paid_lane_dispose")
    sl = load("silence_liability")
    store = opened(tmp_path)
    ev = tmp_path / "evidence" / "agent-90000004"
    ev.mkdir(parents=True)
    (ev / "paid-queue-live-dom.json").write_text(json.dumps({
        "url": "https://coconala.com/talkrooms/90000004",
        "messages": [
            {"side": "seller", "text": "修正しました", "attachments": []},
            {"side": "buyer", "text": "まだ直っていません", "attachments": []},
        ],
    }))
    (ev / "paid-queue-evidence.json").write_text(json.dumps({
        "sent": True, "mode": "answer", "talkroom_id": "90000004",
    }))
    result = m.dispose(store, pass_id="pass-1", evidence_dir=str(tmp_path / "evidence"))
    assert result["closed"] == 0
    assert sl.open_liabilities(store)[0]["last_refusal"]["code"] == "no_artifact_yet"


def test_a_finished_build_is_refused_precisely_not_vaguely(tmp_path) -> None:
    # When the pass records that there was nothing new to build, the refusal must say that
    # rather than awaiting_human_authority. Both leave the liability open, but only one of
    # them is true, and dead_refusals is only useful if the code names the real blocker.
    m = load("paid_lane_dispose")
    sl = load("silence_liability")
    store = opened(tmp_path)
    ev = tmp_path / "evidence"
    ev.mkdir()
    (ev / "paid-work-no-new-version.json").write_text(json.dumps({
        "ok": False, "errors": ["artifact_version_not_newer_than_project_state"],
        "talkroom_id": "90000004", "artifact_version": "v12",
    }))
    projects = tmp_path / "projects"
    (projects / "90000004" / "artifacts").mkdir(parents=True)
    (projects / "90000004" / "artifacts" / "v12.html").write_text("x")

    m.dispose(store, pass_id="pass-1", evidence_dir=str(ev), projects_root=str(projects))
    refusal = sl.open_liabilities(store)[0]["last_refusal"]
    assert refusal["code"] == "no_new_work_required"
    assert "v12" in refusal["blocker_id"]


def test_without_that_record_it_falls_back_to_the_artifact_state(tmp_path) -> None:
    m = load("paid_lane_dispose")
    sl = load("silence_liability")
    store = opened(tmp_path)
    projects = tmp_path / "projects"
    (projects / "90000004" / "artifacts").mkdir(parents=True)
    (projects / "90000004" / "artifacts" / "v12.html").write_text("x")
    m.dispose(store, pass_id="pass-1", evidence_dir=str(tmp_path / "empty"), projects_root=str(projects))
    assert sl.open_liabilities(store)[0]["last_refusal"]["code"] == "awaiting_human_authority"
