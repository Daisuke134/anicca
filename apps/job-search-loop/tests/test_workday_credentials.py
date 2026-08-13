import json
import hashlib
import os
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from job_search_loop.workday_credentials import (
    WorkdayCredentialError,
    _advance_application_entry,
    ensure_credentials,
    fill_account_creation,
    known_tenants,
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

    def test_advances_workday_apply_and_manual_entry_without_sso(self):
        clicked = []

        class Locator:
            def __init__(self, name): self.name = name
            def count(self): return 1
            def is_visible(self): return True
            def click(self, **_kwargs): clicked.append(self.name)

        class Page:
            def locator(self, selector): return Locator(selector)
            def wait_for_timeout(self, _milliseconds): pass

        actions = _advance_application_entry(Page())

        self.assertEqual(actions, 2)
        self.assertIn("jobPostingApplyButton", clicked[0])
        self.assertIn("applyManually", clicked[1])
        self.assertTrue(all("sso" not in value.casefold() for value in clicked))

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
        self.assertEqual(
            known_tenants(self.store),
            ["crowdstrike.wd5.myworkdayjobs.com"],
        )

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

    def test_fill_account_uses_only_registered_page_and_returns_no_secret(self):
        target = "owned-target"
        lease = "lease-1"

        class Locator:
            def __init__(self, kind):
                self.kind = kind
                self.value = ""
                self.checked = False
                self.clicked = False

            def count(self): return 1
            def fill(self, value): self.value = value
            def input_value(self): return self.value
            def is_checked(self): return self.checked
            def check(self, force=False): self.checked = True
            def click(self, **kwargs): self.clicked = True

        controls = {
            name: Locator(name)
            for name in (
                "email",
                "password",
                "verifyPassword",
                "createAccountCheckbox",
                "createAccountSubmitButton",
            )
        }

        class Page:
            url = WORKDAY_URL

            def locator(self, selector):
                name = selector.split('"')[1]
                return controls[name]

            def wait_for_timeout(self, _milliseconds): pass

        page = Page()

        class Session:
            def send(self, _method): return {"targetInfo": {"targetId": target}}

        class Context:
            pages = [page]
            def new_cdp_session(self, _page): return Session()

        class Chromium:
            def connect_over_cdp(self, _endpoint):
                return type("Browser", (), {"contexts": [Context()]})()

        owner = {
            "status": "ready",
            "endpoint": "http://127.0.0.1:9222",
            "lease_id": lease,
            "fence": 3,
        }
        ownership = {
            "version": 1,
            "lease_sha256": hashlib.sha256(lease.encode()).hexdigest(),
            "fence": 3,
            "baseline_sha256": [],
            "created_sha256": [hashlib.sha256(target.encode()).hexdigest()],
        }
        receipt = fill_account_creation(
            job_url=WORKDAY_URL,
            profile_path=self.profile,
            store_path=self.store,
            owner_receipt=owner,
            ownership_receipt=ownership,
            owned_page={"target_id": target, "lease_id": lease, "fence": 3},
            playwright=type("Playwright", (), {"chromium": Chromium()})(),
        )
        account = load_credentials(self.store, WORKDAY_URL)

        self.assertEqual(receipt["status"], "account_creation_clicked")
        self.assertFalse(receipt["secret_values_returned"])
        self.assertNotIn(account["application_email"], json.dumps(receipt))
        self.assertNotIn(account["password"], json.dumps(receipt))
        self.assertEqual(controls["email"].value, account["application_email"])
        self.assertEqual(controls["password"].value, account["password"])
        self.assertTrue(controls["createAccountCheckbox"].checked)
        self.assertTrue(controls["createAccountSubmitButton"].clicked)

        page.url = "https://crowdstrike.wd5.myworkdayjobs.com/login"
        controls.pop("verifyPassword")
        controls.pop("createAccountCheckbox")
        controls.pop("createAccountSubmitButton")
        controls["signInSubmitButton"] = Locator("signInSubmitButton")

        def login_locator(selector):
            if "signInSubmitButton" in selector or 'button[type="submit"]' in selector:
                return controls["signInSubmitButton"]
            name = selector.split('"')[1]
            return controls.get(name, type("Missing", (), {"count": lambda self: 0})())

        page.locator = login_locator
        login_receipt = fill_account_creation(
            job_url=WORKDAY_URL,
            profile_path=self.profile,
            store_path=self.store,
            owner_receipt=owner,
            ownership_receipt=ownership,
            owned_page={"target_id": target, "lease_id": lease, "fence": 3},
            playwright=type("Playwright", (), {"chromium": Chromium()})(),
        )

        self.assertEqual(login_receipt["status"], "sign_in_clicked")
        self.assertEqual(login_receipt["browser_action_count"], 3)
        self.assertFalse(login_receipt["secret_values_returned"])
        self.assertNotIn(account["application_email"], json.dumps(login_receipt))
        self.assertNotIn(account["password"], json.dumps(login_receipt))
        self.assertTrue(controls["signInSubmitButton"].clicked)


if __name__ == "__main__":
    unittest.main()
