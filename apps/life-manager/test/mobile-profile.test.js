"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const { validateMobileProfilePatch, patchMobileProfile, isValidE164 } = require("../lib/mobile-profile.js");

test("profile patch allowlists locale, name, home, phone, and explicit call settings", () => {
  assert.deepEqual(validateMobileProfilePatch({ name: "A", home: "Tokyo", productLocale: "ja", phone: null, callsEnabled: false }), {
    name: "A", home: "Tokyo", productLocale: "ja", phone: null, callsEnabled: false,
  });
  assert.throws(() => validateMobileProfilePatch({ uid: "user-b" }), (error) => error.code === "unknown_profile_field");
  assert.throws(() => validateMobileProfilePatch({ phone: "0901234" }), (error) => error.code === "invalid_phone");
  assert.equal(isValidE164("+819012345678"), true);
  assert.equal(isValidE164(null), false);
});

test("null phone always disables calls and call language defaults to product locale", async () => {
  const patches = [];
  const result = await patchMobileProfile({ uid: "user-a" }, { phone: null, callsEnabled: true, productLocale: "ja" }, {
    store: { async patchUser(scope, patch) { patches.push({ scope, patch }); return { ...patch }; } },
  });
  assert.equal(result.phone, null);
  assert.equal(result.callsEnabled, false);
  assert.equal(result.callLanguage, null);
  assert.deepEqual(patches[0].scope, { uid: "user-a" });
});

test("saving a null phone without a toggle still disables calls", async () => {
  const writes = [];
  await patchMobileProfile({ uid: "user-a" }, { phone: null }, {
    store: {
      async patchUser(_scope, patch) { writes.push(patch); return { calls_enabled: true, call_language: "ja", ...patch }; },
    },
  });
  assert.equal(writes[0].calls_enabled, false);
  assert.equal(writes[0].call_language, null);
});

test("calls cannot be enabled without a phone and call language is independent", async () => {
  await assert.rejects(() => patchMobileProfile({ uid: "user-a" }, { callsEnabled: true }, {
    store: { async patchUser(_scope, patch) { return patch; } },
  }), (error) => error.code === "call_language_required");
  const result = await patchMobileProfile({ uid: "user-a" }, { phone: "+819012345678", callsEnabled: true, productLocale: "en" }, {
    store: { async patchUser(_scope, patch) { return patch; } },
  });
  assert.equal(result.callsEnabled, true);
  assert.equal(result.callLanguage, "en");
});

test("call enablement may be toggled after a phone was already saved", async () => {
  const patches = [];
  await patchMobileProfile({ uid: "user-a" }, { callsEnabled: true }, {
    store: {
      async readUser(scope) { assert.equal(scope.uid, "user-a"); return { phone: "+819012345678", product_locale: "ja" }; },
      async patchUser(_scope, patch) { patches.push(patch); return patch; },
    },
  });
  assert.deepEqual(patches[0], { calls_enabled: true, call_language: "ja" });
});

test("call language can change independently after calls are enabled", async () => {
  const patches = [];
  const result = await patchMobileProfile({ uid: "user-a" }, { callLanguage: "ja" }, {
    store: {
      async readUser(scope) { assert.equal(scope.uid, "user-a"); return { phone: "+819012345678", calls_enabled: true, call_language: "en" }; },
      async patchUser(_scope, patch) { patches.push(patch); return { phone: "+819012345678", calls_enabled: true, ...patch }; },
    },
  });
  assert.equal(result.callsEnabled, true);
  assert.equal(result.callLanguage, "ja");
  assert.deepEqual(patches[0], { call_language: "ja" });
});
