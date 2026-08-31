from __future__ import annotations

import hashlib
import os
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path
from typing import Optional


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
                "MR_BOT_DATA_HOME": str(data_home),
                "MR_BOT_STATE_HOME": str(state_home),
            }
        )
        if manifest is not None:
            environment["MR_BOT_BOOTSTRAP_MANIFEST"] = str(manifest)
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
