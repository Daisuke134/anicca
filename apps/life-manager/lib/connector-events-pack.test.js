"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");

const { createConnectorEventsPack } = require("./connector-events-pack.js");

test("the pack gives discovery and RSVP one auth-aware daily-driver", async () => {
  const calls = [];
  const dailyDriver = { withLumaPage: async () => {} };
  const auth = { ensureAuthenticated: async () => ({ status: "authenticated" }) };
  const pack = createConnectorEventsPack({
    dailyDriver,
    auth,
    evidenceStore: { record: async () => {} },
    createAuthAwareDriver(input) {
      calls.push(["auth-aware", input.dailyDriver, input.auth]);
      return { withLumaPage: async () => "shared" };
    },
    createProvider(input) {
      calls.push(["provider", input.dailyDriver]);
      return {
        inspectRegistration: async () => "absent",
        submitRegistration: async () => "registered",
      };
    },
    discover(options) {
      calls.push(["discover", options.dailyDriver]);
      return { candidates: [{ canonical_url: "https://luma.com/event-one" }] };
    },
    inspect(options) {
      calls.push(["inspect", options.dailyDriver, options.canonicalUrl]);
      return "detail";
    },
    async inspectDateInventory(options) {
      calls.push(["date-inventory", options.coverage, options.now]);
      const inventory = await options.discoverTokyo();
      await options.inspectEvent(inventory.candidates[0].canonical_url);
      return "date-inventory";
    },
    rankPreferences(input, options) {
      calls.push(["rank-preferences", input, options]);
      return "preference-ranking";
    },
    evaluateGoalSerendipity(input, options) {
      calls.push(["goal-serendipity", input, options]);
      return "goal-serendipity";
    },
    createSourceCapabilities(input) {
      calls.push(["source-capabilities", input]);
      return "source-capabilities";
    },
    planSourceHandoff(input) {
      calls.push(["source-handoff-plan", input]);
      return "source-handoff-plan";
    },
    executeSourceHandoff(input) {
      calls.push(["source-handoff-execute", input]);
      return "source-handoff-result";
    },
    createConnpassClient(input) {
      calls.push(["connpass-client", input]);
      return "connpass-client";
    },
  });

  assert.deepEqual(await pack.discoverTokyo(), {
    candidates: [{ canonical_url: "https://luma.com/event-one" }],
  });
  assert.equal(await pack.inspectEvent("https://luma.com/event-one"), "detail");
  assert.equal(await pack.readDateInventory("coverage", { now: "now" }), "date-inventory");
  assert.equal(await pack.rankDatePreferences(
    "date-inventory", "2026-08-02", "AIを優先し全候補を残す", { apiKey: "fixture" },
  ), "preference-ranking");
  assert.equal(await pack.evaluateDateGoals(
    "date-inventory", "preference-ranking", "Dais goals", { apiKey: "fixture" },
  ), "goal-serendipity");
  assert.equal(await pack.handoffEventSource(
    "2026-08-05", "luma-exhaustion", { connpassApiKey: "fixture-secret-api-key-1234567890" },
  ), "source-handoff-result");
  assert.equal(await pack.provider.submitRegistration({}), "registered");
  assert.equal(calls[1][1], calls[2][1]);
  assert.equal(calls[2][1], calls[3][1]);
  assert.deepEqual(calls.slice(4).map((call) => call[0]), [
    "date-inventory", "discover", "inspect", "rank-preferences", "goal-serendipity",
    "source-capabilities", "source-handoff-plan", "connpass-client", "source-handoff-execute",
  ]);
  assert.deepEqual(calls[7][1], {
    dateInventory: "date-inventory",
    date: "2026-08-02",
    preferences: "AIを優先し全候補を残す",
  });
  assert.deepEqual(calls[8][1], {
    dateInventory: "date-inventory",
    preferenceRanking: "preference-ranking",
    goals: "Dais goals",
  });
  assert.deepEqual(calls.at(-1)[1], {
    plan: "source-handoff-plan",
    connpassClient: "connpass-client",
  });
  assert.deepEqual(calls.at(-4)[1], { connpassApiKey: "fixture-secret-api-key-1234567890" });
  assert.deepEqual(calls.at(-3)[1], {
    date: "2026-08-05",
    lumaOutcome: "luma-exhaustion",
    capabilities: "source-capabilities",
  });
  assert.deepEqual(calls.at(-2)[1], { apiKey: "fixture-secret-api-key-1234567890" });
});

