"use strict";

const assert = require("node:assert/strict");
const crypto = require("node:crypto");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const test = require("node:test");
const { captureLatestGoogleCloudInvoice } = require("./cfo-google-invoice-local-source.js");

const account = "ABC123-DEF456-GHI789";
const observedAt = "2026-08-11T03:04:05Z";
const pdf = Buffer.from("%PDF-1.7\nCFO_PRIVATE_PDF_SENTINEL\n%%EOF\n");
const text = [
  "アカウント ID ABC123-DEF456-GHI789",
  "請求期間 2026年7月1日",
  "2026年7月31日",
  "小計 ￥1,000",
  "消費税 ￥100",
  "合計 ￥1,100",
  "小計 ￥1,000",
  "消費税 ￥100",
  "合計 ￥1,100",
].join("\n");
const locator = Object.freeze({ messageId: "abcdef0123456789", attachmentId: "Ab-_09", filename: "invoice.pdf", size: pdf.length, receivedAtLocal: "2026-08-02 10:00", source: "google_cloud_invoice_gmail" });
const hash = bytes => crypto.createHash("sha256").update(bytes).digest("hex");
const mode = file => fs.statSync(file).mode & 0o777;
const sourceDir = root => path.join(root, "cfo", "provider-billing", "google-cloud");
const makeMail = (write = true) => {
  const calls = { find: 0, download: 0 };
  return { calls, mail: { async findLatestGoogleCloudInvoice() { calls.find += 1; return locator; }, async downloadGoogleCloudInvoice(_, outPath) { calls.download += 1; if (!write) return null; fs.writeFileSync(outPath, pdf, { mode: 0o600 }); return { bytes: pdf.length, cached: false }; } } };
};

test("parses, normalizes, appends, and deduplicates one private invoice", async () => {
  const parent = fs.mkdtempSync(path.join(os.tmpdir(), "cfo-google-capture-")), root = path.join(parent, "state");
  try {
    const firstMail = makeMail(), paths = [];
    const runText = pdfPath => { paths.push(pdfPath); return text; };
    const first = await captureLatestGoogleCloudInvoice({ stateRoot: root, observedAt, mail: firstMail.mail, runText });
    assert.deepEqual(Object.keys(first), ["status", "record_id", "confirmed"]); assert.equal(first.status, "appended"); assert.ok(Object.isFrozen(first) && Object.isFrozen(first.confirmed));
    const recordPath = path.join(sourceDir(root), `${first.record_id.slice(7)}.json`), before = fs.readFileSync(recordPath);
    assert.equal(first.record_id, `sha256:${hash(pdf)}`); assert.equal(mode(recordPath), 0o600); for (const dir of [path.join(root, "cfo"), path.join(root, "cfo", "provider-billing"), sourceDir(root)]) assert.equal(mode(dir), 0o700);
    assert.deepEqual(JSON.parse(before), first.confirmed); assert.doesNotMatch(before.toString(), /ABC123|CFO_PRIVATE|abcdef|invoice\.pdf|HOSTILE/); assert.equal(paths.length, 1); assert.equal(fs.existsSync(paths[0]), false); assert.equal(fs.existsSync(path.dirname(paths[0])), false);
    const secondMail = makeMail(); const second = await captureLatestGoogleCloudInvoice({ stateRoot: root, observedAt: "2026-08-12T03:04:05Z", mail: secondMail.mail, runText });
    assert.equal(second.status, "existing"); assert.deepEqual(second.confirmed, first.confirmed); assert.deepEqual(fs.readFileSync(recordPath), before); assert.deepEqual(fs.readdirSync(sourceDir(root)).filter(name => name.endsWith(".json")), [`${first.record_id.slice(7)}.json`]);
  } finally { fs.rmSync(parent, { recursive: true, force: true }); }
});

test("fails closed with redacted errors for source, transfer, PDF, text, arithmetic, and record conflicts", async () => {
  const cases = [
    ["source", ({ mail, root }) => captureLatestGoogleCloudInvoice({ stateRoot: root, observedAt, mail, runText: () => text })],
    ["download", ({ mail, root }) => captureLatestGoogleCloudInvoice({ stateRoot: root, observedAt, mail, runText: () => text })],
    ["pdf", ({ mail, root }) => captureLatestGoogleCloudInvoice({ stateRoot: root, observedAt, mail, runText: () => text })],
    ["text", ({ mail, root }) => captureLatestGoogleCloudInvoice({ stateRoot: root, observedAt, mail, runText: () => "HOSTILE_TEXT" })],
    ["arithmetic", ({ mail, root }) => captureLatestGoogleCloudInvoice({ stateRoot: root, observedAt, mail, runText: () => text.replace("合計 ￥1,100", "合計 ￥1,101") })],
    ["grouping", ({ mail, root }) => captureLatestGoogleCloudInvoice({ stateRoot: root, observedAt, mail, runText: () => text.replaceAll("￥1,000", "￥1,00").replaceAll("￥1,100", "￥1,100") })],
  ];
  for (const [name, invoke] of cases) {
    const parent = fs.mkdtempSync(path.join(os.tmpdir(), "cfo-google-fail-")), root = path.join(parent, "state");
    const fake = makeMail(name !== "download"); if (name === "source") fake.mail.findLatestGoogleCloudInvoice = async () => null;
    if (name === "pdf") fake.mail.downloadGoogleCloudInvoice = async (_, outPath) => { fs.writeFileSync(outPath, Buffer.from("not-pdf"), { mode: 0o600 }); return { bytes: 7, cached: false }; };
    try { await assert.rejects(invoke({ mail: fake.mail, root }), error => error && /^cfo_google_invoice_capture_invalid:[a-z_]+$/.test(error.message) && !/HOSTILE|ABC123|abcdef/.test(error.message), name); assert.equal(fs.existsSync(sourceDir(root)), false); } finally { fs.rmSync(parent, { recursive: true, force: true }); }
  }
  const parent = fs.mkdtempSync(path.join(os.tmpdir(), "cfo-google-conflict-")), root = path.join(parent, "state"), dir = sourceDir(root), recordPath = path.join(dir, `${hash(pdf)}.json`), conflicting = Buffer.from("{\"HOSTILE_CONFLICT\":true}\n");
  try { fs.mkdirSync(dir, { recursive: true, mode: 0o700 }); fs.writeFileSync(recordPath, conflicting, { mode: 0o600 }); await assert.rejects(captureLatestGoogleCloudInvoice({ stateRoot: root, observedAt, mail: makeMail().mail, runText: () => text }), /cfo_google_invoice_capture_invalid:record_conflict$/); assert.deepEqual(fs.readFileSync(recordPath), conflicting); } finally { fs.rmSync(parent, { recursive: true, force: true }); }
});
