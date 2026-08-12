"use strict";

const assert = require("node:assert/strict");
const { createHash } = require("node:crypto");
const test = require("node:test");

const { createEventbriteScriptFirstWorkflow } = require("./connector-eventbrite-workflow.js");

const NOW = new Date("2026-08-11T03:00:00.000Z");
const LIST_URL = "https://www.eventbrite.com/d/japan--tokyo/free--events/";

function binding(id, slug = `tokyo-free-event-${id}`) {
  return {
    event_ref: `eventbrite-event://event/${id}`,
    canonical_url: `https://www.eventbrite.com/e/${slug}-tickets-${id}`,
  };
}

function detail(id, overrides = {}) {
  const row = binding(id);
  const event = {
    "@type": "SocialEvent",
    name: `Tokyo Free Event ${id}`,
    url: row.canonical_url,
    identifier: String(id),
    startDate: "2026-08-20T18:00:00+09:00",
    endDate: "2026-08-20T20:00:00+09:00",
    eventAttendanceMode: "https://schema.org/OfflineEventAttendanceMode",
    location: { "@type": "Place", address: { addressCountry: "JP", addressLocality: "Tokyo" } },
    offers: {
      "@type": "AggregateOffer",
      lowPrice: 0,
      highPrice: 0,
      priceCurrency: "JPY",
      availability: "InStock",
      url: row.canonical_url,
    },
    ...overrides.event,
  };
  return {
    jsonld: event,
    body_text: `Tokyo Free Event ${id} is free admission`,
    controls: [{ text: "Get tickets", visible: true }],
    ...overrides,
    ...(overrides.event ? { jsonld: event } : {}),
  };
}

function workflowFor(rows, details, options = {}) {
  const audits = [];
  const detailReads = [];
  const workflow = createEventbriteScriptFirstWorkflow({
    now: () => new Date(NOW),
    readListingBindings: async () => rows,
    readEventDetail: async (_page, canonicalUrl) => {
      detailReads.push(canonicalUrl);
      return details[canonicalUrl];
    },
    onDiscoveryAudit: async (audit) => { audits.push(audit); },
    ...options,
  });
  return { workflow, audits, detailReads };
}

function pageAt(url) { return { url: () => url }; }
function hash(url) { return createHash("sha256").update(url, "utf8").digest("hex"); }

test("Eventbrite canonicalizes exact tracked links, deduplicates by numeric id, and rejects other hosts or mismatched ids", async () => {
  const first = binding("101");
  const second = binding("202", "202");
  const rows = [
    { href: `${first.canonical_url}?aff=tracked#tickets`, event_id: "101" },
    { href: first.canonical_url, event_id: "101" },
    { href: "https://www.eventbrite.co.uk/e/tokyo-free-event-tickets-303?x=1", event_id: "303" },
    { href: "https://www.eventbrite.com/e/tokyo-free-event-tickets-404", event_id: "405" },
    { href: "https://www.eventbrite.com/e/paid-tokyo-event-tickets-406", event_id: "406", paid_status: "paid" },
    { href: `${second.canonical_url}?source=listing`, event_id: "202" },
  ];
  const { workflow, detailReads } = workflowFor(rows, {
    [first.canonical_url]: detail("101"),
    [second.canonical_url]: detail("202", { event: { url: second.canonical_url, offers: { "@type": "Offer", price: 0, availability: "InStock", url: second.canonical_url } } }),
  });
  const result = await workflow.discoverCandidates({ page: {}, calendar: [] });
  assert.deepEqual(result.map(({ event_ref, canonical_url }) => ({ event_ref, canonical_url })), [first, second]);
  assert.deepEqual(detailReads, [first.canonical_url, second.canonical_url]);
});

