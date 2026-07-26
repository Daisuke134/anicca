// care-booking-wiring.test.js — 11c/11d wiring: careUserOnce may only book BEHIND LM_BOOKING_ENABLED,
// only for an actionable (CADENCE-1 observe_only:false) detection, and only on a web route. With the
// gate absent the runtime must behave exactly as 11a/11b did — zero steel calls, zero Telegram, zero
// calendar writes. Run: node --test lib/care-booking-wiring.test.js
"use strict";
const { test } = require("node:test");
const assert = require("node:assert");
const { careUserOnce } = require("./care-daily-runtime.js");

const NOW = Date.parse("2026-07-26T00:00:00Z");
const DAY_MS = 86400000;
const USER = { uid: "u-care", name: "山田太郎", phone: "+819012345678", email: "y@example.com", telegram_chat_id: 4242, home_address: "東京都新宿区1-1-1" };

// Same stable-cadence fixture the 11a/11b runtime tests use: 5 visits, gaps 40/34/46/40, 70 days
// since the last one — CADENCE-1 rates this actionable, so the chain (and now the booking) may run.
const HAIRCUT_DAYS_AGO = [230, 190, 156, 110, 70];
function overdueHaircutHistory() {
  const office = (n) => ({ id: `of${n}`, summary: "チーム定例", location: "オフィス東京", startMs: NOW - n * 7 * DAY_MS, start: { dateTime: new Date(NOW - n * 7 * DAY_MS).toISOString() } });
  const haircut = (daysAgo, i) => ({ id: `hc${i + 1}`, summary: "散髪", location: "サロンA 新宿", startMs: NOW - daysAgo * DAY_MS, start: { dateTime: new Date(NOW - daysAgo * DAY_MS).toISOString() } });
  return [...HAIRCUT_DAYS_AGO.map(haircut), office(1), office(2), office(3), office(4), office(5), office(6)];
}

// The bimodal burst CADENCE-1 demotes to observe_only — it must never reach a booking.
function burstClinicHistory() {
  const gapDays = [47.02, 5.75, 8.52, 419.0, 3.25];
  const offsets = [0];
  for (const gap of gapDays) offsets.push(offsets[offsets.length - 1] + gap);
  const span = offsets[offsets.length - 1];
  return offsets.map((o, i) => {
    const ms = NOW - (span - o + 58) * DAY_MS;
    return { id: `cl${i}`, summary: "クリニック", location: "内科クリニック新宿", startMs: ms, start: { dateTime: new Date(ms).toISOString() } };
  });
}

function fakeSupa({ existingRows = [], postStatus = 201, patchOk = true } = {}) {
  const calls = { gets: [], posts: [], patches: [] };
  const fetchImpl = async (url, opts = {}) => {
    const method = (opts.method || "GET").toUpperCase();
    if (method === "GET") { calls.gets.push(url); return { ok: true, status: 200, json: async () => existingRows }; }
    if (method === "POST") { calls.posts.push(JSON.parse(opts.body)); return { ok: postStatus === 201, status: postStatus, json: async () => [], text: async () => "" }; }
    calls.patches.push({ url, body: JSON.parse(opts.body) });
    return { ok: patchOk, status: patchOk ? 204 : 500, json: async () => [] };
  };
  return { calls, fetchImpl };
}

const WEB_CANDIDATE = {
  provider_id: "p-web", public_name: "サロンA", official_url: "https://salon.example.jp",
  proximity_rank: 1, usual_provider: true,
  reservation_route: "web", reservation_url: "https://salon.example.jp/reserve",
};
const EMAIL_CANDIDATE = {
  provider_id: "p-mail", public_name: "サロンB", official_url: "https://salonb.example.jp",
  proximity_rank: 2, usual_provider: false,
  reservation_route: "email", reservation_url: "mailto:b@salonb.example.jp",
};

function fakeCdp() {
  const calls = [];
  return {
    calls,
    async createSession() { calls.push(["createSession"]); return { id: "sess-1", websocketUrl: "ws://x/" }; },
    async navigate(s, url) { calls.push(["navigate", url]); },
    async readForm() {
      calls.push(["readForm"]);
      return {
        submitSelector: "#go",
        fields: [
          { selector: "#n", label: "お名前", name: "name", type: "text", required: true },
          { selector: "#e", label: "メールアドレス", name: "email", type: "email", required: true },
          { selector: "#d", label: "ご希望日時", name: "dt", type: "datetime-local", required: true },
        ],
      };
    },
    async fill(s, selector, value) { calls.push(["fill", selector, value]); },
    async submit() { calls.push(["submit"]); },
    async readConfirmation() { calls.push(["readConfirmation"]); return { text: "予約を受け付けました。予約番号: H-42" }; },
    async releaseSession() { calls.push(["releaseSession"]); },
  };
}

