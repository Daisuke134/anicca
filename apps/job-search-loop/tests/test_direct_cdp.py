import unittest
import inspect
from unittest.mock import AsyncMock

from job_search_loop.browser_agent.direct_cdp import DirectCDPPage
from job_search_loop.browser_agent.observation import ObservationBuilder


class DirectCDPTypeTests(unittest.IsolatedAsyncioTestCase):
    def test_target_resolution_includes_pointer_operated_provider_controls(self):
        script = DirectCDPPage._target_script(
            {"label": "Search options", "role": "button", "stable_id": "automation:picker"}
        )
        self.assertIn("[data-automation-id]", script)
        self.assertIn("cursor==='pointer'?'button'", script)
        self.assertIn("relatedInput", script)
        self.assertIn("if (resolvedByStableId) return true", script)
        self.assertIn("closest('[role=\"option\"]')", inspect.getsource(ObservationBuilder.build))

    async def test_type_selects_the_existing_whole_value_before_inserting(self):
        page = DirectCDPPage("ws://example", "target")
        page.click_target = AsyncMock()
        page.evaluate = AsyncMock(return_value=True)
        page.call = AsyncMock(return_value={})

        await page.type_target(
            {"label": "First name", "role": "textbox", "stable_id": "ref:e1"},
            "Daisuke",
        )

        page.evaluate.assert_awaited_once()
        self.assertIn("el.select()", page.evaluate.await_args.args[0])
        self.assertEqual(
            [call.args for call in page.call.await_args_list if call.args[0] == "Input.insertText"],
            [("Input.insertText", {"text": "Daisuke"})],
        )


if __name__ == "__main__":
    unittest.main()
