"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");

const { makeGogRouteMinutes } = require("./maps-gog.js");

test("gog Maps transit directions become exact whole minutes", async () => {
  const calls = [];
  const routeMinutes = makeGogRouteMinutes({
    bin: "/opt/homebrew/bin/gog",
    run(args) {
      calls.push(args);
      return JSON.stringify({
        directions: {
          status: "OK",
          routes: [{
            legs: [
              { duration: { text: "31 mins", value: 1_830 } },
              { duration: { text: "4 mins", value: 240 } },
            ],
          }],
        },
      });
    },
  });

  assert.equal(await routeMinutes({
    from: "Tokyo Station",
    to: "Shibuya Station",
    anchor_at: "2026-08-05T12:00:00+09:00",
  }), 35);
  assert.deepEqual(calls, [[
    "maps", "directions",
    "--origin=Tokyo Station",
    "--destination=Shibuya Station",
    "--mode=transit",
    "--language=ja",
    "--region=jp",
    "--json",
    "--no-input",
    "--enable-commands=maps.directions",
  ]]);
});

test("gog Maps routing fails closed for missing routes, malformed output, and unsafe inputs", async () => {
  const make = (value) => makeGogRouteMinutes({ run: () => value });
  await assert.rejects(
    make(JSON.stringify({ directions: { status: "ZERO_RESULTS", routes: [] } }))({ from: "A", to: "B" }),
    /Connector route unavailable/i,
  );
  await assert.rejects(make("not json")({ from: "A", to: "B" }), /Connector route unavailable/i);
  await assert.rejects(make("{}")({ from: "-A", to: "B" }), /Connector route invalid/i);
  await assert.rejects(make("{}")({ from: "A\nsecret", to: "B" }), /Connector route invalid/i);
  await assert.rejects(make("{}")({ from: "A", to: "B", anchor_at: "not-time" }), /Connector route invalid/i);
});

test("same location needs no provider call", async () => {
  let calls = 0;
  const routeMinutes = makeGogRouteMinutes({ run() { calls += 1; } });
  assert.equal(await routeMinutes({ from: "Tokyo", to: "  Tokyo  " }), 0);
  assert.equal(calls, 0);
});
