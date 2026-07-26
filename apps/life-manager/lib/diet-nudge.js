"use strict";
// H2 ORG-diet — the intervention (spec §10 NEXT HORIZON row H2 ③).
//
// This is the leg that can do real harm. An unsolicited message about what someone eats is a sermon
// unless three things are true at once, and every one of them is a hard gate here:
//
//   EVIDENCE  — at least 4 real answers in the trailing 14 days, and fast food at 50% or more of
//               them. Three samples is an anecdote; nudging on an anecdote is nagging with a
//               spreadsheet attached. 「食べてない」 counts in the DENOMINATOR: a day with no lunch
//               is an observation we made and it is honestly not fast food, which makes the nudge
//               harder to fire — the safe direction for a message nobody asked for.
//   TIMING    — 11:15-11:45 in the user's own clock. Before lunch is decided, not after: a message
//               that arrives at 13:00 can only make someone feel bad about a choice already made,
//               which is the definition of moralising. One per day, maximum, claimed durably.
//   AN OPTION — one real place near the work anchor, found via the SAME Places transport 11b uses
//               (care-candidate-search's textSearch/geocodeAnchor — no second hand-rolled client).
//               When Places finds nothing we SAY so (§9.5: honest failure beats fabricated success)
//               rather than shipping a bare opinion or swallowing the message.
//
// H2 ⑥ binds the copy as much as the code: no calories, no verdict, no 「健康」. The message states a
// count the user can check against their own memory and names one shop. It does not ask a question,
// so there is no reply to owe (§9.11 ④). What we think about their diet never appears, because we
// do not think anything about their diet — we counted taps.

const { DIET_ANSWERS } = require("./diet-question.js");
const { localDay, claimDietRow } = require("./diet-runtime.js");
const { deriveAnchors } = require("./care-anchors.js");
const { textSearch, geocodeAnchor } = require("./care-candidate-search.js");
const { DIET_STRINGS } = require("./i18n.js");
const { sendMessage } = require("./telegram.js");

const DIET_NUDGE_MIN_SAMPLES = 4;
const DIET_NUDGE_FAST_SHARE = 0.5;
const DIET_NUDGE_WINDOW_DAYS = 14;
const NUDGE_WINDOW_START_MIN = 11 * 60 + 15;
const NUDGE_WINDOW_END_MIN = 11 * 60 + 45;
const DEFAULT_TZ_OFFSET_H = 9;
const DEFAULT_RADIUS_M = 1500; // lunch is a walk, not a commute

// The alternatives we look for. 定食 and サラダ are the spec's own examples; both are categories of
// shop rather than judgements about food, which is the only kind of keyword this organ may use.
const DIET_LUNCH_KEYWORDS = Object.freeze(["定食", "サラダ"]);

const INPUT_KEYS = Object.freeze(["nowMs", "tzOffsetH", "answers", "nudgedToday"]);

function localMinuteOfDay(nowMs, tzOffsetH) {
  const localMs = nowMs + tzOffsetH * 3600000;
  return Math.floor((((localMs % 86400000) + 86400000) % 86400000) / 60000);
}

function validateInput(input) {
  if (!input || typeof input !== "object" || Array.isArray(input)) throw new Error("input must be an object");
  for (const key of Object.keys(input)) {
    if (!INPUT_KEYS.includes(key)) throw new Error(`unknown key: ${key}`);
  }
  if (!Number.isFinite(input.nowMs)) throw new Error("nowMs must be a finite number");
  if (!Number.isFinite(input.tzOffsetH)) throw new Error("tzOffsetH must be a finite number");
  if (!Array.isArray(input.answers)) throw new Error("answers must be an array");
  for (const sample of input.answers) {
    if (!sample || typeof sample !== "object") throw new Error("answer sample must be an object");
    if (!DIET_ANSWERS.includes(sample.answer)) {
      throw new Error(`unknown diet answer: ${String(sample && sample.answer).slice(0, 20)}`);
    }
    if (!Number.isFinite(sample.atMs)) throw new Error("answer sample must have a finite atMs");
  }
  if (typeof input.nudgedToday !== "boolean") throw new Error("nudgedToday must be a boolean");
  return input;
}

