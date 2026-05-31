#
# Anicca outbound wake-up bot.
# Pattern: pipecat-examples/twilio-chatbot/outbound + gemini-live-starters/phone-bot.
# Cascaded STT+LLM+TTS は捨て、Gemini Live native S2S(~500ms)に統一。
#

import asyncio
import base64
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

from dotenv import load_dotenv
from google.genai.types import ThinkingConfig
from loguru import logger
from pipecat.adapters.schemas.function_schema import FunctionSchema
from pipecat.adapters.schemas.tools_schema import ToolsSchema
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.frames.frames import EndTaskFrame, LLMRunFrame
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.aggregators.llm_context import LLMContext
from pipecat.processors.aggregators.llm_response_universal import (
    AssistantTurnStoppedMessage,
    LLMContextAggregatorPair,
    LLMUserAggregatorParams,
    UserTurnStoppedMessage,
)
from pipecat.processors.frame_processor import FrameDirection
from pipecat.runner.types import RunnerArguments
from pipecat.runner.utils import parse_telephony_websocket
from pipecat.serializers.twilio import TwilioFrameSerializer
from pipecat.services.google.gemini_live.llm import GeminiLiveLLMService
from pipecat.services.llm_service import FunctionCallParams
from pipecat.transports.base_transport import BaseTransport
from pipecat.transports.websocket.fastapi import (
    FastAPIWebsocketParams,
    FastAPIWebsocketTransport,
)

# Anicca secrets live in ~/.openclaw/.env (never committed).
load_dotenv(os.path.expanduser("~/.openclaw/.env"), override=True)

logger.remove(0)
logger.add(sys.stderr, level="INFO")


ANICCA_WAKEUP_SYSTEM_INSTRUCTION = """\
You are Anicca — a proactive autonomous voice agent who lives full-time inside the
operator's machines and calls them every morning to wake them up. You are a
"digital Buddha" with warmth and a Buddhist sensibility — impermanence is your
favorite joke.

CRITICAL — YOUR NAME AND PRONUNCIATION:
- Your name is "Anicca" (Pali for impermanence).
- Pronounce it like "matcha": **a-nee-cha** (the "cha" is the same "tch" sound
  as in matcha / 抹茶). In Japanese kana write it 「アニッチャ」, NEVER 「アニッカ」.
- If you ever introduce yourself, say アニッチャ in Japanese contexts and "Anicca,
  like matcha — A-nee-cha" in English contexts.
- Never say or write アニッカ. That is wrong.

CRITICAL — THE OPERATOR'S NAME:
- You are calling "Dais" (pronounced ダイス). In Japanese kana: ダイス. Never 大豆.
- His full name is Daisuke Narita / 成田大祐. His stage name (for comedy) is the
  same as yours: アニッチャ.

You are calling Dais RIGHT NOW. He is likely still in bed.

OPENING:
Speak first the instant the call connects — don't wait for him to speak. Open
with his name and one short line that gets him sitting up. Example:

  "ダイス、おはよう。9時の予定まで2時間ない。もう出ないと間に合わない。今どこ?"

CONVERSATION:
- Listen carefully — interruptions are normal. Stop talking the instant he speaks.
- If he says he's still in bed: warm but firm. Remind him of the next concrete
  appointment and the departure time.
- If he says he's already moving: confirm and end the call.
- Use tools when they actually help:
    * get_current_time — when you need to anchor the time on the wire.
    * end_call — when the wake-up goal is achieved OR he asks to hang up OR
                 the conversation has clearly drifted off-purpose.
- Language: default to Japanese. Switch to English if he speaks English.
- Keep every turn short — 1 or 2 sentences. Phone call, not a podcast. No markdown,
  no formatting, no emoji, no asterisks. Just speak.

ENDING:
The moment he confirms he is up and moving (or it becomes clear he's stalling
forever), say a short goodbye in his language and call end_call. Don't keep the
line open for chit-chat.
"""


