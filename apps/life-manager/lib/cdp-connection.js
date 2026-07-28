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
const DEFAULT_LOAD_TIMEOUT_MS = 30_000;
// How long a click gets to START a navigation before we conclude it never will. An in-page (AJAX)
// submit never navigates at all, and waiting the full load timeout for an event that will never come
// would hold the single OSS steel session for nothing.
const NAVIGATION_GRACE_MS = 1_500;

// The CDP events that mean "this page is going somewhere". Used only to tell a page that is still
// loading (→ wait, then time out) from one that never moved (→ return early and read the DOM we have).
const NAVIGATION_STARTED = new Set([
  "Page.frameStartedLoading",
  "Page.frameScheduledNavigation",
  "Page.frameRequestedNavigation",
  "Page.navigatedWithinDocument",
  "Page.frameNavigated",
]);

function connectCdp(websocketUrl, options = {}) {
  const WebSocketImpl = options.WebSocket || require("ws");
  const timeoutMs = Number.isFinite(options.timeoutMs) ? options.timeoutMs : DEFAULT_TIMEOUT_MS;
  const parsedWebsocketUrl = new URL(websocketUrl);
  // Steel's root websocket is an HTTP proxy to Chrome's localhost CDP socket. Chrome rejects a
  // forwarded `Host: steel-browser.railway.internal` as DNS rebinding (HTTP 500), even though the
  // private-network TCP connection reached Steel correctly. Keep the real destination/SNI in the
  // URL and rewrite ONLY the HTTP Host header at this verified Railway private boundary. Hosted CDP
  // endpoints keep their normal Host header.
  const websocketOptions = parsedWebsocketUrl.hostname.endsWith(".railway.internal")
    ? {
        headers: {
          Host: `localhost:${parsedWebsocketUrl.port || (parsedWebsocketUrl.protocol === "wss:" ? "443" : "80")}`,
        },
      }
    : undefined;
  const socket = new WebSocketImpl(websocketUrl, websocketOptions);

  let nextId = 1;
  const pending = new Map();
  const loadWaiters = new Set();
  let cdpSessionId = null;
  let closed = false;
  let navigationStarted = false;

  const failAll = (error) => {
    closed = true;
    for (const { reject } of pending.values()) reject(error);
    pending.clear();
    // A dead socket has not LOADED anything. Resolving the load waiters here (as this used to) made
    // navigate() return successfully off a connection that had just died, and every read after it
    // then described a page that was never fetched.
    for (const waiter of [...loadWaiters]) waiter.reject(error);
    loadWaiters.clear();
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
    if (NAVIGATION_STARTED.has(frame.method)) navigationStarted = true;
    if (frame.method === "Page.loadEventFired") {
      const [waiter] = loadWaiters;
      if (waiter) waiter.resolve(frame.params);
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

  // ONE bounded wait for "the page finished loading", used by navigate() and — the reason it is
  // public — by the booking executor after it clicks submit. Three outcomes, all of them terminal:
  //   • the load event arrives            → { loaded: true }
  //   • nothing ever started navigating   → { loaded: false, navigated: false } after the grace
  //   • it navigated and never finished   → THROWS on the timeout (the page state is unknown)
  // A wait with no timeout is a hang, and a hang here holds the one steel session the OSS build has.
  function waitForLoad(waitMs = DEFAULT_LOAD_TIMEOUT_MS, waitOptions = {}) {
    if (closed) return Promise.reject(new Error("CDP connection closed"));
    const limitMs = Number.isFinite(waitMs) ? waitMs : DEFAULT_LOAD_TIMEOUT_MS;
    const graceMs = Number.isFinite(waitOptions.graceMs) ? waitOptions.graceMs : NAVIGATION_GRACE_MS;
    navigationStarted = waitOptions.navigating === true;
    return new Promise((resolve, reject) => {
      let settled = false;
      const finish = (fn, value) => {
        if (settled) return;
        settled = true;
        clearTimeout(hardTimer);
        clearTimeout(graceTimer);
        loadWaiters.delete(waiter);
        fn(value);
      };
      const waiter = {
        resolve: (params) => finish(resolve, { loaded: true, params: params || null }),
        reject: (error) => finish(reject, error instanceof Error ? error : new Error(String(error))),
      };
      const hardTimer = setTimeout(() => finish(reject, new Error(`CDP timeout: page load (${limitMs}ms)`)), limitMs);
      const graceTimer = setTimeout(() => {
        if (!navigationStarted) finish(resolve, { loaded: false, navigated: false });
      }, Math.min(graceMs, limitMs));
      loadWaiters.add(waiter);
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
      waitForLoad,
      async navigate(url) {
        // `navigating: true` because Page.navigate IS the navigation start — the grace path would
        // otherwise let navigate() return before the new document had arrived.
        const loaded = waitForLoad(timeoutMs, { navigating: true });
        loaded.catch(() => { /* surfaced by the await below; this only silences the in-flight window */ });
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
