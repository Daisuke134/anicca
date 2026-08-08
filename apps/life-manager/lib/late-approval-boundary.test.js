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

function assertSideEffectOrder(source) {
  const claim = source.indexOf("claim = await claimApprovedDelivery(");
  const sender = source.indexOf("provider = await sendLateNotice(");
  const receipt = source.indexOf("receipt = await recordLateDelivery(");
  const telegram = source.indexOf("approvalReceiptText(draft, providerId)");
  assert.ok(claim >= 0, "callback must claim before delivery");
  assert.ok(sender > claim, "mail transport must be after claimApprovedDelivery");
  assert.ok(receipt > sender, "provider receipt must be recorded after the provider call");
  assert.ok(telegram > receipt, "Telegram receipt must be posted after durable provider receipt");
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
