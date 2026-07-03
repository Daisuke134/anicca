// lib/compositional-voice.cjs — C1 compositional TWO-WAY conversation orchestrator
// (VCSDD life-manager-cost-connect-reliability). Free stack: STT (Groq Whisper) + LLM (Groq Llama, stream)
// + TTS (edge-tts). Replaces Gemini Live native-audio. NEVER opens a Gemini Live ws (Goal-1: live_ws_opened=0).
// stt/llm/tts/send/sendClear are INJECTED (Groq HTTP + edge-tts subprocess in prod, fakes in tests).
"use strict";

const { energyVAD, sentenceSplitter, buildLlmChat, decideBargeIn, buildWakeLine } = require("./voice-turn.cjs");
// buildWakeLine now lives in voice-turn.cjs (voice-cheap.js deleted per spec FIND-101)

// createConversation({ event, urgency, lang, groqKey, stt, llm, tts, send, sendClear, vadOpts, system })
// - stt(pcm16Buf, groqKey) -> transcript string
// - llm(chatBody, groqKey, onToken) -> streams tokens via onToken(token)
// - tts(sentence, lang) -> audio buffer (μ-law frames handled by caller's send)
// - send(audio) -> play audio to the caller (Telnyx media out)
// - sendClear() -> Telnyx {"event":"clear"} (barge-in)
function createConversation(opts) {
  const { event, urgency = "firm", lang = "ja", groqKey, stt, llm, tts, send, sendClear, vadOpts, system } = opts;
  const vad = energyVAD(vadOpts);
  let botSpeaking = false;
  let callerSpeaking = false;
  let utterance = []; // buffered caller PCM frames
  let liveWsOpened = 0; // INVARIANT: never incremented — Gemini Live is not on this path
  const sys = system || `You are Life Manager, a concise phone assistant. Answer the caller's question about their upcoming event in one or two short sentences, in ${lang === "ja" ? "Japanese" : "English"}.`;

  // Speak a fixed line (opening) — TTS the whole line, send it.
  async function speak(text) {
    if (!text) return;
    botSpeaking = true;
    const audio = await tts(text, lang);
    if (audio) await send(audio);
    botSpeaking = false;
  }

  // The agent opens the call with the wake guidance, then converses.
  async function start() {
    const line = buildWakeLine({ title: event && event.summary, place: event && event.location }, {}, urgency, lang);
    await speak(line);
  }

  // Stream an LLM response to the caller's text: LLM tokens → sentences → TTS+send per sentence (low TTFB).
  async function respond(userText) {
    botSpeaking = true;
    const splitter = sentenceSplitter();
    const body = buildLlmChat({ system: sys, history: [{ role: "user", content: userText }] });
    await llm(body, groqKey, async (token) => {
      for (const sentence of splitter.push(token)) {
        const audio = await tts(sentence, lang);
        if (audio) await send(audio);
      }
    });
    for (const sentence of splitter.flush()) {
      const audio = await tts(sentence, lang);
      if (audio) await send(audio);
    }
    botSpeaking = false;
  }

  // Feed one caller PCM16 frame. VAD decides speech/endpoint. Barge-in stops the bot + clears Telnyx.
  async function pushCallerFrame(frame) {
    const v = vad.push(frame);
    if (v.speech) {
      if (botSpeaking) {
        const d = decideBargeIn({ botSpeaking: true, callerSpeechStart: !callerSpeaking });
        if (d.sendClear) await sendClear();
        botSpeaking = false; // stop our outbound send loop
      }
      callerSpeaking = true;
      utterance.push(frame);
    } else if (v.endpointed && utterance.length) {
      callerSpeaking = false;
      const audio = Buffer.concat(utterance);
      utterance = [];
      const text = await stt(audio, groqKey);
      if (text && String(text).trim()) await respond(String(text).trim());
    }
  }

  return {
    start,
    pushCallerFrame,
    get liveWsOpened() { return liveWsOpened; },
    get botSpeaking() { return botSpeaking; },
  };
}

module.exports = { createConversation };
