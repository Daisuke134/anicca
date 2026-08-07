import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path

from job_search_loop.ledger import Ledger
from job_search_loop.prefill_prepare import prepare_prefill


class PrefillPrepareTests(unittest.TestCase):
    def test_materializes_private_artifacts_without_claiming_submit(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            resume = root / "resume.pdf"
            posting = root / "inspect.json"
            answers = root / "answers.json"
            resume.write_bytes(b"%PDF-1.4 grounded resume")
            posting.write_text(json.dumps({"status": "inspected", "fields": [{}]}) + "\n")
            answers.write_text(json.dumps({
                "status": "ready",
                "missing_required": [],
                "answers": {"Legal Name": {"answer": "Candidate", "fact_ids": ["profile.name"]}},
            }) + "\n")
            for path in (resume, posting, answers):
                os.chmod(path, 0o600)
            database = root / "ledger.sqlite3"

            result = prepare_prefill(
                ledger_path=database,
                company="Example AI",
                title="Solutions Engineer",
                official_url="https://jobs.ashbyhq.com/example/role",
                resume_path=resume,
                posting_path=posting,
                answers_path=answers,
            )

            ledger = Ledger(database)
            try:
                self.assertEqual(ledger.current_state(result["application_id"]), "materials_ready")
                self.assertEqual(
                    [item["kind"] for item in ledger.application_artifact_chain(result["application_id"])],
                    ["posting", "resume_draft", "answers_draft"],
                )
                self.assertEqual(ledger.submission_attempts(result["application_id"]), [])
            finally:
                ledger.close()
            self.assertEqual(result["status"], "prefill_materials_ready")
            self.assertEqual(result["submit_intent_id"], None)
            self.assertEqual(result["answers_sha256"], hashlib.sha256(answers.read_bytes()).hexdigest())


if __name__ == "__main__":
    unittest.main()
