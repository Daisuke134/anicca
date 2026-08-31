from __future__ import annotations

import hashlib
import json
import os
import pwd
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
SKILL_ROOT = REPO_ROOT / "skills" / "affiliate"
LEGACY_ROOT = SKILL_ROOT / "legacy"
MANIFEST = LEGACY_ROOT / "SHA256SUMS"
DEPENDENCY_MANIFEST = LEGACY_ROOT / "DEPENDENCIES.sha256"

PRESERVED_FILES = {
    "affiliate-cli.sh",
    "affiliate-healthcheck.sh",
    "affiliate_verify.py",
    "launch_affiliate_browser.py",
    "launchd/ai.anicca.affiliate-core-healthcheck.plist",
    "measure_commission.py",
    "producer.sh",
    "run.sh",
    "tests/test_affiliate_verify.py",
    "tests/test_measure_commission.py",
}

DEPENDENCY_FILES = {
    "vendor/ytdlp-parse-shared-lib/ytdlp_parse.py",
}


def manifest_entries(path: Path) -> dict[str, str]:
    entries: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        digest, relative = line.split(maxsplit=1)
        entries[relative] = digest
    return entries


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


GUARD_RELATIVE = Path(
    "gig/releases/mr-bot/current/skills/earn/gig/scripts/gig_disk_guard.py"
)


def canonical_guard() -> Path:
    try:
        owner_home = Path(pwd.getpwuid(os.getuid()).pw_dir)
    except KeyError:
        owner_home = Path.home()
    return owner_home / GUARD_RELATIVE


def canonical_guard_ready() -> bool:
    guard = canonical_guard()
    return guard.is_file() and not guard.is_symlink()


