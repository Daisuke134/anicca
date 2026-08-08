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

test("semantic outbox rejects an unknown generated message key", async () => {
  const store = createMemoryMobileStore({ users: [{ uid: "user-a" }] });
  await assert.rejects(() => appendMobileMessage({ uid: "user-a" }, { key: "chat.arbitrary_prose" }, { store }), (error) => error.code === "message_key_invalid");
});

test("travel receipt keys are deduplicated by stable message id and expose only semanticKey", async () => {
  const store = createMemoryMobileStore({ users: [{ uid: "user-a" }] });
  const input = {
    id: "message:v1:travel-opaque", type: "system", key: "chat.travel_block_confirmed",
    args: { status: "existing", providerEventId: "lmaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", verification: "provider_readback" },
    userContent: { eventTitle: "Meeting", eventLocation: "Roppongi" },
  };
  const first = await appendMobileMessage({ uid: "user-a", productLocale: "en" }, input, { store });
  const second = await appendMobileMessage({ uid: "user-a", productLocale: "en" }, { ...input, args: { ...input.args, marker: "must-not-project" } }, { store });
  assert.equal(first.id, second.id);
  assert.equal(first.semanticKey, "chat.travel_block_confirmed");
  assert.equal(second.semanticKey, "chat.travel_block_confirmed");
  assert.equal(store._outbox.get("user-a").length, 1);
  assert.equal(JSON.stringify(second).includes("must-not-project"), false);
});
