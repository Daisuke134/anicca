"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");

const { createMeetupScriptFirstWorkflow } = require("./connector-meetup-workflow.js");

const NOW = new Date("2026-08-11T08:00:00.000Z");

function binding(id, group = "tokyo-builders") {
  return Object.freeze({
    event_ref: `meetup-event://event/${id}`,
    canonical_url: `https://www.meetup.com/${group}/events/${id}/`,
  });
}

function detail(id, overrides = {}) {
  const row = binding(id);
  const jsonld = {
    "@context": "https://schema.org",
    "@type": "Event",
    name: "Tokyo Free Event",
    url: row.canonical_url,
    startDate: "2026-08-15T20:00:00+09:00",
    endDate: "2026-08-15T21:00:00+09:00",
    eventStatus: "https://schema.org/EventScheduled",
    eventAttendanceMode: "https://schema.org/OfflineEventAttendanceMode",
    location: { "@type": "Place", address: { addressCountry: "JP", addressLocality: "Tokyo", addressRegion: "Tokyo" } },
    ...overrides.jsonld,
  };
  return Object.freeze({
    jsonld,
    body_text: "Free Event - 無料イベント",
    controls: [{ text: "Attend", visible: true }],
    ...overrides,
    ...(overrides.jsonld ? { jsonld } : {}),
  });
}

function workflowFor(rows, details, options = {}) {
  const audits = [];
  const detailReads = [];
  const workflow = createMeetupScriptFirstWorkflow({
    now: () => new Date(NOW),
    readFindBindings: async () => rows,
    readEventDetail: async (_page, canonicalUrl) => { detailReads.push(canonicalUrl); return details[canonicalUrl]; },
    onDiscoveryAudit: async (audit) => { audits.push(audit); },
    ...options,
  });
  return { workflow, audits, detailReads };
}

function pageAt(url) {
  return { url: () => url };
}

test("Meetup accepts only strict canonical event URLs and deduplicates Find order", async () => {
  const first = binding("101");
  const second = binding("202", "ascii-group");
  const rows = [
    first,
    { ...first, canonical_url: `${first.canonical_url}?source=find` },
    first,
    second,
    { ...second, canonical_url: "https://www.meetup.com/ja-JP/ascii-group/events/202/" },
  ];
  const { workflow, detailReads } = workflowFor(rows, {
    [first.canonical_url]: detail("101"),
    [second.canonical_url]: detail("202", { jsonld: { url: second.canonical_url } }),
  });
  const result = await workflow.discoverCandidates({ page: {}, calendar: [] });
  assert.deepEqual(result.map((candidate) => candidate.event_ref), [first.event_ref, second.event_ref]);
  assert.deepEqual(detailReads, [first.canonical_url, second.canonical_url]);

  const invalids = [
    "https://meetup.com/tokyo-builders/events/101/",
    "http://www.meetup.com/tokyo-builders/events/101/",
    "https://www.meetup.com/tokyo-builders/events/0/",
    "https://www.meetup.com/tokyo-builders/events/101",
    "https://www.meetup.com/tokyo-builders/events/101/?x=1",
    "https://user:pass@www.meetup.com/tokyo-builders/events/101/",
    "https://www.meetup.com:443/tokyo-builders/events/101/",
    "https://www.meetup.com/tokyo_builders/events/101/",
  ];
  for (const canonical_url of invalids) {
    const row = { event_ref: "meetup-event://event/101", canonical_url };
    const { workflow: invalidWorkflow } = workflowFor([row], { [canonical_url]: detail("101") });
    assert.deepEqual(await invalidWorkflow.discoverCandidates({ page: {}, calendar: [] }), [], canonical_url);
  }
});

