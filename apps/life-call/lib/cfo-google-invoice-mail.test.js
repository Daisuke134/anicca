"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");
const { makeGogMail } = require("./transport/mail-gog.js");

const QUERY = 'from:payments-noreply@google.com subject:"Google Cloud Platform & APIs:" has:attachment filename:pdf newer_than:400d';
const hit = (id, date, from = "Google Payments <payments-noreply@google.com>", subject = "Google Cloud Platform & APIs: invoice") => ({ id, date, from, subject });
const full = (extra = {}) => ({ attachments: [{ filename: "invoice.pdf", size: 1234, mimeType: "application/pdf", attachmentId: "Ab-_09" }], ...extra });
const ANTHROPIC_QUERY = 'from:(mail.anthropic.com) subject:"Your receipt from Anthropic, PBC" newer_than:400d'; const anthropicHit = (id, date, from = "Anthropic, PBC <receipt@mail.anthropic.com>", subject = "Your receipt from Anthropic, PBC #1234-5678-9012") => ({ id, date, from, subject });
test("readLatestAnthropicSubscriptionReceipt selects the newest authenticated receipt and returns frozen memory evidence", async () => {
  const calls = [], body = "synthetic sanitized Anthropic receipt body";
  const mail = makeGogMail({ account: "cfo@example.com", run: args => {
    calls.push(args);
    if (args[2] === "search") return JSON.stringify({ messages: [anthropicHit("a1b2c3d4", "2026-07-01 10:00"), anthropicHit("deadbeef", "2026-08-11 10:00", "Attacker <x@evil.example>"), anthropicHit("abcdef0123456789", "2026-08-10 10:00")] });
    if (args[1] === "raw") return JSON.stringify({ payload: { headers: [{ name: "Authentication-Results", value: "mx.google.com; dkim=pass header.i=@mail.anthropic.com; dmarc=pass header.from=mail.anthropic.com" }] } });
    return JSON.stringify({ headers: { from: "Anthropic, PBC <receipt@mail.anthropic.com>", subject: "Your receipt from Anthropic, PBC #1234-5678-9012" }, body });
  } });
  const result = await mail.readLatestAnthropicSubscriptionReceipt();
  assert.deepEqual(calls, [["gmail", "messages", "search", ANTHROPIC_QUERY, "-j", "--max=10", "--gmail-no-send"], ["gmail", "raw", "abcdef0123456789", "-j", "--gmail-no-send"], ["gmail", "get", "abcdef0123456789", "-j", "--format=full", "--sanitize-content", "--gmail-no-send"]]);
  assert.deepEqual(result, { source: "anthropic_subscription_receipt_gmail", receivedAtLocal: "2026-08-10 10:00", body });
  assert.equal(Object.isFrozen(result), true);
  assert.deepEqual(Object.keys(result).sort(), ["body", "receivedAtLocal", "source"]);
});

