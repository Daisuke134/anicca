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
