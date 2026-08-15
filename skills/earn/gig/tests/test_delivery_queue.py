import json
import hashlib
import importlib.util
import subprocess
import tempfile
import unittest
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path


SKILL = Path(__file__).resolve().parents[1]
QUEUE = SKILL / "scripts" / "delivery_queue.py"
FIXTURE = Path(__file__).resolve().parent / "fixtures" / "live_queue.json"

SPEC = importlib.util.spec_from_file_location("delivery_queue", QUEUE)
delivery_queue = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(delivery_queue)


def covered_orders_snapshot(*orders):
    return {
        "source": "authenticated_coconala_hidden_default_context_dom",
        "read_only": True,
        "captured_at": "2026-08-11T06:37:05+00:00",
        "collector_mode": "orders-only",
        "observed_sources": ["orders"],
        "open_orders_list_observed": True,
        "orders": list(orders),
        "source_receipt": {
            "source": "orders",
            "requested_route": "https://coconala.com/mypage/received_orders/open",
            "final_route": "https://coconala.com/mypage/received_orders/open",
            "login_redirect": False,
            "cards_count": len(orders),
            "empty_state_present": not orders,
            "coverage_complete": True,
        },
    }


def preliminary_order(
    talkroom_id="90000001",
    *,
    status="unknown",
    delivery_date="2026-08-12",
    price_jpy=12000,
    **overrides,
):
    order = {
        "contract_id": f"talkroom:{talkroom_id}",
        "talkroom_id": str(talkroom_id),
        "buyer": "buyer",
        "title": "paid work",
        "price_jpy": price_jpy,
        "price_source": "structured_order_label",
        "delivery_date": delivery_date,
        "status": status,
        "marketplace_url": f"https://coconala.com/talkrooms/{talkroom_id}",
    }
    order.update(overrides)
    return order


