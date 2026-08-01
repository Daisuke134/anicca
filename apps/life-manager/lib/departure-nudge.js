"use strict";
// lib/departure-nudge.js — spec 2026-08-01-lm-daily-organ-design.md §5.2.1 + §5.2.2 (#2c).
//
// WHY THIS EXISTS: measured over four days, every wake call reached voicemail (§1.3 — human 3,
// machine 17). A phone call demands one action, 出る, and nobody performed it. Telegram stays on the
// screen, so §5.2.1 replaced the push with a ladder of messages: T-25 / T-10 / T-5 / T-0 / T+3 / T+7.
//
// The ladder is only a product because it STOPS — 停止条件の無い連投は嫌がらせであって製品ではない.
// So the design (D4) refuses to separate "may I send this rung" from "has this been stopped": both
// are one PATCH, filtered on acked_at IS NULL AND last_level_min > <level>, and the number of rows
// it returns is the permission. A read followed by a decision is a race that two overlapping 60s
// ticks lose, and losing it means the user gets the same rung twice. This is claimWake's bet on a
// unique constraint, restated for a value that only ever decreases.

const { clockLabel, escapeHtml } = require("./i18n.js");
const { reflectAnswer } = require("./telegram-callback-visibility.js");

// The rungs, in minutes from DEPARTURE (positive = before, negative = after) — §5.2.1's ladder
// verbatim. Separate from scheduler.js' WAKE_LEVELS on purpose (D2): the phone is opt-in extra now,
// so sharing one array would make a user's ladder depend on whether they enabled calls.
const NUDGE_LEVELS = [25, 10, 5, 0, -3, -7];

// Why a stop happened. 'left_home' is declared but NOT yet produced by anything — #3 (location) is
// unimplemented, and §5.2.2 D5 is explicit that writing an unbuilt stop condition into the design
// and calling it done is the most dangerous move available here. See ackNudge's note.
const NUDGE_ACK_REASONS = {
  TAP: "tap",
  CALL_ANSWERED: "call_answered",
  LEFT_HOME: "left_home",
};

// §5.2.1 / §5.2.2「送る文」, verbatim. Held here rather than in lib/i18n.js for the same reason
// wake-miss.js holds its own notice copy: this text only means anything alongside the rung logic it
// belongs to. {placeholder} substitution matches i18n.js' formatter idiom.
//
// The shape is deliberate. The opening rung carries the whole context — time, title, place — because
// it is the one that arrives while the user can still change plans. The middle rungs are one line:
// by then the user knows what this is about and a paragraph is just something to scroll past. The
// overtime rungs switch ⏰ for 🚨 and name the arrival being bought, which is the only new fact left.
//
// T+7 is the terminal rung and says almost nothing on purpose (D6). Contacting the other party is
// the late organ's job — lm_late_notice_log already guarantees one notice per event — and a second
// organ offering the same thing is the duplicated-owner failure §0.17 exists to prevent.
const NUDGE_COPY = Object.freeze({
  ja: Object.freeze({
    ack: "了解",
    "25": "⏰ {start} {header}\n{departure} に出て。あと{over}分",
    "10": "⏰ あと{over}分で出る時間。{departure} 出発",
    "5": "⏰ あと{over}分。そろそろ支度を終えて",
    "0": "🚨 いま出る時間。{departure}",
    "-3": "🚨 {over}分オーバー。今出れば {arrival} 着（{over}分遅れ）",
    "-7": "🚨 {over}分オーバー。",
  }),
  en: Object.freeze({
    ack: "OK",
    "25": "⏰ {start} {header}\nLeave at {departure} — {over} min to go",
    "10": "⏰ {over} min until you leave. Departure {departure}",
    "5": "⏰ {over} min left. Start wrapping up",
    "0": "🚨 Time to leave. {departure}",
    "-3": "🚨 {over} min over. Leave now and you arrive {arrival} ({over} min late)",
    "-7": "🚨 {over} min over.",
  }),
});

// Telegram rejects callback_data over 64 bytes, so D7 keeps uid out of it (the webhook already knows
// which chat tapped) and carries only the event's start.
const NUDGE_CALLBACK_LIMIT = 64;
const departureCallbackData = (startIso) => `depart:ack:${startIso}`;

// A calendar title is written by whoever created the event, and sendMessage posts with parse_mode
// HTML — so it is untrusted input on a markup channel. Bounded first, THEN escaped: a 300-character
// title in a header is not a message, it is a wall.
//
// ★ The order is load-bearing ★. Escaping first and slicing after cuts "&amp;" into "&am", and
// Telegram rejects the malformed entity — the send fails, the rung is released, and the next tick
// renders the identical text and fails identically, so one "R&D" in a title the user did not write
// silences that event's entire ladder. Truncating first can only ever drop whole characters.
const headline = (value, limit) => escapeHtml(String(value || "").replace(/\s+/g, " ").trim().slice(0, limit));

