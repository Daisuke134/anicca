import json
import tempfile
import unittest
from pathlib import Path

from job_search_loop.profile_privacy import ProfileLeakError, scan_provider_log


class ProfilePrivacyTests(unittest.TestCase):
    def test_sensitive_profile_values_fail_without_copying_values_to_receipt(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            profile = root / "profile.json"
            profile.write_text(
                json.dumps(
                    {
                        "candidate": {
                            "application_email": "private@example.test",
                            "phone": "09000000000",
                            "date_of_birth": "2000-01-02",
                            "mailing_address": {"address_line_1": "Private Street 1"},
                        }
                    }
                ),
                encoding="utf-8",
            )
            log = root / "stdout.log"
            log.write_text("tool output private@example.test", encoding="utf-8")
            receipt = root / "receipt.json"

            with self.assertRaises(ProfileLeakError):
                scan_provider_log(profile_path=profile, log_path=log, receipt_path=receipt)
            encoded = receipt.read_text(encoding="utf-8")
            self.assertIn("application_email", encoded)
            self.assertNotIn("private@example.test", encoded)
            self.assertEqual(receipt.stat().st_mode & 0o777, 0o600)

    def test_clean_log_passes_with_content_addressed_receipt(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            profile = root / "profile.json"
            profile.write_text(
                json.dumps({"candidate": {"application_email": "private@example.test"}}),
                encoding="utf-8",
            )
            log = root / "stdout.log"
            log.write_text("no private values", encoding="utf-8")
            receipt = root / "receipt.json"
            value = scan_provider_log(
                profile_path=profile, log_path=log, receipt_path=receipt
            )
            self.assertEqual(value["status"], "clean")
            self.assertEqual(len(value["log_sha256"]), 64)

    def test_public_job_location_does_not_match_mailing_address_geography(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            profile = root / "profile.json"
            profile.write_text(
                json.dumps(
                    {
                        "candidate": {
                            "mailing_address": {
                                "address_line_1": "Private Street 1",
                                "city": "Tokyo",
                                "state_region": "Tokyo",
                                "postal_code": "100-0001",
                                "country": "Japan",
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )
            log = root / "stdout.log"
            log.write_text(
                "Official role location: Tokyo, Japan. Work with customers in Japan.",
                encoding="utf-8",
            )
            receipt = root / "receipt.json"

            value = scan_provider_log(
                profile_path=profile, log_path=log, receipt_path=receipt
            )

            self.assertEqual(value["status"], "clean")
            self.assertEqual(value["leaked_fields"], [])

    def test_exact_private_mailing_contact_still_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            profile = root / "profile.json"
            profile.write_text(
                json.dumps(
                    {
                        "candidate": {
                            "mailing_address": {
                                "address_line_1": "Private Street 1",
                                "city": "Tokyo",
                                "postal_code": "100-0001",
                                "country": "Japan",
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )
            log = root / "stdout.log"
            log.write_text(
                "provider transcript contains Private Street 1 and 100-0001",
                encoding="utf-8",
            )
            receipt = root / "receipt.json"

            with self.assertRaises(ProfileLeakError):
                scan_provider_log(
                    profile_path=profile, log_path=log, receipt_path=receipt
                )

            value = json.loads(receipt.read_text(encoding="utf-8"))
            self.assertEqual(value["status"], "leak_detected")
            self.assertEqual(
                value["leaked_fields"],
                [
                    "mailing_address.address_line_1",
                    "mailing_address.postal_code",
                ],
            )


if __name__ == "__main__":
    unittest.main()
