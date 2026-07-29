import hashlib
import json
import os
import subprocess
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path


APP_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = APP_ROOT.parents[1]
VERSION = "0.1.0-test"
ARCHIVE_NAME = f"anicca-job-search-{VERSION}.tar.gz"
PREFIX = f"anicca-job-search-{VERSION}"


class ReleaseTests(unittest.TestCase):
    def _build(self, output: Path):
        return subprocess.run(
            [
                sys.executable,
                "-m",
                "job_search_loop.release",
                "--repo-root",
                str(REPO_ROOT),
                "--output-dir",
                str(output),
                "--version",
                VERSION,
            ],
            check=False,
            capture_output=True,
            text=True,
            env={**os.environ, "PYTHONPATH": str(APP_ROOT)},
        )

    def test_same_commit_build_is_reproducible_and_bounded(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first_dir = root / "first"
            second_dir = root / "second"

            first = self._build(first_dir)
            second = self._build(second_dir)

            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertEqual(second.returncode, 0, second.stderr)
            first_receipt = json.loads(first.stdout)
            second_receipt = json.loads(second.stdout)
            archive = first_dir / ARCHIVE_NAME
            other = second_dir / ARCHIVE_NAME
            self.assertEqual(archive.read_bytes(), other.read_bytes())
            digest = hashlib.sha256(archive.read_bytes()).hexdigest()
            self.assertEqual(first_receipt["sha256"], digest)
            self.assertEqual(second_receipt["sha256"], digest)
            self.assertEqual(
                (first_dir / f"{ARCHIVE_NAME}.sha256").read_text(encoding="utf-8"),
                f"{digest}  {ARCHIVE_NAME}\n",
            )

            with tarfile.open(archive, "r:gz") as bundle:
                members = bundle.getmembers()
                names = [member.name for member in members]
                self.assertEqual(names, sorted(names))
                self.assertIn(f"{PREFIX}/RELEASE.json", names)
                self.assertIn(
                    f"{PREFIX}/apps/job-search-loop/scripts/install-local.sh", names
                )
                self.assertIn(
                    f"{PREFIX}/apps/job-search-loop/scripts/setup-profile.sh", names
                )
                self.assertIn(
                    f"{PREFIX}/runtime/agent-runner/agent_runner.py", names
                )
                self.assertFalse(
                    any(name.startswith(f"{PREFIX}/docs/") for name in names)
                )
                self.assertFalse(any("/.local/state/" in name for name in names))
                for member in members:
                    self.assertEqual(member.uid, 0)
                    self.assertEqual(member.gid, 0)
                    self.assertEqual(member.uname, "root")
                    self.assertEqual(member.gname, "root")
                    self.assertEqual(member.mtime, 0)
                installer = bundle.getmember(
                    f"{PREFIX}/apps/job-search-loop/scripts/install-local.sh"
                )
                self.assertEqual(installer.mode & 0o777, 0o755)
                release = json.loads(
                    bundle.extractfile(f"{PREFIX}/RELEASE.json")
                    .read()
                    .decode("utf-8")
                )
            expected_commit = subprocess.check_output(
                ["git", "rev-parse", "HEAD"],
                cwd=REPO_ROOT,
                text=True,
            ).strip()
            self.assertEqual(release["commit"], expected_commit)
            self.assertEqual(release["version"], VERSION)
            self.assertEqual(release["private_state_included"], False)

    def test_extracted_artifact_installs_in_clean_home(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            output = root / "release"
            built = self._build(output)
            self.assertEqual(built.returncode, 0, built.stderr)
            receipt = json.loads(built.stdout)
            archive = Path(receipt["archive"])
            self.assertEqual(
                hashlib.sha256(archive.read_bytes()).hexdigest(), receipt["sha256"]
            )
            extracted = root / "extracted"
            extracted.mkdir()
            with tarfile.open(archive, "r:gz") as bundle:
                bundle.extractall(extracted, filter="data")
            release_root = extracted / PREFIX
            app = release_root / "apps" / "job-search-loop"

            answers = root / "answers.json"
            answers.write_text(
                json.dumps(
                    {
                        "version": 1,
                        "candidate": {
                            "name": "Artifact Candidate",
                            "application_email": "artifact@example.test",
                        },
                        "facts": [
                            {
                                "id": "artifact-fact",
                                "claim": "Verified artifact fact.",
                                "evidence": "Synthetic E2E source",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            bin_dir = root / "bin"
            bin_dir.mkdir()
            codex = bin_dir / "codex"
            codex.write_text(
                "#!/bin/sh\n"
                'test "$1" = "login" && test "$2" = "status"\n',
                encoding="utf-8",
            )
            codex.chmod(0o700)
            home = root / "home"
            config = root / "config"
            state = root / "state"
            data = root / "data"
            env = {
                **os.environ,
                "HOME": str(home),
                "XDG_CONFIG_HOME": str(config),
                "XDG_STATE_HOME": str(state),
                "XDG_DATA_HOME": str(data),
                "PATH": f"{bin_dir}:/usr/bin:/bin",
            }
            authored = subprocess.run(
                [
                    "/bin/zsh",
                    str(app / "scripts" / "setup-profile.sh"),
                    "--answers",
                    str(answers),
                ],
                check=False,
                capture_output=True,
                text=True,
                env=env,
            )
            self.assertEqual(authored.returncode, 0, authored.stderr)
            profile = config / "anicca" / "job-search" / "profile.json"

            installed = subprocess.run(
                [
                    "/bin/zsh",
                    str(app / "scripts" / "install-local.sh"),
                    "--profile",
                    str(profile),
                    "--provider",
                    "auto",
                    "--scheduler",
                    "none",
                ],
                check=False,
                capture_output=True,
                text=True,
                env=env,
            )

            self.assertEqual(installed.returncode, 0, installed.stderr)
            install_receipt = json.loads(installed.stdout)
            self.assertEqual(install_receipt["provider"], "codex")
            self.assertEqual(install_receipt["scheduler"], "none")
            self.assertEqual(profile.stat().st_mode & 0o777, 0o600)
            self.assertEqual(
                (config / "anicca" / "job-search" / "install.json").stat().st_mode
                & 0o777,
                0o600,
            )
            self.assertTrue(
                (release_root / "runtime" / "agent-runner" / "agent_runner.py").is_file()
            )


if __name__ == "__main__":
    unittest.main()
