// telegram-onboard.test.js — onboarding stage machine. Run: node --test apps/life-call/lib/telegram-onboard.test.js
"use strict";
const { test } = require("node:test");
const assert = require("node:assert");
const { computeStage, stageMessage } = require("./telegram-onboard.js");

const base = { telegram_chat_id: "123", calendar_provider: "composio_gcal", gmail_account_id: "g", phone: "+81", paid: true };

test("null row → calendar (first step)", () => assert.equal(computeStage(null), "calendar"));
test("linked, no calendar → calendar", () => assert.equal(computeStage({ ...base, calendar_provider: null, paid: false }), "calendar"));
test("calendar done, no gmail → gmail", () => assert.equal(computeStage({ ...base, gmail_account_id: null, paid: false }), "gmail"));
test("gmail done, no phone → phone", () => assert.equal(computeStage({ ...base, phone: null, paid: false }), "phone"));
test("phone done, not paid → pay", () => assert.equal(computeStage({ ...base, paid: false }), "pay"));
test("paid → done", () => assert.equal(computeStage(base), "done"));
test("paid overrides missing fields → done", () => assert.equal(computeStage({ telegram_chat_id: "1", paid: true }), "done"));

test("each stage message has the right button link except done", () => {
  for (const stage of ["calendar", "gmail", "phone", "pay"]) {
    const m = stageMessage(stage, "999", "https://aniccaai.com");
    assert.ok(m.text.length > 0, `${stage} has text`);
    assert.equal(m.extra.reply_markup.inline_keyboard[0][0].url, "https://aniccaai.com/lm?tg=999");
  }
  const done = stageMessage("done", "999", "https://aniccaai.com");
  assert.equal(done.extra, undefined);
  assert.ok(/all set/i.test(done.text));
});

test("acknowledgement copy: gmail stage acknowledges calendar; pay acknowledges phone", () => {
  assert.ok(/Calendar connected/i.test(stageMessage("gmail", "1", "x").text));
  assert.ok(/Phone saved/i.test(stageMessage("pay", "1", "x").text));
});
