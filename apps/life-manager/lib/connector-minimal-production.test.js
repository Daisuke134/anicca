"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const test = require("node:test");

const { createProductionBrowserRail } = require("./connector-minimal-production.js");

test("production browser rail owns exactly one :9222 target without closing the browser", async () => {
  const stateDir = fs.mkdtempSync(path.join(os.tmpdir(), "connector-production-rail-"));
  const calls = [];
  const page = {
    async goto(url, options) { calls.push(["goto", url, options]); },
  };
  const browser = {
    close() { calls.push(["browser-close"]); },
  };
  const controller = {
    async create() {
      calls.push(["target-create"]);
      return Object.freeze({
        target_id: "OWNEDTARGET1",
        page_websocket: "ws://127.0.0.1:9222/devtools/page/OWNEDTARGET1",
        page,
      });
    },
    async close(targetId) { calls.push(["target-close", targetId]); return true; },
    async probe() { return true; },
  };
  const owner = {
    async claimExact(input) {
      calls.push(["claim", input]);
      return Object.freeze({
        schema_version: 1,
        owner_token: "owner-token-production-rail",
        generation: 1,
        target_id: input.targetId,
        page_websocket: input.pageWebsocket,
        canonical_url: "https://luma.com/tokyo?k=p",
        claimed_at: "2026-08-07T02:00:00.000Z",
      });
    },
    async probe() { calls.push(["probe"]); return true; },
    async heartbeat() { calls.push(["heartbeat"]); return true; },
    async release(receipt) { calls.push(["release", receipt.target_id]); return true; },
  };

  try {
    const rail = createProductionBrowserRail({
      stateDir,
      connectOverCDP: async (endpoint) => {
        calls.push(["connect", endpoint]);
        return browser;
      },
      createTargetController: (input) => {
        assert.equal(input.browser, browser);
        return controller;
      },
      createTargetOwnership: ({ ownerToken }) => {
        assert.equal(ownerToken, "owner-token-production-rail");
        return owner;
      },
      makeSessionId: () => "session-production-rail-1",
    });

    const owned = await rail.open({ ownerToken: "owner-token-production-rail" });
    await rail.navigate(owned, "https://luma.com/event-one");
    await rail.close(owned);

    assert.equal(owned.page, page);
    assert.equal(owned.target_id, "OWNEDTARGET1");
    assert.equal(calls.filter(([name]) => name === "connect").length, 1);
    assert.equal(calls.filter(([name]) => name === "target-create").length, 1);
    assert.equal(calls.filter(([name]) => name === "claim").length, 1);
    assert.equal(calls.filter(([name]) => name === "goto").length, 1);
    assert.equal(calls.filter(([name]) => name === "release").length, 1);
    assert.equal(calls.filter(([name]) => name === "target-close").length, 0);
    assert.equal(calls.filter(([name]) => name === "browser-close").length, 0);
  } finally {
    fs.rmSync(stateDir, { recursive: true, force: true });
  }
});
