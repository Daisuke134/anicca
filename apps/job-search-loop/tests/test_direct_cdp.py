import unittest
import inspect
from unittest.mock import AsyncMock, patch

from job_search_loop.browser_agent.direct_cdp import DirectCDPPage
from job_search_loop.browser_agent.observation import ObservationBuilder
from job_search_loop.browser_agent.actions import ActionExecutor
from job_search_loop.browser_agent.contracts import ActionTargetV1, VisibleActionV1
from job_search_loop.browser_agent.runtime import main as browser_runtime_main
from job_search_loop.browser_agent.runtime import type_candidate
from job_search_loop.runtime import main as compatibility_runtime_main


class DirectCDPTypeTests(unittest.IsolatedAsyncioTestCase):
    async def test_type_rejects_non_text_control_without_browser_action(self):
        observation = {"status": "observed", "observation": {"controls": []}}
        with patch(
            "job_search_loop.browser_agent.runtime.observe",
            new=AsyncMock(return_value=observation),
        ) as observe, patch(
            "job_search_loop.browser_agent.runtime.act",
            new=AsyncMock(),
        ) as act:
            result = await type_candidate(
                label="Please Select One",
                role="button",
                stable_id="id:gender",
                candidate_concept="policy.prefer_not_to_say",
            )

        self.assertEqual(result["status"], "action_rejected")
        self.assertEqual(result["reason"], "type_requires_text_control")
        observe.assert_awaited_once()
        act.assert_not_awaited()

    async def test_screenshot_does_not_reflow_virtualized_provider_lists(self):
        page = DirectCDPPage("ws://example", "target")
        page._ensure_viewport = AsyncMock()
        page.call = AsyncMock(return_value={"data": "eA=="})

        await page.screenshot(full_page=True)

        self.assertFalse(page.call.await_args.args[1]["captureBeyondViewport"])

    def test_short_runtime_entrypoint_is_the_same_bounded_runtime(self):
        self.assertIs(compatibility_runtime_main, browser_runtime_main)

    async def test_choose_reopens_an_expired_overlay_and_clicks_the_option_atomically(self):
        page = DirectCDPPage("ws://example", "target")
        page.click_target = AsyncMock(side_effect=[RuntimeError("expired id"), None])
        session = unittest.mock.Mock()
        session.page.return_value = page
        action = VisibleActionV1(
            "choose",
            target=ActionTargetV1("option", "Website", stable_id="id:menuItem"),
            opener=ActionTargetV1("button", "Source options", stable_id="automation:promptSearchButton"),
        )

        await ActionExecutor(session)._execute_direct(page, action)

        self.assertEqual(page.click_target.await_count, 2)

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
