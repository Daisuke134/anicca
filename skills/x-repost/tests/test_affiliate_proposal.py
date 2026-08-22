from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "affiliate_proposal.py"
SPEC = importlib.util.spec_from_file_location("affiliate_proposal", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class AffiliateProposalTests(unittest.TestCase):
    def test_unverified_is_readback_only_until_posted_ledger_recovers_it(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            proposal_path = root / "proposal.json"
            consumed, posted = root / "consumed.jsonl", root / "posted.jsonl"
            proposal = {
                "receipt_type": "AFFILIATE_REPOST_PROPOSAL",
                "state": "READY_FOR_EXISTING_REPOST_OWNER",
                "proposal_id": "9" * 64,
                "placement_id": "voice-changer-en-1",
                "owned_article_url": "https://aniccaai.com/blog/voice-changer",
                "language": "en", "disclosure_required": True,
                "tracking_link_state": "NOT_INCLUDED",
                "revenue_credit_state": "NO_REVENUE_CREDIT",
            }
            proposal_path.write_text(json.dumps(proposal))
            MODULE.claim(consumed, proposal)
            MODULE.record(consumed, proposal, "UNVERIFIED", None)
            selected = MODULE.select(proposal_path, consumed, posted)
            self.assertEqual(selected["state"], "VERIFY_UNVERIFIED")
            posted.write_text(json.dumps({"affiliate_proposal_id": proposal["proposal_id"]}) + "\n")
            self.assertEqual(MODULE.select(proposal_path, consumed, posted)["state"], "ALREADY_CONSUMED")

    def test_select_and_record_are_exactly_once_without_tracking_link(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            proposal_path = root / "proposal.json"
            consumed = root / "consumed.jsonl"
            proposal_path.write_text(json.dumps({
                "receipt_type": "AFFILIATE_REPOST_PROPOSAL",
                "state": "READY_FOR_EXISTING_REPOST_OWNER",
                "proposal_id": "a" * 64,
                "placement_id": "voice-isolator-en-1",
                "owned_article_url": "https://aniccaai.com/blog/voice-isolator",
                "language": "en",
                "disclosure_required": True,
                "tracking_link_state": "NOT_INCLUDED",
                "revenue_credit_state": "NO_REVENUE_CREDIT",
            }))
            selected = MODULE.select(proposal_path, consumed)
            self.assertEqual(selected["state"], "READY")
            self.assertNotIn("try.elevenlabs.io", json.dumps(selected))
            claimed = MODULE.claim(consumed, MODULE.read_json(proposal_path))
            self.assertTrue(claimed["changed"])
            self.assertEqual(claimed["state"], "EFFECT_STARTED")
            self.assertEqual(MODULE.select(proposal_path, consumed)["state"], "RECONCILE")
            posted = MODULE.record(
                consumed, MODULE.read_json(proposal_path), "POSTED",
                "https://x.com/selawmqt/status/123",
            )
            self.assertTrue(posted["changed"])
            self.assertEqual(posted["revenue_credit_state"], "NO_REVENUE_CREDIT_UNTIL_EXACT_AFFILIATE_JOIN")
            self.assertEqual(MODULE.select(proposal_path, consumed)["state"], "ALREADY_CONSUMED")
            self.assertFalse(MODULE.record(
                consumed, MODULE.read_json(proposal_path), "POSTED",
                "https://x.com/selawmqt/status/123",
            )["changed"])

    def test_rejects_query_userinfo_and_second_url(self) -> None:
        base = {
            "receipt_type": "AFFILIATE_REPOST_PROPOSAL",
            "state": "READY_FOR_EXISTING_REPOST_OWNER",
            "proposal_id": "b" * 64,
            "placement_id": "voice-isolator-en-1",
            "language": "en", "disclosure_required": True,
            "tracking_link_state": "NOT_INCLUDED",
            "revenue_credit_state": "NO_REVENUE_CREDIT",
        }
        for url in (
            "https://aniccaai.com/blog/voice-isolator?tag=hidden",
            "https://user@aniccaai.com/blog/voice-isolator",
            "https://aniccaai.com/blog/voice-isolator\nhttps://example.test",
            "https://aniccaai.com/blog/%2e%2e/private",
        ):
            with self.subTest(url=url):
                self.assertFalse(MODULE.valid({**base, "owned_article_url": url}))

    def test_no_effect_terminal_does_not_wedge_the_proposal(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            proposal_path = root / "proposal.json"
            consumed = root / "consumed.jsonl"
            proposal = {
                "receipt_type": "AFFILIATE_REPOST_PROPOSAL",
                "state": "READY_FOR_EXISTING_REPOST_OWNER",
                "proposal_id": "c" * 64,
                "placement_id": "voice-isolator-en-1",
                "owned_article_url": "https://aniccaai.com/blog/voice-isolator",
                "language": "en", "disclosure_required": True,
                "tracking_link_state": "NOT_INCLUDED",
                "revenue_credit_state": "NO_REVENUE_CREDIT",
            }
            proposal_path.write_text(json.dumps(proposal))
            MODULE.claim(consumed, proposal)
            result = MODULE.record(consumed, proposal, "NO_EFFECT", None)
            self.assertTrue(result["changed"])
            self.assertEqual(MODULE.select(proposal_path, consumed)["state"], "ALREADY_CONSUMED")

    def test_unfinished_claim_precedes_newer_latest_proposal(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            proposal_path = root / "proposal.json"
            consumed = root / "consumed.jsonl"
            first = {
                "receipt_type": "AFFILIATE_REPOST_PROPOSAL",
                "state": "READY_FOR_EXISTING_REPOST_OWNER",
                "proposal_id": "d" * 64,
                "placement_id": "voice-isolator-en-1",
                "owned_article_url": "https://aniccaai.com/blog/voice-isolator",
                "language": "en", "disclosure_required": True,
                "tracking_link_state": "NOT_INCLUDED",
                "revenue_credit_state": "NO_REVENUE_CREDIT",
            }
            second = {**first, "proposal_id": "e" * 64,
                      "placement_id": "voice-design-en-1",
                      "owned_article_url": "https://aniccaai.com/blog/voice-design"}
            MODULE.claim(consumed, first)
            proposal_path.write_text(json.dumps(second))
            selected = MODULE.select(proposal_path, consumed)
            self.assertEqual(selected["state"], "RECONCILE")
            self.assertEqual(selected["proposal_id"], first["proposal_id"])
            self.assertEqual(selected["owned_article_url"], first["owned_article_url"])
            proposal_path.unlink()
            self.assertEqual(MODULE.select(proposal_path, consumed)["state"], "RECONCILE")

    def test_legacy_claim_blocks_new_proposal_and_snapshot_drops_extras(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            proposal_path = root / "proposal.json"
            consumed = root / "consumed.jsonl"
            proposal = {
                "receipt_type": "AFFILIATE_REPOST_PROPOSAL",
                "state": "READY_FOR_EXISTING_REPOST_OWNER",
                "proposal_id": "f" * 64,
                "placement_id": "voice-isolator-en-1",
                "owned_article_url": "https://aniccaai.com/blog/voice-isolator",
                "language": "en", "disclosure_required": True,
                "tracking_link_state": "NOT_INCLUDED",
                "revenue_credit_state": "NO_REVENUE_CREDIT",
                "untrusted_tracking_url": "https://example.test/secret",
            }
            proposal_path.write_text(json.dumps(proposal))
            claimed = MODULE.claim(consumed, proposal)
            self.assertNotIn("untrusted_tracking_url", claimed["proposal"])
            consumed.write_text(json.dumps({"proposal_id": "a" * 64, "state": "EFFECT_STARTED"}) + "\n")
            self.assertEqual(MODULE.select(proposal_path, consumed)["state"], "BLOCKED_CONSUMPTION_LEDGER")

    def test_invalid_consumption_ledger_blocks_new_proposal(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            proposal_path = root / "proposal.json"
            consumed = root / "consumed.jsonl"
            proposal_path.write_text(json.dumps({
                "receipt_type": "AFFILIATE_REPOST_PROPOSAL",
                "state": "READY_FOR_EXISTING_REPOST_OWNER",
                "proposal_id": "a" * 64,
                "placement_id": "voice-isolator-en-1",
                "owned_article_url": "https://aniccaai.com/blog/voice-isolator",
                "language": "en", "disclosure_required": True,
                "tracking_link_state": "NOT_INCLUDED",
                "revenue_credit_state": "NO_REVENUE_CREDIT",
            }))
            consumed.write_text("{broken\n")
            self.assertEqual(MODULE.select(proposal_path, consumed)["state"], "BLOCKED_CONSUMPTION_LEDGER")

    def test_unknown_state_or_invalid_timestamp_blocks_new_proposal(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            proposal_path = root / "proposal.json"
            consumed = root / "consumed.jsonl"
            proposal_path.write_text(json.dumps({
                "receipt_type": "AFFILIATE_REPOST_PROPOSAL",
                "state": "READY_FOR_EXISTING_REPOST_OWNER",
                "proposal_id": "a" * 64,
                "placement_id": "voice-isolator-en-1",
                "owned_article_url": "https://aniccaai.com/blog/voice-isolator",
                "language": "en", "disclosure_required": True,
                "tracking_link_state": "NOT_INCLUDED",
                "revenue_credit_state": "NO_REVENUE_CREDIT",
            }))
            for row in (
                {"schema_version": 1, "receipt_type": "X_REPOST_AFFILIATE_PROPOSAL_CONSUMPTION",
                 "proposal_id": "a" * 64, "placement_id": "voice-isolator-en-1",
                 "state": "UNKNOWN", "observed_at": "2026-08-21T00:00:00+00:00"},
                {"schema_version": 1, "receipt_type": "X_REPOST_AFFILIATE_PROPOSAL_CONSUMPTION",
                 "proposal_id": "a" * 64, "placement_id": "voice-isolator-en-1",
                 "state": "EFFECT_STARTED", "observed_at": "not-a-time"},
            ):
                consumed.write_text(json.dumps(row) + "\n")
                self.assertEqual(MODULE.select(proposal_path, consumed)["state"], "BLOCKED_CONSUMPTION_LEDGER")
                consumed.unlink()

    def test_post_text_is_bounded_and_keeps_disclosure_and_url(self) -> None:
        proposal = {
            "receipt_type": "AFFILIATE_REPOST_PROPOSAL",
            "state": "READY_FOR_EXISTING_REPOST_OWNER",
            "proposal_id": "a" * 64,
            "placement_id": "voice-isolator-en-1",
            "owned_article_url": "https://aniccaai.com/blog/voice-isolator",
            "language": "en", "disclosure_required": True,
            "tracking_link_state": "NOT_INCLUDED",
            "revenue_credit_state": "NO_REVENUE_CREDIT",
            "article_title": "Title " * 40,
            "buyer_intent": "Intent " * 30,
        }
        text = MODULE.post_text(proposal)
        self.assertLessEqual(len(text), 280)
        self.assertIn("Affiliate disclosure: I may earn a commission", text)
        self.assertIn("https://aniccaai.com/blog/voice-isolator", text)


if __name__ == "__main__":
    unittest.main()
