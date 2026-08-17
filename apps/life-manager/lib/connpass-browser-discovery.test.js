"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");

const {
  normalizeConnpassEventDetail,
  readCalendarBindings,
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

function calendarPage(anchors) {
  return {
    async evaluate(callback) {
      const previousDocument = global.document;
      const previousLocation = global.location;
      global.location = { href: "https://connpass.com/calendar/?ym=202608&prefectures=13" };
      global.document = {
        querySelectorAll(selector) {
          return selector === 'a[href*="/event/"]' ? anchors : [];
        },
      };
      try { return await callback(); }
      finally {
        global.document = previousDocument;
        global.location = previousLocation;
      }
    },
  };
}

test("Connpass calendar bindings read the date from the hidden `.tooltip` text via textContent (innerText hides it)", async () => {
  // Real connpass.com/calendar/?ym=202608&prefectures=13 markup: each row is
  // `<li>・<a href="...">Title</a><span class="tooltip">...日時: 2026/08/01 05:30〜...</span></li>`
  // and connpass.css sets `.tooltip{display:none}`, so a real browser's
  // `li.innerText` omits the date while `li.textContent` still contains it.
  const li = {
    innerText: "・IT系勉強会【第1507回】朝からもくもく",
    textContent: "・IT系勉強会【第1507回】朝からもくもく IT系勉強会【第1507回】朝からもくもく会 "
      + "日時: 2026/08/01 05:30〜 会場: (場所未定) 人数: 2/5人",
  };
  const anchor = {
    href: "https://connpass.com/event/401581/",
    closest(tag) { return tag === "li" ? li : null; },
  };
  const rows = await readCalendarBindings(calendarPage([anchor]));
  assert.deepEqual(rows, [{
    event_ref: "connpass-event://event/401581",
    canonical_url: "https://connpass.com/event/401581/",
    calendar_date: "2026-08-01",
  }]);
});

test("Connpass calendar bindings return a null date when the anchor has no enclosing li", async () => {
  const anchor = {
    href: "https://openforce.connpass.com/event/399614/",
    closest() { return null; },
  };
  const rows = await readCalendarBindings(calendarPage([anchor]));
  assert.deepEqual(rows, [{
    event_ref: "connpass-event://event/399614",
    canonical_url: "https://openforce.connpass.com/event/399614/",
    calendar_date: null,
  }]);
});

test("Connpass calendar bindings skip anchors whose href is not an event path", async () => {
  const anchor = { href: "https://connpass.com/calendar/?ym=202609&prefectures=13", closest() { return null; } };
  const rows = await readCalendarBindings(calendarPage([anchor]));
  assert.deepEqual(rows, []);
});

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

// Real `<p class="join_fee">` text captured 2026-08-17 from live
// connpass.com/event/<id>/ pages (matches `[class*="fee"]` in readEventDetail
// so it already reaches price_labels without any selector change):
//   free, single tier   -> event/399995, event/403863, event/392421: "無料"
//   paid, single tier    -> event/390309: "2000円（前払い）"
//   mixed tiers          -> event/391962: ["無料", "2000円（会場払い）"]
//                           ("管理者"=staff tier free, "一般枠"=general
//                           tier costs money — a real registrant pays)
test("Connpass price recognizes the real single-tier free join_fee wording", () => {
  const result = normalizeConnpassEventDetail(raw({ offers: [], price_labels: ["無料"] }));
  assert.equal(result.ticket_price_status, "free");
  assert.equal(result.ticket_price_minor, 0);
});

test("Connpass price does NOT report free for a real single-tier paid event", () => {
  const result = normalizeConnpassEventDetail(raw({ offers: [], price_labels: ["2000円（前払い）"] }));
  assert.equal(result.ticket_price_status, "unknown");
  assert.equal(result.ticket_price_minor, null);
});

test("Connpass price does NOT report free when one real ticket tier is free and another costs money", () => {
  const result = normalizeConnpassEventDetail(raw({
    offers: [],
    price_labels: ["無料", "2000円（会場払い）"],
  }));
  assert.equal(result.ticket_price_status, "unknown");
  assert.equal(result.ticket_price_minor, null);
});

test("Connpass price still reports free when every real ticket tier is free", () => {
  const result = normalizeConnpassEventDetail(raw({ offers: [], price_labels: ["無料", "無料"] }));
  assert.equal(result.ticket_price_status, "free");
});

// Real anonymous-session strings captured 2026-08-17 from 10 live Tokyo
// connpass.com event pages: connpass swaps the join button
// (id="ParticipateButton") to a login prompt when the browsing session
// isn't authenticated. Neither string may ever be read as an open
// registration — a false "available" would try to register into a login
// wall instead of the real join flow.
test("Connpass registration status does not treat the real anonymous-session login prompt as available", () => {
  assert.equal(
    normalizeConnpassEventDetail(raw({ controls: ["ログイン・会員登録"] })).registration_status,
    "unknown",
  );
  assert.equal(
    normalizeConnpassEventDetail(raw({ controls: ["イベントに申し込むには"] })).registration_status,
    "unknown",
  );
});

// The 4 exact strings connpass renders on the join button for an
// authenticated, eligible user (same list `submitConnpassOnPage` targets via
// getByRole so the direct-submit flow and this discovery check stay in
// sync) must all still be recognized as open.
test("Connpass registration status recognizes every real open-button wording", () => {
  for (const label of ["このイベントに申し込む", "イベントに申し込む", "参加申し込み", "申し込む"]) {
    assert.equal(normalizeConnpassEventDetail(raw({ controls: [label] })).registration_status, "available");
  }
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

test("Connpass browser detail reads hCalendar dtstart when JSON-LD startDate is absent", async () => {
  const previousDocument = global.document;
  const previousLocation = global.location;
  global.location = { href: "https://openforce.connpass.com/event/399614/" };
  global.document = {
    querySelector(selector) {
      if (selector === 'link[rel="canonical"]') return { href: global.location.href };
      if (selector === ".current_event_title") return { textContent: " Public event " };
      if (selector === ".dtstart .value-title") {
        return { getAttribute(name) { return name === "title" ? "2026-07-31T21:00:00Z" : null; } };
      }
      if (selector === "h1") return { textContent: "" };
      return null;
    },
    querySelectorAll() { return []; },
  };
  const page = { async evaluate(callback) { return callback(); } };
  try {
    const result = await readEventDetail(page);
    assert.equal(result.starts_at, "2026-07-31T21:00:00Z");
  } finally {
    global.document = previousDocument;
    global.location = previousLocation;
  }
});

test("Connpass browser detail leaves starts_at null when hCalendar dtstart is absent", async () => {
  const previousDocument = global.document;
  const previousLocation = global.location;
  global.location = { href: "https://openforce.connpass.com/event/399614/" };
  global.document = {
    querySelector(selector) {
      if (selector === 'link[rel="canonical"]') return { href: global.location.href };
      if (selector === ".current_event_title") return { textContent: " Public event " };
      if (selector === "h1") return { textContent: "" };
      return null;
    },
    querySelectorAll() { return []; },
  };
  const page = { async evaluate(callback) { return callback(); } };
  try {
    const result = await readEventDetail(page);
    assert.equal(result.starts_at, null);
  } finally {
    global.document = previousDocument;
    global.location = previousLocation;
  }
});

test("Connpass browser detail reads hCalendar dtend when JSON-LD endDate is absent", async () => {
  const previousDocument = global.document;
  const previousLocation = global.location;
  global.location = { href: "https://openforce.connpass.com/event/399614/" };
  global.document = {
    querySelector(selector) {
      if (selector === 'link[rel="canonical"]') return { href: global.location.href };
      if (selector === ".current_event_title") return { textContent: " Public event " };
      if (selector === ".dtstart .value-title") {
        return { getAttribute(name) { return name === "title" ? "2026-07-31T21:00:00Z" : null; } };
      }
      if (selector === ".dtend .value-title") {
        return { getAttribute(name) { return name === "title" ? "2026-07-31T23:30:00Z" : null; } };
      }
      if (selector === "h1") return { textContent: "" };
      return null;
    },
    querySelectorAll() { return []; },
  };
  const page = { async evaluate(callback) { return callback(); } };
  try {
    const result = await readEventDetail(page);
    assert.equal(result.ends_at, "2026-07-31T23:30:00Z");
  } finally {
    global.document = previousDocument;
    global.location = previousLocation;
  }
});

test("Connpass browser detail leaves ends_at null when hCalendar dtend is absent", async () => {
  const previousDocument = global.document;
  const previousLocation = global.location;
  global.location = { href: "https://openforce.connpass.com/event/399614/" };
  global.document = {
    querySelector(selector) {
      if (selector === 'link[rel="canonical"]') return { href: global.location.href };
      if (selector === ".current_event_title") return { textContent: " Public event " };
      if (selector === ".dtstart .value-title") {
        return { getAttribute(name) { return name === "title" ? "2026-07-31T21:00:00Z" : null; } };
      }
      if (selector === "h1") return { textContent: "" };
      return null;
    },
    querySelectorAll() { return []; },
  };
  const page = { async evaluate(callback) { return callback(); } };
  try {
    const result = await readEventDetail(page);
    assert.equal(result.ends_at, null);
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
