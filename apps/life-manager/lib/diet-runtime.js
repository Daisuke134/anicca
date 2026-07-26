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
// Reading the ledger is STRICT: a lookup we could not perform THROWS rather than returning "never
// asked". Treating an outage as an empty history is precisely how a weekly cap turns into a daily
// one during an incident.
//
// The tap writes nothing but the choice. §10.0-15 ① is honoured by EDITING the question message —
// that edit IS the visible response, so no thank-you is sent. A follow-up message on every tap
// would make a once-every-48-hours question feel like a conversation the user has to close.

const { evaluateDietQuestion, dietQuestionMessage, DIET_ANSWER_LABELS } = require("./diet-question.js");
const { DIET_STRINGS } = require("./i18n.js");
const { sendMessage } = require("./telegram.js");
const { reflectAnswer } = require("./telegram-callback-visibility.js");

const DIET_CALLBACK = /^diet:answer:(teishoku|men|fast|skip)$/;
const WEEK_MS = 7 * 86400000;
const DEFAULT_TZ_OFFSET_H = 9;

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

function tzOffset(deps) {
  if (Number.isFinite(deps.tzOffsetH)) return deps.tzOffsetH;
  const fromEnv = Number(process.env.LM_DIET_UTC_OFFSET_HOURS);
  return Number.isFinite(fromEnv) ? fromEnv : DEFAULT_TZ_OFFSET_H;
}

// The weekly cap is a TRAILING 7 days, not a calendar week: a Sunday/Monday boundary would let three
// asks on Saturday be followed by three more on Sunday. Throws on any failure — see the header.
async function readDietAskState(uid, nowMs, supa, fetchImpl) {
  const since = new Date(nowMs - WEEK_MS).toISOString();
  const query = `uid=eq.${encodeURIComponent(uid)}&kind=eq.ask`
    + `&asked_at=gte.${encodeURIComponent(since)}&select=asked_at&order=asked_at.desc`;
  const response = await fetchImpl(`${supaBase(supa.supaUrl)}/rest/v1/lm_diet_log?${query}`, {
    headers: headers(supa.supaKey),
  }).catch(() => null);
  if (!response || !response.ok) {
    throw new Error(`diet ask state lookup failed (${response ? response.status : "no response"})`);
  }
  const rows = await response.json().catch(() => null);
  if (!Array.isArray(rows)) throw new Error("diet ask state lookup returned no rows array");
  const times = rows.map((row) => Date.parse(row.asked_at)).filter(Number.isFinite);
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
  const offsetH = tzOffset(deps);

  const state = await readDietAskState(u.uid, nowMs, supa, fetchImpl);
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

  const day = localDay(nowMs, offsetH);
  const claimed = await claimDietRow({
    uid: u.uid, day, kind: "ask", asked_at: new Date(nowMs).toISOString(),
  }, supa, fetchImpl);
  if (!claimed) return { status: "already_asked" };

  const message = dietQuestionMessage();
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
  const [, answer] = match;
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
  const day = localDay(nowMs, tzOffset(opts));
  const token = opts.token !== undefined ? opts.token : process.env.LM_TELEGRAM_BOT_TOKEN;

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
    await (opts.sendMessage || sendMessage)(token, chatId,
      copy.alreadyAnswered.replace("{choice}", recorded || DIET_ANSWER_LABELS[answer]));
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
  readDietAskState,
  claimDietRow,
  readDietRow,
  dietUserOnce,
  handleDietCallback,
};
