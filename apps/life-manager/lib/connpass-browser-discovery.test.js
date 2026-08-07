"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");

const {
  normalizeConnpassEventDetail,
  readEventDetail,
} = require("./connpass-browser-discovery.js");

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

test("Connpass browser detail reads public offers controls and price labels", async () => {
  const previousDocument = global.document;
  const previousLocation = global.location;
  const event = {
    "@type": "Event",
    name: "Public event",
    startDate: "2026-08-10T19:00:00+09:00",
    endDate: "2026-08-10T21:00:00+09:00",
    offers: [{ "@type": "Offer", price: "0", priceCurrency: "JPY" }],
    location: { name: "Public venue", address: "Tokyo" },
  };
  const scripts = [{ textContent: JSON.stringify(event) }];
  const controls = [{ innerText: "このイベントに申し込む", value: "", getAttribute() { return ""; } }];
  const priceNodes = [{ textContent: "参加費 無料" }];
  global.location = { href: "https://tokyo-builders.connpass.com/event/401001/" };
  global.document = {
    querySelector(selector) {
      if (selector === 'link[rel="canonical"]') return { href: global.location.href };
      return null;
    },
    querySelectorAll(selector) {
      if (selector === 'script[type="application/ld+json"]') return scripts;
      if (selector === 'button,a[role="button"],a.btn,input[type="submit"]') return controls;
      if (selector === '[class*="price"],[class*="fee"],[class*="amount"],dt,dd') return priceNodes;
      return [];
    },
  };
  const page = { async evaluate(callback) { return callback(); } };
  try {
    const result = await readEventDetail(page);
    assert.deepEqual(result.offers, [{ price: "0", priceCurrency: "JPY" }]);
    assert.deepEqual(result.controls, ["このイベントに申し込む"]);
    assert.deepEqual(result.price_labels, ["参加費 無料"]);
  } finally {
    global.document = previousDocument;
    global.location = previousLocation;
  }
});

test("Connpass browser detail reads the public header title without JSON-LD", async () => {
  const previousDocument = global.document;
  const previousLocation = global.location;
  global.location = { href: "https://openforce.connpass.com/event/399614/" };
  global.document = {
    querySelector(selector) {
      if (selector === 'link[rel="canonical"]') return { href: global.location.href };
      if (selector === ".current_event_title") return { textContent: " 明るい宇宙農村  第31作 " };
      if (selector === "h1") return { textContent: "" };
      return null;
    },
    querySelectorAll() { return []; },
  };
  const page = { async evaluate(callback) { return callback(); } };
  try {
    const result = await readEventDetail(page);
    assert.equal(result.title, "明るい宇宙農村 第31作");
    assert.equal(result.event_ref, "connpass-event://event/399614");
  } finally {
    global.document = previousDocument;
    global.location = previousLocation;
  }
});

test("Connpass detail normalization exposes only the missing public contract field", () => {
  const cases = [
    [raw({ title: "" }), "CONNPASS_DETAIL_TITLE_INVALID_FAILED"],
    [raw({ starts_at: null }), "CONNPASS_DETAIL_START_INVALID_FAILED"],
    [raw({ ends_at: null }), "CONNPASS_DETAIL_END_INVALID_FAILED"],
    [raw({ ends_at: "2026-08-10T18:00:00+09:00" }), "CONNPASS_DETAIL_RANGE_INVALID_FAILED"],
  ];
  for (const [input, code] of cases) {
    assert.throws(() => normalizeConnpassEventDetail(input), (error) => error.code === code);
  }
});
