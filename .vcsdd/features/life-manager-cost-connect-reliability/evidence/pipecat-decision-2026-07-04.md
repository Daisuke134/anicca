# Voice architecture DECISION: adopt Pipecat (2026-07-04, 2 research passes)

Two independent deep-research subagents converged: the make-or-break for a REAL back-and-forth phone
conversation (not walkie-talkie) is TURN-TAKING/BARGE-IN, and the FREE answer = Silero VAD + Smart Turn v3,
which Pipecat bundles. Hand-rolling it in Node (energyVAD + genId) FAILED the impl adversary (FIND-201).

## Decision (per HARD #-3 = follow the researched BP, originality=bug)
- ADOPT Pipecat (BSD, github.com/pipecat-ai/pipecat, 13.2k★): native TelnyxFrameSerializer, Silero VAD +
  Smart Turn v3 (local, $0), first-party Groq STT/LLM + Kokoro TTS adapters. Copy pipecat-ai/pipecat-examples/
  telnyx-chatbot/inbound/bot.py.
- TTS: edge-tts → Kokoro (pipecat-ai[kokoro], self-hosted, $0, TRUE streaming, Japanese confirmed).
- STT/LLM: keep Groq Whisper Large-v3-Turbo + Groq Llama-3.1-8B-Instant (cheapest+fastest, JA).
- Cost ≈ $0.01–0.02/min all-in (vs Vapi/Retell $0.05–0.16; vs Gemini Live corrected ~$0.023/min). No idle cost.

## Key corrections from research
- Gemini Live is actually ~$0.023/min (audio in $3/M + out $12/M tok), NOT $0.10–0.30 — but cascaded is
  still 10–15× cheaper + zero idle + avoids the unrestricted-key risk.
- Groq has NO realtime/duplex product — cascaded STT+LLM is the correct Groq usage.
- Self-hosted open duplex (Moshi) = ~$280/mo idle GPU + no JA + no Telnyx bridge → NOT viable for a phone agent.
- Turn-taking: Silero VAD (<1ms/30ms chunk) + Smart Turn v3 (bundled ONNX) = the free conversation-quality piece.
- Streaming STT (Soniox ~$0.12/hr / Deepgram Nova-3 $0.35/hr / Deepgram Flux w/ native turn-detect $0.0065-0.0078/min,
  JA) = optional paid upgrades, one-line swaps in Pipecat.

## SUPERSEDES
The hand-rolled Node cascade (compositional-voice/compositional-live/voice-turn/voice-synth.cjs + server.js
/ws wiring) is REPLACED by the Pipecat pipeline. It FAILED impl adversary (FIND-201 barge-in never stops
playback; FIND-202 fallbacks unwired) — exactly the reasons to use Pipecat's proven implementation.

Sources: docs.pipecat.ai, github.com/pipecat-ai/{pipecat,smart-turn,pipecat-examples}, groq.com/pricing,
console.groq.com/docs, github.com/remsky/Kokoro-FastAPI, ai.google.dev/gemini-api/docs/pricing, developers.telnyx.com.