// One rung, rendered. Pure — the tick decides WHETHER to send (claimNudgeLevel), this decides WHAT.
// Returns { text, extra } in the shape sendMessage's trailing argument expects; `extra` is absent on
// the terminal rung, because a button on the last message would promise a ladder that has ended.
function buildNudgeMessage({ level, ev, departureIso, lang } = {}) {
  const copy = NUDGE_COPY[lang === "en" ? "en" : "ja"];
  const template = copy[String(level)];
  if (!template || !ev) return null;

  // Every clock reading is rendered against the EVENT's own UTC offset, so a user travelling (or a
  // server in another zone) still reads the times their calendar shows them.
  const referenceIso = ev.startIso;
  const startMs = Date.parse(ev.startIso);
  const departureMs = Date.parse(departureIso);
  const over = Math.abs(Number(level));
  const summary = headline(ev.summary, 80);
  const location = headline(ev.location, 80);
  const values = {
    start: clockLabel(startMs, referenceIso),
    header: location ? `${summary} / ${location}` : summary,
    departure: Number.isFinite(departureMs) ? clockLabel(departureMs, referenceIso) : "",
    over,
    // Past departure, every minute of delay is a minute of lateness: this is the arrival the user is
    // buying by still being at home, not a fresh routing estimate.
    arrival: clockLabel(startMs + over * 60_000, referenceIso),
  };
  const text = template.replace(/\{(\w+)\}/g, (_match, key) => String(values[key]));

  if (Number(level) === NUDGE_LEVELS[NUDGE_LEVELS.length - 1]) return { text };
  const callbackData = departureCallbackData(ev.startIso);
  // Refuse to attach a button Telegram would reject outright — an inline keyboard that fails to
  // render takes the whole message down with it, and the message matters more than the button.
  if (Buffer.byteLength(callbackData, "utf8") > NUDGE_CALLBACK_LIMIT) return { text };
  return {
    text,
    extra: { reply_markup: { inline_keyboard: [[{ text: copy.ack, callback_data: callbackData }]] } },
  };
}

function supaHeaders(key, prefer) {
  const headers = {
    apikey: key,
    Authorization: `Bearer ${key}`,
    "Content-Type": "application/json",
  };
  if (prefer) headers.Prefer = prefer;
  return headers;
}

const rowFilter = (uid, eventKey) =>
  `uid=eq.${encodeURIComponent(uid)}&event_key=eq.${encodeURIComponent(eventKey)}`;

// Ask permission and take it in the same write. Returns:
//   { ok: true,  claimed: true  }  this tick owns this rung and nobody else can send it
//   { ok: true,  claimed: false }  the ladder is stopped, or this rung is already spent — stay quiet
//   { ok: false, claimed: false, error }  we never confirmed a write — stay quiet, and say why
//
// PATCH first, INSERT second: five of the six rungs already have a row, so this is one round trip in
// the common case. A PATCH that matches nothing is ambiguous — no row yet, or a row that refuses —
// and the INSERT resolves it without a read: 201 means there genuinely was no ladder, 409 means the
// primary key says there is one and it declined us.
async function claimNudgeLevel(uid, eventKey, levelMin, opts = {}) {
  const f = opts.fetchImpl || fetch;
  if (!uid || !eventKey || !Number.isFinite(Number(levelMin))) {
    return { ok: false, claimed: false, error: "missing_args" };
  }
  if (!opts.supaUrl || !opts.supaKey) return { ok: false, claimed: false, error: "no_credentials" };
  const level = Number(levelMin);
  const nowIso = new Date(opts.nowMs == null ? Date.now() : opts.nowMs).toISOString();

  // BOTH conditions belong to this one URL. Drop `last_level_min=gt.` and the same rung repeats every
  // tick; drop `acked_at=is.null` and [了解] stops nothing.
  const url = `${opts.supaUrl}/rest/v1/lm_departure_nudge?${rowFilter(uid, eventKey)}`
    + "&acked_at=is.null"
    + `&last_level_min=gt.${encodeURIComponent(String(level))}`
    + "&select=uid,event_key,last_level_min";
  const patchBody = { last_level_min: level, updated_at: nowIso };
  if (opts.messageId != null) patchBody.last_message_id = Number(opts.messageId);

  let response;
  try {
    response = await f(url, {
      method: "PATCH",
      headers: supaHeaders(opts.supaKey, "return=representation"),
      body: JSON.stringify(patchBody),
    });
  } catch (e) {
    return { ok: false, claimed: false, error: String((e && e.message) || e) };
  }
  if (!response || !response.ok) {
    return { ok: false, claimed: false, error: `http_${(response && response.status) || "unknown"}` };
  }
  const patched = await response.json().catch(() => null);
  // An unreadable body is NOT zero rows: the write may well have landed and taken the rung. Treating
  // it as "no match" would fall through to the INSERT and, on a 409, silently report a clean refusal
  // for a claim we might already own.
  if (!Array.isArray(patched)) return { ok: false, claimed: false, error: "unreadable_response" };
  // `opened` tells the caller which undo applies. An advance can only be rewound; an INSERT has to be
  // removed, because before it there was no ladder at all.
  if (patched.length > 0) return { ok: true, claimed: true, opened: false };

  // No row to advance. Either the ladder has not started, or it has stopped/passed this rung.
  const insertBody = {
    uid: String(uid), event_key: String(eventKey), last_level_min: level,
    created_at: nowIso, updated_at: nowIso,
  };
  if (opts.messageId != null) insertBody.last_message_id = Number(opts.messageId);
  let inserted;
  try {
    inserted = await f(`${opts.supaUrl}/rest/v1/lm_departure_nudge`, {
      method: "POST",
      // return=minimal WITHOUT merge-duplicates: the 409 is load-bearing. Resolving the conflict
      // would overwrite a rung another tick is already sending, which is exactly the double message
      // this module exists to prevent.
      headers: supaHeaders(opts.supaKey, "return=minimal"),
      body: JSON.stringify(insertBody),
    });
  } catch (e) {
    return { ok: false, claimed: false, error: String((e && e.message) || e) };
  }
  if (inserted && inserted.status === 201) return { ok: true, claimed: true, opened: true };
  // 409 = another tick opened this ladder first, or the row is stopped/ahead of us. Nothing is
  // broken; there is simply nothing for us to send.
  if (inserted && inserted.status === 409) return { ok: true, claimed: false };
  return { ok: false, claimed: false, error: `http_${(inserted && inserted.status) || "unknown"}` };
}

