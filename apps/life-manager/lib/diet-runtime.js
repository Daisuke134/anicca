"use strict";
// H2 ORG-diet — the production leg of the observation (spec §10 NEXT HORIZON row H2 ①/②).
//
// diet-question.js decides WHEN; this module is the only place the decision touches the world. It
// rides the same 60s tick as MENTAL and PHYSICAL, which is exactly why the claim comes first: the
// lunch window is 120 minutes wide, so 120 ticks see "ask" and without a durable claim the user
// gets 120 identical questions. The claim is an INSERT into lm_diet_log guarded by
// UNIQUE (uid, day, kind) — the claimWake / lm_care_scan_log precedent, so a restart can neither
// double-ask nor forget.
//
// Claim-before-send has one honest cost, stated rather than hidden: if Telegram then fails, the ask
// row stands (the ledger is append-only, so we cannot take it back) and today's slot is spent. That
// is the safe side of the trade — a lost question costs one data point, a duplicated question costs
// the user's patience, and the 48h spacing means the next attempt is two days out anyway.
//
// Reading the ledger is STRICT: readDietAskState THROWS rather than returning "never asked", because
// treating an outage as an empty history is precisely how a weekly cap turns into a daily one during
// an incident. dietUserOnce catches that throw, reports `ledger-unreadable`, and LOGS IT ONCE per
// user per local day — a 60s tick would otherwise print the same Supabase error 120 times a window.
//
// WHOSE CLOCK. There is no timezone column on lm_users, and this branch does not invent one. The
// chain is: an explicit deps.tzOffsetH → the user row's own zone if the row carries one (scheduler
// merges lm_panel_preferences.call_time_zone, the only tz column that actually exists, onto the row)
// → LM_DIET_UTC_OFFSET_HOURS → NOTHING. When the chain runs out, the organ stays SILENT for that
// user and says so once per boot. A default of JST would ask a Berlin user at 04:30 and a Los
// Angeles user at 20:00; an unasked question costs one data point, a 3am question costs the trust
// that makes every other organ tolerable.
//
// The tap writes nothing but the choice. §10.0-15 ① is honoured by EDITING the question message —
// that edit IS the visible response, so no thank-you is sent. A follow-up message on every tap
// would make a once-every-48-hours question feel like a conversation the user has to close.
//
// LOCATION. deps.getLocationState is a real gate here and it is fed exactly the way MENTAL's is —
// scheduler passes the same injected provider through to both. In production today that provider
// does not exist, so BOTH organs read the constant "unknown": the gate is present and wired, not
// live. That is the sibling's honest state, and this file claims no more than the sibling has.

const {
  evaluateDietQuestion, dietQuestionMessage, DIET_ANSWER_LABELS,
  localMinuteOfDay, WINDOW_START_MIN, WINDOW_END_MIN,
} = require("./diet-question.js");
const { DIET_STRINGS } = require("./i18n.js");
const { sendMessage } = require("./telegram.js");
const { reflectAnswer } = require("./telegram-callback-visibility.js");

// The ask day rides in the callback data (see dietQuestionMessage): a keyboard never expires on its
// own, so the tap has to say which lunch it is about.
const DIET_CALLBACK = /^diet:answer:(teishoku|men|fast|skip):(\d{4}-\d{2}-\d{2})$/;
const WEEK_MS = 7 * 86400000;

function headers(key, extra) {
  return { apikey: key, Authorization: `Bearer ${key}`, ...extra };
}

function supaBase(url) {
  return String(url).replace(/\/$/, "");
}

// The user's LOCAL calendar day as YYYY-MM-DD. Lunch is a local idea: a UTC day would file a 00:30
// JST row under yesterday and split one person's lunch history across two days.
function localDay(nowMs, tzOffsetH) {
  return new Date(nowMs + tzOffsetH * 3600000).toISOString().slice(0, 10);
}

// An IANA zone name → its UTC offset in hours AT THAT INSTANT (so DST is handled by the platform's
// tz database rather than by us). Returns null for anything Intl refuses, because a zone name we
// cannot read is not evidence that the user lives in Tokyo.
function zoneOffsetHours(timeZone, atMs) {
  if (typeof timeZone !== "string" || !timeZone.trim()) return null;
  try {
    const parts = new Intl.DateTimeFormat("en-CA", {
      timeZone, year: "numeric", month: "2-digit", day: "2-digit",
      hour: "2-digit", minute: "2-digit", second: "2-digit", hourCycle: "h23",
    }).formatToParts(new Date(atMs));
    const at = Object.fromEntries(parts.filter((p) => p.type !== "literal").map((p) => [p.type, p.value]));
    const wallMs = Date.UTC(Number(at.year), Number(at.month) - 1, Number(at.day),
      Number(at.hour), Number(at.minute), Number(at.second));
    if (!Number.isFinite(wallMs)) return null;
    return (wallMs - Math.floor(atMs / 1000) * 1000) / 3600000;
  } catch {
    return null;
  }
}

