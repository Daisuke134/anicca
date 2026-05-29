import pytest

import slack_sender


class FakeResponse:
    def __init__(self, status_code, text="", json_data=None):
        self.status_code = status_code
        self.text = text
        self._json = json_data or {}

    def json(self):
        return self._json


class FakeClient:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return self.responses.pop(0)


@pytest.mark.asyncio
async def test_send_to_slack_falls_back_to_bot_token(monkeypatch):
    payload = {"blocks": [{"text": {"text": "header"}}, {"text": {"text": "body"}}]}
    client = FakeClient(
        [
            FakeResponse(404, "no_service"),
            FakeResponse(200, json_data={"ok": True}),
        ]
    )

    monkeypatch.setenv("SLACK_METRICS_WEBHOOK_URL", "https://example.invalid/webhook")
    monkeypatch.setenv("SLACK_BOT_TOKEN", "xoxb-test")
    monkeypatch.setenv("SLACK_METRICS_CHANNEL_ID", "C091G3PKHL2")
    monkeypatch.setattr(slack_sender.httpx, "AsyncClient", lambda timeout=10.0: client)

    assert await slack_sender.send_to_slack(payload) is True
    assert client.calls[0][0] == "https://example.invalid/webhook"
    assert client.calls[1][0] == "https://slack.com/api/chat.postMessage"
