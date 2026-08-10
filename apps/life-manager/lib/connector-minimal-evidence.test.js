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
      const receiptId = createHash("sha256").update(`${input.tenantId}\n${input.eventRef}\n${input.observedAt}\n${pngSha}`).digest("hex");
      return Object.freeze({
        external_receipt_ref: `provider-receipt://luma/${receiptId}`,
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
    async setContent(content) { calls.push(["set-content", content]); },
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
  assert.equal(calls.filter(([name]) => name === "set-content").length, 1);
  assert.equal(calls.some(([name]) => ["goto", "url", "evaluate", "document-open", "document-write", "document-close"].includes(name)), false);
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
  assert.equal(
    calls.find(([name]) => name === "telegram-message")[2].idempotencyKey,
    `connector-evidence:${calls.find(([name]) => name === "calendar-create")[1].idempotencyValue}`,
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
  const png = options.png || Buffer.concat([PNG_SIGNATURE, Buffer.alloc(6_000, 7)]); const pngSha = createHash("sha256").update(png).digest("hex");
  const calls = []; const receipt = { id: "google-peatix-1", htmlLink: "https://www.google.com/calendar/event?eid=peatix-one" }; let reads = 0;
  const calendar = options.calendar || {
    async findConnectorEvents(input) { calls.push(["calendar-read", input]); return reads++ === 0 ? [] : [receipt]; },
    async createConnectorEvent(input) { calls.push(["calendar-create", input]); return receipt; },
  };
  const evidenceStore = options.evidenceStore || { async record(input) { calls.push(["evidence-record", input]); const receiptId = createHash("sha256").update(`${input.tenantId}\n${input.eventRef}\n${input.observedAt}\n${pngSha}`).digest("hex"); return { external_receipt_ref: `provider-receipt://peatix/${receiptId}`, artifact_ref: `object://sha256/${pngSha}` }; } };
  const chain = createMinimalEvidenceChain({ stateDir, tenantId: "dais-local", calendar, calendarId: "primary", telegramTarget: "private-target", peatixEvidenceStore: evidenceStore, now: () => new Date("2026-08-07T08:30:00.000Z"), sendMessage: options.sendMessage || (async (message, telegram) => { calls.push(["telegram-message", message, telegram]); return { messageId: 9101 }; }), sendPhoto: options.sendPhoto || (async (bytes, telegram) => { calls.push(["telegram-photo", bytes, telegram]); return { messageId: 9102 }; }) });
  let pageUrl = options.pageUrl || "https://peatix.com/event/5075819/ticket";
  const page = {
    async setContent(content) { calls.push(["set-content", content]); if (options.setContentNeverSettles) return new Promise(() => {}); if (options.setContentThrows) throw new Error("setContent failed"); },
    async goto(url, input) { calls.push(["goto", url, input]); if (options.gotoThrows) throw new Error("reset failed"); pageUrl = options.gotoReadback || url; },
    url() { calls.push(["url"]); return pageUrl; },
    async evaluate(fn, payload) {
      calls.push(["evaluate", payload]); if (options.evaluateThrows) throw new Error("receipt write failed");
      const previousDocument = global.document;
      global.document = {
        open() { calls.push(["document-open"]); },
        write(value) { calls.push(["document-write", value]); },
        close() { calls.push(["document-close"]); },
        querySelector() { return options.receiptValid === false ? null : {}; },
        querySelectorAll() { return options.receiptValid === false ? [] : [{}, {}, {}]; },
      };
      try { const result = await fn(payload); return options.evaluateResult === undefined ? result : options.evaluateResult; } finally { global.document = previousDocument; }
    },
    async screenshot(input) { calls.push(["screenshot", input]); return png; },
  };
  return { chain, stateDir, calls, pngSha, candidate: peatixCandidate(), page, cleanup: () => fs.rmSync(stateDir, { recursive: true, force: true }) };
}
function bundleFiles(stateDir) {
  try { return fs.readdirSync(path.join(stateDir, "applied-bundles")); } catch { return []; }
}

function checkpointFiles(stateDir) {
  try { return fs.readdirSync(path.join(stateDir, "evidence", "checkpoints")); } catch { return []; }
}

function recoveryStore(png, calls, options = {}) {
  const artifactSha = createHash("sha256").update(png).digest("hex");
  return { async record(input) { calls.push(["evidence-record", input]); const receiptHash = createHash("sha256").update(`${input.tenantId}\n${input.eventRef}\n${input.observedAt}\n${artifactSha}`).digest("hex"); return { external_receipt_ref: `provider-receipt://peatix/${receiptHash}`, artifact_ref: `object://sha256/${artifactSha}` }; },
    async readExternalReceipt(tenant, ref) { calls.push(["evidence-read-receipt", tenant, ref]); if (options.missingReceipt) throw new Error("missing receipt"); return { kind: "provider_response", provider_id: String(ref).split("/").at(-1) }; },
    async readArtifact(tenant, ref) { calls.push(["evidence-read-artifact", tenant, ref]); return options.artifact || png; } };
}

function recoveryCandidate() {
  return peatixCandidate({ title: "Private Title", venue_name: "Private Venue", ticket_id: "private-ticket" });
}

function checkpointValue(fixture, overrides = {}) {
  const observedAt = "2026-08-07T08:30:00.000Z"; const eventRef = fixture.candidate.event_ref; const artifactSha = fixture.pngSha;
  const receiptId = createHash("sha256").update(`dais-local\n${eventRef}\n${observedAt}\n${artifactSha}`).digest("hex");
  const urlSha = createHash("sha256").update(fixture.candidate.canonical_url).digest("hex");
  return { schema_version: 1, stage: "evidence", provider: "peatix", event_ref: eventRef, canonical_url_sha256: urlSha, provider_status: "registered", provider_receipt_ref: `provider-receipt://peatix/${receiptId}`, artifact_ref: `object://sha256/${artifactSha}`, artifact_sha256: artifactSha, observed_at: observedAt, ...overrides };
}

function checkpointPathFor(fixture) {
  const urlSha = createHash("sha256").update(fixture.candidate.canonical_url).digest("hex");
  const identity = createHash("sha256").update(`peatix\n${fixture.candidate.event_ref}\n${urlSha}`).digest("hex");
  return path.join(fixture.stateDir, "evidence", "checkpoints", `${identity}.json`);
}
function rawPointer(fixture, raw) {
  const file = checkpointPathFor(fixture); fs.mkdirSync(path.dirname(file), { recursive: true, mode: 0o700 }); fs.writeFileSync(file, `${raw}\n`, { mode: 0o600 });
}
function symlinkPointer(fixture, raw, parent) {
  const file = checkpointPathFor(fixture); const outside = fs.mkdtempSync(path.join(os.tmpdir(), "connector-checkpoint-outside-")); const target = path.join(outside, path.basename(file)); fs.writeFileSync(target, `${raw}\n`, { mode: 0o600 }); fixture.outside = outside;
  if (parent) { fs.mkdirSync(path.dirname(file), { recursive: true, mode: 0o700 }); fs.rmSync(path.dirname(file), { recursive: true, force: true }); fs.symlinkSync(outside, path.dirname(file), "dir"); } else { fs.mkdirSync(path.dirname(file), { recursive: true, mode: 0o700 }); fs.symlinkSync(target, file); }
}

test("initial provider record rejects a forged receipt identity before pointer and downstream effects", async () => {
  const fixture = peatixFixture({ evidenceStore: { async record(input) { fixture.calls.push(["evidence-record", input]); return { external_receipt_ref: `provider-receipt://peatix/${"f".repeat(64)}`, artifact_ref: `object://sha256/${fixture.pngSha}` }; } } });
  try {
    await assert.rejects(fixture.chain.completeEvidence({ provider: "peatix", candidate: fixture.candidate, page: fixture.page, providerState: { status: "registered" } }));
    for (const name of ["calendar-read", "calendar-create", "telegram-message", "telegram-photo"]) assert.equal(fixture.calls.filter(([callName]) => callName === name).length, 0, name);
    assert.equal(checkpointFiles(fixture.stateDir).length, 0);
  } finally { fixture.cleanup(); }
});

test("checkpoint corruption and symlink matrix fails before every downstream effect", async () => {
  const png = Buffer.concat([PNG_SIGNATURE, Buffer.alloc(6_000, 6)]);
  const cases = [
    ["invalid-json", (f, p) => rawPointer(f, "{")],
    ["extra-key", (f, p) => rawPointer(f, JSON.stringify({ ...p, extra: "reject" }))],
    ["wrong-provider", (f, p) => rawPointer(f, JSON.stringify({ ...p, provider: "luma" }))],
    ["wrong-event", (f, p) => rawPointer(f, JSON.stringify({ ...p, event_ref: "peatix-event://event/999" }))],
    ["wrong-url-hash", (f, p) => rawPointer(f, JSON.stringify({ ...p, canonical_url_sha256: "e".repeat(64) }))],
    ["forged-receipt", (f, p) => rawPointer(f, JSON.stringify({ ...p, provider_receipt_ref: `provider-receipt://peatix/${"f".repeat(64)}` }))],
    ["malformed-receipt-ref", (f, p) => rawPointer(f, JSON.stringify({ ...p, provider_receipt_ref: "provider-receipt://peatix/not-a-hash" }))],
    ["malformed-artifact-ref", (f, p) => rawPointer(f, JSON.stringify({ ...p, artifact_ref: "object://sha256/not-a-hash" }))],
    ["artifact-ref-sha", (f, p) => rawPointer(f, JSON.stringify({ ...p, artifact_ref: `object://sha256/${"a".repeat(64)}` }))],
    ["missing-receipt", (f, p) => rawPointer(f, JSON.stringify(p)), { missingReceipt: true }],
    ["internally-consistent-non-png", (f, p) => { const bytes = Buffer.alloc(6_008, 5); const sha = createHash("sha256").update(bytes).digest("hex"); const receipt = createHash("sha256").update(`dais-local\n${f.candidate.event_ref}\n${p.observed_at}\n${sha}`).digest("hex"); rawPointer(f, JSON.stringify({ ...p, provider_receipt_ref: `provider-receipt://peatix/${receipt}`, artifact_ref: `object://sha256/${sha}`, artifact_sha256: sha })); }, { artifact: Buffer.alloc(6_008, 5) }],
    ["artifact-bytes", (f, p) => rawPointer(f, JSON.stringify(p)), { artifact: Buffer.concat([PNG_SIGNATURE, Buffer.alloc(6_000, 5)]) }],
    ["file-symlink", (f, p) => symlinkPointer(f, JSON.stringify(p), false)],
    ["parent-symlink", (f, p) => symlinkPointer(f, JSON.stringify(p), true)],
  ];
  for (const [name, setup, storeOptions = {}] of cases) {
    const audit = []; const store = recoveryStore(png, audit, storeOptions); const fixture = peatixFixture({ png, evidenceStore: store });
    try {
      setup(fixture, checkpointValue(fixture));
      await assert.rejects(fixture.chain.completeEvidence({ provider: "peatix", candidate: fixture.candidate, page: fixture.page, providerState: { status: "registered" } }), undefined, name);
      for (const effect of ["set-content", "goto", "url", "evaluate", "screenshot", "evidence-record", "calendar-read", "calendar-create", "telegram-message", "telegram-photo"]) assert.equal(fixture.calls.filter(([callName]) => callName === effect).length, 0, `${name}:${effect}`);
      assert.equal(bundleFiles(fixture.stateDir).length, 0, name);
    } finally { fixture.cleanup(); if (fixture.outside) fs.rmSync(fixture.outside, { recursive: true, force: true }); }
  }
});

test("evidence checkpoint recovers PNG/provider receipt without render, screenshot, or record", async () => {
  const stateDir = fs.mkdtempSync(path.join(os.tmpdir(), "connector-minimal-evidence-recovery-")); const png = Buffer.concat([PNG_SIGNATURE, Buffer.alloc(6_000, 9)]); const firstCalls = [];
  const evidenceStore = recoveryStore(png, firstCalls); const failingCalendar = { async findConnectorEvents() { firstCalls.push(["calendar-read"]); throw new Error("Calendar unavailable"); }, async createConnectorEvent() { firstCalls.push(["calendar-create"]); throw new Error("must not create"); } };
  const first = createMinimalEvidenceChain({ stateDir, tenantId: "dais-local", calendar: failingCalendar, calendarId: "primary", telegramTarget: "private-target", peatixEvidenceStore: evidenceStore, now: () => new Date("2026-08-07T08:30:00.000Z"), sendMessage: async () => { throw new Error("must not send"); }, sendPhoto: async () => { throw new Error("must not send"); } });
  const firstPage = { async goto() {}, url() { return "about:blank"; }, async evaluate() { return true; }, async screenshot() { firstCalls.push(["screenshot"]); return png; } };
  await assert.rejects(first.completeEvidence({ provider: "peatix", candidate: recoveryCandidate(), page: firstPage, providerState: { status: "registered" } }));
  assert.equal(firstCalls.filter(([name]) => name === "evidence-record").length, 1);
  assert.equal(firstCalls.filter(([name]) => name === "screenshot").length, 1);
  assert.equal(checkpointFiles(stateDir).length, 1);
  const checkpointFile = path.join(stateDir, "evidence", "checkpoints", checkpointFiles(stateDir)[0]);
  const checkpoint = JSON.parse(fs.readFileSync(checkpointFile, "utf8"));
  assert.deepEqual(Object.keys(checkpoint).sort(), ["artifact_ref", "artifact_sha256", "canonical_url_sha256", "event_ref", "observed_at", "provider", "provider_receipt_ref", "provider_status", "schema_version", "stage"]);
  assert.equal(checkpoint.stage, "evidence");
  assert.equal(fs.statSync(checkpointFile).mode & 0o777, 0o600);
  assert.doesNotMatch(JSON.stringify(checkpoint), /Private Title|Private Venue|private-ticket|private-target|peatix\.com|6536845|PNG/i);

  const secondCalls = [];
  const calendarReceipt = { id: "google-recovery", htmlLink: "https://www.google.com/calendar/event?eid=recovery" };
  let reads = 0;
  const second = createMinimalEvidenceChain({ stateDir, tenantId: "dais-local", calendar: { async findConnectorEvents() { secondCalls.push(["calendar-read"]); return reads++ === 0 ? [calendarReceipt] : [calendarReceipt]; }, async createConnectorEvent() { secondCalls.push(["calendar-create"]); throw new Error("duplicate Calendar"); } }, calendarId: "primary", telegramTarget: "private-target", peatixEvidenceStore: recoveryStore(png, secondCalls), now: () => new Date("2026-08-07T08:31:00.000Z"), sendMessage: async () => ({ messageId: 1 }), sendPhoto: async () => ({ messageId: 2 }) });
  const noEffectsPage = { async goto() { throw new Error("render"); }, url() { throw new Error("render"); }, async evaluate() { throw new Error("render"); }, async screenshot() { throw new Error("screenshot"); } };
  const bundle = await second.completeEvidence({ provider: "peatix", candidate: recoveryCandidate(), page: noEffectsPage, providerState: { status: "registered" } });
  assert.equal(bundle.status, "applied_bundle");
  assert.equal(secondCalls.filter(([name]) => name === "evidence-read-receipt").length, 1);
  assert.equal(secondCalls.filter(([name]) => name === "evidence-read-artifact").length, 1);
  for (const name of ["screenshot", "evidence-record", "calendar-create"]) assert.equal(secondCalls.filter(([callName]) => callName === name).length, 0, name);
  fs.rmSync(stateDir, { recursive: true, force: true });
});

test("Calendar create/readback crash recovery reuses the one idempotent event", async () => {
  const stateDir = fs.mkdtempSync(path.join(os.tmpdir(), "connector-minimal-calendar-recovery-"));
  const png = Buffer.concat([PNG_SIGNATURE, Buffer.alloc(6_000, 8)]); const calls = []; const store = recoveryStore(png, calls);
  const receipt = { id: "google-crash-recovery", htmlLink: "https://www.google.com/calendar/event?eid=crash-recovery" };
  let phase = "crash"; let created = false;
  const calendar = {
    async findConnectorEvents() { calls.push(["calendar-read", phase]); if (phase === "crash") return created ? (() => { throw new Error("readback crashed"); })() : []; if (phase === "deleted") return []; return [receipt]; },
    async createConnectorEvent() { calls.push(["calendar-create"]); created = true; return receipt; },
  };
  const chain = createMinimalEvidenceChain({ stateDir, tenantId: "dais-local", calendar, calendarId: "primary", telegramTarget: "private-target", peatixEvidenceStore: store, now: () => new Date("2026-08-07T08:30:00.000Z"), sendMessage: async () => ({ messageId: 10 }), sendPhoto: async () => ({ messageId: 11 }) });
  const page = { async goto() {}, url() { return "about:blank"; }, async evaluate() { return true; }, async screenshot() { return png; } };
  await assert.rejects(chain.completeEvidence({ provider: "peatix", candidate: recoveryCandidate(), page, providerState: { status: "registered" } }));
  assert.equal(calls.filter(([name]) => name === "calendar-create").length, 1);
  phase = "recovery";
  const recovered = await chain.completeEvidence({ provider: "peatix", candidate: recoveryCandidate(), page, providerState: { status: "registered" } });
  assert.equal(recovered.status, "applied_bundle");
  assert.equal(calls.filter(([name]) => name === "calendar-create").length, 1);
  phase = "deleted";
  await assert.rejects(chain.completeEvidence({ provider: "peatix", candidate: recoveryCandidate(), page, providerState: { status: "registered" } }));
  assert.equal(calls.filter(([name]) => name === "calendar-create").length, 2);
  fs.rmSync(stateDir, { recursive: true, force: true });
});

test("Peatix evidence resets the owned page and parent-writes the receipt without setContent", async () => {
  const fixture = peatixFixture({ setContentNeverSettles: true });
  try {
    const result = await Promise.race([
      fixture.chain.completeEvidence({ provider: "peatix", candidate: fixture.candidate, page: fixture.page, providerState: { status: "registered" } }),
      new Promise((resolve) => setTimeout(() => resolve({ status: "timeout" }), 250)),
    ]);
    assert.equal(result.status, "applied_bundle");
    assert.equal(fixture.calls.filter(([name]) => name === "set-content").length, 0);
    assert.deepEqual(fixture.calls.find(([name]) => name === "goto"), ["goto", "about:blank", { waitUntil: "domcontentloaded", timeout: 30_000 }]);
    const write = fixture.calls.find(([name]) => name === "document-write");
    assert.ok(write);
    assert.match(write[1], /<dt>provider<\/dt><dd>peatix<\/dd>/i);
    assert.match(write[1], /<dt>status<\/dt><dd>registered<\/dd>/i);
    assert.match(write[1], /peatix-event:\/\/event\/5075819/);
    assert.doesNotMatch(write[1], /Peatix Public Event|https:\/\/peatix\.com|6536845|<script|<img|<iframe|<link|<style/i);
    assert.deepEqual(fixture.calls.filter(([name]) => ["document-open", "document-close"].includes(name)).map(([name]) => name), ["document-open", "document-close"]);
    assert.ok(fixture.calls.findIndex(([name]) => name === "document-close") < fixture.calls.findIndex(([name]) => name === "screenshot"));
    assert.equal(bundleFiles(fixture.stateDir).length, 1);
  } finally { fixture.cleanup(); }
});

test("Peatix receipt reset and validation fail before every downstream side effect", async () => {
  const cases = [
    ["missing-goto", (page) => { delete page.goto; }],
    ["missing-url", (page) => { delete page.url; }],
    ["missing-evaluate", (page) => { delete page.evaluate; }],
    ["reset-throws", (page) => { page.goto = async () => { throw new Error("reset failed"); }; }],
    ["wrong-reset-readback", (page) => { page.goto = async () => {}; }],
    ["receipt-write-throws", (page) => { page.evaluate = async () => { throw new Error("write failed"); }; }],
    ["receipt-validation-false", (page) => { page.evaluate = async () => false; }],
    ["invalid-png", (page) => { page.screenshot = async () => Buffer.from("not-a-png"); }],
    ["provider-mismatch", (page, fixture) => { fixture.candidate = peatixCandidate({ event_ref: "luma-event://event/mismatch" }); }],
  ];
  for (const [name, mutate] of cases) {
    const fixture = peatixFixture();
    try {
      mutate(fixture.page, fixture);
      await assert.rejects(fixture.chain.completeEvidence({ provider: "peatix", candidate: fixture.candidate, page: fixture.page, providerState: { status: "registered" } }), undefined, name);
      for (const effect of ["screenshot", "evidence-record", "calendar-read", "calendar-create", "telegram-message", "telegram-photo"]) assert.equal(fixture.calls.filter(([callName]) => callName === effect).length, 0, `${name}:${effect}`);
      assert.equal(bundleFiles(fixture.stateDir).length, 0, name);
    } finally { fixture.cleanup(); }
  }
});

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

test("evidence parent-writes a fixed privacy-safe receipt before screenshot", async () => {
  const fixture = peatixFixture();
  try {
    await fixture.chain.completeEvidence({ provider: "peatix", candidate: fixture.candidate, page: fixture.page, providerState: { status: "registered" } });
    const replacement = fixture.calls.find(([name]) => name === "document-write");
    const screenshotIndex = fixture.calls.findIndex(([name]) => name === "screenshot");
    assert.ok(replacement);
    assert.ok(fixture.calls.indexOf(replacement) < screenshotIndex);
    assert.match(replacement[1], /peatix-event:\/\/event\/5075819/);
    assert.match(replacement[1], /<dt>provider<\/dt><dd>peatix<\/dd>/i);
    assert.match(replacement[1], /<dt>status<\/dt><dd>registered<\/dd>/i);
    assert.doesNotMatch(replacement[1], /Peatix Public Event|https:\/\/peatix\.com|6536845|<script|<img|<iframe|<link|<style/i);
  } finally { fixture.cleanup(); }
});

test("receipt replacement failure prevents screenshot, evidence, Calendar, Telegram, and bundle effects", async () => {
  const fixture = peatixFixture(); fixture.page.evaluate = async () => { throw new Error("replacement failed"); };
  try {
    await assert.rejects(fixture.chain.completeEvidence({ provider: "peatix", candidate: fixture.candidate, page: fixture.page, providerState: { status: "registered" } }));
    for (const name of ["screenshot", "evidence-record", "calendar-read", "calendar-create", "telegram-message", "telegram-photo"]) assert.equal(fixture.calls.filter(([callName]) => callName === name).length, 0, name);
    assert.equal(bundleFiles(fixture.stateDir).length, 0);
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