// The honest chain, in order, ending in null rather than in a guess. `source` is the caller's deps
// or callback opts; `row` is the user row (which carries call_time_zone when the caller selected it
// — lm_users itself has no tz column, and this branch does not add one).
const TZ_ROW_KEYS = Object.freeze(["call_time_zone", "time_zone", "timezone", "tz"]);
function resolveDietTzOffsetH(source = {}, row = null, nowMs = Date.now()) {
  if (Number.isFinite(source && source.tzOffsetH)) return source.tzOffsetH;
  for (const key of TZ_ROW_KEYS) {
    const offsetH = zoneOffsetHours(row && row[key], nowMs);
    if (Number.isFinite(offsetH)) return offsetH;
  }
  const fromEnv = Number(process.env.LM_DIET_UTC_OFFSET_HOURS);
  if (Number.isFinite(fromEnv) && String(process.env.LM_DIET_UTC_OFFSET_HOURS || "").trim() !== "") return fromEnv;
  return null;
}

// Two log latches, both module state ON PURPOSE — being module state is what makes them latches.
// The organ runs on a 60s tick, so anything logged unconditionally is logged 1440 times a day per
// user, which buries every line worth reading.
const MISSING_TZ_LOGGED = new Set(); // uid → warned once since boot
const LEDGER_UNREADABLE_LOGGED = new Set(); // `${uid}|${day}` → warned once for that day

function resetDietRuntimeState() {
  MISSING_TZ_LOGGED.clear();
  LEDGER_UNREADABLE_LOGGED.clear();
}

function logOnce(latch, key, log, line) {
  if (latch.has(key)) return;
  latch.add(key);
  (log || console.warn)(line);
}

// The weekly cap is a TRAILING 7 days, not a calendar week: a Sunday/Monday boundary would let three
// asks on Saturday be followed by three more on Sunday. Throws on any failure — see the header.
//
// The FILTER is on `day`, which is the column the (uid, day DESC) index actually serves, with a
// one-day cushion so no timezone slop can drop a row at the edge. The exact trailing-168-hours cut
// is then made in JS on asked_at: the index picks the candidates, the timestamp decides.
async function readDietAskState(uid, nowMs, supa, fetchImpl, tzOffsetH = 0) {
  const floorDay = localDay(nowMs - WEEK_MS - 86400000, tzOffsetH);
  const query = `uid=eq.${encodeURIComponent(uid)}&kind=eq.ask`
    + `&day=gte.${encodeURIComponent(floorDay)}&select=asked_at,day&order=day.desc`;
  const response = await fetchImpl(`${supaBase(supa.supaUrl)}/rest/v1/lm_diet_log?${query}`, {
    headers: headers(supa.supaKey),
  }).catch(() => null);
  if (!response || !response.ok) {
    throw new Error(`diet ask state lookup failed (${response ? response.status : "no response"})`);
  }
  const rows = await response.json().catch(() => null);
  if (!Array.isArray(rows)) throw new Error("diet ask state lookup returned no rows array");
  const times = rows
    .map((row) => Date.parse(row.asked_at))
    .filter((ms) => Number.isFinite(ms) && ms >= nowMs - WEEK_MS && ms <= nowMs);
  return { askedThisWeek: times.length, lastAskMs: times.length ? Math.max(...times) : null };
}

// 201 = this tick owns the (uid, day, kind) slot. 409 / PostgREST 23505 = another tick or another
// tap already owns it. Anything else is a real failure and THROWS: a Supabase 500 is not "already
// claimed", and swallowing it would silently drop the row we are about to act on.
async function claimDietRow(row, supa, fetchImpl) {
  const response = await fetchImpl(`${supaBase(supa.supaUrl)}/rest/v1/lm_diet_log`, {
    method: "POST",
    headers: headers(supa.supaKey, { "Content-Type": "application/json", Prefer: "return=minimal" }),
    body: JSON.stringify(row),
  });
  if (response && response.status === 201) return true;
  if (response && response.status === 409) return false;
  const body = response && typeof response.text === "function" ? await response.text().catch(() => "") : "";
  if (/23505|duplicate key/i.test(body)) return false;
  throw new Error(`diet log insert failed (${response ? response.status : "no response"})`
    + `${body ? `: ${body.slice(0, 200)}` : ""}`);
}