test("default script-first readers use the same page for Find and exact detail", async () => {
  const row = binding("109");
  const detailView = detail("109");
  const navigations = [];
  let waited = false;
  let evaluates = 0;
  const page = {
    async goto(url) { navigations.push(url); },
    async waitForFunction(predicate) {
      const previousDocument = global.document;
      const node = (text) => ({ innerText: text, textContent: text, offsetWidth: 10, offsetHeight: 10 });
      try {
        global.document = { querySelectorAll: () => [node("Log in")] };
        assert.equal(predicate(), false);
        global.document = { querySelectorAll: () => [node("Attend")] };
        assert.equal(predicate(), true);
      } finally {
        if (previousDocument === undefined) delete global.document;
        else global.document = previousDocument;
      }
      waited = true;
    },
    async evaluate() {
      evaluates += 1;
      if (evaluates === 1) return [{ canonical_url: `${row.canonical_url}?source=recommendation#event` }];
      assert.equal(waited, true);
      return detailView;
    },
  };
  const workflow = createMeetupScriptFirstWorkflow({ now: () => new Date(NOW) });
  const result = await workflow.discoverCandidates({ page, calendar: [] });
  assert.deepEqual(result.map((candidate) => candidate.event_ref), [row.event_ref]);
  assert.deepEqual(navigations, [
    "https://www.meetup.com/find/?keywords=free&location=jp--Tokyo&source=EVENTS",
    row.canonical_url,
  ]);
});

test("default detail reader fails closed when the registration control never becomes ready", async () => {
  const row = binding("110");
  let waitCalls = 0;
  let evaluates = 0;
  const page = {
    async goto() {},
    async waitForFunction() { waitCalls += 1; throw new Error("control timeout"); },
    async evaluate() {
      evaluates += 1;
      if (evaluates === 1) return [{ canonical_url: row.canonical_url }];
      throw new Error("must not read before control readiness");
    },
  };
  const workflow = createMeetupScriptFirstWorkflow({
    now: () => new Date(NOW),
  });
  await assert.rejects(
    workflow.discoverCandidates({ page, calendar: [] }),
    (error) => error && error.code === "MEETUP_DETAIL_READ_FAILED",
  );
  assert.equal(waitCalls, 1);
});

test("default parent readback waits for a terminal registration marker", async () => {
  const candidate = { ...binding("111"), provider: "meetup" };
  let waited = false;
  const page = {
    url: () => candidate.canonical_url,
    async waitForFunction(predicate) {
      const previousDocument = global.document;
      const node = (text) => ({ innerText: text, textContent: text, offsetWidth: 10, offsetHeight: 10 });
      try {
        global.document = { querySelectorAll: () => [node("Sign in")] };
        assert.equal(predicate(), false);
        global.document = { querySelectorAll: () => [node("Going")] };
        assert.equal(predicate(), true);
      } finally {
        if (previousDocument === undefined) delete global.document;
        else global.document = previousDocument;
      }
      waited = true;
    },
    async evaluate() {
      assert.equal(waited, true);
      return { controls: [{ text: "Going", visible: true }] };
    },
  };
  const workflow = createMeetupScriptFirstWorkflow();
  assert.deepEqual(await workflow.readProviderState({ page, candidate }), { status: "registered" });
});

test("default parent readback returns unavailable when marker readiness times out", async () => {
  const candidate = { ...binding("112"), provider: "meetup" };
  let waitCalls = 0;
  const page = {
    url: () => candidate.canonical_url,
    async waitForFunction() { waitCalls += 1; throw new Error("control timeout"); },
    async evaluate() { throw new Error("must not read before control readiness"); },
  };
  const workflow = createMeetupScriptFirstWorkflow();
  assert.deepEqual(await workflow.readProviderState({ page, candidate }), { status: "unavailable" });
  assert.equal(waitCalls, 1);
});

test("JSON-LD identity must match the Find binding", async () => {
  const row = binding("303");
  const mismatched = detail("303", { jsonld: { url: binding("304").canonical_url } });
  const { workflow } = workflowFor([row], { [row.canonical_url]: mismatched });
  await assert.rejects(
    workflow.discoverCandidates({ page: {}, calendar: [] }),
    (error) => error && error.code === "MEETUP_DETAIL_IDENTITY_MISMATCH_FAILED",
  );
});

