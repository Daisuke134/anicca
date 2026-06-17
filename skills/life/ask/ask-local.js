#!/usr/bin/env node
// ~/anicca/skills/life/ask/ask-local.js — the LOCAL ask consumer (self-contained, no aniccaai.com).
// Closes the loop: travel writes life-ask-queue.jsonl → this mails the question via gog Gmail →
// polls Gmail for the reply → writes the location back to the gcal event → clears travel state so
// the move block gets inserted next travel run. Send-channel == read-channel (both Gmail).
//   node ask-local.js --action question   # mail the queued questions
//   node ask-local.js --action poll        # ingest replies → register location
"use strict";
const fs = require("node:fs");
const path = require("node:path");
const os = require("node:os");
const { execFileSync } = require("node:child_process");

const HOME = process.env.HOME || os.homedir();
function loadEnv() {
  const p = path.join(HOME, ".openclaw", ".env");
  const out = {};
  let raw = ""; try { raw = fs.readFileSync(p, "utf8"); } catch { return out; }
  for (const line of raw.split("\n")) {
    const m = line.match(/^([A-Z_][A-Z0-9_]*)=(.*)$/);
    if (m) out[m[1]] = m[2].replace(/^["']|["']$/g, "");
  }
  return out;
}
const ENV = loadEnv();
const GOG_BIN = "/opt/homebrew/bin/gog";
const GOG_ACCOUNT = process.env.GOG_ACCOUNT || ENV.GOG_ACCOUNT || "redacted@example.invalid";
const DAIS_EMAIL = process.env.DAIS_EMAIL || ENV.DAIS_EMAIL || "redacted@example.invalid";
const QUEUE = process.env.LIFE_ASK_QUEUE || path.join(HOME, ".openclaw", "state", "life-ask-queue.jsonl");
const TRAVEL_STATE = path.join(HOME, ".openclaw", "skills", "anicca-travel-fill", "state", "travel_filled.json");
function gogEnv() {
  return { ...process.env, GOG_KEYRING_PASSWORD: process.env.GOG_KEYRING_PASSWORD || ENV.GOG_KEYRING_PASSWORD || "", GOG_ACCOUNT };
}

// ── pure (unit-tested) ─────────────────────────────────────────────────────────
function loadQueue(p) {
  p = p || QUEUE;
  let raw = ""; try { raw = fs.readFileSync(p, "utf8"); } catch { return []; }
  const byId = new Map();
  for (const line of raw.split("\n")) {
    const t = line.trim(); if (!t) continue;
    let r; try { r = JSON.parse(t); } catch { continue; } // tolerate corrupt/half lines
    if (!r.eventId) continue;
    byId.set(r.eventId, r); // latest record wins
  }
  return [...byId.values()];
}
function buildQuestionEmail(row) {
  const s = (row.summary || "予定").trim();
  const why = row.reason === "no_route" ? "の移動経路が分かりませんでした" : "の場所が分かりませんでした";
  const subject = `[Anicca] 場所を教えてください: ${s} [ASK-${row.eventId}]`;
  const body =
    `「${s}」${why}。\nこの予定はどこで行われますか？ 駅名や住所をこのメールに返信してください。\n\nEvent ID: ${row.eventId}`;
  return { subject, body };
}
function parseReply(subject, body) {
  const m = /\[ASK-([^\]]+)\]/.exec(subject || "");
  if (!m) return null;
  let location = "";
  for (const line of (body || "").split("\n")) {
    const t = line.trim();
    if (!t || t.startsWith(">") || /^On .*wrote:/.test(t) || /^Event ID:/.test(t)) continue;
    location = t; break;
  }
  return { eventId: m[1], location };
}

// ── side-effecting (E2E) ───────────────────────────────────────────────────────
function gogSend({ to, subject, body }) {
  const out = execFileSync(GOG_BIN, ["gmail", "send", "--account", GOG_ACCOUNT, "--to", to, "--subject", subject, "--body", body, "--json"],
    { env: gogEnv(), encoding: "utf8", timeout: 30000 });
  try { const j = JSON.parse(out); return j.id || j.messageId || ""; } catch { return ""; }
}
function gogSearchReplyThreads() {
  try {
    const out = execFileSync(GOG_BIN, ["gmail", "search", `from:${DAIS_EMAIL} subject:"[ASK-" newer_than:7d`, "-j", "--account", GOG_ACCOUNT],
      { env: gogEnv(), encoding: "utf8", timeout: 30000 });
    const d = JSON.parse(out);
    return (d.threads || d.messages || d || []).map((t) => ({ id: t.id, subject: t.subject || "" }));
  } catch { return []; }
}
function gogGetBody(id) {
  try {
    const out = execFileSync(GOG_BIN, ["gmail", "get", id, "-j", "--account", GOG_ACCOUNT], { env: gogEnv(), encoding: "utf8", timeout: 30000 });
    const d = JSON.parse(out); return { subject: d.subject || "", body: d.body || d.snippet || "" };
  } catch { return { subject: "", body: "" }; }
}
function setEventLocation(eventId, location) {
  execFileSync(GOG_BIN, ["calendar", "update", eventId, "--location", location, "-j", "--account", GOG_ACCOUNT],
    { env: gogEnv(), encoding: "utf8", timeout: 30000 });
}
function clearTravelState(eventId) {
  let s; try { s = JSON.parse(fs.readFileSync(TRAVEL_STATE, "utf8")); } catch { return; }
  let changed = false;
  for (const k of Object.keys(s)) {
    if (k.includes(eventId) && s[k] === "asked") { delete s[k]; changed = true; } // re-process now that we know the place
  }
  if (changed) fs.writeFileSync(TRAVEL_STATE, JSON.stringify(s, null, 2));
}
function writeQueue(rows) {
  fs.mkdirSync(path.dirname(QUEUE), { recursive: true });
  fs.writeFileSync(QUEUE, rows.map((r) => JSON.stringify(r)).join("\n") + (rows.length ? "\n" : ""));
}

function runQuestions({ dryRun = false } = {}) {
  const rows = loadQueue();
  let sent = 0;
  for (const r of rows) {
    if (r.asked) continue;
    const { subject, body } = buildQuestionEmail(r);
    if (dryRun) { console.log("[ask] would mail:", subject); continue; }
    const id = gogSend({ to: DAIS_EMAIL, subject, body });
    r.asked = true; r.messageId = id; sent++;
  }
  if (!dryRun) writeQueue(rows);
  console.log(JSON.stringify({ action: "question", queued: rows.length, sent }));
  return sent;
}
function runPoll({ dryRun = false } = {}) {
  const threads = gogSearchReplyThreads();
  const rows = loadQueue();
  const queuedIds = new Set(rows.map((r) => r.eventId));
  let registered = 0;
  for (const th of threads) {
    const { subject, body } = gogGetBody(th.id);
    const r = parseReply(subject || th.subject, body);
    if (!r || !r.location || !queuedIds.has(r.eventId)) continue;
    if (dryRun) { console.log("[ask] would register:", r.eventId, "→", r.location); continue; }
    setEventLocation(r.eventId, r.location);
    clearTravelState(r.eventId);
    registered++;
  }
  if (!dryRun && registered) {
    const done = new Set();
    for (const th of threads) { const { subject, body } = gogGetBody(th.id); const r = parseReply(subject || th.subject, body); if (r && r.location) done.add(r.eventId); }
    writeQueue(rows.filter((r) => !done.has(r.eventId))); // drop resolved
  }
  console.log(JSON.stringify({ action: "poll", threads: threads.length, registered }));
  return registered;
}

module.exports = { loadQueue, buildQuestionEmail, parseReply, runQuestions, runPoll };

if (require.main === module) {
  const args = process.argv.slice(2);
  const action = args.includes("--action") ? args[args.indexOf("--action") + 1] : "question";
  const dryRun = args.includes("--dry-run");
  try { (action === "poll" ? runPoll : runQuestions)({ dryRun }); }
  catch (e) { console.error("[ask-local] fatal:", e.message); process.exit(1); }
}
