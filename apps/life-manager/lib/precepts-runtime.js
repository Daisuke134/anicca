"use strict";
// H4 ORG-precepts — the production leg of the observation (spec §10 NEXT HORIZON row H4 ①/②/④/⑤).
//
// precepts-question.js decides WHEN; this module is the only place the decision touches the world.
// It is the H2 diet organ's runtime with one addition — the MENTAL budget — and every problem H2
// solved is solved the same way here rather than a slightly different way:
//
//   CLAIM BEFORE SEND. It rides the same 60s tick as MENTAL/PHYSICAL/DIET, and the bedtime window is
//     30 minutes wide, so 30 ticks see "ask". The claim is an INSERT into lm_precepts_log guarded by
//     UNIQUE (uid, day, kind); the loser of the race gets a 409 and stops without sending. Honest
//     cost, stated rather than hidden: if Telegram then fails, the ask row stands (the ledger is
//     append-only, so we cannot take it back) and this week's slot is spent. That is the safe side —
//     a lost question costs one data point, a duplicated question costs the user's patience, and the
//     7-day spacing means the next attempt is a week out anyway.
//   WINDOW BEFORE READ. The bedtime window is checked before Supabase is touched: for 23½ of every
//     24 hours this organ must cost exactly nothing, and a read placed ahead of the clock check bills
//     the whole fleet 1440 times a day to learn what arithmetic already knew.
//   STRICT LEDGER READS + A LOG-ONCE LATCH. An unreadable history never becomes "never asked" —
//     that is how a weekly cap turns into a nightly one during an incident — but the 60s tick must
//     not narrate the same outage 30 times. One line per user per local day.
//   THE DAY RIDES IN THE CALLBACK. A keyboard never expires on its own, so the tap says which night
//     it is about; a tap from an older night is refused VISIBLY rather than back-filled.
//   WHOSE CLOCK. deps.tzOffsetH → the user row's own zone → LM_PRECEPTS_UTC_OFFSET_HOURS → NOTHING.
//     When the chain runs out the organ stays SILENT for that user and says so once per boot. A
//     default of JST would ask a Berlin user this question at 06:30.
//
// AND THE ONE THING H2 DOES NOT DO — H4 ⑤, 別枠にしない. The ask is a MENTAL send: it reads
// lm_mental_send_log before deciding (3/day cap, 2h spacing) and writes to it after delivering. The
// user does not experience "the precepts organ" and "the mental organ"; they experience one stream of
// unsolicited evening messages, and two organs each politely keeping to three a day is six a day.
//
// The tap writes nothing but the choice. §10.0-15 ① is honoured by EDITING the question message —
// that edit IS the visible response, so no thank-you is sent. A follow-up on every tap would turn a
// once-a-week question into a conversation the user has to close.

const {
  evaluatePreceptsAsk, preceptsQuestionMessage, PRECEPTS_ANSWER_LABELS,
} = require("./precepts-question.js");
const { PRECEPTS_STRINGS } = require("./i18n.js");
const { sendMessage } = require("./telegram.js");
const { reflectAnswer } = require("./telegram-callback-visibility.js");
const { localDay, resolveUserTzOffsetH } = require("./user-tz.js");
const { resolveSleepTarget } = require("./mental-runtime.js");
const { readMentalSendState, recordMentalSend } = require("./mental-send-log.js");

// The ask day rides in the callback data (see preceptsQuestionMessage).
const PRECEPTS_CALLBACK = /^precepts:answer:(lie|harsh|time|impulse|calm):(\d{4}-\d{2}-\d{2})$/;
const WEEK_MS = 7 * 86400000;
// The MENTAL trigger token these sends are recorded under. Both are new legal values of
// lm_mental_send_log.trigger — see migrations/2026-07-27-lm-mental-send-log-precepts-trigger.sql.
const PRECEPTS_SEND_TRIGGER = "precepts";
const PRECEPTS_TZ_ENV_KEYS = Object.freeze(["LM_PRECEPTS_UTC_OFFSET_HOURS"]);

function headers(key, extra) {
  return { apikey: key, Authorization: `Bearer ${key}`, ...extra };
}

function supaBase(url) {
  return String(url).replace(/\/$/, "");
}

function resolvePreceptsTzOffsetH(source = {}, row = null, nowMs = Date.now()) {
  return resolveUserTzOffsetH(source, row, nowMs, PRECEPTS_TZ_ENV_KEYS);
}

// The user's own bedtime, resolved every tick because a bedtime is a clock time in their day rather
// than an instant. Same machinery MENTAL's pre_sleep trigger uses, fed the user's OWN offset instead
// of the scheduler's fleet-wide LM_MENTAL_UTC_OFFSET_HOURS default — a shared question at the wrong
// hour is worse than no question.
function resolvePreceptsSleepTarget(deps, nowMs, offsetH) {
  if (Number.isFinite(deps && deps.sleepTargetMs)) return deps.sleepTargetMs;
  const clock = (deps && deps.sleepClock)
    || process.env.LM_PRECEPTS_SLEEP_TARGET
    || process.env.LM_MENTAL_SLEEP_TARGET
    || "23:30";
  return resolveSleepTarget(clock, nowMs, offsetH);
}

