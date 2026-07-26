"use strict";
// H4 ORG-precepts — the intervention (spec §10 NEXT HORIZON row H4 ③).
//
// One message, Sunday night, and it is a MIRROR: it says what happened and — only when the calendar
// actually says so — where it happened around. 「『きつく当たった』が2回。2回とも予定が3件以上あった
// 木曜の後でした」. Nothing else. The spec's own words for what this may never be: 説教・評価・スコア化
// 禁止.
//
// THE COPY SAYS WHAT THE RULE CHECKED, NOT WHAT THE ROW SKETCHED. H4 ③'s example sentence says
// 「連続MTGの後」 — back-to-back meetings. The rule below checks a COUNT (three or more events on the
// day) and a TAIL (the last of them ended within 8h of the tap); it never checks whether any two of
// them touch. Three half-hour calls spread across a working day would have been reported as 連続MTG.
// So the sentence states the evidence that exists — 「予定が3件以上あった{weekday}曜の後」 — rather
// than the stronger claim. A contiguity check would have been the other way to close the gap, and it
// is the wrong one here: it buys a nicer noun at the cost of a rule nobody can restate, and §9.5 asks
// for the honest statement, not the comfortable one.
//
// A CONTRADICTION IN THE SPEC ROW, RESOLVED HERE RATHER THAN HIDDEN. H4 ① sets the question at
// 週次で closed Q 1問 — at most one ask, and therefore at most ONE ANSWER, per week. H4 ③ then gives
// the mirror's example as 「今週は『きつく当たった』が2回。全部 木曜の…」: two occurrences, all on the
// same weekday. Those cannot both be true of one week — one ask a week yields one answer a week, and
// a seven-day window contains exactly one Thursday. Taking the "trailing 7 days" evidence window
// literally would ship a leg that can NEVER fire: dead code wearing a feature's name, which is the
// exact 12c disease this repo has already been burned by.
//   The ask cadence is the harder constraint (it is what protects the user), so it is kept exactly:
//   7-day spacing, unchanged. The EVIDENCE WINDOW is what widens — to four weeks — because that is
//   the smallest window in which the spec's own example message is producible at all. Everything
//   else in H4 ③ is untouched: Sunday night, one message, at most one a week, ≥2 answers, pattern or
//   nothing, no score, no advice.
//   And the COPY SAYS FOUR WEEKS (「最近4週間の記録です」), because a message that counts 28 days
//   while saying 「今週は」 is a small lie, and §9.5 is explicit that an honest statement beats a
//   comfortable one. If Dais later makes the question more frequent than weekly, this constant is
//   the one line to change and the copy follows it.
//
// This is the leg that can do real harm, so every gate is hard and stated:
//   EVIDENCE — at least 2 answers in the trailing window. One tap is a night, not a period, and a
//              mirror reflecting a single data point is a spotlight, not a mirror.
//   TIMING   — Sunday night in the USER's week, in the same bedtime window as the question, at most
//              once every 7 days. Read from the ledger, not from memory.
//   BUDGET   — H4 ⑤ again: the mirror is a MENTAL send. It reads lm_mental_send_log before speaking
//              and writes to it after. The Sunday ask and the Sunday mirror therefore cannot both
//              land: whichever goes first spends a slot and starts the 2h clock, and the scheduler
//              defers the question for the tick a mirror went out on.
//   FACTS    — the counts are counts of taps the user made. When no pattern holds, the message is
//              facts and stops. A pattern is never reached for; it either survives the rule below or
//              it does not exist.
//
// THE PATTERN RULE, in full, because a heuristic nobody can restate is a heuristic nobody can audit:
//   1. Only NON-calm answers are candidates. 「なし・穏やかだった」 is a real observation and it is
//      counted in the message, but "you were calm on Thursdays" is not a context worth naming.
//   2. The SUBJECT is the single non-calm answer value with the highest count in the window, ties
//      broken by the fixed PRECEPTS_ANSWERS order so the same week always produces the same message.
//      It must occur at least twice. One occurrence has no pattern by construction.
//   3. WEEKDAY: group the subject's answers by the weekday of the EVENING THEY DESCRIBE — the day
//      carried on the row, not the day the tap happened to land on. Half of all answers arrive after
//      local midnight (the question ships ≤30 min before bedtime), so reading the weekday off
//      answered_at would tell a Thursday-heavy user that their Fridays are hard. Take the largest
//      group (ties → the earliest weekday); two or more on the same weekday is a weekday pattern.
//   4. BUSY: an answer is "after a busy day" when its own local day carried BUSY_MIN_EVENTS (3) or
//      more calendar events AND the last of them ended within BUSY_TAIL_MS before the tap. Two or
//      more is a busy pattern. "Ended" is the provider's real end.dateTime wherever there is one;
//      where there is none (all-day rows, an unparseable end) the day falls back to start + 1h,
//      which is an ASSUMPTION and is treated as one — it is documented at both use sites and it
//      makes the branch harder to reach, never easier.
//   5. Both, on the SAME answers (every member of the weekday group is also busy) → the combined
//      sentence, which is the spec's own example. Weekday only → the weekday sentence. Busy only →
//      the busy sentence. Otherwise → facts, and nothing else.
//
// WHY BUSY_TAIL_MS IS NOT THE 2 HOURS THE ROW SKETCHES. The question is a BEDTIME question, so every
// tap lands around 23:00 — five or six hours after a working day ends. A literal 2h tail would make
// this branch unreachable in production: not a conservative heuristic, but a lie in the shape of one.
// The 8h tail is what the sentence 「予定が3件以上あった…の後」 actually claims — that the day's
// events ran INTO the evening the user is now reflecting on — and it still refuses a day whose three
// events all finished before lunch. Same-local-day is the constraint doing most of the work; the tail
// is what keeps "a busy morning" from being reported as the context of a 23:30 tap.

