"use strict";

// DAILY #5 Task 5: this contract is deliberately source-shaped.  A future refactor must not make
// the scheduler/tick an alternate mail entry point, and a callback-owned sender must remain after a
// durable claim and before the provider receipt/Telegram acknowledgement.
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const ROOT = path.join(__dirname, "..");
const lateNoticeSource = fs.readFileSync(path.join(__dirname, "late-notice.js"), "utf8");
const schedulerSource = fs.readFileSync(path.join(ROOT, "scheduler.js"), "utf8");
const approvalSource = fs.readFileSync(path.join(__dirname, "late-approval.js"), "utf8");
const serverSource = fs.readFileSync(path.join(ROOT, "server.js"), "utf8");
const telegramSource = fs.readFileSync(path.join(__dirname, "telegram.js"), "utf8");

const ALLOWED_MAIL_SURFACE = new Set([
  "lib/late-approval.js",
  "lib/notify.js",
  "lib/mail-resend.js",
]);
const MAIL_SURFACE_PATTERNS = [
  /require\(\s*["'][^"']*notify\.js["']\s*\)/,
  /\bsendLateNotice\b/,
];

function assertAllowedMailSurface(sources) {
  for (const [file, source] of sources.entries()) {
    const normalized = file.split(path.sep).join("/");
    if (MAIL_SURFACE_PATTERNS.some((pattern) => pattern.test(source)) && !ALLOWED_MAIL_SURFACE.has(normalized)) {
      throw new Error(`${normalized} mail transport reference is not allowlisted`);
    }
  }
}

function collectProductionJs(dir, files = []) {
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    if (["node_modules", "test-support", "eval"].includes(entry.name)) continue;
    const absolute = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      collectProductionJs(absolute, files);
    } else if (entry.isFile() && entry.name.endsWith(".js") && !entry.name.endsWith(".test.js")) {
      files.push(absolute);
    }
  }
  return files;
}

function authenticatedCallbackSource(source) {
  const start = source.indexOf("async function handleLateApprovalCallback");
  const end = source.indexOf("\nmodule.exports", start);
  assert.ok(start >= 0 && end > start, "late approval callback must have a bounded production body");
  return source.slice(start, end);
}

test("negative fixture: an unallowlisted production mail caller must fail the surface scan", () => {
  assert.throws(
    () => assertAllowedMailSurface(new Map([
      ["lib/unauthorized-mail.js", 'const { sendLateNotice } = require("./notify.js");'],
    ])),
    /not allowlisted/,
  );
});

test("production JS mail surface is explicit and the only caller is the authenticated late callback", () => {
  const sources = new Map(collectProductionJs(ROOT).map((file) => [path.relative(ROOT, file), fs.readFileSync(file, "utf8")]));
  assert.doesNotThrow(() => assertAllowedMailSurface(sources));
  assert.deepEqual(
    [...sources.entries()]
      .filter(([, source]) => MAIL_SURFACE_PATTERNS.some((pattern) => pattern.test(source)))
      .map(([file]) => file)
      .sort(),
    ["lib/late-approval.js", "lib/mail-resend.js", "lib/notify.js"],
  );
  assert.match(serverSource, /LM_TG_SECRET\.length > 0/);
  assert.match(serverSource, /crypto\.timingSafeEqual/);
  assert.match(serverSource, /path === "\/telegram"/);
  assert.match(serverSource, /late: async \(data\).*handleLateApprovalCallback/s);
  assert.match(authenticatedCallbackSource(approvalSource), /sendLateNotice/);
  assertSideEffectOrder(approvalSource);
});

function assertSideEffectOrder(source) {
  const callback = source.includes("async function handleLateApprovalCallback")
    ? authenticatedCallbackSource(source)
    : source;
  const claim = callback.indexOf("claim = await claimApprovedDelivery(");
  const sender = callback.indexOf("provider = await sendLateNotice(");
  const receipt = callback.indexOf("receipt = await recordLateDelivery(");
  const telegram = callback.indexOf("approvalReceiptText(draft, providerId)");
  assert.ok(claim >= 0, "callback must claim before delivery");
  assert.ok(sender > claim, "mail transport must be after claimApprovedDelivery");
  assert.ok(receipt > sender, "provider receipt must be recorded after the provider call");
  assert.ok(telegram > receipt, "Telegram receipt must be posted after durable provider receipt");
  assert.doesNotMatch(source.slice(0, source.indexOf("async function handleLateApprovalCallback")), /sendLateNotice\s*\(/,
    "mail transport must not be callable outside the authenticated callback");
}

test("the tick has no mail transport and only enqueues the approval card", () => {
  assert.doesNotMatch(lateNoticeSource, /require\(["']\.\/notify\.js["']\)/);
  assert.doesNotMatch(lateNoticeSource, /sendLateNotice\s*\(/);
  assert.doesNotMatch(schedulerSource, /require\(["']\.\/lib\/notify\.js["']\)/);
  assert.doesNotMatch(schedulerSource, /sendLateNotice\s*:/);
});

test("the only mail transport call is callback-owned and follows the durable claim", () => {
  assertSideEffectOrder(approvalSource);
  assert.match(telegramSource, /prefix === "late"/);
  assert.match(serverSource, /handleLateApprovalCallback\(data/);
  assert.match(serverSource, /owner:\s*row/);
});

test("mutation probe fails if the sender is moved before claim", () => {
  const claimToken = "claim = await claimApprovedDelivery(";
  const senderToken = "provider = await sendLateNotice(";
  const claimIndex = approvalSource.indexOf(claimToken);
  const senderIndex = approvalSource.indexOf(senderToken);
  assert.ok(claimIndex >= 0 && senderIndex > claimIndex);
  const mutated = approvalSource
    .slice(0, claimIndex)
    + approvalSource.slice(senderIndex, senderIndex + senderToken.length)
    + approvalSource.slice(claimIndex, senderIndex)
    + approvalSource.slice(senderIndex + senderToken.length);
  assert.throws(() => assertSideEffectOrder(mutated), /after claimApprovedDelivery/);
});
