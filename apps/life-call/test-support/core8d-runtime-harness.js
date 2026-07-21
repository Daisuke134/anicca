"use strict";

const fs = require("node:fs");
const Module = require("node:module");
const path = require("node:path");

function loadCollectors(hooks = {}) {
  const filename = path.resolve(__dirname, "../lib/daily-preflight-collectors.js");
  let source = fs.readFileSync(filename, "utf8");
  source = source
    .replace('const { resendSend } = require("./mail-resend.js");', 'const resendSend = global.__core8dHooks.resendSend;')
    .replace('const { makeGogMail } = require("./transport/mail-gog.js");', 'const makeGogMail = global.__core8dHooks.makeGogMail;')
    .replace('crypto.randomBytes(18).toString("hex")', 'global.__core8dHooks.nonce')
    .replace('function sleepMs(ms) { return new Promise(resolve => setTimeout(resolve, ms)); }', 'function sleepMs(ms) { return global.__core8dHooks.sleep(ms); }')
    .replace('async function callTelegramBot(token, method) {', 'async function callTelegramBotOriginal(token, method) {')
    .replace('async function callPinnedSidecar(args) {', 'async function callTelegramBot(token, method) { return global.__core8dHooks.callTelegramBot(token, method); }\nasync function callPinnedSidecarOriginal(args) {')
    .replace('async function writePanelCommand(peer, command) {', 'async function callPinnedSidecar(args) { return global.__core8dHooks.callPinnedSidecar(args); }\nasync function writePanelCommand(peer, command) {')
    .replace('module.exports = { collectProductionControlledL3, validateEmailObservation, validateTelegramObservation };',
      'module.exports = { collectProductionControlledL3, collectProductionTelegram, collectProductionEmail, withinDeadline, validateEmailObservation, validateTelegramObservation };');
  global.__core8dHooks = {
    sleep: async () => {},
    callTelegramBot: async () => ({ ok: true, result: { username: "fixture_bot", url: "https://fixture.invalid/telegram", allowed_updates: ["message", "edited_message", "callback_query"], pending_update_count: 0 } }),
    callPinnedSidecar: async args => args[0] === "send" ? { ok: true, sent_id: 10 } : { ok: true, messages: [{ id: 11, date: new Date().toISOString(), out: false }] },
    resendSend: async () => ({ sent: true, id: "accepted" }),
    nonce: "fixture-nonce",
    makeGogMail: () => ({ findReceipt: async () => ({ id: "receipt", matchedNonce: hooks.nonce, receivedAtLowerMs: Date.now(), receivedAtUpperMs: Date.now() }) }),
    ...hooks,
  };
  const loaded = new Module(filename, module);
  loaded.filename = filename;
  loaded.paths = Module._nodeModulePaths(path.dirname(filename));
  loaded._compile(source, filename);
  return loaded.exports;
}

module.exports = { loadCollectors };