const { PRECEPTS_ANSWERS, PRECEPTS_ANSWER_LABELS, PRECEPTS_CALM } = require("./precepts-question.js");
const {
  claimPreceptsRow, resolvePreceptsTzOffsetH, resolvePreceptsSleepTarget,
  markBudgetUnrecorded, isBudgetUnrecorded,
} = require("./precepts-runtime.js");
const { localDay, localWeekday } = require("./user-tz.js");
const { readMentalSendState, recordMentalSend } = require("./mental-send-log.js");
const { DAILY_CAP, MIN_GAP_MS, LOCATION_STATES } = require("./mental-trigger.js");
const { PRECEPTS_STRINGS, WEEKDAY_JA } = require("./i18n.js");
const { fetchCalendarHistory } = require("./events.js");
const { sendMessage } = require("./telegram.js");

const MIRROR_MIN_ANSWERS = 2;
// Four weeks of evidence — see the header for why this is not the seven days the row sketches, and
// why the copy names the window it actually used.
const MIRROR_WINDOW_DAYS = 28;
// …but still only ONE mirror per week. The cadence and the evidence window are different questions:
// how often we may speak, and how much we may speak about.
const MIRROR_COOLDOWN_DAYS = 7;
const MIRROR_WINDOW_MS = MIRROR_WINDOW_DAYS * 86400000;
const MIRROR_WEEKDAY = 0;              // Sunday, in the user's own week
const PRECEPTS_WINDOW_MS = 30 * 60000; // the same 30 minutes before bedtime the question uses
const BUSY_MIN_EVENTS = 3;
const BUSY_TAIL_MS = 8 * 3600000;
const MIRROR_SEND_TRIGGER = "precepts_mirror";
// A week plus a day of calendar, so a timezone edge cannot drop the oldest answer's own day.
const MIRROR_HISTORY_MS = (MIRROR_WINDOW_DAYS + 1) * 86400000;
const DAY_PATTERN = /^\d{4}-\d{2}-\d{2}$/;