async function readDietRow(uid, day, kind, supa, fetchImpl) {
  const query = `uid=eq.${encodeURIComponent(uid)}&day=eq.${encodeURIComponent(day)}`
    + `&kind=eq.${encodeURIComponent(kind)}&select=answer,created_at&limit=1`;
  const response = await fetchImpl(`${supaBase(supa.supaUrl)}/rest/v1/lm_diet_log?${query}`, {
    headers: headers(supa.supaKey),
  }).catch(() => null);
  if (!response || !response.ok) return null;
  const rows = await response.json().catch(() => null);
  return Array.isArray(rows) && rows[0] ? rows[0] : null;
}

async function dietUserOnce(u, nowMs, deps = {}) {
  const supa = {
    supaUrl: deps.supaUrl || process.env.SUPABASE_URL,
    supaKey: deps.supaKey || process.env.SUPABASE_SERVICE_ROLE_KEY,
  };
  const chatId = String((u && u.telegram_chat_id) || "");
  // notifications_enabled is the same opt-out the late/mental siblings honour — one switch turns
  // off every unsolicited Telegram message, and the diet organ is nothing but unsolicited messages.
  if (!u || !u.uid || !chatId || u.notifications_enabled === false || !supa.supaUrl || !supa.supaKey) {
    return { status: "skipped" };
  }
  const fetchImpl = deps.fetchImpl || globalThis.fetch;

  const offsetH = resolveDietTzOffsetH(deps, u, nowMs);
  if (offsetH === null) {
    logOnce(MISSING_TZ_LOGGED, u.uid, deps.log,
      `[diet] uid=${String(u.uid).slice(0, 12)} no resolvable timezone (row zone / LM_DIET_UTC_OFFSET_HOURS)`
      + " — the lunch question stays SILENT for this user");
    return { status: "skipped", reason: "no-timezone" };
  }

  // The window is checked BEFORE Supabase is touched, mirroring the nudge leg: for 22 of every 24
  // hours this organ must cost exactly nothing, and a read placed ahead of the clock check bills the
  // whole fleet 1440 times a day to learn what arithmetic already knew.
  const minute = localMinuteOfDay(nowMs, offsetH);
  if (minute < WINDOW_START_MIN || minute > WINDOW_END_MIN) {
    return { status: "suppressed", reason: "outside-lunch-window" };
  }
  const day = localDay(nowMs, offsetH);

  let state;
  try {
    state = await readDietAskState(u.uid, nowMs, supa, fetchImpl, offsetH);
  } catch (error) {
    // Strictness is preserved — an unreadable history still never becomes "never asked" — but the
    // 60s tick must not narrate the same outage 120 times. One line per user per day.
    logOnce(LEDGER_UNREADABLE_LOGGED, `${u.uid}|${day}`, deps.log,
      `[diet] uid=${String(u.uid).slice(0, 12)} day=${day} ledger unreadable, staying silent: ${error && error.message}`);
    return { status: "suppressed", reason: "ledger-unreadable" };
  }
  // Same wiring as MENTAL's (scheduler passes one provider to both). Unfed in production today, so
  // this reads the constant "unknown" for every user — a present gate, not a live one.
  const locationState = deps.getLocationState ? await deps.getLocationState(u.uid, nowMs) : "unknown";
  const verdict = evaluateDietQuestion({
    nowMs,
    tzOffsetH: offsetH,
    events: (Array.isArray(deps.events) ? deps.events : [])
      .map((event) => ({ startMs: Number(event.startMs), endMs: Number(event.endMs) }))
      .filter((event) => Number.isFinite(event.startMs) && event.endMs > event.startMs),
    askedThisWeek: state.askedThisWeek,
    lastAskMs: state.lastAskMs,
    location: { state: locationState || "unknown" },
  });
  if (verdict.decision !== "ask") return { status: "suppressed", reason: verdict.reason };

  const claimed = await claimDietRow({
    uid: u.uid, day, kind: "ask", asked_at: new Date(nowMs).toISOString(),
  }, supa, fetchImpl);
  if (!claimed) return { status: "already_asked" };

  // The keyboard carries `day`, so this exact question can only ever be answered as this day.
  const message = dietQuestionMessage(day);
  const sent = await (deps.sendMessage || sendMessage)(
    deps.telegramToken !== undefined ? deps.telegramToken : process.env.LM_TELEGRAM_BOT_TOKEN,
    chatId, message.text, message.extra,
  );
  if (!sent || !sent.ok) return { status: "send_failed", day };
  const messageId = sent.result && sent.result.message_id;
  return { status: "asked", day, telegramMessageId: messageId };
}

