"use strict";
// lib/cdp-connection.js — the minimal Chrome DevTools Protocol client the 11c booking rail needs.
//
// steel-browser hands back a BROWSER-level CDP websocket (SessionDetails.websocketUrl). Driving a
// page through it is three steps that are easy to get subtly wrong, so they live here once:
//   1. Target.getTargets → pick the existing page target (steel always has one), else create one.
//   2. Target.attachToTarget { flatten: true } → a CDP session id that must ride on EVERY later
//      message as `sessionId`. Without flatten the replies come back wrapped and the correlation
//      by message id silently breaks.
//   3. Page.enable / Runtime.enable on that session, so Page.loadEventFired actually arrives.
//
// Deliberately small: navigate + evaluate + close is the entire surface 11c uses. `ws` is already a
// production dependency (the Gemini bridge), and the WebSocket class is injectable so the protocol
// sequencing is testable without a browser.

const DEFAULT_TIMEOUT_MS = 30_000;

function connectCdp(websocketUrl, options = {}) {
  const WebSocketImpl = options.WebSocket || require("ws");
  const timeoutMs = Number.isFinite(options.timeoutMs) ? options.timeoutMs : DEFAULT_TIMEOUT_MS;
  const socket = new WebSocketImpl(websocketUrl);

  let nextId = 1;
  const pending = new Map();
  const loadWaiters = [];
  let cdpSessionId = null;
  let closed = false;

  const failAll = (error) => {
    closed = true;
    for (const { reject } of pending.values()) reject(error);
    pending.clear();
    while (loadWaiters.length) loadWaiters.shift().resolve(null);
  };

  socket.on("message", (raw) => {
    let frame;
    try { frame = JSON.parse(String(raw)); } catch { return; }
    if (frame.id !== undefined && pending.has(frame.id)) {
      const { resolve, reject } = pending.get(frame.id);
      pending.delete(frame.id);
      if (frame.error) reject(new Error(`CDP ${frame.error.message || "error"}`));
      else resolve(frame.result);
      return;
    }
    if (frame.method === "Page.loadEventFired" && loadWaiters.length) {
      loadWaiters.shift().resolve(frame.params);
    }
  });
  socket.on("close", () => failAll(new Error("CDP connection closed")));
  socket.on("error", (error) => failAll(error instanceof Error ? error : new Error(String(error))));

  const ready = new Promise((resolve, reject) => {
    socket.on("open", resolve);
    socket.on("error", reject);
  });

  function send(method, params, sessionId) {
    if (closed) return Promise.reject(new Error("CDP connection closed"));
    const id = nextId++;
    const message = { id, method, params: params || {} };
    if (sessionId) message.sessionId = sessionId;
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => {
        pending.delete(id);
        reject(new Error(`CDP timeout: ${method}`));
      }, timeoutMs);
      pending.set(id, {
        resolve: (value) => { clearTimeout(timer); resolve(value); },
        reject: (error) => { clearTimeout(timer); reject(error); },
      });
      socket.send(JSON.stringify(message));
    });
  }

  async function attach() {
    if (cdpSessionId) return cdpSessionId;
    await ready;
    const { targetInfos } = await send("Target.getTargets");
    let target = (targetInfos || []).find((info) => info.type === "page");
    if (!target) target = await send("Target.createTarget", { url: "about:blank" });
    const attached = await send("Target.attachToTarget", { targetId: target.targetId, flatten: true });
    cdpSessionId = attached.sessionId;
    await send("Page.enable", {}, cdpSessionId);
    await send("Runtime.enable", {}, cdpSessionId);
    return cdpSessionId;
  }

  return Promise.resolve().then(async () => {
    await attach();
    return {
      websocketUrl,
      async navigate(url) {
        const loaded = new Promise((resolve) => loadWaiters.push({ resolve }));
        await send("Page.navigate", { url }, cdpSessionId);
        await loaded;
      },
      // Returns the VALUE, and turns a thrown page-side exception into a thrown JS error — a page
      // that threw must never look like a page that returned undefined.
      async evaluate(expression) {
        const result = await send("Runtime.evaluate", {
          expression,
          returnByValue: true,
          awaitPromise: true,
        }, cdpSessionId);
        if (result && result.exceptionDetails) {
          const detail = result.exceptionDetails;
          throw new Error(`page evaluate failed: ${(detail.exception && detail.exception.description) || detail.text || "unknown"}`);
        }
        return result && result.result ? result.result.value : undefined;
      },
      async close() {
        closed = true;
        try { socket.close(); } catch { /* already gone */ }
      },
    };
  });
}

module.exports = { connectCdp };
