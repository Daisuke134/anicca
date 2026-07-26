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
//   TIMING    — 11:15-11:45 in the user's own clock, and at most ONCE A WEEK. Before lunch is
//               decided, not after: a message that arrives at 13:00 can only make someone feel bad
//               about a choice already made, which is the definition of moralising. The weekly
//               cadence is the anti-sermon bound — at three questions a week the 14-day evidence
//               barely moves between days, so a daily cap would license six near-identical messages
//               about the same four taps. Both bounds are read from the ledger, not from memory.
//   AN OPTION — one real place near the user, found via the SAME Places transport 11b uses
//               (care-candidate-search's textSearch/geocodeAnchor — no second hand-rolled client).
//               The message says WHICH anchor it searched: 「職場の近く」 is claimed only when a real
//               work anchor existed, and the home fallback says 「近くだと」 instead. When Places
//               finds nothing we SAY so (§9.5: honest failure beats fabricated success) rather than
//               shipping a bare opinion or swallowing the message.
//
// H2 ⑥ binds the copy as much as the code: no calories, no verdict, no 「健康」. The message states a
// count the user can check against their own memory and names one shop. It does not ask a question,
// so there is no reply to owe (§9.11 ④). What we think about their diet never appears, because we
// do not think anything about their diet — we counted taps.
//
// The clock is the user's own, resolved by the same honest chain the question leg uses, and a user
// whose zone we cannot resolve gets NOTHING (see diet-runtime's header).

const { DIET_ANSWERS } = require("./diet-question.js");
const { localDay, claimDietRow, resolveDietTzOffsetH } = require("./diet-runtime.js");
const { deriveAnchors } = require("./care-anchors.js");
const { textSearch, geocodeAnchor } = require("./care-candidate-search.js");
const { DIET_STRINGS } = require("./i18n.js");
const { sendMessage } = require("./telegram.js");

const DIET_NUDGE_MIN_SAMPLES = 4;
const DIET_NUDGE_FAST_SHARE = 0.5;
const DIET_NUDGE_WINDOW_DAYS = 14;
const DIET_NUDGE_COOLDOWN_DAYS = 7;
const NUDGE_WINDOW_START_MIN = 11 * 60 + 15;
const NUDGE_WINDOW_END_MIN = 11 * 60 + 45;
const DEFAULT_RADIUS_M = 1500; // lunch is a walk, not a commute
const DAY_PATTERN = /^\d{4}-\d{2}-\d{2}$/;

// The alternatives we look for. 定食 and サラダ are the spec's own examples; both are categories of
// shop rather than judgements about food, which is the only kind of keyword this organ may use.
const DIET_LUNCH_KEYWORDS = Object.freeze(["定食", "サラダ"]);

const INPUT_KEYS = Object.freeze(["nowMs", "tzOffsetH", "answers", "lastNudgeDay"]);

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
  if (input.lastNudgeDay !== null && !DAY_PATTERN.test(String(input.lastNudgeDay))) {
    throw new Error("lastNudgeDay must be null or a YYYY-MM-DD local day");
  }
  return input;
}

// Whole local days between two YYYY-MM-DD strings. Both are already local days, so plain UTC
// arithmetic on them is exact — no offset enters twice.
function daysBetween(fromDay, toDay) {
  return Math.round((Date.parse(`${toDay}T00:00:00Z`) - Date.parse(`${fromDay}T00:00:00Z`)) / 86400000);
}

