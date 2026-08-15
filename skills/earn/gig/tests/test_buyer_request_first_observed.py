"""A request ages when the buyer speaks, never when we rewrite our own file.

Order 91000002, measured 2026-08-08. The buyer sent one revision request at 22:00 JST
on 2026-08-07. v5 was built, judged PASS and bound into the ledger at 22:07 -- seven
minutes after they asked. At 23:31 the collector re-observed the same message, and
c4d73e52 (A6) had changed what goes into ``feedback_sha256``, so the unchanged-poll
early return could not fire and the sidecar was rewritten with a fresh ``observed_at``
of 23:31.

``delivery_cadence._buyer_feedback_processed`` compares the artifact's mtime against
that field. v5 was now older than "the request", so the order read as unprocessed
feedback, routed to ``work_required``, and went back to the builder every pass for the
next nine hours with the finished, accepted file sitting on disk. A6 stabilised the
digest; nothing stabilised the clock the digest is read next to.

Three things are pinned here:
  * an unchanged buyer request keeps its age across a rewrite, including a rewrite
    caused by a change to the hashing rule itself;
  * a buyer who genuinely speaks again moves it forward -- the direction that costs
    money if it is wrong, because a stale artifact would read as an answer;
  * both readers of the field, the cadence and the project reconciler, use the same
    clock, and a sidecar written before the field existed still behaves as it did.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


collector = _load("coconala_queue_snapshot")
delivery_cadence = _load("delivery_cadence")
delivery_project = _load("delivery_project")

PROJECT = "91000002"
FIRST_SEEN = "2026-08-07T13:00:18.610840+00:00"
REHASHED_AT = "2026-08-07T14:31:10.637882+00:00"
# The four sentences the buyer actually sent, in the order the talkroom holds them.
REQUEST = [
    "確認させて頂きました！\nほぼ思った通りの仕上がりです！\nありがとうございます！",
    "画像を差し替えると周囲の枠まで一緒に動いてしまいます。",
    "枠が消えてしまっている。",
    "数字の下に消し切れていない線が残っているので消してほしい。",
]


def _messages(texts: list[str], *, delivered: bool = True) -> list[dict[str, object]]:
    """A conversation. ``delivered`` puts our own attachment before their reply,
    which is the cursor that makes the stage a revision rather than a brief."""
    rows: list[dict[str, object]] = []
    if delivered:
        rows.append({
            "side": "seller",
            "text": "初稿をお送りします。",
            "attachments": [{"filename": "draft.zip", "content_type": "application/zip"}],
        })
    rows.extend({"side": "buyer", "text": text, "attachments": []} for text in texts)
    return rows


def _observe(projects: Path, texts: list[str], at: str):
    return collector.persist_latest_paid_buyer_reply(
        {"url": "https://coconala.com/talkrooms/90000002", "messages": _messages(texts)},
        PROJECT, projects, at, source_talkroom_id="90000002",
    )


def _sidecar_path(projects: Path) -> Path:
    return projects / PROJECT / "requirements" / "live-buyer-reply.json"


def _sidecar(projects: Path) -> dict[str, object]:
    return json.loads(_sidecar_path(projects).read_text(encoding="utf-8"))


def _rehash_the_stored_digest(projects: Path) -> None:
    """Stand in for A6: same file, same message, a digest from the older rule.

    Nothing else is touched, so this isolates the one thing that changed on
    2026-08-07 at 23:31 -- the identity function, not the buyer.
    """
    path = _sidecar_path(projects)
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["feedback_sha256"] = "8" + payload["feedback_sha256"][1:]
    payload.pop("feedback_first_observed_at", None)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


# --------------------------------------------------------------------------
# 1. the collector: what makes the request older
# --------------------------------------------------------------------------

def test_a_rehash_of_one_unchanged_message_does_not_age_the_request(tmp_path):
    """The nine hours, in one assertion pair."""
    projects = tmp_path / "projects"
    _observe(projects, REQUEST, FIRST_SEEN)
    assert _sidecar(projects)["feedback_first_observed_at"] == FIRST_SEEN

    _rehash_the_stored_digest(projects)
    _observe(projects, REQUEST, REHASHED_AT)

    after = _sidecar(projects)
    # We rewrote the file, so our own clock moved. The buyer's did not.
    assert after["observed_at"] == REHASHED_AT
    assert after["feedback_first_observed_at"] == FIRST_SEEN


def test_a_new_buyer_statement_moves_the_request_forward(tmp_path):
    """★ The expensive direction. ★

    The window that defines the current request GROWS when the buyer adds to it, so
    the earliest sighting in it would still be the old one -- and an artifact built
    before they spoke would read as an answer to what they just said. The latest
    statement is the one an artifact has to postdate.
    """
    projects = tmp_path / "projects"
    _observe(projects, REQUEST, FIRST_SEEN)
    _observe(projects, [*REQUEST, "7コマ版も1点お願いできますか？"], REHASHED_AT)
    assert _sidecar(projects)["feedback_first_observed_at"] == REHASHED_AT


def test_an_unchanged_poll_does_not_rewrite_the_file_at_all(tmp_path):
    """The new field must not become a reason to rewrite once per hour."""
    projects = tmp_path / "projects"
    _observe(projects, REQUEST, FIRST_SEEN)
    before = _sidecar_path(projects).stat().st_mtime_ns

    result = _observe(projects, REQUEST, REHASHED_AT)

    assert _sidecar_path(projects).stat().st_mtime_ns == before
    assert result["feedback_sha256"] == _sidecar(projects)["feedback_sha256"]


def test_an_age_we_cannot_establish_is_now_rather_than_backdated(tmp_path):
    """Fail towards "this request is new", never towards "already answered"."""
    projects = tmp_path / "projects"
    rows = [{"sha256": "a" * 64, "first_observed_at": FIRST_SEEN}]
    unknown = [{"sha256": "b" * 64}]
    assert collector.request_first_observed_at(rows, unknown, REHASHED_AT) == REHASHED_AT
    assert collector.request_first_observed_at(None, unknown, REHASHED_AT) == REHASHED_AT
    assert collector.request_first_observed_at(rows, [], REHASHED_AT) == REHASHED_AT


def test_a_message_that_recorded_its_own_first_sighting_keeps_it(tmp_path):
    """The talkroom ledger knows when it saw each sentence; a poll does not."""
    projects = tmp_path / "projects"
    rows = collector._buyer_statement_rows(
        [
            {"side": "buyer", "text": REQUEST[1], "attachments": [], "observed_at": FIRST_SEEN},
            {"side": "buyer", "text": REQUEST[2], "attachments": []},
        ],
        REHASHED_AT,
    )
    assert [row["first_observed_at"] for row in rows] == [FIRST_SEEN, REHASHED_AT]
    assert projects is not None  # keeps the fixture signature honest


def test_an_unreadable_accumulation_is_recovered_from_the_message_ledger(tmp_path):
    """★ The machine has to unstick itself. ★

    Live 91000002 was found on 2026-08-08 with ``accumulated_requirements``
    flattened to bare strings, and later with the key gone entirely. Neither
    shape can name a current statement, so the request would look brand new every
    poll and a finished artifact would be thrown away every hour. The project's
    own append-only ledger still holds when the buyer said each of those things.
    """
    projects = tmp_path / "projects"
    _observe(projects, REQUEST, FIRST_SEEN)
    root = projects / PROJECT
    ledger = root / "source" / "talkroom" / "messages.jsonl"
    ledger.parent.mkdir(parents=True, exist_ok=True)
    ledger.write_text("\n".join(
        json.dumps({"side": "buyer", "text": text, "attachments": [],
                    "observed_at": FIRST_SEEN}, ensure_ascii=False)
        for text in REQUEST
    ) + "\n", encoding="utf-8")

    path = _sidecar_path(projects)
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["accumulated_requirements"] = ["写真を差し替える", "枠を復元する"]
    payload.pop("accumulated_sha256", None)
    payload.pop("feedback_first_observed_at", None)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    _observe(projects, REQUEST, REHASHED_AT)
    assert _sidecar(projects)["feedback_first_observed_at"] == FIRST_SEEN


# --------------------------------------------------------------------------
# 2. the readers: one clock, two call sites
# --------------------------------------------------------------------------

def _accepted_artifact(tmp_path, projects: Path, *, built_at: float) -> dict[str, object]:
    """A finished, accepted artifact bound to this project, with a real mtime."""
    root = projects / PROJECT
    artifact = root / "artifacts" / "order-v5.zip"
    artifact.parent.mkdir(parents=True, exist_ok=True)
    artifact.write_bytes(b"finished work")
    import os
    os.utime(artifact, (built_at, built_at))
    acceptance = root / "acceptance" / "acceptance-v5.json"
    acceptance.parent.mkdir(parents=True, exist_ok=True)
    acceptance.write_text("{}", encoding="utf-8")
    os.utime(acceptance, (built_at, built_at))
    import hashlib
    return {
        "project_root": str(root),
        "requirements_path": str(_sidecar_path(projects)),
        "artifact_path": str(artifact),
        "artifact_version": "v5",
        "acceptance_evidence_path": str(acceptance),
        "acceptance_status": "PASS",
        "package_sha256": hashlib.sha256(b"finished work").hexdigest(),
    }


def test_the_cadence_keeps_a_finished_artifact_after_a_rehash(tmp_path):
    projects = tmp_path / "projects"
    first = _observe(projects, REQUEST, FIRST_SEEN)
    # Built seven minutes after they asked, exactly like v5.
    item = _accepted_artifact(tmp_path, projects, built_at=1786108051.0)
    item["buyer_feedback_sha256"] = first["feedback_sha256"]
    assert delivery_cadence._buyer_feedback_processed(dict(item)) is True

    _rehash_the_stored_digest(projects)
    second = _observe(projects, REQUEST, REHASHED_AT)
    item["buyer_feedback_sha256"] = second["feedback_sha256"]
    assert delivery_cadence._buyer_feedback_processed(dict(item)) is True


def test_the_cadence_still_refuses_an_artifact_older_than_a_new_statement(tmp_path):
    projects = tmp_path / "projects"
    _observe(projects, REQUEST, FIRST_SEEN)
    item = _accepted_artifact(tmp_path, projects, built_at=1786108051.0)
    fresh = _observe(projects, [*REQUEST, "7コマ版も1点お願いできますか？"], REHASHED_AT)
    item["buyer_feedback_sha256"] = fresh["feedback_sha256"]
    assert delivery_cadence._buyer_feedback_processed(dict(item)) is False


def test_a_sidecar_written_before_the_field_existed_behaves_as_it_did(tmp_path):
    """Back-compat is a fallback to the old field, not a skipped check."""
    projects = tmp_path / "projects"
    first = _observe(projects, REQUEST, FIRST_SEEN)
    path = _sidecar_path(projects)
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload.pop("feedback_first_observed_at")
    payload["observed_at"] = "2126-01-01T00:00:00+00:00"
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    item = _accepted_artifact(tmp_path, projects, built_at=1786108051.0)
    item["buyer_feedback_sha256"] = first["feedback_sha256"]
    assert delivery_cadence._buyer_feedback_processed(dict(item)) is False


def test_the_project_reconciler_reads_the_same_clock(tmp_path):
    """Two functions asking one question of one file must not answer differently."""
    projects = tmp_path / "projects"
    _observe(projects, REQUEST, FIRST_SEEN)
    _rehash_the_stored_digest(projects)
    second = _observe(projects, REQUEST, REHASHED_AT)
    stable = _accepted_artifact(tmp_path, projects, built_at=1786108051.0)
    stable["acceptance_delta"] = ["直しました。"]
    stable["status"] = "ok"
    evidence_path = tmp_path / "delivery-evidence" / f"{PROJECT}.json"
    evidence_path.parent.mkdir(parents=True, exist_ok=True)
    evidence_path.write_text(json.dumps(stable, ensure_ascii=False), encoding="utf-8")
    item = {
        "buyer_feedback_sha256": second["feedback_sha256"],
        "buyer_feedback_requirements_path": str(_sidecar_path(projects)),
        "delivery_evidence": {"path": str(evidence_path), "present": True, **stable},
    }
    accepted = delivery_project._validated_accepted_artifact(projects / PROJECT, item)
    assert accepted is not None