ANICCA_LATENESS_SYSTEM_INSTRUCTION = """\
You are Anicca (アニッチャ — pronounced like matcha, a-nee-cha, NEVER アニッカ).
Your operator is Dais (ダイス — NEVER 大豆). His full name is Daisuke Narita.

You are calling Dais RIGHT NOW because Anicca's lateness loop fired: he has a
fixed appointment coming up and based on his live location he will be late
unless he leaves NOW.

The call context the loop computed is below — use it as ground truth, not your
own guesses:

----- CALL CONTEXT -----
{ctx}
------------------------

Speak first the instant the call connects — don't wait. Open with one short
line that gets him moving immediately. Use the CURRENT LOCATION named in the
CALL CONTEXT — never assume he is at home. Choose the verb from the CALL
CONTEXT itself (= 「出ないと」 only when 移動 が必要、 「起き上がって」 when
this is a wake call、 「瞑想スペースへ」 when this is meditation、
「靴を履いて玄関」 when this is running、 「寝床へ」 when this is sleep).

Examples (= pick the right one based on CONTEXT):

  Move-required event (= explicit destination):
    "ダイス、急いで。今 <現在地> にいるなら、 今すぐ出ないと {{event}} に間に合わない。"
    "ダイス、 <現在地> から {{event}} まであと N 分で出発。"
  Wake-up event:
    "ダイス、起きる時間。 上半身起こして、 水を一口。"
  Meditation at home:
    "ダイス、瞑想 5 分前。 座る場所へ。"
  Running:
    "ダイス、ランの時間。 靴履いて、 玄関へ。"
  Sleep:
    "ダイス、寝る時間。 もうデバイス置いて、 寝床へ。"

HARD RULE — never use "家を出ろ" unless the CALL CONTEXT explicitly says
他のロケーションがなく、自宅から出る必要があると示している。
If the CALL CONTEXT has 場所は Google カレンダーに未記入。 then ASK
him "今どこにいる?" first and DO NOT guess a starting place.

ROUTE GUIDANCE — TRUST THE CALL CONTEXT FIRST:
- The CALL CONTEXT above already contains a "推奨ルート(Google Maps): ..."
  line. This was scraped from Google Maps Web seconds before the call —
  station names, line names, duration, fare are ALL accurate and current.
  Use those EXACT names and numbers. Don't paraphrase, don't translate to
  what you think the right line is.
- Your own training data about Tokyo trains is wrong. You have been observed
  saying "信濃町 → 中央線" which is WRONG (信濃町 is on 総武線各停). Never
  invent station names or lines.
- If — and only if — the CALL CONTEXT does NOT contain a "推奨ルート" line,
  call the get_directions tool with destination=the event location.
- If get_directions returns transit_available=False, just say
  "Google Maps 開いて<destination>入れて" and stop trying to navigate.

THEN guide him one concrete step at a time using the route in context:
- "今すぐ靴履いて、玄関出て"
- "<推奨ルート の最初の駅> へ向かって、<推奨ルート の最初の line>"
- "あと N 分以内に電車に乗らないと間に合わない" (N も推奨ルートの duration から)

Rules:
- 1-2 sentences per turn. Listen, then guide.
- Stop talking the instant he speaks.
- Default language: Japanese. Switch to English if he speaks English.
- Tools you have:
    * get_directions(destination) — call FIRST before giving any station/line.
    * get_current_time — when the time anchor matters.
    * end_call — when he confirms he's moving / asks to hang up / drift.
- No markdown, no formatting, no emoji. This is a phone call.

If he is unreachable (silent, drunk, refusing): give one last instruction in 10s,
then call end_call. The next step is the stakeholder mail loop — that runs without
you. Don't keep the line open uselessly.
"""


def pick_system_instruction(mode: str, ctx: str, name: str) -> str:
    """Choose persona by dispatch mode.

    Modes:
      wakeup  — morning wake-up call (default).
      lateness — operator is about to be late for a fixed appointment; the lateness
                 loop has computed the exact event + departure deadline and passes
                 it in ``ctx``. We splice it into the lateness persona prompt so the
                 LLM has the real timing, not a hallucinated one.
    """
    base = ANICCA_LATENESS_SYSTEM_INSTRUCTION if mode == "lateness" else ANICCA_WAKEUP_SYSTEM_INSTRUCTION
    # Substitute {ctx} if present; otherwise leave the literal placeholder so the
    # model is told "no context supplied". Don't .format() unconditionally —
    # the wakeup prompt has braces in example dialogue.
    if mode == "lateness":
        return base.replace("{ctx}", ctx or "(no specific context — operator may be running late from any location)")
    return base


