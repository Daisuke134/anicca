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
      return "inventory";
    },
    inspect(options) {
      calls.push(["inspect", options.dailyDriver, options.canonicalUrl]);
      return "detail";
    },
  });

  assert.equal(await pack.discoverTokyo(), "inventory");
  assert.equal(await pack.inspectEvent("https://luma.com/event-one"), "detail");
  assert.equal(await pack.provider.submitRegistration({}), "registered");
  assert.equal(calls[1][1], calls[2][1]);
  assert.equal(calls[2][1], calls[3][1]);
});

test("pack construction fails closed without auth, driver, or evidence store", () => {
  assert.throws(() => createConnectorEventsPack({}), /events pack configuration unavailable/i);
  assert.throws(() => createConnectorEventsPack({
    dailyDriver: { withLumaPage: async () => {} },
    auth: { ensureAuthenticated: async () => ({ status: "authenticated" }) },
  }), /events pack configuration unavailable/i);
});
