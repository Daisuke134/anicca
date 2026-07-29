#!/usr/bin/env python3
"""Provider-neutral ordering for one claimed Coconala reply action."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Protocol


REPLY_LEASE_SECONDS = 1200


def dom_compatible_outgoing_body(value: str) -> str:
    if type(value) is not str:
        raise TypeError("composed reply must be a string")
    return value.replace("\r\n", "\n").replace("\r", "\n")


class ReplyBrowser(Protocol):
    def read_before(self) -> tuple[dict[str, Any], dict[str, Any]]: ...

    def fill(self, body: str) -> None: ...

    def click(self) -> None: ...

    def read_after(self) -> dict[str, Any]: ...

    def failure_evidence(self, error: Exception) -> dict[str, Any]: ...


def execute_reply(
    *,
    controller: Any,
    queue_item: dict[str, Any],
    owner: str,
    clock: Callable[[], int],
    compose: Callable[[dict[str, Any]], str],
    browser: ReplyBrowser,
    lease_seconds: int = REPLY_LEASE_SECONDS,
    action_id: int | None = None,
) -> dict[str, Any]:
    """Execute compose/read/send/verify with click authority held by the controller."""
    action = controller.claim(
        owner=owner,
        now=clock(),
        lease_seconds=lease_seconds,
        action_id=action_id,
    )
    if action is None:
        return {
            "status": "queue_empty",
            "verified": False,
            "blind_retry_allowed": False,
            "errors": [],
        }
    intent: dict[str, Any] | None = None
    click_authorized = False
    try:
        context, before = browser.read_before()
        outgoing_body = dom_compatible_outgoing_body(compose(context))
        intent = controller.prepare(
            action=action,
            queue_item=queue_item,
            outgoing_body=outgoing_body,
            now=clock(),
        )
        browser.fill(outgoing_body)
        outgoing_body = ""
        controller.authorize_click(intent=intent, now=clock())
        click_authorized = True
        try:
            browser.click()
            after = browser.read_after()
        except Exception as error:
            evidence = getattr(browser, "failure_evidence", None)
            after = evidence(error) if callable(evidence) else {"status": "read_failed"}
        return controller.finalize(
            intent=intent,
            before=before,
            after=after,
            observed_at=clock(),
        )
    except Exception:
        if not click_authorized:
            controller.pre_click_failure(intent=intent or action, now=clock())
        raise