test("source handoff with no connpass key never constructs an API client", async () => {
  let clientCreated = false;
  const pack = createConnectorEventsPack({
    dailyDriver: { withLumaPage: async () => {} },
    auth: { ensureAuthenticated: async () => ({ status: "authenticated" }) },
    evidenceStore: { record: async () => {} },
    createAuthAwareDriver: () => ({ withLumaPage: async () => {} }),
    createProvider: () => ({ inspectRegistration: async () => {}, submitRegistration: async () => {} }),
    createSourceCapabilities: () => "missing-key-capabilities",
    planSourceHandoff: () => "missing-key-plan",
    createConnpassClient() { clientCreated = true; },
    executeSourceHandoff(input) {
      assert.deepEqual(input, { plan: "missing-key-plan", connpassClient: undefined });
      return "open";
    },
  });
  assert.equal(await pack.handoffEventSource("2026-08-05", "exhausted", { connpassApiKey: "" }), "open");
  assert.equal(clientCreated, false);
});

test("the pack exposes the one verified same-day candidate state machine", async () => {
  const calls = [];
  const candidates = [
    { event_ref: "luma-event://event/a", canonical_url: "https://luma.com/a" },
    { event_ref: "luma-event://event/b", canonical_url: "https://luma.com/b" },
  ];
  const attempt = async () => ({ status: "not_eligible" });
  const pack = createConnectorEventsPack({
    dailyDriver: { withLumaPage: async () => {} },
    auth: { ensureAuthenticated: async () => ({ status: "authenticated" }) },
    evidenceStore: { record: async () => {} },
    createAuthAwareDriver: () => ({ withLumaPage: async () => {} }),
    createProvider: () => ({ inspectRegistration: async () => {}, submitRegistration: async () => {} }),
    runCandidateSequence(input) {
      calls.push(input);
      return "verified-sequence-result";
    },
  });
  assert.equal(await pack.runSameDayCandidates(candidates, attempt), "verified-sequence-result");
  assert.deepEqual(calls, [{ candidates, attempt }]);
});

test("the pack exposes the rolling coverage continuation state machine", () => {
  const calls = [];
  const pack = createConnectorEventsPack({
    dailyDriver: { withLumaPage: async () => {} },
    auth: { ensureAuthenticated: async () => ({ status: "authenticated" }) },
    evidenceStore: { record: async () => {} },
    createAuthAwareDriver: () => ({ withLumaPage: async () => {} }),
    createProvider: () => ({ inspectRegistration: async () => {}, submitRegistration: async () => {} }),
    planCoverageContinuation(input) { calls.push(input); return "continuation"; },
  });
  assert.equal(pack.planCoverageContinuation("coverage", ["outcome"], "now"), "continuation");
  assert.deepEqual(calls, [{ coverage: "coverage", observedOutcomes: ["outcome"], now: "now" }]);
});

test("the pack runs only calendar-eligible candidates through the same-day state machine", async () => {
  const calls = [];
  const attempt = async () => ({ status: "not_eligible" });
  const pack = createConnectorEventsPack({
    dailyDriver: { withLumaPage: async () => {} },
    auth: { ensureAuthenticated: async () => ({ status: "authenticated" }) },
    evidenceStore: { record: async () => {} },
    createAuthAwareDriver: () => ({ withLumaPage: async () => {} }),
    createProvider: () => ({ inspectRegistration: async () => {}, submitRegistration: async () => {} }),
    selectCalendarEligibleCandidates(dateInventory, calendarGate) {
      calls.push(["select", dateInventory, calendarGate]);
      return [{ event_ref: "luma-event://event/free", canonical_url: "https://luma.com/free" }];
    },
    runCandidateSequence(input) { calls.push(["run", input]); return "sequence"; },
  });
  assert.equal(await pack.runCalendarGatedSameDay("inventory", "gate", attempt), "sequence");
  assert.deepEqual(calls, [
    ["select", "inventory", "gate"],
    ["run", { candidates: [{ event_ref: "luma-event://event/free", canonical_url: "https://luma.com/free" }], attempt }],
  ]);
});

test("pack construction fails closed without auth, driver, or evidence store", () => {
  assert.throws(() => createConnectorEventsPack({}), /events pack configuration unavailable/i);
  assert.throws(() => createConnectorEventsPack({
    dailyDriver: { withLumaPage: async () => {} },
    auth: { ensureAuthenticated: async () => ({ status: "authenticated" }) },
  }), /events pack configuration unavailable/i);
});
