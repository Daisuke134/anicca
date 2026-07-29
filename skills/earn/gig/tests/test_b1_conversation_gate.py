import hashlib
import importlib.util
import json
import tempfile
import time
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "b1_conversation_gate.py"
SPEC = importlib.util.spec_from_file_location("b1_conversation_gate", SCRIPT)
gate = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(gate)


INBOX_URL = "https://coconala.com/message?fromMyPage=true"


def snapshot() -> dict:
    return {
        "version": 1,
        "source": "authenticated_coconala_default_context_dom",
        "captured_at": "2026-07-22T13:00:00+00:00",
        "inbox": {"url": INBOX_URL, "not_found": False},
        "orders": [
            {"talkroom_id": "101", "marketplace_url": "https://coconala.com/talkrooms/101"},
            {"talkroom_id": "102"},
        ],
        "quotes": [],
        "inquiries": [
            {"talkroom_id": "203", "talkroom_url": "https://coconala.com/mypage/direct_message/203", "reply_required": True},
        ],
        "b1_inquiries": [
            {"talkroom_id": "103", "talkroom_url": "https://coconala.com/talkrooms/103", "reply_required": True},
            {"talkroom_id": "104", "talkroom_url": "https://coconala.com/talkrooms/104", "reply_required": False},
        ],
    }


def queue() -> dict:
    return {
        "version": 1,
        "items": [
            {"queue_class": "other_paid_work", "talkroom_id": "102", "marketplace_url": "https://coconala.com/talkrooms/102"},
            {"queue_class": "nurture", "talkroom_id": "105", "talkroom_url": "https://coconala.com/talkrooms/105"},
        ],
    }


