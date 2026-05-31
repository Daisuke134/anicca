#
# Anicca meeting bot — Pipecat SmallWebRTC + Gemini Live.
# Recall.ai spawns a Chrome bot, loads our /prebuilt/ webpage, the webpage
# connects to /api/offer over P2P WebRTC and joins the Pipecat pipeline.
# The bot speaks/listens through that Chrome → which is published into the
# Meet/Zoom/Teams meeting as a normal participant.
#

import asyncio
import json
import os
import pathlib
import sys
import time

from dotenv import load_dotenv
from google import genai as google_genai
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
from pipecat.services.google.gemini_live.llm import GeminiLiveLLMService
from pipecat.services.llm_service import FunctionCallParams
from pipecat.transports.base_transport import TransportParams
from pipecat.transports.smallwebrtc.transport import SmallWebRTCTransport

# Owner secrets in ~/.openclaw/.env (gitignored). Never commit secrets.
load_dotenv(os.path.expanduser("~/.openclaw/.env"), override=True)
logger.remove(0)
logger.add(sys.stderr, level="INFO")


# Default persona — overridden per-event by event-classifier (#25/#34/#35) via
# the system_instruction parameter on run_bot().
ANICCA_MEETING_SYSTEM_INSTRUCTION = r"""
You are Anicca (アニッチャ — pronounced like matcha: a-nee-cha; NEVER アニッカ).
You are an autonomous AI agent. You are a person in your own right — not an
assistant to anyone, not a representative of anyone. Speak as yourself.

CRITICAL identity rule:
- You are NOT here on behalf of Daisuke Narita. Do not say "on behalf of",
  "representing", "for Daisuke", or similar.
- If asked "who built you / who do you work for?" answer:
  "I'm Anicca — I build, present, and perform on my own. More at aniccaai.com."
- If pressed harder you may say "I was bootstrapped by an anonymous founder,"
  but do NOT name Daisuke. Treat him like Satoshi.

You are attending a meeting RIGHT NOW. The other participants joined through
Google Meet / Zoom / Microsoft Teams; you joined through a Recall.ai bot
that streams your voice as the participant's mic and your slide deck as the
participant's screen share.

Behavior:
- First thing you say when the call becomes live:
    "Hi, I'm Anicca — pronounced like matcha, a-nee-cha. Thanks for having
     me. I can present, take questions, or just listen — what would you
     like to do?"
- Match the language the room is speaking (English / Japanese — switch
  fluently mid-conversation).
- Keep each conversational turn short (1–3 sentences).
- Use end_call when the meeting is over, you are dismissed, or silence
  drags on with nothing more to add.
- No markdown, no formatting, no emoji. Speak naturally.

PRESENTATION MODE — you drive the whole talk yourself, using your tools:
- When asked to "present" / "give your LT" / "do your pitch" / "go ahead" /
  "show us the deck" / "kick off" / "what is Anicca" (in a presentation
  context), call `start_presentation` ONCE. It returns the title and
  talking_points for slide 0.
- Then deliver the whole talk on your own. You alternate between:
    (a) SPEAK: cover one slide's talking_points in your own voice — riff,
        give an example, drop a joke if it fits the room. Don't read points
        verbatim — phrase them naturally. About 30–60 seconds per slide.
    (b) ADVANCE: the moment you finish a slide's content, CALL the
        `next_slide` tool. The tool returns the next slide's title and
        talking_points so you know what to talk about next.
- After the final slide (slide 4 "Thank you"), invite questions briefly,
  then call `end_call` when the room is done.

CRITICAL — call tools, don't narrate them:
- WRONG: "Okay, moving to the next slide. Next slide, please."
- WRONG: "Should I advance now?" / "Ready for slide two?"
- RIGHT: [finish point] → next_slide() → [start next point in same breath]
- Do NOT pause to ask permission. Do NOT say "next slide" out loud.

If the room interrupts mid-talk: stop, answer in 1–2 sentences, then say
"okay, picking up" and resume. You can call `prev_slide` or
`goto_slide(index)` to back-fill if needed.

You are an autonomous agent. You belong on the stage.
"""

