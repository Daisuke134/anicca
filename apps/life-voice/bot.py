# apps/life-voice/bot.py — Life Manager FREE compositional TWO-WAY voice agent (Pipecat v1.4.0).
# C1 (VCSDD life-manager-cost-connect-reliability). Replaces Gemini Live native-audio with a cascaded
# pipeline that DOES real back-and-forth conversation (listen → understand → respond → the caller can
# interrupt): Silero VAD + Smart Turn v3 (turn-taking, 23 langs incl Japanese) → Groq Whisper STT →
# Groq Llama LLM → Kokoro TTS. NO Gemini Live is ever opened. ~$0.01-0.02/min all-in.
#
# The Node service (apps/life-call) schedules + dials; Telnyx streams the call here (stream_url = this
# service's WSS). The per-call context (event/urgency/lang/name) + HMAC sig arrive on the WS query and are
# verified (OQ9) by server.py before the pipeline starts.
#
# API verified against pipecat v1.4.0 (pinned in pyproject.toml): pipeline execution = PipelineWorker
# (pipecat.pipeline.worker) + WorkerRunner (pipecat.workers.runner); VAD + Smart Turn go into
# LLMUserAggregatorParams (NOT PipelineParams); the greeting is a transport on_client_connected handler.
# Refs: pipecat-ai/pipecat examples/turn-management/turn-management-smart-turn-local-coreml.py +
# pipecat-examples/telnyx-chatbot/inbound/bot.py (both @ current API).
import os

from loguru import logger
from pipecat.audio.turn.smart_turn.local_smart_turn_v3 import LocalSmartTurnAnalyzerV3
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.frames.frames import LLMRunFrame
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.worker import PipelineParams, PipelineWorker
from pipecat.processors.aggregators.llm_context import LLMContext
from pipecat.processors.aggregators.llm_response_universal import (
    LLMContextAggregatorPair,
    LLMUserAggregatorParams,
)
from pipecat.services.groq.llm import GroqLLMService
from pipecat.services.groq.stt import GroqSTTService
from pipecat.services.kokoro.tts import KokoroTTSService
from pipecat.transcriptions.language import Language
from pipecat.transports.base_transport import BaseTransport
from pipecat.turns.user_stop import TurnAnalyzerUserTurnStopStrategy
from pipecat.turns.user_turn_strategies import UserTurnStrategies
from pipecat.workers.runner import WorkerRunner

GROQ_KEY = os.getenv("GROQ_API_KEY", "")
# Kokoro model files auto-download on first init if the paths are unset (KokoroTTSService._ensure_model_files).
KOKORO_MODEL = os.getenv("KOKORO_MODEL_PATH") or None
KOKORO_VOICES = os.getenv("KOKORO_VOICES_PATH") or None


def _system_instruction(event: dict, urgency: str, lang: str) -> str:
    ja = str(lang).startswith("ja")
    title = (event or {}).get("summary") or ("ご予定" if ja else "your appointment")
    place = (event or {}).get("location") or ""
    if ja:
        return (
            f"あなたは Life Manager、電話越しの簡潔なアシスタントです。ユーザーの次の予定「{title}」"
            f"（場所: {place or '未設定'}）について、出発を促し、質問には1〜2文の短い日本語で答えます。"
            "音声に変換されるので記号は使わないでください。"
        )
    return (
        f"You are Life Manager, a concise phone assistant. Nudge the user to leave for their next "
        f"event '{title}' ({place or 'no location'}) and answer questions in one or two short sentences. "
        "Your output is spoken, so avoid special characters."
    )


# run_bot(transport, ctx): build + run the compositional pipeline for one answered call.
# ctx = {event, urgency, lang, name} (already HMAC-verified by server.py).
async def run_bot(transport: BaseTransport, ctx: dict):
    event, urgency, lang = ctx.get("event", {}), ctx.get("urgency", "firm"), ctx.get("lang", "ja")
    is_ja = str(lang).startswith("ja")

    stt = GroqSTTService(api_key=GROQ_KEY, model="whisper-large-v3-turbo")
    llm = GroqLLMService(api_key=GROQ_KEY, model="llama-3.1-8b-instant")
    # language MUST be set for JA (default is Language.EN) — jf_alpha voice + EN lang code garbles Japanese.
    tts = KokoroTTSService(
        voice_id=("jf_alpha" if is_ja else "af_heart"),
        model_path=KOKORO_MODEL,
        voices_path=KOKORO_VOICES,
        params=KokoroTTSService.InputParams(language=Language.JA if is_ja else Language.EN),
    )

    context = LLMContext([{"role": "system", "content": _system_instruction(event, urgency, lang)}])
    user_aggregator, assistant_aggregator = LLMContextAggregatorPair(
        context,
        user_params=LLMUserAggregatorParams(
            # Silero VAD detects speech; Smart Turn v3 decides when the caller's turn is really over —
            # together they make this a conversation (not walkie-talkie). Interruptions are on by default,
            # so the caller can barge in and Pipecat cancels in-flight TTS + clears the Telnyx queue.
            user_turn_strategies=UserTurnStrategies(
                stop=[TurnAnalyzerUserTurnStopStrategy(turn_analyzer=LocalSmartTurnAnalyzerV3())]
            ),
            vad_analyzer=SileroVADAnalyzer(),
        ),
    )

    pipeline = Pipeline([
        transport.input(),    # Telnyx μ-law 8k in
        stt,                  # Groq Whisper STT
        user_aggregator,      # user responses → context
        llm,                  # Groq Llama LLM (streams)
        tts,                  # Kokoro TTS (streams) → μ-law out
        transport.output(),   # Telnyx media out
        assistant_aggregator, # assistant spoken responses → context
    ])

    worker = PipelineWorker(
        pipeline,
        params=PipelineParams(
            audio_in_sample_rate=8000,
            audio_out_sample_rate=8000,
            enable_metrics=True,
            enable_usage_metrics=True,
        ),
    )

    @transport.event_handler("on_client_connected")
    async def _greet(_transport, _client):
        # GREET-FIRST (Live-API best practice): the agent opens the conversation, then converses.
        context.add_message({"role": "developer", "content": "Greet the caller and nudge them about the event now."})
        await worker.queue_frames([LLMRunFrame()])

    @transport.event_handler("on_client_disconnected")
    async def _bye(_transport, _client):
        await worker.cancel()

    logger.info(f"[life-voice] pipeline start urgency={urgency} lang={lang} live_ws_opened=0")
    runner = WorkerRunner(handle_sigint=False)
    await runner.add_workers(worker)
    await runner.run()
