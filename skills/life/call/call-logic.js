// call-logic.js — pure audio/transcode + wire-shape logic for B-call (spec27 WF-B).
//
// This is the skill-repo mirror of
// apps/landing/netlify/functions/_lib/call-logic.js (anicca-products), which carries
// the TDD test suite (14 node:test cases). Kept byte-identical so the bridge in
// call.js can require it locally without a cross-repo dependency.
//
// Standards: G.711 μ-law (8-bit companded), Gemini Live realtimeInput/setup/speechConfig
// (input PCM 16kHz, output PCM 24kHz, voice Charon), Twilio Media Streams media frame
// (audio/x-mulaw @ 8000Hz, base64).

"use strict";

const MULAW_BIAS = 0x84;
const MULAW_CLIP = 32635;

function muLawDecodeSample(u) {
  u = ~u & 0xff;
  const sign = u & 0x80;
  const exponent = (u >> 4) & 0x07;
  const mantissa = u & 0x0f;
  let sample = ((mantissa << 3) + MULAW_BIAS) << exponent;
  sample -= MULAW_BIAS;
  return (sign ? -sample : sample) || 0;
}

function muLawEncodeSample(pcm) {
  let sign = (pcm >> 8) & 0x80;
  if (sign !== 0) pcm = -pcm;
  if (pcm > MULAW_CLIP) pcm = MULAW_CLIP;
  pcm += MULAW_BIAS;
  let exponent = 7;
  for (let mask = 0x4000; (pcm & mask) === 0 && exponent > 0; mask >>= 1) exponent--;
  const mantissa = (pcm >> (exponent + 3)) & 0x0f;
  return ~(sign | (exponent << 4) | mantissa) & 0xff;
}

function muLawBufToPcm16(buf) {
  const out = Buffer.alloc(buf.length * 2);
  for (let i = 0; i < buf.length; i++) out.writeInt16LE(muLawDecodeSample(buf[i]), i * 2);
  return out;
}

function pcm16BufToMuLaw(buf) {
  const samples = Math.floor(buf.length / 2);
  const out = Buffer.alloc(samples);
  for (let i = 0; i < samples; i++) out[i] = muLawEncodeSample(buf.readInt16LE(i * 2));
  return out;
}

function resamplePcm16(buf, inRate, outRate) {
  if (inRate === outRate) return Buffer.from(buf);
  const inSamples = Math.floor(buf.length / 2);
  if (inSamples === 0) return Buffer.alloc(0);
  const ratio = outRate / inRate;
  const outSamples = Math.round(inSamples * ratio);
  const out = Buffer.alloc(outSamples * 2);
  for (let i = 0; i < outSamples; i++) {
    const srcPos = i / ratio;
    const i0 = Math.floor(srcPos);
    const i1 = Math.min(i0 + 1, inSamples - 1);
    const frac = srcPos - i0;
    const s0 = buf.readInt16LE(i0 * 2);
    const s1 = buf.readInt16LE(i1 * 2);
    let v = Math.round(s0 + (s1 - s0) * frac);
    if (v > 32767) v = 32767;
    if (v < -32768) v = -32768;
    out.writeInt16LE(v, i * 2);
  }
  return out;
}

function twilioMuLawToGeminiPcm16(b64MuLaw) {
  const mu = Buffer.from(b64MuLaw, "base64");
  return resamplePcm16(muLawBufToPcm16(mu), 8000, 16000).toString("base64");
}

function geminiPcm24ToTwilioMuLaw(b64Pcm24) {
  const pcm24 = Buffer.from(b64Pcm24, "base64");
  return pcm16BufToMuLaw(resamplePcm16(pcm24, 24000, 8000)).toString("base64");
}

function buildGeminiSetup({ model, voiceName, systemInstruction }) {
  const modelPath = String(model || "").startsWith("models/") ? model : `models/${model}`;
  return {
    setup: {
      model: modelPath,
      generationConfig: {
        responseModalities: ["AUDIO"],
        speechConfig: {
          voiceConfig: { prebuiltVoiceConfig: { voiceName: voiceName || "Charon" } },
        },
      },
      systemInstruction: { parts: [{ text: systemInstruction || "" }] },
    },
  };
}

function buildGeminiAudioInput(b64Pcm16) {
  return { realtimeInput: { audio: { data: b64Pcm16, mimeType: "audio/pcm;rate=16000" } } };
}

function buildTwilioMediaFrame(streamSid, b64MuLaw) {
  return { event: "media", streamSid, media: { payload: b64MuLaw } };
}

function formatTime(dateTime) {
  if (!dateTime || typeof dateTime !== "string") return "";
  const m = dateTime.match(/T(\d{2}:\d{2})/);
  return m ? m[1] : "";
}

function buildCallPrompt(event) {
  const e = event || {};
  const title = (e.summary || "your next appointment").toString().trim() || "your next appointment";
  const time = formatTime(e.start && e.start.dateTime);
  const location = (e.location || "").toString().trim();
  return [
    "You are Anicca, a calm, concise voice assistant calling the user on the phone.",
    "Speak naturally and warmly. Keep it short. This is a two-way call — answer follow-ups.",
    `The user's next event is "${title}"${time ? ` at ${time}` : ""}.`,
    location ? `It is at ${location}.` : "",
    "Tell them it's time to leave now so they arrive on time, then ask if they need directions or anything else.",
    `Open with: "Hi, it's Anicca. Your next event is ${title}${time ? ` at ${time}` : ""} — time to leave now."`,
  ]
    .filter(Boolean)
    .join(" ");
}

function xmlEscape(s) {
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&apos;");
}

function buildConnectStreamTwiml(wsUrl) {
  return (
    '<?xml version="1.0" encoding="UTF-8"?>' +
    "<Response><Connect>" +
    `<Stream url="${xmlEscape(wsUrl)}" />` +
    "</Connect></Response>"
  );
}

module.exports = {
  muLawDecodeSample,
  muLawEncodeSample,
  muLawBufToPcm16,
  pcm16BufToMuLaw,
  resamplePcm16,
  twilioMuLawToGeminiPcm16,
  geminiPcm24ToTwilioMuLaw,
  buildGeminiSetup,
  buildGeminiAudioInput,
  buildTwilioMediaFrame,
  buildCallPrompt,
  buildConnectStreamTwiml,
  xmlEscape,
  formatTime,
};
