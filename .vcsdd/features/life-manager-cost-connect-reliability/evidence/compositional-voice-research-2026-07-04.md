# Compositional voice stack research (2026-07-04) — replace Gemini Live native-audio

Recommended FREE compositional two-way conversational stack (Pipecat cascaded pattern, run in the existing Node bridge):
- STT: Groq Whisper Large-v3-Turbo — free tier 20 RPM/2K RPD, ~$0.04/hr, 228× realtime, JA+EN (groq.com/pricing, console.groq.com/docs/rate-limits).
- LLM: Groq Llama-3.1-8B-Instant — free tier 30 RPM/14.4K RPD, 840 TPS (groq.com/pricing).
- TTS: edge-tts (python3 -m edge_tts), $0 (already working).
- VAD/turn: Silero VAD (node port @ricky0123/vad-node) or energy+silence heuristic (500-800ms).
- Orchestration: EXTEND apps/life-call/lib/call-bridge.cjs (Node) — NOT Pipecat (Python, two runtimes). Reuse call-logic.js μ-law/PCM16/resample primitives.
Data flow: μ-law 8k in → PCM 8k→16k → VAD → Groq STT → Groq LLM (stream sentences) → edge-tts → ffmpeg 24k→8k+μ-law → Telnyx out. Barge-in: on speech-start stop TTS + Telnyx clear.
Cost: Gemini Live native-audio ~$0.10-0.30+/min (audio in $3/M, out $12/M tok, ~25 tok/s) vs compositional ~$0.001/min or $0 in free tier = ~150-400× cheaper.
Risks: latency stacking (mitigate: stream LLM→TTS sentence-wise + Groq speed); no node-native Smart Turn (energy VAD interim); Telnyx barge-in clear analog to confirm at impl; Groq free-tier RPM under concurrent load (fall back to paid, still >100× cheaper); 8k→16k upsample before STT.
Source agent: firecrawl docs.pipecat.ai + groq.com/pricing + console.groq.com + Telnyx media-streaming docs.