test("Eventbrite accepts SocialEvent and both zero Offer/AggregateOffer bounds only when identity, offline Tokyo, and exact Get tickets are valid", async () => {
  const ids = [301, 302];
  const rows = ids.map((id) => ({ href: binding(id).canonical_url, event_id: String(id) }));
  const aggregate = detail(301);
  const offer = detail(302, { event: { "@type": "Event", offers: { "@type": "Offer", price: 0, availability: "https://schema.org/InStock", url: binding(302).canonical_url } } });
  const { workflow } = workflowFor(rows, { [binding(301).canonical_url]: aggregate, [binding(302).canonical_url]: offer });
  const result = await workflow.discoverCandidates({ page: {}, calendar: [] });
  assert.deepEqual(result.map((candidate) => candidate.event_ref), ids.map((id) => `eventbrite-event://event/${id}`));
  assert.equal(result[0].ticket_price_minor, 0);
});

test("Eventbrite rejects an unqualified Japanese yen amount in body text", async () => {
  const row = binding("350");
  const { workflow } = workflowFor(
    [{ href: row.canonical_url, event_id: "350" }],
    { [row.canonical_url]: detail("350", { body_text: "1,000円" }) },
  );
  assert.deepEqual(await workflow.discoverCandidates({ page: {}, calendar: [] }), []);
});

test("Eventbrite requires an exact Offer or AggregateOffer type for zero-price offers", async () => {
  const row = binding("351");
  const { workflow } = workflowFor(
    [{ href: row.canonical_url, event_id: "351" }],
    { [row.canonical_url]: detail("351", { event: { offers: { "@type": "Thing", price: 0, availability: "InStock", url: row.canonical_url } } }) },
  );
  assert.deepEqual(await workflow.discoverCandidates({ page: {}, calendar: [] }), []);
});

test("Eventbrite accepts hydrated Reserve a spot for eligibility and absent readback", async () => {
  const row = binding("354");
  const { workflow } = workflowFor(
    [{ href: row.canonical_url, event_id: "354" }],
    { [row.canonical_url]: detail("354", { controls: [{ text: "Reserve a spot", visible: true }] }) },
  );
  assert.equal((await workflow.discoverCandidates({ page: {}, calendar: [] })).length, 1);
  const absent = createEventbriteScriptFirstWorkflow({
    readRegistrationView: async () => ({ page_url: row.canonical_url, canonical_links: [{ href: row.canonical_url, visible: true }], controls: [{ text: "Reserve a spot", visible: true }], body_text: "" }),
  });
  assert.deepEqual(await absent.readProviderState({ page: pageAt(row.canonical_url), candidate: { ...row, provider: "eventbrite", title: "Free", starts_at: "2026-08-20T09:00:00Z", ends_at: "2026-08-20T10:00:00Z" } }), { status: "absent" });
});

test("Eventbrite accepts explicit free phrases and rejects conditional purchase language", async () => {
  const freePhrases = ["参加費無料", "入場無料", "free admission", "no participation fee"];
  for (const [index, phrase] of freePhrases.entries()) {
    const id = String(360 + index); const row = binding(id);
    const { workflow } = workflowFor([{ href: row.canonical_url, event_id: id }], { [row.canonical_url]: detail(id, { body_text: `Tokyo event: ${phrase}` }) });
    assert.equal((await workflow.discoverCandidates({ page: {}, calendar: [] })).length, 1, phrase);
  }
  const purchaseMarkers = ["one drink minimum", "minimum purchase", "purchase required", "ワンドリンク必須"];
  for (const [index, marker] of purchaseMarkers.entries()) {
    const id = String(370 + index); const row = binding(id);
    const { workflow } = workflowFor([{ href: row.canonical_url, event_id: id }], { [row.canonical_url]: detail(id, { body_text: `Free admission. ${marker}` }) });
    assert.deepEqual(await workflow.discoverCandidates({ page: {}, calendar: [] }), [], marker);
  }
  for (const [index, marker] of ["参加費 1,000円", "admission fee ¥1,500", "paid at door"].entries()) {
    const id = String(380 + index); const row = binding(id);
    const { workflow } = workflowFor([{ href: row.canonical_url, event_id: id }], { [row.canonical_url]: detail(id, { body_text: `Free admission. ${marker}` }) });
    assert.deepEqual(await workflow.discoverCandidates({ page: {}, calendar: [] }), [], marker);
  }
});

