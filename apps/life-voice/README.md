# life-voice — Life Manager compositional two-way voice (Pipecat)

Replaces Gemini Live native-audio with a FREE cascaded conversation: Silero VAD + Smart Turn v3 (turn-taking,
JA-confirmed) → Groq Whisper STT → Groq Llama LLM → Kokoro TTS, over Telnyx Media Streaming (Pipecat
TelnyxFrameSerializer). NO Gemini Live is opened (live_ws_opened=0).

- The Node service (apps/life-call) schedules + dials; `scheduler.js buildStreamUrl` points Telnyx's
  `stream_url` at this service's WSS (env PIPECAT_WSS). The signed ctx + HMAC sig on the /ws query is
  verified here (OQ9) with the SAME LM_CALL_SECRET before the pipeline starts.
- Kokoro model files (kokoro-v1.0.onnx + voices-v1.0.bin) must be present (OQ8 benchmark-before-ship:
  measure CPU latency vs the ~800ms/turn budget; fall back to Piper if it misses).
- Run: `python server.py`. Deploy: own Railway service.
