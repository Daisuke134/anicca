"use strict";

const assert = require("node:assert/strict");
const { createHash } = require("node:crypto");
const test = require("node:test");

const { createDoorkeeperScriptFirstWorkflow } = require("./connector-doorkeeper-workflow.js");

const NOW = new Date("2026-08-11T03:00:00.000Z");

function binding(id, group = "tokyo-builders") {
  return {
    event_ref: `doorkeeper-event://event/${id}`,
    canonical_url: `https://${group}.doorkeeper.jp/events/${id}`,
  };
}

function detail(id, group = "tokyo-builders", overrides = {}) {
  const row = binding(id, group);
  const jsonld = {
    "@type": "Event",
    name: `Tokyo Free Event ${id}`,
    url: row.canonical_url,
    startDate: "2026-08-20T18:00:00+09:00",
    endDate: "2026-08-20T20:00:00+09:00",
    eventAttendanceMode: "https://schema.org/OfflineEventAttendanceMode",
    location: { "@type": "Place", address: "東京都千代田区1-1" },
    offers: [{
      "@type": "Offer",
      availability: "https://schema.org/InStock",
      price: "0",
      priceCurrency: "JPY",
      url: row.canonical_url,
    }],
    ...overrides.jsonld,
  };
  return {
    jsonld,
    body_text: `Tokyo Free Event ${id}`,
    controls: [{ text: "申し込む", visible: true }],
    ...overrides,
    ...(overrides.jsonld ? { jsonld } : {}),
  };
}

function workflowFor(rows, details, options = {}) {
  const audits = [];
  const detailReads = [];
  const workflow = createDoorkeeperScriptFirstWorkflow({
    now: () => new Date(NOW),
    readListingPage: async (_page, pageNumber) => ({
      rows: pageNumber === 1 ? rows : [],
      has_next: false,
    }),
    readEventDetail: async (_page, canonicalUrl) => {
      detailReads.push(canonicalUrl);
      return details[canonicalUrl];
    },
    onDiscoveryAudit: async (audit) => { audits.push(audit); },
    ...options,
  });
  return { workflow, audits, detailReads };
}

function pageAt(url) {
  return { url: () => url };
}

function defaultDomPage({ redirectListing = false, redirectDetail = false } = {}) {
  const row = binding("1001");
  let currentUrl = "";
  let phase = "";
  let evaluateCalls = 0;
  const titleAnchor = { href: row.canonical_url };
  const venueAnchor = { href: "https://www.doorkeeper.jp/prefectures/tokyo" };
  const dateNode = { textContent: "2026年8月11日", innerText: "2026年8月11日" };
  const listingItemsWrap = {
    querySelector(selector) {
      if (selector.includes("/events/")) return titleAnchor;
      if (selector === "a[href]") return titleAnchor;
      if (selector === ".events-list-item-time-date") return dateNode;
      if (selector.includes("/prefectures/")) return venueAnchor;
      return null;
    },
    querySelectorAll(selector) { return selector === ".events-list-item, li" ? [] : [titleAnchor, venueAnchor]; },
  };
  const listingRoot = {
    querySelector(selector) {
      if (selector === ".events-list-items-wrap") return listingItemsWrap;
      return listingItemsWrap.querySelector(selector);
    },
    querySelectorAll(selector) {
      if (selector === ".events-list-items-wrap") return [listingItemsWrap];
      if (selector === ".events-list-item, li") return [];
      return listingItemsWrap.querySelectorAll(selector);
    },
  };
  const script = { textContent: JSON.stringify(detail("1001").jsonld) };
  const control = { innerText: "申し込む", textContent: "申し込む", value: "", offsetWidth: 10, offsetHeight: 10 };
  const listingDocument = {
    querySelector(selector) { return selector === ".events-list-items-wrap" ? listingItemsWrap : null; },
    querySelectorAll(selector) { return selector === ".global-event.events-list" ? [listingRoot] : []; },
  };
  const detailDocument = {
    querySelector() { return null; },
    querySelectorAll(selector) {
      if (selector === 'script[type="application/ld+json"]') return [script];
      if (selector === "a,button,input[type='submit']") return [control];
      return [];
    },
    body: { innerText: "Tokyo Free Event 1001" },
  };
  return {
    async goto(url) {
      phase = url.includes("/prefectures/tokyo/events") ? "listing" : "detail";
      currentUrl = (phase === "listing" && redirectListing) || (phase === "detail" && redirectDetail)
        ? "https://redirected.example.invalid/other" : url;
    },
    url() { return currentUrl; },
    async evaluate(callback) {
      evaluateCalls += 1;
      const previousDocument = global.document;
      global.document = phase === "listing" ? listingDocument : detailDocument;
      try { return callback(); } finally {
        if (previousDocument === undefined) delete global.document;
        else global.document = previousDocument;
      }
    },
    evaluateCalls() { return evaluateCalls; },
  };
}

