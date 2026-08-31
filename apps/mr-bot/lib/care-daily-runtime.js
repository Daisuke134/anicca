"use strict";
// lib/care-daily-runtime.js — 11a/11b PHY runtime (§10 rows 11a/11b, §9.1 PHYSICAL organ).
// The detector, anchors, candidate search, and evaluator all existed, were tested, and were called
// by NOTHING in production — the same unreachable-rule disease 12c had. This module is the cure:
// careUserOnce runs on the 60s tick, claims one real scan per user per UTC day durably in
// lm_care_scan_log (no in-memory counters — restarts cannot double-scan or forget), reads ~10
// months of the user's OWN calendar history, and records what the detector saw. Abstention (no
// candidates) is the honest common case and gets a row too. On a REAL detection the 11b chain runs
// in-process — anchors → anchored candidate search → route evaluation — and the full result lands
// on the same scan row.
//
// 11c/11d (booking + aftercare) hang off the END of that chain, BEHIND `LM_BOOKING_ENABLED=1`. With
// the gate absent this module has exactly the side effects it always had: none — no browser session,
// no Telegram, no calendar write. With the gate on, an ACTIONABLE detection (CADENCE-1: observe_only
// detections never get this far) whose selected candidate has a web reservation route is booked by
// care-booking-executor, and care-aftercare reports the outcome and records it under `chain.booking`.
// The booking leg is isolated the way the chain leg is: it can never lose the detection row, which is
// written and claimed before any of it runs. It is also deduplicated ACROSS days: the daily claim only
// stops two ticks on the same day, and an overdue detection stays true until the appointment we just
// booked actually happens — so prior rows are read for a live booking of the same care type first.

const { detectCalendarCare } = require("./care-detector-runtime.js");
const { deriveAnchors } = require("./care-anchors.js");
const { searchCareCandidates } = require("./care-candidate-search.js");
const { evaluateCareCandidates } = require("./care-candidates.js");
const { fetchCalendarHistory } = require("./events.js");
const { executeBooking } = require("./care-booking-executor.js");
const { runAftercare } = require("./care-aftercare.js");
const { makeSteelCdpClient } = require("./steel-cdp-client.js");
const { sendMessage } = require("./telegram.js");

// The user's own words → the 11a care types (the exact categories care-candidate-search.js
// CATEGORY_KEYWORDS knows; no invented types). This is deterministic data
// linkage like careTag() in care-detector.js, not text inference: an event only counts as a care
// visit when its title literally names the care. Specific checkups MUST precede generic clinic:
// one visit is one category, and "胃内視鏡 クリニック" is not ordinary clinic cadence.
const CARE_TYPE_KEYWORDS = Object.freeze({
  gastric_screening: Object.freeze([
    "胃がん検診", "胃検診", "胃ドック", "胃カメラ", "胃内視鏡",
    "gastric screening", "stomach screening", "gastroscopy",
  ]),
  colorectal_screening: Object.freeze([
    "大腸がん検診", "大腸検診", "大腸ドック", "大腸カメラ", "大腸内視鏡", "便潜血",
    "colorectal screening", "colon screening", "colonoscopy",
  ]),
  brain_dock: Object.freeze(["脳ドック", "brain dock", "brain screening"]),
  dental: Object.freeze(["歯科", "歯医者", "デンタル", "dental", "dentist"]),
  haircut: Object.freeze(["散髪", "美容室", "美容院", "床屋", "理容", "ヘアサロン", "haircut", "barber"]),
  clinic: Object.freeze(["クリニック", "健康診断", "内科", "診療所", "clinic", "checkup"]),
});

// history events → detectCalendarCare sources ([{careType, events}]). First matching type wins
// (an event is one visit, never two); unmatched events are not care visits — they still serve
// deriveAnchors as plain calendar events (work anchor), just not as care history.
function classifyCareHistory(events) {
  const byType = new Map();
  for (const event of Array.isArray(events) ? events : []) {
    const summary = String(event?.summary || "").toLowerCase();
    if (!summary) continue;
    for (const [careType, words] of Object.entries(CARE_TYPE_KEYWORDS)) {
      if (words.some((word) => summary.includes(word.toLowerCase()))) {
        if (!byType.has(careType)) byType.set(careType, []);
        byType.get(careType).push(event);
        break;
      }
    }
  }
  return [...byType.entries()].map(([careType, evs]) => ({ careType, events: evs }));
}

function headers(key, extra) {
  return { apikey: key, Authorization: `Bearer ${key}`, ...extra };
}

