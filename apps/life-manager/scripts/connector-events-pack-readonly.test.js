"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");

const { runConnectorEventsPackReadonly } = require("./connector-events-pack-readonly.js");

test("the host read-only entrypoint recovers auth and reads exhaustive inventory through one pack", async () => {
  const calls = [];
  const dailyDriver = { withLumaPage: async () => {} };
  const auth = {
    async ensureAuthenticated() {
      calls.push(["auth"]);
      return { status: "authenticated", recovered: true };
    },
  };
  const result = await runConnectorEventsPackReadonly({
    env: {
      GOG_ACCOUNT: "dais@example.test",
      DAIS_EMAIL: "dais@example.test",
      DAIS_LEGAL_NAME_ROMAJI: "Dais Example",
    },
    deps: {
      createDailyDriver() { return dailyDriver; },
      readLoginCode: async () => "123456",
      createAuth(input) {
        calls.push(["create-auth", input.dailyDriver, input.email, input.name]);
        return auth;
      },
      createPack(input) {
        calls.push(["create-pack", input.dailyDriver, input.auth]);
        return {
          async discoverTokyo() {
            calls.push(["discover"]);
            return { complete: true, rounds: 7, candidates: [{}, {}, {}] };
          },
        };
      },
    },
  });
  assert.deepEqual(result, {
    provider: "luma",
    transport: "cloakbrowser-daily-driver",
    authenticated: true,
    recovered: true,
    inventory_complete: true,
    inventory_rounds: 7,
    candidate_count: 3,
  });
  assert.deepEqual(calls.map((call) => call[0]), ["create-auth", "create-pack", "auth", "discover"]);
});

test("the entrypoint refuses different Gmail and Luma identities before browser access", async () => {
  let touched = false;
  await assert.rejects(runConnectorEventsPackReadonly({
    env: {
      GOG_ACCOUNT: "mail@example.test",
      DAIS_EMAIL: "other@example.test",
      DAIS_LEGAL_NAME_ROMAJI: "Dais Example",
    },
    deps: { createDailyDriver() { touched = true; } },
  }), /events pack unavailable/i);
  assert.equal(touched, false);
});
