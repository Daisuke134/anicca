"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");

const { buildYcDescriptionPatch } = require("./yc-description.js");

const canonical = {
  draftId: "0b61fe42-e383-490d-b60e-04f1ad7ec5df",
  currentValue: "Buddhist AI that self-funds compute & pays UBI",
  canonicalValue: "Self-funding Buddhist AI. Ends suffering.",
  sourceRef: "application-kit://KIT.md#english-one-liner",
  sourceDigest: "a".repeat(64),
};

test("canonical YC one-liner produces a source-bound update below the exclusive 50-char limit", () => {
  const patch = buildYcDescriptionPatch(canonical);
  assert.equal(patch.field_name, "describe");
  assert.equal(patch.value, canonical.canonicalValue);
  assert.equal(patch.unicode_length, 41);
  assert.equal(patch.max_exclusive, 50);
  assert.equal(patch.operation, "update");
  assert.equal(patch.submit_application, false);
  assert.match(patch.patch_digest, /^[0-9a-f]{64}$/);
});

test("an exact saved value becomes a no-op without another browser write", () => {
  const patch = buildYcDescriptionPatch({ ...canonical, currentValue: canonical.canonicalValue });
  assert.equal(patch.operation, "no_op");
});

test("50 chars, blank, multiline, padded, placeholder, and noncanonical source fail closed", () => {
  const invalid = [
    { canonicalValue: "x".repeat(50) },
    { canonicalValue: "" },
    { canonicalValue: "one\ntwo" },
    { canonicalValue: " padded" },
    { canonicalValue: "{{company.description}}" },
    { sourceRef: "legacy-draft://yc-w26" },
    { sourceDigest: "not-a-digest" },
  ];
  for (const overrides of invalid) assert.throws(() => buildYcDescriptionPatch({ ...canonical, ...overrides }), /description/i);
});
