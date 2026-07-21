"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");

const collectorSource = fs.readFileSync(path.join(__dirname, "daily-preflight-collectors.js"), "utf8");

function section(start, end) {
  const from = collectorSource.indexOf(start);
  const to = collectorSource.indexOf(end, from + start.length);
  assert.notEqual(from, -1); assert.notEqual(to, -1);
  return collectorSource.slice(from, to);
}

function assertOneShotBudget() {
  assert.match(collectorSource, /writePanelCommand\(peer, `\/panel core8d_\$\{nonce\}`\)/);
  assert.match(collectorSource, /resendSend\(\{[\s\S]*?subject:[\s\S]*?\}\)/);
  assert.doesNotMatch(collectorSource, /(?:dial|phoneCall|createCall)\s*\(/i);
}

const cases = [
  ["poll: Telegram reply attempt 6 is the final allowed attempt", /for \(let index = 0; index < 6; index \+= 1\)/],
  ["poll: Telegram reply attempt 7 is forbidden", /index < 7/ , true],
  ["poll: Telegram webhook attempt 3 is the final allowed attempt", /for \(let index = 0; index < 3; index \+= 1\)/],
  ["poll: Telegram webhook attempt 4 is forbidden", /index < 4/, true],
  ["poll: email inbox attempt 6 is the final allowed attempt", /for \(let index = 0; index < 6; index \+= 1\)/],
  ["poll: email inbox attempt 7 is forbidden", /index < 7/, true],
  ["timeout: Telegram Bot API calls are bounded at 15000 ms", /15000/, false, section("async function callTelegramBot", "async function callPinnedSidecar")],
  ["timeout: Resend calls are bounded at 15000 ms", /15000/, false, section("async function collectProductionEmail", "async function collectProductionControlledL3")],
  ["timeout: gog inbox calls are bounded at 15000 ms", /findReceipt\([^)]*15000/, false, section("async function collectProductionEmail", "async function collectProductionControlledL3")],
  ["deadline: Telegram collector is bounded at 179000 ms", /TELEGRAM_COLLECTOR_DEADLINE_MS\s*=\s*179000/],
  ["deadline: email collector is bounded at 120000 ms", /EMAIL_COLLECTOR_DEADLINE_MS\s*=\s*120000/],
  ["deadline: parallel controlled collection is bounded at 179000 ms", /CONTROLLED_COLLECTION_DEADLINE_MS\s*=\s*179000/],
];

for (const [name, pattern, forbidden = false, target = collectorSource] of cases) {
  test(name, () => {
    assertOneShotBudget();
    if (forbidden) assert.doesNotMatch(target, pattern);
    else assert.match(target, pattern);
  });
}