test("Eventbrite bounds free clauses and preserves negative purchase statements", async () => {
  const paidContexts = [
    "Free admission fee required.",
    "No participation fee waiver is available.",
    "参加費無料化の対象外です。",
  ];
  for (const [index, phrase] of paidContexts.entries()) {
    const id = String(390 + index); const row = binding(id);
    const { workflow } = workflowFor([{ href: row.canonical_url, event_id: id }], {
      [row.canonical_url]: detail(id, { body_text: `Tokyo event: ${phrase}` }),
    });
    assert.deepEqual(await workflow.discoverCandidates({ page: {}, calendar: [] }), [], phrase);
  }

  const negativePurchase = ["No minimum purchase.", "No purchase required."];
  for (const [index, phrase] of negativePurchase.entries()) {
    const id = String(400 + index); const row = binding(id);
    const { workflow } = workflowFor([{ href: row.canonical_url, event_id: id }], {
      [row.canonical_url]: detail(id, { body_text: `Tokyo event: Free admission. ${phrase}` }),
    });
    assert.equal((await workflow.discoverCandidates({ page: {}, calendar: [] })).length, 1, phrase);
  }

  const boundedNegativePurchase = [
    "No minimum purchase waiver is available.",
    "No purchase required waiver is available.",
  ];
  for (const [index, phrase] of boundedNegativePurchase.entries()) {
    const id = String(420 + index); const row = binding(id);
    const { workflow } = workflowFor([{ href: row.canonical_url, event_id: id }], {
      [row.canonical_url]: detail(id, { body_text: `Tokyo event: Free admission. ${phrase}` }),
    });
    assert.deepEqual(await workflow.discoverCandidates({ page: {}, calendar: [] }), [], phrase);
  }

  for (const [index, phrase] of ["参加費は無料", "参加費：無料"].entries()) {
    const id = String(410 + index); const row = binding(id);
    const { workflow } = workflowFor([{ href: row.canonical_url, event_id: id }], {
      [row.canonical_url]: detail(id, { body_text: `Tokyo event: ${phrase}` }),
    });
    assert.equal((await workflow.discoverCandidates({ page: {}, calendar: [] })).length, 1, phrase);
  }
});

test("Eventbrite rejects mixed visible exact and fuzzy checkout controls", async () => {
  const row = binding("355");
  const controls = [{ text: "Reserve a spot", visible: true }, { text: "Reserve a spot now", visible: true }];
  const { workflow } = workflowFor([{ href: row.canonical_url, event_id: "355" }], { [row.canonical_url]: detail("355", { controls }) });
  assert.deepEqual(await workflow.discoverCandidates({ page: {}, calendar: [] }), []);
  const readback = createEventbriteScriptFirstWorkflow({ readRegistrationView: async () => ({ page_url: row.canonical_url, canonical_links: [], controls, body_text: "" }) });
  assert.deepEqual(await readback.readProviderState({ page: pageAt(row.canonical_url), candidate: { ...row, provider: "eventbrite", title: "Free", starts_at: "2026-08-20T09:00:00Z", ends_at: "2026-08-20T10:00:00Z" } }), { status: "unavailable" });
});

test("Eventbrite rejects foreign Offer suffixes and supported-plus-foreign mixed type arrays", async () => {
  const cases = [
    ["352", "https://evil.example/Offer"],
    ["353", ["Offer", "https://evil.example/Offer"]],
  ];
  const rows = cases.map(([id]) => ({ href: binding(id).canonical_url, event_id: id }));
  const details = Object.fromEntries(cases.map(([id, type]) => [
    binding(id).canonical_url,
    detail(id, { event: { offers: { "@type": type, price: 0, availability: "InStock", url: binding(id).canonical_url } } }),
  ]));
  const { workflow } = workflowFor(rows, details);
  assert.deepEqual(await workflow.discoverCandidates({ page: {}, calendar: [] }), []);
});

