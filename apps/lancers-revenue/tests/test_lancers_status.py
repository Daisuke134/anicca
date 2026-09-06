import importlib.util
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


REPO_ROOT = Path(__file__).resolve().parents[3]
STATUS_PATH = REPO_ROOT / "skills/earn/lancers/scripts/status.py"


def _load_status():
    spec = importlib.util.spec_from_file_location("test_canonical_lancers_status", STATUS_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("canonical_lancers_status_unavailable")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


SEARCH_HTML = """
<div class="p-search-job-media"><a class="p-search-job-media__title" href="/work/detail/1000001">月次SNS運用</a><div class="js-job-show-description">高額teaser</div><div class="p-search-job__division">SNS運用</div><div class="p-search-job-media__price"><span class="c-badge__text">プロジェクト</span><span class="p-search-job-media__number">98,000</span><span class="p-search-job-media__number">120,000</span></div></div>
<div class="p-search-job-media"><a class="p-search-job-media__title" href="/work/detail/1000002">低額SNS運用</a><div class="js-job-show-description">低額teaser</div><div class="p-search-job__division">SNS運用</div><div class="p-search-job-media__price"><span class="c-badge__text">プロジェクト</span><span class="p-search-job-media__number">50,000</span><span class="p-search-job-media__number">97,999</span></div></div>
<div class="p-search-job-media"><a class="p-search-job-media__title" href="/work/detail/1000003">取得失敗SNS運用</a><div class="js-job-show-description">失敗teaser</div><div class="p-search-job__division">SNS運用</div><div class="p-search-job-media__price"><span class="c-badge__text">プロジェクト</span><span class="p-search-job-media__number">98,000</span></div></div>
<div class="p-search-job-media"><a class="p-search-job-media__title" href="/work/detail/1000004">検索上限外</a><div class="js-job-show-description">上限外teaser</div><div class="p-search-job__division">SNS運用</div><div class="p-search-job-media__price"><span class="c-badge__text">プロジェクト</span><span class="p-search-job-media__number">200,000</span></div></div>
"""

DETAIL_HTML = """
<dl><dt>依頼主の業種</dt><dd>情報通信業</dd><dt>依頼概要</dt><dd>SNS運用を毎月、外部委託でお願いしたいです。</dd></dl>
"""


class LancersStatusTests(unittest.TestCase):
    def test_every_card_in_the_page_is_enriched_and_failures_remain_teasers(self):
        status = _load_status()
        requested = []

        def detail_fetcher(*, timeout, _detail_url, **_kwargs):
            requested.append((_detail_url, timeout))
            if _detail_url.endswith("1000003"):
                raise status.LancersProviderError("lancers_network_error")
            return DETAIL_HTML

        with patch.object(status, "fetch_public_html", side_effect=detail_fetcher):
            result = status.run_discovery(
                query="SNS運用",
                limit=3,
                timeout=1,
                fetcher=lambda **_kwargs: SEARCH_HTML,
                observed_at="2026-08-13T12:00:00Z",
            )

        self.assertTrue(result["ok"])
        # Every card inside the page limit is enriched. The 98,000 teaser floor that used to skip
        # cheap cards was removed deliberately in 02e1e5494 "plan from full project details": the
        # search teaser is not a reliable budget, so judging on it rejected work the planner could
        # have taken. 1000004 is absent because limit=3 bounds the page, not because of its price.
        self.assertEqual(
            requested,
            [
                ("https://www.lancers.jp/work/detail/1000001", 1.0),
                ("https://www.lancers.jp/work/detail/1000002", 1.0),
                ("https://www.lancers.jp/work/detail/1000003", 1.0),
            ],
        )
        descriptions = {row["external_id"]: row["description"] for row in result["opportunities"]}
        detail = "依頼主の業種: 情報通信業\n依頼概要: SNS運用を毎月、外部委託でお願いしたいです。"
        self.assertEqual(descriptions["1000001"], detail)
        self.assertEqual(descriptions["1000002"], detail)
        # A detail fetch that fails leaves the card on its teaser rather than dropping it or
        # inventing a description.
        self.assertEqual(descriptions["1000003"], "失敗teaser")
        self.assertEqual(result["detail_enriched_count"], 2)
        self.assertEqual(result["detail_failed_count"], 1)


if __name__ == "__main__":
    unittest.main()
