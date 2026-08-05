import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LOCK = ROOT / "config" / "upstream-lock.v1.json"


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


if __name__ == "__main__":
    unittest.main()
