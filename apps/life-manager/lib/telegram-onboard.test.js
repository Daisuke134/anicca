// telegram-onboard.test.js — LM-6 minimal-question onboarding stage machine.
// Run: node --test apps/life-call/lib/telegram-onboard.test.js
"use strict";
const { test } = require("node:test");
const assert = require("node:assert");
const {
  computeStage, stageMessage, isNativeStage, normalizePhone, telegramProfileName,
  applyTelegramProfileName, handleGmailCallback, onboardNudgeAll, backfillIfCalendarCompleted,
  NUDGE_COOLDOWN_MS,
} = require("./telegram-onboard.js");
const { startReply } = require("./telegram.js");

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

// ── Demo comp window (LM_COMP_UNTIL) ──────────────────────────────────────────
// A stranger who scans the demo QR must not hit a $20 wall mid-onboarding. The comp is a READ-TIME
// override with an expiry; lm_users.paid is never written, so Stripe stays the single writer.
function withCompUntil(value, fn) {
  const previous = process.env.LM_COMP_UNTIL;
  process.env.LM_COMP_UNTIL = value;
  try { return fn(); } finally {
    if (previous === undefined) delete process.env.LM_COMP_UNTIL; else process.env.LM_COMP_UNTIL = previous;
  }
}
// Async variant: a sync try/finally would restore the env before the awaited body ever runs.
async function withCompUntilAsync(value, fn) {
  const previous = process.env.LM_COMP_UNTIL;
  process.env.LM_COMP_UNTIL = value;
  try { return await fn(); } finally {
    if (previous === undefined) delete process.env.LM_COMP_UNTIL; else process.env.LM_COMP_UNTIL = previous;
  }
}
const future = () => new Date(Date.now() + 3600000).toISOString();
const past = () => new Date(Date.now() - 1000).toISOString();

test("comp active: an unpaid row walks past the paywall to the next stage", () => {
  withCompUntil(future(), () => {
    assert.equal(computeStage({ ...full, paid: false }), "done");
    assert.equal(computeStage({ ...full, paid: false, gmail_account_id: null, gmail_skipped: false }), "gmail");
  });
});

test("comp active does NOT skip earlier stages — calendar and phone still gate", () => {
  withCompUntil(future(), () => {
    assert.equal(computeStage({ ...full, paid: false, calendar_provider: null }), "calendar");
    assert.equal(computeStage({ ...full, paid: false, phone: null }), "phone");
  });
});

test("comp expired or invalid → the pay gate is exactly as before", () => {
  withCompUntil(past(), () => assert.equal(computeStage({ ...full, paid: false }), "pay"));
  withCompUntil("whenever", () => assert.equal(computeStage({ ...full, paid: false }), "pay"));
  withCompUntil("", () => assert.equal(computeStage({ ...full, paid: false }), "pay"));
});

test("comp is injectable, so callers can pin the clock without touching process.env", () => {
  const until = "2026-07-27T12:00:00.000Z";
  const env = { LM_COMP_UNTIL: until };
  assert.equal(computeStage({ ...full, paid: false }, { env, now: Date.parse(until) - 1 }), "done");
  assert.equal(computeStage({ ...full, paid: false }, { env, now: Date.parse(until) }), "pay");
});

test("comp NEVER writes lm_users.paid — Stripe stays the single writer", async () => {
  const patches = [], stages = [];
  await withCompUntilAsync(future(), async () => {
    await onboardNudgeAll({
      token: "t", base: "https://x", supaUrl: "s", supaKey: "k", nudgeStore: new Map(),
      linkedRows: async () => [{ ...full, paid: false, gmail_account_id: null, gmail_skipped: true, tg_onboard_stage: "pay" }],
      sendStage: async () => {},
      saveField: async (_uid, patch) => patches.push(patch),
      setStage: async (_uid, stage) => stages.push(stage),
    });
  });
  assert.deepEqual(stages, ["done"]);
  for (const patch of patches) assert.equal(Object.prototype.hasOwnProperty.call(patch, "paid"), false);
});

test("telegram-onboard.js contains no write of the paid column", () => {
  const src = require("node:fs").readFileSync(require("node:path").join(__dirname, "telegram-onboard.js"), "utf8");
  assert.equal(/paid\s*:/.test(src), false, "the comp must stay a read-time override");
});

// ── Nudge discipline ──────────────────────────────────────────────────────────
// The loop ticks every 2 minutes over every linked row. Without a cooldown a user mid-web-flow gets
// re-prompted the moment a stage changes, and the loop ignored the notifications toggle its siblings
// (ask/discovery) already honour.
const nudgeRow = (over = {}) => ({ ...full, phone: null, paid: false, tg_onboard_stage: "calendar", ...over });

test("notifications_enabled=false gets nothing", async () => {
  const calls = [];
  const sent = await onboardNudgeAll({
    token: "t", base: "https://x", supaUrl: "s", supaKey: "k", nudgeStore: new Map(),
    linkedRows: async () => [nudgeRow({ notifications_enabled: false })],
    sendStage: async () => calls.push("send"),
    setStage: async () => calls.push("stage"),
    backfillCalendarContext: async () => calls.push("context"),
  });
  assert.equal(sent, 0);
  assert.deepEqual(calls, []);
});