// End the ladder, recording WHY. Returns {ok, matched, error} — the vocabulary lib/late-notice.js
// established, where "the write landed and matched nothing" (a second tap) is a different outcome
// from "we never got a write" (an outage), and call sites log the two apart.
//
// acked_at=is.null makes this a latch, exactly like markAnswered: the FIRST stop wins. A user who
// taps [了解] and then answers the phone should keep 'tap' as the reason — the ladder ended when
// they acknowledged it, and overwriting that would make the ledger describe the later event as the
// cause of the earlier stop.
//
// NOTE: reason 'left_home' has NO caller yet. #3 (detecting departure from live location) is not
// built, and §5.2.2 D5 keeps it that way on purpose — a stop condition that exists in the design and
// not in the code is worse than an absent one. When #3 lands, it calls this; nothing else changes.
async function ackNudge(uid, eventKey, reason, opts = {}) {
  const f = opts.fetchImpl || fetch;
  if (!uid || !eventKey || !reason) return { ok: false, matched: 0, error: "missing_args" };
  if (!opts.supaUrl || !opts.supaKey) return { ok: false, matched: 0, error: "no_credentials" };

  const url = `${opts.supaUrl}/rest/v1/lm_departure_nudge?${rowFilter(uid, eventKey)}`
    + "&acked_at=is.null&select=uid,event_key,ack_reason";
  const nowIso = new Date(opts.nowMs == null ? Date.now() : opts.nowMs).toISOString();
  let response;
  try {
    response = await f(url, {
      method: "PATCH",
      headers: supaHeaders(opts.supaKey, "return=representation"),
      body: JSON.stringify({ acked_at: nowIso, ack_reason: String(reason), updated_at: nowIso }),
    });
  } catch (e) {
    return { ok: false, matched: 0, error: String((e && e.message) || e) };
  }
  if (!response || !response.ok) {
    return { ok: false, matched: 0, error: `http_${(response && response.status) || "unknown"}` };
  }
  const patched = await response.json().catch(() => null);
  if (!Array.isArray(patched)) return { ok: false, matched: 0, error: "unreadable_response" };
  return { ok: true, matched: patched.length };
}

