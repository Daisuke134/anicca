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
          async readDateInventory(coverage, options) {
            calls.push(["date-inventory", coverage, options]);
            return {
              complete: true,
              window_start_date: "2026-08-02",
              window_end_date: "2026-08-22",
              source_inventory_rounds: 7,
              counts: {
                discovered: 3,
                inspected: 3,
                scheduled_in_person_in_window: 2,
                excluded: 1,
                dates_with_candidates: 2,
                dates_without_candidates: 19,
              },
            };
          },
        };
      },
      now: () => "2026-08-02T01:00:00.000Z",
    },
  });
  assert.deepEqual(result, {
    provider: "luma",
    transport: "cloakbrowser-daily-driver",
    authenticated: true,
    recovered: true,
    inventory_complete: true,
    window_start_date: "2026-08-02",
    window_end_date: "2026-08-22",
    inventory_rounds: 7,
    discovered_candidate_count: 3,
    inspected_detail_count: 3,
    scheduled_in_person_in_window_count: 2,
    excluded_detail_count: 1,
    dates_with_candidates: 2,
    dates_without_candidates: 19,
  });
  assert.deepEqual(calls.map((call) => call[0]), ["create-auth", "create-pack", "auth", "date-inventory"]);
  assert.equal(calls.at(-1)[1].days.length, 21);
  assert.equal(calls.at(-1)[2].now, "2026-08-02T01:00:00.000Z");
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
