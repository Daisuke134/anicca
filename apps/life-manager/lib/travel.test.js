// travel.test.js — unit guards for travelDecision (the home→home noise fix).
// Run: node --test apps/life-call/lib/travel.test.js
"use strict";
const { test } = require("node:test");
const assert = require("node:assert");
const { travelDecision } = require("./travel.js");

const HOME = "新宿区南元町15-27";
const ms = (h) => Date.parse(`2026-06-20T${String(h).padStart(2, "0")}:00:00+09:00`);

test("home→home (at-home activity, origin=home) → NO travel block", () => {
  const ev = { summary: "🧘 Meditation", location: HOME, startMs: ms(6) };
  const d = travelDecision(ev, null, HOME);
  assert.equal(d.insert, false);
  assert.equal(d.reason, "same-location");
});

test("home location with spacing differences still counts as same → skip", () => {
  const ev = { summary: "😴 Sleep", location: " 新宿区南元町15-27 ", startMs: ms(23) };
  assert.equal(travelDecision(ev, null, HOME).insert, false);
});

test("event with no location → skip", () => {
  const ev = { summary: "Call mom", location: "", startMs: ms(10) };
  assert.equal(travelDecision(ev, null, HOME).reason, "helper-or-no-location");
});

test("[Travel] helper block itself → skip", () => {
  const ev = { summary: "[Travel] 🚆 A→B", location: "somewhere", startMs: ms(10) };
  assert.equal(travelDecision(ev, null, HOME).insert, false);
});

test("home unknown → skip (no-origin), leave for ask-loop", () => {
  const ev = { summary: "Meeting", location: "渋谷ヒカリエ", startMs: ms(10) };
  assert.equal(travelDecision(ev, null, "").reason, "no-origin");
});

test("home → real venue → INSERT, origin=home", () => {
  const ev = { summary: "松竹 ネタ見せ", location: "新宿1-36-4", startMs: ms(18) };
  const d = travelDecision(ev, null, HOME);
  assert.equal(d.insert, true);
  assert.equal(d.origin, HOME);
});

test("back-to-back: prev ends ≤90min before, different place → origin=prev (office→home travel)", () => {
  const prev = { location: "MUIT 生駒", endMs: ms(17) };
  const ev = { summary: "😴 Sleep", location: HOME, startMs: ms(18) }; // 60min after prev
  const d = travelDecision(ev, prev, HOME);
  assert.equal(d.insert, true);          // genuine travel home from the office
  assert.equal(d.origin, "MUIT 生駒");
});

test("prev far (>90min gap) → origin falls back to home → home→home skip", () => {
  const prev = { location: "MUIT 生駒", endMs: ms(12) };
  const ev = { summary: "😴 Sleep", location: HOME, startMs: ms(18) }; // 6h after prev
  assert.equal(travelDecision(ev, prev, HOME).reason, "same-location");
});

test("null/undefined ev → skip (no crash)", () => {
  assert.equal(travelDecision(null, null, HOME).insert, false);
  assert.equal(travelDecision(undefined, null, HOME).insert, false);
});

test("same-venue back-to-back (prev location == ev location, != home) → skip", () => {
  const prev = { location: "渋谷ヒカリエ", endMs: ms(13) };
  const ev = { summary: "打ち合わせ2", location: "渋谷ヒカリエ", startMs: ms(14) };
  assert.equal(travelDecision(ev, prev, HOME).reason, "same-location");
});

test("prev is a [Travel] helper block → not used as origin (falls back to home)", () => {
  const prev = { summary: "[Travel] 🚆 A→B", location: "somewhere-else", endMs: ms(17) };
  const ev = { summary: "😴 Sleep", location: HOME, startMs: ms(18) };
  // origin must NOT leak from the [Travel] block; falls back to home → home→home skip
  assert.equal(travelDecision(ev, prev, HOME).reason, "same-location");
});
