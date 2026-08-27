from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "chinese_source_collect.py"


class ChineseSourceCollectTests(unittest.TestCase):
    def load_module(self):
        self.assertTrue(SCRIPT.is_file(), f"missing collector: {SCRIPT}")
        spec = importlib.util.spec_from_file_location("chinese_source_collect", SCRIPT)
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        return module

    def test_decodes_allowed_results_and_deduplicates_urls(self) -> None:
        module = self.load_module()
        html = """
        <a class="result__a" href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fwww.xiaohongshu.com%2Fexplore%2Fabc">XHS AI workflow</a>
        <a class="result__snippet">A Chinese creator describes a three-step AI workflow.</a>
        <a class="result__a" href="https://www.xiaohongshu.com/explore/abc">duplicate</a>
        <a class="result__snippet">Duplicate result.</a>
        <a class="result__a" href="https://www.bilibili.com/video/BV1abc">Bilibili agent test</a>
        <a class="result__snippet">An agent test with a concrete recovery condition.</a>
        <a class="result__a" href="https://example.com/not-allowed">Other site</a>
        <a class="result__snippet">This must not enter the receipt.</a>
        """

        receipt = module.collect(html, "AI agent workflow", "2026-08-27T00:00:00Z")

        self.assertEqual(receipt["candidate_count"], 2)
        self.assertEqual(
            [row["url"] for row in receipt["candidates"]],
            [
                "https://www.xiaohongshu.com/explore/abc",
                "https://www.bilibili.com/video/BV1abc",
            ],
        )
        self.assertEqual(receipt["candidates"][0]["source_domain"], "xiaohongshu.com")
        self.assertEqual(receipt["candidates"][0]["source_language"], "zh")
        self.assertEqual(receipt["observed_at"], "2026-08-27T00:00:00Z")

    def test_supports_each_configured_chinese_platform_domain(self) -> None:
        module = self.load_module()
        urls = [
            "https://xiaohongshu.com/explore/1",
            "https://douyin.com/video/2",
            "https://kuaishou.com/short-video/3",
            "https://bilibili.com/video/4",
            "https://weibo.com/5/6",
            "https://tieba.baidu.com/p/7",
            "https://zhihu.com/question/8",
        ]
        html = "".join(
            f'<a class="result__a" href="{url}">Title {index}</a>'
            f'<a class="result__snippet">Snippet {index}</a>'
            for index, url in enumerate(urls)
        )

        receipt = module.collect(html, "AI", "2026-08-27T00:00:00Z")

        self.assertEqual(receipt["candidate_count"], 7)


if __name__ == "__main__":
    unittest.main()