// Pure. Cheapest and most binding refusal first, so a spent day reports the day, not the evidence.
function evaluateDietNudge(input) {
  validateInput(input);
  const { nowMs, tzOffsetH } = input;

  if (input.nudgedToday) return { decision: "suppress", reason: "already-nudged-today" };

  const minute = localMinuteOfDay(nowMs, tzOffsetH);
  if (minute < NUDGE_WINDOW_START_MIN || minute > NUDGE_WINDOW_END_MIN) {
    return { decision: "suppress", reason: "outside-nudge-window" };
  }

  const cutoff = nowMs - DIET_NUDGE_WINDOW_DAYS * 86400000;
  const recent = input.answers.filter((sample) => sample.atMs >= cutoff && sample.atMs <= nowMs);
  const sampleCount = recent.length;
  const fastCount = recent.filter((sample) => sample.answer === "fast").length;
  const fastShare = sampleCount ? fastCount / sampleCount : 0;

  if (sampleCount < DIET_NUDGE_MIN_SAMPLES) {
    return { decision: "suppress", reason: "not-enough-samples", sampleCount, fastCount, fastShare };
  }
  if (fastShare < DIET_NUDGE_FAST_SHARE) {
    return { decision: "suppress", reason: "fast-share-below-threshold", sampleCount, fastCount, fastShare };
  }
  return { decision: "send", reason: "fast-share-at-threshold", sampleCount, fastCount, fastShare };
}

function buildNudgeMessage({ sampleCount, fastCount, venue }) {
  const copy = DIET_STRINGS.ja.lunchNudge;
  if (!venue) {
    return copy.withoutVenue
      .replace("{sampleCount}", String(sampleCount))
      .replace("{fastCount}", String(fastCount));
  }
  return copy.withVenue
    .replace("{sampleCount}", String(sampleCount))
    .replace("{fastCount}", String(fastCount))
    .replace("{venueName}", venue.name)
    .replace("{venueAddress}", venue.address);
}

// ONE real place near where the user actually is at lunchtime. Work anchor first — lunch happens at
// work — falling back to home rather than searching the country. Returns null for every failure
// (no anchor, no key, no result, a transport error): the caller has an honest message for null, and
// a null is never worse than a shop the user cannot walk to.
async function findLunchAlternative({ anchors, apiKey, fetchImpl = fetch, radiusM = DEFAULT_RADIUS_M } = {}) {
  if (!apiKey) return null;
  const address = (anchors && (anchors.work || anchors.home)) || null;
  if (!address) return null;
  try {
    const point = await geocodeAnchor(fetchImpl, apiKey, address);
    if (!point) return null;
    for (const keyword of DIET_LUNCH_KEYWORDS) {
      const results = await textSearch(fetchImpl, apiKey, keyword, { ...point, radiusM });
      const hit = results.find((result) => result && result.name);
      if (hit) {
        return {
          name: String(hit.name),
          // vicinity is what Text Search returns for a nearby-biased query; formatted_address is
          // the fuller form. Either is public venue data — nothing here is about the user.
          address: String(hit.formatted_address || hit.vicinity || ""),
        };
      }
    }
    return null;
  } catch {
    return null;
  }
}

function headers(key) {
  return { apikey: key, Authorization: `Bearer ${key}` };
}

function supaBase(url) {
  return String(url).replace(/\/$/, "");
}

// The trailing-14-day answers. A read we could not perform returns null, and the caller treats null
// as "no basis to nudge" — an unreadable ledger must never become an assumed pattern.
async function readDietAnswers(uid, nowMs, supa, fetchImpl) {
  const since = new Date(nowMs - DIET_NUDGE_WINDOW_DAYS * 86400000).toISOString();
  const query = `uid=eq.${encodeURIComponent(uid)}&kind=eq.answer`
    + `&answered_at=gte.${encodeURIComponent(since)}&select=answer,answered_at&order=answered_at.desc`;
  const response = await fetchImpl(`${supaBase(supa.supaUrl)}/rest/v1/lm_diet_log?${query}`, {
    headers: headers(supa.supaKey),
  }).catch(() => null);
  if (!response || !response.ok) return null;
  const rows = await response.json().catch(() => null);
  if (!Array.isArray(rows)) return null;
  return rows
    .map((row) => ({ answer: row.answer, atMs: Date.parse(row.answered_at) }))
    .filter((sample) => DIET_ANSWERS.includes(sample.answer) && Number.isFinite(sample.atMs));
}

