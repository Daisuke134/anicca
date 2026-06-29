// lib/dial.js — place a Telnyx Call Control call whose media streams to OUR bridge (/ws), so the
// answered call is bridged to Gemini Live (Charon). Reuses the proven body builders in call-logic.js
// (same ones runner-telnyx.mjs uses locally). No cloudflared: streamUrl is this service's stable
// Railway public wss. Returns { ok, ccid } | { ok:false, error }.
"use strict";

const { telnyxDialBody, telnyxStreamingStartBody } = require("./call-logic.js");

const TELNYX = "https://api.telnyx.com/v2";

function authHeaders() {
  return { Authorization: `Bearer ${process.env.TELNYX_API_KEY}`, "Content-Type": "application/json" };
}

async function txPost(path, body) {
  const r = await fetch(`${TELNYX}${path}`, { method: "POST", headers: authHeaders(), body: JSON.stringify(body) });
  const j = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(`telnyx ${path} ${r.status}: ${JSON.stringify(j).slice(0, 200)}`);
  return j;
}

async function balanceUsd() {
  const r = await fetch(`${TELNYX}/balance`, { headers: authHeaders() });
  const j = await r.json().catch(() => ({}));
  return Number(j && j.data && j.data.balance);
}

// to: E.164 callee. streamUrl: wss://<this-svc>/ws?summary=...&dateTime=...&location=...&urgency=...
// Returns the call_control_id so the caller can issue record_start / streaming_start.
async function placeCall({ to, streamUrl }) {
  const API = process.env.TELNYX_API_KEY;
  const CONN = process.env.TELNYX_CONNECTION_ID;
  const FROM = process.env.TELNYX_PHONE_NUMBER;
  if (!API || !CONN || !FROM) return { ok: false, error: "telnyx env missing (API/CONN/FROM)" };
  if (!to || !streamUrl) return { ok: false, error: "to/streamUrl required" };

  // Preflight: never dial on an empty balance (a mid-call cutoff is a fake "connected").
  const usd = await balanceUsd().catch(() => NaN);
  if (!Number.isFinite(usd) || usd < 0.5) return { ok: false, error: `telnyx balance too low ($${usd})` };

  const dialBody = telnyxDialBody({ connectionId: CONN, to, from: FROM, streamUrl });
  let call;
  try {
    call = await txPost("/calls", dialBody);
  } catch (e) {
    return { ok: false, error: String(e.message || e) };
  }
  const ccid = call && call.data && call.data.call_control_id;
  if (!ccid) return { ok: false, error: "no call_control_id" };

  // NOTE: do NOT record_start here — the call is still RINGING (not answered), so Telnyx rejects
  // record_start ("call is not in a valid state"). Recording is started by the bridge the moment the
  // media `start` frame arrives (= call answered). See startRecording() + the server.js start handler.
  return { ok: true, ccid };
}

// Start mp3 recording on an ANSWERED call. Telnyx record_start requires the call to be active
// (media streaming) — fire this from the bridge's Telnyx `start` frame, NOT right after dial.
// Returns { ok:true } or { ok:false, error } so the caller can LOG it (never silently swallowed).
async function startRecording(ccid) {
  if (!ccid) return { ok: false, error: "no ccid" };
  try {
    await txPost(`/calls/${encodeURIComponent(ccid)}/actions/record_start`, { format: "mp3", channels: "single" });
    return { ok: true };
  } catch (e) {
    return { ok: false, error: String(e.message || e) };
  }
}

module.exports = { placeCall, startRecording, telnyxStreamingStartBody, balanceUsd };
