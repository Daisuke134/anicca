import json
import plistlib
import subprocess
import tarfile
import tempfile
import unittest
from pathlib import Path

from runtime.loop.lm_loop_apply import build_apply_plan, install_one


ROOT = Path(__file__).resolve().parents[3]


class CleanUserInstallTest(unittest.TestCase):
    def test_public_archive_contains_general_agent_release_contract(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            release = root / "release"
            release.mkdir()
            archive = root / "release.tar"
            tree = subprocess.run(
                ["git", "write-tree"], cwd=ROOT, check=True,
                capture_output=True, text=True).stdout.strip()
            subprocess.run(
                [
                    "git", "archive", "--format=tar", "-o", str(archive), tree,
                    "README.md", "LICENSE", "THIRD_PARTY_NOTICES.md",
                    "apps/life-manager/.env.example",
                    "skills/earn/gig/config/provider-capability.example.json",
                ],
                cwd=ROOT, check=True)
            with tarfile.open(archive) as handle:
                handle.extractall(release)

            manifest = json.loads((
                release / "skills/earn/gig/config/provider-capability.example.json"
            ).read_text())
            self.assertEqual(manifest["capability"], "marketplace.application")
            self.assertEqual(manifest["effect"]["replay"], "zero")

            env_lines = (release / "apps/life-manager/.env.example").read_text().splitlines()
            refs = [line.split("=", 1)[1] for line in env_lines
                    if line and not line.startswith("#") and line.split("=", 1)[0].endswith("_REF")]
            self.assertTrue(refs)
            self.assertTrue(all(value.startswith("secret://") for value in refs))

            readme = (release / "README.md").read_text()
            self.assertIn("### Use it — cloud", readme)
            self.assertTrue((release / "LICENSE").is_file())

            notices = (release / "THIRD_PARTY_NOTICES.md").read_text()
            for project, license_name in (
                ("DeepAgentsJS", "MIT"),
                ("browser-use", "MIT"),
                ("OpenClaw", "MIT"),
                ("Steel Browser", "Apache-2.0"),
            ):
                self.assertIn(project, notices)
                self.assertIn(license_name, notices)
            self.assertIn("No source code from these projects is vendored", notices)

    def test_clean_user_installs_every_generated_job_without_starting_workloads(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            release = root / "release"
            release.mkdir()
            archive = root / "release.tar"
            sha = subprocess.run(
                ["git", "rev-parse", "HEAD"], cwd=ROOT, check=True,
                capture_output=True, text=True).stdout.strip()
            subprocess.run(
                ["git", "archive", "--format=tar", "-o", str(archive), sha],
                cwd=ROOT, check=True)
            with tarfile.open(archive) as handle:
                handle.extractall(release)
            (release / "RELEASE.json").write_text(json.dumps({"sha": sha}))
            for dependency in ("playwright-core", "jsqr"):
                package = release / "apps/life-manager/node_modules" / dependency / "package.json"
                package.parent.mkdir(parents=True)
                package.write_text("{}\n")
            registry = json.loads((release / "config/loop-registry.json").read_text())
            plan = build_apply_plan(registry, release, sha)
            agents = root / "home/Library/LaunchAgents"
            loaded = {}

            def launchctl(args):
                action = args[0]
                if action == "print":
                    label = args[1].rsplit("/", 1)[-1]
                    argv = loaded.get(label)
                    if argv is None:
                        return 1, "not loaded"
                    return 0, "arguments = {\n" + "\n".join(argv) + "\n}\n"
                if action == "bootout":
                    loaded.pop(args[1].rsplit("/", 1)[-1], None)
                    return 0, ""
                if action == "bootstrap":
                    with open(args[2], "rb") as handle:
                        plist = plistlib.load(handle)
                    loaded[plist["Label"]] = list(map(str, plist["ProgramArguments"]))
                    return 0, ""
                raise AssertionError(args)

            results = []
            for item in plan:
                results.append(install_one(
                    item, agents / f"{item['label']}.plist", launchctl,
                    attempts=1, sleeper=lambda _seconds: None))

            self.assertEqual(len(results), len(registry["loops"]))
            self.assertTrue(all(row["ok"] for row in results))
            self.assertEqual(len(list(agents.glob("*.plist"))), len(registry["loops"]))
            self.assertEqual(len(loaded), len(registry["loops"]))


if __name__ == "__main__":
    unittest.main()