// Give a rung back when the message it was claimed for was never delivered — the counterpart of
// releaseWake after a failed dial. The claim exists to prevent a SECOND send; when there was no
// first send, letting it stand costs the user that rung for nothing.
//
// `last_level_min=eq.<level>` is the ownership guard, and it does the job releaseWake needed a
// claim_token for: if a later tick has already moved the ladder on, this stale release matches
// nothing instead of dragging the ladder backwards. acked_at=is.null is the second guard — a user
// who tapped [了解] in the meantime must not have the ladder reopened by a failed send.
//
// Which undo applies comes from the claim's own `opened` flag, NOT from guessing. A ladder that
// opens at a middle rung — an event first seen inside T-25, i.e. an ordinary same-morning entry — is
// DELETEd like any other opening rung. Inferring it from `coarser === undefined` would be right only
// for level 25 and would leave a phantom row for every other opening rung.
//
// ★ The one imprecision in this module, named rather than hidden ★: when the rung was an advance
// (not the opening one) we cannot know the exact value it replaced — PostgREST returns the row AFTER
// the update, not before — so the row is restored to the NEXT COARSER rung. As a gate that is exact:
// `level` becomes claimable again and everything coarser stays blocked, which is the entire job.
// As history it reads "the ladder got at least this far", which is true but rounded, and only ever
// on the failure path. Fixing it properly means a prev_level_min column written by a BEFORE UPDATE
// trigger; that is more schema than one retry is worth.
async function releaseNudgeLevel(uid, eventKey, levelMin, opts = {}) {
  const f = opts.fetchImpl || fetch;
  if (!uid || !eventKey || !Number.isFinite(Number(levelMin))) {
    return { ok: false, matched: 0, error: "missing_args" };
  }
  if (!opts.supaUrl || !opts.supaKey) return { ok: false, matched: 0, error: "no_credentials" };
  const level = Number(levelMin);
  const url = `${opts.supaUrl}/rest/v1/lm_departure_nudge?${rowFilter(uid, eventKey)}`
    + `&last_level_min=eq.${encodeURIComponent(String(level))}`
    + "&acked_at=is.null&select=uid,event_key";

  // The opening rung had no row before it, so the faithful undo is to remove the one it created.
  const coarser = NUDGE_LEVELS[NUDGE_LEVELS.indexOf(level) - 1];
  const request = opts.opened || coarser === undefined
    ? { method: "DELETE", body: undefined }
    : {
      method: "PATCH",
      body: JSON.stringify({
        last_level_min: coarser,
        updated_at: new Date(opts.nowMs == null ? Date.now() : opts.nowMs).toISOString(),
      }),
    };

  let response;
  try {
    response = await f(url, {
      method: request.method,
      headers: supaHeaders(opts.supaKey, "return=representation"),
      ...(request.body === undefined ? {} : { body: request.body }),
    });
  } catch (e) {
    return { ok: false, matched: 0, error: String((e && e.message) || e) };
  }
  if (!response || !response.ok) {
    return { ok: false, matched: 0, error: `http_${(response && response.status) || "unknown"}` };
  }
  const rows = await response.json().catch(() => null);
  if (!Array.isArray(rows)) return { ok: false, matched: 0, error: "unreadable_response" };
  return { ok: true, matched: rows.length };
}

// The [了解] tap — §5.2.1's primary stop condition, and therefore the one path here whose failure
// turns the product into harassment. Shaped like handleAskCallback (lib/ask.js:544): verify the
// scope, write, then reflect the tap onto the message so the button cannot be pressed into silence.
//
// ★ The uid comes from OPTS — the chat that tapped — and never from the callback data ★. D7 keeps
// uid out of the payload for the 64-byte limit, and that constraint turns out to be the security
// property too: the event key is assembled from a uid this process looked up, so two users with a
// 09:00 meeting tap two different rows and neither can address the other's.
async function handleDepartureCallback(data, opts = {}) {
  const match = String(data || "").match(/^depart:ack:(.+)$/);
  if (!match) return { ok: false, ignored: true };
  const startIso = match[1];
  const chatId = String(opts.chatId || "");
  const actorId = String(opts.actorId || "");
  // Same scope check the ask callback uses: in a private chat the tapper's user id IS the chat id,
  // so a mismatch means the tap did not come from the person this ladder belongs to.
  if (!opts.uid || !chatId || !actorId || actorId !== chatId || !opts.supaUrl || !opts.supaKey) {
    return { ok: false, reason: "callback scope mismatch" };
  }

  const eventKey = `${opts.uid}|${startIso}`;
  const result = await ackNudge(opts.uid, eventKey, NUDGE_ACK_REASONS.TAP, opts);
  // Best-effort, and deliberately AFTER the write: the stop is already persisted, so a Telegram
  // outage here costs the visual confirmation, never the stop itself.
  if (opts.token && chatId && opts.messageId) {
    await (opts.reflectAnswer || reflectAnswer)({
      token: opts.token, chatId, messageId: opts.messageId, messageText: opts.messageText,
      label: (opts.lang === "en" ? NUDGE_COPY.en : NUDGE_COPY.ja).ack,
      fetchImpl: opts.fetchImpl,
    });
  }
  // matched === 0 is not a failure: it is a second tap on a ladder that already stopped, which is
  // exactly what the latch is for. The caller logs ok and matched separately.
  return { ok: result.ok, handled: true, matched: result.matched, eventKey, error: result.error };
}

module.exports = {
  NUDGE_LEVELS, NUDGE_ACK_REASONS, claimNudgeLevel, ackNudge, releaseNudgeLevel,
  buildNudgeMessage, departureCallbackData, handleDepartureCallback,
};
