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
