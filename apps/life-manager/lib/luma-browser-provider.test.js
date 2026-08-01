"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");

const {
  createLumaBrowserProvider,
} = require("./luma-browser-provider.js");

function eventJson() {
  return [{
    "@type": "Event",
    name: "Tokyo Agent Night",
    startDate: "2026-08-04T19:00:00.000+09:00",
    endDate: "2026-08-04T21:00:00.000+09:00",
    eventAttendanceMode: "https://schema.org/OfflineEventAttendanceMode",
    eventStatus: "https://schema.org/EventScheduled",
    location: { "@type": "Place", name: "Tokyo" },
  }];
}

function contract() {
  return {
    tenant_id: "dais-local",
    event_ref: "luma-event://event/tokyo-agent-night",
    canonical_url: "https://luma.com/tokyo-agent-night",
  };
}

function fixture(controls) {
  const calls = [];
  const page = {
    async screenshot(options) {
      calls.push(["screenshot", options]);
      return Buffer.from("png-fixture");
    },
  };
  return {
    calls,
    page,
    dailyDriver: {
      async withLumaPage(url, task) {
        calls.push(["withLumaPage", url]);
        return task(page);
      },
    },
    readRawDetail: async (seenPage, url) => {
      assert.equal(seenPage, page);
      return { canonicalUrl: url, jsonLd: eventJson(), controls };
    },
    evidenceStore: {
      async record(input) {
        calls.push(["record", input]);
        return {
          external_receipt_ref: "provider-receipt://luma/proof-1",
          artifact_ref: "object://sha256/" + "a".repeat(64),
        };
      },
    },
  };
}

test("inspection separates login, absence, unavailability, and existing registration", async () => {
  const login = fixture(["ログイン", "参加登録"]);
  assert.deepEqual(
    await createLumaBrowserProvider(login).inspectRegistration(contract()),
    { state: "login_required" },
  );

  const available = fixture(["参加登録"]);
  assert.deepEqual(
    await createLumaBrowserProvider(available).inspectRegistration(contract()),
    { state: "absent" },
  );

  const full = fixture(["Sold Out"]);
  assert.deepEqual(
    await createLumaBrowserProvider(full).inspectRegistration(contract()),
    { state: "unavailable", reason: "full" },
  );

  const registered = fixture(["参加予定"]);
  const proof = await createLumaBrowserProvider({
    ...registered,
    now: () => "2026-08-01T10:00:00.000Z",
  }).inspectRegistration(contract());
  assert.deepEqual(proof, {
    state: "registered",
    external_receipt_ref: "provider-receipt://luma/proof-1",
    artifact_ref: "object://sha256/" + "a".repeat(64),
    canonical_url: "https://luma.com/tokyo-agent-night",
  });
  assert.equal(registered.calls.some(([name]) => name === "record"), true);
});

test("submit rechecks the page, performs one bounded action, and records readback evidence", async () => {
  const fx = fixture(["参加登録"]);
  const provider = createLumaBrowserProvider({
    ...fx,
    now: () => "2026-08-01T10:00:00.000Z",
    submitOnPage: async (page, input) => {
      assert.equal(page, fx.page);
      assert.equal(input.event_ref, contract().event_ref);
      fx.calls.push(["submitOnPage"]);
      return { status: "registered", effect_started: true };
    },
  });

  const proof = await provider.submitRegistration(contract());
  assert.equal(proof.canonical_url, contract().canonical_url);
  assert.deepEqual(fx.calls.map(([name]) => name), [
    "withLumaPage",
    "submitOnPage",
    "screenshot",
    "record",
  ]);
});

test("pre-submit form failure remains known while post-click uncertainty is unknown", async () => {
  const known = fixture(["参加登録"]);
  const providerKnown = createLumaBrowserProvider({
    ...known,
    submitOnPage: async () => {
      const error = new Error("required questions unavailable");
      error.unknownEffect = false;
      throw error;
    },
  });
  await assert.rejects(providerKnown.submitRegistration(contract()), (error) => {
    assert.equal(error.unknownEffect, false);
    return true;
  });

  const unknown = fixture(["参加登録"]);
  const providerUnknown = createLumaBrowserProvider({
    ...unknown,
    submitOnPage: async () => ({ status: "unknown", effect_started: true }),
  });
  await assert.rejects(providerUnknown.submitRegistration(contract()), (error) => {
    assert.equal(error.unknownEffect, true);
    return true;
  });
});
