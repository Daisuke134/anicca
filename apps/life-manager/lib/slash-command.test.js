// lib/slash-command.test.js — spec §12.1 row 4: the generic slash-command router.
"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const {
  parseSlashCommand,
  slashAliasText,
  helpMessage,
  handleSlashCommand,
} = require("./slash-command.js");

const NOW = Date.parse("2026-07-30T12:00:00.000Z");

const ROW = Object.freeze({
  uid: "u1", telegram_chat_id: "100", tg_onboard_stage: "done",
  calendar_provider: "composio_gcal", phone: "+819012345678", paid: true,
  gmail_skipped: true, payout_destination: null, name: "Fixture",
});

function harness(overrides = {}) {
  const sent = [];
  const logs = [];
  const deps = {
    token: "t", chatId: "100", base: "https://lm.test",
    supaUrl: "https://db.test", supaKey: "k", nowMs: NOW,
    send: async (token, chatId, text, extra) => { sent.push({ token, chatId, text, extra }); return { ok: true, result: { message_id: 1 } }; },
    log: (line) => logs.push(line),
    getLiveLocation: async () => null,
    deleteLiveLocation: async () => ({ deleted: 0 }),
    setStage: async () => {},
    askPayoutQuestion: async () => ({ asked: true }),
    ...overrides,
  };
  return { sent, logs, deps };
}

test("parseSlashCommand recognises /commands, bot-name suffixes, and args; plain text is null", () => {
  assert.deepEqual(parseSlashCommand("/help"), { name: "help", args: "" });
  assert.deepEqual(parseSlashCommand("  /WHERE  "), { name: "where", args: "" });
  assert.deepEqual(parseSlashCommand("/help@LifeManagerBot"), { name: "help", args: "" });
  assert.deepEqual(parseSlashCommand("/panel@LifeManagerBot AB2cdef3"), { name: "panel", args: "AB2cdef3" });
  assert.deepEqual(parseSlashCommand("/frobnicate now please"), { name: "frobnicate", args: "now please" });
  assert.equal(parseSlashCommand("hello"), null);
  assert.equal(parseSlashCommand("feedback: /where broke"), null);
  assert.equal(parseSlashCommand(""), null);
  assert.equal(parseSlashCommand(undefined), null);
  assert.equal(parseSlashCommand("/ nope"), null);
});

test("slashAliasText maps /connect to the same NL control flow and nothing else", () => {
  assert.equal(slashAliasText(parseSlashCommand("/connect")), "connect calendar");
  assert.equal(slashAliasText(parseSlashCommand("/connect@LifeManagerBot")), "connect calendar");
  assert.equal(slashAliasText(parseSlashCommand("/help")), null);
  assert.equal(slashAliasText(parseSlashCommand("/frobnicate")), null);
  assert.equal(slashAliasText(null), null);
});

test("helpMessage lists every legacy-parity command and the NL actions from kind:help", () => {
  const text = helpMessage();
  for (const name of ["/start", "/panel", "/help", "/status", "/where", "/stop", "/subscribe", "/connect", "/payout", "/reset"]) {
    assert.ok(text.includes(name), `help must list ${name}`);
  }
  // kind:"help" wiring: the availableActions parseUserCommand computes are no longer dropped.
  assert.ok(text.includes("connect calendar"), "help must include the NL availableActions");
});

test("/start and /panel pass through untouched — their existing branches stay the owner", async () => {
  for (const raw of ["/start", "/panel", "/panel AB2cdef3", "/start panel"]) {
    const { sent, deps } = harness();
    const outcome = await handleSlashCommand(parseSlashCommand(raw), ROW, deps);
    assert.deepEqual(outcome, { handled: false }, raw);
    assert.equal(sent.length, 0, raw);
  }
});

test("unknown /command gets an honest unknown reply pointing at /help", async () => {
  const { sent, deps } = harness();
  const outcome = await handleSlashCommand(parseSlashCommand("/frobnicate now"), ROW, deps);
  assert.equal(outcome.handled, true);
  assert.equal(outcome.action, "unknown");
  assert.equal(sent.length, 1);
  assert.ok(sent[0].text.includes("/frobnicate"), "names the command it did not understand");
  assert.ok(sent[0].text.includes("/help"), "points at /help");
});

test("/help replies with the command list", async () => {
  const { sent, deps } = harness();
  const outcome = await handleSlashCommand(parseSlashCommand("/help"), ROW, deps);
  assert.deepEqual(outcome, { handled: true, action: "help" });
  assert.equal(sent.length, 1);
  assert.equal(sent[0].text, helpMessage());
});

test("account-scoped commands on an unlinked chat get the setup-first reply and touch no store", async () => {
  for (const raw of ["/status", "/where", "/stop", "/payout", "/reset"]) {
    let stores = 0;
    const { sent, deps } = harness({
      getLiveLocation: async () => { stores++; return null; },
      deleteLiveLocation: async () => { stores++; return { deleted: 0 }; },
      setStage: async () => { stores++; },
      askPayoutQuestion: async () => { stores++; return { asked: true }; },
    });
    const outcome = await handleSlashCommand(parseSlashCommand(raw), null, deps);
    assert.equal(outcome.handled, true, raw);
    assert.equal(outcome.ok, false, raw);
    assert.equal(outcome.reason, "unlinked", raw);
    assert.equal(stores, 0, `${raw} must not touch the store for an unlinked chat`);
    assert.equal(sent.length, 1, raw);
    assert.ok(sent[0].text.includes("/start"), `${raw} setup-first reply names /start`);
  }
});