const INPUT_KEYS = Object.freeze([
  "nowMs", "tzOffsetH", "sleepTargetMs", "sentTodayCount", "lastMentalSentMs",
  "answers", "lastMirrorDay", "events", "location",
]);

function validateInput(input) {
  if (!input || typeof input !== "object" || Array.isArray(input)) throw new Error("input must be an object");
  for (const key of Object.keys(input)) {
    if (!INPUT_KEYS.includes(key)) throw new Error(`unknown key: ${key}`);
  }
  if (!Number.isFinite(input.nowMs)) throw new Error("nowMs must be a finite number");
  if (!Number.isFinite(input.tzOffsetH)) throw new Error("tzOffsetH must be a finite number");
  if (input.sleepTargetMs !== null && !Number.isFinite(input.sleepTargetMs)) {
    throw new Error("sleepTargetMs must be null or a finite number");
  }
  if (!Number.isInteger(input.sentTodayCount) || input.sentTodayCount < 0) {
    throw new Error("sentTodayCount must be a non-negative integer");
  }
  if (input.lastMentalSentMs !== null && !Number.isFinite(input.lastMentalSentMs)) {
    throw new Error("lastMentalSentMs must be null or a finite number");
  }
  if (!Array.isArray(input.answers)) throw new Error("answers must be an array");
  for (const sample of input.answers) {
    if (!sample || typeof sample !== "object") throw new Error("answer sample must be an object");
    if (!PRECEPTS_ANSWERS.includes(sample.answer)) {
      throw new Error(`unknown precepts answer: ${String(sample && sample.answer).slice(0, 20)}`);
    }
    if (!Number.isFinite(sample.atMs)) throw new Error("answer sample must have a finite atMs");
  }
  if (input.lastMirrorDay !== null && !DAY_PATTERN.test(String(input.lastMirrorDay))) {
    throw new Error("lastMirrorDay must be null or a YYYY-MM-DD local day");
  }
  if (!Array.isArray(input.events)) throw new Error("events must be an array");
  if (!input.location || !LOCATION_STATES.includes(input.location.state)) {
    throw new Error(`location.state must be one of ${LOCATION_STATES.join("|")}`);
  }
  return input;
}

// Whole local days between two YYYY-MM-DD strings. Both are already local days, so plain UTC
// arithmetic on them is exact — no offset enters twice.
function daysBetween(fromDay, toDay) {
  return Math.round((Date.parse(`${toDay}T00:00:00Z`) - Date.parse(`${fromDay}T00:00:00Z`)) / 86400000);
}

