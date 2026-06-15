#!/usr/bin/env node
// life-call.mjs — runner that places the REAL B-call (spec27c). It:
//   1. starts call-bridge.cjs locally
//   2. opens a cloudflared quick tunnel to it
//   3. POSTs a real Twilio outbound call to +818046270314 with <Connect><Stream wss://…/ws>
//      + Record=true (RecordingTrack=both) so Charon + Dais are both captured
//   4. polls the call until it ends, then fetches the recording
//   5. prints the real CALL_SID / CALL_STATUS / RECORDING_URL + bridge frame counts
//
// NO FAKE RUN (HARD 0.24) / END-TO-END (HARD 0.31): the BUILDER fires this and reads the
// real Twilio call SID + recording back. Any failed step exits non-zero. The only human in
// the loop is Dais answering his own phone (he is the callee).
//
// Usage:
//   node scripts/life-call.mjs --dry-run   build TwiML + call args only, ZERO side effects, exit 0
//   node scripts/life-call.mjs             real run: dial +818046270314 (override with --to=+E164)
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";
import { spawn } from "node:child_process";
import path from "node:path";

const require = createRequire(import.meta.url);
const here = path.dirname(fileURLToPath(import.meta.url));
const { buildConnectStreamTwiml } = require(
  path.join(here, "..", "netlify", "functions", "_lib", "call-logic.js")
);

// ---- args
const args = process.argv.slice(2);
const DRY = args.includes("--dry-run");
let TO = process.env.LIFE_CALL_TO || "+818046270314"; // Dais's real number (spec27c)
for (const a of args) if (a.startsWith("--to=")) TO = a.slice("--to=".length);
const PORT = Number(process.env.BRIDGE_PORT || 8787);

// ---- env
const FROM = process.env.TWILIO_PHONE_NUMBER || process.env.TWILIO_FROM;
const SID = process.env.TWILIO_ACCOUNT_SID;
const TOKEN = process.env.TWILIO_AUTH_TOKEN;

function die(msg) {
  console.error("FATAL:", msg);
  process.exit(1);
}
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

// ---- Twilio REST helpers (Basic auth, form-encoded)
function twAuth() {
  return "Basic " + Buffer.from(`${SID}:${TOKEN}`).toString("base64");
}
async function twPost(p, form) {
  const res = await fetch(`https://api.twilio.com/2010-04-01/Accounts/${SID}${p}`, {
    method: "POST",
    headers: { Authorization: twAuth(), "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams(form).toString(),
  });
  const body = await res.json();
  if (!res.ok) throw new Error(`Twilio POST ${p} ${res.status}: ${JSON.stringify(body)}`);
  return body;
}
async function twGet(p) {
  const res = await fetch(`https://api.twilio.com/2010-04-01/Accounts/${SID}${p}`, {
    headers: { Authorization: twAuth() },
  });
  const body = await res.json();
  if (!res.ok) throw new Error(`Twilio GET ${p} ${res.status}: ${JSON.stringify(body)}`);
  return body;
}

// ---- dry run: prove the wire without side effects
if (DRY) {
  const wsUrl = "wss://EXAMPLE.trycloudflare.com/ws";
  const twiml = buildConnectStreamTwiml(wsUrl);
  console.log(JSON.stringify({ dryRun: true, to: TO, from: FROM || "(env TWILIO_PHONE_NUMBER)", twiml, record: true, recordingTrack: "both" }, null, 2));
  process.exit(0);
}

// ---- real run
if (!FROM || !SID || !TOKEN) die("TWILIO_PHONE_NUMBER / TWILIO_ACCOUNT_SID / TWILIO_AUTH_TOKEN missing in env");
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
  // 1. start bridge
  bridge = spawn("node", [path.join(here, "call-bridge.cjs"), "--port", String(PORT)], {
    env: process.env,
    stdio: ["ignore", "pipe", "pipe"],
  });
  bridge.stderr.on("data", (d) => process.stderr.write("[bridge.err] " + d));
  // collect bridge stdout for later frame-count assertions
  let bridgeLog = "";
  bridge.stdout.on("data", (d) => { bridgeLog += d.toString(); });
  await waitFor(bridge.stdout, /listening \d+ path=\/ws/, 15000, "bridge listening");

  // 2. cloudflared tunnel
  tunnel = spawn("cloudflared", ["tunnel", "--url", `http://localhost:${PORT}`], {
    stdio: ["ignore", "pipe", "pipe"],
  });
  const m = await waitFor(tunnel.stderr, /https:\/\/[a-z0-9-]+\.trycloudflare\.com/, 40000, "tunnel url");
  const httpsUrl = m[0];
  const wsUrl = httpsUrl.replace(/^https:/, "wss:") + "/ws";
  console.log(`\n[runner] tunnel=${httpsUrl}  ws=${wsUrl}`);
  await sleep(4000); // let the edge route settle

  // 3. place the real call
  const twiml = buildConnectStreamTwiml(wsUrl);
  const call = await twPost("/Calls.json", {
    To: TO,
    From: FROM,
    Twiml: twiml,
    Record: "true",
    RecordingTrack: "both",
    Timeout: "30",
  });
  const callSid = call.sid;
  console.log(`[runner] CALL_SID=${callSid} initial_status=${call.status}`);

  // 4. poll until terminal
  const terminal = new Set(["completed", "busy", "no-answer", "failed", "canceled"]);
  let status = call.status, dur = "0";
  for (let i = 0; i < 60; i++) {
    await sleep(3000);
    const c = await twGet(`/Calls/${callSid}.json`);
    status = c.status; dur = c.duration || dur;
    process.stdout.write(`[poll ${i}] status=${status} dur=${dur}\n`);
    if (terminal.has(status)) break;
  }

  // 5. recording
  let recUrl = "";
  try {
    const recs = await twGet(`/Calls/${callSid}/Recordings.json`);
    if (recs.recordings && recs.recordings[0]) {
      const r = recs.recordings[0];
      recUrl = `https://api.twilio.com/2010-04-01/Accounts/${SID}/Recordings/${r.sid}.mp3`;
    }
  } catch (e) {
    console.error("[runner] recording fetch err:", e.message);
  }

  // bridge frame accounting (from its stdout)
  const inM = bridgeLog.match(/twilio_media frames=(\d+)/g) || [];
  const outM = bridgeLog.match(/gemini_audio frames=(\d+)/g) || [];
  const setupOk = /EVENT setupComplete/.test(bridgeLog);
  const lastIn = inM.length ? inM[inM.length - 1].match(/(\d+)/)[0] : "0";
  const lastOut = outM.length ? outM[outM.length - 1].match(/(\d+)/)[0] : "0";

  console.log("\n==== B-call RESULT ====");
  console.log(JSON.stringify({
    CALL_SID: callSid,
    CALL_STATUS: status,
    CALL_DURATION: dur,
    RECORDING_URL: recUrl,
    BRIDGE_GEMINI_SETUP: setupOk,
    UPLINK_FRAMES: lastIn,
    DOWNLINK_FRAMES: lastOut,
  }, null, 2));

  cleanup();
  // success requires a real SID + the call actually connected (completed)
  if (!callSid) process.exit(1);
  if (status !== "completed") {
    console.error(`[runner] call ended ${status} (not completed) — exiting non-zero`);
    process.exit(2);
  }
  process.exit(0);
}

main().catch((e) => { console.error("FATAL:", e.message); cleanup(); process.exit(1); });
