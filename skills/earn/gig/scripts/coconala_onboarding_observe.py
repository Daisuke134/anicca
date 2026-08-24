#!/usr/bin/env python3
"""Observe Coconala setup pages without emitting form values or page text."""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

SCRIPTS = Path(__file__).resolve().parent
GIG_ROOT = SCRIPTS.parent
BROWSER_SCRIPTS = GIG_ROOT.parents[1] / "browser" / "scripts"
sys.path.insert(0, str(BROWSER_SCRIPTS))

import cdp_default_tab  # noqa: E402
import websockets  # noqa: E402
from coconala_onboarding import _write_private, record  # noqa: E402


PAGES = {
    "authenticated": "https://coconala.com/mypage",
    "sms_verified": "https://coconala.com/mypage/sms",
    "seller_information": "https://coconala.com/mypage/user_information",
    "identity_approved": "https://coconala.com/mypage/user_identification",
    "bank_registered": "https://coconala.com/mypage/bank",
}

EXPRESSION = r"""(()=>JSON.stringify({
  url: location.origin + location.pathname,
  ready: document.readyState,
  forms: document.forms.length,
  controls: [...document.querySelectorAll('input,select,textarea')].map(x=>({
    tag:x.tagName.toLowerCase(), type:(x.type||''), name:(x.name||''), id:(x.id||''),
    required:!!x.required, disabled:!!x.disabled, checked:!!x.checked,
    has_value: x.type==='file' ? x.files.length>0 : String(x.value||'').trim().length>0
  })),
  body: (document.body?.innerText||'').trim()
}))()"""


async def _evaluate(ws_url: str) -> dict[str, object]:
    async with websockets.connect(ws_url, max_size=64 * 1024 * 1024) as ws:
        await ws.send(json.dumps({
            "id": 1, "method": "Runtime.evaluate",
            "params": {"expression": EXPRESSION, "returnByValue": True, "awaitPromise": True},
        }))
        while True:
            message = json.loads(await ws.recv())
            if message.get("id") != 1:
                continue
            value = message.get("result", {}).get("result", {}).get("value")
            if not isinstance(value, str):
                raise RuntimeError("onboarding_dom_unavailable")
            return json.loads(value)


def _safe_snapshot(raw: dict[str, object]) -> dict[str, object]:
    controls = raw.get("controls") if isinstance(raw.get("controls"), list) else []
    safe_controls = [
        {key: row.get(key) for key in (
            "tag", "type", "name", "id", "required", "disabled", "checked", "has_value"
        )}
        for row in controls if isinstance(row, dict)
    ]
    body = str(raw.get("body") or "")
    return {
        "url": str(raw.get("url") or ""),
        "ready": raw.get("ready"),
        "forms": int(raw.get("forms") or 0),
        "controls": safe_controls,
        "body_sha256": hashlib.sha256(body.encode("utf-8")).hexdigest(),
        "body_length": len(body),
    }


def observe(home: Path) -> dict[str, object]:
    os.environ["CLOAK_CDP_BASE_URL"] = "http://127.0.0.1:9223"
    snapshots: dict[str, object] = {}
    for state, url in PAGES.items():
        tab = cdp_default_tab.open_tab(url, background=True, owner="gig-onboarding")
        try:
            raw = {}
            for _ in range(20):
                time.sleep(0.5)
                raw = asyncio.run(_evaluate(str(tab["ws"])))
                if raw.get("ready") == "complete":
                    break
            snapshots[state] = _safe_snapshot(raw)
        finally:
            cdp_default_tab.close_tab(str(tab["target_id"]), owner="gig-onboarding")
    evidence = {"version": 1, "platform": "coconala", "pages": snapshots}
    output = home / ".config" / "anicca" / "gig" / "onboarding-observation.json"
    _write_private(output, evidence)

    auth_url = str(snapshots["authenticated"].get("url") or "")
    parsed = urlparse(auth_url)
    if parsed.hostname == "coconala.com" and parsed.path.startswith("/mypage"):
        digest = hashlib.sha256(
            json.dumps(snapshots["authenticated"], sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        record(home, "authenticated", digest)
    return evidence


def main() -> int:
    evidence = observe(Path.home())
    print(json.dumps({
        "status": "observed",
        "pages": {state: row["url"] for state, row in evidence["pages"].items()},
        "evidence": "private:onboarding-observation.json",
    }, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
