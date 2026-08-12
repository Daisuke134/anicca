"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const test = require("node:test");

const { readLumaFormProfile } = require("./luma-form-profile.js");

function fixture(value, mode = 0o600) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "luma-form-profile-"));
  const file = path.join(root, "profile.json");
  fs.writeFileSync(file, JSON.stringify(value), { mode });
  return { root, file };
}

function valid() {
  return {
    schema_version: 1,
    phone: "+81 90 0000 0000",
    form_answers: { "Primary field": ["Technology", "Founder"] },
    consents: { code_of_conduct_and_media_release: true },
  };
}

test("reads one closed mode-0600 private Luma form profile", () => {
  const fx = fixture(valid());
  try {
    const actual = readLumaFormProfile({ path: fx.file });
    assert.deepEqual(actual, valid());
    assert.equal(Object.isFrozen(actual), true);
    assert.equal(Object.isFrozen(actual.form_answers), true);
    assert.equal(Object.isFrozen(actual.consents), true);
  } finally {
    fs.rmSync(fx.root, { recursive: true, force: true });
  }
});

test("rejects permissive files, extra keys, secrets, and unsupported answer shapes", () => {
  const cases = [
    [valid(), 0o644],
    [{ ...valid(), email: "owner@example.com" }, 0o600],
    [{ ...valid(), form_answers: { Field: "token=secret-value" } }, 0o600],
    [{ ...valid(), form_answers: { Field: { invented: true } } }, 0o600],
  ];
  for (const [value, mode] of cases) {
    const fx = fixture(value, mode);
    try {
      assert.throws(() => readLumaFormProfile({ path: fx.file }), /Luma form profile unavailable/);
    } finally {
      fs.rmSync(fx.root, { recursive: true, force: true });
    }
  }
});
