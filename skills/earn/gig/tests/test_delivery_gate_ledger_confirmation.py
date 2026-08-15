from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path


# Talkroom 90000004's delivery was completed and verified on the site at 2026-08-06 05:33
# (FORMAL_DELIVERY_CONFIRMED in the project ledger, artifact readback, dedupe on the second
# attempt), and every pass afterwards still failed with blockers=formal_delivery_not_confirmed:
# delivery_gate confirms a delivery only through the live talkroom's 納品確認待ち step, which a
# 定期購入 room never shows. The loop kept re-queuing a finished job and reporting the pass
# failed, hourly, over work it had already done.
#
# The project ledger row is the durable fact -- and it is only trusted when its
# artifact_sha256 equals the package the queue is currently trying to deliver, so a NEW
# version of the same project still queues for delivery.

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))


def load_module():
    spec = importlib.util.spec_from_file_location(
        "delivery_queue_ledger", SCRIPTS / "delivery_queue.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def fixture(tmp_path: Path):
    module = load_module()
    evidence_root = tmp_path / "evidence"
    evidence_root.mkdir()
    projects_root = tmp_path / "projects"
    project = projects_root / "90000004"
    project.mkdir(parents=True)
    artifact = project / "catalog-v12.html"
    artifact.write_bytes(b"deliverable bytes")
    digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
    acceptance = project / "acceptance.json"
    acceptance.write_text(json.dumps({"status": "PASS"}), encoding="utf-8")
    item = {
        "talkroom_id": "90000004",
        "contract_id": "talkroom:90000004",
        "talkroom_state": "unknown",  # measured: a subscription room has no step bar
        "snapshot_captured_at": "2026-08-06T07:00:00Z",
    }
    evidence = {
        "artifact_path": str(artifact),
        "artifact_version": "v12",
        "acceptance_evidence_path": str(acceptance),
        "acceptance_status": "PASS",
        "acceptance_delta": ["直した"],
        "package_sha256": digest,
    }
    module_path = module.evidence_path(evidence_root, item)
    module_path.write_text(json.dumps(evidence), encoding="utf-8")
    return module, item, evidence_root, projects_root, project, digest


def ledger_row(project: Path, sha: str) -> None:
    (project / "events.jsonl").write_text(
        json.dumps({
            "event": "FORMAL_DELIVERY_CONFIRMED",
            "event_key": f"coconala:formal:90000004:{sha}",
            "artifact_sha256": sha,
            "talkroom_id": "90000004",
        }) + "\n",
        encoding="utf-8",
    )


def test_a_ledger_confirmed_delivery_is_not_requeued(tmp_path) -> None:
    module, item, evidence_root, projects_root, project, digest = fixture(tmp_path)
    ledger_row(project, digest)
    _, blockers = module.delivery_gate(item, evidence_root, projects_root=projects_root)
    assert "formal_delivery_not_confirmed" not in blockers
    assert blockers == []


def test_a_new_artifact_version_still_queues(tmp_path) -> None:
    # The ledger says v11 went out; the queue is now holding v12. That is NEW work.
    module, item, evidence_root, projects_root, project, digest = fixture(tmp_path)
    ledger_row(project, "f" * 64)
    _, blockers = module.delivery_gate(item, evidence_root, projects_root=projects_root)
    assert "formal_delivery_not_confirmed" in blockers


def test_no_ledger_still_blocks(tmp_path) -> None:
    module, item, evidence_root, projects_root, project, digest = fixture(tmp_path)
    _, blockers = module.delivery_gate(item, evidence_root, projects_root=projects_root)
    assert "formal_delivery_not_confirmed" in blockers


def test_a_corrupt_ledger_line_never_confirms_and_never_crashes(tmp_path) -> None:
    module, item, evidence_root, projects_root, project, digest = fixture(tmp_path)
    (project / "events.jsonl").write_text("not json\n", encoding="utf-8")
    _, blockers = module.delivery_gate(item, evidence_root, projects_root=projects_root)
    assert "formal_delivery_not_confirmed" in blockers
