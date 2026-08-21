import unittest

from job_search_loop.workday_fast_path import _field_element


class _PageForField:
    def __init__(self):
        self.calls = []

    def locator(self, selector):
        self.calls.append(("locator", selector))
        return selector


class WorkdayFastPathTests(unittest.IsolatedAsyncioTestCase):
    def test_field_relookup_uses_stable_id_after_dom_reorder(self):
        page = _PageForField()

        _field_element(page, {"id": "source--source", "index": 2})

        self.assertEqual(page.calls, [("locator", "#source--source")])


if __name__ == "__main__":
    unittest.main()
