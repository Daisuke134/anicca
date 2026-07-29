import tempfile
import unittest
from pathlib import Path

import pii_shape_scan


class PiiShapeScanTests(unittest.TestCase):
    def test_blocks_pii_shapes_without_returning_matched_values(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            candidate = root / "candidate.js"
            jp_phone = "+8190" + "12345678"
            jp_national_phone = "080" + "12345678"
            us_phone = "+1415" + "5552671"
            gmail = "person" + "@gmail.com"
            home_address = '"home_' + 'address":"Tokyo 1-2-3"'
            candidate.write_text(
                "\n".join(
                    [
                        f'const jp = "{jp_phone}";',
                        f'const jpLocal = "{jp_national_phone}";',
                        f'const us = "{us_phone}";',
                        f'const mail = "{gmail}";',
                        "{" + home_address + "}",
                        f'{{"phone":"{jp_phone}"}}',
                    ]
                ),
                encoding="utf-8",
            )

            findings = pii_shape_scan.scan_paths([candidate])

        self.assertEqual(
            [finding.pattern for finding in findings],
            [
                "jp_e164",
                "jp_national_mobile",
                "us_e164",
                "personal_gmail",
                "home_address",
                "json_phone",
            ],
        )
        rendered = "\n".join(finding.render() for finding in findings)
        self.assertNotIn(jp_phone, rendered)
        self.assertNotIn(jp_national_phone, rendered)
        self.assertNotIn(us_phone, rendered)
        self.assertNotIn(gmail, rendered)
        self.assertIn("candidate.js:1:jp_e164", rendered)
        self.assertTrue(
            all(
                pii_shape_scan.FINGERPRINT.fullmatch(finding.fingerprint)
                for finding in findings
            )
        )

    def test_allowlist_is_scoped_to_exact_rule_path_and_value(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            allowed = root / "fixtures" / "allowed.js"
            allowed.parent.mkdir()
            phone = "+1202" + "5550100"
            allowed.write_text(f'const phone = "{phone}";\n', encoding="utf-8")
            fingerprint = pii_shape_scan.fingerprint_for(
                "us_e164",
                Path("fixtures/allowed.js"),
                phone,
            )
            allowlist = root / ".pii-shape-allowlist"
            allowlist.write_text(
                f"{fingerprint} # synthetic fixture\n",
                encoding="utf-8",
            )
            same_value_elsewhere = root / "other.js"
            same_value_elsewhere.write_text(
                f'const phone = "{phone}";\n',
                encoding="utf-8",
            )

            allowed_fingerprints = pii_shape_scan.load_allowlist(allowlist)
            self.assertEqual(
                pii_shape_scan.scan_paths(
                    [allowed],
                    root=root,
                    allowed_fingerprints=allowed_fingerprints,
                ),
                [],
            )
            findings = pii_shape_scan.scan_paths(
                [same_value_elsewhere],
                root=root,
                allowed_fingerprints=allowed_fingerprints,
            )

        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].pattern, "us_e164")

    def test_allowlist_rejects_non_hash_entries(self):
        with tempfile.TemporaryDirectory() as directory:
            allowlist = Path(directory) / ".pii-shape-allowlist"
            allowlist.write_text("not-a-fingerprint # unsafe\n", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "invalid PII fingerprint"):
                pii_shape_scan.load_allowlist(allowlist)


if __name__ == "__main__":
    unittest.main()