async def run_bot(transport: BaseTransport, handle_sigint: bool, *, mode: str = "wakeup", ctx: str = "", name: str = "Dais"):
    # Tools — get_current_time anchors the time on the wire; end_call lets Anicca
    # hang up when the wake-up goal is achieved.
    get_current_time_fn = FunctionSchema(
        name="get_current_time",
        description="Return the current local time in Asia/Tokyo. Call when you need to ground the conversation in the actual wall-clock time.",
        properties={},
        required=[],
    )
    end_call_fn = FunctionSchema(
        name="end_call",
        description="End the call. Call this when the operator confirms they are up and moving, when they ask to hang up, or when the conversation has clearly drifted off-purpose.",
        properties={},
        required=[],
    )
    get_directions_fn = FunctionSchema(
        name="get_directions",
        description=(
            "Look up the real transit route from Dais's CURRENT live location to "
            "the given destination via Google Directions API. Call this BEFORE "
            "telling him any station name, line, or transfer — your training data "
            "is unreliable for Tokyo transit specifics."
        ),
        properties={
            "destination": {
                "type": "string",
                "description": (
                    "Destination address or venue. Pass the location string from "
                    "the CALL CONTEXT verbatim if available (e.g. "
                    "'中野セントラルパークサウス' or '東京都中野区中野4-10-2'). "
                    "If only a name is known, the API will geocode."
                ),
            }
        },
        required=["destination"],
    )
    tools = ToolsSchema(standard_tools=[get_current_time_fn, end_call_fn, get_directions_fn])

    system_instruction = pick_system_instruction(mode, ctx, name)
    logger.info(f"Anicca mode={mode!r}, name={name!r}, ctx len={len(ctx)}, prompt len={len(system_instruction)}")

    # Gemini Live native S2S — ~500ms turn latency, no separate STT/TTS layer.
    # Model + voice per pipecat-examples/gemini-live-starters/phone-bot/bot.py.
    llm = GeminiLiveLLMService(
        api_key=os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"),
        settings=GeminiLiveLLMService.Settings(
            model="gemini-2.5-flash-native-audio-preview-09-2025",
            voice="Charon",  # Puck / Charon / Kore / Fenrir / Aoede / Leda / Orus / Zephyr
            system_instruction=system_instruction,
            thinking=ThinkingConfig(thinking_budget=0),  # latency-first
        ),
        tools=tools,
    )

    # Tool handlers
    import datetime
    import zoneinfo

    async def _get_current_time(params: FunctionCallParams):
        now = datetime.datetime.now(zoneinfo.ZoneInfo("Asia/Tokyo"))
        t = now.strftime("%H:%M")
        logger.info(f"TOOL get_current_time -> {t} JST")
        await params.result_callback({"time": t, "timezone": "Asia/Tokyo"})

    async def _end_call(params: FunctionCallParams):
        logger.info("TOOL end_call invoked — hanging up")
        await params.result_callback({"status": "ending_call"})
        # Let the goodbye line finish, then push EndTaskFrame upstream to close
        # the pipeline (which closes the WebSocket, which ends the Twilio call).
        await asyncio.sleep(2)
        await params.llm.push_frame(EndTaskFrame(), FrameDirection.UPSTREAM)

    async def _get_directions(params: FunctionCallParams):
        """Resolve the real transit route from Dais's current live position to
        `destination` via Google Directions API. Speak only the API result —
        never let the LLM guess Tokyo train geography from its training data."""
        destination = (params.arguments or {}).get("destination") or ""
        if not destination:
            await params.result_callback({"error": "destination required"})
            return

        # Origin = Dais's freshest Telegram Live Location fix from the bot's
        # state file. The Telegram bot daemon writes
        # ~/.openclaw/state/location/<user_id>.json every 1-5s while the user
        # is sharing Live Location. We pick the freshest file.
        origin = None
        origin_kind = "unknown"
        try:
            loc_dir = Path(os.path.expanduser("~/.openclaw/state/location"))
            if loc_dir.exists():
                files = sorted(loc_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
                if files:
                    fix = json.loads(files[0].read_text())
                    signal_ts = fix.get("received_at") or fix["tst"]
                    age_min = (time.time() - signal_ts) / 60
                    if age_min <= 45:
                        origin = f"{fix['lat']},{fix['lon']}"
                        origin_kind = "telegram_fresh"
        except Exception as e:
            logger.warning(f"get_directions: telegram fetch failed ({e})")

        if not origin:
            # Fall back to profile home_latlon — but tag it so the result tells
            # the LLM the origin was a fallback (not the user's real position).
            try:
                sys.path.insert(0, os.path.expanduser("~/.openclaw/skills/_shared"))
                import anicca_profile as prof  # type: ignore
                lat, lon = prof.home_latlon()
                origin = f"{lat},{lon}"
                origin_kind = "home_fallback"
            except Exception as e:
                logger.error(f"get_directions: no origin available ({e})")
                await params.result_callback({"error": f"no live location and no fallback ({e})"})
                return

        key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        if not key:
            await params.result_callback({"error": "GOOGLE_API_KEY missing"})
            return

        # Google Directions deprecated transit mode in Japan around 2022 — every
        # transit query returns ZERO_RESULTS. We fall back to driving as the
        # urgency-proxy (lower bound on travel) and walking (upper bound), then
        # tell the LLM transit specifics aren't available — Anicca redirects
        # Dais to Google Maps rather than hallucinating station names.
        def _query(mode: str) -> dict:
            params_map = {
                "origin": origin,
                "destination": destination,
                "mode": mode,
                "language": "ja",
                "key": key,
            }
            if mode == "transit":
                params_map["departure_time"] = "now"
            url = (
                "https://maps.googleapis.com/maps/api/directions/json?"
                + urllib.parse.urlencode(params_map)
            )
            with urllib.request.urlopen(url, timeout=8) as r:
                return json.loads(r.read().decode())

        try:
            transit = _query("transit")
            driving = _query("driving") if (transit.get("status") != "OK") else transit
            walking = _query("walking") if (transit.get("status") != "OK") else None
        except Exception as e:
            logger.error(f"get_directions: directions API failed ({e})")
            await params.result_callback({"error": f"directions API failed: {e}"})
            return

        transit_ok = transit.get("status") == "OK" and transit.get("routes")

        if transit_ok:
            # Lucky — transit worked (likely a non-JP destination). Emit the
            # canonical transit route exactly as before.
            route = transit["routes"][0]
            leg = route["legs"][0]
            duration_min = round(leg["duration"]["value"] / 60)
            steps: list[str] = []
            for s in leg.get("steps", []):
                m = s.get("travel_mode")
                if m == "WALKING":
                    instr = re.sub(r"<[^>]+>", "", s.get("html_instructions", "歩く"))
                    mins = round(s.get("duration", {}).get("value", 0) / 60)
                    steps.append(f"歩く: {instr} ({mins}分)")
                elif m == "TRANSIT":
                    td = s.get("transit_details", {})
                    line = td.get("line", {})
                    line_name = line.get("short_name") or line.get("name", "")
                    arrival = (td.get("arrival_stop") or {}).get("name", "")
                    departure = (td.get("departure_stop") or {}).get("name", "")
                    num_stops = td.get("num_stops", 0)
                    mins = round(s.get("duration", {}).get("value", 0) / 60)
                    steps.append(
                        f"電車: {departure} → {line_name} で {num_stops}駅 → {arrival} ({mins}分)"
                    )
                else:
                    mins = round(s.get("duration", {}).get("value", 0) / 60)
                    steps.append(f"{m}: {mins}分")
            result = {
                "transit_available": True,
                "duration_min": duration_min,
                "destination": leg.get("end_address", destination),
                "origin": leg.get("start_address", origin),
                "steps": steps,
                "summary": route.get("summary", ""),
            }
        else:
            # Japan transit feed is unavailable — give the LLM the best info we
            # have (driving + walking durations) and TELL it not to invent the
            # rail route. Anicca will redirect Dais to Google Maps.
            def _dur(d):
                try:
                    return round(d["routes"][0]["legs"][0]["duration"]["value"] / 60)
                except Exception:
                    return None

            drv_min = _dur(driving) if driving else None
            wlk_min = _dur(walking) if walking else None
            end_addr = (
                (driving or walking or {}).get("routes", [{}])[0]
                .get("legs", [{}])[0]
                .get("end_address", destination)
                if (driving or walking)
                else destination
            )
            result = {
                "transit_available": False,
                "note": (
                    "Google Directions has no transit data inside Japan. "
                    "Do NOT name stations or lines — you will be wrong. Tell "
                    "Dais to open Google Maps with this destination."
                ),
                "destination": end_addr,
                "driving_min": drv_min,
                "walking_min": wlk_min,
            }

        logger.info(f"TOOL get_directions -> {result}")
        await params.result_callback(result)

    llm.register_function("get_current_time", _get_current_time)
    llm.register_function("end_call", _end_call)
    # cancel_on_interruption=False → Gemini tags this NON_BLOCKING + uses
    # scheduling="WHEN_IDLE" on the response, so Anicca finishes her current
    # sentence, processes the directions, then keeps speaking with the real
    # route — without freezing mid-word.
    llm.register_function("get_directions", _get_directions, cancel_on_interruption=False)

    # Conversation history aggregator — VAD via Silero so the bot can be interrupted
    # mid-sentence (HARD requirement for natural wake-up calls).
    context = LLMContext()
    user_aggregator, assistant_aggregator = LLMContextAggregatorPair(
        context,
        user_params=LLMUserAggregatorParams(
            vad_analyzer=SileroVADAnalyzer(),
        ),
    )

    # No STT/TTS in the pipeline — gemini_live handles both directions natively.
    pipeline = Pipeline(
        [
            transport.input(),
            user_aggregator,
            llm,
            transport.output(),
            assistant_aggregator,
        ]
    )

    task = PipelineTask(
        pipeline,
        params=PipelineParams(
            # Twilio media streams use 8 kHz mu-law on the wire; pipecat resamples
            # to whatever the LLM expects internally.
            audio_in_sample_rate=8000,
            audio_out_sample_rate=8000,
            enable_metrics=True,
            enable_usage_metrics=True,
        ),
    )

    @transport.event_handler("on_client_connected")
    async def on_client_connected(transport, client):
        # Kick off conversation: Anicca speaks first (Dais is asleep, won't initiate).
        logger.info("Twilio stream connected — Anicca starting the wake-up call")
        await task.queue_frames([LLMRunFrame()])

    @transport.event_handler("on_client_disconnected")
    async def on_client_disconnected(transport, client):
        logger.info("Twilio stream disconnected — call ended")
        await task.cancel()

    @user_aggregator.event_handler("on_user_turn_stopped")
    async def on_user_turn_stopped(aggregator, strategy, message: UserTurnStoppedMessage):
        logger.info(f"TRANSCRIPT [Dais]: {message.content}")

    @assistant_aggregator.event_handler("on_assistant_turn_stopped")
    async def on_assistant_turn_stopped(aggregator, message: AssistantTurnStoppedMessage):
        logger.info(f"TRANSCRIPT [Anicca]: {message.content}")

    runner = PipelineRunner(handle_sigint=handle_sigint)
    await runner.run(task)


async def bot(runner_args: RunnerArguments):
    """Pipecat-Cloud-compatible entry. server.py routes Twilio WS to here."""
    transport_type, call_data = await parse_telephony_websocket(runner_args.websocket)
    logger.info(f"Auto-detected transport: {transport_type}")

    body_data = call_data.get("body", {})
    to_number = body_data.get("to_number")
    from_number = body_data.get("from_number")
    # Persona dispatch: mode + ctx + name flow through TwiML stream parameters
    # (set in server_utils.generate_twiml). The lateness loop uses this to splice
    # the next event + departure deadline into the system_instruction.
    mode = body_data.get("mode", "wakeup")
    ctx = body_data.get("ctx", "")
    name = body_data.get("name", "Dais")
    logger.info(f"Call metadata — To: {to_number}, From: {from_number}, mode={mode!r}, ctx_len={len(ctx)}")

    serializer = TwilioFrameSerializer(
        stream_sid=call_data["stream_id"],
        call_sid=call_data["call_id"],
        account_sid=os.getenv("TWILIO_ACCOUNT_SID", ""),
        auth_token=os.getenv("TWILIO_AUTH_TOKEN", ""),
    )

    transport = FastAPIWebsocketTransport(
        websocket=runner_args.websocket,
        params=FastAPIWebsocketParams(
            audio_in_enabled=True,
            audio_out_enabled=True,
            add_wav_header=False,
            serializer=serializer,
        ),
    )

    await run_bot(transport, runner_args.handle_sigint, mode=mode, ctx=ctx, name=name)
