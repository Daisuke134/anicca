#!/usr/bin/env node
// ~/anicca/skills/life/ask/ask.js
// B-ask skill entrypoint — spec27 WF-B B-ask.
//
// Wrapper that calls the live Netlify function for B-ask:
//   POST https://aniccaai.com/.netlify/functions/life-ask?action=question
//
// The Netlify function (apps/landing/netlify/functions/life-ask.js) is the
// canonical implementation. This script is the OSS skill stub that:
//   1. Reads NETLIFY_SITE_URL (default: https://aniccaai.com) from env
//   2. POSTs to /.netlify/functions/life-ask?action=<action>
//   3. Prints the JSON response and exits 0 on ok:true, 1 on error
//
// Canonical trigger: ~/.openclaw/cron/jobs.json "anicca-life-ask" (daily 06:00 JST)
// Also callable manually: node ask.js [--action question|reply] [--body <json>]
//
// Env (read from ~/.openclaw/.env if present):
//   NETLIFY_SITE_URL   — target site (default: https://aniccaai.com)
//   LIFE_ASK_ACTION    — action override (default: question)

"use strict";

const path = require("path");
const fs = require("fs");

// ── Env loading ──────────────────────────────────────────────────────────────

function loadEnv() {
  const envPath = path.join(process.env.HOME, ".openclaw", ".env");
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
  const url = `${SITE_URL}/.netlify/functions/life-ask?action=${encodeURIComponent(action)}`;
  const body = bodyOverride || "{}";

  console.log(`[ask] POST ${url}`);

  const r = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body,
  });

  const text = await r.text();
  let result;
  try {
    result = JSON.parse(text);
  } catch {
    result = { raw: text };
  }

  console.log(`[ask] status=${r.status}`);
  console.log(JSON.stringify(result, null, 2));

  if (!r.ok || result?.ok === false) {
    process.exit(1);
  }
}

if (require.main === module) {
  main().catch((err) => {
    console.error("[ask] fatal:", err.message);
    process.exit(1);
  });
}

module.exports = { main };