// The tap. Guards before writes, in the order that makes a wrong write impossible rather than
// merely unlikely — the same actorId===chatId + row-re-verify pair payout-address-intake uses.
async function handleDietCallback(data, opts = {}) {
  const match = DIET_CALLBACK.exec(String(data || ""));
  if (!match) return { ignored: true };
  const [, answer, askedDay] = match;
  const copy = DIET_STRINGS.ja.lunchQuestion;
  const row = opts.row || null;
  const chatId = String(opts.chatId || "");
  const actorId = String(opts.actorId || "");

  if (!row || !row.uid || !chatId) return { handled: true, ok: false, answer, reason: "unlinked" };
  if (!actorId || actorId !== chatId) return { handled: true, ok: false, answer, reason: "scope_mismatch" };
  // Defence in depth: the row handed to us must itself name this chat. A row-lookup bug upstream
  // must fail here rather than file one person's lunch under another person's uid.
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

  // The row's day comes from the QUESTION, never from the clock at tap time. A tap at 00:20 on the
  // 28th is still an answer about the 27th's lunch, and filing it as the 28th would invent a lunch
  // that was never asked about — in the one ledger whose entire value is that every row is something
  // the user actually said.
  const day = askedDay;

  // Stale taps are refused rather than back-filled: the ask leg spends one of three weekly slots on
  // the question, and an answer arriving days later is not evidence about the day it names any more.
  // The tz chain may end in null here (the webhook has no per-user zone to read); when it does we
  // cannot say what "today" is, so we do NOT guess — we accept the tap under the day it carries,
  // which is safe precisely because the day is carried. A solicited tap is not the 3am-message risk
  // the silence rule exists for.
  const offsetH = resolveDietTzOffsetH(opts, row, nowMs);
  if (offsetH !== null && day !== localDay(nowMs, offsetH)) {
    // CB-1: strip the dead keyboard WITHOUT claiming a choice, then say why the button did nothing.
    await reflectDietTap(opts, "", "");
    await (opts.sendMessage || sendMessage)(token, chatId, copy.expired);
    return { handled: true, ok: false, answer, day, reason: "expired" };
  }

  let claimed;
  try {
    claimed = await claimDietRow({
      uid: row.uid, day, kind: "answer", answer, answered_at: new Date(nowMs).toISOString(),
      ...(opts.messageId ? { telegram_message_id: String(opts.messageId) } : {}),
    }, supa, fetchImpl);
  } catch {
    // Never dress an unwritten answer as a recorded one: no edit, no reassuring reply.
    return { handled: true, ok: false, answer, reason: "persist_failed" };
  }

  if (!claimed) {
    // §10.0-15 ③: a second tap is visible. It reports what is ALREADY on file — telling the user we
    // recorded 麺・丼 when the row says バーガー・ファスト would be a comfortable lie about their own day.
    const existing = await readDietRow(row.uid, day, "answer", supa, fetchImpl);
    const recorded = existing && DIET_ANSWER_LABELS[existing.answer];
    // Function replacer: a label is data, and `$&`/`$'` inside data must never be re-expanded.
    const choice = recorded || DIET_ANSWER_LABELS[answer];
    await (opts.sendMessage || sendMessage)(token, chatId,
      copy.alreadyAnswered.replace("{choice}", () => choice));
    // Strip the stale keyboard without appending a label — the choice on file may not be this tap's.
    await reflectDietTap(opts, "", "");
    return { handled: true, ok: false, answer, reason: "already_answered" };
  }

  // §10.0-15 ①: the recorded choice becomes visible ON the question, and the keyboard goes away.
  // No thank-you follows: the edit is the answer, and the flow does not continue (②).
  await reflectDietTap(opts, DIET_ANSWER_LABELS[answer], opts.messageText);
  return { handled: true, ok: true, answer, day };
}

// Best-effort visibility, exactly like reflectPayoutTap: it never throws and never gates the
// persisted outcome — a Telegram outage here degrades to "toast only", it does not roll anything back.
function reflectDietTap(opts, label, messageText) {
  if (!opts.token || !opts.chatId || !opts.messageId) return Promise.resolve({ ok: false });
  return (opts.reflectAnswer || reflectAnswer)({
    token: opts.token, chatId: opts.chatId, messageId: opts.messageId,
    messageText, label, fetchImpl: opts.fetchImpl,
  });
}

module.exports = {
  DIET_CALLBACK,
  localDay,
  zoneOffsetHours,
  resolveDietTzOffsetH,
  resetDietRuntimeState,
  readDietAskState,
  claimDietRow,
  readDietRow,
  dietUserOnce,
  handleDietCallback,
};
