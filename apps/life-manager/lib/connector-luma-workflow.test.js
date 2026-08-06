"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");

const { createLumaScriptFirstWorkflow } = require("./connector-luma-workflow.js");

function event(slug, overrides = {}) {
  return Object.freeze({
    provider: "luma",
    event_ref: `luma-event://event/${slug}`,
    canonical_url: `https://luma.com/${slug}`,
    title: `Event ${slug}`,
    starts_at: "2026-08-10T10:00:00.000Z",
    ends_at: "2026-08-10T11:00:00.000Z",
    event_status: "scheduled",
    rsvp_status: "available",
    ticket_price_status: "free",
    ticket_price_minor: 0,
    ...overrides,
  });
}

test("Luma discovery returns the first free open non-conflicting candidates in provider order", async () => {
  const page = Object.freeze({ page_id: "owned-page" });
  const inspected = [
    event("paid", { ticket_price_status: "paid", ticket_price_minor: 1000 }),
    event("conflict"),
    event("closed", { rsvp_status: "closed" }),
    event("free-first"),
    event("free-second", { rsvp_status: "approval_required" }),
  ];
  const workflow = createLumaScriptFirstWorkflow({
    async discoverOnPage(input) {
      assert.equal(input.page, page);
      return inspected;
    },
    isCalendarFree(candidate) { return candidate.event_ref !== "luma-event://event/conflict"; },
    async submitOnPage() { return { status: "registered" }; },
    async readProviderStateOnPage() { return { status: "registered" }; },
  });

  const result = await workflow.discoverCandidates({ page, calendar: { busy_intervals: [] } });

  assert.deepEqual(result.map((candidate) => candidate.event_ref), [
    "luma-event://event/free-first",
    "luma-event://event/free-second",
  ]);
});

test("Luma default conflict filter consumes the minimal runner busy interval array", async () => {
  const conflicting = event("calendar-conflict");
  const free = event("calendar-free", {
    starts_at: "2026-08-11T10:00:00.000Z",
    ends_at: "2026-08-11T11:00:00.000Z",
  });
  const workflow = createLumaScriptFirstWorkflow({
    async discoverOnPage() { return [conflicting, free]; },
    async submitOnPage() { return { status: "registered" }; },
    async readProviderStateOnPage() { return { status: "absent" }; },
  });

  const result = await workflow.discoverCandidates({
    page: {},
    calendar: [{
      kind: "timed",
      start_at: "2026-08-10T09:30:00.000Z",
      end_at: "2026-08-10T10:30:00.000Z",
    }],
  });

  assert.deepEqual(result.map((candidate) => candidate.event_ref), [free.event_ref]);
});

test("Luma candidates are limited to today and the next thirteen Tokyo days", async () => {
  const workflow = createLumaScriptFirstWorkflow({
    now: () => new Date("2026-08-07T08:30:00.000Z"),
    async discoverOnPage() {
      return [
        event("before-window", { starts_at: "2026-08-06T14:59:59.000Z", ends_at: "2026-08-06T15:30:00.000Z" }),
        event("today", { starts_at: "2026-08-06T15:00:00.000Z", ends_at: "2026-08-06T16:00:00.000Z" }),
        event("last-day", { starts_at: "2026-08-20T14:59:59.000Z", ends_at: "2026-08-20T15:30:00.000Z" }),
        event("after-window", { starts_at: "2026-08-20T15:00:00.000Z", ends_at: "2026-08-20T16:00:00.000Z" }),
      ];
    },
    async submitOnPage() { return { status: "registered" }; },
    async readProviderStateOnPage() { return { status: "absent" }; },
  });

  const result = await workflow.discoverCandidates({ page: {}, calendar: [] });
  assert.deepEqual(result.map((candidate) => candidate.event_ref), [
    "luma-event://event/today",
    "luma-event://event/last-day",
  ]);
});

test("Luma direct action uses the retained submit function without agent assistance", async () => {
  const calls = [];
  const page = Object.freeze({ page_id: "owned-page" });
  const selected = event("free-first");
  const workflow = createLumaScriptFirstWorkflow({
    async discoverOnPage() { return [selected]; },
    isCalendarFree() { return true; },
    async submitOnPage(suppliedPage, contract, dependencies) {
      calls.push({ suppliedPage, contract, dependencies });
      return Object.freeze({ status: "registered", effect_started: true });
    },
    async readProviderStateOnPage() { return { status: "registered" }; },
    async readLumaFormProfile() { return Object.freeze({ profile_version: 1 }); },
  });

  const result = await workflow.runDirectAction({ page, candidate: selected });

  assert.deepEqual(result, { status: "completed", method: "luma_direct_submit" });
  assert.equal(calls.length, 1);
  assert.equal(calls[0].suppliedPage, page);
  assert.equal(calls[0].contract.event_ref, selected.event_ref);
  assert.equal(calls[0].dependencies.agenticRegister, undefined);
  assert.equal(typeof calls[0].dependencies.readLumaFormProfile, "function");
});

test("unknown required fields and changed controls request bounded fallback without claiming success", async () => {
  for (const code of [
    "LUMA_REQUIRED_PROFILE_FIELD_UNAVAILABLE",
    "LUMA_FORM_SCHEMA_UNAVAILABLE",
    "LUMA_FORM_FILL_UNAVAILABLE",
    "LUMA_CONTROL_UNAVAILABLE",
    "LUMA_CONFIRM_UNAVAILABLE",
  ]) {
    const workflow = createLumaScriptFirstWorkflow({
      async discoverOnPage() { return [event("fallback")]; },
      isCalendarFree() { return true; },
      async submitOnPage() {
        const error = new Error("private provider text");
        error.code = code;
        throw error;
      },
      async readProviderStateOnPage() { return { status: "absent" }; },
    });

    assert.deepEqual(await workflow.runDirectAction({ page: {}, candidate: event("fallback") }), {
      status: "failed",
      safe_reason: "direct_action_requires_fallback",
    });
  }
});

test("parent readback normalizes only registered, pending, absent, and unavailable states", async () => {
  for (const [observed, expected] of [
    [{ status: "registered", provider_receipt_id: "receipt-1" }, { status: "registered", provider_receipt_id: "receipt-1" }],
    [{ status: "pending", provider_receipt_id: "receipt-2" }, { status: "pending", provider_receipt_id: "receipt-2" }],
    [{ status: "available" }, { status: "absent" }],
    [{ status: "closed" }, { status: "unavailable" }],
  ]) {
    const workflow = createLumaScriptFirstWorkflow({
      async discoverOnPage() { return []; },
      isCalendarFree() { return true; },
      async submitOnPage() { return { status: "registered" }; },
      async readProviderStateOnPage() { return observed; },
    });
    assert.deepEqual(
      await workflow.readProviderState({ page: {}, candidate: event("readback") }),
      expected,
    );
  }
});
