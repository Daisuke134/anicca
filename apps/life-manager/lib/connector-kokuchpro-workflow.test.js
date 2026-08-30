"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");

const {
  canonicalKokuchProBinding,
  createKokuchProDiscoveryWorkflow,
  normalizeKokuchProDetail,
} = require("./connector-kokuchpro-workflow.js");

const NOW = new Date("2026-08-12T00:30:00.000Z");
const KEY = "ab".repeat(16);
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

test("KokuchPro accepts a colonless timezone offset as the same instant", () => {
  const compact = normalizeKokuchProDetail({
    binding: binding(),
    detail: detail({
      starts_at: "2026-08-31T18:00:00+0900",
      ends_at: "2026-08-31T20:30:00+0900",
    }),
    now: new Date("2026-08-20T00:30:00.000Z"),
  });
  const colon = normalizeKokuchProDetail({
    binding: binding(),
    detail: detail({
      starts_at: "2026-08-31T18:00:00+09:00",
      ends_at: "2026-08-31T20:30:00+09:00",
    }),
    now: new Date("2026-08-20T00:30:00.000Z"),
  });

  assert.ok(compact);
  assert.ok(colon);
  assert.deepEqual([compact.starts_at, compact.ends_at], [colon.starts_at, colon.ends_at]);
  assert.deepEqual([compact.starts_at, compact.ends_at], [
    "2026-08-31T09:00:00.000Z",
    "2026-08-31T11:30:00.000Z",
  ]);
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

test("KokuchPro rejects conflicting URL and identity aliases", () => {
  assert.equal(canonicalKokuchProBinding({ canonical_url: ROOT, href: OCCURRENCE_URL }), null);
  assert.equal(canonicalKokuchProBinding({ canonical_url: ROOT, url: ROOT, href: ROOT }).canonical_url, ROOT);
  assert.equal(canonicalKokuchProBinding({
    canonical_url: ROOT,
    event_ref: `kokuchpro-event://event/${KEY}`,
    event_key: "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  }), null);
  assert.equal(canonicalKokuchProBinding({
    canonical_url: OCCURRENCE_URL,
    event_ref: `kokuchpro-event://event/${KEY}/${OCCURRENCE}`,
    event_key: KEY,
    occurrence_id: "1",
  }), null);
  assert.throws(() => normalizeKokuchProDetail({
    binding: binding(), detail: detail({ event_ref: "kokuchpro-event://event/wrong" }), now: NOW,
  }), /KokuchPro workflow invalid/);
  assert.throws(() => normalizeKokuchProDetail({
    binding: binding(), detail: detail({ canonical_url: ROOT, href: OCCURRENCE_URL }), now: NOW,
  }), /KokuchPro workflow invalid/);
});

test("KokuchPro requires a Japanese Tokyo prefecture address", () => {
  assert.equal(normalizeKokuchProDetail({
    binding: binding(), detail: detail({ address: "千葉県浦安市 Tokyo venue" }), now: NOW,
  }), null);
  assert.equal(normalizeKokuchProDetail({
    binding: binding(), detail: detail({ address: "東京都豊島区" }), now: NOW,
  }).address, "東京都豊島区");
});

test("KokuchPro rejects semantically invalid ISO calendar dates", () => {
  const februaryNow = new Date("2026-02-20T00:30:00.000Z");
  assert.equal(normalizeKokuchProDetail({
    binding: binding(),
    detail: detail({ starts_at: "2026-02-30T19:00:00+09:00", ends_at: "2026-02-30T20:00:00+09:00" }),
    now: februaryNow,
  }), null);
  assert.equal(normalizeKokuchProDetail({
    binding: binding(),
    detail: detail({ starts_at: "2026-02-20T24:00:00+09:00", ends_at: "2026-02-20T25:00:00+09:00" }),
    now: februaryNow,
  }), null);
});

const LIST_URL = "https://www.kokuchpro.com/s/area-%E6%9D%B1%E4%BA%AC%E9%83%BD/charge-0/?et=0&start_date=2026-08-12&end_date=2026-08-26&enabled=1&sort=date";
const LOGIN_URL = "https://www.kokuchpro.com/auth/login/";
const ENTRY_URL = `${ROOT}entry/`;

function jsonLdDetail(url = ROOT, overrides = {}) {
  const occurrence = url === ROOT ? null : OCCURRENCE;
  return {
    jsonld: {
      "@type": "Event",
      url,
      name: "Tokyo free event",
      startDate: "2026-08-20T19:00:00+09:00",
      endDate: "2026-08-20T20:30:00+09:00",
      eventAttendanceMode: "https://schema.org/OfflineEventAttendanceMode",
      location: { "@type": "Place", name: "豊島区ホール", address: { addressLocality: "東京都豊島区" } },
      offers: { "@type": "Offer", url, price: 0, priceCurrency: "JPY", availability: "https://schema.org/InStock" },
      ...overrides.event,
    },
    fee_rows: [{ label: "料金制度", value: "無料イベント" }],
    ticket_rows: [{ id: "ticket-1", label: "無料", status: "募集中" }],
    canonical_url: url,
    event_key: KEY,
    occurrence_id: occurrence,
    ...overrides,
  };
}

function workflowPage(url = "") {
  return {
    current: url,
    calls: [],
    url() { return this.current; },
    async goto(nextUrl) { this.calls.push(["goto", nextUrl]); this.current = nextUrl; },
  };
}

function defaultEvaluatePage({ listingRows = [], details = {} } = {}) {
  const page = workflowPage();
  page.evaluate = async (_fn, argument) => {
    page.calls.push(["evaluate", page.current]);
    if (page.current === LIST_URL) return listingRows.map((row) => [row && (row.href || row.canonical_url || row.url || row)]);
    return details[argument || page.current];
  };
  return page;
}

function readbackPage(url, facts, { evaluateError = false, driftTo = null } = {}) {
  const page = workflowPage(url);
  page.evaluate = async () => {
    if (evaluateError) throw new Error("evaluate");
    if (driftTo) page.current = driftTo;
    return facts;
  };
  return page;
}

function scopedListingPage(inScopeCount = 40, outsideCount = 5) {
  const cardLinks = Array.from({ length: inScopeCount }, (_, index) => [`https://www.kokuchpro.com/event/${String(index + 1).padStart(32, "a")}/`]);
  if (inScopeCount === 40) {
    cardLinks[38] = Array.from({ length: 5 }, (_, index) => `https://www.kokuchpro.com/event/${String(index + 39).padStart(32, "c")}/`);
    cardLinks[39] = Array.from({ length: 5 }, (_, index) => `https://www.kokuchpro.com/event/${String(index + 44).padStart(32, "d")}/`);
  }
  const inside = cardLinks.flat();
  const outside = Array.from({ length: outsideCount }, (_, index) => `https://www.kokuchpro.com/event/${String(index + 101).padStart(32, "b")}/`);
  const anchor = (href) => ({ href, getAttribute() { return href; } });
  const cards = cardLinks.map((links) => [...links, links[0]]);
  const page = workflowPage();
  page.evaluate = async (fn) => {
    const previous = global.document;
    global.document = { querySelectorAll(selector) {
      if (selector === ".event_list .event_item") return cards.map((links) => ({ querySelectorAll() { return links.map(anchor); } }));
      return [...inside.flatMap((href) => [anchor(href), anchor(href)]), ...outside.map(anchor)];
    } };
    try { return await fn(); } finally { if (previous === undefined) delete global.document; else global.document = previous; }
  };
  return page;
}

function cardResultPage(cards) {
  const anchor = (href) => ({ href, getAttribute() { return href; } });
  const page = workflowPage();
  page.evaluate = async (fn) => {
    const previous = global.document;
    global.document = { querySelectorAll() { return cards.map((links) => links && { querySelectorAll(selector) { const selected = selector === 'a[href^="https://www.kokuchpro.com/event/"]' ? links.filter((href) => String(href).startsWith("https://www.kokuchpro.com/event/")) : links; return selected.map(anchor); } }); } };
    try { return await fn(); } finally { if (previous === undefined) delete global.document; else global.document = previous; }
  };
  return page;
}

test("KokuchPro listing scopes to first-page result items and ignores outside anchors", async () => {
  const audits = [];
  const page = scopedListingPage(40, 5);
  const workflow = createKokuchProDiscoveryWorkflow({
    now: () => new Date(NOW),
    readEventDetail: async (ownedPage, url) => { ownedPage.current = url; return null; },
    onDiscoveryAudit: async (audit) => audits.push(audit),
  });
  assert.deepEqual(await workflow.discoverCandidates({ page, calendar: [] }), []);
  assert.deepEqual(audits, [{ discovered_count: 48, within_window_count: 0, eligible_count: 0, calendar_free_count: 0, selected_count: 0 }]);
  await assert.rejects(createKokuchProDiscoveryWorkflow({
    now: () => new Date(NOW),
    readEventDetail: async (ownedPage, url) => { ownedPage.current = url; return null; },
  }).discoverCandidates({ page: scopedListingPage(41, 1), calendar: [] }), (error) => error.code === "KOKUCHPRO_LISTING_RESULT_CONTRACT_FAILED");
  const unique = Array.from({ length: 21 }, (_, index) => `https://www.kokuchpro.com/event/${String(index + 201).padStart(32, "e")}/`);
  for (const cards of [[], [null], [unique]]) {
    await assert.rejects(createKokuchProDiscoveryWorkflow({ now: () => new Date(NOW), readEventDetail: async () => null }).discoverCandidates({ page: cardResultPage(cards), calendar: [] }), (error) => error.code === "KOKUCHPRO_LISTING_RESULT_CONTRACT_FAILED");
  }
  const tooManyInjected = createKokuchProDiscoveryWorkflow({ now: () => new Date(NOW), readListingBindings: async () => Array.from({ length: 801 }, (_, index) => ({ canonical_url: `https://www.kokuchpro.com/event/${String(index + 301).padStart(32, "f")}/` })) });
  await assert.rejects(tooManyInjected.discoverCandidates({ page: {}, calendar: [] }), (error) => error.code === "KOKUCHPRO_LISTING_RESULT_CONTRACT_FAILED");
});

test("KokuchPro listing ignores ordinary card anchors while bounding event-like raw and unique links", async () => {
  const events = Array.from({ length: 5 }, (_, index) => `https://www.kokuchpro.com/event/${String(index + 501).padStart(32, "a")}/`);
  const eventLinks = [events[0], events[0], events[1], events[1], events[2], events[3], events[4]];
  const ordinary = Array.from({ length: 16 }, (_, index) => `https://www.kokuchpro.com/help/${index}`);
  const audits = [];
  const workflow = createKokuchProDiscoveryWorkflow({
    now: () => new Date(NOW),
    readEventDetail: async (ownedPage, url) => { ownedPage.current = url; return null; },
    onDiscoveryAudit: async (audit) => audits.push(audit),
  });
  assert.deepEqual(await workflow.discoverCandidates({ page: cardResultPage([[...ordinary, ...eventLinks]]), calendar: [] }), []);
  assert.deepEqual(audits, [{ discovered_count: 5, within_window_count: 0, eligible_count: 0, calendar_free_count: 0, selected_count: 0 }]);

  const tooManyUnique = Array.from({ length: 21 }, (_, index) => `https://www.kokuchpro.com/event/${String(index + 601).padStart(32, "b")}/`);
  await assert.rejects(createKokuchProDiscoveryWorkflow({ now: () => new Date(NOW), readEventDetail: async () => null }).discoverCandidates({ page: cardResultPage([tooManyUnique]), calendar: [] }), (error) => error.code === "KOKUCHPRO_LISTING_RESULT_CONTRACT_FAILED");
  const tooManyRaw = Array.from({ length: 101 }, (_, index) => events[index % events.length]);
  await assert.rejects(createKokuchProDiscoveryWorkflow({ now: () => new Date(NOW), readEventDetail: async () => null }).discoverCandidates({ page: cardResultPage([tooManyRaw]), calendar: [] }), (error) => error.code === "KOKUCHPRO_LISTING_RESULT_CONTRACT_FAILED");
});

test("KokuchPro default listing is exact, same-page, canonical-only, and bounded", async () => {
  const first = ROOT;
  const second = `${ROOT}${OCCURRENCE}/`;
  const page = defaultEvaluatePage({ listingRows: [
    { href: first }, { href: `${first}?tracking=1` }, { href: second }, { href: second },
    { href: "https://kokuchpro.com/event/aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa/" },
  ], details: { [first]: jsonLdDetail(first), [second]: jsonLdDetail(second) } });
  const result = await createKokuchProDiscoveryWorkflow({ now: () => new Date(NOW) }).discoverCandidates({ page, calendar: [] });
  assert.deepEqual(result.map((row) => row.canonical_url), [first, second]);
  assert.deepEqual(page.calls.slice(0, 4), [["goto", LIST_URL], ["evaluate", LIST_URL], ["goto", first], ["evaluate", first]]);
  const over = defaultEvaluatePage({ listingRows: Array.from({ length: 41 }, (_, index) => ({ href: `https://www.kokuchpro.com/event/${String(index + 1).padStart(32, "a")}/` })) });
  await assert.rejects(createKokuchProDiscoveryWorkflow({ now: () => new Date(NOW) }).discoverCandidates({ page: over, calendar: [] }), (error) => error.code === "KOKUCHPRO_LISTING_RESULT_CONTRACT_FAILED");
});

test("KokuchPro default readers reject a same-page redirect", async () => {
  const page = defaultEvaluatePage({ listingRows: [{ href: ROOT }], details: { [ROOT]: jsonLdDetail(ROOT) } });
  const originalGoto = page.goto;
  page.goto = async function redirected(url) {
    await originalGoto.call(this, url);
    if (url === LIST_URL) this.current = "https://www.kokuchpro.com/login/";
  };
  await assert.rejects(createKokuchProDiscoveryWorkflow({ now: () => new Date(NOW) }).discoverCandidates({ page, calendar: [] }), (error) => error.code === "KOKUCHPRO_LISTING_NAVIGATION_FAILED");
});

test("KokuchPro default detail requires one exact offline free Event and explicit ticket table", async () => {
  const page = defaultEvaluatePage({ listingRows: [{ href: ROOT }], details: { [ROOT]: jsonLdDetail(ROOT) } });
  const workflow = createKokuchProDiscoveryWorkflow({ now: () => new Date(NOW) });
  const result = await workflow.discoverCandidates({ page, calendar: [] });
  assert.deepEqual(Object.keys(result[0]).sort(), [
    "address", "canonical_url", "ends_at", "event_ref", "provider", "registration_status",
    "starts_at", "ticket_id", "ticket_price_minor", "ticket_price_status", "title", "venue",
  ]);
  assert.equal(JSON.stringify(result).includes("fee_rows"), false);
  const stringAddressPage = defaultEvaluatePage({ listingRows: [{ href: ROOT }], details: { [ROOT]: jsonLdDetail(ROOT, { event: { location: { name: "豊島区ホール", address: "東京都豊島区" } } }) } });
  assert.equal((await createKokuchProDiscoveryWorkflow({ now: () => new Date(NOW) }).discoverCandidates({ page: stringAddressPage, calendar: [] })).length, 1);
  const identityPage = defaultEvaluatePage({ listingRows: [{ href: ROOT }], details: { [ROOT]: jsonLdDetail(ROOT, { event: { url: `${ROOT}?redirect=1` } }) } });
  await assert.rejects(createKokuchProDiscoveryWorkflow({ now: () => new Date(NOW) }).discoverCandidates({ page: identityPage, calendar: [] }), (error) => error.code === "KOKUCHPRO_DETAIL_IDENTITY_MISMATCH_FAILED");
  for (const [name, overrides] of [
    ["duplicate-events", { jsonld: [jsonLdDetail(ROOT).jsonld, jsonLdDetail(ROOT).jsonld] }],
    ["online", { event: { eventAttendanceMode: "https://schema.org/OnlineEventAttendanceMode" } }],
    ["paid", { event: { offers: { "@type": "Offer", url: ROOT, price: 1000, priceCurrency: "JPY", availability: "https://schema.org/InStock" } } }],
    ["wrong-offer-type", { event: { offers: { "@type": "Thing", url: ROOT, price: 0, priceCurrency: "JPY", availability: "https://schema.org/InStock" } } }],
    ["fee", { fee_rows: [{ label: "料金制度", value: "有料イベント" }] }],
    ["ticket", { ticket_rows: [{ id: "ticket-1", label: "無料", status: "受付終了" }] }],
    ["duplicate-ticket", { ticket_rows: [{ id: "ticket-1", label: "無料", status: "募集中" }, { id: "ticket-2", label: "無料", status: "募集中" }] }],
    ["canonical-action", { availability_values: ["1"], entry_actions: [ROOT] }],
    ["action-count", { availability_values: ["1", "1"], entry_actions: [`${ROOT}entry/`] }],
    ["availability-count", { availability_values: ["1"], entry_actions: [`${ROOT}entry/`, `${ROOT}entry/`] }],
    ["paired-action", { availability_values: ["1", "1"], entry_actions: [`${ROOT}entry/`, ROOT] }],
  ]) {
    const badPage = defaultEvaluatePage({ listingRows: [{ href: ROOT }], details: { [ROOT]: jsonLdDetail(ROOT, overrides) } });
    const badResult = await createKokuchProDiscoveryWorkflow({ now: () => new Date(NOW) }).discoverCandidates({ page: badPage, calendar: [] });
    assert.deepEqual(badResult, [], name);
  }
});

test("KokuchPro rejects contradictory structured Tokyo address components", async () => {
  const cases = [
    { addressRegion: "東京都", addressLocality: "大阪市" },
    { name: "東京都港区", addressRegion: "大阪府", addressLocality: "港区" },
  ];
  for (const address of cases) {
    const page = defaultEvaluatePage({ listingRows: [{ href: ROOT }], details: { [ROOT]: jsonLdDetail(ROOT, { event: { location: { name: "会場", address } } }) } });
    assert.deepEqual(await createKokuchProDiscoveryWorkflow({ now: () => new Date(NOW) }).discoverCandidates({ page, calendar: [] }), []);
  }
});

test("KokuchPro maps coded goto and URL assertion failures to navigation stages", async () => {
  const failure = (code) => Object.assign(new Error("timeout"), { code });
  for (const mode of ["goto", "url"]) {
    const listingPage = {
      async goto() { if (mode === "goto") throw failure("ETIMEDOUT"); },
      async evaluate() { return []; },
      url() { if (mode === "url") throw failure("ETIMEDOUT"); return LIST_URL; },
    };
    const listingWorkflow = createKokuchProDiscoveryWorkflow({ now: () => new Date(NOW) });
    await assert.rejects(listingWorkflow.discoverCandidates({ page: listingPage, calendar: [] }), (error) => error.code === "KOKUCHPRO_LISTING_NAVIGATION_FAILED");

    const detailPage = {
      async goto() { if (mode === "goto") throw failure("ETIMEDOUT"); },
      async evaluate() { return null; },
      url() { if (mode === "url") throw failure("ETIMEDOUT"); return ROOT; },
    };
    const detailWorkflow = createKokuchProDiscoveryWorkflow({
      now: () => new Date(NOW),
      readListingBindings: async () => [canonicalKokuchProBinding(ROOT)],
    });
    await assert.rejects(detailWorkflow.discoverCandidates({ page: detailPage, calendar: [] }), (error) => error.code === "KOKUCHPRO_DETAIL_NAVIGATION_FAILED");
  }
});

test("KokuchPro default detail derives one safe ticket id from duplicate availability forms and binds entry action identity", async () => {
  const good = jsonLdDetail(ROOT, { availability_values: ["1", "1"], entry_actions: [`${ROOT}entry/`, `${ROOT}entry/`] });
  const goodPage = defaultEvaluatePage({ listingRows: [{ href: ROOT }], details: { [ROOT]: good } });
  const goodResult = await createKokuchProDiscoveryWorkflow({ now: () => new Date(NOW) }).discoverCandidates({ page: goodPage, calendar: [] });
  assert.equal(goodResult[0].ticket_id, "1");
  for (const [name, overrides] of [
    ["zero", { availability_values: ["0", "0"] }],
    ["mismatch", { availability_values: ["1", "2"] }],
    ["unsafe", { availability_values: ["javascript:alert(1)"] }],
    ["entry identity", { availability_values: ["1", "1"], entry_actions: ["https://www.kokuchpro.com/event/aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa/entry/"] }],
  ]) {
    const page = defaultEvaluatePage({ listingRows: [{ href: ROOT }], details: { [ROOT]: jsonLdDetail(ROOT, overrides) } });
    assert.deepEqual(await createKokuchProDiscoveryWorkflow({ now: () => new Date(NOW) }).discoverCandidates({ page, calendar: [] }), [], name);
  }
});

test("KokuchPro workflow gates Calendar once, orders exact coverage first, and freezes audit counts", async () => {
  const first = canonicalKokuchProBinding(ROOT);
  const secondUrl = OCCURRENCE_URL;
  const second = canonicalKokuchProBinding(secondUrl);
  const reads = [];
  const audits = [];
  let calendarCalls = 0;
  const workflow = createKokuchProDiscoveryWorkflow({
    now: () => new Date(NOW),
    readListingBindings: async () => [first, first, second, { href: "https://evil.example/event/1" }],
    readEventDetail: async (_page, url) => { reads.push(url); return detail({}, url); },
    isCalendarFree: async () => { calendarCalls += 1; return true; },
    onDiscoveryAudit: async (audit) => audits.push(audit),
  });
  const result = await workflow.discoverCandidates({ page: {}, calendar: [] });
  assert.deepEqual(reads, [ROOT, secondUrl]);
  assert.equal(calendarCalls, 2);
  assert.deepEqual(result.map((row) => row.canonical_url), [ROOT, secondUrl]);
  assert.deepEqual(audits, [{ discovered_count: 2, within_window_count: 2, eligible_count: 2, calendar_free_count: 2, selected_count: 2 }]);
  assert.equal(Object.isFrozen(audits[0]), true);
});

test("KokuchPro audit counts valid in-window timing before remaining eligibility", async () => {
  const first = canonicalKokuchProBinding(ROOT);
  const second = canonicalKokuchProBinding(OCCURRENCE_URL);
  const audits = [];
  const workflow = createKokuchProDiscoveryWorkflow({
    now: () => new Date(NOW),
    readListingBindings: async () => [first, second],
    readEventDetail: async (_page, url) => url === ROOT
      ? detail({ fee_scheme: "paid" })
      : detail({ starts_at: "2026-09-01T19:00:00+09:00", ends_at: "2026-09-01T20:00:00+09:00" }, OCCURRENCE_URL),
    onDiscoveryAudit: async (audit) => audits.push(audit),
  });
  assert.deepEqual(await workflow.discoverCandidates({ page: {}, calendar: [] }), []);
  assert.deepEqual(audits, [{ discovered_count: 2, within_window_count: 1, eligible_count: 0, calendar_free_count: 0, selected_count: 0 }]);
});

test("KokuchPro rejects a hidden Event nested in a top-level JSON-LD array graph", async () => {
  const canonical = jsonLdDetail(ROOT).jsonld;
  const page = defaultEvaluatePage({ listingRows: [{ href: ROOT }], details: {
    [ROOT]: jsonLdDetail(ROOT, { jsonld: [{ "@graph": [canonical] }, canonical] }),
  } });
  assert.deepEqual(await createKokuchProDiscoveryWorkflow({ now: () => new Date(NOW) }).discoverCandidates({ page, calendar: [] }), []);
});

test("KokuchPro readback classifies exact absent and auth-required boundaries", async () => {
  const candidate = normalizeKokuchProDetail({ binding: binding(), detail: detail(), now: NOW });
  const workflow = createKokuchProDiscoveryWorkflow();
  for (const entry_forms of [
    [{ action: ENTRY_URL, method: "POST" }],
    [{ action: ENTRY_URL, method: "POST" }, { action: ENTRY_URL, method: "POST" }],
  ]) {
    assert.deepEqual(await workflow.readProviderState({ page: readbackPage(ROOT, { entry_forms }), candidate }), { status: "absent" });
  }
  const entryPath = new URL(ENTRY_URL).pathname;
  const loginPage = readbackPage(`${LOGIN_URL}?continue=${encodeURIComponent(entryPath)}`, {
    password_count: 1,
    login_forms: [{ action: LOGIN_URL, method: "POST" }],
  });
  assert.deepEqual(await workflow.readProviderState({ page: loginPage, candidate }), { status: "auth_required" });
});

test("KokuchPro readback accepts canonical registration evidence and a same-event detail page", async () => {
  const candidate = normalizeKokuchProDetail({ binding: binding(), detail: detail(), now: NOW });
  const canonicalPage = readbackPage(ROOT, {
    entry_forms: [],
    password_count: 0,
    login_forms: [],
    registration_links: [{ href: ENTRY_URL, text: "申込情報を確認する", visible: true }],
  });
  const detailUrl = `${ROOT}entry/detail/`;
  const detailPage = readbackPage(detailUrl, {
    entry_forms: [],
    password_count: 0,
    login_forms: [],
    detail_headings: [{ text: "申込詳細", visible: true }],
    canonical_links: [{ href: ROOT, text: "イベント", visible: true }],
  });
  const workflow = createKokuchProDiscoveryWorkflow();

  assert.deepEqual(await workflow.readProviderState({ page: canonicalPage, candidate }), { status: "registered" });
  assert.deepEqual(await workflow.readProviderState({ page: detailPage, candidate }), { status: "registered" });
});

test("KokuchPro readback rejects ambiguous or foreign registration evidence", async () => {
  const candidate = normalizeKokuchProDetail({ binding: binding(), detail: detail(), now: NOW });
  const workflow = createKokuchProDiscoveryWorkflow();
  const cases = [
    [ROOT, {
      entry_forms: [], password_count: 0, login_forms: [],
      registration_links: [
        { href: ENTRY_URL, text: "申込情報を確認する", visible: true },
        { href: ENTRY_URL, text: "申込情報を確認する", visible: true },
      ],
    }],
    [ROOT, {
      entry_forms: [], password_count: 0, login_forms: [],
      registration_links: [{ href: "https://evil.example/event/entry/", text: "申込情報を確認する", visible: true }],
    }],
    [`${ROOT}entry/detail/`, {
      entry_forms: [], password_count: 0, login_forms: [],
      detail_headings: [{ text: "申込詳細", visible: true }],
      canonical_links: [{ href: `${ROOT}?foreign=1`, text: "イベント", visible: true }],
    }],
    [`${ROOT}entry/detail/`, {
      entry_forms: [], password_count: 0, login_forms: [],
      detail_headings: [{ text: "申込詳細", visible: true }, { text: "申込詳細", visible: true }],
      canonical_links: [{ href: ROOT, text: "イベント", visible: true }],
    }],
    [`${ROOT}entry/detail/?query=1`, {
      entry_forms: [], password_count: 0, login_forms: [],
      detail_headings: [{ text: "申込詳細", visible: true }],
      canonical_links: [{ href: ROOT, text: "イベント", visible: true }],
    }],
  ];
  for (const [url, facts] of cases) {
    assert.deepEqual(await workflow.readProviderState({ page: readbackPage(url, facts), candidate }), { status: "unavailable" }, url);
  }
});

test("KokuchPro readback fails closed for URL, candidate, DOM, and evaluation ambiguity", async () => {
  const candidate = normalizeKokuchProDetail({ binding: binding(), detail: detail(), now: NOW });
  const workflow = createKokuchProDiscoveryWorkflow();
  const entryForms = (actions, methods = actions.map(() => "POST")) => ({ entry_forms: actions.map((action, index) => ({ action, method: methods[index] })) });
  for (const [name, page] of [
    ["wrong current", readbackPage(`${ROOT}?x=1`, entryForms([ENTRY_URL]))],
    ["entry missing", readbackPage(ROOT, entryForms([]))],
    ["entry duplicate", readbackPage(ROOT, entryForms([ENTRY_URL, ENTRY_URL, ENTRY_URL]))],
    ["entry action", readbackPage(ROOT, entryForms([`${ROOT}entry/?x=1`]))],
    ["entry method", readbackPage(ROOT, entryForms([ENTRY_URL], ["GET"]))],
    ["malformed entry", readbackPage(ROOT, { entry_forms: [{ action: ENTRY_URL }] })],
    ["evaluate", readbackPage(ROOT, null, { evaluateError: true })],
    ["redirect", readbackPage(ROOT, entryForms([ENTRY_URL]), { driftTo: LOGIN_URL })],
  ]) {
    assert.deepEqual(await workflow.readProviderState({ page, candidate }), { status: "unavailable" }, name);
  }
  const entryPath = new URL(ENTRY_URL).pathname;
  const loginFacts = { password_count: 1, login_forms: [{ action: LOGIN_URL, method: "POST" }] };
  const loginUrls = [
    `http://www.kokuchpro.com/auth/login/?continue=${encodeURIComponent(entryPath)}`,
    `https://kokuchpro.com/auth/login/?continue=${encodeURIComponent(entryPath)}`,
    `https://www.kokuchpro.com:443/auth/login/?continue=${encodeURIComponent(entryPath)}`,
    `https://user:pass@www.kokuchpro.com/auth/login/?continue=${encodeURIComponent(entryPath)}`,
    `https://www.kokuchpro.com/auth/login?continue=${encodeURIComponent(entryPath)}`,
    `${LOGIN_URL}?continue=${encodeURIComponent(entryPath)}#fragment`,
    `${LOGIN_URL}?continue=${encodeURIComponent(entryPath)}&continue=${encodeURIComponent(entryPath)}`,
    `${LOGIN_URL}?continue=${encodeURIComponent(`${entryPath}wrong`)}`,
  ];
  for (const url of loginUrls) assert.deepEqual(await workflow.readProviderState({ page: readbackPage(url, loginFacts), candidate }), { status: "unavailable" }, url);
  for (const facts of [
    { password_count: 0, login_forms: loginFacts.login_forms },
    { password_count: 2, login_forms: loginFacts.login_forms },
    { password_count: 1, login_forms: [] },
    { password_count: 1, login_forms: [{ action: LOGIN_URL, method: "GET" }] },
    { password_count: 1, login_forms: [loginFacts.login_forms[0], loginFacts.login_forms[0]] },
    { password_count: 1, login_forms: [{ action: "https://evil.example/auth/login/", method: "POST" }] },
    { password_count: 1 },
  ]) assert.deepEqual(await workflow.readProviderState({ page: readbackPage(`${LOGIN_URL}?continue=${encodeURIComponent(entryPath)}`, facts), candidate }), { status: "unavailable" });
  const otherCandidate = normalizeKokuchProDetail({ binding: binding(OCCURRENCE_URL), detail: detail({}, OCCURRENCE_URL), now: NOW });
  assert.deepEqual(await workflow.readProviderState({ page: readbackPage(`${LOGIN_URL}?continue=${encodeURIComponent(entryPath)}`, loginFacts), candidate: otherCandidate }), { status: "unavailable" });
});

test("KokuchPro workflow maps stage failures safely and leaves action/readback unavailable", async () => {
  const row = canonicalKokuchProBinding(ROOT);
  const cases = [
    ["KOKUCHPRO_LISTING_READ_FAILED", { readListingBindings: async () => { throw new Error("listing"); } }],
    ["KOKUCHPRO_DETAIL_READ_FAILED", { readListingBindings: async () => [row], readEventDetail: async () => { throw new Error("detail"); } }],
    ["KOKUCHPRO_CALENDAR_CONFLICT_CHECK_FAILED", { readListingBindings: async () => [row], readEventDetail: async () => detail(), isCalendarFree: async () => { throw new Error("calendar"); } }],
    ["KOKUCHPRO_AUDIT_FAILED", { readListingBindings: async () => [row], readEventDetail: async () => detail(), onDiscoveryAudit: async () => { throw new Error("audit"); } }],
  ];
  for (const [code, options] of cases) {
    const workflow = createKokuchProDiscoveryWorkflow({ now: () => new Date(NOW), ...options });
    await assert.rejects(workflow.discoverCandidates({ page: {}, calendar: [] }), (error) => error.code === code);
  }
  const candidate = normalizeKokuchProDetail({ binding: row, detail: detail(), now: NOW });
  const workflow = createKokuchProDiscoveryWorkflow();
  assert.deepEqual(await workflow.runDirectAction({ page: { click: async () => { throw new Error("must not click"); } }, candidate }), { status: "failed", safe_reason: "kokuchpro_direct_requires_harness" });
  assert.deepEqual(await workflow.readProviderState({ page: {}, candidate }), { status: "unavailable" });
});
