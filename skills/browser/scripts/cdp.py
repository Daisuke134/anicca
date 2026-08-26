#!/usr/bin/env python3
"""Small repo-owned raw-CDP CLI used by Life Manager browser loops."""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.request

from websocket import create_connection


HOST = os.environ.get("CDP_HOST", "localhost")
PORT = os.environ.get("CDP_PORT", "9222")
BASE = f"http://{HOST}:{PORT}"


def _rpc(ws, call_id: int, method: str, params: dict | None = None) -> dict:
    ws.send(json.dumps({"id": call_id, "method": method, "params": params or {}}))
    while True:
        message = json.loads(ws.recv())
        if message.get("id") != call_id:
            continue
        if "error" in message:
            raise RuntimeError(f"{method}: {message['error']}")
        return message.get("result", {})


def _browser_ws() -> str:
    with urllib.request.urlopen(BASE + "/json/version", timeout=5) as response:
        return json.load(response)["webSocketDebuggerUrl"]


def _browser_call(method: str, params: dict) -> dict:
    ws = create_connection(_browser_ws(), timeout=20, suppress_origin=True)
    try:
        return _rpc(ws, 1, method, params)
    finally:
        ws.close()


def _page(tid: str):
    return create_connection(
        f"ws://{HOST}:{PORT}/devtools/page/{tid}", timeout=30, max_size=None, suppress_origin=True
    )


def evaluate(tid: str, expression: str):
    ws = _page(tid)
    try:
        result = _rpc(ws, 1, "Runtime.evaluate", {
            "expression": expression, "returnByValue": True, "awaitPromise": True, "userGesture": True,
        })
        if result.get("exceptionDetails"):
            return {"__error__": str(result["exceptionDetails"].get("text") or result["exceptionDetails"])}
        return result.get("result", {}).get("value")
    finally:
        ws.close()


def navigate(tid: str, url: str) -> None:
    ws = _page(tid)
    try:
        _rpc(ws, 1, "Page.enable")
        _rpc(ws, 2, "Page.navigate", {"url": url})
        time.sleep(0.5)
    finally:
        ws.close()


def click(tid: str, x: int, y: int) -> dict:
    ws = _page(tid)
    try:
        _rpc(ws, 1, "Input.dispatchMouseEvent", {"type": "mouseMoved", "x": x, "y": y})
        _rpc(ws, 2, "Input.dispatchMouseEvent", {"type": "mousePressed", "x": x, "y": y,
                                                 "button": "left", "clickCount": 1})
        _rpc(ws, 3, "Input.dispatchMouseEvent", {"type": "mouseReleased", "x": x, "y": y,
                                                 "button": "left", "clickCount": 1})
        return {"clicked": [x, y]}
    finally:
        ws.close()


def insert(tid: str, value: str) -> dict:
    ws = _page(tid)
    try:
        _rpc(ws, 1, "Input.insertText", {"text": value})
        return {"ok": True, "inserted_chars": len(value)}
    finally:
        ws.close()


def key(tid: str, value: str) -> dict:
    ws = _page(tid)
    try:
        for call_id, kind in enumerate(("keyDown", "keyUp"), start=1):
            _rpc(ws, call_id, "Input.dispatchKeyEvent", {"type": kind, "key": value})
        return {"key": value}
    finally:
        ws.close()


def set_file(tid: str, selector: str, path: str, index: int = 0) -> dict:
    ws = _page(tid)
    try:
        _rpc(ws, 1, "DOM.enable")
        root = _rpc(ws, 2, "DOM.getDocument", {"depth": -1})["root"]["nodeId"]
        nodes = _rpc(ws, 3, "DOM.querySelectorAll", {"nodeId": root, "selector": selector}).get("nodeIds", [])
        if not nodes:
            return {"__error__": f"no file input for {selector}"}
        node = nodes[min(index, len(nodes) - 1)]
        _rpc(ws, 4, "DOM.setFileInputFiles", {"nodeId": node, "files": [path]})
        return {"set": path, "node": node, "of": len(nodes)}
    finally:
        ws.close()