async function nudgedToday(uid, day, supa, fetchImpl) {
  const query = `uid=eq.${encodeURIComponent(uid)}&day=eq.${encodeURIComponent(day)}`
    + "&kind=eq.nudge&select=id&limit=1";
  const response = await fetchImpl(`${supaBase(supa.supaUrl)}/rest/v1/lm_diet_log?${query}`, {
    headers: headers(supa.supaKey),
  }).catch(() => null);
  if (!response || !response.ok) throw new Error("diet nudge state lookup failed");
  const rows = await response.json().catch(() => null);
  return Array.isArray(rows) && rows.length > 0;
}

async function dietNudgeOnce(u, nowMs, deps = {}) {
  const supa = {
    supaUrl: deps.supaUrl || process.env.SUPABASE_URL,
    supaKey: deps.supaKey || process.env.SUPABASE_SERVICE_ROLE_KEY,
  };
  const chatId = String((u && u.telegram_chat_id) || "");
  if (!u || !u.uid || !chatId || u.notifications_enabled === false || !supa.supaUrl || !supa.supaKey) {
    return { status: "skipped" };
  }
  const fetchImpl = deps.fetchImpl || globalThis.fetch;
  const offsetH = Number.isFinite(deps.tzOffsetH)
    ? deps.tzOffsetH
    : (Number.isFinite(Number(process.env.LM_DIET_UTC_OFFSET_HOURS))
      ? Number(process.env.LM_DIET_UTC_OFFSET_HOURS) : DEFAULT_TZ_OFFSET_H);
  const day = localDay(nowMs, offsetH);

  // The window is checked before anything is read: 23 of every 24 hours this costs nothing.
  const minute = localMinuteOfDay(nowMs, offsetH);
  if (minute < NUDGE_WINDOW_START_MIN || minute > NUDGE_WINDOW_END_MIN) {
    return { status: "suppressed", reason: "outside-nudge-window" };
  }

  const already = await nudgedToday(u.uid, day, supa, fetchImpl);
  const answers = await readDietAnswers(u.uid, nowMs, supa, fetchImpl);
  if (answers === null) return { status: "suppressed", reason: "ledger-unreadable" };

  const verdict = evaluateDietNudge({ nowMs, tzOffsetH: offsetH, answers, nudgedToday: already });
  if (verdict.decision !== "send") return { status: "suppressed", reason: verdict.reason, ...verdict };

  // The venue is resolved BEFORE the claim, on purpose. The ledger is append-only — there is no
  // second write to fill `venue` in afterwards — so claiming first would mean the row could never
  // say which shop we actually named, and the nudge would be unauditable. The cost of this ordering
  // is bounded and known: a rare two-tick race buys one extra Places call. It does NOT buy a second
  // message, because the claim below is still ahead of the send, and it does not buy 30 calls,
  // because the already-nudged read above stops every tick after the first one lands.
  const venue = await (deps.findLunchAlternative || findLunchAlternative)({
    anchors: deriveAnchors({
      homeAddress: u.home_address || null,
      calendarEvents: Array.isArray(deps.calendarEvents) ? deps.calendarEvents : [],
      careHistory: [],
    }),
    apiKey: deps.mapsKey || process.env.LIFE_MAPS_KEY,
    fetchImpl: deps.searchFetch || globalThis.fetch,
  }).catch(() => null); // a Places failure must cost the venue, never the message

  const claimed = await claimDietRow({
    uid: u.uid, day, kind: "nudge", asked_at: new Date(nowMs).toISOString(),
    venue: venue || null,
  }, supa, fetchImpl);
  if (!claimed) return { status: "suppressed", reason: "already-nudged-today" };

  const text = buildNudgeMessage({
    sampleCount: verdict.sampleCount, fastCount: verdict.fastCount, venue,
  });
  const sent = await (deps.sendMessage || sendMessage)(
    deps.telegramToken !== undefined ? deps.telegramToken : process.env.LM_TELEGRAM_BOT_TOKEN,
    chatId, text,
  );
  if (!sent || !sent.ok) return { status: "send_failed", day, ...verdict };
  return {
    status: "nudged",
    day,
    venue: venue ? venue.name : null,
    telegramMessageId: sent.result && sent.result.message_id,
    ...verdict,
  };
}

module.exports = {
  DIET_NUDGE_MIN_SAMPLES,
  DIET_NUDGE_FAST_SHARE,
  DIET_NUDGE_WINDOW_DAYS,
  NUDGE_WINDOW_START_MIN,
  NUDGE_WINDOW_END_MIN,
  DIET_LUNCH_KEYWORDS,
  evaluateDietNudge,
  buildNudgeMessage,
  findLunchAlternative,
  readDietAnswers,
  dietNudgeOnce,
};
