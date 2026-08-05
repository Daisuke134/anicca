import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LOCK = ROOT / "config" / "upstream-lock.v1.json"
ADOPTION = ROOT / "config" / "upstream-adoption.v1.json"


class UpstreamLockTests(unittest.TestCase):
    def test_ai_job_search_v130_is_content_addressed_and_licensed(self):
        data = json.loads(LOCK.read_text(encoding="utf-8"))
        upstream = data["upstreams"]["mads-lorentzen-ai-job-search"]

        self.assertEqual(upstream["repository"], "https://github.com/MadsLorentzen/ai-job-search")
        self.assertEqual(upstream["release"], "v1.3.0")
        self.assertEqual(upstream["commit_sha"], "a8a10011126f443e0041bb4924a1106c2f7f7536")
        self.assertEqual(upstream["tree_sha"], "dd84a322610becd7c46b74f823d1e4ebc1c8432d")
        self.assertEqual(upstream["license"]["spdx"], "MIT")
        self.assertEqual(upstream["license"]["blob_sha"], "dd86a45cbf864dd2cd82df06064cb8cc9aef995a")
        self.assertEqual(
            upstream["license"]["content_sha256"],
            "accbf0accb87b7b905dd7ee0c7013075f0453637acf354ddae6fc0e4d8282e8e",
        )
        self.assertEqual(
            upstream["sources"]["release"],
            "https://github.com/MadsLorentzen/ai-job-search/releases/tag/v1.3.0",
        )
        self.assertEqual(
            upstream["sources"]["license"],
            "https://github.com/MadsLorentzen/ai-job-search/blob/v1.3.0/LICENSE",
        )

    def test_every_v130_component_has_one_explicit_adoption_decision(self):
        data = json.loads(ADOPTION.read_text(encoding="utf-8"))
        self.assertEqual(data["upstream_release"], "v1.3.0")
        self.assertEqual(
            data["upstream_commit"],
            "a8a10011126f443e0041bb4924a1106c2f7f7536",
        )

        components = data["components"]
        expected = {
            "profile_setup", "job_scraper", "rank", "apply", "outcome",
            "gmail_sync", "interview", "upskill", "html_report", "notion_sync",
            "portal_freehire", "portal_jobbank", "portal_jobdanmark",
            "portal_jobindex", "portal_jobnet", "portal_linkedin", "add_portal",
            "add_template", "expand", "reset", "salary_lookup", "latex_assets",
            "security_tooling", "upstream_update_tooling", "upstream_tests",
            "project_documentation", "claude_runtime_binding",
        }
        self.assertEqual({item["id"] for item in components}, expected)
        self.assertEqual(len(components), len(expected))

        for item in components:
            self.assertIn(item["decision"], {"reuse", "adapt", "supersede"})
            self.assertTrue(item["source_paths"])
            self.assertTrue(item["reason"].strip())
            self.assertTrue(item["local_contract"].strip())
            self.assertRegex(item["owner_task"], r"^L-\d+[A-Z]?$|^none$")


if __name__ == "__main__":
    unittest.main()
