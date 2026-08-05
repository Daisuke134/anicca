import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LOCK = ROOT / "config" / "upstream-lock.v1.json"
ADOPTION = ROOT / "config" / "upstream-adoption.v1.json"
MASTER_DELTA = ROOT / "config" / "upstream-master-delta.v1.json"


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

    def test_career_ops_v1250_is_content_addressed_and_licensed(self):
        data = json.loads(LOCK.read_text(encoding="utf-8"))
        self.assertIn("santifer-career-ops", data["upstreams"])
        upstream = data["upstreams"]["santifer-career-ops"]

        self.assertEqual(upstream["repository"], "https://github.com/santifer/career-ops")
        self.assertEqual(upstream["package_version"], "1.25.0")
        self.assertEqual(upstream["release"], "career-ops-v1.25.0")
        self.assertEqual(upstream["commit_sha"], "ae1a92dd1a4d299e637ce5d96f18e79f743a50ba")
        self.assertEqual(upstream["tree_sha"], "f0003d2870570efbb4595997d85bcb16e9586814")
        self.assertEqual(upstream["file_count"], 965)
        self.assertEqual(
            upstream["archive"],
            {
                "url": "https://api.github.com/repos/santifer/career-ops/tarball/ae1a92dd1a4d299e637ce5d96f18e79f743a50ba",
                "content_sha256": "65762e626ac69d83880b361a882ea4714387025940643ed03b4cd2481b555234",
            },
        )
        self.assertEqual(upstream["license"]["spdx"], "MIT")
        self.assertEqual(upstream["license"]["blob_sha"], "89c4ce0ad6b1db98d827ddd9725da5efdff55997")
        self.assertEqual(
            upstream["license"]["content_sha256"],
            "51989d2589b2aa87ca6cbb253391bcb476a21cbafdc71eea4410548538510870",
        )
        self.assertEqual(
            upstream["files"],
            {
                "LICENSE": {
                    "blob_sha": "89c4ce0ad6b1db98d827ddd9725da5efdff55997",
                    "content_sha256": "51989d2589b2aa87ca6cbb253391bcb476a21cbafdc71eea4410548538510870",
                    "size": 1090,
                },
                "README.md": {
                    "blob_sha": "bd87484929cdd45d611c3d2860e6f658730d427d",
                    "content_sha256": "0293b375b7cea0d8f7c70ea65a6567c5071317d9262a6ff4eae562188b17a4ec",
                    "size": 31737,
                },
                "docs/APPLY_AUTOFILL.md": {
                    "blob_sha": "43afc62bd3c2fb7ff8d939e5f3d115c01e2f8ee6",
                    "content_sha256": "05e2734a6f80b89adfa0297c41fa56e2c8f188b6c240b363a65a21ac98559551",
                    "size": 4186,
                },
                "package.json": {
                    "blob_sha": "aa157b12e6b6c26da9ac912ad348111a5cbdd9f4",
                    "content_sha256": "c30dd080f4e1b54520dea0779d79cdc08f61512702000d8047276a5301708a77",
                    "size": 3635,
                },
            },
        )
        self.assertEqual(
            upstream["sources"]["release"],
            "https://github.com/santifer/career-ops/releases/tag/career-ops-v1.25.0",
        )
        self.assertEqual(
            upstream["sources"]["license"],
            "https://github.com/santifer/career-ops/blob/career-ops-v1.25.0/LICENSE",
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

    def test_master_delta_is_recorded_without_automatic_activation(self):
        data = json.loads(MASTER_DELTA.read_text(encoding="utf-8"))
        self.assertEqual(data["base_release"], "v1.3.0")
        self.assertEqual(data["base_commit"], "a8a10011126f443e0041bb4924a1106c2f7f7536")
        self.assertEqual(data["master_commit"], "fcefb8150fb073ae0d86b5b7a6f09e94aa5976ee")
        self.assertEqual(data["ahead_by"], 3)
        self.assertEqual(data["changed_file_count"], 13)
        self.assertFalse(data["auto_activate"])

        candidates = {item["id"]: item for item in data["candidates"]}
        self.assertEqual(
            set(candidates),
            {"rank_language_gate_regression_tests", "robots_aware_web_research"},
        )
        for item in candidates.values():
            self.assertEqual(item["decision"], "port_later")
            self.assertTrue(item["source_commits"])
            self.assertTrue(item["changed_paths"])
            self.assertRegex(item["owner_task"], r"^L-\d+[A-Z]?$|^L-\d+\u2013L-\d+$")


if __name__ == "__main__":
    unittest.main()