// Daily-claim lookup — the recordDailyComposioPoll pattern: check today's row in Supabase on every
// tick, so the claim survives restarts. The atomic half is the UNIQUE(uid, scan_day) insert below.
async function todayScanExists(uid, day, supa, fetchImpl) {
  const query = `uid=eq.${encodeURIComponent(uid)}&scan_day=eq.${encodeURIComponent(day)}&select=id&limit=1`;
  const response = await fetchImpl(`${supa.url}/rest/v1/lm_care_scan_log?${query}`, { headers: headers(supa.key) });
  if (!response.ok) throw new Error(`care scan lookup failed (${response.status})`);
  const rows = await response.json().catch(() => []);
  return Array.isArray(rows) && rows.length > 0;
}

// 201 = this tick owns today's scan; 409 / PostgREST duplicate-key body (23505) = another tick
// already claimed it — the claimWake precedent, so two overlapping ticks can never both run the 11b
// chain. Anything ELSE is a real failure and THROWS: a Supabase 500 is not "already scanned", and
// treating it as the race loss would silently drop the scan (the scheduler's catch logs the throw).
async function insertScanRow(row, supa, fetchImpl) {
  const response = await fetchImpl(`${supa.url}/rest/v1/lm_care_scan_log`, {
    method: "POST",
    headers: headers(supa.key, { "Content-Type": "application/json", Prefer: "return=minimal" }),
    body: JSON.stringify(row),
  });
  if (response.status === 201) return true;
  if (response.status === 409) return false;
  const body = typeof response.text === "function" ? await response.text().catch(() => "") : "";
  if (/23505|duplicate key/i.test(body)) return false;
  throw new Error(`care scan insert failed (${response.status})${body ? `: ${body.slice(0, 200)}` : ""}`);
}

// ─── cross-day double booking ───────────────────────────────────────────────────────────────────
// The scan runs EVERY day, and an overdue detection stays true until a NEW visit lands on the user's
// calendar — which will not happen until the appointment we just booked actually takes place, weeks
// out. The daily claim in lm_care_scan_log stops two ticks on the same day; nothing stopped tomorrow.
// So before the booking leg runs at all, the prior rows are read for a booking of the SAME care type
// that is still live. `possibly_booked` counts every bit as much as `booked`: an unconfirmed submit is
// precisely the case where booking again would double-book a real clinic.
const BOOKING_DEDUP_WINDOW_MS = 30 * 86_400_000;
const LIVE_BOOKING_OUTCOMES = new Set(["booked", "possibly_booked"]);

async function findLiveBooking(uid, careType, nowMs, supa, fetchImpl) {
  const query = `uid=eq.${encodeURIComponent(uid)}&select=id,scan_day,chain&order=scan_day.desc&limit=60`;
  const response = await fetchImpl(`${supa.url}/rest/v1/lm_care_scan_log?${query}`, { headers: headers(supa.key) });
  if (!response || !response.ok) {
    // A lookup we could not run is NOT "no prior booking". Throwing lands as chain_error and skips
    // the booking leg — the safe side of a question we cannot answer.
    throw new Error(`care booking history lookup failed (${response ? response.status : "no response"})`);
  }
  const rows = await response.json().catch(() => []);
  for (const row of Array.isArray(rows) ? rows : []) {
    const booking = row && row.chain && row.chain.booking;
    if (!booking || row.chain.category !== careType) continue;
    if (!LIVE_BOOKING_OUTCOMES.has(booking.outcome)) continue;
    // Prefer the slot that was actually requested; fall back to the day the attempt was made, so a
    // possibly_booked with no slot still blocks the retry for the window.
    const slotMs = booking.booked_slot ? Date.parse(booking.booked_slot) : NaN;
    const referenceMs = Number.isFinite(slotMs) ? slotMs : Date.parse(`${row.scan_day}T00:00:00Z`);
    if (!Number.isFinite(referenceMs)) continue;
    if (referenceMs >= nowMs - BOOKING_DEDUP_WINDOW_MS) return { id: row.id, scanDay: row.scan_day, booking };
  }
  return null;
}

async function updateScanChain(uid, day, patch, supa, fetchImpl) {
  const query = `uid=eq.${encodeURIComponent(uid)}&scan_day=eq.${encodeURIComponent(day)}`;
  const response = await fetchImpl(`${supa.url}/rest/v1/lm_care_scan_log?${query}`, {
    method: "PATCH",
    headers: headers(supa.key, { "Content-Type": "application/json", Prefer: "return=minimal" }),
    body: JSON.stringify(patch),
  });
  return Boolean(response && response.ok);
}

