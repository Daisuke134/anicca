"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");

const { createConnpassScriptFirstWorkflow } = require("./connector-connpass-workflow.js");

function event(id, overrides = {}) {
  return Object.freeze({
    provider: "connpass",
    event_ref: `connpass-event://event/${id}`,
    canonical_url: `https://tokyo-builders.connpass.com/event/${id}/`,
    title: `Event ${id}`,
    starts_at: "2026-08-10T10:00:00.000Z",
    ends_at: "2026-08-10T11:00:00.000Z",
    registration_status: "available",
    ticket_price_status: "free",
    ticket_price_minor: 0,
    ...overrides,
  });
}

test("Connpass discovery keeps provider order and only returns eligible fourteen-day candidates", async () => {
  const page = Object.freeze({ page_id: "same-owned-page" });
  const workflow = createConnpassScriptFirstWorkflow({
    now: () => new Date("2026-08-07T08:30:00.000Z"),
    async discoverOnPage(input) {
      assert.equal(input.page, page);
      return [
        event(101, { starts_at: "2026-08-21T10:00:00.000Z", ends_at: "2026-08-21T11:00:00.000Z" }),
        event(102, { ticket_price_status: "paid", ticket_price_minor: 1000 }),
        event(103, { registration_status: "closed" }),
        event(104),
        event(105),
      ];
    },
    isCalendarFree(candidate) { return candidate.event_ref !== "connpass-event://event/104"; },
    async submitOnPage() { return { status: "registered" }; },
    async readStateOnPage() { return { state: "registered" }; },
  });

  const result = await workflow.discoverCandidates({ page, calendar: [] });

  assert.deepEqual(result.map((candidate) => candidate.event_ref), ["connpass-event://event/105"]);
});

test("Connpass recovery stably returns registered before available candidates", async () => {
  const registered = event(106, { registration_status: "registered" });
  const availableA = event(107);
  const availableB = event(108);
  const workflow = createConnpassScriptFirstWorkflow({
    now: () => new Date("2026-08-07T08:30:00.000Z"),
    async discoverOnPage() { return [availableA, registered, availableB]; },
  });
  const result = await workflow.discoverCandidates({ page: {}, calendar: [] });

  assert.deepEqual(result, [registered, availableA, availableB]);
});

test("Connpass registered recovery bypasses Calendar conflict while available remains blocked", async () => {
  const registered = event(109, { registration_status: "registered" });
  const available = event(110);
  const checked = [];
  const workflow = createConnpassScriptFirstWorkflow({
    now: () => new Date("2026-08-07T08:30:00.000Z"),
    async discoverOnPage() { return [registered, available]; },
    async isCalendarFree(candidate) { checked.push(candidate.event_ref); return false; },
  });

  const result = await workflow.discoverCandidates({ page: {}, calendar: [{ kind: "timed", start_at: registered.starts_at, end_at: registered.ends_at }] });

  assert.deepEqual(result.map((candidate) => candidate.event_ref), [registered.event_ref]);
  assert.deepEqual(checked, [available.event_ref]);
});

test("Connpass recovery audit counts registered separately from free-open candidates", async () => {
  const audits = [];
  const registered = event(111, { registration_status: "registered" });
  const available = event(112);
  const paid = event(113, { registration_status: "unknown", ticket_price_status: "paid", ticket_price_minor: 1000 });
  const outsideRegistered = event(115, { registration_status: "registered", starts_at: "2026-08-22T10:00:00.000Z", ends_at: "2026-08-22T11:00:00.000Z" });
  const workflow = createConnpassScriptFirstWorkflow({
    now: () => new Date("2026-08-07T08:30:00.000Z"),
    async discoverOnPage() { return [registered, available, paid, outsideRegistered]; },
    onDiscoveryAudit(audit) { audits.push(audit); },
  });

  const result = await workflow.discoverCandidates({ page: {}, calendar: [] });

  assert.deepEqual(result.map((candidate) => candidate.event_ref), [registered.event_ref, available.event_ref]);
  assert.deepEqual(audits, [{
    observed_count: 4, normalized_count: 4, window_count: 3,
    free_open_count: 1, calendar_free_count: 2,
  }]);
});