function bookingDeps(supa, overrides = {}) {
  const sent = [];
  const events = [];
  const cdp = fakeCdp();
  const deps = {
    supaUrl: "https://db.example",
    supaKey: "service",
    fetchImpl: supa.fetchImpl,
    fetchCalendarHistory: async () => overdueHaircutHistory(),
    searchCareCandidates: async () => ({ definitions: [{}], shortfallReason: null }),
    evaluateCareCandidates: async () => ({ schema_version: 1, candidates: [WEB_CANDIDATE, EMAIL_CANDIDATE], selected_provider_id: "p-web" }),
    cdp,
    slotPreference: { startIso: "2026-08-08T11:00:00+09:00" },
    telegramToken: "tok",
    sendMessage: async (token, chatId, text) => { sent.push({ chatId, text }); return { ok: true, result: { message_id: 555 } }; },
    calendar: { async createEvent(uid, args) { events.push({ uid, args }); return { successful: true }; } },
    ...overrides,
  };
  return { deps, sent, events, cdp };
}

test("gate absent: the 11a/11b behaviour is unchanged — zero steel, zero Telegram, zero calendar", async () => {
  const supa = fakeSupa();
  const { deps, sent, events, cdp } = bookingDeps(supa, { bookingEnabled: false });
  const result = await careUserOnce(USER, NOW, deps);

  assert.equal(result.status, "detected");
  assert.equal(result.selectedProviderId, "p-web");
  assert.equal(result.bookingOutcome, undefined, "no booking leg at all");
  assert.equal(cdp.calls.length, 0, "zero steel calls with the gate off");
  assert.equal(sent.length, 0);
  assert.equal(events.length, 0);
  // The chain patch is the ONLY write, exactly as before.
  assert.equal(supa.calls.patches.length, 1);
  assert.equal(supa.calls.patches[0].body.chain.booking, undefined);
});

test("gate on + web route: booking runs, aftercare reports, and the booking lands on the chain", async () => {
  const supa = fakeSupa();
  const { deps, sent, events, cdp } = bookingDeps(supa, { bookingEnabled: true });
  const result = await careUserOnce(USER, NOW, deps);

  assert.equal(result.status, "detected");
  assert.equal(result.bookingOutcome, "booked");
  assert.equal(cdp.calls.filter((c) => c[0] === "submit").length, 1);
  assert.equal(cdp.calls.filter((c) => c[0] === "releaseSession").length, 1);
  assert.equal(sent.length, 1, "one 事後報告");
  assert.equal(events.length, 1, "one calendar event");

  const bookingPatch = supa.calls.patches.at(-1).body.chain.booking;
  assert.equal(bookingPatch.outcome, "booked");
  assert.equal(bookingPatch.provider_id, "p-web");
  assert.equal(bookingPatch.confirmation.number, "H-42");
  assert.equal(bookingPatch.booked_slot, "2026-08-08T11:00:00+09:00");
});

test("gate on + email route: honestly declared unimplemented, no steel session, still reported", async () => {
  const supa = fakeSupa();
  const { deps, sent, events, cdp } = bookingDeps(supa, {
    bookingEnabled: true,
    evaluateCareCandidates: async () => ({ schema_version: 1, candidates: [EMAIL_CANDIDATE], selected_provider_id: "p-mail" }),
  });
  const result = await careUserOnce(USER, NOW, deps);

  assert.equal(result.bookingOutcome, "honest_failure");
  assert.equal(cdp.calls.length, 0, "the email route never opens a browser");
  assert.equal(events.length, 0, "no calendar event for an unbooked visit");
  assert.equal(sent.length, 1);
  assert.equal(supa.calls.patches.at(-1).body.chain.booking.reason_code, "email_route_not_implemented");
});

test("CADENCE-1: an observe_only detection never books even with the gate on", async () => {
  const supa = fakeSupa();
  const { deps, sent, cdp } = bookingDeps(supa, {
    bookingEnabled: true,
    fetchCalendarHistory: async () => burstClinicHistory(),
  });
  const result = await careUserOnce(USER, NOW, deps);

  assert.equal(result.status, "observed");
  assert.equal(cdp.calls.length, 0);
  assert.equal(sent.length, 0);
});

test("a booking that throws never loses the detection row", async () => {
  const supa = fakeSupa();
  const { deps, cdp } = bookingDeps(supa, {
    bookingEnabled: true,
    cdp: { async createSession() { throw new Error("steel unreachable"); } },
  });
  const result = await careUserOnce(USER, NOW, deps);
  assert.equal(result.status, "detected");
  assert.equal(result.bookingOutcome, "honest_failure");
  assert.equal(supa.calls.posts.length, 1, "the detection row still landed");
  void cdp;
});

test("no selected candidate: nothing to book, and it says so instead of picking one", async () => {
  const supa = fakeSupa();
  const { deps, cdp, sent } = bookingDeps(supa, {
    bookingEnabled: true,
    evaluateCareCandidates: async () => ({ schema_version: 1, candidates: [EMAIL_CANDIDATE], selected_provider_id: null }),
  });
  const result = await careUserOnce(USER, NOW, deps);
  assert.equal(result.bookingOutcome, undefined);
  assert.equal(cdp.calls.length, 0);
  assert.equal(sent.length, 0);
});

