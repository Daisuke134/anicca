"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");

const {
  canonicalKokuchProBinding,
  normalizeKokuchProDetail,
} = require("./connector-kokuchpro-workflow.js");

const NOW = new Date("2026-08-12T00:30:00.000Z");
const KEY = "89a92aac6c9a221ec337481b51c1bbef";
const OCCURRENCE = "3847918";
const ROOT = `https://www.kokuchpro.com/event/${KEY}/`;
const OCCURRENCE_URL = `${ROOT}${OCCURRENCE}/`;

function binding(url = ROOT) {
  return canonicalKokuchProBinding(url);
}

function detail(overrides = {}, url = ROOT) {
  return {
    canonical_url: url,
    event_key: KEY,
    occurrence_id: url === ROOT ? null : OCCURRENCE,
    title: "Tokyo free event",
    starts_at: "2026-08-20T19:00:00+09:00",
    ends_at: "2026-08-20T20:30:00+09:00",
    venue: "豊島区ホール",
    address: "東京都豊島区",
    event_format: "offline",
    fee_scheme: "free",
    registration_status: "open",
    is_full: false,
    tickets: [{ id: "ticket-1", status: "available", price_currency: "JPY", price_minor: 0 }],
    ...overrides,
  };
}

test("KokuchPro canonical binding preserves root and occurrence identity", () => {
  assert.deepEqual(canonicalKokuchProBinding(ROOT), {
    event_ref: `kokuchpro-event://event/${KEY}`,
    canonical_url: ROOT,
  });
  assert.deepEqual(canonicalKokuchProBinding({
    href: OCCURRENCE_URL,
    event_ref: `kokuchpro-event://event/${KEY}/${OCCURRENCE}`,
  }), {
    event_ref: `kokuchpro-event://event/${KEY}/${OCCURRENCE}`,
    canonical_url: OCCURRENCE_URL,
  });
  assert.equal(Object.isFrozen(canonicalKokuchProBinding(ROOT)), true);
});

