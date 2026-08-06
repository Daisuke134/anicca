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