async function careUserOnce(u, nowMs, deps = {}) {
  const supa = {
    url: deps.supaUrl || process.env.SUPABASE_URL,
    key: deps.supaKey || process.env.SUPABASE_SERVICE_ROLE_KEY,
  };
  if (!u || !u.uid || !supa.url || !supa.key) return { status: "skipped" };
  const fetchImpl = deps.fetchImpl || globalThis.fetch;
  const logError = deps.logError || console.error;
  const now = Number.isFinite(nowMs) ? nowMs : Date.now();
  const day = new Date(now).toISOString().slice(0, 10); // UTC day, like recordDailyComposioPoll

  if (await todayScanExists(u.uid, day, supa, fetchImpl)) return { status: "already_scanned" };

  // The day is claimed ONLY after a successful history read. fetchCalendarHistory is a STRICT read
  // (transport failure throws, never []): if the claim were written from a failed read, a single API
  // blip would freeze history_event_count=0 / detections=[] into the append-only lm_care_scan_log and
  // poison the whole day. On failure: no row, no claim — the next 60s tick simply retries.
  let history;
  try {
    history = await (deps.fetchCalendarHistory || fetchCalendarHistory)(u.uid, {
      nowMs: now,
      historyMs: deps.historyMs, // undefined → events.js CARE_HISTORY_MS (~10 years)
      apiKey: deps.apiKey || process.env.COMPOSIO_API_KEY,
      calendar: deps.calendar,
      gmailAccountId: u.gmail_account_id,
    });
  } catch (error) {
    return { status: "history_unavailable", error: String((error && error.message) || error) };
  }
  const sources = classifyCareHistory(history);
  const receipt = detectCalendarCare({
    nowMs: now,
    // intents: deliberately unwired — no intents store exists in production yet (§10 row 11a is
    // calendar-history-only detection). deps.intents is a test seam, not a production source.
    intents: Array.isArray(deps.intents) ? deps.intents : [],
    sources,
  });

  // The detection row goes in FIRST so a chain failure can never lose the detection. The insert is
  // also the atomic claim: a 409 means a concurrent tick won the day — stop, run no chain.
  const claimed = await insertScanRow({
    uid: u.uid,
    scan_day: day,
    scanned_at: new Date(now).toISOString(),
    history_event_count: receipt.real_event_count,
    detections: receipt.candidates,
  }, supa, fetchImpl);
  if (!claimed) return { status: "already_scanned" };
  if (receipt.candidates.length === 0) return { status: "abstained" };

  // CADENCE-1 gate (§10 row CADENCE-1). An observe_only detection was genuinely seen and is
  // already on the row above — but its gaps are not a cadence, so "overdue" names no real debt.
  // It must not spend a Places search, must not produce a chain, and must not count as a reason
  // to act. Only actionable detections continue.
  const actionable = receipt.candidates.filter((candidate) => !candidate.observe_only);
  if (actionable.length === 0) {
    return { status: "observed", observeOnly: receipt.candidates.map((c) => c.care_type) };
  }

  // 11b chain, in-process, on the first ACTIONABLE detected category.
  const category = actionable[0].care_type;
  try {
    const careHistory = [];
    for (const source of sources) {
      for (const event of source.events) {
        if (event.location) careHistory.push({ careType: source.careType, location: event.location, startMs: event.startMs });
      }
    }
    const anchors = deriveAnchors({
      homeAddress: u.home_address || null,
      calendarEvents: history,
      careHistory,
    });
    const searchFetch = deps.searchFetch || globalThis.fetch;
    const search = await (deps.searchCareCandidates || searchCareCandidates)({
      category,
      anchors,
      apiKey: deps.mapsKey || process.env.LIFE_MAPS_KEY,
      fetchImpl: searchFetch,
    });
    const evaluated = search.definitions.length
      ? await (deps.evaluateCareCandidates || evaluateCareCandidates)(search.definitions, searchFetch)
      : { schema_version: 1, candidates: [], selected_provider_id: null };
    // anchors_used is presence-only: the 11b evidence rule — the private home value is a search
    // input, never a logged/persisted value. Provider names/ids are public data and may persist.
    const chain = {
      category,
      anchors_used: {
        home: Boolean(anchors.home),
        work: Boolean(anchors.work),
        usual_provider_care_types: anchors.usualProviders.map((p) => p.careType),
      },
      candidates: evaluated.candidates,
      selected_provider_id: evaluated.selected_provider_id,
      shortfall_reason: search.shortfallReason || null,
    };
    // The Places spend above already happened — a silently dropped PATCH would burn the spend and
    // hide the loss, so a failed chain persist must be VISIBLE (injectable logger, console.error
    // default). The detection row itself is safe either way: it landed before the chain ran.
    const persisted = await updateScanChain(u.uid, day, { chain }, supa, fetchImpl);
    if (!persisted) logError(`[care] chain-persist-failed uid=${u.uid} day=${day} category=${category}`);

    // ── 11c/11d, behind the gate ────────────────────────────────────────────────────────────────
    // The gate is checked BEFORE anything is constructed, so with LM_BOOKING_ENABLED absent not one
    // steel call, Telegram send, or calendar write can occur — the 11a/11b behaviour is unchanged.
    const bookingEnabled = deps.bookingEnabled !== undefined
      ? Boolean(deps.bookingEnabled)
      : process.env.LM_BOOKING_ENABLED === "1";
    const selected = evaluated.candidates.find((c) => c.provider_id === evaluated.selected_provider_id) || null;
    if (!bookingEnabled || !selected) {
      return { status: "detected", category, selectedProviderId: evaluated.selected_provider_id };
    }

    // Nothing below here may run twice for the same overdue care. The check reads PRIOR days' rows,
    // because that is where yesterday's booking lives.
    const priorBooking = await findLiveBooking(u.uid, category, now, supa, fetchImpl);
    if (priorBooking) {
      const record = { outcome: "already_booked_ref", care_type: category, ref_scan_id: priorBooking.id, ref_scan_day: priorBooking.scanDay };
      const noted = await updateScanChain(u.uid, day, { chain: { ...chain, booking: record } }, supa, fetchImpl);
      if (!noted) logError(`[care] booking-dedup-persist-failed uid=${u.uid} day=${day} ref=${priorBooking.id}`);
      return {
        status: "detected",
        category,
        selectedProviderId: evaluated.selected_provider_id,
        bookingOutcome: "already_booked_ref",
      };
    }

    const detection = actionable[0];
    // Days since the last visit = the cadence plus how far past it we are. Both numbers are the
    // detector's own arithmetic on real events; nothing here re-derives or rounds them differently.
    const sinceDays = Number.isFinite(detection.personal_interval_days) && Number.isFinite(detection.overdue_days)
      ? detection.personal_interval_days + detection.overdue_days
      : detection.overdue_days;

    let booking;
    try {
      booking = await executeBooking({
        candidate: selected,
        user: u,
        // The slot POLICY (which datetime to request) is deliberately not invented here: picking a
        // time needs the user's real availability, and a guessed 木曜18:00 would be a fabricated
        // commitment. Absent an injected preference the executor honestly fails on the date field.
        slotPreference: deps.slotPreference || null,
        // The executor gets a deadline SHORTER than forEachUserSafe's per-tenant abandon (90s), so a
        // hung provider page cannot keep the single OSS steel session past the tick that owns it.
        deps: { cdp: deps.cdp || makeSteelCdpClient(), deadlineMs: deps.bookingDeadlineMs },
      });
    } catch (error) {
      booking = {
        schema_version: 1,
        outcome: "honest_failure",
        provider_id: selected.provider_id,
        reservation_url: selected.reservation_url || null,
        reason_code: "booking_executor_failed",
        reason: `予約処理が途中で失敗しました（${String((error && error.message) || error)}）`,
        submitted: false,
      };
    }

    const aftercare = await runAftercare({
      booking,
      candidate: selected,
      candidates: evaluated.candidates,
      careType: category,
      sinceDays,
      user: u,
      deps: {
        sendMessage: deps.sendMessage || sendMessage,
        telegramToken: deps.telegramToken !== undefined ? deps.telegramToken : process.env.LM_TELEGRAM_BOT_TOKEN,
        calendar: deps.calendar,
        logError,
        // lm_care_scan_log's append-only trigger permits only chain / chain_error to be filled in
        // after insert, so the booking rides INSIDE the chain jsonb — no new column, no migration.
        recordBooking: (record) => updateScanChain(u.uid, day, { chain: { ...chain, booking: record } }, supa, fetchImpl),
      },
    }).catch((error) => {
      logError(`[care] aftercare-failed uid=${u.uid} day=${day} ${String((error && error.message) || error)}`);
      return { status: "failed" };
    });

    return {
      status: "detected",
      category,
      selectedProviderId: evaluated.selected_provider_id,
      bookingOutcome: booking.outcome,
      aftercareStatus: aftercare.status,
    };
  } catch (error) {
    const chainError = String((error && error.message) || error);
    const persisted = await updateScanChain(u.uid, day, { chain_error: chainError }, supa, fetchImpl).catch(() => false);
    if (!persisted) logError(`[care] chain-persist-failed uid=${u.uid} day=${day} chain_error=${chainError}`);
    return { status: "detected", category, chainError };
  }
}

module.exports = { careUserOnce, classifyCareHistory, CARE_TYPE_KEYWORDS };
