#!/usr/bin/env node
"use strict";

const { execFileSync } = require("node:child_process");
const { selectManagedAccount } = require("../lib/personalized-action");
const { detectCalendarCare } = require("../lib/care-detector-runtime");

function jsonCommand(file, args) {
  return JSON.parse(execFileSync(file, args, {
    encoding: "utf8",
    maxBuffer: 4 * 1024 * 1024,
    stdio: ["ignore", "pipe", "pipe"],
  }));
}

function main() {
  const auth = jsonCommand("gog", ["auth", "list", "--json"]);
  const account = selectManagedAccount({}, auth.accounts);
  if (!account) throw new Error("managed_calendar_account_unavailable");
  const raw = jsonCommand("gog", [
    "calendar", "events",
    "--account", account,
    "--from", "2015-01-01",
    "--to", "today",
    "--query", "クリニック",
    "--max", "250",
    "--json",
    "--results-only",
    "--fields", "items(id,start,end)",
  ]);
  const events = Array.isArray(raw) ? raw : raw.items || [];
  const receipt = detectCalendarCare({
    nowMs: Date.now(),
    intents: [],
    sources: [{ careType: "clinic", events }],
  });
  process.stdout.write(`${JSON.stringify(receipt)}\n`);
  if (receipt.candidates.length !== 1) process.exitCode = 1;
}

try {
  main();
} catch (error) {
  process.stderr.write(`care-detection-e2e: ${error.message}\n`);
  process.exitCode = 1;
}
