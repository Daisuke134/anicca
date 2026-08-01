"use strict";
// spec 2026-08-01-lm-daily-organ-design.md §5.2.1 + §5.2.2 (#2c) — the ladder as the wake tick runs it.
//
// D1 puts the rungs on the wake tick, not the organ tick, for the reason 1c split the dial out in the
// first place: departure is the only deadline-critical job here, and an organ that runs slow turns a
// "leave now" into a message that arrives after the user is already late.
//
// Every case below is really one question — does it STOP? §5.2.1: 停止条件の無い連投は嫌がらせ
// であって製品ではない. The stops are three (D5): the tap, the phone being answered, and the crossing
// into the late organ's territory. Location is NOT among them, because #3 does not exist yet.
// Run: node --test test/departure-nudge-tick.test.js
const { test } = require("node:test");
const assert = require("node:assert");

process.env.LM_CALL_SECRET = "unit_secret";
process.env.PUBLIC_WSS = "wss://life-call.invalid";

const { wakeCallOnce, wakeTick, LATE_CUTOFF_MIN } = require("../scheduler.js");
const { NUDGE_LEVELS } = require("../lib/departure-nudge.js");

const MINUTE = 60_000;
const EVENT_START_ISO = "2026-08-05T14:00:00+09:00";
const EVENT_START_MS = Date.parse(EVENT_START_ISO);
const TRAVEL_MIN = 35; // + resolveDeparture's 5-min buffer → departure = start − 40 min
const DEPARTURE_MS = EVENT_START_MS - 40 * MINUTE;

// #6, and since 2026-08-01 the DEFAULT: no phone at all. The ladder is this user's entire product.
const NO_PHONE_USER = {
  uid: "ladder-user",
  name: "Ladder User",
  home_address: "東京都渋谷区",
  call_language: "ja",
  telegram_chat_id: "5550001",
  daily_automation_enabled: true,
  notifications_enabled: true,
  call_enabled: false,
};

const EVENT = {
  id: "ladder-event",
  summary: "新宿で打ち合わせ",
  location: "新宿",
  startMs: EVENT_START_MS,
  startIso: EVENT_START_ISO,
  endMs: EVENT_START_MS + 60 * MINUTE,
};

// A stand-in for lm_departure_nudge that obeys the SAME rule the real table does: one row per event,
// last_level_min strictly decreasing, and acked_at excluding the row from every future claim. The
// unit tests pin that the real PATCH expresses this; here it is modelled so the tick's DECISIONS are
// what is under test.
function harness({ send, answered } = {}) {
  const ledger = new Map();
  const sent = [];
  let attempts = 0;
  const acks = [];
  const deps = {
    recordDailyPoll: async () => true,
    fetchUpcomingEvents: async () => [{ ...EVENT }],
    mapsKey: "ladder-maps-key",
    directionsMinutes: async () => TRAVEL_MIN,
    telegramToken: "ladder-bot-token",
    claimNudgeLevel: async (uid, eventKey, level) => {
      const row = ledger.get(eventKey);
      if (!row) {
        ledger.set(eventKey, { last: level, acked: false });
        return { ok: true, claimed: true, opened: true };
      }
      if (row.acked || !(row.last > level)) return { ok: true, claimed: false };
      row.last = level;
      return { ok: true, claimed: true, opened: false };
    },
    releaseNudgeLevel: async (uid, eventKey, level, opts = {}) => {
      const row = ledger.get(eventKey);
      if (!row || row.last !== level) return { ok: true, matched: 0 };
      if (opts.opened) ledger.delete(eventKey);
      else row.last = NUDGE_LEVELS[NUDGE_LEVELS.indexOf(level) - 1];
      return { ok: true, matched: 1 };
    },
    ackNudge: async (uid, eventKey, reason) => {
      const row = ledger.get(eventKey);
      acks.push({ eventKey, reason });
      if (!row || row.acked) return { ok: true, matched: 0 };
      row.acked = true;
      return { ok: true, matched: 1 };
    },
    wakeWasAnswered: async () => !!answered,
    // `send` is scripted by ATTEMPT, not by delivery — a retry is the second attempt even though it
    // is the first thing the user ever sees.
    sendMessage: async (_token, chatId, text, extra) => {
      attempts += 1;
      const outcome = send ? send(attempts) : { ok: true, result: { message_id: 900 + attempts } };
      if (outcome.ok) sent.push({ chatId, text, hasButton: !!extra });
      return outcome;
    },
    // Nothing in this file should reach the phone; if it does, say so loudly rather than pass.
    claimWake: async () => { throw new Error("the ladder must not touch the phone ledger"); },
    placeCall: async () => { throw new Error("the ladder must not dial"); },
  };
  return { deps, ledger, sent, acks };
}

