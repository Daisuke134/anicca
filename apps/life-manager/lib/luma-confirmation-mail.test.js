"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const test = require("node:test");

const {
  createLumaConfirmationMailStore,
  lumaConfirmationMessageFromGog,
  verifyLumaConfirmationMessage,
} = require("./luma-confirmation-mail.js");

const JOB_ID = `outbound-event:${"9".repeat(64)}`;

function fixture(overrides = {}) {
  return {
    tenantId: "dais-local",
    jobId: JOB_ID,
    eventUrl: "https://luma.com/a879ax7k",
    eventTitle: "Engineer BAR",
    registrationStartedAt: "2026-08-01T14:38:32.325Z",
    registrationCompletedAt: "2026-08-01T14:38:40.076Z",
    message: {
      id: "19fbdc3478265ec8",
      internalDate: "2026-08-01T14:38:44.000Z",
      from: "mii <event-owner@user.luma-mail.com>",
      subject: "Engineer BARの参加登録が完了しました",
      body: "予約済みです。 https://luma.com/a879ax7k",
    },
    ...overrides,
  };
}

test("同じjobの登録後に届いたLuma確認mailだけを安全なreceiptへ変換する", () => {
  const receipt = verifyLumaConfirmationMessage(fixture());

  assert.deepEqual(receipt, {
    kind: "confirmation_mail",
    provider_id: "19fbdc3478265ec8",
    observed_at: "2026-08-01T14:38:44.000Z",
    tenant_id: "dais-local",
    job_id: JOB_ID,
    event_url: "https://luma.com/a879ax7k",
  });
  assert.equal(Object.isFrozen(receipt), true);
  assert.doesNotMatch(JSON.stringify(receipt), /event-owner|subject|body|cookie|token/i);
});

test("gog full JSONをGmailのexact internalDate付きmessageへ正規化する", () => {
  assert.deepEqual(lumaConfirmationMessageFromGog({
    body: "https://luma.com/a879ax7k",
    headers: {
      from: "mii <event-owner@user.luma-mail.com>",
      subject: "Engineer BARの参加登録が完了しました",
    },
    message: {
      id: "19fbdc3478265ec8",
      internalDate: "1785595124000",
    },
  }), {
    id: "19fbdc3478265ec8",
    internalDate: "2026-08-01T14:38:44.000Z",
    from: "mii <event-owner@user.luma-mail.com>",
    subject: "Engineer BARの参加登録が完了しました",
    body: "https://luma.com/a879ax7k",
  });
});

test("attempt開始前、完了から30分超、別event、曖昧な件名、非Luma送信元を拒否する", () => {
  assert.throws(() => verifyLumaConfirmationMessage(fixture({
    message: { ...fixture().message, internalDate: "2026-08-01T14:38:32.324Z" },
  })), /registration/i);
  assert.throws(() => verifyLumaConfirmationMessage(fixture({
    message: { ...fixture().message, internalDate: "2026-08-01T15:08:40.077Z" },
  })), /registration/i);
  assert.throws(() => verifyLumaConfirmationMessage(fixture({
    message: { ...fixture().message, body: "https://luma.com/not-this-event" },
  })), /event URL/i);
  assert.throws(() => verifyLumaConfirmationMessage(fixture({
    message: { ...fixture().message, subject: "イベントのお知らせ" },
  })), /subject/i);
  assert.throws(() => verifyLumaConfirmationMessage(fixture({
    message: { ...fixture().message, from: "attacker@example.com" },
  })), /sender/i);
});

test("minute精度のGmail時刻は同じregistration attemptと重なる区間だけ許可する", () => {
  const receipt = verifyLumaConfirmationMessage(fixture({
    message: {
      ...fixture().message,
      internalDate: undefined,
      date: "2026-08-01 23:38",
    },
  }));
  assert.equal(receipt.observed_at, "2026-08-01T14:38:59.999Z");

  assert.throws(() => verifyLumaConfirmationMessage(fixture({
    message: {
      ...fixture().message,
      internalDate: undefined,
      date: "2026-08-01 23:37",
    },
  })), /registration/i);
});

test("tenant/jobにboundしたreceiptはimmutableでcross-tenantから読めない", async () => {
  const dataDir = fs.mkdtempSync(path.join(os.tmpdir(), "luma-confirmation-mail-"));
  const store = createLumaConfirmationMailStore({ dataDir });
  const verified = verifyLumaConfirmationMessage(fixture());
  const first = await store.record(verified);
  const second = await store.record(verified);

  assert.deepEqual(second, first);
  assert.match(first.external_receipt_ref, /^gmail-message:\/\/dais-local\/[0-9a-f]{64}$/);
  assert.deepEqual(
    await store.readExternalReceipt("dais-local", first.external_receipt_ref),
    {
      kind: "confirmation_mail",
      provider_id: "19fbdc3478265ec8",
      observed_at: "2026-08-01T14:38:44.000Z",
    },
  );
  await assert.rejects(
    store.readExternalReceipt("tenant-b", first.external_receipt_ref),
    /unavailable/i,
  );
  await assert.rejects(
    store.record(JSON.parse(JSON.stringify(verified))),
    /verified receipt/i,
  );
});