test("notifications_enabled true/undefined still nudges (undefined must not fail closed)", async () => {
  for (const value of [true, undefined]) {
    const sent = await onboardNudgeAll({
      token: "t", base: "https://x", supaUrl: "s", supaKey: "k", nudgeStore: new Map(),
      linkedRows: async () => [nudgeRow({ notifications_enabled: value })],
      sendStage: async () => {}, setStage: async () => {}, backfillCalendarContext: async () => {},
    });
    assert.equal(sent, 1, `notifications_enabled=${value}`);
  }
});

test("same-stage suppression still works (no cooldown entry is even created)", async () => {
  const store = new Map();
  const sent = await onboardNudgeAll({
    token: "t", base: "https://x", supaUrl: "s", supaKey: "k", nudgeStore: store,
    linkedRows: async () => [nudgeRow({ tg_onboard_stage: "phone" })], // computeStage → phone
    sendStage: async () => { throw new Error("must not send"); },
    setStage: async () => { throw new Error("must not persist"); },
  });
  assert.equal(sent, 0);
  assert.equal(store.size, 0);
});

test("a stage CHANGE inside the 30-min cooldown still waits, then fires once elapsed", async () => {
  const store = new Map();
  const stages = [];
  const t0 = Date.parse("2026-07-27T00:00:00.000Z");
  const run = (row, now) => onboardNudgeAll({
    token: "t", base: "https://x", supaUrl: "s", supaKey: "k", nudgeStore: store, now,
    linkedRows: async () => [row], sendStage: async () => {},
    setStage: async (_uid, stage) => stages.push(stage), backfillCalendarContext: async () => {},
  });
  assert.equal(await run(nudgeRow({ tg_onboard_stage: "calendar" }), t0), 1); // calendar → phone
  assert.deepEqual(stages, ["phone"]);
  // stage really changed (phone → pay) but only 2 minutes have passed → hold
  assert.equal(await run(nudgeRow({ phone: "+81", tg_onboard_stage: "phone" }), t0 + 2 * 60000), 0);
  assert.equal(await run(nudgeRow({ phone: "+81", tg_onboard_stage: "phone" }), t0 + NUDGE_COOLDOWN_MS - 1), 0);
  assert.deepEqual(stages, ["phone"]);
  // cooldown elapsed → the pending change is finally announced
  assert.equal(await run(nudgeRow({ phone: "+81", tg_onboard_stage: "phone" }), t0 + NUDGE_COOLDOWN_MS), 1);
  assert.deepEqual(stages, ["phone", "pay"]);
});

test("the cooldown is 30 minutes and is per-uid, not global", async () => {
  assert.equal(NUDGE_COOLDOWN_MS, 30 * 60 * 1000);
  const store = new Map();
  const t0 = Date.parse("2026-07-27T00:00:00.000Z");
  const rows = [nudgeRow({ uid: "a" }), nudgeRow({ uid: "b" })];
  const sent = await onboardNudgeAll({
    token: "t", base: "https://x", supaUrl: "s", supaKey: "k", nudgeStore: store, now: t0,
    linkedRows: async () => rows, sendStage: async () => {}, setStage: async () => {},
    backfillCalendarContext: async () => {},
  });
  assert.equal(sent, 2);
  assert.deepEqual([...store.keys()].sort(), ["a", "b"]);
});

test("linkedRows joins notifications_enabled from lm_panel_preferences in ONE batched query", async () => {
  const { linkedRows } = require("./telegram-onboard.js");
  const urls = [];
  const fetchImpl = async (url) => {
    urls.push(String(url));
    if (String(url).includes("lm_panel_preferences")) {
      return { ok: true, json: async () => [{ uid: "a", notifications_enabled: false }] };
    }
    return { ok: true, json: async () => [{ uid: "a" }, { uid: "b" }] };
  };
  const rows = await linkedRows("https://supa.test", "key", { fetchImpl });
  assert.equal(urls.length, 2, "one users query + one batched preferences query");
  assert.equal(rows.find(r => r.uid === "a").notifications_enabled, false);
  assert.equal(rows.find(r => r.uid === "b").notifications_enabled, true); // no preferences row → default on
});

test("Telegram /start identifies the product only as Life Manager", () => {
  const reply = startReply("1", "https://life.example");
  assert.match(reply.text, /^👋 <b>Life Manager<\/b>/);
  assert.doesNotMatch(reply.text, /\bAnicca\b/i);
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
    nudgeStore: new Map(), // isolated per test: the real store is module-level and 30-min sticky
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
    nudgeStore: new Map(), // isolated per test: the real store is module-level and 30-min sticky
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
  assert.equal(normalizePhone("+810000000000"), "+810000000000");
  assert.equal(normalizePhone("08012345678"), "+8012345678");
  assert.equal(normalizePhone("+44 (20) 7946-0958"), "+442079460958");
});
test("normalizePhone: junk → null", () => {
  assert.equal(normalizePhone("hello"), null);
  assert.equal(normalizePhone("123"), null);
  assert.equal(normalizePhone(""), null);
});
