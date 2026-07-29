import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


SKILL = Path(__file__).resolve().parents[1]


def load(name):
    spec = importlib.util.spec_from_file_location(name, SKILL / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ledger = load("project_ledger")
reconcile = load("reconcile_paid_delivery")


class PaidDeliveryReconcileTest(unittest.TestCase):
    def test_green_answer_evidence_reconciles_feedback_without_artifact_fields(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "projects" / "generic-contract"
            ledger.init_project(root.parent, root.name, "generic", {
                "current_version": "v2", "buyer_visible": True,
            })
            evidence = Path(temp) / "pass" / "agent-PAID_QUEUE_DELIVERY"
            evidence.mkdir(parents=True)
            screenshot = evidence / "post.png"
            screenshot.write_bytes(b"png")
            message = "確認事項へ回答しました。"
            message_hash = hashlib.sha256(message.encode()).hexdigest()
            live = evidence / "post.json"
            live.write_text(json.dumps({
                "url": "https://example.test/talkrooms/generic",
                "sent": True,
                "mode": "answer",
                "formal_delivery_control_checked": False,
                "latest_seller_message": message,
            }) + "\n")
            (evidence / "paid-queue-evidence.json").write_text(json.dumps({
                "sent": True,
                "mode": "answer",
                "send_performed": True,
                "captured_at": "now",
                "talkroom_id": "generic",
                "message_sha256": message_hash,
                "screenshot_path": str(screenshot),
                "live_dom_path": str(live),
            }) + "\n")
            answer = evidence.parent / "paid-answer.json"
            answer.write_text(json.dumps({
                "version": 1, "status": "answer", "message": message,
            }) + "\n")
            expected = Path(temp) / "expected.json"
            expected.write_text(json.dumps({
                "talkroom_id": "generic",
                "marketplace_url": "https://example.test/talkrooms/generic",
                "buyer_feedback_sha256": "b" * 64,
                "delivery_evidence": {"project_root": str(root)},
            }) + "\n")

            first = reconcile.reconcile_answer(root, evidence, expected, answer)
            second = reconcile.reconcile_answer(root, evidence, expected, answer)

            self.assertTrue(first["buyer_visible_response"])
            self.assertTrue(first["send_performed"])
            self.assertEqual(first["handled_buyer_feedback_sha256"], "b" * 64)
            self.assertEqual(first["material_event_outcome"], "buyer_answer_sent")
            self.assertEqual(first["last_buyer_answer_sha256"], message_hash)
            self.assertTrue(first["reconciled"])
            self.assertFalse(second["reconciled"])
            self.assertEqual(first["current_version"], "v2")

    def test_answer_hash_mismatch_does_not_mutate_project_state(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "projects" / "generic-contract"
            ledger.init_project(root.parent, root.name, "generic", {"current_version": "v2"})
            before = (root / "state.json").read_bytes()
            evidence = Path(temp) / "pass" / "agent-PAID_QUEUE_DELIVERY"
            evidence.mkdir(parents=True)
            screenshot = evidence / "post.png"
            screenshot.write_bytes(b"png")
            live = evidence / "post.json"
            live.write_text(json.dumps({
                "url": "https://example.test/talkrooms/generic",
                "sent": True, "mode": "answer",
                "formal_delivery_control_checked": False,
                "latest_seller_message": "different",
            }) + "\n")
            (evidence / "paid-queue-evidence.json").write_text(json.dumps({
                "sent": True, "mode": "answer", "captured_at": "now",
                "talkroom_id": "generic", "message_sha256": "a" * 64,
                "screenshot_path": str(screenshot), "live_dom_path": str(live),
            }) + "\n")
            answer = evidence.parent / "paid-answer.json"
            answer.write_text(json.dumps({
                "version": 1, "status": "answer", "message": "answer",
            }) + "\n")
            expected = Path(temp) / "expected.json"
            expected.write_text(json.dumps({
                "talkroom_id": "generic",
                "marketplace_url": "https://example.test/talkrooms/generic",
                "buyer_feedback_sha256": "b" * 64,
                "delivery_evidence": {"project_root": str(root)},
            }) + "\n")

            with self.assertRaises(reconcile.ReconcileError):
                reconcile.reconcile_answer(root, evidence, expected, answer)
            self.assertEqual((root / "state.json").read_bytes(), before)

    def test_mark_ready_for_browser_persists_bound_artifact_after_prior_visible_version(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "projects" / "generic-contract"
            ledger.init_project(root.parent, root.name, "generic", {
                "current_version": "v1", "buyer_visible": True,
                "latest_buyer_visible_version": "v1",
            })
            artifact = root / "artifacts" / "v3.zip"
            artifact.write_bytes(b"v3")
            req = root / "requirements" / "latest-feedback.json"
            req.write_text('{"feedback":"fixed"}\n')
            acceptance = root / "acceptance" / "v3.json"
            acceptance.write_text('{"status":"PASS","acceptance_delta":["fixed"]}\n')
            digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
            row = {
                "status": "ok", "project_root": str(root),
                "requirements_path": str(req), "artifact_path": str(artifact),
                "artifact_version": "v3", "acceptance_evidence_path": str(acceptance),
                "acceptance_status": "PASS", "acceptance_delta": ["fixed"],
                "package_sha256": digest,
            }
            manifest = root / "delivery" / "paid-work-result.json"
            manifest.write_text(json.dumps(row) + "\n")
            delivery_evidence = Path(temp) / "delivery-evidence.json"
            delivery_evidence.write_text(json.dumps(row) + "\n")
            first = reconcile.mark_ready_for_browser(root, delivery_evidence)
            self.assertTrue(first["reconciled"])
            self.assertFalse(first["buyer_visible"])
            self.assertTrue(first["artifact_ready_pending_browser"])
            self.assertEqual(first["next_action"], "retry_buyer_visible_delivery")
            self.assertEqual(first["current_delivery_evidence_path"], str(delivery_evidence.resolve()))
            self.assertGreater(first["current_delivery_evidence_mtime"], 0)
            events = root / "events.jsonl"
            count_after_first = len(events.read_text().splitlines())
            second = reconcile.mark_ready_for_browser(root, delivery_evidence)
            self.assertFalse(second["reconciled"])
            self.assertFalse(second["resend"])
            self.assertEqual(len(events.read_text().splitlines()), count_after_first)

    def test_green_evidence_reconciles_once_without_resend(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "projects" / "generic-contract"
            ledger.init_project(root.parent, root.name, "generic", {"current_version": "v2"})
            artifact = root / "artifacts" / "v3.zip"
            artifact.write_bytes(b"v3")
            evidence = Path(temp) / "evidence"
            evidence.mkdir()
            screenshot = evidence / "post.png"; screenshot.write_bytes(b"png")
            digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
            live = evidence / "post.json"
            live.write_text(json.dumps({
                "talkroom_url": "https://example.test/talkrooms/generic", "sent": True,
                "formal_delivery_checkbox": False,
                "latest_seller_attachment": {"filename": artifact.name, "size_bytes": artifact.stat().st_size,
                                             "message": f"v3 {digest}"},
            }) + "\n")
            (evidence / "paid-queue-evidence.json").write_text(json.dumps({
                "sent": True, "send_performed": True, "captured_at": "now", "talkroom_id": "generic",
                "artifact_basename": artifact.name, "artifact_version": "v3", "package_sha256": digest,
                "acceptance_delta": ["fixed"], "screenshot_path": str(screenshot), "live_dom_path": str(live),
            }) + "\n")
            expected = Path(temp) / "expected.json"
            expected.write_text(json.dumps({"talkroom_id": "generic", "marketplace_url": "https://example.test/talkrooms/generic",
                                             "delivery_evidence": {"project_root": str(root), "artifact_path": str(artifact),
                                                                      "artifact_version": "v3", "package_sha256": digest,
                                                                      "acceptance_delta": ["fixed"]}}) + "\n")
            first = reconcile.reconcile(root, evidence, expected)
            self.assertEqual(first["current_version"], "v3")
            self.assertTrue(first["buyer_visible"])
            self.assertFalse(first["artifact_ready_pending_browser"])
            self.assertEqual(first["next_action"], "await_buyer_feedback")
            self.assertTrue(first["send_performed"])
            events = root / "events.jsonl"
            count_after_first = len(events.read_text().splitlines())
            second = reconcile.reconcile(root, evidence, expected)
            for key in ("current_version", "current_artifact_path", "current_package_sha256", "buyer_visible", "next_action"):
                self.assertEqual(second[key], first[key])
            self.assertTrue(first["reconciled"])
            self.assertFalse(second["reconciled"])
            self.assertTrue(second["send_performed"])
            self.assertEqual(len(events.read_text().splitlines()), count_after_first)

    def test_invalid_evidence_does_not_mutate_state(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "projects" / "generic-contract"
            ledger.init_project(root.parent, root.name, "generic", {"current_version": "v2"})
            evidence = Path(temp) / "evidence"; evidence.mkdir()
            (evidence / "paid-queue-evidence.json").write_text(json.dumps({"sent": True}) + "\n")
            expected = Path(temp) / "expected.json"
            expected.write_text(json.dumps({"talkroom_id": "generic", "delivery_evidence": {
                "project_root": str(root), "artifact_path": str(root / "artifacts" / "v3.zip"),
                "artifact_version": "v3", "package_sha256": "a" * 64, "acceptance_delta": ["fixed"]}}) + "\n")
            with self.assertRaises(reconcile.ReconcileError):
                reconcile.reconcile(root, evidence, expected)
            self.assertEqual(json.loads((root / "state.json").read_text())["current_version"], "v2")


if __name__ == "__main__":
    unittest.main()
