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
                  return expected.exact ? actual === expected.label : actual.includes(expected.label);
                }""",
                {"label": target.label, "exact": target.exact},
            ):
                continue
            if target.stable_id:
                visible.append(candidate)
            else:
                visible.append(candidate)
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
        elif action.kind in {"click", "type", "select", "upload"}:
            if action.target is None:
                raise ValueError(f"{action.kind} requires target")
            if action.kind == "click" and _FINAL_SUBMIT.match(action.target.label):
                raise PermissionError("final Submit requires the SubmissionFence path")
            target = await self._target(page, action.target)
            if action.kind == "click":
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
                await target.set_input_files(str(action.file_path), timeout=self._timeout_ms)
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
        await target.click(timeout=self._timeout_ms)
        safe = {
            "kind": action.kind,
            "target_role": action.target.role,
            "target_label": action.target.label,
            "target_stable_id": action.target.stable_id,
            "before_url": before_url,
            "after_url": page.url,
            "fence_receipt_sha256": fence_receipt,
        }
        receipt_sha = hashlib.sha256(
            json.dumps(safe, ensure_ascii=False, sort_keys=True).encode("utf-8")
        ).hexdigest()
        return ActionReceiptV1(1, receipt_sha256=receipt_sha, **safe)