// Pure. Cheapest and most binding refusal first, so a spent day reports the day, not the evidence.
function evaluateDietNudge(input) {
  validateInput(input);
  const { nowMs, tzOffsetH } = input;

  if (input.lastNudgeDay !== null) {
    const today = localDay(nowMs, tzOffsetH);
    const sinceDays = daysBetween(input.lastNudgeDay, today);
    if (sinceDays <= 0) return { decision: "suppress", reason: "already-nudged-today" };
    // The cadence bound. The evidence window is 14 days wide and gains at most three taps a week, so
    // two nudges inside one week would be two readings of the same four answers — the definition of
    // nagging with a spreadsheet attached.
    if (sinceDays < DIET_NUDGE_COOLDOWN_DAYS) {
      return { decision: "suppress", reason: "nudge-cooldown", daysSinceLastNudge: sinceDays };
    }
  }

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

// Every substitution goes through a FUNCTION replacer. Venue names are third-party data and `$&`,
// `$'`, `` $` `` and `$1` are all magic to String.replace's string form — a shop actually called
// 「$&キッチン」 would otherwise print the template's own matched text back at the user.
function fill(template, values) {
  let out = template;
  for (const [key, value] of Object.entries(values)) out = out.replace(`{${key}}`, () => String(value));
  return out;
}

// Which sentence we may use is a question of fact, not of tone: 「職場の近く」 requires a WORK anchor.
// findLunchAlternative labels its hit with the anchor it searched, and an unlabelled venue takes the
// weaker claim — never the stronger one.
function buildNudgeMessage({ sampleCount, fastCount, venue }) {
  const copy = DIET_STRINGS.ja.lunchNudge;
  if (!venue) return fill(copy.withoutVenue, { sampleCount, fastCount });
  const template = venue.anchor === "work" ? copy.withVenue : copy.withVenueNearby;
  return fill(template, {
    sampleCount, fastCount, venueName: venue.name, venueAddress: venue.address,
  });
}

// A calendar `location` is free text, and most of what lands there is not a place: a Zoom link, a
// room number, a desk. Geocoding those spends a Places call to be told nothing, and the one thing
// worse than a wasted call is a confident geocode of "3F". This is deliberately a crude filter —
// reject links outright, and require enough characters that a bare room label cannot pass — because
// the honest answer for anything it wrongly drops is the same as for a Places miss: no venue.
function isGeocodableAnchor(value) {
  const address = typeof value === "string" ? value.trim() : "";
  if (!address || /^https?:\/\//i.test(address)) return false;
  return address.length >= 6;
}

// ONE real place near where the user actually is at lunchtime. Work anchor first — lunch happens at
// work — falling back to home rather than searching the country, and SAYING which one it used so the
// copy cannot claim office proximity from a home hit. Returns null for every failure (no usable
// anchor, no key, no result, a transport error): the caller has an honest message for null, and a
// null is never worse than a shop the user cannot walk to.
async function findLunchAlternative({ anchors, apiKey, fetchImpl = fetch, radiusM = DEFAULT_RADIUS_M } = {}) {
  if (!apiKey) return null;
  const candidates = [
    { anchor: "work", address: anchors && anchors.work },
    { anchor: "home", address: anchors && anchors.home },
  ].filter((candidate) => isGeocodableAnchor(candidate.address));
  if (candidates.length === 0) return null;
  const { anchor, address } = candidates[0];
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
          anchor,
        };
      }
    }
    return null;
  } catch {
    return null;
  }
}

// The Places bound. A day whose claim keeps failing used to re-resolve the venue on every one of the
// window's 31 ticks — ~93 Places calls billed to a single user for a single incident. The memo makes
// the resolution once per (uid, local day) per process, whatever happens downstream.
//
// WHY a memo rather than claiming first with a venue-less row: the ledger is append-only, so a row
// claimed before the lookup could never be corrected to name the shop we actually suggested, and an
// unauditable nudge row is exactly the thing the append-only ledger was built to prevent. The memo
// keeps the row honest and still kills the per-tick spend. Its cost is stated rather than hidden: a
// process restart mid-window re-resolves once (bounded by restarts, not by ticks), and a Places
// outage is remembered for the rest of that user's day, which only ever degrades the message to the
// honest no-venue sentence it would already have used.
const VENUE_MEMO = new Map(); // `${uid}|${day}` → venue | null

function resetDietNudgeState() {
  VENUE_MEMO.clear();
}

async function resolveVenueOnce(uid, day, resolve) {
  const key = `${uid}|${day}`;
  if (VENUE_MEMO.has(key)) return VENUE_MEMO.get(key);
  // Promise.resolve().then: an injected resolver that throws SYNCHRONOUSLY never returns a promise,
  // so a trailing .catch() on the call would never run and the throw would escape into the tick.
  const venue = await Promise.resolve().then(resolve).catch(() => null);
  for (const existing of [...VENUE_MEMO.keys()]) {
    if (!existing.endsWith(`|${day}`)) VENUE_MEMO.delete(existing); // yesterday's memo is dead weight
  }
  VENUE_MEMO.set(key, venue);
  return venue;
}

function headers(key) {
  return { apikey: key, Authorization: `Bearer ${key}` };
}

function supaBase(url) {
  return String(url).replace(/\/$/, "");
}

