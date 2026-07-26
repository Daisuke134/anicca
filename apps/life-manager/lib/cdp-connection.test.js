// cdp-connection.test.js — the CDP sequencing the 11c rail depends on: attach flattened, then send
// every later message with that sessionId. Run: node --test lib/cdp-connection.test.js
"use strict";
const { test } = require("node:test");
const assert = require("node:assert");
const { connectCdp } = require("./cdp-connection.js");

// A websocket double that speaks just enough CDP. `sent` records every outgoing frame so the test
// can assert the sessionId actually rides along.
function fakeSocket(handlers = {}) {
  const listeners = new Map();
  const sent = [];
  const socket = {
    sent,
    on(event, handler) { listeners.set(event, [...(listeners.get(event) || []), handler]); return socket; },
    emit(event, ...args) { for (const handler of listeners.get(event) || []) handler(...args); },
    close() { socket.closed = true; },
    send(raw) {
      const frame = JSON.parse(raw);
      sent.push(frame);
      const reply = handlers[frame.method];
      const result = typeof reply === "function" ? reply(frame) : (reply || {});
      queueMicrotask(() => socket.emit("message", JSON.stringify({ id: frame.id, result })));
    },
  };
  queueMicrotask(() => socket.emit("open"));
  return socket;
}

const BASE_HANDLERS = {
  "Target.getTargets": { targetInfos: [{ targetId: "T1", type: "page" }] },
  "Target.attachToTarget": { sessionId: "S1" },
  "Page.enable": {},
  "Runtime.enable": {},
};

test("attaches flattened to the page target and rides the sessionId on every later call", async () => {
  const socket = fakeSocket({
    ...BASE_HANDLERS,
    "Runtime.evaluate": { result: { value: { ok: true } } },
  });
  const page = await connectCdp("ws://steel/", { WebSocket: function () { return socket; } });
  const value = await page.evaluate("1+1");

  assert.deepEqual(value, { ok: true });
  const attach = socket.sent.find((f) => f.method === "Target.attachToTarget");
  assert.equal(attach.params.flatten, true);
  assert.equal(attach.params.targetId, "T1");
  const evaluate = socket.sent.find((f) => f.method === "Runtime.evaluate");
  assert.equal(evaluate.sessionId, "S1");
  assert.equal(evaluate.params.returnByValue, true);
});

test("a page-side exception throws instead of looking like undefined", async () => {
  const socket = fakeSocket({
    ...BASE_HANDLERS,
    "Runtime.evaluate": { exceptionDetails: { text: "field not found: #x" }, result: {} },
  });
  const page = await connectCdp("ws://steel/", { WebSocket: function () { return socket; } });
  await assert.rejects(() => page.evaluate("boom()"), /field not found/);
});

test("navigate waits for Page.loadEventFired before returning", async () => {
  const socket = fakeSocket({ ...BASE_HANDLERS, "Page.navigate": { frameId: "F1" } });
  const page = await connectCdp("ws://steel/", { WebSocket: function () { return socket; } });

  let settled = false;
  const navigation = page.navigate("https://x.example").then(() => { settled = true; });
  await new Promise((resolve) => setTimeout(resolve, 5));
  assert.equal(settled, false, "does not return on the navigate ack alone");

  socket.emit("message", JSON.stringify({ method: "Page.loadEventFired", params: {} }));
  await navigation;
  assert.equal(settled, true);
});

test("a closed socket rejects in-flight work rather than hanging", async () => {
  const socket = fakeSocket({ ...BASE_HANDLERS, "Runtime.evaluate": null });
  socket.send = (raw) => {
    const frame = JSON.parse(raw);
    socket.sent.push(frame);
    if (frame.method === "Runtime.evaluate") return; // never answered
    queueMicrotask(() => socket.emit("message", JSON.stringify({ id: frame.id, result: BASE_HANDLERS[frame.method] || {} })));
  };
  const page = await connectCdp("ws://steel/", { WebSocket: function () { return socket; }, timeoutMs: 50 });
  const pending = assert.rejects(() => page.evaluate("hang()"), /closed/);
  socket.emit("close");
  await pending;
});

// ─── review findings ────────────────────────────────────────────────────────────────────────────

// 🟡 Finding 14: failAll used to RESOLVE the load waiters, so navigate() returned "loaded" on a socket
// that had just died. A connection that is gone has not loaded anything.
test("a dead socket rejects the navigate load wait instead of resolving it", async () => {
  const socket = fakeSocket({ ...BASE_HANDLERS, "Page.navigate": { frameId: "F1" } });
  const page = await connectCdp("ws://steel/", { WebSocket: function () { return socket; } });
  const navigation = assert.rejects(() => page.navigate("https://x.example"), /closed/);
  await new Promise((resolve) => setTimeout(resolve, 5));
  socket.emit("close");
  await navigation;
});

// 🟡 Finding 15 / 🔴 Finding 7: the load wait is bounded wherever it is awaited, and it is awaitable
// on its own so the executor can wait for the POST-submit page before reading a confirmation off it.
test("waitForLoad resolves when the load event fires", async () => {
  const socket = fakeSocket(BASE_HANDLERS);
  const page = await connectCdp("ws://steel/", { WebSocket: function () { return socket; } });
  const wait = page.waitForLoad(500, { navigating: true });
  socket.emit("message", JSON.stringify({ method: "Page.loadEventFired", params: {} }));
  const outcome = await wait;
  assert.equal(outcome.loaded, true);
});

test("waitForLoad times out on its own rather than hanging forever", async () => {
  const socket = fakeSocket(BASE_HANDLERS);
  const page = await connectCdp("ws://steel/", { WebSocket: function () { return socket; } });
  await assert.rejects(() => page.waitForLoad(20, { navigating: true }), /timeout/i);
});

// An in-page (AJAX) submit never navigates. Waiting the full timeout for a load event that will never
// come would burn the single OSS steel session, so a submit that started no navigation returns early
// and says so — the caller reads the CURRENT dom, which is the right page in that case.
test("waitForLoad returns early when nothing ever started navigating", async () => {
  const socket = fakeSocket(BASE_HANDLERS);
  const page = await connectCdp("ws://steel/", { WebSocket: function () { return socket; } });
  const outcome = await page.waitForLoad(5000, { graceMs: 10 });
  assert.deepEqual(outcome, { loaded: false, navigated: false });
});

test("a navigation that started but never loaded still times out", async () => {
  const socket = fakeSocket(BASE_HANDLERS);
  const page = await connectCdp("ws://steel/", { WebSocket: function () { return socket; } });
  const wait = assert.rejects(() => page.waitForLoad(60, { graceMs: 10 }), /timeout/i);
  socket.emit("message", JSON.stringify({ method: "Page.frameStartedLoading", params: { frameId: "F1" } }));
  await wait;
});