class B1ConversationGateTest(unittest.TestCase):
    def test_context_unions_open_orders_inquiries_and_queue_without_identity_hardcodes(self):
        context = gate.build_context(snapshot(), queue(), Path("/tmp/current-snapshot.json"), Path("/tmp/current-queue.json"))
        self.assertEqual(context["inbox_url"], INBOX_URL)
        self.assertEqual(
            [row["talkroom_id"] for row in context["actionable_talkrooms"]],
            ["101", "102", "103", "104", "105"],
        )
        by_id = {row["talkroom_id"]: row for row in context["actionable_talkrooms"]}
        self.assertEqual(by_id["102"]["reasons"], ["open_paid_order", "queue:other_paid_work"])
        self.assertEqual(by_id["103"]["reasons"], ["open_inquiry", "reply_required"])
        self.assertEqual(by_id["104"]["reasons"], ["open_inquiry"])
        self.assertNotIn("203", by_id)
        serialized = json.dumps(context, ensure_ascii=False)
        self.assertNotIn("buyer", serialized)
        self.assertNotIn("title", serialized)

    def test_context_fails_closed_for_missing_or_invalid_inputs(self):
        cases = []
        missing_inbox = snapshot(); missing_inbox.pop("inbox")
        cases.append((missing_inbox, queue(), "missing_snapshot_inbox"))
        wrong_route = snapshot(); wrong_route["inbox"]["url"] = "https://coconala.com/mypage/messages"
        cases.append((wrong_route, queue(), "invalid_inbox_route"))
        not_found = snapshot(); not_found["inbox"]["not_found"] = True
        cases.append((not_found, queue(), "inbox_not_found"))
        malformed_queue = queue(); malformed_queue["items"] = "not-a-list"
        cases.append((snapshot(), malformed_queue, "malformed_queue_items"))
        mismatched = snapshot(); mismatched["orders"][0]["marketplace_url"] = "https://coconala.com/talkrooms/999"
        cases.append((mismatched, queue(), "talkroom_identity_url_mismatch"))
        for snapshot_row, queue_row, expected in cases:
            with self.subTest(expected=expected):
                with self.assertRaisesRegex(gate.ContractError, expected):
                    gate.build_context(snapshot_row, queue_row, Path("snapshot.json"), Path("queue.json"))

    def test_result_must_cover_every_talkroom_with_fresh_owned_browser_evidence(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            context_path = root / "b1-context.json"
            context = gate.build_context(snapshot(), queue(), root / "snapshot.json", root / "queue.json")
            context_path.write_text(json.dumps(context) + "\n", encoding="utf-8")
            context_sha = hashlib.sha256(context_path.read_bytes()).hexdigest()
            agent = root / "agent-B1"; agent.mkdir()

            inbox_shot = agent / "inbox.png"; inbox_shot.write_bytes(b"png")
            inbox_dom = agent / "inbox.json"
            inbox_dom.write_text(json.dumps({"url": INBOX_URL, "not_found": False, "observed": True}) + "\n")
            inspected = []
            for row in context["actionable_talkrooms"]:
                room_id = row["talkroom_id"]
                shot = agent / f"room-{room_id}.png"; shot.write_bytes(b"png")
                dom = agent / f"room-{room_id}.json"
                dom.write_text(json.dumps({"url": row["url"], "observed": True}) + "\n")
                inspected.append({
                    "talkroom_id": room_id,
                    "url": row["url"],
                    "outcome": "observed_no_action",
                    "screenshot_path": str(shot),
                    "live_dom_path": str(dom),
                })
            result_path = agent / "attempt-01.result.json"
            result = {
                "status": "ok",
                "summary": "all deterministic conversations inspected",
                "evidence": ["fresh inbox and talkroom evidence"],
                "current_b1": {
                    "context_path": str(context_path),
                    "context_sha256": context_sha,
                    "inbox_url": INBOX_URL,
                    "inbox_status": "ok",
                    "inbox_screenshot_path": str(inbox_shot),
                    "inbox_live_dom_path": str(inbox_dom),
                    "inspected_talkrooms": inspected,
                },
            }
            result_path.write_text(json.dumps(result) + "\n")
            summary_path = agent / "summary.json"
            summary_path.write_text(json.dumps({
                "status": "success", "task_label": "gig-B1", "result_path": str(result_path),
            }) + "\n")
            min_mtime = time.time() - 2

            ok, errors = gate.validate_result(context_path, summary_path, agent, min_mtime)
            self.assertTrue(ok, errors)

            result["current_b1"]["inspected_talkrooms"].pop()
            result_path.write_text(json.dumps(result) + "\n")
            ok, errors = gate.validate_result(context_path, summary_path, agent, min_mtime)
            self.assertFalse(ok)
            self.assertIn("talkroom_coverage_mismatch", errors)

    def test_result_rejects_404_inbox_and_escaped_or_wrong_talkroom_evidence(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); agent = root / "agent-B1"; agent.mkdir()
            small_snapshot = snapshot(); small_snapshot["orders"] = [small_snapshot["orders"][0]]; small_snapshot["inquiries"] = []; small_snapshot["b1_inquiries"] = []
            context = gate.build_context(small_snapshot, {"version": 1, "items": []}, root / "snapshot.json", root / "queue.json")
            context_path = root / "b1-context.json"; context_path.write_text(json.dumps(context) + "\n")
            context_sha = hashlib.sha256(context_path.read_bytes()).hexdigest()
            outside = root / "outside.png"; outside.write_bytes(b"png")
            inbox_dom = agent / "inbox.json"; inbox_dom.write_text(json.dumps({"url": INBOX_URL, "not_found": True, "observed": True}))
            room_dom = agent / "room.json"; room_dom.write_text(json.dumps({"url": "https://coconala.com/talkrooms/999", "observed": True}))
            result_path = agent / "attempt-01.result.json"
            result_path.write_text(json.dumps({
                "status": "ok", "summary": "bad", "evidence": ["bad"],
                "current_b1": {
                    "context_path": str(context_path), "context_sha256": context_sha,
                    "inbox_url": INBOX_URL, "inbox_status": "ok",
                    "inbox_screenshot_path": str(outside), "inbox_live_dom_path": str(inbox_dom),
                    "inspected_talkrooms": [{
                        "talkroom_id": "101", "url": "https://coconala.com/talkrooms/101",
                        "outcome": "observed_no_action", "screenshot_path": str(outside),
                        "live_dom_path": str(room_dom),
                    }],
                },
            }) + "\n")
            summary = agent / "summary.json"; summary.write_text(json.dumps({
                "status": "success", "task_label": "gig-B1", "result_path": str(result_path),
            }))
            ok, errors = gate.validate_result(context_path, summary, agent, time.time() - 2)
            self.assertFalse(ok)
            self.assertIn("inbox_not_found", errors)
            self.assertIn("inbox_screenshot_not_owned", errors)
            self.assertIn("talkroom_screenshot_not_owned:101", errors)
            self.assertIn("talkroom_live_dom_url_mismatch:101", errors)


if __name__ == "__main__":
    unittest.main(verbosity=2)
