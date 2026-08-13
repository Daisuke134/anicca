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
RELEASE_FILES = (
    "skills/earn/lancers/scripts/application_loop.py",
    "skills/earn/lancers/scripts/application_tick.py",
    "skills/earn/lancers/scripts/status.py",
    "skills/earn/lancers/scripts/lancers_adapter.py",
    "skills/_shared/marketplace-core/scripts/application_transaction.py",
    "skills/_shared/marketplace-core/scripts/contracts.py",
    "skills/_shared/marketplace-core/scripts/ledger.py",
    "skills/_shared/marketplace-core/schemas/event.schema.json",
    "skills/_shared/marketplace-core/schemas/opportunity.schema.json",
    "skills/gig-work/schemas/application_decisions.schema.json",
    "skills/agent-runner/agent_runner.py",
    "skills/agent-runner/token_budget.py",
    "skills/agent-runner/config.json",
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

    def _run_install(self, root: Path, mode: str) -> tuple[Path, dict, dict]:
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
        plist_path = launch_agent_dir / PLIST_NAME
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        plist = plistlib.loads(plist_path.read_bytes())
        return release, manifest, plist

    def test_installs_immutable_exact_sha_release_and_reconcile_owner(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            release, manifest, plist = self._run_install(root / "reconcile", "reconcile-only")
            self.assertEqual(release, root / "reconcile/install/releases" / self.release_sha)
            for relative in RELEASE_FILES:
                self.assertTrue((release / relative).is_file(), relative)
            self.assertFalse((release / "runtime/agent-runner").exists())

            self.assertEqual(manifest["deployed_sha"], self.release_sha)
            self.assertEqual(manifest["mode"], "reconcile-only")
            self.assertEqual(manifest["launchd_label"], "ai.anicca.lancers-revenue-application")
            self.assertEqual(list(manifest["files"]), sorted(manifest["files"]))
            self.assertEqual(
                set(manifest["files"]), set(RELEASE_FILES)
            )
            for relative, digest in manifest["files"].items():
                self.assertEqual(digest, sha256(release / relative), relative)
            mode = stat.S_IMODE((root / "reconcile/state/deployment.json").stat().st_mode)
            self.assertEqual(mode, 0o600)

            arguments = plist["ProgramArguments"]
            self.assertIn(str(release / "skills/earn/lancers/scripts/application_loop.py"), arguments)
            self.assertIn("--json", arguments)
            self.assertIn("--reconcile-only", arguments)
            self.assertEqual(plist["Label"], "ai.anicca.lancers-revenue-application")
            self.assertEqual(plist["StartInterval"], 1800)
            self.assertEqual(plist["ProcessType"], "Background")
            self.assertEqual(plist["Umask"], 63)
            self.assertNotIn("RunAtLoad", plist)
            self.assertEqual(
                plist["EnvironmentVariables"]["PATH"],
                f"{os.environ['HOME']}/.local/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin",
            )
            self.assertNotIn("__LANCERS_", str(plist))

            state_root = root / "reconcile/state"
            for path in state_root.rglob("*"):
                relative = path.relative_to(state_root)
                self.assertTrue(
                    relative == Path("deployment.json") or relative.parts[0] == "logs",
                    relative,
                )
            self.assertNotIn("launchctl", INSTALLER.read_text(encoding="utf-8"))

    def test_normal_owner_keeps_json_without_reconcile_flag(self):
        with tempfile.TemporaryDirectory() as directory:
            _, manifest, plist = self._run_install(Path(directory), "normal")
            self.assertEqual(manifest["mode"], "normal")
            arguments = plist["ProgramArguments"]
            self.assertIn("--json", arguments)
            self.assertNotIn("--reconcile-only", arguments)


if __name__ == "__main__":
    unittest.main()
