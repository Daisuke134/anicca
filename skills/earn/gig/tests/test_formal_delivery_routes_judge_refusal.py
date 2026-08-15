"""A judge refusal the buyer can answer must become a question, not a dead process."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import artifact_judge  # noqa: E402
import coconala_formal_delivery_browser as browser  # noqa: E402
import first_contact  # noqa: E402
import paid_work_evidence  # noqa: E402

ASK_REFUSAL = ValueError(
    f"{artifact_judge.ERROR_NEEDS_BUYER_INPUT}:"
    "記録には題材と納品形式しかなく、何をどこまで作るかが確定できていません"
)


def _project(tmp_path: Path) -> Path:
    """A project the ask lane can actually read.

    ``blocked_evidence_verdict`` only reports ``fresh`` when the BLOCKED record carries the
    same 64-hex digest as the requirements sidecar it points at. A project without that
    sidecar produces a record the ask lane rejects as ``undeterminable`` -- which is the
    silence this whole change exists to end, so the fixture has to carry it.
    """
    root = tmp_path / "9000001"
    (root / "context").mkdir(parents=True)
    (root / "requirements").mkdir(parents=True)
    feedback_text = "サンプルの動画を作ってほしいです"
    digest = hashlib.sha256(feedback_text.encode("utf-8")).hexdigest()
    requirements_path = root / "requirements" / "live-buyer-reply.json"
    requirements_path.write_text(
        json.dumps({"feedback_sha256": digest, "feedback_text": feedback_text},
                   ensure_ascii=False),
        encoding="utf-8",
    )
    (root / "context" / "current.json").write_text(
        json.dumps({
            "combined_context": {
                "requirements": {
                    "path": str(requirements_path),
                    "everything_the_buyer_has_asked_for": [{"text": feedback_text}],
                },
            },
        }, ensure_ascii=False),
        encoding="utf-8",
    )
    return root


def _delivery_fixture(tmp_path: Path) -> tuple[Path, Path, Path]:
    """The queue item + manifest pair a real formal delivery is invoked with."""
    root = _project(tmp_path)
    artifact = root / "deliverable.zip"
    artifact.write_bytes(b"final artifact bytes")
    digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
    acceptance = root / "acceptance.json"
    acceptance.write_text(
        json.dumps({"status": "PASS", "package": {"sha256": digest}}), encoding="utf-8"
    )
    manifest = {
        "status": "ok",
        "acceptance_status": "PASS",
        "project_root": str(root),
        "artifact_path": str(artifact),
        "artifact_version": "v1",
        "acceptance_evidence_path": str(acceptance),
        "acceptance_delta": ["台本を書いた"],
        "package_sha256": digest,
    }
    queue = {
        "delivery_action": "formal",
        "formal_delivery_checkbox": True,
        "delivery_evidence": {
            key: manifest[key]
            for key in (
                "artifact_path", "artifact_version", "acceptance_evidence_path",
                "acceptance_status", "acceptance_delta", "package_sha256",
            )
        },
        "talkroom_id": "93000000",
        "request_id": "9000001",
        "title": "サンプル動画の企画・台本作成",
        # Synthetic ids, but the host is real on purpose: validate_queue_contract raises
        # formal_queue_identity_invalid on any other hostname, so example.com would fail the
        # contract before the judge is ever reached.
        "marketplace_url": "https://coconala.com/talkrooms/93000000",
    }
    queue_path = tmp_path / "queue.json"
    queue_path.write_text(json.dumps(queue, ensure_ascii=False), encoding="utf-8")
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
    return queue_path, manifest_path, root


def _argv(queue_path: Path, manifest_path: Path, root: Path, tmp_path: Path) -> list[str]:
    return [
        "coconala_formal_delivery_browser.py",
        "--queue-item", str(queue_path),
        "--manifest", str(manifest_path),
        "--project-root", str(root),
        "--evidence-dir", str(tmp_path / "evidence"),
        "--ledger", str(root / "events.jsonl"),
        "--default-tab-helper", str(tmp_path / "cdp_default_tab.py"),
    ]


def test_ask_refusal_becomes_the_blocked_record_the_ask_lane_reads(tmp_path):
    root = _project(tmp_path)

    routed = browser.route_judge_refusal(
        ASK_REFUSAL, root, {"title": "サンプル動画の企画・台本作成"}
    )

    assert routed["decision"] == "ask"
    assert routed["blocked_record_written"] is True
    assert routed["source"] == "artifact_judge"
    # Written is not the same as readable. The ask lane sends nothing on anything but fresh.
    assert paid_work_evidence.blocked_evidence_verdict(root)[0] == paid_work_evidence.BLOCK_FRESH


def test_a_refusal_the_buyer_cannot_answer_still_raises(tmp_path):
    root = _project(tmp_path)
    refusal = ValueError(f"{artifact_judge.ERROR_NOT_THE_ORDER}:別物が入っています")

    with pytest.raises(ValueError, match=artifact_judge.ERROR_NOT_THE_ORDER):
        browser.route_judge_refusal(refusal, root, {"title": "irrelevant"})


def test_main_exits_with_the_code_the_pass_reads_as_a_routed_refusal(tmp_path, monkeypatch):
    """The boundary the whole change exists for: the exit code bash actually branches on.

    Without this, ROUTED_TO_ASK_EXIT could be renumbered with every test still green while
    the pass silently went back to blaming the browser transport.
    """
    queue_path, manifest_path, root = _delivery_fixture(tmp_path)

    def refuse(*_args, **_kwargs):
        raise ASK_REFUSAL

    monkeypatch.setattr(browser.artifact_judge, "refuse_unless_deliverable", refuse)
    monkeypatch.setattr(sys, "argv", _argv(queue_path, manifest_path, root, tmp_path))

    assert browser.main() == 7
    assert paid_work_evidence.blocked_evidence_verdict(root)[0] == paid_work_evidence.BLOCK_FRESH


def test_main_still_dies_when_the_question_was_never_written(tmp_path, monkeypatch):
    """An unwritten record means the ask lane has no input, so nothing may claim it does."""
    queue_path, manifest_path, root = _delivery_fixture(tmp_path)

    def refuse(*_args, **_kwargs):
        raise ASK_REFUSAL

    monkeypatch.setattr(browser.artifact_judge, "refuse_unless_deliverable", refuse)
    monkeypatch.setattr(first_contact, "write_blocked_record", lambda *_a, **_k: False)
    monkeypatch.setattr(sys, "argv", _argv(queue_path, manifest_path, root, tmp_path))

    with pytest.raises(ValueError) as excinfo:
        browser.main()
    # The refusal itself, not some other ValueError the fixture happened to trip on --
    # validate_queue_contract raises ValueError too.
    assert excinfo.value is ASK_REFUSAL


def test_main_still_dies_when_the_written_question_is_unreadable(tmp_path, monkeypatch):
    """Written is not queued. A record the ask lane cannot key on sends nothing.

    order_brief fills feedback_sha256 best-effort, so a record whose digest does not match
    the requirements file it points at is written and grades undeterminable. Deleting the
    sidecar is simply the cheapest way to produce that shape -- it is not a claim about how
    often it occurs on disk. gig_pass.sh's first_contact_redirect would read no standing
    refusal from this and route the order back to a plain delivery attempt on the next pass,
    while this exit code claimed a redirect was already queued.
    """
    queue_path, manifest_path, root = _delivery_fixture(tmp_path)
    (root / "requirements" / "live-buyer-reply.json").unlink()

    def refuse(*_args, **_kwargs):
        raise ASK_REFUSAL

    monkeypatch.setattr(browser.artifact_judge, "refuse_unless_deliverable", refuse)
    monkeypatch.setattr(sys, "argv", _argv(queue_path, manifest_path, root, tmp_path))

    with pytest.raises(ValueError) as excinfo:
        browser.main()
    assert excinfo.value is ASK_REFUSAL
    assert paid_work_evidence.blocked_evidence_verdict(root)[0] != paid_work_evidence.BLOCK_FRESH


def test_bash_branches_on_the_number_python_returns():
    """The exit code is written in two languages; only one of them has a type checker."""
    pass_sh = (Path(__file__).resolve().parents[1] / "gig_pass.sh").read_text(encoding="utf-8")
    assert f'"$formal_rc" -eq {browser.ROUTED_TO_ASK_EXIT} ]' in pass_sh
    # Matching the number is not enough: a `-ne 0` test placed above it makes the routed
    # branch unreachable and silently restores formal_delivery_transaction_failed.
    assert pass_sh.index(f'"$formal_rc" -eq {browser.ROUTED_TO_ASK_EXIT} ]') < pass_sh.index('"$formal_rc" -ne 0 ]')