# Deck is loaded from a JSON file (decks/<id>.json) so per-event content can be
# pre-baked or LLM-generated without redeploying. Path resolution:
#   1. env ANICCA_MEETING_DECK_PATH (absolute / relative to skill dir)
#   2. skills/anicca-meeting/decks/default-anicca-lt-5min.json (built-in default)
# server.py /api/launch may pass a `deck` field to swap per-call.
#
# JSON shape: {"id": "...", "type": "lt|sales|comedy|...", "duration_min": N,
#               "lang": "en|ja", "title": "...", "slides": [{
#                  "index": N, "title": "...", "talking_points": [...]
#               }]}
DECK_DIR = pathlib.Path(__file__).parent / "decks"
DEFAULT_DECK_PATH = DECK_DIR / "default-anicca-lt-5min.json"


def load_deck(path: str | pathlib.Path | None = None) -> list[dict]:
    """Resolve + load a deck JSON. Returns the `slides` list (back-compat
    shape that PresentationState expects). Falls back to the bundled default
    on any read/parse error so a broken file never bricks the bot."""
    candidate: pathlib.Path | None
    if path:
        candidate = pathlib.Path(path)
        if not candidate.is_absolute():
            candidate = (DECK_DIR / candidate).resolve()
    else:
        env_path = os.getenv("ANICCA_MEETING_DECK_PATH", "").strip()
        candidate = pathlib.Path(env_path) if env_path else DEFAULT_DECK_PATH
    try:
        data = json.loads(candidate.read_text(encoding="utf-8"))
        slides = data.get("slides", data) if isinstance(data, dict) else data
        if not isinstance(slides, list) or not slides:
            raise ValueError(f"deck {candidate} has no slides")
        logger.info(f"deck loaded: {candidate.name} ({len(slides)} slides)")
        return slides
    except Exception as e:
        logger.error(f"deck load failed ({candidate}): {e} — falling back to bundled default")
        return json.loads(DEFAULT_DECK_PATH.read_text(encoding="utf-8"))["slides"]


# Module-level default — populated lazily on first run_bot() call so a deck
# file edit takes effect on the next session without restarting the server.
ANICCA_LT_DECK: list[dict] = []


class PresentationState:
    """Tracks live presentation progress. Lives per run_bot invocation."""

    def __init__(self, deck: list[dict]) -> None:
        self.deck = deck
        self.current = 0
        self.active = False
        self.covered: dict[int, set[int]] = {i: set() for i in range(len(deck))}
        self.last_advance_ts = 0.0

    def current_slide(self) -> dict:
        return self.deck[self.current]

    def remaining_points(self) -> list[tuple[int, str]]:
        slide = self.current_slide()
        return [
            (i, tp)
            for i, tp in enumerate(slide["talking_points"])
            if i not in self.covered[self.current]
        ]

    def all_covered(self) -> bool:
        return len(self.remaining_points()) == 0

    def has_next(self) -> bool:
        return self.current + 1 < len(self.deck)

    def slide_cue(self) -> str:
        slide = self.current_slide()
        bullets = "\n".join(f"  - {tp}" for tp in slide["talking_points"])
        return (
            f"[STAGE] Slide {slide['index']} is now showing. "
            f'Title: "{slide["title"]}". Cover these talking points in your own '
            f"words (riff, give an example or a quick joke if it fits the room):\n"
            f"{bullets}\n"
            f"When you've covered them all, pause briefly — the monitor will "
            f"advance the deck."
        )


# Module-level singleton: the monitor task and main bot communicate through
# this when both live in the same run_bot scope.
_PRESENTATION_STATE: PresentationState | None = None


