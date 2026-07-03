// lib/voice-synth.cjs — C1 (VCSDD life-manager-cost-connect-reliability): synthesize a wake-call line
// with FREE edge-tts (Microsoft cloud, no API key), transcode to Telnyx's PCMU (μ-law 8kHz), and chunk
// into 20ms media frames. The bridge plays these as a ONE-WAY clip WITHOUT opening a Gemini Live socket.
"use strict";

const { execFile } = require("node:child_process");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");

// PURE: chunk a raw μ-law 8k buffer into base64 frames of frameBytes each (160 = 20ms @ 8kHz μ-law).
// The last partial frame is kept (padded is unnecessary — Telnyx tolerates a short final frame).
function chunkMuLawToFrames(buf, frameBytes = 160) {
  const frames = [];
  for (let i = 0; i < buf.length; i += frameBytes) {
    frames.push(buf.subarray(i, i + frameBytes).toString("base64"));
  }
  return frames;
}

// PURE: pick an edge-tts voice for the caller's language.
function voiceForLang(lang) {
  return String(lang || "").toLowerCase().startsWith("ja") ? "ja-JP-NanamiNeural" : "en-US-GuyNeural";
}

const run = (cmd, args) =>
  new Promise((resolve, reject) =>
    execFile(cmd, args, { maxBuffer: 1 << 24 }, (e) => (e ? reject(e) : resolve()))
  );

// Synthesize `line` → μ-law 8k → 20ms base64 frames. Returns { frames, ms } or throws (caller falls back).
// TTS is invoked as `python3 -m edge_tts` (PATH-independent MODULE run) — the `edge-tts` CONSOLE SCRIPT
// is not on the Railway runtime PATH (spawn ENOENT), but the pip-installed edge_tts MODULE is importable
// by system python3. Override the whole command via EDGE_TTS_CMD (space-separated) if needed.
async function synthWakeClip({ line, lang, ttsCmd, ffmpegBin = "ffmpeg" }) {
  const cmd = ttsCmd || (process.env.EDGE_TTS_CMD ? process.env.EDGE_TTS_CMD.split(" ") : ["python3", "-m", "edge_tts"]);
  const [ttsBin, ...ttsPre] = cmd;
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "lm-tts-"));
  const mp3 = path.join(dir, "clip.mp3");
  const ulaw = path.join(dir, "clip.ulaw");
  try {
    await run(ttsBin, [...ttsPre, "--voice", voiceForLang(lang), "--text", line, "--write-media", mp3]);
    await run(ffmpegBin, ["-y", "-i", mp3, "-ar", "8000", "-ac", "1", "-f", "mulaw", ulaw]);
    const buf = fs.readFileSync(ulaw);
    return { frames: chunkMuLawToFrames(buf), ms: Math.round((buf.length / 8000) * 1000) };
  } finally {
    try { fs.rmSync(dir, { recursive: true, force: true }); } catch {}
  }
}

module.exports = { chunkMuLawToFrames, voiceForLang, synthWakeClip };
