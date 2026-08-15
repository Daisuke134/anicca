import hashlib
import importlib.util
import json
import sys
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
SPEC = importlib.util.spec_from_file_location("paid_direct_review_inputs", SCRIPTS / "paid_direct.py")
paid_direct = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(paid_direct)


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False) + "\n", encoding="utf-8")


def test_operator_policy_is_bound_to_exact_paid_cycle(tmp_path):
    root = tmp_path / "18130722"
    policy = root / "context" / paid_direct.PAID_FILE_OPERATOR_POLICY
    value = {
        "version": 1,
        "authorized_by": "account_owner",
        "request_id": root.name,
        "buyer_feedback_sha256": "a" * 64,
        "requirements_sha256": "b" * 64,
        "directives": ["Use the available OSS renderer and make no proprietary-editor claim."],
    }
    write_json(policy, value)

    path, loaded, digest = paid_direct._file_operator_policy(root, "a" * 64, "b" * 64)
    assert path == policy
    assert loaded == value
    assert digest == hashlib.sha256(policy.read_bytes()).hexdigest()

    assert paid_direct._file_operator_policy(root, "c" * 64, "b" * 64) == (None, {}, "")


def test_video_review_receipt_supplies_real_and_cited_images(tmp_path):
    root = tmp_path / "18130722"
    frames = root / "work" / "render" / "review-frames"
    frames.mkdir(parents=True)
    for number in range(1, 70):
        (frames / f"frame-{number:04d}.jpg").write_bytes(f"frame-{number}".encode())
    artifact_sha = "d" * 64
    write_json(root / "work" / "render" / "receipt.json", {
        "output": {"sha256": artifact_sha},
        "qc": {"output": {"review_frames": {"path": str(frames), "count": 69}}},
    })

    selected = paid_direct._file_review_images(
        root, artifact_sha, "defects in review frames 0008, 0040, and 0060", limit=12,
    )
    assert len(selected) == 12
    assert selected[:3] == [
        frames / "frame-0008.jpg", frames / "frame-0040.jpg", frames / "frame-0060.jpg",
    ]
    assert selected[-1] == frames / "frame-0069.jpg"
    assert paid_direct._file_review_images(root, "e" * 64) == []


def test_pdf_review_renders_and_binds_every_candidate_page(tmp_path):
    from PIL import Image

    root = tmp_path / "18138707"
    artifact = root / "delivery" / "candidate.pdf"
    artifact.parent.mkdir(parents=True)
    images = [Image.new("RGB", (20, 30), color) for color in ("white", "black")]
    images[0].save(artifact, "PDF", save_all=True, append_images=images[1:])
    artifact_sha = hashlib.sha256(artifact.read_bytes()).hexdigest()
    write_json(root / "delivery" / "paid-work-result.json", {
        "artifact_path": str(artifact),
        "package_sha256": artifact_sha,
    })

    selected = paid_direct._file_review_images(root, artifact_sha)

    assert len(selected) == 2
    review = json.loads((selected[0].parent / "review-manifest.json").read_text())
    assert review["artifact_path"] == str(artifact)
    assert review["artifact_sha256"] == artifact_sha
    assert [row["page"] for row in review["pages"]] == [1, 2]
    assert [row["sha256"] for row in review["pages"]] == [
        hashlib.sha256(path.read_bytes()).hexdigest() for path in selected
    ]


def test_visual_references_are_read_from_bound_acceptance_evidence(tmp_path):
    root = tmp_path / "18130722"
    reference = root / "work" / "analysis" / "reference-sheet.jpg"
    reference.parent.mkdir(parents=True)
    reference.write_bytes(b"reference")
    acceptance = root / "acceptance" / "candidate.json"
    write_json(acceptance, {
        "checks": [{"reference_sheet_paths": [str(reference)]}],
    })

    selected = paid_direct._file_reference_images(
        root, {"acceptance_evidence_path": str(acceptance)},
    )
    assert selected == [reference]


def test_only_concrete_revision_verdict_reenters_builder():
    assert paid_direct._file_review_disposition("deliverable") == "approve"
    assert paid_direct._file_review_disposition("needs_revision") == "repair"
    for verdict in ("undeterminable", "needs_buyer_input", "not_the_order", "about_the_deal"):
        assert paid_direct._file_review_disposition(verdict) == "block"

    schema = json.loads((SCRIPTS.parent / "schemas" / "paid_file_judgement.schema.json").read_text())
    assert "needs_revision" in schema["properties"]["verdict"]["enum"]


def test_changed_buyer_context_rechecks_exact_review_blocked_artifact_before_rebuild(tmp_path):
    root = tmp_path / "project"
    artifact = root / "delivery" / "delivery-v1.md"
    artifact.parent.mkdir(parents=True)
    artifact.write_text("verified candidate", encoding="utf-8")
    acceptance = root / "acceptance" / "delivery-v1.json"
    write_json(acceptance, {"status": "PASS", "acceptance_delta": ["candidate prepared"]})
    requirements = root / "requirements" / "live-buyer-reply.json"
    write_json(requirements, {"feedback_sha256": "b" * 64})
    artifact_sha256 = hashlib.sha256(artifact.read_bytes()).hexdigest()
    write_json(root / "delivery" / "paid-work-result.json", {
        "status": "ok",
        "project_root": str(root),
        "requirements_path": str(requirements),
        "artifact_path": str(artifact),
        "artifact_version": "v1",
        "acceptance_evidence_path": str(acceptance),
        "acceptance_status": "PASS",
        "acceptance_delta": ["candidate prepared"],
        "package_sha256": artifact_sha256,
    })
    blocked = {
        "state": "REVIEW_BLOCKED",
        "mode": "file",
        "artifact_sha256": artifact_sha256,
        "buyer_feedback_sha256": "a" * 64,
        "finding": "proof was missing",
    }

    resumed = paid_direct._blocked_file_bundle_for_recheck(root, blocked)

    assert resumed is not None
    assert resumed[0]["artifact_path"] == str(artifact)
    assert paid_direct._blocked_file_bundle_for_recheck(
        root, {**blocked, "artifact_sha256": "c" * 64},
    ) is None


def test_paid_file_progress_message_does_not_expose_internal_acceptance_details():
    payload = paid_direct._file_progress_payload({
        "artifact_version": "v19",
        "acceptance_delta": ["internal SHA-256 and renderer provenance"],
        "blockers": ["buyer_explicit_formal_delivery_hold"],
        "buyer_feedback_stage": "revision",
    })
    assert payload["acceptance_delta"] == ["internal SHA-256 and renderer provenance"]
    assert payload["message"] == "お世話になっております。修正版をお送りします。ご確認をお願いいたします。"
    assert "SHA" not in payload["message"]