// Pure. Cheapest and most binding refusal first, so a spent budget reports the budget, not the week.
function evaluatePreceptsMirror(input) {
  validateInput(input);
  const { nowMs, tzOffsetH } = input;

  if (input.sentTodayCount >= DAILY_CAP) return { decision: "suppress", reason: "mental-daily-cap-reached" };
  if (input.lastMentalSentMs !== null && nowMs - input.lastMentalSentMs < MIN_GAP_MS) {
    return { decision: "suppress", reason: "too-soon-after-mental-send" };
  }
  if (input.lastMirrorDay !== null) {
    const sinceDays = daysBetween(input.lastMirrorDay, localDay(nowMs, tzOffsetH));
    if (sinceDays <= 0) return { decision: "suppress", reason: "already-mirrored-today" };
    if (sinceDays < MIRROR_COOLDOWN_DAYS) {
      return { decision: "suppress", reason: "mirror-cooldown", daysSinceLastMirror: sinceDays };
    }
  }
  if (input.events.some((e) => Number.isFinite(e.startMs) && Number.isFinite(e.endMs)
    && nowMs >= e.startMs && nowMs < e.endMs)) {
    return { decision: "suppress", reason: "mid-event" };
  }
  if (input.location.state === "moving") return { decision: "suppress", reason: "user-moving" };

  // Sunday in the USER's week. A user whose bedtime target falls after local midnight is mirrored on
  // the day the clock actually reads, which is stated rather than papered over: "Sunday night" for
  // a 00:30 sleeper is Monday 00:00, and inventing a rule that says otherwise would put the weekly
  // message on a different night than the weekly window it shares with the question.
  if (localWeekday(nowMs, tzOffsetH) !== MIRROR_WEEKDAY) {
    return { decision: "suppress", reason: "not-sunday" };
  }
  if (input.sleepTargetMs === null) return { decision: "suppress", reason: "no-sleep-target" };
  const untilSleep = input.sleepTargetMs - nowMs;
  if (untilSleep < 0 || untilSleep > PRECEPTS_WINDOW_MS) {
    return { decision: "suppress", reason: "outside-bedtime-window" };
  }

  const cutoff = nowMs - MIRROR_WINDOW_MS;
  const recent = input.answers.filter((sample) => sample.atMs >= cutoff && sample.atMs <= nowMs);
  if (recent.length < MIRROR_MIN_ANSWERS) {
    return { decision: "suppress", reason: "not-enough-answers", answerCount: recent.length };
  }
  return { decision: "send", reason: "weekly-mirror-due", answerCount: recent.length, answers: recent };
}

// { answer → count } over the window, in the fixed PRECEPTS_ANSWERS order so the same week always
// renders the same sentence. Only values that actually occurred appear — a zero is not a fact the
// user told us, and printing 「『嘘をついた』が0回」 would read as an accusation dressed as arithmetic.
function countAnswers(answers) {
  const counts = new Map();
  for (const sample of answers) counts.set(sample.answer, (counts.get(sample.answer) || 0) + 1);
  return PRECEPTS_ANSWERS
    .filter((answer) => counts.has(answer))
    .map((answer) => ({ answer, count: counts.get(answer) }));
}

// When an event ended, or — said out loud — when we are ASSUMING it ended.
//
// `null` is what fetchCalendarHistory reports for an event with no end instant (an all-day row, or an
// end the provider could not parse), and `Number(null)` is 0, so a naive Number.isFinite check turns
// "we do not know" into "it ended at the epoch". The absence has to be tested before the coercion.
// An end at or before the start is treated the same way: a zero-length or backwards event is not a
// measurement either.
const ASSUMED_EVENT_MS = 3600000;

function resolveEventEndMs(event, startMs) {
  const raw = event ? event.endMs : null;
  const parsed = raw === null || raw === undefined || raw === "" ? NaN : Number(raw);
  return Number.isFinite(parsed) && parsed > startMs ? parsed : startMs + ASSUMED_EVENT_MS;
}

// The busy-day index: local day → { events, lastEndMs }. Built once per mirror rather than scanned
// per answer, and it holds NO event content — only how many there were and when the last one ended.
function indexEventDays(events, tzOffsetH) {
  const byDay = new Map();
  for (const event of (Array.isArray(events) ? events : [])) {
    const startMs = Number(event && event.startMs);
    if (!Number.isFinite(startMs)) continue;
    // The provider's real end where there is one (fetchCalendarHistory now carries end.dateTime
    // through). Where there is none, this ASSUMES one hour — stated rather than dressed as a
    // measurement, and erring toward an EARLIER end, which can only push a day out of the tail and
    // never pull one in.
    const endMs = resolveEventEndMs(event, startMs);
    const day = localDay(startMs, tzOffsetH);
    const bucket = byDay.get(day) || { events: 0, lastEndMs: -Infinity };
    bucket.events += 1;
    bucket.lastEndMs = Math.max(bucket.lastEndMs, endMs);
    byDay.set(day, bucket);
  }
  return byDay;
}

