"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");
const { makeGogMail } = require("./mail-gog.js");

test("findReceipt uses message search, exact nonce content, and returns only safe receipt metadata", async () => {
  const nonce = "a".repeat(32);
  const calls = [];
  const mail = makeGogMail({ account: "controlled@aniccaai.com", run: args => {
    calls.push(args);
    return JSON.stringify({ messages: [{ id: "gmail-id", subject: `check ${nonce}`,
      body: "harmless", date: "2026-07-21T06:00:00Z" }] });
  } });
  const receipt = await mail.findReceipt({ nonce, afterMs: Date.parse("2026-07-21T05:59:00Z") });
  assert.deepEqual(calls, [["gmail", "messages", "search", `in:anywhere newer_than:1d \"${nonce}\"`, "-j", "--max=10", "--include-body"]]);
  assert.deepEqual(receipt, { id: "gmail-id", receivedAtMs: Date.parse("2026-07-21T06:00:00Z"), matchedNonce: nonce });
  assert.equal("subject" in receipt, false);
  assert.equal("body" in receipt, false);
});

test("findReceipt fails closed for nonce mismatch and stale messages", async () => {
  const nonce = "b".repeat(32);
  for (const message of [
    { id: "gmail-id", subject: "different", body: "different", date: "2026-07-21T06:00:00Z" },
    { id: "gmail-id", subject: nonce, body: "", date: "2026-07-20T06:00:00Z" },
  ]) {
    const mail = makeGogMail({ account: "controlled@aniccaai.com", run: () => JSON.stringify({ messages: [message] }) });
    assert.equal(await mail.findReceipt({ nonce, afterMs: Date.parse("2026-07-21T05:59:00Z") }), null);
  }
});

test("existing gog transport send and inbox paths retain their contracts", async () => {
  const calls = [];
  const mail = makeGogMail({ account: "controlled@aniccaai.com", run: args => {
    calls.push(args);
    if (args[1] === "send") return JSON.stringify({ id: "sent-id" });
    if (args[1] === "search") return JSON.stringify({ messages: [{ id: "message-id", subject: "subject" }] });
    return JSON.stringify({ headers: { subject: "subject" }, body: "body" });
  } });
  assert.equal(mail.ready(), true);
  assert.equal(await mail.send("to@example.com", "subject", "body"), true);
  assert.deepEqual(await mail.listInbox({ limit: 1 }), [{ subject: "subject", body: "body" }]);
  assert.equal(calls.length, 3);
});

test("default gog runner uses execFile argv with the fixed account", async () => {
  const calls = [];
  const mail = makeGogMail({ bin: "/opt/homebrew/bin/gog", account: "controlled@aniccaai.com", keyring: "keyring",
    execFileSyncImpl: (file, args, options) => { calls.push({ file, args, options }); return JSON.stringify({ id: "sent-id" }); } });
  assert.equal(await mail.send("to@example.com", "subject", "body"), true);
  assert.equal(calls[0].file, "/opt/homebrew/bin/gog");
  assert.deepEqual(calls[0].args.slice(-2), ["--account", "controlled@aniccaai.com"]);
  assert.equal(calls[0].options.env.GOG_ACCOUNT, "controlled@aniccaai.com");
});