// The trailing-14-day answers. A read we could not perform returns null, and the caller treats null
// as "no basis to nudge" — an unreadable ledger must never become an assumed pattern.
//
// Filtered on `day` (the column the (uid, day DESC) index serves) with a one-day cushion, then cut
// precisely on answered_at in JS: the index picks the candidates, the timestamp decides.
async function readDietAnswers(uid, nowMs, supa, fetchImpl, tzOffsetH = 0) {
  const floorDay = localDay(nowMs - (DIET_NUDGE_WINDOW_DAYS + 1) * 86400000, tzOffsetH);
  const query = `uid=eq.${encodeURIComponent(uid)}&kind=eq.answer`
    + `&day=gte.${encodeURIComponent(floorDay)}&select=answer,answered_at,day&order=day.desc`;
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

// The LAST nudge inside the cooldown horizon, as a local day. Both bounds the pure function needs —
// "did we already speak today" and "has a week passed" — are answered by this one row, so the
// cadence lives in the ledger and survives a restart. Throws on a failed read: assuming we have
// never nudged is how a weekly cadence becomes a daily one during an incident.
async function readLastNudgeDay(uid, nowMs, tzOffsetH, supa, fetchImpl) {
  const floorDay = localDay(nowMs - DIET_NUDGE_COOLDOWN_DAYS * 86400000, tzOffsetH);
  const query = `uid=eq.${encodeURIComponent(uid)}&kind=eq.nudge`
    + `&day=gte.${encodeURIComponent(floorDay)}&select=day&order=day.desc&limit=1`;
  const response = await fetchImpl(`${supaBase(supa.supaUrl)}/rest/v1/lm_diet_log?${query}`, {
    headers: headers(supa.supaKey),
  }).catch(() => null);
  if (!response || !response.ok) throw new Error("diet nudge state lookup failed");
  const rows = await response.json().catch(() => null);
  if (!Array.isArray(rows)) throw new Error("diet nudge state lookup returned no rows array");
  const day = rows[0] && rows[0].day ? String(rows[0].day).slice(0, 10) : null;
  return day && DAY_PATTERN.test(day) ? day : null;
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

  // The same chain the question leg uses, ending in silence rather than in a guessed JST.
  const offsetH = resolveDietTzOffsetH(deps, u, nowMs);
  if (offsetH === null) return { status: "skipped", reason: "no-timezone" };
  const day = localDay(nowMs, offsetH);

  // The window is checked before anything is read: 23 of every 24 hours this costs nothing.
  const minute = localMinuteOfDay(nowMs, offsetH);
  if (minute < NUDGE_WINDOW_START_MIN || minute > NUDGE_WINDOW_END_MIN) {
    return { status: "suppressed", reason: "outside-nudge-window" };
  }

  const lastNudgeDay = await readLastNudgeDay(u.uid, nowMs, offsetH, supa, fetchImpl);
  const answers = await readDietAnswers(u.uid, nowMs, supa, fetchImpl, offsetH);
  if (answers === null) return { status: "suppressed", reason: "ledger-unreadable" };

  const verdict = evaluateDietNudge({ nowMs, tzOffsetH: offsetH, answers, lastNudgeDay });
  if (verdict.decision !== "send") return { status: "suppressed", reason: verdict.reason, ...verdict };

  // The venue is resolved BEFORE the claim, on purpose. The ledger is append-only — there is no
  // second write to fill `venue` in afterwards — so claiming first would mean the row could never
  // say which shop we actually named, and the nudge would be unauditable. What used to make that
  // ordering expensive was the failure case: a day whose claim keeps erroring re-resolved on every
  // tick. resolveVenueOnce is the bound (see its comment) — one resolution per user per day per
  // process, no matter how the rest of the tick goes.
  const venue = await resolveVenueOnce(u.uid, day, () => (deps.findLunchAlternative || findLunchAlternative)({
    anchors: deriveAnchors({
      homeAddress: u.home_address || null,
      calendarEvents: Array.isArray(deps.calendarEvents) ? deps.calendarEvents : [],
      careHistory: [],
    }),
    apiKey: deps.mapsKey || process.env.LIFE_MAPS_KEY,
    fetchImpl: deps.searchFetch || globalThis.fetch,
  })); // a Places failure must cost the venue, never the message

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
  DIET_NUDGE_COOLDOWN_DAYS,
  NUDGE_WINDOW_START_MIN,
  NUDGE_WINDOW_END_MIN,
  DIET_LUNCH_KEYWORDS,
  evaluateDietNudge,
  buildNudgeMessage,
  findLunchAlternative,
  isGeocodableAnchor,
  readDietAnswers,
  readLastNudgeDay,
  resetDietNudgeState,
  dietNudgeOnce,
};