test("readLatestAnthropicSubscriptionReceipt fails closed without logs for malformed or unauthenticated data", async () => {
  const authValue = "mx.google.com; dkim=pass header.i=@mail.anthropic.com; dmarc=pass header.from=mail.anthropic.com";
  const validSearch = JSON.stringify({ messages: [anthropicHit("abcdef0123456789", "2026-08-10 10:00")] });
  const auth = value => JSON.stringify({ payload: { headers: value == null ? [] : Array.isArray(value) ? value : [{ name: "Authentication-Results", value }] } });
  const validRaw = auth(authValue), validGet = JSON.stringify({ headers: { from: anthropicHit("x", "2026-08-10 10:00").from, subject: anthropicHit("x", "2026-08-10 10:00").subject }, body: "body" });
  const script = (search = validSearch, raw = validRaw, get = validGet) => args => { const value = args[2] === "search" ? search : args[1] === "raw" ? raw : get; return typeof value === "function" ? value() : value; };
  const ar = value => ({ name: "Authentication-Results", value });
  const cases = [
    ["absent account", "", script()], ["search failure", "x@y", script(() => { throw new Error("search"); })], ["search invalid JSON", "x@y", script("bad")],
    ["all hits invalid", "x@y", script(JSON.stringify({ messages: [anthropicHit("not-hex", "2026-08-10 10:00")] }))], ["raw failure", "x@y", script(validSearch, () => { throw new Error("raw"); })], ["raw invalid JSON", "x@y", script(validSearch, "bad")],
    ["duplicate auth", "x@y", script(validSearch, auth([ar(authValue), ar(authValue)]))], ["non-Google auth", "x@y", script(validSearch, auth(authValue.replace("mx.google.com", "evil.google.com")))], ["missing auth", "x@y", script(validSearch, auth(null))],
    ["failing auth", "x@y", script(validSearch, auth(authValue.replace("dkim=pass", "dkim=fail")))], ["relaxed-domain auth", "x@y", script(validSearch, auth(authValue.replace("@mail.anthropic.com", "@sub.mail.anthropic.com").replace("header.from=mail.anthropic.com", "header.from=anthropic.com")))],
    ["get failure", "x@y", script(validSearch, validRaw, () => { throw new Error("get"); })], ["get invalid JSON", "x@y", script(validSearch, validRaw, "bad")], ["mismatched fetched sender", "x@y", script(validSearch, validRaw, validGet.replace("receipt@mail.anthropic.com", "attacker@mail.anthropic.com"))], ["empty body", "x@y", script(validSearch, validRaw, validGet.replace('"body":"body"', '"body":""'))], ["oversized body", "x@y", script(validSearch, validRaw, JSON.stringify({ headers: { from: anthropicHit("x", "2026-08-10 10:00").from, subject: anthropicHit("x", "2026-08-10 10:00").subject }, body: "x".repeat(20001) }))],
  ];
  const sinks = [console.log, console.error, console.warn]; let logs = 0; console.log = console.error = console.warn = () => { logs += 1; };
  try { for (const [name, account, run] of cases) { logs = 0; const old = process.env.GOG_ACCOUNT; if (!account) delete process.env.GOG_ACCOUNT; let result; try { result = await makeGogMail({ account, run }).readLatestAnthropicSubscriptionReceipt(); } finally { old === undefined ? delete process.env.GOG_ACCOUNT : process.env.GOG_ACCOUNT = old; } assert.equal(result, null, name); assert.equal(logs, 0, name); } } finally { [console.log, console.error, console.warn] = sinks; }
});

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

const downloadLocator = Object.freeze({ messageId: "abcdef0123456789", attachmentId: "Ab-_09", filename: "invoice.pdf", size: 1234, receivedAtLocal: "2026-08-02 10:00", source: "google_cloud_invoice_gmail" });
const downloadPath = "/tmp/cfo-google-invoice.pdf";
const downloadJson = (extra = {}) => JSON.stringify({ bytes: 1234, cached: false, path: downloadPath, ...extra });

test("downloadGoogleCloudInvoice issues one fixed command and returns frozen safe metadata", async () => {
  const calls = [];
  const mail = makeGogMail({ account: "cfo@example.com", run: args => { calls.push(args); return downloadJson(); } });
  const result = await mail.downloadGoogleCloudInvoice(downloadLocator, downloadPath);
  assert.deepEqual(calls, [["gmail", "attachment", downloadLocator.messageId, downloadLocator.attachmentId, `--out=${downloadPath}`, "-j", "--gmail-no-send"]]);
  assert.deepEqual(result, { bytes: 1234, cached: false });
  assert.equal(Object.isFrozen(result), true);
});

test("downloadGoogleCloudInvoice fails closed for invalid input or transfer data", async () => {
  const cases = [
    ["account absent", "", downloadLocator, downloadPath, () => "{}"],
    ["invalid message", "x@y", { ...downloadLocator, messageId: "not-hex" }, downloadPath, () => downloadJson()],
    ["invalid attachment", "x@y", { ...downloadLocator, attachmentId: "bad/id" }, downloadPath, () => downloadJson()],
    ["invalid source", "x@y", { ...downloadLocator, source: "other" }, downloadPath, () => downloadJson()],
    ["relative path", "x@y", downloadLocator, "invoice.pdf", () => downloadJson()],
    ["unsafe path", "x@y", downloadLocator, "/tmp/invoice.txt", () => downloadJson()],
    ["command failure", "x@y", downloadLocator, downloadPath, () => { throw new Error("gog failed"); }],
    ["invalid JSON", "x@y", downloadLocator, downloadPath, () => "bad"],
    ["path mismatch", "x@y", downloadLocator, downloadPath, () => downloadJson({ path: "/tmp/other.pdf" })],
    ["invalid bytes", "x@y", downloadLocator, downloadPath, () => downloadJson({ bytes: 0 })],
    ["non-integer bytes", "x@y", downloadLocator, downloadPath, () => downloadJson({ bytes: 1.5 })],
    ["non-boolean cached", "x@y", downloadLocator, downloadPath, () => downloadJson({ cached: "false" })],
  ];
  for (const [name, account, locator, outPath, run] of cases) {
    assert.equal(await makeGogMail({ account, run }).downloadGoogleCloudInvoice(locator, outPath), null, name);
  }
});