class DeliveryQueueTest(unittest.TestCase):
    def test_covered_orders_only_row_becomes_non_actionable_preliminary_item(self):
        snapshot = covered_orders_snapshot(preliminary_order(status="unknown"))

        queue = delivery_queue.build_preliminary(
            snapshot, delivery_queue.date(2026, 8, 11)
        )

        self.assertEqual(queue["selection_stage"], "preliminary")
        self.assertEqual(len(queue["items"]), 1)
        item = queue["items"][0]
        self.assertEqual(item["status"], "unknown")
        self.assertEqual(item["selection_stage"], "preliminary")
        self.assertTrue(item["targeted_readback_required"])
        self.assertFalse(item["delivery_ready"])
        self.assertEqual(item["delivery_action"], "none")
        self.assertEqual(item["blockers"], ["targeted_talkroom_readback_required"])

    def test_preliminary_cli_writes_selection_queue(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            snapshot = root / "snapshot.json"
            output = root / "preliminary.json"
            snapshot.write_text(
                json.dumps(covered_orders_snapshot(preliminary_order(status="paid")))
            )
            proc = subprocess.run([
                "python3", str(QUEUE), "preliminary", "--snapshot", str(snapshot),
                "--today", "2026-08-11", "--output", str(output),
            ], text=True, capture_output=True)

            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            queue = json.loads(output.read_text())
        self.assertEqual(queue["selection_stage"], "preliminary")
        self.assertEqual(queue["items"][0]["status"], "paid")
        self.assertEqual(queue["items"][0]["delivery_action"], "none")

    def test_preliminary_rejects_missing_or_malformed_coverage(self):
        order = preliminary_order()
        cases = []

        missing_observed = covered_orders_snapshot(order)
        missing_observed.pop("open_orders_list_observed")
        cases.append(missing_observed)

        incomplete = covered_orders_snapshot(order)
        incomplete["source_receipt"]["coverage_complete"] = False
        cases.append(incomplete)

        count_mismatch = covered_orders_snapshot(order)
        count_mismatch["source_receipt"]["cards_count"] = 0
        cases.append(count_mismatch)

        wrong_route = covered_orders_snapshot(order)
        wrong_route["source_receipt"]["final_route"] = (
            "https://coconala.com/mypage/received_orders/closed"
        )
        cases.append(wrong_route)

        for snapshot in cases:
            with self.subTest(snapshot=snapshot):
                with self.assertRaises(ValueError):
                    delivery_queue.build_preliminary(
                        deepcopy(snapshot), delivery_queue.date(2026, 8, 11)
                    )

    def test_preliminary_marker_denies_strict_paid_gate_until_targeted_readback(self):
        unknown = delivery_queue.build_preliminary(
            covered_orders_snapshot(preliminary_order(status="unknown")),
            delivery_queue.date(2026, 8, 11),
        )["items"][0]
        paid = delivery_queue.build_preliminary(
            covered_orders_snapshot(preliminary_order(status="paid")),
            delivery_queue.date(2026, 8, 11),
        )["items"][0]
        self.assertFalse(delivery_queue.is_active_paid_order(unknown))
        self.assertFalse(delivery_queue.is_active_paid_order(paid))
        for marker, value in (("selection_stage", "preliminary"),
                              ("targeted_readback_required", True)):
            marked = dict(paid, selection_stage=None, targeted_readback_required=False)
            marked[marker] = value
            self.assertFalse(delivery_queue.is_active_paid_order(marked), marker)

        enriched = dict(unknown)
        for key in (
            "selection_stage",
            "targeted_readback_required",
            "delivery_ready",
            "delivery_action",
            "blockers",
        ):
            enriched.pop(key, None)
        enriched.update({
            "price_jpy": 12000,
            "price_source": "structured_order_label",
            "talkroom_state": "取引中",
            "buyer_feedback_pending_artifact": True,
            "buyer_reply_after_artifact_observed": True,
            "buyer_feedback_stage": "revision",
        })
        self.assertTrue(delivery_queue.is_active_paid_order(enriched))

    def test_targeted_paid_revalidates_live_state_but_legacy_paid_shortcut_remains(self):
        targeted = preliminary_order(
            status="paid",
            selection_stage="targeted",
            targeted_readback_required=False,
            talkroom_state="取引中",
            buyer_feedback_pending_artifact=True,
            buyer_reply_after_artifact_observed=False,
            buyer_feedback_stage="revision",
            buyer_feedback_sha256="f" * 64,
        )
        self.assertTrue(delivery_queue.is_active_paid_order(targeted))

        terminal = dict(
            targeted,
            talkroom_state="取引完了",
            formal_delivery_observed=False,
            buyer_formal_delivery_hold=False,
        )
        self.assertFalse(delivery_queue.is_active_paid_order(terminal))

        legacy = preliminary_order(status="paid")
        self.assertTrue(delivery_queue.is_active_paid_order(legacy))

    def test_targeted_subscription_revision_is_live_when_step_state_is_unknown(self):
        subscription = preliminary_order(
            status="paid",
            selection_stage="targeted",
            targeted_readback_required=False,
            room_contract_kind="subscription",
            talkroom_state="unknown",
            buyer_feedback_pending_artifact=True,
            buyer_feedback_stage="revision",
            buyer_feedback_sha256="d" * 64,
        )

        self.assertTrue(delivery_queue.is_active_paid_order(subscription))

    def test_covered_semantic_empty_snapshot_returns_verified_empty_preliminary_queue(self):
        queue = delivery_queue.build_preliminary(
            covered_orders_snapshot(), delivery_queue.date(2026, 8, 11)
        )

        self.assertEqual(queue["selection_stage"], "preliminary")
        self.assertEqual(queue["items"], [])

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

    def test_production_queue_still_rejects_a_truly_stale_live_dom_snapshot(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            snapshot = root / "snapshot.json"
            output = root / "queue.json"
            snapshot.write_text(json.dumps({
                "source": "authenticated_coconala_hidden_default_context_dom",
                "read_only": True,
                "captured_at": (datetime.now(timezone.utc) - timedelta(seconds=301)).isoformat(),
                "orders": [],
                "quotes": [],
            }))
            proc = subprocess.run([
                "python3", str(QUEUE), "build", "--snapshot", str(snapshot),
                "--delivery-evidence-dir", str(root / "delivery"),
                "--today", "2026-07-28", "--output", str(output),
                "--require-live-source", "--max-age-seconds", "300",
            ], text=True, capture_output=True)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("live DOM snapshot is stale", proc.stdout)

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
            "91000014", "91000018", "direct-offer:92000003",
        ])
        self.assertEqual([item["queue_class"] for item in queue["items"]], [
            "buyer_feedback_or_revision", "buyer_feedback_or_revision", "buyer_feedback_or_revision",
        ])
        self.assertEqual(sum(item["buyer"] == "buyer_handle_c" for item in queue["items"]), 1)

    def test_paid_always_wins_over_stale_quote_for_same_work(self):
        paid = {
            "contract_id": "talkroom:90000010", "request_id": "91000018", "talkroom_id": "90000010",
            "buyer": "buyer_handle_c", "title": "Minecraft addon repair", "status": "paid",
            "delivery_date": "2026-07-23", "price_jpy": 17000,
        }
        stale_quote = {
            "contract_id": "request:91000018", "request_id": "91000018", "buyer": "buyer_handle_c",
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
                self.assertEqual(queue["items"][0]["talkroom_id"], "90000010")

    def test_quote_before_purchase_remains_when_no_paid_order_exists(self):
        quote = {
            "contract_id": "request:91000018", "request_id": "91000018", "buyer": "buyer_handle_c",
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
            "contract_id": "offer:92000005", "request_id": "91000014",
            "talkroom_id": "90000008", "buyer": "buyer_handle_a",
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
        self.assertEqual(item["talkroom_id"], "90000008")

    def test_unknown_completed_buyer_hold_with_open_feedback_stays_paid(self):
        snapshot = {"source": "authenticated_coconala_default_context_dom", "orders": [{
            "contract_id": "offer:generic-held-42", "request_id": "91000042",
            "talkroom_id": "90000042", "buyer": "buyer", "title": "openable draft",
            "price_jpy": 5000, "price_source": "structured_order_label", "status": "unknown",
            "talkroom_state": "取引完了", "formal_delivery_observed": False,
            "formal_delivery_control_disabled": True,
            "buyer_formal_delivery_hold": True,
            "buyer_feedback_pending_artifact": True,
            "buyer_reply_after_artifact_observed": True,
        }], "quotes": []}
        item = delivery_queue.build(
            snapshot, Path("/nonexistent"), delivery_queue.date(2026, 8, 11)
        )["items"][0]
        self.assertEqual(item["status"], "paid")
        self.assertEqual(item["queue_class"], "buyer_feedback_or_revision")
        self.assertTrue(item["buyer_formal_delivery_hold"])

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
            "contract_id": "direct-offer:92000003",
            "talkroom_id": "90000000",
            "status": "paid",
        }
        self.assertEqual(
            delivery_queue.evidence_path(Path("/tmp/delivery-evidence"), item).name,
            "90000000.json",
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
        # Forged local booleans cannot fabricate the live 納品確認待ち state, so
        # the item is still owed a formal submission (Dais ruling 2026-07-25:
        # formal_delivery_not_confirmed is the action to perform, not a
        # prerequisite). The real artifact/acceptance/hash gates all passed.
        self.assertEqual(item["delivery_action"], "formal")
        self.assertTrue(item["formal_delivery_checkbox"])
        # The forgery is still refused where it matters: the item is not closed
        # out as already delivered.
        self.assertNotEqual(item["delivery_action"], "none")

    def test_real_live_dom_formal_confirmation_can_clear_final_blocker(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            artifact = root / "artifact-v2.zip"
            acceptance = root / "acceptance.json"
            artifact.write_bytes(b"accepted artifact")
            acceptance.write_text('{"status":"PASS"}\n')
            evidence_root = root / "delivery"
            evidence_root.mkdir()
            # project_root is what the builder records in every real manifest, and the
            # cadence needs it to look for a standing BLOCKED record before closing a
            # delivered order out. There is none here: this is a healthy delivery.
            (evidence_root / "1000.json").write_text(json.dumps({
                "project_root": str(root), "artifact_path": str(artifact),
                "artifact_version": "v2",
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
        # P0-1: nothing was built, so there is nothing to show the buyer. The
        # item stays internal work instead of becoming a promise to send later,
        # and no buyer-visible payload is produced at all.
        self.assertEqual(top["delivery_action"], "work_required")
        self.assertFalse(top["formal_delivery_checkbox"])
        self.assertIsNone(top["progress_payload"])

    def test_site_observed_buyer_hold_suppresses_only_the_same_package_hash(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "projects" / "9000001"
            root.mkdir(parents=True)
            artifact = root / "deliverable-v1.zip"
            artifact.write_bytes(b"held package")
            digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
            acceptance = root / "acceptance.json"
            acceptance.write_text('{"status":"PASS"}\n', encoding="utf-8")
            (root / "state.json").write_text(json.dumps({
                "request_id": "9000001",
                "adapter": "coconala",
                "transaction_state": "取引完了",
            }), encoding="utf-8")
            (root / "events.jsonl").write_text(json.dumps({
                "event": "formal_delivery_observed_held",
                "state": {"delivery_send_suppressed_package_sha256": digest},
            }) + "\n", encoding="utf-8")
            delivery = Path(temp) / "delivery"
            delivery.mkdir()
            (delivery / "9000001.json").write_text(json.dumps({
                "project_root": str(root),
                "artifact_path": str(artifact),
                "artifact_version": "v1",
                "acceptance_evidence_path": str(acceptance),
                "acceptance_status": "PASS",
                "acceptance_delta": ["対応済み"],
                "package_sha256": digest,
            }), encoding="utf-8")
            common = {
                "contract_id": "talkroom:93000000",
                "request_id": "9000001",
                "talkroom_id": "93000000",
                "buyer": "buyer",
                "title": "work",
                "status": "paid",
                "price_jpy": 1000,
                "price_source": "structured_order_label",
                "contract_id": "talkroom:93000000",
                "talkroom_state": "取引完了",
                "buyer_formal_delivery_hold": True,
                "formal_delivery_control_disabled": True,
            }
            same = delivery_queue.build(
                {"orders": [common], "quotes": []}, delivery, delivery_queue.date(2026, 8, 10)
            )["items"][0]
            self.assertEqual(same["delivery_action"], "none")
            self.assertFalse(same["formal_delivery_checkbox"])
            self.assertTrue(same["resend_suppressed"])
            self.assertEqual(same["delivery_send_suppressed_package_sha256"], digest)

            new_artifact = root / "deliverable-v2.zip"
            new_artifact.write_bytes(b"new package")
            new_digest = hashlib.sha256(new_artifact.read_bytes()).hexdigest()
            (delivery / "9000001.json").write_text(json.dumps({
                "project_root": str(root),
                "artifact_path": str(new_artifact),
                "artifact_version": "v2",
                "acceptance_evidence_path": str(acceptance),
                "acceptance_status": "PASS",
                "acceptance_delta": ["追加対応"],
                "package_sha256": new_digest,
            }), encoding="utf-8")
            fresh = delivery_queue.build(
                {"orders": [common], "quotes": []}, delivery, delivery_queue.date(2026, 8, 10)
            )["items"][0]
            self.assertNotEqual(fresh["delivery_action"], "none")
            self.assertFalse(fresh.get("resend_suppressed", False))

            feedback = "f" * 64
            requirements = root / "requirements" / "live-buyer-reply.json"
            requirements.parent.mkdir(parents=True)
            requirements.write_text(json.dumps({
                "feedback_sha256": feedback,
                "feedback_first_observed_at": "2026-08-11T00:00:00+00:00",
            }), encoding="utf-8")
            reopened = delivery_queue.build(
                {"orders": [dict(common,
                    buyer_feedback_pending_artifact=True,
                    buyer_reply_after_artifact_observed=True,
                    buyer_feedback_sha256=feedback,
                    buyer_feedback_requirements_path=str(requirements),
                )], "quotes": []},
                delivery, delivery_queue.date(2026, 8, 11),
            )["items"][0]
            self.assertFalse(reopened.get("resend_suppressed", False))
            self.assertEqual(reopened["delivery_action"], "work_required")


if __name__ == "__main__":
    unittest.main(verbosity=2)
