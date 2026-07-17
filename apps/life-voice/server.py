# apps/life-voice/server.py — FastAPI WebSocket endpoint that Telnyx streams the call to. Verifies the
# same signed ctx the Node service produced (OQ9 HMAC carryover) BEFORE starting the Pipecat pipeline,
# then bridges the Telnyx media stream to bot.run_bot. NO Gemini Live anywhere.
import hashlib
import hmac
import json
import os

import uvicorn
from fastapi import FastAPI, WebSocket
from loguru import logger
from pipecat.serializers.telnyx import TelnyxFrameSerializer
from pipecat.transports.websocket.fastapi import FastAPIWebsocketParams, FastAPIWebsocketTransport

from bot import run_bot

LM_CALL_SECRET = os.getenv("LM_CALL_SECRET", "")
app = FastAPI()


# verify_ctx: recompute the HMAC exactly as Node's scheduler.js signCtx does — HMAC-SHA256 over
# [summary,dateTime,location,urgency,lang,name] joined by "\n", base64url — and timing-safe compare.
def verify_ctx(q: dict) -> bool:
    if not LM_CALL_SECRET or not q.get("sig"):
        return False
    parts = [q.get(k, "") for k in ("summary", "dateTime", "location", "urgency", "lang", "name")]
    mac = hmac.new(LM_CALL_SECRET.encode(), "\n".join(parts).encode(), hashlib.sha256).digest()
    import base64
    expected = base64.urlsafe_b64encode(mac).rstrip(b"=").decode()
    return hmac.compare_digest(expected, q.get("sig", ""))


@app.get("/health")
async def health():
    return {"ok": True, "service": "life-voice", "voice": "pipecat-groq-kokoro", "live_ws_opened": 0}


@app.websocket("/ws")
async def ws(ws: WebSocket):
    q = dict(ws.query_params)
    if not verify_ctx(q):
        logger.error("[life-voice] rejected unauthenticated /ws (bad signed ctx)")
        await ws.close(code=1008)
        return
    await ws.accept()

    # First two Telnyx frames carry the stream_id + call_control_id needed by the serializer.
    start = json.loads(await ws.receive_text())
    _connected = start  # "connected" event
    start2 = json.loads(await ws.receive_text())  # "start" event
    stream_id = (start2.get("stream_id") or start2.get("start", {}).get("stream_id"))
    call_control_id = start2.get("start", {}).get("call_control_id")

    serializer = TelnyxFrameSerializer(stream_id=stream_id, call_control_id=call_control_id)
    transport = FastAPIWebsocketTransport(
        websocket=ws,
        params=FastAPIWebsocketParams(
            audio_in_enabled=True,
            audio_out_enabled=True,
            add_wav_header=False,
            serializer=serializer,
        ),
    )
    ctx = {
        "event": {"summary": q.get("summary", ""), "location": q.get("location", ""),
                  "start": {"dateTime": q.get("dateTime", "")}},
        "urgency": q.get("urgency", "firm"),
        "lang": q.get("lang", "ja"),
        "name": q.get("name", ""),
    }
    logger.info(f"[life-voice] call accepted stream_id={stream_id} lang={ctx['lang']}")
    await run_bot(transport, ctx)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8080")))