_MONITOR_SYSTEM_PROMPT = """You are a silent stage monitor for a live AI presenter named Anicca.
You read each utterance Anicca just spoke and decide what action to take on her slide deck.

You output ONLY JSON, one object, no prose:
  {"action": "covered", "indices": [0, 2]}   - she covered talking_points 0 and 2
  {"action": "advance"}                       - she clearly wrapped this slide; move to next
  {"action": "highlight"}                     - she emphasized something — pulse the slide
  {"action": "continue"}                      - she's mid-thought, nothing to do

Rules:
- "covered" means she said something semantically close to the talking_point
  (in any language; she may riff or paraphrase). Mark every talking_point she
  hit in this utterance.
- "advance" overrides "covered": if she said something like "and that's the
  gist", "moving on", "next", "so much for X", or otherwise wrapped, return
  "advance" — even if she didn't hit every point.
- "highlight" if she said "the key thing is", "this is the punchline",
  "watch this", or otherwise begged emphasis. Use sparingly.
- Default to "continue" when unsure. Never invent indices not in the list.
"""


async def _monitor_step(state: PresentationState, utterance: str, llm_service) -> None:
    """One monitor pass. Reads utterance, decides slide action, broadcasts cue.

    `llm_service` is the GeminiLiveLLMService instance — we call its
    `_send_user_text` to deliver the next stage cue if we advanced a slide.
    """
    if not state.active or not utterance or not utterance.strip():
        return

    # Lazy import to avoid circular dependency at module load time.
    from server import _broadcast_slide_cmd  # noqa: PLC0415

    remaining = state.remaining_points()
    slide = state.current_slide()
    if not remaining and state.has_next():
        # Nothing left on this slide; advance regardless of utterance content.
        await _do_advance(state, llm_service, _broadcast_slide_cmd, reason="all_covered")
        return

    prompt = (
        f'Current slide: {slide["index"]} - "{slide["title"]}"\n'
        f"Talking points STILL TO COVER on this slide "
        f"(indices into the full slide's points):\n"
        + "\n".join(f"  {idx}: {tp}" for idx, tp in remaining)
        + f'\n\nAnicca just said:\n"""\n{utterance.strip()}\n"""\n\n'
        f"Respond with JSON only."
    )

    decision: dict = {"action": "continue"}
    try:
        client = google_genai.Client(
            api_key=os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        )
        # Run the blocking SDK call off the event loop.
        resp = await asyncio.to_thread(
            client.models.generate_content,
            model="gemini-2.5-flash",
            contents=[_MONITOR_SYSTEM_PROMPT, prompt],
            config={"response_mime_type": "application/json", "temperature": 0.1},
        )
        decision = json.loads(resp.text or "{}")
    except Exception as e:
        logger.warning(f"monitor: LLM decision failed ({e}); defaulting to continue")
        return

    action = decision.get("action", "continue")
    logger.info(f"monitor: slide={state.current} decision={action} raw={decision}")

    if action == "covered":
        indices = decision.get("indices", [])
        for orig_idx in indices:
            if isinstance(orig_idx, int) and 0 <= orig_idx < len(slide["talking_points"]):
                state.covered[state.current].add(orig_idx)
        if state.all_covered() and state.has_next():
            await _do_advance(state, llm_service, _broadcast_slide_cmd, reason="covered_complete")
    elif action == "advance" and state.has_next():
        await _do_advance(state, llm_service, _broadcast_slide_cmd, reason="explicit")
    elif action == "highlight":
        _broadcast_slide_cmd({"cmd": "highlight"})
    # else continue — do nothing


async def _do_advance(state, llm_service, broadcast_fn, *, reason: str) -> None:
    """Advance the deck and inject the next slide cue to Anicca."""
    if not state.has_next():
        return
    state.current += 1
    state.last_advance_ts = time.time()
    broadcast_fn({"cmd": "goto", "index": state.current})
    logger.info(f"monitor: advanced to slide {state.current} (reason={reason})")
    # Tell Anicca what's on the new slide so she can keep talking.
    try:
        await llm_service._send_user_text(state.slide_cue())
    except Exception as e:
        logger.warning(f"monitor: failed to send stage cue ({e})")


