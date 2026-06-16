#!/usr/bin/env node
// ~/anicca/skills/life/ask/ask.js
// B-ask skill entrypoint — spec27 WF-B B-ask.
//
// Local Anicca body implementation (Mac-mini). The mail SEND happens HERE via
// the `gog` CLI (gog lives on the Mac-mini and CANNOT run inside a Netlify
// lambda). The GCal read + patch happen in the Netlify function
// (apps/landing/netlify/functions/life-ask.js).
//
// Flow for `--action question`:
//   1. POST Netlify ?action=question  → GCal-read-only; returns { toAsk: [...] }
//   2. for each event to ask: `gog gmail send` the question email to Dais
//   3. POST Netlify ?action=mark-asked → set the pending flag on the event
//
// Flow for `--action reply` (manual test path):
//   forward the supplied --body straight to Netlify ?action=reply.
//
// Canonical trigger: ~/.openclaw/cron/jobs.json "anicca-life-ask" (daily 06:00 JST)
// Also callable manually:
//   node ask.js --action question
//   node ask.js --action reply --body '<json>'
//
// Env (read from ~/.openclaw/.env if present):
//   NETLIFY_SITE_URL     — target site (default: https://aniccaai.com)
//   GOG_ACCOUNT          — Google account for gog (default: GOOGLE_LOGIN_EMAIL)
//   GOG_KEYRING_PASSWORD — gog keyring password (required for gog send)
//   DAIS_EMAIL           — question recipient (default: keiodaisuke@gmail.com)
//   LIFE_ASK_ACTION      — action override (default: question)
//
// Pattern mirrors ~/anicca/skills/life/notify/notify.js (proven gog gmail send).

"use strict";

const path = require("path");
const fs = require("fs");
const { execFileSync } = require("node:child_process");

// ── Env loading ──────────────────────────────────────────────────────────────

function loadEnv() {
  const envPath = path.join(process.env.HOME || "/root", ".openclaw", ".env");
  const raw = fs.existsSync(envPath) ? fs.readFileSync(envPath, "utf8") : "";
  const out = {};
  for (const line of raw.split("\n")) {
    const m = line.match(/^([A-Z_][A-Z0-9_]*)=(.*)$/);
    if (m) out[m[1]] = m[2].replace(/^["']|["']$/g, "");
  }
  return out;
}

const ENV = loadEnv();

const SITE_URL = process.env.NETLIFY_SITE_URL || ENV.NETLIFY_SITE_URL || "https://aniccaai.com";
const GOG_BIN = "/opt/homebrew/bin/gog";
const GOG_ACCOUNT =
  process.env.GOG_ACCOUNT ||
  ENV.GOG_ACCOUNT ||
  process.env.GOOGLE_LOGIN_EMAIL ||
  ENV.GOOGLE_LOGIN_EMAIL ||
  "keiodaisuke@gmail.com";
const DAIS_EMAIL = process.env.DAIS_EMAIL || ENV.DAIS_EMAIL || "keiodaisuke@gmail.com";

// ── gog gmail send (mirrors notify.js gogGmailSend) ────────────────────────────

// gog exec env: inherit + inject keyring password (proven pattern, notify.js:245).
function gogEnv() {
  return {
    ...process.env,
    GOG_KEYRING_PASSWORD: process.env.GOG_KEYRING_PASSWORD || ENV.GOG_KEYRING_PASSWORD || "",
    GOG_ACCOUNT,
  };
}

// Send one question email via gog. Returns Gmail message id when available.
function gogSend({ to, subject, body }) {
  const out = execFileSync(
    GOG_BIN,
    ["gmail", "send", "--account", GOG_ACCOUNT, "--to", to, "--subject", subject, "--body", body, "--json"],
    { env: gogEnv(), encoding: "utf8", timeout: 30000 }
  );
  try {
    const j = JSON.parse(out);
    return j.id || j.messageId || "";
  } catch {
    return "";
  }
}

// ── Netlify POST helper ────────────────────────────────────────────────────────

async function postNetlify(action, body) {
  const url = `${SITE_URL}/.netlify/functions/life-ask?action=${encodeURIComponent(action)}`;
  const r = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: body || "{}",
  });
  const text = await r.text();
  let j;
  try {
    j = JSON.parse(text);
  } catch {
    j = { raw: text };
  }
  if (!r.ok || j?.ok === false) {
    throw new Error(`netlify ${action} ${r.status}: ${text.slice(0, 200)}`);
  }
  return j;
}

// CLI arg parsing
const args = process.argv.slice(2);
let action = process.env.LIFE_ASK_ACTION || ENV.LIFE_ASK_ACTION || "question";
let bodyOverride = null;

for (let i = 0; i < args.length; i++) {
  if (args[i] === "--action" && args[i + 1]) {
    action = args[++i];
  } else if (args[i] === "--body" && args[i + 1]) {
    bodyOverride = args[++i];
  }
}

// ── Main ─────────────────────────────────────────────────────────────────────

async function main() {
  if (action === "reply") {
    // Manual reply test path: forward body straight to Netlify reply handler.
    const res = await postNetlify("reply", bodyOverride || "{}");
    console.log(JSON.stringify(res, null, 2));
    return;
  }

  // action=question: GCal-read on Netlify, send locally via gog, then mark-asked.
  const { toAsk = [], checked = 0 } = await postNetlify("question", "{}");
  const asked = [];
  for (const a of toAsk) {
    let messageId = "";
    try {
      messageId = gogSend({ to: DAIS_EMAIL, subject: a.subject, body: a.body });
    } catch (err) {
      asked.push({ eventId: a.eventId, error: `gog_send: ${err.message}` });
      continue;
    }
    try {
      await postNetlify("mark-asked", JSON.stringify({ eventId: a.eventId, messageId }));
    } catch (err) {
      asked.push({ eventId: a.eventId, messageId, markError: err.message });
      continue;
    }
    asked.push({ eventId: a.eventId, eventTitle: a.eventTitle, messageId });
  }
  console.log(JSON.stringify({ ok: true, checked, asked }, null, 2));
  if (asked.some((x) => x.error)) process.exit(1);
}

if (require.main === module) {
  main().catch((err) => {
    console.error("[ask] fatal:", err.message);
    process.exit(1);
  });
}

module.exports = { main, gogSend, postNetlify };
