#!/usr/bin/env python3
"""Can this browser still run a page, or only answer the door?

ensure_browser.sh decided the browser was healthy from `GET /json/version`. That endpoint is
served by the browser process itself and keeps answering long after pages stop working, so on
2026-08-05 every gig pass was told ALIVE while B2 died on cdp_Page.enable_timeout_after_30s --
the loop restarted nothing, the apply lane recorded no application for three days, and the
one surface that could have caught it was measuring whether a socket was open.

So the probe does the smallest version of the thing the loop actually needs: open a fresh
browser context, open a page in it, evaluate 1, throw the context away. A browser that cannot
do that cannot run a 応募 form either, whatever /json/version says.

    python3 browser_responsive.py            -> prints RESPONSIVE / WEDGED, exit 0 / 1
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
import urllib.request

CDP = os.environ.get("CLOAK_CDP_BASE_URL", "http://127.0.0.1:9222")
TIMEOUT = float(os.environ.get("BROWSER_PROBE_TIMEOUT", "20"))

try:
    import websockets
except ImportError:  # the probe must never be the reason a pass cannot start
    print("RESPONSIVE (probe unavailable: websockets not installed)")
    raise SystemExit(0)


def browser_ws() -> str:
    payload = json.loads(urllib.request.urlopen(f"{CDP}/json/version", timeout=8).read())
    return payload["webSocketDebuggerUrl"]


async def call(ws, call_id: int, method: str, params: dict, deadline: float) -> dict:
    await ws.send(json.dumps({"id": call_id, "method": method, "params": params}))
    loop = asyncio.get_running_loop()
    while True:
        remaining = deadline - loop.time()
        if remaining <= 0:
            raise TimeoutError(method)
        message = json.loads(await asyncio.wait_for(ws.recv(), timeout=remaining))
        if message.get("id") != call_id:
            continue
        if "error" in message:
            raise RuntimeError(f"{method}: {message['error']}")
        return message.get("result") or {}


async def probe() -> str:
    loop = asyncio.get_running_loop()
    deadline = loop.time() + TIMEOUT
    context_id = None
    async with websockets.connect(browser_ws(), max_size=1 << 20, ping_interval=None) as browser:
        try:
            created = await call(browser, 1, "Target.createBrowserContext", {}, deadline)
            context_id = created["browserContextId"]
            target = await call(
                browser, 2, "Target.createTarget",
                {"url": "about:blank", "browserContextId": context_id}, deadline,
            )
            page_ws = f"{CDP.replace('http', 'ws', 1)}/devtools/page/{target['targetId']}"
            async with websockets.connect(page_ws, max_size=1 << 20, ping_interval=None) as page:
                answer = await call(
                    page, 1, "Runtime.evaluate",
                    {"expression": "1", "returnByValue": True}, deadline,
                )
            value = ((answer.get("result") or {}).get("value"))
            return "RESPONSIVE" if value == 1 else f"WEDGED (evaluate returned {value!r})"
        finally:
            if context_id:
                # Never leak the probe's own context; a leaked context keeps tabs alive forever.
                try:
                    await call(
                        browser, 99, "Target.disposeBrowserContext",
                        {"browserContextId": context_id}, loop.time() + 8,
                    )
                except Exception:
                    pass


def main() -> int:
    try:
        verdict = asyncio.run(probe())
    except Exception as error:
        print(f"WEDGED ({type(error).__name__}: {error})")
        return 1
    print(verdict)
    return 0 if verdict == "RESPONSIVE" else 1


if __name__ == "__main__":
    sys.exit(main())