test("Connpass discovery reports the ordered eligibility gate counts", async () => {
  const audits = [];
  const workflow = createConnpassScriptFirstWorkflow({
    now: () => new Date("2026-08-07T08:30:00.000Z"),
    async discoverOnPage() {
      return [
        event(201, { starts_at: "2026-08-21T16:00:00.000Z", ends_at: "2026-08-21T17:00:00.000Z" }),
        event(202, { ticket_price_status: "paid", ticket_price_minor: 1000 }),
        event(203, { registration_status: "closed" }),
        event(204),
        event(205),
      ];
    },
    isCalendarFree(candidate) { return candidate.event_ref !== "connpass-event://event/204"; },
    onDiscoveryAudit(audit) { audits.push(audit); },
  });

  await workflow.discoverCandidates({ page: {}, calendar: [] });

  assert.deepEqual(audits, [{
    observed_count: 5,
    normalized_count: 5,
    window_count: 4,
    free_open_count: 2,
    calendar_free_count: 1,
  }]);
});

test("Connpass direct action and parent readback use the supplied owned page", async () => {
  const candidate = event(105);
  const page = Object.freeze({ page_id: "same-owned-page", url() { return candidate.canonical_url; } });
  const calls = [];
  const workflow = createConnpassScriptFirstWorkflow({
    async discoverOnPage() { return []; },
    async submitOnPage(suppliedPage, suppliedCandidate) {
      calls.push(["submit", suppliedPage, suppliedCandidate]);
      return { status: "pending", effect_started: true };
    },
    async readStateOnPage(suppliedPage) {
      calls.push(["readback", suppliedPage]);
      return { state: "pending" };
    },
  });

  assert.deepEqual(await workflow.runDirectAction({ page, candidate }), {
    status: "completed", method: "connpass_direct_submit",
  });
  assert.deepEqual(await workflow.readProviderState({ page, candidate }), { status: "pending" });
  assert.equal(calls.every((entry) => entry[1] === page), true);
});

test("Connpass direct action requires exact canonical URL without browser side effects", async () => {
  const candidate = event(106);
  const cases = [
    ["join", `${candidate.canonical_url}join/`],
    ["complete", `${candidate.canonical_url}complete/`],
    ["query", `${candidate.canonical_url}?submitted=1`],
    ["hash", `${candidate.canonical_url}#submitted`],
    ["wrong-event", "https://tokyo-builders.connpass.com/event/108/"],
    ["about-blank", "about:blank"],
    ["missing-url", null],
    ["throwing-url", "throw"],
  ];
  for (const [label, resultingUrl] of cases) {
    let currentUrl = candidate.canonical_url;
    let submitCalls = 0;
    const forbiddenCalls = [];
    const page = label === "missing-url" ? {} : {
      url() {
        if (resultingUrl === "throw") throw new Error("url unavailable");
        return currentUrl;
      },
      goto() { forbiddenCalls.push("goto"); },
      getByRole() { forbiddenCalls.push("click"); },
      readCredentials() { forbiddenCalls.push("credentials"); },
    };
    const workflow = createConnpassScriptFirstWorkflow({
      async discoverOnPage() { return []; },
      async submitOnPage() {
        submitCalls += 1;
        currentUrl = resultingUrl;
        return { status: "registered" };
      },
    });
    assert.deepEqual(
      await workflow.runDirectAction({ page, candidate }),
      { status: "failed", safe_reason: "direct_action_unverified" },
      label,
    );
    assert.equal(submitCalls, 1, label);
    assert.deepEqual(forbiddenCalls, [], label);
  }
});

