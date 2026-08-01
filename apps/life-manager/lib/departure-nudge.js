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
  if (patched.length > 0) return { ok: true, claimed: true };

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
  if (inserted && inserted.status === 201) return { ok: true, claimed: true };
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

module.exports = { NUDGE_LEVELS, NUDGE_ACK_REASONS, claimNudgeLevel, ackNudge };