test("discovery keeps the five-count audit contract", async () => {
  const first = binding("401");
  const second = binding("402");
  const { workflow, audits } = workflowFor([first, first, second], {
    [first.canonical_url]: detail("401"), [second.canonical_url]: detail("402"),
  });
  const result = await workflow.discoverCandidates({ page: {}, calendar: [] });
  assert.equal(result.length, 2);
  assert.deepEqual(audits, [{ observed_count: 3, normalized_count: 2, window_count: 2, free_open_count: 2, calendar_free_count: 2 }]);
  assert.deepEqual(Object.keys(audits[0]).sort(), ["calendar_free_count", "free_open_count", "normalized_count", "observed_count", "window_count"]);
});

test("only scheduled in-person Tokyo events in the fourteen-day window with exact Attend and explicit free text pass", async () => {
  const cases = [
    ["scheduled", {}, true],
    ["cancelled", { jsonld: { eventStatus: "https://schema.org/EventCancelled" } }, false],
    ["online", { jsonld: { eventAttendanceMode: "https://schema.org/OnlineEventAttendanceMode" } }, false],
    ["outside-japan", { jsonld: { location: { address: { addressCountry: "US", addressLocality: "Tokyo" } } } }, false],
    ["outside-tokyo", { jsonld: { location: { address: { addressCountry: "JP", addressLocality: "Osaka" } } } }, false],
    ["too-early", { jsonld: { startDate: "2026-08-10T20:00:00+09:00", endDate: "2026-08-10T21:00:00+09:00" } }, false],
    ["too-late", { jsonld: { startDate: "2026-08-25T20:00:00+09:00", endDate: "2026-08-25T21:00:00+09:00" } }, false],
    ["invalid-interval", { jsonld: { startDate: "2026-08-15T21:00:00+09:00", endDate: "2026-08-15T20:00:00+09:00" } }, false],
    ["no-attend", { controls: [{ text: "Attend", visible: false }] }, false],
    ["duplicate-attend", { controls: [{ text: "Attend", visible: true }, { text: "Attend", visible: true }] }, false],
    ["not-free", { body_text: "Tokyo event", jsonld: { offers: { price: 0 } } }, false],
    ["not-a-free-event", { body_text: "This is not a free event" }, false],
    ["not-free-event", { body_text: "This is not free event" }, false],
    ["jp-free-negated", { body_text: "無料ではありません" }, false],
    ["jp-free-negated-plain", { body_text: "無料ではないイベント" }, false],
    ["free-admission", { body_text: "Free admission" }, true],
    ["participation-fee-free", { body_text: "Participation fee: FREE" }, true],
    ["event-fee-free", { body_text: "Event fee: free" }, true],
    ["無料イベント", { body_text: "無料イベント" }, true],
    ["参加費無料", { body_text: "参加費無料" }, true],
    ["入場料無料", { body_text: "入場料無料" }, true],
    ["料金無料", { body_text: "料金無料" }, true],
    ["feel-free-generic", { body_text: "Feel free to join our meetup" }, false],
    ["free-wifi-generic", { body_text: "Free Wi-Fi available" }, false],
    ["board-games-free-generic", { body_text: "Board games for free" }, false],
    ["first-time-meal-free-generic", { body_text: "First-time meal free" }, false],
    ["amount-marker", { body_text: "Free Event, ¥1,000 at the door" }, false],
    ["mandatory-drink", { body_text: "Free Event - one drink purchase required" }, false],
    ["waitlist", { body_text: "Free Event - join waitlist", controls: [{ text: "Attend", visible: true }] }, false],
    ["full", { body_text: "Free Event - sold out", controls: [{ text: "Attend", visible: true }] }, false],
  ];
  for (const [name, overrides, expected] of cases) {
    const row = binding(String(500 + cases.indexOf(cases.find((entry) => entry[0] === name))));
    const { workflow } = workflowFor([row], { [row.canonical_url]: detail(row.event_ref.split("/").pop(), overrides) });
    const result = await workflow.discoverCandidates({ page: {}, calendar: [] });
    assert.equal(result.length > 0, expected, name);
  }
});