class RepositoryOwnershipTests(unittest.TestCase):
    def test_live_installer_does_not_bootout_loaded_affiliate_owners(self) -> None:
        installer = REPO_ROOT / "skills" / "affiliate" / "scripts" / "install-release.sh"
        text = installer.read_text(encoding="utf-8")
        self.assertNotIn('/bin/launchctl bootout "gui/$(id -u)/$label"', text)

    def test_installer_supports_explicit_canonical_home_without_weakening_guard(self) -> None:
        installer = REPO_ROOT / "skills" / "affiliate" / "scripts" / "install-release.sh"
        text = installer.read_text(encoding="utf-8")
        self.assertIn("AFFILIATE_CANONICAL_HOME", text)
        self.assertIn('[[ "$CANONICAL_HOME" = /* && -d "$CANONICAL_HOME" ]]', text)
        self.assertIn('[[ -f "$GUARD_PATH" && ! -L "$GUARD_PATH" && -r "$GUARD_PATH" ]]', text)

    def test_canonical_skill_is_migration_only_and_active_files_are_portable(self) -> None:
        skill = SKILL_ROOT / "SKILL.md"
        self.assertTrue(skill.is_file())
        text = skill.read_text(encoding="utf-8")
        self.assertTrue(text.startswith("---\n"))
        self.assertIn("name: affiliate\n", text)
        self.assertIn("description:", text)
        self.assertIn("MIGRATION_ONLY", text)
        self.assertIn("MACOS_LOCAL_ONLY", text)
        self.assertIn("MR_BOT_STATE_HOME", text)
        self.assertIn("MR_BOT_DATA_HOME", text)

        active_files = (
            path
            for path in SKILL_ROOT.rglob("*")
            if path.is_file()
            and "legacy" not in path.relative_to(SKILL_ROOT).parts
            and "tests" not in path.relative_to(SKILL_ROOT).parts
            and "state" not in path.relative_to(SKILL_ROOT).parts
            and "__pycache__" not in path.relative_to(SKILL_ROOT).parts
            and path.suffix != ".pyc"
        )
        for path in active_files:
            body = path.read_text(encoding="utf-8")
            self.assertNotIn("/Users/anicca", body, path.as_posix())
            self.assertNotIn("profitable-claude", body, path.as_posix())

    def test_legacy_manifest_covers_exact_preserved_files(self) -> None:
        self.assertTrue(MANIFEST.is_file())
        self.assertTrue(DEPENDENCY_MANIFEST.is_file())
        entries = manifest_entries(MANIFEST)
        dependencies = manifest_entries(DEPENDENCY_MANIFEST)
        self.assertEqual(set(entries), PRESERVED_FILES)
        self.assertEqual(set(dependencies), DEPENDENCY_FILES)
        for relative, expected in {**entries, **dependencies}.items():
            preserved = LEGACY_ROOT / relative
            self.assertTrue(preserved.is_file(), relative)
            self.assertEqual(sha256(preserved), expected, relative)

        payload = {
            path.relative_to(LEGACY_ROOT).as_posix()
            for path in LEGACY_ROOT.rglob("*")
            if path.is_file()
            and "__pycache__" not in path.relative_to(LEGACY_ROOT).parts
            and path.suffix != ".pyc"
        }
        self.assertEqual(
            payload,
            PRESERVED_FILES
            | DEPENDENCY_FILES
            | {"SHA256SUMS", "DEPENDENCIES.sha256"},
        )

    @unittest.skipUnless(
        canonical_guard_ready(),
        "canonical Mr.bot guard is unavailable; success integration is not hermetic here",
    )
    def test_install_release_is_atomic_and_does_not_touch_launch_agents(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            temporary_root = Path(temporary)
            fixture_root = temporary_root / "mr-bot"
            fixture_skill = fixture_root / "skills" / "affiliate"
            fixture_skill.parent.mkdir(parents=True)
            shutil.copytree(
                SKILL_ROOT,
                fixture_skill,
                ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
            )

            subprocess.run(["git", "init", "-q", str(fixture_root)], check=True)
            subprocess.run(
                ["git", "-C", str(fixture_root), "add", "skills/affiliate"],
                check=True,
            )
            subprocess.run(
                [
                    "git",
                    "-C",
                    str(fixture_root),
                    "-c",
                    "user.name=ownership-test",
                    "-c",
                    "user.email=ownership-test@example.invalid",
                    "commit",
                    "-qm",
                    "fixture",
                ],
                check=True,
            )
            commit = subprocess.check_output(
                ["git", "-C", str(fixture_root), "rev-parse", "HEAD"],
                text=True,
            ).strip()

            home = temporary_root / "home"
            launch_agents = home / "Library" / "LaunchAgents"
            launch_agents.mkdir(parents=True)
            sentinel = launch_agents / "sentinel"
            sentinel.write_text("untouched\n", encoding="utf-8")
            sentinel_hash = sha256(sentinel)

            data_home = temporary_root / "data"
            state_home = temporary_root / "state"
            environment = os.environ.copy()
            environment.update(
                {
                    "HOME": str(home),
                    "MR_BOT_DATA_HOME": str(data_home),
                    "MR_BOT_STATE_HOME": str(state_home),
                    "MR_BOT_RELEASE_SHA": commit,
                    "AFFILIATE_INSTALL_LAUNCHD": "0",
                    "AFFILIATE_CANONICAL_HOME": str(Path.home()),
                }
            )
            install_script = fixture_skill / "scripts" / "install-release.sh"
            subprocess.run(["bash", str(install_script)], check=True, env=environment)

            release = data_home / "affiliate" / "releases" / commit
            current = data_home / "affiliate" / "current"
            self.assertTrue(release.is_dir())
            self.assertTrue(current.is_symlink())
            self.assertEqual(current.resolve(), release.resolve())
            self.assertFalse(any(path.name == "__pycache__" for path in release.rglob("*")))
            self.assertFalse(any(path.suffix == ".pyc" for path in release.rglob("*")))
            self.assertEqual(sha256(sentinel), sentinel_hash)
            self.assertFalse((state_home / "affiliate" / "Library").exists())
            self.assertTrue(
                any((state_home / "affiliate").glob("*.json")),
                "ownership receipt is written outside the release",
            )

            # A second identical install is a no-op and must keep the same
            # immutable release and receipt.
            receipt = next((state_home / "affiliate").glob("*.json"))
            receipt_data = json.loads(receipt.read_text(encoding="utf-8"))
            guard = canonical_guard()
            guard_hash = sha256(guard)
            self.assertEqual(receipt_data["status"], "LOCAL_RELEASE_ONLY")
            self.assertEqual(receipt_data["canonical_sha"], commit)
            self.assertEqual(receipt_data["release_path"], str(release))
            self.assertEqual(
                receipt_data["artifact_hashes"],
                ["legacy/SHA256SUMS", "legacy/DEPENDENCIES.sha256"],
            )
            self.assertEqual(receipt_data["excluded_mutable_paths"], ["state"])
            self.assertEqual(receipt_data["launchd_owners"], [])
            self.assertEqual(receipt_data["disk_guard_path"], str(guard))
            self.assertEqual(receipt_data["disk_guard_sha256"], guard_hash)
            self.assertEqual(
                receipt_data["external_dependencies"],
                [{"name": "mr-bot-disk-guard", "path": str(guard), "sha256": guard_hash}],
            )
            self.assertEqual(
                receipt_data["deferred_launchd_owners"],
                [
                    "ai.anicca.affiliate-browser",
                    "ai.anicca.affiliate-impact-browser",
                    "ai.anicca.affiliate-x-browser",
                ],
            )
            receipt_hash = sha256(receipt)
            subprocess.run(["bash", str(install_script)], check=True, env=environment)
            self.assertEqual(current.resolve(), release.resolve())
            self.assertEqual(sha256(receipt), receipt_hash)

            # Simulate a stale/corrupt current pointer. The next install must
            # replace the symlink without following its target.
            bogus_target = temporary_root / "bogus-release"
            current.unlink()
            current.symlink_to(bogus_target)
            subprocess.run(["bash", str(install_script)], check=True, env=environment)
            self.assertTrue(current.is_symlink())
            self.assertEqual(current.resolve(), release.resolve())

            # A release is immutable: the same SHA must never silently repair
            # or accept bytes changed outside the installer.
            (release / "SKILL.md").write_text("mutated\n", encoding="utf-8")
            conflict = subprocess.run(
                ["bash", str(install_script)],
                check=False,
                env=environment,
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(conflict.returncode, 0)
            self.assertIn("conflicts with canonical source", conflict.stderr)

    @unittest.skipIf(
        canonical_guard_ready(),
        "canonical Mr.bot guard exists; missing-dependency branch is CI-only",
    )
    def test_install_release_fails_closed_when_canonical_guard_is_absent(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            temporary_root = Path(temporary)
            fixture_root = temporary_root / "mr-bot"
            fixture_skill = fixture_root / "skills" / "affiliate"
            fixture_skill.parent.mkdir(parents=True)
            shutil.copytree(
                SKILL_ROOT,
                fixture_skill,
                ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
            )
            subprocess.run(["git", "init", "-q", str(fixture_root)], check=True)
            subprocess.run(
                ["git", "-C", str(fixture_root), "add", "skills/affiliate"],
                check=True,
            )
            subprocess.run(
                [
                    "git", "-C", str(fixture_root), "-c", "user.name=ownership-test",
                    "-c", "user.email=ownership-test@example.invalid", "commit", "-qm", "fixture",
                ],
                check=True,
            )
            commit = subprocess.check_output(
                ["git", "-C", str(fixture_root), "rev-parse", "HEAD"], text=True,
            ).strip()
            home = temporary_root / "home"
            data_home = temporary_root / "data"
            state_home = temporary_root / "state"
            environment = os.environ.copy()
            environment.update(
                {
                    "HOME": str(home),
                    "MR_BOT_DATA_HOME": str(data_home),
                    "MR_BOT_STATE_HOME": str(state_home),
                    "MR_BOT_RELEASE_SHA": commit,
                    "AFFILIATE_INSTALL_LAUNCHD": "0",
                    "AFFILIATE_CANONICAL_HOME": str(Path.home()),
                }
            )
            result = subprocess.run(
                ["bash", str(fixture_skill / "scripts" / "install-release.sh")],
                check=False,
                env=environment,
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Mr.bot disk guard is unavailable", result.stderr)
            self.assertFalse((data_home / "affiliate" / "current").exists())
            self.assertFalse((data_home / "affiliate" / "releases").exists())


if __name__ == "__main__":
    unittest.main()
