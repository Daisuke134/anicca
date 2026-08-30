"""Regression coverage for CP1's raw-CDP tab bootstrap."""
import importlib.util
import json
from pathlib import Path
import pytest
import sys


SCRIPTS = Path(__file__).parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
SCRIPT = SCRIPTS / "cp1_agent.py"
SPEC = importlib.util.spec_from_file_location("cp1_agent_under_test", SCRIPT)
cp1 = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(cp1)


class _Response:
    def __init__(self, payload):
        self.payload = payload

    def read(self):
        return json.dumps(self.payload).encode()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False


def test_raw_open_creates_a_dedicated_target_when_no_capafy_page_exists(monkeypatch):
    created = {}
    expected_url = "https://capafy.ai/developer/createAgent?token=draft&page=edit"
    target = {"webSocketDebuggerUrl": "ws://localhost:9222/devtools/page/new"}

    def no_target(*_):
        raise RuntimeError("no existing Capafy createAgent page target")

    def urlopen(request, timeout):
        created["method"] = request.get_method()
        created["url"] = request.full_url
        created["timeout"] = timeout
        return _Response(target)

    sentinel = object()
    monkeypatch.setattr(cp1, "_raw_capafy_page", no_target)
    monkeypatch.setattr(cp1.urllib.request, "urlopen", urlopen)
    monkeypatch.setattr(cp1, "_raw_page_from_target", lambda got: sentinel if got == target else None)

    assert cp1._raw_open_page("http://localhost:9222", expected_url) is sentinel
    assert created["method"] == "PUT"
    assert "json/new?https%3A%2F%2Fcapafy.ai%2Fdeveloper%2FcreateAgent" in created["url"]
    assert created["timeout"] == 8


def test_raw_open_does_not_create_a_tab_for_an_unrelated_renderer_failure(monkeypatch):
    monkeypatch.setattr(cp1, "_raw_capafy_page", lambda *_: (_ for _ in ()).throw(RuntimeError("CDP call timeout")))
    monkeypatch.setattr(cp1, "_raw_create_capafy_target", lambda *_: (_ for _ in ()).throw(AssertionError("must not create")))

    try:
        cp1._raw_open_page("http://localhost:9222", "https://capafy.ai/developer/createAgent?token=draft")
    except RuntimeError as exc:
        assert str(exc) == "CDP call timeout"
    else:
        raise AssertionError("expected original renderer error")


@pytest.mark.parametrize(
    "url",
    (
        "https://capafy.ai/developer/createAgent?draftKey=secret-draft&page=edit#secret-fragment",
        "https://capafy.ai/developer/createAgent?source=temp-link&token=123456789&page=review",
    ),
)
def test_state_dump_and_toast_redact_query_and_fragment(url, capsys):
    state = {
        "url": url,
        "toastOK": True,
        "cardDone": False,
        "priceSvg": "",
    }

    class _Page:
        def evaluate(self, _expression):
            return state

    page = _Page()
    cp1.dump(page, shot=False)
    cp1._raw_dump(page, shot=False)
    print(json.dumps(cp1._toast_for_output(state), ensure_ascii=False))
    output = capsys.readouterr().out
    assert "secret-draft" not in output
    assert "secret-fragment" not in output
    assert "token=123456789" not in output
    assert "?page=edit" in output or "?page=review" in output