// Two log latches, both module state ON PURPOSE — being module state is what makes them latches.
const MISSING_TZ_LOGGED = new Set();          // uid → warned once since boot
const LEDGER_UNREADABLE_LOGGED = new Set();   // `${uid}|${day}` → warned once for that day

function resetPreceptsRuntimeState() {
  MISSING_TZ_LOGGED.clear();
  LEDGER_UNREADABLE_LOGGED.clear();
}

function logOnce(latch, key, log, line) {
  if (latch.has(key)) return;
  latch.add(key);
  (log || console.warn)(line);
}

// The weekly spacing is a TRAILING 7 days, not a calendar week: a Sunday/Monday boundary would let
// Saturday's ask be followed by Sunday's. Throws on any failure — see the header.
//
// The FILTER is on `day`, which is the column the (uid, day DESC) index actually serves, with a
// one-day cushion so no timezone slop can drop a row at the edge. The exact trailing-168-hours cut
// is then made in JS on asked_at: the index picks the candidates, the timestamp decides.
async function readPreceptsAskState(uid, nowMs, supa, fetchImpl, tzOffsetH = 0) {
  const floorDay = localDay(nowMs - WEEK_MS - 86400000, tzOffsetH);
  const query = `uid=eq.${encodeURIComponent(uid)}&kind=eq.ask`
    + `&day=gte.${encodeURIComponent(floorDay)}&select=asked_at,day&order=day.desc`;
  const response = await fetchImpl(`${supaBase(supa.supaUrl)}/rest/v1/lm_precepts_log?${query}`, {
    headers: headers(supa.supaKey),
  }).catch(() => null);
  if (!response || !response.ok) {
    throw new Error(`precepts ask state lookup failed (${response ? response.status : "no response"})`);
  }
  const rows = await response.json().catch(() => null);
  if (!Array.isArray(rows)) throw new Error("precepts ask state lookup returned no rows array");
  const times = rows
    .map((row) => Date.parse(row.asked_at))
    .filter((ms) => Number.isFinite(ms) && ms >= nowMs - WEEK_MS && ms <= nowMs);
  return { askedThisWeek: times.length, lastAskMs: times.length ? Math.max(...times) : null };
}

// 201 = this tick owns the (uid, day, kind) slot. 409 / PostgREST 23505 = another tick or another tap
// already owns it. Anything else is a real failure and THROWS: a Supabase 500 is not "already
// claimed", and swallowing it would silently drop the row we are about to act on.
async function claimPreceptsRow(row, supa, fetchImpl) {
  const response = await fetchImpl(`${supaBase(supa.supaUrl)}/rest/v1/lm_precepts_log`, {
    method: "POST",
    headers: headers(supa.supaKey, { "Content-Type": "application/json", Prefer: "return=minimal" }),
    body: JSON.stringify(row),
  });
  if (response && response.status === 201) return true;
  if (response && response.status === 409) return false;
  const body = response && typeof response.text === "function" ? await response.text().catch(() => "") : "";
  if (/23505|duplicate key/i.test(body)) return false;
  throw new Error(`precepts log insert failed (${response ? response.status : "no response"})`
    + `${body ? `: ${body.slice(0, 200)}` : ""}`);
}

async function readPreceptsRow(uid, day, kind, supa, fetchImpl) {
  const query = `uid=eq.${encodeURIComponent(uid)}&day=eq.${encodeURIComponent(day)}`
    + `&kind=eq.${encodeURIComponent(kind)}&select=answer,created_at&limit=1`;
  const response = await fetchImpl(`${supaBase(supa.supaUrl)}/rest/v1/lm_precepts_log?${query}`, {
    headers: headers(supa.supaKey),
  }).catch(() => null);
  if (!response || !response.ok) return null;
  const rows = await response.json().catch(() => null);
  return Array.isArray(rows) && rows[0] ? rows[0] : null;
}

