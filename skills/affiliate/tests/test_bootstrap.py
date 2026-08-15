from __future__ import annotations

import hashlib
import json
import os
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path
from typing import Any, Optional


REPO_ROOT = Path(__file__).resolve().parents[3]
INSTALLER = REPO_ROOT / "skills" / "affiliate" / "bootstrap" / "install.sh"
RECEIPT_RELATIVE = Path("affiliate") / "bootstrap" / "machine-capability.json"


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tree_hashes(root: Path) -> dict[str, str]:
    if not root.exists():
        return {}
    return {
        path.relative_to(root).as_posix(): file_sha256(path)
        for path in root.rglob("*")
        if path.is_file()
    }


def contains_value(value: Any, expected: str) -> bool:
    if value == expected:
        return True
    if isinstance(value, dict):
        return any(contains_value(item, expected) for item in value.values())
    if isinstance(value, list):
        return any(contains_value(item, expected) for item in value)
    return False


class BootstrapInstallRedTests(unittest.TestCase):
    def require_installer(self) -> Path:
        self.assertTrue(
            INSTALLER.is_file(),
            f"feature missing: expected bootstrap installer at {INSTALLER}",
        )
        return INSTALLER

    def run_installer(self, installer: Path, environment: dict[str, str]) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["bash", str(installer)],
            env=environment,
            text=True,
            capture_output=True,
            check=False,
        )

    def base_environment(
        self,
        home: Path,
        data_home: Path,
        state_home: Path,
        manifest: Optional[Path] = None,
    ) -> dict[str, str]:
        environment = os.environ.copy()
        environment.update(
            {
                "HOME": str(home),
                "LIFE_MANAGER_DATA_HOME": str(data_home),
                "LIFE_MANAGER_STATE_HOME": str(state_home),
            }
        )
        if manifest is not None:
            environment["LIFE_MANAGER_BOOTSTRAP_MANIFEST"] = str(manifest)
        return environment

    def test_unsupported_os_fails_closed_without_mutating_state(self) -> None:
        installer = self.require_installer()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            fake_bin = root / "fake-bin"
            fake_bin.mkdir()
            fake_uname = fake_bin / "uname"
            fake_uname.write_text("#!/bin/sh\nprintf 'Linux\\n'\n", encoding="utf-8")
            fake_uname.chmod(fake_uname.stat().st_mode | stat.S_IXUSR)

            home = root / "home"
            data_home = root / "data"
            state_home = root / "state"
            launch_agents = home / "Library" / "LaunchAgents"
            launch_agents.mkdir(parents=True)
            (data_home / "sentinel").parent.mkdir(parents=True)
            (state_home / "sentinel").parent.mkdir(parents=True)
            (data_home / "sentinel").write_text("data-untouched\n", encoding="utf-8")
            (state_home / "sentinel").write_text("state-untouched\n", encoding="utf-8")
            (launch_agents / "sentinel").write_text("launchd-untouched\n", encoding="utf-8")
            before = {
                "data": tree_hashes(data_home),
                "state": tree_hashes(state_home),
                "launch_agents": tree_hashes(launch_agents),
            }

            environment = self.base_environment(home, data_home, state_home)
            environment["PATH"] = f"{fake_bin}{os.pathsep}{environment.get('PATH', '')}"
            result = self.run_installer(installer, environment)

            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(tree_hashes(data_home), before["data"])
            self.assertEqual(tree_hashes(state_home), before["state"])
            self.assertEqual(tree_hashes(launch_agents), before["launch_agents"])

    def test_pinned_artifact_install_is_idempotent_and_resumes_partial_receipt(self) -> None:
        installer = self.require_installer()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            artifact = root / "affiliate-runtime.bin"
            artifact_bytes = b"affiliate-bootstrap-fixture-v1\n"
            artifact.write_bytes(artifact_bytes)
            artifact_hash = file_sha256(artifact)
            manifest = root / "manifest.tsv"
            manifest.write_text(
                f"runtime\t1.0\t{artifact.as_uri()}\t{artifact_hash}\n",
                encoding="utf-8",
            )
            home = root / "home"
            data_home = root / "data"
            state_home = root / "state"
            secret = "bootstrap-secret-sentinel"
            environment = self.base_environment(home, data_home, state_home, manifest)
            environment["LIFE_MANAGER_BOOTSTRAP_SECRET"] = secret

            first = self.run_installer(installer, environment)
            self.assertEqual(first.returncode, 0, first.stderr)
            receipt_path = state_home / RECEIPT_RELATIVE
            self.assertTrue(receipt_path.is_file())
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            self.assertEqual(receipt["status"], "READY")
            self.assertEqual(receipt["platform"], "Darwin")
            self.assertEqual(receipt["manifest_sha256"], file_sha256(manifest))
            self.assertTrue(contains_value(receipt, artifact_hash))
            installed_artifacts = [
                path
                for path in data_home.rglob("*")
                if path.is_file() and path.read_bytes() == artifact_bytes
            ]
            self.assertEqual(len(installed_artifacts), 1)
            first_data = tree_hashes(data_home)
            first_state = tree_hashes(state_home)

            second = self.run_installer(installer, environment)
            self.assertEqual(second.returncode, 0, second.stderr)
            self.assertEqual(tree_hashes(data_home), first_data)
            self.assertEqual(tree_hashes(state_home), first_state)

            partial = {
                "status": "IN_PROGRESS",
                "completed_steps": ["directories"],
                "manifest_sha256": file_sha256(manifest),
            }
            receipt_path.write_text(json.dumps(partial) + "\n", encoding="utf-8")
            resumed = self.run_installer(installer, environment)
            self.assertEqual(resumed.returncode, 0, resumed.stderr)
            resumed_receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            self.assertEqual(resumed_receipt["status"], "READY")
            self.assertEqual(resumed_receipt["manifest_sha256"], file_sha256(manifest))
            self.assertEqual(
                len(
                    [
                        path
                        for path in data_home.rglob("*")
                        if path.is_file() and path.read_bytes() == artifact_bytes
                    ]
                ),
                1,
            )

            for result in (first, second, resumed):
                self.assertNotIn(secret, result.stdout)
                self.assertNotIn(secret, result.stderr)
            for root_to_scan in (data_home, state_home):
                for path in root_to_scan.rglob("*"):
                    if path.is_file():
                        self.assertNotIn(secret, path.read_text(encoding="utf-8", errors="replace"))

    def test_missing_or_mismatched_checksum_fails_closed(self) -> None:
        installer = self.require_installer()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            artifact = root / "affiliate-runtime.bin"
            artifact.write_bytes(b"affiliate-bootstrap-fixture-v1\n")
            artifact_hash = file_sha256(artifact)
            for case_name, checksum in (
                ("missing", ""),
                ("mismatch", "0" * 64 if artifact_hash != "0" * 64 else "f" * 64),
            ):
                with self.subTest(case=case_name):
                    case_root = root / case_name
                    case_root.mkdir()
                    manifest = case_root / "manifest.tsv"
                    manifest.write_text(
                        f"runtime\t1.0\t{artifact.as_uri()}\t{checksum}\n",
                        encoding="utf-8",
                    )
                    home = case_root / "home"
                    data_home = case_root / "data"
                    state_home = case_root / "state"
                    environment = self.base_environment(home, data_home, state_home, manifest)
                    result = self.run_installer(installer, environment)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertFalse((state_home / RECEIPT_RELATIVE).exists())
                    self.assertFalse(
                        any(path.is_file() for path in data_home.rglob("*"))
                    )


if __name__ == "__main__":
    unittest.main()