// The weekday of the EVENING the row describes. `day` is what the question carried and what the row
// is keyed to; answered_at is when the person tapped, which for a bedtime question is very often the
// next calendar day already. Reading the weekday off the instant would report Fridays to a user whose
// hard nights are Thursdays. Rows written before the day was carried (or fixtures without one) fall
// back to the instant, which is all there is for them.
function sampleWeekday(sample, tzOffsetH) {
  const day = sample && sample.day ? String(sample.day) : "";
  if (DAY_PATTERN.test(day)) {
    const ms = Date.parse(`${day}T00:00:00Z`);
    if (Number.isFinite(ms)) return new Date(ms).getUTCDay();
  }
  return localWeekday(sample.atMs, tzOffsetH);
}

function isAfterBusyDay(sample, dayIndex, tzOffsetH) {
  const bucket = dayIndex.get(sample.day || localDay(sample.atMs, tzOffsetH));
  if (!bucket || bucket.events < BUSY_MIN_EVENTS) return false;
  const gap = sample.atMs - bucket.lastEndMs;
  return gap >= 0 && gap <= BUSY_TAIL_MS;
}

// The rule from the header, executed. Returns a SHAPE — {kind, answer, count, weekday} — never any
// event content, because that shape is what gets written to the append-only ledger.
function detectPreceptsPattern({ answers = [], events = [], tzOffsetH = 0 } = {}) {
  const none = { kind: "none" };
  const candidates = answers.filter((sample) => sample.answer !== PRECEPTS_CALM);
  if (candidates.length < 2) return none;

  const counts = new Map();
  for (const sample of candidates) counts.set(sample.answer, (counts.get(sample.answer) || 0) + 1);
  // Ties break on the fixed answer order, so the same week never renders two different messages.
  let subject = null;
  for (const answer of PRECEPTS_ANSWERS) {
    if (!counts.has(answer)) continue;
    if (subject === null || counts.get(answer) > counts.get(subject)) subject = answer;
  }
  if (subject === null || counts.get(subject) < 2) return none;
  const subjectSamples = candidates.filter((sample) => sample.answer === subject);

  const byWeekday = new Map();
  for (const sample of subjectSamples) {
    const weekday = sampleWeekday(sample, tzOffsetH);
    byWeekday.set(weekday, [...(byWeekday.get(weekday) || []), sample]);
  }
  let weekdayGroup = null;
  let weekday = null;
  for (const [day, group] of [...byWeekday.entries()].sort((a, b) => a[0] - b[0])) {
    if (weekdayGroup === null || group.length > weekdayGroup.length) { weekdayGroup = group; weekday = day; }
  }
  const hasWeekday = weekdayGroup !== null && weekdayGroup.length >= 2;

  const dayIndex = indexEventDays(events, tzOffsetH);
  const busySamples = subjectSamples.filter((sample) => isAfterBusyDay(sample, dayIndex, tzOffsetH));
  const hasBusy = busySamples.length >= 2;

  if (hasWeekday && weekdayGroup.every((sample) => isAfterBusyDay(sample, dayIndex, tzOffsetH))) {
    return { kind: "weekday_busy", answer: subject, count: weekdayGroup.length, weekday };
  }
  if (hasWeekday) return { kind: "weekday", answer: subject, count: weekdayGroup.length, weekday };
  if (hasBusy) return { kind: "busy", answer: subject, count: busySamples.length, weekday: null };
  return none;
}

// Every substitution goes through a FUNCTION replacer: labels are data, and `$&` / `$'` / `` $` `` /
// `$1` are all magic to String.replace's string form.
function fill(template, values) {
  let out = String(template);
  for (const [key, value] of Object.entries(values)) out = out.replace(`{${key}}`, () => String(value));
  return out;
}

