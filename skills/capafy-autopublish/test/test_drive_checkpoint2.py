from __future__ import annotations

import importlib.util
import json
import sys
import types
from pathlib import Path

import pytest


SCRIPT = Path(__file__).parents[1] / "scripts" / "drive_checkpoint2.py"


def load_module():
    spec = importlib.util.spec_from_file_location("drive_checkpoint2", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class _Response:
    def __init__(self, payload):
        self._payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self):
        return json.dumps(self._payload).encode()


def test_raw_page_target_prefers_existing_capafy_page(monkeypatch) -> None:
    module = load_module()
    targets = [
        {"type": "page", "url": "https://coconala.com/", "webSocketDebuggerUrl": "ws://other"},
        {"type": "page", "url": "https://capafy.ai/developer/createAgent?page=credential", "webSocketDebuggerUrl": "ws://127.0.0.1:9222/devtools/page/capafy"},
        {"type": "iframe", "url": "https://capafy.ai/iframe", "webSocketDebuggerUrl": "ws://iframe"},
    ]
    monkeypatch.setattr(module.urllib.request, "urlopen", lambda *_args, **_kwargs: _Response(targets))

    assert module._raw_page_target("http://localhost:9222") == targets[1]


def test_raw_target_rejects_evil_host_and_non_loopback_ws(monkeypatch) -> None:
    module = load_module()
    targets = [{
        "type": "page",
        "url": "https://evil.example/developer/createAgent?page=credential",
        "webSocketDebuggerUrl": "ws://evil.example/devtools/page/x",
    }]
    monkeypatch.setattr(module.urllib.request, "urlopen", lambda *_args, **_kwargs: _Response(targets))

    with pytest.raises(RuntimeError, match="no existing Capafy page"):
        module._raw_page_target("http://127.0.0.1:9222")
    with pytest.raises(RuntimeError, match="loopback HTTP"):
        module._raw_page_target("http://evil.example:9222")
    with pytest.raises(RuntimeError, match="loopback host"):
        module._validate_ws_url("ws://evil.example/devtools/browser/x")


def test_short_cp2_url_resolves_one_valid_redirect(monkeypatch) -> None:
    module = load_module()
    final = "https://capafy.ai/developer/createAgent?source=temp-link&token=123&page=credential"
    seen = []

    def redirect(url, method):
        seen.append((url, method))
        return [final]

    monkeypatch.setattr(module, "_single_redirect_location", redirect)

    assert module._resolve_cp2_url("https://api.capafy.ai/C123") == final
    assert seen == [("https://api.capafy.ai/C123", "HEAD")]


def test_short_cp2_url_rejects_cross_domain_location(monkeypatch) -> None:
    module = load_module()
    monkeypatch.setattr(
        module,
        "_single_redirect_location",
        lambda *_args: ["https://evil.example/developer/createAgent?token=123&page=credential"],
    )

    with pytest.raises(RuntimeError, match="exact Capafy"):
        module._resolve_cp2_url("https://api.capafy.ai/C123")


def test_short_cp2_url_rejects_invalid_path() -> None:
    module = load_module()

    with pytest.raises(RuntimeError, match="exactly https://api.capafy.ai/C"):
        module._resolve_cp2_url("https://api.capafy.ai/not-a-short-url")


def test_raw_page_connects_to_validated_page_websocket(monkeypatch) -> None:
    module = load_module()
    calls = []

    class _Socket:
        def close(self):
            pass

    fake_websocket = types.SimpleNamespace(
        create_connection=lambda url, **kwargs: (calls.append((url, kwargs)) or _Socket())
    )
    monkeypatch.setitem(sys.modules, "websocket", fake_websocket)

    page = module._RawPage("ws://127.0.0.1:9222/devtools/page/capafy")
    page.close()

    assert calls == [("ws://127.0.0.1:9222/devtools/page/capafy", {"timeout": 15, "enable_multithread": True})]


@pytest.mark.parametrize(
    "evaluation",
    (
        {"ok": False, "reason": "path-count", "count": 0},
        {"ok": False, "reason": "button-count", "count": 2},
        {"ok": True, "disabled": True, "x": 1, "y": 2},
        {"ok": True, "disabled": False, "x": None, "y": 2},
    ),
)
def test_strict_click_rejects_missing_ambiguous_disabled_or_invalid_coords(evaluation) -> None:
    module = load_module()
    page = object.__new__(module._RawPage)
    page.evaluate = lambda _expression: evaluation
    page.call = lambda *_args, **_kwargs: pytest.fail("no dispatch on rejected strict click")

    with pytest.raises(RuntimeError):
        page.strict_click(module.OPENROUTER_API_KEY_PATH, "confirm")


def test_strict_click_dispatches_first_evaluation_coordinates_only() -> None:
    module = load_module()
    page = object.__new__(module._RawPage)
    page.evaluate = lambda _expression: {"ok": True, "disabled": False, "x": 12, "y": 34}
    calls = []
    page.call = lambda method, params=None: calls.append((method, params)) or {}

    assert page.strict_click(module.OPENROUTER_API_KEY_PATH, "confirm") is True
    assert [method for method, _ in calls] == ["Input.dispatchMouseEvent", "Input.dispatchMouseEvent"]
    assert calls[0][1]["x"] == 12 and calls[0][1]["y"] == 34


