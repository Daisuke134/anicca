import tempfile
import unittest
from pathlib import Path

from job_search_loop.mercor_human_gate import HumanGateStore


class MercorHumanGateTests(unittest.TestCase):
    def test_gate_is_idempotent_and_pending_is_replayable(self):
        with tempfile.TemporaryDirectory() as directory:
            store = HumanGateStore(Path(directory) / "human-gates.jsonl")
            first = store.record(
                run_id="run-1",
                reason="assessment_required",
                evidence_ref="evidence://assessment",
            )
            duplicate = store.record(
                run_id="run-1",
                reason="assessment_required",
                evidence_ref="evidence://assessment",
            )
            self.assertEqual(first, duplicate)
            self.assertEqual(len(store.pending()), 1)
            self.assertEqual(store.pending()[0]["reason"], "assessment_required")
            self.assertEqual(store.path.stat().st_mode & 0o777, 0o600)

    def test_different_reason_creates_distinct_gate(self):
        with tempfile.TemporaryDirectory() as directory:
            store = HumanGateStore(Path(directory) / "human-gates.jsonl")
            first = store.record(run_id="run-1", reason="assessment_required", evidence_ref="evidence://a")
            second = store.record(run_id="run-1", reason="missing_fact", evidence_ref="evidence://b")
            self.assertNotEqual(first["gate_id"], second["gate_id"])
            self.assertEqual(len(store.pending()), 2)

    def test_project_thor_wording_drift_does_not_duplicate_pending_gate(self):
        with tempfile.TemporaryDirectory() as directory:
            store = HumanGateStore(Path(directory) / "human-gates.jsonl")
            first = store.record(
                run_id="run-1",
                reason="list_abc: Project Thor Assessment is the next required step; it was not started.",
                evidence_ref="https://work.mercor.com/explore?listingId=list_abc",
            )
            second = store.record(
                run_id="run-2",
                reason="Project Thor Assessment required for Generalist (Macbook User)",
                evidence_ref="https://work.mercor.com/explore?listingId=list_other",
            )
            self.assertEqual(first["gate_id"], second["gate_id"])
            self.assertEqual(len(store.pending()), 1)

    def test_finance_interview_wording_drift_does_not_duplicate_pending_gate(self):
        with tempfile.TemporaryDirectory() as directory:
            store = HumanGateStore(Path(directory) / "human-gates.jsonl")
            first = store.record(
                run_id="run-1",
                reason="Corporate Development Expert: Finance Interview is the next required step.",
                evidence_ref="https://work.mercor.com/explore?listingId=list_a",
            )
            second = store.record(
                run_id="run-2",
                reason="Finance Interview required for Corporate Development Expert",
                evidence_ref="https://work.mercor.com/explore?listingId=list_b",
            )
            self.assertEqual(first["gate_id"], second["gate_id"])
            self.assertEqual(len(store.pending()), 1)


if __name__ == "__main__":
    unittest.main()