const eligibleJsonLd = {
  "@type": "Event",
  name: "Tokyo Free Event",
  url: "https://tokyo-builders.doorkeeper.jp/events/101",
  startDate: "2026-08-20T18:00:00+09:00",
  endDate: "2026-08-20T20:00:00+09:00",
  eventAttendanceMode: "https://schema.org/OfflineEventAttendanceMode",
  location: { "@type": "Place", address: "東京都千代田区1-1" },
  offers: [{
    "@type": "Offer",
    availability: "https://schema.org/InStock",
    price: "0",
    priceCurrency: "JPY",
    url: "https://tokyo-builders.doorkeeper.jp/events/101",
  }],
};

test("Doorkeeper reads ordered Tokyo listing pages and accepts only exact canonical events", async () => {
  const first = binding("101");
  const second = binding("202", "ascii-group");
  const pages = [];
  const detailReads = [];
  const workflow = createDoorkeeperScriptFirstWorkflow({
    now: () => new Date(NOW),
    async readListingPage(_page, pageNumber) {
      pages.push(pageNumber);
      if (pageNumber === 1) return {
        rows: [
          { canonical_url: first.canonical_url, day: "2026-08-11", venue_url: "https://www.doorkeeper.jp/prefectures/tokyo" },
          { canonical_url: first.canonical_url, day: "2026-08-11", venue_url: "https://www.doorkeeper.jp/prefectures/tokyo" },
          { canonical_url: "https://www.doorkeeper.jp/events/101", day: "2026-08-11", venue_url: "https://www.doorkeeper.jp/prefectures/tokyo" },
          { canonical_url: "https://tokyo-builders.doorkeeper.jp/events/101?x=1", day: "2026-08-11", venue_url: "https://www.doorkeeper.jp/prefectures/tokyo" },
        ],
        has_next: true,
      };
      assert.equal(pageNumber, 2);
      return {
        rows: [
          { canonical_url: second.canonical_url, day: "2026-08-24", venue_url: "https://www.doorkeeper.jp/prefectures/tokyo" },
          { canonical_url: binding("303").canonical_url, day: "2026-08-25", venue_url: "https://www.doorkeeper.jp/prefectures/tokyo" },
        ],
        has_next: true,
      };
    },
    async readEventDetail(_page, canonicalUrl) {
      detailReads.push(canonicalUrl);
      return canonicalUrl === first.canonical_url ? detail("101") : detail("202", "ascii-group");
    },
  });

  const result = await workflow.discoverCandidates({ page: {}, calendar: [] });
  assert.deepEqual(pages, [1, 2]);
  assert.deepEqual(detailReads, [first.canonical_url, second.canonical_url]);
  assert.deepEqual(result.map(({ event_ref, canonical_url }) => ({ event_ref, canonical_url })), [first, second]);
});

