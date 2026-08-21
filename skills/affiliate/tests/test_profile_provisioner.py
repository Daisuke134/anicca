from __future__ import annotations

import hashlib
import json
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "skills" / "affiliate" / "scripts" / "profile_provisioner.py"
PROTECTED_PORTS = {9222, 9223, 9225}


def tree_hashes(root: Path) -> dict[str, str]:
    if not root.exists():
        return {}
    return {
        path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in root.rglob("*")
        if path.is_file()
    }


class ProfileProvisionerRedTests(unittest.TestCase):
    def require_script(self) -> Path:
        self.assertTrue(
            SCRIPT.is_file(),
            f"feature missing: expected profile provisioner at {SCRIPT}",
        )
        return SCRIPT

    def run_provisioner(
        self,
        script: Path,
        root: Path,
        receipt: Path,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["python3", str(script), "--root", str(root), "--receipt", str(receipt)],
            text=True,
            capture_output=True,
            check=False,
        )

    def receipt_locale_path(self, root: Path, record: dict[str, object]) -> Path:
        path = Path(str(record["path"]))
        return path if path.is_absolute() else root / path

    def test_creates_distinct_real_provider_language_and_x_profiles(self) -> None:
        script = self.require_script()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "profiles"
            receipt = Path(temporary) / "profile-receipt.json"
            result = self.run_provisioner(script, root, receipt)
            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(receipt.read_text(encoding="utf-8"))
            self.assertEqual(payload["status"], "READY")
            self.assertEqual(set(payload["locales"]), {"en", "ja", "x-en", "impact-en"})

            records = payload["locales"]
            names = ("en", "ja", "x-en", "impact-en")
            paths = [self.receipt_locale_path(root, records[locale]) for locale in names]
            ports = [int(records[locale]["cdp_port"]) for locale in names]
            self.assertEqual(len(set(paths)), 4)
            self.assertEqual(len(set(ports)), 4)
            self.assertTrue(PROTECTED_PORTS.isdisjoint(ports))
            for path in paths:
                self.assertTrue(path.is_dir())
                self.assertFalse(path.is_symlink())

    def test_second_provision_preserves_locale_state_without_cross_copy(self) -> None:
        script = self.require_script()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "profiles"
            receipt = Path(temporary) / "profile-receipt.json"
            first = self.run_provisioner(script, root, receipt)
            self.assertEqual(first.returncode, 0, first.stderr)
            first_payload = json.loads(receipt.read_text(encoding="utf-8"))
            en = self.receipt_locale_path(root, first_payload["locales"]["en"])
            ja = self.receipt_locale_path(root, first_payload["locales"]["ja"])
            (en / "Cookies").write_text("en-cookie\n", encoding="utf-8")
            (ja / "Storage").write_text("ja-storage\n", encoding="utf-8")
            before_tree = tree_hashes(root)
            before_receipt = hashlib.sha256(receipt.read_bytes()).hexdigest()

            second = self.run_provisioner(script, root, receipt)
            self.assertEqual(second.returncode, 0, second.stderr)
            self.assertEqual(tree_hashes(root), before_tree)
            self.assertEqual(hashlib.sha256(receipt.read_bytes()).hexdigest(), before_receipt)
            self.assertEqual((en / "Cookies").read_text(encoding="utf-8"), "en-cookie\n")
            self.assertEqual((ja / "Storage").read_text(encoding="utf-8"), "ja-storage\n")
            self.assertFalse((en / "Storage").exists())
            self.assertFalse((ja / "Cookies").exists())


if __name__ == "__main__":
    unittest.main()
