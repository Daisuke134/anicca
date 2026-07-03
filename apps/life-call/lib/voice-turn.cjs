// lib/voice-turn.cjs — C1 compositional voice: pure turn-logic (VCSDD life-manager-cost-connect-reliability).
// The free two-way loop = μ-law in → VAD endpointing → Groq Whisper STT → Groq Llama LLM (stream) →
// edge-tts → μ-law out, with barge-in. This file holds the PURE, testable pieces; the live STT/LLM HTTP
// calls + the Telnyx socket wiring live in server.js. NO Gemini Live is opened anywhere here (Goal-1).
"use strict";

// Split a streaming token feed into sentences as terminators (. ? ! 。 ！ ？) arrive, so each finished
// sentence can be sent to TTS immediately (low time-to-first-audio). push() returns any completed
// sentences; flush() returns the trailing remainder.
function sentenceSplitter() {
  let buf = "";
  const TERM = /[.?!。！？]/;
  return {
    push(chunk) {
      buf += chunk;
      const out = [];
      let m;
      // Flush every complete sentence (up to and including its terminator).
      while ((m = buf.match(TERM))) {
        const end = m.index + 1;
        out.push(buf.slice(0, end).trim());
        buf = buf.slice(end);
      }
      return out;
    },
    flush() {
      const r = buf.trim();
      buf = "";
      return r ? [r] : [];
    },
  };
}

// Energy-based VAD + silence endpointing (interim in lieu of a node-native Smart Turn model).
// push(pcm16Frame) → { speech, endpointed }. RMS over threshold = speech; a silence run ≥ silenceMs
// after speech = end-of-turn (endpointed once).
function energyVAD({ threshold = 200, silenceMs = 500, frameMs = 20 } = {}) {
  const needed = Math.ceil(silenceMs / frameMs);
  let silentFrames = 0;
  let sawSpeech = false;
  let endpointedFired = false;
  return {
    push(pcm16Frame) {
      let sum = 0;
      const n = Math.floor(pcm16Frame.length / 2);
      for (let i = 0; i < n; i++) {
        const s = pcm16Frame.readInt16LE(i * 2);
        sum += s * s;
      }
      const rms = n ? Math.sqrt(sum / n) : 0;
      const speech = rms >= threshold;
      let endpointed = false;
      if (speech) {
        sawSpeech = true;
        silentFrames = 0;
        endpointedFired = false;
      } else if (sawSpeech) {
        silentFrames++;
        if (silentFrames >= needed && !endpointedFired) {
          endpointed = true;
          endpointedFired = true;
        }
      }
      return { speech, endpointed };
    },
  };
}

// Barge-in: if the bot is speaking and the caller starts talking, stop our outbound send + tell Telnyx
// to clear its playback ({"event":"clear"} — verified in building-voice-agents.md). NEVER opens Live.
function decideBargeIn({ botSpeaking, callerSpeechStart }) {
  const barge = Boolean(botSpeaking && callerSpeechStart);
  return { stopSend: barge, sendClear: barge, openLive: false };
}

// Fail-closed provider selection. Groq is primary; on no-key / 429 / timeout, fall back to a local/cheap
// provider — NEVER Gemini Live native-audio.
function chooseSttProvider({ groqKey, lastError } = {}) {
  const groqOk = Boolean(groqKey) && lastError !== 429 && lastError !== "timeout";
  return { name: groqOk ? "groq-whisper" : "faster-whisper-local" };
}
function chooseLlmProvider({ groqKey, lastError } = {}) {
  const groqOk = Boolean(groqKey) && lastError !== 429 && lastError !== "timeout";
  return { name: groqOk ? "groq-llama" : "gemini-flash-text" };
}

// OpenAI-compatible chat body for Groq's LLM (streamed).
function buildLlmChat({ system, history = [], model = "llama-3.1-8b-instant" }) {
  const messages = [];
  if (system) messages.push({ role: "system", content: system });
  for (const m of history) messages.push(m);
  return { model, stream: true, messages, temperature: 0.4 };
}

module.exports = {
  sentenceSplitter,
  energyVAD,
  decideBargeIn,
  chooseSttProvider,
  chooseLlmProvider,
  buildLlmChat,
};
