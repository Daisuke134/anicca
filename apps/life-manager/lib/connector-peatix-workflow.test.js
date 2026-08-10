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
  const { event: eventOverrides = {}, json_data: jsonDataOverrides = {}, ...rest } = overrides;
  return {
    ...rest,
    json_data: {
      ...jsonDataOverrides,
      event: {
        id,
        name: `Event ${id}`,
        status: "OPEN",
        isOpen: true,
        isFinished: false,
        datetime: "2026-08-10 10:00",
        datetimeEnd: "2026-08-10 11:00",
        tickets: [ticket()],
        ...eventOverrides,
      },
    },
  };
}

function binding(id) {
  return {
    event_ref: `peatix-event://event/${id}`,
    canonical_url: `https://peatix.com/event/${id}`,
  };
}

function searchResponse(pageNumber, events) {
  return { url: () => `https://peatix.com/search/events?p=${pageNumber}&size=20`, ok: () => true, status: () => 200, async json() { return { json_data: { page: pageNumber, events } }; } };
}

function retryPage(waitSequence, navigationErrors = []) {
  const state = { waits: 0, navigations: 0, owners: [] }; const page = {
    waitForResponse() { const next = waitSequence[state.waits++]; state.owners.push(this); return next instanceof Error ? Promise.reject(next) : Promise.resolve(next); },
    async goto() { state.owners.push(this); const error = navigationErrors[state.navigations++]; if (error) throw error; },
  };
  return { page, state };
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
      event: { name: "Eligible Event 106", tickets: [ticket({ id: 6 }), ticket({ id: 7 })] },
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
    ticket_id: "6",
  }]);
  assert.equal(readerPages.length, 7);
  assert.equal(readerPages.every((suppliedPage) => suppliedPage === page), true);
  assert.deepEqual(detailCalls, fixture.map(([row]) => row.canonical_url));
  assert.equal(Object.isFrozen(result), true);
  assert.equal(Object.isFrozen(result[0]), true);
});

test("Peatix direct action carries the exact ticket/profile and readback stays privacy-safe", async () => {
  const selected = {
    provider: "peatix", event_ref: "peatix-event://event/106", canonical_url: "https://peatix.com/event/106",
    title: "Eligible Event 106", starts_at: "2026-08-10T01:00:00.000Z", ends_at: "2026-08-10T02:00:00.000Z",
    registration_status: "available", ticket_price_status: "free", ticket_price_minor: 0, ticket_id: "6",
  };
  const page = Object.freeze({}); const profile = { name: "Private Name", email: "private@example.test", accept_organizer_privacy: true }; const calls = [];
  const workflow = createPeatixDiscoveryWorkflow({
    readAttendeeProfile: async () => { calls.push("profile"); return profile; },
    async submitOnPage(suppliedPage, candidate, suppliedProfile) { calls.push(["submit", suppliedPage, candidate, suppliedProfile]); return { status: "registered", reason: "private" }; },
    async readStateOnPage(suppliedPage, candidate) { calls.push(["read", suppliedPage, candidate]); return { status: "registered", reason: "private", email: profile.email }; },
  });
  assert.deepEqual(await workflow.runDirectAction({ page, candidate: selected }), { status: "completed", method: "peatix_direct_submit" });
  assert.equal(calls[0], "profile"); assert.equal(calls[1][1], page); assert.equal(calls[1][2], selected); assert.equal(calls[1][3], profile);
  assert.deepEqual(await workflow.readProviderState({ page, candidate: selected }), { status: "registered" });
  assert.equal(JSON.stringify(await workflow.readProviderState({ page, candidate: selected })).includes(profile.email), false);
  const ambiguous = createPeatixDiscoveryWorkflow({ readAttendeeProfile: async () => profile, async submitOnPage() { return { status: "unavailable", reason: "private" }; } });
  assert.deepEqual(await ambiguous.runDirectAction({ page, candidate: selected }), { status: "failed", safe_reason: "direct_action_unverified" });
  await assert.rejects(workflow.runDirectAction({ page, candidate: { ...selected, ticket_id: "" } }));
});

