import json
import hashlib
import importlib.util
import subprocess
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path


SKILL = Path(__file__).resolve().parents[1]
QUEUE = SKILL / "scripts" / "delivery_queue.py"
FIXTURE = Path(__file__).resolve().parent / "fixtures" / "live_queue.json"

SPEC = importlib.util.spec_from_file_location("delivery_queue", QUEUE)
delivery_queue = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(delivery_queue)


class DeliveryQueueTest(unittest.TestCase):
    def test_production_queue_accepts_authenticated_hidden_dom_snapshot(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            snapshot = root / "snapshot.json"
            output = root / "queue.json"
            snapshot.write_text(json.dumps({
                "source": "authenticated_coconala_hidden_default_context_dom",
                "read_only": True,
                "captured_at": datetime.now(timezone.utc).isoformat(),
                "orders": [],
                "quotes": [],
            }))
            proc = subprocess.run([
                "python3", str(QUEUE), "build", "--snapshot", str(snapshot),
                "--delivery-evidence-dir", str(root / "delivery"),
                "--today", "2026-07-28", "--output", str(output),
                "--require-live-source",
            ], text=True, capture_output=True)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)

    def test_real_state_fields_derive_due_feedback_quote_order_and_dedupe_quote(self):
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp) / "queue.json"
            proc = subprocess.run([
                "python3", str(QUEUE), "build", "--snapshot", str(FIXTURE),
                "--delivery-evidence-dir", str(Path(temp) / "delivery"),
                "--today", "2026-07-21", "--output", str(out),
            ], text=True, capture_output=True)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            queue = json.loads(out.read_text())
        self.assertEqual([item.get("request_id") or item["contract_id"] for item in queue["items"]], [
            "5138597", "5167108", "direct-offer:6198868",
        ])
        self.assertEqual([item["queue_class"] for item in queue["items"]], [
            "buyer_feedback_or_revision", "buyer_feedback_or_revision", "buyer_feedback_or_revision",
        ])
        self.assertEqual(sum(item["buyer"] == "sunai267" for item in queue["items"]), 1)

    def test_paid_always_wins_over_stale_quote_for_same_work(self):
        paid = {
            "contract_id": "talkroom:18011694", "request_id": "5167108", "talkroom_id": "18011694",
            "buyer": "sunai267", "title": "Minecraft addon repair", "status": "paid",
            "delivery_date": "2026-07-23", "price_jpy": 17000,
        }
        stale_quote = {
            "contract_id": "request:5167108", "request_id": "5167108", "buyer": "sunai267",
            "title": "Minecraft addon repair", "status": "proposal_required", "proposal_due": "2026-07-24",
            "price_jpy": 17000,
        }
        fuzzy_paid = dict(paid)
        fuzzy_paid.pop("request_id")
        fuzzy_quote = dict(stale_quote, request_id="old-quote-id")
        for match_kind, orders, quotes in (
            ("stable-request-id", [paid], [stale_quote]),
            ("exact-buyer-title-transition", [fuzzy_paid], [fuzzy_quote]),
        ):
            with self.subTest(match_kind=match_kind):
                queue = delivery_queue.build({"orders": orders, "quotes": quotes}, Path("/nonexistent"), delivery_queue.date(2026, 7, 21))
                self.assertEqual(len(queue["items"]), 1)
                self.assertEqual(queue["items"][0]["status"], "paid")
                self.assertEqual(queue["items"][0]["talkroom_id"], "18011694")

    def test_quote_before_purchase_remains_when_no_paid_order_exists(self):
        quote = {
            "contract_id": "request:5167108", "request_id": "5167108", "buyer": "sunai267",
            "title": "Minecraft addon repair", "status": "proposal_required", "proposal_due": "2026-07-24",
        }
        queue = delivery_queue.build({"orders": [], "quotes": [quote]}, Path("/nonexistent"), delivery_queue.date(2026, 7, 21))
        self.assertEqual(len(queue["items"]), 1)
        self.assertEqual(queue["items"][0]["queue_class"], "quote_needing_proposal")

    def test_same_buyer_different_title_keeps_paid_and_quote(self):
        snapshot = {
            "orders": [{"contract_id": "talkroom:1", "talkroom_id": "1", "buyer": "same", "title": "Paid work", "status": "paid"}],
            "quotes": [{"contract_id": "request:2", "request_id": "2", "buyer": "same", "title": "Different proposal", "status": "proposal_required"}],
        }
        queue = delivery_queue.build(snapshot, Path("/nonexistent"), delivery_queue.date(2026, 7, 21))
        self.assertEqual({item["status"] for item in queue["items"]}, {"paid", "proposal_required"})

    def test_any_buyer_reply_after_artifact_is_prioritized_as_feedback(self):
        snapshot = {"orders": [{
            "contract_id": "talkroom:42", "talkroom_id": "42",
            "buyer": "buyer", "title": "work", "status": "paid",
            "delivery_date": "2026-08-14",
            "buyer_reply_after_artifact_observed": True,
            "buyer_feedback_pending_artifact": False,
        }], "quotes": []}
        item = delivery_queue.build(snapshot, Path("/nonexistent"), delivery_queue.date(2026, 7, 22))["items"][0]
        self.assertEqual(item["queue_class"], "buyer_feedback_or_revision")

    def test_unknown_card_status_with_live_feedback_is_normalized_to_paid(self):
        snapshot = {"source": "authenticated_coconala_default_context_dom", "orders": [{
            "contract_id": "direct-offer:generic-42", "talkroom_id": "4201",
            "buyer": "buyer", "title": "generic returned delivery",
            "price_jpy": 17000, "price_source": "structured_order_label",
            "status": "unknown", "talkroom_state": "取引中",
            "buyer_feedback_pending_artifact": True,
            "buyer_reply_after_artifact_observed": False,
        }], "quotes": []}
        item = delivery_queue.build(snapshot, Path("/nonexistent"), delivery_queue.date(2026, 7, 22))["items"][0]
        self.assertEqual(item["status"], "paid")
        self.assertEqual(item["queue_class"], "buyer_feedback_or_revision")
        self.assertTrue(item["blockers"])

    def test_unknown_card_status_with_return_after_formal_delivery_stays_paid(self):
        snapshot = {"source": "authenticated_coconala_default_context_dom", "orders": [{
            "contract_id": "offer:6216643", "request_id": "5138597",
            "talkroom_id": "17963099", "buyer": "Fkimura",
            "title": "Python OpenCV board PoC",
            "delivery_date": "2026-07-21",
            "price_jpy": 65000, "price_source": "structured_order_label",
            "status": "unknown", "talkroom_state": "納品確認待ち",
            "formal_delivery_observed": True,
            "buyer_feedback_pending_artifact": True,
            "buyer_reply_after_artifact_observed": True,
            "buyer_visible_artifact_observed": False,
        }], "quotes": []}
        item = delivery_queue.build(
            snapshot, Path("/nonexistent"), delivery_queue.date(2026, 7, 22)
        )["items"][0]
        self.assertEqual(item["status"], "paid")
        self.assertEqual(item["queue_class"], "buyer_feedback_or_revision")
        self.assertEqual(item["talkroom_id"], "17963099")

    def test_unknown_card_status_without_structured_active_identity_is_not_paid(self):
        snapshot = {"orders": [{
            "contract_id": "talkroom:generic-43", "buyer": "buyer",
            "title": "generic unknown card", "status": "unknown",
            "talkroom_state": "取引中", "buyer_feedback_pending_artifact": True,
        }], "quotes": []}
        queue = delivery_queue.build(snapshot, Path("/nonexistent"), delivery_queue.date(2026, 7, 22))
        self.assertEqual(queue["items"], [])

    def test_evidence_path_uses_same_stable_identity_as_project_root(self):
        item = {
            "contract_id": "direct-offer:6198868",
            "talkroom_id": "17943244",
            "status": "paid",
        }
        self.assertEqual(
            delivery_queue.evidence_path(Path("/tmp/delivery-evidence"), item).name,
            "17943244.json",
        )

    def test_forged_local_formal_booleans_cannot_override_live_dom_false(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            artifact = root / "artifact-v1.zip"
            acceptance = root / "acceptance.json"
            artifact.write_bytes(b"real artifact bytes")
            acceptance.write_text('{"status":"PASS"}\n')
            evidence_root = root / "delivery"
            evidence_root.mkdir()
            (evidence_root / "999.json").write_text(json.dumps({
                "artifact_path": str(artifact), "artifact_version": "v1",
                "acceptance_evidence_path": str(acceptance), "acceptance_status": "PASS",
                "package_sha256": hashlib.sha256(artifact.read_bytes()).hexdigest(),
                # Forged local fields must never override the live snapshot.
                "formal_delivery_observed": True, "buyer_agreement_observed": True,
                "buyer_visible_artifact_observed": True, "talkroom_state": "納品確認待ち",
            }))
            snapshot = {"captured_at": "2026-07-21T11:00:00+00:00", "orders": [{
                "contract_id": "talkroom:999", "request_id": "999", "talkroom_id": "999",
                "buyer": "buyer", "title": "work", "status": "paid",
                "talkroom_state": "取引中", "formal_delivery_observed": False,
                "buyer_visible_artifact_observed": False,
            }], "quotes": []}
            item = delivery_queue.build(snapshot, evidence_root, delivery_queue.date(2026, 7, 21))["items"][0]
        self.assertEqual(item["blockers"], ["formal_delivery_not_confirmed"])
        self.assertFalse(item["delivery_ready"])
        self.assertEqual(item["delivery_action"], "progress")
        self.assertFalse(item["formal_delivery_checkbox"])

    def test_real_live_dom_formal_confirmation_can_clear_final_blocker(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            artifact = root / "artifact-v2.zip"
            acceptance = root / "acceptance.json"
            artifact.write_bytes(b"accepted artifact")
            acceptance.write_text('{"status":"PASS"}\n')
            evidence_root = root / "delivery"
            evidence_root.mkdir()
            (evidence_root / "1000.json").write_text(json.dumps({
                "artifact_path": str(artifact), "artifact_version": "v2",
                "acceptance_evidence_path": str(acceptance), "acceptance_status": "PASS",
                "package_sha256": hashlib.sha256(artifact.read_bytes()).hexdigest(),
            }))
            captured = "2026-07-21T11:00:00+00:00"
            snapshot = {"captured_at": captured, "orders": [{
                "contract_id": "talkroom:1000", "request_id": "1000", "talkroom_id": "1000",
                "buyer": "buyer", "title": "work", "status": "paid",
                "talkroom_state": "納品確認待ち", "formal_delivery_observed": True,
                "buyer_visible_artifact_observed": True, "talkroom_observed_at": captured,
                "talkroom_evidence_sha256": "a" * 64,
                "talkroom_screenshot_sha256": "b" * 64,
            }], "quotes": []}
            item = delivery_queue.build(snapshot, evidence_root, delivery_queue.date(2026, 7, 21))["items"][0]
        self.assertEqual(item["blockers"], [])
        self.assertTrue(item["delivery_ready"])
        self.assertEqual(item["delivery_action"], "none")

    def test_missing_artifact_acceptance_hash_and_formal_delivery_are_explicit_blockers(self):
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp) / "queue.json"
            subprocess.run([
                "python3", str(QUEUE), "build", "--snapshot", str(FIXTURE),
                "--delivery-evidence-dir", str(Path(temp) / "delivery"),
                "--today", "2026-07-21", "--output", str(out),
            ], check=True)
            top = json.loads(out.read_text())["items"][0]
        self.assertEqual(top["blockers"], [
            "missing_versioned_artifact", "missing_acceptance_evidence",
            "missing_package_hash", "formal_delivery_not_confirmed",
        ])
        self.assertFalse(top["delivery_ready"])
        self.assertEqual(top["delivery_action"], "progress")
        self.assertFalse(top["formal_delivery_checkbox"])
        self.assertTrue(top["progress_payload"]["buyer_visible"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