test("unrelated Calendar overlap blocks a candidate while exact Connector coverage is recoverable first", async () => {
  const covered = binding("601");
  const blocked = binding("602");
  const calendar = [
    { kind: "timed", start_at: "2026-08-15T18:30:00.000+09:00", end_at: "2026-08-15T19:30:00.000+09:00", connector_idempotency: "other" },
    { kind: "timed", start_at: "2026-08-15T20:00:00.000+09:00", end_at: "2026-08-15T21:00:00.000+09:00", connector_idempotency: "replace-me" },
  ];
  const { workflow } = workflowFor([covered, blocked], {
    [covered.canonical_url]: detail("601"),
    [blocked.canonical_url]: detail("602", { jsonld: {
      startDate: "2026-08-15T19:00:00+09:00", endDate: "2026-08-15T20:00:00+09:00",
    } }),
  }, { isCalendarFree: async (candidate, intervals) => {
    const rows = intervals.filter((busy) => busy.kind === "timed");
    return !rows.some((busy) => Date.parse(candidate.starts_at) < Date.parse(busy.end_at)
      && Date.parse(candidate.ends_at) > Date.parse(busy.start_at)
      && busy.connector_idempotency !== require("node:crypto").createHash("sha256").update(candidate.canonical_url).digest("hex"));
  } });
  calendar[1].connector_idempotency = require("node:crypto").createHash("sha256").update(covered.canonical_url).digest("hex");
  const result = await workflow.discoverCandidates({ page: {}, calendar });
  assert.deepEqual(result.map((candidate) => candidate.event_ref), [covered.event_ref]);
});

test("parent readback registers only one exact visible Edit RSVP or Going marker", async () => {
  const candidate = { ...binding("701"), provider: "meetup" };
  const registeredViews = [
    { controls: [{ text: "Edit RSVP", visible: true }] },
    { controls: [{ text: "Going", visible: true }] },
    { controls: [{ text: "Edit RSVP", visible: true }, { text: "Going", visible: true }] },
    { controls: [{ text: "Going", visible: false }] },
    { controls: [{ text: "Edit RSVP", visible: true }], auth_required: true },
    { controls: [{ text: "Edit RSVP", visible: true }], waitlist: true },
  ];
  for (const view of registeredViews) {
    const { workflow } = workflowFor([], {}, { readRegistrationView: async () => view });
    const result = await workflow.readProviderState({ page: pageAt(candidate.canonical_url), candidate });
    assert.equal(result.status, view.controls.filter((control) => control.visible && ["Edit RSVP", "Going"].includes(control.text)).length === 1 && !view.auth_required && !view.waitlist ? "registered" : "unavailable");
  }
});

test("parent readback reports absent only for one exact visible Attend without auth or waitlist", async () => {
  const candidate = { ...binding("702"), provider: "meetup" };
  const views = [
    [{ controls: [{ text: "Attend", visible: true }] }, "absent"],
    [{ controls: [{ text: "Attend", visible: true }, { text: "Attend", visible: true }] }, "unavailable"],
    [{ controls: [{ text: "Attend", visible: false }] }, "unavailable"],
    [{ controls: [{ text: "Attend", visible: true }], auth_required: true }, "unavailable"],
    [{ controls: [{ text: "Attend", visible: true }], waitlist: true }, "unavailable"],
    [{ controls: [{ text: "Attend", visible: true }] }, "unavailable", "https://www.meetup.com/tokyo-builders/events/703/"],
  ];
  for (const [view, expected, url = candidate.canonical_url] of views) {
    const { workflow } = workflowFor([], {}, { readRegistrationView: async () => view });
    const result = await workflow.readProviderState({ page: pageAt(url), candidate });
    assert.equal(result.status, expected);
  }
});

test("Meetup direct action is a stable safe failure and never submits", async () => {
  let submits = 0;
  const candidate = { ...binding("801"), provider: "meetup" };
  const workflow = createMeetupScriptFirstWorkflow({
    async submitOnPage() { submits += 1; return { status: "registered" }; },
  });
  assert.deepEqual(await workflow.runDirectAction({ page: {}, candidate }), {
    status: "failed", safe_reason: "meetup_direct_requires_harness",
  });
  assert.equal(submits, 0);
});
