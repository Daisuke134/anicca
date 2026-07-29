import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "reply_evidence.py"


def load_module():
    spec = importlib.util.spec_from_file_location("reply_evidence", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load reply_evidence")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class SpeedyReplyEvidenceTest(unittest.TestCase):
    def test_bounded_server_validation_category_is_retained(self):
        reply_evidence = load_module()
        self.assertIn(
            "submit_rejected_external_contact",
            reply_evidence.BROWSER_ERROR_CODES,
        )

    def test_matching_new_seller_message_is_replied_ground_truth(self):
        reply_evidence = load_module()
        outgoing_hash = "a" * 64
        intent = {
            "event_key": "coconala:message:v1:4201:msg-7",
            "talkroom_id": "4201",
            "talkroom_url": "https://coconala.com/mypage/direct_message/4201",
            "origin_at": "2026-07-22T00:00:00+00:00",
            "outgoing_hash": outgoing_hash,
        }
        before = {
            "talkroom_id": "4201",
            "url": "https://coconala.com/mypage/direct_message/4201",
            "fingerprint": "before",
            "seller_count": 2,
            "observed_at": "2026-07-22T00:04:00+00:00",
        }
        after = {
            "talkroom_id": "4201",
            "url": "https://coconala.com/mypage/direct_message/4201",
            "fingerprint": "after",
            "seller_count": 3,
            "last_sender": "seller",
            "seller_message_hashes": [outgoing_hash],
            "seller_sent_at": "2026-07-22T00:05:00+00:00",
            "observed_at": "2026-07-22T00:05:05+00:00",
        }

        result = reply_evidence.verify_reply(intent, before, after)

        self.assertEqual(result, {
            "status": "replied",
            "verified": True,
            "event_key": "coconala:message:v1:4201:msg-7",
            "talkroom_id": "4201",
            "thread_url": "https://coconala.com/mypage/direct_message/4201",
            "outgoing_hash": outgoing_hash,
            "seller_sent_at": "2026-07-22T00:05:00+00:00",
            "last_sender": "seller",
            "follow_up_required": False,
            "follow_up_origin_at": None,
            "blind_retry_allowed": False,
            "errors": [],
        })

    def test_buyer_message_after_verified_send_completes_reply_and_requires_follow_up(self):
        reply_evidence = load_module()
        outgoing_hash = "b" * 64
        intent = {
            "event_key": "coconala:4201:msg-7",
            "talkroom_id": "4201",
            "talkroom_url": "https://coconala.com/talkrooms/4201",
            "origin_at": "2026-07-22T00:00:00+00:00",
            "outgoing_hash": outgoing_hash,
        }
        before = {
            "talkroom_id": "4201",
            "url": "https://coconala.com/talkrooms/4201",
            "fingerprint": "before",
            "seller_count": 2,
        }
        after = {
            "talkroom_id": "4201",
            "url": "https://coconala.com/talkrooms/4201",
            "fingerprint": "after-buyer-follow-up",
            "seller_count": 3,
            "last_sender": "buyer",
            "seller_message_hashes": [outgoing_hash],
            "seller_sent_at": "2026-07-22T00:05:00+00:00",
            "latest_buyer_sent_at": "2026-07-22T00:05:03+00:00",
        }

        result = reply_evidence.verify_reply(intent, before, after)

        self.assertEqual(result["status"], "replied")
        self.assertTrue(result["verified"])
        self.assertTrue(result["follow_up_required"])
        self.assertEqual(result["follow_up_origin_at"], "2026-07-22T00:05:03+00:00")
        self.assertFalse(result["blind_retry_allowed"])

    def test_post_send_read_failure_stays_reconcile_pending_without_blind_retry(self):
        reply_evidence = load_module()
        intent = {
            "event_key": "coconala:4201:msg-7",
            "talkroom_id": "4201",
            "talkroom_url": "https://coconala.com/talkrooms/4201",
            "origin_at": "2026-07-22T00:00:00+00:00",
            "outgoing_hash": "c" * 64,
        }
        before = {
            "talkroom_id": "4201",
            "url": "https://coconala.com/talkrooms/4201",
            "fingerprint": "before",
            "seller_count": 2,
        }

        result = reply_evidence.verify_reply(intent, before, {"status": "read_failed"})

        self.assertEqual(result["status"], "reconcile_pending")
        self.assertFalse(result["verified"])
        self.assertFalse(result["blind_retry_allowed"])
        self.assertIsNone(result["seller_sent_at"])
        self.assertEqual(result["errors"], ["post_send_ground_truth_unavailable"])

    def test_post_click_page_diagnostic_explains_unconfirmed_send_without_raw_text(self):
        reply_evidence = load_module()
        intent = {
            "event_key": "coconala:4201:msg-7",
            "talkroom_id": "4201",
            "talkroom_url": "https://coconala.com/talkrooms/4201",
            "origin_at": "2026-07-22T00:00:00+00:00",
            "outgoing_hash": "c" * 64,
        }
        before = {
            "talkroom_id": "4201",
            "url": "https://coconala.com/talkrooms/4201",
            "fingerprint": "before",
            "seller_count": 2,
        }

        result = reply_evidence.verify_reply(
            intent,
            before,
            {
                "status": "read_failed",
                "send_diagnostic": {
                    "textarea_length": 42,
                    "button_disabled": False,
                    "visible_error_count": 1,
                },
            },
        )

        self.assertEqual(result["status"], "reconcile_pending")
        self.assertEqual(result["errors"], [
            "post_send_ground_truth_unavailable",
            "composer_not_cleared_after_click",
            "page_reported_send_error",
        ])
        self.assertNotIn("send_diagnostic", result)

    def test_post_click_network_failure_becomes_bounded_error_code(self):
        reply_evidence = load_module()
        intent = {
            "event_key": "coconala:4201:msg-7",
            "talkroom_id": "4201",
            "talkroom_url": "https://coconala.com/talkrooms/4201",
            "origin_at": "2026-07-22T00:00:00+00:00",
            "outgoing_hash": "c" * 64,
        }
        before = {
            "talkroom_id": "4201",
            "url": "https://coconala.com/talkrooms/4201",
            "fingerprint": "before",
            "seller_count": 2,
        }

        result = reply_evidence.verify_reply(intent, before, {
            "status": "read_failed",
            "send_network": [{
                "method": "POST",
                "path": "/mypage/direct_message_ajax/4201",
                "status": 422,
                "outcome": "finished",
            }],
        })

        self.assertEqual(result["errors"], [
            "post_send_ground_truth_unavailable",
            "send_request_http_error",
        ])
        self.assertNotIn("send_network", result)
        self.assertNotIn("/mypage/direct_message/4201", json.dumps(result))

    def test_pending_direct_message_post_has_specific_private_safe_error(self):
        reply_evidence = load_module()
        intent = {
            "event_key": "coconala:4201:msg-7",
            "talkroom_id": "4201",
            "talkroom_url": "https://coconala.com/mypage/direct_message/4201",
            "origin_at": "2026-07-22T00:00:00+00:00",
            "outgoing_hash": "c" * 64,
        }
        before = {
            "talkroom_id": "4201",
            "url": intent["talkroom_url"],
            "fingerprint": "before",
            "seller_count": 2,
        }

        result = reply_evidence.verify_reply(intent, before, {
            "status": "read_failed",
            "send_network": [{
                "method": "POST",
                "path": "/mypage/direct_message_ajax/4201",
                "status": None,
                "outcome": "pending",
            }],
        })

        self.assertEqual(result["errors"], [
            "post_send_ground_truth_unavailable",
            "direct_message_post_stalled",
        ])
        self.assertNotIn("send_network", result)

    def test_old_hash_plus_unrelated_new_seller_message_is_not_verified(self):
        reply_evidence = load_module()
        outgoing_hash = "c" * 64
        unrelated_hash = "d" * 64
        intent = {
            "event_key": "coconala:4201:msg-7",
            "talkroom_id": "4201",
            "talkroom_url": "https://coconala.com/mypage/direct_message/4201",
            "origin_at": "2026-07-22T00:00:00+00:00",
            "outgoing_hash": outgoing_hash,
        }
        before = {
            "talkroom_id": "4201",
            "url": intent["talkroom_url"],
            "fingerprint": "before",
            "seller_count": 1,
            "seller_message_hashes": [outgoing_hash],
            "seller_messages": [{
                "body_sha256": outgoing_hash,
                "sent_at": "2026-07-21T23:55:00+00:00",
            }],
        }
        after = {
            "talkroom_id": "4201",
            "url": intent["talkroom_url"],
            "fingerprint": "after",
            "seller_count": 2,
            "seller_message_hashes": [outgoing_hash, unrelated_hash],
            "seller_messages": [
                {
                    "body_sha256": outgoing_hash,
                    "sent_at": "2026-07-21T23:55:00+00:00",
                },
                {
                    "body_sha256": unrelated_hash,
                    "sent_at": "2026-07-22T00:01:00+00:00",
                },
            ],
            "seller_sent_at": "2026-07-22T00:01:00+00:00",
            "last_sender": "seller",
        }

        result = reply_evidence.verify_reply(intent, before, after)

        self.assertEqual(result["status"], "reconcile_pending")
        self.assertFalse(result["verified"])
        self.assertEqual(result["errors"], ["reply_ground_truth_not_confirmed"])

    def test_buyer_follow_up_without_new_outgoing_hash_stays_reconcile_pending(self):
        reply_evidence = load_module()
        old_hash = "a" * 64
        outgoing_hash = "b" * 64
        intent = {
            "event_key": "coconala:4201:msg-7",
            "talkroom_id": "4201",
            "talkroom_url": "https://coconala.com/mypage/direct_message/4201",
            "origin_at": "2026-07-22T00:00:00+00:00",
            "outgoing_hash": outgoing_hash,
        }
        before = {
            "talkroom_id": "4201",
            "url": intent["talkroom_url"],
            "fingerprint": "before",
            "seller_count": 1,
            "seller_message_hashes": [old_hash],
            "seller_messages": [{
                "body_sha256": old_hash,
                "sent_at": "2026-07-21T23:55:00+00:00",
            }],
        }
        after = {
            **before,
            "fingerprint": "after-buyer-follow-up",
            "seller_sent_at": "2026-07-21T23:55:00+00:00",
            "latest_buyer_sent_at": "2026-07-22T00:01:00+00:00",
            "last_sender": "buyer",
        }

        result = reply_evidence.verify_reply(intent, before, after)

        self.assertEqual(result["status"], "reconcile_pending")
        self.assertFalse(result["verified"])
        self.assertFalse(result["blind_retry_allowed"])
        self.assertFalse(result["follow_up_required"])
        self.assertEqual(result["errors"], ["reply_ground_truth_not_confirmed"])

    def test_only_auxiliary_post_means_direct_message_post_was_not_observed(self):
        reply_evidence = load_module()
        intent = {
            "event_key": "coconala:4201:msg-7",
            "talkroom_id": "4201",
            "talkroom_url": "https://coconala.com/mypage/direct_message/4201",
            "origin_at": "2026-07-22T00:00:00+00:00",
            "outgoing_hash": "c" * 64,
        }
        before = {
            "talkroom_id": "4201",
            "url": intent["talkroom_url"],
            "fingerprint": "before",
            "seller_count": 2,
        }

        result = reply_evidence.verify_reply(intent, before, {
            "status": "read_failed",
            "send_network": [{
                "method": "POST",
                "path": "/logs/impression",
                "status": None,
                "outcome": "pending",
            }],
        })

        self.assertEqual(result["errors"], [
            "post_send_ground_truth_unavailable",
            "direct_message_post_not_observed",
        ])

    def test_duplicate_outgoing_hash_is_detected_not_marked_replied(self):
        reply_evidence = load_module()
        outgoing_hash = "d" * 64
        intent = {
            "event_key": "coconala:4201:msg-7",
            "talkroom_id": "4201",
            "talkroom_url": "https://coconala.com/talkrooms/4201",
            "origin_at": "2026-07-22T00:00:00+00:00",
            "outgoing_hash": outgoing_hash,
        }
        before = {
            "talkroom_id": "4201",
            "url": "https://coconala.com/talkrooms/4201",
            "fingerprint": "before",
            "seller_count": 2,
        }
        after = {
            "talkroom_id": "4201",
            "url": "https://coconala.com/talkrooms/4201",
            "fingerprint": "after",
            "seller_count": 4,
            "last_sender": "seller",
            "seller_message_hashes": [outgoing_hash, outgoing_hash],
            "seller_sent_at": "2026-07-22T00:05:00+00:00",
        }

        result = reply_evidence.verify_reply(intent, before, after)

        self.assertEqual(result["status"], "duplicate_detected")
        self.assertFalse(result["verified"])
        self.assertFalse(result["blind_retry_allowed"])
        self.assertEqual(result["errors"], ["duplicate_outgoing_message"])

    def test_wrong_thread_evidence_is_invalid_not_replied(self):
        reply_evidence = load_module()
        outgoing_hash = "e" * 64
        intent = {
            "event_key": "coconala:4201:msg-7",
            "talkroom_id": "4201",
            "talkroom_url": "https://coconala.com/talkrooms/4201",
            "origin_at": "2026-07-22T00:00:00+00:00",
            "outgoing_hash": outgoing_hash,
        }
        before = {
            "talkroom_id": "4201",
            "url": "https://coconala.com/talkrooms/4201",
            "fingerprint": "before",
            "seller_count": 2,
        }
        after = {
            "talkroom_id": "9999",
            "url": "https://coconala.com/talkrooms/9999",
            "fingerprint": "after",
            "seller_count": 3,
            "last_sender": "seller",
            "seller_message_hashes": [outgoing_hash],
            "seller_sent_at": "2026-07-22T00:05:00+00:00",
        }

        result = reply_evidence.verify_reply(intent, before, after)

        self.assertEqual(result["status"], "evidence_invalid")
        self.assertFalse(result["verified"])
        self.assertEqual(result["errors"], ["thread_identity_mismatch"])

    def test_intent_url_must_match_its_talkroom_id(self):
        reply_evidence = load_module()
        outgoing_hash = "9" * 64
        intent = {
            "event_key": "coconala:4201:msg-7",
            "talkroom_id": "4201",
            "talkroom_url": "https://coconala.com/talkrooms/9999",
            "origin_at": "2026-07-22T00:00:00+00:00",
            "outgoing_hash": outgoing_hash,
        }
        before = {
            "talkroom_id": "4201",
            "url": "https://coconala.com/talkrooms/9999",
            "fingerprint": "before",
            "seller_count": 2,
        }
        after = {
            "talkroom_id": "4201",
            "url": "https://coconala.com/talkrooms/9999",
            "fingerprint": "after",
            "seller_count": 3,
            "last_sender": "seller",
            "seller_message_hashes": [outgoing_hash],
            "seller_sent_at": "2026-07-22T00:05:00+00:00",
        }

        result = reply_evidence.verify_reply(intent, before, after)

        self.assertEqual(result["status"], "evidence_invalid")
        self.assertFalse(result["verified"])
        self.assertEqual(result["errors"], ["intent_thread_identity_mismatch"])

    def test_verify_cli_writes_owner_only_privacy_bounded_result(self):
        outgoing_hash = "f" * 64
        intent = {
            "event_key": "coconala:4201:msg-7",
            "talkroom_id": "4201",
            "talkroom_url": "https://coconala.com/talkrooms/4201",
            "origin_at": "2026-07-22T00:00:00+00:00",
            "outgoing_hash": outgoing_hash,
        }
        before = {
            "talkroom_id": "4201",
            "url": "https://coconala.com/talkrooms/4201",
            "fingerprint": "before",
            "seller_count": 2,
            "raw_message": "must-not-leak",
        }
        after = {
            "talkroom_id": "4201",
            "url": "https://coconala.com/talkrooms/4201",
            "fingerprint": "after",
            "seller_count": 3,
            "last_sender": "seller",
            "seller_message_hashes": [outgoing_hash],
            "seller_sent_at": "2026-07-22T00:05:00+00:00",
            "raw_message": "must-not-leak",
        }
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            paths = {}
            for name, value in (("intent", intent), ("before", before), ("after", after)):
                paths[name] = root / f"{name}.json"
                paths[name].write_text(json.dumps(value), encoding="utf-8")
            output = root / "reply-evidence.json"

            completed = subprocess.run([
                sys.executable,
                str(SCRIPT),
                "verify",
                "--intent", str(paths["intent"]),
                "--before", str(paths["before"]),
                "--after", str(paths["after"]),
                "--output", str(output),
            ], capture_output=True, text=True, check=False)

            self.assertEqual(completed.returncode, 0, completed.stderr)
            serialized = output.read_text(encoding="utf-8")
            self.assertEqual(json.loads(serialized)["status"], "replied")
            self.assertNotIn("must-not-leak", serialized)
            self.assertEqual(os.stat(output).st_mode & 0o777, 0o600)

    def test_non_sha256_intent_cannot_be_verified(self):
        reply_evidence = load_module()
        intent = {
            "event_key": "coconala:4201:msg-7",
            "talkroom_id": "4201",
            "talkroom_url": "https://coconala.com/talkrooms/4201",
            "origin_at": "2026-07-22T00:00:00+00:00",
            "outgoing_hash": "not-a-sha256",
        }
        before = {
            "talkroom_id": "4201",
            "url": "https://coconala.com/talkrooms/4201",
            "fingerprint": "before",
            "seller_count": 2,
        }
        after = {
            "talkroom_id": "4201",
            "url": "https://coconala.com/talkrooms/4201",
            "fingerprint": "after",
            "seller_count": 3,
            "last_sender": "seller",
            "seller_message_hashes": ["not-a-sha256"],
            "seller_sent_at": "2026-07-22T00:05:00+00:00",
        }

        result = reply_evidence.verify_reply(intent, before, after)

        self.assertEqual(result["status"], "evidence_invalid")
        self.assertFalse(result["verified"])
        self.assertEqual(result["errors"], ["invalid_outgoing_hash"])

    def test_changed_dom_without_matching_hash_remains_reconcile_pending(self):
        reply_evidence = load_module()
        outgoing_hash = "1" * 64
        intent = {
            "event_key": "coconala:4201:msg-7",
            "talkroom_id": "4201",
            "talkroom_url": "https://coconala.com/talkrooms/4201",
            "origin_at": "2026-07-22T00:00:00+00:00",
            "outgoing_hash": outgoing_hash,
        }
        before = {
            "talkroom_id": "4201",
            "url": "https://coconala.com/talkrooms/4201",
            "fingerprint": "before",
            "seller_count": 2,
        }
        after = {
            "talkroom_id": "4201",
            "url": "https://coconala.com/talkrooms/4201",
            "fingerprint": "changed-for-another-reason",
            "seller_count": 3,
            "last_sender": "seller",
            "seller_message_hashes": ["2" * 64],
            "seller_sent_at": "2026-07-22T00:05:00+00:00",
        }

        result = reply_evidence.verify_reply(intent, before, after)

        self.assertEqual(result["status"], "reconcile_pending")
        self.assertFalse(result["verified"])
        self.assertFalse(result["blind_retry_allowed"])
        self.assertEqual(result["errors"], ["reply_ground_truth_not_confirmed"])
