"""A pending prior formal delivery is the marketplace declining a duplicate, not a browser
bug -- the ledger must say so, not fall into formal_delivery_transaction_failed.

Mirrors tests/test_formal_delivery_routes_judge_refusal.py: same fixture builder, same
main()-driving + bash-branch-reading pinning pattern, applied to
AWAITING_BUYER_CONFIRMATION_EXIT instead of ROUTED_TO_ASK_EXIT.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import coconala_formal_delivery_browser as browser  # noqa: E402


def _project(tmp_path: Path) -> Path:
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


def _held_recovery_case(tmp_path: Path, evidence_dir: Path | None = None):
    root = _project(tmp_path)
    artifact = root / "deliverable-v1.zip"
    artifact.write_bytes(b"held artifact")
    digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
    contract = {
        "project_id": root.name, "talkroom_id": "93000000",
        "talkroom_url": "https://coconala.com/talkrooms/93000000", "artifact": artifact,
        "artifact_sha256": digest,
        "message": "お世話になっております。ご依頼いただいた件が仕上がりました。",
    }
    state = {
        "url": contract["talkroom_url"],
        "transaction_state": "取引完了",
        "buyer_formal_delivery_hold": True,
        "formal_delivery_control_disabled": True,
        "buyer_messages": [{"side": "buyer", "text": "正式な納品はまだ待ってください credential buyer-secret@example.com password=sekret"}],
        "seller_messages": [{"text": contract["message"], "attachments": [artifact.name]}],
    }
    state_path = root / "state.json"
    state_path.write_text(json.dumps({"request_id": root.name, "adapter": "coconala"}), encoding="utf-8")
    return root, contract, state, digest, evidence_dir or root / "evidence", root / "events.jsonl"


class _FakeDefaultTab:
    """Stands in for collector.DefaultTab: no real CDP subprocess in a unit test."""

    def __init__(self, *_args, **_kwargs):
        self.ws = "ws://fake"

    def __enter__(self):
        return self

    def __exit__(self, *_exc_info):
        return False


def test_main_returns_the_awaiting_confirmation_exit_code(tmp_path, monkeypatch):
    """execute() raising the pending-confirmation guard must surface as its own exit code,
    not the generic uncaught traceback gig_pass.sh cannot tell apart from a transport bug.
    """
    queue_path, manifest_path, root = _delivery_fixture(tmp_path)

    def fake_execute(*_args, **_kwargs):
        raise RuntimeError("awaiting_buyer_confirmation")

    monkeypatch.setattr(browser.artifact_judge, "refuse_unless_deliverable", lambda *_a, **_k: None)
    monkeypatch.setattr(browser.collector, "DefaultTab", _FakeDefaultTab)
    monkeypatch.setattr(browser, "execute", fake_execute)
    monkeypatch.setattr(sys, "argv", _argv(queue_path, manifest_path, root, tmp_path))

    assert browser.main() == browser.AWAITING_BUYER_CONFIRMATION_EXIT


def test_main_still_raises_other_runtime_errors_from_execute(tmp_path, monkeypatch):
    """Only the pending-confirmation message gets its own exit; every other RuntimeError out
    of execute() is a real transport fault and must keep today's fail-closed traceback.
    """
    queue_path, manifest_path, root = _delivery_fixture(tmp_path)

    def fake_execute(*_args, **_kwargs):
        raise RuntimeError("formal_checkbox_readback_failed")

    monkeypatch.setattr(browser.artifact_judge, "refuse_unless_deliverable", lambda *_a, **_k: None)
    monkeypatch.setattr(browser.collector, "DefaultTab", _FakeDefaultTab)
    monkeypatch.setattr(browser, "execute", fake_execute)
    monkeypatch.setattr(sys, "argv", _argv(queue_path, manifest_path, root, tmp_path))

    try:
        browser.main()
        raise AssertionError("expected RuntimeError to propagate")
    except RuntimeError as exc:
        assert str(exc) == "formal_checkbox_readback_failed"


def test_bash_branches_on_the_number_python_returns():
    """The exit code is written in two languages; only one of them has a type checker."""
    pass_sh = (Path(__file__).resolve().parents[1] / "gig_pass.sh").read_text(encoding="utf-8")
    needle = f'"$formal_rc" -eq {browser.AWAITING_BUYER_CONFIRMATION_EXIT} ]'
    assert needle in pass_sh
    # Matching the number is not enough: a `-ne 0` test placed above it makes the new branch
    # unreachable and silently restores formal_delivery_transaction_failed for this case too.
    assert pass_sh.index(needle) < pass_sh.index('"$formal_rc" -ne 0 ]')


def test_read_only_buyer_hold_ack_is_terminal_and_idempotent_without_delivery_effects(tmp_path):
    """A completed-room hold is observed, never sent, and written once per package."""
    root = _project(tmp_path)
    artifact = root / "deliverable-v1.zip"
    artifact.write_bytes(b"held artifact")
    digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
    contract = {
        "project_id": root.name,
        "talkroom_id": "93000000",
        "talkroom_url": "https://coconala.com/talkrooms/93000000",
        "artifact": artifact,
        "artifact_sha256": digest,
        "message": "お世話になっております。ご依頼いただいた件が仕上がりました。",
    }
    state = {
        "url": contract["talkroom_url"],
        "transaction_state": "取引完了",
        "buyer_formal_delivery_hold": True,
        "formal_delivery_control_disabled": True,
        "buyer_messages": [{"side": "buyer", "text": "正式な納品はまだ待ってください credential buyer-secret@example.com password=sekret"}],
        "seller_messages": [{
            "text": contract["message"],
            "attachments": [artifact.name],
        }],
    }
    state_path = root / "state.json"
    state_path.write_text(json.dumps({
        "request_id": root.name,
        "adapter": "coconala",
        "buyer_visible": False,
        "latest_buyer_visible_version": "v2",
        "delivery_confirmed_digest": "old",
        "handled_delivery_digest": "old",
    }), encoding="utf-8")
    ledger = root / "events.jsonl"
    evidence_dir = root / "evidence"

    first = browser.recover_buyer_hold_ack(
        contract, state, b"dom-screenshot", evidence_dir, ledger
    )
    first_persisted_state = json.loads(state_path.read_text(encoding="utf-8"))
    state_path.write_text(json.dumps({
        "request_id": root.name,
        "adapter": "coconala",
        "transaction_state": "取引完了",
    }), encoding="utf-8")
    second = browser.recover_buyer_hold_ack(
        contract, state, b"dom-screenshot", evidence_dir, ledger
    )

    assert first["terminal_state"] == "site_observed_buyer_hold"
    assert second["deduplicated"] is True
    persisted_state = json.loads(state_path.read_text(encoding="utf-8"))
    assert first_persisted_state["terminal_state"] == "site_observed_buyer_hold"
    assert first_persisted_state["delivery_send_suppressed_package_sha256"] == digest
    assert first_persisted_state["buyer_visible"] is False
    assert first_persisted_state["latest_buyer_visible_version"] == "v2"
    assert first_persisted_state["delivery_confirmed_digest"] == "old"
    assert first_persisted_state["handled_delivery_digest"] == "old"
    assert first_persisted_state["buyer_formal_delivery_hold"] is True
    assert first_persisted_state["buyer_formal_delivery_hold_reason"] == "buyer_explicit_formal_delivery_hold"
    assert persisted_state == {"request_id": root.name, "adapter": "coconala", "transaction_state": "取引完了"}
    events = [json.loads(line) for line in ledger.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert [row["event"] for row in events] == ["formal_delivery_observed_held"]
    assert len(events) == 1
    assert events[0]["state"]["delivery_send_suppressed_package_sha256"] == digest
    assert "FORMAL_DELIVERY_CONFIRMED" not in ledger.read_text(encoding="utf-8")
    dom_path = Path(first["dom_path"])
    assert first["dom_sha256"] == hashlib.sha256(dom_path.read_bytes()).hexdigest()
    assert first["screenshot_sha256"] == hashlib.sha256(
        Path(first["screenshot_path"]).read_bytes()
    ).hexdigest()
    evidence = json.loads((evidence_dir / "formal-delivery-held-evidence.json").read_text(encoding="utf-8"))
    assert evidence["transaction_state"] == "取引完了"
    serialized = json.dumps(
        {"result": first, "evidence": evidence, "state": first_persisted_state, "events": events},
        ensure_ascii=False,
    )
    assert "buyer-secret@example.com" not in serialized
    assert "password=sekret" not in serialized
    assert "buyer-secret@example.com" not in dom_path.read_text(encoding="utf-8")
    assert "password=sekret" not in dom_path.read_text(encoding="utf-8")


def test_buyer_hold_recovery_rebuilds_gc_manifest_from_durable_event(tmp_path, monkeypatch):
    """A GC'd held manifest is rebuilt from the append-only event without appending again."""
    canonical_evidence_root = tmp_path / "gig-evidence"
    monkeypatch.setenv("GIG_EVIDENCE_ROOT", str(canonical_evidence_root))
    root, contract, state, digest, evidence_dir, ledger = _held_recovery_case(
        tmp_path, canonical_evidence_root / "gig-pass-first"
    )
    state_path = root / "state.json"

    first = browser.recover_buyer_hold_ack(contract, state, b"dom-screenshot", evidence_dir, ledger)
    event_rows = [json.loads(line) for line in ledger.read_text(encoding="utf-8").splitlines() if line.strip()]
    historical_manifest = Path(event_rows[0]["state"]["formal_delivery_held_evidence_path"])
    historical_manifest.unlink()
    state_path.write_text(json.dumps({"request_id": root.name, "adapter": "coconala", "transaction_state": "取引完了"}), encoding="utf-8")

    def forbidden_append(*_args, **_kwargs):
        raise AssertionError("duplicate recovery must not append a new event")

    monkeypatch.setattr(browser.project_ledger, "append", forbidden_append)
    second = browser.recover_buyer_hold_ack(
        contract, state, b"dom-screenshot", canonical_evidence_root / "gig-pass-second", ledger
    )

    assert first["deduplicated"] is False
    assert second["deduplicated"] is True
    assert historical_manifest.is_file()
    rebuilt = json.loads(historical_manifest.read_text(encoding="utf-8"))
    assert {rebuilt[k] for k in ("event", "status", "terminal_state", "artifact_sha256", "transaction_state")} == {
        "formal_delivery_observed_held", "observed", "site_observed_buyer_hold", digest, "取引完了"
    }
    serialized = json.dumps({"result": second, "evidence": rebuilt}, ensure_ascii=False)
    assert "buyer-secret@example.com" not in serialized and "password=sekret" not in serialized
    events_after = [json.loads(line) for line in ledger.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(events_after) == 1
    assert events_after[0]["event"] == "formal_delivery_observed_held"


def test_buyer_hold_recovery_rejects_untrusted_historical_manifest_path(tmp_path, monkeypatch):
    """A corrupt event path falls back to current evidence and cannot overwrite outside it."""
    root, contract, state, _digest, evidence_dir, ledger = _held_recovery_case(tmp_path)
    browser.recover_buyer_hold_ack(contract, state, b"dom-screenshot", evidence_dir, ledger)
    safe_manifest = evidence_dir / "formal-delivery-held-evidence.json"
    safe_manifest.unlink()
    outside = tmp_path / "outside" / "victim.json"
    outside.parent.mkdir()
    outside.write_text("do-not-overwrite", encoding="utf-8")
    rows = [json.loads(line) for line in ledger.read_text(encoding="utf-8").splitlines() if line.strip()]
    rows[0]["state"]["formal_delivery_held_evidence_path"] = str(outside)
    ledger.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n", encoding="utf-8")

    def forbidden_append(*_args, **_kwargs):
        raise AssertionError("duplicate recovery must not append a new event")

    monkeypatch.setattr(browser.project_ledger, "append", forbidden_append)
    second = browser.recover_buyer_hold_ack(contract, state, b"dom-screenshot", evidence_dir, ledger)

    assert second["deduplicated"] is True
    assert outside.read_text(encoding="utf-8") == "do-not-overwrite"
    assert safe_manifest.is_file()
    assert Path(second["formal_delivery_held_evidence_path"]).resolve() == safe_manifest.resolve()


def test_buyer_hold_recovery_projects_existing_manifest_without_secrets(tmp_path, monkeypatch):
    """An existing but polluted manifest is projected before it can reach stdout."""
    root, contract, state, digest, evidence_dir, ledger = _held_recovery_case(tmp_path)
    browser.recover_buyer_hold_ack(contract, state, b"dom-screenshot", evidence_dir, ledger)
    manifest = evidence_dir / "formal-delivery-held-evidence.json"
    manifest.write_text(json.dumps({
        "event": "formal_delivery_observed_held", "status": "observed",
        "terminal_state": "site_observed_buyer_hold", "artifact_sha256": digest,
        "transaction_state": "取引完了", "buyer_messages": [{"text": "buyer-secret@example.com"}],
        "extra_secret": "password=sekret",
    }, ensure_ascii=False), encoding="utf-8")

    def forbidden_append(*_args, **_kwargs):
        raise AssertionError("duplicate recovery must not append a new event")

    monkeypatch.setattr(browser.project_ledger, "append", forbidden_append)
    second = browser.recover_buyer_hold_ack(contract, state, b"dom-screenshot", evidence_dir, ledger)
    serialized = json.dumps(second, ensure_ascii=False)
    persisted = json.loads(manifest.read_text(encoding="utf-8"))

    assert second["deduplicated"] is True
    assert "buyer-secret@example.com" not in serialized
    assert "password=sekret" not in serialized
    assert not {"buyer_messages", "extra_secret"} & persisted.keys()


def test_read_only_buyer_hold_ack_fails_closed_for_mismatch_hold_or_open_transaction(tmp_path):
    root = _project(tmp_path)
    artifact = root / "deliverable-v1.zip"
    artifact.write_bytes(b"held artifact")
    digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
    contract = {
        "project_id": root.name,
        "talkroom_id": "93000000",
        "talkroom_url": "https://coconala.com/talkrooms/93000000",
        "artifact": artifact,
        "artifact_sha256": digest,
        "message": "お世話になっております。ご依頼いただいた件が仕上がりました。",
    }
    base = {
        "url": contract["talkroom_url"],
        "transaction_state": "取引完了",
        "buyer_formal_delivery_hold": True,
        "formal_delivery_control_disabled": True,
        "seller_messages": [{"text": contract["message"], "attachments": [artifact.name]}],
    }
    for name, state in (
        ("mismatch", {**base, "seller_messages": []}),
        ("no-hold", {**base, "buyer_formal_delivery_hold": False}),
        ("open", {**base, "transaction_state": "取引中"}),
    ):
        with pytest.raises(ValueError):
            browser.recover_buyer_hold_ack(
                contract, state, b"dom-screenshot", root / name, root / f"{name}.jsonl"
            )
        assert not (root / name).exists()
        assert not (root / f"{name}.jsonl").exists()


def test_read_only_main_ack_never_enters_delivery_effect_path(tmp_path, monkeypatch, capsys):
    queue_path, manifest_path, root = _delivery_fixture(tmp_path)
    queue = json.loads(queue_path.read_text(encoding="utf-8"))
    queue["buyer_formal_delivery_hold"] = True
    queue_path.write_text(json.dumps(queue, ensure_ascii=False), encoding="utf-8")
    artifact = root / "deliverable.zip"
    state = {
        "url": "https://coconala.com/talkrooms/93000000", "transaction_state": "取引完了",
        "buyer_formal_delivery_hold": True, "formal_delivery_control_disabled": True,
        "buyer_messages": [{"side": "buyer", "text": "正式な納品はまだ待ってください credential buyer-secret@example.com password=sekret"}],
        "seller_messages": [{"text": browser.delivery_message(artifact.name, ["台本を書いた"]), "attachments": [artifact.name]}],
    }
    (root / "state.json").write_text(json.dumps({"request_id": root.name, "adapter": "coconala"}), encoding="utf-8")
    monkeypatch.setattr(browser.collector, "DefaultTab", _FakeDefaultTab)
    async def fake_read_only_capture(*_args, **_kwargs):
        return state, b"shot"
    monkeypatch.setattr(browser, "read_only_capture", fake_read_only_capture)
    for name in ("execute", "trusted_click", "trusted_click_send"):
        monkeypatch.setattr(browser, name, lambda *_a, _name=name, **_k: (_ for _ in ()).throw(AssertionError(_name)))
    monkeypatch.setattr(sys, "argv", _argv(queue_path, manifest_path, root, tmp_path) + ["--read-only"])
    assert browser.main() == 0
    captured = capsys.readouterr().out
    captured_result = json.loads(captured)
    assert captured_result["state"]["buyer_formal_delivery_hold"] is True
    assert captured_result["state"]["buyer_formal_delivery_hold_reason"] == "buyer_explicit_formal_delivery_hold"
    assert "buyer-secret@example.com" not in captured
    assert "password=sekret" not in captured
    evidence_files = list((tmp_path / "evidence").glob("*.json"))
    assert evidence_files
    assert all("buyer-secret@example.com" not in path.read_text(encoding="utf-8") for path in evidence_files)
    assert json.loads((root / "events.jsonl").read_text(encoding="utf-8"))["event"] == "formal_delivery_observed_held"
