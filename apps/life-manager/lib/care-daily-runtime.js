"use strict";
// lib/care-daily-runtime.js — 11a/11b PHY runtime (§10 rows 11a/11b, §9.1 PHYSICAL organ).
// The detector, anchors, candidate search, and evaluator all existed, were tested, and were called
// by NOTHING in production — the same unreachable-rule disease 12c had. This module is the cure:
// careUserOnce runs on the 60s tick, claims one real scan per user per UTC day durably in
// lm_care_scan_log (no in-memory counters — restarts cannot double-scan or forget), reads ~18
// months of the user's OWN calendar history, and records what the detector saw. Abstention (no
// candidates) is the honest common case and gets a row too. On a REAL detection the 11b chain runs
// in-process — anchors → anchored candidate search → route evaluation — and the full result lands
// on the same scan row. NO side effects here: no booking, no calendar writes, no messages of any
// kind — 11c/11d own those. The product of this module is the self-executing detection+candidates
// record.

const { detectCalendarCare } = require("./care-detector-runtime.js");
const { deriveAnchors } = require("./care-anchors.js");
const { searchCareCandidates } = require("./care-candidate-search.js");
const { evaluateCareCandidates } = require("./care-candidates.js");
const { fetchCalendarHistory } = require("./events.js");

// The user's own words → the 11a care types (dental / haircut / clinic — the exact categories
// care-candidate-search.js CATEGORY_KEYWORDS knows; no invented types). This is deterministic data
// linkage like careTag() in care-detector.js, not text inference: an event only counts as a care
// visit when its title literally names the care. 健康診断/内科 fold into clinic — the 11a evidence
// (2026-07-25 remeasure) grouped provider-side queries the same way.
const CARE_TYPE_KEYWORDS = Object.freeze({
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
      historyMs: deps.historyMs, // undefined → events.js CARE_HISTORY_MS (~18 months)
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

  // 11b chain, in-process, on the first (only expected) detected category.
  const category = receipt.candidates[0].care_type;
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
    return { status: "detected", category, selectedProviderId: evaluated.selected_provider_id };
  } catch (error) {
    const chainError = String((error && error.message) || error);
    const persisted = await updateScanChain(u.uid, day, { chain_error: chainError }, supa, fetchImpl).catch(() => false);
    if (!persisted) logError(`[care] chain-persist-failed uid=${u.uid} day=${day} chain_error=${chainError}`);
    return { status: "detected", category, chainError };
  }
}

module.exports = { careUserOnce, classifyCareHistory, CARE_TYPE_KEYWORDS };
