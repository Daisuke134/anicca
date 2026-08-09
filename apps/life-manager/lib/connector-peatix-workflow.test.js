"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");

const { createPeatixDiscoveryWorkflow } = require("./connector-peatix-workflow.js");

const NOW = new Date("2026-08-07T08:30:00.000Z");

function ticket(overrides = {}) {
  return {
    id: 1,
    price: 0,
    status: 10,
    seatsAvailable: 10,
    ...overrides,
  };
}

function detail(id, overrides = {}) {
  const { event: eventOverrides = {}, ...rest } = overrides;
  return {
    event: {
      id,
      title: `Event ${id}`,
      status: "OPEN",
      isOpen: true,
      isFinished: false,
      datetime: "2026-08-10 10:00",
      datetimeEnd: "2026-08-10 11:00",
      tickets: [ticket()],
      ...eventOverrides,
    },
    ...rest,
  };
}

function binding(id) {
  return {
    event_ref: `peatix-event://event/${id}`,
    canonical_url: `https://peatix.com/event/${id}`,
  };
}

function eligibilityFixture() {
  return [
    [binding(101), detail(101, {
      event: {
        datetime: "2026-08-24 10:00",
        datetimeEnd: "2026-08-24 11:00",
      },
    })],
    [binding(102), detail(102, {
      event: {
        tickets: [ticket({ id: 2, price: 1000 })],
      },
    })],
    [binding(103), detail(103, {
      event: {
        tickets: [ticket({ id: 3, status: 100, seatsAvailable: 0 })],
      },
    })],
    [binding(104), detail(104, {
      event: {
        tickets: [ticket({
          id: 4,
          salesEnds: { datetime: "2026-08-07 17:00" },
        })],
      },
    })],
    [binding(105), detail(105)],
    [binding(106), detail(106, {
      event: { title: "Eligible Event 106" },
    })],
  ];
}

test("Peatix normalizes public details and keeps only ordered free/open calendar-free candidates", async () => {
  const page = Object.freeze({ page_id: "same-owned-page" });
  const fixture = eligibilityFixture();
  const readerPages = [];
  const detailCalls = [];
  const workflow = createPeatixDiscoveryWorkflow({
    now: () => NOW,
    async readSearchBindings(suppliedPage) {
      readerPages.push(suppliedPage);
      return fixture.map(([row]) => row);
    },
    async readEventViewData(suppliedPage, canonicalUrl) {
      readerPages.push(suppliedPage);
      detailCalls.push(canonicalUrl);
      return fixture.find(([row]) => row.canonical_url === canonicalUrl)[1];
    },
    isCalendarFree(candidate) {
      return candidate.event_ref !== "peatix-event://event/105";
    },
  });

  const result = await workflow.discoverCandidates({ page, calendar: [] });

  assert.deepEqual(result, [{
    provider: "peatix",
    event_ref: "peatix-event://event/106",
    canonical_url: "https://peatix.com/event/106",
    title: "Eligible Event 106",
    starts_at: "2026-08-10T01:00:00.000Z",
    ends_at: "2026-08-10T02:00:00.000Z",
    registration_status: "available",
    ticket_price_status: "free",
    ticket_price_minor: 0,
  }]);
  assert.equal(readerPages.length, 7);
  assert.equal(readerPages.every((suppliedPage) => suppliedPage === page), true);
  assert.deepEqual(detailCalls, fixture.map(([row]) => row.canonical_url));
  assert.equal(Object.isFrozen(result), true);
  assert.equal(Object.isFrozen(result[0]), true);
});

test("Peatix reports the ordered five-count discovery audit", async () => {
  const audits = [];
  const fixture = eligibilityFixture();
  const workflow = createPeatixDiscoveryWorkflow({
    now: () => NOW,
    async readSearchBindings() { return fixture.map(([row]) => row); },
    async readEventViewData(_page, canonicalUrl) {
      return fixture.find(([row]) => row.canonical_url === canonicalUrl)[1];
    },
    isCalendarFree(candidate) {
      return candidate.event_ref !== "peatix-event://event/105";
    },
    onDiscoveryAudit(audit) {
      audits.push(audit);
      assert.equal(Object.isFrozen(audit), true);
    },
  });

  await workflow.discoverCandidates({ page: {}, calendar: [] });

  assert.deepEqual(audits, [{
    observed_count: 6,
    normalized_count: 6,
    window_count: 5,
    free_open_count: 2,
    calendar_free_count: 1,
  }]);
});