test("Eventbrite fails closed for online, outside-Tokyo, invalid-window, paid, unsafe, body-price, and duplicate-control details", async () => {
  const cases = [
    ["online", { event: { eventAttendanceMode: "https://schema.org/OnlineEventAttendanceMode" } }],
    ["outside-tokyo", { event: { location: { address: { addressCountry: "JP", addressLocality: "Osaka" } } } }],
    ["out-of-window", { event: { startDate: "2026-08-26T18:00:00+09:00", endDate: "2026-08-26T20:00:00+09:00" } }],
    ["paid-offer", { event: { offers: { "@type": "Offer", price: 100, availability: "InStock", url: binding(403).canonical_url } } }],
    ["door-price", { body_text: "Free online reservation. Door price ¥1,000." }],
    ["sold-out", { body_text: "Sold out" }],
    ["duplicate-control", { controls: [{ text: "Get tickets", visible: true }, { text: "Get tickets", visible: true }] }],
    ["unsupported-jsonld-type", { event: { "@type": "Thing" } }],
  ];
  const rows = cases.map(([,], index) => ({ href: binding(String(401 + index)).canonical_url, event_id: String(401 + index) }));
  const details = Object.fromEntries(cases.map(([name, overrides], index) => {
    const id = String(401 + index);
    return [binding(id).canonical_url, detail(id, overrides)];
  }));
  const { workflow } = workflowFor(rows, details);
  assert.deepEqual(await workflow.discoverCandidates({ page: {}, calendar: [] }), []);

  const mismatch = binding("499");
  const mismatchWorkflow = workflowFor(
    [{ href: mismatch.canonical_url, event_id: "499" }],
    { [mismatch.canonical_url]: detail("499", { event: { url: binding("498").canonical_url } }) },
  ).workflow;
  await assert.rejects(mismatchWorkflow.discoverCandidates({ page: {}, calendar: [] }), (error) => error && error.code === "EVENTBRITE_DETAIL_IDENTITY_MISMATCH_FAILED");
});

test("Eventbrite blocks unrelated timed overlap but keeps exact Connector coverage first", async () => {
  const covered = binding("501");
  const free = binding("502");
  const calendar = [
    { kind: "timed", start_at: "2026-08-21T18:30:00+09:00", end_at: "2026-08-21T19:30:00+09:00", connector_idempotency: "other" },
    { kind: "timed", start_at: "2026-08-20T18:00:00+09:00", end_at: "2026-08-20T20:00:00+09:00", connector_idempotency: hash(covered.canonical_url) },
  ];
  const { workflow } = workflowFor(
    [{ href: covered.canonical_url, event_id: "501" }, { href: free.canonical_url, event_id: "502" }],
    { [covered.canonical_url]: detail("501"), [free.canonical_url]: detail("502", { event: { startDate: "2026-08-21T18:00:00+09:00", endDate: "2026-08-21T20:00:00+09:00" } }) },
  );
  const result = await workflow.discoverCandidates({ page: {}, calendar });
  assert.deepEqual(result.map((candidate) => candidate.event_ref), [covered.event_ref]);
});

test("Eventbrite emits only the five privacy-safe audit counts", async () => {
  const first = binding("601");
  const second = binding("602");
  const audits = [];
  const { workflow } = workflowFor(
    [
      { href: `${first.canonical_url}?utm_source=x`, event_id: "601" },
      { href: first.canonical_url, event_id: "601" },
      { href: second.canonical_url, event_id: "602" },
    ],
    { [first.canonical_url]: detail("601"), [second.canonical_url]: detail("602", { body_text: "Sold out" }) },
    { onDiscoveryAudit: async (audit) => audits.push(audit) },
  );
  await workflow.discoverCandidates({ page: {}, calendar: [] });
  assert.deepEqual(audits, [{ discovered_count: 3, within_window_count: 2, eligible_count: 1, calendar_free_count: 1, selected_count: 1 }]);
  assert.deepEqual(Object.keys(audits[0]).sort(), ["calendar_free_count", "discovered_count", "eligible_count", "selected_count", "within_window_count"]);
  assert.equal(JSON.stringify(audits).includes("eventbrite.com"), false);
  assert.equal(JSON.stringify(audits).includes("Tokyo Free Event"), false);
});

