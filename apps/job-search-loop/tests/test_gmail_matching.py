import json
import tempfile
import unittest
from pathlib import Path

from job_search_loop.gmail_matching import match_gmail_event, validate_match_result
from job_search_loop.ledger import FenceError, Ledger


def event(**overrides):
    value = {
        "message_id": "message-1",
        "thread_id": "thread-1",
        "received_at": "2030-01-01T00:00:00+00:00",
        "evidence_sha256": "a" * 64,
        "company": {"value": "Example AI", "source_span": "From Example AI recruiting"},
        "title": {"value": "Applied AI Engineer", "source_span": "Applied AI Engineer application update"},
        "posting_url": None,
    }
    value.update(overrides)
    return value


class GmailMatchingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.ledger = Ledger(Path(self.temp.name) / "ledger.sqlite3")

    def tearDown(self):
        self.ledger.close()
        self.temp.cleanup()

    def test_exact_company_and_title_uniquely_bind_message(self):
        application_id = self.ledger.add_application("Example AI", "Applied AI Engineer", "https://jobs.example/one")
        result = match_gmail_event(self.ledger, event())
        self.assertEqual(result, {"status": "matched", "application_id": application_id})
        row = self.ledger.connection.execute("SELECT * FROM gmail_application_matches").fetchone()
        self.assertEqual(row["message_id"], "message-1")
        self.assertEqual(row["application_id"], application_id)

    def test_same_company_title_on_two_postings_is_ambiguous_and_records_nothing(self):
        self.ledger.add_application("Example AI", "Applied AI Engineer", "https://jobs.example/one")
        self.ledger.add_application("Example AI", "Applied AI Engineer", "https://jobs.example/two")
        self.assertEqual(match_gmail_event(self.ledger, event()), {"status": "ambiguous"})
        self.assertEqual(self.ledger.connection.execute("SELECT COUNT(*) FROM gmail_application_matches").fetchone()[0], 0)

    def test_exact_url_with_conflicting_title_is_no_match(self):
        self.ledger.add_application("Example AI", "Applied AI Engineer", "https://jobs.example/one")
        result = match_gmail_event(self.ledger, event(
            title={"value": "Different Role", "source_span": "Different Role update"},
            posting_url={"value": "https://jobs.example/one", "source_span": "Apply at https://jobs.example/one"},
        ))
        self.assertEqual(result, {"status": "no_match"})

    def test_insufficient_identifier_or_unverbatim_span_records_nothing(self):
        self.ledger.add_application("Example AI", "Applied AI Engineer", "https://jobs.example/one")
        self.assertEqual(match_gmail_event(self.ledger, event(title=None)), {"status": "insufficient_evidence"})
        with self.assertRaisesRegex(ValueError, "source span"):
            match_gmail_event(self.ledger, event(company={"value": "Example AI", "source_span": "unrelated"}))
        self.assertEqual(self.ledger.connection.execute("SELECT COUNT(*) FROM gmail_application_matches").fetchone()[0], 0)

    def test_exact_replay_is_idempotent_but_rebinding_message_is_fenced(self):
        first = self.ledger.add_application("Example AI", "Applied AI Engineer", "https://jobs.example/one")
        self.assertEqual(match_gmail_event(self.ledger, event())["application_id"], first)
        self.assertEqual(match_gmail_event(self.ledger, event()), {"status": "matched", "application_id": first})
        with self.assertRaises(FenceError):
            match_gmail_event(self.ledger, event(
                evidence_sha256="b" * 64,
                company={"value": "Other AI", "source_span": "Other AI recruiting"},
                title={"value": "AI Product Manager", "source_span": "AI Product Manager update"},
            ))

    def _write_validation_files(self, request):
        candidates = Path(self.temp.name) / "candidates.json"
        result = Path(self.temp.name) / "result.json"
        source = event()
        candidates.write_text(json.dumps({"events": [{
            key: source[key] for key in (
                "message_id", "thread_id", "received_at", "evidence_sha256"
            )
        }]}), encoding="utf-8")
        result.write_text(json.dumps({
            "processed_message_ids": ["message-1"],
            "gmail_matches": [request],
        }), encoding="utf-8")
        return candidates, result

    def test_result_validator_persists_only_a_recomputed_exact_match(self):
        application_id = self.ledger.add_application(
            "Example AI", "Applied AI Engineer", "https://jobs.example/one"
        )
        request = event(status="matched", application_id=application_id)
        candidates, result = self._write_validation_files(request)
        receipt = validate_match_result(
            ledger_path=Path(self.temp.name) / "ledger.sqlite3",
            candidates_path=candidates,
            result_path=result,
        )
        self.assertEqual(receipt, {"validated_count": 1, "matched_count": 1})
        self.assertEqual(self.ledger.connection.execute(
            "SELECT COUNT(*) FROM gmail_application_matches"
        ).fetchone()[0], 1)

    def test_forged_model_claim_is_rejected_without_persistence(self):
        self.ledger.add_application(
            "Example AI", "Applied AI Engineer", "https://jobs.example/one"
        )
        request = event(status="no_match")
        candidates, result = self._write_validation_files(request)
        with self.assertRaisesRegex(ValueError, "differs from deterministic"):
            validate_match_result(
                ledger_path=Path(self.temp.name) / "ledger.sqlite3",
                candidates_path=candidates,
                result_path=result,
            )
        self.assertEqual(self.ledger.connection.execute(
            "SELECT COUNT(*) FROM gmail_application_matches"
        ).fetchone()[0], 0)


if __name__ == "__main__":
    unittest.main()
