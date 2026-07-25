"use strict";
// MEN-b: the MENTAL organ speaks, it never asks. Spec 9.11 allows one direction only and at most one
// emoji, and the message has to belong to the moment it was triggered by — a pre-sleep line must not
// be usable before a meeting. These tests pin the rule before the copy exists.
const assert = require("node:assert/strict");
const test = require("node:test");

const { SEED_LIMIT, validateMentalMessage, buildMentalMessage, buildSamples } = require("./mental-copy.js");

const SEEDS = [
  "I am enough exactly as I am",
  "I choose peace over worry",
  "I release what I cannot control",
  "My potential is limitless",
];

test("a question is refused because the MENTAL organ never asks", () => {
  for (const text of ["準備はできてる?", "How are you feeling?", "眠れそう？"]) {
    const verdict = validateMentalMessage(text);
    assert.equal(verdict.ok, false, `expected "${text}" to be refused`);
    assert.equal(verdict.reason, "not_one_directional");
  }
});

test("a message asking for a reply is refused even without a question mark", () => {
  for (const text of ["返信して", "教えてください", "reply when you can"]) {
    assert.equal(validateMentalMessage(text).reason, "not_one_directional");
  }
});

test("at most one emoji is allowed", () => {
  assert.equal(validateMentalMessage("準備は全部入ってる。あとは話すだけ").ok, true);
  assert.equal(validateMentalMessage("🌙 今日はここまでで充分だ").ok, true);
  assert.equal(validateMentalMessage("🌙✨ 今日はここまでで充分だ").reason, "too_many_emoji");
});

test("an empty or whitespace message is refused", () => {
  assert.equal(validateMentalMessage("").reason, "empty");
  assert.equal(validateMentalMessage("   ").reason, "empty");
});

test("a message long enough to be a lecture is refused", () => {
  assert.equal(validateMentalMessage("あ".repeat(121)).reason, "too_long");
});

test("each trigger produces copy that belongs to its own moment", () => {
  const pre = buildMentalMessage({ trigger: "pre_event", seed: SEEDS[0] });
  const between = buildMentalMessage({ trigger: "between_events", seed: SEEDS[0] });
  const sleep = buildMentalMessage({ trigger: "pre_sleep", seed: SEEDS[0] });

  assert.notEqual(pre, between);
  assert.notEqual(between, sleep);
  for (const text of [pre, between, sleep]) {
    assert.equal(validateMentalMessage(text).ok, true, `generated copy must satisfy the rule: ${text}`);
  }
});

test("the seed shapes the message rather than being read out verbatim", () => {
  const text = buildMentalMessage({ trigger: "pre_event", seed: SEEDS[1] });
  assert.ok(!text.includes(SEEDS[1]), "an English affirmation must not be pasted into Japanese copy");
  assert.ok(text.length > 8);
});

test("an unknown trigger is refused rather than silently defaulted", () => {
  assert.throws(() => buildMentalMessage({ trigger: "whenever", seed: SEEDS[0] }), /trigger/);
});

test("a missing seed is refused", () => {
  assert.throws(() => buildMentalMessage({ trigger: "pre_event", seed: "" }), /seed/);
});

test("ten samples can be produced and every one satisfies the rule", () => {
  const samples = buildSamples(SEEDS, 10);
  assert.equal(samples.length, 10);
  for (const sample of samples) {
    assert.ok(["pre_event", "between_events", "pre_sleep"].includes(sample.trigger));
    const verdict = validateMentalMessage(sample.text);
    assert.equal(verdict.ok, true, `sample failed: ${sample.text} (${verdict.reason})`);
  }
  // Ten identical lines would not be "situation specific" in any useful sense.
  assert.ok(new Set(samples.map((sample) => sample.text)).size >= 6);
});

test("the sample run refuses to invent more variety than the seeds can carry", () => {
  assert.throws(() => buildSamples(SEEDS, SEED_LIMIT * SEEDS.length + 1), /samples/);
});
