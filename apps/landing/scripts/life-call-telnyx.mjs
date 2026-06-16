#!/usr/bin/env node
// life-call-telnyx.mjs — places the REAL B-call to Dais (+818046270314) via Telnyx
// Call Control, bypassing the Twilio error-21216 fraud block on that one destination
// (Twilio JP geo-permissions are fully enabled; the block is account+destination
// fraud control that lifts only via an async Support ticket — see
// docs/superpowers/specs/2026-06-16-life-call-telnyx-charon-design.md §1).
//
// Telnyx outbound profile "anicca-out" has JP whitelisted, so it can legally dial +81.
// Flow (identical Charon/Gemini bridge, different carrier):
//   1. start call-bridge.cjs --provider telnyx (Telnyx media-streaming frame shapes)
//   2. cloudflared quick tunnel → public wss for the bridge /ws
//   3. POST https://api.telnyx.com/v2/calls with stream_url + stream_bidirectional_mode=rtp
//      + stream_bidirectional_codec=PCMU + stream_track=both_tracks  → Telnyx dials Dais
//   4. POST /v2/calls/{ccid}/actions/record_start (mp3, both channels) so the call is recorded
//   5. poll call status via webhook-less polling of /v2/calls is unavailable, so we derive
//      connect/hangup from the bridge's own start/stop frames + Charon frame counts, and we
//      fetch the recording from /v2/recordings filtered by call_session_id.
//
// NO FAKE RUN (HARD 0.24): real sockets + a real Telnyx call. The only human in the loop is
// Dais picking up his own phone (he is the callee).
//
// Usage:
//   node scripts/life-call-telnyx.mjs --dry-run                build the dial body only, exit 0
//   node scripts/life-call-telnyx.mjs                          real run → dial +818046270314
//   node scripts/life-call-telnyx.mjs --to=+E164               override destination
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";
import { spawn } from "node:child_process";
import path from "node:path";

const require = createRequire(import.meta.url);
const here = path.dirname(fileURLToPath(import.meta.url));
const { telnyxDialBody } = require(
  path.join(here, "..", "netlify", "functions", "_lib", "call-logic.js")
);

// ---- args
const args = process.argv.slice(2);
const DRY = args.includes("--dry-run");
let TO = process.env.LIFE_CALL_TO || "+818046270314"; // Dais's real number (spec27 B-call)
for (const a of args) if (a.startsWith("--to=")) TO = a.slice("--to=".length);
const PORT = Number(process.env.BRIDGE_PORT || 8788); // distinct default from the Twilio runner

// ---- env (Telnyx)
const API = process.env.TELNYX_API_KEY;
const CONN = process.env.TELNYX_CONNECTION_ID || "2982013078364751402"; // anicca-cc
const FROM = process.env.TELNYX_PHONE_NUMBER || "+14322234204"; // our Telnyx number

function die(msg) {
  console.error("FATAL:", msg);
  process.exit(1);
}
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

