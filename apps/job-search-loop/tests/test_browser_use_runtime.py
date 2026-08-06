import tempfile
import os
import subprocess
import unittest
from pathlib import Path

from job_search_loop.browser_use_runtime import browser_use_runtime_python, bootstrap_browser_use_runtime


class BrowserUseRuntimeTests(unittest.TestCase):
    def test_runtime_paths_prefers_verified_browser_use_python(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            python = browser_use_runtime_python(root)
            python.parent.mkdir(parents=True)
            python.write_text("#!/bin/sh\n", encoding="utf-8")
            python.chmod(0o700)
            script = Path(__file__).parents[1] / "scripts" / "runtime-paths.sh"
            result = subprocess.run(
                ["/bin/zsh", "-c", f'source "{script}"; print -r -- "$JOB_SEARCH_PYTHON"'],
                check=False,
                capture_output=True,
                text=True,
                env={
                    key: value
                    for key, value in os.environ.items()
                    if key not in {"JOB_SEARCH_PYTHON", "JOB_SEARCH_FRAMEWORK_ROOT"}
                }
                | {
                    "JOB_SEARCH_FRAMEWORK_ROOT": str(root),
                    "JOB_SEARCH_BROWSER_USE_RUNTIME_ROOT": str(root),
                },
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout.strip(), str(python))

    def test_installer_bootstraps_browser_use_before_local_setup(self):
        script = (Path(__file__).parents[1] / "scripts" / "install-local.sh").read_text(
            encoding="utf-8"
        )
        self.assertIn("bootstrap-browser-use.sh", script)
        self.assertLess(script.index("bootstrap-browser-use.sh"), script.index("job_search_loop.local_setup"))

    def test_bootstrap_resolves_uv_from_path_by_default(self):
        script = (
            Path(__file__).parents[1] / "scripts" / "bootstrap-browser-use.sh"
        ).read_text(encoding="utf-8")
        self.assertIn("command -v uv", script)

    def test_bootstrap_uses_python312_and_hash_locked_sync(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            lock = root / "browser-use.lock"
            lock.write_text("browser-use==0.13.7 --hash=sha256:abc\n", encoding="utf-8")
            calls = []

            def command_runner(arguments):
                calls.append([str(item) for item in arguments])
                if arguments[1] == "venv":
                    python = Path(arguments[-1]) / "bin" / "python"
                    python.parent.mkdir(parents=True)
                    python.write_text("fixture", encoding="utf-8")
                    python.chmod(0o700)
                    return ""
                if arguments[1:3] == ["pip", "sync"]:
                    return ""
                if arguments[0].name == "python":
                    return "0.13.7\n"
                raise AssertionError(arguments)

            python = bootstrap_browser_use_runtime(
                runtime_root=root / "runtime",
                lock_path=lock,
                uv_path=Path("/fixture/uv"),
                command_runner=command_runner,
            )

            self.assertEqual(python, browser_use_runtime_python(root / "runtime"))
            self.assertEqual(calls[0][1:4], ["venv", "--python", "3.12"])
            self.assertEqual(calls[1][1:3], ["pip", "sync"])
            self.assertIn("--require-hashes", calls[1])
            self.assertIn(str(lock), calls[1])
            self.assertEqual(calls[-1][0], str(python))

    def test_bootstrap_reuses_only_an_exact_valid_runtime(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            python = browser_use_runtime_python(root)
            python.parent.mkdir(parents=True)
            python.write_text("fixture", encoding="utf-8")
            python.chmod(0o700)
            calls = []

            def command_runner(arguments):
                calls.append([str(item) for item in arguments])
                if Path(arguments[0]) == python:
                    return "0.13.7\n"
                raise AssertionError("valid runtime must not be rebuilt")

            result = bootstrap_browser_use_runtime(
                runtime_root=root,
                lock_path=root / "unused.lock",
                uv_path=Path("/fixture/uv"),
                command_runner=command_runner,
            )

            self.assertEqual(result, python)
            self.assertEqual(len(calls), 1)


if __name__ == "__main__":
    unittest.main()
