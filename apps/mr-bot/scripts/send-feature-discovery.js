#!/usr/bin/env node
// One-user LM-32 E2E hook. It uses the production gates and weekly throttle.
"use strict";

const { runDiscoveryForUid } = require("../lib/feature-discovery.js");

async function main() {
  const uid = process.argv[2];
  if (!uid) throw new Error("usage: node scripts/send-feature-discovery.js <uid>");
  const result = await runDiscoveryForUid(uid, Date.now(), {
    token: process.env.LM_TELEGRAM_BOT_TOKEN,
    supaUrl: process.env.SUPABASE_URL,
    supaKey: process.env.SUPABASE_SERVICE_ROLE_KEY,
  });
  process.stdout.write(`${JSON.stringify(result)}\n`);
  if (!result.sent) process.exitCode = 2;
}

main().catch((error) => {
  console.error(error && error.message ? error.message : String(error));
  process.exitCode = 1;
});
