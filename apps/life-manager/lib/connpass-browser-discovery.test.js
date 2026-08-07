"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");

const { normalizeConnpassEventDetail } = require("./connpass-browser-discovery.js");

function raw(overrides = {}) {
  return {
    event_ref: "connpass-event://event/401001",
    canonical_url: "https://tokyo-builders.connpass.com/event/401001/",
    title: "Public event",
    starts_at: "2026-08-10T19:00:00+09:00",
    ends_at: "2026-08-10T21:00:00+09:00",
    venue_name: "Public venue",
    address: "Tokyo",
    controls: ["このイベントに申し込む"],
    offers: [{ price: "0", priceCurrency: "JPY" }],
    price_labels: ["参加費 無料"],
    ...overrides,
  };
}

test("Connpass detail normalization requires explicit free price and open registration", () => {
  assert.deepEqual(normalizeConnpassEventDetail(raw()), {
    provider: "connpass",
    event_ref: "connpass-event://event/401001",
    canonical_url: "https://tokyo-builders.connpass.com/event/401001/",
    title: "Public event",
    starts_at: "2026-08-10T10:00:00.000Z",
    ends_at: "2026-08-10T12:00:00.000Z",
    venue_name: "Public venue",
    venue_address: "Tokyo",
    registration_status: "available",
    ticket_price_status: "free",
    ticket_price_minor: 0,
  });
  assert.equal(normalizeConnpassEventDetail(raw({ offers: [], price_labels: [] })).ticket_price_status, "unknown");
  assert.equal(normalizeConnpassEventDetail(raw({ controls: ["受付終了"] })).registration_status, "closed");
});