test("KokuchPro canonical binding rejects non-exact URL and supplied identity variants", () => {
  const variants = [
    `http://www.kokuchpro.com/event/${KEY}/`,
    `https://kokuchpro.com/event/${KEY}/`,
    `https://user:pass@www.kokuchpro.com/event/${KEY}/`,
    `https://www.kokuchpro.com:443/event/${KEY}/`,
    `${ROOT}?source=listing`, `${ROOT}#ticket`, `${ROOT}entry/`, `${ROOT} `,
    `https://www.kokuchpro.com/event/${KEY.toUpperCase()}/`,
    `https://www.kokuchpro.com/event/${KEY.slice(0, 31)}/`,
    `https://www.kokuchpro.com/event/${KEY}/0/`,
    `https://www.kokuchpro.com/event/${KEY}/01/`,
    `https://www.kokuchpro.com/event/${KEY}/abc/`,
  ];
  for (const url of variants) assert.equal(canonicalKokuchProBinding(url), null, url);
  assert.equal(canonicalKokuchProBinding({
    canonical_url: ROOT,
    event_ref: "kokuchpro-event://event/wrong",
  }), null);
  assert.equal(canonicalKokuchProBinding({
    canonical_url: ROOT,
    event_key: "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  }), null);
});

test("KokuchPro normalizes one public free Tokyo offline occurrence", () => {
  const row = normalizeKokuchProDetail({
    binding: binding(OCCURRENCE_URL),
    detail: detail({}, OCCURRENCE_URL),
    now: NOW,
  });
  assert.deepEqual(row, {
    provider: "kokuchpro",
    event_ref: `kokuchpro-event://event/${KEY}/${OCCURRENCE}`,
    canonical_url: OCCURRENCE_URL,
    title: "Tokyo free event",
    starts_at: "2026-08-20T10:00:00.000Z",
    ends_at: "2026-08-20T11:30:00.000Z",
    venue: "豊島区ホール",
    address: "東京都豊島区",
    registration_status: "available",
    ticket_id: "ticket-1",
    ticket_price_status: "free",
    ticket_price_minor: 0,
  });
  assert.equal(Object.isFrozen(row), true);
});

test("KokuchPro identity drift throws generic invalid while eligibility failures return null", () => {
  assert.throws(() => normalizeKokuchProDetail({
    binding: binding(),
    detail: detail({ event_key: "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa" }),
    now: NOW,
  }), /KokuchPro workflow invalid/);
  assert.throws(() => normalizeKokuchProDetail({
    binding: binding(), detail: detail({ canonical_url: OCCURRENCE_URL }), now: NOW,
  }), /KokuchPro workflow invalid/);

  const cases = [
    { fee_scheme: "paid" },
    { tickets: [{ id: "ticket-1", status: "available", price_currency: "JPY", price_minor: 1000 }] },
    { tickets: detail().tickets.concat({ id: "ticket-2", status: "available", price_currency: "JPY", price_minor: 0 }) },
    { event_format: "online" },
    { address: "大阪府大阪市" },
    { registration_status: "closed" },
    { is_full: true },
    { starts_at: "not-a-time" },
    { starts_at: "2026-09-01T19:00:00+09:00" },
  ];
  for (const overrides of cases) {
    assert.equal(normalizeKokuchProDetail({ binding: binding(), detail: detail(overrides), now: NOW }), null);
  }
});

test("KokuchPro requires exact structured free ticket facts despite free text", () => {
  assert.equal(normalizeKokuchProDetail({
    binding: binding(),
    detail: detail({ title: "無料のイベント", description: "参加費無料", fee_scheme: "paid" }),
    now: NOW,
  }), null);
  assert.equal(normalizeKokuchProDetail({
    binding: binding(),
    detail: detail({ title: "無料のイベント", tickets: [{ id: "ticket-1", status: "available", price_currency: "JPY", price_minor: 1 }] }),
    now: NOW,
  }), null);
});

test("KokuchPro uses Tokyo-day window with inclusive start and exclusive day-plus-14 boundary", () => {
  const atStart = detail({ starts_at: "2026-08-11T15:00:00.000Z", ends_at: "2026-08-11T16:00:00.000Z" });
  assert.deepEqual(normalizeKokuchProDetail({ binding: binding(), detail: atStart, now: NOW }).starts_at, "2026-08-11T15:00:00.000Z");
  const atEnd = detail({ starts_at: "2026-08-25T15:00:00.000Z", ends_at: "2026-08-25T16:00:00.000Z" });
  assert.equal(normalizeKokuchProDetail({ binding: binding(), detail: atEnd, now: NOW }), null);
  const endsBeforeStart = detail({ starts_at: "2026-08-20T10:00:00.000Z", ends_at: "2026-08-20T10:00:00.000Z" });
  assert.equal(normalizeKokuchProDetail({ binding: binding(), detail: endsBeforeStart, now: NOW }), null);
});

test("KokuchPro bounds public text, ticket tokens, occurrence ids, and timestamp zones", () => {
  assert.equal(canonicalKokuchProBinding(`${ROOT}${"7".repeat(21)}/`), null);
  const invalidDetails = [
    { title: " title" },
    { title: `${"t".repeat(501)}` },
    { title: "line\nfeed" },
    { venue: `v${"x".repeat(1000)} ` },
    { address: `東京都${"x".repeat(1000)} ` },
    { tickets: [{ id: "ticket/1", status: "available", price_currency: "JPY", price_minor: 0 }] },
    { tickets: [{ id: `ticket-${"x".repeat(126)}`, status: "available", price_currency: "JPY", price_minor: 0 }] },
    { tickets: [{ id: " ticket-1", status: "available", price_currency: "JPY", price_minor: 0 }] },
    { starts_at: "2026-08-20T19:00:00", ends_at: "2026-08-20T20:30:00" },
    { starts_at: "2026-08-20 19:00:00+09:00", ends_at: "2026-08-20T20:30:00+09:00" },
  ];
  for (const overrides of invalidDetails) {
    assert.equal(normalizeKokuchProDetail({ binding: binding(), detail: detail(overrides), now: NOW }), null);
  }
  assert.equal(normalizeKokuchProDetail({
    binding: binding(),
    detail: detail({ venue: "v\u0001enue" }),
    now: NOW,
  }), null);
  assert.equal(normalizeKokuchProDetail({
    binding: binding(),
    detail: detail({ address: "東京都\u0085" }),
    now: NOW,
  }), null);
});
