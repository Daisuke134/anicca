#!/usr/bin/env python3
"""BLOCKED and PASS cannot both be true about the same buyer feedback.

Order 91000002 is the whole reason. In one pass the build agent wrote
``evidence/acceptance-blocked.json`` saying the generic validator FAILed with
artifact_missing and that the buyer had specified no deliverable at all, and
``delivery/paid-work-result.json`` saying acceptance_status=PASS. Nothing read the first
file, the second drove a real delivery of a 1879-byte meta-document to a paying buyer,
and every gate in the pass agreed with it.

The fixtures below are the real files, copied. The point of the first test is that these
exact bytes now stop the delivery.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, SKILL / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


paid_work_evidence = _load("paid_work_evidence")


# This file is about one contradiction: BLOCKED and PASS in the same pass. The semantic
# judge is a separate gate with its own tests (tests/test_artifact_judge.py), and
# validate_paid_work now refuses anything no judge has seen -- so these calls say what the
# judge said and keep the subject of the test the contradiction, not the artifact.
def JUDGE_SAYS_DELIVERABLE(project_root, artifact_path, requirements_path=None):
    return "deliverable", "fixture: contradiction test, semantics out of scope"

# Verbatim from ~/gig/projects/91000002/requirements/live-buyer-reply.json. The buyer's
# entire instruction for a paid order: two lines of pleasantries.
REAL_FEEDBACK_SHA = "57b8719d5bd8ff77a7f68614fd9e9e6a4dbc35411094f43fd82891a103bdcfda"
REAL_REQUIREMENTS = {
    "version": 2,
    "source": "latest_buyer_request_before_first_delivery",
    "buyer_feedback_stage": "initial_request",
    "project_id": "91000002",
    "talkroom_id": "90000002",
    "observed_at": "2026-08-06T08:27:42.323306+00:00",
    "feedback_sha256": REAL_FEEDBACK_SHA,
    "feedback_text": "よろしくお願いいたします！！\n\n了解いたしました！\nどうぞよろしくお願いします！",
    "attachments": [],
}

# Verbatim from ~/gig/projects/91000002/evidence/acceptance-blocked.json, with the
# absolute paths rebased onto the fixture root by write_project().
REAL_BLOCKED = {
    "version": 1,
    "status": "BLOCKED",
    "requirements_path": "requirements/live-buyer-reply.json",
    "feedback_sha256": REAL_FEEDBACK_SHA,
    "checks": [
        {
            "command": "find source work artifacts acceptance delivery evidence -maxdepth 3 -type f -print | sort",
            "result": "source と work には買い手メッセージと整理記録のみがあり、実制作ソース、ビルドスクリプト、テストスクリプト、成果物は確認できませんでした。",
        },
        {
            "command": "python3 validation/validate_delivery_generic.py artifacts/delivery-v2.md",
            "result": "FAIL。検証対象の実成果物が存在しないため artifact_missing です。",
        },
    ],
    "blocker": "買い手の実質的な制作指示、納品物の種類、仕様、素材、既存ソース、ビルド手順がないため、内容を推測した成果物を作成できません。",
}

# Verbatim from ~/gig/projects/91000002/delivery/paid-work-result.json -- the record that
# actually shipped, written in the same pass as the BLOCKED file above.
REAL_ACCEPTANCE_DELTA = [
    "現在確認できる買い手からのメッセージと取引情報を確認資料としてまとめました。",
    "記載のない制作内容は推測せず、未確認の条件として明記しました。",
    "作業を始める前に必要な確認事項を買い手向けにまとめました。",
]


def write_project(
    tmp_path: Path,
    *,
    requirements_sha: str,
    blocked_sha: str | None,
    acceptance_status: str = "PASS",
) -> tuple[Path, Path]:
    """A project whose manifest is otherwise valid, plus an optional BLOCKED record."""
    root = tmp_path / "projects" / "91000002"
    for name in ("requirements", "artifacts", "acceptance", "delivery", "evidence"):
        (root / name).mkdir(parents=True)

    requirements = root / "requirements" / "live-buyer-reply.json"
    requirements.write_text(
        json.dumps(dict(REAL_REQUIREMENTS, feedback_sha256=requirements_sha), ensure_ascii=False),
        encoding="utf-8",
    )
    # The delivered file was a 1879-byte .md that the bootstrap validator waved through
    # because it exists, is over 1024 bytes, and has an allowed extension.
    artifact = root / "artifacts" / "delivery-v2.md"
    artifact.write_text("# 確認資料\n" + ("あ" * 1024), encoding="utf-8")
    acceptance = root / "acceptance" / "acceptance-v2.json"
    acceptance.write_text(
        json.dumps({"status": "PASS", "acceptance_delta": REAL_ACCEPTANCE_DELTA}, ensure_ascii=False),
        encoding="utf-8",
    )
    if blocked_sha is not None:
        (root / "evidence" / "acceptance-blocked.json").write_text(
            json.dumps(
                dict(
                    REAL_BLOCKED,
                    feedback_sha256=blocked_sha,
                    requirements_path=str(requirements),
                ),
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
    row = {
        "status": "ok",
        "project_root": str(root),
        "requirements_path": str(requirements),
        "artifact_path": str(artifact),
        "artifact_version": "v2",
        "acceptance_evidence_path": str(acceptance),
        "acceptance_status": acceptance_status,
        "acceptance_delta": REAL_ACCEPTANCE_DELTA,
        "package_sha256": hashlib.sha256(artifact.read_bytes()).hexdigest(),
    }
    (root / "state.json").write_text('{"current_version":"v1"}\n', encoding="utf-8")
    (root / "delivery" / "paid-work-result.json").write_text(
        json.dumps(row, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    evidence = tmp_path / "delivery-evidence" / "91000002.json"
    evidence.parent.mkdir(parents=True)
    evidence.write_text(json.dumps(row, ensure_ascii=False) + "\n", encoding="utf-8")
    return root, evidence


def test_the_real_91000002_delivery_is_refused(tmp_path):
    """§5-1: the exact pair of files that shipped now fails the gate."""
    root, evidence = write_project(
        tmp_path, requirements_sha=REAL_FEEDBACK_SHA, blocked_sha=REAL_FEEDBACK_SHA
    )
    ok, errors = paid_work_evidence.validate_paid_work(root, evidence, artifact_judge=JUDGE_SAYS_DELIVERABLE)
    assert ok is False
    assert "acceptance_pass_contradicts_blocked_evidence" in errors, errors


def test_only_a_fresh_review_path_can_resolve_the_current_block(tmp_path):
    root, evidence = write_project(
        tmp_path, requirements_sha=REAL_FEEDBACK_SHA, blocked_sha=REAL_FEEDBACK_SHA
    )
    source = root / "evidence" / "acceptance-blocked.json"
    original = source.read_bytes()
    artifact_sha = json.loads(
        (root / "delivery" / "paid-work-result.json").read_text(encoding="utf-8")
    )["package_sha256"]

    ok, errors = paid_work_evidence.validate_paid_work(
        root,
        evidence,
        artifact_judge=JUDGE_SAYS_DELIVERABLE,
        allow_fresh_blocked_for_review=True,
    )
    assert ok is True, errors
    archived = paid_work_evidence.resolve_fresh_blocked_after_review(
        root,
        root / "requirements" / "live-buyer-reply.json",
        REAL_FEEDBACK_SHA,
        artifact_sha,
    )
    assert archived == (
        root / "evidence" / "resolved-blocked" / f"{REAL_FEEDBACK_SHA}-{artifact_sha}.json"
    )
    assert source.exists() is False
    assert archived.read_bytes() == original

    source.write_bytes(original)
    assert paid_work_evidence.resolve_fresh_blocked_after_review(
        root,
        root / "requirements" / "live-buyer-reply.json",
        REAL_FEEDBACK_SHA,
        artifact_sha,
    ) == archived
    assert source.exists() is False

    ok, errors = paid_work_evidence.validate_paid_work(
        root, evidence, artifact_judge=JUDGE_SAYS_DELIVERABLE
    )
    assert ok is True, errors


def test_a_block_the_buyer_already_answered_does_not_freeze_the_order(tmp_path):
    """§5-2: a BLOCKED record naming older feedback is spent, not a contradiction.

    Without this the first unanswerable pass would brick the project forever: the file
    survives rollback, so a permanent BLOCKED would outlive the buyer's reply.
    """
    root, evidence = write_project(
        tmp_path, requirements_sha="a" * 64, blocked_sha=REAL_FEEDBACK_SHA
    )
    ok, errors = paid_work_evidence.validate_paid_work(root, evidence, artifact_judge=JUDGE_SAYS_DELIVERABLE)
    assert "acceptance_pass_contradicts_blocked_evidence" not in errors, errors
    assert ok is True, errors


def test_a_project_that_never_blocked_is_unaffected(tmp_path):
    root, evidence = write_project(
        tmp_path, requirements_sha=REAL_FEEDBACK_SHA, blocked_sha=None
    )
    ok, errors = paid_work_evidence.validate_paid_work(root, evidence, artifact_judge=JUDGE_SAYS_DELIVERABLE)
    assert ok is True, errors


def test_the_contradiction_is_about_pass_not_about_being_blocked(tmp_path):
    """A manifest that does not claim PASS is already refused for that reason.

    Pinned so the new error cannot start doubling up on an existing one and make a
    failure list say two things about one fact.
    """
    root, evidence = write_project(
        tmp_path,
        requirements_sha=REAL_FEEDBACK_SHA,
        blocked_sha=REAL_FEEDBACK_SHA,
        acceptance_status="FAIL",
    )
    ok, errors = paid_work_evidence.validate_paid_work(root, evidence, artifact_judge=JUDGE_SAYS_DELIVERABLE)
    assert ok is False
    assert "acceptance_status_not_pass" in errors, errors
    assert "acceptance_pass_contradicts_blocked_evidence" not in errors, errors


def test_an_unparseable_blocked_record_refuses_the_delivery(tmp_path):
    """★Fails closed.★ A gate that cannot read the record has not cleared it.

    And the incentive matters as much as the safety: if malformed JSON read as "no block",
    the cheapest way past the contradiction check would be to write malformed JSON.
    """
    root, evidence = write_project(
        tmp_path, requirements_sha=REAL_FEEDBACK_SHA, blocked_sha=REAL_FEEDBACK_SHA
    )
    (root / "evidence" / "acceptance-blocked.json").write_text(
        '{"version":1,"status":"BLOC', encoding="utf-8")
    ok, errors = paid_work_evidence.validate_paid_work(root, evidence, artifact_judge=JUDGE_SAYS_DELIVERABLE)
    assert ok is False
    assert "blocked_evidence_undeterminable" in errors, errors


def test_an_unloadable_reader_refuses_the_delivery(tmp_path, monkeypatch):
    root, evidence = write_project(
        tmp_path, requirements_sha=REAL_FEEDBACK_SHA, blocked_sha=None
    )
    monkeypatch.setattr(paid_work_evidence, "_ASK_BUYER", None)
    monkeypatch.setattr(paid_work_evidence, "_ask_buyer_module", lambda: None)
    ok, errors = paid_work_evidence.validate_paid_work(root, evidence, artifact_judge=JUDGE_SAYS_DELIVERABLE)
    assert ok is False
    assert "blocked_evidence_undeterminable" in errors, errors


def test_an_unreadable_feedback_digest_refuses_the_delivery(tmp_path):
    """BLOCKED is present and parses, but freshness cannot be decided."""
    root, evidence = write_project(
        tmp_path, requirements_sha=REAL_FEEDBACK_SHA, blocked_sha=REAL_FEEDBACK_SHA
    )
    # The requirements file the manifest points at no longer carries a digest, so neither
    # "this block is current" nor "the buyer answered" can be established.
    (root / "requirements" / "live-buyer-reply.json").write_text(
        json.dumps({"feedback_text": "よろしくお願いいたします！！"}, ensure_ascii=False),
        encoding="utf-8",
    )
    ok, errors = paid_work_evidence.validate_paid_work(root, evidence, artifact_judge=JUDGE_SAYS_DELIVERABLE)
    assert ok is False
    assert "blocked_evidence_undeterminable" in errors, errors


def test_a_blocked_record_without_a_digest_is_undeterminable_not_stale(tmp_path):
    root, evidence = write_project(
        tmp_path, requirements_sha=REAL_FEEDBACK_SHA, blocked_sha=REAL_FEEDBACK_SHA
    )
    payload = json.loads((root / "evidence" / "acceptance-blocked.json").read_text(encoding="utf-8"))
    payload.pop("feedback_sha256")
    (root / "evidence" / "acceptance-blocked.json").write_text(
        json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    ok, errors = paid_work_evidence.validate_paid_work(root, evidence, artifact_judge=JUDGE_SAYS_DELIVERABLE)
    assert ok is False
    assert "blocked_evidence_undeterminable" in errors, errors


def test_the_healthy_absent_case_stays_silent(tmp_path):
    """An absent record is the normal case and must not add noise to every clean pass."""
    root, evidence = write_project(
        tmp_path, requirements_sha=REAL_FEEDBACK_SHA, blocked_sha=None
    )
    ok, errors = paid_work_evidence.validate_paid_work(root, evidence, artifact_judge=JUDGE_SAYS_DELIVERABLE)
    assert ok is True, errors
    assert "blocked_evidence_undeterminable" not in errors

    # So is a record that determinately says something other than BLOCKED.
    (root / "evidence" / "acceptance-blocked.json").write_text(
        json.dumps({"version": 1, "status": "PASS"}), encoding="utf-8")
    ok, errors = paid_work_evidence.validate_paid_work(root, evidence, artifact_judge=JUDGE_SAYS_DELIVERABLE)
    assert ok is True, errors


def test_the_verdict_names_all_four_outcomes(tmp_path):
    verdict = paid_work_evidence.blocked_evidence_verdict

    root, _ = write_project(tmp_path / "fresh", requirements_sha=REAL_FEEDBACK_SHA,
                            blocked_sha=REAL_FEEDBACK_SHA)
    assert verdict(root)[0] == paid_work_evidence.BLOCK_FRESH

    root, _ = write_project(tmp_path / "stale", requirements_sha="c" * 64,
                            blocked_sha=REAL_FEEDBACK_SHA)
    assert verdict(root)[0] == paid_work_evidence.BLOCK_STALE

    root, _ = write_project(tmp_path / "absent", requirements_sha=REAL_FEEDBACK_SHA,
                            blocked_sha=None)
    assert verdict(root)[0] == paid_work_evidence.BLOCK_ABSENT

    root, _ = write_project(tmp_path / "broken", requirements_sha=REAL_FEEDBACK_SHA,
                            blocked_sha=REAL_FEEDBACK_SHA)
    (root / "evidence" / "acceptance-blocked.json").write_text("not json", encoding="utf-8")
    assert verdict(root)[0] == paid_work_evidence.BLOCK_UNDETERMINABLE


def test_fresh_blocked_state_is_the_shared_freshness_rule(tmp_path):
    """The gate and the question lane read one predicate, so they cannot disagree."""
    root, _ = write_project(
        tmp_path, requirements_sha=REAL_FEEDBACK_SHA, blocked_sha=REAL_FEEDBACK_SHA
    )
    state = paid_work_evidence.fresh_blocked_state(root)
    assert state is not None
    assert state["status"] == "BLOCKED"
    assert state["feedback_sha256"] == REAL_FEEDBACK_SHA

    stale_root, _ = write_project(
        tmp_path / "stale", requirements_sha="b" * 64, blocked_sha=REAL_FEEDBACK_SHA
    )
    assert paid_work_evidence.fresh_blocked_state(stale_root) is None

    clean_root, _ = write_project(
        tmp_path / "clean", requirements_sha=REAL_FEEDBACK_SHA, blocked_sha=None
    )
    assert paid_work_evidence.fresh_blocked_state(clean_root) is None