test("Eventbrite direct action is a zero-click safe failure", async () => {
  let clicks = 0;
  const candidate = { ...binding("701"), provider: "eventbrite", title: "Free", starts_at: "2026-08-20T09:00:00Z", ends_at: "2026-08-20T10:00:00Z" };
  const { workflow } = workflowFor([], {}, { submitOnPage: async () => { clicks += 1; } });
  assert.deepEqual(await workflow.runDirectAction({ page: { click: async () => { clicks += 1; } }, candidate }), { status: "failed", safe_reason: "eventbrite_direct_requires_harness" });
  assert.equal(clicks, 0);
});

test("Eventbrite parent readback is strict and fail-closed", async () => {
  const candidate = { ...binding("801"), provider: "eventbrite", title: "Free", starts_at: "2026-08-20T09:00:00Z", ends_at: "2026-08-20T10:00:00Z" };
  const registered = createEventbriteScriptFirstWorkflow({
    readRegistrationView: async () => ({
      page_url: candidate.canonical_url,
      canonical_links: [{ href: candidate.canonical_url, visible: true }],
      controls: [],
      body_text: "Registration complete",
    }),
  });
  assert.deepEqual(await registered.readProviderState({ page: pageAt(candidate.canonical_url), candidate }), { status: "registered" });

  const absent = createEventbriteScriptFirstWorkflow({
    readRegistrationView: async () => ({ page_url: candidate.canonical_url, canonical_links: [{ href: candidate.canonical_url, visible: true }], controls: [{ text: "Get tickets", visible: true }], body_text: "" }),
  });
  assert.deepEqual(await absent.readProviderState({ page: pageAt(candidate.canonical_url), candidate }), { status: "absent" });

  const missingCanonical = createEventbriteScriptFirstWorkflow({
    readRegistrationView: async () => ({ page_url: candidate.canonical_url, canonical_links: [], controls: [{ text: "Get tickets", visible: true }], body_text: "" }),
  });
  assert.deepEqual(await missingCanonical.readProviderState({ page: pageAt(candidate.canonical_url), candidate }), { status: "unavailable" });

  const explicitAuth = createEventbriteScriptFirstWorkflow({
    readRegistrationView: async () => ({ page_url: candidate.canonical_url, canonical_links: [{ href: candidate.canonical_url, visible: true }], controls: [{ text: "Get tickets", visible: true }], body_text: "", auth_required: true }),
  });
  assert.deepEqual(await explicitAuth.readProviderState({ page: pageAt(candidate.canonical_url), candidate }), { status: "unavailable" });

  const hiddenCompletion = createEventbriteScriptFirstWorkflow({
    readRegistrationView: async () => ({
      page_url: candidate.canonical_url,
      canonical_links: [{ href: candidate.canonical_url, visible: true }],
      controls: [{ text: "Registration complete", visible: false }],
      body_text: "Registration complete",
    }),
  });
  assert.deepEqual(await hiddenCompletion.readProviderState({ page: pageAt(candidate.canonical_url), candidate }), { status: "unavailable" });

  for (const view of [
    { page_url: candidate.canonical_url, canonical_links: [{ href: candidate.canonical_url, visible: true }, { href: candidate.canonical_url, visible: true }], controls: [], body_text: "Registration complete" },
    { page_url: candidate.canonical_url, canonical_links: [{ href: binding("802").canonical_url, visible: true }], controls: [], body_text: "Registration complete" },
    { page_url: candidate.canonical_url, canonical_links: [{ href: candidate.canonical_url, visible: true }], controls: [], body_text: "Registration complete payment required" },
    { page_url: "https://www.eventbrite.com/e/other-tickets-801", canonical_links: [], controls: [{ text: "Get tickets", visible: true }], body_text: "" },
    { page_url: candidate.canonical_url, canonical_links: [], controls: [{ text: "Get tickets", visible: true }], body_text: "Sold out" },
  ]) {
    const workflow = createEventbriteScriptFirstWorkflow({ readRegistrationView: async () => view });
    assert.deepEqual(await workflow.readProviderState({ page: pageAt(candidate.canonical_url), candidate }), { status: "unavailable" });
  }
});

