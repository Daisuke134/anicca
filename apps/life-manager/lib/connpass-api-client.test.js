"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");

const { createConnpassApiClient } = require("./connpass-api-client.js");

test("missing API key fails before any connpass network access", async () => {
  let fetches = 0;
  assert.throws(() => createConnpassApiClient({
    apiKey: "",
    fetchImpl: async () => { fetches += 1; },
  }), /connpass API unavailable/i);
  assert.equal(fetches, 0);
});

test("search uses only official v2 GET with a secret header", async () => {
  const calls = [];
  const client = createConnpassApiClient({
    apiKey: "fixture-secret-api-key-1234567890",
    now: () => 2_000,
    sleep: async () => {},
    async fetchImpl(url, options) {
      calls.push([url, options]);
      return {
        ok: true,
        status: 200,
        async json() {
          return { results_returned: 0, results_available: 0, results_start: 1, events: [] };
        },
      };
    },
  });
  const result = await client.searchEvents({
    ymd: ["20260805"],
    keyword_or: ["AI", "startup"],
    count: 100,
    order: 2,
  });
  assert.equal(result.events.length, 0);
  const url = new URL(calls[0][0]);
  assert.equal(url.origin, "https://connpass.com");
  assert.equal(url.pathname, "/api/v2/events/");
  assert.deepEqual(url.searchParams.getAll("ymd"), ["20260805"]);
  assert.deepEqual(url.searchParams.getAll("keyword_or"), ["AI", "startup"]);
  assert.equal(calls[0][1].method, "GET");
  assert.equal(calls[0][1].headers["X-API-Key"], "fixture-secret-api-key-1234567890");
  assert.equal(JSON.stringify(result).includes("fixture-secret"), false);
});

test("unsupported query shapes cannot turn the client into a browser or write transport", async () => {
  const client = createConnpassApiClient({
    apiKey: "fixture-secret-api-key-1234567890",
    fetchImpl: async () => assert.fail("invalid query must fail before fetch"),
  });
  for (const query of [
    { url: "https://group.connpass.com/event/123/" },
    { method: "POST" },
    { count: 101 },
    { ymd: ["2026-08-05"] },
    { start: 0 },
  ]) {
    await assert.rejects(client.searchEvents(query), /connpass API query invalid/i);
  }
});

test("requests are serialized at the stricter five-second interval stated by the application form", async () => {
  const sleeps = [];
  const times = [10_000, 10_100, 11_000];
  const client = createConnpassApiClient({
    apiKey: "fixture-secret-api-key-1234567890",
    now: () => times.shift(),
    sleep: async (ms) => sleeps.push(ms),
    fetchImpl: async () => ({
      ok: true,
      status: 200,
      json: async () => ({ results_returned: 0, results_available: 0, results_start: 1, events: [] }),
    }),
  });
  await client.searchEvents({ keyword: ["AI"] });
  await client.searchEvents({ keyword: ["crypto"] });
  assert.deepEqual(sleeps, [4_900]);
});

test("HTTP errors and malformed payloads fail without reflecting the API key", async () => {
  for (const response of [
    { ok: false, status: 401, json: async () => ({ detail: "bad key" }) },
    { ok: true, status: 200, json: async () => ({ events: "not-array" }) },
  ]) {
    const client = createConnpassApiClient({
      apiKey: "fixture-secret-api-key-1234567890",
      fetchImpl: async () => response,
    });
    await assert.rejects(client.searchEvents({ keyword: ["AI"] }), (error) => {
      assert.equal(error.message, "connpass API unavailable");
      assert.equal(error.message.includes("fixture-secret"), false);
      return true;
    });
  }
});
