import asyncio
import json
import os
import sys
import websockets
import base64
from pathlib import Path


CREDENTIALS = Path(os.environ.get("ANICCA_CREDENTIALS_FILE") or Path.home() / ".local/share/anicca/credentials.json")


def credential_value(ref, field):
    if not ref.startswith("credentials:") or field not in {"password", "passcode", "token", "api_key"}:
        raise ValueError("invalid credential reference")
    rows = json.loads(CREDENTIALS.read_text(encoding="utf-8")).get("credentials", [])
    value = rows[int(ref.split(":", 1)[1])].get(field)
    if not isinstance(value, str) or not value:
        raise ValueError("credential field unavailable")
    return value

async def cdp_call(ws, method, params=None):
    request_id = 1
    await ws.send(json.dumps({"id": request_id, "method": method, "params": params or {}}))
    while True:
        msg = json.loads(await ws.recv())
        if msg.get("id") == request_id:
            if "error" in msg:
                raise RuntimeError(f"{method}: {msg['error']}")
            return msg.get("result", {})

async def navigate(ws_url, url):
    async with websockets.connect(ws_url, max_size=64 * 1024 * 1024) as ws:
        await cdp_call(ws, "Page.enable")
        await cdp_call(ws, "Page.navigate", {"url": url})
        await asyncio.sleep(3) # Give the page some time to load
        await cdp_call(ws, "Runtime.evaluate", {"expression": "document.readyState", "awaitPromise": True})
        print(json.dumps({"ok": True, "action": "navigate", "url": url}))

async def get_dom(ws_url):
    async with websockets.connect(ws_url, max_size=64 * 1024 * 1024) as ws:
        await cdp_call(ws, "DOM.enable")
        doc = await cdp_call(ws, "DOM.getDocument", {"depth": -1})
        root_node_id = doc["root"]["nodeId"]
        outer_html = await cdp_call(ws, "DOM.getOuterHTML", {"nodeId": root_node_id})
        print(json.dumps({"ok": True, "action": "get_dom", "html": outer_html["outerHTML"]}))

async def screenshot(ws_url, path):
    async with websockets.connect(ws_url, max_size=64 * 1024 * 1024) as ws:
        await cdp_call(ws, "Page.enable")
        result = await cdp_call(ws, "Page.captureScreenshot")
        with open(path, "wb") as f:
            f.write(base64.b64decode(result["data"]))
        print(json.dumps({"ok": True, "action": "screenshot", "path": path}))

async def click_element(ws_url, selector):
    async with websockets.connect(ws_url, max_size=64 * 1024 * 1024) as ws:
        await cdp_call(ws, "DOM.enable")
        doc = await cdp_call(ws, "DOM.getDocument", {"depth": 1})
        root_node_id = doc["root"]["nodeId"]
        node_id_result = await cdp_call(ws, "DOM.querySelector", {"nodeId": root_node_id, "selector": selector})
        node_id = node_id_result["nodeId"]
        if not node_id:
            raise RuntimeError(f"Element with selector '{selector}' not found.")

        box_model = await cdp_call(ws, "DOM.getBoxModel", {"nodeId": node_id})
        # Get the center of the element
        content_box = box_model["model"]["content"]
        x = (content_box[0] + content_box[2]) / 2
        y = (content_box[1] + content_box[5]) / 2

        await cdp_call(ws, "Input.dispatchMouseEvent", {
            "type": "mousePressed",
            "x": x,
            "y": y,
            "button": "left",
            "clickCount": 1
        })
        await cdp_call(ws, "Input.dispatchMouseEvent", {
            "type": "mouseReleased",
            "x": x,
            "y": y,
            "button": "left",
            "clickCount": 1
        })
        print(json.dumps({"ok": True, "action": "click_element", "selector": selector}))

async def type_text(ws_url, selector, text):
    async with websockets.connect(ws_url, max_size=64 * 1024 * 1024) as ws:
        await cdp_call(ws, "DOM.enable")
        doc = await cdp_call(ws, "DOM.getDocument", {"depth": 1})
        root_node_id = doc["root"]["nodeId"]
        node_id_result = await cdp_call(ws, "DOM.querySelector", {"nodeId": root_node_id, "selector": selector})
        node_id = node_id_result["nodeId"]
        if not node_id:
            raise RuntimeError(f"Element with selector '{selector}' not found.")
        await cdp_call(ws, "DOM.focus", {"nodeId": node_id})
        await cdp_call(ws, "Input.insertText", {"text": text})
        print(json.dumps({"ok": True, "action": "type_text", "selector": selector, "text_length": len(text)}))

async def evaluate_js(ws_url, expression):
    async with websockets.connect(ws_url, max_size=64 * 1024 * 1024) as ws:
        result = await cdp_call(ws, "Runtime.evaluate", {"expression": expression, "returnByValue": True})
        value = result.get("result", {}).get("value")
        print(json.dumps({"ok": True, "action": "evaluate_js", "expression": expression, "value": value}))

async def main():
    action = sys.argv[1]
    ws_url = sys.argv[2]

    if action == "navigate":
        url = sys.argv[3]
        await navigate(ws_url, url)
    elif action == "get_dom":
        await get_dom(ws_url)
    elif action == "screenshot":
        path = sys.argv[3]
        await screenshot(ws_url, path)
    elif action == "click":
        selector = sys.argv[3]
        await click_element(ws_url, selector)
    elif action == "type":
        selector = sys.argv[3]
        text = sys.argv[4]
        await type_text(ws_url, selector, text)
    elif action == "type_credential":
        selector, ref, field = sys.argv[3:6]
        await type_text(ws_url, selector, credential_value(ref, field))
    elif action == "evaluate_js":
        expression = sys.argv[3]
        await evaluate_js(ws_url, expression)
    else:
        print(json.dumps({"ok": False, "reason": f"unknown action {action}"}))

if __name__ == "__main__":
    asyncio.run(main())
