from __future__ import annotations

import hashlib
import importlib.util
import json
import plistlib
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock
from typing import Any, Dict


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "skills" / "affiliate" / "scripts" / "machine_capability_inventory.py"


class MachineCapabilityInventoryTests(unittest.TestCase):
    def require_script(self) -> Path:
        self.assertTrue(
            SCRIPT.is_file(),
            f"feature missing: expected machine capability inventory at {SCRIPT}",
        )
        return SCRIPT

    def run_inventory(
        self,
        script: Path,
        request: Path,
        receipt: Path,
    ) -> subprocess.CompletedProcess:
        return subprocess.run(
            ["python3", str(script), "--request", str(request), "--receipt", str(receipt)],
            text=True,
            capture_output=True,
            check=False,
        )

    def write_json(self, path: Path, value: object) -> None:
        path.write_text(json.dumps(value, sort_keys=True) + "\n", encoding="utf-8")

    def sha256(self, path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def load_module(self, script: Path) -> Any:
        spec = importlib.util.spec_from_file_location("machine_capability_inventory", script)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_inventory_is_deterministic_for_macos_app(self) -> None:
        script = self.require_script()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            app = root / "Example.app"
            app_binary = app / "Contents" / "MacOS" / "Example"
            app_binary.parent.mkdir(parents=True)
            app_binary.write_bytes(b"app executable\n")
            app_binary.chmod(0o755)
            info = app / "Contents" / "Info.plist"
            with info.open("wb") as stream:
                plistlib.dump(
                    {
                        "CFBundleIdentifier": "com.example.affiliate",
                        "CFBundleShortVersionString": "2.4.1",
                    },
                    stream,
                )

            request = root / "request.json"
            receipt = root / "state" / "machine-capability.json"
            self.write_json(
                request,
                {
                    "capabilities": [{
                        "name": "example-app",
                        "kind": "macos_app",
                        "path": str(app),
                        "executable": "Example",
                    }]
                },
            )

            first = self.run_inventory(script, request, receipt)
            self.assertEqual(first.returncode, 0, first.stderr)
            first_bytes = receipt.read_bytes()
            payload = json.loads(first_bytes)
            self.assertEqual(payload["schema_version"], 1)
            self.assertEqual(payload["status"], "READY")
            self.assertEqual(payload["platform"], "macOS")
            self.assertTrue(payload["architecture"])
            self.assertEqual(
                payload["request_sha256"], self.sha256(request)
            )
            self.assertEqual(
                [entry["name"] for entry in payload["capabilities"]],
                ["example-app"],
            )

            records = {entry["name"]: entry for entry in payload["capabilities"]}
            self.assertEqual(records["example-app"]["kind"], "macos_app")
            self.assertEqual(records["example-app"]["canonical_path"], str(app.resolve()))
            self.assertEqual(records["example-app"]["version"], "2.4.1")
            self.assertEqual(records["example-app"]["size_bytes"], app_binary.stat().st_size)
            self.assertEqual(records["example-app"]["sha256"], self.sha256(app_binary))

            second = self.run_inventory(script, request, receipt)
            self.assertEqual(second.returncode, 0, second.stderr)
            self.assertEqual(receipt.read_bytes(), first_bytes)
            self.assertEqual(list(receipt.parent.glob(".*")), [])

            module = self.load_module(script)
            unsupported_request = root / "unsupported-request.json"
            unsupported_receipt = root / "unsupported-receipt.json"
            self.write_json(
                unsupported_request,
                {"capabilities": [{
                    "name": "example-app",
                    "kind": "macos_app",
                    "path": str(app),
                    "executable": "Example",
                }]},
            )
            with mock.patch.object(module.platform, "system", return_value="Linux"), mock.patch.object(
                module.sys,
                "argv",
                ["machine_capability_inventory.py", "--request", str(unsupported_request), "--receipt", str(unsupported_receipt)],
            ):
                with self.assertRaises(module.InventoryError):
                    module.main()
            self.assertFalse(unsupported_receipt.exists())

    def test_rejects_missing_duplicate_and_secret_inputs_without_receipt(self) -> None:
        script = self.require_script()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            executable = root / "tool"
            executable.write_bytes(b"tool\n")
            executable.chmod(0o755)
            base: Dict[str, Any] = {
                "name": "tool",
                "kind": "executable",
                "path": str(executable),
            }
            bad_app = root / "External.app"
            bad_binary = root / "outside" / "External"
            bad_binary.parent.mkdir()
            bad_binary.write_bytes(b"outside\n")
            bad_binary.chmod(0o755)
            (bad_app / "Contents").mkdir(parents=True)
            (bad_app / "Contents" / "Info.plist").write_bytes(
                plistlib.dumps({"CFBundleVersion": "1.0"})
            )
            (bad_app / "Contents" / "MacOS").symlink_to(
                bad_binary.parent, target_is_directory=True
            )
            secret_app = root / "Version.app"
            secret_binary = secret_app / "Contents" / "MacOS" / "Version"
            secret_binary.parent.mkdir(parents=True)
            secret_binary.write_bytes(b"version\n")
            secret_binary.chmod(0o755)
            (secret_app / "Contents" / "Info.plist").write_bytes(
                plistlib.dumps({"CFBundleVersion": "sk_live_123456789"})
            )
            cases = {
                "generic_executable": {"capabilities": [dict(base)]},
                "missing": {
                    "capabilities": [dict(base, path=str(root / "missing"))]
                },
                "duplicate": {"capabilities": [dict(base), dict(base)]},
                "secret": {
                    "capabilities": [dict(base, token="AUTHORITY_SECRET_SENTINEL")]
                },
                "unknown_entry": {
                    "capabilities": [dict(base, unexpected="reject-me")]
                },
                "unknown_top_level": {
                    "capabilities": [dict(base)],
                    "extra": "reject-me",
                },
                "empty": {"capabilities": []},
                "fake_version": {
                    "capabilities": [dict(base, version="9.9.9")]
                },
                "external_macos": {
                    "capabilities": [{
                        "name": "external-app",
                        "kind": "macos_app",
                        "path": str(bad_app),
                        "executable": "External",
                    }]
                },
                "secret_version": {
                    "capabilities": [{
                        "name": "version-app",
                        "kind": "macos_app",
                        "path": str(secret_app),
                        "executable": "Version",
                    }]
                },
            }
            for name, request_value in cases.items():
                with self.subTest(case=name):
                    request = root / (name + "-request.json")
                    receipt = root / (name + "-receipt.json")
                    self.write_json(request, request_value)
                    result = self.run_inventory(script, request, receipt)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertFalse(receipt.exists())
                    self.assertNotIn("AUTHORITY_SECRET_SENTINEL", result.stdout)
                    self.assertNotIn("AUTHORITY_SECRET_SENTINEL", result.stderr)

            module = self.load_module(script)

            def valid_app(name: str) -> tuple[Path, Path, Path]:
                app = root / (name + ".app")
                binary = app / "Contents" / "MacOS" / name
                binary.parent.mkdir(parents=True)
                binary.write_bytes(b"valid app\n")
                binary.chmod(0o755)
                info = app / "Contents" / "Info.plist"
                info.write_bytes(plistlib.dumps({"CFBundleVersion": "1.0"}))
                return app, app / "Contents" / "MacOS", info

            swap_app, swap_macos, _ = valid_app("Swap")
            swap_outside = root / "swap-outside"
            swap_outside.mkdir()
            (swap_outside / "Swap").write_bytes(b"outside\n")
            (swap_outside / "Swap").chmod(0o755)
            original_bundle_version = module.bundle_version

            def swap_macos_after_validation(info_fd: int) -> tuple[str, Any]:
                swap_macos.rename(root / "Swap-MacOS")
                swap_macos.symlink_to(swap_outside, target_is_directory=True)
                return original_bundle_version(info_fd)

            with mock.patch.object(
                module, "bundle_version", side_effect=swap_macos_after_validation
            ):
                with self.assertRaises(module.InventoryError):
                    module.inspect({
                        "name": "swap-app",
                        "kind": "macos_app",
                        "path": str(swap_app),
                        "executable": "Swap",
                    })

            info_app, _, info_path = valid_app("InfoSwap")

            def swap_info_after_validation(info_fd: int) -> tuple[str, Any]:
                info_path.rename(root / "InfoSwap-original.plist")
                info_path.write_bytes(
                    plistlib.dumps({"CFBundleShortVersionString": "secret-version"})
                )
                return original_bundle_version(info_fd)

            with mock.patch.object(module, "bundle_version", side_effect=swap_info_after_validation):
                with self.assertRaises(module.InventoryError):
                    module.inspect({
                        "name": "info-swap-app",
                        "kind": "macos_app",
                        "path": str(info_app),
                        "executable": "InfoSwap",
                    })

    def test_stat_mutation_during_hash_fails_closed(self) -> None:
        script = self.require_script()
        module = self.load_module(script)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            app = root / "Mutable.app"
            target = app / "Contents" / "MacOS" / "Mutable"
            target.parent.mkdir(parents=True)
            target.write_bytes(b"stable content\n")
            target.chmod(0o755)
            (app / "Contents" / "Info.plist").write_bytes(
                plistlib.dumps({"CFBundleVersion": "1.0"})
            )
            original_stream = module.stream_sha256

            def mutate_then_hash(fd: int) -> str:
                target.chmod(0o700)
                return original_stream(fd)

            with mock.patch.object(module, "stream_sha256", side_effect=mutate_then_hash):
                with self.assertRaises(module.InventoryError):
                    module.inspect({
                        "name": "mutable-app",
                        "kind": "macos_app",
                        "path": str(app),
                        "executable": "Mutable",
                    })


if __name__ == "__main__":
    unittest.main()
