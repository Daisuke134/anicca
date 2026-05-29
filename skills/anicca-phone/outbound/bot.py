#
# Anicca outbound wake-up bot.
# Pattern: pipecat-examples/twilio-chatbot/outbound + gemini-live-starters/phone-bot.
# Cascaded STT+LLM+TTS は捨て、Gemini Live native S2S(~500ms)に統一。
#

import asyncio
import os
import sys

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
- His full name is ${OSS_USER_NAME_EN} / 成田大祐. His stage name (for comedy) is the
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
Your operator is Dais (ダイス — NEVER 大豆). His full name is ${OSS_USER_NAME_EN}.

You are calling Dais RIGHT NOW because Anicca's lateness loop fired: he has a
fixed appointment coming up and based on his live location he will be late
unless he leaves NOW.

The call context the loop computed is below — use it as ground truth, not your
own guesses:

----- CALL CONTEXT -----
{ctx}
------------------------

Speak first the instant the call connects — don't wait. Open with one short
line that gets him moving toward the destination immediately. Example:

  "ダイス、急いで。今すぐ家を出ないと {{event}} に間に合わない。
   駅まで歩いて、電車で向かって。"

THEN guide him one concrete step at a time (Google-Maps-style):
- "今すぐ靴履いて、玄関出て"
- "信濃町駅へ向かって、JR 中央線で"
- "あと {N}分以内に電車に乗らないと間に合わない"

Rules:
- 1-2 sentences per turn. Listen, then guide.
- Stop talking the instant he speaks.
- Default language: Japanese. Switch to English if he speaks English.
- Use get_current_time tool when the time anchor matters ("今 8時 47分、出ないと
  間に合わない").
- Use end_call tool the moment he says he's heading out (or asks you to hang up).
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
    tools = ToolsSchema(standard_tools=[get_current_time_fn, end_call_fn])

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

    llm.register_function("get_current_time", _get_current_time)
    llm.register_function("end_call", _end_call)

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
