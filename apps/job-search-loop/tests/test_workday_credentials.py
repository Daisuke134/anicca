import json
import os
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from job_search_loop.workday_credentials import (
    WorkdayCredentialError,
    ensure_credentials,
    load_credentials,
    tenant_key,
)


WORKDAY_URL = (
    "https://crowdstrike.wd5.myworkdayjobs.com/crowdstrikecareers/"
    "job/Japan---Tokyo/Regional-Sales-Engineer---AIDR_R29264-1"
)


class WorkdayCredentialTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.profile = self.root / "profile.json"
        self.store = self.root / "private" / "workday-accounts.json"
        self._write_profile("candidate@example.com")

    def tearDown(self):
        self.tempdir.cleanup()

    def _write_profile(self, email):
        self.profile.write_text(
            json.dumps(
                {
                    "version": 1,
                    "candidate": {
                        "name": "Candidate",
                        "application_email": email,
                    },
                    "facts": [
                        {
                            "id": "fact-001",
                            "claim": "Verified claim",
                            "evidence": "Private evidence",
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        os.chmod(self.profile, 0o600)

    def test_official_tenant_key_is_host_and_non_workday_is_rejected(self):
        self.assertEqual(
            tenant_key(WORKDAY_URL),
            "crowdstrike.wd5.myworkdayjobs.com",
        )
        with self.assertRaises(WorkdayCredentialError):
            tenant_key("https://example.com/jobs/42")
        with self.assertRaises(WorkdayCredentialError):
            tenant_key("https://myworkdayjobs.com.evil.example/jobs/42")

    def test_creation_is_private_strong_atomic_and_receipt_is_redacted(self):
        receipt = ensure_credentials(
            job_url=WORKDAY_URL,
            profile_path=self.profile,
            store_path=self.store,
            password_factory=lambda: "Strong-Workday-Password-9!",
        )

        self.assertEqual(
            receipt,
            {
                "version": 1,
                "tenant": "crowdstrike.wd5.myworkdayjobs.com",
                "credential_path": str(self.store.resolve()),
                "created": True,
                "email_sha256": receipt["email_sha256"],
            },
        )
        serialized_receipt = json.dumps(receipt)
        self.assertNotIn("candidate@example.com", serialized_receipt)
        self.assertNotIn("Strong-Workday-Password-9!", serialized_receipt)
        self.assertEqual(stat.S_IMODE(self.store.parent.stat().st_mode), 0o700)
        self.assertEqual(stat.S_IMODE(self.store.stat().st_mode), 0o600)
        self.assertEqual(
            list(self.store.parent.glob(f".{self.store.name}.tmp-*")),
            [],
        )

        account = load_credentials(self.store, WORKDAY_URL)
        self.assertEqual(account["application_email"], "candidate@example.com")
        self.assertEqual(account["password"], "Strong-Workday-Password-9!")

    def test_existing_tenant_is_reused_without_rotation(self):
        ensure_credentials(
            job_url=WORKDAY_URL,
            profile_path=self.profile,
            store_path=self.store,
            password_factory=lambda: "Strong-Workday-Password-9!",
        )

        def must_not_generate():
            self.fail("existing credential must not be rotated")

        receipt = ensure_credentials(
            job_url=WORKDAY_URL,
            profile_path=self.profile,
            store_path=self.store,
            password_factory=must_not_generate,
        )
        self.assertFalse(receipt["created"])
        self.assertEqual(
            load_credentials(self.store, WORKDAY_URL)["password"],
            "Strong-Workday-Password-9!",
        )

    def test_existing_tenant_with_different_profile_email_fails_closed(self):
        ensure_credentials(
            job_url=WORKDAY_URL,
            profile_path=self.profile,
            store_path=self.store,
            password_factory=lambda: "Strong-Workday-Password-9!",
        )
        self._write_profile("different@example.com")
        with self.assertRaisesRegex(
            WorkdayCredentialError, "application email does not match"
        ):
            ensure_credentials(
                job_url=WORKDAY_URL,
                profile_path=self.profile,
                store_path=self.store,
            )

    def test_cli_stdout_contains_receipt_but_no_secret(self):
        env = os.environ.copy()
        env["PYTHONPATH"] = str(Path(__file__).parents[1])
        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "job_search_loop.workday_credentials",
                "--job-url",
                WORKDAY_URL,
                "--profile-path",
                str(self.profile),
                "--store-path",
                str(self.store),
            ],
            check=False,
            capture_output=True,
            text=True,
            env=env,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        receipt = json.loads(completed.stdout)
        account = load_credentials(self.store, WORKDAY_URL)
        self.assertEqual(receipt["tenant"], "crowdstrike.wd5.myworkdayjobs.com")
        self.assertNotIn(account["application_email"], completed.stdout)
        self.assertNotIn(account["password"], completed.stdout)


if __name__ == "__main__":
    unittest.main()