test("Doorkeeper rejects the www origin even when it has an event-shaped path", async () => {
  const malformed = { canonical_url: "https://www.doorkeeper.jp/events/1001", day: "2026-08-11", venue_url: "https://www.doorkeeper.jp/prefectures/tokyo" };
  const { workflow } = workflowFor([malformed], {});
  assert.deepEqual(await workflow.discoverCandidates({ page: {}, calendar: [] }), []);
});

test("Doorkeeper rejects a mismatched JSON-LD identity", async () => {
  const row = binding("304");
  const { workflow } = workflowFor(
    [{ canonical_url: row.canonical_url, day: "2026-08-11", venue_url: "https://www.doorkeeper.jp/prefectures/tokyo" }],
    { [row.canonical_url]: detail("304", "tokyo-builders", { jsonld: { url: binding("305").canonical_url } }) },
  );
  await assert.rejects(
    workflow.discoverCandidates({ page: {}, calendar: [] }),
    (error) => error && error.code === "DOORKEEPER_DETAIL_IDENTITY_MISMATCH_FAILED",
  );
});

test("default listing and detail readers observe the owned page DOM after exact navigation", async () => {
  const page = defaultDomPage();
  const workflow = createDoorkeeperScriptFirstWorkflow({ now: () => new Date(NOW) });
  const result = await workflow.discoverCandidates({ page, calendar: [] });
  assert.deepEqual(result.map(({ event_ref, canonical_url, title }) => ({ event_ref, canonical_url, title })), [{
    event_ref: "doorkeeper-event://event/1001",
    canonical_url: "https://tokyo-builders.doorkeeper.jp/events/1001",
    title: "Tokyo Free Event 1001",
  }]);
  assert.equal(page.evaluateCalls(), 2);
});

test("default listing reader fails before DOM acceptance when navigation redirects", async () => {
  const page = defaultDomPage({ redirectListing: true });
  const workflow = createDoorkeeperScriptFirstWorkflow({ now: () => new Date(NOW) });
  await assert.rejects(
    workflow.discoverCandidates({ page, calendar: [] }),
    (error) => error && error.code === "DOORKEEPER_LISTING_NAVIGATION_FAILED",
  );
  assert.equal(page.evaluateCalls(), 0);
});

test("default detail reader fails before JSON-LD acceptance when navigation redirects", async () => {
  const page = defaultDomPage({ redirectDetail: true });
  const workflow = createDoorkeeperScriptFirstWorkflow({
    now: () => new Date(NOW),
    readListingPage: async () => ({
      rows: [{ canonical_url: binding("1001").canonical_url, day: "2026-08-11", venue_url: "https://www.doorkeeper.jp/prefectures/tokyo" }],
      has_next: false,
    }),
  });
  await assert.rejects(
    workflow.discoverCandidates({ page, calendar: [] }),
    (error) => error && error.code === "DOORKEEPER_DETAIL_NAVIGATION_FAILED",
  );
  assert.equal(page.evaluateCalls(), 0);
});