function buildMirrorMessage({ counts, pattern } = {}) {
  const copy = PRECEPTS_STRINGS.ja.weeklyMirror;
  const rendered = (Array.isArray(counts) ? counts : [])
    .map(({ answer, count }) => fill(copy.countItem, { label: PRECEPTS_ANSWER_LABELS[answer], count }))
    .join(copy.countSeparator);
  const kind = pattern && pattern.kind;
  if (kind === "weekday_busy") {
    return fill(copy.weekdayBusy, {
      counts: rendered, patternCount: pattern.count, weekday: WEEKDAY_JA[pattern.weekday],
    });
  }
  if (kind === "weekday") {
    return fill(copy.weekday, {
      counts: rendered, patternCount: pattern.count, weekday: WEEKDAY_JA[pattern.weekday],
    });
  }
  if (kind === "busy") return fill(copy.busy, { counts: rendered, patternCount: pattern.count });
  return fill(copy.facts, { counts: rendered });
}

function headers(key) {
  return { apikey: key, Authorization: `Bearer ${key}` };
}

function supaBase(url) {
  return String(url).replace(/\/$/, "");
}

// The trailing-7-day answers. Throws on a failed read — an unreadable ledger must never become an
// assumed week. Filtered on `day` (the column the (uid, day DESC) index serves) with a one-day
// cushion, then cut precisely on answered_at in JS.
async function readPreceptsAnswers(uid, nowMs, supa, fetchImpl, tzOffsetH = 0) {
  const floorDay = localDay(nowMs - MIRROR_WINDOW_MS - 86400000, tzOffsetH);
  const query = `uid=eq.${encodeURIComponent(uid)}&kind=eq.answer`
    + `&day=gte.${encodeURIComponent(floorDay)}&select=answer,answered_at,day&order=day.desc`;
  const response = await fetchImpl(`${supaBase(supa.supaUrl)}/rest/v1/lm_precepts_log?${query}`, {
    headers: headers(supa.supaKey),
  }).catch(() => null);
  if (!response || !response.ok) throw new Error("precepts answer lookup failed");
  const rows = await response.json().catch(() => null);
  if (!Array.isArray(rows)) throw new Error("precepts answer lookup returned no rows array");
  return rows
    .map((row) => ({
      answer: row.answer,
      atMs: Date.parse(row.answered_at),
      day: row.day ? String(row.day).slice(0, 10) : null,
    }))
    .filter((sample) => PRECEPTS_ANSWERS.includes(sample.answer) && Number.isFinite(sample.atMs));
}

// The LAST mirror inside the cooldown horizon, as a local day. Both bounds the pure function needs —
// "did we already speak today" and "has a week passed" — come from this one row, so the cadence lives
// in the ledger and survives a restart. Throws on a failed read.
async function readLastMirrorDay(uid, nowMs, tzOffsetH, supa, fetchImpl) {
  const floorDay = localDay(nowMs - MIRROR_COOLDOWN_DAYS * 86400000, tzOffsetH);
  const query = `uid=eq.${encodeURIComponent(uid)}&kind=eq.mirror`
    + `&day=gte.${encodeURIComponent(floorDay)}&select=day&order=day.desc&limit=1`;
  const response = await fetchImpl(`${supaBase(supa.supaUrl)}/rest/v1/lm_precepts_log?${query}`, {
    headers: headers(supa.supaKey),
  }).catch(() => null);
  if (!response || !response.ok) throw new Error("precepts mirror state lookup failed");
  const rows = await response.json().catch(() => null);
  if (!Array.isArray(rows)) throw new Error("precepts mirror state lookup returned no rows array");
  const day = rows[0] && rows[0].day ? String(rows[0].day).slice(0, 10) : null;
  return day && DAY_PATTERN.test(day) ? day : null;
}

// The calendar bound, and the same memo diet-nudge's venue lookup needed for the same reason. The
// mirror runs inside a 30-tick window; a day whose claim keeps failing would otherwise pull an
// 8-day calendar history on every one of them. Once per (uid, local day) per process.
//
// WHY the history is resolved BEFORE the claim rather than claiming a pattern-less row first: the
// ledger is append-only, so a row claimed early could never be corrected to say which pattern the
// message actually named, and an unauditable mirror row is exactly what an append-only ledger exists
// to prevent. Cost, stated: a restart mid-window re-resolves once (bounded by restarts, not ticks).
const HISTORY_MEMO = new Map(); // `${uid}|${day}` → events[]