test("Eventbrite default parent readback ignores related event anchors and benign login copy", async () => {
  const candidate = { ...binding("803"), provider: "eventbrite", title: "Free", starts_at: "2026-08-20T09:00:00Z", ends_at: "2026-08-20T10:00:00Z" };
  const canonical = { tagName: "LINK", href: candidate.canonical_url, getAttribute(name) { return name === "rel" ? "canonical" : name === "href" ? this.href : null; } };
  const anchors = [candidate.canonical_url, binding("804").canonical_url, binding("805").canonical_url, binding("806").canonical_url].map((href) => ({ tagName: "A", href, offsetWidth: 120, offsetHeight: 24, getAttribute(name) { return name === "href" ? this.href : null; } }));
  const control = { innerText: "Reserve a spot", offsetWidth: 120, offsetHeight: 32 };
  const page = { url() { return candidate.canonical_url; }, async evaluate(callback) {
    const previous = global.document;
    global.document = { body: { innerText: "Welcome. Log in or sign in to continue; auth is handled by the host." }, querySelectorAll(selector) {
      if (selector === "link[rel='canonical']") return [canonical];
      if (selector === "a[href],link[rel='canonical']") return [canonical, ...anchors];
      if (selector === '[data-testid="conversion-bar-checkout-button"]') return [control];
      return [];
    } };
    try { return await callback(); } finally { if (previous === undefined) delete global.document; else global.document = previous; }
  } };
  const workflow = createEventbriteScriptFirstWorkflow();
  assert.deepEqual(await workflow.readProviderState({ page, candidate }), { status: "absent" });
});

test("Eventbrite default parent readback rejects a missing canonical rel", async () => {
  const candidate = { ...binding("807"), provider: "eventbrite", title: "Free", starts_at: "2026-08-20T09:00:00Z", ends_at: "2026-08-20T10:00:00Z" };
  const control = { innerText: "Reserve a spot", offsetWidth: 120, offsetHeight: 32 };
  const page = { url() { return candidate.canonical_url; }, async evaluate(callback) {
    const previous = global.document;
    global.document = { body: { innerText: "Welcome. Log in or sign in; auth is benign copy." }, querySelectorAll(selector) {
      if (selector === "link[rel='canonical']") return [];
      if (selector === '[data-testid="conversion-bar-checkout-button"]') return [control];
      return [];
    } };
    try { return await callback(); } finally { if (previous === undefined) delete global.document; else global.document = previous; }
  } };
  const workflow = createEventbriteScriptFirstWorkflow();
  assert.deepEqual(await workflow.readProviderState({ page, candidate }), { status: "unavailable" });
});

