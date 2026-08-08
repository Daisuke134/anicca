"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const { appendMobileMessage, listMobileMessages, encodeCursor, decodeCursor } = require("../lib/mobile-outbox.js");
const { createMemoryMobileStore } = require("../lib/mobile-store.js");

test("semantic outbox appends stable IDs and lists monotonic opaque cursor pages", async () => {
  const store = createMemoryMobileStore({ users: [{ uid: "user-a", product_locale: "en", home_address: "Tokyo" }] });
  const deps = { store, now: () => Date.parse("2026-08-08T00:00:00.000Z") };
  const scope = { uid: "user-a", productLocale: "en" };
  const first = await appendMobileMessage(scope, { type: "system", key: "chat.welcome", args: {}, userContent: { eventTitle: null, eventLocation: null } }, deps);
  const second = await appendMobileMessage(scope, { type: "system", key: "chat.no_upcoming_event", args: {}, userContent: { eventTitle: null, eventLocation: null } }, deps);
  assert.notEqual(first.id, second.id);
  const page = await listMobileMessages(scope, null, { ...deps, pageSize: 1 });
  assert.equal(page.messages.length, 1);
  assert.equal(page.messages[0].id, first.id);
  assert.equal(page.hasMore, true);
  assert.equal(decodeCursor(page.nextCursor), 1);
  const next = await listMobileMessages(scope, page.nextCursor, { ...deps, pageSize: 1 });
  assert.equal(next.messages[0].id, second.id);
  assert.equal(decodeCursor(next.messages[0].cursor), 2);
  assert.equal(encodeCursor(2), next.messages[0].cursor);
});

test("invalid cursor is a structured 400 and locale switch re-projects history without duplicating rows", async () => {
  const store = createMemoryMobileStore({ users: [{ uid: "user-a" }] });
  const scope = { uid: "user-a", productLocale: "en" };
  await appendMobileMessage(scope, { type: "system", key: "chat.welcome", args: {}, userContent: { eventTitle: "日本語", eventLocation: null } }, { store });
  await assert.rejects(() => listMobileMessages(scope, "cursor:v1:not-valid", { store }), (error) => error.code === "invalid_cursor" && error.status === 400);
  const ja = await listMobileMessages({ ...scope, productLocale: "ja" }, null, { store });
  assert.match(ja.messages[0].text, /チャット/u);
  const refetch = await listMobileMessages(scope, null, { store });
  assert.equal(new Set(refetch.messages.map((message) => message.id)).size, 1);
});