test("Doorkeeper applies strict detail eligibility gates", async () => {
  const cases = [
    ["online", { jsonld: { eventAttendanceMode: "https://schema.org/OnlineEventAttendanceMode" } }, false],
    ["outside-tokyo", { jsonld: { location: { "@type": "Place", address: "大阪府大阪市" } } }, false],
    ["invalid-interval", { jsonld: { startDate: "2026-08-20T20:00:00+09:00", endDate: "2026-08-20T18:00:00+09:00" } }, false],
    ["outside-window", { jsonld: { startDate: "2026-08-25T18:00:00+09:00", endDate: "2026-08-25T20:00:00+09:00" } }, false],
    ["paid", { jsonld: { offers: [{ ...eligibleJsonLd.offers[0], price: "100" }] } }, false],
    ["non-jpy", { jsonld: { offers: [{ ...eligibleJsonLd.offers[0], priceCurrency: "USD" }] } }, false],
    ["no-offer", { jsonld: { offers: [] } }, false],
    ["not-in-stock", { jsonld: { offers: [{ ...eligibleJsonLd.offers[0], availability: "https://schema.org/SoldOut" }] } }, false],
    ["offer-mismatch", { jsonld: { offers: [{ ...eligibleJsonLd.offers[0], url: binding("999").canonical_url }] } }, false],
    ["paid-body", { body_text: "1,000円 会場払い" }, false],
    ["missing-submit", { controls: [] }, false],
    ["duplicate-submit", { controls: [{ text: "申し込む", visible: true }, { text: "申し込む", visible: true }] }, false],
    ["visible-trigger-hidden-final-submit", { controls: [{ text: "申し込む", visible: true }, { text: "申し込む", visible: false }] }, true],
    ["hidden-submit", { controls: [{ text: "申し込む", visible: false }] }, false],
    ["cancelled", { body_text: "受付終了" }, false],
  ];
  for (const [name, overrides, expected] of cases) {
    const row = binding(String(500 + cases.indexOf(cases.find((entry) => entry[0] === name))));
    const { workflow } = workflowFor(
      [{ canonical_url: row.canonical_url, day: "2026-08-11", venue_url: "https://www.doorkeeper.jp/prefectures/tokyo" }],
      { [row.canonical_url]: detail(row.canonical_url.split("/").pop(), "tokyo-builders", { jsonld: { ...eligibleJsonLd, url: row.canonical_url, offers: [{ ...eligibleJsonLd.offers[0], url: row.canonical_url }], ...overrides.jsonld }, ...overrides }) },
    );
    const result = await workflow.discoverCandidates({ page: {}, calendar: [] });
    assert.equal(result.length > 0, expected, name);
  }
});

test("all offers must be exact free JPY InStock offers", async () => {
  const first = binding("610");
  const second = binding("611");
  const { workflow } = workflowFor(
    [
      { canonical_url: first.canonical_url, day: "2026-08-11", venue_url: "https://www.doorkeeper.jp/prefectures/tokyo" },
      { canonical_url: second.canonical_url, day: "2026-08-11", venue_url: "https://www.doorkeeper.jp/prefectures/tokyo" },
    ],
    {
      [first.canonical_url]: detail("610", "tokyo-builders", { jsonld: { offers: [{ ...eligibleJsonLd.offers[0], url: first.canonical_url }, { ...eligibleJsonLd.offers[0], url: first.canonical_url }] } }),
      [second.canonical_url]: detail("611", "tokyo-builders", { jsonld: { offers: [eligibleJsonLd.offers[0], { ...eligibleJsonLd.offers[0], price: 1 }] } }),
    },
  );
  const result = await workflow.discoverCandidates({ page: {}, calendar: [] });
  assert.deepEqual(result.map((candidate) => candidate.event_ref), [first.event_ref]);
});

test("Doorkeeper keeps the five-count audit contract without private fields", async () => {
  const rows = Array.from({ length: 4 }, (_, index) => {
    const id = String(700 + index);
    return { canonical_url: binding(id).canonical_url, day: index === 3 ? "2026-08-25" : "2026-08-11", venue_url: "https://www.doorkeeper.jp/prefectures/tokyo" };
  });
  const audits = [];
  const { workflow } = workflowFor(rows, Object.fromEntries(rows.slice(0, 3).map((row) => [row.canonical_url, detail(row.canonical_url.split("/").pop())])), {
    onDiscoveryAudit: async (audit) => { audits.push(audit); },
    isCalendarFree: async (candidate) => candidate.event_ref.endsWith("701"),
  });
  await workflow.discoverCandidates({ page: {}, calendar: [] });
  assert.deepEqual(audits, [{ discovered_count: 4, within_window_count: 3, eligible_count: 3, calendar_free_count: 1, selected_count: 1 }]);
  assert.deepEqual(Object.keys(audits[0]).sort(), ["calendar_free_count", "discovered_count", "eligible_count", "selected_count", "within_window_count"]);
  assert.equal(JSON.stringify(audits).includes("doorkeeper.jp"), false);
  assert.equal(JSON.stringify(audits).includes("Tokyo Free Event"), false);
});

