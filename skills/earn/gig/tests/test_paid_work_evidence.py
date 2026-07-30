import hashlib
import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path


SKILL = Path(__file__).resolve().parents[1]


def load(name):
    spec = importlib.util.spec_from_file_location(name, SKILL / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


paid_work_evidence = load("paid_work_evidence")
paid_queue_evidence = load("paid_queue_evidence")


class PaidEvidenceTest(unittest.TestCase):
    def test_paid_work_requires_project_bound_artifact_acceptance_hash_and_delta(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "projects" / "17943244"
            for name in ("requirements", "artifacts", "acceptance", "delivery"):
                (root / name).mkdir(parents=True)
            requirements = root / "requirements" / "latest-feedback.json"
            requirements.write_text('{"feedback":"fix"}\n')
            artifact = root / "artifacts" / "delivery-v3.zip"
            artifact.write_bytes(b"real v3")
            acceptance = root / "acceptance" / "v3.json"
            acceptance.write_text('{"status":"PASS","acceptance_delta":["fixed"]}\n')
            digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
            manifest = root / "delivery" / "paid-work-result.json"
            row = {
                "status": "ok", "project_root": str(root),
                "requirements_path": str(requirements), "artifact_path": str(artifact),
                "artifact_version": "v3", "acceptance_evidence_path": str(acceptance),
                "acceptance_status": "PASS", "acceptance_delta": ["fixed"],
                "package_sha256": digest,
            }
            (root / "state.json").write_text('{"current_version":"v2"}\n')
            manifest.write_text(json.dumps(row) + "\n")
            evidence = Path(temp) / "delivery-evidence" / "17943244.json"
            evidence.parent.mkdir()
            evidence.write_text(json.dumps(row) + "\n")
            ok, errors = paid_work_evidence.validate_paid_work(root, evidence)
            self.assertTrue(ok, errors)

    def test_paid_work_requires_current_feedback_suite_but_allows_repacked_artifact(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "projects" / "generic-contract"
            for name in ("requirements", "artifacts", "acceptance", "delivery"):
                (root / name).mkdir(parents=True)
            requirements = root / "requirements" / "latest-feedback.json"
            requirements.write_text('{"feedback":"fix"}\n')
            artifact = root / "artifacts" / "delivery-v3.zip"
            artifact.write_bytes(b"repacked artifact")
            acceptance = root / "acceptance" / "v3.json"
            acceptance.write_text('{"status":"PASS","acceptance_delta":["fixed"]}\n')
            digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
            row = {
                "status": "ok", "project_root": str(root),
                "requirements_path": str(requirements), "artifact_path": str(artifact),
                "artifact_version": "v3", "acceptance_evidence_path": str(acceptance),
                "acceptance_status": "PASS", "acceptance_delta": ["fixed"],
                "package_sha256": digest,
            }
            (root / "state.json").write_text('{"current_version":"v2"}\n')
            manifest = root / "delivery" / "paid-work-result.json"
            manifest.write_text(json.dumps(row) + "\n")
            evidence = Path(temp) / "delivery-evidence" / "generic-contract.json"
            evidence.parent.mkdir()
            evidence.write_text(json.dumps(row) + "\n")
            # A large artifact may be repacked in place and retain an old mtime;
            # the current feedback/acceptance/manifest/evidence records must not.
            for path in (requirements, acceptance, manifest, evidence):
                os.utime(path, (200, 200))
            os.utime(artifact, (1, 1))
            ok, errors = paid_work_evidence.validate_paid_work(root, evidence, min_mtime=100)
            self.assertTrue(ok, errors)

            os.utime(requirements, (1, 1))
            ok, errors = paid_work_evidence.validate_paid_work(root, evidence, min_mtime=100)
            self.assertFalse(ok)
            self.assertIn("requirements_stale", errors)
            os.utime(requirements, (200, 200))

            os.utime(acceptance, (1, 1))
            ok, errors = paid_work_evidence.validate_paid_work(root, evidence, min_mtime=100)
            self.assertFalse(ok)
            self.assertIn("acceptance_stale", errors)
            os.utime(acceptance, (200, 200))

            os.utime(manifest, (1, 1))
            ok, errors = paid_work_evidence.validate_paid_work(root, evidence, min_mtime=100)
            self.assertFalse(ok)
            self.assertIn("manifest_stale", errors)
            os.utime(manifest, (200, 200))

            os.utime(evidence, (1, 1))
            ok, errors = paid_work_evidence.validate_paid_work(root, evidence, min_mtime=100)
            self.assertFalse(ok)
            self.assertIn("delivery_evidence_stale", errors)

    def test_paid_work_rejects_text_only_or_downloads_result(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "projects" / "17943244"
            (root / "delivery").mkdir(parents=True)
            (root / "delivery" / "paid-work-result.json").write_text(json.dumps({"status": "ok"}))
            ok, errors = paid_work_evidence.validate_paid_work(root, Path(temp) / "evidence.json")
            self.assertFalse(ok)
            self.assertIn("artifact_path_outside_project_root", errors)
            self.assertIn("delivery_evidence_missing_or_empty", errors)

    def test_paid_work_rejects_acceptance_file_without_pass_delta(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "projects" / "1"
            for name in ("requirements", "artifacts", "acceptance", "delivery"):
                (root / name).mkdir(parents=True)
            req = root / "requirements" / "feedback.json"; req.write_text("feedback")
            artifact = root / "artifacts" / "delivery-v3.zip"; artifact.write_bytes(b"x")
            acceptance = root / "acceptance" / "v3.json"; acceptance.write_text('{"status":"FAIL","acceptance_delta":[]}\n')
            row = {"status":"ok","project_root":str(root),"requirements_path":str(req),"artifact_path":str(artifact),
                   "artifact_version":"v3","acceptance_evidence_path":str(acceptance),"acceptance_status":"PASS",
                   "acceptance_delta":["claimed"],"package_sha256":hashlib.sha256(b"x").hexdigest()}
            (root / "delivery" / "paid-work-result.json").write_text(json.dumps(row))
            evidence = Path(temp) / "evidence.json"; evidence.write_text(json.dumps(row))
            ok, errors = paid_work_evidence.validate_paid_work(root, evidence)
            self.assertFalse(ok)
            self.assertIn("acceptance_evidence_status_not_pass", errors)
            self.assertIn("acceptance_evidence_delta_empty", errors)

    def test_paid_work_rejects_same_version_as_project_state(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "projects" / "1"
            for name in ("requirements", "artifacts", "acceptance", "delivery"):
                (root / name).mkdir(parents=True)
            (root / "state.json").write_text('{"current_version":"v3"}\n')
            req = root / "requirements" / "feedback.json"; req.write_text("feedback")
            artifact = root / "artifacts" / "delivery-v3.zip"; artifact.write_bytes(b"x")
            acceptance = root / "acceptance" / "v3.json"; acceptance.write_text('{"status":"PASS","acceptance_delta":["claimed"]}\n')
            row = {"status":"ok","project_root":str(root),"requirements_path":str(req),"artifact_path":str(artifact),
                   "artifact_version":"v3","acceptance_evidence_path":str(acceptance),"acceptance_status":"PASS",
                   "acceptance_delta":["claimed"],"package_sha256":hashlib.sha256(b"x").hexdigest()}
            (root / "delivery" / "paid-work-result.json").write_text(json.dumps(row))
            evidence = Path(temp) / "evidence.json"; evidence.write_text(json.dumps(row))
            ok, errors = paid_work_evidence.validate_paid_work(root, evidence)
            self.assertFalse(ok)
            self.assertIn("artifact_version_not_newer_than_project_state", errors)

    def test_paid_queue_requires_fresh_browser_evidence_not_text(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "paid-queue-evidence.json").write_text(json.dumps({"sent": True}))
            ok, errors = paid_queue_evidence.validate_paid_queue(root)
            self.assertFalse(ok)
            self.assertIn("screenshot_outside_evidence_dir", errors)
            self.assertIn("post_send_live_dom_url_missing", errors)

    def test_paid_queue_binds_fresh_dom_attachment_to_artifact_and_talkroom(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            screenshot = root / "post.png"; screenshot.write_bytes(b"png")
            live = root / "post.json"
            digest = "a" * 64
            live.write_text(json.dumps({
                "url": "https://coconala.com/talkrooms/17943244", "sent": True,
                "formal_delivery_checkbox": False,
                "latest_seller_attachment": {
                    "filename": "delivery-v3.zip", "size_bytes": 42,
                    "message": f"v3 hash={digest}",
                },
            }) + "\n")
            (root / "paid-queue-evidence.json").write_text(json.dumps({
                "sent": True, "formal_delivery_checkbox": False,
                "captured_at": "2026-07-22T08:00:00Z", "talkroom_id": "17943244",
                "artifact_basename": "delivery-v3.zip", "artifact_version": "v3",
                "package_sha256": digest, "acceptance_delta": ["fixed"],
                "screenshot_path": str(screenshot), "live_dom_path": str(live),
            }) + "\n")
            ok, errors = paid_queue_evidence.validate_paid_queue(root, {"talkroom_id": "17943244"})
            self.assertTrue(ok, errors)

    def test_paid_queue_rejects_sent_false_progress_evidence(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            screenshot = root / "post.png"; screenshot.write_bytes(b"png")
            live = root / "post.json"
            digest = "a" * 64
            live.write_text(json.dumps({
                "url": "https://coconala.com/talkrooms/1", "sent": False,
                "formal_delivery_checkbox": False,
                "latest_seller_attachment": {
                    "filename": "delivery-v3.zip", "size_bytes": 1,
                    "message": f"v3 {digest}",
                },
            }) + "\n")
            (root / "paid-queue-evidence.json").write_text(json.dumps({
                "sent": False, "formal_delivery_checkbox": False,
                "captured_at": "now", "talkroom_id": "1",
                "artifact_basename": "delivery-v3.zip", "artifact_version": "v3",
                "package_sha256": digest, "acceptance_delta": ["fixed"],
                "screenshot_path": str(screenshot), "live_dom_path": str(live),
            }) + "\n")
            ok, errors = paid_queue_evidence.validate_paid_queue(
                root, {"delivery_action": "progress", "talkroom_id": "1"}
            )
            self.assertFalse(ok)
            self.assertIn("paid_queue_send_not_observed", errors)
            self.assertIn("post_send_live_dom_send_not_observed", errors)

    def test_paid_queue_accepts_legacy_talkroom_url_for_browser_free_recovery(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            screenshot = root / "post.png"; screenshot.write_bytes(b"png")
            live = root / "post.json"
            digest = "a" * 64
            live.write_text(json.dumps({
                "talkroom_url": "https://coconala.com/talkrooms/18011694", "sent": True,
                "formal_delivery_checkbox": False,
                "latest_seller_attachment": {
                    "filename": "v3.zip", "size_bytes": 42,
                    "message": f"v3 {digest}",
                },
            }) + "\n")
            (root / "paid-queue-evidence.json").write_text(json.dumps({
                "sent": True, "formal_delivery_checkbox": False,
                "captured_at": "2026-07-22T09:01:07Z", "talkroom_id": "18011694",
                "artifact_basename": "v3.zip", "artifact_version": "v3",
                "package_sha256": digest, "acceptance_delta": ["fixed"],
                "screenshot_path": str(screenshot), "live_dom_path": str(live),
            }) + "\n")
            ok, errors = paid_queue_evidence.validate_paid_queue(
                root, {"talkroom_id": "18011694", "marketplace_url": "https://coconala.com/talkrooms/18011694"}
            )
            self.assertTrue(ok, errors)
            live.write_text(json.dumps({
                "url": "https://coconala.com/talkrooms/18011694",
                "talkroom_url": "https://coconala.com/talkrooms/other",
                "sent": True, "formal_delivery_checkbox": False,
                "latest_seller_attachment": {
                    "filename": "v3.zip", "size_bytes": 42, "message": f"v3 {digest}",
                },
            }) + "\n")
            ok, errors = paid_queue_evidence.validate_paid_queue(
                root, {"talkroom_id": "18011694", "marketplace_url": "https://coconala.com/talkrooms/18011694"}
            )
            self.assertFalse(ok)
            self.assertIn("post_send_url_fields_conflict", errors)

    def test_paid_queue_rejects_attachment_not_bound_to_expected_manifest(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            screenshot = root / "post.png"; screenshot.write_bytes(b"png")
            live = root / "post.json"
            expected_hash = "a" * 64
            live.write_text(json.dumps({
                "url": "https://coconala.com/talkrooms/17943244", "sent": True,
                "latest_seller_attachment": {"filename": "wrong.zip", "size_bytes": 1, "message": f"v3 {expected_hash}"},
            }) + "\n")
            (root / "paid-queue-evidence.json").write_text(json.dumps({
                "sent": True, "formal_delivery_checkbox": False, "captured_at": "now",
                "talkroom_id": "17943244", "artifact_basename": "wrong.zip", "artifact_version": "v3",
                "package_sha256": expected_hash, "acceptance_delta": ["fixed"],
                "screenshot_path": str(screenshot), "live_dom_path": str(live),
            }) + "\n")
            expected = {"talkroom_id": "17943244", "delivery_evidence": {
                "artifact_path": "/project/delivery-v3.zip", "artifact_version": "v3",
                "package_sha256": "b" * 64, "acceptance_delta": ["fixed"],
            }}
            ok, errors = paid_queue_evidence.validate_paid_queue(root, expected)
            self.assertFalse(ok)
            self.assertIn("sent_artifact_not_bound_to_queue_manifest", errors)
            self.assertIn("sent_hash_not_bound_to_queue_manifest", errors)

    def test_paid_queue_allows_none_action_as_observe_only(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            screenshot = root / "observed.png"; screenshot.write_bytes(b"png")
            live = root / "observed.json"
            live.write_text(json.dumps({"url": "https://coconala.com/talkrooms/17943244",
                                        "formal_delivery_checkbox": False}) + "\n")
            (root / "paid-queue-evidence.json").write_text(json.dumps({
                "observed": True, "sent": False, "formal_delivery_checkbox": False,
                "captured_at": "now", "talkroom_id": "17943244",
                "screenshot_path": str(screenshot), "live_dom_path": str(live),
            }) + "\n")
            ok, errors = paid_queue_evidence.validate_paid_queue(root, {
                "delivery_action": "none", "talkroom_id": "17943244",
            })
            self.assertTrue(ok, errors)

    def test_paid_queue_rejects_stale_post_send_manifest(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            screenshot = root / "post.png"; screenshot.write_bytes(b"png")
            live = root / "post.json"; live.write_text(json.dumps({"url": "https://coconala.com/talkrooms/1", "sent": True}) + "\n")
            manifest = root / "paid-queue-evidence.json"
            manifest.write_text(json.dumps({"sent": True, "formal_delivery_checkbox": False, "captured_at": "now", "talkroom_id": "1", "artifact_version": "v3", "package_sha256": "a" * 64, "acceptance_delta": ["x"], "screenshot_path": str(screenshot), "live_dom_path": str(live)}) + "\n")
            old = 1.0
            for path in (manifest, screenshot, live):
                os.utime(path, (old, old))
            ok, errors = paid_queue_evidence.validate_paid_queue(root, {"talkroom_id": "1"}, min_mtime=2.0)
            self.assertFalse(ok)
            self.assertIn("paid_queue_manifest_stale", errors)
            self.assertIn("screenshot_stale", errors)
            self.assertIn("live_dom_stale", errors)

    def test_paid_queue_accepts_runs17_manifest_when_live_dom_proves_checkbox_off(self):
        """A missing duplicate outer field is recoverable from authoritative live DOM."""
        with tempfile.TemporaryDirectory() as temp:
            source = Path("__HOME__/gig/evidence/gig-pass-1784705225-67113/agent-PAID_QUEUE_DELIVERY")
            if not (source / "paid-queue-evidence.json").is_file():
                self.skipTest("runs17 evidence is not available on this host")
            root = Path(temp) / "agent-PAID_QUEUE_DELIVERY"
            root.mkdir()
            manifest = json.loads((source / "paid-queue-evidence.json").read_text())
            live = json.loads((source / "live-dom-17943244.json").read_text())
            artifact = Path("__HOME__/gig/projects/17943244/artifacts/v3.zip")
            manifest["screenshot_path"] = str(root / "post.png")
            manifest["live_dom_path"] = str(root / "post.json")
            (root / "post.png").write_bytes(b"png")
            (root / "post.json").write_text(json.dumps(live) + "\n")
            (root / "paid-queue-evidence.json").write_text(json.dumps(manifest) + "\n")
            expected = json.loads(Path("__HOME__/gig/evidence/gig-pass-1784705225-67113/paid-queue-expected.json").read_text())
            expected["delivery_evidence"]["artifact_path"] = str(artifact)
            ok, errors = paid_queue_evidence.validate_paid_queue(root, expected)
            self.assertTrue(ok, errors)

    def test_paid_queue_rejects_live_dom_checkbox_on_or_missing(self):
        for live_value, expected_error in ((True, "formal_delivery_checkbox_on"), (None, "formal_delivery_checkbox_missing")):
            with self.subTest(live_value=live_value), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                (root / "post.png").write_bytes(b"png")
                live = {"url": "https://coconala.com/talkrooms/17943244", "sent": True}
                if live_value is not None:
                    live["formal_delivery_checkbox"] = live_value
                (root / "post.json").write_text(json.dumps(live) + "\n")
                (root / "paid-queue-evidence.json").write_text(json.dumps({
                    "sent": True, "captured_at": "now", "talkroom_id": "17943244",
                    "artifact_basename": "delivery-v3.zip", "artifact_version": "v3",
                    "package_sha256": "a" * 64, "acceptance_delta": ["fixed"],
                    "screenshot_path": str(root / "post.png"), "live_dom_path": str(root / "post.json"),
                }) + "\n")
                ok, errors = paid_queue_evidence.validate_paid_queue(root, {"talkroom_id": "17943244"})
                self.assertFalse(ok)
                self.assertIn(expected_error, errors)


if __name__ == "__main__":
    unittest.main()