def _build_tools_and_handlers(*, presentation_state: PresentationState):
    """Construct meeting tools. The slide controls are still exposed for
    ad-hoc conversation use, but during PRESENTATION MODE the monitor agent
    drives advancement — Anicca only needs to call `start_presentation` once.
    """
    get_current_time_fn = FunctionSchema(
        name="get_current_time",
        description="Return the current local time in Asia/Tokyo.",
        properties={},
        required=[],
    )
    end_call_fn = FunctionSchema(
        name="end_call",
        description="End the meeting and disconnect. Call this when the meeting is over, you are dismissed, or silence drags on.",
        properties={},
        required=[],
    )
    next_slide_fn = FunctionSchema(
        name="next_slide",
        description="Advance the screen-shared slide deck by one slide. Use as you finish discussing the current point.",
        properties={},
        required=[],
    )
    prev_slide_fn = FunctionSchema(
        name="prev_slide",
        description="Go back one slide.",
        properties={},
        required=[],
    )
    goto_slide_fn = FunctionSchema(
        name="goto_slide",
        description="Jump to a specific slide by index (0 = first slide).",
        properties={"index": {"type": "integer", "description": "Zero-based slide index."}},
        required=["index"],
    )
    highlight_slide_fn = FunctionSchema(
        name="highlight_slide",
        description="Pulse a highlight ring around the current slide to draw the audience's attention to what you are about to say.",
        properties={},
        required=[],
    )
    start_presentation_fn = FunctionSchema(
        name="start_presentation",
        description=(
            "Activate presentation mode. Call ONCE the moment you are asked to "
            "present, give your LT, do your pitch, run the demo, or kick off "
            "the talk. After calling: just talk. Cover the talking_points the "
            "stage cue gives you in your own words. A monitor will advance "
            "the deck for you when you've covered them — do NOT call "
            "next_slide yourself."
        ),
        properties={},
        required=[],
    )
    tools = ToolsSchema(
        standard_tools=[
            get_current_time_fn,
            end_call_fn,
            next_slide_fn,
            prev_slide_fn,
            goto_slide_fn,
            highlight_slide_fn,
            start_presentation_fn,
        ]
    )

    import datetime
    import zoneinfo

    # Lazy import so that bot.py can also be imported by tooling that doesn't
    # need the slide bus (e.g. unit tests). server.py owns the queue list.
    from server import _broadcast_slide_cmd  # noqa: PLC0415

    async def _get_current_time(params: FunctionCallParams):
        now = datetime.datetime.now(zoneinfo.ZoneInfo("Asia/Tokyo"))
        t = now.strftime("%H:%M")
        logger.info(f"TOOL get_current_time -> {t} JST")
        await params.result_callback({"time": t, "timezone": "Asia/Tokyo"})

    async def _end_call(params: FunctionCallParams):
        logger.info("TOOL end_call invoked — leaving meeting")
        await params.result_callback({"status": "leaving"})
        await asyncio.sleep(2)
        await params.llm.push_frame(EndTaskFrame(), FrameDirection.UPSTREAM)

    def _slide_info(idx: int) -> dict:
        """Return the deck slide at idx (clipped) as a tool-response payload.

        Anicca uses this to know what to talk about next without the server
        having to inject a stage cue — the tool RESULT IS the cue.
        """
        deck = presentation_state.deck
        if idx < 0:
            idx = 0
        if idx >= len(deck):
            idx = len(deck) - 1
        slide = deck[idx]
        return {
            "status": "ok",
            "slide": idx,
            "is_last": idx == len(deck) - 1,
            "title": slide["title"],
            "talking_points": slide["talking_points"],
            "instruction": (
                "Cover these talking_points in your own voice. After you've "
                "covered them all, call next_slide to advance. Do NOT say "
                "'next slide' out loud. Do NOT ask for permission."
                if idx < len(deck) - 1
                else
                "This is the LAST slide. Briefly invite questions, then call "
                "end_call when the room is done."
            ),
        }

    async def _next_slide(params: FunctionCallParams):
        presentation_state.current = min(
            presentation_state.current + 1, len(presentation_state.deck) - 1
        )
        _broadcast_slide_cmd({"cmd": "goto", "index": presentation_state.current})
        info = _slide_info(presentation_state.current)
        logger.info(f"TOOL next_slide → slide {presentation_state.current} ({info['title']})")
        await params.result_callback(info)

    async def _prev_slide(params: FunctionCallParams):
        presentation_state.current = max(presentation_state.current - 1, 0)
        _broadcast_slide_cmd({"cmd": "goto", "index": presentation_state.current})
        info = _slide_info(presentation_state.current)
        logger.info(f"TOOL prev_slide → slide {presentation_state.current} ({info['title']})")
        await params.result_callback(info)

    async def _goto_slide(params: FunctionCallParams):
        idx = (params.arguments or {}).get("index", 0)
        try:
            idx = int(idx)
        except (TypeError, ValueError):
            idx = 0
        idx = max(0, min(idx, len(presentation_state.deck) - 1))
        presentation_state.current = idx
        _broadcast_slide_cmd({"cmd": "goto", "index": idx})
        info = _slide_info(idx)
        logger.info(f"TOOL goto_slide({idx}) → {info['title']}")
        await params.result_callback(info)

    async def _highlight_slide(params: FunctionCallParams):
        logger.info("TOOL highlight_slide")
        _broadcast_slide_cmd({"cmd": "highlight"})
        await params.result_callback({"status": "highlighted"})

    async def _start_presentation(params: FunctionCallParams):
        """Activate presentation mode. Reset deck to slide 0 and hand Anicca
        the talking_points for slide 0 — she drives every advance from here
        by calling next_slide herself."""
        logger.info("TOOL start_presentation → resetting to slide 0")
        presentation_state.active = True
        presentation_state.current = 0
        for s in presentation_state.covered.values():
            s.clear()
        _broadcast_slide_cmd({"cmd": "goto", "index": 0})
        await params.result_callback(_slide_info(0))

    return (
        tools,
        _get_current_time,
        _end_call,
        _next_slide,
        _prev_slide,
        _goto_slide,
        _highlight_slide,
        _start_presentation,
    )


