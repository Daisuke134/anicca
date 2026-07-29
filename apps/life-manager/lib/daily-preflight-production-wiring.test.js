"use strict";

const assert = require("node:assert/strict");
const childProcess = require("node:child_process");
const test = require("node:test");

const originalExecFile = childProcess.execFile;
const originalFetch = global.fetch;
const originalEnv = { ...process.env };
const execCalls = [];
const fetchCalls = [];
let resendCalls = 0;
let receiptCalls = 0;

childProcess.execFile = (file, args, options, callback) => {
  execCalls.push({ file, args, options });
  const value = args[1] === "send"
    ? { ok: true, sent_id: 41 }
    : { ok: true, messages: [{ id: 42, date: new Date().toISOString(), out: false, text: "discard me" }] };
  callback(null, { stdout: JSON.stringify(value), stderr: "" });
};

global.fetch = async url => {
  fetchCalls.push(String(url));
  const result = String(url).endsWith("/getMe")
    ? { username: "LifeBot" }
    : { url: "https://life.example/telegram", allowed_updates: ["message", "edited_message", "callback_query"], pending_update_count: 0 };
  return { ok: true, json: async () => ({ ok: true, result }) };
};

const resend = require("./mail-resend.js");
resend.resendSend = async () => { resendCalls += 1; return { sent: true, id: "provider-id" }; };
const gog = require("./transport/mail-gog.js");
gog.makeGogMail = () => ({
  findReceipt: async ({ nonce, afterMs }) => {
    receiptCalls += 1;
    return { id: "gmail-id", matchedNonce: nonce, receivedAtLowerMs: afterMs, receivedAtUpperMs: afterMs };
  },
});

process.env = {
  ...originalEnv,
  LM_TELEGRAM_BOT_TOKEN: "fixture-token",
  ANICCA_PROXY_BASE_URL: "https://life.example",
  GOG_ACCOUNT: "controlled@aniccaai.com",
  LM_CONTROLLED_EMAIL_ALLOWLIST: "controlled@aniccaai.com",
  RESEND_API_KEY: "fixture-key",
};

const { collectProductionControlledL3 } = require("./daily-preflight-collectors.js");

test.after(() => {
  childProcess.execFile = originalExecFile;
  global.fetch = originalFetch;
  process.env = originalEnv;
});

test("closed production wiring uses only preinstalled fakes and sends each transport once", async () => {
  const result = await collectProductionControlledL3();

  assert.equal(resendCalls, 1);
  assert.equal(receiptCalls, 1);
  assert.equal(fetchCalls.filter(url => url.endsWith("/getMe")).length, 1);
  assert.equal(fetchCalls.filter(url => url.endsWith("/getWebhookInfo")).length, 1);
  assert.equal(execCalls.filter(call => call.args[1] === "send").length, 1);
  assert.equal(execCalls.filter(call => call.args[1] === "read").length, 1);
  assert.equal(execCalls.every(call => call.file === "/home/life-manager/.cache/telegram-user-venv/bin/python"), true);
  assert.equal(execCalls.every(call => call.args[0] === require("node:path").resolve(__dirname, "../../../skills/tools/telegram-user/tg_user.py")), true);
  assert.match(execCalls.find(call => call.args[1] === "send").args[3], /^\/panel core8d_[a-f0-9]{24}$/);
  assert.doesNotMatch(JSON.stringify(result), /discard me|fixture-token|fixture-key/);
});
