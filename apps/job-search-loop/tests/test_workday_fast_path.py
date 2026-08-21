import unittest

from job_search_loop.workday_fast_path import _choose


class _PromptOptions:
    async def count(self):
        return 1


class _Page:
    def __init__(self, events):
        self.events = events

    def locator(self, selector):
        self.events.append(("options", selector))
        return _PromptOptions()


class _Input:
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


class WorkdayFastPathTests(unittest.IsolatedAsyncioTestCase):
    async def test_source_input_waits_for_prompt_before_keyboard_selection(self):
        events = []

        selected = await _choose(_Page(events), _Input(events), "Job Boards")

        self.assertTrue(selected)
        self.assertLess(
            next(i for i, event in enumerate(events) if event[0] == "options"),
            next(i for i, event in enumerate(events) if event == ("press", "ArrowDown")),
        )


if __name__ == "__main__":
    unittest.main()
