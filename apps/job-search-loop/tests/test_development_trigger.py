import json
import tempfile
import unittest
from pathlib import Path


class DevelopmentTriggerTests(unittest.TestCase):
    def test_request_rejects_broad_mode_symlink_and_stale_commit(self):
        from job_search_loop import development_trigger

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            release = root / "RELEASE.json"
            release.write_text(json.dumps({"commit": "c" * 40}), encoding="utf-8")
            request = root / "development-kickstart.request"
            output = root / "receipt.json"
            development_trigger.create_request(request, release)
            request.chmod(0o644)
            with self.assertRaisesRegex(ValueError, "mode 0600"):
                development_trigger.consume_request(
                    request=request,
                    release=release,
                    output=output,
                    uid=501,
                    label="ai.anicca.job-search-daily",
                )
            request.unlink()
            request.symlink_to(release)
            with self.assertRaisesRegex(ValueError, "regular file"):
                development_trigger.consume_request(
                    request=request,
                    release=release,
                    output=output,
                    uid=501,
                    label="ai.anicca.job-search-daily",
                )
            request.unlink()
            development_trigger.create_request(request, release)
            release.write_text(json.dumps({"commit": "d" * 40}), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "does not match"):
                development_trigger.consume_request(
                    request=request,
                    release=release,
                    output=output,
                    uid=501,
                    label="ai.anicca.job-search-daily",
                )

    def test_commit_bound_request_kicks_idle_owner_once_without_kill(self):
        from job_search_loop import development_trigger

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            commit = "a" * 40
            release = root / "RELEASE.json"
            release.write_text(json.dumps({"commit": commit}), encoding="utf-8")
            request = root / "development-kickstart.request"
            output = root / "receipt.json"
            calls = []

            def launchctl(arguments):
                calls.append(arguments)
                if arguments[0] == "print":
                    return 0, "    state = not running\n"
                return 0, ""

            development_trigger.create_request(request, release)
            receipt = development_trigger.consume_request(
                request=request,
                release=release,
                output=output,
                uid=501,
                label="ai.anicca.job-search-daily",
                launchctl=launchctl,
            )

            self.assertFalse(request.exists())
            self.assertEqual(receipt["status"], "kicked")
            self.assertEqual(
                calls,
                [
                    ["print", "gui/501/ai.anicca.job-search-daily"],
                    ["kickstart", "gui/501/ai.anicca.job-search-daily"],
                ],
            )
            self.assertEqual(json.loads(output.read_text()), receipt)
            self.assertEqual(output.stat().st_mode & 0o777, 0o600)

    def test_running_owner_preserves_request_and_never_kills_it(self):
        from job_search_loop import development_trigger

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            commit = "b" * 40
            release = root / "RELEASE.json"
            release.write_text(json.dumps({"commit": commit}), encoding="utf-8")
            request = root / "development-kickstart.request"
            output = root / "receipt.json"
            calls = []

            def launchctl(arguments):
                calls.append(arguments)
                return 0, "    state = running\n"

            development_trigger.create_request(request, release)
            receipt = development_trigger.consume_request(
                request=request,
                release=release,
                output=output,
                uid=501,
                label="ai.anicca.job-search-daily",
                launchctl=launchctl,
            )

            self.assertEqual(receipt["status"], "owner_running")
            self.assertTrue(request.is_file())
            self.assertEqual(calls, [["print", "gui/501/ai.anicca.job-search-daily"]])
