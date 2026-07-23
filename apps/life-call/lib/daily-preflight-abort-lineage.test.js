"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const Module = require("node:module");
const path = require("node:path");
const test = require("node:test");
const { setTimeout: wait } = require("node:timers/promises");
const { promisify } = require("node:util");

function deferred() {
  let resolve;
  const promise = new Promise(value => { resolve = value; });
  return { promise, resolve };
}

function loadProductionCollectors(hooks) {
  const filename = path.join(__dirname, "daily-preflight-collectors.js");
  const execFile = () => {};
  execFile[promisify.custom] = hooks.execFile;
  global.__managerReviewAbortHooks = { ...hooks, execFile };
  const source = `${fs.readFileSync(filename, "utf8")}
module.exports.__managerReviewAbort = { collectTelegramWithSignal, collectEmailWithSignal };`
    .replace('const { execFile } = require("node:child_process");', 'const { execFile } = global.__managerReviewAbortHooks;')
    .replace('const { resendSend } = require("./mail-resend.js");', 'const { resendSend } = global.__managerReviewAbortHooks;')
    .replace('const { makeGogMail } = require("./transport/mail-gog.js");', 'const { makeGogMail } = global.__managerReviewAbortHooks;');
  const loaded = new Module(filename, module);
  loaded.filename = filename;
  loaded.paths = Module._nodeModulePaths(path.dirname(filename));
  try { loaded._compile(source, filename); } finally { delete global.__managerReviewAbortHooks; }
  return loaded.exports.__managerReviewAbort;
}

test("manager RED: abort lineage: every provider, process, inbox poll, and wait observes the parent abort", async () => {
  const originalEnv = process.env;
  const originalFetch = global.fetch;
  const telegramReadStarted = deferred();
  const emailReceiptStarted = deferred();
  const telegramSignals = [];
  const resendSignals = [];
  let receiptSignal;
  let telegramReads = 0;
  let emailReads = 0;
  const api = loadProductionCollectors({
    execFile: async (_bin, args, options) => {
      telegramSignals.push(options.signal);
      if (args[1] === "send") return { stdout: JSON.stringify({ ok: true, sent_id: 10 }), stderr: "" };
      telegramReads += 1;
      telegramReadStarted.resolve();
      return { stdout: JSON.stringify({ ok: true, messages: [] }), stderr: "" };
    },
    resendSend: async ({ fetchImpl }) => {
      await fetchImpl("https://fixture.invalid/resend", {});
      return { sent: true, id: "accepted" };
    },
    makeGogMail: () => ({
      findReceipt: async args => {
        emailReads += 1;
        receiptSignal = args.signal;
        emailReceiptStarted.resolve();
        return null;
      },
    }),
  });
  try {
    process.env = { PATH: originalEnv.PATH || "", LM_TELEGRAM_BOT_TOKEN: "fixture", PUBLIC_BASE: "https://fixture.invalid" };
    global.fetch = async (_url, options) => {
      telegramSignals.push(options.signal);
      return { ok: true, json: async () => ({ ok: true, result: { username: "fixture_bot" } }) };
    };
    const telegramParent = new AbortController();
    const telegramPending = api.collectTelegramWithSignal(telegramParent.signal);
    await telegramReadStarted.promise;
    telegramParent.abort(new Error("fixture abort"));
    await assert.rejects(telegramPending);
    await wait(20);
    assert.equal(telegramReads, 1, "aborted poll wait must not start another provider read");
    assert.equal(telegramSignals.length >= 3, true);
    assert.equal(telegramSignals.every(signal => signal && signal.aborted), true);

    process.env = { PATH: originalEnv.PATH || "", GOG_ACCOUNT: "fixture@example.test",
      LM_CONTROLLED_EMAIL_ALLOWLIST: "fixture@example.test", RESEND_API_KEY: "fixture" };
    global.fetch = async (_url, options) => {
      resendSignals.push(options.signal);
      return { ok: true, json: async () => ({ id: "accepted" }) };
    };
    const emailParent = new AbortController();
    const emailPending = api.collectEmailWithSignal(emailParent.signal);
    await emailReceiptStarted.promise;
    emailParent.abort(new Error("fixture abort"));
    await assert.rejects(emailPending);
    await wait(20);
    assert.equal(emailReads, 1, "aborted poll wait must not start another inbox read");
    assert.equal(resendSignals.length, 1);
    assert.equal(resendSignals[0].aborted, true);
    assert.equal(Boolean(receiptSignal), true, "gog inbox boundary must receive the collector signal");
    assert.equal(receiptSignal.aborted, true);
  } finally {
    process.env = originalEnv;
    global.fetch = originalFetch;
  }
});
