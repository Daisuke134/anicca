from __future__ import annotations

import importlib.util
import subprocess
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


SCRIPT = Path(__file__).parents[1] / "scripts" / "chinese_source_collect.py"


class ChineseSourceCollectTests(unittest.TestCase):
    def test_discovery_falls_back_to_duckduckgo_over_scrapy(self) -> None:
        module = self.load_module()

        def run(command, **_kwargs):
            if command[:2] == ["crwl", "crawl"] and "search_result" in command[2]:
                raise subprocess.TimeoutExpired(command, 60)
            if command[:2] == ["scrapy", "fetch"]:
                return SimpleNamespace(returncode=0, stdout=(
                    '<a class="result__a" href="//duckduckgo.com/l/?uddg='
                    'https%3A%2F%2Fwww.xiaohongshu.com%2Fexplore%2Fabc">Workflow</a>'
                    '<a class="result__snippet">具体的なAI手順</a>'
                ))
            if command[:2] == ["crwl", "crawl"]:
                return SimpleNamespace(
                    returncode=0,
                    stdout="这是一个可重复执行的人工智能工作流，包含失败恢复条件和具体步骤。",
                )
            return SimpleNamespace(returncode=1, stdout="")

        with tempfile.TemporaryDirectory() as root:
            query_file = Path(root) / "queries.txt"
            query_file.write_text(
                "AI Agent\thttps://www.xiaohongshu.com/search_result?keyword=AI\n"
            )
            with patch.object(module.subprocess, "run", side_effect=run):
                receipt = module.discover(query_file, "2026-08-28T00:00:00Z")

        self.assertEqual(receipt["candidate_count"], 1)
        self.assertEqual(
            receipt["candidates"][0]["url"],
            "https://www.xiaohongshu.com/explore/abc",
        )

    def test_discovery_continues_after_one_source_times_out(self) -> None:
        module = self.load_module()
        calls = []

        def run(command, **_kwargs):
            url = command[2]
            calls.append(url)
            if "xiaohongshu.com/search" in url:
                raise subprocess.TimeoutExpired(command, 60)
            if "search.bilibili.com" in url:
                return SimpleNamespace(returncode=0, stdout=(
                    "## [Agent workflow](https://www.bilibili.com/video/BV1abc)\n"
                ))
            if url == "https://www.bilibili.com/video/BV1abc":
                return SimpleNamespace(
                    returncode=0,
                    stdout="这是一个可重复执行的人工智能工作流，包含失败恢复条件和具体步骤。",
                )
            return SimpleNamespace(returncode=1, stdout="")

        with tempfile.TemporaryDirectory() as root:
            query_file = Path(root) / "queries.txt"
            query_file.write_text(
                "AI\thttps://www.xiaohongshu.com/search_result?keyword=AI\n"
                "Agent\thttps://search.bilibili.com/all?keyword=Agent\n"
            )
            with patch.object(module.subprocess, "run", side_effect=run):
                receipt = module.discover(query_file, "2026-08-28T00:00:00Z")

        self.assertEqual(receipt["candidate_count"], 1)
        self.assertIn("https://search.bilibili.com/all?keyword=Agent", calls)

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

    def test_decodes_allowed_results_from_crwl_markdown(self) -> None:
        module = self.load_module()
        markdown = """
## [Bilibili agent workflow](https://duckduckgo.com/l/?uddg=https%3A%2F%2Fwww.bilibili.com%2Fvideo%2FBV1abc&rut=one)
[www.bilibili.com/video/BV1abc](https://duckduckgo.com/l/?uddg=https%3A%2F%2Fwww.bilibili.com%2Fvideo%2FBV1abc&rut=two)
## [Bilibili ad tracker](https://cm.bilibili.com/cm/api/fees/pc/sync/v2?msg=ad)
## [Unrelated](https://duckduckgo.com/l/?uddg=https%3A%2F%2Fexample.com%2Fpost&rut=three)
"""

        receipt = module.collect_markdown(markdown, "AI agent", "2026-08-27T00:00:00Z")

        self.assertEqual(receipt["candidate_count"], 1)
        self.assertEqual(receipt["candidates"][0]["url"], "https://www.bilibili.com/video/BV1abc")
        self.assertEqual(receipt["candidates"][0]["title"], "Bilibili agent workflow")

    def test_parses_public_search_specs_without_treating_urls_as_queries(self) -> None:
        module = self.load_module()
        specs = module.parse_search_specs("""
        # comment
        AI Agent 实战\thttps://search.bilibili.com/all?keyword=AI%20Agent
        AI 工具\thttps://www.zhihu.com/search?type=content&q=AI%20Agent
        """)

        self.assertEqual(specs, [
            ("AI Agent 实战", "https://search.bilibili.com/all?keyword=AI%20Agent"),
            ("AI 工具", "https://www.zhihu.com/search?type=content&q=AI%20Agent"),
        ])

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

    def test_hydrate_keeps_only_candidates_with_direct_source_text(self) -> None:
        module = self.load_module()
        receipt = {
            "candidates": [
                {"url": "https://zhihu.com/question/1", "title": "Zhihu", "snippet": "index"},
                {"url": "https://bilibili.com/video/2", "title": "Bilibili", "snippet": "index"},
            ]
        }
        pages = {
            "https://zhihu.com/question/1": "这是从原始页面直接读取的具体 AI 工作流和失败恢复步骤。",
            "https://bilibili.com/video/2": "",
        }

        hydrated = module.hydrate(receipt, pages.get, limit=5)

        self.assertEqual(hydrated["candidate_count"], 1)
        self.assertEqual(hydrated["candidates"][0]["url"], "https://zhihu.com/question/1")
        self.assertEqual(hydrated["candidates"][0]["text"], pages["https://zhihu.com/question/1"])
        self.assertEqual(hydrated["candidates"][0]["handle"], "zhihu.com")
        self.assertEqual(hydrated["candidates"][0]["metrics"], {})

    def test_hydrate_never_attempts_more_sources_than_limit(self) -> None:
        module = self.load_module()
        attempted = []
        receipt = {"candidates": [
            {"url": f"https://zhihu.com/question/{index}", "title": str(index), "snippet": ""}
            for index in range(10)
        ]}

        def unavailable(url: str) -> str:
            attempted.append(url)
            return ""

        hydrated = module.hydrate(receipt, unavailable, limit=3)

        self.assertEqual(hydrated["candidate_count"], 0)
        self.assertEqual(len(attempted), 3)


if __name__ == "__main__":
    unittest.main()
