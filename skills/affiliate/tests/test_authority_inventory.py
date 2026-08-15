from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from typing import Optional


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "skills" / "affiliate" / "scripts" / "authority_inventory.py"


class AuthorityInventoryRedTests(unittest.TestCase):
    def require_script(self) -> Path:
        self.assertTrue(
            SCRIPT.is_file(),
            f"feature missing: expected authority inventory at {SCRIPT}",
        )
        return SCRIPT

    def run_inventory(
        self,
        script: Path,
        request: Path,
        receipt: Path,
        bundle: Optional[Path] = None,
    ) -> subprocess.CompletedProcess[str]:
        command = ["python3", str(script), "--request", str(request)]
        if bundle is not None:
            command.extend(["--bundle", str(bundle)])
        command.extend(["--receipt", str(receipt)])
        return subprocess.run(command, text=True, capture_output=True, check=False)

    def write_json(self, path: Path, value: object) -> None:
        path.write_text(json.dumps(value) + "\n", encoding="utf-8")

    def test_missing_bundle_and_intent_mismatch_are_external_challenges(self) -> None:
        script = self.require_script()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            request = root / "request.json"
            bundle = root / "bundle.json"
            receipt_missing = root / "missing-receipt.json"
            receipt_mismatch = root / "mismatch-receipt.json"
            intent_id = "affiliate-login-001"
            capability = "inbox_otp"
            self.write_json(request, {"intent_id": intent_id, "capability": capability})
            self.write_json(
                bundle,
                {
                    "authorities": [
                        {
                            "intent_id": intent_id,
                            "capability": capability,
                            "secret_ref": "keychain://affiliate/account",
                        }
                    ]
                },
            )

            missing = self.run_inventory(script, request, receipt_missing)
            self.assertEqual(missing.returncode, 0, missing.stderr)
            missing_receipt = json.loads(receipt_missing.read_text(encoding="utf-8"))
            self.assertEqual(missing_receipt["status"], "EXTERNAL_CHALLENGE")
            self.assertEqual(missing_receipt["challenge"], "AUTHORITY_REQUIRED")

            mismatch_request = root / "mismatch-request.json"
            self.write_json(
                mismatch_request,
                {"intent_id": "different-intent", "capability": capability},
            )
            mismatch = self.run_inventory(script, mismatch_request, receipt_mismatch, bundle)
            self.assertEqual(mismatch.returncode, 0, mismatch.stderr)
            mismatch_receipt = json.loads(receipt_mismatch.read_text(encoding="utf-8"))
            self.assertEqual(mismatch_receipt["status"], "EXTERNAL_CHALLENGE")
            self.assertEqual(mismatch_receipt["challenge"], "AUTHORITY_REQUIRED")

    def test_exact_authority_is_scoped_and_typed_challenges_never_bypass(self) -> None:
        script = self.require_script()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            intent_id = "affiliate-login-001"
            capability = "inbox_otp"
            secret = "authority-secret-sentinel"
            bundle = root / "bundle.json"
            self.write_json(
                bundle,
                {
                    "secret_sentinel": secret,
                    "authorities": [
                        {
                            "intent_id": intent_id,
                            "capability": capability,
                            "secret_ref": "keychain://affiliate/account",
                            "secret_sentinel": secret,
                        }
                    ],
                },
            )

            exact_request = root / "exact-request.json"
            exact_receipt = root / "exact-receipt.json"
            self.write_json(
                exact_request,
                {"intent_id": intent_id, "capability": capability, "secret_sentinel": secret},
            )
            exact = self.run_inventory(script, exact_request, exact_receipt, bundle)
            self.assertEqual(exact.returncode, 0, exact.stderr)
            authorized = json.loads(exact_receipt.read_text(encoding="utf-8"))
            self.assertEqual(authorized["status"], "REFERENCE_BOUND")
            self.assertEqual(authorized["intent_id"], intent_id)
            self.assertEqual(authorized["capability"], capability)
            self.assertEqual(authorized["secret_ref"], "keychain://affiliate/account")

            captcha_request = root / "reused-captcha-request.json"
            self.write_json(
                captcha_request,
                {
                    "intent_id": intent_id,
                    "capability": capability,
                    "external_challenge": "CAPTCHA",
                },
            )
            replaced = self.run_inventory(script, captcha_request, exact_receipt, bundle)
            self.assertEqual(replaced.returncode, 0, replaced.stderr)
            replaced_receipt = json.loads(exact_receipt.read_text(encoding="utf-8"))
            self.assertEqual(replaced_receipt["status"], "EXTERNAL_CHALLENGE")
            self.assertEqual(replaced_receipt["challenge"], "CAPTCHA")
            self.assertNotIn("secret_ref", replaced_receipt)

            malformed_challenge_bundle = root / "malformed-challenge-bundle.json"
            self.write_json(
                malformed_challenge_bundle,
                {
                    "authorities": [
                        {
                            "intent_id": intent_id,
                            "capability": capability,
                            "secret_ref": "keychain://affiliate/account?token=" + secret,
                        }
                    ]
                },
            )
            malformed_challenge = self.run_inventory(
                script, captcha_request, exact_receipt, malformed_challenge_bundle
            )
            self.assertEqual(malformed_challenge.returncode, 0, malformed_challenge.stderr)
            malformed_challenge_receipt = json.loads(
                exact_receipt.read_text(encoding="utf-8")
            )
            self.assertEqual(malformed_challenge_receipt["status"], "EXTERNAL_CHALLENGE")
            self.assertEqual(malformed_challenge_receipt["challenge"], "CAPTCHA")
            self.assertNotIn("secret_ref", malformed_challenge_receipt)
            self.assertNotIn(secret, malformed_challenge.stdout)
            self.assertNotIn(secret, malformed_challenge.stderr)

            other_request = root / "other-request.json"
            other_receipt = root / "other-receipt.json"
            self.write_json(
                other_request,
                {"intent_id": "other-intent", "capability": capability},
            )
            other = self.run_inventory(script, other_request, other_receipt, bundle)
            self.assertEqual(other.returncode, 0, other.stderr)
            self.assertEqual(
                json.loads(other_receipt.read_text(encoding="utf-8"))["status"],
                "EXTERNAL_CHALLENGE",
            )

            for challenge in ("CAPTCHA", "KYC", "CONTRACT"):
                with self.subTest(challenge=challenge):
                    request = root / f"{challenge.lower()}-request.json"
                    receipt = root / f"{challenge.lower()}-receipt.json"
                    self.write_json(
                        request,
                        {
                            "intent_id": intent_id,
                            "capability": capability,
                            "external_challenge": challenge,
                            "secret_sentinel": secret,
                        },
                    )
                    result = self.run_inventory(script, request, receipt, bundle)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    challenge_receipt = json.loads(receipt.read_text(encoding="utf-8"))
                    self.assertEqual(challenge_receipt["status"], "EXTERNAL_CHALLENGE")
                    self.assertEqual(challenge_receipt["challenge"], challenge)

            malformed_bundle = root / "malformed-bundle.json"
            malformed_receipt = root / "malformed-receipt.json"
            self.write_json(
                malformed_bundle,
                {
                    "authorities": [
                        {
                            "intent_id": intent_id,
                            "capability": capability,
                            "secret_ref": "keychain://affiliate/account?token=" + secret,
                        }
                    ]
                },
            )
            malformed = self.run_inventory(script, exact_request, malformed_receipt, malformed_bundle)
            self.assertNotEqual(malformed.returncode, 0)
            self.assertEqual(
                json.loads(malformed_receipt.read_text(encoding="utf-8"))["status"],
                "IN_PROGRESS",
            )
            self.assertNotIn(secret, malformed.stdout)
            self.assertNotIn(secret, malformed.stderr)

            for output in (exact.stdout, exact.stderr, other.stdout, other.stderr):
                self.assertNotIn(secret, output)
            for path in root.glob("*-receipt.json"):
                self.assertNotIn(secret, path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