def test_strict_click_dispatch_failure_is_fail_closed() -> None:
    module = load_module()
    page = object.__new__(module._RawPage)
    page.evaluate = lambda _expression: {"ok": True, "disabled": False, "x": 12, "y": 34}
    page.call = lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("socket closed"))

    with pytest.raises(RuntimeError, match="dispatch failed"):
        page.strict_click(module.OPENROUTER_API_KEY_PATH, "confirm")


def test_raw_navigation_error_text_aborts_before_ready_probe() -> None:
    module = load_module()

    class _Page:
        def __init__(self):
            self.calls = []

        def call(self, method, params=None):
            self.calls.append(method)
            return {"errorText": "net::ERR_CONNECTION_RESET"}

        def evaluate(self, _expression):
            raise AssertionError("navigation error must not probe or write the page")

    page = _Page()
    with pytest.raises(RuntimeError, match="Page.navigate failed"):
        module._wait_raw_navigation(page, "https://capafy.ai/developer/createAgent?token=t&page=credential")
    assert page.calls == ["Page.navigate"]


def test_raw_navigation_location_mismatch_aborts_before_write() -> None:
    module = load_module()

    class _Page:
        def call(self, method, params=None):
            assert method == "Page.navigate"
            return {}

        def evaluate(self, _expression):
            return {"ready": "complete", "href": "https://evil.example/developer/createAgent?token=x"}

    with pytest.raises(RuntimeError, match="wrong origin/path"):
        module._wait_raw_navigation(_Page(), "https://capafy.ai/developer/createAgent?token=t&page=credential")


def test_raw_call_queues_interleaved_events_and_honors_deadline(monkeypatch) -> None:
    module = load_module()

    class _Socket:
        def __init__(self, messages):
            self.messages = iter(messages)

        def send(self, _message):
            pass

        def settimeout(self, _timeout):
            pass

        def recv(self):
            return next(self.messages)

    page = object.__new__(module._RawPage)
    page._next_id = 0
    page._events = []
    page._session_id = None
    page._ws = _Socket([
        json.dumps({"method": "Page.loadEventFired"}),
        json.dumps({"id": 1, "result": {"value": 7}}),
    ])
    assert page.call("Runtime.evaluate") == {"value": 7}
    assert page._events == [{"method": "Page.loadEventFired"}]

    class _Never:
        def send(self, _message):
            pass

        def settimeout(self, _timeout):
            pass

        def recv(self):
            raise TimeoutError("never")

    page._ws = _Never()
    monkeypatch.setattr(module, "RAW_CALL_TIMEOUT_S", 0.01)
    with pytest.raises(RuntimeError, match="CDP call timeout"):
        page.call("Runtime.evaluate")


@pytest.mark.parametrize(("raw_ok", "expected_exit"), ((True, 0), (False, 1)))
def test_main_falls_back_after_playwright_attach_timeout(monkeypatch, raw_ok, expected_exit) -> None:
    module = load_module()
    calls = []

    class _Chromium:
        def connect_over_cdp(self, *_args, **_kwargs):
            raise TimeoutError("browser-level CDP attach timeout")

    class _Playwright:
        chromium = _Chromium()

        def stop(self):
            calls.append("stop")

    class _Factory:
        def start(self):
            return _Playwright()

    monkeypatch.setattr(module, "sync_playwright", lambda: _Factory())
    monkeypatch.setattr(module, "_detect_cdp", lambda: "http://localhost:9222")

    def raw_fallback(cp2, key, cdp):
        calls.append((cp2, key, cdp))
        return raw_ok

    monkeypatch.setattr(module, "_raw_cp2", raw_fallback)
    monkeypatch.setenv("CAPAFY_HOST_OPENROUTER_KEY", "test-secret")
    monkeypatch.setattr(sys, "argv", ["drive_checkpoint2.py", "https://capafy.ai/developer/createAgent?token=t&page=credential"])

    with pytest.raises(SystemExit) as exc:
        module.main()

    assert exc.value.code == expected_exit
    assert calls[0] == "stop"
    assert calls[1][0].startswith("https://capafy.ai/developer/createAgent?")
    assert calls[1][2] == "http://localhost:9222"


def test_fresh_success_accepts_only_new_toast_or_url_transition() -> None:
    module = load_module()
    before = "https://capafy.ai/developer/createAgent?token=t&page=credential"
    assert module._fresh_success(before, ["キー確認済み"], before, "キー確認済み") is False
    assert module._fresh_success(before, [], before, "キー確認済み") is True
    assert module._fresh_success(before, [], before + "&page=credential-done", "") is True


def test_fallback_does_not_print_secret(capsys, monkeypatch) -> None:
    module = load_module()

    class _Chromium:
        def connect_over_cdp(self, *_args, **_kwargs):
            raise TimeoutError("attach")

    class _Playwright:
        chromium = _Chromium()

        def stop(self):
            pass

    class _Factory:
        def start(self):
            return _Playwright()

    monkeypatch.setattr(module, "sync_playwright", lambda: _Factory())
    monkeypatch.setattr(module, "_detect_cdp", lambda: "http://127.0.0.1:9222")
    monkeypatch.setattr(module, "_raw_cp2", lambda *_args: True)
    monkeypatch.setenv("CAPAFY_HOST_OPENROUTER_KEY", "do-not-print-secret")
    monkeypatch.setattr(sys, "argv", ["drive_checkpoint2.py", "https://capafy.ai/developer/createAgent?token=t&page=credential"])

    with pytest.raises(SystemExit) as exc:
        module.main()
    assert exc.value.code == 0
    assert "do-not-print-secret" not in capsys.readouterr().out