test("Peatix default readers use one page, canonical event identities, and same-origin JSON", async () => {
  const navigations = [];
  const evaluations = [];
  const page = {
    async goto(url) {
      navigations.push(url);
    },
    async evaluate(fn, argument) {
      evaluations.push({ fn, argument });
      if (argument === undefined) {
        return [
          { href: "https://peatix.com/event/201/", title: "First" },
          { href: "https://peatix.com/event/201", title: "Duplicate" },
          { href: "https://example.com/event/999", title: "Ignore" },
          { href: "https://peatix.com/event/202", title: "Second" },
        ];
      }
      const id = argument.endsWith("/201") ? 201 : 202;
      return detail(id, { event: { title: `Default ${id}` } });
    },
  };
  const workflow = createPeatixDiscoveryWorkflow({
    now: () => NOW,
    isCalendarFree() { return true; },
  });

  const result = await workflow.discoverCandidates({ page, calendar: [] });

  assert.deepEqual(navigations, [
    "https://peatix.com/search?q=%E7%84%A1%E6%96%99&country=JP&l.text=Tokyo",
    "https://peatix.com/event/201",
    "https://peatix.com/event/202",
  ]);
  assert.deepEqual(evaluations.map(({ argument }) => argument), [
    undefined,
    "https://peatix.com/event/201",
    "https://peatix.com/event/202",
  ]);
  assert.deepEqual(result.map((candidate) => candidate.event_ref), [
    "peatix-event://event/201",
    "peatix-event://event/202",
  ]);
});

test("Peatix rejects a search binding list over the bounded contract", async () => {
  const workflow = createPeatixDiscoveryWorkflow({
    async readSearchBindings() {
      return Array.from({ length: 101 }, (_, index) => binding(index + 1));
    },
  });

  await assert.rejects(
    workflow.discoverCandidates({ page: {}, calendar: [] }),
    (error) => error.code === "PEATIX_SEARCH_ROWS_CONTRACT_FAILED"
      && error.message === "Peatix discovery stage failed",
  );
});

test("Peatix maps navigation, reader, identity, candidate, and Calendar failures to safe stage codes", async () => {
  const page = {};
  const oneBinding = binding(301);
  const validDetail = detail(301);
  const injectedCases = [
    ["search read", {
      async readSearchBindings() { throw new Error("private search error"); },
    }, "PEATIX_SEARCH_READ_FAILED"],
    ["detail read", {
      async readSearchBindings() { return [oneBinding]; },
      async readEventViewData() { throw new Error("private detail error"); },
    }, "PEATIX_DETAIL_READ_FAILED"],
    ["identity mismatch", {
      async readSearchBindings() { return [oneBinding]; },
      async readEventViewData() { return detail(302); },
    }, "PEATIX_DETAIL_IDENTITY_MISMATCH_FAILED"],
    ["candidate validation", {
      async readSearchBindings() { return [oneBinding]; },
      async readEventViewData() {
        return detail(301, { event: { datetime: "not-a-date" } });
      },
    }, "PEATIX_CANDIDATE_VALIDATION_FAILED"],
    ["Calendar check", {
      async readSearchBindings() { return [oneBinding]; },
      async readEventViewData() { return validDetail; },
      async isCalendarFree() { throw new Error("private calendar error"); },
    }, "PEATIX_CALENDAR_CONFLICT_CHECK_FAILED"],
  ];

  for (const [, options, code] of injectedCases) {
    const workflow = createPeatixDiscoveryWorkflow({ now: () => NOW, ...options });
    await assert.rejects(
      workflow.discoverCandidates({ page, calendar: [] }),
      (error) => error.code === code
        && error.message === "Peatix discovery stage failed"
        && !error.message.includes("private"),
    );
  }
});

test("Peatix default reader maps search navigation and read failures without leaking browser text", async () => {
  const navigationWorkflow = createPeatixDiscoveryWorkflow();
  await assert.rejects(
    navigationWorkflow.discoverCandidates({
      page: {
        async goto() { throw new Error("private navigation error"); },
        async evaluate() { return []; },
      },
      calendar: [],
    }),
    (error) => error.code === "PEATIX_SEARCH_NAVIGATION_FAILED"
      && error.message === "Peatix discovery stage failed",
  );

  const readWorkflow = createPeatixDiscoveryWorkflow();
  await assert.rejects(
    readWorkflow.discoverCandidates({
      page: {
        async goto() {},
        async evaluate() { throw new Error("private evaluate error"); },
      },
      calendar: [],
    }),
    (error) => error.code === "PEATIX_SEARCH_READ_FAILED"
      && error.message === "Peatix discovery stage failed",
  );

  const detailNavigationWorkflow = createPeatixDiscoveryWorkflow({ now: () => NOW });
  let navigationCount = 0;
  await assert.rejects(
    detailNavigationWorkflow.discoverCandidates({
      page: {
        async goto() {
          navigationCount += 1;
          if (navigationCount === 2) throw new Error("private detail navigation error");
        },
        async evaluate(_fn, argument) {
          return argument === undefined ? [{ href: "https://peatix.com/event/401" }] : detail(401);
        },
      },
      calendar: [],
    }),
    (error) => error.code === "PEATIX_DETAIL_NAVIGATION_FAILED"
      && error.message === "Peatix discovery stage failed",
  );

  const detailReadWorkflow = createPeatixDiscoveryWorkflow({ now: () => NOW });
  let evaluateCount = 0;
  await assert.rejects(
    detailReadWorkflow.discoverCandidates({
      page: {
        async goto() {},
        async evaluate(_fn, argument) {
          evaluateCount += 1;
          if (evaluateCount === 2) throw new Error("private detail JSON error");
          return argument === undefined ? [{ href: "https://peatix.com/event/402" }] : detail(402);
        },
      },
      calendar: [],
    }),
    (error) => error.code === "PEATIX_DETAIL_READ_FAILED"
      && error.message === "Peatix discovery stage failed",
  );
});