test("/where formats a stored fix privacy-safe (rounded coords, age, expiry — no fabricated accuracy)", async () => {
  const { sent, deps } = harness({
    getLiveLocation: async (uid) => {
      assert.equal(uid, "u1");
      return {
        uid: "u1", latitude: 35.681236, longitude: 139.767125,
        observed_at: new Date(NOW - 42_000).toISOString(),
        expires_at: new Date(NOW + 14 * 60_000).toISOString(),
      };
    },
  });
  const outcome = await handleSlashCommand(parseSlashCommand("/where"), ROW, deps);
  assert.deepEqual(outcome, { handled: true, action: "where", ok: true });
  assert.equal(sent.length, 1);
  const text = sent[0].text;
  assert.ok(text.includes("35.68"), "rounded latitude");
  assert.ok(text.includes("139.77"), "rounded longitude");
  assert.ok(!text.includes("35.681236"), "full-precision latitude never echoed");
  assert.ok(!text.includes("139.767125"), "full-precision longitude never echoed");
  assert.ok(text.includes("42s"), "age in seconds");
  assert.ok(text.includes("14"), "expiry minutes");
  assert.ok(!/accuracy/i.test(text), "accuracy is not stored, so it is never fabricated");
});

test("/where with no stored fix is an honest none reply", async () => {
  const { sent, deps } = harness({ getLiveLocation: async () => null });
  const outcome = await handleSlashCommand(parseSlashCommand("/where"), ROW, deps);
  assert.deepEqual(outcome, { handled: true, action: "where", ok: true, stored: false });
  assert.equal(sent.length, 1);
  assert.ok(/don't have|no fresh/i.test(sent[0].text));
  assert.ok(/Live Location/i.test(sent[0].text), "tells the user how to share");
});

test("/stop deletes the tenant's stored location and writes an audit log line", async () => {
  const deleted = [];
  const { sent, logs, deps } = harness({
    deleteLiveLocation: async (uid) => { deleted.push(uid); return { deleted: 1 }; },
  });
  const outcome = await handleSlashCommand(parseSlashCommand("/stop"), ROW, deps);
  assert.deepEqual(outcome, { handled: true, action: "stop", ok: true, deleted: 1 });
  assert.deepEqual(deleted, ["u1"], "delete is scoped to THIS row's uid");
  assert.equal(sent.length, 1);
  assert.ok(/deleted/i.test(sent[0].text));
  assert.equal(logs.length, 1, "audit log entry");
  assert.ok(logs[0].includes("[location]"), "audit names the surface");
  assert.ok(logs[0].includes("deleted=1"), "audit records the outcome");
  assert.ok(!logs[0].includes("u1-secret"), "sanity");
});

test("/stop with nothing stored and with a failed delete stay honest", async () => {
  const none = harness({ deleteLiveLocation: async () => ({ deleted: 0 }) });
  const zero = await handleSlashCommand(parseSlashCommand("/stop"), ROW, none.deps);
  assert.deepEqual(zero, { handled: true, action: "stop", ok: true, deleted: 0 });
  assert.ok(/no stored|nothing/i.test(none.sent[0].text), "zero rows is said, not dressed as a delete");

  const broken = harness({ deleteLiveLocation: async () => null });
  const fail = await handleSlashCommand(parseSlashCommand("/stop"), ROW, broken.deps);
  assert.deepEqual(fail, { handled: true, action: "stop", ok: false, reason: "delete_failed" });
  assert.ok(/couldn't|could not/i.test(broken.sent[0].text), "a failed delete is a visible failure");
  assert.ok(broken.logs[0].includes("deleted=error"), "audit records the failure");
});

test("/subscribe reuses the onboard link builder and never invents URLs", async () => {
  const { sent, deps } = harness();
  const outcome = await handleSlashCommand(parseSlashCommand("/subscribe"), { ...ROW, paid: false }, deps);
  assert.deepEqual(outcome, { handled: true, action: "subscribe", ok: true });
  assert.equal(sent.length, 1);
  const keyboard = sent[0].extra.reply_markup.inline_keyboard;
  assert.equal(keyboard[0][0].url, "https://lm.test/lm?tg=100", "the existing onboardLink builder, verbatim");
});

test("/subscribe on an already-paid row says so instead of re-linking; unlinked chats still get the link", async () => {
  const paid = harness();
  const active = await handleSlashCommand(parseSlashCommand("/subscribe"), ROW, paid.deps);
  assert.deepEqual(active, { handled: true, action: "subscribe", ok: true, alreadyActive: true });
  assert.ok(/already active/i.test(paid.sent[0].text));
  assert.equal(paid.sent[0].extra, undefined, "no checkout button for an active subscription");

  const fresh = harness();
  const linked = await handleSlashCommand(parseSlashCommand("/subscribe"), null, fresh.deps);
  assert.deepEqual(linked, { handled: true, action: "subscribe", ok: true });
  assert.equal(fresh.sent[0].extra.reply_markup.inline_keyboard[0][0].url, "https://lm.test/lm?tg=100");
});

test("/subscribe without a chat id is an honest unavailable reply, not an invented URL", async () => {
  const { sent, deps } = harness({ chatId: "" });
  const outcome = await handleSlashCommand(parseSlashCommand("/subscribe"), null, deps);
  assert.deepEqual(outcome, { handled: true, action: "subscribe", ok: false, reason: "link_unavailable" });
  assert.ok(/unavailable/i.test(sent[0].text));
  assert.equal(sent[0].extra, undefined);
});

test("/reset reuses setStage to restart onboarding announcements and confirms", async () => {
  const staged = [];
  const { sent, deps } = harness({
    setStage: async (uid, stage, supaUrl, supaKey) => { staged.push({ uid, stage, supaUrl, supaKey }); },
  });
  const outcome = await handleSlashCommand(parseSlashCommand("/reset"), ROW, deps);
  assert.deepEqual(outcome, { handled: true, action: "reset", ok: true });
  assert.deepEqual(staged, [{ uid: "u1", stage: "calendar", supaUrl: "https://db.test", supaKey: "k" }]);
  assert.equal(sent.length, 1);
  assert.ok(sent[0].text.includes("/start"), "confirm message tells the user how to continue");
});

test("/payout reopens the picker through askPayoutQuestion (its read makes the reopen idempotent)", async () => {
  const asks = [];
  const { sent, deps } = harness({
    askPayoutQuestion: async (args) => { asks.push(args); return { asked: true }; },
  });
  const outcome = await handleSlashCommand(parseSlashCommand("/payout"), ROW, deps);
  assert.deepEqual(outcome, { handled: true, action: "payout", ok: true, asked: true });
  assert.equal(asks.length, 1);
  assert.equal(asks[0].uid, "u1");
  assert.equal(asks[0].chatId, "100");
  assert.equal(sent.length, 0, "the question itself is sent by askPayoutQuestion, never duplicated here");
});

test("/payout surfaces already-answered silently (askPayoutQuestion replied) and failures honestly", async () => {
  const answered = harness({ askPayoutQuestion: async () => ({ asked: false, reason: "already_answered" }) });
  const already = await handleSlashCommand(parseSlashCommand("/payout"), ROW, answered.deps);
  assert.deepEqual(already, { handled: true, action: "payout", ok: true, asked: false, reason: "already_answered" });
  assert.equal(answered.sent.length, 0, "askPayoutQuestion already sent the already-registered reply");

  const broken = harness({ askPayoutQuestion: async () => ({ asked: false, reason: "lookup_failed" }) });
  const fail = await handleSlashCommand(parseSlashCommand("/payout"), ROW, broken.deps);
  assert.deepEqual(fail, { handled: true, action: "payout", ok: false, asked: false, reason: "lookup_failed" });
  assert.equal(broken.sent.length, 1);
  assert.ok(/couldn't|could not/i.test(broken.sent[0].text), "a failed lookup is a visible failure");
});

test("/status projects only real local data: stage, connections, payout, location — no fabricated fields", async () => {
  const { sent, deps } = harness({
    getLiveLocation: async () => ({
      uid: "u1", latitude: 35.68, longitude: 139.76,
      observed_at: new Date(NOW - 9_000).toISOString(),
      expires_at: new Date(NOW + 60_000).toISOString(),
    }),
  });
  const outcome = await handleSlashCommand(parseSlashCommand("/status"), ROW, deps);
  assert.deepEqual(outcome, { handled: true, action: "status", ok: true });
  const text = sent[0].text;
  assert.ok(/Onboarding: done/.test(text));
  assert.ok(/Calendar: connected/.test(text));
  assert.ok(/Phone: on file/.test(text));
  assert.ok(/Subscription: active/.test(text));
  assert.ok(/Payout: not set/.test(text));
  assert.ok(/observed 9s ago/.test(text));
  assert.ok(!/call|cron|daemon/i.test(text), "nothing the webhook cannot read is claimed");
});

test("/status stays honest for the sparse row and the missing location", async () => {
  const row = {
    uid: "u2", telegram_chat_id: "200", tg_onboard_stage: "phone",
    calendar_provider: null, phone: null, paid: false,
    payout_destination: { type: "wallet", status: "awaiting_address" },
  };
  const { sent, deps } = harness({ getLiveLocation: async () => null });
  await handleSlashCommand(parseSlashCommand("/status"), row, deps);
  const text = sent[0].text;
  assert.ok(/Onboarding: at the "calendar" step/.test(text), "stage is computed from the row, not the stale column");
  assert.ok(/Calendar: not connected/.test(text));
  assert.ok(/Phone: not set/.test(text));
  assert.ok(/Subscription: not active/.test(text));
  assert.ok(/Payout: awaiting typed address/.test(text));
  assert.ok(/Location: not available/.test(text));
});