test("Eventbrite parent readback accepts completion on the direct official checkout child only", async () => {
  const candidate = { ...binding("1997468673573"), provider: "eventbrite", title: "Free", starts_at: "2026-08-20T09:00:00Z", ends_at: "2026-08-20T10:00:00Z" };
  const canonical = { tagName: "LINK", href: candidate.canonical_url, getAttribute(name) { return name === "rel" ? "canonical" : name === "href" ? this.href : null; } };
  const control = { innerText: "Reserve a spot", offsetWidth: 120, offsetHeight: 32 };
  const nested = (url) => ({ url() { return url; }, async evaluate() { throw new Error("nested frame must not be read"); } });
  const checkout = { url() { return `https://www.eventbrite.com/checkout-external?eid=1997468673573`; }, childFrames() { return [nested(this.url()), nested(this.url())]; }, async evaluate(callback) {
    const previous = global.document;
    global.document = { body: { innerText: "Thanks for your order! YOU'RE GOING TO Tokyo" }, querySelectorAll(selector) { return selector === "button" ? [] : []; } };
    try { return await callback(); } finally { if (previous === undefined) delete global.document; else global.document = previous; }
  } };
  const mainFrame = { childFrames() { return [checkout]; } };
  const page = { url() { return candidate.canonical_url; }, mainFrame() { return mainFrame; }, async evaluate(callback) {
    const previous = global.document;
    global.document = { body: { innerText: "" }, querySelectorAll(selector) {
      if (selector === "link[rel='canonical']") return [canonical];
      if (selector === '[data-testid="conversion-bar-checkout-button"]') return [control];
      return [];
    } };
    try { return await callback(); } finally { if (previous === undefined) delete global.document; else global.document = previous; }
  } };
  const workflow = createEventbriteScriptFirstWorkflow();
  assert.deepEqual(await workflow.readProviderState({ page, candidate }), { status: "registered" });
});

test("Eventbrite direct checkout readback rejects ambiguous, nested, and partial completion", async () => {
  const candidate = { ...binding("1997468673574"), provider: "eventbrite", title: "Free", starts_at: "2026-08-20T09:00:00Z", ends_at: "2026-08-20T10:00:00Z" };
  const canonical = { href: candidate.canonical_url, getAttribute(name) { return name === "rel" ? "canonical" : this.href; } };
  const control = { innerText: "Reserve a spot", offsetWidth: 120, offsetHeight: 32 };
  const frame = ({ eid = "1997468673574", body = "", register = 0, nested = [], error = false, host = "www.eventbrite.com", href = "" } = {}) => ({
    url() { return href || `https://${host}/checkout-external?eid=${eid}`; },
    childFrames() { return nested; },
    async evaluate(callback) {
      if (error) throw new Error("checkout evaluate failed");
      const previous = global.document;
      global.document = { body: { innerText: body }, querySelectorAll(selector) {
        return selector === "button" ? Array.from({ length: register }, () => ({ innerText: "Register" })) : [];
      } };
      try { return await callback(); } finally { if (previous === undefined) delete global.document; else global.document = previous; }
    },
  });
  const pageFor = (children) => ({ url() { return candidate.canonical_url; }, mainFrame() { return { childFrames() { return children; } }; }, async evaluate(callback) {
    const previous = global.document;
    global.document = { body: { innerText: "" }, querySelectorAll(selector) {
      if (selector === "link[rel='canonical']") return [canonical];
      if (selector === '[data-testid="conversion-bar-checkout-button"]') return [control];
      return [];
    } };
    try { return await callback(); } finally { if (previous === undefined) delete global.document; else global.document = previous; }
  } });
  const complete = "Thanks for your order! YOU'RE GOING TO Tokyo";
  const cases = [
    ["wrong-eid", [frame({ eid: "1997468673575", body: complete })], "unavailable"],
    ["duplicate", [frame({ body: complete }), frame({ body: complete })], "unavailable"],
    ["nested-only", [frame({ nested: [frame({ body: complete })] })], "absent"],
    ["thanks-only", [frame({ body: "Thanks for your order!" })], "absent"],
    ["going-only", [frame({ body: "YOU'RE GOING TO Tokyo" })], "absent"],
    ["register-residual", [frame({ body: complete, register: 1 })], "absent"],
    ["evaluate-error", [frame({ error: true })], "unavailable"],
    ["wrong-host", [frame({ body: complete, host: "evil.example" })], "unavailable"],
    ["port", [frame({ body: complete, href: "https://www.eventbrite.com:444/checkout-external?eid=1997468673574" })], "unavailable"],
    ["userinfo", [frame({ body: complete, href: "https://user:pass@www.eventbrite.com/checkout-external?eid=1997468673574" })], "unavailable"],
    ["empty-userinfo", [frame({ body: complete, href: "https://@www.eventbrite.com/checkout-external?eid=1997468673574" })], "unavailable"],
    ["empty-userpass", [frame({ body: complete, href: "https://:@www.eventbrite.com/checkout-external?eid=1997468673574" })], "unavailable"],
    ["hash", [frame({ body: complete, href: "https://www.eventbrite.com/checkout-external?eid=1997468673574#done" })], "unavailable"],
  ];
  const workflow = createEventbriteScriptFirstWorkflow();
  for (const [name, children, status] of cases) {
    assert.deepEqual(await workflow.readProviderState({ page: pageFor(children), candidate }), { status }, name);
  }
});

