"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const Module = require("node:module");
const path = require("node:path");

const serverPath = path.resolve(__dirname, "../server.js");
const originalLoad = Module._load;
Module._load = function load(request, parent, isMain) {
  if (parent && parent.filename === serverPath && request.startsWith(".")) return {};
  if (request === "inngest/node") return { serve: () => () => {} };
  if (request === "stripe") return () => ({ webhooks: { constructEvent: () => ({}) } });
  if (request === "ws") {
    class FakeWebSocketServer { on() {} }
    return { Server: FakeWebSocketServer, OPEN: 1 };
  }
  return originalLoad.call(this, request, parent, isMain);
};
let server;
try {
  server = require("../server.js");
} finally {
  Module._load = originalLoad;
}

const FALLBACK = "lm2a-webhook-retry-v1";
const VALID_SHA = "0123456789abcdef0123456789abcdef01234567";

test("buildTag uses only an exact Railway deployment SHA", () => {
  assert.equal(typeof server.buildTag, "function");
  assert.equal(server.buildTag({ RAILWAY_GIT_COMMIT_SHA: VALID_SHA }), VALID_SHA);
  assert.equal(server.buildTag({ RAILWAY_GIT_COMMIT_SHA: VALID_SHA.toUpperCase() }), VALID_SHA.toUpperCase());
  for (const env of [
    {},
    { RAILWAY_GIT_COMMIT_SHA: "" },
    { RAILWAY_GIT_COMMIT_SHA: "   " },
    { RAILWAY_GIT_COMMIT_SHA: "not-a-sha" },
    { RAILWAY_GIT_COMMIT_SHA: "0123456789abcdef0123456789abcdef0123456" },
    { RAILWAY_GIT_COMMIT_SHA: `${VALID_SHA}0` },
  ]) {
    assert.equal(server.buildTag(env), FALLBACK);
  }
});
