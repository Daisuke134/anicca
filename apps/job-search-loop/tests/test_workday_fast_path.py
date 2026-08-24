import unittest

from job_search_loop.workday_fast_path import _choose, _field_element


class _VisiblePrompt:
    def __init__(self, events):
        self.events = events

    async def is_visible(self):
        self.events.append(("visible",))
        return True


class _PromptLocator:
    def __init__(self, events):
        self.events = events
        self.first = _VisiblePrompt(events)

    async def count(self):
        self.events.append(("count",))
        return 1


class _ChoosePage:
    def __init__(self, events):
        self.events = events

    def locator(self, selector):
        self.events.append(("locator", selector))
        return _PromptLocator(self.events)


class _ChooseInput:
    def __init__(self, events):
        self.events = events

    async def evaluate(self, script):
        return "input"

    async def click(self, **kwargs):
        self.events.append(("click",))

    async def fill(self, value):
        self.events.append(("fill", value))

    async def press(self, key):
        self.events.append(("press", key))


class _PageForField:
    def __init__(self):
        self.calls = []

    def locator(self, selector):
        self.calls.append(("locator", selector))
        return selector


class WorkdayFastPathTests(unittest.IsolatedAsyncioTestCase):
    async def test_source_keyboard_waits_for_exact_prompt_option(self):
        events = []

        selected = await _choose(_ChoosePage(events), _ChooseInput(events), "Job Boards")

        self.assertTrue(selected)
        option_index = next(i for i, event in enumerate(events) if event[0] == "locator")
        key_index = next(i for i, event in enumerate(events) if event == ("press", "ArrowDown"))
        self.assertLess(option_index, key_index)
        self.assertIn("Job Boards", events[option_index][1])

    def test_field_relookup_uses_stable_id_after_dom_reorder(self):
        page = _PageForField()

        _field_element(page, {"id": "source--source", "index": 2})

        self.assertEqual(page.calls, [("locator", "#source--source")])


if __name__ == "__main__":
    unittest.main()
