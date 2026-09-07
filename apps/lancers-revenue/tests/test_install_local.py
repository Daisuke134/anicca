import hashlib
import json
import os
import plistlib
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
INSTALLER = REPO_ROOT / "apps/lancers-revenue/scripts/install-local.sh"
PLIST_NAME = "ai.anicca.lancers-revenue-application.plist"
REPORTER_PLIST_NAME = "ai.anicca.lancers-revenue-telegram-report.plist"
WORK_SYNC_PLIST_NAME = "ai.anicca.lancers-revenue-work-sync.plist"
STOREFRONT_PLIST_NAME = "ai.anicca.lancers-revenue-storefront.plist"
RELEASE_FILES = (
    "skills/earn/lancers/SKILL.md",
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class InstallLocalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.release_sha = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=REPO_ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()

    def _run_install(self, root: Path, mode: str) -> tuple[Path, dict]:
        install_root = root / "install"
        launch_agent_dir = root / "LaunchAgents"
        state_root = root / "state"
        environment = os.environ.copy()
        environment.update(
            {
                "LANCERS_RELEASE_SHA": self.release_sha,
                "LANCERS_INSTALL_ROOT": str(install_root),
                "LANCERS_LAUNCH_AGENT_DIR": str(launch_agent_dir),
                "LANCERS_STATE_ROOT": str(state_root),
                "LANCERS_INSTALL_MODE": mode,
                "LANCERS_ACTIVATE": "0",
                "LANCERS_SKIP_MAIN_ASSERT": "1",
            }
        )
        result = subprocess.run(
            ["/bin/zsh", str(INSTALLER)],
            cwd=REPO_ROOT,
            env=environment,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        release = install_root / "releases" / self.release_sha
        manifest_path = state_root / "deployment.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.assertFalse((launch_agent_dir / PLIST_NAME).exists())
        self.assertFalse((launch_agent_dir / WORK_SYNC_PLIST_NAME).exists())
        self.assertFalse((launch_agent_dir / STOREFRONT_PLIST_NAME).exists())
        self.assertFalse((launch_agent_dir / REPORTER_PLIST_NAME).exists())
        return release, manifest

    def test_installs_immutable_exact_sha_release_and_reconcile_owner(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            release, manifest = self._run_install(root / "reconcile", "reconcile-only")
            self.assertEqual(release, root / "reconcile/install/releases" / self.release_sha)
            for relative in RELEASE_FILES:
                self.assertTrue((release / relative).is_file(), relative)

            self.assertEqual(manifest["deployed_sha"], self.release_sha)
            self.assertEqual(manifest["mode"], "reconcile-only")
            self.assertNotIn("launchd_label", manifest)
            self.assertNotIn("report_launchd_label", manifest)
            self.assertNotIn("work_sync_launchd_label", manifest)
            self.assertNotIn("storefront_launchd_label", manifest)
            self.assertEqual(list(manifest["files"]), sorted(manifest["files"]))
            self.assertEqual(
                set(manifest["files"]), set(RELEASE_FILES)
            )
            for relative, digest in manifest["files"].items():
                self.assertEqual(digest, sha256(release / relative), relative)
            mode = stat.S_IMODE((root / "reconcile/state/deployment.json").stat().st_mode)
            self.assertEqual(mode, 0o600)

            state_root = root / "reconcile/state"
            for path in state_root.rglob("*"):
                relative = path.relative_to(state_root)
                self.assertTrue(
                    relative == Path("deployment.json") or relative.parts[0] == "logs",
                    relative,
                )
            self.assertIn("LANCERS_ACTIVATE", INSTALLER.read_text(encoding="utf-8"))
            self.assertNotIn(
                "ai.anicca.lancers-revenue-application",
                INSTALLER.read_text(encoding="utf-8"),
            )
            self.assertNotIn(
                "ai.anicca.lancers-revenue-work-sync",
                INSTALLER.read_text(encoding="utf-8"),
            )
            self.assertNotIn(
                "ai.anicca.lancers-revenue-storefront",
                INSTALLER.read_text(encoding="utf-8"),
            )
            self.assertNotIn(
                "ai.anicca.lancers-revenue-telegram-report",
                INSTALLER.read_text(encoding="utf-8"),
            )

    def test_normal_owner_keeps_json_without_reconcile_flag(self):
        with tempfile.TemporaryDirectory() as directory:
            _, manifest = self._run_install(Path(directory), "normal")
            self.assertEqual(manifest["mode"], "normal")


if __name__ == "__main__":
    unittest.main()
