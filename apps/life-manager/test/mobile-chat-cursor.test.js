"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const {
  fixture,
  assertGeneratedEnglish,
  assertIso,
  assertNoClientAuthority,
  assertOpaque,
} = require("./mobile-contract-support.js");

const ACTIONS = new Set(["reply", "refresh", "show_route"]);

test("English chat page is durable, chronological, and cursor-addressable", () => {
  const page = fixture("chat-page.json");
  assert.deepEqual(Object.keys(page).sort(), ["hasMore", "messages", "nextCursor"].sort());
  assert.equal(page.hasMore, false);
  assertOpaque(page.nextCursor, "chat next cursor", /^cursor:v1:[A-Za-z0-9_-]{8,}$/u);
  assert.equal(Array.isArray(page.messages), true);
  assert.equal(page.messages.length > 0, true);

  const ids = new Set();
  let previousCreatedAt = "";
  for (const message of page.messages) {
    assert.deepEqual(Object.keys(message).sort(), [
      "actions", "createdAt", "cursor", "id", "locale", "question", "route", "text", "type", "userContent",
    ].sort());
    assertOpaque(message.id, "chat message id");
    assert.equal(ids.has(message.id), false, `duplicate message id ${message.id}`);
    ids.add(message.id);
    assertOpaque(message.cursor, "message cursor", /^cursor:v1:[A-Za-z0-9_-]{8,}$/u);
    assertIso(message.createdAt, `message ${message.id} createdAt`);
    assert.equal(previousCreatedAt === "" || Date.parse(message.createdAt) >= Date.parse(previousCreatedAt), true);
    previousCreatedAt = message.createdAt;
    assert.equal(message.locale, "en");
    assert.equal(typeof message.text, "string");
    assert.equal(Array.isArray(message.actions), true);
    message.actions.forEach((action) => {
      assert.deepEqual(Object.keys(action).sort(), ["id", "label"].sort());
      assert.equal(ACTIONS.has(action.id), true);
      assert.equal(typeof action.label, "string");
    });
    assertGeneratedEnglish(message, `chat message ${message.id}`);
    assertNoClientAuthority(message, `chat message ${message.id}`);
  }
});

test("chat messages keep calendar-authored content separate and preserve route nullability", () => {
  const page = fixture("chat-page.json");
  const routeMessage = page.messages.find((message) => message.type === "route");
  assert.ok(routeMessage, "chat page must include a route message");
  assert.equal(routeMessage.route.status, "route_ready");
  assert.equal(typeof routeMessage.userContent.eventTitle, "string");
  assert.equal(typeof routeMessage.userContent.eventLocation, "string");
  for (const message of page.messages) {
    assert.equal(message.question === null || typeof message.question === "object", true);
    assert.equal(message.route === null || typeof message.route === "object", true);
  }
});
