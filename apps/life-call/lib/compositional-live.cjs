// lib/compositional-live.cjs — C1 LIVE adapters for the compositional voice loop: Groq Whisper STT,
// Groq Llama streaming LLM, edge-tts→μ-law frames. Injected into createConversation in server.js.
// Pure helpers (pcm16ToWav, parseGroqSSE) are unit-tested; the network fns are exercised in the real-call E2E.
"use strict";

const { synthWakeClip } = require("./voice-synth.cjs");

// PURE: wrap raw PCM16-LE mono into a minimal WAV container (Groq's file endpoint wants a real audio file).
function pcm16ToWav(pcm, sampleRate = 16000) {
  const numCh = 1, bps = 16;
  const byteRate = (sampleRate * numCh * bps) / 8;
  const blockAlign = (numCh * bps) / 8;
  const h = Buffer.alloc(44);
  h.write("RIFF", 0); h.writeUInt32LE(36 + pcm.length, 4); h.write("WAVE", 8);
  h.write("fmt ", 12); h.writeUInt32LE(16, 16); h.writeUInt16LE(1, 20); h.writeUInt16LE(numCh, 22);
  h.writeUInt32LE(sampleRate, 24); h.writeUInt32LE(byteRate, 28); h.writeUInt16LE(blockAlign, 32);
  h.writeUInt16LE(bps, 34); h.write("data", 36); h.writeUInt32LE(pcm.length, 40);
  return Buffer.concat([h, pcm]);
}

// PURE: parse one chunk of Groq's SSE stream → array of content-delta strings (ignores [DONE]/keepalive).
function parseGroqSSE(chunkText) {
  const out = [];
  for (const line of String(chunkText).split("\n")) {
    const s = line.trim();
    if (!s.startsWith("data:")) continue;
    const payload = s.slice(5).trim();
    if (payload === "[DONE]" || !payload) continue;
    try {
      const j = JSON.parse(payload);
      const delta = j.choices && j.choices[0] && j.choices[0].delta && j.choices[0].delta.content;
      if (delta) out.push(delta);
    } catch { /* partial line — caller buffers across chunks */ }
  }
  return out;
}

// LIVE: Groq Whisper STT. pcm16 (16kHz mono) → transcript. Fails → throws (caller fail-closes to local).
async function groqStt(pcm16Buf, groqKey, { model = "whisper-large-v3-turbo", fetchImpl = fetch } = {}) {
  const wav = pcm16ToWav(pcm16Buf, 16000);
  const form = new FormData();
  form.append("model", model);
  form.append("file", new Blob([wav], { type: "audio/wav" }), "audio.wav");
  const r = await fetchImpl("https://api.groq.com/openai/v1/audio/transcriptions", {
    method: "POST", headers: { Authorization: `Bearer ${groqKey}` }, body: form,
  });
  if (!r.ok) { const e = new Error(`groq stt ${r.status}`); e.status = r.status; throw e; }
  const j = await r.json();
  return (j.text || "").trim();
}

// LIVE: Groq Llama streaming chat. Calls onToken(text) as content arrives. Fails → throws.
async function groqLlmStream(chatBody, groqKey, onToken, { fetchImpl = fetch } = {}) {
  const r = await fetchImpl("https://api.groq.com/openai/v1/chat/completions", {
    method: "POST",
    headers: { Authorization: `Bearer ${groqKey}`, "Content-Type": "application/json" },
    body: JSON.stringify({ ...chatBody, stream: true }),
  });
  if (!r.ok) { const e = new Error(`groq llm ${r.status}`); e.status = r.status; throw e; }
  const reader = r.body.getReader();
  const dec = new TextDecoder();
  let buf = "";
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    buf += dec.decode(value, { stream: true });
    // process complete lines; keep the trailing partial in buf
    const nl = buf.lastIndexOf("\n");
    if (nl >= 0) {
      const ready = buf.slice(0, nl);
      buf = buf.slice(nl + 1);
      for (const t of parseGroqSSE(ready)) await onToken(t);
    }
  }
  for (const t of parseGroqSSE(buf)) await onToken(t);
}

// LIVE TTS: a sentence → μ-law 8k base64 frames (edge-tts via python3 -m edge_tts + ffmpeg). Returns [frames].
async function ttsToMuLawFrames(sentence, lang) {
  const { frames } = await synthWakeClip({ line: sentence, lang });
  return frames;
}

module.exports = { pcm16ToWav, parseGroqSSE, groqStt, groqLlmStream, ttsToMuLawFrames };
