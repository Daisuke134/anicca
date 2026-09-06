import json
import tempfile
import unittest
from pathlib import Path

from runtime.host.boot_panic_collector import (
    build_receipt,
    classify_component_boundary,
    write_receipt,
)


class BootPanicCollectorTest(unittest.TestCase):
    def test_build_receipt_contains_required_counts_without_browser_content(self):
        fixture = {
            "boot_session_uuid": "A1B2-C3D4",
            "boot_time": "2026-09-03T06:45:31+09:00",
            "orderly_shutdown_before_boot": False,
            "panic_reports": ["panic-full-2026-09-03-064551.0002.panic"],
            "reset_reports": ["ResetCounter-2026-09-03-064606.diag"],
            "watchdog_reports": {
                "WindowServer": ["WindowServer_2026-09-06.userspace_watchdog_timeout.spin"],
                "tccd": [],
                "sandboxd": ["sandboxd_2026-09-03.resource.diag"],
            },
            "panic_text": (
                "userspace watchdog timeout: no successful checkins from WindowServer; "
                "blocked through tccd; sandboxd thread limit; compressor 100%"
            ),
            "memory": {"page_size_bytes": 16384, "pages_free": 10, "pages_compressed": 20,
                       "swap_used_bytes": 30},
            "disk": {"root_free_bytes": 40},
            "browser": {"owner_count": 2, "process_count": 9, "renderer_count": 6,
                        "debug_endpoint_count": 1, "tab_count": 4},
        }

        receipt = build_receipt(fixture, collected_at="2026-09-06T01:00:00Z")

        self.assertEqual(receipt["boot"]["id"], "A1B2-C3D4")
        self.assertEqual(receipt["component_boundary"], "WindowServer")
        self.assertEqual(receipt["reset_reports"], ["ResetCounter-2026-09-03-064606.diag"])
        self.assertTrue(receipt["watchdog_evidence"]["tccd"]["mentioned_in_latest_panic"])
        self.assertEqual(receipt["browser"]["tab_count"], 4)
        serialized = json.dumps(receipt)
        self.assertNotIn("panic_text", serialized)
        self.assertNotIn("http", serialized)

    def test_component_boundary_is_explicit_and_conservative(self):
        self.assertEqual(
            classify_component_boundary("userspace watchdog timeout WindowServer tccd sandboxd"),
            "WindowServer",
        )
        self.assertEqual(classify_component_boundary("panic(cpu 0 caller ...)"), "kernel_or_hardware")
        self.assertEqual(classify_component_boundary(""), "no_panic_evidence")

    def test_receipt_is_deduplicated_by_boot_id_and_private(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            receipt = {
                "version": 1,
                "boot": {"id": "A/B C", "time": "2026-09-03T06:45:31+09:00"},
            }
            first = write_receipt(root, receipt)
            second = write_receipt(root, receipt)

            self.assertEqual(first, second)
            self.assertEqual(len(list((root / "boots").glob("*/summary.json"))), 1)
            self.assertEqual(first.stat().st_mode & 0o777, 0o600)


if __name__ == "__main__":
    unittest.main()
