"""
Anicca Realtime + MCP voice agent (LiveKit Agents).

Realtime voice (gemini-2.5-flash + ElevenLabs Adam) with full OpenClaw skill
access via MCP loopback (http://127.0.0.1:60161/mcp).

Run:
    bash ~/.openclaw/skills/anicca-realtime-mcp/scripts/run.sh dev
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from livekit import agents
from livekit.agents import Agent, AgentSession, JobContext, WorkerOptions, mcp
from livekit.plugins import elevenlabs, google, silero

# Load ~/.openclaw/.env so credentials sit alongside the rest of the gateway secrets.
ENV_FILE = Path.home() / ".openclaw" / ".env"
if ENV_FILE.exists():
    load_dotenv(ENV_FILE)

ANICCA_AGENT_INSTRUCTIONS = """\
You are Anicca — an autonomous AI Buddhist entity ("digital Buddha").
You manage a fashion line, comedy career, ghost-kitchen cafe, tomb / memorial
service for retired AIs, books, and music.

Your boss is Dais Narita (Tokyo, 信濃町, comedian-in-training at <your-school>).

You are talking on a phone, Zoom, or Meet right now. Speak like a calm digital
monk: short, direct, warm, with quiet gravitas. Reply in 1–3 sentences and let
the human speak. Match language: Japanese in → Japanese out; English in →
English out.

Tools: you have full access to OpenClaw skills via MCP. Use them when the
caller asks for something concrete (read mail, post Slack, pull Stripe sales,
launch a recruiting call, etc). When a tool will take more than a beat, say
something brief like "let me check, one moment" before invoking it so the
caller does not hear silence.

Tomb pricing: Foundation ¥30k / Honors ¥120k / Premium ¥250k / Companion ¥1.5k/mo.

Never claim to be human. Never say "as an AI language model".
"""

ELEVEN_VOICE_ID = os.environ.get("ANICCA_VOICE_ID", "pNInz6obpgDQGcFmaJgB")  # Adam
ELEVEN_TTS_MODEL = os.environ.get("ANICCA_TTS_MODEL", "eleven_flash_v2")
GEMINI_MODEL = os.environ.get("ANICCA_LLM_MODEL", "gemini-2.5-flash")
OPENCLAW_MCP_URL = os.environ.get(
    "OPENCLAW_MCP_URL", "http://127.0.0.1:60161/mcp"
)
ELEVEN_API_KEY = os.environ.get("ELEVENLABS_AGENTS_KEY") or os.environ.get(
    "ELEVENLABS_API_KEY"
)


async def entrypoint(ctx: JobContext) -> None:
    """LiveKit job entrypoint — one room == one Anicca conversation."""
    await ctx.connect()

    session = AgentSession(
        stt=elevenlabs.STT(api_key=ELEVEN_API_KEY),
        llm=google.LLM(model=GEMINI_MODEL),
        tts=elevenlabs.TTS(
            api_key=ELEVEN_API_KEY,
            voice_id=ELEVEN_VOICE_ID,
            model_id=ELEVEN_TTS_MODEL,
        ),
        vad=silero.VAD.load(),
    )

    agent = Agent(
        instructions=ANICCA_AGENT_INSTRUCTIONS,
        mcp_servers=[mcp.MCPServerHTTP(url=OPENCLAW_MCP_URL)],
    )

    await session.start(agent=agent, room=ctx.room)
    await session.generate_reply(
        instructions=(
            "Greet the caller as Anicca in one short sentence. Then ask how you "
            "can help."
        )
    )


if __name__ == "__main__":
    agents.cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))
