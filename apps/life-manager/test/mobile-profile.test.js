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