test("Connpass default discovery reuses one page across two calendar months and event details", async () => {
  const navigations = [];
  const page = {
    current: "",
    async goto(url) { this.current = url; navigations.push(url); },
  };
  const workflow = createConnpassScriptFirstWorkflow({
    now: () => new Date("2026-08-27T03:00:00.000Z"),
    async readCalendarBindings(suppliedPage) {
      assert.equal(suppliedPage, page);
      return suppliedPage.current.includes("ym=202608") ? [{
        event_ref: "connpass-event://event/201",
        canonical_url: "https://tokyo-builders.connpass.com/event/201/",
        calendar_date: "2026-08-30",
      }] : [{
        event_ref: "connpass-event://event/202",
        canonical_url: "https://tokyo-builders.connpass.com/event/202/",
        calendar_date: "2026-09-03",
      }];
    },
    async readEventDetail(suppliedPage) {
      assert.equal(suppliedPage, page);
      const id = suppliedPage.current.includes("/201/") ? 201 : 202;
      const date = id === 201 ? "2026-08-30" : "2026-09-03";
      return {
        ...event(id, { starts_at: `${date}T10:00:00.000Z`, ends_at: `${date}T11:00:00.000Z` }),
        controls: ["このイベントに申し込む"], offers: [{ price: "0", priceCurrency: "JPY" }],
        venue_name: "Public venue", address: "Tokyo",
      };
    },
    async submitOnPage() { return { status: "registered" }; },
    async readStateOnPage() { return { state: "registered" }; },
  });

  const result = await workflow.discoverCandidates({ page, calendar: [] });

  assert.deepEqual(result.map((candidate) => candidate.event_ref), [
    "connpass-event://event/201", "connpass-event://event/202",
  ]);
  assert.equal(navigations.filter((url) => url.includes("/calendar/")).length, 2);
  assert.equal(navigations.filter((url) => url.includes("/event/")).length, 2);
});

test("Connpass default discovery identifies the exact failed browser stage safely", async () => {
  const workflow = createConnpassScriptFirstWorkflow({
    now: () => new Date("2026-08-07T03:00:00.000Z"),
    async readCalendarBindings() { return []; },
    async readEventDetail() { return {}; },
    async submitOnPage() { return { status: "registered" }; },
    async readStateOnPage() { return { state: "registered" }; },
  });
  const page = { async goto() { throw new Error("private browser error"); } };

  await assert.rejects(
    workflow.discoverCandidates({ page, calendar: [] }),
    (error) => error.code === "CONNPASS_CALENDAR_NAVIGATION_FAILED"
      && error.message === "Connpass discovery stage failed",
  );
});

test("Connpass accepts a verified same-event redirect from group subdomain to root host", async () => {
  const page = { current: "", async goto(url) { this.current = url; } };
  const workflow = createConnpassScriptFirstWorkflow({
    now: () => new Date("2026-08-07T03:00:00.000Z"),
    async readCalendarBindings() {
      return [{ event_ref: "connpass-event://event/393711", canonical_url: "https://group.connpass.com/event/393711/", calendar_date: "2026-08-10" }];
    },
    async readEventDetail() {
      return {
        event_ref: "connpass-event://event/393711", canonical_url: "https://connpass.com/event/393711/",
        title: "Public event", starts_at: "2026-08-10T10:00:00.000Z", ends_at: "2026-08-10T11:00:00.000Z",
        venue_name: "Public venue", address: "Tokyo", controls: ["このイベントに申し込む"],
        offers: [{ price: "0", priceCurrency: "JPY" }], price_labels: ["参加費 無料"],
      };
    },
    async submitOnPage() { return { status: "registered" }; },
    async readStateOnPage() { return { state: "registered" }; },
  });

  const result = await workflow.discoverCandidates({ page, calendar: [] });
  assert.equal(result[0].canonical_url, "https://connpass.com/event/393711/");
});

test("Connpass reports a safe code when detail redirects to a different event identity", async () => {
  const page = { async goto() {} };
  const workflow = createConnpassScriptFirstWorkflow({
    now: () => new Date("2026-08-07T03:00:00.000Z"),
    async readCalendarBindings() {
      return [{ event_ref: "connpass-event://event/393711", canonical_url: "https://connpass.com/event/393711/", calendar_date: "2026-08-10" }];
    },
    async readEventDetail() {
      return {
        event_ref: "connpass-event://event/999999", canonical_url: "https://connpass.com/event/999999/",
        title: "Public event", starts_at: "2026-08-10T10:00:00.000Z", ends_at: "2026-08-10T11:00:00.000Z",
        venue_name: "Public venue", address: "Tokyo", controls: ["このイベントに申し込む"],
        offers: [{ price: "0", priceCurrency: "JPY" }], price_labels: ["参加費 無料"],
      };
    },
    async submitOnPage() { return { status: "registered" }; },
    async readStateOnPage() { return { state: "registered" }; },
  });

  await assert.rejects(
    workflow.discoverCandidates({ page, calendar: [] }),
    (error) => error.code === "CONNPASS_DETAIL_IDENTITY_MISMATCH_FAILED",
  );
});