test("unrelated Calendar overlap blocks while exact Connector coverage is recoverable first", async () => {
  const covered = binding("801");
  const free = binding("802");
  const calendar = [
    { kind: "timed", start_at: "2026-08-20T19:00:00+09:00", end_at: "2026-08-20T19:30:00+09:00", connector_idempotency: "other" },
    { kind: "timed", start_at: "2026-08-20T18:00:00+09:00", end_at: "2026-08-20T19:00:00+09:00", connector_idempotency: createHash("sha256").update(covered.canonical_url).digest("hex") },
  ];
  const { workflow } = workflowFor(
    [
      { canonical_url: covered.canonical_url, day: "2026-08-11", venue_url: "https://www.doorkeeper.jp/prefectures/tokyo" },
      { canonical_url: free.canonical_url, day: "2026-08-11", venue_url: "https://www.doorkeeper.jp/prefectures/tokyo" },
    ],
    {
      [covered.canonical_url]: detail("801", "tokyo-builders", { jsonld: { startDate: "2026-08-20T18:00:00+09:00", endDate: "2026-08-20T19:00:00+09:00" } }),
      [free.canonical_url]: detail("802", "tokyo-builders", { jsonld: { startDate: "2026-08-20T19:00:00+09:00", endDate: "2026-08-20T20:00:00+09:00" } }),
    },
  );
  const result = await workflow.discoverCandidates({ page: {}, calendar });
  assert.deepEqual(result.map((candidate) => candidate.event_ref), [covered.event_ref]);
});

test("parent readback is strict about page identity, completion marker, and exact link", async () => {
  const candidate = { ...binding("901"), provider: "doorkeeper" };
  const workflow = createDoorkeeperScriptFirstWorkflow({
    readRegistrationView: async () => ({
      page_url: candidate.canonical_url,
      canonical_links: [{ href: candidate.canonical_url, visible: true }],
      controls: [],
      body_text: "申し込みが完了しました",
    }),
  });
  assert.deepEqual(await workflow.readProviderState({ page: pageAt(candidate.canonical_url), candidate }), { status: "registered" });

  const absentWorkflow = createDoorkeeperScriptFirstWorkflow({
    readRegistrationView: async () => ({
      page_url: candidate.canonical_url,
      canonical_links: [],
      controls: [{ text: "申し込む", visible: true }],
      body_text: "イベント詳細",
    }),
  });
  assert.deepEqual(await absentWorkflow.readProviderState({ page: pageAt(candidate.canonical_url), candidate }), { status: "absent" });
});

test("parent readback returns unavailable for ambiguous or unsafe views", async () => {
  const candidate = { ...binding("902"), provider: "doorkeeper" };
  const views = [
    { page_url: candidate.canonical_url, canonical_links: [{ href: candidate.canonical_url, visible: true }, { href: candidate.canonical_url, visible: true }], controls: [], body_text: "申し込みが完了しました" },
    { page_url: candidate.canonical_url, canonical_links: [{ href: binding("903").canonical_url, visible: true }], controls: [], body_text: "申し込みが完了しました" },
    { page_url: candidate.canonical_url, canonical_links: [{ href: candidate.canonical_url, visible: true }], controls: [], body_text: "申し込みが完了しました 申し込みが完了しました" },
    { page_url: candidate.canonical_url, canonical_links: [{ href: candidate.canonical_url, visible: true }], controls: [], body_text: "申し込みが完了しました 支払いが必要です" },
    { page_url: "https://other.doorkeeper.jp/events/902", canonical_links: [{ href: candidate.canonical_url, visible: true }], controls: [{ text: "申し込む", visible: true }], body_text: "" },
    { page_url: candidate.canonical_url, canonical_links: [{ href: candidate.canonical_url, visible: true }], controls: [{ text: "申し込みが完了しました", visible: false }, { text: "申し込む", visible: true }], body_text: "" },
  ];
  for (const view of views) {
    const workflow = createDoorkeeperScriptFirstWorkflow({ readRegistrationView: async () => view });
    assert.deepEqual(await workflow.readProviderState({ page: pageAt(candidate.canonical_url), candidate }), { status: "unavailable" });
  }
});

