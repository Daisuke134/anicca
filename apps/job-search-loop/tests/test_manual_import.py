import hashlib
import inspect
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from job_search_loop.ledger import FenceError, Ledger


class ManualImportTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.ledger = Ledger(Path(self.tempdir.name) / "ledger.sqlite3")

    def tearDown(self):
        self.ledger.close()
        self.tempdir.cleanup()

    def import_manual(self):
        return self.ledger.import_external_application(
            company="Palantir Technologies",
            title="Deployment Strategist - Japan Forward Deployed",
            owner="dais_manual",
            source="gmail",
            source_message_id="gmail-message-1",
            applied_at="2024-12-10T05:36:18+09:00",
            evidence_sha256=hashlib.sha256(b"palantir-confirmation").hexdigest(),
        )

    def test_historical_import_is_submitted_owned_and_idempotent(self):
        self.assertTrue(hasattr(self.ledger, "import_external_application"))
        first = self.import_manual()
        second = self.import_manual()

        self.assertEqual(first["application_id"], second["application_id"])
        self.assertEqual(first["status"], "imported")
        self.assertEqual(second["status"], "already_imported")
        self.assertEqual(self.ledger.current_state(first["application_id"]), "submitted")
        self.assertEqual(self.ledger.application_owner(first["application_id"]), "dais_manual")
        self.assertEqual(len(self.ledger.external_application_imports()), 1)

    def test_import_alias_fences_agent_even_when_url_is_different(self):
        self.assertTrue(hasattr(self.ledger, "import_external_application"))
        receipt = self.import_manual()
        generation_id = self.ledger.record_strategy_generation({"threshold": 75})

        with self.assertRaisesRegex(FenceError, "owned by dais_manual"):
            self.ledger.add_attributed_application(
                "Palantir Technologies",
                "Deployment Strategist - Japan Forward Deployed",
                "https://jobs.lever.co/palantir/future-url",
                strategy_generation_id=generation_id,
                source="official_ats",
                query_family="dream",
                rank_config={"threshold": 75},
                role_family="ai_consulting",
                material_variant="business_en_v2",
                message_variant="none",
                model_route="terra-high",
                prompt_sha256="a" * 64,
                material_sha256="b" * 64,
            )
        self.assertEqual(self.ledger.current_state(receipt["application_id"]), "submitted")

    def test_external_import_rejects_agent_owner(self):
        self.assertTrue(hasattr(self.ledger, "import_external_application"))
        with self.assertRaisesRegex(ValueError, "external owner"):
            self.ledger.import_external_application(
                company="X",
                title="AI Role",
                owner="agent",
                source="gmail",
                source_message_id="message-x",
                applied_at="2026-08-05T00:00:00+09:00",
                evidence_sha256="a" * 64,
            )

    def test_cli_writes_private_secret_free_receipt(self):
        ledger_path = Path(self.tempdir.name) / "cli-ledger.sqlite3"
        output = Path(self.tempdir.name) / "receipt.json"
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "job_search_loop.external_import",
                "import",
                "--ledger",
                str(ledger_path),
                "--company",
                "Palantir Technologies",
                "--title",
                "Deployment Strategist - Japan Forward Deployed",
                "--owner",
                "dais_manual",
                "--source",
                "gmail",
                "--source-message-id",
                "gmail-message-cli",
                "--applied-at",
                "2024-12-10T05:36:18+09:00",
                "--evidence-sha256",
                "a" * 64,
                "--output",
                str(output),
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        receipt = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(receipt["status"], "imported")
        self.assertEqual(receipt["owner"], "dais_manual")
        self.assertNotIn("body", receipt)
        self.assertEqual(output.stat().st_mode & 0o777, 0o600)