function resetPreceptsMirrorState() {
  HISTORY_MEMO.clear();
}

async function resolveHistoryOnce(uid, day, resolve) {
  const key = `${uid}|${day}`;
  if (HISTORY_MEMO.has(key)) return HISTORY_MEMO.get(key);
  // Promise.resolve().then: an injected resolver that throws SYNCHRONOUSLY never returns a promise,
  // so a trailing .catch() on the call would never run and the throw would escape into the tick.
  const events = await Promise.resolve().then(resolve).catch(() => null);
  for (const existing of [...HISTORY_MEMO.keys()]) {
    if (!existing.endsWith(`|${day}`)) HISTORY_MEMO.delete(existing);
  }
  const shaped = Array.isArray(events) ? events : [];
  HISTORY_MEMO.set(key, shaped);
  return shaped;
}

// The calendar read for the pattern. A failure yields [] — no pattern, facts only — which is the
// honest degradation: we can always say what the user told us, and we simply do not claim a context
// we could not check. fetchCalendarHistory is STRICT by contract, so the throw is caught here.
async function readPatternEvents(uid, nowMs, deps) {
  const events = await (deps.fetchHistory || fetchCalendarHistory)(uid, {
    nowMs, historyMs: MIRROR_HISTORY_MS,
    apiKey: deps.apiKey || process.env.COMPOSIO_API_KEY,
    calendar: deps.calendar, gmailAccountId: deps.gmailAccountId,
  });
  // Only the two numbers the busy rule reads survive this projection — no summary, no attendees, no
  // location. The end is the provider's own where it exists and the documented start+1h assumption
  // where it does not (see resolveEventEndMs).
  return (Array.isArray(events) ? events : [])
    .map((event) => ({ startMs: Number(event.startMs), raw: event }))
    .filter((event) => Number.isFinite(event.startMs))
    .map(({ startMs, raw }) => ({ startMs, endMs: resolveEventEndMs(raw, startMs) }));
}

