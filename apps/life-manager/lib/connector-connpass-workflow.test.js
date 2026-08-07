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

test("Connpass direct action and parent readback use the supplied owned page", async () => {
  const page = Object.freeze({ page_id: "same-owned-page" });
  const candidate = event(105);
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
