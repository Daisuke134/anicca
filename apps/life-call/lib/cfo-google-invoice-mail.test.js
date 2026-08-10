"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");
const { makeGogMail } = require("./transport/mail-gog.js");

const QUERY = 'from:payments-noreply@google.com subject:"Google Cloud Platform & APIs:" has:attachment filename:pdf newer_than:400d';
const hit = (id, date, from = "Google Payments <payments-noreply@google.com>", subject = "Google Cloud Platform & APIs: invoice") => ({ id, date, from, subject });
const full = (extra = {}) => ({ attachments: [{ filename: "invoice.pdf", size: 1234, mimeType: "application/pdf", attachmentId: "Ab-_09" }], ...extra });

test("findLatestGoogleCloudInvoice chooses newest valid hit, reads once, and returns private frozen locator", async () => {
  const calls = [];
  const mail = makeGogMail({ account: "cfo@example.com", run: args => {
    calls.push(args);
    if (args[2] === "search") return JSON.stringify({ messages: [hit("a1b2c3d4", "2026-07-01 10:00"), hit("deadbeef", "2026-08-01 10:00", "attacker@example.com"), hit("abcdef0123456789", "2026-08-02 10:00")] });
    return JSON.stringify(full());
  } });
  const locator = await mail.findLatestGoogleCloudInvoice();
  assert.deepEqual(calls, [["gmail", "messages", "search", QUERY, "-j", "--max=10", "--gmail-no-send"], ["gmail", "get", "abcdef0123456789", "-j", "--format=full", "--gmail-no-send"]]);
  assert.deepEqual(locator, { messageId: "abcdef0123456789", attachmentId: "Ab-_09", filename: "invoice.pdf", size: 1234, receivedAtLocal: "2026-08-02 10:00", source: "google_cloud_invoice_gmail" });
  assert.equal(Object.isFrozen(locator), true);
  assert.deepEqual(Object.keys(locator).sort(), ["attachmentId", "filename", "messageId", "receivedAtLocal", "size", "source"]);
  assert.equal("body" in locator, false);
});

test("findLatestGoogleCloudInvoice fails closed for absent account, bad command/data, invalid hits, or unsafe PDFs", async () => {
  const cases = [
    ["account absent", "", () => "{}"], ["search JSON", "x@y", () => "bad"], ["get JSON", "x@y", a => a[2] === "search" ? JSON.stringify({ messages: [hit("abcdef", "2026-08-02 10:00")] }) : "bad"],
    ["invalid hits", "x@y", () => JSON.stringify({ messages: [hit("not-hex", "2026-08-02 10:00"), hit("abcdef", "2026/08/02 10:00")] })],
    ["missing PDF", "x@y", a => a[2] === "search" ? JSON.stringify({ messages: [hit("abcdef", "2026-08-02 10:00")] }) : JSON.stringify({ attachments: [] })],
    ["duplicate PDF", "x@y", a => a[2] === "search" ? JSON.stringify({ messages: [hit("abcdef", "2026-08-02 10:00")] }) : JSON.stringify({ attachments: [full().attachments[0], full().attachments[0]] })],
    ["unsafe PDF", "x@y", a => a[2] === "search" ? JSON.stringify({ messages: [hit("abcdef", "2026-08-02 10:00")] }) : JSON.stringify({ attachments: [{ ...full().attachments[0], filename: "../invoice.pdf" }] })],
    ["command fails", "x@y", () => { throw new Error("gog failed"); }],
  ];
  for (const [name, account, run] of cases) assert.equal(await makeGogMail({ account, run }).findLatestGoogleCloudInvoice(), null, name);
});
