// telegram-onboard.test.js — LM-6 minimal-question onboarding stage machine.
// Run: node --test apps/life-call/lib/telegram-onboard.test.js
"use strict";
const { test } = require("node:test");
const assert = require("node:assert");
const {
  computeStage, stageMessage, isNativeStage, normalizePhone, telegramProfileName,
  applyTelegramProfileName, handleGmailCallback, onboardNudgeAll, backfillIfCalendarCompleted,
} = require("./telegram-onboard.js");

const full = {
  uid: "u1", telegram_chat_id: "1", name: "Dais", calendar_provider: "composio_gcal",
  phone: "+81", paid: true, gmail_account_id: "gmail-1", gmail_skipped: false,
};

test("null row → calendar (name is never a blocking typed stage)", () => assert.equal(computeStage(null), "calendar"));
test("no calendar → calendar even when name is absent", () => assert.equal(computeStage({ ...full, name: null, calendar_provider: null }), "calendar"));
test("calendar set, no phone → phone", () => assert.equal(computeStage({ ...full, phone: null, paid: false }), "phone"));
test("phone set, not paid → pay", () => assert.equal(computeStage({ ...full, paid: false }), "pay"));
test("paid without Gmail decision → gmail", () => assert.equal(computeStage({ ...full, gmail_account_id: null, gmail_skipped: false }), "gmail"));
test("Gmail connected → done", () => assert.equal(computeStage(full), "done"));
test("Gmail skipped → done", () => assert.equal(computeStage({ ...full, gmail_account_id: null, gmail_skipped: true }), "done"));
test("order is strict: phone and pay precede Gmail", () => {
  assert.equal(computeStage({ ...full, phone: null, paid: true, gmail_account_id: null }), "phone");
  assert.equal(computeStage({ ...full, paid: false, gmail_account_id: null }), "pay");
});

test("telegramProfileName: derives name from first_name + last_name", () => {
  assert.equal(telegramProfileName({ first_name: " Dais ", last_name: " Tanaka " }), "Dais Tanaka");
  assert.equal(telegramProfileName({ first_name: "Dais" }), "Dais");
  assert.equal(telegramProfileName(null), "");
});
test("applyTelegramProfileName: fills missing name without overwriting an existing name", () => {
  assert.deepEqual(applyTelegramProfileName(null, { first_name: "Dais", last_name: "Tanaka" }), { name: "Dais Tanaka" });
  assert.equal(applyTelegramProfileName({ name: "Existing" }, { first_name: "Dais" }).name, "Existing");
  assert.equal(computeStage(applyTelegramProfileName(null, { first_name: "Dais" })), "calendar");
});

test("phone is the only NATIVE typed stage", () => {
  assert.ok(isNativeStage("phone"));
  for (const stage of ["name", "calendar", "pay", "gmail", "done"]) assert.ok(!isNativeStage(stage));
});

test("calendar/pay carry web buttons; Gmail carries connect + skip buttons", () => {
  for (const s of ["calendar", "pay"]) {
    assert.equal(stageMessage(s, "9", "https://aniccaai.com").extra.reply_markup.inline_keyboard[0][0].url, "https://aniccaai.com/lm?tg=9");
  }
  const buttons = stageMessage("gmail", "9", "https://aniccaai.com", "https://life.example/gmail-connect").extra.reply_markup.inline_keyboard[0];
  assert.equal(buttons[0].url, "https://life.example/gmail-connect");
  assert.equal(buttons[1].callback_data, "gmail:skip");
});

test("phone acknowledges calendar; pay acknowledges phone; Gmail never claims connection", () => {
  assert.match(stageMessage("phone", "1", "x").text, /Calendar connected/i);
  assert.match(stageMessage("pay", "1", "x").text, /Phone saved/i);
  assert.match(stageMessage("gmail", "1", "x").text, /Gmail/i);
  assert.doesNotMatch(stageMessage("gmail", "1", "x").text, /connected!/i);
});

test("Gmail skip persists gmail_skipped=true and advances to done", async () => {
  const saved = [], stages = [], sent = [];
  const result = await handleGmailCallback("gmail:skip", full, {
    token: "t", chatId: "1", base: "https://x", saveField: async (_uid, patch) => saved.push(patch),
    setStage: async (_uid, stage) => stages.push(stage), sendMessage: async (_t, _c, text) => sent.push(text),
  });
  assert.deepEqual(result, { ok: true, stage: "done" });
  assert.deepEqual(saved, [{ gmail_skipped: true }]);
  assert.deepEqual(stages, ["done"]);
  assert.match(sent[0], /all set/i);
});

test("Gmail OFF: onboarding auto-skips with an honest preparation message and no OAuth button", async () => {
  const saved = [], stages = [], messages = [];
  const row = { ...full, gmail_account_id: null, gmail_skipped: false, tg_onboard_stage: "gmail" };
  const sent = await onboardNudgeAll({ token: "t", base: "https://x", supaUrl: "s", supaKey: "k",
    linkedRows: async () => [row], mailAvailable: async () => false,
    saveField: async (_uid, patch) => saved.push(patch),
    sendMessage: async (_token, _chat, text, extra) => messages.push({ text, extra }),
    setStage: async (_uid, stage) => stages.push(stage) });
  assert.equal(sent, 1);
  assert.deepEqual(saved, [{ gmail_skipped: true }]);
  assert.deepEqual(stages, ["done"]);
  assert.match(messages[0].text, /currently being prepared/i);
  assert.equal(messages[0].extra, undefined);
});

test("calendar completion triggers best-effort context backfill once before announcing phone", async () => {
  const calls = [];
  const row = { ...full, phone: null, paid: false, tg_onboard_stage: "calendar" };
  const sent = await onboardNudgeAll({ token: "t", base: "https://x", supaUrl: "s", supaKey: "k",
    linkedRows: async () => [row], sendStage: async () => calls.push("send"),
    setStage: async (_uid, stage) => calls.push(`stage:${stage}`),
    backfillCalendarContext: async (uid) => calls.push(`context:${uid}`),
  });
  assert.equal(sent, 1);
  assert.deepEqual(calls, ["context:u1", "send", "stage:phone"]);
});

test("calendar completion hook also runs on immediate /start or text resume", async () => {
  const calls = [];
  const row = { ...full, phone: null, paid: false, tg_onboard_stage: "calendar" };
  assert.equal(await backfillIfCalendarCompleted(row, {
    backfillCalendarContext: async (uid) => calls.push(uid),
  }), true);
  assert.deepEqual(calls, ["u1"]);
  assert.equal(await backfillIfCalendarCompleted({ ...row, tg_onboard_stage: "phone" }, {
    backfillCalendarContext: async () => calls.push("unexpected"),
  }), false);
});

test("normalizePhone: valid forms", () => {
  assert.equal(normalizePhone("+818012345678"), "+818012345678");
  assert.equal(normalizePhone("08012345678"), "+8012345678");
  assert.equal(normalizePhone("+1 (415) 555-2671"), "+14155552671");
});
test("normalizePhone: junk → null", () => {
  assert.equal(normalizePhone("hello"), null);
  assert.equal(normalizePhone("123"), null);
  assert.equal(normalizePhone(""), null);
});
