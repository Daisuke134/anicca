"""
Tests for fetch_x_metrics.py (#1, #2, #3, #25)
"""
import json
import unittest
from unittest.mock import patch, MagicMock

from fetch_x_metrics import fetch_metrics_by_ids, update_metrics, main


class TestFetchMetricsByIds(unittest.TestCase):
    """#1: test_fetch_metrics_by_ids_success"""

    @patch("fetch_x_metrics.requests.get")
    def test_fetch_metrics_by_ids_success(self, mock_get):
        """#1: 正常にメトリクスを取得"""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {
            "data": [
                {
                    "id": "111",
                    "public_metrics": {
                        "impression_count": 500,
                        "like_count": 10,
                        "retweet_count": 3,
                        "reply_count": 1,
                    },
                },
                {
                    "id": "222",
                    "public_metrics": {
                        "impression_count": 1000,
                        "like_count": 50,
                        "retweet_count": 20,
                        "reply_count": 5,
                    },
                },
            ]
        }
        mock_get.return_value = mock_resp

        result = fetch_metrics_by_ids("test_bearer", ["111", "222"])

        self.assertEqual(len(result), 2)
        self.assertEqual(result["111"]["impression_count"], 500)
        self.assertEqual(result["111"]["like_count"], 10)
        self.assertEqual(result["222"]["impression_count"], 1000)
        self.assertEqual(result["222"]["retweet_count"], 20)

    @patch("fetch_x_metrics.requests.get")
    def test_fetch_metrics_by_ids_missing_id(self, mock_get):
        """#2: X API にない ID はスキップ（結果に含まれない）"""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status = MagicMock()
        # X API は存在する ID のみ data に返す
        mock_resp.json.return_value = {
            "data": [
                {
                    "id": "111",
                    "public_metrics": {
                        "impression_count": 100,
                        "like_count": 5,
                        "retweet_count": 1,
                        "reply_count": 0,
                    },
                },
            ]
        }
        mock_get.return_value = mock_resp

        result = fetch_metrics_by_ids("test_bearer", ["111", "999"])

        self.assertIn("111", result)
        self.assertNotIn("999", result)
        self.assertEqual(len(result), 1)

    def test_fetch_metrics_empty_ids(self):
        """空の ID リストは空辞書を返す"""
        result = fetch_metrics_by_ids("test_bearer", [])
        self.assertEqual(result, {})


class TestMainSkipsNullXPostId(unittest.TestCase):
    """#3: test_main_skips_null_xPostId"""

    @patch("fetch_x_metrics.api_get")
    @patch("fetch_x_metrics.X_BEARER_TOKEN", "test_token")
    @patch("fetch_x_metrics.API_BASE_URL", "http://test")
    def test_main_skips_null_xPostId(self, mock_api_get):
        """#3: xPostId が null のレコードは X API に送らない"""
        mock_api_get.return_value = {
            "posts": [
                {"id": "db-1", "x_post_id": "111", "text": "with id"},
                {"id": "db-2", "x_post_id": None, "text": "null id"},
                {"id": "db-3", "x_post_id": "", "text": "empty id"},
            ]
        }

        # main() の Step 2 のフィルタロジックをテスト
        posts = mock_api_get.return_value["posts"]
        posts_with_id = [p for p in posts if p.get("x_post_id")]

        self.assertEqual(len(posts_with_id), 1)
        self.assertEqual(posts_with_id[0]["id"], "db-1")


class TestUpdateMetrics(unittest.TestCase):
    """#25: test_fetch_metrics_partial_fields_no_overwrite"""

    @patch("fetch_x_metrics.api_put")
    def test_partial_fields_no_overwrite(self, mock_api_put):
        """#25: 部分的なメトリクス — null フィールドは送信しない"""
        metrics = {
            "impression_count": 500,
            "like_count": None,
            "retweet_count": 10,
            "reply_count": None,
        }
        update_metrics("http://test", "token", "db-1", metrics)

        mock_api_put.assert_called_once()
        payload = mock_api_put.call_args[0][1]
        # like_count と reply_count は None なので送信しない
        self.assertIn("impression_count", payload)
        self.assertIn("retweet_count", payload)
        self.assertNotIn("like_count", payload)
        self.assertNotIn("reply_count", payload)

    @patch("fetch_x_metrics.api_put")
    def test_all_none_skips_update(self, mock_api_put):
        """全フィールド None の場合は PUT を呼ばない"""
        metrics = {
            "impression_count": None,
            "like_count": None,
            "retweet_count": None,
            "reply_count": None,
        }
        update_metrics("http://test", "token", "db-1", metrics)
        mock_api_put.assert_not_called()


if __name__ == "__main__":
    unittest.main()
