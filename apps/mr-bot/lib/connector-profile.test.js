"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const test = require("node:test");

const {
  isVerifiedConnectorProfile,
  readConnectorProfile,
} = require("./connector-profile.js");

function valid() {
  return {
    schema_version: 1,
    tenant_id: "dais-local",
    timezone: "Asia/Tokyo",
    preferences: "東京の対面イベントを広く評価し、特定分野だけで除外しない。",
    goals: "毎日人に会い、Mr.botと人生を前進させる接点を増やす。",
    spend_policy: { limits: [] },
    identity_ref: "identity://dais-local/luma",
    browser_profile_ref: "browser-profile://cloakbrowser/daily-driver",
    calendar_ref: "calendar://google/primary",
  };
}

function fixture(value = valid()) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "connector-profile-test-"));
  const file = path.join(root, "profile.json");
  fs.writeFileSync(file, `${JSON.stringify(value)}\n`, { mode: 0o600 });
  return { root, file };
}

test("reads one exact tenant-bound secret-free Connector profile", () => {
  const fx = fixture();
  try {
    const profile = readConnectorProfile({ path: fx.file, tenantId: "dais-local" });
    assert.equal(profile.preferences, valid().preferences);
    assert.deepEqual(profile.spend_policy, { limits: [] });
    assert.equal(isVerifiedConnectorProfile(profile), true);
    assert.equal(isVerifiedConnectorProfile(structuredClone(profile)), false);
  } finally { fs.rmSync(fx.root, { recursive: true, force: true }); }
});

test("missing files, schema drift, tenant drift, raw secrets, and paid limits fail closed", () => {
  const cases = [
    { ...valid(), extra: true },
    { ...valid(), tenant_id: "other" },
    { ...valid(), preferences: "send to person@example.com" },
    { ...valid(), goals: "use API_KEY secret-value" },
    { ...valid(), spend_policy: { limits: [{ currency: "JPY" }] } },
    { ...valid(), identity_ref: "dais@example.com" },
  ];
  for (const value of cases) {
    const fx = fixture(value);
    try {
      assert.throws(
        () => readConnectorProfile({ path: fx.file, tenantId: "dais-local" }),
        /Connector profile unavailable/,
      );
    } finally { fs.rmSync(fx.root, { recursive: true, force: true }); }
  }
  assert.throws(
    () => readConnectorProfile({ path: "/not/a/real/profile.json", tenantId: "dais-local" }),
    /Connector profile unavailable/,
  );
});