test("Peatix workflow readback exposes only registered, absent, or unavailable", async () => {
  const candidate = { provider: "peatix", event_ref: "peatix-event://event/106", canonical_url: "https://peatix.com/event/106", title: "Event", starts_at: "2026-08-10T01:00:00.000Z", ends_at: "2026-08-10T02:00:00.000Z", registration_status: "available", ticket_price_status: "free", ticket_price_minor: 0, ticket_id: "6" };
  for (const observed of ["registered", "absent", "unavailable"]) {
    const workflow = createPeatixDiscoveryWorkflow({ async readStateOnPage() { return { status: observed, reason: "private", name: "private" }; } });
    assert.deepEqual(await workflow.readProviderState({ page: {}, candidate }), { status: observed });
  }
});

test("Peatix action/readback reject non-claimable candidates before private/provider calls", async () => {
  const base = { provider: "peatix", event_ref: "peatix-event://event/106", canonical_url: "https://peatix.com/event/106", title: "Event", starts_at: "2026-08-10T01:00:00.000Z", ends_at: "2026-08-10T02:00:00.000Z", registration_status: "available", ticket_price_status: "free", ticket_price_minor: 0, ticket_id: "6" };
  const invalid = [
    { registration_status: "closed" }, { ticket_price_status: "paid", ticket_price_minor: 100 },
    { event_ref: "peatix-event://event/106", canonical_url: "https://peatix.com/event/107" },
    { canonical_url: "https://peatix.com:444/event/106" }, { ticket_id: 6 },
  ];
  for (const patch of invalid) {
    let calls = 0; const workflow = createPeatixDiscoveryWorkflow({ readAttendeeProfile: async () => { calls += 1; return {}; }, async submitOnPage() { calls += 1; }, async readStateOnPage() { calls += 1; } });
    const candidate = { ...base, ...patch };
    await assert.rejects(workflow.runDirectAction({ page: {}, candidate }));
    await assert.rejects(workflow.readProviderState({ page: {}, candidate }));
    assert.equal(calls, 0);
  }
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

test("Peatix default reader waits for the matching page-1 response before navigation", async () => {
  const calls = [];
  const responsePredicates = [];
  const searchResponse = {
    url() {
      return "https://peatix.com/search/events?dr=range&dr_from=2026-08-07&dr_to=2026-08-20&p=1&size=20";
    },
    ok() { return true; },
    status() { return 200; },
    async json() {
      return { json_data: { page: 1, events: [{ id: 201 }, { id: 202 }] } };
    },
  };
  const page = {
    waitForResponse(predicate, options) {
      calls.push("waitForResponse");
      responsePredicates.push({ predicate, options });
      return Promise.resolve(searchResponse);
    },
    async goto(url) {
      calls.push(["goto", url]);
    },
    async evaluate(_fn, argument) {
      calls.push(["evaluate", argument]);
      const id = argument.endsWith("/201") ? 201 : 202;
      return detail(id, { event: { name: `Default ${id}` } });
    },
  };
  const workflow = createPeatixDiscoveryWorkflow({
    now: () => NOW,
    isCalendarFree() { return true; },
  });

  const result = await workflow.discoverCandidates({ page, calendar: [] });

  assert.equal(calls[0], "waitForResponse");
  assert.equal(calls[1][0], "goto");
  assert.match(calls[1][1], /dr=2026-08-07:2026-08-20/);
  assert.match(calls[1][1], /[?&]p=1(?:&|$)/);
  assert.equal(responsePredicates.length, 1);
  const { predicate, options } = responsePredicates[0];
  assert.deepEqual(options, { timeout: 10_000 });
  assert.equal(predicate(searchResponse), true);
  assert.equal(predicate({
    url() { return searchResponse.url().replace("peatix.com", "example.com"); },
    ok() { return true; },
  }), false);
  assert.equal(predicate({
    url() { return searchResponse.url().replace("/search/events", "/search"); },
    ok() { return true; },
  }), false);
  assert.equal(predicate({
    url() { return searchResponse.url().replace("p=1", "p=2"); },
    ok() { return true; },
  }), false);
  assert.equal(predicate({
    url() { return searchResponse.url().replace("size=20", "size=10"); },
    ok() { return true; },
  }), false);
  assert.deepEqual(calls.slice(2), [
    ["goto", "https://peatix.com/event/201"],
    ["evaluate", "https://peatix.com/event/201"],
    ["goto", "https://peatix.com/event/202"],
    ["evaluate", "https://peatix.com/event/202"],
  ]);
  assert.deepEqual(result.map((candidate) => candidate.event_ref), [
    "peatix-event://event/201",
    "peatix-event://event/202",
  ]);
});

test("Peatix retries one page-1 read or navigation failure on the same page", async () => {
  for (const [waits, navigationErrors, id] of [
    [[new Error("private response timeout"), searchResponse(1, [{ id: 201 }])], [], 201],
    [[searchResponse(1, [{ id: 202 }]), searchResponse(1, [{ id: 202 }])], [new Error("private navigation error")], 202],
  ]) {
    const fixture = retryPage(waits, navigationErrors);
    const workflow = createPeatixDiscoveryWorkflow({ now: () => NOW,
      async readEventViewData() { return detail(id); }, isCalendarFree() { return true; } });
    const result = await workflow.discoverCandidates({ page: fixture.page, calendar: [] });
    assert.deepEqual([fixture.state.waits, fixture.state.navigations], [2, 2]);
    assert.equal(fixture.state.owners.every((owner) => owner === fixture.page), true);
    assert.deepEqual(result.map((candidate) => candidate.event_ref), [`peatix-event://event/${id}`]);
  }
});

test("Peatix page-1 retry is bounded and never covers row contract or page 2", async () => {
  for (const [waits, code, counts] of [
    [[new Error("private response timeout"), new Error("private response timeout")], "PEATIX_SEARCH_READ_FAILED", [2, 2]],
    [[searchResponse(1, [{ id: 0 }])], "PEATIX_SEARCH_ROWS_CONTRACT_FAILED", [1, 1]],
    [[searchResponse(1, Array.from({ length: 20 }, (_, id) => ({ id: id + 1 }))), new Error("private page-2 response timeout")], "PEATIX_SEARCH_READ_FAILED", [2, 2]],
  ]) {
    const fixture = retryPage(waits);
    await assert.rejects(
      createPeatixDiscoveryWorkflow({ now: () => NOW }).discoverCandidates({ page: fixture.page, calendar: [] }),
      (error) => error.code === code,
    );
    assert.deepEqual([fixture.state.waits, fixture.state.navigations], counts);
    assert.equal(fixture.state.owners.every((owner) => owner === fixture.page), true);
  }
});

test("Peatix default reader scans five 20-result pages and preserves global order", async () => {
  const pageEvents = Array.from({ length: 5 }, (_, pageIndex) => (
    Array.from({ length: 20 }, (_, eventIndex) => ({
      id: pageIndex * 20 + eventIndex + 1,
    }))
  ));
  const waitCalls = [];
  const searchNavigations = [];
  const detailCalls = [];
  const page = {
    waitForResponse(predicate) {
      const pageNumber = waitCalls.length + 1;
      waitCalls.push({ pageNumber, predicate });
      return Promise.resolve({
        url() {
          return `https://peatix.com/search/events?dr=range&dr_from=2026-08-07&dr_to=2026-08-20&p=${pageNumber}&size=20`;
        },
        ok() { return true; },
        status() { return 200; },
        async json() {
          return { json_data: { page: pageNumber, events: pageEvents[pageNumber - 1] } };
        },
      });
    },
    async goto(url) {
      if (url.includes("/search?")) searchNavigations.push(url);
    },
  };
  const workflow = createPeatixDiscoveryWorkflow({
    now: () => NOW,
    async readEventViewData(_page, canonicalUrl) {
      detailCalls.push(canonicalUrl);
      return detail(Number(canonicalUrl.split("/").pop()));
    },
    isCalendarFree() { return true; },
  });

  const result = await workflow.discoverCandidates({ page, calendar: [] });

  assert.equal(waitCalls.length, 5);
  assert.equal(searchNavigations.length, 5);
  assert.equal(detailCalls.length, 100);
  assert.equal(searchNavigations.some((url) => /[?&]p=6(?:&|$)/.test(url)), false);
  assert.deepEqual(detailCalls, Array.from({ length: 100 }, (_, index) => (
    `https://peatix.com/event/${index + 1}`
  )));
  assert.deepEqual(result.map((candidate) => candidate.event_ref), Array.from(
    { length: 100 }, (_, index) => `peatix-event://event/${index + 1}`,
  ));
});

test("Peatix default reader stops after the first short response page", async () => {
  const payloads = [
    Array.from({ length: 20 }, (_, index) => ({ id: index + 501 })),
    [{ id: 601 }, { id: 602 }, { id: 603 }],
  ];
  const waitPages = [];
  const searchNavigations = [];
  const page = {
    waitForResponse() {
      const pageNumber = waitPages.length + 1;
      waitPages.push(pageNumber);
      return Promise.resolve({
        url() {
          return `https://peatix.com/search/events?dr=range&dr_from=2026-08-07&dr_to=2026-08-20&p=${pageNumber}&size=20`;
        },
        ok() { return true; },
        async json() {
          return { json_data: { page: pageNumber, events: payloads[pageNumber - 1] } };
        },
      });
    },
    async goto(url) {
      if (url.includes("/search?")) searchNavigations.push(url);
    },
  };
  const workflow = createPeatixDiscoveryWorkflow({
    now: () => NOW,
    async readEventViewData(_page, canonicalUrl) {
      return detail(Number(canonicalUrl.split("/").pop()));
    },
    isCalendarFree() { return true; },
  });

  const result = await workflow.discoverCandidates({ page, calendar: [] });

  assert.deepEqual(waitPages, [1, 2]);
  assert.equal(searchNavigations.length, 2);
  assert.equal(searchNavigations.some((url) => /[?&]p=3(?:&|$)/.test(url)), false);
  assert.equal(result.length, 23);
});

test("Peatix default reader treats a valid empty response as one frozen zero audit", async () => {
  const audits = [];
  let detailCalls = 0;
  const page = {
    waitForResponse() {
      return Promise.resolve({
        url() {
          return "https://peatix.com/search/events?dr=range&dr_from=2026-08-07&dr_to=2026-08-20&p=1&size=20";
        },
        ok() { return true; },
        async json() { return { json_data: { page: 1, events: [] } }; },
      });
    },
    async goto() {},
  };
  const workflow = createPeatixDiscoveryWorkflow({
    now: () => NOW,
    async readEventViewData() { detailCalls += 1; return detail(1); },
    onDiscoveryAudit(audit) { audits.push(audit); },
  });

  const result = await workflow.discoverCandidates({ page, calendar: [] });

  assert.deepEqual(result, []);
  assert.equal(Object.isFrozen(result), true);
  assert.equal(detailCalls, 0);
  assert.equal(audits.length, 1);
  assert.deepEqual(audits[0], {
    observed_count: 0,
    normalized_count: 0,
    window_count: 0,
    free_open_count: 0,
    calendar_free_count: 0,
  });
  assert.equal(Object.isFrozen(audits[0]), true);
});

test("Peatix rejects more than 100 unique canonical search identities", async () => {
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

test("Peatix applies the search cap after canonical deduplication", async () => {
  const duplicate = binding(350);
  const workflow = createPeatixDiscoveryWorkflow({
    async readSearchBindings() {
      return Array.from({ length: 101 }, () => duplicate);
    },
    async readEventViewData(_page, canonicalUrl) {
      assert.equal(canonicalUrl, duplicate.canonical_url);
      return detail(350);
    },
    isCalendarFree() { return true; },
  });

  const result = await workflow.discoverCandidates({ page: {}, calendar: [] });

  assert.deepEqual(result.map((candidate) => candidate.event_ref), [
    "peatix-event://event/350",
  ]);
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
    ["legacy root payload", {
      async readSearchBindings() { return [oneBinding]; },
      async readEventViewData() { return { event: validDetail.json_data.event }; },
    }, "PEATIX_CANDIDATE_VALIDATION_FAILED"],
    ["title-only payload", {
      async readSearchBindings() { return [oneBinding]; },
      async readEventViewData() {
        const { name: _name, ...titleOnlyEvent } = validDetail.json_data.event;
        return { json_data: { event: { ...titleOnlyEvent, title: "Unmeasured title" } } };
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

test("Peatix default reader maps navigation, response, JSON, and contract failures safely", async () => {
  function response(payload, overrides = {}) {
    return {
      url() {
        return overrides.url || "https://peatix.com/search/events?dr=range&dr_from=2026-08-07&dr_to=2026-08-20&p=1&size=20";
      },
      ok() { return overrides.ok !== undefined ? overrides.ok : true; },
      status() { return overrides.status || 200; },
      async json() {
        if (overrides.jsonError) throw new Error(overrides.jsonError);
        return payload;
      },
    };
  }

  async function searchFailure(searchResponse, expectedCode, options = {}) {
    const workflow = createPeatixDiscoveryWorkflow({ now: () => NOW });
    await assert.rejects(
      workflow.discoverCandidates({
        page: {
          waitForResponse() {
            if (options.waitError) return Promise.reject(new Error(options.waitError));
            return Promise.resolve(searchResponse);
          },
          async goto() {
            if (options.navigationError) throw new Error(options.navigationError);
          },
        },
        calendar: [],
      }),
      (error) => error.code === expectedCode
        && error.message === "Peatix discovery stage failed"
        && !error.message.includes("private"),
    );
  }

  await searchFailure(
    response({ json_data: { page: 2, events: [] } }),
    "PEATIX_SEARCH_ROWS_CONTRACT_FAILED",
  );
  await searchFailure(
    response({ json_data: { page: 1, events: Array.from({ length: 21 }, (_, id) => ({ id: id + 1 })) } }),
    "PEATIX_SEARCH_ROWS_CONTRACT_FAILED",
  );
  await searchFailure(
    response({ json_data: { page: 1 } }),
    "PEATIX_SEARCH_ROWS_CONTRACT_FAILED",
  );
  await searchFailure(
    response({ json_data: { page: 1, events: [{ id: 0 }] } }),
    "PEATIX_SEARCH_ROWS_CONTRACT_FAILED",
  );
  await searchFailure(
    response({ json_data: { page: 1, events: [{ id: -1 }] } }),
    "PEATIX_SEARCH_ROWS_CONTRACT_FAILED",
  );
  await searchFailure(
    response({ json_data: { page: 1, events: [{ id: "201" }] } }),
    "PEATIX_SEARCH_ROWS_CONTRACT_FAILED",
  );
  await searchFailure(
    response({ json_data: { page: 1, events: [{ id: 201 }] }, }, { ok: false, status: 503 }),
    "PEATIX_SEARCH_READ_FAILED",
  );
  await searchFailure(
    response({ json_data: { page: 1, events: [{ id: 201 }] } }, { jsonError: "private JSON error" }),
    "PEATIX_SEARCH_READ_FAILED",
  );
  await searchFailure(
    null,
    "PEATIX_SEARCH_READ_FAILED",
    { waitError: "private response timeout" },
  );
  await searchFailure(
    response({ json_data: { page: 1, events: [{ id: 201 }] } }),
    "PEATIX_SEARCH_NAVIGATION_FAILED",
    { navigationError: "private navigation error" },
  );
});

test("Peatix default detail reader keeps safe navigation and JSON errors", async () => {
  const responseForPage = {
    url() {
      return "https://peatix.com/search/events?dr=range&dr_from=2026-08-07&dr_to=2026-08-20&p=1&size=20";
    },
    ok() { return true; },
    async json() { return { json_data: { page: 1, events: [{ id: 401 }] } }; },
  };

  let navigationCount = 0;
  await assert.rejects(
    createPeatixDiscoveryWorkflow({ now: () => NOW }).discoverCandidates({
      page: {
        waitForResponse() { return Promise.resolve(responseForPage); },
        async goto() {
          navigationCount += 1;
          if (navigationCount === 2) throw new Error("private detail navigation error");
        },
        async evaluate() { return detail(401); },
      },
      calendar: [],
    }),
    (error) => error.code === "PEATIX_DETAIL_NAVIGATION_FAILED"
      && error.message === "Peatix discovery stage failed",
  );

  let evaluateCount = 0;
  await assert.rejects(
    createPeatixDiscoveryWorkflow({ now: () => NOW }).discoverCandidates({
      page: {
        waitForResponse() { return Promise.resolve(responseForPage); },
        async goto() {},
        async evaluate() {
          evaluateCount += 1;
          if (evaluateCount === 1) throw new Error("private detail JSON error");
          return detail(401);
        },
      },
      calendar: [],
    }),
    (error) => error.code === "PEATIX_DETAIL_READ_FAILED"
      && error.message === "Peatix discovery stage failed",
  );
});
