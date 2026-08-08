"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const {
  fixture,
  assertNoClientAuthority,
  assertOpaque,
} = require("./mobile-contract-support.js");

test("durable outbox stores a semantic key and structured args, not generated prose only", () => {
  const contract = fixture("contract.json");
  const row = fixture("semantic-outbox.json");
  assert.equal(Number.isSafeInteger(row.sequence), true);
  assert.equal(row.sequence > 0, true);
  assertOpaque(row.id, "semantic outbox message id");
  assert.equal(contract.semanticMessageKeys.includes(row.key), true);
  assert.equal(typeof row.args, "object");
  assert.equal(Array.isArray(row.args), false);
  assert.equal(Object.hasOwn(row, "text"), false);
  assert.deepEqual(Object.keys(row.userContent).sort(), ["eventLocation", "eventTitle"]);
  assertNoClientAuthority(row, "semantic outbox row");
});

test("English demo analysis binds origin and destination to Calendar event facts", () => {
  const contract = fixture("contract.json");
  assert.equal(contract.demo.calendarConnection, "preconnected_session_restore");
  assert.equal(contract.demo.oauthUi, false);
  assert.equal(contract.demo.softPaywall, false);
  assert.equal(contract.analysis.originSource, "most_recent_physical_calendar_event");
  assert.equal(contract.analysis.destinationSource, "next_event_location");
  assert.equal(contract.analysis.foregroundDetectionMaxSeconds, 60);
  assert.equal(contract.analysis.calendarTravelBlock, "backend_owned_exactly_once_by_idempotency_key");
});