test("parent readback rejects Doorkeeper unavailable status text even with a visible submit control", async () => {
  const candidate = { ...binding("904"), provider: "doorkeeper" };
  for (const marker of ["中止", "延期", "受付終了"]) {
    const workflow = createDoorkeeperScriptFirstWorkflow({
      readRegistrationView: async () => ({
        page_url: candidate.canonical_url,
        canonical_links: [],
        controls: [{ text: "申し込む", visible: true }],
        body_text: marker,
      }),
    });
    assert.deepEqual(await workflow.readProviderState({ page: pageAt(candidate.canonical_url), candidate }), { status: "unavailable" }, marker);
  }
});

test("parent readback fails closed when an unsafe marker is visible in controls", async () => {
  const candidate = { ...binding("905"), provider: "doorkeeper" };
  for (const marker of ["中止", "延期", "受付終了"]) {
    const workflow = createDoorkeeperScriptFirstWorkflow({
      readRegistrationView: async () => ({
        page_url: candidate.canonical_url,
        canonical_links: [],
        controls: [{ text: "申し込む", visible: true }, { text: marker, visible: true }],
        body_text: "",
      }),
    });
    assert.deepEqual(await workflow.readProviderState({ page: pageAt(candidate.canonical_url), candidate }), { status: "unavailable" }, marker);
  }
});

test("Doorkeeper direct action is a stable safe failure and never submits", async () => {
  const candidate = {
    ...binding("999"),
    provider: "doorkeeper",
    title: "Tokyo Free Event",
    starts_at: "2026-08-20T09:00:00.000Z",
    ends_at: "2026-08-20T10:00:00.000Z",
    registration_status: "available",
    ticket_price_status: "free",
    ticket_price_minor: 0,
  };
  const workflow = createDoorkeeperScriptFirstWorkflow();
  assert.deepEqual(await workflow.runDirectAction({ page: {}, candidate }), {
    status: "failed", safe_reason: "doorkeeper_direct_requires_harness",
  });
});

test("a logged-out doorkeeper header (both login and signup controls) is reported as a session problem, not a generic harness requirement", async () => {
  const candidate = {
    ...binding("998"),
    provider: "doorkeeper",
    title: "Tokyo Free Event",
    starts_at: "2026-08-20T09:00:00.000Z",
    ends_at: "2026-08-20T10:00:00.000Z",
    registration_status: "available",
    ticket_price_status: "free",
    ticket_price_minor: 0,
  };
  const workflow = createDoorkeeperScriptFirstWorkflow();
  const page = { evaluate: async () => ({ login: true, signup: true }) };
  assert.deepEqual(await workflow.runDirectAction({ page, candidate }), {
    status: "failed", safe_reason: "doorkeeper_session_expired",
  });
});

test("only one of the login/signup header controls keeps the ordinary requires-harness reason, never misreporting a closed or full event as a logout", async () => {
  const candidate = {
    ...binding("997"),
    provider: "doorkeeper",
    title: "Tokyo Free Event",
    starts_at: "2026-08-20T09:00:00.000Z",
    ends_at: "2026-08-20T10:00:00.000Z",
    registration_status: "available",
    ticket_price_status: "free",
    ticket_price_minor: 0,
  };
  const workflow = createDoorkeeperScriptFirstWorkflow();
  for (const observed of [
    { login: true, signup: false },
    { login: false, signup: true },
    { login: false, signup: false },
  ]) {
    const page = { evaluate: async () => observed };
    assert.deepEqual(await workflow.runDirectAction({ page, candidate }), {
      status: "failed", safe_reason: "doorkeeper_direct_requires_harness",
    }, JSON.stringify(observed));
  }
});
