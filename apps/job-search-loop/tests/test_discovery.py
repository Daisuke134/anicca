import importlib
import json
import tempfile
import unittest
from pathlib import Path


class DiscoveryTests(unittest.TestCase):
    def _module(self):
        try:
            return importlib.import_module("job_search_loop.discovery")
        except ModuleNotFoundError:
            self.fail("job_search_loop.discovery is missing")

    def _provider(self, module, root, name, *, returncode, payload=None):
        executable = root / name
        marker = root / f"{name}.called"
        stdout = json.dumps(payload) if payload is not None else ""
        executable.write_text(
            f"""#!/bin/zsh
print called > {marker}
print -r -- {json.dumps(stdout)}
exit {returncode}
""",
            encoding="utf-8",
        )
        executable.chmod(0o700)
        return module.Provider(name=name, command=(str(executable),)), marker

    def test_primary_failure_still_runs_every_free_fallback(self):
        module = self._module()
        search = getattr(module, "search_jobs", None)
        self.assertIsNotNone(search)

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            firecrawl, firecrawl_marker = self._provider(
                module, root, "firecrawl", returncode=1
            )
            freehire, freehire_marker = self._provider(
                module,
                root,
                "freehire",
                returncode=0,
                payload={
                    "meta": {"count": 1},
                    "results": [
                        {
                            "id": "dream-1",
                            "title": "AI Agent Product Engineer",
                            "company": "Dream AI",
                            "location": "Remote",
                            "url": "https://jobs.example/dream-1",
                        }
                    ],
                },
            )
            linkedin, linkedin_marker = self._provider(
                module,
                root,
                "linkedin",
                returncode=0,
                payload={
                    "meta": {"count": 1},
                    "results": [
                        {
                            "id": "dream-2",
                            "title": "AI Partnerships",
                            "company": "Crypto Agents",
                            "location": "Tokyo",
                            "url": "https://jobs.example/dream-2",
                        }
                    ],
                },
            )

            result = search(
                "AI agent crypto",
                providers=(firecrawl, freehire, linkedin),
                timeout_seconds=5,
            )

            self.assertTrue(firecrawl_marker.exists())
            self.assertTrue(freehire_marker.exists())
            self.assertTrue(linkedin_marker.exists())
            self.assertEqual(
                [row["status"] for row in result["providers"]],
                ["failed", "success", "success"],
            )
            self.assertEqual(result["usable_result_count"], 2)
            self.assertEqual(result["status"], "usable")
            self.assertFalse(result["requires_browser_fallback"])

    def test_all_automated_sources_exhaust_to_browser_instead_of_blocked(self):
        module = self._module()
        search = getattr(module, "search_jobs", None)
        self.assertIsNotNone(search)

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            failed, failed_marker = self._provider(
                module, root, "failed", returncode=1
            )
            empty, empty_marker = self._provider(
                module,
                root,
                "empty",
                returncode=0,
                payload={"meta": {"count": 0}, "results": []},
            )

            result = search(
                "AI agent",
                providers=(failed, empty),
                timeout_seconds=5,
            )

            self.assertTrue(failed_marker.exists())
            self.assertTrue(empty_marker.exists())
            self.assertEqual(result["usable_result_count"], 0)
            self.assertEqual(result["status"], "browser_fallback_required")
            self.assertTrue(result["requires_browser_fallback"])
            self.assertNotEqual(result["status"], "blocked")


if __name__ == "__main__":
    unittest.main()
