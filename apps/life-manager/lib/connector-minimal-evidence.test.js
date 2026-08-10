"use strict";

const assert = require("node:assert/strict");
const { createHash } = require("node:crypto");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const test = require("node:test");

const { createMinimalEvidenceChain } = require("./connector-minimal-evidence.js");

const PNG_SIGNATURE = Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]);

test("verified registration becomes one durable Calendar PNG Telegram applied bundle", async () => {
  const stateDir = fs.mkdtempSync(path.join(os.tmpdir(), "connector-minimal-evidence-"));
  const png = Buffer.concat([PNG_SIGNATURE, Buffer.alloc(6_000, 7)]);
  const pngSha = createHash("sha256").update(png).digest("hex");
  const calls = [];
  const calendarReceipt = Object.freeze({
    id: "google-event-1",
    htmlLink: "https://www.google.com/calendar/event?eid=verified-one",
  });
  let calendarReads = 0;
  const calendar = {
    async findConnectorEvents(input) {
      calls.push(["calendar-read", input]);
      calendarReads += 1;
      return calendarReads === 1 ? [] : [calendarReceipt];
    },
    async createConnectorEvent(input) {
      calls.push(["calendar-create", input]);
      return calendarReceipt;
    },
  };
  const evidenceStore = {
    async record(input) {
      calls.push(["evidence-record", input]);
      assert.equal(input.screenshot, png);
      return Object.freeze({
        external_receipt_ref: `provider-receipt://luma/${"a".repeat(64)}`,
        artifact_ref: `object://sha256/${pngSha}`,
      });
    },
  };
  const chain = createMinimalEvidenceChain({
    stateDir,
    tenantId: "dais-local",
    calendar,
    calendarId: "primary",
    telegramTarget: "private-target",
    evidenceStore,
    now: () => new Date("2026-08-07T08:30:00.000Z"),
    async sendMessage(message, options) {
      calls.push(["telegram-message", message, options]);
      return { messageId: 9101 };
    },
    async sendPhoto(bytes, options) {
      calls.push(["telegram-photo", bytes, options]);
      return { messageId: 9102 };
    },
  });
  const candidate = Object.freeze({
    provider: "luma",
    event_ref: "luma-event://event/verified-one",
    canonical_url: "https://luma.com/verified-one",
    title: "Verified Technology Event",
    starts_at: "2026-08-10T10:00:00.000Z",
    ends_at: "2026-08-10T11:00:00.000Z",
    venue_name: "Tokyo",
  });
  const page = {
    async screenshot(input) {
      calls.push(["screenshot", input]);
      return png;
    },
  };

  const bundle = await chain.completeEvidence({
    provider: "luma",
    candidate,
    page,
    providerState: { status: "registered" },
    repairedActions: [],
  });

  assert.equal(bundle.status, "applied_bundle");
  assert.match(bundle.bundle_id, /^applied-bundle:[0-9a-f]{64}$/);
  assert.equal(calls.filter(([name]) => name === "screenshot").length, 1);
  assert.deepEqual(calls.find(([name]) => name === "screenshot")[1], { type: "png", fullPage: true });
  assert.equal(calls.filter(([name]) => name === "calendar-create").length, 1);
  assert.equal(calls.filter(([name]) => name === "calendar-read").length, 2);
  assert.equal(calls.filter(([name]) => name === "telegram-message").length, 1);
  assert.equal(calls.filter(([name]) => name === "telegram-photo").length, 1);
  assert.equal(
    calls.find(([name]) => name === "telegram-message")[1],
    [
      "Connector::: イベント申込を確認しました",
      "provider: luma",
      "event: Verified Technology Event",
      "status: registered",
      "starts at: 2026-08-10T10:00:00.000Z",
      "calendar event ID: google-event-1",
    ].join("\n"),
  );
  assert.equal(calls.find(([name]) => name === "telegram-photo")[2].caption, "Connector::: Verified Technology Event / registered");

  const bundleFile = path.join(stateDir, "applied-bundles", `${bundle.bundle_id.slice("applied-bundle:".length)}.json`);
  const persisted = JSON.parse(fs.readFileSync(bundleFile, "utf8"));
  assert.equal(persisted.bundle_id, bundle.bundle_id);
  assert.equal(persisted.provider_status, "registered");
  assert.equal(persisted.artifact_sha256, pngSha);
  assert.equal(persisted.calendar_event_id, "google-event-1");
  assert.equal(persisted.telegram_message_provider_id, "9101");
  assert.equal(persisted.telegram_photo_provider_id, "9102");
  assert.equal(JSON.stringify(persisted).includes("private-target"), false);
  assert.equal(fs.statSync(bundleFile).mode & 0o777, 0o600);
});