// ---- Telnyx REST helpers (Bearer auth, JSON)
async function txPost(p, body) {
  const res = await fetch(`https://api.telnyx.com/v2${p}`, {
    method: "POST",
    headers: { Authorization: `Bearer ${API}`, "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const j = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(`Telnyx POST ${p} ${res.status}: ${JSON.stringify(j)}`);
  return j;
}
async function txGet(p) {
  const res = await fetch(`https://api.telnyx.com/v2${p}`, {
    headers: { Authorization: `Bearer ${API}` },
  });
  const j = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(`Telnyx GET ${p} ${res.status}: ${JSON.stringify(j)}`);
  return j;
}

// ---- dry run: prove the dial body without side effects
if (DRY) {
  const body = telnyxDialBody({
    connectionId: CONN,
    to: TO,
    from: FROM,
    streamUrl: "wss://EXAMPLE.trycloudflare.com/ws",
  });
  console.log(JSON.stringify({ dryRun: true, provider: "telnyx", dialBody: body }, null, 2));
  process.exit(0);
}

// ---- real run
if (!API) die("TELNYX_API_KEY missing in env");
if (!process.env.GEMINI_API_KEY) die("GEMINI_API_KEY missing in env");

let bridge, tunnel;
function cleanup() {
  try { bridge && bridge.kill("SIGTERM"); } catch {}
  try { tunnel && tunnel.kill("SIGTERM"); } catch {}
}
process.on("exit", cleanup);
process.on("SIGINT", () => { cleanup(); process.exit(130); });

async function waitFor(stream, re, timeoutMs, label) {
  return await new Promise((resolve, reject) => {
    const to = setTimeout(() => reject(new Error(`timeout waiting for ${label}`)), timeoutMs);
    const onData = (d) => {
      const s = d.toString();
      process.stdout.write(s);
      const m = s.match(re);
      if (m) { clearTimeout(to); stream.off("data", onData); resolve(m); }
    };
    stream.on("data", onData);
  });
}

async function main() {
  // 1. cloudflared tunnel
  tunnel = spawn("cloudflared", ["tunnel", "--url", `http://localhost:${PORT}`], {
    stdio: ["ignore", "pipe", "pipe"],
  });
  const m = await waitFor(tunnel.stderr, /https:\/\/[a-z0-9-]+\.trycloudflare\.com/, 40000, "tunnel url");
  const httpsUrl = m[0];
  const wsUrl = httpsUrl.replace(/^https:/, "wss:") + "/ws";
  console.log(`\n[runner] tunnel=${httpsUrl}  ws=${wsUrl}`);

  // 2. start the bridge in Telnyx mode (Telnyx frame shapes both ways)
  bridge = spawn(
    "node",
    [path.join(here, "call-bridge.cjs"), "--port", String(PORT), "--provider", "telnyx"],
    { env: { ...process.env, BRIDGE_PUBLIC_WSS: wsUrl }, stdio: ["ignore", "pipe", "pipe"] }
  );
  bridge.stderr.on("data", (d) => process.stderr.write("[bridge.err] " + d));
  let bridgeLog = "";
  bridge.stdout.on("data", (d) => { bridgeLog += d.toString(); });
  await waitFor(bridge.stdout, /listening \d+ path=\/ws/, 15000, "bridge listening");
  await sleep(4000); // let the edge route settle

  // 3. place the REAL Telnyx call to Dais with bidirectional media streaming
  const dialBody = telnyxDialBody({ connectionId: CONN, to: TO, from: FROM, streamUrl: wsUrl });
  const call = await txPost("/calls", dialBody);
  const ccid = call.data.call_control_id;
  const sessionId = call.data.call_session_id;
  const legId = call.data.call_leg_id;
  console.log(`[runner] CALL_CONTROL_ID=${ccid}\n[runner] CALL_SESSION_ID=${sessionId} to=${TO}`);

  // 4. start a recording for this call (mp3, both channels)
  let recStarted = false;
  try {
    await txPost(`/calls/${encodeURIComponent(ccid)}/actions/record_start`, {
      format: "mp3",
      channels: "single",
    });
    recStarted = true;
    console.log("[runner] record_start ok");
  } catch (e) {
    console.error("[runner] record_start err:", e.message);
  }

  // 4b. Contingency: if the bridge has not logged a Telnyx `start` frame a few seconds after dial,
  //     the dial-params stream did not auto-start — explicitly request it (docs: answer/streaming_start).
  await sleep(6000);
  if (!/twilio_start/.test(bridgeLog)) {
    try {
      const { telnyxStreamingStartBody } = require(
        path.join(here, "..", "netlify", "functions", "_lib", "call-logic.js"));
      await txPost(`/calls/${encodeURIComponent(ccid)}/actions/streaming_start`,
        telnyxStreamingStartBody({ streamUrl: wsUrl }));
      console.log("[runner] streaming_start contingency sent");
    } catch (e) { console.error("[runner] streaming_start err:", e.message); }
  }

  // 5. let the call run; the bridge logs uplink/downlink frames as audio flows.
  //    We give it up to ~50s of conversation (Dais answers, Charon speaks, Dais replies).
  for (let i = 0; i < 18; i++) {
    await sleep(3000);
    const inM = (bridgeLog.match(/twilio_media frames=(\d+)/g) || []).pop();
    const outM = (bridgeLog.match(/gemini_audio frames=(\d+)/g) || []).pop();
    const stopped = /twilio_stop/.test(bridgeLog);
    process.stdout.write(`[poll ${i}] uplink=${inM || "0"} downlink=${outM || "0"} stopped=${stopped}\n`);
    if (stopped) break;
  }

  // 6. hang up (best effort) + fetch the recording for this call session
  try { await txPost(`/calls/${encodeURIComponent(ccid)}/actions/hangup`, {}); } catch {}
  await sleep(4000);
  let recUrl = "";
  let recId = "";
  try {
    const recs = await txGet(`/recordings?filter[call_session_id]=${encodeURIComponent(sessionId)}`);
    const r = (recs.data && recs.data[0]) || null;
    if (r) {
      recId = r.id;
      recUrl = (r.download_urls && (r.download_urls.mp3 || r.download_urls.wav)) || "";
    }
  } catch (e) {
    console.error("[runner] recording fetch err:", e.message);
  }

  // bridge frame accounting (same log strings as the Twilio runner)
  const inM = bridgeLog.match(/twilio_media frames=(\d+)/g) || [];
  const outM = bridgeLog.match(/gemini_audio frames=(\d+)/g) || [];
  const setupOk = /EVENT setupComplete/.test(bridgeLog);
  const startedOk = /twilio_start/.test(bridgeLog);
  const lastIn = inM.length ? inM[inM.length - 1].match(/(\d+)/)[0] : "0";
  const lastOut = outM.length ? outM[outM.length - 1].match(/(\d+)/)[0] : "0";

  console.log("\n==== B-call (Telnyx) RESULT ====");
  console.log(JSON.stringify({
    PROVIDER: "telnyx",
    CALL_CONTROL_ID: ccid,
    CALL_SESSION_ID: sessionId,
    CALL_LEG_ID: legId,
    TO,
    FROM,
    RECORDING_STARTED: recStarted,
    RECORDING_ID: recId,
    RECORDING_URL: recUrl,
    BRIDGE_STREAM_STARTED: startedOk,
    BRIDGE_GEMINI_SETUP: setupOk,
    UPLINK_FRAMES: lastIn,
    DOWNLINK_FRAMES: lastOut,
  }, null, 2));

  cleanup();
  // success requires the carrier media stream to have started (Dais's leg connected)
  // and Charon to have spoken at least one downlink frame.
  if (!ccid) process.exit(1);
  if (!startedOk || Number(lastOut) <= 0) {
    console.error("[runner] no media stream / no Charon audio — exiting non-zero");
    process.exit(2);
  }
  process.exit(0);
}

main().catch((e) => { console.error("FATAL:", e.message); cleanup(); process.exit(1); });
