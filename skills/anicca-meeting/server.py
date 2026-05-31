#
# Anicca meeting server — hosts the SmallWebRTC signalling endpoint and the
# prebuilt control webpage that Recall.ai's Chrome bot loads.
#
# Endpoints:
#   GET  /             — redirect to /prebuilt/ (the Pipecat prebuilt UI)
#   GET  /prebuilt/*   — Pipecat's built-in WebRTC client (mounted by FastAPI)
#   POST /api/offer    — WebRTC SDP offer/answer (handled by SmallWebRTCRequestHandler)
#   PATCH /api/offer   — ICE candidate updates
#   POST /api/launch   — launch a Recall bot pointed at a Meet/Zoom URL
#                        (passes the live tunnel URL so the bot loads /prebuilt/)
#

import asyncio
import base64
import json
import os
import pathlib
import time
import urllib.request

import uvicorn
from dotenv import load_dotenv
from fastapi import BackgroundTasks, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from sse_starlette.sse import EventSourceResponse
from loguru import logger
from pipecat.transports.smallwebrtc.connection import IceServer
from pipecat.transports.smallwebrtc.request_handler import (
    SmallWebRTCPatchRequest,
    SmallWebRTCRequest,
    SmallWebRTCRequestHandler,
)
from pipecat_ai_small_webrtc_prebuilt.frontend import SmallWebRTCPrebuiltUI

from bot import run_bot

load_dotenv(os.path.expanduser("~/.openclaw/.env"), override=True)

BASE_DIR = pathlib.Path(__file__).parent
AUTO_HTML = BASE_DIR / "auto.html"
SLIDES_HTML = BASE_DIR / "slides.html"


# ---- Slide control bus ---------------------------------------------------
# Anicca's tools (next_slide / prev_slide / goto_slide / highlight) push
# small JSON commands here; the /slides/ page subscribes via SSE and applies
# them to reveal.js. Multiple subscribers (e.g. the actual screen-share
# Chrome + a local preview tab) each get their own queue so they all stay
# in sync.
_SLIDE_SUBSCRIBERS: "list[asyncio.Queue]" = []


def _broadcast_slide_cmd(cmd: dict) -> None:
    """Push one command to every connected /slides/ page."""
    dead = []
    for q in _SLIDE_SUBSCRIBERS:
        try:
            q.put_nowait(cmd)
        except asyncio.QueueFull:
            dead.append(q)
    for q in dead:
        try:
            _SLIDE_SUBSCRIBERS.remove(q)
        except ValueError:
            pass

# ---- Twilio NTS (TURN) token cache --------------------------------------
# Pipecat docs (docs.pipecat.ai/.../small-webrtc#ice-servers-configuration)
# explicitly require TURN when peers are on different networks behind a strict
# NAT — which is exactly Recall's AWS Chrome → home-NAT Mac mini. We grab a
# Twilio NTS token (TTL=24h) and pass identical credentials to both sides:
#   - aiortc (server) via SmallWebRTCRequestHandler(ice_servers=...)
#   - browser (Recall Chrome) via GET /api/ice
_ICE_CACHE: dict = {"servers": [], "expires_at": 0}


