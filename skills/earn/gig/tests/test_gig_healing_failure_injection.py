from __future__ import annotations

import importlib.util
import tempfile
from types import SimpleNamespace
from pathlib import Path


GIG_ROOT = Path(__file__).resolve().parents[1]
CONTROLLER = GIG_ROOT / "src/gig/healing/controller.py"
QUEUE = GIG_ROOT / "scripts/repair_queue.py"
HEALER = GIG_ROOT / "scripts/gig_healer.py"


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_known_failure_classes_need_fresh_clearance_after_dispatch():
    controller = load("failure_injection_controller", CONTROLLER)
    queue_module = load("failure_injection_queue", QUEUE)
    healer = load("failure_injection_healer", HEALER)
    repair_classes = (
        "scheduler_restart",
        "lane_probe",
        "browser_restart",
        "disk_recover",
        "sandbox_recover",
        "application_expand",
        "telegram_reconcile",
        "telegram_probe",
    )
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        for index, repair_class in enumerate(repair_classes):
            queue = queue_module.RepairQueue(root / f"{index}.sqlite3")
            fingerprint = f"injected:{repair_class}"
            queue.enqueue(
                fingerprint=fingerprint,
                repair_class=repair_class,
                evidence={"injected": True},
                detected_at=100,
            )
            observations = iter([
                [{"fingerprint": fingerprint}],
                [],
            ])
            result = controller.reconcile_once(
                queue=queue,
                owner=f"injector-{index}",
                uid=501,
                now=120,
                audit_path=root / f"{index}.audit.jsonl",
                observe_incidents=lambda: next(observations),
                dispatcher=lambda selected, uid: {
                    "status": "dispatched",
                    "repair_class": selected,
                    "command": healer.repair_command(selected, uid=uid),
                },
            )
            assert result["status"] == "recovered", repair_class
            assert result["repair_dispatched"] is True
            assert queue.list_incidents()[0]["state"] == "recovered"


def test_diagnostic_failures_never_become_customer_retries():
    controller = load("diagnostic_injection_controller", CONTROLLER)
    queue_module = load("diagnostic_injection_queue", QUEUE)
    healer = load("diagnostic_injection_healer", HEALER)
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        for index, repair_class in enumerate(
            ("schema_diagnose", "provider_diagnose", "task_diagnose")
        ):
            queue = queue_module.RepairQueue(root / f"diagnostic-{index}.sqlite3")
            fingerprint = f"injected:{repair_class}"
            queue.enqueue(
                fingerprint=fingerprint,
                repair_class=repair_class,
                evidence={
                    "diagnosis_class": "provider_timeout",
                    "diagnosis_evidence": {"attempt_executable": "/bin/sh"},
                },
                detected_at=100,
            )
            result = controller.reconcile_once(
                queue=queue,
                owner=f"diagnostic-{index}",
                uid=501,
                now=120,
                audit_path=root / f"diagnostic-{index}.audit.jsonl",
                observe_incidents=lambda: [{"fingerprint": fingerprint}],
                dispatcher=lambda selected, uid, incident: healer.dispatch(
                    selected,
                    uid=uid,
                    incident=incident,
                    runner=lambda *args, **kwargs: SimpleNamespace(
                        returncode=0,
                        stdout="self-fix spawned",
                        stderr="",
                    ),
                ),
            )
            assert result["status"] == "diagnosed_blocked", repair_class
            assert result["repair_dispatched"] is False
            assert queue.list_incidents()[0]["state"] == "blocked"
