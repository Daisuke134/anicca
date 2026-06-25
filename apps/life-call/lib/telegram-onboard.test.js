// telegram-onboard.test.js — onboarding stage machine. Run: node --test apps/life-call/lib/telegram-onboard.test.js
// v1 (Dais 2026-06-25): Telegram users do NOT connect Gmail — flow = name → calendar → phone → pay → done.
"use strict";
const { test } = require("node:test");
const assert = require("node:assert");
const { computeStage, stageMessage, isNativeStage, normalizePhone } = require("./telegram-onboard.js");

const full = { telegram_chat_id: "1", name: "Dais", calendar_provider: "composio_gcal", phone: "+81", paid: true };

test("null row → name (first step, asked in chat)", () => assert.equal(computeStage(null), "name"));
test("row without name → name", () => assert.equal(computeStage({ ...full, name: null, paid: false }), "name"));
test("name set, no calendar → calendar", () => assert.equal(computeStage({ ...full, calendar_provider: null, paid: false }), "calendar"));
test("calendar set, no phone → phone (Gmail stage dropped)", () => assert.equal(computeStage({ ...full, phone: null, paid: false }), "phone"));
test("gmail_account_id is NOT required — absent gmail still reaches done", () => assert.equal(computeStage({ ...full, gmail_account_id: null }), "done"));
test("phone set, not paid → pay", () => assert.equal(computeStage({ ...full, paid: false }), "pay"));
test("all set + paid → done", () => assert.equal(computeStage(full), "done"));
test("order is strict: missing name beats everything", () => assert.equal(computeStage({ ...full, name: null }), "name"));

test("name + phone are NATIVE (typed in chat); calendar/pay are not", () => {
  assert.ok(isNativeStage("name"));
  assert.ok(isNativeStage("phone"));
  assert.ok(!isNativeStage("calendar"));
  assert.ok(!isNativeStage("pay"));
});

test("name/phone messages have NO button (native ask); calendar/pay have a button", () => {
  assert.equal(stageMessage("name", "1", "x").extra, undefined);
  assert.equal(stageMessage("phone", "1", "x").extra, undefined);
  for (const s of ["calendar", "pay"]) {
    assert.equal(stageMessage(s, "9", "https://aniccaai.com").extra.reply_markup.inline_keyboard[0][0].url, "https://aniccaai.com/lm?tg=9");
  }
});

test("name message asks for the name", () => assert.ok(/what'?s your name/i.test(stageMessage("name", "1", "x").text)));
test("phone acknowledges calendar; pay acknowledges phone", () => {
  assert.ok(/Calendar connected/i.test(stageMessage("phone", "1", "x").text));
  assert.ok(/Phone saved/i.test(stageMessage("pay", "1", "x").text));
});

test("normalizePhone: valid forms", () => {
  assert.equal(normalizePhone("+818012345678"), "+818012345678");
  assert.equal(normalizePhone("08012345678"), "+8012345678"); // strips leading 0, prefixes +
  assert.equal(normalizePhone("+1 (415) 555-2671"), "+14155552671");
});
test("normalizePhone: junk → null", () => {
  assert.equal(normalizePhone("hello"), null);
  assert.equal(normalizePhone("123"), null);
  assert.equal(normalizePhone(""), null);
});
