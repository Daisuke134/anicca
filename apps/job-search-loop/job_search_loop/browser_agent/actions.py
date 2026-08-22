from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from urllib.parse import urlparse

from .contracts import (
    ActionReceiptV1,
    ActionTargetV1,
    SessionHandleV1,
    SubmissionFenceLeaseV1,
    VisibleActionV1,
)
from .session import BrowserSession
from .submission_fence import SubmissionFence


_FINAL_SUBMIT = re.compile(r"^\s*(submit|submit application)\s*$", re.IGNORECASE)


class ActionExecutor:
    """Execute only fresh, unique, visible user-facing actions."""

    def __init__(self, session: BrowserSession, timeout_ms: int = 20_000) -> None:
        self._session = session
        self._timeout_ms = timeout_ms

    @staticmethod
    def _validate_https(url: str) -> None:
        parsed = urlparse(url)
        if parsed.scheme != "https" or not parsed.hostname:
            raise ValueError("navigation requires an absolute HTTPS URL")

    async def _target(self, page, target: ActionTargetV1):
        if not target.label.strip():
            raise ValueError("a non-empty user-facing label is required")
        if target.stable_id:
            kind, separator, value = target.stable_id.partition(":")
            if not separator or kind not in {"automation", "id"} or not value:
                raise ValueError("stable_id must be automation:<value> or id:<value>")
            attribute = "data-automation-id" if kind == "automation" else "id"
            locator = page.locator(f"[{attribute}={json.dumps(value)}]")
        else:
            locator = (
                page.get_by_role(target.role, name=target.label, exact=target.exact)
                if target.role
                else page.get_by_label(target.label, exact=target.exact)
            )
        async def resolve():
            visible = []
            for index in range(await locator.count()):
                candidate = locator.nth(index)
                if not await candidate.is_visible() or not await candidate.is_enabled():
                    continue
                if target.stable_id and not await candidate.evaluate(
                """(el, expected) => {
                  const own = el.getAttribute('aria-label') || el.getAttribute('title') || '';
                  const linked = el.labels && el.labels.length
                    ? Array.from(el.labels).map(x => x.innerText).join(' ') : '';
                  const actual = (own || linked || el.getAttribute('placeholder') || el.innerText || '').trim();
                  const variants = [actual];
                  variants.push(actual.replace(/\\s+(?:not checked|checked)$/i, ''));
                  if (el.hasAttribute('aria-checked')) {
                    variants.push(`${actual} ${el.getAttribute('aria-checked') === 'true' ? 'checked' : 'not checked'}`);
                  }
                  return expected.exact
                    ? variants.includes(expected.label)
                    : variants.some(value => value.includes(expected.label));
                }""",
                {"label": target.label, "exact": target.exact},
                ):
                    continue
                visible.append(candidate)
            return visible

        visible = await resolve()
        if not visible and target.role == "option":
            # Transient ARIA menus may collapse when a short-lived CDP client
            # disconnects between observe and act. Re-open only the control that
            # retained focus, then resolve the exact previously observed option.
            focused = page.locator(":focus")
            if await focused.count() == 1 and await focused.evaluate(
                """el => el.getAttribute('role') === 'combobox'
                  || el.getAttribute('data-automation-id') === 'searchBox'"""
            ):
                await focused.click(timeout=self._timeout_ms)
                visible = await resolve()
        if target.ordinal is not None:
            if target.ordinal < 1 or target.ordinal > len(visible):
                raise RuntimeError("action target ordinal is outside the visible controls")
            return visible[target.ordinal - 1]
        if len(visible) != 1:
            raise RuntimeError(
                "action target must resolve to exactly one visible enabled control"
            )
        return visible[0]

    async def execute(
        self, handle: SessionHandleV1, action: VisibleActionV1
    ) -> ActionReceiptV1:
        page = self._session.page(handle)
        before_url = page.url
        target = None
        if action.kind == "navigate":
            if action.url is None:
                raise ValueError("navigate requires url")
            self._validate_https(action.url)
            await page.goto(action.url, wait_until="commit", timeout=self._timeout_ms)
        elif action.kind in {"click", "choose", "type", "select", "upload"}:
            if action.target is None:
                raise ValueError(f"{action.kind} requires target")
            if action.kind == "click" and _FINAL_SUBMIT.match(action.target.label):
                raise PermissionError("final Submit requires the SubmissionFence path")
            if action.kind == "choose":
                if action.opener is None:
                    raise ValueError("choose requires opener")
                try:
                    target = await self._target(page, action.target)
                except RuntimeError:
                    try:
                        opener = await self._target(page, action.opener)
                    except RuntimeError:
                        opener = await self._target(
                            page,
                            ActionTargetV1(
                                role=action.opener.role,
                                label=action.opener.label,
                                exact=action.opener.exact,
                            ),
                        )
                    await opener.click(timeout=self._timeout_ms)
                    try:
                        target = await self._target(page, action.target)
                    except RuntimeError:
                        if not await opener.evaluate(
                            "el => el.tagName === 'INPUT' || el.tagName === 'TEXTAREA'"
                        ):
                            raise
                        option_label = re.sub(
                            r"\s+(?:not checked|checked)$",
                            "",
                            action.target.label,
                            flags=re.IGNORECASE,
                        )
                        await opener.fill(option_label, timeout=self._timeout_ms)
                        prompt_option = page.locator(
                            "[data-automation-id='promptOption']"
                        ).filter(has_text=option_label)
                        await prompt_option.first.wait_for(
                            state="visible", timeout=self._timeout_ms
                        )
                        if await prompt_option.count() != 1:
                            raise RuntimeError(
                                "typed option must resolve to exactly one prompt option"
                            )
                        target = prompt_option.first
            else:
                target = await self._target(page, action.target)
            if action.kind in {"click", "choose"}:
                await target.click(timeout=self._timeout_ms)
            elif action.kind == "type":
                if action.text is None:
                    raise ValueError("type requires text")
                await target.fill(action.text, timeout=self._timeout_ms)
            elif action.kind == "select":
                if action.text is None:
                    raise ValueError("select requires option label")
                await target.select_option(label=action.text, timeout=self._timeout_ms)
            else:
                if action.file_path is None or not Path(action.file_path).is_file():
                    raise ValueError("upload requires an existing file")
                is_file_input = await target.evaluate(
                    "el => el.tagName === 'INPUT' && el.type === 'file'"
                )
                if is_file_input:
                    await target.set_input_files(
                        str(action.file_path), timeout=self._timeout_ms
                    )
                else:
                    async with page.expect_file_chooser(
                        timeout=self._timeout_ms
                    ) as chooser_info:
                        await target.click(timeout=self._timeout_ms)
                    chooser = await chooser_info.value
                    await chooser.set_files(str(action.file_path))
        elif action.kind == "scroll":
            if action.delta_y is None or abs(action.delta_y) > 10_000:
                raise ValueError("scroll requires bounded delta_y")
            await page.mouse.wheel(0, action.delta_y)
        elif action.kind == "wait":
            if action.wait_ms is None or not 0 < action.wait_ms <= 10_000:
                raise ValueError("wait requires 1..10000 milliseconds")
            await page.wait_for_timeout(action.wait_ms)
        else:
            raise ValueError(f"unsupported action kind: {action.kind}")

        safe = {
            "kind": action.kind,
            "target_role": action.target.role if action.target else None,
            "target_label": action.target.label if action.target else None,
            "target_stable_id": action.target.stable_id if action.target else None,
            "before_url": before_url,
            "after_url": page.url,
        }
        receipt_sha = hashlib.sha256(
            json.dumps(safe, ensure_ascii=False, sort_keys=True).encode("utf-8")
        ).hexdigest()
        return ActionReceiptV1(1, receipt_sha256=receipt_sha, **safe)

    async def execute_final(
        self,
        handle: SessionHandleV1,
        action: VisibleActionV1,
        fence: SubmissionFence,
        lease: SubmissionFenceLeaseV1,
        observation_sha256: str,
    ) -> ActionReceiptV1:
        """Consume one fresh fence and click one visible final Submit exactly once."""
        if (
            action.kind != "click"
            or action.target is None
            or not _FINAL_SUBMIT.match(action.target.label)
        ):
            raise ValueError("final action must be the visible Submit click")
        page = self._session.page(handle)
        before_url = page.url
        target = await self._target(page, action.target)
        fence_receipt = fence.consume(lease, observation_sha256)
        click_error_type = None
        try:
            await target.click(timeout=self._timeout_ms)
        except Exception as error:
            # Once the fence is consumed the click may have reached the provider.
            # Return an opaque receipt so the caller observes and classifies the
            # rendered result exactly once instead of retrying an ambiguous submit.
            click_error_type = type(error).__name__
        safe = {
            "kind": action.kind,
            "target_role": action.target.role,
            "target_label": action.target.label,
            "target_stable_id": action.target.stable_id,
            "before_url": before_url,
            "after_url": page.url,
            "fence_receipt_sha256": fence_receipt,
            "click_error_type": click_error_type,
        }
        receipt_sha = hashlib.sha256(
            json.dumps(safe, ensure_ascii=False, sort_keys=True).encode("utf-8")
        ).hexdigest()
        safe.pop("click_error_type")
        return ActionReceiptV1(1, receipt_sha256=receipt_sha, **safe)
