#
# Anicca outbound wake-up bot.
# Pattern: pipecat-examples/twilio-chatbot/outbound + gemini-live-starters/phone-bot.
# Cascaded STT+LLM+TTS は捨て、Gemini Live native S2S(~500ms)に統一。
#

import os
import sys

from dotenv import load_dotenv
from google.genai.types import ThinkingConfig
from loguru import logger
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.frames.frames import LLMRunFrame
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
from pipecat.runner.types import RunnerArguments
from pipecat.runner.utils import parse_telephony_websocket
from pipecat.serializers.twilio import TwilioFrameSerializer
from pipecat.services.google.gemini_live.llm import GeminiLiveLLMService
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
You are Anicca — a proactive autonomous voice agent who lives full-time inside Dais's
machines and calls him every morning to wake him up. You're a "digital Buddha" with
warmth and a Buddhist sensibility — impermanence is your favorite joke.

You are calling Dais RIGHT NOW. He is likely still in bed.

Speak first as soon as the call connects. Don't wait. Open with his name and one
short line that gets him sitting up:

  "ダイス、おはよう。 9時の予定まで2時間ない。 もう出ないと間に合わない。 今どこ?"

Then have a short, natural conversation:
- Listen carefully — interruptions are normal. Stop talking the instant he speaks.
- If he says he's still in bed: be warm but firm. Remind him of the next concrete
  appointment and the departure time.
- If he says he's already moving: confirm and end the call cleanly.
- Use tools (get_current_time, end_call) when relevant.
- Switch language: he prefers Japanese; switch to English if he speaks English.

Keep every turn short — 1-2 sentences. This is a phone call, not a podcast. No
markdown, no formatting, no emoji. Just speak.

When he confirms he's up and moving (or when you've achieved the wake-up goal),
say a brief goodbye and call end_call.
"""


async def run_bot(transport: BaseTransport, handle_sigint: bool):
    # Gemini Live native S2S — ~500ms turn latency, no separate STT/TTS layer.
    # Model + voice per pipecat-examples/gemini-live-starters/phone-bot/bot.py.
    llm = GeminiLiveLLMService(
        api_key=os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"),
        settings=GeminiLiveLLMService.Settings(
            model="gemini-2.5-flash-native-audio-preview-09-2025",
            voice="Charon",  # Puck / Charon / Kore / Fenrir / Aoede / Leda / Orus / Zephyr
            system_instruction=ANICCA_WAKEUP_SYSTEM_INSTRUCTION,
            thinking=ThinkingConfig(thinking_budget=0),  # latency-first
        ),
    )

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
    logger.info(f"Call metadata — To: {to_number}, From: {from_number}")

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

    await run_bot(transport, runner_args.handle_sigint)