function peatixCandidate(extra = {}) {
  return {
    provider: "peatix", event_ref: "peatix-event://event/5075819", canonical_url: "https://peatix.com/event/5075819",
    title: "Peatix Public Event", starts_at: "2026-08-10T10:00:00.000Z", ends_at: "2026-08-10T11:00:00.000Z",
    venue_name: "Tokyo", ticket_id: "6536845", ...extra,
  };
}
function peatixFixture(options = {}) {
  const stateDir = fs.mkdtempSync(path.join(os.tmpdir(), "connector-minimal-peatix-evidence-"));
  const png = Buffer.concat([PNG_SIGNATURE, Buffer.alloc(6_000, 7)]); const pngSha = createHash("sha256").update(png).digest("hex");
  const calls = []; const receipt = { id: "google-peatix-1", htmlLink: "https://www.google.com/calendar/event?eid=peatix-one" }; let reads = 0;
  const calendar = options.calendar || {
    async findConnectorEvents(input) { calls.push(["calendar-read", input]); return reads++ === 0 ? [] : [receipt]; },
    async createConnectorEvent(input) { calls.push(["calendar-create", input]); return receipt; },
  };
  const evidenceStore = options.evidenceStore || { async record(input) { calls.push(["evidence-record", input]); return { external_receipt_ref: `provider-receipt://peatix/${"b".repeat(64)}`, artifact_ref: `object://sha256/${pngSha}` }; } };
  const chain = createMinimalEvidenceChain({ stateDir, tenantId: "dais-local", calendar, calendarId: "primary", telegramTarget: "private-target", peatixEvidenceStore: evidenceStore, now: () => new Date("2026-08-07T08:30:00.000Z"), sendMessage: options.sendMessage || (async (message, telegram) => { calls.push(["telegram-message", message, telegram]); return { messageId: 9101 }; }), sendPhoto: options.sendPhoto || (async (bytes, telegram) => { calls.push(["telegram-photo", bytes, telegram]); return { messageId: 9102 }; }) });
  return { chain, stateDir, calls, pngSha, candidate: peatixCandidate(), page: { async screenshot(input) { calls.push(["screenshot", input]); return png; } }, cleanup: () => fs.rmSync(stateDir, { recursive: true, force: true }) };
}
function bundleFiles(stateDir) {
  try { return fs.readdirSync(path.join(stateDir, "applied-bundles")); } catch { return []; }
}

test("Peatix registered readback creates a provider-specific complete applied bundle", async () => {
  const fixture = peatixFixture();
  try {
    const bundle = await fixture.chain.completeEvidence({ provider: "peatix", candidate: fixture.candidate, page: fixture.page, providerState: { status: "registered" } });
    assert.equal(bundle.provider, "peatix");
    assert.match(bundle.provider_receipt_ref, /^provider-receipt:\/\/peatix\/[0-9a-f]{64}$/);
    assert.equal(bundle.artifact_sha256, fixture.pngSha);
    assert.equal(fixture.calls.filter(([name]) => name === "calendar-read").length, 2);
    assert.equal(fixture.calls.filter(([name]) => name === "calendar-create").length, 1);
    assert.match(fixture.calls.find(([name]) => name === "telegram-message")[1], /provider: peatix/);
    assert.match(fixture.calls.find(([name]) => name === "telegram-photo")[2].caption, /peatix/i);
    assert.equal(fixture.calls.find(([name]) => name === "calendar-create")[1].canonicalUrl, fixture.candidate.canonical_url);
    assert.doesNotMatch(JSON.stringify(bundle), /Private Name|private@example\.test|6536845|private-target/);
    assert.equal(bundleFiles(fixture.stateDir).length, 1);
    const persisted = JSON.parse(fs.readFileSync(path.join(fixture.stateDir, "applied-bundles", `${bundle.bundle_id.slice("applied-bundle:".length)}.json`), "utf8"));
    assert.equal(persisted.provider, "peatix");
    assert.doesNotMatch(JSON.stringify(persisted), /Private Name|private@example\.test|6536845|private-target/);
  } finally { fixture.cleanup(); }
});

