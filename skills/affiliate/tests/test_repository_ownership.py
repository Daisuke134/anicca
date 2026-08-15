from __future__ import annotations

import hashlib
import json
import os
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


class RepositoryOwnershipTests(unittest.TestCase):
    def test_canonical_skill_is_migration_only_and_active_files_are_portable(self) -> None:
        skill = SKILL_ROOT / "SKILL.md"
        self.assertTrue(skill.is_file())
        text = skill.read_text(encoding="utf-8")
        self.assertTrue(text.startswith("---\n"))
        self.assertIn("name: affiliate\n", text)
        self.assertIn("description:", text)
        self.assertIn("MIGRATION_ONLY", text)
        self.assertIn("DISABLED", text)
        self.assertIn("LIFE_MANAGER_STATE_HOME", text)
        self.assertIn("LIFE_MANAGER_DATA_HOME", text)

        active_files = (
            path
            for path in SKILL_ROOT.rglob("*")
            if path.is_file()
            and "legacy" not in path.relative_to(SKILL_ROOT).parts
            and "tests" not in path.relative_to(SKILL_ROOT).parts
            and "state" not in path.relative_to(SKILL_ROOT).parts
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

    def test_install_release_is_atomic_and_does_not_touch_launch_agents(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            temporary_root = Path(temporary)
            fixture_root = temporary_root / "life-manager"
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
                    "LIFE_MANAGER_DATA_HOME": str(data_home),
                    "LIFE_MANAGER_STATE_HOME": str(state_home),
                    "LIFE_MANAGER_RELEASE_SHA": commit,
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
            self.assertEqual(receipt_data["status"], "DISABLED")
            self.assertEqual(receipt_data["canonical_sha"], commit)
            self.assertEqual(receipt_data["release_path"], str(release))
            self.assertEqual(
                receipt_data["artifact_hashes"],
                ["legacy/SHA256SUMS", "legacy/DEPENDENCIES.sha256"],
            )
            self.assertEqual(receipt_data["excluded_mutable_paths"], ["state"])
            self.assertEqual(receipt_data["launchd_owners"], [])
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


if __name__ == "__main__":
    unittest.main()
