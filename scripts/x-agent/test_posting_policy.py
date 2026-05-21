import unittest

from posting_policy import (
    MAX_CHARS_X,
    backoff_seconds,
    classify_http_status,
    should_retry,
    truncate_x_text,
)


class TestPostingPolicy(unittest.TestCase):
    def test_truncate_x_text_no_change(self):
        self.assertEqual(truncate_x_text('hello', MAX_CHARS_X), 'hello')

    def test_truncate_x_text_truncates_with_ellipsis(self):
        s = 'a' * (MAX_CHARS_X + 10)
        out = truncate_x_text(s)
        self.assertEqual(len(out), MAX_CHARS_X)
        self.assertTrue(out.endswith('...'))

    def test_classify_http_status(self):
        self.assertEqual(classify_http_status(401).category, 'AUTH')
        self.assertEqual(classify_http_status(403).category, 'PERMISSION')
        self.assertEqual(classify_http_status(429).category, 'RATE_LIMIT')
        self.assertEqual(classify_http_status(422).category, 'VALIDATION')
        self.assertEqual(classify_http_status(503).category, 'PROVIDER_OUTAGE')

    def test_should_retry_only_for_retryable_and_within_budget(self):
        self.assertTrue(should_retry(429, 0))
        self.assertTrue(should_retry(503, 1))
        self.assertFalse(should_retry(401, 0))
        self.assertFalse(should_retry(422, 0))
        self.assertFalse(should_retry(429, 999))

    def test_backoff_seconds(self):
        self.assertEqual(backoff_seconds(0), 60)
        self.assertEqual(backoff_seconds(1), 300)
        self.assertEqual(backoff_seconds(2), 1800)


if __name__ == '__main__':
    unittest.main()
