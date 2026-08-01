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
  });

  assert.deepEqual(await pack.discoverTokyo(), {
    candidates: [{ canonical_url: "https://luma.com/event-one" }],
  });
  assert.equal(await pack.inspectEvent("https://luma.com/event-one"), "detail");
  assert.equal(await pack.readDateInventory("coverage", { now: "now" }), "date-inventory");
  assert.equal(await pack.rankDatePreferences(
    "date-inventory", "2026-08-02", "AIを優先し全候補を残す", { apiKey: "fixture" },
  ), "preference-ranking");
  assert.equal(await pack.provider.submitRegistration({}), "registered");
  assert.equal(calls[1][1], calls[2][1]);
  assert.equal(calls[2][1], calls[3][1]);
  assert.deepEqual(calls.slice(4).map((call) => call[0]), [
    "date-inventory", "discover", "inspect", "rank-preferences",
  ]);
  assert.deepEqual(calls.at(-1)[1], {
    dateInventory: "date-inventory",
    date: "2026-08-02",
    preferences: "AIを優先し全候補を残す",
  });
});

test("pack construction fails closed without auth, driver, or evidence store", () => {
  assert.throws(() => createConnectorEventsPack({}), /events pack configuration unavailable/i);
  assert.throws(() => createConnectorEventsPack({
    dailyDriver: { withLumaPage: async () => {} },
    auth: { ensureAuthenticated: async () => ({ status: "authenticated" }) },
  }), /events pack configuration unavailable/i);
});