async function preceptsUserOnce(u, nowMs, deps = {}) {
  const supa = {
    supaUrl: deps.supaUrl || process.env.SUPABASE_URL,
    supaKey: deps.supaKey || process.env.SUPABASE_SERVICE_ROLE_KEY,
  };
  const chatId = String((u && u.telegram_chat_id) || "");
  // notifications_enabled is the same opt-out the late/mental/diet siblings honour — one switch turns
  // off every unsolicited Telegram message, and this organ is nothing but unsolicited messages.
  if (!u || !u.uid || !chatId || u.notifications_enabled === false || !supa.supaUrl || !supa.supaKey) {
    return { status: "skipped" };
  }
  const fetchImpl = deps.fetchImpl || globalThis.fetch;

  const offsetH = resolvePreceptsTzOffsetH(deps, u, nowMs);
  if (offsetH === null) {
    logOnce(MISSING_TZ_LOGGED, u.uid, deps.log,
      `[precepts] uid=${String(u.uid).slice(0, 12)} no resolvable timezone (row zone / LM_PRECEPTS_UTC_OFFSET_HOURS)`
      + " — the bedtime question stays SILENT for this user");
    return { status: "skipped", reason: "no-timezone" };
  }

  const sleepTargetMs = resolvePreceptsSleepTarget(deps, nowMs, offsetH);
  if (!Number.isFinite(sleepTargetMs)) return { status: "skipped", reason: "no-sleep-target" };
  // Window before read — see the header.
  const untilSleep = sleepTargetMs - nowMs;
  if (untilSleep < 0 || untilSleep > 30 * 60000) {
    return { status: "suppressed", reason: "outside-bedtime-window" };
  }
  const day = localDay(nowMs, offsetH);

  let state;
  let mentalState;
  try {
    state = await readPreceptsAskState(u.uid, nowMs, supa, fetchImpl, offsetH);
    // STRICT: an unreadable MENTAL budget must not read as an empty one. This organ would otherwise
    // spend a cap it cannot see, which is worse than the same mistake inside MENTAL itself.
    mentalState = await (deps.readMentalSendState || readMentalSendState)(
      u.uid, nowMs, supa, fetchImpl, { strict: true },
    );
  } catch (error) {
    logOnce(LEDGER_UNREADABLE_LOGGED, `${u.uid}|${day}`, deps.log,
      `[precepts] uid=${String(u.uid).slice(0, 12)} day=${day} ledger unreadable, staying silent: ${error && error.message}`);
    return { status: "suppressed", reason: "ledger-unreadable" };
  }

  // Same wiring as MENTAL's and DIET's (scheduler passes one provider to all three). Nothing supplies
  // it in production today, so this reads the constant "unknown" — a present gate, not a live one.
  const locationState = deps.getLocationState ? await deps.getLocationState(u.uid, nowMs) : "unknown";
  const verdict = evaluatePreceptsAsk({
    nowMs,
    sleepTargetMs,
    sentTodayCount: Number(mentalState && mentalState.sentTodayCount) || 0,
    lastMentalSentMs: mentalState && Number.isFinite(mentalState.lastSentMs) ? mentalState.lastSentMs : null,
    lastAskMs: state.lastAskMs,
    events: (Array.isArray(deps.events) ? deps.events : [])
      .map((event) => ({ startMs: Number(event.startMs), endMs: Number(event.endMs) }))
      .filter((event) => Number.isFinite(event.startMs) && event.endMs > event.startMs),
    location: { state: locationState || "unknown" },
  });
  if (verdict.decision !== "ask") return { status: "suppressed", reason: verdict.reason };

  const claimed = await claimPreceptsRow({
    uid: u.uid, day, kind: "ask", asked_at: new Date(nowMs).toISOString(),
  }, supa, fetchImpl);
  if (!claimed) return { status: "already_asked" };

  // The keyboard carries `day`, so this exact question can only ever be answered as this night.
  const message = preceptsQuestionMessage(day);
  const sent = await (deps.sendMessage || sendMessage)(
    deps.telegramToken !== undefined ? deps.telegramToken : process.env.LM_TELEGRAM_BOT_TOKEN,
    chatId, message.text, message.extra,
  );
  if (!sent || !sent.ok) return { status: "send_failed", day };
  const messageId = sent.result && sent.result.message_id;
  // H4 ⑤: the question spends one of MENTAL's three. Recorded AFTER delivery — a row for a message
  // nobody received would suppress a real affirmation later tonight for no reason.
  const budgeted = await (deps.recordMentalSend || recordMentalSend)(
    u.uid, PRECEPTS_SEND_TRIGGER, messageId, supa, fetchImpl,
  );
  return { status: "asked", day, telegramMessageId: messageId, budgeted };
}

