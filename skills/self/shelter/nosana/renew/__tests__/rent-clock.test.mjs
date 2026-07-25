// node:test — rent-clock: pure expiry math + the renewal decision + window-id derivation. No I/O.
import { test } from "node:test";
import assert from "node:assert/strict";
import {
  DEFAULT_RENEWAL_LEAD_SECONDS,
  computeExpiresAtTs,
  evaluateRentClock,
  computeRenewalWindowId,
  computeBootstrapWindowId,
} from "../rent-clock.mjs";

test("computeExpiresAtTs adds timeStart + timeout", () => {
  assert.equal(computeExpiresAtTs({ timeStart: 1784956456, timeout: 900 }), 1784957356);
});

test("computeExpiresAtTs fails closed on a negative timeout rather than computing garbage", () => {
  assert.throws(() => computeExpiresAtTs({ timeStart: 100, timeout: -1 }), /non-negative finite number/);
});

test("computeExpiresAtTs fails closed on a non-finite timeStart", () => {
  assert.throws(() => computeExpiresAtTs({ timeStart: NaN, timeout: 900 }), /non-negative finite number/);
});

test("evaluateRentClock: far from expiry is not due", () => {
  const r = evaluateRentClock({ nowTs: 1000, expiresAtTs: 10000, leadSeconds: 180 });
  assert.equal(r.dueForRenewal, false);
  assert.equal(r.alreadyExpired, false);
  assert.equal(r.secondsUntilExpiry, 9000);
});

test("evaluateRentClock: exactly at the lead-time boundary is due (inclusive)", () => {
  const r = evaluateRentClock({ nowTs: 1000, expiresAtTs: 1180, leadSeconds: 180 });
  assert.equal(r.secondsUntilExpiry, 180);
  assert.equal(r.dueForRenewal, true);
  assert.equal(r.alreadyExpired, false);
});

test("evaluateRentClock: one second inside the lead time is due", () => {
  const r = evaluateRentClock({ nowTs: 1000, expiresAtTs: 1179, leadSeconds: 180 });
  assert.equal(r.dueForRenewal, true);
});

test("evaluateRentClock: one second outside the lead time is not yet due", () => {
  const r = evaluateRentClock({ nowTs: 1000, expiresAtTs: 1181, leadSeconds: 180 });
  assert.equal(r.dueForRenewal, false);
});

test("evaluateRentClock: already past expiry is both expired and due", () => {
  const r = evaluateRentClock({ nowTs: 2000, expiresAtTs: 1000, leadSeconds: 180 });
  assert.equal(r.alreadyExpired, true);
  assert.equal(r.dueForRenewal, true);
  assert.equal(r.secondsUntilExpiry, -1000);
});

test("evaluateRentClock uses DEFAULT_RENEWAL_LEAD_SECONDS when leadSeconds is omitted", () => {
  const r = evaluateRentClock({ nowTs: 1000, expiresAtTs: 1000 + DEFAULT_RENEWAL_LEAD_SECONDS });
  assert.equal(r.dueForRenewal, true);
  assert.equal(r.leadSeconds, DEFAULT_RENEWAL_LEAD_SECONDS);
});

test("evaluateRentClock fails closed (throws) on a non-finite nowTs — never guesses a verdict", () => {
  assert.throws(() => evaluateRentClock({ nowTs: NaN, expiresAtTs: 1000 }), /finite number/);
});

test("evaluateRentClock fails closed on a negative leadSeconds", () => {
  assert.throws(() => evaluateRentClock({ nowTs: 1, expiresAtTs: 2, leadSeconds: -1 }), /leadSeconds must be >= 0/);
});

test("computeRenewalWindowId is deterministic for the same job+expiry and floors fractional expiry", () => {
  const id1 = computeRenewalWindowId({ jobAddress: "JOB111", referenceExpiresAtTs: 1784957356.9 });
  const id2 = computeRenewalWindowId({ jobAddress: "JOB111", referenceExpiresAtTs: 1784957356.1 });
  assert.equal(id1, "JOB111:1784957356");
  assert.equal(id1, id2);
});

test("computeRenewalWindowId differs across jobs and across expiries", () => {
  const a = computeRenewalWindowId({ jobAddress: "JOB111", referenceExpiresAtTs: 100 });
  const b = computeRenewalWindowId({ jobAddress: "JOB222", referenceExpiresAtTs: 100 });
  const c = computeRenewalWindowId({ jobAddress: "JOB111", referenceExpiresAtTs: 200 });
  assert.notEqual(a, b);
  assert.notEqual(a, c);
});

test("computeRenewalWindowId fails closed on a missing jobAddress", () => {
  assert.throws(() => computeRenewalWindowId({ jobAddress: "", referenceExpiresAtTs: 1 }), /jobAddress is required/);
});

test("computeBootstrapWindowId buckets nearby timestamps into the same window and never collides with a real job-anchored id", () => {
  const a = computeBootstrapWindowId({ nowTs: 1000, bucketSeconds: 360 });
  const b = computeBootstrapWindowId({ nowTs: 1010, bucketSeconds: 360 });
  const c = computeBootstrapWindowId({ nowTs: 2000, bucketSeconds: 360 });
  assert.equal(a, b);
  assert.notEqual(a, c);
  assert.match(a, /^bootstrap:/);
});

test("computeBootstrapWindowId fails closed on a non-positive bucketSeconds", () => {
  assert.throws(() => computeBootstrapWindowId({ nowTs: 1, bucketSeconds: 0 }), /bucketSeconds must be a positive/);
});
