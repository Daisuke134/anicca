from __future__ import annotations

import importlib.util
import json
import os
import zipfile
from pathlib import Path
from types import SimpleNamespace

import pytest


PAID_PATH = Path(__file__).resolve().parents[1] / "scripts" / "paid_direct.py"


def _load_paid():
    spec = importlib.util.spec_from_file_location("paid_direct_disk_preflight_test", PAID_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_paid_browser_diagnostics_use_private_data_redactor():
    paid = _load_paid()

    assert paid.redact_prompt_text("password:secret-value") == "password:[REDACTED]"


def test_audio_only_zip_does_not_require_visual_review_images(tmp_path):
    paid = _load_paid()
    root = tmp_path / "project"
    delivery = root / "delivery"
    delivery.mkdir(parents=True)
    artifact = delivery / "review.zip"
    with zipfile.ZipFile(artifact, "w") as archive:
        archive.writestr("review.mp3", b"audio")
    digest = paid.hashlib.sha256(artifact.read_bytes()).hexdigest()
    (delivery / "paid-work-result.json").write_text(json.dumps({
        "artifact_path": str(artifact),
        "package_sha256": digest,
    }), encoding="utf-8")

    assert paid._file_review_images(root, digest) == []


def test_browser_contract_failure_becomes_owner_repair_finding():
    paid = _load_paid()
    process = SimpleNamespace(
        stdout='{"ok":false,"contract_invalid":"buyer_style_violation:evidence"}\n',
    )

    assert paid._browser_contract_finding(process) == "buyer_style_violation:evidence"


def test_non_contract_browser_failure_is_not_owner_repair_finding():
    paid = _load_paid()

    assert paid._browser_contract_finding(SimpleNamespace(stdout="")) is None


def test_inflight_gate_reports_pressure(monkeypatch):
    paid = _load_paid()
    monkeypatch.setattr(paid, "disk_headroom_ok", lambda: False)

    assert paid._disk_gate_reason() == "disk_pressure"


def test_inflight_gate_fails_closed_when_probe_errors(monkeypatch):
    paid = _load_paid()

    def unavailable():
        raise OSError("control state unavailable")

    monkeypatch.setattr(paid, "disk_headroom_ok", unavailable)

    assert paid._disk_gate_reason() == "disk_preflight_error:OSError"


@pytest.mark.parametrize(
    ("brake_status", "expected"),
    (("held", "operator_brake"), ("free", None), ("failed", "operator_brake_check_failed")),
)
def test_effect_gate_uses_expiring_brake_contract(monkeypatch, tmp_path, brake_status, expected):
    paid = _load_paid()
    path = tmp_path / "operator.brake"
    monkeypatch.setattr(paid, "disk_headroom_ok", lambda: True)
    seen = []

    def status(received):
        seen.append(received)
        return brake_status

    monkeypatch.setattr(paid, "_operator_brake_status", status)

    assert paid._effect_gate_reason(SimpleNamespace(operator_brake=path)) == expected
    assert seen == [path]


def test_write_item_gate_returns_no_effect_pending_checkpoint(tmp_path, monkeypatch):
    paid = _load_paid()
    item_path = tmp_path / "item-room.json"
    item_path.write_text(json.dumps({"talkroom_id": "room", "_paid_mode": "remote"}), encoding="utf-8")
    output = tmp_path / "effect.json"
    args = SimpleNamespace()
    monkeypatch.setenv("CLOAK_BROWSER_OWNER", "paid-direct-room")
    monkeypatch.setattr(paid, "disk_headroom_ok", lambda: False)

    assert paid._write_one(args, item_path, output) == 0

    row = json.loads(output.read_text(encoding="utf-8"))
    assert row["status"] == "pending"
    assert row["effect"] == row["readback"] == 0
    assert row["checkpoint"] == "before_paid_effect"


def test_paid_item_keeps_atomic_checkpoint_when_effect_child_reports_pressure(tmp_path, monkeypatch):
    paid = _load_paid()
    monkeypatch.setattr(paid, "disk_headroom_ok", lambda: True)
    item_file = tmp_path / "item.json"
    prepared_file = tmp_path / "item-prepared.json"
    effect_file = tmp_path / "item-result.json"
    item_file.write_text("{}", encoding="utf-8")
    calls = []

    def fake_run(command, **_kwargs):
        calls.append(command)
        if "--effect-item" in command:
            prepared_file.write_text(
                json.dumps({"_paid_prepare_status": "prepared", "talkroom_id": "room"}),
                encoding="utf-8",
            )
        else:
            effect_file.write_text(
                json.dumps({"status": "pending", "checkpoint": "before_paid_effect",
                            "reason": "disk_pressure"}),
                encoding="utf-8",
            )
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(paid, "_run_bounded", fake_run)
    monkeypatch.setattr(paid, "_prepare_command", lambda *_args: ["--effect-item"])
    monkeypatch.setattr(paid, "_effect_command", lambda *_args: ["--write-item"])
    monkeypatch.setattr(paid, "_fresh_child_env", lambda _args, owner=None: os.environ.copy())

    row, effect, readback, failed, step = paid._run_paid_item(
        SimpleNamespace(), "room", item_file, prepared_file, effect_file,
    )

    assert calls == [["--effect-item"], ["--write-item"]]
    assert row["status"] == "pending"
    assert effect == readback == failed == 0
    assert step == ""
    checkpoint = effect_file.with_name("item-result-checkpoint.json")
    assert checkpoint.is_file()
    assert json.loads(checkpoint.read_text(encoding="utf-8"))["effect"] == 0


def test_parent_disk_checkpoint_is_atomic_and_private(tmp_path):
    paid = _load_paid()
    args = SimpleNamespace(evidence_dir=tmp_path)

    checkpoint = paid._persist_disk_checkpoint(
        args, "room", {"buyer_feedback_sha256": "a" * 64, "buyer": "private"},
        "disk_pressure", "before_project_queue_mutation",
    )

    assert checkpoint is not None
    row = json.loads(Path(checkpoint).read_text(encoding="utf-8"))
    assert row == {
        "version": 1,
        "status": "pending",
        "talkroom_id": "room",
        "buyer_feedback_sha256": "a" * 64,
        "effect": 0,
        "readback": 0,
        "checkpoint": "before_project_queue_mutation",
        "reason": "disk_pressure",
    }
    assert "private" not in Path(checkpoint).read_text(encoding="utf-8")


def test_effect_failure_with_observed_send_advances_checkpoint_to_unknown(tmp_path, monkeypatch):
    paid = _load_paid()
    monkeypatch.setattr(paid, "disk_headroom_ok", lambda: True)
    item_file = tmp_path / "item.json"
    prepared_file = tmp_path / "item-prepared.json"
    effect_file = tmp_path / "item-result.json"
    item_file.write_text("{}", encoding="utf-8")

    def fake_run(command, **_kwargs):
        if "--effect-item" in command:
            prepared_file.write_text(
                json.dumps({"_paid_prepare_status": "prepared", "talkroom_id": "room"}),
                encoding="utf-8",
            )
        else:
            effect_file.write_text(
                json.dumps({"status": "failed", "effect": 1, "readback": 0,
                            "failed_step": "official_readback"}),
                encoding="utf-8",
            )
        return SimpleNamespace(returncode=1 if "--write-item" in command else 0)

    monkeypatch.setattr(paid, "_run_bounded", fake_run)
    monkeypatch.setattr(paid, "_prepare_command", lambda *_args: ["--effect-item"])
    monkeypatch.setattr(paid, "_effect_command", lambda *_args: ["--write-item"])
    monkeypatch.setattr(paid, "_fresh_child_env", lambda _args, owner=None: os.environ.copy())

    row, effect, readback, failed, step = paid._run_paid_item(
        SimpleNamespace(), "room", item_file, prepared_file, effect_file,
    )

    checkpoint = effect_file.with_name("item-result-checkpoint.json")
    saved = json.loads(checkpoint.read_text(encoding="utf-8"))
    assert row["status"] == "failed"
    assert effect == 1 and readback == 0 and failed == 1
    assert step == "official_readback"
    assert saved["status"] == "delivery_unknown"
    assert saved["checkpoint"] == "effect_observed"
    assert saved["effect"] == 1
