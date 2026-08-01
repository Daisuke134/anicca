"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");

const {
  DAILY_DRIVER_CDP,
  classifyLumaLogin,
  createCloakBrowserDailyDriver,
} = require("./cloakbrowser-daily-driver.js");

function fixture({ contexts = 1 } = {}) {
  const calls = [];
  const existingPage = { id: "existing-page" };
  const ownedPage = {
    async goto(url, options) {
      calls.push(["goto", url, options]);
    },
    async close() {
      calls.push(["close-owned-page"]);
    },
  };
  const context = {
    pages() {
      calls.push(["read-existing-pages"]);
      return [existingPage];
    },
    async newPage() {
      calls.push(["new-page"]);
      return ownedPage;
    },
  };
  const browser = {
    contexts() {
      calls.push(["contexts"]);
      return Array.from({ length: contexts }, () => context);
    },
    async close() {
      calls.push(["close-browser"]);
    },
  };
  return {
    calls,
    existingPage,
    ownedPage,
    async connectOverCDP(endpoint) {
      calls.push(["connect", endpoint]);
      return browser;
    },
  };
}

test("uses only the live :9222 shared context and closes only its own page", async () => {
  const fx = fixture();
  const driver = createCloakBrowserDailyDriver({
    connectOverCDP: fx.connectOverCDP,
  });

  const result = await driver.withLumaPage(
    "https://luma.com/tokyo-ai",
    async (page, metadata) => {
      assert.equal(page, fx.ownedPage);
      assert.deepEqual(metadata, {
        endpoint: DAILY_DRIVER_CDP,
        existing_page_count: 1,
      });
      return { status: "read-only" };
    },
  );

  assert.deepEqual(result, { status: "read-only" });
  assert.deepEqual(fx.calls, [
    ["connect", "http://127.0.0.1:9222"],
    ["contexts"],
    ["read-existing-pages"],
    ["new-page"],
    ["goto", "https://luma.com/tokyo-ai", {
      waitUntil: "domcontentloaded",
      timeout: 30_000,
    }],
    ["close-owned-page"],
  ]);
});

test("refuses another CDP port, non-Luma origins, credentials, and multiple contexts", async () => {
  assert.throws(
    () => createCloakBrowserDailyDriver({
      connectOverCDP: async () => {},
      endpoint: "http://127.0.0.1:9223",
    }),
    /daily-driver endpoint/i,
  );

  const fx = fixture();
  const driver = createCloakBrowserDailyDriver({ connectOverCDP: fx.connectOverCDP });
  await assert.rejects(
    driver.withLumaPage("https://example.com/event", async () => {}),
    /Luma URL/i,
  );
  await assert.rejects(
    driver.withLumaPage("https://user:secret@luma.com/event", async () => {}),
    /Luma URL/i,
  );

  const multiple = fixture({ contexts: 2 });
  const unsafe = createCloakBrowserDailyDriver({ connectOverCDP: multiple.connectOverCDP });
  await assert.rejects(
    unsafe.withLumaPage("https://luma.com/event", async () => {}),
    /shared context/i,
  );
});

test("always closes its own page after a task failure without closing the browser", async () => {
  const fx = fixture();
  const driver = createCloakBrowserDailyDriver({ connectOverCDP: fx.connectOverCDP });

  await assert.rejects(
    driver.withLumaPage("https://lu.ma/tokyo-ai", async () => {
      throw new Error("fixture task failed");
    }),
    /fixture task failed/,
  );
  assert.equal(fx.calls.filter(([name]) => name === "close-owned-page").length, 1);
  assert.equal(fx.calls.some(([name]) => name === "close-browser"), false);
});

test("classifies Luma login without exposing page text or cookie values", () => {
  assert.deepEqual(classifyLumaLogin({
    origin: "https://luma.com",
    path: "/home",
    loginForm: false,
    authenticatedMarker: true,
    signInMarker: false,
  }), {
    status: "authenticated",
    origin: "https://luma.com",
    path: "/home",
  });
  assert.deepEqual(classifyLumaLogin({
    origin: "https://luma.com",
    path: "/signin",
    loginForm: true,
    authenticatedMarker: false,
    signInMarker: true,
  }), {
    status: "login_required",
    origin: "https://luma.com",
    path: "/signin",
  });
  assert.deepEqual(classifyLumaLogin({
    origin: "https://luma.com",
    path: "/home",
    loginForm: false,
    authenticatedMarker: false,
    signInMarker: false,
  }), {
    status: "unknown",
    origin: "https://luma.com",
    path: "/home",
  });
});

test("Docker may resolve the same :9222 owner to a private host IP but never another port", async () => {
  const fx = fixture();
  const driver = createCloakBrowserDailyDriver({
    connectOverCDP: fx.connectOverCDP,
    resolveEndpoint: async () => "http://192.168.5.2:9222",
  });
  await driver.withLumaPage("https://luma.com/event-a", async () => ({}));
  assert.deepEqual(fx.calls[0], ["connect", "http://192.168.5.2:9222"]);

  const badPort = createCloakBrowserDailyDriver({
    connectOverCDP: fx.connectOverCDP,
    resolveEndpoint: async () => "http://192.168.5.2:9223",
  });
  await assert.rejects(
    badPort.withLumaPage("https://luma.com/event-a", async () => ({})),
    /resolved endpoint/i,
  );

  const publicHost = createCloakBrowserDailyDriver({
    connectOverCDP: fx.connectOverCDP,
    resolveEndpoint: async () => "http://8.8.8.8:9222",
  });
  await assert.rejects(
    publicHost.withLumaPage("https://luma.com/event-a", async () => ({})),
    /resolved endpoint/i,
  );
});