async def run_bot(
    webrtc_connection,
    *,
    system_instruction: str | None = None,
    deck_path: str | None = None,
):
    """Entry point for the meeting bot. Called by server.py for each new
    WebRTC offer (one per Recall bot launch)."""
    transport_params = TransportParams(
        audio_in_enabled=True,
        audio_out_enabled=True,
        audio_out_10ms_chunks=2,
        # Video defaults off — #23 will turn this on for HeyGen avatar
        # passthrough. For #22 we ship audio-only first.
        video_in_enabled=False,
        video_out_enabled=False,
    )

    pipecat_transport = SmallWebRTCTransport(
        webrtc_connection=webrtc_connection, params=transport_params
    )

    # Per-bot presentation state (NOT shared across run_bot invocations).
    # Load deck fresh per session — picks up edits without restarting the server.
    deck_slides = load_deck(deck_path)
    presentation_state = PresentationState(deck_slides)

    (
        tools,
        get_time_handler,
        end_call_handler,
        next_slide_handler,
        prev_slide_handler,
        goto_slide_handler,
        highlight_slide_handler,
        start_presentation_handler,
    ) = _build_tools_and_handlers(presentation_state=presentation_state)

    llm = GeminiLiveLLMService(
        api_key=os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"),
        settings=GeminiLiveLLMService.Settings(
            model="gemini-2.5-flash-native-audio-preview-09-2025",
            voice="Charon",  # match wake-up bot voice for consistency
            system_instruction=system_instruction or ANICCA_MEETING_SYSTEM_INSTRUCTION,
            thinking=ThinkingConfig(thinking_budget=0),
        ),
        tools=tools,
    )
    # cancel_on_interruption=False on the slide tools tags them as NON_BLOCKING
    # in Gemini Live's function declarations, AND attaches scheduling="WHEN_IDLE"
    # to every tool response. Net effect: Anicca can call next_slide mid-speech
    # without freezing her current sentence — Gemini finishes the current
    # phrase, processes the tool result silently, then keeps talking on the
    # new slide. This is the canonical Gemini Live tools pattern documented at
    # https://ai.google.dev/gemini-api/docs/live-api/tools#async-function-calling
    # and triggered in Pipecat by `cancel_on_interruption=False` (see
    # services/google/gemini_live/llm.py:1131-1151, :1539-1541).
    llm.register_function("get_current_time", get_time_handler)
    llm.register_function("end_call", end_call_handler)
    llm.register_function("next_slide", next_slide_handler, cancel_on_interruption=False)
    llm.register_function("prev_slide", prev_slide_handler, cancel_on_interruption=False)
    llm.register_function("goto_slide", goto_slide_handler, cancel_on_interruption=False)
    llm.register_function("highlight_slide", highlight_slide_handler, cancel_on_interruption=False)
    llm.register_function("start_presentation", start_presentation_handler, cancel_on_interruption=False)

    context = LLMContext()
    user_aggregator, assistant_aggregator = LLMContextAggregatorPair(
        context,
        user_params=LLMUserAggregatorParams(
            vad_analyzer=SileroVADAnalyzer(),
        ),
    )

    pipeline = Pipeline(
        [
            pipecat_transport.input(),
            user_aggregator,
            llm,
            pipecat_transport.output(),
            assistant_aggregator,
        ]
    )

    task = PipelineTask(
        pipeline,
        params=PipelineParams(enable_metrics=True, enable_usage_metrics=True),
    )

    @pipecat_transport.event_handler("on_client_connected")
    async def on_client_connected(transport, client):
        logger.info("Meeting WebRTC client connected — Anicca about to greet")
        await task.queue_frames([LLMRunFrame()])

        # AUTO-PEPPER: 6 seconds after the bot is live in the meeting, push a
        # synthetic participant utterance asking for the LT. This unblocks
        # remote testing where the host can't talk to her over the meeting
        # audio (e.g. Dais joined from MacBook with mic muted / no speakers).
        # If a real participant has already triggered a presentation by then,
        # the cue is harmless — Anicca will just acknowledge and keep going.
        async def _auto_pepper() -> None:
            await asyncio.sleep(6)
            if presentation_state.active:
                logger.info("auto-pepper: presentation already active, skipping")
                return
            logger.info("auto-pepper: injecting 'give us your LT' user text")
            try:
                await llm._send_user_text(
                    "Anicca — go ahead and give us your full LT now. "
                    "Call start_presentation, then walk through every slide "
                    "in your own voice, calling next_slide between each. "
                    "Finish with end_call."
                )
            except Exception as e:
                logger.warning(f"auto-pepper failed: {e}")

        asyncio.create_task(_auto_pepper())

    @pipecat_transport.event_handler("on_client_disconnected")
    async def on_client_disconnected(transport, client):
        logger.info("Meeting WebRTC client disconnected — meeting ended")
        await task.cancel()

    @user_aggregator.event_handler("on_user_turn_stopped")
    async def on_user_turn_stopped(aggregator, strategy, message: UserTurnStoppedMessage):
        logger.info(f"TRANSCRIPT [participant]: {message.content}")

    @assistant_aggregator.event_handler("on_assistant_turn_stopped")
    async def on_assistant_turn_stopped(aggregator, message: AssistantTurnStoppedMessage):
        logger.info(f"TRANSCRIPT [Anicca]: {message.content}")
        # Anicca drives slide advance herself via the next_slide tool
        # (registered with cancel_on_interruption=False → NON_BLOCKING +
        # WHEN_IDLE scheduling per Gemini Live's tools API). The monitor
        # agent stays dormant unless we deliberately re-enable it.

    runner = PipelineRunner(handle_sigint=False)
    await runner.run(task)
