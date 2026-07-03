// lib/voice-cheap.js — C1 (VCSDD life-manager-cost-connect-reliability): the cheap wake-call path.
// DEFAULT = a pre-synthesized ONE-WAY guidance clip (cheap text line → edge-tts → μ-law → Telnyx play),
// which opens NO Gemini Live websocket → zero native-audio tokens (Goal 1 invariant, measurable).
// A two-way Gemini Live session is opened ONLY when the caller interacts (speaks / presses a key).
// Pure logic; the actual edge-tts synth + Telnyx send live in the bridge.
"use strict";

// Fallback order for producing the clip. edge-tts (free MS cloud) first; local Kokoro/piper if the MS
// endpoint is down; Gemini Live only as the last resort (billed). A silent call is worse than none.
const TTS_ORDER = ["edge-tts", "kokoro", "piper", "live"];

function chooseTts(available) {
  for (const t of TTS_ORDER) if (available && available[t]) return t;
  return null; // nothing available → caller MUST NOT dial (no silent call)
}

// Decide the call mode from live interaction signals. Default = one-way (no Live ws).
function planVoice({ callerSpoke = false, keypad = null } = {}) {
  const interacted = Boolean(callerSpoke) || keypad != null;
  return interacted
    ? { mode: "live_escalation", opensLiveWs: true }
    : { mode: "oneway", opensLiveWs: false };
}

// Build the one-line spoken guidance. Names event + place + route + urgency, in the caller's language.
function buildWakeLine(event, route, urgency = "firm", lang = "ja") {
  const title = (event && event.title) || "";
  const place = (event && event.place) || "";
  const line = (route && route.line) || "";
  const dur = route && route.durationMin != null ? route.durationMin : null;
  if (lang === "ja") {
    const push = urgency === "harsh" ? "今すぐ出てください。" : "そろそろ出発しましょう。";
    const via = line ? `${line}で` : "";
    const mins = dur != null ? `${dur}分ほどです。` : "";
    return `${title}へ、${place}まで${via}${mins}${push}`.replace(/\s+/g, " ").trim();
  }
  const push = urgency === "harsh" ? "Leave right now." : "Time to head out.";
  const via = line ? `via ${line}` : "";
  const mins = dur != null ? `about ${dur} min.` : "";
  return `${title} at ${place}, ${via} ${mins} ${push}`.replace(/\s+/g, " ").trim();
}

module.exports = { TTS_ORDER, chooseTts, planVoice, buildWakeLine };