test("Connpass distinguishes binding validation from candidate validation", async () => {
  const common = {
    now: () => new Date("2026-08-07T03:00:00.000Z"),
    async submitOnPage() { return { status: "registered" }; },
    async readStateOnPage() { return { state: "registered" }; },
  };
  const bindingWorkflow = createConnpassScriptFirstWorkflow({
    ...common,
    async readCalendarBindings() {
      return [{ event_ref: "connpass-event://event/393711", canonical_url: "https://example.com/event/393711/", calendar_date: "2026-08-10" }];
    },
    async readEventDetail() { return {}; },
  });
  await assert.rejects(
    bindingWorkflow.discoverCandidates({ page: { async goto() {} }, calendar: [] }),
    (error) => error.code === "CONNPASS_CALENDAR_BINDING_VALIDATION_FAILED",
  );

  const candidateWorkflow = createConnpassScriptFirstWorkflow({
    ...common,
    async discoverOnPage() { return [{ provider: "connpass" }]; },
  });
  await assert.rejects(
    candidateWorkflow.discoverCandidates({ page: {}, calendar: [] }),
    (error) => error.code === "CONNPASS_CANDIDATE_VALIDATION_FAILED",
  );
});

test("Connpass classifies remaining parent discovery contracts without leaking errors", async () => {
  const common = {
    now: () => new Date("2026-08-07T03:00:00.000Z"),
    async submitOnPage() { return { status: "registered" }; },
    async readStateOnPage() { return { state: "registered" }; },
  };
  const rowsWorkflow = createConnpassScriptFirstWorkflow({
    ...common,
    async readCalendarBindings() { return Array.from({ length: 5001 }, () => ({})); },
    async readEventDetail() { return {}; },
  });
  await assert.rejects(
    rowsWorkflow.discoverCandidates({ page: { async goto() {} }, calendar: [] }),
    (error) => error.code === "CONNPASS_CALENDAR_ROWS_CONTRACT_FAILED",
  );

  const resultWorkflow = createConnpassScriptFirstWorkflow({
    ...common,
    async discoverOnPage() { return {}; },
  });
  await assert.rejects(
    resultWorkflow.discoverCandidates({ page: {}, calendar: [] }),
    (error) => error.code === "CONNPASS_DISCOVERY_RESULT_CONTRACT_FAILED",
  );

  const calendarWorkflow = createConnpassScriptFirstWorkflow({
    ...common,
    async discoverOnPage() { return [event(301)]; },
    async isCalendarFree() { throw new Error("private calendar error"); },
  });
  await assert.rejects(
    calendarWorkflow.discoverCandidates({ page: {}, calendar: [] }),
    (error) => error.code === "CONNPASS_CALENDAR_CONFLICT_CHECK_FAILED",
  );
});

test("Connpass filters large calendar noise before enforcing the eligible binding cap", async () => {
  const noise = Array.from({ length: 501 }, (_, index) => ({
    event_ref: `connpass-event://event/${500000 + index}`,
    canonical_url: `https://connpass.com/event/${500000 + index}/`,
    calendar_date: "2026-07-01",
  }));
  const workflow = createConnpassScriptFirstWorkflow({
    now: () => new Date("2026-08-07T03:00:00.000Z"),
    async readCalendarBindings() {
      return [...noise, {
        event_ref: "connpass-event://event/393711",
        canonical_url: "https://connpass.com/event/393711/",
        calendar_date: "2026-08-10",
      }];
    },
    async readEventDetail() {
      return {
        event_ref: "connpass-event://event/393711", canonical_url: "https://connpass.com/event/393711/",
        title: "Public event", starts_at: "2026-08-10T10:00:00.000Z", ends_at: "2026-08-10T11:00:00.000Z",
        venue_name: "Public venue", address: "Tokyo", controls: ["このイベントに申し込む"],
        offers: [{ price: "0", priceCurrency: "JPY" }], price_labels: ["参加費 無料"],
      };
    },
    async submitOnPage() { return { status: "registered" }; },
    async readStateOnPage() { return { state: "registered" }; },
  });

  const result = await workflow.discoverCandidates({ page: { async goto() {} }, calendar: [] });
  assert.deepEqual(result.map((candidate) => candidate.event_ref), ["connpass-event://event/393711"]);
});
