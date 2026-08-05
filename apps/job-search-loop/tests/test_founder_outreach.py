import hashlib
import tempfile
import unittest
from pathlib import Path

from job_search_loop.ledger import Ledger


class FounderOutreachTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.ledger = Ledger(Path(self.tempdir.name) / "ledger.sqlite3")

    def tearDown(self):
        self.ledger.close()
        self.tempdir.cleanup()

    def test_founder_funnel_is_independent_from_applications(self):
        self.assertTrue(hasattr(self.ledger, "add_founder_outreach_target"))
        before = self.ledger.connection.execute("SELECT COUNT(*) FROM applications").fetchone()[0]
        target_id = self.ledger.add_founder_outreach_target(
            company="BlockRunAI",
            relationship_url="https://github.com/BlockRunAI/blockrun-mcp",
            evidence_source="github",
            evidence_id="repo:BlockRunAI/blockrun-mcp",
            evidence_sha256=hashlib.sha256(b"repo research").hexdigest(),
        )
        after = self.ledger.connection.execute("SELECT COUNT(*) FROM applications").fetchone()[0]

        self.assertEqual(before, after)
        self.assertEqual(self.ledger.founder_outreach_status(target_id)["current_state"], "researched")

    def test_historical_evidence_advances_to_replied_idempotently(self):
        self.assertTrue(hasattr(self.ledger, "add_founder_outreach_target"))
        target_id = self.ledger.add_founder_outreach_target(
            company="BlockRunAI",
            relationship_url="https://github.com/BlockRunAI/blockrun-mcp",
            evidence_source="github",
            evidence_id="repo:BlockRunAI/blockrun-mcp",
            evidence_sha256="a" * 64,
        )
        transitions = [
            ("contribution_ready", "github-pr-82-created", "b" * 64),
            ("outreach_sent", "github-pr-82-opened", "c" * 64),
            ("replied", "github-comment-5174816350", "d" * 64),
        ]
        event_ids = []
        for state, evidence_id, digest in transitions:
            event_ids.append(
                self.ledger.transition_founder_outreach(
                    target_id=target_id,
                    to_state=state,
                    evidence_source="github",
                    evidence_id=evidence_id,
                    evidence_sha256=digest,
                )
            )
        replay = self.ledger.transition_founder_outreach(
            target_id=target_id,
            to_state="replied",
            evidence_source="github",
            evidence_id="github-comment-5174816350",
            evidence_sha256="d" * 64,
        )

        self.assertEqual(replay, event_ids[-1])
        self.assertEqual(self.ledger.founder_outreach_status(target_id)["current_state"], "replied")
        self.assertEqual(len(self.ledger.founder_outreach_events(target_id)), 4)

    def test_invalid_state_jump_is_rejected(self):
        self.assertTrue(hasattr(self.ledger, "add_founder_outreach_target"))
        target_id = self.ledger.add_founder_outreach_target(
            company="BlockRunAI",
            relationship_url="https://github.com/BlockRunAI/blockrun-mcp",
            evidence_source="github",
            evidence_id="repo",
            evidence_sha256="a" * 64,
        )
        with self.assertRaisesRegex(ValueError, "invalid founder outreach transition"):
            self.ledger.transition_founder_outreach(
                target_id=target_id,
                to_state="employment",
                evidence_source="github",
                evidence_id="imagined-offer",
                evidence_sha256="e" * 64,
            )
