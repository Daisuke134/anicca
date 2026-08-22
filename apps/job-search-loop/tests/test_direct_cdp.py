import unittest
import inspect
from unittest.mock import AsyncMock

from job_search_loop.browser_agent.direct_cdp import DirectCDPPage
from job_search_loop.browser_agent.observation import ObservationBuilder
from job_search_loop.browser_agent.actions import ActionExecutor
from job_search_loop.browser_agent.contracts import ActionTargetV1, VisibleActionV1
from job_search_loop.browser_agent.runtime import main as browser_runtime_main
from job_search_loop.runtime import main as compatibility_runtime_main


class DirectCDPTypeTests(unittest.IsolatedAsyncioTestCase):
    def test_short_runtime_entrypoint_is_the_same_bounded_runtime(self):
        self.assertIs(compatibility_runtime_main, browser_runtime_main)

    async def test_choose_reopens_an_expired_overlay_and_clicks_the_option_atomically(self):
        page = DirectCDPPage("ws://example", "target")
        page.click_target = AsyncMock(side_effect=[RuntimeError("closed"), None, None])
        session = unittest.mock.Mock()
        session.page.return_value = page
        action = VisibleActionV1(
            "choose",
            target=ActionTargetV1("option", "Website", stable_id="id:menuItem"),
            opener=ActionTargetV1("button", "Source options", stable_id="automation:promptSearchButton"),
        )

        await ActionExecutor(session)._execute_direct(page, action)

        self.assertEqual(page.click_target.await_count, 3)

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
