from __future__ import annotations

import importlib.util
import json
import re
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "affiliate_proposal.py"
SPEC = importlib.util.spec_from_file_location("affiliate_proposal", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class AffiliateProposalTests(unittest.TestCase):
    def test_claimed_distribution_job_renders_one_safe_idempotent_payload(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            queue, claims = root / "jobs.jsonl", root / "claims.jsonl"
            payloads = root / "payloads"
            job = {
                "schema_version": 1, "receipt_type": "AFFILIATE_X_DISTRIBUTION_JOB",
                "state": "QUEUED", "job_id": "1" * 64,
                "effect_identity": "2" * 64,
                "placement_id": "elevenlabs-discovered-caption-generator-en-1",
                "owned_article_url": "https://aniccaai.com/blog/caption-generator",
                "content_sha256": "3" * 64,
                "experiment_lineage": {"kind": "BASE", "decision_id": None,
                                       "control_placement_id": None},
                "target_x_account": "selawmqt",
                "cadence_class": "AFFILIATE_MONETIZATION",
                "policy_sha256": "4" * 64, "source_set_sha256": "5" * 64,
                "created_at": "2026-08-24T00:00:00+00:00",
                "private_tracking_url_state": "NOT_INCLUDED",
                "revenue_credit_state": "NO_REVENUE_CREDIT",
            }
            queue.write_text(json.dumps(job) + "\n")
            MODULE.claim_next_job(queue, claims)

            first = MODULE.render_claimed_job(claims, payloads)
            second = MODULE.render_claimed_job(claims, payloads)

            self.assertEqual(first["state"], "PAYLOAD_READY")
            self.assertTrue(first["changed"])
            self.assertFalse(second["changed"])
            self.assertEqual(first["text_sha256"], second["text_sha256"])
            self.assertEqual(first["text"].count(job["owned_article_url"]), 1)
            self.assertIn("Affiliate disclosure:", first["text"])
            self.assertNotIn("try.elevenlabs.io", json.dumps(first))
            self.assertEqual(first["private_tracking_url_state"], "NOT_INCLUDED")
            self.assertEqual(len(list(payloads.glob("*.json"))), 1)
            weighted = len(re.sub(r"https?://\S+", "x" * 23, first["text"]))
            self.assertLessEqual(weighted, 280)

    def test_owner_renders_claimed_job_before_legacy_proposal(self) -> None:
        shell = (SCRIPT.parents[1] / "x-repost-cli.sh").read_text()
        render = shell.index("--render-claimed-job")
        legacy = shell.index("--proposal \"$AFFILIATE_PROPOSAL\"")
        self.assertLess(render, legacy)
        self.assertIn("affiliate distribution payload ready", shell)

    def test_owner_claims_distribution_job_before_legacy_proposal(self) -> None:
        shell = (SCRIPT.parents[1] / "x-repost-cli.sh").read_text()
        claim = shell.index("--claim-next-job")
        legacy = shell.index("--proposal \"$AFFILIATE_PROPOSAL\"")
        self.assertLess(claim, legacy)
        self.assertIn("affiliate distribution job claimed", shell)

    def test_oldest_distribution_job_is_claimed_once_across_processes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            queue = root / "jobs.jsonl"
            claims = root / "claims.jsonl"

            def job(job_id: str, created_at: str) -> dict:
                return {
                    "schema_version": 1,
                    "receipt_type": "AFFILIATE_X_DISTRIBUTION_JOB",
                    "state": "QUEUED",
                    "job_id": job_id,
                    "effect_identity": ("a" if job_id[0] == "1" else "b") * 64,
                    "placement_id": "elevenlabs-discovered-caption-generator-en-1",
                    "owned_article_url": "https://aniccaai.com/blog/caption-generator",
                    "content_sha256": "c" * 64,
                    "experiment_lineage": {
                        "kind": "BASE", "decision_id": None,
                        "control_placement_id": None,
                    },
                    "target_x_account": "selawmqt",
                    "cadence_class": "AFFILIATE_MONETIZATION",
                    "policy_sha256": "d" * 64,
                    "source_set_sha256": "e" * 64,
                    "created_at": created_at,
                    "private_tracking_url_state": "NOT_INCLUDED",
                    "revenue_credit_state": "NO_REVENUE_CREDIT",
                }

            older = job("1" * 64, "2026-08-23T00:00:00+00:00")
            newer = job("2" * 64, "2026-08-24T00:00:00+00:00")
            queue.write_text(json.dumps(newer) + "\n" + json.dumps(older) + "\n")
            command = [
                sys.executable, str(SCRIPT), "--job-queue", str(queue),
                "--job-claims", str(claims), "--claim-next-job",
            ]
            processes = [
                subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                for _ in range(2)
            ]
            results = [process.communicate(timeout=10) for process in processes]

            self.assertEqual([process.returncode for process in processes], [0, 0])
            values = [json.loads(stdout) for stdout, _ in results]
            self.assertEqual({value["job_id"] for value in values}, {older["job_id"]})
            self.assertEqual(sorted(value["changed"] for value in values), [False, True])
            claim_rows = [json.loads(line) for line in claims.read_text().splitlines()]
            self.assertEqual(len(claim_rows), 1)
            self.assertEqual(claim_rows[0]["state"], "EFFECT_STARTED")
            self.assertEqual(claim_rows[0]["job"], older)

    def test_distribution_job_consumer_rejects_extra_private_field(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            queue, claims = root / "jobs.jsonl", root / "claims.jsonl"
            queue.write_text(json.dumps({
                "schema_version": 1,
                "receipt_type": "AFFILIATE_X_DISTRIBUTION_JOB",
                "state": "QUEUED",
                "job_id": "1" * 64,
                "effect_identity": "2" * 64,
                "placement_id": "elevenlabs-discovered-caption-generator-en-1",
                "owned_article_url": "https://aniccaai.com/blog/caption-generator",
                "content_sha256": "3" * 64,
                "experiment_lineage": {"kind": "BASE", "decision_id": None,
                                       "control_placement_id": None},
                "target_x_account": "selawmqt",
                "cadence_class": "AFFILIATE_MONETIZATION",
                "policy_sha256": "4" * 64,
                "source_set_sha256": "5" * 64,
                "created_at": "2026-08-24T00:00:00+00:00",
                "private_tracking_url_state": "NOT_INCLUDED",
                "revenue_credit_state": "NO_REVENUE_CREDIT",
                "private_tracking_url": "https://try.elevenlabs.io/private",
            }) + "\n")
            result = subprocess.run([
                sys.executable, str(SCRIPT), "--job-queue", str(queue),
                "--job-claims", str(claims), "--claim-next-job",
            ], capture_output=True, text=True, check=False)
            self.assertEqual(result.returncode, 2)
            self.assertFalse(claims.exists())

    def test_new_ready_proposal_precedes_older_terminal_readback(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            proposal_path, consumed = root / "proposal.json", root / "consumed.jsonl"
            old = {
                "receipt_type": "AFFILIATE_REPOST_PROPOSAL",
                "state": "READY_FOR_EXISTING_REPOST_OWNER",
                "proposal_id": "8" * 64,
                "placement_id": "subtitle-en-1",
                "owned_article_url": "https://aniccaai.com/blog/subtitle",
                "language": "en", "disclosure_required": True,
                "tracking_link_state": "NOT_INCLUDED",
                "revenue_credit_state": "NO_REVENUE_CREDIT",
            }
            current = {**old, "proposal_id": "7" * 64,
                       "placement_id": "voice-cloning-en-1",
                       "owned_article_url": "https://aniccaai.com/blog/voice-cloning"}
            MODULE.claim(consumed, old)
            MODULE.record(consumed, old, "UNVERIFIED", None)
            proposal_path.write_text(json.dumps(current))
            selected = MODULE.select(proposal_path, consumed)
            self.assertEqual(selected["state"], "READY")
            self.assertEqual(selected["proposal_id"], current["proposal_id"])

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

    def test_old_unverified_does_not_starve_new_acquisition_work(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            proposal_path = root / "missing.json"
            consumed = root / "consumed.jsonl"
            proposal = {
                "receipt_type": "AFFILIATE_REPOST_PROPOSAL",
                "state": "READY_FOR_EXISTING_REPOST_OWNER",
                "proposal_id": "8" * 64,
                "placement_id": "subtitle-en-1",
                "owned_article_url": "https://aniccaai.com/blog/subtitle",
                "language": "en", "disclosure_required": True,
                "tracking_link_state": "NOT_INCLUDED",
                "revenue_credit_state": "NO_REVENUE_CREDIT",
            }
            old = (datetime.now(timezone.utc) - timedelta(hours=7)).isoformat()
            consumed.write_text(
                json.dumps({"schema_version": 1,
                            "receipt_type": "X_REPOST_AFFILIATE_PROPOSAL_CONSUMPTION",
                            "proposal_id": proposal["proposal_id"],
                            "placement_id": proposal["placement_id"],
                            "proposal": proposal, "state": "EFFECT_STARTED",
                            "observed_at": old}) + "\n" +
                json.dumps({"schema_version": 1,
                            "receipt_type": "X_REPOST_AFFILIATE_PROPOSAL_CONSUMPTION",
                            "proposal_id": proposal["proposal_id"],
                            "placement_id": proposal["placement_id"],
                            "state": "UNVERIFIED", "observed_at": old}) + "\n"
            )
            self.assertEqual(MODULE.select(proposal_path, consumed)["state"], "NO_PROPOSAL")

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
        weighted = len(re.sub(r"https?://\S+", "x" * 23, text))
        self.assertLessEqual(weighted, 280)
        self.assertIn("Affiliate disclosure: I may earn a commission", text)
        self.assertIn("https://aniccaai.com/blog/voice-isolator", text)

    def test_post_text_uses_x_transformed_url_length(self) -> None:
        proposal = {
            "receipt_type": "AFFILIATE_REPOST_PROPOSAL",
            "state": "READY_FOR_EXISTING_REPOST_OWNER",
            "proposal_id": "b" * 64,
            "placement_id": "realtime-speech-to-text-en-1",
            "owned_article_url": "https://aniccaai.com/blog/elevenlabs-realtime-speech-to-text-for-creators",
            "language": "en", "disclosure_required": True,
            "tracking_link_state": "NOT_INCLUDED",
            "revenue_credit_state": "NO_REVENUE_CREDIT",
            "article_title": "Is ElevenLabs Scribe v2 Realtime a Fit for Your Live Transcription Build?",
            "buyer_intent": "Creators evaluating ElevenLabs Realtime Speech To Text before paying",
        }
        text = MODULE.post_text(proposal)
        self.assertGreater(len(text), 280)
        self.assertLessEqual(len(re.sub(r"https?://\S+", "x" * 23, text)), 280)
        self.assertIn(proposal["owned_article_url"], text)

    def test_post_text_uses_complete_sentences_instead_of_sliced_fields(self) -> None:
        proposal = {
            "receipt_type": "AFFILIATE_REPOST_PROPOSAL",
            "state": "READY_FOR_EXISTING_REPOST_OWNER",
            "proposal_id": "c" * 64,
            "placement_id": "youtube-transcript-generator-en-1",
            "owned_article_url": "https://aniccaai.com/blog/youtube-transcript-generator",
            "language": "en", "disclosure_required": True,
            "tracking_link_state": "NOT_INCLUDED",
            "revenue_credit_state": "NO_REVENUE_CREDIT",
            "article_title": "Is ElevenLabs' YouTube Transcript Generator a Fit for Your Workflow?",
            "buyer_intent": "Creators evaluating ElevenLabs Youtube Transcript Generator before paying",
        }
        text = MODULE.post_text(proposal)
        self.assertIn("Considering ElevenLabs Youtube Transcript Generator?", text)
        self.assertIn("Use this decision checklist to compare the trade-offs.", text)
        self.assertNotIn("Youtube T\n", text)
        self.assertNotIn("Genera\n", text)


if __name__ == "__main__":
    unittest.main()