test("the opening rung reaches a user who never gave a phone number", async () => {
  const h = harness();
  await wakeCallOnce(NO_PHONE_USER, DEPARTURE_MS - 25 * MINUTE, h.deps);
  assert.equal(h.sent.length, 1, "T-25 goes out");
  assert.equal(h.sent[0].chatId, "5550001");
  assert.match(h.sent[0].text, /25/);
  assert.equal(h.sent[0].hasButton, true, "and it carries [了解], which is the only way to stop it");
});

test("a tick that fell behind sends only the most urgent rung it owes", async () => {
  const h = harness();
  // T-10 and T-5 both became due while the process was restarting.
  await wakeCallOnce(NO_PHONE_USER, DEPARTURE_MS - 4 * MINUTE, h.deps);
  assert.equal(h.sent.length, 1, "one message, not a backlog dumped into the chat");
  assert.match(h.sent[0].text, /あと5分/);
  // Monotonicity does the suppressing: last_level_min is 5, so gt.10 can never match again. This is
  // why the ladder needs no equivalent of the phone's "claim the superseded level" dance.
  await wakeCallOnce(NO_PHONE_USER, DEPARTURE_MS - 3 * MINUTE, h.deps);
  assert.equal(h.sent.length, 1, "the skipped coarser rung stays skipped forever");
});

test("one tap ends it: an acknowledged event sends nothing more", async () => {
  const h = harness();
  await wakeCallOnce(NO_PHONE_USER, DEPARTURE_MS - 25 * MINUTE, h.deps);
  await h.deps.ackNudge(NO_PHONE_USER.uid, `${NO_PHONE_USER.uid}|${EVENT_START_ISO}`, "tap");
  for (const at of [-10, -5, 0, 3, 7]) {
    await wakeCallOnce(NO_PHONE_USER, DEPARTURE_MS + at * MINUTE, h.deps);
  }
  assert.equal(h.sent.length, 1, "only the rung sent before the tap");
});

test("answering the phone stops the ladder, and is recorded as the reason", async () => {
  // D5 ③: picking up is the strongest evidence of a reaction there is. Continuing to push someone
  // who just spoke to us is the harassment the stop conditions exist to prevent.
  const h = harness({ answered: true });
  const caller = { ...NO_PHONE_USER, phone: "+810000000000", call_enabled: true };
  h.deps.claimWake = async () => false;  // the phone ladder is not what this case is about
  for (const at of [-25, -10, -5, 0]) {
    await wakeCallOnce(caller, DEPARTURE_MS + at * MINUTE, h.deps);
  }
  assert.deepEqual(h.sent, [], "not one push after the user answered");
  assert.equal(h.acks[0].reason, "call_answered", "and the ledger says why it stopped");
});

test("past the late cutoff the ladder is over, terminal rung included", async () => {
  assert.equal(LATE_CUTOFF_MIN, -15, "the cutoff is the named constant, not a magic number");
  const h = harness();
  await wakeCallOnce(NO_PHONE_USER, DEPARTURE_MS + 16 * MINUTE, h.deps);
  assert.deepEqual(h.sent, [], "this is the late-notice organ's territory now (D5 ②)");
  assert.equal(h.ledger.size, 0, "and no rung was burned on the way out");
});

test("a user who switched the daily automation off is not nudged", async () => {
  const h = harness();
  await wakeCallOnce({ ...NO_PHONE_USER, daily_automation_enabled: false }, DEPARTURE_MS - 25 * MINUTE, h.deps);
  assert.deepEqual(h.sent, []);
  const quiet = harness();
  await wakeCallOnce({ ...NO_PHONE_USER, notifications_enabled: false }, DEPARTURE_MS - 25 * MINUTE, quiet.deps);
  assert.deepEqual(quiet.sent, [], "nor a user who asked for no messages");
});

