import asyncio
import importlib.util
import json
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts/cdp_nav_snapshot.py"
SPEC = importlib.util.spec_from_file_location("cdp_nav_snapshot_ownership", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


def test_hidden_target_is_claimed_and_released(monkeypatch):
    events = []
    responses = [
        json.dumps({"id": 1, "result": {"targetId": "hidden-owned"}}),
        json.dumps({"id": 2, "result": {"success": True}}),
    ]

    class Socket:
        async def send(self, payload):
            events.append(("send", json.loads(payload)["method"]))

        async def recv(self):
            return responses.pop(0)

    class Connection:
        async def __aenter__(self):
            return Socket()

        async def __aexit__(self, *_args):
            return None

    monkeypatch.setenv("CLOAK_BROWSER_OWNER", "gig-paid-direct")
    monkeypatch.setenv("CLOAK_CDP_BASE_URL", "http://127.0.0.1:9223")
    monkeypatch.setattr(MODULE, "_browser_ws_url", lambda: "ws://browser")
    monkeypatch.setattr(MODULE.websockets, "connect", lambda *_a, **_k: Connection())
    monkeypatch.setattr(
        MODULE.target_ownership,
        "claim_target",
        lambda target, owner: events.append(("claim", target, owner)),
    )
    monkeypatch.setattr(
        MODULE.target_ownership,
        "release_target",
        lambda target, owner: events.append(("release", target, owner)),
    )

    async def exercise():
        async with MODULE.hidden_page_target("https://coconala.com") as ws_url:
            assert ws_url.endswith("/hidden-owned")
            events.append(("yield",))

    asyncio.run(exercise())

    assert events == [
        ("send", "Target.createTarget"),
        ("claim", "hidden-owned", "gig-paid-direct"),
        ("yield",),
        ("send", "Target.closeTarget"),
        ("release", "hidden-owned", "gig-paid-direct"),
    ]
