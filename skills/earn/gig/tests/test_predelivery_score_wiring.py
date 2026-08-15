"""E1 gate wiring: the score check sits next to the judge at both delivery call sites,
and a confidently bad score stops the send exactly the way a judge refusal already does.

Fixture builders mirror ``test_formal_delivery_routes_judge_refusal.py`` exactly (same
queue/manifest shape, same argv), so this file only adds the score dimension on top of an
already-pinned contract rather than re-deriving one.
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

import coconala_formal_delivery_browser as formal_browser  # noqa: E402
import coconala_paid_progress_browser as progress_browser  # noqa: E402
import predelivery_score  # noqa: E402


class _TabReached(Exception):
    """Raised by the fake DefaultTab to prove control flow passed both delivery gates."""


class _FakeDefaultTab:
    def __init__(self, *_args, **_kwargs):
        pass

    def __enter__(self):
        raise _TabReached("both gates cleared: the browser would now open a real tab")

    def __exit__(self, *_exc):
        return False


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


def _formal_argv(queue_path: Path, manifest_path: Path, root: Path, tmp_path: Path) -> list[str]:
    return [
        "coconala_formal_delivery_browser.py",
        "--queue-item", str(queue_path),
        "--manifest", str(manifest_path),
        "--project-root", str(root),
        "--evidence-dir", str(tmp_path / "evidence"),
        "--ledger", str(root / "events.jsonl"),
        "--default-tab-helper", str(tmp_path / "cdp_default_tab.py"),
    ]


def test_formal_browser_blocks_before_send_on_a_low_score(tmp_path, monkeypatch):
    queue_path, manifest_path, root = _delivery_fixture(tmp_path)
    monkeypatch.setattr(formal_browser.artifact_judge, "refuse_unless_deliverable", lambda *_a, **_k: None)
    monkeypatch.setattr(
        formal_browser.predelivery_score, "score_predelivery",
        lambda *_a, **_k: (_ for _ in ()).throw(
            ValueError(f"{predelivery_score.ERROR_PREDELIVERY_SCORE_LOW}:too far off")
        ),
    )
    monkeypatch.setattr(formal_browser.collector, "DefaultTab", _FakeDefaultTab)
    monkeypatch.setattr(sys, "argv", _formal_argv(queue_path, manifest_path, root, tmp_path))

    # Not askable (no ERROR_NEEDS_BUYER_INPUT prefix), so route_judge_refusal re-raises --
    # same fail-closed shape a judge's about_the_deal/not_the_order refusal already has.
    with pytest.raises(ValueError, match=predelivery_score.ERROR_PREDELIVERY_SCORE_LOW):
        formal_browser.main()


def test_formal_browser_reaches_the_tab_after_a_score_that_clears(tmp_path, monkeypatch):
    queue_path, manifest_path, root = _delivery_fixture(tmp_path)
    monkeypatch.setattr(formal_browser.artifact_judge, "refuse_unless_deliverable", lambda *_a, **_k: None)
    calls = []
    monkeypatch.setattr(
        formal_browser.predelivery_score, "score_predelivery",
        lambda *a, **k: calls.append((a, k)) or {"score": 85, "dimensions": []},
    )
    monkeypatch.setattr(formal_browser.collector, "DefaultTab", _FakeDefaultTab)
    monkeypatch.setattr(sys, "argv", _formal_argv(queue_path, manifest_path, root, tmp_path))

    with pytest.raises(_TabReached):
        formal_browser.main()
    assert len(calls) == 1  # the score gate ran exactly once before the tab opened


def _progress_fixture(tmp_path: Path) -> tuple[Path, Path, Path]:
    """Same shape as CoconalaPaidProgressBrowserTest.setUp -- a valid progress delivery."""
    root = tmp_path / "project"
    for name in ("artifacts", "acceptance", "delivery"):
        (root / name).mkdir(parents=True, exist_ok=True)
    artifact = root / "artifacts" / "v3.zip"
    artifact.write_bytes(b"real-v3-artifact")
    acceptance = root / "acceptance" / "v3.json"
    acceptance.write_text('{"status":"PASS"}\n', encoding="utf-8")
    digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
    manifest = {
        "status": "ok",
        "project_root": str(root),
        "artifact_path": str(artifact),
        "artifact_version": "v3",
        "acceptance_evidence_path": str(acceptance),
        "acceptance_status": "PASS",
        "acceptance_delta": ["real regression suite passes"],
        "package_sha256": digest,
    }
    queue = {
        "talkroom_id": "4201",
        "marketplace_url": "https://coconala.com/talkrooms/4201",
        "delivery_action": "progress",
        "formal_delivery_checkbox": False,
        "progress_payload": {
            "mode": "progress",
            "formal_delivery_checkbox": False,
            "buyer_visible": True,
            "artifact_version": "v3",
            "acceptance_delta": ["real regression suite passes"],
            "blockers": ["buyer_agreement_not_observed"],
            "message": "お世話になっております。修正版 v3 をお送りします。",
        },
        "delivery_evidence": dict(manifest),
    }
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
    queue_path = tmp_path / "queue.json"
    queue_path.write_text(json.dumps(queue, ensure_ascii=False), encoding="utf-8")
    return queue_path, manifest_path, root


def _progress_argv(queue_path: Path, manifest_path: Path, tmp_path: Path) -> list[str]:
    return [
        "coconala_paid_progress_browser.py",
        "--queue-item", str(queue_path),
        "--manifest", str(manifest_path),
        "--evidence-dir", str(tmp_path / "evidence"),
        "--default-tab-helper", str(tmp_path / "cdp_default_tab.py"),
    ]


def test_progress_browser_blocks_before_send_on_a_low_score(tmp_path, monkeypatch):
    queue_path, manifest_path, _root = _progress_fixture(tmp_path)
    monkeypatch.setattr(progress_browser.artifact_judge, "refuse_unless_deliverable", lambda *_a, **_k: None)
    monkeypatch.setattr(
        progress_browser.predelivery_score, "score_predelivery",
        lambda *_a, **_k: (_ for _ in ()).throw(
            ValueError(f"{predelivery_score.ERROR_PREDELIVERY_SCORE_LOW}:too far off")
        ),
    )
    monkeypatch.setattr(progress_browser.collector, "DefaultTab", _FakeDefaultTab)
    monkeypatch.setattr(sys, "argv", _progress_argv(queue_path, manifest_path, tmp_path))

    # No try/except wraps this call site (unlike the formal browser) -- a refusal here has
    # always propagated uncaught, and the score gate must keep that shape exactly.
    with pytest.raises(ValueError, match=predelivery_score.ERROR_PREDELIVERY_SCORE_LOW):
        progress_browser._main()


def test_progress_browser_reaches_the_tab_after_a_score_that_clears(tmp_path, monkeypatch):
    queue_path, manifest_path, _root = _progress_fixture(tmp_path)
    monkeypatch.setattr(progress_browser.artifact_judge, "refuse_unless_deliverable", lambda *_a, **_k: None)
    calls = []
    monkeypatch.setattr(
        progress_browser.predelivery_score, "score_predelivery",
        lambda *a, **k: calls.append((a, k)) or {"score": 85, "dimensions": []},
    )
    monkeypatch.setattr(progress_browser.collector, "DefaultTab", _FakeDefaultTab)
    monkeypatch.setattr(sys, "argv", _progress_argv(queue_path, manifest_path, tmp_path))

    with pytest.raises(_TabReached):
        progress_browser._main()
    assert len(calls) == 1