test("a failed send gives the rung back so the next tick can retry it", async () => {
  // Same posture as a failed dial releasing its claim: the claim exists to prevent a DOUBLE send, so
  // when nothing was sent it must not survive as though something had been.
  const h = harness({ send: (n) => (n === 1 ? { ok: false, error: "telegram 502" } : { ok: true, result: { message_id: 901 } }) });
  await wakeCallOnce(NO_PHONE_USER, DEPARTURE_MS - 25 * MINUTE, h.deps);
  assert.deepEqual(h.sent, [], "nothing was delivered");
  await wakeCallOnce(NO_PHONE_USER, DEPARTURE_MS - 24 * MINUTE, h.deps);
  assert.equal(h.sent.length, 1, "so the next tick sends T-25 after all");
  assert.match(h.sent[0].text, /25/);
});

test("the phone ladder is untouched: still exactly T-10 and T-5", async () => {
  const dialed = [];
  const held = new Set();
  const h = harness();
  const caller = { ...NO_PHONE_USER, phone: "+810000000000", call_enabled: true };
  h.deps.claimWake = async (_uid, key) => (held.has(key) ? false : (held.add(key), true));
  h.deps.placeCall = async ({ streamUrl }) => {
    const params = new URL(streamUrl, "https://life-manager.invalid").searchParams;
    dialed.push(params.get("wakeEventKey").split("|").at(-1));
    return { ok: true, ccid: `ladder-call-${dialed.length}` };
  };
  for (const at of [-25, -10, -5, 0, 3, 7]) {
    await wakeCallOnce(caller, DEPARTURE_MS + at * MINUTE, h.deps);
  }
  assert.deepEqual(dialed, ["10", "5"], "two calls, exactly the two WAKE_LEVELS — no more, no fewer");
  assert.equal(h.sent.length, 6, "and the six Telegram rungs ran alongside them, independently (D2)");
});

// ── the cohort (§5.3) ────────────────────────────────────────────────────────────────────────────

// ★ THE test this file was missing ★. Every case above calls wakeCallOnce directly — one layer BELOW
// where the cohort is chosen — so they all stayed green while wakeTick's own `call_enabled === true`
// filter kept the ladder from reaching a single user it was built for. §5.3 makes phone-less the
// DEFAULT cohort, so that filter shipped the feature to nobody.
//
// The three shapes below are the ones 2b had to enumerate for the opposite reason: no preference row,
// a SQL NULL column, and an explicit false. All three mean "no phone", and all three must get rungs.
test("every automated user enters the wake tick, not just the ones with a phone", async () => {
  const entered = [];
  await wakeTick({
    listUsers: async () => [
      { uid: "no-pref-row", daily_automation_enabled: true },                      // no call_enabled at all
      { uid: "null-column", daily_automation_enabled: true, call_enabled: null },  // SQL NULL
      { uid: "opted-out-of-calls", daily_automation_enabled: true, call_enabled: false },
      { uid: "caller", daily_automation_enabled: true, call_enabled: true },
    ],
    wake: async (u) => { entered.push(u.uid); },
    now: 0,
  });
  assert.deepEqual(entered.sort(), ["caller", "no-pref-row", "null-column", "opted-out-of-calls"],
    "the ladder is the product for phone-less users — the tick must not filter them out");
});

test("the one switch that means 'run nothing for me' still empties the tick", async () => {
  const entered = [];
  await wakeTick({
    listUsers: async () => [{ uid: "opted-out", daily_automation_enabled: false, call_enabled: true }],
    wake: async (u) => { entered.push(u.uid); },
    now: 0,
  });
  assert.deepEqual(entered, [], "daily_automation_enabled=false is the real opt-out and still holds");
});

// ── budget order (§3 row 1c) ─────────────────────────────────────────────────────────────────────

// scheduler.js:509 records the failure this pins: bookkeeping placed in front of placeCall "spent the
// user's entire wake budget and the phone never rang". The ladder is up to three sequential HTTP
// calls with no timeout of their own, so for a phone user it must run AFTER the dial. Row 1c bought
// that 20s budget for the dial; the ladder does not get to spend it first.
test("for a phone user the dial goes out before the ladder spends any of the budget", async () => {
  const order = [];
  const h = harness();
  const caller = { ...NO_PHONE_USER, phone: "+810000000000", call_enabled: true };
  h.deps.claimWake = async () => "claim-token";
  h.deps.placeCall = async () => { order.push("dial"); return { ok: true, ccid: "order-1" }; };
  const claim = h.deps.claimNudgeLevel;
  h.deps.claimNudgeLevel = async (...args) => { order.push("nudge"); return claim(...args); };

  await wakeCallOnce(caller, DEPARTURE_MS - 5 * MINUTE, h.deps);
  assert.deepEqual(order, ["dial", "nudge"], "the phone rings first; the ladder's I/O comes after");
});