test("Eventbrite default listing reader uses one owned page and exact card selectors across three pages", async () => {
  const rows = [binding("901"), binding("902"), binding("903")];
  const listingUrls = [LIST_URL, `${LIST_URL}?page=2`, `${LIST_URL}?page=3`];
  const calls = [];
  let currentUrl = LIST_URL;
  const page = {
    async goto(url) { calls.push(["goto", url]); currentUrl = url; },
    url() { return currentUrl; },
    async evaluate(callback) {
      const row = rows[listingUrls.indexOf(currentUrl)];
      const anchor = {
        href: `${row.canonical_url}?aff=foo`, dataset: { eventId: row.event_ref.split("/").pop(), eventLocation: "Tokyo", eventPaidStatus: "free" },
        getAttribute(name) { return name === "data-event-id" ? this.dataset.eventId : name === "href" ? this.href : null; },
      };
      const old = global.document;
      global.document = { querySelectorAll(selector) {
        assert.equal(selector, '[data-testid="search-event"]');
        return [{ querySelectorAll(inner) { assert.equal(inner, "a.event-card-link[data-event-id][href]"); return [anchor]; } }];
      } };
      try { return callback(); } finally { if (old === undefined) delete global.document; else global.document = old; }
    },
  };
  const workflow = createEventbriteScriptFirstWorkflow({
    now: () => NOW,
    readEventDetail: async (_page, canonicalUrl) => detail(canonicalUrl.match(/-(\d+)$/)[1]),
  });
  const result = await workflow.discoverCandidates({ page, calendar: [] });
  assert.deepEqual(result.map((row) => row.event_ref), rows.map((row) => row.event_ref));
  assert.deepEqual(calls, listingUrls.map((url) => ["goto", url]));
});

test("Eventbrite default listing reader fails closed on exact URL drift", async () => {
  const calls = [];
  let currentUrl = LIST_URL;
  const page = {
    async goto(url) { calls.push(["goto", url]); currentUrl = `${url}?drift=1`; },
    url() { return currentUrl; },
    async evaluate() { throw new Error("evaluate must not run after URL drift"); },
  };
  const workflow = createEventbriteScriptFirstWorkflow({ now: () => NOW });
  await assert.rejects(
    workflow.discoverCandidates({ page, calendar: [] }),
    (error) => error && error.code === "EVENTBRITE_LISTING_NAVIGATION_FAILED",
  );
  assert.deepEqual(calls, [["goto", LIST_URL]]);
});

test("Eventbrite default listing reader rejects page read failure without partial rows", async () => {
  const calls = [];
  let currentUrl = LIST_URL;
  let evaluateCount = 0;
  const page = {
    async goto(url) { calls.push(["goto", url]); currentUrl = url; },
    url() { return currentUrl; },
    async evaluate() {
      evaluateCount += 1;
      if (evaluateCount === 1) return [{ href: binding("904").canonical_url, event_id: "904" }];
      throw new Error("page two read failed");
    },
  };
  let detailReads = 0;
  const workflow = createEventbriteScriptFirstWorkflow({
    now: () => NOW,
    readEventDetail: async () => { detailReads += 1; return detail("904"); },
  });
  await assert.rejects(
    workflow.discoverCandidates({ page, calendar: [] }),
    (error) => error && error.code === "EVENTBRITE_LISTING_READ_FAILED",
  );
  assert.deepEqual(calls, [["goto", LIST_URL], ["goto", `${LIST_URL}?page=2`]]);
  assert.equal(detailReads, 0);
});
