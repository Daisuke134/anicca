"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");

const {
  buildErrorIntake,
  persistErrorIntake,
} = require("./error-intake.js");


const KEY = "fixture-error-provenance-key";


test("production error intake is a closed PII-free schema built only from allowlisted fields", () => {
  const email = ["person", "example.com"].join("@");
  const phone = ["+81", "90123", "45678"].join("");
  const rawError = [
    "Bearer", "not-a-real-secret",
    email,
    phone,
  ].join(" ");
  const intake = buildErrorIntake({
    signal: "provider_timeout",
    component: "calendar",
    fingerprint: "calendar-read-deadline",
    rawError,
    provenanceKey: KEY,
  });
  assert.deepEqual(Object.keys(intake).sort(), ["labels", "source_ref", "summary"]);
  assert.deepEqual(intake.labels, ["error", "provider-timeout"]);
  assert.equal(intake.summary, "Provider timeout in calendar (calendar-read-deadline).");
  assert.match(intake.source_ref, /^err:sha256:[a-f0-9]{32}$/);
  const serialized = JSON.stringify(intake);
  for (const forbidden of ["not-a-real-secret", email, phone, rawError]) {
    assert.equal(serialized.includes(forbidden), false);
  }
});


test("six production signals map to exactly three incident classes", () => {
  const cases = {
    provider_timeout: "provider-timeout",
    call_failed: "side-effect-failed",
    email_failed: "side-effect-failed",
    post_failed: "side-effect-failed",
    http_5xx: "runtime-regression",
    eval_regression: "runtime-regression",
  };
  for (const [signal, label] of Object.entries(cases)) {
    const intake = buildErrorIntake({
      signal,
      component: signal === "provider_timeout" ? "calendar" : signal.endsWith("failed") ? "delivery" : "production-health",
      fingerprint: `controlled-${label}`,
      rawError: "private provider text must disappear",
      provenanceKey: KEY,
    });
    assert.deepEqual(intake.labels, ["error", label]);
  }
});


test("5xx and eval signals with one root fingerprint dedupe to the same source reference", () => {
  const common = {
    component: "production-health",
    fingerprint: "controlled-service-regression",
    provenanceKey: KEY,
  };
  const http = buildErrorIntake({ ...common, signal: "http_5xx", rawError: "private 503 body" });
  const evaluation = buildErrorIntake({ ...common, signal: "eval_regression", rawError: "private assertion body" });
  assert.equal(http.source_ref, evaluation.source_ref);
  assert.deepEqual(http, evaluation);
});


test("invalid signal, component, fingerprint, or provenance is rejected before persistence", () => {
  const email = ["private", "example.com"].join("@");
  const base = {
    signal: "provider_timeout",
    component: "calendar",
    fingerprint: "deadline",
    rawError: "ignored",
    provenanceKey: KEY,
  };
  for (const patch of [
    { signal: "unknown" },
    { component: `calendar ${email}` },
    { fingerprint: "space is forbidden" },
    { provenanceKey: "" },
  ]) {
    assert.throws(() => buildErrorIntake({ ...base, ...patch }), /error_intake_invalid/);
  }
});


test("error persistence reuses the deduplicating developer intake table", async () => {
  const seen = [];
  const intake = buildErrorIntake({
    signal: "email_failed",
    component: "delivery",
    fingerprint: "controlled-side-effect",
    rawError: "private provider body",
    provenanceKey: KEY,
  });
  const result = await persistErrorIntake(intake, {
    persist: async (value) => {
      seen.push(value);
      return { id: "2", duplicate: false };
    },
  });
  assert.deepEqual(result, { id: "2", duplicate: false });
  assert.deepEqual(seen, [intake]);
});