def _visible_named_expression(name: str, body: str) -> str:
    return f"""(() => {{
      const candidates = [...document.getElementsByName({json.dumps(name)})];
      const element = candidates.find((candidate) => {{
        const rect = candidate.getBoundingClientRect();
        const style = getComputedStyle(candidate);
        return rect.width > 0 && rect.height > 0 && style.visibility !== 'hidden' && style.display !== 'none';
      }}) || candidates.at(-1);
      if (!element) throw new Error('named field not found');
      {body}
    }})()"""


def fill_name(tid: str, name: str, value: str) -> dict:
    expression = _visible_named_expression(name, f"""
      const prototype = element.tagName === 'TEXTAREA'
        ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
      Object.getOwnPropertyDescriptor(prototype, 'value').set.call(element, {json.dumps(value)});
      element.dispatchEvent(new Event('input', {{bubbles: true}}));
      element.dispatchEvent(new Event('change', {{bubbles: true}}));
      return {{name: element.name, tag: element.tagName, value_length: element.value.length,
        valid: element.checkValidity(), visible: element.getBoundingClientRect().width > 0}};
    """)
    return evaluate(tid, expression)


def select_name(tid: str, name: str, value: str) -> dict:
    expression = _visible_named_expression(name, f"""
      Object.getOwnPropertyDescriptor(HTMLSelectElement.prototype, 'value')
        .set.call(element, {json.dumps(value)});
      element.dispatchEvent(new Event('input', {{bubbles: true}}));
      element.dispatchEvent(new Event('change', {{bubbles: true}}));
      return {{name: element.name, value: element.value, valid: element.checkValidity(),
        visible: element.getBoundingClientRect().width > 0}};
    """)
    return evaluate(tid, expression)


def form_state(tid: str) -> list[dict]:
    expression = """[...document.querySelectorAll('input,textarea,select,button')]
      .filter((element) => { const rect = element.getBoundingClientRect(); return rect.width > 0 && rect.height > 0; })
      .map((element) => ({tag: element.tagName, type: element.type || '', name: element.name || '',
        required: Boolean(element.required), filled: Boolean(element.value), value_length: (element.value || '').length,
        valid: typeof element.checkValidity === 'function' ? element.checkValidity() : true,
        text: (element.innerText || element.textContent || '').trim().slice(0, 120)}))"""
    return evaluate(tid, expression)


def main(argv: list[str]) -> int:
    if not argv:
        raise SystemExit("usage: cdp.py new|nav|eval|clickxy|insert|key|setfile|fillname|selectname|formstate|close ...")
    command, *args = argv
    if command == "new":
        print(_browser_call("Target.createTarget", {"url": args[0] if args else "about:blank"})["targetId"])
    elif command == "nav":
        navigate(args[0], args[1]); print("OK")
    elif command == "eval":
        source = sys.stdin.read() if args[1] == "-" else open(args[1], encoding="utf-8").read()
        print(json.dumps(evaluate(args[0], source), ensure_ascii=False))
    elif command == "clickxy":
        print(json.dumps(click(args[0], int(args[1]), int(args[2]))))
    elif command == "insert":
        print(json.dumps(insert(args[0], args[1])))
    elif command == "key":
        print(json.dumps(key(args[0], args[1])))
    elif command == "setfile":
        print(json.dumps(set_file(args[0], args[1], args[2], int(args[3]) if len(args) > 3 else 0)))
    elif command == "fillname":
        print(json.dumps(fill_name(args[0], args[1], args[2]), ensure_ascii=False))
    elif command == "selectname":
        print(json.dumps(select_name(args[0], args[1], args[2]), ensure_ascii=False))
    elif command == "formstate":
        print(json.dumps(form_state(args[0]), ensure_ascii=False))
    elif command == "close":
        _browser_call("Target.closeTarget", {"targetId": args[0]}); print("CLOSED")
    else:
        raise SystemExit(f"unknown command: {command}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
