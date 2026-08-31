"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const TRAVEL_WORDING = /routeMinutes|homeLocation|route_minutes|inbound_minutes|outbound_minutes/;

const NO_TRAVEL_FILES = [
  "connector-minimal-production.js",
  "connector-minimal-runner.js",
  "connector-minimal-operations.js",
  "connector-minimal-evidence.js",
  "calendar-candidate-gate.js",
  "connector-events-pack.js",
  "connector-open-date-planner.js",
  "connector-coverage-runtime-services.js",
  "connector-host-bridge.js",
];

test("the native wake path and the calendar candidate gate never reference travel time", () => {
  for (const name of NO_TRAVEL_FILES) {
    const source = fs.readFileSync(path.join(__dirname, name), "utf8");
    assert.doesNotMatch(source, TRAVEL_WORDING, `${name} must not reference travel time`);
  }
});

test("the route-minutes module was removed with its only caller", () => {
  const routeModulePath = path.join(__dirname, "connector-route-minutes.js");
  assert.equal(fs.existsSync(routeModulePath), false, "connector-route-minutes.js must not exist");
});

test("the Google Calendar write path syncs only the event itself, never travel/buffer wording", () => {
  const source = fs.readFileSync(path.join(__dirname, "connector-calendar-sync.js"), "utf8");
  assert.doesNotMatch(
    source,
    /routeMinutes|homeLocation|travel_minutes|inbound_minutes|outbound_minutes|buffer_minutes/i,
    "connector-calendar-sync.js must not reference travel/buffer",
  );
});