async function preceptsMirrorOnce(u, nowMs, deps = {}) {
  const supa = {
    supaUrl: deps.supaUrl || process.env.SUPABASE_URL,
    supaKey: deps.supaKey || process.env.SUPABASE_SERVICE_ROLE_KEY,
  };
  const chatId = String((u && u.telegram_chat_id) || "");
  if (!u || !u.uid || !chatId || u.notifications_enabled === false || !supa.supaUrl || !supa.supaKey) {
    return { status: "skipped" };
  }
  const fetchImpl = deps.fetchImpl || globalThis.fetch;

  const offsetH = resolvePreceptsTzOffsetH(deps, u, nowMs);
  if (offsetH === null) return { status: "skipped", reason: "no-timezone" };

  // Sunday and the window are both arithmetic, and both are checked before anything is read: six
  // nights in seven, and 23½ hours of the seventh, this leg must cost exactly nothing.
  if (localWeekday(nowMs, offsetH) !== MIRROR_WEEKDAY) {
    return { status: "suppressed", reason: "not-sunday" };
  }
  const sleepTargetMs = resolvePreceptsSleepTarget(deps, nowMs, offsetH);
  if (!Number.isFinite(sleepTargetMs)) return { status: "skipped", reason: "no-sleep-target" };
  const untilSleep = sleepTargetMs - nowMs;
  if (untilSleep < 0 || untilSleep > PRECEPTS_WINDOW_MS) {
    return { status: "suppressed", reason: "outside-bedtime-window" };
  }
  const day = localDay(nowMs, offsetH);
  // Fail closed on cap accounting, shared with the question leg: both spend MENTAL's three, so a day
  // whose budget row was lost stands BOTH of them down. Checked before the reads — a stood-down organ
  // costs nothing.
  if (isBudgetUnrecorded(u.uid, day)) {
    return { status: "suppressed", reason: "budget-unrecorded" };
  }

  let lastMirrorDay;
  let answers;
  let mentalState;
  try {
    lastMirrorDay = await readLastMirrorDay(u.uid, nowMs, offsetH, supa, fetchImpl);
    answers = await readPreceptsAnswers(u.uid, nowMs, supa, fetchImpl, offsetH);
    mentalState = await (deps.readMentalSendState || readMentalSendState)(
      u.uid, nowMs, supa, fetchImpl, { strict: true },
    );
  } catch (error) {
    return { status: "suppressed", reason: "ledger-unreadable", error: error && error.message };
  }

  const locationState = deps.getLocationState ? await deps.getLocationState(u.uid, nowMs) : "unknown";
  const verdict = evaluatePreceptsMirror({
    nowMs,
    tzOffsetH: offsetH,
    sleepTargetMs,
    sentTodayCount: Number(mentalState && mentalState.sentTodayCount) || 0,
    lastMentalSentMs: mentalState && Number.isFinite(mentalState.lastSentMs) ? mentalState.lastSentMs : null,
    answers,
    lastMirrorDay,
    events: Array.isArray(deps.events) ? deps.events : [],
    location: { state: locationState || "unknown" },
  });
  if (verdict.decision !== "send") return { status: "suppressed", reason: verdict.reason, ...verdict };

  const events = await resolveHistoryOnce(u.uid, day, () => readPatternEvents(u.uid, nowMs, deps));
  const pattern = detectPreceptsPattern({ answers: verdict.answers, events, tzOffsetH: offsetH });
  const counts = countAnswers(verdict.answers);

  const claimed = await claimPreceptsRow({
    uid: u.uid, day, kind: "mirror", asked_at: new Date(nowMs).toISOString(),
    pattern: pattern.kind === "none" ? null : pattern,
  }, supa, fetchImpl);
  if (!claimed) return { status: "suppressed", reason: "already-mirrored-today" };

  const text = buildMirrorMessage({ counts, pattern });
  const sent = await (deps.sendMessage || sendMessage)(
    deps.telegramToken !== undefined ? deps.telegramToken : process.env.LM_TELEGRAM_BOT_TOKEN,
    chatId, text,
  );
  if (!sent || !sent.ok) return { status: "send_failed", day, pattern: pattern.kind };
  const messageId = sent.result && sent.result.message_id;
  // H4 ⑤: the mirror spends one of MENTAL's three too.
  const budgeted = await (deps.recordMentalSend || recordMentalSend)(
    u.uid, MIRROR_SEND_TRIGGER, messageId, supa, fetchImpl,
  );
  // Delivered, and the cap never saw it. Stand the organ down for the day rather than let the
  // question leg keep spending an accounting we know is short.
  if (!budgeted) markBudgetUnrecorded(u.uid, day);
  return {
    status: "mirrored",
    day,
    pattern: pattern.kind,
    answerCount: verdict.answerCount,
    telegramMessageId: messageId,
    budgeted,
  };
}

module.exports = {
  MIRROR_MIN_ANSWERS,
  MIRROR_WINDOW_DAYS,
  MIRROR_COOLDOWN_DAYS,
  MIRROR_WEEKDAY,
  MIRROR_SEND_TRIGGER,
  MIRROR_HISTORY_MS,
  BUSY_MIN_EVENTS,
  BUSY_TAIL_MS,
  countAnswers,
  detectPreceptsPattern,
  evaluatePreceptsMirror,
  buildMirrorMessage,
  readPreceptsAnswers,
  readLastMirrorDay,
  resetPreceptsMirrorState,
  preceptsMirrorOnce,
};
