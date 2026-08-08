"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const { readMobileBootstrap } = require("../lib/mobile-bootstrap.js");

test("bootstrap projects only authenticated profile, connection, and analysis state", async () => {
  const result = await readMobileBootstrap({ uid: "user-a", productLocale: "ja" }, {
    store: { async readUser(scope) { assert.equal(scope.uid, "user-a"); return {
      uid: "user-a", name: "A", home_address: "Tokyo", phone: "+819012345678", calls_enabled: false,
      call_language: null, calendar_provider: "composio_gcal", gmail_account_id: "account-a", time_zone: "Asia/Tokyo",
    }; }, async readAnalysisState() { return { status: "idle" }; } },
  });
  assert.deepEqual(result, {
    user: {
      id: "user-a", name: "A", productLocale: "ja", timezone: "Asia/Tokyo",
      home: { status: "ready", display: "Tokyo" }, phone: { status: "configured", masked: "+81••••••••78" },
      callsEnabled: false, callLanguage: null,
    },
    calendar: { status: "connected" }, offer: { status: "available" }, analysis: { status: "idle" },
  });
});