// ─── review findings ────────────────────────────────────────────────────────────────────────────

// A Supabase double that REMEMBERS rows across days: the cross-day double-booking bug is invisible to
// a stateless double, because yesterday's booking lives on yesterday's row.
function statefulSupa() {
  const rows = [];
  let nextId = 1;
  const fetchImpl = async (url, opts = {}) => {
    const method = (opts.method || "GET").toUpperCase();
    const query = new URLSearchParams(String(url).split("?")[1] || "");
    const uid = String(query.get("uid") || "").replace(/^eq\./, "");
    const day = String(query.get("scan_day") || "").replace(/^eq\./, "");
    if (method === "GET") {
      if (day) {
        const hit = rows.filter((r) => r.uid === uid && r.scan_day === day).map((r) => ({ id: r.id }));
        return { ok: true, status: 200, json: async () => hit };
      }
      const history = rows
        .filter((r) => r.uid === uid)
        .sort((a, b) => (a.scan_day < b.scan_day ? 1 : -1))
        .map((r) => ({ id: r.id, scan_day: r.scan_day, chain: r.chain || null }));
      return { ok: true, status: 200, json: async () => history };
    }
    if (method === "POST") {
      const row = JSON.parse(opts.body);
      if (rows.some((r) => r.uid === row.uid && r.scan_day === row.scan_day)) {
        return { ok: false, status: 409, json: async () => [], text: async () => "" };
      }
      rows.push({ ...row, id: nextId += 1 });
      return { ok: true, status: 201, json: async () => [], text: async () => "" };
    }
    const patch = JSON.parse(opts.body);
    for (const row of rows) if (row.uid === uid && row.scan_day === day) Object.assign(row, patch);
    return { ok: true, status: 204, json: async () => [] };
  };
  return { rows, fetchImpl, rowFor: (scanDay) => rows.find((r) => r.scan_day === scanDay) };
}

// 🔴 Finding 8: the scan runs EVERY day and the overdue detection stays true until a new visit lands
// on the calendar. Without reading prior rows, day 2 books the same haircut all over again.
test("a booking recorded on a PRIOR day blocks a second booking for the same care", async () => {
  const supa = statefulSupa();
  const day1 = bookingDeps(supa, { bookingEnabled: true });
  const first = await careUserOnce(USER, NOW, day1.deps);
  assert.equal(first.bookingOutcome, "booked");
  assert.equal(day1.sent.length, 1);

  const day2 = bookingDeps(supa, { bookingEnabled: true });
  const second = await careUserOnce(USER, NOW + DAY_MS, day2.deps);

  assert.equal(second.status, "detected", "the detection itself still lands on day 2");
  assert.equal(second.bookingOutcome, "already_booked_ref");
  assert.equal(day2.cdp.calls.length, 0, "no second steel session");
  assert.equal(day2.sent.length, 0, "no second 事後報告 for a booking already made");
  assert.equal(day2.events.length, 0, "no second calendar event");

  const booking = supa.rowFor("2026-07-27").chain.booking;
  assert.equal(booking.outcome, "already_booked_ref");
  assert.equal(booking.ref_scan_id, supa.rowFor("2026-07-26").id);
});

test("an unconfirmed (possibly_booked) prior day blocks the retry too — that is the double-booking case", async () => {
  const supa = statefulSupa();
  const day1 = bookingDeps(supa, {
    bookingEnabled: true,
    cdp: { ...fakeCdp(), async readConfirmation() { return { text: "送信中です…" }; } },
  });
  const first = await careUserOnce(USER, NOW, day1.deps);
  assert.equal(first.bookingOutcome, "possibly_booked");

  const day2 = bookingDeps(supa, { bookingEnabled: true });
  const second = await careUserOnce(USER, NOW + DAY_MS, day2.deps);
  assert.equal(second.bookingOutcome, "already_booked_ref");
  assert.equal(day2.cdp.calls.length, 0);
});

test("a booking older than the dedup window no longer blocks a fresh one", async () => {
  const supa = statefulSupa();
  supa.rows.push({
    id: 1, uid: USER.uid, scan_day: "2026-01-10",
    chain: { category: "haircut", booking: { outcome: "booked", booked_slot: "2026-01-12T11:00:00+09:00" } },
  });
  const { deps } = bookingDeps(supa, { bookingEnabled: true });
  const result = await careUserOnce(USER, NOW, deps);
  assert.equal(result.bookingOutcome, "booked", "a months-old booking must not block the care forever");
});

test("a recent booking for a DIFFERENT care type does not block this one", async () => {
  const supa = statefulSupa();
  supa.rows.push({
    id: 1, uid: USER.uid, scan_day: "2026-07-20",
    chain: { category: "dental", booking: { outcome: "booked", booked_slot: "2026-08-01T10:00:00+09:00" } },
  });
  const { deps } = bookingDeps(supa, { bookingEnabled: true });
  const result = await careUserOnce(USER, NOW, deps);
  assert.equal(result.bookingOutcome, "booked");
});