def _twilio_nts_token() -> list[dict]:
    """Fetch fresh Twilio NTS ice_servers (or return cached)."""
    now = int(time.time())
    if _ICE_CACHE["servers"] and now < _ICE_CACHE["expires_at"]:
        return _ICE_CACHE["servers"]

    sid = os.getenv("TWILIO_ACCOUNT_SID")
    tok = os.getenv("TWILIO_AUTH_TOKEN")
    if not sid or not tok:
        logger.warning("TWILIO_ACCOUNT_SID/AUTH_TOKEN missing — falling back to public STUN only")
        servers = [{"urls": "stun:stun.l.google.com:19302"}]
        _ICE_CACHE["servers"] = servers
        _ICE_CACHE["expires_at"] = now + 600
        return servers

    auth = base64.b64encode(f"{sid}:{tok}".encode()).decode()
    req = urllib.request.Request(
        f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Tokens.json",
        data=b"",
        headers={"Authorization": f"Basic {auth}"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read().decode())
    except Exception as e:
        logger.error(f"Twilio NTS token fetch failed: {e}")
        return _ICE_CACHE["servers"] or [{"urls": "stun:stun.l.google.com:19302"}]

    # Twilio returns {"url": "..."} singular; WebRTC standard is "urls" plural.
    normalized = []
    for s in data.get("ice_servers") or []:
        out = {}
        if "urls" in s:
            out["urls"] = s["urls"]
        elif "url" in s:
            out["urls"] = s["url"]
        if "username" in s:
            out["username"] = s["username"]
        if "credential" in s:
            out["credential"] = s["credential"]
        normalized.append(out)

    ttl = int(data.get("ttl", 3600))
    _ICE_CACHE["servers"] = normalized
    _ICE_CACHE["expires_at"] = now + max(60, ttl - 300)  # refresh 5min before expiry
    logger.info(f"Twilio NTS token refreshed: {len(normalized)} ice_servers, ttl={ttl}s")
    return normalized


def _ice_servers_for_aiortc() -> list[IceServer]:
    """Convert cached NTS tokens into Pipecat/aiortc IceServer objects."""
    out = []
    for s in _twilio_nts_token():
        urls = s.get("urls")
        if not urls:
            continue
        kwargs: dict = {"urls": urls if isinstance(urls, list) else [urls]}
        if s.get("username"):
            kwargs["username"] = s["username"]
        if s.get("credential"):
            kwargs["credential"] = s["credential"]
        out.append(IceServer(**kwargs))
    return out


app = FastAPI()
app.mount("/prebuilt", SmallWebRTCPrebuiltUI)


@app.get("/auto/", include_in_schema=False)
@app.get("/auto", include_in_schema=False)
async def auto_page():
    """Headless auto-connecting WebRTC page for Recall.ai's Chrome bot.

    The Pipecat prebuilt UI at /prebuilt/ requires a human to click "Connect".
    Recall's bot never clicks anything, so it would just sit there. This page
    starts the WebRTC handshake the moment it loads — which is what Recall's
    headless Chrome needs.

    Reference: github.com/recallai/sample-apps/blob/main/bot_output_media_heygen_avatar/README.md
    """
    return FileResponse(AUTO_HTML, media_type="text/html")


@app.get("/slides/", include_in_schema=False)
@app.get("/slides", include_in_schema=False)
async def slides_page():
    """reveal.js presentation page that Recall publishes as the bot's
    screenshare. Subscribes to /slides/events for live control."""
    return FileResponse(SLIDES_HTML, media_type="text/html")


@app.get("/slides/events", include_in_schema=False)
async def slides_events(request: Request):
    """SSE channel: Anicca's tools push next/prev/goto/highlight here."""
    q: asyncio.Queue = asyncio.Queue(maxsize=64)
    _SLIDE_SUBSCRIBERS.append(q)
    logger.info(f"/slides/events subscriber attached (total={len(_SLIDE_SUBSCRIBERS)})")

    async def stream():
        try:
            # Greet the page so the SSE handshake completes and reveal.js
            # flips its status to "connected".
            yield {"data": json.dumps({"cmd": "ping"})}
            while True:
                if await request.is_disconnected():
                    break
                try:
                    cmd = await asyncio.wait_for(q.get(), timeout=15.0)
                    yield {"data": json.dumps(cmd)}
                except asyncio.TimeoutError:
                    # Periodic heartbeat keeps the SSE channel + cloudflared
                    # connection from idling out.
                    yield {"data": json.dumps({"cmd": "ping"})}
        finally:
            try:
                _SLIDE_SUBSCRIBERS.remove(q)
            except ValueError:
                pass
            logger.info(f"/slides/events subscriber detached (total={len(_SLIDE_SUBSCRIBERS)})")

    return EventSourceResponse(stream())


@app.post("/slides/cmd")
async def slides_cmd(request: Request):
    """Direct push for testing — Anicca normally invokes via Pipecat tools.

    Body: {"cmd": "next" | "prev" | "highlight" | "goto", "index": 2}
    """
    body = await request.json()
    if not isinstance(body, dict) or "cmd" not in body:
        raise HTTPException(status_code=400, detail="cmd field required")
    _broadcast_slide_cmd(body)
    return {"status": "ok", "subscribers": len(_SLIDE_SUBSCRIBERS)}


@app.get("/api/ice")
async def get_ice_servers():
    """Hand the browser the same Twilio NTS ice_servers we hand aiortc.

    Both ends MUST use matching TURN credentials so a relay candidate pair can
    establish. Canonical config per Pipecat docs.
    """
    return JSONResponse({"ice_servers": _twilio_nts_token()})


# Prime the cache + build the handler with real TURN creds at startup.
_handler = SmallWebRTCRequestHandler(ice_servers=_ice_servers_for_aiortc())


@app.get("/", include_in_schema=False)
async def root():
    return RedirectResponse(url="/prebuilt/")


# Latest deck path requested by /api/launch — passed into run_bot when the
# next WebRTC offer arrives. Single-bot single-tenant; for multi-session
# isolation we'd key this by session/meeting id.
_PENDING_DECK_PATH: str | None = None


@app.post("/api/offer")
async def offer(request: SmallWebRTCRequest, background_tasks: BackgroundTasks):
    """WebRTC offer from the prebuilt UI (or Recall.ai's Chrome bot loading it)."""
    deck_path = _PENDING_DECK_PATH

    async def _on_connect(connection):
        background_tasks.add_task(run_bot, connection, deck_path=deck_path)

    answer = await _handler.handle_web_request(
        request=request,
        webrtc_connection_callback=_on_connect,
    )
    return answer


@app.patch("/api/offer")
async def ice_candidate(request: SmallWebRTCPatchRequest):
    await _handler.handle_patch_request(request)
    return {"status": "success"}


@app.post("/api/launch")
async def launch_recall_bot(request: Request):
    """Launch a Recall.ai bot into the given meeting URL.

    Body:
      {
        "meeting_url": "https://meet.google.com/...",
        "bot_name":    "Anicca"                          # optional
        "deck":        "default-anicca-lt-5min"          # optional, id or path
                                                          # → skills/anicca-meeting/decks/<id>.json
                                                          # absolute path also allowed
      }
    """
    global _PENDING_DECK_PATH
    body = await request.json()
    meeting_url = body.get("meeting_url")
    if not meeting_url:
        raise HTTPException(status_code=400, detail="meeting_url required")
    bot_name = body.get("bot_name", "Anicca")

    # Stash the deck so the next /api/offer hands it to run_bot. None resets
    # to the bundled default (default-anicca-lt-5min.json).
    deck_arg = (body.get("deck") or "").strip() or None
    if deck_arg and not deck_arg.endswith(".json"):
        deck_arg = f"{deck_arg}.json"  # let callers omit the suffix
    _PENDING_DECK_PATH = deck_arg
    logger.info(f"/api/launch deck = {_PENDING_DECK_PATH or '(default)'}")

    recall_key = os.getenv("RECALL_API_KEY")
    recall_region = os.getenv("RECALL_REGION", "ap-northeast-1")
    public_url = os.getenv("ANICCA_MEETING_PUBLIC_URL")
    if not recall_key:
        raise HTTPException(status_code=500, detail="RECALL_API_KEY missing")
    if not public_url:
        raise HTTPException(status_code=500, detail="ANICCA_MEETING_PUBLIC_URL missing (set by launchd run.sh)")

    # Recall.ai output_media supports `camera` + `screenshare` in parallel.
    # camera     → /auto/   (Anicca's voice + small visual identity orb)
    # screenshare → /slides/ (reveal.js deck driven live by Anicca's tools)
    # Reference: github.com/recallai/sample-apps/blob/main/bot_output_media_heygen_avatar/run.sh
    payload = {
        "meeting_url": meeting_url,
        "bot_name": bot_name,
        "output_media": {
            "camera": {
                # /auto/ is our headless WebRTC bootstrap (auto-runs on load).
                # /prebuilt/ would require a human click and so never connects.
                "kind": "webpage",
                "config": {"url": f"{public_url}/auto/"},
            },
            "screenshare": {
                "kind": "webpage",
                "config": {"url": f"{public_url}/slides/"},
            },
        },
        "recording_config": {
            "include_bot_in_recording": {"audio": True},
        },
        "variant": {
            "zoom": "web_4_core",
            "google_meet": "web_4_core",
            "microsoft_teams": "web_4_core",
            "webex": "web_4_core",
        },
    }
    req = urllib.request.Request(
        f"https://{recall_region}.recall.ai/api/v1/bot/",
        data=json.dumps(payload).encode(),
        headers={
            "Authorization": f"Token {recall_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        detail = e.read().decode() if hasattr(e, "read") else str(e)
        logger.error(f"Recall launch failed: {e.code} {detail}")
        raise HTTPException(status_code=502, detail=f"Recall {e.code}: {detail}")
    logger.info(f"Recall bot launched: id={data.get('id')} meeting={meeting_url}")
    return JSONResponse(data)


if __name__ == "__main__":
    port = int(os.getenv("PORT", "7861"))
    logger.info(f"Anicca meeting server on :{port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
