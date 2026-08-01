"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const test = require("node:test");

const {
  captureOfficialLumaTicketQr,
  createLumaGuestBinding,
  createLumaTicketQrStore,
} = require("./luma-ticket-qr.js");

const JOB_ID = `outbound-event:${"9".repeat(64)}`;
const GUEST_KEY = "g-FixtureSecret123";
const EVENT_WITH_KEY = `https://luma.com/a879ax7k?pk=${GUEST_KEY}`;
const TICKET_WITH_KEY = `https://luma.com/e/ticket/evt-fixture?pk=${GUEST_KEY}`;
const CHECK_IN_WITH_KEY = `https://luma.com/check-in/evt-fixture?pk=${GUEST_KEY}`;

function png() {
  const value = Buffer.alloc(5000, 0x61);
  Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]).copy(value);
  return value;
}

function binding(overrides = {}) {
  return createLumaGuestBinding({
    tenantId: "dais-local",
    jobId: JOB_ID,
    eventUrl: "https://luma.com/a879ax7k",
    providerMessageId: "19fbdc3478265ec8",
    body: `イベントページ: ${EVENT_WITH_KEY}\nマイチケット: ${TICKET_WITH_KEY}`,
    ...overrides,
  });
}

function pageFixture(candidates = [png()]) {
  return {
    async clickExactTicketControl() { return true; },
    async qrCandidates() { return candidates; },
  };
}

test("同じeventのmail内で一致するguest keyだけをopaque bindingにする", () => {
  const value = binding();
  assert.deepEqual(value, {
    tenant_id: "dais-local",
    job_id: JOB_ID,
    event_url: "https://luma.com/a879ax7k",
    provider_message_id: "19fbdc3478265ec8",
    guest_key_sha256: "a50b22c87f2f9134b4337700c49a33e462a6ef1b15abfd12ba9312f80e7e2412",
  });
  assert.doesNotMatch(JSON.stringify(value), /FixtureSecret|ticket\/evt/i);
});

test("別event、異なるguest key、guest key欠落を拒否する", () => {
  assert.throws(() => binding({
    body: `https://luma.com/another?pk=${GUEST_KEY}\n${TICKET_WITH_KEY}`,
  }), /event/i);
  assert.throws(() => binding({
    body: `${EVENT_WITH_KEY}\nhttps://luma.com/e/ticket/evt-fixture?pk=g-OtherKey999`,
  }), /guest key/i);
  assert.throws(() => binding({ body: "https://luma.com/a879ax7k" }), /guest key/i);
});

test("Luma公式QRのdecoded payloadがmailのguest bindingと一致する時だけ検証済みにする", async () => {
  const value = binding();
  const verified = await captureOfficialLumaTicketQr(pageFixture(), value, {
    decodeQr: async () => CHECK_IN_WITH_KEY,
    observedAt: () => "2026-08-01T15:10:00.000Z",
  });
  assert.deepEqual(verified, {
    kind: "ticket",
    tenant_id: "dais-local",
    job_id: JOB_ID,
    event_url: "https://luma.com/a879ax7k",
    provider_message_id: "19fbdc3478265ec8",
    guest_key_sha256: value.guest_key_sha256,
    observed_at: "2026-08-01T15:10:00.000Z",
    png_sha256: "ab6b33a196b0847df36693f384dd1104cfd8fb874dec9507e03eabf658012791",
    png_size_bytes: 5000,
  });
  await assert.rejects(
    captureOfficialLumaTicketQr(pageFixture(), value, {
      decodeQr: async () => "https://luma.com/check-in/evt-fixture?pk=g-WrongKey999",
    }),
    /matching official QR/i,
  );
});

test("verified QRだけをtenant-bound objectとして保存し、cross-tenant readを拒否する", async () => {
  const value = binding();
  const verified = await captureOfficialLumaTicketQr(pageFixture(), value, {
    decodeQr: async () => CHECK_IN_WITH_KEY,
    observedAt: () => "2026-08-01T15:10:00.000Z",
  });
  const dataDir = fs.mkdtempSync(path.join(os.tmpdir(), "luma-ticket-qr-"));
  const store = createLumaTicketQrStore({ dataDir });
  const refs = await store.record(verified);

  assert.match(refs.ticket_receipt_ref, /^ticket:\/\/dais-local\/[0-9a-f]{64}$/);
  assert.match(refs.artifact_ref, /^object:\/\/sha256\/[0-9a-f]{64}$/);
  assert.deepEqual(await store.readArtifact("dais-local", refs.artifact_ref), png());
  assert.deepEqual(await store.readTicketReceipt("dais-local", refs.ticket_receipt_ref), {
    kind: "ticket",
    provider_id: verified.png_sha256,
    observed_at: "2026-08-01T15:10:00.000Z",
  });
  await assert.rejects(store.readArtifact("tenant-b", refs.artifact_ref), /unavailable/i);
  await assert.rejects(store.record({ ...verified }), /verified QR/i);
});