test("Peatix identity, state, receipt, Calendar, and Telegram partial failures never write a bundle", async () => {
  const wrongReceipt = { async record() { return { external_receipt_ref: `provider-receipt://luma/${"a".repeat(64)}`, artifact_ref: `object://sha256/${"c".repeat(64)}` }; } };
  let badCalendarReads = 0;
  const badCalendar = { async findConnectorEvents() { return badCalendarReads++ === 0 ? [] : [{ id: "wrong", htmlLink: "https://www.google.com/calendar/event?eid=wrong" }]; }, async createConnectorEvent() { return { id: "created", htmlLink: "https://www.google.com/calendar/event?eid=created" }; } };
  const cases = [
    () => { const f = peatixFixture(); return [f, { provider: "peatix", candidate: peatixCandidate({ canonical_url: "https://peatix.com/event/999" }), page: f.page, providerState: { status: "registered" } }]; },
    () => { const f = peatixFixture(); return [f, { provider: "peatix", candidate: f.candidate, page: f.page, providerState: { status: "pending" } }]; },
    () => { const f = peatixFixture({ evidenceStore: wrongReceipt }); return [f, { provider: "peatix", candidate: f.candidate, page: f.page, providerState: { status: "registered" } }]; },
    () => { const f = peatixFixture({ calendar: badCalendar }); return [f, { provider: "peatix", candidate: f.candidate, page: f.page, providerState: { status: "registered" } }]; },
  ];
  for (const makeCase of cases) {
    const [fixture, input] = makeCase();
    try { await assert.rejects(fixture.chain.completeEvidence(input)); assert.equal(bundleFiles(fixture.stateDir).length, 0); } finally { fixture.cleanup(); }
  }
  for (const channel of ["message", "photo"]) {
    const fixture = peatixFixture(channel === "message" ? { sendMessage: async () => ({ messageId: 0 }) } : { sendPhoto: async () => ({ messageId: 0 }) });
    try { await assert.rejects(fixture.chain.completeEvidence({ provider: "peatix", candidate: fixture.candidate, page: fixture.page, providerState: { status: "registered" } })); assert.equal(bundleFiles(fixture.stateDir).length, 0); } finally { fixture.cleanup(); }
  }
});

test("Peatix canonical URL rejects parser-normalized variants before every side effect", async () => {
  const invalidUrls = [
    "https://peatix.com/event/5075819/../5075819",
    "https://peatix.com/event/./5075819",
    "https://peatix.com:443/event/5075819",
    "https://PEATIX.COM/event/5075819",
    "https://peatix.com/event/5075819/",
    "https://peatix.com/event/5075819?utm_source=test",
    "https://peatix.com/event/5075819#details",
    " https://peatix.com/event/5075819",
    "https://peatix.com/event/5075819 ",
    "https://user:pass@peatix.com/event/5075819",
  ];
  for (const canonical_url of invalidUrls) {
    const fixture = peatixFixture();
    try {
      await assert.rejects(fixture.chain.completeEvidence({
        provider: "peatix",
        candidate: peatixCandidate({ canonical_url }),
        page: fixture.page,
        providerState: { status: "registered" },
      }));
      for (const name of ["screenshot", "evidence-record", "calendar-read", "calendar-create", "telegram-message", "telegram-photo"]) {
        assert.equal(fixture.calls.filter(([callName]) => callName === name).length, 0, `${canonical_url}: ${name}`);
      }
      assert.equal(bundleFiles(fixture.stateDir).length, 0, canonical_url);
    } finally { fixture.cleanup(); }
  }
});