// The tap. Guards before writes, in the order that makes a wrong write impossible rather than merely
// unlikely — the same actorId===chatId + row-re-verify pair payout-address-intake and the diet organ
// use. This ledger holds the most private thing the product records, so the boundary is not softened.
async function handlePreceptsCallback(data, opts = {}) {
  const match = PRECEPTS_CALLBACK.exec(String(data || ""));
  if (!match) return { ignored: true };
  const [, answer, askedDay] = match;
  const copy = PRECEPTS_STRINGS.ja.nightQuestion;
  const row = opts.row || null;
  const chatId = String(opts.chatId || "");
  const actorId = String(opts.actorId || "");

  if (!row || !row.uid || !chatId) return { handled: true, ok: false, answer, reason: "unlinked" };
  if (!actorId || actorId !== chatId) return { handled: true, ok: false, answer, reason: "scope_mismatch" };
  // Defence in depth: the row handed to us must itself name this chat. A row-lookup bug upstream must
  // fail here rather than file one person's evening under another person's uid.
  if (String(row.telegram_chat_id || "") !== chatId) {
    return { handled: true, ok: false, answer, reason: "row_chat_mismatch" };
  }

  const supa = {
    supaUrl: opts.supaUrl || process.env.SUPABASE_URL,
    supaKey: opts.supaKey || process.env.SUPABASE_SERVICE_ROLE_KEY,
  };
  if (!supa.supaUrl || !supa.supaKey) return { handled: true, ok: false, answer, reason: "unconfigured" };
  const fetchImpl = opts.fetchImpl || globalThis.fetch;
  const nowMs = opts.nowMs == null ? Date.now() : opts.nowMs;
  const token = opts.token !== undefined ? opts.token : process.env.LM_TELEGRAM_BOT_TOKEN;

  // The row's day comes from the QUESTION, never from the clock at tap time. A tap at 00:20 is still
  // an answer about the evening that just ended, and filing it as the next day would invent a night
  // that was never asked about.
  const day = askedDay;

  // Stale taps are refused rather than back-filled: an answer arriving days later is not evidence
  // about the night it names any more. The tz chain may end in null here (the webhook has no
  // per-user zone to read); when it does we cannot say what "today" is, so we do NOT guess — we
  // accept the tap under the day it carries, which is safe precisely because the day is carried.
  const offsetH = resolvePreceptsTzOffsetH(opts, row, nowMs);
  if (offsetH !== null && day !== localDay(nowMs, offsetH)) {
    // CB-1: strip the dead keyboard WITHOUT claiming a choice, then say why the button did nothing.
    await reflectPreceptsTap(opts, "", "");
    await (opts.sendMessage || sendMessage)(token, chatId, copy.expired);
    return { handled: true, ok: false, answer, day, reason: "expired" };
  }

  let claimed;
  try {
    claimed = await claimPreceptsRow({
      uid: row.uid, day, kind: "answer", answer, answered_at: new Date(nowMs).toISOString(),
      ...(opts.messageId ? { telegram_message_id: String(opts.messageId) } : {}),
    }, supa, fetchImpl);
  } catch {
    // Never dress an unwritten answer as a recorded one: no edit, no reassuring reply.
    return { handled: true, ok: false, answer, reason: "persist_failed" };
  }

  if (!claimed) {
    // §10.0-15 ③: a second tap is visible. It reports what is ALREADY on file — telling the user we
    // recorded 「なし・穏やかだった」 when the row says 「きつく当たった」 would be a comfortable lie
    // about their own evening.
    const existing = await readPreceptsRow(row.uid, day, "answer", supa, fetchImpl);
    const recorded = existing && PRECEPTS_ANSWER_LABELS[existing.answer];
    const choice = recorded || PRECEPTS_ANSWER_LABELS[answer];
    // Function replacer: a label is data, and `$&`/`$'` inside data must never be re-expanded.
    await (opts.sendMessage || sendMessage)(token, chatId,
      copy.alreadyAnswered.replace("{choice}", () => choice));
    // Strip the stale keyboard without appending a label — the choice on file may not be this tap's.
    await reflectPreceptsTap(opts, "", "");
    return { handled: true, ok: false, answer, reason: "already_answered" };
  }

  // §10.0-15 ①: the recorded choice becomes visible ON the question, and the keyboard goes away.
  // No thank-you follows: the edit is the answer, and the flow does not continue (②).
  await reflectPreceptsTap(opts, PRECEPTS_ANSWER_LABELS[answer], opts.messageText);
  return { handled: true, ok: true, answer, day };
}

// Best-effort visibility, exactly like reflectDietTap / reflectPayoutTap: it never throws and never
// gates the persisted outcome — a Telegram outage here degrades to "toast only".
function reflectPreceptsTap(opts, label, messageText) {
  if (!opts.token || !opts.chatId || !opts.messageId) return Promise.resolve({ ok: false });
  return (opts.reflectAnswer || reflectAnswer)({
    token: opts.token, chatId: opts.chatId, messageId: opts.messageId,
    messageText, label, fetchImpl: opts.fetchImpl,
  });
}

module.exports = {
  PRECEPTS_CALLBACK,
  PRECEPTS_SEND_TRIGGER,
  resolvePreceptsTzOffsetH,
  resolvePreceptsSleepTarget,
  resetPreceptsRuntimeState,
  readPreceptsAskState,
  claimPreceptsRow,
  readPreceptsRow,
  preceptsUserOnce,
  handlePreceptsCallback,
};
